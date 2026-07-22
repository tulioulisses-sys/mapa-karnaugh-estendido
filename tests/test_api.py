from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health() -> None:
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"
    assert resposta.json()["api_version"] == "1.0.0"
    assert resposta.headers["x-content-type-options"] == "nosniff"


def test_analisa_sequencia() -> None:
    resposta = client.post(
        "/api/v1/analises",
        json={"sequencia": "A+, B+, B-, A-"},
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["atuadores"] == ["A", "B"]
    assert dados["quantidade_etapas"] == 4
    assert "projeto" not in dados


def test_resolve_com_mapa() -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        json={"sequencia": "A+, B+, B-, A-"},
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["memorias"] == ["X"]
    assert dados["quantidade_memorias"] == 1
    assert dados["mapa_svg"].startswith("<svg")
    assert dados["mapa_largura"] > 0
    assert resposta.headers["cache-control"] == "no-store"


def test_pode_omitir_mapa() -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        json={
            "sequencia": "A+, B+, B-, A-",
            "incluir_mapa": False,
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["mapa_svg"] is None


def test_padroniza_erro_do_motor() -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        json={"sequencia": "A+, B"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SEQUENCIA_INVALIDA"
    assert resposta.json()["erro"]["campo"] == "sequencia"


def test_rejeita_campo_desconhecido() -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        json={
            "sequencia": "A+, B+, B-, A-",
            "administrador": True,
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_limita_tamanho_da_sequencia() -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        json={"sequencia": "A" * 20_001},
    )

    assert resposta.status_code == 413
    assert resposta.json()["erro"]["codigo"] == "ENTRADA_MUITO_GRANDE"


def test_openapi_publica_endpoints_v1() -> None:
    resposta = client.get("/openapi.json")

    assert resposta.status_code == 200
    caminhos = resposta.json()["paths"]
    assert "/health" in caminhos
    assert "/api/v1/analises" in caminhos
    assert "/api/v1/resolucoes" in caminhos

