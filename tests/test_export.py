"""Exportação em CSV, XLSX, JSON e Parquet e bloqueio por privacidade."""

import json

import pandas as pd
import pyarrow.parquet as pq
import pytest

from app.exporter import FORMATS, export_dataset, export_splits
from app.generator import enforce_dtypes
from app.privacy_guard import PrivacyViolationError

AMOSTRA = 300


@pytest.fixture
def pequeno(dataset):
    return dataset.head(AMOSTRA).copy()


def _ler(caminho, fmt):
    if fmt == "csv":
        return pd.read_csv(caminho, keep_default_na=False, na_values=[])
    if fmt == "xlsx":
        return pd.read_excel(caminho, sheet_name="dados", keep_default_na=False, na_values=[])
    if fmt == "json":
        return pd.DataFrame(json.loads(caminho.read_text(encoding="utf-8"))["records"])
    return pd.read_parquet(caminho)


@pytest.mark.parametrize("fmt", list(FORMATS))
def test_exporta_e_le_de_volta(pequeno, tmp_path, fmt):
    caminho = export_dataset(pequeno, fmt, tmp_path / "saida", {"dataset_id": "teste"})
    assert caminho.exists() and caminho.suffix == FORMATS[fmt]
    lido = enforce_dtypes(_ler(caminho, fmt))
    assert list(lido.columns) == list(pequeno.columns)
    assert len(lido) == AMOSTRA
    assert lido["patient_id"].tolist() == pequeno["patient_id"].tolist()
    assert (lido["data_type"] == "SYNTHETIC").all()
    pd.testing.assert_series_equal(lido["imc"], pequeno["imc"], check_names=False)


def test_xlsx_tem_aviso_e_dicionario(pequeno, tmp_path):
    caminho = export_dataset(pequeno, "xlsx", tmp_path / "saida")
    abas = pd.ExcelFile(caminho).sheet_names
    assert abas[:3] == ["LEIA-ME", "dados", "dicionario"]
    assert "NÃO CONTÉM DADOS REAIS" in pd.read_excel(caminho, sheet_name="LEIA-ME").iloc[0, 0]


def test_json_tem_marcacao(pequeno, tmp_path):
    conteudo = json.loads(export_dataset(pequeno, "json", tmp_path / "saida").read_text(encoding="utf-8"))
    assert conteudo["data_type"] == "SYNTHETIC" and conteudo["research_only"] is True


def test_parquet_tem_metadados(pequeno, tmp_path):
    esquema = pq.read_schema(export_dataset(pequeno, "parquet", tmp_path / "saida", {"dataset_id": "abc"}))
    meta = json.loads(esquema.metadata[b"synthetic_dataset"])
    assert meta["data_type"] == "SYNTHETIC" and meta["dataset_id"] == "abc"


@pytest.mark.parametrize("fmt", list(FORMATS))
def test_exportacao_bloqueada_com_campo_proibido(pequeno, tmp_path, fmt):
    pequeno["telefone"] = "x"
    with pytest.raises(PrivacyViolationError):
        export_dataset(pequeno, fmt, tmp_path / "bloqueado")
    assert not list(tmp_path.iterdir()), "nenhum arquivo pode ser gravado quando a exportação é bloqueada"


def test_formato_invalido(pequeno, tmp_path):
    with pytest.raises(ValueError):
        export_dataset(pequeno, "pdf", tmp_path / "x")


def test_exporta_splits(dataset, tmp_path):
    saidas = export_splits(dataset, tmp_path)
    tamanhos = {nome: len(pd.read_csv(caminho)) for nome, caminho in saidas.items()}
    assert sum(tamanhos.values()) == len(dataset)
    assert tamanhos["train"] > tamanhos["validation"] > 0 and tamanhos["test"] > 0
    assert "split" not in pd.read_csv(saidas["train"]).columns
