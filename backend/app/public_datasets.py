"""Base pública REAL e anonimizada, mantida separada do dataset sintético.

UCI Heart Disease — subconjunto Cleveland (303 pacientes, 14 atributos).
Coletada na Cleveland Clinic Foundation (1988); nomes e números de documento
foram removidos na origem pelos mantenedores do repositório. Licença CC BY 4.0.

Este módulo NUNCA mistura esses registros com os sintéticos: eles têm
data_type = "REAL_PUBLIC_ANONYMIZED", identificador próprio (UCI-CLE-...) e
ficam em data/real_public/. Servem para comparar distribuições e como
referência de desempenho em dados reais.
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PUBLIC_DATA_TYPE = "REAL_PUBLIC_ANONYMIZED"

UCI_HEART = {
    "nome": "UCI Heart Disease — Cleveland",
    "url_download": "https://archive.ics.uci.edu/static/public/45/heart+disease.zip",
    "pagina": "https://archive.ics.uci.edu/dataset/45/heart+disease",
    "arquivo": "processed.cleveland.data",
    "sha256": "a74b7efa387bc9d108d7d0115d831fe9b414b29ae7124f331b622b4efa0427c8",
    "doi": "10.24432/C52P4X",
    "licenca": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
    "citacao": "Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1989). Heart Disease [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X",
    "origem": "Cleveland Clinic Foundation (pesquisador responsável: Robert Detrano, M.D., Ph.D.), coleta de 1988",
    "anonimizacao": "Segundo a documentação do repositório (heart-disease.names), nomes e números de seguridade social dos pacientes foram removidos e substituídos por valores fictícios. O arquivo processado contém apenas 14 atributos clínicos, sem identificadores.",
}

RAW_COLUMNS = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal", "num"]

TIPO_DOR = {1: "ANGINA_TIPICA", 2: "ANGINA_ATIPICA", 3: "DOR_NAO_ANGINOSA", 4: "ASSINTOMATICO"}
ECG_REPOUSO = {0: "NORMAL", 1: "ANORMALIDADE_ST_T", 2: "HIPERTROFIA_VE"}
INCLINACAO_ST = {1: "ASCENDENTE", 2: "PLANA", 3: "DESCENDENTE"}
CINTILOGRAFIA = {3: "NORMAL", 6: "DEFEITO_FIXO", 7: "DEFEITO_REVERSIVEL"}


@dataclass(frozen=True)
class PublicField:
    name: str
    original: str | None
    dtype: str
    description: str
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    nullable: bool = False


PUBLIC_FIELDS: tuple[PublicField, ...] = (
    PublicField("registro_id", None, "string", "Identificador sequencial criado neste projeto (UCI-CLE-0001…). Não existe na base original."),
    PublicField("idade", "age", "int", "Idade em anos.", "anos", 18, 100),
    PublicField("sexo", "sex", "category", "Sexo (original: 1 = masculino, 0 = feminino).", None),
    PublicField("tipo_dor_toracica", "cp", "category", "Tipo de dor torácica: angina típica, atípica, dor não anginosa ou assintomático."),
    PublicField("pa_sistolica_repouso", "trestbps", "int", "Pressão arterial sistólica em repouso na admissão.", "mmHg", 70, 250),
    PublicField("colesterol_total", "chol", "int", "Colesterol sérico total.", "mg/dL", 80, 700),
    PublicField("glicemia_jejum_maior_120", "fbs", "bool", "Glicemia de jejum > 120 mg/dL."),
    PublicField("ecg_repouso", "restecg", "category", "Eletrocardiograma em repouso: normal, anormalidade ST-T ou hipertrofia ventricular esquerda."),
    PublicField("freq_cardiaca_maxima", "thalach", "int", "Frequência cardíaca máxima atingida no teste de esforço.", "bpm", 60, 220),
    PublicField("angina_exercicio", "exang", "bool", "Angina induzida pelo exercício."),
    PublicField("depressao_st", "oldpeak", "float", "Depressão do segmento ST induzida pelo exercício em relação ao repouso.", "mm", 0, 10),
    PublicField("inclinacao_st", "slope", "category", "Inclinação do segmento ST no pico do exercício."),
    PublicField("n_vasos_fluoroscopia", "ca", "int", "Número de vasos principais (0–3) coloridos na fluoroscopia.", "vasos", 0, 3, nullable=True),
    PublicField("cintilografia_talio", "thal", "category", "Resultado da cintilografia com tálio: normal, defeito fixo ou reversível.", nullable=True),
    PublicField("grau_doenca", "num", "int", "Diagnóstico angiográfico original (0 = sem estreitamento > 50%; 1–4 = presença, por grau).", None, 0, 4),
    PublicField("doenca_cardiaca", None, "bool", "Alvo binário derivado: grau_doenca > 0 (convenção usada na literatura)."),
    PublicField("fonte", None, "string", "Nome da base de origem."),
    PublicField("data_type", None, "category", f"Marcação obrigatória: {PUBLIC_DATA_TYPE} (dado real, público e anonimizado na origem)."),
    PublicField("research_only", None, "bool", "Uso exclusivo em pesquisa (sempre true)."),
)
PUBLIC_COLUMNS = [f.name for f in PUBLIC_FIELDS]


def sha256_bytes(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def download_uci_heart(timeout: int = 60) -> bytes:
    """Baixa o pacote oficial da UCI e devolve o conteúdo de processed.cleveland.data,
    conferindo o SHA-256 (garante que é exatamente o arquivo documentado)."""
    with urllib.request.urlopen(UCI_HEART["url_download"], timeout=timeout) as resposta:
        pacote = resposta.read()
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        conteudo = z.read(UCI_HEART["arquivo"])
    verify_checksum(conteudo)
    return conteudo


def verify_checksum(conteudo: bytes) -> None:
    obtido = sha256_bytes(conteudo)
    if obtido != UCI_HEART["sha256"]:
        raise ValueError(f"SHA-256 inesperado para {UCI_HEART['arquivo']}: {obtido} (esperado {UCI_HEART['sha256']})")


def parse_cleveland(conteudo: bytes | str) -> pd.DataFrame:
    """Converte o arquivo processado (CSV sem cabeçalho, '?' = ausente) para o esquema em português."""
    texto = conteudo.decode("utf-8") if isinstance(conteudo, bytes) else conteudo
    bruto = pd.read_csv(io.StringIO(texto), header=None, names=RAW_COLUMNS, na_values=["?", "-9", "-9.0"])
    if bruto.shape[1] != len(RAW_COLUMNS):
        raise ValueError("Arquivo com número de colunas inesperado")

    df = pd.DataFrame(
        {
            "registro_id": [f"UCI-CLE-{i:04d}" for i in range(1, len(bruto) + 1)],
            "idade": bruto["age"].astype(int),
            "sexo": bruto["sex"].map({1.0: "M", 0.0: "F"}),
            "tipo_dor_toracica": bruto["cp"].map(TIPO_DOR),
            "pa_sistolica_repouso": bruto["trestbps"].astype(int),
            "colesterol_total": bruto["chol"].astype(int),
            "glicemia_jejum_maior_120": bruto["fbs"].astype(int).astype(bool),
            "ecg_repouso": bruto["restecg"].map(ECG_REPOUSO),
            "freq_cardiaca_maxima": bruto["thalach"].astype(int),
            "angina_exercicio": bruto["exang"].astype(int).astype(bool),
            "depressao_st": bruto["oldpeak"].astype(float),
            "inclinacao_st": bruto["slope"].map(INCLINACAO_ST),
            "n_vasos_fluoroscopia": bruto["ca"].astype("Int64"),
            "cintilografia_talio": bruto["thal"].map(CINTILOGRAFIA),
            "grau_doenca": bruto["num"].astype(int),
        }
    )
    df["doenca_cardiaca"] = df["grau_doenca"] > 0
    df["fonte"] = UCI_HEART["nome"]
    df["data_type"] = PUBLIC_DATA_TYPE
    df["research_only"] = True
    return df[PUBLIC_COLUMNS]


def public_quality(df: pd.DataFrame) -> dict[str, Any]:
    """Qualidade da base real: diferente da sintética, ausências são esperadas e só reportadas."""
    problemas = []
    ausentes = {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()}
    for f in PUBLIC_FIELDS:
        if f.name not in df.columns:
            problemas.append(f"coluna ausente: {f.name}")
            continue
        if f.dtype in ("int", "float") and (f.min is not None or f.max is not None):
            valores = pd.to_numeric(df[f.name], errors="coerce")
            fora = ((valores < f.min) | (valores > f.max)).sum()
            if fora:
                problemas.append(f"{int(fora)} valor(es) de {f.name} fora de [{f.min}, {f.max}]")
        if not f.nullable and df[f.name].isna().any():
            problemas.append(f"valores ausentes em coluna obrigatória: {f.name}")
    duplicados = int(df["registro_id"].duplicated().sum())
    if duplicados:
        problemas.append(f"{duplicados} registro_id duplicado(s)")
    return {
        "passed": not problemas,
        "n_records": int(len(df)),
        "problems": problemas,
        "missing_values": ausentes,
        "registros_completos": int(df.dropna().shape[0]),
        "prevalencia_doenca_cardiaca": round(float(df["doenca_cardiaca"].mean()), 4),
    }


def build_public_metadata(df: pd.DataFrame, privacy: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_name": UCI_HEART["nome"],
        "data_type": PUBLIC_DATA_TYPE,
        "synthetic": False,
        "real_data": True,
        "publicly_available": True,
        "anonymized_at_source": True,
        "research_only": True,
        "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_records": int(len(df)),
        "source": {k: UCI_HEART[k] for k in ("pagina", "url_download", "arquivo", "sha256", "doi", "licenca", "citacao", "origem", "anonimizacao")},
        "transformations": [
            "Renomeação das 14 colunas para português e decodificação das categorias numéricas em rótulos.",
            "Valores '?' tratados como ausentes (n_vasos_fluoroscopia e cintilografia_talio).",
            "Criação de registro_id sequencial próprio, de doenca_cardiaca (grau_doenca > 0) e das colunas de marcação.",
            "Nenhum registro foi alterado, removido, combinado com outra fonte ou enriquecido.",
        ],
        "fields": [
            {"name": f.name, "original_attribute": f.original, "type": f.dtype, "unit": f.unit, "description": f.description}
            for f in PUBLIC_FIELDS
        ],
        "privacy_validation": privacy,
        "quality": quality,
        "separation_from_synthetic": "Mantido em data/real_public/, com data_type próprio; nunca concatenado ao dataset sintético.",
    }


def build_public_card(df: pd.DataFrame, metadata: dict[str, Any]) -> str:
    q = metadata["quality"]
    linhas = [
        f"# Dataset Card — {UCI_HEART['nome']} (base pública real)",
        "",
        f"> **DADOS REAIS, PÚBLICOS E ANONIMIZADOS NA ORIGEM** · `data_type = {PUBLIC_DATA_TYPE}` · separados do dataset sintético",
        "",
        "## Origem",
        "",
        f"- **Repositório:** UCI Machine Learning Repository — {UCI_HEART['pagina']}",
        f"- **Coleta:** {UCI_HEART['origem']}",
        f"- **Licença:** {UCI_HEART['licenca']}",
        f"- **DOI:** https://doi.org/{UCI_HEART['doi']}",
        f"- **Arquivo usado:** `{UCI_HEART['arquivo']}` (SHA-256 `{UCI_HEART['sha256']}`)",
        "",
        "**Citação obrigatória (CC BY 4.0):**",
        "",
        f"> {UCI_HEART['citacao']}",
        "",
        "## Anonimização",
        "",
        UCI_HEART["anonimizacao"],
        "Este projeto não adicionou nenhum identificador pessoal: `registro_id` é um número sequencial criado aqui.",
        "",
        "## Conteúdo",
        "",
        f"- Registros: **{q['n_records']}** (completos: {q['registros_completos']}).",
        f"- Prevalência de doença cardíaca (grau_doenca > 0): **{100 * q['prevalencia_doenca_cardiaca']:.1f}%**.",
        f"- Valores ausentes: {', '.join(f'{k}: {v}' for k, v in q['missing_values'].items()) or 'nenhum'}.",
        "",
        "| Variável | Atributo original | Tipo | Unidade | Descrição |",
        "|---|---|---|---|---|",
        *[f"| `{f.name}` | {f.original or '—'} | {f.dtype} | {f.unit or '-'} | {f.description} |" for f in PUBLIC_FIELDS],
        "",
        "## Usos neste projeto",
        "",
        "- Comparar distribuições das variáveis em comum com o dataset sintético (idade, sexo, pressão sistólica, colesterol, glicemia).",
        "- Servir de referência de desempenho de modelos em dados reais (alvo: `doenca_cardiaca`).",
        "",
        "## Limitações",
        "",
        "- Amostra pequena (303) de um único centro nos EUA, coletada em 1988; não representa a população brasileira atual.",
        "- Pacientes encaminhados para angiografia: há viés de seleção (prevalência de doença muito maior que na população geral).",
        "- Predominância masculina (≈ 68%).",
        "- As variáveis não são idênticas às do dataset sintético (ex.: frequência cardíaca máxima no esforço × frequência em repouso).",
        "",
    ]
    return "\n".join(linhas)


def summary_numeric(serie: pd.Series) -> dict[str, float]:
    s = pd.to_numeric(serie, errors="coerce").dropna()
    return {"n": int(s.size), "media": round(float(s.mean()), 2), "dp": round(float(s.std()), 2), "mediana": round(float(s.median()), 2), "min": float(s.min()), "max": float(s.max())}


def standardized_mean_difference(a: pd.Series, b: pd.Series) -> float:
    """SMD = (média_a − média_b) / sqrt((dp_a² + dp_b²) / 2)."""
    a, b = pd.to_numeric(a, errors="coerce").dropna(), pd.to_numeric(b, errors="coerce").dropna()
    return round(float((a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)), 3)
