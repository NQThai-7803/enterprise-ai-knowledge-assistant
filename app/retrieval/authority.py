from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, and_, case, func, literal, or_, true

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


def retrieval_as_of() -> tuple[date, str]:
    """The date versions are ranked by, and where it comes from (GET /health/ready)."""
    as_of = get_settings().eval_as_of_date
    if as_of is not None:
        return as_of, "EVAL_AS_OF_DATE"
    return datetime.now(UTC).date(), "system"  # the database's current_date, also UTC


def current_authority_order_expression():
    as_of = get_settings().eval_as_of_date
    today = func.current_date() if as_of is None else literal(as_of, Date)
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
