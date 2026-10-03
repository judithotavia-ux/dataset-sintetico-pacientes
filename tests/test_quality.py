"""Validações de qualidade: cada defeito injetado precisa ser detectado."""

import numpy as np

from app.quality import validate_quality


def _checks(report):
    return {i["check"] for i in report["issues"]}


def test_dataset_gerado_passa(df):
    report = validate_quality(df)
    assert report["passed"], report["issues"]
    assert set(report["checks"].values()) == {"OK"}


def test_valores_ausentes(df):
    df.loc[3, "glicemia_jejum"] = np.nan
    df.loc[4, "sexo"] = ""
    report = validate_quality(df)
    assert not report["passed"]
    colunas = {i["column"] for i in report["issues"] if i["check"] == "valores_ausentes"}
    assert {"glicemia_jejum", "sexo"} <= colunas


def test_medicamentos_vazio_e_permitido(df):
    assert (df["medicamentos"] == "").any()
    assert "valores_ausentes" not in _checks(validate_quality(df))


def test_idade_fora_do_intervalo(df):
    df.loc[0, "idade"] = 130
    df.loc[1, "idade"] = 5
    report = validate_quality(df)
    assert "idade_fora_do_intervalo" in _checks(report)
    assert next(i for i in report["issues"] if i["check"] == "idade_fora_do_intervalo")["count"] == 2


def test_peso_incompativel(df):
    df.loc[0, "peso_kg"] = 400.0
    assert "peso_incompativel" in _checks(validate_quality(df))


def test_altura_incompativel(df):
    df.loc[0, "altura_cm"] = 30.0
    assert "altura_incompativel" in _checks(validate_quality(df))


def test_imc_incorreto(df):
    df.loc[0, "imc"] = df.loc[0, "imc"] + 3
    assert "imc_incorreto" in _checks(validate_quality(df))


def test_pressao_diastolica_maior_que_sistolica(df):
    df.loc[0, "pa_diastolica"] = df.loc[0, "pa_sistolica"] + 5
    assert "pressao_arterial_invalida" in _checks(validate_quality(df))


def test_pressao_impossivel(df):
    df.loc[0, "pa_sistolica"] = 400
    assert "pressao_arterial_invalida" in _checks(validate_quality(df))


def test_valor_impossivel_generico(df):
    df.loc[0, "temperatura_c"] = 50.0
    assert "valor_impossivel" in _checks(validate_quality(df))


def test_duplicidade_de_patient_id(df):
    df.loc[1, "patient_id"] = df.loc[0, "patient_id"]
    report = validate_quality(df)
    assert "patient_id_duplicado" in _checks(report)


def test_patient_id_fora_do_padrao(df):
    df.loc[0, "patient_id"] = "12345678900"
    assert "patient_id_invalido" in _checks(validate_quality(df))


def test_tipo_incorreto(df):
    df["idade"] = df["idade"].astype(str)
    assert "tipo_incorreto" in _checks(validate_quality(df))


def test_data_invalida(df):
    df.loc[0, "data_atendimento"] = "31/12/2024"
    assert "tipo_incorreto" in _checks(validate_quality(df))


def test_categoria_invalida(df):
    df.loc[0, "sexo"] = "X"
    assert "categoria_invalida" in _checks(validate_quality(df))


def test_coluna_obrigatoria_ausente(df):
    report = validate_quality(df.drop(columns=["imc"]))
    assert "colunas_ausentes" in _checks(report)


def test_inconsistencia_interna(df):
    df.loc[0, "desfecho_adverso"] = not df.loc[0, "desfecho_adverso"]
    assert "inconsistencia" in _checks(validate_quality(df))
