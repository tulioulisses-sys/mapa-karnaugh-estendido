from pathlib import Path

import streamlit as st

from src.interface import mostrar_titulo_etapa


# -------------------------------------------------------------------
# Configuração dos arquivos de referência e apoio
# -------------------------------------------------------------------

# Este arquivo está dentro da pasta "pages".
# Portanto, parents[1] corresponde à pasta raiz do projeto.
PASTA_RAIZ = Path(__file__).resolve().parents[1]

CAMINHO_ARTIGO = (
    PASTA_RAIZ
    / "Método de projeto ótimo para circuitos sequenciais fluídicos.pdf"
)

CAMINHO_APOSTILA = (
    PASTA_RAIZ
    / "Sistemas Automáticos.pdf"
)

CAMINHO_GUIA_RAPIDO = (
    PASTA_RAIZ
    / "Guia Rápido.pdf"
)


@st.cache_data(show_spinner=False)
def carregar_pdf(caminho: str) -> bytes:
    """
    Carrega um arquivo PDF e mantém seu conteúdo em cache.

    O uso do cache evita que o Streamlit leia novamente o arquivo
    do disco a cada interação realizada na página.
    """

    return Path(caminho).read_bytes()


def mostrar_download_pdf(
    titulo: str,
    descricao: str,
    caminho: Path,
    nome_download: str,
    chave: str,
    texto_botao: str = "Baixar PDF",
) -> None:
    """
    Exibe a descrição de um material e seu botão para download.

    Caso o arquivo não exista, apresenta uma mensagem informando
    o caminho esperado dentro do projeto.
    """

    st.markdown(f"#### {titulo}")
    st.write(descricao)

    if not caminho.exists():
        st.warning(
            "O arquivo não foi encontrado na pasta raiz do projeto.\n\n"
            f"Caminho esperado: `{caminho}`"
        )
        return

    try:
        dados_pdf = carregar_pdf(
            str(caminho)
        )

        st.download_button(
            label=texto_botao,
            data=dados_pdf,
            file_name=nome_download,
            mime="application/pdf",
            key=chave,
            width="stretch",
        )

    except OSError as erro:
        st.error(
            "Não foi possível abrir o arquivo para download.\n\n"
            f"Detalhes: {erro}"
        )


# -------------------------------------------------------------------
# Conteúdo da página
# -------------------------------------------------------------------

st.title("Sobre o método")

st.markdown(
    """
    O **Método do Mapa de Karnaugh Estendido** é uma técnica utilizada
    no projeto de comandos para sistemas sequenciais fluídicos, como
    circuitos pneumáticos, eletropneumáticos e hidráulicos.

    O método parte da sequência de movimentos desejada para os atuadores
    e analisa os diferentes estados assumidos pelo sistema durante o ciclo.
    A partir dessa análise, são determinadas as condições lógicas que devem
    comandar cada avanço, retorno ou mudança de memória.
    """
)


mostrar_titulo_etapa(
    1,
    "Objetivo do método",
    (
        "Obter equações de comando que executem a sequência desejada "
        "de maneira organizada, segura e com a menor quantidade possível "
        "de elementos auxiliares."
    ),
)

st.markdown(
    """
    O objetivo principal é transformar uma sequência de movimentos, como
    `A+ → B+ → B− → A−`, em um conjunto de equações booleanas capazes de
    controlar os atuadores.

    Essas equações devem permitir que cada comando seja acionado apenas no
    momento correto, evitando que um mesmo sinal permaneça ativo em regiões
    inadequadas do ciclo ou provoque movimentos diferentes ao mesmo tempo.
    """
)


mostrar_titulo_etapa(
    2,
    "Como o método funciona",
    (
        "A sequência é representada por estados físicos dos atuadores "
        "e, quando necessário, por estados adicionais de memória."
    ),
)

st.markdown(
    """
    Cada atuador possui sinais que representam suas posições. Por exemplo,
    `a0` indica que o cilindro A está recuado e `a1` indica que ele está
    avançado.

    Em atuadores com mais de duas posições, podem existir sensores
    intermediários, como `b0`, `b1`, `b2` e `b3`. Nesses casos, a sequência
    também informa até qual sensor o atuador deve se deslocar.

    A sequência de operação é percorrida passo a passo. Em cada etapa,
    observa-se o estado dos sensores e identifica-se qual sinal deve provocar
    o próximo movimento.

    Quando dois momentos diferentes da sequência apresentam o mesmo conjunto
    de sinais físicos, os sensores podem não ser suficientes para distinguir
    em qual parte do ciclo o sistema se encontra. Nesse caso, o método
    acrescenta memórias, normalmente representadas por `X`, `Y`, `Z` e assim
    por diante.

    Essas memórias dividem o ciclo em regiões lógicas diferentes e permitem
    separar comandos que, sem essa diferenciação, poderiam receber a mesma
    condição de acionamento.
    """
)


mostrar_titulo_etapa(
    3,
    "Condição mínima e qualificação dos comandos",
    (
        "Cada comando recebe inicialmente a condição que representa "
        "a conclusão do passo anterior."
    ),
)

st.markdown(
    """
    A primeira condição encontrada para um movimento é chamada de
    **condição mínima**. Ela corresponde ao sinal produzido pela etapa
    anterior da sequência.

    Entretanto, essa condição pode também estar presente em outro momento
    do ciclo. Por isso, o método compara o comando com seu contracomando e
    com os demais movimentos do sistema.

    Quando existe possibilidade de acionamento indevido, são acrescentados
    sinais qualificadores. Esses sinais podem ser posições de outros
    atuadores, estados das memórias ou condições externas de um loop.

    A qualificação garante que a equação seja verdadeira apenas na região
    correta do mapa.
    """
)


mostrar_titulo_etapa(
    4,
    "Pontos perigosos",
    (
        "São estados nos quais uma equação ainda poderia acionar um "
        "movimento fora do momento previsto."
    ),
)

st.markdown(
    """
    Mesmo depois da diferenciação entre comando e contracomando, uma equação
    pode continuar verdadeira em algum estado no qual sua saída deveria estar
    desligada.

    Esse estado é chamado de **ponto perigoso**. Ele representa uma situação
    em que o circuito poderia produzir um movimento antecipado, repetir uma
    ação já executada ou acionar uma saída indevidamente.

    Para eliminar esse risco, o método acrescenta um
    **qualificador complementar** à equação. A equação final deve ser falsa em
    todos os pontos perigosos e verdadeira somente durante a etapa em que o
    comando é necessário.
    """
)


mostrar_titulo_etapa(
    5,
    "Recursos adicionais da plataforma",
    (
        "A ferramenta também interpreta movimentos simultâneos, atuadores "
        "multiposição e trechos repetitivos condicionais."
    ),
)

st.markdown(
    """
    Além das sequências tradicionais, a plataforma permite representar:

    - **movimentos simultâneos**, usando parênteses, como
      `(B+, C+)`;
    - **atuadores multiposição**, indicando o sensor de destino, como
      `B+ até b2`;
    - **loops condicionais**, usando colchetes e uma condição, como
      `[C+, D+, C-, D-] enquanto e=0`;
    - **mais de um loop independente**, utilizando sinais externos
      diferentes, como `e` e `f`.

    Nos loops, a condição negada, como `e'`, normalmente representa a
    repetição. A condição direta, como `e`, representa a saída do trecho
    repetitivo e a continuação da sequência.
    """
)


mostrar_titulo_etapa(
    6,
    "Resultado fornecido pelo método",
    (
        "Ao final, são obtidas as equações booleanas que comandam "
        "os atuadores e as memórias do sistema."
    ),
)

st.markdown(
    """
    O resultado é um conjunto de equações para os avanços e retornos dos
    atuadores, além das equações de acionamento e desacionamento das memórias.

    Quando uma mesma saída física aparece várias vezes na sequência, a
    plataforma mostra cada **ocorrência lógica** separadamente, como
    `B+(1)`, `B+(2)` e `B+(3)`. Em seguida, apresenta a
    **saída física agregada**, formada pela soma lógica dessas ocorrências.

    As equações podem ser utilizadas na montagem de circuitos pneumáticos,
    eletropneumáticos ou hidráulicos. Também podem servir como base para uma
    implementação em relés, lógica elétrica, controladores programáveis ou
    sistemas de simulação.

    A ferramenta desenvolvida neste projeto automatiza essa análise:
    interpreta a sequência informada, identifica os estados dos atuadores,
    determina a quantidade necessária de memórias, localiza qualificações e
    pontos perigosos, constrói o mapa e apresenta as equações finais de
    comando.
    """
)


st.info(
    """
    O mapa de Karnaugh Estendido não é apenas uma simplificação algébrica.
    Ele também representa a evolução sequencial do sistema e utiliza
    memórias para diferenciar estados físicos que se repetem durante o ciclo.
    """
)


# -------------------------------------------------------------------
# Materiais para download
# -------------------------------------------------------------------

st.divider()

st.header("Materiais de referência e apoio")

st.write(
    """
    Os materiais abaixo apresentam a fundamentação do método, exemplos de
    aplicação em sistemas sequenciais fluídicos e orientações para utilizar
    a plataforma.
    """
)

coluna_1, coluna_2, coluna_3 = st.columns(3)


with coluna_1:
    with st.container(border=True):
        mostrar_download_pdf(
            titulo="Guia rápido da plataforma",
            descricao=(
                "Manual resumido com instruções para escrever sequências, "
                "representar movimentos simultâneos, utilizar sensores "
                "intermediários, configurar loops e interpretar os símbolos "
                "das equações finais."
            ),
            caminho=CAMINHO_GUIA_RAPIDO,
            nome_download="Guia Rápido.pdf",
            chave="download_guia_rapido",
            texto_botao="Baixar guia rápido",
        )


with coluna_2:
    with st.container(border=True):
        mostrar_download_pdf(
            titulo="Artigo sobre o método",
            descricao=(
                "Documento que apresenta o método de projeto ótimo para "
                "circuitos sequenciais fluídicos e discute a utilização "
                "de memórias e a obtenção das equações de comando."
            ),
            caminho=CAMINHO_ARTIGO,
            nome_download=(
                "Método de projeto ótimo para circuitos "
                "sequenciais fluídicos.pdf"
            ),
            chave="download_artigo_metodo",
        )


with coluna_3:
    with st.container(border=True):
        mostrar_download_pdf(
            titulo="Sistemas Automáticos",
            descricao=(
                "Material didático com a explicação do mapa de Karnaugh "
                "Estendido e exemplos de identificação das condições "
                "mínimas, qualificadores e pontos perigosos."
            ),
            caminho=CAMINHO_APOSTILA,
            nome_download="Sistemas Automáticos.pdf",
            chave="download_sistemas_automaticos",
        )