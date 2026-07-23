import json
from pathlib import Path

from tools.gerar_referencias_mobile import (
    CAMINHO_PADRAO,
    construir_referencias,
)


def test_referencias_mobile_estao_atualizadas() -> None:
    assert CAMINHO_PADRAO.exists()

    referencias_salvas = json.loads(
        Path(CAMINHO_PADRAO).read_text(encoding="utf-8")
    )

    assert referencias_salvas == construir_referencias()


def test_referencias_cobrem_recursos_principais() -> None:
    referencias = construir_referencias()
    ids = {caso["id"] for caso in referencias["casos"]}

    assert ids == {
        "simples",
        "simultaneo",
        "multiposicao",
        "loop",
    }
