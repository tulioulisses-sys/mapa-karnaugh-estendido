import pytest


@pytest.fixture
def sequencia_simples() -> str:
    return "A+, B+, B-, A-"


@pytest.fixture
def sequencia_multiposicao() -> str:
    return (
        "A+, B+ até b1, C+, B+ até b2, C-, "
        "B+ até b3, A-, B- até b0"
    )


@pytest.fixture
def sequencia_loop() -> str:
    return "A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-"

