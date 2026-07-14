from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.interface import mostrar_cabecalho, mostrar_chamada
from src.mapa import gerar_mapa_svg
from src.solver import analisar_entrada, resolver_site


import streamlit as st

# Outros imports...

st.markdown(
    """
    <style>
    [data-testid="stToolbar"] a[href*="github.com"],
    header a[href*="github.com"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

EXEMPLOS = {
    "simples": "A+, B+, B-, A-",
    "multiposicao": (
        "A+, B+ até b1, C+, B+ até b2, C-, "
        "B+ até b3, A-, B- até b0"
    ),
    "loop": (
        "A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-"
    ),
}


def limpar_resultado() -> None:
    """Remove resultados que pertencem a uma entrada anterior."""

    for chave in (
        "resultado_solver",
        "assinatura_resultado",
        "erro_resolucao",
    ):
        st.session_state.pop(chave, None)


def limpar_analise() -> None:
    """Reinicia a análise quando o texto da sequência é alterado."""

    for chave in (
        "entrada_analisada",
        "dados_entrada",
        "erro_sequencia",
    ):
        st.session_state.pop(chave, None)

    limpar_resultado()


def ao_alterar_sequencia() -> None:
    limpar_analise()


def preencher_exemplo(sequencia: str) -> None:
    st.session_state["sequencia_digitada"] = sequencia
    limpar_analise()


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------


def formatar_estado_indices(
    estado: Mapping[str, int | bool],
) -> str:
    """Formata o estado legado, como ``a0 · b1``."""

    if not estado:
        return "—"

    return " · ".join(
        f"{str(atuador).lower()}{int(valor)}"
        for atuador, valor in estado.items()
    )


def formatar_estado_sensores(
    sensores: Mapping[str, str] | None,
) -> str:
    """Formata os sensores ativos, inclusive os multiposição."""

    if not sensores:
        return "—"

    return " · ".join(str(sensor) for sensor in sensores.values())


def formatar_memorias(
    codigo: Mapping[str, int | bool] | None,
) -> str:
    if not codigo:
        return "—"

    return " · ".join(
        f"{str(nome).lower()}{int(valor)}"
        for nome, valor in codigo.items()
    )


def assinatura_da_entrada(sequencia: str) -> dict[str, str]:
    return {"sequencia": sequencia.strip()}


def descricao_recursos(dados: Mapping[str, Any]) -> list[str]:
    recursos: list[str] = []

    multiposicao = list(dados.get("atuadores_multiposicao", []))
    if multiposicao:
        recursos.append(
            "Multiposição: " + ", ".join(multiposicao)
        )

    entradas = list(dados.get("entradas_externas", []))
    if entradas:
        recursos.append(
            "Entradas externas: " + ", ".join(entradas)
        )

    if dados.get("possui_loop"):
        recursos.append("Loop condicional")

    if not recursos:
        recursos.append("Sequência linear com sensores de duas posições")

    return recursos


# ---------------------------------------------------------------------------
# Memórias e tabelas
# ---------------------------------------------------------------------------


def analisar_necessidade_memorias(
    resultado: Mapping[str, Any],
) -> tuple[list[dict[str, str]], int]:
    """
    Localiza estados físicos repetidos que receberam códigos de memória
    diferentes. A comparação usa os sensores ativos, não apenas 0/1.
    """

    grupos: dict[tuple[tuple[str, str], ...], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )

    for etapa in resultado.get("etapas", []):
        sensores = etapa.get("sensores_ativos_antes") or {}

        if sensores:
            chave = tuple(
                (str(nome), str(sensor))
                for nome, sensor in sensores.items()
            )
        else:
            estado = etapa.get("estado_antes") or {}
            chave = tuple(
                (str(nome), str(valor))
                for nome, valor in estado.items()
            )

        grupos[chave].append(etapa)

    conflitos: list[dict[str, str]] = []
    maior_quantidade = 1

    for etapas_mesmo_estado in grupos.values():
        codigos: dict[
            tuple[tuple[str, int], ...],
            list[Mapping[str, Any]],
        ] = {}

        for etapa in etapas_mesmo_estado:
            codigo = tuple(
                (str(nome), int(valor))
                for nome, valor in (
                    etapa.get("codigo_memorias") or {}
                ).items()
            )
            codigos.setdefault(codigo, []).append(etapa)

        if len(codigos) <= 1:
            continue

        maior_quantidade = max(maior_quantidade, len(codigos))
        primeira = etapas_mesmo_estado[0]
        estado_texto = primeira.get("estado_antes_texto")

        if not estado_texto:
            estado_texto = formatar_estado_sensores(
                primeira.get("sensores_ativos_antes")
            )

        conflitos.append(
            {
                "Estado físico repetido": str(estado_texto),
                "Etapas": ", ".join(
                    str(etapa.get("numero", "—"))
                    for etapa in etapas_mesmo_estado
                ),
                "Comandos seguintes": ", ".join(
                    str(etapa.get("comando_texto", "—"))
                    for etapa in etapas_mesmo_estado
                ),
                "Códigos utilizados": ", ".join(
                    formatar_memorias(dict(codigo))
                    for codigo in codigos
                ),
            }
        )

    return conflitos, maior_quantidade


def tabela_sensores(
    sensores_por_atuador: Mapping[str, list[str]],
    sensores_iniciais: Mapping[str, str],
) -> pd.DataFrame:
    linhas = []

    for atuador, sensores in sensores_por_atuador.items():
        linhas.append(
            {
                "Atuador": atuador,
                "Sensores": ", ".join(sensores),
                "Posições": len(sensores),
                "Posição inicial": sensores_iniciais.get(atuador, "—"),
            }
        )

    return pd.DataFrame(linhas)


def tabela_loops(loops: list[Mapping[str, Any]]) -> pd.DataFrame:
    linhas = []

    for numero, loop in enumerate(loops, start=1):
        linhas.append(
            {
                "Loop": numero,
                "Trecho": (
                    f"Etapas {loop.get('etapa_inicial', '—')} a "
                    f"{loop.get('etapa_final', '—')}"
                ),
                "Repetição": loop.get(
                    "condicao_repeticao_texto",
                    "—",
                ),
                "Saída": loop.get("condicao_saida_texto", "—"),
                "Retorno": (
                    f"Etapa {loop.get('retorna_para_etapa', '—')}"
                ),
                "Continuação": (
                    f"Etapa {loop.get('continua_na_etapa', '—')}"
                ),
            }
        )

    return pd.DataFrame(linhas)


def tabela_etapas(resultado: Mapping[str, Any]) -> pd.DataFrame:
    linhas = []

    for etapa in resultado.get("etapas", []):
        estado_antes = etapa.get("estado_antes_texto")
        if not estado_antes:
            estado_antes = formatar_estado_sensores(
                etapa.get("sensores_ativos_antes")
            )

        estado_depois = etapa.get("estado_depois_texto")
        if not estado_depois:
            estado_depois = formatar_estado_sensores(
                etapa.get("sensores_ativos_depois")
            )

        condicao = etapa.get("condicao_externa_texto") or "—"

        linhas.append(
            {
                "Etapa": etapa.get("numero"),
                "Comando": etapa.get("comando_texto", "—"),
                "Estado antes": estado_antes,
                "Estado depois": estado_depois,
                "Condição externa": condicao,
                "No loop": "Sim" if etapa.get("pertence_loop") else "Não",
                "Fase": f"F{etapa.get('fase', 0)}",
                "Memórias": formatar_memorias(
                    etapa.get("codigo_memorias")
                ),
            }
        )

    return pd.DataFrame(linhas)


def tabela_equacoes(resultado: Mapping[str, Any]) -> pd.DataFrame:
    linhas: list[dict[str, str]] = []

    equacoes_comandos = dict(
        resultado.get("equacoes_comandos") or {}
    )
    equacoes_fisicas = dict(
        resultado.get("equacoes_fisicas")
        or resultado.get("equacoes")
        or {}
    )

    for saida, equacao in equacoes_comandos.items():
        linhas.append(
            {
                "Tipo": "Ocorrência lógica",
                "Saída": saida,
                "Equação": equacao,
            }
        )

    for saida, equacao in equacoes_fisicas.items():
        ja_identica = (
            saida in equacoes_comandos
            and equacoes_comandos[saida] == equacao
        )

        if ja_identica:
            continue

        linhas.append(
            {
                "Tipo": "Saída física agregada",
                "Saída": saida,
                "Equação": equacao,
            }
        )

    for memoria, equacao in (
        resultado.get("equacoes_memorias") or {}
    ).items():
        linhas.append(
            {
                "Tipo": "Memória completa",
                "Saída": memoria,
                "Equação": equacao,
            }
        )

    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Componentes de exibição
# ---------------------------------------------------------------------------


def mostrar_previa_entrada(dados: Mapping[str, Any]) -> None:
    st.success("Sequência interpretada e validada.")

    st.html(
        f"""
        <div class="sequence-preview">
            {dados.get('sequencia_formatada', '')}
        </div>
        """
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Atuadores", len(dados.get("atuadores", [])))
    col2.metric("Etapas", dados.get("quantidade_etapas", 0))
    col3.metric(
        "Multiposição",
        len(dados.get("atuadores_multiposicao", [])),
    )
    col4.metric("Loops", len(dados.get("loops", [])))

    st.caption(" · ".join(descricao_recursos(dados)))

    st.subheader("Atuadores e sensores")
    st.dataframe(
        tabela_sensores(
            dados.get("sensores_por_atuador", {}),
            dados.get("sensores_iniciais", {}),
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "Estado inicial identificado: "
        + formatar_estado_sensores(
            dados.get("sensores_iniciais")
        )
    )

    loops = list(dados.get("loops", []))
    if loops:
        st.subheader("Loop reconhecido")
        st.dataframe(
            tabela_loops(loops),
            use_container_width=True,
            hide_index=True,
        )


def mostrar_mapa(resultado: Mapping[str, Any]) -> None:
    try:
        mapa = gerar_mapa_svg(
            resultado,
            incluir_titulo=True,
            limite_celulas=256,
        )

        html_mapa = f"""
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: #ffffff;
            }}

            .mapa-scroll {{
                width: 100%;
                overflow: auto;
                padding-bottom: 10px;
                background: #ffffff;
            }}

            .mapa-conteudo {{
                width: {mapa.largura}px;
                min-width: {mapa.largura}px;
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
            height=mapa.altura + 35,
            scrolling=False,
        )

        st.download_button(
            label="Baixar mapa em SVG",
            data=mapa.svg.encode("utf-8"),
            file_name="mapa_karnaugh_estendido.svg",
            mime="image/svg+xml",
            width="stretch",
        )

    except (KeyError, ValueError, RuntimeError) as erro:
        st.error(
            "Não foi possível construir o mapa. "
            f"Detalhes: {erro}"
        )


def mostrar_resumo(resultado: Mapping[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Atuadores", len(resultado.get("atuadores", [])))
    col2.metric("Etapas", len(resultado.get("etapas", [])))
    col3.metric(
        "Memórias",
        resultado.get("quantidade_memorias", 0),
    )
    col4.metric("Loops", len(resultado.get("loops", [])))

    sensores_iniciais = resultado.get("sensores_iniciais", {})
    st.info(
        "Estado inicial: "
        + formatar_estado_sensores(sensores_iniciais)
    )

    if resultado.get("possui_atuador_multiposicao"):
        st.success(
            "Atuadores multiposição considerados: "
            + ", ".join(
                resultado.get("atuadores_multiposicao", [])
            )
        )

    loops = list(resultado.get("loops", []))
    if loops:
        st.subheader("Decisões do loop")
        st.dataframe(
            tabela_loops(loops),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Necessidade de memórias")
    quantidade = int(resultado.get("quantidade_memorias", 0))
    capacidade = 2 ** quantidade
    conflitos, maior_quantidade = analisar_necessidade_memorias(
        resultado
    )

    st.markdown(
        f"""
        **Memórias encontradas:** `{quantidade}`  
        **Capacidade de diferenciação:** `2^{quantidade} = {capacidade}`
        """
    )

    if quantidade == 0:
        st.info(
            "Nenhuma memória interna foi necessária. Os sensores físicos "
            "e as condições externas já distinguem todas as decisões."
        )
    else:
        st.write(
            "Memórias utilizadas: "
            + ", ".join(resultado.get("memorias", []))
        )

        if conflitos:
            st.dataframe(
                pd.DataFrame(conflitos),
                use_container_width=True,
                hide_index=True,
            )

        st.caption(
            "Maior quantidade de situações distintas para um mesmo "
            f"estado físico: {maior_quantidade}."
        )

    versao = resultado.get("versao_motor")



# Página



mostrar_cabecalho()

mostrar_chamada("Informe a sequência de movimentos")

with st.expander("Como escrever a sequência?", expanded=True):
    st.markdown(
        """
        Use uma única linha de texto. O sistema identifica automaticamente
        atuadores, sensores, movimentos simultâneos e loops.

        **Sequência simples**  
        `A+, B+, B-, A-`

        **Movimentos simultâneos**  
        `A+, B+, (C-, D+), (D-, A-)`

        **Atuador com várias posições**  
        `A+, B+ até b1, C+, B+ até b2, C-, B+ até b3, A-, B- até b0`

        **Loop condicional**  
        `A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-`
        """
    )
    st.info(
        """
        Para consultar mais exemplos e entender o significado dos símbolos
        utilizados nas equações, acesse a página **Sobre o método**.

        Nessa página, role até **Materiais de referência e apoio** e baixe o
        **Guia rápido da plataforma**.
        """
    )

st.caption("Preencher com um exemplo")
col_ex1, col_ex2, col_ex3 = st.columns(3)

col_ex1.button(
    "Sequência simples",
    on_click=preencher_exemplo,
    args=(EXEMPLOS["simples"],),
    width="stretch",
)
col_ex2.button(
    "Multiposição",
    on_click=preencher_exemplo,
    args=(EXEMPLOS["multiposicao"],),
    width="stretch",
)
col_ex3.button(
    "Loop condicional",
    on_click=preencher_exemplo,
    args=(EXEMPLOS["loop"],),
    width="stretch",
)

sequencia = st.text_area(
    "Sequência",
    placeholder=(
        "Exemplo: A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-"
    ),
    key="sequencia_digitada",
    on_change=ao_alterar_sequencia,
    height=105,
)

analisar_clicado = st.button(
    "Analisar sequência",
    type="primary",
    width="stretch",
)

if analisar_clicado:
    try:
        dados_entrada = analisar_entrada(sequencia)
        st.session_state["dados_entrada"] = dados_entrada
        st.session_state["entrada_analisada"] = True
        st.session_state.pop("erro_sequencia", None)
        limpar_resultado()
    except (ValueError, TypeError) as erro:
        st.session_state["entrada_analisada"] = False
        st.session_state.pop("dados_entrada", None)
        st.session_state["erro_sequencia"] = str(erro)
        limpar_resultado()

erro_sequencia = st.session_state.get("erro_sequencia")
if erro_sequencia:
    st.error(
        "Corrija a sequência antes de continuar: "
        f"{erro_sequencia}"
    )

entrada_analisada = bool(
    st.session_state.get("entrada_analisada", False)
)
dados_entrada = st.session_state.get("dados_entrada")

if entrada_analisada and dados_entrada:
    st.divider()
    mostrar_chamada("Confira a interpretação")
    mostrar_previa_entrada(dados_entrada)

    assinatura_atual = assinatura_da_entrada(sequencia)

    resolver_clicado = st.button(
        "Resolver sequência e gerar mapa",
        type="primary",
        width="stretch",
    )

    if resolver_clicado:
        try:
            with st.spinner(
                "Calculando etapas, memórias, equações e mapa...",
                show_time=True,
            ):
                resultado_calculado = resolver_site(
                    sequencia=sequencia,
                    ciclo_continuo=False,
                )

            st.session_state["resultado_solver"] = resultado_calculado
            st.session_state["assinatura_resultado"] = assinatura_atual
            st.session_state.pop("erro_resolucao", None)

        except (ValueError, RuntimeError, TypeError) as erro:
            limpar_resultado()
            st.session_state["erro_resolucao"] = str(erro)

else:
    assinatura_atual = assinatura_da_entrada(sequencia)

erro_resolucao = st.session_state.get("erro_resolucao")
if erro_resolucao:
    st.error(
        "Não foi possível resolver a sequência. "
        f"Detalhes: {erro_resolucao}"
    )

resultado = st.session_state.get("resultado_solver")
assinatura_resultado = st.session_state.get("assinatura_resultado")

resultado_corresponde = (
    entrada_analisada
    and resultado is not None
    and assinatura_resultado == assinatura_atual
)

if resultado_corresponde:
    st.divider()
    mostrar_chamada("Resultado da resolução")

    (
        aba_resumo,
        aba_mapa,
        aba_etapas,
        aba_resolucao,
        aba_equacoes,
    ) = st.tabs(
        [
            "Resumo",
            "Mapa",
            "Etapas",
            "Resolução do método",
            "Equações",
        ]
    )

    with aba_resumo:
        mostrar_resumo(resultado)

    with aba_mapa:
        mostrar_mapa(resultado)

    with aba_etapas:
        st.subheader("Evolução da sequência")
        st.dataframe(
            tabela_etapas(resultado),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Etapa": st.column_config.NumberColumn(width="small"),
                "Comando": st.column_config.TextColumn(width="medium"),
                "Estado antes": st.column_config.TextColumn(width="large"),
                "Estado depois": st.column_config.TextColumn(width="large"),
                "Condição externa": st.column_config.TextColumn(
                    width="medium"
                ),
            },
        )

    with aba_resolucao:
        st.subheader("Qualificação dos comandos")
        resolucao = pd.DataFrame(resultado.get("resolucao", []))

        if resolucao.empty:
            st.info("Nenhuma linha de resolução foi produzida.")
        else:
            st.dataframe(
                resolucao,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Passo": st.column_config.NumberColumn(width="small"),
                    "Comando": st.column_config.TextColumn(width="small"),
                    "Condição mínima": st.column_config.TextColumn(
                        width="medium"
                    ),
                    "Condição externa": st.column_config.TextColumn(
                        width="small"
                    ),
                    "Restrição do ramo": st.column_config.TextColumn(
                        width="medium"
                    ),
                    "Contato de parada": st.column_config.TextColumn(
                        width="medium"
                    ),
                    "Pontos perigosos": st.column_config.TextColumn(
                        width="large"
                    ),
                    "Equação final": st.column_config.TextColumn(
                        width="large"
                    ),
                },
            )

    with aba_equacoes:
        st.subheader("Equações booleanas de comando")
        equacoes = tabela_equacoes(resultado)

        st.dataframe(
            equacoes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tipo": st.column_config.TextColumn(width="medium"),
                "Saída": st.column_config.TextColumn(width="small"),
                "Equação": st.column_config.TextColumn(width="large"),
            },
        )

        csv_equacoes = equacoes.to_csv(
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


elif resultado is not None and entrada_analisada:
    st.info(
        "A sequência foi alterada depois da última resolução. "
        "Analise e resolva novamente para atualizar os resultados."
    )