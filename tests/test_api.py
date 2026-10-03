"""API: fluxo completo do painel, validações de entrada e bloqueio de dados pessoais."""

import io

import pandas as pd
import pytest


def _gerar(client, n=100, seed=42):
    resposta = client.post("/api/datasets/generate", json={"n_records": n, "seed": seed})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_sem_dataset_retorna_404(client):
    assert client.get("/api/datasets/current").status_code == 404


def test_fluxo_completo(client):
    gerado = _gerar(client, 1000, 7)
    assert gerado["dataset"]["n_registros"] == 1000
    assert gerado["dataset"]["data_type"] == "SYNTHETIC"
    assert gerado["privacy"]["compliant"] is True
    assert gerado["quality"]["passed"] is True

    painel = client.get("/api/datasets/current").json()
    stats = painel["stats"]
    assert stats["n_registros"] == 1000
    assert sum(item["value"] for item in stats["idade"]) == 1000
    assert sum(item["value"] for item in stats["sexo"]) == 1000
    assert sum(item["value"] for item in stats["imc"]) == 1000
    assert sum(item["value"] for item in stats["classificacao_risco"]) == 1000

    pagina = client.get("/api/datasets/current/patients", params={"page": 2, "page_size": 10}).json()
    assert pagina["total"] == 1000 and len(pagina["rows"]) == 10

    assert client.post("/api/privacy/validate").json() == {"compliant": True, "blocked_fields": [], "warnings": []}
    assert client.get("/api/quality").json()["passed"] is True


@pytest.mark.parametrize("fmt", ["csv", "xlsx", "json", "parquet"])
def test_exportacao_pela_api(client, fmt):
    _gerar(client)
    resposta = client.get(f"/api/export/{fmt}")
    assert resposta.status_code == 200
    assert f".{fmt}" in resposta.headers["content-disposition"]
    if fmt == "csv":
        df = pd.read_csv(io.BytesIO(resposta.content))
        assert len(df) == 100 and (df["data_type"] == "SYNTHETIC").all()


def test_exportacao_por_split(client):
    _gerar(client, 1000)
    df = pd.read_csv(io.BytesIO(client.get("/api/export/csv", params={"split": "test"}).content))
    assert set(df["split"]) == {"test"} and 100 < len(df) < 200


def test_quantidade_fora_das_opcoes(client):
    assert client.post("/api/datasets/generate", json={"n_records": 500}).status_code == 422


def test_formato_de_exportacao_invalido(client):
    _gerar(client)
    assert client.get("/api/export/pdf").status_code == 422


@pytest.mark.parametrize("campo", ["cpf", "nome_completo", "telefone", "email", "numero_prontuario", "endereco"])
def test_bloqueia_tentativa_de_enviar_dado_pessoal(client, campo):
    resposta = client.post("/api/datasets/generate", json={"n_records": 100, campo: "valor-sensivel-123"})
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert "privacy_guard" in corpo["detail"]
    assert any(b.startswith(campo) for b in corpo["blocked_fields"])

    logs = client.get("/api/audit-logs").json()
    alerta = next(l for l in logs if l["evento"] == "tentativa_insercao_dado_pessoal")
    assert alerta["nivel"] == "ALERTA"
    assert "valor-sensivel-123" not in str(logs)


def test_check_fields(client):
    resposta = client.post("/api/privacy/check-fields", json={"fields": ["idade", "CPF", "E-mail"]}).json()
    assert resposta["compliant"] is False
    assert resposta["blocked_fields"] == ["CPF (CPF)", "E-mail (EMAIL)"]
    assert client.post("/api/privacy/check-fields", json={"fields": ["idade", "imc"]}).json()["compliant"] is True


def test_seed_reprodutivel_pela_api(client):
    _gerar(client, 100, 2024)
    primeiro = client.get("/api/datasets/current/patients", params={"page_size": 5}).json()["rows"]
    _gerar(client, 100, 2024)
    segundo = client.get("/api/datasets/current/patients", params={"page_size": 5}).json()["rows"]
    assert primeiro == segundo
