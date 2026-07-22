from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parents[1]
MIGRACAO = (
    RAIZ
    / "supabase"
    / "migrations"
    / "202607220001_controle_acesso.sql"
)

TABELAS = {
    "turmas",
    "usuarios",
    "matriculas",
    "convites",
    "reservas_analise",
    "movimentos_cota",
    "transferencias_master",
    "auditoria",
}


@pytest.fixture(scope="module")
def sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").casefold()


def test_migracao_existe() -> None:
    assert MIGRACAO.exists()


@pytest.mark.parametrize("tabela", sorted(TABELAS))
def test_migracao_cria_tabelas_do_dominio(sql: str, tabela: str) -> None:
    assert f"create table public.{tabela}" in sql


@pytest.mark.parametrize("tabela", sorted(TABELAS))
def test_todas_as_tabelas_expostas_usam_rls(sql: str, tabela: str) -> None:
    assert f"alter table public.{tabela} enable row level security" in sql


def test_banco_limita_master_a_um_registro(sql: str) -> None:
    assert "create unique index usuarios_master_unico_uk" in sql
    assert "where papel = 'master'" in sql


def test_cota_limitada_nao_pode_ser_negativa(sql: str) -> None:
    assert "constraint usuarios_cota_coerente_ck" in sql
    assert "analises_restantes >= 0" in sql
    assert "constraint usuarios_admin_ilimitado_ck" in sql


def test_convite_comum_nao_cria_master(sql: str) -> None:
    assert "constraint convites_nao_criam_master_ck" in sql
    assert "papel_destino <> 'master'" in sql


def test_reserva_possui_idempotencia_por_usuario(sql: str) -> None:
    assert "create unique index reservas_idempotencia_usuario_uk" in sql
    assert "(usuario_id, chave_idempotencia)" in sql


def test_auditoria_e_imutavel(sql: str) -> None:
    assert "create trigger auditoria_impedir_mutacao" in sql
    assert "before update or delete on public.auditoria" in sql


def test_cliente_autenticado_nao_recebe_escrita_direta(sql: str) -> None:
    for tabela in TABELAS:
        assert f"grant insert on table public.{tabela} to authenticated" not in sql
        assert f"grant update on table public.{tabela} to authenticated" not in sql
        assert f"grant delete on table public.{tabela} to authenticated" not in sql


def test_chave_administrativa_nao_esta_no_flutter() -> None:
    termos_proibidos = (
        "service_role",
        "supabase_service_role_key",
        "smtp_pass",
    )

    origens_cliente = (
        RAIZ / "mobile" / "lib",
        RAIZ / "mobile" / "android" / "app" / "src",
        RAIZ / "mobile" / "ios" / "Runner",
        RAIZ / "mobile" / "web",
    )

    for origem in origens_cliente:
        for caminho in origem.rglob("*"):
            if not caminho.is_file():
                continue

            try:
                conteudo = caminho.read_text(encoding="utf-8").casefold()
            except UnicodeDecodeError:
                continue

            assert not any(
                termo in conteudo
                for termo in termos_proibidos
            ), caminho
