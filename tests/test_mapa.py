from xml.etree import ElementTree

from src.mapa import gerar_mapa_svg
from src.solver import resolver_site


def test_gera_svg_valido(sequencia_simples: str) -> None:
    resultado = resolver_site(sequencia_simples)
    mapa = gerar_mapa_svg(resultado)
    raiz = ElementTree.fromstring(mapa.svg)

    assert raiz.tag.endswith("svg")
    assert mapa.largura > 0
    assert mapa.altura > 0
    assert "Mapa de Karnaugh Estendido" in mapa.svg
    assert "A+" in mapa.svg
    assert "X+" in mapa.svg


def test_limite_de_celulas_produz_aviso(sequencia_simples: str) -> None:
    resultado = resolver_site(sequencia_simples)
    mapa = gerar_mapa_svg(resultado, limite_celulas=1)

    assert "Mapa muito grande para exibição" in mapa.svg
    ElementTree.fromstring(mapa.svg)

