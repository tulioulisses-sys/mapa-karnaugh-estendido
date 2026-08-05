from src.engine import resolver


def eventos_da_sequencia(sequencia: str):
    resultado = resolver(sequencia)
    return tuple(evento.saidas for evento in resultado.eventos)


def test_posicao_memorias_a_a_e_e_c_c():
    assert eventos_da_sequencia(
        "A+, A-, E+, E-, C+, C-"
    ) == (
        ("A+",),
        ("X+",),
        ("A-",),
        ("E+",),
        ("Y+",),
        ("E-",),
        ("C+",),
        ("X-",),
        ("C-",),
        ("Y-",),
    )


def test_posicao_memorias_com_repeticao_de_e():
    assert eventos_da_sequencia(
        "A+, E+, E-, C-, E+, E-, (A-, C+)"
    ) == (
        ("A+",),
        ("E+",),
        ("X+",),
        ("E-",),
        ("C-",),
        ("Y+",),
        ("E+",),
        ("X-",),
        ("E-",),
        ("A-", "C+"),
        ("Y-",),
    )
