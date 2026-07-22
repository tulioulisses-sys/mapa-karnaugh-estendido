from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    estados_iniciais: dict[str, int | bool | str] | None = None
    ciclo_continuo: bool = False
    incluir_mapa: bool = True


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

