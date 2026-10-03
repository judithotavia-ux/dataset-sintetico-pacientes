"""Dicionário de dados do dataset sintético.

Fonte única de verdade sobre as variáveis: o gerador, a validação de qualidade,
o privacy_guard, os metadados (metadata.json) e a Dataset Card leem daqui.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DATASET_NAME = "Synthetic Patients Dataset (SPD-BR)"
DATASET_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"
DATA_TYPE = "SYNTHETIC"
DISCLAIMER = "DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES"

ALLOWED_SIZES = (100, 1_000, 10_000, 100_000)

AGE_MIN, AGE_MAX = 18, 90

SEXOS = ("F", "M")
ESTADOS_UF = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)
TABAGISMO = ("NUNCA_FUMOU", "EX_FUMANTE", "FUMANTE_ATUAL")
CONSUMO_ALCOOL = ("NENHUM", "MODERADO", "ELEVADO")
ATIVIDADE_FISICA = ("SEDENTARIO", "MODERADA", "ATIVA")
QUALIDADE_DIETA = ("RUIM", "REGULAR", "BOA")
ADERENCIA = ("ALTA", "MEDIA", "BAIXA", "NAO_SE_APLICA")
CONDICOES = (
    "HIPERTENSAO",
    "DIABETES_TIPO_2",
    "DISLIPIDEMIA",
    "OBESIDADE",
    "ASMA",
    "DOENCA_RENAL_CRONICA",
    "INFECCAO_RESPIRATORIA_AGUDA",
)
SEM_CONDICAO = "SEM_CONDICAO_CRONICA"
CLASSIFICACAO_RISCO = ("BAIXO", "MODERADO", "ALTO", "MUITO_ALTO")
DESFECHOS = ("SEM_INTERCORRENCIA", "INTERNACAO", "EVENTO_CARDIOVASCULAR", "OBITO")
SPLITS = ("train", "validation", "test")
SPLIT_RATIOS = {"train": 0.70, "validation": 0.15, "test": 0.15}

PATIENT_ID_PATTERN = r"^SYN-[0-9A-F]{16}$"


@dataclass(frozen=True)
class Field:
    name: str
    dtype: str  # string | int | float | bool | date | category
    description: str
    group: str  # identificacao | demografia | antropometria | sinais_vitais | ...
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    categories: tuple[str, ...] | None = None
    ml_role: str = "feature"  # id | feature | target | meta
    nullable: bool = False
    extra: dict = field(default_factory=dict)


FIELDS: tuple[Field, ...] = (
    Field("patient_id", "string", "Identificador aleatório do paciente sintético (prefixo SYN-). Não tem relação com nenhum documento real.", "identificacao", ml_role="id"),
    Field("idade", "int", "Idade em anos completos.", "demografia", "anos", AGE_MIN, AGE_MAX),
    Field("sexo", "category", "Sexo biológico simulado (F/M).", "demografia", categories=SEXOS),
    Field("municipio", "string", "Município fictício (nome inventado, não corresponde a cidade real).", "demografia", ml_role="meta"),
    Field("estado", "category", "Unidade federativa (UF) sorteada para o registro sintético.", "demografia", categories=ESTADOS_UF),
    Field("peso_kg", "float", "Peso corporal.", "antropometria", "kg", 35, 200),
    Field("altura_cm", "float", "Altura.", "antropometria", "cm", 140, 205),
    Field("imc", "float", "Índice de massa corporal = peso_kg / (altura_cm/100)^2.", "antropometria", "kg/m²", 12, 70),
    Field("pa_sistolica", "int", "Pressão arterial sistólica.", "sinais_vitais", "mmHg", 70, 250),
    Field("pa_diastolica", "int", "Pressão arterial diastólica (sempre menor que a sistólica).", "sinais_vitais", "mmHg", 40, 150),
    Field("frequencia_cardiaca", "int", "Frequência cardíaca em repouso.", "sinais_vitais", "bpm", 30, 200),
    Field("temperatura_c", "float", "Temperatura axilar.", "sinais_vitais", "°C", 34.0, 42.0),
    Field("hf_diabetes", "bool", "Histórico familiar sintético de diabetes.", "historico_familiar"),
    Field("hf_hipertensao", "bool", "Histórico familiar sintético de hipertensão.", "historico_familiar"),
    Field("hf_doenca_cardiovascular", "bool", "Histórico familiar sintético de doença cardiovascular.", "historico_familiar"),
    Field("historico_familiar", "string", "Resumo textual do histórico familiar sintético.", "historico_familiar", ml_role="meta"),
    Field("tabagismo", "category", "Hábito de tabagismo simulado.", "habitos_de_vida", categories=TABAGISMO),
    Field("consumo_alcool", "category", "Consumo de álcool simulado.", "habitos_de_vida", categories=CONSUMO_ALCOOL),
    Field("atividade_fisica", "category", "Nível de atividade física simulado.", "habitos_de_vida", categories=ATIVIDADE_FISICA),
    Field("qualidade_dieta", "category", "Qualidade da dieta simulada.", "habitos_de_vida", categories=QUALIDADE_DIETA),
    Field("horas_sono", "float", "Média de horas de sono por noite.", "habitos_de_vida", "h", 3, 12),
    Field("cond_hipertensao", "bool", "Condição simulada: hipertensão arterial.", "condicao_clinica"),
    Field("cond_diabetes_tipo_2", "bool", "Condição simulada: diabetes tipo 2.", "condicao_clinica"),
    Field("cond_dislipidemia", "bool", "Condição simulada: dislipidemia.", "condicao_clinica"),
    Field("cond_obesidade", "bool", "Condição simulada: obesidade (derivada de IMC >= 30).", "condicao_clinica"),
    Field("cond_asma", "bool", "Condição simulada: asma.", "condicao_clinica"),
    Field("cond_doenca_renal_cronica", "bool", "Condição simulada: doença renal crônica.", "condicao_clinica"),
    Field("cond_infeccao_respiratoria_aguda", "bool", "Condição aguda simulada: infecção respiratória (com febre).", "condicao_clinica"),
    Field("n_condicoes", "int", "Quantidade de condições simuladas presentes.", "condicao_clinica", min=0, max=len(CONDICOES)),
    Field("condicao_clinica", "category", "Condição clínica principal simulada (a de maior prioridade presente).", "condicao_clinica", categories=CONDICOES + (SEM_CONDICAO,)),
    Field("medicamentos", "string", "Medicamentos simulados prescritos, separados por '; ' (vazio = nenhum).", "medicamentos", ml_role="meta", nullable=True),
    Field("n_medicamentos", "int", "Quantidade de medicamentos simulados.", "medicamentos", min=0, max=10),
    Field("aderencia_tratamento", "category", "Aderência simulada ao tratamento medicamentoso.", "medicamentos", categories=ADERENCIA),
    Field("glicemia_jejum", "float", "Exame simulado: glicemia de jejum.", "exames_laboratoriais", "mg/dL", 40, 600),
    Field("hba1c", "float", "Exame simulado: hemoglobina glicada.", "exames_laboratoriais", "%", 3.5, 16),
    Field("colesterol_total", "float", "Exame simulado: colesterol total.", "exames_laboratoriais", "mg/dL", 80, 450),
    Field("ldl", "float", "Exame simulado: LDL (estimado por Friedewald quando TG < 400).", "exames_laboratoriais", "mg/dL", 20, 350),
    Field("hdl", "float", "Exame simulado: HDL.", "exames_laboratoriais", "mg/dL", 15, 130),
    Field("triglicerides", "float", "Exame simulado: triglicerídeos.", "exames_laboratoriais", "mg/dL", 20, 1500),
    Field("creatinina", "float", "Exame simulado: creatinina sérica.", "exames_laboratoriais", "mg/dL", 0.2, 12),
    Field("hemoglobina", "float", "Exame simulado: hemoglobina.", "exames_laboratoriais", "g/dL", 6, 21),
    Field("data_atendimento", "date", "Data fictícia do atendimento (AAAA-MM-DD).", "atendimento", ml_role="meta"),
    Field("escore_risco", "float", "Escore de risco sintético (0–100). Não é escore clínico validado.", "desfecho", "pontos", 0, 100, ml_role="target"),
    Field("classificacao_risco", "category", "Classificação de risco derivada do escore sintético.", "desfecho", categories=CLASSIFICACAO_RISCO, ml_role="target"),
    Field("diagnostico_sintetico", "string", "Diagnóstico textual simulado (condição principal + situação de controle).", "desfecho", ml_role="target"),
    Field("resultado_desfecho", "category", "Desfecho simulado em 12 meses.", "desfecho", categories=DESFECHOS, ml_role="target"),
    Field("desfecho_adverso", "bool", "Indicador binário de desfecho adverso (qualquer desfecho diferente de SEM_INTERCORRENCIA).", "desfecho", ml_role="target"),
    Field("split", "category", "Partição para ML: train (70%), validation (15%), test (15%), estratificada por classificacao_risco.", "ml", categories=SPLITS, ml_role="meta"),
    Field("data_type", "category", "Marcação obrigatória: todo registro é SYNTHETIC.", "governanca", categories=(DATA_TYPE,), ml_role="meta"),
    Field("research_only", "bool", "Marcação obrigatória: uso exclusivo em pesquisa (sempre true).", "governanca", ml_role="meta"),
)

FIELDS_BY_NAME = {f.name: f for f in FIELDS}
COLUMN_ORDER = [f.name for f in FIELDS]
CONDITION_COLUMNS = {c: f"cond_{c.lower()}" for c in CONDICOES}

# Exames vão para a tabela lab_results em formato longo (um registro por exame).
LAB_FIELDS = [f for f in FIELDS if f.group == "exames_laboratoriais"]
