from __future__ import annotations

from sqlalchemy import and_, case, func, or_

from app.models import Document, DocumentLifecycleStatus
from app.retrieval.question_analysis import fold_text

_HISTORICAL_CUES = (
    "lich su",
    "phien ban cu",
    "version cu",
    "old version",
    "previous version",
    "superseded",
    "archived",
    "truoc day",
    "nam ",
)


def is_historical_query(query: str) -> bool:
    folded = f" {fold_text(query)} "
    return any(cue in folded for cue in _HISTORICAL_CUES)


def current_authority_order_expression():
    today = func.current_date()
    currently_effective = and_(
        Document.lifecycle_status == DocumentLifecycleStatus.ACTIVE,
        or_(Document.effective_from.is_(None), Document.effective_from <= today),
        or_(Document.effective_to.is_(None), Document.effective_to >= today),
    )
    return case(
        (currently_effective, 2),
        (Document.lifecycle_status == DocumentLifecycleStatus.ACTIVE, 1),
        else_=0,
    )
