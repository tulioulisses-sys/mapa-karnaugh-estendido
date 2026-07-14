import streamlit as st

from src.interface import (
    carregar_css,
    mostrar_rodape,
)


st.set_page_config(
    page_title="Comandos Fluídicos Sequenciais",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stToolbar"] a[href*="github.com"],
    [data-testid="stToolbar"] a[aria-label*="GitHub"],
    [data-testid="stToolbar"] a[title*="GitHub"],
    [data-testid="stToolbar"] button[aria-label*="GitHub"],
    [data-testid="stToolbar"] button[title*="GitHub"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

carregar_css()

paginas = [
    st.Page(
        "pages/1_Resolver.py",
        title="Resolver",
        icon="⚙️",
        default=True,
    ),
    st.Page(
        "pages/2_Sobre_o_metodo.py",
        title="Sobre o método",
        icon="📘",
    ),
]

pagina_atual = st.navigation(
    paginas,
    position="top",
)

pagina_atual.run()

mostrar_rodape()