"""Compara o dataset SINTÉTICO com a base pública REAL (UCI Heart Disease — Cleveland)
e treina modelos de referência na base real.

Uso:
    python scripts/compare_synthetic_real.py
    python scripts/compare_synthetic_real.py --sintetico data/synthetic_dataset.csv --seed 42

Saídas:
    data/real_public/comparacao_sintetico_real.md e .json
    docs/figuras/comparacao_*.png

As bases NÃO são concatenadas: cada uma é lida do seu próprio arquivo.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.dummy import DummyClassifier  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

warnings.filterwarnings("ignore", message="Unknown solver options")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.public_datasets import UCI_HEART, standardized_mean_difference, summary_numeric  # noqa: E402

REAL_PATH = ROOT / "data" / "real_public" / "uci_heart_disease" / "heart_disease_cleveland.csv"
FIG_DIR = ROOT / "docs" / "figuras"

# (rótulo, coluna no sintético, coluna no real, unidade)
NUMERICAS = [
    ("Idade", "idade", "idade", "anos"),
    ("PA sistólica", "pa_sistolica", "pa_sistolica_repouso", "mmHg"),
    ("Colesterol total", "colesterol_total", "colesterol_total", "mg/dL"),
]
COR_SINT, COR_REAL = "#2563eb", "#dc2626"


def comparar_numericas(sint: pd.DataFrame, real: pd.DataFrame) -> list[dict]:
    linhas = []
    for rotulo, cs, cr, unidade in NUMERICAS:
        a, b = sint[cs].astype(float), real[cr].astype(float)
        ks = stats.ks_2samp(a, b)
        linhas.append(
            {
                "variavel": rotulo,
                "unidade": unidade,
                "sintetico": summary_numeric(a),
                "real": summary_numeric(b),
                "smd": standardized_mean_difference(a, b),
                "ks_d": round(float(ks.statistic), 4),
                "ks_p": float(f"{ks.pvalue:.3g}"),
                "wasserstein": round(float(stats.wasserstein_distance(a, b)), 3),
            }
        )
    return linhas


def teste_proporcoes(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """Teste z para diferença de duas proporções (variância agrupada)."""
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    z = (p1 - p2) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return float(z), float(2 * stats.norm.sf(abs(z)))


def comparar_categoricas(sint: pd.DataFrame, real: pd.DataFrame) -> list[dict]:
    pares = [
        ("Sexo masculino", sint["sexo"] == "M", real["sexo"] == "M"),
        ("Glicemia de jejum > 120 mg/dL", sint["glicemia_jejum"] > 120, real["glicemia_jejum_maior_120"].astype(str).str.lower() == "true"),
    ]
    linhas = []
    for rotulo, a, b in pares:
        z, p = teste_proporcoes(int(a.sum()), len(a), int(b.sum()), len(b))
        linhas.append({"variavel": rotulo, "sintetico_pct": round(100 * a.mean(), 1), "real_pct": round(100 * b.mean(), 1), "z": round(z, 2), "p": float(f"{p:.3g}")})
    return linhas


def modelos_base_real(real: pd.DataFrame, seed: int) -> dict:
    alvo = real["doenca_cardiaca"].astype(str).str.lower().eq("true").astype(int)
    numericas = ["idade", "pa_sistolica_repouso", "colesterol_total", "freq_cardiaca_maxima", "depressao_st", "n_vasos_fluoroscopia"]
    categoricas = ["sexo", "tipo_dor_toracica", "glicemia_jejum_maior_120", "ecg_repouso", "angina_exercicio", "inclinacao_st", "cintilografia_talio"]
    X = real[numericas + categoricas].copy()
    for c in categoricas:
        X[c] = X[c].astype(str).replace({"nan": np.nan})
    prep = ColumnTransformer(
        [
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("esc", StandardScaler())]), numericas),
            ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("ohe", OneHotEncoder(handle_unknown="ignore"))]), categoricas),
        ]
    )
    modelos = {
        "Dummy (classe majoritária)": DummyClassifier(strategy="prior"),
        "Regressão logística": LogisticRegression(max_iter=2000),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=seed, n_jobs=-1),
    }
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed)
    resultados = {}
    for nome, modelo in modelos.items():
        r = cross_validate(Pipeline([("prep", prep), ("model", modelo)]), X, alvo, cv=cv, scoring=["roc_auc", "accuracy", "f1", "balanced_accuracy"])
        resultados[nome] = {
            m: {"media": round(float(r[f"test_{m}"].mean()), 4), "dp": round(float(r[f"test_{m}"].std()), 4)}
            for m in ("roc_auc", "accuracy", "f1", "balanced_accuracy")
        }
    return {"alvo": "doenca_cardiaca", "prevalencia": round(float(alvo.mean()), 4), "validacao": "5-fold estratificado repetido 10x (50 ajustes por modelo)", "modelos": resultados}


def figuras(sint: pd.DataFrame, real: pd.DataFrame, numericas: list[dict], categoricas: list[dict]) -> list[str]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, eixos = plt.subplots(1, 3, figsize=(11, 3.2))
    for ax, (rotulo, cs, cr, unidade), linha in zip(eixos, NUMERICAS, numericas):
        a, b = sint[cs].astype(float), real[cr].astype(float)
        bins = np.linspace(min(a.min(), b.min()), max(a.max(), b.max()), 30)
        ax.hist(a, bins=bins, density=True, alpha=0.55, color=COR_SINT, label=f"Sintético (n={len(a)})")
        ax.hist(b, bins=bins, density=True, alpha=0.55, color=COR_REAL, label=f"Real UCI (n={len(b)})")
        ax.set_title(f"{rotulo} — KS D={linha['ks_d']:.2f}", fontsize=9)
        ax.set_xlabel(unidade)
        ax.set_ylabel("densidade")
    eixos[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    caminho1 = FIG_DIR / "comparacao_numericas.png"
    fig.savefig(caminho1, dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 2.8))
    rotulos = [c["variavel"] for c in categoricas]
    x = np.arange(len(rotulos))
    ax.bar(x - 0.2, [c["sintetico_pct"] for c in categoricas], 0.4, color=COR_SINT, label="Sintético")
    ax.bar(x + 0.2, [c["real_pct"] for c in categoricas], 0.4, color=COR_REAL, label="Real UCI")
    ax.set_xticks(x, rotulos)
    ax.set_ylabel("% dos pacientes")
    ax.legend(frameon=False)
    for i, c in enumerate(categoricas):
        ax.text(i - 0.2, c["sintetico_pct"] + 1, f"{c['sintetico_pct']}%", ha="center", fontsize=8)
        ax.text(i + 0.2, c["real_pct"] + 1, f"{c['real_pct']}%", ha="center", fontsize=8)
    fig.tight_layout()
    caminho2 = FIG_DIR / "comparacao_categoricas.png"
    fig.savefig(caminho2, dpi=160)
    plt.close(fig)
    return [str(caminho1.relative_to(ROOT)), str(caminho2.relative_to(ROOT))]


def markdown(res: dict) -> str:
    linhas = [
        "# Comparação: dataset sintético × base pública real (UCI Heart Disease — Cleveland)",
        "",
        "> As duas bases foram lidas de arquivos separados e **não foram combinadas**. O sintético não foi ajustado à base real.",
        "",
        f"- Sintético: `{res['arquivos']['sintetico']}` (n = {res['n']['sintetico']})",
        f"- Real: `{res['arquivos']['real']}` (n = {res['n']['real']}) — {UCI_HEART['citacao']}",
        "",
        "## Variáveis numéricas em comum",
        "",
        "| Variável | Sintético média (DP) | Real média (DP) | SMD | KS D | KS p | Wasserstein |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in res["numericas"]:
        linhas.append(
            f"| {l['variavel']} ({l['unidade']}) | {l['sintetico']['media']} ({l['sintetico']['dp']}) | {l['real']['media']} ({l['real']['dp']}) | {l['smd']} | {l['ks_d']} | {l['ks_p']} | {l['wasserstein']} |"
        )
    linhas += ["", "## Proporções em comum", "", "| Variável | Sintético | Real | z | p |", "|---|---|---|---|---|"]
    linhas += [f"| {c['variavel']} | {c['sintetico_pct']}% | {c['real_pct']}% | {c['z']} | {c['p']} |" for c in res["categoricas"]]
    m = res["modelos_base_real"]
    linhas += [
        "",
        f"## Modelos na base real — alvo `{m['alvo']}` (prevalência {100 * m['prevalencia']:.1f}%)",
        "",
        f"Validação: {m['validacao']}. Valores = média (desvio padrão).",
        "",
        "| Modelo | ROC-AUC | Acurácia | F1 | Acurácia balanceada |",
        "|---|---|---|---|---|",
    ]
    for nome, r in m["modelos"].items():
        linhas.append(" | ".join([f"| {nome}"] + [f"{r[k]['media']} ({r[k]['dp']})" for k in ("roc_auc", "accuracy", "f1", "balanced_accuracy")]) + " |")
    linhas += [
        "",
        "## Interpretação",
        "",
        "- As diferenças de distribuição são **esperadas e não são defeito**: o gerador não foi calibrado com esta base,",
        "  e a base UCI é de pacientes encaminhados para angiografia nos EUA em 1988 (mais velhos, mais homens, colesterol mais alto).",
        "- SMD (diferença média padronizada) acima de 0,2 indica diferença pequena; acima de 0,5, média; acima de 0,8, grande.",
        "- O KS testa se as duas amostras vêm da mesma distribuição; com amostras grandes, até diferenças pequenas ficam significativas.",
        "- Os modelos na base real servem de **referência de desempenho em dados reais** para a pesquisa.",
        "",
    ]
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara o dataset sintético com a base pública real.")
    parser.add_argument("--sintetico", type=Path, default=ROOT / "data" / "synthetic_dataset.csv")
    parser.add_argument("--real", type=Path, default=REAL_PATH)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.real.exists():
        print("Base real não encontrada. Rode antes: python scripts/fetch_public_dataset.py")
        return 1

    sint = pd.read_csv(args.sintetico, keep_default_na=False, na_values=[""])
    real = pd.read_csv(args.real)
    numericas = comparar_numericas(sint, real)
    categoricas = comparar_categoricas(sint, real)
    resultado = {
        "arquivos": {"sintetico": str(args.sintetico.relative_to(ROOT)), "real": str(args.real.relative_to(ROOT))},
        "n": {"sintetico": int(len(sint)), "real": int(len(real))},
        "numericas": numericas,
        "categoricas": categoricas,
        "modelos_base_real": modelos_base_real(real, args.seed),
    }
    resultado["figuras"] = figuras(sint, real, numericas, categoricas)
    saida = args.real.parent.parent
    (saida / "comparacao_sintetico_real.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    texto = markdown(resultado)
    (saida / "comparacao_sintetico_real.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
