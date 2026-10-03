"""Cálculo do IMC."""

import numpy as np
import pytest

from app.generator import calculate_bmi, calculate_bmi_series


@pytest.mark.parametrize(
    "peso, altura, esperado",
    [(70, 175, 22.86), (50, 160, 19.53), (100, 180, 30.86), (45.5, 152.3, 19.62)],
)
def test_valores_conhecidos(peso, altura, esperado):
    assert calculate_bmi(peso, altura) == esperado


@pytest.mark.parametrize("peso, altura", [(0, 170), (70, 0), (-1, 170), (70, -170), (None, 170)])
def test_entradas_invalidas(peso, altura):
    with pytest.raises(ValueError):
        calculate_bmi(peso, altura)


def test_versao_vetorizada_igual_a_escalar():
    pesos = np.array([70, 50, 100])
    alturas = np.array([175, 160, 180])
    assert list(calculate_bmi_series(pesos, alturas)) == [calculate_bmi(p, a) for p, a in zip(pesos, alturas)]


def test_imc_do_dataset_confere_com_peso_e_altura(dataset):
    recalculado = calculate_bmi_series(dataset["peso_kg"], dataset["altura_cm"])
    assert np.allclose(dataset["imc"], recalculado, atol=0.01)
