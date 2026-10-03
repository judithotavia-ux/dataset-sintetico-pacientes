"""metadata.json e Dataset Card."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.dataset_schema import (
    DATA_TYPE,
    DATASET_NAME,
    DATASET_VERSION,
    DISCLAIMER,
    FIELDS,
    GENERATOR_VERSION,
    SPLIT_RATIOS,
)

GENERATION_METHOD = (
    "Simulação estatística paramétrica com modelo causal simplificado e fictício: idade, sexo, hábitos "
    "de vida e histórico familiar influenciam IMC; estes influenciam a probabilidade (função logística) "
    "de condições clínicas; condições determinam medicamentos e aderência; sinais vitais e exames "
    "dependem das condições e do efeito do tratamento; um escore de risco sintético define a "
    "classificação de risco e a probabilidade de desfecho em 12 meses. Toda a aleatoriedade deriva de "
    "um único seed (NumPy Generator PCG64 + Faker pt_BR para identificadores e nomes de municípios "
    "inventados). Nenhum dado real foi usado como entrada, molde ou referência individual."
)

GROUP_LABELS = {
    "identificacao": "Identificação",
    "demografia": "Demografia",
    "antropometria": "Antropometria",
    "sinais_vitais": "Sinais vitais",
    "historico_familiar": "Histórico familiar",
    "habitos_de_vida": "Hábitos de vida",
    "condicao_clinica": "Condição clínica",
    "medicamentos": "Medicamentos",
    "exames_laboratoriais": "Exames laboratoriais",
    "atendimento": "Atendimento",
    "desfecho": "Risco, diagnóstico e desfecho",
    "ml": "Aprendizado de máquina",
    "governanca": "Governança",
}

LIMITATIONS = [
    "Os dados são inteiramente sintéticos: não representam nenhuma população real e não servem para estimar prevalências, riscos ou efeitos de tratamento reais.",
    "Os coeficientes do modelo de geração foram escolhidos para produzir valores plausíveis, não estimados de estudos clínicos; relações entre variáveis são simplificadas.",
    "O escore_risco e a classificacao_risco são construções sintéticas e NÃO equivalem a escores clínicos validados (ex.: Framingham, SCORE2).",
    "Variáveis independentes entre si no gerador (ex.: estado, municipio, data_atendimento) não carregam sinal preditivo.",
    "Não há séries temporais longitudinais: cada paciente possui um único atendimento fictício.",
    "Modelos treinados apenas com estes dados não devem ser usados em decisões clínicas nem considerados validados para uso real.",
    "Desempenho de modelos neste dataset reflete a estrutura do gerador; resultados precisam ser validados em dados reais devidamente autorizados antes de qualquer conclusão clínica.",
]


def build_metadata(df: pd.DataFrame, dataset_id: str, seed: int, privacy: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_name": DATASET_NAME,
        "dataset_id": dataset_id,
        "version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_records": int(len(df)),
        "seed": int(seed),
        "data_type": DATA_TYPE,
        "synthetic": True,
        "research_only": True,
        "contains_real_personal_data": False,
        "disclaimer": DISCLAIMER,
        "purpose": "Uso acadêmico: testes, treinamento e validação de sistemas de Inteligência Artificial em pesquisa de mestrado.",
        "generation_method": GENERATION_METHOD,
        "splits": {
            "strategy": "Estratificada por classificacao_risco",
            "ratios": SPLIT_RATIOS,
            "counts": {k: int(v) for k, v in df["split"].value_counts().items()} if "split" in df else {},
        },
        "fields": [
            {
                "name": f.name,
                "type": f.dtype,
                "description": f.description,
                "group": f.group,
                "unit": f.unit,
                "min": f.min,
                "max": f.max,
                "categories": list(f.categories) if f.categories else None,
                "ml_role": f.ml_role,
                "nullable": f.nullable,
            }
            for f in FIELDS
        ],
        "privacy_validation": privacy,
        "quality_validation": {"passed": quality["passed"], "checks": quality["checks"], "n_issues": len(quality["issues"])},
        "limitations": LIMITATIONS,
        "license": "MIT (código) — dados sintéticos de uso livre para pesquisa, mantida a identificação SYNTHETIC.",
    }


def build_dataset_card(df: pd.DataFrame, metadata: dict[str, Any]) -> str:
    n = metadata["n_records"]
    risco = df["classificacao_risco"].value_counts(normalize=True).mul(100).round(1).to_dict()
    desfecho = df["desfecho_adverso"].mean() * 100
    grupos: dict[str, list] = {}
    for f in FIELDS:
        grupos.setdefault(f.group, []).append(f)

    linhas = [
        f"# Dataset Card — {DATASET_NAME}",
        "",
        f"> **{DISCLAIMER}**",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Versão | {metadata['version']} |",
        f"| dataset_id | `{metadata['dataset_id']}` |",
        f"| Gerado em | {metadata['generated_at']} |",
        f"| Registros | {n} |",
        f"| Seed | {metadata['seed']} |",
        f"| data_type | `{DATA_TYPE}` |",
        "| research_only | `true` |",
        "",
        "## 1. Origem",
        "",
        "Dados **100% sintéticos**, produzidos por um gerador estatístico local. Nenhum prontuário, sistema de saúde, "
        "pesquisa populacional, rede social ou qualquer fonte com dados pessoais foi consultado, copiado ou usado como "
        "molde. Os identificadores (`patient_id`, prefixo `SYN-`) são aleatórios e os municípios têm nomes inventados.",
        "",
        "## 2. Finalidade",
        "",
        metadata["purpose"],
        "Serve para desenvolver e testar pipelines (ingestão, pré-processamento, treinamento, avaliação), comparar "
        "algoritmos em um ambiente controlado e ensinar/demonstrar técnicas de ML sem expor dados de pacientes.",
        "",
        "## 3. Variáveis",
        "",
    ]
    for grupo, campos in grupos.items():
        linhas += [f"### {GROUP_LABELS.get(grupo, grupo)}", "", "| Variável | Tipo | Unidade | Papel em ML | Descrição |", "|---|---|---|---|---|"]
        linhas += [f"| `{f.name}` | {f.dtype} | {f.unit or '-'} | {f.ml_role} | {f.description} |" for f in campos]
        linhas.append("")
    linhas += [
        "Alvos sugeridos: `desfecho_adverso` (classificação binária), `classificacao_risco` (multiclasse), "
        "`resultado_desfecho` (multiclasse desbalanceada), `escore_risco` / `pa_sistolica` / `hba1c` (regressão).",
        "",
        "Resumo deste arquivo: classificação de risco — "
        + ", ".join(f"{k}: {v}%" for k, v in risco.items())
        + f"; desfecho adverso em 12 meses: {desfecho:.1f}%.",
        "",
        "## 4. Método de geração",
        "",
        metadata["generation_method"],
        "",
        "Particionamento: 70% treino, 15% validação, 15% teste, estratificado por `classificacao_risco` (coluna `split`). "
        "O mesmo seed reproduz exatamente o mesmo dataset e a mesma partição.",
        "",
        "## 5. Limitações",
        "",
        *[f"- {item}" for item in metadata["limitations"]],
        "",
        "## 6. Riscos de uso",
        "",
        "- **Falsa sensação de validade clínica:** métricas altas aqui não indicam que um modelo funcionaria com pacientes reais.",
        "- **Vazamento de alvo:** `escore_risco`, `classificacao_risco`, `diagnostico_sintetico` e `resultado_desfecho` são derivados uns dos outros; não use um como preditor do outro sem intenção explícita.",
        "- **Viés do gerador:** o modelo reflete as escolhas do autor do gerador (coeficientes, categorias), não a realidade epidemiológica.",
        "- **Mistura com dados reais:** combinar este dataset com dados reais pode criar registros ambíguos; mantenha sempre `data_type = SYNTHETIC`.",
        "",
        "## 7. Usos permitidos",
        "",
        "- Pesquisa acadêmica, ensino e prototipagem de modelos de IA.",
        "- Testes de software, de pipelines de dados e de mecanismos de privacidade.",
        "- Análise exploratória, comparação de algoritmos, estudos de reprodutibilidade.",
        "",
        "## 8. Usos não recomendados",
        "",
        "- Apoio a decisão clínica, diagnóstico ou tratamento de pessoas reais.",
        "- Estimativa de prevalência, incidência ou risco de qualquer população real.",
        "- Publicação de resultados como se fossem evidência clínica.",
        "- Remover as colunas `data_type`/`research_only` ou apresentar os dados como reais.",
        "- Enriquecer os registros com dados pessoais reais (CPF, nome, contato, endereço etc.).",
        "",
        "## 9. Privacidade",
        "",
        f"Validação do `privacy_guard`: compliant = `{str(metadata['privacy_validation']['compliant']).lower()}`, "
        f"campos bloqueados = {metadata['privacy_validation']['blocked_fields'] or 'nenhum'}.",
        "",
    ]
    return "\n".join(linhas)
