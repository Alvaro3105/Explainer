"""Catálogo de estudo: matérias, temas e subtemas.

O conteúdo fica em arquivos de texto em backend/database/catalogo/, um por matéria:

    @ Matemática | Matemática e suas Tecnologias | matematica; mat
    Matemática Financeira | juros; capital; montante
    - Juros Simples | juro simples
    - Juros Compostos

`@` abre a matéria (nome | área | sinônimos), a linha sem marcação é um tema
(nome | sinônimos) e a linha que começa com `-` é um subtema do tema de cima.
"""
import re
import unicodedata
from pathlib import Path

from models.model_materia import Materia
from models.model_tema import Tema
from repositories.materia_repository import MateriaRepository
from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao
from services.aprendizado.erros import ErroDeNegocio

PASTA_CATALOGO = Path(__file__).resolve().parents[2] / "database" / "catalogo"
LIMITE_PADRAO = 8
LIMITE_MAXIMO = 50
PAGINA_MAXIMA = 1000
# Nomes antigos de matéria que passaram a ter outro nome no catálogo.
APELIDOS_DE_MATERIA = {"portugues": "lingua portuguesa"}


def normalizar(texto):
    """Minúsculas, sem acentos e só com letras, números e espaços simples."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra)).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", texto)).strip()


def _termos(sinonimos, *extras):
    """Junta os sinônimos normalizados no formato |termo|termo|, usado na busca."""
    termos = [normalizar(t) for t in list(sinonimos) + [e for e in extras if e]]
    termos = [t for t in dict.fromkeys(termos) if t]
    return "|" + "|".join(termos) + "|" if termos else None


def _separar(linha):
    partes = [parte.strip() for parte in linha.split("|")]
    return partes[0], partes[1:]


def _lista(texto):
    return [item.strip() for item in (texto or "").split(";") if item.strip()]


def ler_catalogo(pasta=PASTA_CATALOGO):
    """Lê os arquivos do catálogo e devolve a lista de matérias com seus temas e subtemas."""
    materias = []
    for arquivo in sorted(Path(pasta).glob("*.txt")):
        materia = None
        for numero, bruta in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            linha = bruta.strip()
            if not linha or linha.startswith("#"):
                continue
            local = f"{arquivo.name}:{numero}"
            if linha.startswith("@"):
                nome, resto = _separar(linha[1:])
                materia = {"nome": nome, "area": resto[0] if resto else None,
                           "sinonimos": _lista(resto[1]) if len(resto) > 1 else [], "temas": [], "origem": local}
                materias.append(materia)
                continue
            if materia is None:
                raise ValueError(f"{local}: o arquivo precisa começar com a linha da matéria (@ Nome).")
            if linha.startswith("-"):
                if not materia["temas"]:
                    raise ValueError(f"{local}: subtema sem tema acima dele.")
                nome, resto = _separar(linha[1:])
                materia["temas"][-1]["subtemas"].append({"nome": nome, "sinonimos": _lista(resto[0] if resto else ""), "origem": local})
            else:
                nome, resto = _separar(linha)
                materia["temas"].append({"nome": nome, "sinonimos": _lista(resto[0] if resto else ""), "subtemas": [], "origem": local})
    return materias


class CatalogoService:

    # ---------- importação ----------

    def importar(self, pasta=PASTA_CATALOGO):
        """Grava o catálogo no banco sem duplicar nada e sem apagar histórico.

        Pode rodar quantas vezes quiser: o que já existe é atualizado, o que falta é criado.
        Temas antigos (criados antes do catálogo) são ligados à matéria certa pelo nome.
        Matérias que saíram dos arquivos saem também da busca (veja _retirar_materias_fora_do_catalogo).
        """
        catalogo = ler_catalogo(pasta)
        materias = {m.nome_busca: m for m in MateriaRepository.listar()}
        todos = TemaRepository.listar()
        por_chave = {(t.id_materia, t.nome_busca): t for t in todos if t.id_materia and t.nome_busca}
        soltos = [t for t in todos if not t.id_materia]
        gravados = set()
        resumo = {"materias_novas": 0, "temas_novos": 0, "temas_antigos_ligados": 0,
                  "materias_removidas": 0, "temas_removidos": 0, "temas_fora_da_busca": 0, "ignorados": []}

        nomes_do_catalogo = {normalizar(dados["nome"]) for dados in catalogo}

        def materia_antiga(tema):
            chave = normalizar(tema.materia)
            return APELIDOS_DE_MATERIA.get(chave, chave)

        def ligar_solto(nome_busca, sinonimos_busca, materia):
            """Tema criado antes do catálogo, com o mesmo nome ou com um dos sinônimos.

            Se a matéria antiga também existe no catálogo, o tema só pode ir para ela.
            """
            for tema in soltos:
                antiga = materia_antiga(tema)
                if antiga in nomes_do_catalogo and antiga != materia.nome_busca:
                    continue
                if normalizar(tema.nome) in {nome_busca} | sinonimos_busca:
                    soltos.remove(tema)
                    return tema
            return None

        def gravar(item, materia, pai=None):
            nome_busca = normalizar(item["nome"])
            if not nome_busca or len(item["nome"]) > 100:
                resumo["ignorados"].append(f"{item['origem']}: nome vazio ou com mais de 100 letras")
                return None
            tema = por_chave.get((materia.id_materia, nome_busca))
            if tema is not None and id(tema) in gravados:
                resumo["ignorados"].append(f"{item['origem']}: '{item['nome']}' já aparece nesta matéria")
                return None
            if tema is None:
                tema = ligar_solto(nome_busca, {normalizar(s) for s in item["sinonimos"]}, materia)
                if tema is None:
                    tema = Tema(materia=materia.nome, nome=item["nome"])
                    TemaRepository.adicionar(tema)
                    resumo["temas_novos"] += 1
                else:
                    resumo["temas_antigos_ligados"] += 1
            novos = {"materia": materia.nome, "nome": item["nome"], "id_materia": materia.id_materia,
                     "id_tema_pai": pai.id_tema if pai else None, "nome_busca": nome_busca,
                     "sinonimos": "; ".join(item["sinonimos"]) or None,
                     "termos_busca": _termos(item["sinonimos"], pai.nome if pai else None)}
            for campo, valor in novos.items():
                if getattr(tema, campo) != valor:
                    setattr(tema, campo, valor)
            gravados.add(id(tema))
            por_chave[(materia.id_materia, nome_busca)] = tema
            return tema

        for dados in catalogo:
            chave = normalizar(dados["nome"])
            materia = materias.get(chave)
            if materia is None:
                materia = Materia(nome=dados["nome"], nome_busca=chave)
                MateriaRepository.adicionar(materia)
                materias[chave] = materia
                resumo["materias_novas"] += 1
            materia.area = dados["area"]
            materia.sinonimos = "; ".join(dados["sinonimos"]) or None
            materia.termos_busca = _termos(dados["sinonimos"])
        Transacao.enviar()  # gera os ids das matérias novas

        principais = []
        for dados in catalogo:
            materia = materias[normalizar(dados["nome"])]
            for item in dados["temas"]:
                principais.append((item, materia, gravar(item, materia)))
        Transacao.enviar()  # gera os ids dos temas, usados pelos subtemas

        for item, materia, tema in principais:
            if tema is None:
                continue
            for sub in item["subtemas"]:
                gravar(sub, materia, pai=tema)

        # Temas antigos que não estão no catálogo: ficam na matéria do nome antigo, se ela
        # for do catálogo. Os de outras matérias ficam fora da busca, mas não são apagados.
        for tema in soltos:
            chave = materia_antiga(tema)
            if chave not in nomes_do_catalogo:
                continue
            materia = materias[chave]
            nome_busca = normalizar(tema.nome)
            if (materia.id_materia, nome_busca) in por_chave:
                continue  # já existe um tema igual nesta matéria: o antigo fica como estava
            tema.id_materia = materia.id_materia
            tema.materia = materia.nome
            tema.nome_busca = nome_busca
            por_chave[(materia.id_materia, nome_busca)] = tema
        Transacao.enviar()
        self._retirar_materias_fora_do_catalogo(nomes_do_catalogo, resumo)
        Transacao.confirmar()
        return resumo

    @staticmethod
    def _retirar_materias_fora_do_catalogo(nomes_do_catalogo, resumo):
        """Tira do banco as matérias que não estão mais nos arquivos do catálogo.

        Tema ou subtema sem questões e sem desafios é apagado. O que tem histórico
        de aluno não é apagado: só deixa de ter matéria, e com isso some da busca.
        """
        for materia in MateriaRepository.listar():
            if materia.nome_busca in nomes_do_catalogo:
                continue
            temas = TemaRepository.listar_da_materia(materia.id_materia)
            # Subtemas primeiro, para o tema principal ficar sem filhos antes de ser apagado.
            for tema in sorted(temas, key=lambda t: t.id_tema_pai is None):
                if TemaRepository.possui_vinculos(tema.id_tema):
                    tema.id_materia = None
                    tema.id_tema_pai = None
                    resumo["temas_fora_da_busca"] += 1
                else:
                    TemaRepository.remover(tema)
                    resumo["temas_removidos"] += 1
                Transacao.enviar()
            MateriaRepository.remover(materia)
            resumo["materias_removidas"] += 1
        Transacao.enviar()

    @staticmethod
    def ligar_ao_catalogo(tema):
        """Liga um tema criado pelo painel à matéria certa, para ele aparecer na busca."""
        chave = normalizar(tema.materia)
        chave = APELIDOS_DE_MATERIA.get(chave, chave)
        if not chave or not normalizar(tema.nome):
            raise ValueError("Matéria e nome do tema precisam ter letras ou números.")
        materia = MateriaRepository.buscar_por_nome_busca(chave)
        if materia is None:
            nomes = ", ".join(sorted(m.nome for m in MateriaRepository.listar()))
            raise ValueError(f"Matéria fora do catálogo. Use uma destas: {nomes}.")
        nome_busca = normalizar(tema.nome)
        repetido = TemaRepository.buscar_por_nome(materia.id_materia, nome_busca)
        if repetido is not None and repetido is not tema:
            raise ValueError("Já existe um tema com esse nome nesta matéria.")
        tema.id_materia = materia.id_materia
        tema.materia = materia.nome
        tema.nome_busca = nome_busca

    # ---------- busca ----------

    @staticmethod
    def _limites(limite, pagina):
        try:
            limite = max(1, min(int(limite or LIMITE_PADRAO), LIMITE_MAXIMO))
            pagina = max(1, min(int(pagina or 1), PAGINA_MAXIMA))
        except (TypeError, ValueError, OverflowError):
            raise ErroDeNegocio("Limite e página precisam ser números.")
        return limite, pagina

    @staticmethod
    def _busca(texto):
        frase = normalizar(texto)[:80]
        return frase.split(), frase

    def materias(self, texto="", limite=None, pagina=1):
        limite, pagina = self._limites(limite or LIMITE_MAXIMO, pagina)
        palavras, frase = self._busca(texto)
        encontradas = MateriaRepository.pesquisar(palavras, frase, limite + 1, (pagina - 1) * limite)
        if frase and not encontradas and pagina == 1:
            # Nada no começo das palavras: tenta o trecho no meio delas ("tica" acha "Matemática").
            encontradas = MateriaRepository.pesquisar(palavras, frase, limite + 1, no_meio=True)
        quantidades = MateriaRepository.contar_temas_por_materia()
        itens = [{**m.to_dict(), "quantidade_temas": quantidades.get(m.id_materia, 0)} for m in encontradas[:limite]]
        return {"materias": itens, "pagina": pagina, "tem_mais": len(encontradas) > limite}

    def temas(self, id_materia, texto="", limite=None, pagina=1, id_tema_pai=None):
        materia = MateriaRepository.buscar_por_id(id_materia)
        if not materia:
            raise ErroDeNegocio("Matéria não encontrada.", 404)
        limite, pagina = self._limites(limite, pagina)
        palavras, frase = self._busca(texto)
        encontrados = TemaRepository.pesquisar(materia.id_materia, palavras, frase, limite + 1,
                                               (pagina - 1) * limite, id_tema_pai=id_tema_pai)
        if frase and not encontrados and pagina == 1:
            # Nada no começo das palavras: tenta o trecho no meio delas.
            encontrados = TemaRepository.pesquisar(materia.id_materia, palavras, frase, limite + 1,
                                                   id_tema_pai=id_tema_pai, no_meio=True)
        pagina_atual = encontrados[:limite]
        pais = TemaRepository.buscar_varios(t.id_tema_pai for t in pagina_atual)
        subtemas = TemaRepository.contar_subtemas(t.id_tema for t in pagina_atual if not t.id_tema_pai)
        itens = []
        for tema in pagina_atual:
            pai = pais.get(tema.id_tema_pai)
            relacionado = None
            if frase and frase not in (tema.nome_busca or ""):
                relacionado = next((s for s in (tema.sinonimos or "").split("; ")
                                    if s and all(p in normalizar(s) for p in palavras)), None)
            itens.append({
                "id_tema": tema.id_tema,
                "nome": tema.nome,
                "tipo": "subtema" if tema.id_tema_pai else "tema",
                "tema_pai": {"id_tema": pai.id_tema, "nome": pai.nome} if pai else None,
                "id_materia": materia.id_materia,
                "materia": materia.nome,
                "quantidade_subtemas": subtemas.get(tema.id_tema, 0),
                "termo_relacionado": relacionado,
            })
        return {"materia": materia.to_dict(), "temas": itens, "pagina": pagina,
                "tem_mais": len(encontrados) > limite}

    def subtemas(self, id_tema, texto="", limite=None, pagina=1):
        tema = TemaRepository.buscar_por_id(id_tema)
        if not tema or not tema.id_materia:
            raise ErroDeNegocio("Tema não encontrado.", 404)
        if tema.id_tema_pai:
            raise ErroDeNegocio("Escolha um tema principal para ver os subtemas.")
        resultado = self.temas(tema.id_materia, texto, limite, pagina, id_tema_pai=tema.id_tema)
        resultado["tema"] = {"id_tema": tema.id_tema, "nome": tema.nome}
        return resultado

    @staticmethod
    def resumo():
        temas, subtemas = TemaRepository.contar_por_tipo()
        return {"materias": len(MateriaRepository.listar()), "temas": temas, "subtemas": subtemas}
