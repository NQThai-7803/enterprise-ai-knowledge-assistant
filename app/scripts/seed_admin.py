from __future__ import annotations

import asyncio
import sys
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import async_session_factory, dispose_database_engine
from app.models import User, UserRole

ALLOWED_ENVIRONMENTS = {"development", "test"}
MIN_ADMIN_PASSWORD_LENGTH = 12
ADMIN_CREATED_MESSAGE = "Development Admin created successfully."
ADMIN_EXISTS_MESSAGE = "Development Admin already exists."


class SeedAdminError(RuntimeError):
    pass


def normalize_admin_email(email: str) -> str:
    return email.strip().lower()


def validate_admin_password(password: str) -> None:
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        msg = f"Development Admin password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters."
        raise SeedAdminError(msg)


def resolve_admin_password(settings: Settings, *, prompt_for_password: bool = True) -> str:
    password = settings.dev_admin_password
    if password:
        return password

    if prompt_for_password and sys.stdin.isatty():
        return getpass("Development Admin password: ")

    msg = "DEV_ADMIN_PASSWORD is required when no interactive terminal is available."
    raise SeedAdminError(msg)


async def seed_development_admin(
    *,
    settings: Settings | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    prompt_for_password: bool = True,
) -> str:
    settings = settings or get_settings()
    session_factory = session_factory or async_session_factory

    if settings.app_env not in ALLOWED_ENVIRONMENTS:
        msg = "Development Admin seed can only run in development or test environments."
        raise SeedAdminError(msg)

    email = normalize_admin_email(settings.dev_admin_email)
    password = resolve_admin_password(settings, prompt_for_password=prompt_for_password)
    validate_admin_password(password)

    async with session_factory() as session:
        try:
            existing_user = await session.scalar(select(User).where(User.email == email))
            if existing_user is not None:
                if existing_user.role == UserRole.ADMIN:
                    return ADMIN_EXISTS_MESSAGE
                msg = "A user with the Development Admin email already exists and is not an Admin."
                raise SeedAdminError(msg)

            admin = User(
                email=email,
                full_name=settings.dev_admin_full_name,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                department_id=None,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    return ADMIN_CREATED_MESSAGE


async def run_seed_command() -> int:
    try:
        message = await seed_development_admin()
    except SeedAdminError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        await dispose_database_engine()

    print(message)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run_seed_command()))


if __name__ == "__main__":
    main()
