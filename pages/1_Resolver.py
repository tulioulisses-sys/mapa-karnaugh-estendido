
from collections import defaultdict
import pandas as pd
import streamlit as st

import streamlit.components.v1 as components

from src.mapa import gerar_mapa_svg

from src.interface import (
    mostrar_cabecalho,
    mostrar_chamada,
)
from src.solver import (
    analisar_entrada,
    resolver_site,
)


# ---------------------------------------------------------
# Controle do estado da interface
# ---------------------------------------------------------

def limpar_resultado() -> None:
    """
    Remove o resultado anterior quando algum estado inicial
    é alterado.
    """

    st.session_state.pop("resultado_solver", None)
    st.session_state.pop("assinatura_resultado", None)


def ao_alterar_sequencia() -> None:
    """
    Limpa erros, confirmação e resultados quando o usuário
    altera o texto da sequência.
    """

    st.session_state["sequencia_confirmada"] = False

    st.session_state.pop("erro_sequencia", None)
    st.session_state.pop("etapas_confirmadas", None)
    st.session_state.pop(
        "estado_inicial_confirmado",
        None,
    )
    st.session_state.pop("atuadores_confirmados", None)
    st.session_state.pop("sequencia_formatada", None)

    limpar_resultado()


if "sequencia_confirmada" not in st.session_state:
    st.session_state["sequencia_confirmada"] = False


# ---------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------


def formatar_estado(estado: dict[str, int]) -> str:
    """
    Transforma {"A": 0, "B": 1} em:
    a0 · b1
    """

    if not estado:
        return "—"

    return " · ".join(
        f"{atuador.lower()}{valor}"
        for atuador, valor in estado.items()
    )

def analisar_necessidade_memorias(
    resultado: dict,
) -> tuple[list[dict], int]:
    """
    Localiza estados físicos iguais que receberam códigos
    de memória diferentes.
    """

    grupos = defaultdict(list)

    for etapa in resultado["etapas"]:
        chave = tuple(
            etapa["estado_antes"].items()
        )

        grupos[chave].append(etapa)

    conflitos = []
    maior_quantidade_situacoes = 1

    for etapas_mesmo_estado in grupos.values():
        codigos = {}

        for etapa in etapas_mesmo_estado:
            codigo = tuple(
                etapa["codigo_memorias"].items()
            )

            codigos.setdefault(
                codigo,
                [],
            ).append(etapa)

        if len(codigos) <= 1:
            continue

        maior_quantidade_situacoes = max(
            maior_quantidade_situacoes,
            len(codigos),
        )

        conflitos.append(
            {
                "Estado físico repetido": formatar_estado(
                    etapas_mesmo_estado[0][
                        "estado_antes"
                    ]
                ),
                "Etapas": ", ".join(
                    str(etapa["numero"])
                    for etapa in etapas_mesmo_estado
                ),
                "Comandos seguintes": ", ".join(
                    etapa["comando_texto"]
                    for etapa in etapas_mesmo_estado
                ),
                "Códigos utilizados": ", ".join(
                    formatar_estado(dict(codigo))
                    for codigo in codigos
                ),
            }
        )

    return conflitos, maior_quantidade_situacoes

# ---------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------

mostrar_cabecalho()


# ---------------------------------------------------------
# Etapa 1 — sequência
# ---------------------------------------------------------

mostrar_chamada(
    "Informe aqui a sequência desejada"
)


# Instruções agora aparecem antes do campo.

with st.expander(
    "Como escrever a sequência?",
    expanded=True,
):
    st.markdown(
        """
        - `A`, `B`, `C` representam os atuadores.
        - `+` significa avanço.
        - `-` significa retorno.
        - Separe as etapas usando vírgulas.
        - Use parênteses para movimentos simultâneos.

        **Exemplo simples**

        `A+, B+, B-, A-`

        **Exemplo com simultaneidade**

        `A+, B+, (C-, D+), (D-, A-)`
        """
    )


sequencia = st.text_input(
    "Sequência de movimentos",
    placeholder="Exemplo: A+, B+, B-, A-",
    key="sequencia_digitada",
    on_change=ao_alterar_sequencia,
)


continuar_clicado = st.button(
    "Continuar",
    type="primary",
    width="stretch",
)


if continuar_clicado:
    try:
        dados_entrada = analisar_entrada(
            sequencia
        )

        st.session_state[
            "sequencia_formatada"
        ] = dados_entrada["sequencia_formatada"]

        st.session_state[
            "estado_inicial_confirmado"
        ] = dados_entrada["estado_inicial"]

        st.session_state[
            "sequencia_confirmada"
        ] = True

        st.session_state.pop(
            "erro_sequencia",
            None,
        )

        limpar_resultado()

    except ValueError as erro:
        st.session_state[
            "sequencia_confirmada"
        ] = False

        st.session_state[
            "erro_sequencia"
        ] = str(erro)


erro_sequencia = st.session_state.get(
    "erro_sequencia"
)

if erro_sequencia:
    st.error(
        "Corrija a sequência antes de continuar: "
        f"{erro_sequencia}"
    )


sequencia_valida = st.session_state.get(
    "sequencia_confirmada",
    False,
)


if sequencia_valida:
    st.html(
        f"""
        <div class="sequence-preview">
            {st.session_state["sequencia_formatada"]}
        </div>
        """
    )


# ---------------------------------------------------------
# Etapa 2 — estado inicial identificado
# ---------------------------------------------------------

estados_iniciais = {}
entrada_coerente = False


if sequencia_valida:
    estados_iniciais = dict(
        st.session_state[
            "estado_inicial_confirmado"
        ]
    )

    entrada_coerente = True

    st.info(
        "Estado inicial identificado para os atuadores: "
        f"{formatar_estado(estados_iniciais)}"
    )


# ---------------------------------------------------------
# Botão de resolução
# ---------------------------------------------------------

if sequencia_valida:
    st.write("")

    assinatura_atual = {
        "sequencia": sequencia.strip(),
    }

    resolver_clicado = st.button(
        "Resolver sequência",
        type="primary",
        disabled=not entrada_coerente,
        width="stretch",
    )

    if resolver_clicado:
        try:
            with st.spinner(
                "Calculando memórias e equações...",
                show_time=True,
            ):
                resultado_calculado = resolver_site(
                    sequencia=sequencia,
                    ciclo_continuo=False,
                )

            st.session_state[
                "resultado_solver"
            ] = resultado_calculado

            st.session_state[
                "assinatura_resultado"
            ] = assinatura_atual

        except (ValueError, RuntimeError) as erro:
            limpar_resultado()

            st.error(
                "Não foi possível resolver a sequência. "
                f"Detalhes: {erro}"
            )


# ---------------------------------------------------------
# Resultado
# ---------------------------------------------------------

resultado = st.session_state.get(
    "resultado_solver"
)

assinatura_resultado = st.session_state.get(
    "assinatura_resultado"
)


resultado_corresponde_entrada = (
    sequencia_valida
    and resultado is not None
    and assinatura_resultado == assinatura_atual
)


if resultado_corresponde_entrada:
    st.divider()

    mostrar_chamada(
        "Veja abaixo o resultado da resolução"
    )

    (
        aba_memorias,
        aba_etapas,
        aba_mapa,
        aba_resolucao,
        aba_equacoes,
    ) = st.tabs(
        [
            "Memórias",
            "Etapas",
            "Mapa",
            "Resolução",
            "Equações de Comando",
        ]
    )


    # -----------------------------------------------------
    # Aba: memórias
    # -----------------------------------------------------

    with aba_memorias:
        st.subheader(
            "Cálculo da necessidade de memórias"
        )

        quantidade = resultado[
            "quantidade_memorias"
        ]

        capacidade = 2 ** quantidade

        conflitos, maior_quantidade = (
            analisar_necessidade_memorias(
                resultado
            )
        )

        st.markdown(
            f"""
            **Memórias encontradas:** `{quantidade}`

            **Capacidade de diferenciação:**

            \[
            2^{quantidade} = {capacidade}
            \]

            Portanto, o circuito pode representar
            **{capacidade} estado(s) lógico(s) de memória**.
            """
        )

        if quantidade == 0:
            st.info(
                "Nenhuma memória foi necessária porque "
                "os estados físicos alcançáveis já distinguem "
                "corretamente os comandos seguintes. "
                "Com 0 memórias, existe uma única combinação: "
                "2⁰ = 1."
            )

        else:
            st.write(
                "As memórias são necessárias porque um mesmo "
                "estado físico aparece em momentos diferentes "
                "da sequência e precisa produzir decisões "
                "diferentes."
            )

            if conflitos:
                st.dataframe(
                    pd.DataFrame(conflitos),
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown(
                f"""
                O maior grupo encontrado exige distinguir
                **{maior_quantidade} situação(ões)** para um
                mesmo estado físico.
                """
            )

            st.markdown(
                "**Memórias utilizadas:** "
                + ", ".join(
                    resultado["memorias"]
                )
            )


    # -----------------------------------------------------
    # Aba: etapas
    # -----------------------------------------------------

    with aba_etapas:
        st.subheader("Evolução da sequência")

        linhas_tabela = []

        for etapa in resultado["etapas"]:
            linhas_tabela.append(
                {
                    "Etapa": etapa["numero"],
                    "Comando": etapa[
                        "comando_texto"
                    ],
                    "Estado antes": formatar_estado(
                        etapa["estado_antes"]
                    ),
                    "Estado depois": formatar_estado(
                        etapa["estado_depois"]
                    ),
                    "Fase": f"F{etapa['fase']}",
                    "Memórias": formatar_estado(
                        etapa["codigo_memorias"]
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(linhas_tabela),
            use_container_width=True,
            hide_index=True,
        )


    # -----------------------------------------------------
    # Aba: mapa
    # -----------------------------------------------------

    with aba_mapa:
        try:
            mapa = gerar_mapa_svg(
                resultado,
                incluir_titulo=True,
            )

            html_mapa = f"""
            <style>
                html,
                body {{
                    margin: 0;
                    padding: 0;
                    background: #ffffff;
                }}

                .mapa-scroll {{
                    width: 100%;
                    overflow-x: auto;
                    overflow-y: hidden;
                    padding-bottom: 8px;
                }}

                .mapa-conteudo {{
                    width: {mapa.largura}px;
                    margin: 0 auto;
                }}

                .mapa-conteudo svg {{
                    display: block;
                    width: {mapa.largura}px;
                    height: {mapa.altura}px;
                }}

                @media (max-width: 768px) {{
                    .mapa-conteudo {{
                        margin: 0;
                    }}
                }}
            </style>

            <div class="mapa-scroll">
                <div class="mapa-conteudo">
                    {mapa.svg}
                </div>
            </div>
            """

            components.html(
                html_mapa,
                height=mapa.altura + 25,
                scrolling=False,
            )

            st.download_button(
                label="Baixar mapa em SVG",
                data=mapa.svg.encode("utf-8"),
                file_name="mapa_karnaugh_estendido.svg",
                mime="image/svg+xml",
                width="stretch",
            )

        except (KeyError, ValueError) as erro:
            st.error(
                "Não foi possível construir o mapa. "
                f"Detalhes: {erro}"
            )


    # -----------------------------------------------------
    # Aba: resolução
    # -----------------------------------------------------

    with aba_resolucao:
        st.subheader(
            "Qualificação dos comandos"
        )

        tabela_resolucao = pd.DataFrame(
            resultado["resolucao"]
        )

        st.dataframe(
            tabela_resolucao,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Comando": (
                    st.column_config.TextColumn(
                        width="small",
                    )
                ),
                "Condição básica": (
                    st.column_config.TextColumn(
                        width="small",
                    )
                ),
                "Pontos perigosos encontrados": (
                    st.column_config.TextColumn(
                        width="large",
                    )
                ),
                "Qualificador acrescentado": (
                    st.column_config.TextColumn(
                        width="medium",
                    )
                ),
                "Equação final": (
                    st.column_config.TextColumn(
                        width="large",
                    )
                ),
            },
        )


    # -----------------------------------------------------
    # Aba: equações
    # -----------------------------------------------------

    with aba_equacoes:
        st.subheader(
            "Equações booleanas de comando"
        )

        linhas_equacoes = []

        for saida, equacao in resultado[
            "equacoes"
        ].items():
            linhas_equacoes.append(
                {
                    "Tipo": "Comando",
                    "Saída": saida,
                    "Equação": equacao,
                }
            )

        for memoria, equacao in resultado[
            "equacoes_memorias"
        ].items():
            linhas_equacoes.append(
                {
                    "Tipo": "Memória completa",
                    "Saída": memoria,
                    "Equação": equacao,
                }
            )

        tabela_equacoes = pd.DataFrame(
            linhas_equacoes
        )

        st.dataframe(
            tabela_equacoes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tipo": st.column_config.TextColumn(
                    width="medium",
                ),
                "Saída": st.column_config.TextColumn(
                    width="small",
                ),
                "Equação": st.column_config.TextColumn(
                    width="large",
                ),
            },
        )

        csv_equacoes = tabela_equacoes.to_csv(
            index=False,
            sep=";",
        ).encode("utf-8-sig")

        st.download_button(
            "Baixar equações para o Excel",
            data=csv_equacoes,
            file_name="equacoes_karnaugh.csv",
            mime="text/csv",
            width="stretch",
        )


elif (
    resultado is not None
    and sequencia_valida
):
    st.write(
        "A entrada foi alterada. Resolva novamente "
        "para atualizar os resultados."
    )