import pytest

from src.solver import analisar_entrada


def test_interpreta_sequencia_simples(sequencia_simples: str) -> None:
    resultado = analisar_entrada(sequencia_simples)

    assert resultado["atuadores"] == ["A", "B"]
    assert resultado["etapas"] == [["A+"], ["B+"], ["B-"], ["A-"]]
    assert resultado["sensores_iniciais"] == {"A": "a0", "B": "b0"}
    assert resultado["quantidade_etapas"] == 4


def test_interpreta_movimentos_simultaneos() -> None:
    resultado = analisar_entrada("A+, (B+, C+), C-, B-, A-")

    assert resultado["etapas"][1] == ["B+", "C+"]
    assert resultado["quantidade_etapas"] == 5


@pytest.mark.parametrize(
    ("sequencia", "mensagem"),
    [
        ("", "não pode estar vazia"),
        ("A+, B", "Movimento inválido"),
        ("A+, A+", "já está no sensor a1"),
        (
            "A+, (B+, B-), A-",
            "Um mesmo atuador não pode aparecer duas vezes",
        ),
    ],
)
def test_rejeita_entradas_invalidas(sequencia: str, mensagem: str) -> None:
    with pytest.raises(ValueError, match=mensagem):
        analisar_entrada(sequencia)

