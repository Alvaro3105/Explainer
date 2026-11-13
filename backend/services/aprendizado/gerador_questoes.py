import json
import logging
import os
import random
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.request

LETRAS = ("A", "B", "C", "D")

ROTULOS_DIFICULDADE = {"Normal": "Médio"}


def rotulo_dificuldade(dificuldade):
    return ROTULOS_DIFICULDADE.get(dificuldade, dificuldade)


registro = logging.getLogger(__name__)

TENTATIVAS_IA = 2
TEMPO_LIMITE_IA = 45
PRAZO_TOTAL_IA = 80       # segundos para todas as tentativas de um pedido, somadas
PAUSA_APOS_COTA = 30      # sem chamar o provedor por este tempo depois de um "limite atingido"
PAUSA_MAXIMA = 120
LIMITE_ENUNCIADO = 1500
LIMITE_ALTERNATIVA = 400
LIMITE_EXPLICACAO = 1200
MENSAGEM_INDISPONIVEL = "Não foi possível gerar as questões agora. Tente novamente em instantes."
MENSAGEM_COTA = "A IA atingiu o limite de uso por agora. Aguarde cerca de um minuto e tente de novo."
MENSAGEM_CHAVE = "A geração de questões está indisponível no momento. Avise a equipe do ExplAIner."
MENSAGEM_RESPOSTA = "A IA devolveu questões incompletas. Tente gerar de novo."

# Trechos (sem acento e em minúsculas) que aparecem quando a própria IA percebe, na explicação,
# que a questão não fecha: ela "reavalia", "ajusta" o enunciado ou admite que nenhuma
# alternativa serve. Questão assim não tem resposta certa e é descartada.
SINAIS_DE_QUESTAO_QUEBRADA = (
    "reavaliando", "recalculando", "refazendo o calculo", "ajustando para", "ajustando a questao",
    "ajustando o enunciado", "corrigindo o enunciado", "corrigindo a questao", "caso a questao peca",
    "erro no enunciado", "enunciado esta incorreto", "questao esta incorreta", "gabarito incorreto",
    "nenhuma das alternativas", "nenhuma alternativa esta correta", "nao ha alternativa correta",
    "nao existe alternativa correta", "alternativa mais proxima", "valor mais proximo entre as alternativas",
)


def questoes_de_reserva(quantidade):
    """Questões pedidas a mais (uma a cada cinco), para repor as que a validação descartar."""
    return -(-int(quantidade) // 5)


def _explicacao_contraditoria(explicacao):
    texto = _normalizar(explicacao)
    return any(sinal in texto for sinal in SINAIS_DE_QUESTAO_QUEBRADA)


class ErroDaIA(RuntimeError):
    """Falha de um provedor. `motivo`: "chave" (recusada), "cota" (limite de uso),
    "resposta" (veio fora do formato) ou "indisponivel" (rede, tempo esgotado, erro do provedor)."""

    def __init__(self, motivo, detalhe, espera=None):
        super().__init__(f"Falha ao gerar questões pela IA ({motivo}): {detalhe}")
        self.motivo = motivo
        self.espera = espera


class ErroDeGeracao(RuntimeError):
    """O que o aluno vê quando nenhuma fonte gerou as questões: mensagem, status HTTP e espera sugerida."""

    def __init__(self, mensagem, status=502, espera=None):
        super().__init__(mensagem)
        self.status = status
        self.espera = espera


def _igual(texto):
    """Chave para achar textos repetidos: minúsculas e espaços simples. Sinais e números
    ficam como estão, porque "x + 7" e "x − 7" são questões diferentes."""
    return re.sub(r"\s+", " ", str(texto or "")).strip().casefold()


_NUMERO = re.compile(r"\d[\d.]*(?:,\d+)?")


def _numeros(texto):
    """Números do texto, na ordem em que aparecem, lidos no formato brasileiro (1.200,50)."""
    valores = []
    for bruto in _NUMERO.findall(str(texto or "")):
        bruto = bruto.rstrip(".")
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", bruto):
            bruto = bruto.replace(".", "")          # ponto de milhar
        try:
            valores.append(round(float(bruto.replace(",", ".")), 6))
        except ValueError:
            continue
    return valores


def _mesmo_valor(a, b):
    """Iguais, aceitando a troca entre porcentagem e decimal (36% e 0,36)."""
    return any(abs(a - b * fator) < 1e-6 for fator in (1, 100, 0.01))


def _gabarito_desmentido_pelos_numeros(alternativas, correta, explicacao):
    """A conta da explicação termina no número de OUTRA alternativa e nunca cita o da correta?

    É uma conferência estreita de propósito, para só recusar o caso sem dúvida: as quatro
    alternativas têm um único número cada, todos diferentes; a explicação traz uma conta
    (tem "="); o resultado depois do último "=" é o valor de outra alternativa; e o valor
    do gabarito não aparece em lugar nenhum da explicação.
    Não resolve a questão: só pega a letra do gabarito trocada. Em qualquer outro caso
    (texto, datas, unidades diferentes, mais de um número por alternativa) não opina.
    """
    valores = {}
    for letra, texto in zip(LETRAS, alternativas):
        numeros = _numeros(texto)
        if len(numeros) != 1:
            return False
        valores[letra] = numeros[0]
    if len(set(valores.values())) < len(LETRAS):
        return False
    explicacao = str(explicacao or "")
    if "=" not in explicacao:
        return False
    depois_do_igual = _numeros(explicacao.rsplit("=", 1)[1])
    if not depois_do_igual:
        return False
    if any(_mesmo_valor(numero, valores[correta]) for numero in _numeros(explicacao)):
        return False
    return any(_mesmo_valor(depois_do_igual[0], valor) for letra, valor in valores.items() if letra != correta)


def _questao_valida(item):
    """Devolve a questão no formato do sistema, ou None se ela não puder ser usada."""
    if not isinstance(item, dict):
        return None
    enunciado = str(item.get("enunciado", "")).strip()
    alternativas = item.get("alternativas", {})
    correta = str(item.get("alternativa_correta", "")).upper().strip()
    if isinstance(alternativas, list) and len(alternativas) == 4:
        alternativas = dict(zip(LETRAS, alternativas))
    if not enunciado or len(enunciado) > LIMITE_ENUNCIADO or not isinstance(alternativas, dict) or correta not in LETRAS:
        return None
    textos = [str(alternativas.get(letra, "") or "").strip() for letra in LETRAS]
    if any(not texto or len(texto) > LIMITE_ALTERNATIVA for texto in textos):
        return None
    if len({_igual(texto) for texto in textos}) < len(LETRAS):
        return None  # alternativas repetidas: a questão teria mais de uma resposta igual
    explicacao = str(item.get("explicacao", "") or "").strip()
    if _explicacao_contraditoria(explicacao):
        return None  # a explicação desmente o próprio gabarito
    if _gabarito_desmentido_pelos_numeros(textos, correta, explicacao):
        return None  # a conta chega ao valor de outra alternativa: a letra do gabarito está trocada
    explicacao = explicacao[:LIMITE_EXPLICACAO]
    return {
        "enunciado": enunciado,
        "alternativas": dict(zip(LETRAS, textos)),
        "alternativa_correta": correta,
        "explicacao": explicacao or "Revise o conceito apresentado para compreender a resposta correta.",
    }


def _validar_questoes(questoes, quantidade):
    """Fica com as primeiras `quantidade` questões válidas e diferentes entre si.

    Questão incompleta, com alternativas repetidas, grande demais, com explicação que
    desmente o gabarito ou com o mesmo enunciado de outra do lote é descartada.
    Se não sobrar a quantidade pedida, o lote é recusado.
    """
    if not isinstance(questoes, list) or len(questoes) < quantidade:
        raise ValueError("A IA não retornou a quantidade solicitada de questões.")
    validas, enunciados = [], set()
    for item in questoes:
        if len(validas) == quantidade:
            break
        questao = _questao_valida(item)
        if questao is None or _igual(questao["enunciado"]) in enunciados:
            continue
        enunciados.add(_igual(questao["enunciado"]))
        validas.append(questao)
    if len(validas) < quantidade:
        raise ValueError("A IA retornou questões incompletas, repetidas ou fora do formato.")
    return validas


SISTEMA_IA = "Você é um elaborador rigoroso de questões educacionais. Priorize precisão factual e siga exatamente o formato JSON solicitado."
MODELOS_GEMINI = ("gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview")


def _montar_prompt(materia, tema, dificuldade, quantidade, excluir_enunciados=None, subtema=None):
    nivel = rotulo_dificuldade(dificuldade)
    foco = (f"Tema: {tema}. Subtema: {subtema}. Todas as questões devem tratar especificamente do subtema \"{subtema}\"."
            if subtema else f"Tema específico: {tema}.")
    prompt = f"""Crie exatamente {quantidade} questões de múltipla escolha em português brasileiro.
Matéria: {materia}. {foco} Dificuldade: {nivel}.
Público: estudantes do Ensino Médio que se preparam para o ENEM. Use linguagem clara e adequada a essa idade.
Não misture conteúdos de outras matérias: todas as questões precisam ser de {materia}.
As questões devem ser educacionalmente corretas, distintas, relevantes ao tema e apropriadas a estudantes.
Cada questão deve ter quatro alternativas plausíveis A, B, C e D, apenas uma correta, e explicação curta.
Antes de escrever cada questão, resolva-a por completo e confira que exatamente uma alternativa está correta e que é ela a indicada em "alternativa_correta". Se a conta não fechar com nenhuma alternativa, descarte a questão e crie outra no lugar.
A explicação deve ser direta e chegar ao valor da alternativa correta. Não escreva dúvidas, correções nem revisões do próprio enunciado na explicação.
Não use 'todas as anteriores' nem 'nenhuma das anteriores'. Não repita enunciados, exemplos, números, contexto ou estrutura dentro deste lote.
Varie deliberadamente os subtemas, situações-problema, formatos de raciocínio e exemplos. Não use perguntas genéricas que só mencionem o tema no texto. TODA questão precisa testar diretamente um conceito do tema específico; se o tema for "corpo humano", não pergunte sobre planetas, clima ou fotossíntese. Antes de retornar, confira individualmente que cada enunciado, resposta e explicação pertence à matéria E ao tema. Se não houver conteúdo suficiente para criar questões corretas, gere variações de raciocínio dentro do próprio tema, nunca mude para outro assunto.
A dificuldade precisa mudar o tipo de raciocínio: Fácil = conceitos fundamentais e identificação; Médio = aplicação, interpretação e relações entre conceitos; Difícil = análise, inferência e resolução em várias etapas. Evite reutilizar a mesma pergunta em dificuldades diferentes.
Enunciados já usados que devem ser evitados nesta nova tentativa: {json.dumps((excluir_enunciados or [])[:80], ensure_ascii=False)}.
Não copie nem reformule superficialmente essas perguntas; crie questões novas dentro do mesmo tema.
Retorne exclusivamente JSON neste formato:
{{"questoes":[{{"enunciado":"...","alternativas":{{"A":"...","B":"...","C":"...","D":"..."}},"alternativa_correta":"A","explicacao":"..."}}]}}
"""
    return prompt


_pausas = {}  # provedor -> até quando (relógio monotônico) ele fica sem ser chamado
_trava_pausas = threading.Lock()


def _classificar(erro):
    """Motivo da falha e espera sugerida pelo provedor (cabeçalho Retry-After), se houver."""
    if isinstance(erro, urllib.error.HTTPError):
        espera = None
        try:
            espera = max(1, min(int(erro.headers.get("Retry-After", "")), PAUSA_MAXIMA))
        except (TypeError, ValueError, AttributeError):
            pass
        if erro.code == 429:
            return "cota", espera, "HTTP 429"
        corpo = ""
        try:
            corpo = erro.read(2000).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 - o corpo do erro é só uma pista a mais
            pass
        # O Gemini responde 400 (e não 401) quando a chave é inválida.
        if erro.code in (401, 403) or "API_KEY_INVALID" in corpo or "API key not valid" in corpo:
            return "chave", None, f"HTTP {erro.code}"
        return "indisponivel", espera, f"HTTP {erro.code}"
    if isinstance(erro, OSError):
        return "indisponivel", None, type(erro).__name__
    return "resposta", None, str(erro)[:120]


def _tentar(provedor, requisicoes, extrair, quantidade, prazo=None, insistir_na_cota=False):
    """Faz as requisições em ordem até uma devolver questões válidas.

    Para na hora quando a chave é recusada (insistir não adianta) e, a menos que
    `insistir_na_cota`, quando o limite de uso é atingido. Respeita o prazo total do pedido.
    Os avisos gravados no log nunca levam a chave nem o corpo da resposta.
    """
    with _trava_pausas:
        em_pausa = _pausas.get(provedor, 0) - time.monotonic()
    if em_pausa > 0:
        raise ErroDaIA("cota", f"{provedor} em pausa depois de atingir o limite", espera=int(em_pausa) + 1)
    motivos, espera, detalhe = [], None, "sem tempo para tentar"
    for requisicao in requisicoes:
        restante = (prazo - time.monotonic()) if prazo else TEMPO_LIMITE_IA
        if restante < 5:
            break
        try:
            with urllib.request.urlopen(requisicao, timeout=min(TEMPO_LIMITE_IA, restante)) as resposta:
                retorno = json.loads(resposta.read().decode("utf-8"))
            return _validar_questoes(json.loads(extrair(retorno))["questoes"], quantidade)
        except (OSError, KeyError, IndexError, TypeError, AttributeError, ValueError) as erro:
            motivo, espera_do_provedor, detalhe = _classificar(erro)
            motivos.append(motivo)
            espera = espera_do_provedor or espera
            registro.warning("IA %s: tentativa falhou (%s, %s)", provedor, motivo, detalhe)
            if motivo == "chave" or (motivo == "cota" and not insistir_na_cota):
                break
    if "chave" in motivos:
        motivo = "chave"
    elif motivos and all(m == "cota" for m in motivos):
        motivo = "cota"
        with _trava_pausas:
            _pausas[provedor] = time.monotonic() + (espera or PAUSA_APOS_COTA)
    else:
        motivo = motivos[-1] if motivos else "indisponivel"
    raise ErroDaIA(motivo, detalhe, espera=espera)


def _gerar_com_gemini(materia, tema, dificuldade, quantidade, excluir_enunciados=None, subtema=None, prazo=None):
    chave = os.getenv("GEMINI_API_KEY", "").strip()
    if not chave:
        return None
    escolhido = os.getenv("GEMINI_MODEL", "").strip()
    modelos = ([escolhido] if escolhido else []) + [m for m in MODELOS_GEMINI if m != escolhido]
    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": SISTEMA_IA}]},
        "contents": [{"role": "user", "parts": [{"text": _montar_prompt(
            materia, tema, dificuldade, quantidade + questoes_de_reserva(quantidade), excluir_enunciados, subtema)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9},
    }).encode("utf-8")
    requisicoes = [urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        data=payload,
        headers={"x-goog-api-key": chave, "Content-Type": "application/json"},
        method="POST",
    ) for modelo in modelos[:TENTATIVAS_IA]]
    # Cada modelo do Gemini tem a sua cota: se um atingiu o limite, vale tentar o seguinte.
    return _tentar("gemini", requisicoes, lambda r: r["candidates"][0]["content"]["parts"][0]["text"], quantidade,
                   prazo=prazo, insistir_na_cota=True)


def _gerar_com_openai(materia, tema, dificuldade, quantidade, excluir_enunciados=None, subtema=None, prazo=None):
    chave = os.getenv("OPENAI_API_KEY", "").strip()
    if not chave:
        return None
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": SISTEMA_IA},
            {"role": "user", "content": _montar_prompt(
                materia, tema, dificuldade, quantidade + questoes_de_reserva(quantidade), excluir_enunciados, subtema)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
        "max_completion_tokens": min(16000, 1000 + 450 * (int(quantidade) + questoes_de_reserva(quantidade))),
    }
    requisicao = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
        method="POST",
    )
    return _tentar("openai", [requisicao] * TENTATIVAS_IA, lambda r: r["choices"][0]["message"]["content"], quantidade,
                   prazo=prazo)


BANCO_TEMATICO = {
    "corpo humano": [
        ("Qual órgão bombeia o sangue para a circulação?", ["Pulmão", "Coração", "Estômago", "Rim"], "B", "O coração impulsiona o sangue pelos vasos sanguíneos."),
        ("Em qual estrutura ocorre a maior parte da absorção dos nutrientes?", ["Intestino delgado", "Esôfago", "Traqueia", "Bexiga"], "A", "As vilosidades do intestino delgado ampliam a absorção dos nutrientes."),
        ("Qual é a principal função dos alvéolos pulmonares?", ["Produzir bile", "Filtrar a urina", "Realizar trocas gasosas", "Bombear sangue"], "C", "Nos alvéolos, oxigênio e gás carbônico são trocados entre ar e sangue."),
        ("Qual sistema coordena respostas rápidas por meio de impulsos nervosos?", ["Digestório", "Nervoso", "Urinário", "Esquelético"], "B", "O sistema nervoso transmite sinais elétricos e químicos."),
        ("Qual célula transporta a maior parte do oxigênio no sangue?", ["Neurônio", "Hemácia", "Plaqueta", "Osteócito"], "B", "A hemoglobina das hemácias transporta a maior parte do oxigênio."),
        ("Qual órgão produz a bile, que auxilia na digestão de gorduras?", ["Pâncreas", "Fígado", "Baço", "Rim"], "B", "O fígado produz a bile, armazenada e concentrada na vesícula biliar."),
        ("Qual é a função principal dos rins?", ["Produzir movimentos", "Filtrar o sangue e formar urina", "Realizar trocas gasosas", "Digerir proteínas no estômago"], "B", "Os rins removem resíduos do sangue e ajudam a regular água e sais."),
        ("Onde ocorre a troca de oxigênio e gás carbônico entre o ar e o sangue?", ["Alvéolos", "Tendões", "Ventrículos intestinais", "Articulações"], "A", "A parede fina dos alvéolos permite a difusão dos gases."),
        ("Qual estrutura liga músculos aos ossos?", ["Ligamento", "Tendão", "Cartilagem articular", "Neurônio"], "B", "Tendões conectam músculos aos ossos e transmitem força."),
        ("Qual tipo de músculo atua principalmente de forma involuntária no intestino?", ["Esquelético", "Liso", "Voluntário estriado", "Nenhum"], "B", "A musculatura lisa movimenta o conteúdo do tubo digestório involuntariamente."),
        ("Qual parte do cérebro participa de forma importante do equilíbrio e da coordenação?", ["Cerebelo", "Hipófise", "Medula óssea", "Laringe"], "A", "O cerebelo contribui para coordenação motora, postura e equilíbrio."),
        ("Qual componente do sangue participa da coagulação?", ["Plaquetas", "Alvéolos", "Bile", "Neurônios"], "A", "As plaquetas ajudam a formar o tampão inicial na coagulação."),
        ("Qual é a sequência correta do caminho do alimento após a boca?", ["Faringe, esôfago, estômago", "Traqueia, pulmão, estômago", "Rim, ureter, bexiga", "Coração, artéria, estômago"], "A", "Após a boca, o alimento passa pela faringe, esôfago e estômago."),
        ("Que estrutura protege o cérebro?", ["Costelas", "Crânio", "Pelve", "Esterno"], "B", "Os ossos do crânio envolvem e protegem o encéfalo."),
        ("Qual hormônio ajuda a reduzir a glicose no sangue?", ["Insulina", "Adrenalina", "Melatonina", "Tiroxina"], "A", "A insulina favorece a entrada de glicose em células e reduz sua concentração sanguínea."),
        ("Por que a frequência cardíaca aumenta durante exercícios?", ["O corpo precisa levar mais oxigênio aos tecidos", "Os rins param de funcionar", "O estômago passa a respirar", "Os ossos produzem ar"], "A", "Os músculos ativos precisam de mais oxigênio e nutrientes, exigindo maior fluxo sanguíneo."),
        ("Como o diafragma contribui para a inspiração?", ["Contrai e aumenta o volume torácico", "Fecha os rins", "Diminui a caixa torácica ao relaxar", "Impede o ar de entrar"], "A", "Ao contrair, o diafragma desce e amplia o volume do tórax."),
        ("O que acontece com a urina antes de chegar à bexiga?", ["Passa pelos ureteres", "Passa pela traqueia", "Vai pelo esôfago", "É bombeada pela aorta"], "A", "Os ureteres conduzem a urina dos rins até a bexiga."),
        ("Qual relação descreve corretamente neurônios e sinapses?", ["Sinapses permitem comunicação entre células nervosas", "Sinapses filtram a urina", "Neurônios produzem bile", "Neurônios são ossos"], "A", "Sinapses são regiões de comunicação entre neurônios ou entre neurônios e outras células."),
        ("Por que as articulações são importantes para o movimento?", ["Permitem conexão e movimento relativo entre ossos", "Produzem glóbulos vermelhos em todos os casos", "Bombeiam sangue", "Fazem a digestão química"], "A", "As articulações conectam ossos e permitem movimentos de diferentes amplitudes."),
    ],
    "do 1º grau": [
        ("Resolva: x + 7 = 15.", ["6", "7", "8", "22"], "C", "Subtraindo 7 dos dois membros: x = 15 − 7 = 8."),
        ("Resolva: 2x = 18.", ["6", "9", "16", "36"], "B", "Dividindo os dois membros por 2: x = 9."),
        ("Resolva: 3x − 4 = 11.", ["3", "5", "7", "15"], "B", "Somando 4: 3x = 15; dividindo por 3: x = 5."),
        ("Resolva: 5x + 10 = 0.", ["−2", "−5", "2", "10"], "A", "Subtraindo 10: 5x = −10; dividindo por 5: x = −2."),
        ("Resolva: x/4 = 6.", ["1,5", "10", "24", "2"], "C", "Multiplicando os dois membros por 4: x = 24."),
        ("Resolva: 2(x + 3) = 14.", ["4", "5", "7", "11"], "A", "Dividindo por 2: x + 3 = 7; logo x = 4."),
        ("Resolva: 4x − 3 = 2x + 9.", ["3", "4", "6", "12"], "C", "Agrupando: 4x − 2x = 9 + 3, então 2x = 12 e x = 6."),
        ("Qual valor de x satisfaz 7 − x = 2?", ["−5", "2", "5", "9"], "C", "7 − x = 2 → −x = −5 → x = 5."),
        ("O triplo de um número menos 5 é igual a 16. Qual é o número?", ["5", "7", "11", "21"], "B", "3n − 5 = 16 → 3n = 21 → n = 7."),
        ("A soma de um número com o seu dobro é 27. Qual é o número?", ["7", "9", "13,5", "18"], "B", "n + 2n = 27 → 3n = 27 → n = 9."),
        ("Em uma equação do 1º grau, qual é o maior expoente da incógnita?", ["0", "1", "2", "3"], "B", "Na equação do 1º grau a incógnita aparece com expoente 1, como em ax + b = 0."),
        ("Qual destas é uma equação do 1º grau?", ["x² + 1 = 5", "3x − 2 = 7", "x³ = 8", "√x = 4"], "B", "Em 3x − 2 = 7 a incógnita tem expoente 1; as outras têm expoente 2, 3 ou raiz."),
        ("Resolva: (x − 1)/3 = 4.", ["11", "12", "13", "15"], "C", "Multiplicando por 3: x − 1 = 12; logo x = 13."),
        ("Resolva: −2x + 8 = 2.", ["−3", "3", "5", "−5"], "B", "Subtraindo 8: −2x = −6; dividindo por −2: x = 3."),
        ("João tem R$ 50 e gasta R$ 8 por dia. Depois de quantos dias ficará com R$ 10?", ["4", "5", "6", "8"], "B", "50 − 8d = 10 → 8d = 40 → d = 5."),
        ("Resolva: 0,5x = 7.", ["3,5", "7,5", "14", "0,07"], "C", "Dividindo por 0,5 (o mesmo que multiplicar por 2): x = 14."),
        ("Qual é a raiz da equação 6x + 6 = 6?", ["−1", "0", "1", "6"], "B", "6x + 6 = 6 → 6x = 0 → x = 0."),
        ("Ao resolver 3x + 2 = 3x + 5, o que se conclui?", ["x = 1", "x = 0", "A equação não tem solução", "Todo número é solução"], "C", "Subtraindo 3x dos dois lados sobra 2 = 5, o que é falso: não existe x que satisfaça a equação."),
        ("O perímetro de um retângulo é 30 cm e o comprimento é 9 cm. Qual é a largura?", ["6 cm", "12 cm", "15 cm", "21 cm"], "A", "2 × (9 + L) = 30 → 9 + L = 15 → L = 6 cm."),
        ("Para isolar x em x + 12 = 20, qual operação deve ser feita nos dois membros?", ["Somar 12", "Subtrair 12", "Multiplicar por 12", "Dividir por 12"], "B", "Subtraindo 12 dos dois membros mantém-se a igualdade e obtém-se x = 8."),
    ],
    "figuras de linguagem": [
        ("Em \"Seus olhos são duas estrelas\", qual figura de linguagem aparece?", ["Metáfora", "Comparação", "Hipérbole", "Eufemismo"], "A", "Há uma comparação implícita, sem conectivo como \"como\": isso é metáfora."),
        ("Em \"Ela é forte como um touro\", qual figura de linguagem aparece?", ["Comparação", "Metáfora", "Ironia", "Metonímia"], "A", "O conectivo \"como\" torna a comparação explícita."),
        ("Em \"Já te disse isso um milhão de vezes\", qual figura de linguagem aparece?", ["Hipérbole", "Eufemismo", "Prosopopeia", "Antítese"], "A", "Há um exagero intencional para dar ênfase: hipérbole."),
        ("Em \"O vento sussurrava segredos às árvores\", qual figura de linguagem aparece?", ["Personificação (prosopopeia)", "Hipérbole", "Metonímia", "Pleonasmo"], "A", "O vento recebe uma ação humana, sussurrar: personificação."),
        ("Em \"Ele partiu desta para melhor\", dito sobre alguém que morreu, qual figura aparece?", ["Eufemismo", "Hipérbole", "Ironia", "Catacrese"], "A", "A expressão suaviza uma ideia dolorosa: eufemismo."),
        ("Em \"Que belo trabalho! Você quebrou tudo\", qual figura de linguagem aparece?", ["Ironia", "Comparação", "Metáfora", "Aliteração"], "A", "Diz-se o contrário do que se pensa: ironia."),
        ("Em \"Li Machado de Assis nas férias\", referindo-se às obras do autor, qual figura aparece?", ["Metonímia", "Metáfora", "Hipérbole", "Antítese"], "A", "O autor é usado no lugar da obra: metonímia."),
        ("Em \"Ele ria por fora e chorava por dentro\", há oposição de ideias. Qual figura aparece?", ["Antítese", "Eufemismo", "Metonímia", "Pleonasmo"], "A", "A aproximação de ideias opostas (rir e chorar, fora e dentro) é antítese."),
        ("Em \"O silêncio ensurdecedor tomou conta da sala\", qual figura de linguagem aparece?", ["Paradoxo", "Eufemismo", "Metonímia", "Catacrese"], "A", "Ideias contraditórias reunidas no mesmo termo (silêncio que ensurdece) formam um paradoxo."),
        ("\"Subir para cima\" é exemplo de qual figura de linguagem?", ["Pleonasmo", "Metáfora", "Ironia", "Eufemismo"], "A", "Repete-se uma ideia já contida no verbo: pleonasmo (vicioso, neste caso)."),
        ("Em \"O pé da mesa quebrou\", qual figura de linguagem aparece?", ["Catacrese", "Hipérbole", "Ironia", "Antítese"], "A", "Uma metáfora já incorporada ao uso, por falta de termo próprio, é catacrese."),
        ("Em \"O rato roeu a roupa do rei de Roma\", qual recurso sonoro predomina?", ["Aliteração", "Assonância", "Onomatopeia", "Eufemismo"], "A", "A repetição do som consonantal /r/ caracteriza a aliteração."),
        ("Em \"O tique-taque do relógio me acordou\", qual figura de linguagem aparece?", ["Onomatopeia", "Metonímia", "Antítese", "Eufemismo"], "A", "\"Tique-taque\" imita um som: onomatopeia."),
        ("Qual é a principal diferença entre comparação e metáfora?", ["A comparação usa conectivo como \"como\"; a metáfora não", "A metáfora sempre usa \"como\"", "Não há diferença entre elas", "A comparação exagera e a metáfora suaviza"], "A", "As duas aproximam elementos por semelhança, mas só a comparação explicita o conectivo."),
        ("Qual figura de linguagem consiste em um exagero intencional?", ["Hipérbole", "Eufemismo", "Pleonasmo", "Catacrese"], "A", "A hipérbole amplia ou exagera algo para dar ênfase."),
        ("Qual figura de linguagem suaviza uma ideia desagradável?", ["Eufemismo", "Hipérbole", "Ironia", "Aliteração"], "A", "O eufemismo troca uma expressão dura por outra mais branda."),
        ("Em \"Bebi dois copos de água\", qual figura de linguagem aparece?", ["Metonímia", "Hipérbole", "Pleonasmo", "Antítese"], "A", "Usa-se o recipiente (copo) no lugar do conteúdo (água): metonímia."),
        ("Como se chama a repetição de sons vocálicos em um verso ou frase?", ["Assonância", "Aliteração", "Onomatopeia", "Hipérbato"], "A", "Assonância repete vogais; aliteração repete consoantes."),
        ("A inversão da ordem direta da frase, como em \"Ao parque fomos nós ontem\", chama-se:", ["Hipérbato", "Pleonasmo", "Eufemismo", "Catacrese"], "A", "O hipérbato altera a ordem sujeito-verbo-complemento."),
        ("Em \"Ela tinha uma voz doce e aveludada\", qual figura de linguagem aparece?", ["Sinestesia", "Hipérbole", "Antítese", "Metonímia"], "A", "A voz (audição) é descrita com termos do paladar e do tato: sinestesia."),
    ],
    "sistema solar": [
        ("Qual é a estrela do Sistema Solar?", ["Sol", "Sirius", "Lua", "Estrela Polar"], "A", "O Sol é a única estrela do Sistema Solar; os planetas giram ao seu redor."),
        ("Qual planeta é o mais próximo do Sol?", ["Mercúrio", "Vênus", "Terra", "Marte"], "A", "A ordem a partir do Sol começa por Mercúrio, Vênus, Terra e Marte."),
        ("Qual é o maior planeta do Sistema Solar?", ["Júpiter", "Saturno", "Netuno", "Terra"], "A", "Júpiter é o maior planeta, um gigante gasoso com mais de 11 vezes o diâmetro da Terra."),
        ("Qual planeta é mais conhecido pelos seus anéis bem visíveis?", ["Saturno", "Marte", "Mercúrio", "Vênus"], "A", "Os gigantes têm anéis, mas os de Saturno são os mais extensos e visíveis."),
        ("Quantos planetas tem o Sistema Solar segundo a classificação da União Astronômica Internacional de 2006?", ["8", "9", "7", "10"], "A", "Desde 2006 são oito planetas; Plutão passou a ser planeta anão."),
        ("Por que Plutão deixou de ser classificado como planeta em 2006?", ["Não domina gravitacionalmente a vizinhança da sua órbita", "Deixou de orbitar o Sol", "É maior que a Terra", "Não tem gravidade"], "A", "Plutão orbita o Sol e é arredondado, mas divide a órbita com outros corpos: é um planeta anão."),
        ("Qual é o planeta mais quente do Sistema Solar?", ["Vênus", "Mercúrio", "Marte", "Júpiter"], "A", "A atmosfera densa de gás carbônico de Vênus causa um efeito estufa intenso, mais quente até que Mercúrio."),
        ("O que é a Lua em relação à Terra?", ["Um satélite natural", "Um planeta anão", "Uma estrela", "Um cometa"], "A", "A Lua orbita a Terra e é seu único satélite natural."),
        ("Quanto tempo a Terra leva, aproximadamente, para dar uma volta completa ao redor do Sol?", ["365 dias", "24 horas", "30 dias", "12 horas"], "A", "A translação dura cerca de 365 dias e 6 horas; as 24 horas são a rotação."),
        ("Entre quais planetas fica o cinturão de asteroides principal?", ["Marte e Júpiter", "Terra e Marte", "Júpiter e Saturno", "Vênus e Terra"], "A", "O cinturão principal fica entre as órbitas de Marte e Júpiter."),
        ("Quais são os planetas rochosos (telúricos) do Sistema Solar?", ["Mercúrio, Vênus, Terra e Marte", "Júpiter, Saturno, Urano e Netuno", "Apenas a Terra", "Saturno e Urano"], "A", "Os quatro planetas internos são rochosos; os externos são gigantes gasosos ou gelados."),
        ("A cor avermelhada de Marte se deve principalmente a quê?", ["Óxido de ferro na superfície", "Lava ativa em toda a superfície", "Reflexo da luz de Júpiter", "Excesso de oxigênio na atmosfera"], "A", "A poeira rica em óxido de ferro, semelhante à ferrugem, dá a cor avermelhada."),
        ("Qual planeta gira \"deitado\", com o eixo de rotação inclinado em cerca de 98°?", ["Urano", "Netuno", "Marte", "Vênus"], "A", "Urano tem o eixo quase paralelo ao plano da órbita."),
        ("O que mantém os planetas em órbita ao redor do Sol?", ["A gravidade", "O magnetismo da Terra", "O vento solar", "A pressão atmosférica"], "A", "A atração gravitacional do Sol curva a trajetória dos planetas em órbitas."),
        ("O que é um cometa?", ["Um corpo de gelo e poeira que pode formar cauda perto do Sol", "Uma estrela pequena", "Um satélite da Terra", "Um planeta sem órbita"], "A", "Ao se aproximar do Sol, o gelo do cometa sublima e forma a cabeleira e a cauda."),
        ("Qual é o planeta mais distante do Sol?", ["Netuno", "Urano", "Plutão", "Saturno"], "A", "Netuno é o oitavo e último planeta; Plutão é classificado como planeta anão."),
        ("Em qual galáxia está o Sistema Solar?", ["Via Láctea", "Andrômeda", "Grande Nuvem de Magalhães", "Galáxia do Triângulo"], "A", "O Sistema Solar fica em um dos braços da Via Láctea."),
        ("Quanto tempo, aproximadamente, a luz do Sol leva para chegar à Terra?", ["Cerca de 8 minutos", "Cerca de 1 segundo", "Cerca de 1 dia", "Cerca de 1 ano"], "A", "A cerca de 150 milhões de km, a luz leva aproximadamente 8 minutos e 20 segundos."),
        ("Qual é o maior satélite natural do Sistema Solar?", ["Ganimedes", "Lua", "Titã", "Europa"], "A", "Ganimedes, lua de Júpiter, é o maior satélite natural, maior até que Mercúrio."),
        ("Por que a Lua apresenta fases?", ["Porque vemos partes diferentes da sua face iluminada pelo Sol conforme ela orbita a Terra", "Porque a sombra da Terra a cobre todo mês", "Porque ela muda de tamanho", "Porque ela produz luz própria variável"], "A", "A Lua reflete a luz do Sol; o ângulo entre Sol, Terra e Lua muda a parte iluminada que vemos."),
    ],
    "brasil col": [
        ("Em que ano a frota de Pedro Álvares Cabral chegou ao território que hoje é o Brasil?", ["1500", "1492", "1532", "1822"], "A", "A frota chegou em abril de 1500; 1492 é a chegada de Colombo à América."),
        ("Qual foi o primeiro produto explorado economicamente pelos portugueses no Brasil?", ["Pau-brasil", "Café", "Ouro", "Borracha"], "A", "O pau-brasil, usado como corante, foi explorado desde as primeiras décadas."),
        ("O que foram as capitanias hereditárias?", ["Grandes faixas de terra entregues a donatários para colonizar", "Cidades fundadas pelos indígenas", "Impostos sobre o ouro", "Missões jesuíticas"], "A", "A partir de 1534, a Coroa dividiu o território em faixas doadas a donatários."),
        ("Qual foi a primeira capital do Brasil colonial?", ["Salvador", "Rio de Janeiro", "São Paulo", "Recife"], "A", "Salvador foi fundada em 1549 como sede do Governo-Geral; a capital só passou ao Rio em 1763."),
        ("Qual cultura foi a base da economia do Nordeste colonial nos séculos XVI e XVII?", ["Cana-de-açúcar", "Café", "Algodão", "Cacau"], "A", "O açúcar produzido nos engenhos era o principal produto de exportação."),
        ("Como se chamava a unidade de produção de açúcar, com moenda e casa de purgar?", ["Engenho", "Quilombo", "Bandeira", "Missão"], "A", "O engenho reunia a plantação, a moenda e as instalações de fabrico do açúcar."),
        ("Qual foi a principal mão de obra na produção açucareira colonial?", ["Pessoas africanas escravizadas", "Imigrantes europeus assalariados", "Trabalhadores japoneses", "Operários de fábricas"], "A", "A economia açucareira dependeu do trabalho de africanos escravizados trazidos pelo tráfico."),
        ("O que eram os quilombos?", ["Comunidades formadas por pessoas que resistiam à escravidão", "Fazendas de gado", "Fortes portugueses", "Escolas jesuíticas"], "A", "Os quilombos reuniam principalmente pessoas que fugiam da escravidão."),
        ("Qual foi o quilombo mais conhecido do período colonial?", ["Palmares", "Canudos", "Contestado", "Caldeirão"], "A", "Palmares, na Serra da Barriga, resistiu por quase um século; Canudos e Contestado são do período republicano."),
        ("No século XVIII, a descoberta de ouro deslocou o centro econômico da colônia para qual região?", ["Minas Gerais", "Amazônia", "Rio Grande do Sul", "Pernambuco"], "A", "A mineração concentrou população e riqueza nas Minas Gerais."),
        ("O que foram as bandeiras?", ["Expedições ao interior em busca de riquezas e de indígenas para escravizar", "Revoltas a favor da independência", "Navios de guerra holandeses", "Festas religiosas"], "A", "Partindo principalmente de São Paulo, as bandeiras exploraram o interior e ampliaram o território."),
        ("Qual ordem religiosa teve papel central na catequese dos indígenas no início da colonização?", ["Companhia de Jesus (jesuítas)", "Ordem dos Templários", "Ordem de Malta", "Ordem Teutônica"], "A", "Os jesuítas chegaram em 1549 e fundaram colégios e aldeamentos."),
        ("Qual país europeu ocupou parte do Nordeste no século XVII, com destaque para Pernambuco?", ["Holanda (Províncias Unidas)", "França", "Inglaterra", "Espanha"], "A", "Os holandeses dominaram Pernambuco e áreas vizinhas entre 1630 e 1654."),
        ("Quem governou o Brasil holandês e incentivou as artes e as ciências em Recife?", ["Maurício de Nassau", "Tomé de Sousa", "Tiradentes", "Duarte Coelho"], "A", "João Maurício de Nassau governou de 1637 a 1644 e modernizou Recife."),
        ("O que foi a Inconfidência Mineira (1789)?", ["Uma conspiração contra o domínio português em Minas Gerais", "Uma revolta de escravizados em Salvador", "Um tratado de paz com a Holanda", "A fundação de São Paulo"], "A", "Os inconfidentes, insatisfeitos com os impostos, planejavam romper com Portugal."),
        ("Qual inconfidente foi executado em 1792 e se tornou símbolo da conspiração?", ["Tiradentes", "Zumbi", "Padre Antônio Vieira", "Dom João VI"], "A", "Joaquim José da Silva Xavier, o Tiradentes, foi enforcado no Rio de Janeiro em 1792."),
        ("O que era o \"quinto\" no período da mineração?", ["Um imposto que destinava 20% do ouro extraído à Coroa", "Um tipo de engenho", "Uma capitania", "Uma moeda indígena"], "A", "O quinto correspondia a um quinto, ou 20%, do ouro."),
        ("Com que objetivo principal foi criado o Governo-Geral em 1548-1549?", ["Centralizar a administração da colônia", "Declarar a independência", "Abolir a escravidão", "Dividir a colônia com a Espanha"], "A", "Diante das dificuldades das capitanias, a Coroa criou um governo central, com Tomé de Sousa."),
        ("Qual tratado de 1494 dividiu entre Portugal e Espanha as terras descobertas e a descobrir?", ["Tratado de Tordesilhas", "Tratado de Madri", "Tratado de Versalhes", "Tratado de Methuen"], "A", "Tordesilhas traçou uma linha imaginária a 370 léguas a oeste de Cabo Verde."),
        ("Qual acontecimento de 1808 mudou profundamente a situação da colônia?", ["A chegada da família real portuguesa ao Brasil", "A abolição da escravidão", "A proclamação da República", "A descoberta do ouro"], "A", "Fugindo das tropas de Napoleão, a corte se instalou no Rio e abriu os portos às nações amigas."),
    ],
}

# Nomes de tema (sem acentos e em minúsculas) que usam cada banco local. A comparação é exata,
# para um tema parecido (ex.: "Função do primeiro grau") não receber questões de outro assunto.
TEMAS_DO_BANCO_LOCAL = {
    "corpo humano": "corpo humano",
    "equacao do primeiro grau": "do 1º grau",
    "equacoes do primeiro grau": "do 1º grau",
    "equacao do 1o grau": "do 1º grau",
    "equacoes do 1o grau": "do 1º grau",
    "figuras de linguagem": "figuras de linguagem",
    "sistema solar": "sistema solar",
    "brasil colonia": "brasil col",
}


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra)).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", texto)).strip()


def _banco_do_tema(tema):
    chave = TEMAS_DO_BANCO_LOCAL.get(_normalizar(tema))
    return BANCO_TEMATICO[chave] if chave else None


def _gerar_local(tema, quantidade, excluir_enunciados=None):
    base = _banco_do_tema(tema)
    if not base or len(base) < quantidade:
        raise RuntimeError(MENSAGEM_INDISPONIVEL)
    excluir = {str(texto).strip().casefold() for texto in (excluir_enunciados or []) if texto}
    novas = [questao for questao in base if questao[0].strip().casefold() not in excluir]
    antigas = [questao for questao in base if questao[0].strip().casefold() in excluir]
    random.shuffle(novas)
    random.shuffle(antigas)
    saida = []
    for enunciado, opcoes, correta, explicacao in (novas + antigas)[:quantidade]:
        opcoes = list(opcoes)
        resposta_correta = opcoes[LETRAS.index(correta)]
        random.shuffle(opcoes)
        saida.append({
            "enunciado": enunciado,
            "alternativas": dict(zip(LETRAS, opcoes)),
            "alternativa_correta": LETRAS[opcoes.index(resposta_correta)],
            "explicacao": explicacao,
        })
    return saida


def _erro_para_o_aluno(motivos, espera):
    """Escolhe a mensagem e o status conforme o motivo das falhas da IA."""
    if "cota" in motivos:
        return ErroDeGeracao(MENSAGEM_COTA, 503, espera=espera or 60)
    if "chave" in motivos:
        registro.error("A chave da IA foi recusada pelo provedor. Confira GEMINI_API_KEY / OPENAI_API_KEY.")
        return ErroDeGeracao(MENSAGEM_CHAVE, 503)
    if motivos and all(motivo == "resposta" for motivo in motivos):
        return ErroDeGeracao(MENSAGEM_RESPOSTA, 502)
    return ErroDeGeracao(MENSAGEM_INDISPONIVEL, 502)


def gerar_questoes(materia, tema, dificuldade, quantidade, excluir_enunciados=None, subtema=None):
    """Questões do tema (e do subtema, se houver): Gemini, depois OpenAI, depois o banco local."""
    prazo = time.monotonic() + PRAZO_TOTAL_IA
    motivos, espera = [], None
    for gerador in (_gerar_com_gemini, _gerar_com_openai):
        try:
            geradas = gerador(materia, tema, dificuldade, quantidade, excluir_enunciados, subtema=subtema, prazo=prazo)
            if geradas:
                return geradas, "ia"
        except RuntimeError as erro:
            registro.warning("%s", erro)
            motivos.append(getattr(erro, "motivo", "indisponivel"))
            espera = getattr(erro, "espera", None) or espera
    # O banco local só serve quando o nome escolhido é exatamente um dos temas que ele cobre.
    try:
        return _gerar_local(subtema or tema, quantidade, excluir_enunciados), "banco_local"
    except RuntimeError:
        raise _erro_para_o_aluno(motivos, espera) from None
