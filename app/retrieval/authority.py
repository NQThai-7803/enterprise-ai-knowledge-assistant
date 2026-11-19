from __future__ import annotations

from sqlalchemy import and_, case, func, or_, true

from app.core.config import get_settings
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
# A DRAFT document ranks as an ACTIVE one; RAG_DRAFT_DOCUMENT_POLICY=exclude removes it instead.
_ISSUED_OR_DRAFT = (DocumentLifecycleStatus.ACTIVE, DocumentLifecycleStatus.DRAFT)


def is_historical_query(query: str) -> bool:
    folded = f" {fold_text(query)} "
    return any(cue in folded for cue in _HISTORICAL_CUES)


def answer_document_filter():
    """DEC-033: the documents an answer may use, on top of the permission filter."""
    if get_settings().rag_draft_document_policy == "exclude":
        return Document.lifecycle_status != DocumentLifecycleStatus.DRAFT
    return true()


def current_authority_order_expression():
    today = func.current_date()
    current = Document.lifecycle_status.in_(_ISSUED_OR_DRAFT)
    currently_effective = and_(
        current,
        or_(Document.effective_from.is_(None), Document.effective_from <= today),
        or_(Document.effective_to.is_(None), Document.effective_to >= today),
    )
    return case(
        (currently_effective, 2),
        (current, 1),
        else_=0,
    )
