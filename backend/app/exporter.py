"""Exportação para CSV, XLSX, JSON e Parquet.

Toda exportação passa antes pelo privacy_guard: se houver campo proibido ou
conteúdo com formato de dado pessoal, nada é gravado (PrivacyViolationError).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.dataset_schema import DISCLAIMER, FIELDS, SPLITS
from app.privacy_guard import assert_privacy

FORMATS = {"csv": ".csv", "xlsx": ".xlsx", "json": ".json", "parquet": ".parquet"}


def _data_dictionary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "variavel": f.name,
                "tipo": f.dtype,
                "unidade": f.unit or "",
                "minimo": f.min,
                "maximo": f.max,
                "categorias": ", ".join(f.categories) if f.categories else "",
                "papel_ml": f.ml_role,
                "descricao": f.description,
            }
            for f in FIELDS
        ]
    )


def _write_sheet(workbook, nome: str, tabela: pd.DataFrame, negrito) -> None:
    planilha = workbook.add_worksheet(nome)
    planilha.write_row(0, 0, [str(c) for c in tabela.columns], negrito)
    # write_row direto com tipos nativos: muito mais rápido que DataFrame.to_excel em 100 mil linhas.
    for i, linha in enumerate(tabela.itertuples(index=False, name=None), start=1):
        planilha.write_row(i, 0, ["" if v is None else v for v in linha])


def _write_xlsx(df: pd.DataFrame, caminho: Path, metadata: dict[str, Any]) -> None:
    import xlsxwriter

    workbook = xlsxwriter.Workbook(str(caminho), {"constant_memory": True, "nan_inf_to_errors": True})
    negrito = workbook.add_format({"bold": True})
    try:
        _write_sheet(workbook, "LEIA-ME", pd.DataFrame({"aviso": [DISCLAIMER, "data_type = SYNTHETIC | research_only = true"]}), negrito)
        _write_sheet(workbook, "dados", df.astype(object).where(df.notna(), None), negrito)
        _write_sheet(workbook, "dicionario", _data_dictionary().astype(object).where(lambda t: t.notna(), None), negrito)
        if metadata:
            resumo = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
            _write_sheet(workbook, "metadados", pd.DataFrame(list(resumo.items()), columns=["chave", "valor"]), negrito)
    finally:
        workbook.close()


def export_dataset(df: pd.DataFrame, fmt: str, destination: Path, metadata: dict[str, Any] | None = None) -> Path:
    """Exporta `df` no formato pedido. `destination` é o caminho do arquivo (a extensão é ajustada)."""
    fmt = fmt.lower()
    if fmt not in FORMATS:
        raise ValueError(f"Formato não suportado: {fmt}. Use um de: {', '.join(FORMATS)}")
    assert_privacy(df)

    caminho = Path(destination).with_suffix(FORMATS[fmt])
    caminho.parent.mkdir(parents=True, exist_ok=True)
    metadata = metadata or {}

    if fmt == "csv":
        df.to_csv(caminho, index=False, encoding="utf-8")
    elif fmt == "xlsx":
        _write_xlsx(df, caminho, metadata)
    elif fmt == "json":
        conteudo = {
            "disclaimer": DISCLAIMER,
            "data_type": "SYNTHETIC",
            "research_only": True,
            "metadata": {k: v for k, v in metadata.items() if k != "fields"},
            "records": json.loads(df.to_json(orient="records", force_ascii=False)),
        }
        caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8")
    elif fmt == "parquet":
        tabela = pa.Table.from_pandas(df, preserve_index=False)
        meta_extra = {b"synthetic_dataset": json.dumps({"disclaimer": DISCLAIMER, "data_type": "SYNTHETIC", "research_only": True, "dataset_id": metadata.get("dataset_id")}).encode()}
        tabela = tabela.replace_schema_metadata({**(tabela.schema.metadata or {}), **meta_extra})
        pq.write_table(tabela, caminho)
    return caminho


def export_splits(df: pd.DataFrame, directory: Path, fmt: str = "csv") -> dict[str, Path]:
    """Grava train/validation/test em arquivos separados (sem a coluna split)."""
    assert_privacy(df)
    saidas = {}
    for nome in SPLITS:
        parte = df[df["split"] == nome].drop(columns=["split"]).reset_index(drop=True)
        saidas[nome] = export_dataset(parte, fmt, Path(directory) / nome)
    return saidas
