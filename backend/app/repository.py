"""Persistência do dataset no banco relacional e reconstrução da tabela plana.

O DataFrame "plano" (1 linha por paciente) é normalizado em patients,
clinical_records, lab_results e medications. `load_dataset_frame` faz o caminho
inverso; o teste de integridade garante que ida e volta preservam os dados.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from app.dataset_schema import COLUMN_ORDER, DATASET_NAME, DATASET_VERSION, LAB_FIELDS
from app.generator import CATALOGO_MEDICAMENTOS, enforce_dtypes
from app.models import ClinicalRecord, DatasetMetadata, LabResult, Medication, Patient

PATIENT_COLUMNS = [c.key for c in Patient.__table__.columns if c.key != "dataset_id"]
CLINICAL_COLUMNS = [c.key for c in ClinicalRecord.__table__.columns if c.key not in ("id", "dataset_id")]
LAB_UNITS = {f.name: f.unit or "" for f in LAB_FIELDS}
MED_INFO = {nome: (classe, posologia) for opcoes in CATALOGO_MEDICAMENTOS.values() for nome, classe, posologia in opcoes}

CHUNK = 20_000

_cache: dict[str, pd.DataFrame] = {}


def _chunks(rows: list[dict[str, Any]]):
    for i in range(0, len(rows), CHUNK):
        yield rows[i:i + CHUNK]


def _bulk_insert(session: Session, model, rows: list[dict[str, Any]]) -> None:
    # Insert do SQLAlchemy Core (executemany em lote), bem mais rápido que o caminho do ORM.
    for parte in _chunks(rows):
        session.execute(model.__table__.insert(), parte)


def remove_other_datasets(session: Session, keep_dataset_id: str) -> int:
    """Mantém só o dataset ativo no banco (os anteriores ficam registrados como SUBSTITUIDO)."""
    antigos = session.scalars(select(DatasetMetadata.dataset_id).where(DatasetMetadata.dataset_id != keep_dataset_id, DatasetMetadata.status == "ATIVO")).all()
    for model in (LabResult, Medication, ClinicalRecord):
        session.execute(delete(model).where(model.dataset_id != keep_dataset_id))
    session.execute(delete(Patient).where(Patient.dataset_id != keep_dataset_id))
    session.execute(update(DatasetMetadata).where(DatasetMetadata.dataset_id != keep_dataset_id).values(status="SUBSTITUIDO"))
    for antigo in antigos:
        _cache.pop(antigo, None)
    return len(antigos)


def save_dataset(session: Session, df: pd.DataFrame, dataset_id: str, seed: int, metadata: dict[str, Any], privacy_ok: bool, quality_ok: bool) -> None:
    session.add(
        DatasetMetadata(
            dataset_id=dataset_id,
            nome=DATASET_NAME,
            versao=DATASET_VERSION,
            seed=seed,
            n_registros=len(df),
            criado_em=datetime.now(timezone.utc).replace(tzinfo=None),
            status="ATIVO",
            data_type="SYNTHETIC",
            privacy_compliant=privacy_ok,
            quality_passed=quality_ok,
            metadata_json=json.dumps(metadata, ensure_ascii=False),
        )
    )
    session.flush()
    # Remove o dataset anterior ANTES de inserir: o mesmo seed gera os mesmos patient_id.
    # Tudo acontece na mesma transação, então uma falha no meio desfaz a troca inteira.
    remove_other_datasets(session, dataset_id)

    registros = df.to_dict(orient="records")
    datas = {r["patient_id"]: date.fromisoformat(r["data_atendimento"]) for r in registros}

    _bulk_insert(session, Patient, [{**{c: r[c] for c in PATIENT_COLUMNS}, "dataset_id": dataset_id} for r in registros])
    _bulk_insert(
        session,
        ClinicalRecord,
        [{**{c: r[c] for c in CLINICAL_COLUMNS if c != "data_atendimento"}, "data_atendimento": datas[r["patient_id"]], "dataset_id": dataset_id} for r in registros],
    )
    _bulk_insert(
        session,
        LabResult,
        [
            {"patient_id": r["patient_id"], "dataset_id": dataset_id, "exame": exame, "valor": float(r[exame]), "unidade": unidade, "data_coleta": datas[r["patient_id"]]}
            for r in registros
            for exame, unidade in LAB_UNITS.items()
        ],
    )
    _bulk_insert(
        session,
        Medication,
        [
            {"patient_id": r["patient_id"], "dataset_id": dataset_id, "ordem": i, "nome": nome, "classe": MED_INFO[nome][0], "posologia": MED_INFO[nome][1]}
            for r in registros
            for i, nome in enumerate([m for m in r["medicamentos"].split("; ") if m])
        ],
    )
    session.commit()
    _cache.clear()
    _cache[dataset_id] = df.copy()


def get_active_dataset(session: Session) -> DatasetMetadata | None:
    return session.scalars(select(DatasetMetadata).where(DatasetMetadata.status == "ATIVO").order_by(DatasetMetadata.criado_em.desc())).first()


def load_dataset_frame(session: Session, dataset_id: str, use_cache: bool = True) -> pd.DataFrame:
    """Reconstrói o DataFrame plano a partir das tabelas normalizadas."""
    if use_cache and dataset_id in _cache:
        return _cache[dataset_id].copy()

    conexao = session.connection()
    pacientes = pd.read_sql(select(Patient).where(Patient.dataset_id == dataset_id).order_by(text("patients.rowid")), conexao)
    clinicos = pd.read_sql(select(ClinicalRecord).where(ClinicalRecord.dataset_id == dataset_id), conexao)
    exames = pd.read_sql(select(LabResult.patient_id, LabResult.exame, LabResult.valor).where(LabResult.dataset_id == dataset_id), conexao)
    meds = pd.read_sql(select(Medication.patient_id, Medication.ordem, Medication.nome).where(Medication.dataset_id == dataset_id), conexao)
    if pacientes.empty:
        return pd.DataFrame(columns=COLUMN_ORDER)

    df = pacientes.drop(columns=["dataset_id"]).merge(clinicos.drop(columns=["id", "dataset_id"]), on="patient_id", how="left")
    df = df.merge(exames.pivot(index="patient_id", columns="exame", values="valor").reset_index(), on="patient_id", how="left")
    if meds.empty:
        df["medicamentos"] = ""
    else:
        lista = meds.sort_values(["patient_id", "ordem"]).groupby("patient_id")["nome"].agg("; ".join).rename("medicamentos").reset_index()
        df = df.merge(lista, on="patient_id", how="left")
        df["medicamentos"] = df["medicamentos"].fillna("")
    df["n_medicamentos"] = df["medicamentos"].map(lambda s: len([m for m in s.split("; ") if m]))
    df["data_atendimento"] = pd.to_datetime(df["data_atendimento"]).dt.strftime("%Y-%m-%d")

    # Mantém a ordem de inserção (ordem de geração), que é a ordem das linhas de patients.
    df = enforce_dtypes(df[COLUMN_ORDER])
    _cache[dataset_id] = df.copy()
    return df


def clear_cache() -> None:
    _cache.clear()
