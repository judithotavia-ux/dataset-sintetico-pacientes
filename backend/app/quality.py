"""Validação de qualidade do dataset e relatório de qualidade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.dataset_schema import COLUMN_ORDER, FIELDS, FIELDS_BY_NAME, PATIENT_ID_PATTERN
from app.generator import calculate_bmi_series

BMI_TOLERANCE = 0.05  # kg/m², margem para arredondamento


def _issue(check: str, message: str, column: str | None = None, count: int = 1, severity: str = "ERROR") -> dict[str, Any]:
    return {"check": check, "column": column, "count": int(count), "severity": severity, "message": message}


def check_columns(df: pd.DataFrame) -> list[dict[str, Any]]:
    issues = []
    faltando = [c for c in COLUMN_ORDER if c not in df.columns]
    if faltando:
        issues.append(_issue("colunas_ausentes", f"Colunas obrigatórias ausentes: {', '.join(faltando)}", count=len(faltando)))
    return issues


def check_missing(df: pd.DataFrame) -> list[dict[str, Any]]:
    issues = []
    for coluna in df.columns:
        campo = FIELDS_BY_NAME.get(coluna)
        if campo is not None and campo.nullable:
            continue
        nulos = df[coluna].isna()
        if campo is not None and campo.dtype in ("string", "category", "date"):
            nulos = nulos | (df[coluna].astype(str).str.strip() == "")
        if (qtd := int(nulos.sum())):
            issues.append(_issue("valores_ausentes", f"{qtd} valor(es) ausente(s) em '{coluna}'", coluna, qtd))
    return issues


def check_types(df: pd.DataFrame) -> list[dict[str, Any]]:
    issues = []
    for campo in FIELDS:
        if campo.name not in df.columns:
            continue
        serie = df[campo.name]
        ok = True
        if campo.dtype == "int":
            ok = pd.api.types.is_integer_dtype(serie)
        elif campo.dtype == "float":
            ok = pd.api.types.is_float_dtype(serie) or pd.api.types.is_integer_dtype(serie)
        elif campo.dtype == "bool":
            ok = pd.api.types.is_bool_dtype(serie)
        elif campo.dtype in ("string", "category"):
            ok = pd.api.types.is_object_dtype(serie) or pd.api.types.is_string_dtype(serie)
            if ok:
                nao_texto = int(serie.dropna().map(lambda v: not isinstance(v, str)).sum())
                ok = nao_texto == 0
        elif campo.dtype == "date":
            convertido = pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce")
            if (invalidas := int(convertido.isna().sum() - serie.isna().sum())):
                issues.append(_issue("tipo_incorreto", f"{invalidas} data(s) inválida(s) em '{campo.name}' (esperado AAAA-MM-DD)", campo.name, invalidas))
            continue
        if not ok:
            issues.append(_issue("tipo_incorreto", f"'{campo.name}' deveria ser do tipo {campo.dtype} (atual: {serie.dtype})", campo.name, len(serie)))
    return issues


def check_ranges(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Valores impossíveis/fora do intervalo e categorias desconhecidas."""
    issues = []
    for campo in FIELDS:
        if campo.name not in df.columns:
            continue
        serie = df[campo.name]
        if campo.dtype in ("int", "float") and (campo.min is not None or campo.max is not None):
            numerica = pd.to_numeric(serie, errors="coerce")
            fora = pd.Series(False, index=serie.index)
            if campo.min is not None:
                fora |= numerica < campo.min
            if campo.max is not None:
                fora |= numerica > campo.max
            if (qtd := int(fora.sum())):
                nome_check = {
                    "idade": "idade_fora_do_intervalo",
                    "peso_kg": "peso_incompativel",
                    "altura_cm": "altura_incompativel",
                    "pa_sistolica": "pressao_arterial_invalida",
                    "pa_diastolica": "pressao_arterial_invalida",
                }.get(campo.name, "valor_impossivel")
                issues.append(_issue(nome_check, f"{qtd} valor(es) de '{campo.name}' fora de [{campo.min}, {campo.max}] {campo.unit or ''}".strip(), campo.name, qtd))
        if campo.categories:
            invalidas = ~serie.astype(str).isin(campo.categories)
            if (qtd := int(invalidas.sum())):
                issues.append(_issue("categoria_invalida", f"{qtd} valor(es) de '{campo.name}' fora das categorias permitidas", campo.name, qtd))
    return issues


def check_bmi(df: pd.DataFrame) -> list[dict[str, Any]]:
    if not {"peso_kg", "altura_cm", "imc"} <= set(df.columns):
        return []
    peso = pd.to_numeric(df["peso_kg"], errors="coerce")
    altura = pd.to_numeric(df["altura_cm"], errors="coerce")
    esperado = calculate_bmi_series(peso, altura)
    diferenca = np.abs(pd.to_numeric(df["imc"], errors="coerce") - esperado)
    incorretos = int((diferenca > BMI_TOLERANCE).sum())
    return [_issue("imc_incorreto", f"{incorretos} IMC(s) não conferem com peso/altura²", "imc", incorretos)] if incorretos else []


def check_blood_pressure(df: pd.DataFrame) -> list[dict[str, Any]]:
    if not {"pa_sistolica", "pa_diastolica"} <= set(df.columns):
        return []
    sis = pd.to_numeric(df["pa_sistolica"], errors="coerce")
    dia = pd.to_numeric(df["pa_diastolica"], errors="coerce")
    invertida = int((dia >= sis).sum())
    return [_issue("pressao_arterial_invalida", f"{invertida} registro(s) com diastólica >= sistólica", "pa_diastolica", invertida)] if invertida else []


def check_identifiers(df: pd.DataFrame) -> list[dict[str, Any]]:
    if "patient_id" not in df.columns:
        return []
    issues = []
    duplicados = int(df["patient_id"].duplicated().sum())
    if duplicados:
        issues.append(_issue("patient_id_duplicado", f"{duplicados} patient_id duplicado(s)", "patient_id", duplicados))
    fora_padrao = int((~df["patient_id"].astype(str).str.match(PATIENT_ID_PATTERN)).sum())
    if fora_padrao:
        issues.append(_issue("patient_id_invalido", f"{fora_padrao} patient_id fora do padrão SYN-XXXXXXXXXXXXXXXX", "patient_id", fora_padrao))
    return issues


def check_consistency(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Regras de coerência interna do modelo de geração."""
    issues = []
    if {"cond_obesidade", "imc"} <= set(df.columns):
        incoerente = int((df["cond_obesidade"].astype(bool) != (pd.to_numeric(df["imc"], errors="coerce") >= 30)).sum())
        if incoerente:
            issues.append(_issue("inconsistencia", f"{incoerente} registro(s) com cond_obesidade incoerente com o IMC", "cond_obesidade", incoerente))
    if {"resultado_desfecho", "desfecho_adverso"} <= set(df.columns):
        incoerente = int(((df["resultado_desfecho"] != "SEM_INTERCORRENCIA") != df["desfecho_adverso"].astype(bool)).sum())
        if incoerente:
            issues.append(_issue("inconsistencia", f"{incoerente} registro(s) com desfecho_adverso incoerente com resultado_desfecho", "desfecho_adverso", incoerente))
    if {"medicamentos", "n_medicamentos"} <= set(df.columns):
        contagem = df["medicamentos"].fillna("").astype(str).map(lambda s: len([m for m in s.split("; ") if m]))
        incoerente = int((contagem != pd.to_numeric(df["n_medicamentos"], errors="coerce")).sum())
        if incoerente:
            issues.append(_issue("inconsistencia", f"{incoerente} registro(s) com n_medicamentos incoerente", "n_medicamentos", incoerente))
    return issues


def validate_quality(df: pd.DataFrame) -> dict[str, Any]:
    """Executa todas as verificações e retorna {passed, n_records, issues, checks}."""
    verificacoes = {
        "colunas_obrigatorias": check_columns,
        "valores_ausentes": check_missing,
        "tipos_de_dados": check_types,
        "intervalos_e_categorias": check_ranges,
        "imc": check_bmi,
        "pressao_arterial": check_blood_pressure,
        "identificadores": check_identifiers,
        "consistencia_interna": check_consistency,
    }
    issues: list[dict[str, Any]] = []
    checks: dict[str, str] = {}
    for nome, funcao in verificacoes.items():
        encontrados = funcao(df)
        issues.extend(encontrados)
        checks[nome] = "OK" if not encontrados else "FALHOU"
    return {
        "passed": not any(i["severity"] == "ERROR" for i in issues),
        "n_records": int(len(df)),
        "checks": checks,
        "issues": issues,
    }


def descriptive_statistics(df: pd.DataFrame) -> dict[str, Any]:
    numericas = [f.name for f in FIELDS if f.dtype in ("int", "float") and f.name in df.columns]
    categoricas = [f.name for f in FIELDS if f.dtype in ("category", "bool") and f.name in df.columns and f.name not in ("data_type",)]
    numericas_desc = df[numericas].describe().T.round(2)
    return {
        "numericas": {
            col: {k: float(v) for k, v in numericas_desc.loc[col, ["mean", "std", "min", "25%", "50%", "75%", "max"]].items()}
            for col in numericas
        },
        "categoricas": {
            col: {str(k): int(v) for k, v in df[col].astype(str).value_counts().items()} for col in categoricas
        },
    }


def quality_report_markdown(df: pd.DataFrame, quality: dict[str, Any], privacy: dict[str, Any], dataset_info: dict[str, Any]) -> str:
    stats = descriptive_statistics(df)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    linhas = [
        "# Relatório de Qualidade — Dataset Sintético de Pacientes",
        "",
        "> **DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES**",
        "",
        f"- Gerado em: {agora}",
        f"- dataset_id: `{dataset_info.get('dataset_id', '-')}`",
        f"- Seed: `{dataset_info.get('seed', '-')}`",
        f"- Registros: **{quality['n_records']}**",
        f"- Qualidade: **{'APROVADO' if quality['passed'] else 'REPROVADO'}**",
        f"- Privacidade: **{'CONFORME' if privacy['compliant'] else 'NÃO CONFORME'}**",
        "",
        "## Verificações de qualidade",
        "",
        "| Verificação | Resultado |",
        "|---|---|",
        *[f"| {nome} | {res} |" for nome, res in quality["checks"].items()],
        "",
    ]
    if quality["issues"]:
        linhas += ["### Problemas encontrados", "", "| Check | Coluna | Qtd | Mensagem |", "|---|---|---|---|"]
        linhas += [f"| {i['check']} | {i['column'] or '-'} | {i['count']} | {i['message']} |" for i in quality["issues"]]
        linhas.append("")
    linhas += [
        "## Validação de privacidade (privacy_guard)",
        "",
        f"- compliant: `{str(privacy['compliant']).lower()}`",
        f"- blocked_fields: {privacy['blocked_fields'] or 'nenhum'}",
        f"- warnings: {privacy['warnings'] or 'nenhum'}",
        "",
        "## Estatísticas descritivas (variáveis numéricas)",
        "",
        "| Variável | Média | DP | Mín | P25 | Mediana | P75 | Máx |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for col, s in stats["numericas"].items():
        linhas.append(f"| {col} | {s['mean']} | {s['std']} | {s['min']} | {s['25%']} | {s['50%']} | {s['75%']} | {s['max']} |")
    linhas += ["", "## Distribuição das variáveis categóricas", ""]
    total = max(quality["n_records"], 1)
    for col, contagens in stats["categoricas"].items():
        partes = ", ".join(f"{k}: {v} ({100 * v / total:.1f}%)" for k, v in contagens.items())
        linhas.append(f"- **{col}** — {partes}")
    linhas.append("")
    return "\n".join(linhas)
