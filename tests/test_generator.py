"""Geração dos pacientes: estrutura, reprodutibilidade, distribuições e partições."""

import numpy as np
import pandas as pd
import pytest

from app.dataset_schema import AGE_MAX, AGE_MIN, COLUMN_ORDER, PATIENT_ID_PATTERN, SPLIT_RATIOS
from app.generator import generate_dataset, stratified_split


def test_quantidade_e_colunas(dataset):
    assert len(dataset) == 2_000
    assert list(dataset.columns) == COLUMN_ORDER


@pytest.mark.parametrize("n", [1, 100, 1_000])
def test_gera_quantidade_pedida(n):
    assert len(generate_dataset(n, 1)) == n


@pytest.mark.parametrize("n", [0, -5, 2.5, "100"])
def test_rejeita_quantidade_invalida(n):
    with pytest.raises(ValueError):
        generate_dataset(n, 1)


def test_marcacoes_obrigatorias(dataset):
    assert (dataset["data_type"] == "SYNTHETIC").all()
    assert dataset["research_only"].all()


def test_mesmo_seed_reproduz_exatamente(dataset):
    pd.testing.assert_frame_equal(dataset, generate_dataset(2_000, 123))


def test_seeds_diferentes_geram_datasets_diferentes(dataset):
    outro = generate_dataset(2_000, 124)
    assert not outro["patient_id"].equals(dataset["patient_id"])
    assert not outro["idade"].equals(dataset["idade"])


def test_patient_id_sintetico_e_unico(dataset):
    assert dataset["patient_id"].str.match(PATIENT_ID_PATTERN).all()
    assert dataset["patient_id"].is_unique


def test_intervalos_basicos(dataset):
    assert dataset["idade"].between(AGE_MIN, AGE_MAX).all()
    assert (dataset["pa_diastolica"] < dataset["pa_sistolica"]).all()
    assert dataset["altura_cm"].between(140, 205).all()
    assert dataset["peso_kg"].between(35, 200).all()


def test_distribuicoes_plausiveis(dataset):
    assert 40 <= dataset["idade"].mean() <= 58
    assert 0.44 <= (dataset["sexo"] == "F").mean() <= 0.58
    assert 22 <= dataset["imc"].mean() <= 29
    assert 0.05 <= dataset["desfecho_adverso"].mean() <= 0.25
    # todas as classes de risco presentes
    assert set(dataset["classificacao_risco"]) == {"BAIXO", "MODERADO", "ALTO", "MUITO_ALTO"}


def test_relacoes_causais_existem(dataset):
    """O dataset precisa ter sinal aprendível, não ser ruído independente."""
    assert dataset["idade"].corr(dataset["pa_sistolica"]) > 0.2
    assert dataset.groupby("cond_diabetes_tipo_2")["glicemia_jejum"].mean().diff().iloc[-1] > 30
    assert dataset.groupby("desfecho_adverso")["escore_risco"].mean().diff().iloc[-1] > 5
    assert dataset.loc[dataset["cond_obesidade"], "imc"].min() >= 30


def test_medicamentos_coerentes_com_condicoes(dataset):
    com_metformina = dataset["medicamentos"].str.contains("Metformina")
    assert dataset.loc[com_metformina, "cond_diabetes_tipo_2"].all()
    sem_condicao = dataset["condicao_clinica"] == "SEM_CONDICAO_CRONICA"
    assert (dataset.loc[sem_condicao, "n_medicamentos"] == 0).all()
    assert (dataset.loc[sem_condicao, "aderencia_tratamento"] == "NAO_SE_APLICA").all()


def test_split_70_15_15(dataset):
    proporcoes = dataset["split"].value_counts(normalize=True)
    for nome, esperado in SPLIT_RATIOS.items():
        assert abs(proporcoes[nome] - esperado) < 0.01


def test_split_estratificado(dataset):
    geral = dataset["classificacao_risco"].value_counts(normalize=True)
    for nome in SPLIT_RATIOS:
        parte = dataset.loc[dataset["split"] == nome, "classificacao_risco"].value_counts(normalize=True)
        assert (abs(parte - geral) < 0.03).all()


def test_split_reprodutivel():
    rotulos = np.array(["A"] * 50 + ["B"] * 30 + ["C"] * 20)
    assert (stratified_split(rotulos, 5) == stratified_split(rotulos, 5)).all()
    assert not (stratified_split(rotulos, 5) == stratified_split(rotulos, 6)).all()


def test_datas_ficticias_no_periodo(dataset):
    datas = pd.to_datetime(dataset["data_atendimento"], format="%Y-%m-%d")
    assert datas.min() >= pd.Timestamp("2023-01-01")
    assert datas.max() <= pd.Timestamp("2024-12-31")
