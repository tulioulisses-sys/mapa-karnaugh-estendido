from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self


class PapelUsuario(StrEnum):
    """Função permanente do usuário dentro da aplicação."""

    MASTER = "master"
    SUBMASTER = "submaster"
    USUARIO = "usuario"


class EstadoConta(StrEnum):
    """Estado do ciclo de vida da conta."""

    CONVIDADO = "convidado"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    REVOGADO = "revogado"


class EstadoConvite(StrEnum):
    PENDENTE = "pendente"
    ACEITO = "aceito"
    EXPIRADO = "expirado"
    CANCELADO = "cancelado"


class TipoAcesso(StrEnum):
    ILIMITADO = "ilimitado"
    LIMITADO = "limitado"


class AjusteCota(StrEnum):
    """Operações distintas disponíveis no painel administrativo."""

    DEFINIR = "definir"
    ADICIONAR = "adicionar"


class CotaEsgotadaError(ValueError):
    pass


def _texto_obrigatorio(valor: str, descricao: str) -> str:
    normalizado = str(valor).strip()
    if not normalizado:
        raise ValueError(f"{descricao} não pode estar vazio.")
    return normalizado


def _email_normalizado(email: str) -> str:
    normalizado = _texto_obrigatorio(email, "O email").casefold()
    if "@" not in normalizado:
        raise ValueError("O email informado é inválido.")
    return normalizado


@dataclass(frozen=True, slots=True)
class CotaAnalises:
    tipo: TipoAcesso
    restantes: int | None

    def __post_init__(self) -> None:
        if self.tipo is TipoAcesso.ILIMITADO:
            if self.restantes is not None:
                raise ValueError(
                    "O acesso ilimitado não possui saldo de análises."
                )
            return

        if self.restantes is None or self.restantes < 0:
            raise ValueError(
                "O acesso limitado precisa de um saldo não negativo."
            )

    @classmethod
    def ilimitada(cls) -> Self:
        return cls(
            tipo=TipoAcesso.ILIMITADO,
            restantes=None,
        )

    @classmethod
    def limitada(cls, quantidade: int) -> Self:
        return cls(
            tipo=TipoAcesso.LIMITADO,
            restantes=quantidade,
        )

    @property
    def disponivel(self) -> bool:
        return (
            self.tipo is TipoAcesso.ILIMITADO
            or bool(self.restantes and self.restantes > 0)
        )

    def definir(self, quantidade: int) -> Self:
        return type(self).limitada(quantidade)

    def adicionar(self, quantidade: int) -> Self:
        if quantidade <= 0:
            raise ValueError(
                "A quantidade adicionada precisa ser maior que zero."
            )

        if self.tipo is TipoAcesso.ILIMITADO:
            return self

        assert self.restantes is not None
        return type(self).limitada(self.restantes + quantidade)

    def consumir(self) -> Self:
        if self.tipo is TipoAcesso.ILIMITADO:
            return self

        assert self.restantes is not None
        if self.restantes == 0:
            raise CotaEsgotadaError(
                "O usuário não possui análises disponíveis."
            )

        return type(self).limitada(self.restantes - 1)


@dataclass(frozen=True, slots=True)
class Turma:
    id: str
    codigo: str
    nome: str
    ativa: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _texto_obrigatorio(self.id, "O id"))
        object.__setattr__(
            self,
            "codigo",
            _texto_obrigatorio(self.codigo, "O código da turma"),
        )
        object.__setattr__(
            self,
            "nome",
            _texto_obrigatorio(self.nome, "O nome da turma"),
        )


@dataclass(frozen=True, slots=True)
class UsuarioAcesso:
    id: str
    email: str
    papel: PapelUsuario
    estado: EstadoConta
    cota: CotaAnalises
    turma_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _texto_obrigatorio(self.id, "O id"))
        object.__setattr__(self, "email", _email_normalizado(self.email))

        if self.papel in {PapelUsuario.MASTER, PapelUsuario.SUBMASTER}:
            if self.cota.tipo is not TipoAcesso.ILIMITADO:
                raise ValueError(
                    "Master e submaster precisam possuir acesso ilimitado."
                )


@dataclass(frozen=True, slots=True)
class ConviteAcesso:
    id: str
    email: str
    convidado_por: str
    papel_destino: PapelUsuario = PapelUsuario.USUARIO
    turma_id: str | None = None
    estado: EstadoConvite = EstadoConvite.PENDENTE

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _texto_obrigatorio(self.id, "O id"))
        object.__setattr__(self, "email", _email_normalizado(self.email))
        object.__setattr__(
            self,
            "convidado_por",
            _texto_obrigatorio(self.convidado_por, "O autor do convite"),
        )

        if self.papel_destino is PapelUsuario.MASTER:
            raise ValueError(
                "A propriedade deve ser transferida pelo fluxo próprio."
            )
