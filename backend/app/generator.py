"""Gerador de pacientes sintéticos.

Não é um sorteio de números independentes: os dados seguem um modelo causal
simplificado (e fictício) para que existam relações aprendíveis por modelos de ML:

    idade, sexo, hábitos de vida, histórico familiar
        -> IMC, altura, peso
        -> condições clínicas (probabilidade logística)
        -> medicamentos e aderência
        -> sinais vitais e exames (com efeito do tratamento)
        -> escore de risco sintético -> classificação de risco
        -> desfecho simulado em 12 meses

Os coeficientes foram escolhidos para produzir distribuições plausíveis, mas NÃO
foram estimados a partir de nenhuma população real e não devem ser interpretados
como evidência clínica. Toda a aleatoriedade vem de um único seed.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from app.dataset_schema import (
    AGE_MAX,
    AGE_MIN,
    CLASSIFICACAO_RISCO,
    COLUMN_ORDER,
    CONDICOES,
    CONDITION_COLUMNS,
    DATA_TYPE,
    ESTADOS_UF,
    FIELDS,
    SEM_CONDICAO,
    SPLIT_RATIOS,
)

ATTENDANCE_START = date(2023, 1, 1)
ATTENDANCE_END = date(2024, 12, 31)

# Ordem de prioridade para escolher a condição principal.
PRIORIDADE_CONDICOES = (
    "DOENCA_RENAL_CRONICA",
    "DIABETES_TIPO_2",
    "HIPERTENSAO",
    "INFECCAO_RESPIRATORIA_AGUDA",
    "DISLIPIDEMIA",
    "OBESIDADE",
    "ASMA",
)

# Catálogo de medicamentos simulados por condição: (nome, classe, posologia).
CATALOGO_MEDICAMENTOS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "HIPERTENSAO": (
        ("Losartana", "Antagonista do receptor da angiotensina II", "50 mg 1x/dia"),
        ("Hidroclorotiazida", "Diurético tiazídico", "25 mg 1x/dia"),
        ("Anlodipino", "Bloqueador de canal de cálcio", "5 mg 1x/dia"),
        ("Enalapril", "Inibidor da ECA", "10 mg 2x/dia"),
    ),
    "DIABETES_TIPO_2": (
        ("Metformina", "Biguanida", "850 mg 2x/dia"),
        ("Glibenclamida", "Sulfonilureia", "5 mg 1x/dia"),
    ),
    "DISLIPIDEMIA": (
        ("Sinvastatina", "Estatina", "20 mg 1x/dia"),
        ("Atorvastatina", "Estatina", "20 mg 1x/dia"),
    ),
    "ASMA": (
        ("Salbutamol", "Broncodilatador beta-2 agonista", "100 mcg se necessário"),
        ("Budesonida", "Corticoide inalatório", "200 mcg 2x/dia"),
    ),
    "INFECCAO_RESPIRATORIA_AGUDA": (
        ("Amoxicilina", "Antibiótico betalactâmico", "500 mg 8/8h por 7 dias"),
        ("Paracetamol", "Analgésico/antipirético", "750 mg 6/6h se febre"),
    ),
}
PROB_TRATAMENTO = {
    "HIPERTENSAO": 0.80,
    "DIABETES_TIPO_2": 0.85,
    "DISLIPIDEMIA": 0.60,
    "ASMA": 0.75,
    "INFECCAO_RESPIRATORIA_AGUDA": 0.90,
}

# Sílabas inventadas para nomes de municípios fictícios.
_PREFIXOS_MUNICIPIO = ("Vale de", "Serra de", "Campo de", "Vila", "Lago de", "Alto de", "Barra de", "Nova")
_RADICAIS_MUNICIPIO = ("Aur", "Belv", "Cendr", "Dorv", "Esmir", "Falv", "Gurv", "Ibir", "Jaquel", "Lumir", "Mirv", "Norv", "Orval", "Pelv", "Quirel", "Relv", "Solv", "Tavr", "Urval", "Velm", "Xerv", "Zanv")
_SUFIXOS_MUNICIPIO = ("ival", "anda", "elha", "orém", "imar", "unda", "alena", "ério", "osa", "inel")

DIAGNOSTICO_BASE = {
    "HIPERTENSAO": "Hipertensão arterial sistêmica",
    "DIABETES_TIPO_2": "Diabetes mellitus tipo 2",
    "DISLIPIDEMIA": "Dislipidemia",
    "OBESIDADE": "Obesidade",
    "ASMA": "Asma",
    "DOENCA_RENAL_CRONICA": "Doença renal crônica",
    "INFECCAO_RESPIRATORIA_AGUDA": "Infecção respiratória aguda",
    SEM_CONDICAO: "Sem condição crônica identificada",
}


def calculate_bmi(peso_kg: float, altura_cm: float) -> float:
    """IMC = peso (kg) / altura (m)², arredondado em 2 casas."""
    if peso_kg is None or altura_cm is None:
        raise ValueError("peso_kg e altura_cm são obrigatórios")
    if peso_kg <= 0 or altura_cm <= 0:
        raise ValueError("peso_kg e altura_cm devem ser positivos")
    altura_m = altura_cm / 100.0
    return round(peso_kg / (altura_m * altura_m), 2)


def calculate_bmi_series(peso_kg: pd.Series | np.ndarray, altura_cm: pd.Series | np.ndarray) -> np.ndarray:
    altura_m = np.asarray(altura_cm, dtype=float) / 100.0
    return np.round(np.asarray(peso_kg, dtype=float) / (altura_m * altura_m), 2)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _bernoulli(rng: np.random.Generator, p: np.ndarray | float, n: int) -> np.ndarray:
    return rng.random(n) < p


def _categorical(rng: np.random.Generator, probs: np.ndarray, labels: tuple[str, ...]) -> np.ndarray:
    """Sorteia um rótulo por linha a partir de uma matriz de probabilidades (n, k)."""
    probs = probs / probs.sum(axis=1, keepdims=True)
    cumulativa = probs.cumsum(axis=1)
    u = rng.random(probs.shape[0])[:, None]
    idx = (u > cumulativa).sum(axis=1)
    idx = np.minimum(idx, len(labels) - 1)
    return np.asarray(labels, dtype=object)[idx]


def _truncated_normal(rng: np.random.Generator, mean: float, sd: float, low: float, high: float, n: int) -> np.ndarray:
    """Normal truncada por reamostragem (sem empilhar valores nos limites)."""
    out = rng.normal(mean, sd, n)
    fora = (out < low) | (out > high)
    while fora.any():
        out[fora] = rng.normal(mean, sd, fora.sum())
        fora = (out < low) | (out > high)
    return out


def _fictitious_municipalities(fake: Faker, count: int = 120) -> list[tuple[str, str]]:
    """Gera municípios com nomes inventados, cada um associado a uma UF."""
    nomes: set[str] = set()
    municipios: list[tuple[str, str]] = []
    while len(municipios) < count:
        nome = f"{fake.random_element(_PREFIXOS_MUNICIPIO)} {fake.random_element(_RADICAIS_MUNICIPIO)}{fake.random_element(_SUFIXOS_MUNICIPIO)}"
        if nome in nomes:
            continue
        nomes.add(nome)
        municipios.append((nome, fake.random_element(ESTADOS_UF)))
    return municipios


def _patient_ids(fake: Faker, n: int) -> list[str]:
    ids: set[str] = set()
    out: list[str] = []
    while len(out) < n:
        candidato = "SYN-" + fake.uuid4().replace("-", "")[:16].upper()
        if candidato not in ids:
            ids.add(candidato)
            out.append(candidato)
    return out


def stratified_split(labels: np.ndarray, seed: int, ratios: dict[str, float] = SPLIT_RATIOS) -> np.ndarray:
    """Divide em train/validation/test preservando a proporção de cada rótulo."""
    rng = np.random.default_rng(seed + 7919)
    labels = np.asarray(labels)
    split = np.empty(len(labels), dtype=object)
    nomes = list(ratios)
    for valor in pd.unique(labels):
        idx = np.flatnonzero(labels == valor)
        rng.shuffle(idx)
        n = len(idx)
        n_train = int(round(n * ratios[nomes[0]]))
        n_val = int(round(n * ratios[nomes[1]]))
        if n_train + n_val > n:
            n_val = n - n_train
        split[idx[:n_train]] = nomes[0]
        split[idx[n_train:n_train + n_val]] = nomes[1]
        split[idx[n_train + n_val:]] = nomes[2]
    return split


def generate_dataset(n_records: int, seed: int = 42) -> pd.DataFrame:
    """Gera `n_records` pacientes sintéticos de forma reprodutível a partir do `seed`."""
    if not isinstance(n_records, (int, np.integer)) or n_records <= 0:
        raise ValueError("n_records deve ser um inteiro positivo")
    n = int(n_records)
    rng = np.random.default_rng(seed)
    fake = Faker("pt_BR")
    fake.seed_instance(seed)

    # ---- Identificação e demografia ----
    patient_id = _patient_ids(fake, n)
    idade = np.rint(_truncated_normal(rng, 48, 17, AGE_MIN, AGE_MAX, n)).astype(int)
    sexo = np.where(rng.random(n) < 0.51, "F", "M").astype(object)
    masc = sexo == "M"
    municipios = _fictitious_municipalities(fake)
    escolha_mun = rng.integers(0, len(municipios), n)
    municipio = np.array([municipios[i][0] for i in escolha_mun], dtype=object)
    estado = np.array([municipios[i][1] for i in escolha_mun], dtype=object)

    # ---- Histórico familiar ----
    hf_diabetes = _bernoulli(rng, 0.25, n)
    hf_hipertensao = _bernoulli(rng, 0.35, n)
    hf_dcv = _bernoulli(rng, 0.18, n)
    historico = []
    for d, h, c in zip(hf_diabetes, hf_hipertensao, hf_dcv):
        itens = [nome for flag, nome in ((d, "Diabetes"), (h, "Hipertensão"), (c, "Doença cardiovascular")) if flag]
        historico.append("; ".join(itens) if itens else "Sem histórico relevante")

    # ---- Hábitos de vida ----
    fumante_extra = np.where(masc, 0.05, 0.0)
    tabagismo = _categorical(rng, np.column_stack([np.full(n, 0.66) - fumante_extra, np.full(n, 0.18), np.full(n, 0.16) + fumante_extra]), ("NUNCA_FUMOU", "EX_FUMANTE", "FUMANTE_ATUAL"))
    alcool_extra = np.where(masc, 0.06, 0.0)
    consumo_alcool = _categorical(rng, np.column_stack([np.full(n, 0.45) - alcool_extra, np.full(n, 0.43), np.full(n, 0.12) + alcool_extra]), ("NENHUM", "MODERADO", "ELEVADO"))
    p_sed = np.clip(0.30 + 0.005 * (idade - 18), 0.30, 0.65)
    p_ativa = np.clip(0.30 - 0.003 * (idade - 18), 0.10, 0.30)
    atividade_fisica = _categorical(rng, np.column_stack([p_sed, 1 - p_sed - p_ativa, p_ativa]), ("SEDENTARIO", "MODERADA", "ATIVA"))
    qualidade_dieta = _categorical(rng, np.tile([0.25, 0.50, 0.25], (n, 1)), ("RUIM", "REGULAR", "BOA"))
    horas_sono = np.round(np.clip(rng.normal(7.0, 1.1, n), 4.0, 10.0), 1)

    fumante = tabagismo == "FUMANTE_ATUAL"
    alcool_alto = consumo_alcool == "ELEVADO"
    sedentario = atividade_fisica == "SEDENTARIO"
    ativo = atividade_fisica == "ATIVA"
    dieta_ruim = qualidade_dieta == "RUIM"
    dieta_boa = qualidade_dieta == "BOA"

    # ---- Antropometria ----
    altura_cm = np.round(np.where(masc, rng.normal(172, 7, n), rng.normal(160, 6.5, n)).clip(145, 200), 1)
    imc_latente = (
        24.0 + 0.07 * (np.minimum(idade, 65) - 40) + 1.6 * sedentario - 1.3 * ativo
        + 1.3 * dieta_ruim - 0.9 * dieta_boa + 0.6 * alcool_alto + rng.normal(0, 4.0, n)
    ).clip(16.5, 48)
    peso_kg = np.round((imc_latente * (altura_cm / 100) ** 2).clip(38, 180), 1)
    imc = calculate_bmi_series(peso_kg, altura_cm)

    # ---- Condições clínicas simuladas ----
    p_has = _sigmoid(-5.2 + 0.065 * idade + 0.09 * (imc - 25) + 0.7 * hf_hipertensao + 0.35 * fumante + 0.3 * alcool_alto + 0.25 * sedentario)
    cond_has = _bernoulli(rng, p_has, n)
    p_dm = _sigmoid(-5.6 + 0.045 * idade + 0.13 * (imc - 25) + 0.9 * hf_diabetes + 0.35 * sedentario + 0.3 * dieta_ruim)
    cond_dm = _bernoulli(rng, p_dm, n)
    p_dlp = _sigmoid(-3.6 + 0.035 * idade + 0.07 * (imc - 25) + 0.4 * dieta_ruim + 0.3 * hf_dcv)
    cond_dlp = _bernoulli(rng, p_dlp, n)
    cond_obes = imc >= 30
    cond_asma = _bernoulli(rng, _sigmoid(-2.6 + 0.3 * fumante), n)
    p_drc = _sigmoid(-7.5 + 0.05 * idade + 1.0 * cond_dm + 0.8 * cond_has)
    cond_drc = _bernoulli(rng, p_drc, n)
    cond_ira = _bernoulli(rng, 0.07 + 0.03 * fumante, n)

    flags = {
        "HIPERTENSAO": cond_has,
        "DIABETES_TIPO_2": cond_dm,
        "DISLIPIDEMIA": cond_dlp,
        "OBESIDADE": cond_obes,
        "ASMA": cond_asma,
        "DOENCA_RENAL_CRONICA": cond_drc,
        "INFECCAO_RESPIRATORIA_AGUDA": cond_ira,
    }
    n_condicoes = np.sum(np.column_stack([flags[c] for c in CONDICOES]), axis=1)
    condicao_clinica = np.full(n, SEM_CONDICAO, dtype=object)
    for condicao in reversed(PRIORIDADE_CONDICOES):
        condicao_clinica[flags[condicao]] = condicao

    # ---- Medicamentos e aderência ----
    tratado = {c: flags[c] & _bernoulli(rng, p, n) for c, p in PROB_TRATAMENTO.items()}
    aderencia_sorteio = _categorical(rng, np.tile([0.55, 0.30, 0.15], (n, 1)), ("ALTA", "MEDIA", "BAIXA"))
    algum_tratamento = np.any(np.column_stack(list(tratado.values())), axis=1)
    aderencia = np.where(algum_tratamento, aderencia_sorteio, "NAO_SE_APLICA").astype(object)
    efeito = np.select([aderencia == "ALTA", aderencia == "MEDIA", aderencia == "BAIXA"], [1.0, 0.55, 0.15], 0.0)

    escolhas_med = rng.random((n, 4))
    medicamentos_por_paciente: list[list[tuple[str, str, str]]] = []
    for i in range(n):
        lista: list[tuple[str, str, str]] = []
        for j, (condicao, opcoes) in enumerate(CATALOGO_MEDICAMENTOS.items()):
            if not tratado[condicao][i]:
                continue
            principal = opcoes[int(escolhas_med[i, j % 4] * len(opcoes)) % len(opcoes)]
            lista.append(principal)
            # Hipertensão e infecção podem ter um segundo medicamento associado.
            if condicao in ("HIPERTENSAO", "INFECCAO_RESPIRATORIA_AGUDA") and escolhas_med[i, (j + 1) % 4] < 0.4:
                segundo = opcoes[(opcoes.index(principal) + 1) % len(opcoes)]
                lista.append(segundo)
        medicamentos_por_paciente.append(lista)
    medicamentos = np.array(["; ".join(m[0] for m in lista) for lista in medicamentos_por_paciente], dtype=object)
    n_medicamentos = np.array([len(lista) for lista in medicamentos_por_paciente], dtype=int)

    # ---- Sinais vitais ----
    trata_has = tratado["HIPERTENSAO"]
    pa_sis = (
        112 + 0.35 * (idade - 40) + 0.7 * (imc - 25) + 18 * cond_has + 3 * fumante + 2 * alcool_alto
        + 4 * cond_drc - 12 * trata_has * efeito + rng.normal(0, 10, n)
    )
    pa_sistolica = np.rint(pa_sis.clip(85, 215)).astype(int)
    pa_dia = 0.5 * pa_sistolica + 12 + 0.2 * (imc - 25) + rng.normal(0, 6, n)
    pa_diastolica = np.rint(np.minimum(pa_dia.clip(50, 125), pa_sistolica - 20)).astype(int)
    frequencia_cardiaca = np.rint((72 + 4 * sedentario - 5 * ativo + 3 * fumante + 15 * cond_ira + rng.normal(0, 9, n)).clip(45, 150)).astype(int)
    temperatura_c = np.round((36.6 + rng.normal(0, 0.3, n) + cond_ira * (1.8 + rng.normal(0, 0.5, n))).clip(35.0, 41.0), 1)

    # ---- Exames laboratoriais simulados ----
    trata_dm = tratado["DIABETES_TIPO_2"]
    glicemia = np.where(
        cond_dm,
        rng.normal(160, 35, n) - 30 * trata_dm * efeito,
        rng.normal(90 + 0.25 * (imc - 25), 9, n),
    )
    glicemia_jejum = np.round(glicemia.clip(60, 450), 1)
    hba1c = np.round(((glicemia_jejum + 46.7) / 28.7 + rng.normal(0, 0.35, n)).clip(4.0, 14.0), 1)
    trata_dlp = tratado["DISLIPIDEMIA"]
    colesterol_total = np.round((185 + 0.4 * (idade - 40) + 35 * cond_dlp - 30 * trata_dlp * efeito + 6 * dieta_ruim + rng.normal(0, 28, n)).clip(110, 380), 1)
    hdl = np.round((np.where(masc, 47, 56) - 4 * sedentario - 3 * cond_obes + 5 * ativo + rng.normal(0, 9, n)).clip(20, 110), 1)
    triglicerides = np.round((110 * np.exp(0.03 * (imc - 25) + 0.35 * cond_dlp + 0.25 * cond_dm + rng.normal(0, 0.35, n))).clip(35, 900), 1)
    ldl_friedewald = colesterol_total - hdl - triglicerides / 5
    ldl_alternativo = (colesterol_total - hdl) * 0.75
    ldl = np.round(np.where(triglicerides < 400, ldl_friedewald, ldl_alternativo).clip(30, 300), 1)
    creatinina = np.round((np.where(masc, 0.95, 0.75) + 0.004 * (idade - 40) + cond_drc * rng.normal(1.0, 0.4, n) + rng.normal(0, 0.12, n)).clip(0.4, 6.0), 2)
    hemoglobina = np.round((np.where(masc, 14.8, 13.2) - 1.0 * cond_drc + rng.normal(0, 1.0, n)).clip(8.0, 19.0), 1)

    # ---- Data fictícia do atendimento ----
    dias = (ATTENDANCE_END - ATTENDANCE_START).days
    deslocamento = rng.integers(0, dias + 1, n)
    data_atendimento = np.array([(ATTENDANCE_START + timedelta(days=int(d))).isoformat() for d in deslocamento], dtype=object)

    # ---- Escore de risco sintético (NÃO é escore clínico validado) ----
    z = (
        0.055 * (idade - 50) + 0.028 * (pa_sistolica - 130) + 0.6 * fumante + 0.8 * cond_dm
        + 0.010 * (colesterol_total - 200) - 0.025 * (hdl - 50) + 1.0 * cond_drc + 0.04 * (imc - 27)
        + 0.4 * hf_dcv + 0.6 * (temperatura_c >= 38.5) + rng.normal(0, 0.35, n)
    )
    escore_risco = np.round(100 * _sigmoid(z - 1.4), 1)
    classificacao_risco = np.select(
        [escore_risco < 10, escore_risco < 20, escore_risco < 40],
        list(CLASSIFICACAO_RISCO[:3]),
        CLASSIFICACAO_RISCO[3],
    ).astype(object)

    # ---- Diagnóstico textual simulado ----
    diagnostico = []
    for i in range(n):
        condicao = condicao_clinica[i]
        texto = DIAGNOSTICO_BASE[condicao]
        if condicao == "HIPERTENSAO":
            texto += " controlada" if pa_sistolica[i] < 140 else " não controlada"
        elif condicao == "DIABETES_TIPO_2":
            texto += " compensado" if hba1c[i] < 7.0 else " descompensado"
        elif condicao == "DISLIPIDEMIA":
            texto += " com LDL elevado" if ldl[i] >= 160 else " com LDL na meta"
        diagnostico.append(f"{texto} (simulado)")

    # ---- Desfecho simulado em 12 meses ----
    p_adverso = _sigmoid(-3.6 + 0.045 * escore_risco + 0.9 * cond_drc + 0.6 * (aderencia == "BAIXA") + 0.5 * cond_ira + rng.normal(0, 0.5, n))
    adverso = _bernoulli(rng, p_adverso, n)
    p_cv = np.clip(0.20 + 0.004 * (pa_sistolica - 130) + 0.15 * cond_dm, 0.05, 0.6)
    p_obito = np.clip(0.02 + 0.0025 * (idade - 50) + 0.05 * cond_drc, 0.01, 0.25)
    tipo = _categorical(rng, np.column_stack([1 - p_cv - p_obito, p_cv, p_obito]), ("INTERNACAO", "EVENTO_CARDIOVASCULAR", "OBITO"))
    resultado_desfecho = np.where(adverso, tipo, "SEM_INTERCORRENCIA").astype(object)

    df = pd.DataFrame(
        {
            "patient_id": patient_id,
            "idade": idade,
            "sexo": sexo,
            "municipio": municipio,
            "estado": estado,
            "peso_kg": peso_kg,
            "altura_cm": altura_cm,
            "imc": imc,
            "pa_sistolica": pa_sistolica,
            "pa_diastolica": pa_diastolica,
            "frequencia_cardiaca": frequencia_cardiaca,
            "temperatura_c": temperatura_c,
            "hf_diabetes": hf_diabetes,
            "hf_hipertensao": hf_hipertensao,
            "hf_doenca_cardiovascular": hf_dcv,
            "historico_familiar": historico,
            "tabagismo": tabagismo,
            "consumo_alcool": consumo_alcool,
            "atividade_fisica": atividade_fisica,
            "qualidade_dieta": qualidade_dieta,
            "horas_sono": horas_sono,
            **{CONDITION_COLUMNS[c]: flags[c] for c in CONDICOES},
            "n_condicoes": n_condicoes,
            "condicao_clinica": condicao_clinica,
            "medicamentos": medicamentos,
            "n_medicamentos": n_medicamentos,
            "aderencia_tratamento": aderencia,
            "glicemia_jejum": glicemia_jejum,
            "hba1c": hba1c,
            "colesterol_total": colesterol_total,
            "ldl": ldl,
            "hdl": hdl,
            "triglicerides": triglicerides,
            "creatinina": creatinina,
            "hemoglobina": hemoglobina,
            "data_atendimento": data_atendimento,
            "escore_risco": escore_risco,
            "classificacao_risco": classificacao_risco,
            "diagnostico_sintetico": diagnostico,
            "resultado_desfecho": resultado_desfecho,
            "desfecho_adverso": adverso,
            "split": stratified_split(classificacao_risco, seed),
            "data_type": DATA_TYPE,
            "research_only": True,
        }
    )
    return enforce_dtypes(df[COLUMN_ORDER])


def enforce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Converte cada coluna para o tipo declarado no dicionário de dados."""
    df = df.copy()
    for f in FIELDS:
        if f.name not in df.columns:
            continue
        if f.dtype == "int":
            df[f.name] = df[f.name].astype("int64")
        elif f.dtype == "float":
            df[f.name] = df[f.name].astype("float64")
        elif f.dtype == "bool":
            df[f.name] = df[f.name].astype(bool)
        else:
            df[f.name] = df[f.name].fillna("").astype(str) if f.nullable else df[f.name].astype(str)
    return df.reset_index(drop=True)
