"""Remove the worked `notes` example in one step.

    make strip-example

Leaves the core framework intact and `make check` green. Idempotent: running it
a second time is a no-op.
"""

from __future__ import annotations

import argparse
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXAMPLE_FILES = (
    "app/models/note.py",
    "app/repositories/note.py",
    "app/schemas/note.py",
    "app/services/note.py",
    "app/routers/notes.py",
    "tests/test_notes.py",
)

EXAMPLE_DIRS = ("app/templates/pages/notes",)


def strip_example(root: Path = ROOT) -> list[str]:
    """Delete the `notes` example files and unwire their imports/routes."""
    removed: list[str] = []

    for rel in EXAMPLE_FILES:
        target = root / rel
        if target.is_file():
            target.unlink()
            removed.append(rel)

    for rel in EXAMPLE_DIRS:
        target = root / rel
        if target.is_dir():
            shutil.rmtree(target)
            removed.append(f"{rel}/")

    versions_dir = root / "migrations" / "versions"
    if versions_dir.is_dir():
        for mig in sorted(versions_dir.glob("*_add_notes_table.py")):
            mig.unlink()
            removed.append(mig.relative_to(root).as_posix())

    models_init = root / "app" / "models" / "__init__.py"
    if models_init.is_file():
        original = models_init.read_text(encoding="utf-8")
        updated = original.replace("from app.models.note import Note\n", "")
        updated = updated.replace('    "Note",\n', "")
        if updated != original:
            models_init.write_text(updated, encoding="utf-8")
            removed.append("app/models/__init__.py (unwired Note)")

    main_py = root / "app" / "main.py"
    if main_py.is_file():
        original = main_py.read_text(encoding="utf-8")
        updated = re.sub(r", notes\b", "", original)
        updated = updated.replace("    app.include_router(notes.router)\n", "")
        if updated != original:
            main_py.write_text(updated, encoding="utf-8")
            removed.append("app/main.py (unwired notes.router)")

    nav_auth = root / "app" / "templates" / "partials" / "nav_auth.html"
    if nav_auth.is_file():
        original = nav_auth.read_text(encoding="utf-8")
        updated = re.sub(
            r"\n?[ \t]*\{# Parte del ejemplo trabajado del golden path.*?#\}"
            r"\n[ \t]*<a [^>]*href=\"/notes\"[^>]*>Notas</a>",
            "",
            original,
            flags=re.DOTALL,
        )
        if updated != original:
            nav_auth.write_text(updated, encoding="utf-8")
            removed.append("app/templates/partials/nav_auth.html (removed /notes link)")

    return removed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Elimina el CRUD de ejemplo (notes).")
    parser.add_argument("--root", type=Path, default=ROOT, help="raíz del proyecto")
    args = parser.parse_args(argv)

    removed = strip_example(args.root)
    if not removed:
        print("strip-example: el ejemplo 'notes' ya no está presente")
        return 0

    print("strip-example: eliminado el ejemplo 'notes':")
    for item in removed:
        print(f"  · {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
