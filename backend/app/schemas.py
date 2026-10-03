"""Modelos de entrada/saída da API.

Todos os modelos de entrada usam extra="forbid": a API não aceita campos além
dos previstos. Uma tentativa de enviar, por exemplo, "cpf" ou "nome" é rejeitada
e registrada como alerta de privacidade (ver main.py).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DatasetSize = Literal[100, 1_000, 10_000, 100_000]
ExportFormat = Literal["csv", "xlsx", "json", "parquet"]
SplitFilter = Literal["all", "train", "validation", "test"]


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_records: DatasetSize = Field(description="Quantidade de pacientes sintéticos: 100, 1000, 10000 ou 100000.")
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1, description="Seed para reprodutibilidade. Vazio = seed aleatório.")


class FieldCheckRequest(BaseModel):
    """Verifica apenas NOMES de campos (nunca valores) contra a lista de campos proibidos."""

    model_config = ConfigDict(extra="forbid")

    fields: list[str] = Field(min_length=1, max_length=200)


class PrivacyReport(BaseModel):
    compliant: bool
    blocked_fields: list[str]
    warnings: list[str]


class DatasetInfo(BaseModel):
    dataset_id: str
    nome: str
    versao: str
    seed: int
    n_registros: int
    criado_em: str
    data_type: Literal["SYNTHETIC"]
    research_only: bool
    privacy_compliant: bool
    quality_passed: bool
