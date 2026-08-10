from itertools import permutations

from src.engine import resolver


def _normalizar_produto(texto: str) -> tuple[str, ...]:
    return tuple(sorted(parte for parte in texto.replace(" ", "").split(".") if parte))


def _assert_produto(resultado, saida: str, esperado: str) -> None:
    obtido = resultado.equacoes_comandos.get(
        saida,
        resultado.equacoes.get(saida),
    )
    assert obtido is not None
    assert _normalizar_produto(obtido) == _normalizar_produto(esperado), (
        f"{saida}: esperado {esperado!r}, obtido {obtido!r}"
    )


def test_gabarito_professor_simultaneidade_tres_atuadores() -> None:
    resultado = resolver("(E+, A+, C+), (A-, C-), E-")

    assert resultado.memorias == ()
    _assert_produto(resultado, "E+", "S.e0")
    _assert_produto(resultado, "A+", "S.e0")
    _assert_produto(resultado, "C+", "S.e0")
    _assert_produto(resultado, "A-", "e1.a1.c1")
    _assert_produto(resultado, "C-", "e1.a1.c1")
    _assert_produto(resultado, "E-", "a0.c0")


def test_conclusao_simultanea_independe_da_ordem_das_acoes() -> None:
    for ordem in permutations(("E+", "A+", "C+")):
        sequencia = f"({', '.join(ordem)}), (A-, C-), E-"
        resultado = resolver(sequencia)

        _assert_produto(resultado, "A-", "e1.a1.c1")
        _assert_produto(resultado, "C-", "e1.a1.c1")
        _assert_produto(resultado, "E-", "a0.c0")


def test_regra_de_simultaneidade_nao_depende_dos_nomes() -> None:
    resultado = resolver("(P+, Q+, R+), (Q-, R-), P-")

    _assert_produto(resultado, "Q-", "p1.q1.r1")
    _assert_produto(resultado, "R-", "p1.q1.r1")
    _assert_produto(resultado, "P-", "q0.r0")
