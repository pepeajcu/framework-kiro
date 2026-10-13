"""Fonts: validate woff2 files and render their `@font-face` and tokens.

Every font is a local `.woff2` under `app/static/fonts/` (ADR-0005: no CDN; the
CSP is `font-src 'self'`). Downloading is I/O and lives in `scripts/`; what is
here is pure: where a file must be, what makes it a real woff2, and the CSS.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from app.design_engine.contract import DesignError, FontFace, Typography

FONTS_URL_PREFIX = "/static/fonts"
FONTSOURCE_CDN = "https://cdn.jsdelivr.net/fontsource/fonts"

WOFF2_MAGIC = b"wOF2"
# A Latin-subset woff2 is 10-60 KB. 400 KB leaves room for a large display
# family and still stops a wrong file (a full CJK font, a page of HTML) early.
MAX_FONT_BYTES = 400_000
_MIN_FONT_BYTES = 1_000

# What `latin-<weight>-normal.woff2` covers: Spanish, Portuguese, French and
# English fully, plus common punctuation.
LATIN_RANGE = (
    "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, "
    "U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, "
    "U+2212, U+2215, U+FEFF, U+FFFD"
)

_EMOJI = '"Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"'
_FALLBACKS = {
    "sans": f"ui-sans-serif, system-ui, sans-serif, {_EMOJI}",
    "serif": "ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif",
    "mono": (
        "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "
        "'Liberation Mono', 'Courier New', monospace"
    ),
}
_DEFAULT_FALLBACK = {"display": "sans", "body": "sans", "mono": "mono"}


@dataclass(frozen=True)
class FontFile:
    """One woff2 the contract needs on disk."""

    role: str
    family: str
    slug: str
    weight: int

    @property
    def filename(self) -> str:
        return font_filename(self.slug, self.weight)

    @property
    def url(self) -> str:
        return f"{FONTSOURCE_CDN}/{self.slug}@latest/latin-{self.weight}-normal.woff2"


def font_filename(slug: str, weight: int) -> str:
    return f"{slug}-latin-{weight}-normal.woff2"


def required_files(typography: Typography) -> tuple[FontFile, ...]:
    """Every woff2 the contract declares, in a stable order, without duplicates."""
    seen: set[str] = set()
    files: list[FontFile] = []
    for role, face in typography.faces():
        for weight in face.weights:
            file = FontFile(role, face.name, face.slug, weight)
            if file.filename not in seen:
                seen.add(file.filename)
                files.append(file)
    return tuple(files)


def validate_woff2(data: bytes, *, label: str) -> None:
    """Raise `DesignError` unless `data` is a plausible woff2 file.

    The signature and the header's own length field are checked, so an HTML
    error page saved as `.woff2`, or a truncated download, is refused instead of
    shipping as a font that silently falls back.
    """
    if len(data) < _MIN_FONT_BYTES:
        raise DesignError(f"{label}: el archivo es demasiado pequeño para ser una fuente woff2")
    if len(data) > MAX_FONT_BYTES:
        raise DesignError(
            f"{label}: pesa {len(data) // 1000} KB; el máximo son {MAX_FONT_BYTES // 1000} KB "
            "(¿no es el subconjunto latin?)"
        )
    if data[:4] != WOFF2_MAGIC:
        raise DesignError(f"{label}: no es un woff2 (la firma del archivo no coincide)")
    declared_length, num_tables = struct.unpack(">IH", data[8:14])
    if declared_length != len(data):
        raise DesignError(f"{label}: el woff2 está truncado o dañado (la longitud no coincide)")
    if num_tables == 0:
        raise DesignError(f"{label}: el woff2 no contiene tablas de fuente")


def fallback_stack(role: str, face: FontFace) -> str:
    """The generic fallback that follows the family name in `font-family`."""
    kind = face.fallback or _DEFAULT_FALLBACK[role]
    return _FALLBACKS[kind]


def _font_face_rule(file: FontFile) -> str:
    return (
        "@font-face {\n"
        f'  font-family: "{file.family}";\n'
        "  font-style: normal;\n"
        f"  font-weight: {file.weight};\n"
        "  font-display: swap;\n"
        f'  src: url("{FONTS_URL_PREFIX}/{file.filename}") format("woff2");\n'
        f"  unicode-range: {LATIN_RANGE};\n"
        "}"
    )


_TOKEN = {"display": "--font-display", "body": "--font-sans", "mono": "--font-mono"}


def render_fonts_block_body(typography: Typography) -> str | None:
    """CSS for every declared font, or None when the project declares none."""
    faces = typography.faces()
    if not faces:
        return None

    parts = [_font_face_rule(file) for file in required_files(typography)]
    tokens = [
        f'  {_TOKEN[role]}: "{face.name}", {fallback_stack(role, face)};' for role, face in faces
    ]
    parts.append("@theme {\n" + "\n".join(tokens) + "\n}")
    if typography.display is not None:
        # Titles take the display face without every heading having to ask for
        # it. Body text and UI controls keep `--font-sans`.
        parts.append(
            "@layer base {\n  h1,\n  h2,\n  h3 {\n    font-family: var(--font-display);\n  }\n}"
        )
    return "\n\n".join(parts)
