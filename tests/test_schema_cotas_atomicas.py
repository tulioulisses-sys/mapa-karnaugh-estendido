from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parents[1]
MIGRACAO = (
    RAIZ
    / "supabase"
    / "migrations"
    / "202607220003_cotas_atomicas.sql"
)


@pytest.fixture(scope="module")
def sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").casefold()


def test_migracao_de_cotas_atomicas_existe() -> None:
    assert MIGRACAO.exists()


@pytest.mark.parametrize(
    "funcao",
    (
        "reservar_analise",
        "consumir_reserva_analise",
        "estornar_reserva_analise",
        "expirar_reservas_analise",
    ),
)
def test_cria_operacoes_do_ciclo_da_reserva(sql: str, funcao: str) -> None:
    assert f"create or replace function public.{funcao}" in sql


def test_reserva_bloqueia_usuario_antes_de_reduzir_saldo(sql: str) -> None:
    inicio = sql.index("create or replace function public.reservar_analise")
    fim = sql.index("create or replace function public.consumir_reserva_analise")
    reserva = sql[inicio:fim]

    assert "from public.usuarios as usuario" in reserva
    assert "for update" in reserva
    assert reserva.index("for update") < reserva.index(
        "set analises_restantes = v_saldo_posterior"
    )


def test_repeticao_da_chave_nao_desconta_novamente(sql: str) -> None:
    assert "reserva.chave_idempotencia = p_chave_idempotencia" in sql
    assert "'idempotente', true" in sql


def test_usuario_comum_precisa_de_matricula_e_turma_ativas(sql: str) -> None:
    assert "if v_usuario.papel = 'usuario'" in sql
    assert "from public.matriculas as matricula" in sql
    assert "and matricula.ativa" in sql
    assert "and turma.ativa" in sql


def test_reserva_limitada_reduz_uma_unidade(sql: str) -> None:
    assert "if v_usuario.acesso = 'limitado'" in sql
    assert "v_saldo_posterior := v_saldo_anterior - 1" in sql
    assert "'reservar'" in sql


def test_estorno_e_expiracao_devolvem_uma_unidade(sql: str) -> None:
    assert sql.count("v_saldo_posterior := v_saldo_anterior + 1") == 2
    assert "set estado = 'estornada'" in sql
    assert "set estado = 'expirada'" in sql


def test_consumo_e_estorno_sao_idempotentes(sql: str) -> None:
    assert "if v_reserva.estado = 'consumida'" in sql
    assert "if v_reserva.estado in ('estornada', 'expirada')" in sql


def test_funcoes_de_cota_sao_exclusivas_do_backend(sql: str) -> None:
    assinaturas = (
        "reservar_analise(uuid, text, uuid)",
        "consumir_reserva_analise(uuid)",
        "estornar_reserva_analise(uuid, text)",
        "expirar_reservas_analise(integer)",
    )

    for assinatura in assinaturas:
        assert f"revoke all on function public.{assinatura}" in sql
        assert f"grant execute on function public.{assinatura}" in sql

    assert sql.count("from public, anon, authenticated") == 4
    assert sql.count("to service_role") == 4
