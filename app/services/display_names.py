"""BR-4 option (a): names of other Users and of Departments go to Admin callers only.

RBAC.md (TASK-007) keeps User reads by Manager and Staff at 404 to avoid account enumeration and
makes Department list and detail Admin-only, so a non-Admin caller gets no such name, not even
as a null: the response keys are left out.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User, UserRole
from app.repositories import department_repository, document_repository, user_repository


@dataclass(frozen=True, slots=True)
class DisplayNames:
    users: dict[UUID, str]
    departments: dict[UUID, str]

    def user(self, user_id: UUID | None) -> str | None:
        return self.users.get(user_id) if user_id is not None else None

    def department(self, department_id: UUID | None) -> str | None:
        return self.departments.get(department_id) if department_id is not None else None


async def admin_display_names(
    session: AsyncSession,
    *,
    current_user: User,
    user_ids: Iterable[UUID | None],
    department_ids: Iterable[UUID | None],
) -> DisplayNames | None:
    """The names an Admin caller sees; None for any other role."""
    if current_user.role != UserRole.ADMIN:
        return None
    return DisplayNames(
        users=await user_repository.full_names_by_id(session, {i for i in user_ids if i}),
        departments=await department_repository.names_by_id(
            session, {i for i in department_ids if i}
        ),
    )


# BR-11: the target types an audit row may be labelled by; chat sessions, messages and feedback
# have no label, since their only text is user content (a session title can be the question).
_LABELLED_TARGETS = ("USER", "DEPARTMENT", "DOCUMENT", "DOCUMENT_PERMISSION")


@dataclass(frozen=True, slots=True)
class AuditLabels:
    actors: dict[UUID, str]
    targets: dict[tuple[str, UUID], str]

    def actor(self, user_id: UUID | None) -> str | None:
        return self.actors.get(user_id) if user_id is not None else None

    def target(self, target_type: str | None, target_id: UUID | None) -> str | None:
        if target_type is None or target_id is None:
            return None
        return self.targets.get((target_type, target_id))


async def admin_audit_labels(
    session: AsyncSession,
    *,
    current_user: User,
    rows: Iterable[AuditLog],
) -> AuditLabels | None:
    """Actor full names and target labels (a full name, a Department code, a Document code or
    title) for an Admin caller; None for any other role."""
    if current_user.role != UserRole.ADMIN:
        return None
    rows = list(rows)
    ids: dict[str, set[UUID]] = {kind: set() for kind in _LABELLED_TARGETS}
    for row in rows:
        if row.entity_type in ids and row.entity_id is not None:
            ids[row.entity_type].add(row.entity_id)
    actor_ids = {row.user_id for row in rows if row.user_id is not None}
    users = await user_repository.full_names_by_id(session, actor_ids | ids["USER"])
    found = {
        "USER": {i: users[i] for i in ids["USER"] if i in users},
        "DEPARTMENT": await department_repository.codes_by_id(session, ids["DEPARTMENT"]),
        "DOCUMENT": await document_repository.labels_by_id(session, ids["DOCUMENT"]),
        "DOCUMENT_PERMISSION": await document_repository.permission_labels_by_id(
            session, ids["DOCUMENT_PERMISSION"]
        ),
    }
    return AuditLabels(
        actors={i: users[i] for i in actor_ids if i in users},
        targets={(kind, i): label for kind, labels in found.items() for i, label in labels.items()},
    )
