"""Modelo relacional. Nenhuma tabela possui coluna para dado pessoal real.

patients          1 linha por paciente sintético (demografia, antropometria, hábitos)
clinical_records  1 linha por atendimento fictício (sinais vitais, condições, risco, desfecho)
lab_results       N linhas por paciente (exames simulados em formato longo)
medications       N linhas por paciente (medicamentos simulados)
dataset_metadata  1 linha por dataset gerado
audit_logs        eventos técnicos (sem dados pessoais)
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    versao: Mapped[str] = mapped_column(String(20))
    seed: Mapped[int] = mapped_column(Integer)
    n_registros: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="ATIVO")  # ATIVO | SUBSTITUIDO
    data_type: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")
    privacy_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[str] = mapped_column(Text)


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_metadata.dataset_id"), index=True)
    idade: Mapped[int] = mapped_column(Integer)
    sexo: Mapped[str] = mapped_column(String(1))
    municipio: Mapped[str] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(2))
    peso_kg: Mapped[float] = mapped_column(Float)
    altura_cm: Mapped[float] = mapped_column(Float)
    imc: Mapped[float] = mapped_column(Float)
    hf_diabetes: Mapped[bool] = mapped_column(Boolean)
    hf_hipertensao: Mapped[bool] = mapped_column(Boolean)
    hf_doenca_cardiovascular: Mapped[bool] = mapped_column(Boolean)
    historico_familiar: Mapped[str] = mapped_column(String(200))
    tabagismo: Mapped[str] = mapped_column(String(20))
    consumo_alcool: Mapped[str] = mapped_column(String(20))
    atividade_fisica: Mapped[str] = mapped_column(String(20))
    qualidade_dieta: Mapped[str] = mapped_column(String(20))
    horas_sono: Mapped[float] = mapped_column(Float)
    split: Mapped[str] = mapped_column(String(12), index=True)
    data_type: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")
    research_only: Mapped[bool] = mapped_column(Boolean, default=True)


class ClinicalRecord(Base):
    __tablename__ = "clinical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.patient_id", ondelete="CASCADE"), unique=True)
    dataset_id: Mapped[str] = mapped_column(String(36), index=True)
    data_atendimento: Mapped[date] = mapped_column(Date)
    pa_sistolica: Mapped[int] = mapped_column(Integer)
    pa_diastolica: Mapped[int] = mapped_column(Integer)
    frequencia_cardiaca: Mapped[int] = mapped_column(Integer)
    temperatura_c: Mapped[float] = mapped_column(Float)
    cond_hipertensao: Mapped[bool] = mapped_column(Boolean)
    cond_diabetes_tipo_2: Mapped[bool] = mapped_column(Boolean)
    cond_dislipidemia: Mapped[bool] = mapped_column(Boolean)
    cond_obesidade: Mapped[bool] = mapped_column(Boolean)
    cond_asma: Mapped[bool] = mapped_column(Boolean)
    cond_doenca_renal_cronica: Mapped[bool] = mapped_column(Boolean)
    cond_infeccao_respiratoria_aguda: Mapped[bool] = mapped_column(Boolean)
    n_condicoes: Mapped[int] = mapped_column(Integer)
    condicao_clinica: Mapped[str] = mapped_column(String(40))
    aderencia_tratamento: Mapped[str] = mapped_column(String(20))
    escore_risco: Mapped[float] = mapped_column(Float)
    classificacao_risco: Mapped[str] = mapped_column(String(20))
    diagnostico_sintetico: Mapped[str] = mapped_column(String(160))
    resultado_desfecho: Mapped[str] = mapped_column(String(30))
    desfecho_adverso: Mapped[bool] = mapped_column(Boolean)


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.patient_id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[str] = mapped_column(String(36), index=True)
    exame: Mapped[str] = mapped_column(String(40))
    valor: Mapped[float] = mapped_column(Float)
    unidade: Mapped[str] = mapped_column(String(20))
    data_coleta: Mapped[date] = mapped_column(Date)


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.patient_id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[str] = mapped_column(String(36), index=True)
    ordem: Mapped[int] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(60))
    classe: Mapped[str] = mapped_column(String(80))
    posologia: Mapped[str] = mapped_column(String(60))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, index=True)
    evento: Mapped[str] = mapped_column(String(60))
    nivel: Mapped[str] = mapped_column(String(10))
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detalhes: Mapped[str] = mapped_column(Text, default="{}")
