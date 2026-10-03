"""privacy_guard: campos proibidos, conteúdo sensível, alertas e logs sem dados pessoais."""

import logging

import pandas as pd
import pytest

from app.dataset_schema import COLUMN_ORDER
from app.privacy_guard import (
    PrivacyViolationError,
    assert_privacy,
    check_payload_keys,
    classify_field,
    validate_privacy,
)


@pytest.mark.parametrize(
    "campo, categoria",
    [
        ("cpf", "CPF"),
        ("CPF_paciente", "CPF"),
        ("rg", "RG"),
        ("numero_rg", "RG"),
        ("cns", "CNS"),
        ("Cartão SUS", "CNS"),
        ("numero_prontuario", "PRONTUARIO"),
        ("Número do Prontuário", "PRONTUARIO"),
        ("telefone", "TELEFONE"),
        ("celular_contato", "TELEFONE"),
        ("phoneNumber", "TELEFONE"),
        ("email", "EMAIL"),
        ("E-mail", "EMAIL"),
        ("endereco_completo", "ENDERECO"),
        ("Endereço", "ENDERECO"),
        ("cep", "ENDERECO"),
        ("nome_completo", "NOME"),
        ("Nome", "NOME"),
        ("patientName", "NOME"),
        ("full_name", "NOME"),
        ("data_nascimento", "DATA_NASCIMENTO"),
    ],
)
def test_detecta_campos_proibidos(campo, categoria):
    assert classify_field(campo) == categoria


@pytest.mark.parametrize("campo", COLUMN_ORDER + ["regiao", "dataset_id", "registro", "programa"])
def test_sem_falso_positivo_nos_campos_do_dataset(campo):
    assert classify_field(campo) is None


def test_dataset_gerado_e_conforme(dataset):
    assert validate_privacy(dataset) == {"compliant": True, "blocked_fields": [], "warnings": []}


def test_formato_do_retorno(df):
    report = validate_privacy(df)
    assert set(report) == {"compliant", "blocked_fields", "warnings"}
    assert isinstance(report["compliant"], bool)


def test_bloqueia_coluna_proibida(df):
    df["cpf"] = "000.000.000-00"
    df["email"] = "x"
    report = validate_privacy(df)
    assert report["compliant"] is False
    assert "cpf (CPF)" in report["blocked_fields"]
    assert "email (EMAIL)" in report["blocked_fields"]


@pytest.mark.parametrize(
    "valor, categoria",
    [
        ("contato: 123.456.789-09", "CPF"),
        ("enviar para fulano@exemplo.com", "EMAIL"),
        ("ligar (11) 98765-4321", "TELEFONE"),
        ("CEP 01310-100", "CEP"),
        ("cartão 898001160123456", "IDENTIFICADOR_NUMERICO_LONGO"),
    ],
)
def test_detecta_conteudo_sensivel_em_coluna_permitida(df, valor, categoria):
    df.loc[10, "diagnostico_sintetico"] = valor
    report = validate_privacy(df)
    assert report["compliant"] is False
    assert any(b.startswith("diagnostico_sintetico") and categoria in b for b in report["blocked_fields"])


def test_patient_id_fora_do_padrao_e_bloqueado(df):
    df.loc[0, "patient_id"] = "123.456.789-09"
    report = validate_privacy(df)
    assert any("PATIENT_ID_FORA_DO_PADRAO_SINTETICO" in b for b in report["blocked_fields"])


def test_exige_marcacao_synthetic(df):
    report = validate_privacy(df.drop(columns=["data_type"]))
    assert report["compliant"] is False
    assert any("data_type" in w for w in report["warnings"])

    df.loc[0, "data_type"] = "REAL"
    assert validate_privacy(df)["compliant"] is False


def test_exige_research_only(df):
    df.loc[0, "research_only"] = False
    assert validate_privacy(df)["compliant"] is False


def test_coluna_desconhecida_gera_aviso_sem_bloquear(df):
    df["variavel_extra"] = 1
    report = validate_privacy(df)
    assert report["compliant"] is True
    assert any("variavel_extra" in w for w in report["warnings"])


def test_aceita_lista_de_registros_e_dict():
    registros = [{"idade": 40, "data_type": "SYNTHETIC", "research_only": True, "telefone": "x"}]
    assert validate_privacy(registros)["compliant"] is False
    assert validate_privacy({"idade": [40], "data_type": ["SYNTHETIC"], "research_only": [True]})["compliant"] is True


def test_assert_privacy_lanca_excecao(df):
    df["rg"] = "x"
    with pytest.raises(PrivacyViolationError) as erro:
        assert_privacy(df)
    assert "rg (RG)" in erro.value.report["blocked_fields"]


def test_payload_aninhado():
    payload = {"n_records": 100, "paciente": {"nome": "x", "contato": {"telefone": "y"}}, "lista": [{"cpf": "z"}]}
    campos = {(p["field"], p["category"]) for p in check_payload_keys(payload)}
    assert ("paciente.nome", "NOME") in campos
    assert ("paciente.contato.telefone", "TELEFONE") in campos
    assert ("lista[0].cpf", "CPF") in campos


def test_alerta_emitido_sem_registrar_valores(df, caplog):
    valor_sensivel = "123.456.789-09"
    df["cpf"] = valor_sensivel
    df.loc[0, "diagnostico_sintetico"] = f"teste {valor_sensivel}"
    with caplog.at_level(logging.WARNING, logger="privacy_guard"):
        validate_privacy(df)
    assert "ALERTA DE PRIVACIDADE" in caplog.text
    assert valor_sensivel not in caplog.text


def test_dataframe_vazio_gera_aviso():
    report = validate_privacy(pd.DataFrame(columns=COLUMN_ORDER))
    assert any("vazio" in w for w in report["warnings"])
