import pytest

from src.solver import resolver_site


def test_resolve_equacoes_da_referencia_simples(
    sequencia_simples: str,
) -> None:
    resultado = resolver_site(sequencia_simples)

    assert resultado["memorias"] == ["X"]
    assert resultado["quantidade_memorias"] == 1
    assert resultado["equacoes_comandos"] == {
        "A+": "S.x0",
        "B+": "a1.x0",
        "X+": "b1",
        "B-": "x",
        "A-": "b0.x",
        "X-": "a0",
    }
    assert resultado["equacoes_memorias"] == {"X": "(b1 + x).¬(a0)"}


def test_resultado_preserva_invariantes_de_seguranca(
    sequencia_simples: str,
) -> None:
    resultado = resolver_site(sequencia_simples)
    validacoes = " ".join(resultado["validacoes"])

    assert "nenhum ponto perigoso permaneceu" in validacoes
    assert "nenhum comando e contracomando ficam ativos" in validacoes
    assert "somente uma memória muda" in validacoes
    assert "SET, RESET e retenção" in validacoes


def test_ciclo_continuo_exige_fechamento() -> None:
    with pytest.raises(ValueError, match="estado final deve ser igual"):
        resolver_site("A+", ciclo_continuo=True)

