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

from app.models import User, UserRole
from app.repositories import department_repository, user_repository


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
