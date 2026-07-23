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
