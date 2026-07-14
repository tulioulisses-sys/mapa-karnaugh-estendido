from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


# -------------------------------------------------------------------
# Caminhos do projeto
# -------------------------------------------------------------------

RAIZ_PROJETO = Path(__file__).resolve().parents[1]

CAMINHO_CSS = (
    RAIZ_PROJETO
    / "assets"
    / "styles.css"
)

CAMINHO_LOGO_UFPE = (
    RAIZ_PROJETO
    / "assets"
    / "images"
    / "lofo_ufpe.png"
)


# -------------------------------------------------------------------
# Funções auxiliares
# -------------------------------------------------------------------

def carregar_css() -> None:
    """Carrega a folha de estilos da aplicação."""

    if not CAMINHO_CSS.exists():
        st.error(
            f"Arquivo de estilos não encontrado: {CAMINHO_CSS}"
        )
        return

    st.html(CAMINHO_CSS)


@st.cache_data(show_spinner=False)
def carregar_imagem_base64(caminho: str) -> str:


    dados = Path(caminho).read_bytes()

    return base64.b64encode(dados).decode("utf-8")


def obter_html_logo_ufpe() -> str:


    if not CAMINHO_LOGO_UFPE.exists():
        return """
        <div
            class="footer-ufpe"
            title="Imagem da UFPE não encontrada"
        >
            UFPE
        </div>
        """

    try:
        imagem_base64 = carregar_imagem_base64(
            str(CAMINHO_LOGO_UFPE)
        )

        return f"""
        <div
            class="footer-ufpe footer-logo-box"
            style="
                background-color: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 12px;
                border-radius: 10px;
                min-width: 130px;
                min-height: 100px;
                box-sizing: border-box;
            "
        >
            <img
                src="data:image/png;base64,{imagem_base64}"
                alt="Logo da Universidade Federal de Pernambuco"
                title="Universidade Federal de Pernambuco"
                style="
                    display: block;
                    width: 100%;
                    max-width: 115px;
                    max-height: 85px;
                    object-fit: contain;
                    background-color: #ffffff;
                "
            >
        </div>
        """

    except OSError:
        return """
        <div
            class="footer-ufpe"
            title="Não foi possível carregar a imagem da UFPE"
        >
            UFPE
        </div>
        """


# -------------------------------------------------------------------
# Componentes da interface
# -------------------------------------------------------------------

def mostrar_cabecalho() -> None:
    """Mostra a apresentação principal da ferramenta."""

    st.html(
        """
        <section class="hero">
            <h1 class="hero-title">
                Resolução das Equações de Comando de Sistemas
                Fluídicos Utilizando o Método do Mapa de
                Karnaugh Estendido
            </h1>
        </section>
        """
    )


def mostrar_titulo_etapa(
    numero: int,
    titulo: str,
    descricao: str,
) -> None:
    """Mostra o cabeçalho padronizado de uma etapa."""

    st.html(
        f"""
        <div class="step-header">
            <div class="step-number">
                {numero}
            </div>

            <div>
                <h2 class="step-title">
                    {titulo}
                </h2>

                <p class="step-description">
                    {descricao}
                </p>
            </div>
        </div>
        """
    )


def mostrar_chamada(titulo: str) -> None:
    """Mostra uma chamada visual indicando a próxima ação."""

    st.html(
        f"""
        <div class="action-callout">
            <div class="action-callout-arrow">
                ↘
            </div>

            <div class="action-callout-title">
                {titulo}
            </div>
        </div>
        """
    )


def mostrar_rodape() -> None:
    """Mostra a identificação acadêmica da aplicação."""

    html_logo = obter_html_logo_ufpe()

    st.html(
        f"""
        <footer class="site-footer">
            {html_logo}

            <div class="footer-content">
                <strong>
                    Universidade Federal de Pernambuco
                </strong>

                <br>

                Engenharia Mecânica

                <br>

                Disciplina: Circuitos Fluídicos Mecânicos

                <br>

                Professor: Antonio Marques da Costa Soares Junior
            </div>
        </footer>
        """
    )