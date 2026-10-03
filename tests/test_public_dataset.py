"""Base pública real (UCI Heart Disease — Cleveland): conversão, integridade, privacidade e separação."""

from pathlib import Path

import pandas as pd
import pytest

from app.privacy_guard import validate_privacy
from app.public_datasets import (
    PUBLIC_COLUMNS,
    PUBLIC_DATA_TYPE,
    parse_cleveland,
    public_quality,
    standardized_mean_difference,
    verify_checksum,
)

AMOSTRA = (
    "63.0,1.0,1.0,145.0,233.0,1.0,2.0,150.0,0.0,2.3,3.0,0.0,6.0,0\n"
    "67.0,1.0,4.0,160.0,286.0,0.0,2.0,108.0,1.0,1.5,2.0,3.0,3.0,2\n"
    "41.0,0.0,2.0,130.0,204.0,0.0,2.0,172.0,0.0,1.4,1.0,?,3.0,0\n"
    "57.0,1.0,4.0,140.0,192.0,0.0,0.0,148.0,0.0,0.4,2.0,0.0,?,1\n"
)
CSV_REAL = Path(__file__).resolve().parents[1] / "data" / "real_public" / "uci_heart_disease" / "heart_disease_cleveland.csv"


@pytest.fixture
def amostra():
    return parse_cleveland(AMOSTRA)


def test_conversao_de_colunas_e_categorias(amostra):
    assert list(amostra.columns) == PUBLIC_COLUMNS
    primeira = amostra.iloc[0]
    assert primeira["sexo"] == "M" and primeira["tipo_dor_toracica"] == "ANGINA_TIPICA"
    assert bool(primeira["glicemia_jejum_maior_120"])
    assert primeira["cintilografia_talio"] == "DEFEITO_FIXO"
    assert amostra.iloc[2]["sexo"] == "F"


def test_alvo_binario_derivado(amostra):
    assert amostra["grau_doenca"].tolist() == [0, 2, 0, 1]
    assert amostra["doenca_cardiaca"].tolist() == [False, True, False, True]


def test_ausentes_preservados(amostra):
    assert pd.isna(amostra.iloc[2]["n_vasos_fluoroscopia"])
    assert pd.isna(amostra.iloc[3]["cintilografia_talio"])
    q = public_quality(amostra)
    assert q["passed"] and q["missing_values"] == {"n_vasos_fluoroscopia": 1, "cintilografia_talio": 1}


def test_marcacao_e_identificador_proprio(amostra):
    assert (amostra["data_type"] == PUBLIC_DATA_TYPE).all()
    assert amostra["registro_id"].tolist() == ["UCI-CLE-0001", "UCI-CLE-0002", "UCI-CLE-0003", "UCI-CLE-0004"]


def test_privacidade_conforme_com_marcacao_real(amostra):
    assert validate_privacy(amostra, expected_data_type=PUBLIC_DATA_TYPE, known_fields=PUBLIC_COLUMNS) == {
        "compliant": True,
        "blocked_fields": [],
        "warnings": [],
    }


def test_base_real_nunca_passa_como_sintetica(amostra):
    """Validada com as regras do sintético, a base real é recusada — elas não se misturam."""
    assert validate_privacy(amostra)["compliant"] is False


def test_checksum_rejeita_arquivo_diferente():
    with pytest.raises(ValueError):
        verify_checksum(AMOSTRA.encode())


def test_smd():
    assert standardized_mean_difference(pd.Series([1, 2, 3]), pd.Series([1, 2, 3])) == 0
    assert standardized_mean_difference(pd.Series([2, 3, 4]), pd.Series([1, 2, 3])) == 1.0


@pytest.mark.skipif(not CSV_REAL.exists(), reason="base real ainda não importada")
def test_arquivo_importado_confere_com_a_documentacao_da_uci():
    df = pd.read_csv(CSV_REAL)
    assert len(df) == 303
    # Distribuição de classes documentada pela UCI para Cleveland: 164 sem doença (grau 0).
    assert (df["grau_doenca"] == 0).sum() == 164
    assert df["grau_doenca"].value_counts().sort_index().tolist() == [164, 55, 36, 35, 13]
    assert (df["data_type"] == PUBLIC_DATA_TYPE).all()
    assert validate_privacy(df, expected_data_type=PUBLIC_DATA_TYPE, known_fields=PUBLIC_COLUMNS)["compliant"] is True
