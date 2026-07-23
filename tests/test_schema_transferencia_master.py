from pathlib import Path

import pytest


MIGRACAO = (
    Path(__file__).parents[1]
    / "supabase"
    / "migrations"
    / "202607230003_transferencia_master.sql"
)


@pytest.fixture(scope="module")
def sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").casefold()


@pytest.mark.parametrize(
    "funcao",
    (
        "iniciar_transferencia_master",
        "obter_transferencia_master",
        "cancelar_transferencia_master",
        "aceitar_transferencia_master",
    ),
)
def test_cria_fluxo_completo_de_transferencia(
    sql: str,
    funcao: str,
) -> None:
    assert f"create or replace function public.{funcao}" in sql


def test_funcoes_sao_protegidas_pelo_backend(sql: str) -> None:
    assert sql.count("security definer") == 4
    assert sql.count("to service_role") == 4
    assert ") to authenticated;" not in sql


def test_somente_master_ativo_inicia_e_cancela(sql: str) -> None:
    assert sql.count("papel = 'master'") >= 2
    assert sql.count("estado = 'ativo'") >= 2
    assert "somente o master ativo pode iniciar" in sql
    assert "somente o master ativo pode cancelar" in sql


def test_destinatario_precisa_ser_o_email_confirmado(sql: str) -> None:
    assert "somente o destinatário pode aceitar" in sql
    assert "email_confirmed_at" in sql
    assert "o destinatário precisa confirmar o email" in sql


def test_troca_master_e_atomica_e_preserva_antigo_como_submaster(
    sql: str,
) -> None:
    assert "pg_advisory_xact_lock" in sql
    rebaixamento = sql.index("set papel = 'submaster'")
    promocao = sql.index("set papel = 'master'", rebaixamento)
    aceite = sql.index("set estado = 'aceita'", promocao)
    assert rebaixamento < promocao < aceite
    assert "'master_anterior_papel', 'submaster'" in sql


def test_operacoes_geram_auditoria(sql: str) -> None:
    assert "'iniciar_transferencia_master'" in sql
    assert "'cancelar_transferencia_master'" in sql
    assert "'aceitar_transferencia_master'" in sql
    assert sql.count("insert into public.auditoria") == 3
