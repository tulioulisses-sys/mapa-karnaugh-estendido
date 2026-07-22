from __future__ import annotations

from dataclasses import replace
from enum import StrEnum

from .modelos import (
    AjusteCota,
    CotaAnalises,
    EstadoConta,
    PapelUsuario,
    UsuarioAcesso,
)


class Permissao(StrEnum):
    REALIZAR_ANALISE = "realizar_analise"
    VISUALIZAR_PAINEL = "visualizar_painel"
    CONVIDAR_USUARIOS = "convidar_usuarios"
    APROVAR_USUARIOS = "aprovar_usuarios"
    SUSPENDER_USUARIOS = "suspender_usuarios"
    REVOGAR_USUARIOS = "revogar_usuarios"
    AJUSTAR_COTAS = "ajustar_cotas"
    GERENCIAR_TURMAS = "gerenciar_turmas"
    CONSULTAR_AUDITORIA = "consultar_auditoria"
    GERENCIAR_SUBMASTERS = "gerenciar_submasters"
    TRANSFERIR_PROPRIEDADE = "transferir_propriedade"


_PERMISSOES_USUARIO = frozenset(
    {
        Permissao.REALIZAR_ANALISE,
    }
)

_PERMISSOES_SUBMASTER = frozenset(
    {
        Permissao.REALIZAR_ANALISE,
        Permissao.VISUALIZAR_PAINEL,
        Permissao.CONVIDAR_USUARIOS,
        Permissao.APROVAR_USUARIOS,
        Permissao.SUSPENDER_USUARIOS,
        Permissao.REVOGAR_USUARIOS,
        Permissao.AJUSTAR_COTAS,
        Permissao.GERENCIAR_TURMAS,
        Permissao.CONSULTAR_AUDITORIA,
    }
)

_PERMISSOES_MASTER = frozenset(
    {
        *_PERMISSOES_SUBMASTER,
        Permissao.GERENCIAR_SUBMASTERS,
        Permissao.TRANSFERIR_PROPRIEDADE,
    }
)


def permissoes_do_usuario(
    usuario: UsuarioAcesso,
) -> frozenset[Permissao]:
    if usuario.estado is not EstadoConta.ATIVO:
        return frozenset()

    if usuario.papel is PapelUsuario.MASTER:
        return _PERMISSOES_MASTER

    if usuario.papel is PapelUsuario.SUBMASTER:
        return _PERMISSOES_SUBMASTER

    return _PERMISSOES_USUARIO


def tem_permissao(
    usuario: UsuarioAcesso,
    permissao: Permissao,
) -> bool:
    return permissao in permissoes_do_usuario(usuario)


def pode_gerenciar_usuario(
    ator: UsuarioAcesso,
    alvo: UsuarioAcesso,
) -> bool:
    """Protege master, submasters e o próprio ator de alterações indevidas."""

    if ator.estado is not EstadoConta.ATIVO or ator.id == alvo.id:
        return False

    if ator.papel is PapelUsuario.MASTER:
        return alvo.papel is not PapelUsuario.MASTER

    if ator.papel is PapelUsuario.SUBMASTER:
        return alvo.papel is PapelUsuario.USUARIO

    return False


def pode_convidar_para_papel(
    ator: UsuarioAcesso,
    papel_destino: PapelUsuario,
) -> bool:
    if papel_destino is PapelUsuario.MASTER:
        return False

    if papel_destino is PapelUsuario.SUBMASTER:
        return tem_permissao(ator, Permissao.GERENCIAR_SUBMASTERS)

    return tem_permissao(ator, Permissao.CONVIDAR_USUARIOS)


def pode_ajustar_cota(
    ator: UsuarioAcesso,
    alvo: UsuarioAcesso,
) -> bool:
    return (
        alvo.papel is PapelUsuario.USUARIO
        and tem_permissao(ator, Permissao.AJUSTAR_COTAS)
        and pode_gerenciar_usuario(ator, alvo)
    )


def pode_realizar_analise(usuario: UsuarioAcesso) -> bool:
    return (
        tem_permissao(usuario, Permissao.REALIZAR_ANALISE)
        and usuario.cota.disponivel
    )


def registrar_consumo(usuario: UsuarioAcesso) -> UsuarioAcesso:
    """Calcula o novo saldo; a persistência fará isso em transação atômica."""

    if usuario.estado is not EstadoConta.ATIVO:
        raise PermissionError("A conta não está ativa.")

    return replace(
        usuario,
        cota=usuario.cota.consumir(),
    )


def ajustar_cota(
    usuario: UsuarioAcesso,
    operacao: AjusteCota,
    quantidade: int,
) -> UsuarioAcesso:
    if usuario.papel is not PapelUsuario.USUARIO:
        raise ValueError(
            "A cota numérica só pode ser aplicada a usuários comuns."
        )

    if operacao is AjusteCota.DEFINIR:
        nova_cota = usuario.cota.definir(quantidade)
    elif operacao is AjusteCota.ADICIONAR:
        nova_cota = usuario.cota.adicionar(quantidade)
    else:
        raise ValueError("A operação de ajuste de cota é inválida.")

    return replace(usuario, cota=nova_cota)


def definir_acesso_ilimitado(
    usuario: UsuarioAcesso,
) -> UsuarioAcesso:
    return replace(
        usuario,
        cota=CotaAnalises.ilimitada(),
    )
