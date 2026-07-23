from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parents[1]
MIGRACAO = (
    RAIZ
    / "supabase"
    / "migrations"
    / "202607220002_cadastro_e_bootstrap.sql"
)


@pytest.fixture(scope="module")
def sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").casefold()


def test_migracao_de_cadastro_existe() -> None:
    assert MIGRACAO.exists()


def test_corrige_coluna_de_atualizacao_dos_convites(sql: str) -> None:
    assert "rename column atualizado_em to atualizada_em" in sql


def test_auth_cria_perfil_publico_automaticamente(sql: str) -> None:
    assert "create trigger auth_usuario_criado" in sql
    assert "after insert on auth.users" in sql
    assert "insert into public.usuarios" in sql


def test_confirmacao_de_email_processa_convite(sql: str) -> None:
    assert "create trigger auth_email_confirmado" in sql
    assert "after update of email_confirmed_at on auth.users" in sql
    assert "new.email_confirmed_at is not null" in sql
    assert "set estado = 'aceito'" in sql
    assert "set papel = v_convite.papel_destino" in sql


def test_cadastro_espontaneo_aguarda_aprovacao(sql: str) -> None:
    assert "v_estado_inicial := 'aguardando_aprovacao'" in sql


def test_convite_so_e_aceito_para_o_mesmo_email(sql: str) -> None:
    assert "lower(btrim(convite.email)) = v_email" in sql
    assert "convite.expira_em > now()" in sql


def test_bootstrap_exige_email_confirmado_e_master_inexistente(
    sql: str,
) -> None:
    assert "create or replace function public.bootstrap_primeiro_master" in sql
    assert "where papel = 'master'" in sql
    assert "if v_email_confirmado_em is null" in sql
    assert "pg_advisory_xact_lock" in sql


def test_bootstrap_e_exclusivo_do_backend(sql: str) -> None:
    assert (
        "revoke all on function public.bootstrap_primeiro_master(text)"
        in sql
    )
    assert "from public, anon, authenticated" in sql
    assert (
        "grant execute on function public.bootstrap_primeiro_master(text)"
        in sql
    )
    assert "to service_role" in sql
