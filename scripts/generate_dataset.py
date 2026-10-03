"""Gera um dataset sintético completo pela linha de comando.

Exemplos (a partir da raiz do projeto, com o ambiente virtual ativo):
    python scripts/generate_dataset.py --n 1000 --seed 42
    python scripts/generate_dataset.py --n 100000 --seed 7 --formats csv,parquet --out data/experimento_7

Saídas em --out (padrão: data/):
    synthetic_dataset.<formato>   dataset completo (com a coluna split)
    splits/train|validation|test.csv
    metadata.json, dataset_card.md, quality_report.md, quality_report.json, privacy_report.json
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.dataset_schema import ALLOWED_SIZES, DISCLAIMER  # noqa: E402
from app.exporter import FORMATS, export_dataset, export_splits  # noqa: E402
from app.service import build_validated_dataset, write_artifacts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Gera um dataset sintético de pacientes. {DISCLAIMER}.")
    parser.add_argument("--n", type=int, default=1000, choices=ALLOWED_SIZES, help="Quantidade de pacientes (100, 1000, 10000 ou 100000).")
    parser.add_argument("--seed", type=int, default=42, help="Seed para reprodutibilidade (padrão: 42).")
    parser.add_argument("--out", type=Path, default=ROOT / "data", help="Pasta de saída (padrão: data/).")
    parser.add_argument("--formats", default="csv", help=f"Formatos separados por vírgula: {', '.join(FORMATS)} (padrão: csv).")
    parser.add_argument("--no-splits", action="store_true", help="Não gravar os arquivos separados de train/validation/test.")
    parser.add_argument("--store-db", action="store_true", help="Também grava no banco SQLite usado pela aplicação web.")
    args = parser.parse_args()

    formatos = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    invalidos = [f for f in formatos if f not in FORMATS]
    if invalidos:
        parser.error(f"formato(s) inválido(s): {', '.join(invalidos)}")

    print(f"[!] {DISCLAIMER}")
    inicio = time.perf_counter()
    resultado = build_validated_dataset(args.n, args.seed)
    print(f"Gerados {len(resultado.df):,} pacientes sintéticos (seed={args.seed}) em {time.perf_counter() - inicio:.1f}s".replace(",", "."))
    print(f"Qualidade: {'APROVADO' if resultado.quality['passed'] else 'REPROVADO'} | Privacidade: {resultado.privacy}")

    args.out.mkdir(parents=True, exist_ok=True)
    for formato in formatos:
        caminho = export_dataset(resultado.df, formato, args.out / "synthetic_dataset", resultado.metadata)
        print(f"  dataset -> {caminho.relative_to(ROOT) if caminho.is_relative_to(ROOT) else caminho}")
    if not args.no_splits:
        for nome, caminho in export_splits(resultado.df, args.out / "splits").items():
            print(f"  {nome:<10} -> {caminho.relative_to(ROOT) if caminho.is_relative_to(ROOT) else caminho}")
    for nome, caminho in write_artifacts(resultado, args.out).items():
        print(f"  {nome:<20} -> {caminho.relative_to(ROOT) if caminho.is_relative_to(ROOT) else caminho}")

    if args.store_db:
        from app.config import get_settings
        from app.database import Database
        from app.repository import save_dataset

        db = Database(get_settings().resolved_database_url)
        db.create_all()
        for sessao in db.session():
            save_dataset(sessao, resultado.df, resultado.dataset_id, args.seed, resultado.metadata, True, True)
        print("  banco SQLite atualizado (dataset ativo na aplicação web)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
