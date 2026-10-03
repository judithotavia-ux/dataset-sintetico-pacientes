"""API FastAPI do gerador de dataset sintético de pacientes.

Executar (a partir da pasta backend):  uvicorn app.main:app --reload
Documentação interativa: http://localhost:8000/docs
"""

from __future__ import annotations

import json
import logging
import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app import __version__, repository
from app.audit import list_events, log_event
from app.config import Settings, get_settings
from app.database import Database
from app.dataset_schema import ALLOWED_SIZES, DISCLAIMER, FIELDS
from app.exporter import FORMATS, export_dataset
from app.privacy_guard import PrivacyViolationError, check_payload_keys, emit_alert, find_forbidden_fields, validate_privacy
from app.quality import validate_quality
from app.schemas import DatasetInfo, ExportFormat, FieldCheckRequest, GenerateRequest, PrivacyReport, SplitFilter
from app.service import DatasetQualityError, dashboard_stats, generate_and_store

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    app = FastAPI(
        title="Gerador de Dataset Sintético de Pacientes",
        version=__version__,
        description=f"**{DISCLAIMER}**. API para gerar, validar e exportar dados 100% sintéticos para pesquisa acadêmica.",
    )
    app.state.settings = settings
    app.state.db = Database(settings.resolved_database_url)
    app.state.db.create_all()
    app.state.privacy_status = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    def get_session(request: Request) -> Iterator[Session]:
        yield from request.app.state.db.session()

    def active_dataset(session: Session):
        ativo = repository.get_active_dataset(session)
        if ativo is None:
            raise HTTPException(status_code=404, detail="Nenhum dataset gerado ainda. Use 'Gerar Dataset'.")
        return ativo

    def dataset_info(ativo) -> dict[str, Any]:
        return DatasetInfo(
            dataset_id=ativo.dataset_id,
            nome=ativo.nome,
            versao=ativo.versao,
            seed=ativo.seed,
            n_registros=ativo.n_registros,
            criado_em=ativo.criado_em.isoformat(timespec="seconds"),
            data_type="SYNTHETIC",
            research_only=True,
            privacy_compliant=ativo.privacy_compliant,
            quality_passed=ativo.quality_passed,
        ).model_dump()

    # ---------- Tratamento de erros ----------

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        extras = [str(e["loc"][-1]) for e in exc.errors() if e.get("type") == "extra_forbidden"]
        proibidos = find_forbidden_fields(extras)
        try:
            corpo = await request.json()
        except Exception:
            corpo = None
        if corpo is not None:
            ja = {p["field"] for p in proibidos}
            proibidos += [p for p in check_payload_keys(corpo) if p["field"] not in ja and p["field"].split(".")[-1] not in ja]
        if proibidos:
            relatorio = {"compliant": False, "blocked_fields": [f"{p['field']} ({p['category']})" for p in proibidos], "warnings": []}
            emit_alert(f"requisicao {request.url.path}", relatorio)
            for session in request.app.state.db.session():
                log_event(session, "tentativa_insercao_dado_pessoal", "ALERTA", rota=request.url.path, campos=relatorio["blocked_fields"])
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Requisição bloqueada pelo privacy_guard: este sistema não aceita dados pessoais (CPF, RG, CNS, prontuário, telefone, e-mail, endereço, nome, data de nascimento).",
                    "blocked_fields": relatorio["blocked_fields"],
                },
            )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(PrivacyViolationError)
    async def privacy_handler(request: Request, exc: PrivacyViolationError):
        return JSONResponse(status_code=403, content={"detail": "Operação bloqueada pelo privacy_guard.", **exc.report})

    @app.exception_handler(DatasetQualityError)
    async def quality_handler(request: Request, exc: DatasetQualityError):
        return JSONResponse(status_code=422, content={"detail": str(exc), "quality": exc.report})

    # ---------- Rotas ----------

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "disclaimer": DISCLAIMER}

    @app.get("/api/schema")
    def schema():
        return {
            "allowed_sizes": list(ALLOWED_SIZES),
            "export_formats": list(FORMATS),
            "fields": [
                {"name": f.name, "type": f.dtype, "unit": f.unit, "group": f.group, "ml_role": f.ml_role, "description": f.description}
                for f in FIELDS
            ],
        }

    @app.post("/api/datasets/generate")
    def generate(payload: GenerateRequest, session: Session = Depends(get_session)):
        seed = payload.seed if payload.seed is not None else secrets.randbelow(2**31)
        resultado = generate_and_store(session, payload.n_records, seed, artifacts_root=settings.generated_dir)
        app.state.privacy_status[resultado.dataset_id] = resultado.privacy
        ativo = active_dataset(session)
        return {"dataset": dataset_info(ativo), "quality": {"passed": resultado.quality["passed"], "checks": resultado.quality["checks"]}, "privacy": resultado.privacy}

    @app.get("/api/datasets/current")
    def current(session: Session = Depends(get_session)):
        ativo = active_dataset(session)
        df = repository.load_dataset_frame(session, ativo.dataset_id)
        privacidade = app.state.privacy_status.get(ativo.dataset_id)
        return {
            "dataset": dataset_info(ativo),
            "stats": dashboard_stats(df),
            "privacy": privacidade,
            "privacy_checked": privacidade is not None,
        }

    @app.get("/api/datasets/current/patients")
    def patients(
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=200),
        split: SplitFilter = "all",
        session: Session = Depends(get_session),
    ):
        ativo = active_dataset(session)
        df = repository.load_dataset_frame(session, ativo.dataset_id)
        if split != "all":
            df = df[df["split"] == split]
        inicio = (page - 1) * page_size
        pagina = df.iloc[inicio:inicio + page_size]
        return {
            "total": int(len(df)),
            "page": page,
            "page_size": page_size,
            "columns": list(df.columns),
            "rows": pagina.to_dict(orient="records"),
        }

    @app.post("/api/privacy/validate", response_model=PrivacyReport)
    def privacy_validate(session: Session = Depends(get_session)):
        ativo = active_dataset(session)
        df = repository.load_dataset_frame(session, ativo.dataset_id)
        relatorio = validate_privacy(df)
        app.state.privacy_status[ativo.dataset_id] = relatorio
        log_event(
            session,
            "validacao_privacidade",
            "INFO" if relatorio["compliant"] else "ALERTA",
            dataset_id=ativo.dataset_id,
            compliant=relatorio["compliant"],
            n_blocked=len(relatorio["blocked_fields"]),
            n_warnings=len(relatorio["warnings"]),
        )
        return relatorio

    @app.post("/api/privacy/check-fields", response_model=PrivacyReport)
    def privacy_check_fields(payload: FieldCheckRequest, session: Session = Depends(get_session)):
        """Simula a validação de um esquema de colunas (apenas nomes, sem valores)."""
        proibidos = find_forbidden_fields(payload.fields)
        relatorio = {"compliant": not proibidos, "blocked_fields": [f"{p['field']} ({p['category']})" for p in proibidos], "warnings": []}
        if proibidos:
            emit_alert("check-fields", relatorio)
            log_event(session, "campos_proibidos_detectados", "ALERTA", campos=relatorio["blocked_fields"])
        return relatorio

    @app.get("/api/quality")
    def quality(session: Session = Depends(get_session)):
        ativo = active_dataset(session)
        return validate_quality(repository.load_dataset_frame(session, ativo.dataset_id))

    @app.get("/api/export/{fmt}")
    def export(fmt: ExportFormat, split: SplitFilter = "all", session: Session = Depends(get_session)):
        ativo = active_dataset(session)
        df = repository.load_dataset_frame(session, ativo.dataset_id)
        if split != "all":
            df = df[df["split"] == split].reset_index(drop=True)
        nome = f"synthetic_patients_{ativo.dataset_id[:8]}_{split}"
        destino = Path(settings.exports_dir) / ativo.dataset_id / nome
        try:
            metadados = json.loads(ativo.metadata_json)
            caminho = export_dataset(df, fmt, destino, metadados)
        except PrivacyViolationError as erro:
            log_event(session, "exportacao_bloqueada", "ALERTA", dataset_id=ativo.dataset_id, formato=fmt, blocked_fields=erro.report["blocked_fields"])
            raise
        log_event(session, "exportacao", dataset_id=ativo.dataset_id, formato=fmt, split=split, n_records=len(df))
        return FileResponse(caminho, filename=caminho.name)

    @app.get("/api/audit-logs")
    def audit_logs(limit: int = Query(50, ge=1, le=500), session: Session = Depends(get_session)):
        return list_events(session, limit)

    return app


app = create_app()
