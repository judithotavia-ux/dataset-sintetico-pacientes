"""Orquestração: gerar -> validar qualidade -> validar privacidade -> persistir -> artefatos."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app import repository
from app.audit import log_event
from app.dataset_schema import CLASSIFICACAO_RISCO, CONDICOES, CONDITION_COLUMNS, DESFECHOS, LAB_FIELDS, SEM_CONDICAO, SPLITS
from app.generator import generate_dataset
from app.metadata import build_dataset_card, build_metadata
from app.privacy_guard import PrivacyViolationError, validate_privacy
from app.quality import quality_report_markdown, validate_quality


class DatasetQualityError(Exception):
    def __init__(self, report: dict):
        self.report = report
        super().__init__(f"Dataset reprovado na validação de qualidade ({len(report['issues'])} problema(s))")


@dataclass
class GenerationResult:
    dataset_id: str
    seed: int
    df: pd.DataFrame
    metadata: dict[str, Any]
    quality: dict[str, Any]
    privacy: dict[str, Any]


def build_validated_dataset(n_records: int, seed: int, dataset_id: str | None = None) -> GenerationResult:
    """Gera e valida (qualidade + privacidade) sem tocar no banco."""
    dataset_id = dataset_id or str(uuid.uuid4())
    df = generate_dataset(n_records, seed)
    quality = validate_quality(df)
    if not quality["passed"]:
        raise DatasetQualityError(quality)
    privacy = validate_privacy(df)
    if not privacy["compliant"]:
        raise PrivacyViolationError(privacy)
    metadata = build_metadata(df, dataset_id, seed, privacy, quality)
    return GenerationResult(dataset_id, seed, df, metadata, quality, privacy)


def write_artifacts(result: GenerationResult, directory: Path) -> dict[str, Path]:
    """Grava metadata.json, dataset_card.md, quality_report.(md|json) e privacy_report.json."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    info = {"dataset_id": result.dataset_id, "seed": result.seed}
    arquivos = {
        "metadata": directory / "metadata.json",
        "dataset_card": directory / "dataset_card.md",
        "quality_report_md": directory / "quality_report.md",
        "quality_report_json": directory / "quality_report.json",
        "privacy_report": directory / "privacy_report.json",
    }
    arquivos["metadata"].write_text(json.dumps(result.metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    arquivos["dataset_card"].write_text(build_dataset_card(result.df, result.metadata), encoding="utf-8")
    arquivos["quality_report_md"].write_text(quality_report_markdown(result.df, result.quality, result.privacy, info), encoding="utf-8")
    arquivos["quality_report_json"].write_text(json.dumps({**info, **result.quality}, ensure_ascii=False, indent=2), encoding="utf-8")
    arquivos["privacy_report"].write_text(json.dumps(result.privacy, ensure_ascii=False, indent=2), encoding="utf-8")
    return arquivos


def generate_and_store(session: Session, n_records: int, seed: int, artifacts_root: Path | None = None) -> GenerationResult:
    log_event(session, "geracao_iniciada", n_records=n_records, seed=seed)
    try:
        result = build_validated_dataset(n_records, seed)
    except DatasetQualityError as erro:
        log_event(session, "geracao_reprovada_qualidade", "ERROR", n_records=n_records, seed=seed, checks=erro.report["checks"])
        raise
    except PrivacyViolationError as erro:
        log_event(session, "geracao_bloqueada_privacidade", "ALERTA", n_records=n_records, seed=seed, blocked_fields=erro.report["blocked_fields"])
        raise
    repository.save_dataset(session, result.df, result.dataset_id, seed, result.metadata, result.privacy["compliant"], result.quality["passed"])
    if artifacts_root is not None:
        write_artifacts(result, Path(artifacts_root) / result.dataset_id)
    log_event(session, "geracao_concluida", dataset_id=result.dataset_id, n_records=len(result.df), seed=seed, splits=result.metadata["splits"]["counts"])
    return result


IDADE_FAIXAS = [(18, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 90)]
IMC_FAIXAS = [
    ("Baixo peso", 0, 18.5),
    ("Normal", 18.5, 25),
    ("Sobrepeso", 25, 30),
    ("Obesidade I", 30, 35),
    ("Obesidade II", 35, 40),
    ("Obesidade III", 40, np.inf),
]


def dashboard_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Agregados para o painel (nunca devolve registros individuais)."""
    def contagens(serie: pd.Series, ordem: tuple[str, ...]) -> list[dict[str, Any]]:
        vc = serie.astype(str).value_counts()
        return [{"label": k, "value": int(vc.get(k, 0))} for k in ordem]

    imc = df["imc"]
    return {
        "n_registros": int(len(df)),
        "idade": [{"label": f"{a}–{b}", "value": int(df["idade"].between(a, b).sum())} for a, b in IDADE_FAIXAS],
        "sexo": contagens(df["sexo"], ("F", "M")),
        "imc": [{"label": nome, "value": int(((imc >= lo) & (imc < hi)).sum())} for nome, lo, hi in IMC_FAIXAS],
        "condicoes": sorted(
            [{"label": c, "value": int(df[CONDITION_COLUMNS[c]].sum())} for c in CONDICOES]
            + [{"label": SEM_CONDICAO, "value": int((df["n_condicoes"] == 0).sum())}],
            key=lambda x: -x["value"],
        ),
        "classificacao_risco": contagens(df["classificacao_risco"], CLASSIFICACAO_RISCO),
        "desfecho": contagens(df["resultado_desfecho"], DESFECHOS),
        "split": contagens(df["split"], SPLITS),
        "medias": {
            "idade": round(float(df["idade"].mean()), 1),
            "imc": round(float(imc.mean()), 1),
            "pa_sistolica": round(float(df["pa_sistolica"].mean()), 1),
            "pa_diastolica": round(float(df["pa_diastolica"].mean()), 1),
            "desfecho_adverso_pct": round(100 * float(df["desfecho_adverso"].mean()), 1),
        },
        "registros_por_tabela": {
            "patients": int(len(df)),
            "clinical_records": int(len(df)),
            "lab_results": int(len(df)) * len(LAB_FIELDS),
            "medications": int(df["n_medicamentos"].sum()),
        },
    }
