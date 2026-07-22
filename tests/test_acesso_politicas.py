import pytest

from api.acesso import (
    AjusteCota,
    ConviteAcesso,
    CotaAnalises,
    CotaEsgotadaError,
    EstadoConta,
    PapelUsuario,
    Permissao,
    UsuarioAcesso,
    ajustar_cota,
    pode_ajustar_cota,
    pode_convidar_para_papel,
    pode_gerenciar_usuario,
    pode_realizar_analise,
    registrar_consumo,
    tem_permissao,
)


def _usuario(
    identificador: str,
    papel: PapelUsuario = PapelUsuario.USUARIO,
    estado: EstadoConta = EstadoConta.ATIVO,
    cota: CotaAnalises | None = None,
) -> UsuarioAcesso:
    return UsuarioAcesso(
        id=identificador,
        email=f"{identificador}@example.com",
        papel=papel,
        estado=estado,
        cota=cota or CotaAnalises.ilimitada(),
        turma_id="2026.1",
    )


def test_normaliza_email_de_usuario_e_convite() -> None:
    usuario = UsuarioAcesso(
        id="u1",
        email="  Aluno@Example.COM ",
        papel=PapelUsuario.USUARIO,
        estado=EstadoConta.ATIVO,
        cota=CotaAnalises.limitada(1),
    )
    convite = ConviteAcesso(
        id="c1",
        email="  Convidado@Example.COM ",
        convidado_por="master-1",
    )

    assert usuario.email == "aluno@example.com"
    assert convite.email == "convidado@example.com"


def test_master_possui_controle_superior() -> None:
    master = _usuario("master", PapelUsuario.MASTER)
    submaster = _usuario("submaster", PapelUsuario.SUBMASTER)
    aluno = _usuario("aluno")

    assert tem_permissao(master, Permissao.TRANSFERIR_PROPRIEDADE)
    assert tem_permissao(master, Permissao.GERENCIAR_SUBMASTERS)
    assert pode_gerenciar_usuario(master, submaster)
    assert not pode_gerenciar_usuario(master, master)
    assert pode_ajustar_cota(master, aluno)
    assert pode_convidar_para_papel(master, PapelUsuario.SUBMASTER)
    assert not pode_convidar_para_papel(master, PapelUsuario.MASTER)


def test_submaster_administra_aluno_mas_nao_administradores() -> None:
    master = _usuario("master", PapelUsuario.MASTER)
    submaster = _usuario("submaster", PapelUsuario.SUBMASTER)
    outro_submaster = _usuario("submaster-2", PapelUsuario.SUBMASTER)
    aluno = _usuario("aluno")

    assert tem_permissao(submaster, Permissao.AJUSTAR_COTAS)
    assert not tem_permissao(submaster, Permissao.GERENCIAR_SUBMASTERS)
    assert not tem_permissao(submaster, Permissao.TRANSFERIR_PROPRIEDADE)
    assert pode_gerenciar_usuario(submaster, aluno)
    assert not pode_gerenciar_usuario(submaster, outro_submaster)
    assert not pode_gerenciar_usuario(submaster, master)
    assert pode_ajustar_cota(submaster, aluno)
    assert pode_convidar_para_papel(submaster, PapelUsuario.USUARIO)
    assert not pode_convidar_para_papel(
        submaster,
        PapelUsuario.SUBMASTER,
    )


@pytest.mark.parametrize(
    "estado",
    [
        EstadoConta.CONVIDADO,
        EstadoConta.AGUARDANDO_APROVACAO,
        EstadoConta.SUSPENSO,
        EstadoConta.REVOGADO,
    ],
)
def test_conta_inativa_nao_recebe_permissoes(estado: EstadoConta) -> None:
    usuario = _usuario("aluno", estado=estado)

    assert not pode_realizar_analise(usuario)
    assert not tem_permissao(usuario, Permissao.REALIZAR_ANALISE)


def test_acesso_limitado_consumido_ate_zero() -> None:
    usuario = _usuario(
        "aluno",
        cota=CotaAnalises.limitada(2),
    )

    usuario = registrar_consumo(usuario)
    usuario = registrar_consumo(usuario)

    assert usuario.cota.restantes == 0
    assert not pode_realizar_analise(usuario)

    with pytest.raises(CotaEsgotadaError):
        registrar_consumo(usuario)


def test_acesso_ilimitado_nao_reduz_saldo() -> None:
    usuario = _usuario("aluno")

    depois = registrar_consumo(usuario)

    assert depois.cota == CotaAnalises.ilimitada()
    assert pode_realizar_analise(depois)


def test_definir_e_adicionar_cota_sao_operacoes_diferentes() -> None:
    usuario = _usuario(
        "aluno",
        cota=CotaAnalises.limitada(3),
    )

    definido = ajustar_cota(usuario, AjusteCota.DEFINIR, 1)
    adicionado = ajustar_cota(usuario, AjusteCota.ADICIONAR, 1)

    assert definido.cota.restantes == 1
    assert adicionado.cota.restantes == 4


def test_adicionar_cota_nao_rebaixa_acesso_ilimitado() -> None:
    usuario = _usuario("aluno")

    ajustado = ajustar_cota(usuario, AjusteCota.ADICIONAR, 1)

    assert ajustado.cota == CotaAnalises.ilimitada()


def test_master_e_submaster_precisam_ser_ilimitados() -> None:
    with pytest.raises(ValueError, match="acesso ilimitado"):
        _usuario(
            "submaster",
            papel=PapelUsuario.SUBMASTER,
            cota=CotaAnalises.limitada(3),
        )


def test_convite_nao_pode_criar_master_diretamente() -> None:
    with pytest.raises(ValueError, match="fluxo próprio"):
        ConviteAcesso(
            id="c1",
            email="novo@example.com",
            convidado_por="master-1",
            papel_destino=PapelUsuario.MASTER,
        )
