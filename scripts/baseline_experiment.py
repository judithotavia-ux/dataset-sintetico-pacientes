"""Experimento de referência (baseline) de Machine Learning no dataset sintético.

Mostra como usar as partições train/validation/test e serve de ponto de partida
para a pesquisa. Tarefas:
    1. Classificação binária: desfecho_adverso
    2. Classificação multiclasse: classificacao_risco
    3. Regressão: pa_sistolica

Uso:
    python scripts/baseline_experiment.py --input data/synthetic_dataset.csv --seed 42

Grava baseline_results.md e baseline_results.json na pasta do arquivo de entrada.
Os resultados medem a capacidade de recuperar a estrutura do GERADOR e não têm
validade clínica.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Aviso inofensivo de compatibilidade entre scikit-learn 1.6 e SciPy >= 1.15 ("Unknown solver options: iprint").
warnings.filterwarnings("ignore", message="Unknown solver options")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.dataset_schema import CLASSIFICACAO_RISCO, DISCLAIMER, FIELDS  # noqa: E402

# Colunas que são alvos ou derivadas dos alvos (vazamento) nunca entram como preditores.
TARGET_AND_LEAKAGE = {"escore_risco", "classificacao_risco", "diagnostico_sintetico", "resultado_desfecho", "desfecho_adverso"}
NUMERIC = [f.name for f in FIELDS if f.ml_role == "feature" and f.dtype in ("int", "float") and f.name not in TARGET_AND_LEAKAGE]
CATEGORICAL = [f.name for f in FIELDS if f.ml_role == "feature" and f.dtype in ("category", "bool") and f.name not in TARGET_AND_LEAKAGE]


def preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
        ]
    )


def load_splits(path: Path) -> dict[str, pd.DataFrame]:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, keep_default_na=False, na_values=[""])
    for col in CATEGORICAL:
        df[col] = df[col].astype(str)
    return {nome: df[df["split"] == nome].reset_index(drop=True) for nome in ("train", "validation", "test")}


def best_threshold(y_true: np.ndarray, proba: np.ndarray) -> float:
    candidatos = np.linspace(0.05, 0.95, 91)
    return float(max(candidatos, key=lambda t: f1_score(y_true, proba >= t, zero_division=0)))


def binary_task(splits, seed) -> dict:
    alvo = "desfecho_adverso"
    X = {k: v[NUMERIC + CATEGORICAL] for k, v in splits.items()}
    y = {k: v[alvo].astype(str).str.lower().isin(["true", "1"]).astype(int).to_numpy() for k, v in splits.items()}
    modelos = {
        "Dummy (classe majoritária)": DummyClassifier(strategy="prior"),
        "Regressão logística": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=seed, n_jobs=-1),
    }
    resultados = {}
    for nome, modelo in modelos.items():
        pipe = Pipeline([("prep", preprocessor(NUMERIC, CATEGORICAL)), ("model", modelo)]).fit(X["train"], y["train"])
        limiar = best_threshold(y["validation"], pipe.predict_proba(X["validation"])[:, 1])
        proba = pipe.predict_proba(X["test"])[:, 1]
        pred = (proba >= limiar).astype(int)
        resultados[nome] = {
            "roc_auc": round(roc_auc_score(y["test"], proba), 4),
            "pr_auc": round(average_precision_score(y["test"], proba), 4),
            "f1": round(f1_score(y["test"], pred, zero_division=0), 4),
            "balanced_accuracy": round(balanced_accuracy_score(y["test"], pred), 4),
            "brier": round(brier_score_loss(y["test"], proba), 4),
            "limiar_escolhido_na_validacao": round(limiar, 2),
        }
    return {"alvo": alvo, "prevalencia_teste": round(float(y["test"].mean()), 4), "modelos": resultados}


def multiclass_task(splits, seed) -> dict:
    alvo = "classificacao_risco"
    X = {k: v[NUMERIC + CATEGORICAL] for k, v in splits.items()}
    y = {k: v[alvo].to_numpy() for k, v in splits.items()}
    modelos = {
        "Dummy (classe majoritária)": DummyClassifier(strategy="most_frequent"),
        "Regressão logística multinomial": LogisticRegression(max_iter=3000),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=seed, n_jobs=-1),
    }
    resultados = {}
    melhor_cm = None
    for nome, modelo in modelos.items():
        pipe = Pipeline([("prep", preprocessor(NUMERIC, CATEGORICAL)), ("model", modelo)]).fit(X["train"], y["train"])
        pred = pipe.predict(X["test"])
        resultados[nome] = {
            "accuracy": round(accuracy_score(y["test"], pred), 4),
            "macro_f1": round(f1_score(y["test"], pred, average="macro"), 4),
            "balanced_accuracy": round(balanced_accuracy_score(y["test"], pred), 4),
            "validation_macro_f1": round(f1_score(y["validation"], pipe.predict(X["validation"]), average="macro"), 4),
        }
        if nome == "Random Forest":
            melhor_cm = confusion_matrix(y["test"], pred, labels=list(CLASSIFICACAO_RISCO)).tolist()
    return {"alvo": alvo, "modelos": resultados, "matriz_confusao_random_forest": {"labels": list(CLASSIFICACAO_RISCO), "matriz": melhor_cm}}


def regression_task(splits, seed) -> dict:
    alvo = "pa_sistolica"
    # pa_diastolica é gerada a partir da sistólica: fica de fora para não vazar o alvo.
    numericas = [c for c in NUMERIC if c not in (alvo, "pa_diastolica")]
    X = {k: v[numericas + CATEGORICAL] for k, v in splits.items()}
    y = {k: v[alvo].astype(float).to_numpy() for k, v in splits.items()}
    modelos = {
        "Dummy (média)": DummyRegressor(),
        "Ridge": Ridge(alpha=1.0),
        "Random Forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=seed, n_jobs=-1),
    }
    resultados = {}
    for nome, modelo in modelos.items():
        pipe = Pipeline([("prep", preprocessor(numericas, CATEGORICAL)), ("model", modelo)]).fit(X["train"], y["train"])
        pred = pipe.predict(X["test"])
        resultados[nome] = {
            "mae": round(mean_absolute_error(y["test"], pred), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(y["test"], pred))), 3),
            "r2": round(r2_score(y["test"], pred), 4),
            "validation_r2": round(r2_score(y["validation"], pipe.predict(X["validation"])), 4),
        }
    return {"alvo": alvo, "unidade": "mmHg", "modelos": resultados}


def to_markdown(resultados: dict, input_path: Path, seed: int, tamanhos: dict) -> str:
    linhas = [
        "# Resultados do experimento de referência (baseline)",
        "",
        f"> **{DISCLAIMER}** — as métricas medem a capacidade dos modelos de recuperar a estrutura do gerador sintético; não têm validade clínica.",
        "",
        f"- Arquivo: `{input_path.name}` · seed dos modelos: `{seed}`",
        f"- Partições: treino {tamanhos['train']}, validação {tamanhos['validation']}, teste {tamanhos['test']} (métricas reportadas no **teste**)",
        f"- Preditores: {len(NUMERIC)} numéricos + {len(CATEGORICAL)} categóricos/booleanos (excluídos alvos e variáveis derivadas deles)",
        "",
    ]
    b = resultados["classificacao_binaria"]
    linhas += [
        f"## 1. Classificação binária — `{b['alvo']}` (prevalência no teste: {100 * b['prevalencia_teste']:.1f}%)",
        "",
        "| Modelo | ROC-AUC | PR-AUC | F1 | Acurácia balanceada | Brier | Limiar (validação) |",
        "|---|---|---|---|---|---|---|",
        *[f"| {n} | {m['roc_auc']} | {m['pr_auc']} | {m['f1']} | {m['balanced_accuracy']} | {m['brier']} | {m['limiar_escolhido_na_validacao']} |" for n, m in b["modelos"].items()],
        "",
    ]
    mc = resultados["classificacao_multiclasse"]
    linhas += [
        f"## 2. Classificação multiclasse — `{mc['alvo']}`",
        "",
        "| Modelo | Acurácia | Macro-F1 | Acurácia balanceada | Macro-F1 (validação) |",
        "|---|---|---|---|---|",
        *[f"| {n} | {m['accuracy']} | {m['macro_f1']} | {m['balanced_accuracy']} | {m['validation_macro_f1']} |" for n, m in mc["modelos"].items()],
        "",
        "Matriz de confusão (Random Forest, linhas = real, colunas = previsto):",
        "",
        "| | " + " | ".join(mc["matriz_confusao_random_forest"]["labels"]) + " |",
        "|---|" + "---|" * len(mc["matriz_confusao_random_forest"]["labels"]),
        *[f"| **{lab}** | " + " | ".join(map(str, linha)) + " |" for lab, linha in zip(mc["matriz_confusao_random_forest"]["labels"], mc["matriz_confusao_random_forest"]["matriz"])],
        "",
    ]
    r = resultados["regressao"]
    linhas += [
        f"## 3. Regressão — `{r['alvo']}` ({r['unidade']})",
        "",
        "| Modelo | MAE | RMSE | R² | R² (validação) |",
        "|---|---|---|---|---|",
        *[f"| {n} | {m['mae']} | {m['rmse']} | {m['r2']} | {m['validation_r2']} |" for n, m in r["modelos"].items()],
        "",
        "## Leitura",
        "",
        "- Os modelos superam claramente as baselines *dummy*, o que confirma que o dataset contém relações aprendíveis.",
        "- O desempenho não é perfeito porque o gerador inclui ruído aleatório em cada etapa, como em dados observacionais.",
        "- Use estes números apenas como referência para comparar métodos dentro da pesquisa.",
        "",
    ]
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Experimento baseline de ML no dataset sintético.")
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "synthetic_dataset.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    splits = load_splits(args.input)
    tamanhos = {k: len(v) for k, v in splits.items()}
    print(f"[!] {DISCLAIMER}\nPartições: {tamanhos}")
    resultados = {
        "classificacao_binaria": binary_task(splits, args.seed),
        "classificacao_multiclasse": multiclass_task(splits, args.seed),
        "regressao": regression_task(splits, args.seed),
    }
    saida = args.input.parent
    (saida / "baseline_results.json").write_text(json.dumps({"seed": args.seed, "tamanhos": tamanhos, **resultados}, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = to_markdown(resultados, args.input, args.seed, tamanhos)
    (saida / "baseline_results.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
