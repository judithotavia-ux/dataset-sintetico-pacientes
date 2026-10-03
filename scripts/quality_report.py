"""Valida qualidade e privacidade de um arquivo de dataset já gerado.

Uso:
    python scripts/quality_report.py --input data/synthetic_dataset.csv
    python scripts/quality_report.py --input data/experimento/synthetic_dataset.parquet --out data/experimento

Grava quality_report.md, quality_report.json e privacy_report.json na pasta --out
(padrão: a pasta do arquivo de entrada). Sai com código 1 se o dataset for reprovado.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.generator import enforce_dtypes  # noqa: E402
from app.privacy_guard import validate_privacy  # noqa: E402
from app.quality import quality_report_markdown, validate_quality  # noqa: E402


def load(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path, keep_default_na=False, na_values=[""])
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".json":
        return pd.DataFrame(json.loads(path.read_text(encoding="utf-8"))["records"])
    if path.suffix == ".xlsx":
        return pd.read_excel(path, sheet_name="dados", keep_default_na=False, na_values=[""])
    raise SystemExit(f"Formato não suportado: {path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Relatório de qualidade e privacidade de um dataset sintético.")
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "synthetic_dataset.csv")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    bruto = load(args.input)
    # Privacidade é validada no arquivo como está; qualidade após aplicar os tipos do dicionário.
    privacidade = validate_privacy(bruto)
    if "medicamentos" in bruto:
        bruto["medicamentos"] = bruto["medicamentos"].fillna("")
    try:
        df = enforce_dtypes(bruto)
    except (ValueError, TypeError) as erro:
        print(f"Não foi possível converter os tipos: {erro}")
        df = bruto
    qualidade = validate_quality(df)

    meta_path = args.input.parent / "metadata.json"
    info = {"dataset_id": "-", "seed": "-"}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        info = {"dataset_id": meta.get("dataset_id", "-"), "seed": meta.get("seed", "-")}

    out = args.out or args.input.parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "quality_report.md").write_text(quality_report_markdown(df, qualidade, privacidade, info), encoding="utf-8")
    (out / "quality_report.json").write_text(json.dumps({**info, **qualidade}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "privacy_report.json").write_text(json.dumps(privacidade, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Registros: {len(df)}")
    for nome, resultado in qualidade["checks"].items():
        print(f"  {nome:<26} {resultado}")
    for problema in qualidade["issues"]:
        print(f"  - [{problema['check']}] {problema['message']}")
    print(f"Privacidade: {privacidade}")
    print(f"Relatórios gravados em {out}")
    aprovado = qualidade["passed"] and privacidade["compliant"]
    print("RESULTADO:", "APROVADO" if aprovado else "REPROVADO")
    return 0 if aprovado else 1


if __name__ == "__main__":
    raise SystemExit(main())
