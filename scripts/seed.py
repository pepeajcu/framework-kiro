"""Seed the database with its initial data.

    make seed

Run it as often as you like: the script must stay **idempotent**. Look each row
up by a natural key and update it instead of inserting, so seeding a populated
database refreshes it rather than duplicating it. A seed that can only run once
is a seed nobody dares to run.

Seeds are for data the application needs to work — categories, a starting
catalogue, the first administrator. Not for test fixtures (those live in
`tests/`) and not for a customer's real data.

The `admin` and `user` roles are **not** here: they are created by the first
migration, because the code assumes they exist.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import SessionFactory
from app.models.role import ADMIN_ROLE
from app.repositories.user import RoleRepository, UserRepository
from app.security import hash_password


def seed() -> None:
    """Insert or refresh the initial data.

    Add your project's own below. The transaction is committed once at the end,
    so a failure halfway leaves nothing behind.

    A worked example, once you have a model and its repository::

        from app.repositories.category import CategoryRepository

        CATEGORIES = [
            {"slug": "general", "name": "General", "sort_order": 0},
        ]

        repo = CategoryRepository(session)
        for values in CATEGORIES:
            existing = repo.get_by_slug(values["slug"])
            if existing is None:
                repo.create(**values)
            else:
                repo.update(existing, **values)
    """
    settings = get_settings()

    with SessionFactory() as session:
        seed_admin(session, settings)
        session.commit()


def seed_admin(session: Session, settings: Settings) -> None:
    """Create the first administrator from ADMIN_EMAIL / ADMIN_PASSWORD.

    An existing account keeps its password. That matters twice over: running the
    seed again must not silently reset a password somebody changed, and
    `ADMIN_PASSWORD` tends to linger in a `.env` long after it stopped being the
    real one.
    """
    if not settings.admin_email or not settings.admin_password:
        print("ADMIN_EMAIL o ADMIN_PASSWORD sin definir: no se crea administrador")
        return

    users = UserRepository(session)
    roles = RoleRepository(session)

    admin = users.get_by_email(settings.admin_email)
    if admin is None:
        admin = users.create(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            full_name="Administración",
        )
        print(f"administrador creado: {admin.email}")
    else:
        print(f"el administrador {admin.email} ya existe; su contraseña no se toca")

    admin_role = roles.get_by_slug(ADMIN_ROLE)
    if admin_role is None:
        print("no existe el rol 'admin': ¿has corrido 'make migrate'?")
        return

    if not admin.has_role(ADMIN_ROLE):
        admin.roles.append(admin_role)
        print("rol 'admin' asignado")


if __name__ == "__main__":
    seed()
