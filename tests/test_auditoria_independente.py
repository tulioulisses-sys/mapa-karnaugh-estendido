from __future__ import annotations

from itertools import permutations

import pytest

from src.engine import resolver


def normalizar_produto(texto: str) -> tuple[str, ...]:
    texto = texto.strip().replace(" ", "")
    return tuple(sorted(parte for parte in texto.split(".") if parte))


def normalizar_equacao(texto: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        sorted(
            normalizar_produto(parcela)
            for parcela in texto.split("+")
            if parcela.strip()
        )
    )


def assert_equacao(resultado, saida: str, esperado: str) -> None:
    obtido = resultado.equacoes_comandos.get(
        saida,
        resultado.equacoes.get(saida),
    )
    assert obtido is not None, f"Equação ausente para {saida}"
    assert normalizar_equacao(obtido) == normalizar_equacao(esperado), (
        f"{saida}: esperado {esperado!r}, obtido {obtido!r}"
    )


def eventos(resultado) -> tuple[tuple[str, ...], ...]:
    return tuple(evento.saidas for evento in resultado.eventos)


def assinatura(resultado) -> tuple:
    return (
        resultado.memorias,
        eventos(resultado),
        tuple(
            sorted(
                (chave, normalizar_equacao(valor))
                for chave, valor in resultado.equacoes.items()
            )
        ),
        tuple(
            sorted(
                (chave, normalizar_equacao(valor))
                for chave, valor in resultado.equacoes_comandos.items()
            )
        ),
        tuple(sorted(resultado.equacoes_memorias.items())),
    )


def test_gabarito_a_a_e_e_c_c_completo() -> None:
    resultado = resolver("A+, A-, E+, E-, C+, C-")

    assert resultado.memorias == ("X", "Y")
    assert eventos(resultado) == (
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

    esperado = {
        "A+": "S.y0.x0",
        "X+": "a1",
        "A-": "x",
        "E+": "a0.x.y0",
        "Y+": "e1",
        "E-": "y",
        "C+": "e0.x.y",
        "X-": "c1",
        "C-": "x0",
        "Y-": "c0.x0",
    }

    for saida, equacao in esperado.items():
        assert_equacao(resultado, saida, equacao)


def test_gabarito_repeticao_e_uma_memoria_completo() -> None:
    resultado = resolver(
        "A+, E+, E-, C-, E+, E-, (A-, C+)"
    )

    assert resultado.memorias == ("X",)
    assert eventos(resultado) == (
        ("A+",),
        ("E+",),
        ("X+",),
        ("E-",),
        ("C-",),
        ("E+",),
        ("X-",),
        ("E-",),
        ("A-", "C+"),
    )

    esperado = {
        "A+": "S.c1.x0",
        "E+(1)": "a1.x0.c1",
        "X+": "e1.c1",
        "E-(1)": "x.c1",
        "C-": "e0.x",
        "E+(2)": "c0.x",
        "X-": "e1.c0",
        "E-(2)": "x0.c0",
        "A-": "e0.c0.x0",
        "C+": "e0.c0.x0",
    }

    for saida, equacao in esperado.items():
        assert_equacao(resultado, saida, equacao)

    assert_equacao(
        resultado,
        "E+",
        "a1.x0.c1 + c0.x",
    )
    assert_equacao(
        resultado,
        "E-",
        "x.c1 + x0.c0",
    )


def test_simultaneidade_preservada() -> None:
    resultado = resolver(
        "A+, E+, E-, C-, E+, E-, (A-, C+)"
    )

    simultaneos = [
        evento
        for evento in resultado.eventos
        if evento.saidas == ("A-", "C+")
    ]

    assert len(simultaneos) == 1
    assert_equacao(resultado, "A-", "e0.c0.x0")
    assert_equacao(resultado, "C+", "e0.c0.x0")


def test_equacoes_fisicas_sao_soma_das_ocorrencias() -> None:
    resultado = resolver(
        "A+, E+, E-, C-, E+, E-, (A-, C+)"
    )

    assert normalizar_equacao(resultado.equacoes["E+"]) == (
        normalizar_equacao(
            resultado.equacoes_comandos["E+(1)"]
            + " + "
            + resultado.equacoes_comandos["E+(2)"]
        )
    )

    assert normalizar_equacao(resultado.equacoes["E-"]) == (
        normalizar_equacao(
            resultado.equacoes_comandos["E-(1)"]
            + " + "
            + resultado.equacoes_comandos["E-(2)"]
        )
    )


@pytest.mark.parametrize(
    "sequencia",
    [
        "A+, B+, B-, A-",
        "A+, A-, B+, B-, C+, C-",
        "A+, B+, B-, C+, B+, B-, C-, A-",
        "A+, B+, C+, (C-, B-), B+, (B-, A-)",
        "A+, A-, E-, C+, (E+, C-)",
        "(E+, A+, C+), (A-, C-), E-",
        "P+, P-, Q+, Q-, R+, R-",
        "M+, N+, N-, M-",
    ],
)
def test_resultado_deterministico(sequencia: str) -> None:
    primeiro = resolver(sequencia)
    segundo = resolver(sequencia)

    assert assinatura(primeiro) == assinatura(segundo)


def intercalacoes_validas(
    atuadores: tuple[str, ...],
) -> list[str]:
    movimentos = tuple(
        movimento
        for atuador in atuadores
        for movimento in (f"{atuador}+", f"{atuador}-")
    )

    validas: list[str] = []

    for ordem in permutations(movimentos):
        correta = all(
            ordem.index(f"{atuador}+") <
            ordem.index(f"{atuador}-")
            for atuador in atuadores
        )

        if correta:
            validas.append(", ".join(ordem))

    return validas


SEQUENCIAS_GERADAS = (
    intercalacoes_validas(("A", "B"))
    + intercalacoes_validas(("P", "Q"))
    + intercalacoes_validas(("A", "B", "C"))
)


@pytest.mark.parametrize("sequencia", SEQUENCIAS_GERADAS)
def test_sequencias_geradas_nao_travam_e_sao_deterministicas(
    sequencia: str,
) -> None:
    primeiro = resolver(sequencia)
    segundo = resolver(sequencia)

    assert primeiro.eventos
    assert assinatura(primeiro) == assinatura(segundo)

    for evento in primeiro.eventos:
        saidas = set(evento.saidas)

        for memoria in primeiro.memorias:
            assert not {
                f"{memoria}+",
                f"{memoria}-",
            }.issubset(saidas)


def test_renomear_atuadores_preserva_quantidade_de_memorias() -> None:
    original = resolver("A+, A-, E+, E-, C+, C-")
    renomeado = resolver("P+, P-, Q+, Q-, R+, R-")

    assert len(original.memorias) == len(renomeado.memorias)
    assert len(original.eventos) == len(renomeado.eventos)

    assert tuple(evento.tipo for evento in original.eventos) == tuple(
        evento.tipo for evento in renomeado.eventos
    )


def test_renomear_caso_repetido_preserva_estrutura() -> None:
    original = resolver(
        "A+, E+, E-, C-, E+, E-, (A-, C+)"
    )
    renomeado = resolver(
        "P+, Q+, Q-, R-, Q+, Q-, (P-, R+)"
    )

    assert len(original.memorias) == 1
    assert len(renomeado.memorias) == 1

    assert tuple(evento.tipo for evento in original.eventos) == tuple(
        evento.tipo for evento in renomeado.eventos
    )

    assert tuple(len(evento.saidas) for evento in original.eventos) == tuple(
        len(evento.saidas) for evento in renomeado.eventos
    )
