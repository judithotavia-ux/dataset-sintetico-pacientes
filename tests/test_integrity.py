"""Integridade: banco relacional, ida e volta dos dados, metadados e artefatos."""

import json

import pandas as pd
import pytest
from sqlalchemy import func, select

from app import repository
from app.config import Settings
from app.database import Database
from app.dataset_schema import LAB_FIELDS
from app.models import AuditLog, ClinicalRecord, DatasetMetadata, LabResult, Medication, Patient
from app.service import build_validated_dataset, generate_and_store, write_artifacts


@pytest.fixture
def session(tmp_path):
    db = Database(Settings(data_dir=tmp_path).resolved_database_url)
    db.create_all()
    gen = db.session()
    sessao = next(gen)
    repository.clear_cache()
    yield sessao
    sessao.close()
    db.engine.dispose()
    repository.clear_cache()


def _contar(session, model, dataset_id=None):
    consulta = select(func.count()).select_from(model)
    if dataset_id:
        consulta = consulta.where(model.dataset_id == dataset_id)
    return session.scalar(consulta)


def test_ida_e_volta_preserva_dados(session):
    resultado = generate_and_store(session, 500, 99)
    repository.clear_cache()  # força a reconstrução a partir das tabelas
    reconstruido = repository.load_dataset_frame(session, resultado.dataset_id)
    pd.testing.assert_frame_equal(reconstruido, resultado.df)


def test_contagens_por_tabela(session):
    resultado = generate_and_store(session, 300, 5)
    did = resultado.dataset_id
    assert _contar(session, Patient, did) == 300
    assert _contar(session, ClinicalRecord, did) == 300
    assert _contar(session, LabResult, did) == 300 * len(LAB_FIELDS)
    assert _contar(session, Medication, did) == int(resultado.df["n_medicamentos"].sum())


def test_novo_dataset_substitui_o_anterior(session):
    primeiro = generate_and_store(session, 100, 1)
    segundo = generate_and_store(session, 100, 2)
    assert _contar(session, Patient) == 100
    assert _contar(session, Patient, primeiro.dataset_id) == 0
    status = dict(session.execute(select(DatasetMetadata.dataset_id, DatasetMetadata.status)).all())
    assert status == {primeiro.dataset_id: "SUBSTITUIDO", segundo.dataset_id: "ATIVO"}
    assert repository.get_active_dataset(session).dataset_id == segundo.dataset_id


def test_auditoria_sem_dados_pessoais(session):
    resultado = generate_and_store(session, 100, 3)
    detalhes = " ".join(r.detalhes for r in session.scalars(select(AuditLog)))
    assert "geracao_concluida" in {r.evento for r in session.scalars(select(AuditLog))}
    # nenhum valor de registro (ex.: patient_id) vai para o log
    assert not any(pid in detalhes for pid in resultado.df["patient_id"])


def test_metadados_completos():
    resultado = build_validated_dataset(200, 11)
    meta = resultado.metadata
    for chave in ("dataset_name", "version", "generated_at", "n_records", "fields", "generation_method", "limitations", "purpose"):
        assert meta[chave]
    assert meta["synthetic"] is True and meta["data_type"] == "SYNTHETIC"
    assert meta["n_records"] == 200
    assert {f["name"] for f in meta["fields"]} == set(resultado.df.columns)
    assert all(f["description"] for f in meta["fields"])


def test_artefatos_gravados(tmp_path):
    resultado = build_validated_dataset(200, 11)
    arquivos = write_artifacts(resultado, tmp_path)
    for caminho in arquivos.values():
        assert caminho.exists() and caminho.stat().st_size > 0
    card = arquivos["dataset_card"].read_text(encoding="utf-8")
    for secao in ("Origem", "Finalidade", "Variáveis", "Método de geração", "Limitações", "Riscos de uso", "Usos permitidos", "Usos não recomendados"):
        assert secao in card
    assert json.loads(arquivos["privacy_report"].read_text(encoding="utf-8"))["compliant"] is True
