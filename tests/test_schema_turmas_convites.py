from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
MIGRACAO = (
    RAIZ
    / "supabase"
    / "migrations"
    / "202607230002_turmas_convites.sql"
)


def _sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").casefold()


def test_convite_guarda_perfil_e_cota_inicial() -> None:
    sql = _sql()

    assert "add column acesso_destino" in sql
    assert "add column analises_iniciais" in sql
    assert "convites_cota_inicial_coerente_ck" in sql
    assert "v_convite.acesso_destino" in sql
    assert "v_convite.analises_iniciais" in sql


def test_criacao_em_lote_e_limitada_e_auditada() -> None:
    sql = _sql()

    assert "function public.criar_convites_em_lote" in sql
    assert "cardinality(p_emails) > 300" in sql
    assert "'criar_convite'" in sql
    assert "'magic_link'" in sql
    assert "'confirmacao'" in sql


def test_funcoes_administrativas_sao_exclusivas_do_backend() -> None:
    sql = _sql()

    assert "from public, anon, authenticated" in sql
    assert "to service_role" in sql
    assert "function public.listar_turmas_administracao" in sql
    assert "function public.listar_convites_administracao" in sql
    assert "function public.cancelar_convite" in sql
