"""Shared FastAPI dependencies.

Import the aliases from here rather than wiring `Depends(...)` by hand in every
route: one definition, one place to change.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db

DbSession = Annotated[Session, Depends(get_db)]
"""Request-scoped database session."""

AppSettings = Annotated[Settings, Depends(get_settings)]
"""Application configuration."""
