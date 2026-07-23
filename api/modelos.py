from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


LIMITE_SEQUENCIA = 20_000


class ModeloEntrada(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class SolicitacaoAnalise(ModeloEntrada):
    sequencia: str = Field(min_length=1, max_length=LIMITE_SEQUENCIA)

    @field_validator("sequencia")
    @classmethod
    def impedir_sequencia_vazia(cls, valor: str) -> str:
        if not valor:
            raise ValueError("A sequência não pode estar vazia.")
        return valor


class SolicitacaoResolucao(SolicitacaoAnalise):
    chave_idempotencia: str = Field(min_length=1, max_length=200)
    turma_id: UUID | None = None
    estados_iniciais: dict[str, int | bool | str] | None = None
    ciclo_continuo: bool = False
    incluir_mapa: bool = True


class SolicitacaoEstadoUsuario(ModeloEntrada):
    estado: Literal["ativo", "suspenso", "revogado"]


class SolicitacaoAcessoUsuario(ModeloEntrada):
    acesso: Literal["ilimitado", "limitado"]
    analises_restantes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validar_cota(self) -> SolicitacaoAcessoUsuario:
        if self.acesso == "ilimitado" and self.analises_restantes is not None:
            raise ValueError("O acesso ilimitado não possui saldo.")
        if self.acesso == "limitado" and self.analises_restantes is None:
            raise ValueError("Informe o saldo do acesso limitado.")
        return self


class SolicitacaoCotasLote(ModeloEntrada):
    operacao: Literal["definir", "adicionar"]
    quantidade: int = Field(ge=0)
    usuario_ids: list[UUID] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validar_quantidade_adicionada(self) -> SolicitacaoCotasLote:
        if self.operacao == "adicionar" and self.quantidade < 1:
            raise ValueError("A quantidade adicionada deve ser positiva.")
        return self


class SolicitacaoPapelUsuario(ModeloEntrada):
    papel: Literal["usuario", "submaster"]


class SolicitacaoTransferenciaMaster(ModeloEntrada):
    email_destino: str = Field(min_length=3, max_length=254)
    dias_validade: int = Field(default=7, ge=1, le=30)

    @field_validator("email_destino")
    @classmethod
    def validar_email_destino(cls, valor: str) -> str:
        email = valor.strip().casefold()
        partes = email.split("@")
        if (
            len(partes) != 2
            or not partes[0]
            or "." not in partes[1]
            or partes[1].startswith(".")
            or partes[1].endswith(".")
            or any(caractere.isspace() for caractere in email)
        ):
            raise ValueError("Informe um e-mail válido.")
        return email


class SolicitacaoTurma(ModeloEntrada):
    codigo: str = Field(min_length=1, max_length=40)
    nome: str = Field(min_length=1, max_length=120)


class SolicitacaoConvitesLote(ModeloEntrada):
    emails: list[str] = Field(min_length=1, max_length=300)
    papel_destino: Literal["usuario", "submaster"] = "usuario"
    acesso_destino: Literal["ilimitado", "limitado"] = "limitado"
    analises_iniciais: int | None = Field(default=0, ge=0)
    turma_id: UUID | None = None
    dias_validade: int = Field(default=7, ge=1, le=30)

    @field_validator("emails")
    @classmethod
    def normalizar_emails(cls, valores: list[str]) -> list[str]:
        normalizados: list[str] = []
        vistos: set[str] = set()
        for valor in valores:
            email = valor.strip().casefold()
            partes = email.split("@")
            if (
                len(partes) != 2
                or not partes[0]
                or "." not in partes[1]
                or partes[1].startswith(".")
                or partes[1].endswith(".")
                or any(caractere.isspace() for caractere in email)
                or len(email) > 254
            ):
                raise ValueError(f"E-mail inválido: {valor}.")
            if email not in vistos:
                vistos.add(email)
                normalizados.append(email)
        if not normalizados:
            raise ValueError("Informe pelo menos um e-mail.")
        return normalizados

    @model_validator(mode="after")
    def validar_acesso_inicial(self) -> SolicitacaoConvitesLote:
        if self.papel_destino == "submaster":
            if (
                self.acesso_destino != "ilimitado"
                or self.analises_iniciais is not None
            ):
                raise ValueError("Submaster deve possuir acesso ilimitado.")
        elif self.acesso_destino == "ilimitado":
            if self.analises_iniciais is not None:
                raise ValueError("O acesso ilimitado não possui saldo.")
        elif self.analises_iniciais is None:
            raise ValueError("Informe a cota inicial dos alunos.")
        return self


class DetalheErro(BaseModel):
    codigo: str
    mensagem: str
    campo: str | None = None
    detalhes: dict[str, Any] = Field(default_factory=dict)


class RespostaErro(BaseModel):
    erro: DetalheErro


class RespostaSaude(BaseModel):
    status: str
    api_version: str
    motor_version: str
