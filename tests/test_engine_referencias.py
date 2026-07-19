from src.engine import validar_exemplos_referencia


def test_exemplos_documentados_continuam_validos() -> None:
    validacoes = validar_exemplos_referencia()

    assert len(validacoes) == 6
    assert all("validad" in mensagem.lower() for mensagem in validacoes)
