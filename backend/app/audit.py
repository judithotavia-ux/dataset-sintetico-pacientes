"""Auditoria técnica.

Regra: os logs guardam apenas informação técnica (evento, contagens, nomes de
campos, formatos, seed, ids sintéticos de dataset). Nunca valores de registros.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.privacy_guard import classify_field

logger = logging.getLogger("audit")

_MAX_TEXT = 300


def _sanitize(value: Any) -> Any:
    """Mantém só tipos simples e descarta chaves que pareçam dado pessoal."""
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items() if classify_field(str(k)) is None}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in list(value)[:50]]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)[:_MAX_TEXT]


def log_event(session: Session, evento: str, nivel: str = "INFO", dataset_id: str | None = None, **detalhes: Any) -> AuditLog:
    registro = AuditLog(
        criado_em=datetime.now(timezone.utc).replace(tzinfo=None),
        evento=evento,
        nivel=nivel,
        dataset_id=dataset_id,
        detalhes=json.dumps(_sanitize(detalhes), ensure_ascii=False),
    )
    session.add(registro)
    session.commit()
    logger.log(logging.WARNING if nivel in ("WARNING", "ALERTA") else logging.INFO, "%s dataset=%s %s", evento, dataset_id or "-", registro.detalhes)
    return registro


def list_events(session: Session, limit: int = 100) -> list[dict[str, Any]]:
    linhas = session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "criado_em": r.criado_em.isoformat(),
            "evento": r.evento,
            "nivel": r.nivel,
            "dataset_id": r.dataset_id,
            "detalhes": json.loads(r.detalhes or "{}"),
        }
        for r in linhas
    ]
