"""privacy_guard — camada de proteção contra dados pessoais.

Responsabilidades:
1. Bloquear campos de identificação direta (CPF, RG, CNS, prontuário, telefone,
   e-mail, endereço, nome, data de nascimento) — pelo NOME da coluna/chave.
2. Detectar CONTEÚDO com formato de dado pessoal em colunas de texto (CPF,
   e-mail, telefone, CEP, sequências numéricas longas como CNS).
3. Emitir alerta (logging WARNING + registro técnico na auditoria).
4. Impedir exportação quando houver violação (PrivacyViolationError).
5. Nunca registrar VALORES nos logs: somente nomes de colunas, categorias e contagens.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from app.dataset_schema import DATA_TYPE, FIELDS_BY_NAME, PATIENT_ID_PATTERN

logger = logging.getLogger("privacy_guard")

# Categoria -> nomes proibidos (já normalizados: minúsculas, sem acento, "_" como separador).
# Entradas de uma palavra casam com qualquer token do nome da coluna ("cpf_paciente" -> cpf);
# entradas compostas casam como sequência contígua de tokens ("numero_prontuario").
FORBIDDEN_FIELDS: dict[str, tuple[str, ...]] = {
    "CPF": ("cpf",),
    "RG": ("rg", "identidade", "registro_geral"),
    "CNS": ("cns", "cartao_sus", "cartao_nacional_de_saude", "cartao_nacional_saude", "cartaosus"),
    "PRONTUARIO": ("prontuario", "numero_prontuario", "medical_record", "mrn"),
    "TELEFONE": ("telefone", "celular", "fone", "phone", "telephone", "mobile", "whatsapp"),
    "EMAIL": ("email", "mail", "correio_eletronico"),
    "ENDERECO": ("endereco", "logradouro", "rua", "cep", "address", "street", "zip", "zipcode", "bairro", "complemento"),
    "NOME": ("nome", "name", "full_name", "first_name", "last_name", "sobrenome", "nome_completo", "nome_social", "nome_mae", "nome_pai"),
    "DATA_NASCIMENTO": ("data_nascimento", "nascimento", "birth_date", "birthdate", "dob", "date_of_birth", "data_de_nascimento"),
}

# Padrões de conteúdo. Os limites (?<![\w.@-]) / (?![\w@-]) evitam casar trechos de outros tokens.
VALUE_PATTERNS: dict[str, re.Pattern[str]] = {
    "CPF": re.compile(r"(?<![\w.@-])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\w@-])"),
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "TELEFONE": re.compile(r"(?<![\w-])(?:\(?\d{2}\)?\s?)?9?\d{4}-\d{4}(?![\w-])"),
    "CEP": re.compile(r"(?<![\w-])\d{5}-\d{3}(?![\w-])"),
    "IDENTIFICADOR_NUMERICO_LONGO": re.compile(r"(?<![\w.-])\d{10,15}(?![\w-])"),
}

_PATIENT_ID_RE = re.compile(PATIENT_ID_PATTERN)


class PrivacyViolationError(Exception):
    """Lançada quando um dataset viola as regras de privacidade."""

    def __init__(self, report: dict):
        self.report = report
        super().__init__(
            "Dataset bloqueado pelo privacy_guard: " + ", ".join(report.get("blocked_fields", []) or report.get("warnings", []))
        )


def normalize_name(name: str) -> str:
    """"Número do Prontuário" -> "numero_do_prontuario"; "patientName" -> "patient_name"."""
    texto = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name))
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower()


def classify_field(name: str) -> str | None:
    """Retorna a categoria proibida de um nome de campo, ou None se for permitido."""
    normalizado = normalize_name(name)
    if not normalizado:
        return None
    tokens = normalizado.split("_")
    juntos = "_".join(tokens)
    for categoria, proibidos in FORBIDDEN_FIELDS.items():
        for proibido in proibidos:
            partes = proibido.split("_")
            if len(partes) == 1:
                if proibido in tokens or juntos == proibido:
                    return categoria
            else:
                for i in range(len(tokens) - len(partes) + 1):
                    if tokens[i:i + len(partes)] == partes:
                        return categoria
    return None


def find_forbidden_fields(fields: Iterable[str]) -> list[dict[str, str]]:
    return [{"field": str(f), "category": c} for f in fields if (c := classify_field(f))]


def check_payload_keys(payload: Any, _prefix: str = "") -> list[dict[str, str]]:
    """Procura chaves proibidas em qualquer nível de um payload JSON (dict/list)."""
    encontrados: list[dict[str, str]] = []
    if isinstance(payload, Mapping):
        for chave, valor in payload.items():
            caminho = f"{_prefix}.{chave}" if _prefix else str(chave)
            if categoria := classify_field(str(chave)):
                encontrados.append({"field": caminho, "category": categoria})
            encontrados.extend(check_payload_keys(valor, caminho))
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            encontrados.extend(check_payload_keys(item, f"{_prefix}[{i}]"))
    return encontrados


def scan_values(df: pd.DataFrame, max_rows: int | None = None) -> list[dict[str, Any]]:
    """Procura valores com formato de dado pessoal nas colunas de texto.

    Retorna apenas coluna, categoria e quantidade de ocorrências — nunca o valor.
    """
    achados: list[dict[str, Any]] = []
    amostra = df if max_rows is None or len(df) <= max_rows else df.sample(max_rows, random_state=0)
    for coluna in amostra.columns:
        serie = amostra[coluna]
        if not (pd.api.types.is_object_dtype(serie) or pd.api.types.is_string_dtype(serie)):
            continue
        textos = serie.dropna().astype(str)
        if coluna == "patient_id":
            invalidos = int((~textos.str.match(_PATIENT_ID_RE)).sum())
            if invalidos:
                achados.append({"field": coluna, "category": "PATIENT_ID_FORA_DO_PADRAO_SINTETICO", "count": invalidos})
            continue
        # Aplica as expressões só nos valores distintos e pondera pela frequência
        # (colunas categóricas têm poucos valores distintos mesmo com 100 mil linhas).
        frequencias = textos.value_counts()
        distintos = frequencias.index.to_series()
        for categoria, padrao in VALUE_PATTERNS.items():
            ocorrencias = int(frequencias[distintos.str.contains(padrao, regex=True).to_numpy()].sum())
            if ocorrencias:
                achados.append({"field": coluna, "category": categoria, "count": ocorrencias})
    return achados


def _to_dataframe(dataset: Any) -> pd.DataFrame:
    if isinstance(dataset, pd.DataFrame):
        return dataset
    if isinstance(dataset, Mapping):
        return pd.DataFrame(dataset)
    if isinstance(dataset, list):
        return pd.DataFrame.from_records(dataset)
    raise TypeError("dataset deve ser DataFrame, dict de colunas ou lista de registros")


def validate_privacy(dataset: Any) -> dict[str, Any]:
    """Valida um dataset e retorna {"compliant": bool, "blocked_fields": [...], "warnings": [...]}.

    - blocked_fields: colunas proibidas pelo nome ou com conteúdo de dado pessoal.
    - warnings: problemas de governança (marcação SYNTHETIC ausente, colunas fora do
      dicionário, dataset vazio). Marcação SYNTHETIC ausente também torna o dataset não conforme.
    """
    df = _to_dataframe(dataset)
    blocked: list[str] = []
    warnings: list[str] = []
    marcacao_ok = True

    for item in find_forbidden_fields(df.columns):
        blocked.append(f"{item['field']} ({item['category']})")

    colunas_bloqueadas = {b.split(" (")[0] for b in blocked}
    for item in scan_values(df.drop(columns=[c for c in df.columns if c in colunas_bloqueadas])):
        blocked.append(f"{item['field']} (conteúdo com formato de {item['category']}: {item['count']} ocorrência(s))")

    if df.empty:
        warnings.append("Dataset vazio.")
    if "data_type" not in df.columns:
        marcacao_ok = False
        warnings.append("Coluna obrigatória 'data_type' ausente: o dataset precisa ser marcado como SYNTHETIC.")
    elif not df.empty and not (df["data_type"].astype(str) == DATA_TYPE).all():
        marcacao_ok = False
        warnings.append("Há registros com data_type diferente de 'SYNTHETIC'.")
    if "research_only" not in df.columns:
        marcacao_ok = False
        warnings.append("Coluna obrigatória 'research_only' ausente.")
    elif not df.empty and not df["research_only"].astype(bool).all():
        marcacao_ok = False
        warnings.append("Há registros com research_only diferente de true.")

    desconhecidas = [c for c in df.columns if c not in FIELDS_BY_NAME and c not in colunas_bloqueadas]
    if desconhecidas:
        warnings.append(f"Colunas fora do dicionário de dados (revisar antes de usar): {', '.join(map(str, desconhecidas))}")

    report = {"compliant": not blocked and marcacao_ok, "blocked_fields": blocked, "warnings": warnings}
    if blocked or not marcacao_ok:
        emit_alert("dataset_validation", report)
    return report


def assert_privacy(dataset: Any) -> dict[str, Any]:
    """Valida e lança PrivacyViolationError se o dataset não estiver conforme."""
    report = validate_privacy(dataset)
    if not report["compliant"]:
        raise PrivacyViolationError(report)
    return report


def emit_alert(context: str, report: dict[str, Any]) -> None:
    """Alerta técnico: registra apenas nomes de campos/categorias, nunca valores."""
    logger.warning(
        "ALERTA DE PRIVACIDADE [%s]: %d campo(s) bloqueado(s), %d aviso(s). Campos: %s",
        context,
        len(report.get("blocked_fields", [])),
        len(report.get("warnings", [])),
        "; ".join(report.get("blocked_fields", [])) or "-",
    )
