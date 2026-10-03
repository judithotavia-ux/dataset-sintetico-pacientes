"""Baixa e prepara a base pública REAL (UCI Heart Disease — Cleveland), separada do dataset sintético.

Uso:
    python scripts/fetch_public_dataset.py
    python scripts/fetch_public_dataset.py --arquivo caminho/processed.cleveland.data   # usa cópia local

Saídas em data/real_public/uci_heart_disease/:
    heart_disease_cleveland.csv, metadata.json, dataset_card.md, privacy_report.json, CITACAO.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.privacy_guard import validate_privacy  # noqa: E402
from app.public_datasets import (  # noqa: E402
    PUBLIC_COLUMNS,
    PUBLIC_DATA_TYPE,
    UCI_HEART,
    build_public_card,
    build_public_metadata,
    download_uci_heart,
    parse_cleveland,
    public_quality,
    verify_checksum,
)

DESTINO = ROOT / "data" / "real_public" / "uci_heart_disease"


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa a base pública UCI Heart Disease (Cleveland).")
    parser.add_argument("--arquivo", type=Path, help="Usa um processed.cleveland.data já baixado em vez de baixar.")
    parser.add_argument("--out", type=Path, default=DESTINO)
    args = parser.parse_args()

    if args.arquivo:
        conteudo = args.arquivo.read_bytes()
        verify_checksum(conteudo)
        print(f"Arquivo local verificado (SHA-256 confere): {args.arquivo}")
    else:
        print(f"Baixando {UCI_HEART['url_download']} …")
        conteudo = download_uci_heart()
        print("Download concluído e SHA-256 conferido.")

    df = parse_cleveland(conteudo)
    privacidade = validate_privacy(df, expected_data_type=PUBLIC_DATA_TYPE, known_fields=PUBLIC_COLUMNS)
    if not privacidade["compliant"]:
        print(f"Base bloqueada pelo privacy_guard: {privacidade}")
        return 1
    qualidade = public_quality(df)
    metadata = build_public_metadata(df, privacidade, qualidade)

    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / "heart_disease_cleveland.csv", index=False, encoding="utf-8")
    (args.out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "dataset_card.md").write_text(build_public_card(df, metadata), encoding="utf-8")
    (args.out / "privacy_report.json").write_text(json.dumps(privacidade, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "CITACAO.txt").write_text(
        f"{UCI_HEART['citacao']}\n\nLicença: {UCI_HEART['licenca']}\nPágina: {UCI_HEART['pagina']}\n", encoding="utf-8"
    )

    print(f"Registros: {qualidade['n_records']} (completos: {qualidade['registros_completos']})")
    print(f"Ausentes: {qualidade['missing_values']}")
    print(f"Prevalência de doença cardíaca: {100 * qualidade['prevalencia_doenca_cardiaca']:.1f}%")
    print(f"Qualidade: {'OK' if qualidade['passed'] else qualidade['problems']} | Privacidade: {privacidade}")
    print(f"Arquivos gravados em {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
