from __future__ import annotations

from itertools import product

import pytest

from src.engine import resolver


def _eventos_atuadores(resultado) -> tuple[tuple[str, ...], ...]:
    return tuple(
        evento.saidas
        for evento in resultado.eventos
        if evento.tipo == "atuador"
    )


def _eventos_todos(resultado) -> tuple[tuple[str, ...], ...]:
    return tuple(evento.saidas for evento in resultado.eventos)


def test_gabarito_tres_atuadores_equacoes_minimas() -> None:
    resultado = resolver("A+, A-, E+, E-, C+, C-")

    assert _eventos_todos(resultado) == (
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
    assert resultado.equacoes == {
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


def test_gabarito_repeticao_com_simultaneidade() -> None:
    resultado = resolver("A+, E+, E-, C-, E+, E-, (A-, C+)")

    assert resultado.memorias == ("X",)
    assert _eventos_todos(resultado) == (
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
    assert resultado.equacoes_comandos == {
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
    assert resultado.equacoes == {
        "A+": "S.c1.x0",
        "E+": "a1.x0.c1 + c0.x",
        "X+": "e1.c1",
        "E-": "x.c1 + x0.c0",
        "C-": "e0.x",
        "X-": "e1.c0",
        "A-": "e0.c0.x0",
        "C+": "e0.c0.x0",
    }


def test_reducao_de_memoria_nao_depende_dos_nomes() -> None:
    resultado = resolver("P+, Q+, Q-, R-, Q+, Q-, (P-, R+)")

    assert resultado.memorias == ("X",)
    assert resultado.equacoes_comandos == {
        "P+": "S.r1.x0",
        "Q+(1)": "p1.x0.r1",
        "X+": "q1.r1",
        "Q-(1)": "x.r1",
        "R-": "q0.x",
        "Q+(2)": "r0.x",
        "X-": "q1.r0",
        "Q-(2)": "x0.r0",
        "P-": "q0.r0.x0",
        "R+": "q0.r0.x0",
    }


def test_regra_nao_depende_dos_nomes_dos_atuadores() -> None:
    resultado = resolver("P+, P-, Q+, Q-, R+, R-")

    assert resultado.equacoes == {
        "P+": "S.y0.x0",
        "X+": "p1",
        "P-": "x",
        "Q+": "p0.x.y0",
        "Y+": "q1",
        "Q-": "y",
        "R+": "q0.x.y",
        "X-": "r1",
        "R-": "x0",
        "Y-": "r0.x0",
    }


def _sequencia_por_alternancias(
    alternancias: tuple[int, ...],
) -> tuple[str, tuple[int, ...]]:
    nomes = ("A", "B", "C")
    estado = [0, 0, 0]
    acoes: list[str] = []

    for indice in alternancias:
        sentido = "+" if estado[indice] == 0 else "-"
        acoes.append(f"{nomes[indice]}{sentido}")
        estado[indice] = 1 - estado[indice]

    return ", ".join(acoes), tuple(estado)


def _ciclos_fechados_ate_seis_passos() -> tuple[str, ...]:
    sequencias: list[str] = []
    for quantidade in (2, 4, 6):
        for alternancias in product(range(3), repeat=quantidade):
            sequencia, estado_final = _sequencia_por_alternancias(
                alternancias
            )
            if estado_final == (0, 0, 0):
                sequencias.append(sequencia)
    return tuple(sequencias)


_CICLOS_FECHADOS = _ciclos_fechados_ate_seis_passos()


@pytest.mark.parametrize("sequencia", _CICLOS_FECHADOS)
def test_varredura_exaustiva_de_ciclos_validos(sequencia: str) -> None:
    resultado = resolver(sequencia)
    acoes_esperadas = tuple(
        (acao.strip(),) for acao in sequencia.split(",")
    )

    assert _eventos_atuadores(resultado) == acoes_esperadas
    assert len(resultado.validacoes) == 10
    assert "nenhum ponto perigoso permaneceu nos estados alcançáveis" in (
        resultado.validacoes
    )


@pytest.mark.parametrize(
    ("sequencia", "eventos_esperados"),
    (
        (
            "(A+, B+), (A-, B-)",
            (("A+", "B+"), ("A-", "B-")),
        ),
        (
            "A+, (B+, C+), (B-, C-), A-",
            (("A+",), ("B+", "C+"), ("B-", "C-"), ("A-",)),
        ),
        (
            "(A+, B+), C+, (A-, B-), C-",
            (("A+", "B+"), ("C+",), ("A-", "B-"), ("C-",)),
        ),
        (
            "A+, B+, C+, (C-, B-), B+, (B-, A-)",
            (
                ("A+",),
                ("B+",),
                ("C+",),
                ("C-", "B-"),
                ("B+",),
                ("B-", "A-"),
            ),
        ),
    ),
)
def test_simultaneidades_fora_do_gabarito(
    sequencia: str,
    eventos_esperados: tuple[tuple[str, ...], ...],
) -> None:
    resultado = resolver(sequencia)
    assert _eventos_atuadores(resultado) == eventos_esperados
