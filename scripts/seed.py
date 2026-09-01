"""Seed the database with its initial data.

    make seed

Run it as often as you like: the script must stay **idempotent**. Look each row
up by a natural key and update it instead of inserting, so seeding a populated
database refreshes it rather than duplicating it. A seed that can only run once
is a seed nobody dares to run.

Seeds are for data the application needs to work — categories, roles, a starting
catalogue. Not for test fixtures (those live in `tests/`) and not for a
customer's real data.
"""

from __future__ import annotations

from app.db import SessionFactory


def seed() -> None:
    """Insert or refresh the initial data.

    Replace the body with your project's own. The transaction is committed once
    at the end, so a failure halfway leaves nothing behind.

    A worked example, once you have a model and its repository::

        from app.repositories.category import CategoryRepository

        CATEGORIES = [
            {"slug": "general", "name": "General", "sort_order": 0},
        ]

        with SessionFactory() as session:
            repo = CategoryRepository(session)
            for values in CATEGORIES:
                existing = repo.get_by_slug(values["slug"])
                if existing is None:
                    repo.create(**values)
                else:
                    repo.update(existing, **values)
            session.commit()
    """
    with SessionFactory() as session:
        # El proyecto todavía no tiene datos iniciales que cargar.
        _ = session
        print("Nada que cargar: define los datos iniciales en scripts/seed.py")


if __name__ == "__main__":
    seed()
