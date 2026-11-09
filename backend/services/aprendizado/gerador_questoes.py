import json
import os
import random
import urllib.error
import urllib.request

LETRAS = ("A", "B", "C", "D")

# "Normal" é o valor interno (banco e API); na interface e no prompt usamos "Médio",
# para que a sequência Fácil → Médio → Difícil fique clara.
ROTULOS_DIFICULDADE = {"Normal": "Médio"}


def rotulo_dificuldade(dificuldade):
    return ROTULOS_DIFICULDADE.get(dificuldade, dificuldade)


# Banco demonstrativo usado quando OPENAI_API_KEY não está configurada.
# As questões são agrupadas por área; para uso escolar real, configure a API de IA.
BANCO_LOCAL = {
    "Matemática": [
        ("Quanto é 25% de 200?", ["25", "40", "50", "75"], "C", "25% corresponde a um quarto; 200 ÷ 4 = 50."),
        ("Qual fração é equivalente a 1/2?", ["2/3", "3/4", "4/5", "2/4"], "D", "Multiplicando numerador e denominador de 1/2 por 2, obtemos 2/4."),
        ("Resolva: 3x + 5 = 20.", ["3", "5", "7", "15"], "B", "Subtraindo 5, 3x = 15; dividindo por 3, x = 5."),
        ("Qual é a área de um retângulo de lados 8 cm e 4 cm?", ["12 cm²", "24 cm²", "32 cm²", "64 cm²"], "C", "A área é base × altura: 8 × 4 = 32 cm²."),
        ("Qual é a média aritmética de 6, 8 e 10?", ["8", "9", "10", "24"], "A", "A média é (6 + 8 + 10) ÷ 3 = 8."),
        ("Qual é o resultado de 2³?", ["5", "6", "8", "9"], "C", "2³ significa 2 × 2 × 2, que resulta em 8."),
        ("Um produto de R$ 80 teve desconto de 10%. Qual é o preço final?", ["R$ 8", "R$ 70", "R$ 72", "R$ 78"], "C", "10% de 80 é 8; 80 − 8 = 72."),
        ("Qual é o perímetro de um quadrado de lado 6 cm?", ["12 cm", "18 cm", "24 cm", "36 cm"], "C", "O perímetro é 4 × 6 = 24 cm."),
        ("Qual número é primo?", ["21", "27", "29", "33"], "C", "29 só é divisível por 1 e por ele mesmo."),
        ("Qual é o valor de 7 × 8?", ["48", "54", "56", "64"], "C", "Sete vezes oito é 56."),
        ("Quanto é 3/4 em porcentagem?", ["25%", "50%", "75%", "80%"], "C", "3 ÷ 4 = 0,75, equivalente a 75%."),
        ("Qual é a raiz quadrada de 81?", ["7", "8", "9", "10"], "C", "9 × 9 = 81."),
        ("Se y = 2x e x = 7, quanto vale y?", ["9", "12", "14", "21"], "C", "Substituindo x por 7: y = 2 × 7 = 14."),
        ("Qual é a forma decimal de 3/10?", ["0,03", "0,3", "3,0", "30"], "B", "Três décimos são escritos como 0,3."),
        ("Um triângulo tem ângulos de 60° e 50°. Qual é o terceiro ângulo?", ["60°", "70°", "80°", "90°"], "B", "A soma dos ângulos internos de um triângulo é 180°; 180 − 110 = 70°."),
        ("Qual expressão representa o dobro de um número n acrescido de 4?", ["2(n + 4)", "n² + 4", "2n + 4", "n + 8"], "C", "O dobro é 2n; acrescentando 4, temos 2n + 4."),
        ("Qual é o MMC de 4 e 6?", ["2", "6", "12", "24"], "C", "O menor múltiplo positivo comum a 4 e 6 é 12."),
        ("Em um mapa na escala 1:100, 3 cm representam quantos centímetros reais?", ["30 cm", "100 cm", "300 cm", "3.000 cm"], "C", "Cada centímetro no mapa representa 100 cm reais; 3 × 100 = 300 cm."),
        ("Qual é a probabilidade de sair cara em uma moeda justa?", ["0%", "25%", "50%", "100%"], "C", "Há dois resultados equiprováveis: cara e coroa; a chance é 1/2."),
        ("Qual é o próximo número da sequência 2, 5, 8, 11...?", ["12", "13", "14", "15"], "C", "A sequência aumenta de 3 em 3; 11 + 3 = 14."),
    ],
    "Programação": [
        ("Qual é a função principal de uma variável?", ["Armazenar um valor", "Desligar o programa", "Criar uma rede", "Formatar o disco"], "A", "Uma variável associa um nome a um valor que pode ser usado no programa."),
        ("Qual estrutura costuma repetir um bloco de código?", ["if", "for", "return", "import"], "B", "Laços como for repetem instruções para uma sequência ou quantidade de vezes."),
        ("Em lógica booleana, o que representa o valor true?", ["Falso", "Nulo", "Verdadeiro", "Texto"], "C", "true representa uma condição verdadeira."),
        ("Qual estrutura permite executar código apenas se uma condição for verdadeira?", ["if", "while", "print", "class"], "A", "A estrutura if avalia uma condição antes de executar seu bloco."),
        ("O que é um algoritmo?", ["Uma sequência finita de passos", "Um tipo de monitor", "Uma linguagem de marcação", "Uma peça de hardware"], "A", "Um algoritmo descreve passos organizados para resolver um problema."),
        ("Para que serve uma função?", ["Agrupar instruções reutilizáveis", "Somente desenhar telas", "Aumentar a memória física", "Substituir o sistema operacional"], "A", "Funções encapsulam comportamentos que podem ser chamados quando necessário."),
        ("Qual tipo de dado costuma representar números inteiros?", ["Boolean", "String", "Integer", "Char"], "C", "Integer representa números inteiros em muitas linguagens."),
        ("O que significa depurar um programa?", ["Localizar e corrigir erros", "Apagar todo o código", "Instalar uma impressora", "Criar um usuário"], "A", "Depuração é o processo de encontrar e corrigir defeitos no código."),
        ("Qual linguagem é usada principalmente para estruturar o conteúdo de páginas web?", ["HTML", "SQL", "C", "Bash"], "A", "HTML define a estrutura semântica do conteúdo de uma página web."),
        ("Qual linguagem é usada para estilizar páginas web?", ["CSS", "SQL", "Python", "C#"], "A", "CSS controla apresentação, layout e aparência visual das páginas."),
        ("Em JavaScript, qual operador testa igualdade estrita?", ["=", "==", "===", "!="], "C", "=== compara valor e tipo sem conversão implícita."),
        ("Para que serve SQL?", ["Consultar e manipular dados relacionais", "Editar imagens vetoriais", "Compilar o kernel", "Criar cabos de rede"], "A", "SQL é usada para consultar e manipular dados em bancos relacionais."),
        ("O que é um loop infinito?", ["Um ciclo que não termina", "Um comentário", "Uma função matemática", "Um banco de dados"], "A", "É uma repetição cuja condição de saída nunca é atingida."),
        ("O que significa API?", ["Interface de Programação de Aplicações", "Arquivo Pessoal Interno", "Aplicativo de Processamento de Imagem", "Ambiente de Projeto Integrado"], "A", "API define meios para sistemas e componentes se comunicarem."),
        ("Qual estrutura costuma representar pares chave-valor?", ["Dicionário", "Fila de impressão", "Pilha física", "Comentário"], "A", "Dicionários ou mapas associam chaves a valores."),
        ("Qual é a finalidade de um teste automatizado?", ["Verificar comportamento com execução repetível", "Substituir documentação sempre", "Aumentar o tamanho do código", "Desativar os logs"], "A", "Testes automatizados validam comportamentos de forma repetível."),
        ("O que é um banco de dados?", ["Uma coleção organizada de dados", "Um compilador", "Um tipo de variável apenas", "Um cabo"], "A", "Banco de dados armazena dados de modo estruturado para consulta e gestão."),
        ("Qual é o resultado lógico de true AND false?", ["true", "false", "null", "Erro sempre"], "B", "AND só é verdadeiro quando ambos os operandos são verdadeiros."),
        ("O que um controle de versão como Git acompanha?", ["Alterações nos arquivos do projeto", "Temperatura do processador", "Consumo elétrico da tela", "Apenas imagens"], "A", "Git registra o histórico de mudanças em arquivos de um projeto."),
        ("Qual é o objetivo de um comentário no código?", ["Explicar trechos para leitores", "Executar a próxima função", "Criar tabela automaticamente", "Compactar arquivos"], "A", "Comentários documentam intenção e ajudam na manutenção do código."),
    ],
    "Português": [
        ("Qual opção apresenta um substantivo?", ["Rapidamente", "Beleza", "Correr", "Azulmente"], "B", "Beleza nomeia uma qualidade ou conceito, funcionando como substantivo."),
        ("Em 'A menina estudou bastante', qual é o verbo?", ["A", "menina", "estudou", "bastante"], "C", "Estudou indica uma ação realizada no passado."),
        ("Qual frase está pontuada corretamente?", ["Vamos comer, pessoal!", "Vamos, comer pessoal!", "Vamos comer pessoal?", "Vamos comer; pessoal"], "A", "A vírgula separa o vocativo 'pessoal' do restante da frase."),
        ("Qual palavra é sinônimo de 'conciso'?", ["Extenso", "Objetivo", "Confuso", "Repetitivo"], "B", "Conciso é aquilo que comunica com poucas palavras e precisão."),
        ("Qual palavra é antônimo de 'escasso'?", ["Raro", "Pouco", "Abundante", "Limitado"], "C", "Abundante indica grande quantidade, o oposto de escasso."),
        ("Qual alternativa contém um adjetivo?", ["Casa", "Cantar", "Gentil", "Ontem"], "C", "Gentil caracteriza um substantivo, por isso é adjetivo."),
        ("Na comunicação, qual é a função principal de uma conclusão?", ["Introduzir assunto novo sem relação", "Encerrar e sintetizar as ideias", "Apagar a tese", "Substituir todo o desenvolvimento"], "B", "A conclusão fecha a argumentação e retoma os pontos centrais."),
        ("Qual forma está corretamente acentuada?", ["Voce", "Público", "Ideiá", "Heroì"], "B", "Público é proparoxítona e recebe acento gráfico."),
        ("Em 'Embora estivesse cansado, continuou', 'embora' expressa ideia de:", ["Causa", "Concessão", "Finalidade", "Comparação"], "B", "Embora introduz uma concessão: algo ocorre apesar de um obstáculo."),
        ("Qual opção é um pronome pessoal?", ["Eles", "Mesa", "Cantar", "Verde"], "A", "Eles é pronome pessoal do caso reto."),
        ("Qual é o plural correto de 'cidadão'?", ["Cidadões", "Cidadães", "Cidadãos", "Cidadãoses"], "C", "O plural mais comum e normativo de cidadão é cidadãos."),
        ("O que é uma metáfora?", ["Comparação explícita sempre com 'como'", "Uso figurado por aproximação de sentidos", "Repetição de sons iniciais", "Omissão obrigatória de verbo"], "B", "A metáfora transfere sentido por uma relação de semelhança implícita."),
        ("Em 'O livro que comprei é ótimo', 'que' retoma:", ["ótimo", "comprei", "livro", "é"], "C", "O pronome relativo que retoma o antecedente 'livro'."),
        ("Qual opção está escrita corretamente?", ["Excessão", "Exceção", "Ecessão", "Exceçâo"], "B", "A grafia correta é exceção."),
        ("Qual elemento apresenta o ponto de vista defendido em um texto argumentativo?", ["Tese", "Legenda", "Índice", "Epígrafe apenas"], "A", "A tese é a ideia central que o texto procura defender."),
        ("Qual alternativa contém uma conjunção adversativa?", ["Portanto", "Mas", "Porque", "Quando"], "B", "Mas expressa contraste ou oposição entre ideias."),
        ("Qual palavra é oxítona?", ["Lâmpada", "Mesa", "Café", "Árvore"], "C", "Café tem a última sílaba tônica."),
        ("O que caracteriza a linguagem denotativa?", ["Sentido literal", "Sentido exclusivamente irônico", "Sentido sempre poético", "Uso obrigatório de rima"], "A", "A denotação utiliza o significado literal da palavra."),
        ("Qual gênero costuma defender publicamente uma causa ou reivindicação coletiva?", ["Carta aberta", "Receita culinária", "Bula", "Verbete técnico apenas"], "A", "A carta aberta é dirigida ao público para expor uma posição ou demanda."),
        ("Qual alternativa apresenta concordância adequada?", ["Fazem dois anos", "Houveram problemas", "Faz dois anos", "Existe muitas opções"], "C", "O verbo fazer indicando tempo decorrido é impessoal e fica no singular."),
    ],
    "Ciências": [
        ("Qual organela celular está associada à produção de energia por respiração celular?", ["Ribossomo", "Mitocôndria", "Lisossomo", "Complexo de Golgi"], "B", "A mitocôndria participa da respiração celular e da produção de ATP."),
        ("Qual gás as plantas absorvem principalmente na fotossíntese?", ["Oxigênio", "Nitrogênio", "Dióxido de carbono", "Hélio"], "C", "As plantas utilizam dióxido de carbono e água para produzir matéria orgânica."),
        ("Qual é a unidade básica da vida?", ["Átomo", "Célula", "Tecido", "Órgão"], "B", "A célula é a menor unidade estrutural e funcional dos seres vivos."),
        ("Qual planeta é conhecido como planeta vermelho?", ["Vênus", "Marte", "Júpiter", "Mercúrio"], "B", "O óxido de ferro presente na superfície dá a Marte a aparência avermelhada."),
        ("Ao nível do mar, a água pura entra em ebulição aproximadamente a:", ["0 °C", "50 °C", "100 °C", "200 °C"], "C", "A água pura ferve perto de 100 °C sob pressão atmosférica de 1 atm."),
        ("Qual órgão bombeia o sangue pelo corpo humano?", ["Pulmão", "Rim", "Coração", "Fígado"], "C", "O coração bombeia o sangue pela circulação pulmonar e sistêmica."),
        ("Qual é a principal fonte de energia para a maioria dos ecossistemas?", ["Lua", "Sol", "Vento lunar", "Núcleo da Terra apenas"], "B", "A energia solar sustenta a fotossíntese e muitas cadeias alimentares."),
        ("Qual mudança de estado transforma líquido em gás?", ["Solidificação", "Condensação", "Vaporização", "Fusão"], "C", "Vaporização é a passagem do estado líquido para o gasoso."),
        ("Qual molécula carrega informação genética na maioria dos seres vivos?", ["DNA", "Amido", "Glicose", "Água"], "A", "O DNA armazena informação genética hereditária."),
        ("Qual destes é um recurso renovável?", ["Carvão mineral", "Petróleo", "Energia solar", "Gás natural"], "C", "A energia solar é renovada continuamente pela radiação do Sol."),
        ("Qual é a função principal das raízes em muitas plantas?", ["Produzir som", "Absorver água e sais minerais", "Fazer a polinização", "Formar sementes diretamente"], "B", "As raízes ajudam na fixação e na absorção de água e sais minerais."),
        ("Qual partícula possui carga elétrica negativa?", ["Próton", "Nêutron", "Elétron", "Fóton sempre"], "C", "O elétron tem carga elétrica negativa."),
        ("Qual sistema do corpo humano realiza as trocas gasosas?", ["Digestório", "Respiratório", "Esquelético", "Endócrino"], "B", "O sistema respiratório permite captar oxigênio e eliminar dióxido de carbono."),
        ("Qual é o pH aproximado de uma solução neutra a 25 °C?", ["0", "3", "7", "14"], "C", "Em condições usuais, soluções neutras têm pH próximo de 7."),
        ("Como se chama a variedade de seres vivos em uma região?", ["Biodiversidade", "Erosão", "Evaporação", "Mimetismo apenas"], "A", "Biodiversidade corresponde à variedade de formas de vida."),
        ("Qual força atrai objetos com massa entre si?", ["Atrito", "Gravidade", "Empuxo apenas", "Tensão elétrica sempre"], "B", "A gravidade é a interação atrativa entre corpos com massa."),
        ("Qual é a fórmula química da água?", ["CO₂", "O₂", "H₂O", "NaCl"], "C", "Uma molécula de água contém dois átomos de hidrogênio e um de oxigênio."),
        ("O que acontece com partículas quando a temperatura de uma substância aumenta, em geral?", ["A energia cinética média diminui", "A energia cinética média aumenta", "A massa desaparece", "Os átomos deixam de existir"], "B", "A temperatura está relacionada à energia cinética média das partículas."),
        ("Qual destes animais é um mamífero?", ["Sapo", "Tubarão", "Golfinho", "Tartaruga"], "C", "Golfinhos são mamíferos: respiram por pulmões e amamentam seus filhotes."),
        ("Qual processo devolve vapor de água à atmosfera a partir de superfícies líquidas?", ["Evaporação", "Congelamento", "Precipitação", "Infiltração"], "A", "Na evaporação, a água líquida passa para o estado gasoso."),
    ],
    "História": [
        ("Qual acontecimento é tradicionalmente usado como marco inicial da Idade Moderna?", ["Queda de Constantinopla em 1453", "Revolução Francesa em 1789", "Fim da Segunda Guerra em 1945", "Independência do Brasil em 1822"], "A", "1453 é um marco convencional, embora a transição histórica tenha sido gradual."),
        ("Em que ano foi proclamada a Independência do Brasil?", ["1500", "1789", "1822", "1889"], "C", "A Independência do Brasil foi proclamada em 7 de setembro de 1822."),
        ("Qual foi uma característica central da Revolução Industrial?", ["Substituição das máquinas por trabalho manual", "Mecanização crescente da produção", "Fim imediato das cidades", "Desaparecimento do comércio"], "B", "A industrialização ampliou o uso de máquinas e transformou a produção e o trabalho."),
        ("Qual sistema econômico predominou na Europa medieval?", ["Feudalismo", "Fordismo", "Toyotismo", "Mercantilismo digital"], "A", "O feudalismo organizou grande parte da sociedade medieval europeia."),
        ("Qual movimento defendia ideias de razão e crítica à autoridade tradicional no século XVIII?", ["Iluminismo", "Romantismo apenas", "Futurismo", "Surrealismo"], "A", "O Iluminismo valorizou razão, debate e crítica a estruturas tradicionais."),
        ("A abolição legal da escravidão no Brasil ocorreu em que ano?", ["1822", "1850", "1888", "1889"], "C", "A Lei Áurea foi assinada em 13 de maio de 1888."),
        ("Qual civilização antiga se desenvolveu ao longo do rio Nilo?", ["Egípcia", "Inca", "Asteca", "Fenícia exclusivamente"], "A", "O rio Nilo foi fundamental à agricultura e à organização do Egito antigo."),
        ("Qual foi o principal objetivo das grandes navegações europeias, entre outros?", ["Buscar rotas comerciais marítimas", "Eliminar toda navegação", "Criar a internet", "Encerrar o comércio de especiarias"], "A", "A busca por rotas para comércio e acesso a produtos foi um importante motor das navegações."),
        ("Qual evento iniciou a Primeira Guerra Mundial em 1914 como estopim imediato?", ["Invasão da Polônia", "Assassinato do arquiduque Francisco Ferdinando", "Queda do Muro de Berlim", "Ataque a Pearl Harbor"], "B", "O assassinato do arquiduque em Sarajevo desencadeou a crise de julho de 1914."),
        ("Qual foi uma consequência política da Revolução Francesa?", ["Fortalecimento dos privilégios feudais sem mudanças", "Questionamento da monarquia absolutista e dos privilégios", "Restauração do Império Romano", "Fim de todos os conflitos europeus"], "B", "A revolução transformou instituições políticas e difundiu ideias de cidadania e igualdade jurídica."),
        ("Qual povo desenvolveu a escrita cuneiforme na Mesopotâmia antiga?", ["Sumérios", "Maias", "Incas", "Vikings"], "A", "A escrita cuneiforme surgiu entre os sumérios na Mesopotâmia."),
        ("O que foi o apartheid na África do Sul?", ["Política de segregação racial", "Acordo de livre navegação medieval", "Sistema de votação universal desde o início", "Reforma agrícola do Império Romano"], "A", "O apartheid institucionalizou a segregação racial e a desigualdade de direitos."),
        ("Qual documento inglês de 1215 limitou certos poderes do rei?", ["Magna Carta", "Tratado de Versalhes", "Carta da ONU", "Código de Hamurábi"], "A", "A Magna Carta impôs limites e obrigações ao rei João da Inglaterra."),
        ("Qual período histórico veio após a Antiguidade na divisão tradicional europeia?", ["Idade Média", "Idade Contemporânea", "Pré-História", "Era Digital"], "A", "Na divisão tradicional, a Idade Média sucede à Antiguidade."),
        ("Qual foi uma característica do colonialismo europeu nas Américas?", ["Exploração de recursos e imposição de estruturas de poder", "Ausência de conflitos", "Igualdade política plena", "Independência imediata de todas as colônias"], "A", "O colonialismo envolveu exploração econômica e relações assimétricas de poder."),
        ("A Proclamação da República no Brasil ocorreu em:", ["1808", "1822", "1888", "1889"], "D", "A República foi proclamada em 15 de novembro de 1889."),
        ("Qual foi uma característica do Renascimento cultural europeu?", ["Valorização de referências clássicas e do humanismo", "Proibição de toda investigação científica", "Adoção da internet", "Fim de toda produção artística"], "A", "O Renascimento valorizou as culturas clássicas, as artes e o ser humano."),
        ("Qual organização foi criada em 1945 para promover cooperação internacional e paz?", ["ONU", "Liga Hanseática", "OTAN em 1910", "Mercosul"], "A", "A Organização das Nações Unidas foi fundada em 1945."),
        ("Qual foi uma consequência da chegada dos portugueses em 1500 para os povos indígenas?", ["Contato sem mudanças", "Transformações profundas, conflitos e perda de territórios", "Fim imediato das línguas indígenas", "Ausência de epidemias"], "B", "A colonização produziu impactos demográficos, territoriais e culturais profundos."),
        ("A Guerra Fria foi marcada principalmente pela rivalidade entre:", ["Estados Unidos e União Soviética", "Brasil e Argentina", "Roma e Cartago", "Portugal e Espanha no século XV"], "A", "A disputa geopolítica e ideológica entre EUA e URSS marcou a Guerra Fria."),
    ],
    "Geografia": [
        ("Qual é a camada mais externa e sólida da Terra?", ["Núcleo interno", "Núcleo externo", "Crosta terrestre", "Manto inferior apenas"], "C", "A crosta é a camada mais externa da estrutura interna terrestre."),
        ("Qual linha imaginária divide a Terra em hemisférios Norte e Sul?", ["Meridiano de Greenwich", "Linha do Equador", "Trópico de Capricórnio", "Círculo Polar Ártico"], "B", "A Linha do Equador divide os hemisférios Norte e Sul."),
        ("Qual é a capital do Brasil?", ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador"], "C", "Brasília é a capital federal do Brasil desde 1960."),
        ("Qual bioma brasileiro é conhecido por sua vegetação adaptada à seca?", ["Caatinga", "Pampa", "Mata de Araucárias", "Pantanal apenas"], "A", "A Caatinga apresenta espécies adaptadas à disponibilidade irregular de água."),
        ("O que mede a densidade demográfica?", ["Habitantes por unidade de área", "Nascimentos por ano apenas", "Área total de rios", "Temperatura média anual"], "A", "Densidade demográfica é a relação entre população e área."),
        ("Qual fenômeno explica o deslocamento de massas de ar e influencia o tempo?", ["Circulação atmosférica", "Tectônica de placas apenas", "Fotossíntese", "Erosão costeira somente"], "A", "A circulação atmosférica transporta calor e umidade e influencia o tempo e o clima."),
        ("Qual região brasileira possui a maior parte da Floresta Amazônica?", ["Norte", "Sul", "Sudeste", "Centro-Sul"], "A", "A Amazônia ocupa grande parte da Região Norte, além de áreas de outras regiões."),
        ("Qual movimento da Terra explica a alternância de dias e noites?", ["Translação", "Rotação", "Precessão apenas", "Deriva continental"], "B", "A rotação da Terra em torno de seu eixo gera a alternância entre dia e noite."),
        ("Qual é a principal causa das estações do ano?", ["Variação da distância Terra-Sol como único fator", "Inclinação do eixo terrestre combinada à translação", "Rotação da Lua", "Mudanças nas marés"], "B", "A inclinação do eixo e a translação alteram a incidência solar ao longo do ano."),
        ("Qual é um exemplo de fonte de energia não renovável?", ["Solar", "Eólica", "Petróleo", "Marés"], "C", "O petróleo é um combustível fóssil formado em escalas de milhões de anos."),
        ("O que é êxodo rural?", ["Migração do campo para a cidade", "Mudança de país para país apenas", "Migração da cidade para o campo", "Deslocamento de animais"], "A", "Êxodo rural é a saída de população das áreas rurais, frequentemente rumo às cidades."),
        ("Qual agente modela o relevo ao transportar sedimentos em rios?", ["Água corrente", "Som", "Campo magnético apenas", "Luz visível"], "A", "Rios erodem, transportam e depositam sedimentos, modificando o relevo."),
        ("Qual oceano banha a costa leste do Brasil?", ["Pacífico", "Índico", "Atlântico", "Ártico"], "C", "A costa brasileira é banhada pelo Oceano Atlântico."),
        ("Qual mapa é especialmente adequado para mostrar fronteiras políticas?", ["Mapa político", "Mapa de precipitação apenas", "Mapa batimétrico", "Mapa de vegetação apenas"], "A", "Mapas políticos representam divisões territoriais e fronteiras administrativas."),
        ("O aquecimento global atual está associado principalmente ao aumento de:", ["Gases de efeito estufa por atividades humanas", "Oxigênio na estratosfera apenas", "Salinidade do oceano apenas", "Rotação terrestre"], "A", "Emissões humanas de gases de efeito estufa intensificam o aquecimento do sistema climático."),
        ("Qual fenômeno é o desgaste e transporte de materiais da superfície terrestre?", ["Erosão", "Condensação", "Fotossíntese", "Magnetização"], "A", "A erosão envolve remoção e transporte de partículas por água, vento, gelo ou gravidade."),
        ("Qual é a principal característica de uma metrópole?", ["Influência econômica e funcional sobre ampla área", "População sempre menor que vila", "Ausência de serviços", "Localização obrigatória no campo"], "A", "Metrópoles concentram funções e influenciam redes urbanas mais amplas."),
        ("Qual região brasileira é a menor em área territorial?", ["Norte", "Nordeste", "Sul", "Centro-Oeste"], "C", "A Região Sul é a menor das cinco grandes regiões do Brasil em área."),
        ("O que representa a latitude?", ["Distância angular em relação ao Equador", "Distância em relação ao meridiano de Greenwich", "Altura de uma montanha apenas", "Profundidade oceânica"], "A", "A latitude é medida ao norte ou ao sul do Equador."),
        ("Qual processo está ligado à formação de montanhas pela interação das placas tectônicas?", ["Orogênese", "Evaporação", "Sedimentação exclusivamente marinha", "Transpiração"], "A", "A orogênese envolve deformações da crosta e formação de cadeias montanhosas."),
    ],
}


def _validar_questoes(questoes, quantidade):
    if not isinstance(questoes, list) or len(questoes) < quantidade:
        raise ValueError("A IA não retornou a quantidade solicitada de questões.")
    normalizadas = []
    for item in questoes[:quantidade]:
        enunciado = str(item.get("enunciado", "")).strip()
        alternativas = item.get("alternativas", {})
        correta = str(item.get("alternativa_correta", "")).upper().strip()
        if isinstance(alternativas, list) and len(alternativas) == 4:
            alternativas = dict(zip(LETRAS, alternativas))
        if not enunciado or not isinstance(alternativas, dict) or any(not str(alternativas.get(letra, "")).strip() for letra in LETRAS):
            raise ValueError("Questão incompleta recebida da IA.")
        if correta not in LETRAS:
            raise ValueError("Alternativa correta inválida recebida da IA.")
        normalizadas.append({
            "enunciado": enunciado,
            "alternativas": {letra: str(alternativas[letra]).strip() for letra in LETRAS},
            "alternativa_correta": correta,
            "explicacao": str(item.get("explicacao", "")).strip() or "Revise o conceito apresentado para compreender a resposta correta.",
        })
    return normalizadas


def _gerar_com_openai(materia, tema, dificuldade, quantidade, excluir_enunciados=None):
    chave = os.getenv("OPENAI_API_KEY", "").strip()
    if not chave:
        return None
    modelo = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    nivel = rotulo_dificuldade(dificuldade)
    prompt = f"""Crie exatamente {quantidade} questões de múltipla escolha em português brasileiro.
Matéria: {materia}. Tema específico: {tema}. Dificuldade: {nivel}.
As questões devem ser educacionalmente corretas, distintas, relevantes ao tema e apropriadas a estudantes.
Cada questão deve ter quatro alternativas plausíveis A, B, C e D, apenas uma correta, e explicação curta.
Não use 'todas as anteriores' nem 'nenhuma das anteriores'. Não repita enunciados, exemplos, números, contexto ou estrutura dentro deste lote.
Varie deliberadamente os subtemas, situações-problema, formatos de raciocínio e exemplos. Não use perguntas genéricas que só mencionem o tema no texto. TODA questão precisa testar diretamente um conceito do tema específico; se o tema for "corpo humano", não pergunte sobre planetas, clima ou fotossíntese. Antes de retornar, confira individualmente que cada enunciado, resposta e explicação pertence à matéria E ao tema. Se não houver conteúdo suficiente para criar questões corretas, gere variações de raciocínio dentro do próprio tema, nunca mude para outro assunto.
A dificuldade precisa mudar o tipo de raciocínio: Fácil = conceitos fundamentais e identificação; Médio = aplicação, interpretação e relações entre conceitos; Difícil = análise, inferência e resolução em várias etapas. Evite reutilizar a mesma pergunta em dificuldades diferentes.
Enunciados já usados que devem ser evitados nesta nova tentativa: {json.dumps((excluir_enunciados or [])[:80], ensure_ascii=False)}.
Não copie nem reformule superficialmente essas perguntas; crie questões novas dentro do mesmo tema.
Retorne exclusivamente JSON neste formato:
{{"questoes":[{{"enunciado":"...","alternativas":{{"A":"...","B":"...","C":"...","D":"..."}},"alternativa_correta":"A","explicacao":"..."}}]}}
"""
    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Você é um elaborador rigoroso de questões educacionais. Priorize precisão factual e siga exatamente o formato JSON solicitado."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
        # ~400 tokens por questão (com margem) evita truncar o JSON em lotes de 15/20 questões.
        "max_completion_tokens": min(16000, 1000 + 450 * int(quantidade)),
    }
    requisicao = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=50) as resposta:
            retorno = json.loads(resposta.read().decode("utf-8"))
        conteudo = retorno["choices"][0]["message"]["content"]
        return _validar_questoes(json.loads(conteudo)["questoes"], quantidade)
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError, ValueError) as erro:
        raise RuntimeError(f"Não foi possível gerar questões pela API de IA: {erro}") from erro


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
    # Os bancos abaixo garantem que todos os temas do catálogo inicial (app.py) tenham
    # questões locais, mesmo sem OPENAI_API_KEY.
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

# Grafias alternativas que as pessoas costumam usar ao cadastrar o tema.
BANCO_TEMATICO["primeiro grau"] = BANCO_TEMATICO["do 1º grau"]
BANCO_TEMATICO["do 1o grau"] = BANCO_TEMATICO["do 1º grau"]


def _gerar_local(materia, tema, quantidade, dificuldade="Normal", excluir_enunciados=None):
    nome = str(materia or "").strip().casefold()
    categorias = {
        "matemática": "Matemática", "matematica": "Matemática",
        "programação": "Programação", "programacao": "Programação", "desenvolvimento web": "Programação",
        "português": "Português", "portugues": "Português", "língua portuguesa": "Português",
        "ciências": "Ciências", "ciencias": "Ciências", "biologia": "Ciências", "física": "Ciências", "química": "Ciências",
        "história": "História", "historia": "História",
        "geografia": "Geografia",
    }
    categoria = next((valor for chave, valor in categorias.items() if chave in nome), "Ciências")
    tema_normalizado = str(tema or "").strip().casefold()
    base_tematica = next((questoes for nome_tema, questoes in BANCO_TEMATICO.items() if nome_tema in tema_normalizado), None)
    if base_tematica:
        base = base_tematica
    else:
        # O banco genérico só pode ser usado quando o próprio tema corresponde à categoria.
        palavras_categoria = {
            "Matemática": ("matem", "álgebra", "geometr", "fração", "porcentagem", "equação"),
            "Programação": ("program", "código", "algorit", "python", "javascript", "html", "css", "sql", "lógica"),
            "Português": ("portugu", "gramática", "verbo", "substantivo", "interpretação de texto", "literatura", "acentuação"),
            "Ciências": ("ciência", "biolog", "química", "física", "ecologia", "fotossíntese", "célula", "genética", "corpo humano", "sistema digestório", "sistema respiratório"),
            "História": ("história", "guerra", "revolução", "império", "idade média", "colonização", "independência"),
            "Geografia": ("geografia", "clima", "relevo", "continente", "cartografia", "população", "urbanização"),
        }
        if not any(palavra in tema_normalizado for palavra in palavras_categoria.get(categoria, ())):
            raise RuntimeError(f"Não há banco local confiável para o tema '{tema}'. Configure OPENAI_API_KEY para gerar questões específicas, em vez de receber perguntas de outro assunto.")
        base = BANCO_LOCAL[categoria]
    # Seleciona primeiro perguntas nunca vistas por este aluno neste tema/dificuldade.
    # O banco demonstrativo não possui tags pedagógicas suficientes para separar perfeitamente
    # cada nível; a separação rigorosa por dificuldade é feita pela IA quando configurada.
    excluir = {str(texto).strip().casefold() for texto in (excluir_enunciados or []) if texto}
    novas = [questao for questao in base if questao[0].strip().casefold() not in excluir]
    antigas = [questao for questao in base if questao[0].strip().casefold() in excluir]
    random.shuffle(novas)
    random.shuffle(antigas)
    questoes = novas + antigas
    selecionadas = questoes[:min(quantidade, len(questoes))]
    # Evita duplicar enunciados dentro do mesmo desafio. Se o banco for menor que o pedido,
    # completa com questões já vistas somente depois de esgotar as inéditas.
    while len(selecionadas) < quantidade:
        disponiveis = [q for q in base if q[0] not in {item[0] for item in selecionadas}]
        if not disponiveis:
            break
        random.shuffle(disponiveis)
        selecionadas.extend(disponiveis[:quantidade - len(selecionadas)])
    if len(selecionadas) < quantidade:
        raise RuntimeError(
            f"O banco local tem apenas {len(base)} questões para '{tema}', insuficientes para montar "
            f"{quantidade} questões sem repetição. Configure OPENAI_API_KEY para ampliar a variedade."
        )
    saida = []
    for indice in range(quantidade):
        enunciado, opcoes, correta, explicacao = selecionadas[indice]
        opcoes = list(opcoes)
        resposta_correta = opcoes[LETRAS.index(correta)]
        random.shuffle(opcoes)
        letra_correta = LETRAS[opcoes.index(resposta_correta)]
        # O contexto do tema aparece no desafio sem afirmar que toda pergunta
        # do banco local foi criada especificamente para ele.
        saida.append({
            "enunciado": enunciado,
            "alternativas": dict(zip(LETRAS, opcoes)),
            "alternativa_correta": letra_correta,
            "explicacao": explicacao,
        })
    return saida


def gerar_questoes(materia, tema, dificuldade, quantidade, excluir_enunciados=None):
    erro_ia = None
    try:
        geradas = _gerar_com_openai(materia, tema, dificuldade, quantidade, excluir_enunciados)
        if geradas:
            return geradas, "ia", None
    except RuntimeError as erro:
        erro_ia = str(erro)
    return _gerar_local(materia, tema, quantidade, dificuldade, excluir_enunciados), "banco_local", erro_ia
