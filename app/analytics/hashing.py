"""PII hashing for Meta's Conversions API.

Meta requires personal fields — email, phone — hashed with SHA-256 before
they leave the server, and matches them against its own hashes of the same
fields. Case and whitespace are not normalised on Meta's side, so a hash of
`" Ana@Example.com"` never matches one of `"ana@example.com"` even though a
human reads them as the same address. Getting this wrong does not error; it
just means every event silently fails to match a person.
"""

from __future__ import annotations

import hashlib


def sha256_lower(value: str) -> str:
    """Normalise (strip, lowercase) and SHA-256-hash a value for Meta's API."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()
