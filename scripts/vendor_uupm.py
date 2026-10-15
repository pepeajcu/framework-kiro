"""Vendor the uupm advisor (nextlevelbuilder's ui-ux-pro-max) and build Kiro's overlay.

A tool for whoever maintains the framework, not for a project:

    make vendor-uupm                      # fetch the pinned commit, verify, write
    uv run python -m scripts.vendor_uupm verify     # is what is vendored what the lock says?

Running it again is safe: it rewrites the same files and rebuilds the overlay (for
example after a new preset exists, so a uupm style can point at it).

Two outputs, both committed:

- `.claude/skills/kiro-design/uupm/`: the search scripts and the data we use
  (stdlib-only Python and CSV, MIT). A closed list of files, pinned by commit, with
  the SHA-256 of every file in `vendor.lock.json`: GitHub's tarballs are not
  byte-stable, the files in them are. Its `SKILL.md` is saved as `GUIDE.md` so that
  it is not a second design skill (see `references/constitution.md`).
- `.claude/skills/kiro-design/uupm-kiro/`: what uupm says, translated once to what
  Kiro can do, so the clashes are settled in CI and not in every conversation:
  which of its fonts exist on Fontsource, which palettes pass AA with our compiler,
  which style is nearest to which preset, which stack advice does not apply here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import tarfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

import httpx2

from app.branding import BrandError, parse_hex, rgb_to_oklch
from app.design_engine.contract import Brand, ValidationError
from app.design_engine.palette import derive_palette, suggest_primary
from app.design_engine.presets import PRESETS
from scripts.fetch import fetch_bytes

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "kiro-design"
VENDORED = SKILL / "uupm"
OVERLAY = SKILL / "uupm-kiro"

REPOSITORY = "nextlevelbuilder/ui-ux-pro-max-skill"
VERSION = "v2.15.0"
COMMIT = "a38d04c3d5c298c851dbe5e6ee1965ee3de42cb5"
TARBALL_URL = f"https://codeload.github.com/{REPOSITORY}/tar.gz/{COMMIT}"
MAX_TARBALL_BYTES = 60 * 1024 * 1024
FONTSOURCE_URL = "https://api.fontsource.org/v1/fonts"
UPSTREAM_SKILL = ".claude/skills/ui-ux-pro-max"

#: Closed list: upstream path (under the skill folder) to path under `uupm/`.
#: What is left out on purpose: the icon sets and the Google Fonts catalogue
#: (2 MB, and a CDN we do not use), every stack but the one we are, React-only
#: data, and upstream's own tests and maintenance scripts.
FILES: dict[str, str] = {
    "SKILL.md": "GUIDE.md",
    "references/pro-rules.md": "references/pro-rules.md",
    "references/quick-reference.md": "references/quick-reference.md",
    "scripts/core.py": "scripts/core.py",
    "scripts/design_system.py": "scripts/design_system.py",
    "scripts/reasoning_contract.py": "scripts/reasoning_contract.py",
    "scripts/search.py": "scripts/search.py",
    "data/app-interface.csv": "data/app-interface.csv",
    "data/catalog-summary.json": "data/catalog-summary.json",
    "data/charts.csv": "data/charts.csv",
    "data/colors.csv": "data/colors.csv",
    "data/data-provenance.json": "data/data-provenance.json",
    "data/icons.csv": "data/icons.csv",
    "data/landing.csv": "data/landing.csv",
    "data/motion.csv": "data/motion.csv",
    "data/products.csv": "data/products.csv",
    "data/styles.csv": "data/styles.csv",
    "data/typography.csv": "data/typography.csv",
    "data/ui-reasoning.csv": "data/ui-reasoning.csv",
    "data/ux-guidelines.csv": "data/ux-guidelines.csv",
    "data/stacks/html-tailwind.csv": "data/stacks/html-tailwind.csv",
}
LICENSE_MEMBER = "LICENSE"
#: Read at build time for a font's category; not vendored.
GOOGLE_FONTS_MEMBER = f"{UPSTREAM_SKILL}/data/google-fonts.csv"

LOCK_NAME = "vendor.lock.json"


# --- Fetching and writing ------------------------------------------------------------


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract(tarball: bytes) -> dict[str, bytes]:
    """The members we want, keyed by upstream path. Nothing else is read or written."""
    wanted = {f"{UPSTREAM_SKILL}/{name}": name for name in FILES} | {
        LICENSE_MEMBER: LICENSE_MEMBER,
        GOOGLE_FONTS_MEMBER: "google-fonts.csv",
    }
    found: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        for member in archive:
            # `owner/repo-<sha>/path`: drop the first component.
            _, _, relative = member.name.partition("/")
            if relative in wanted and member.isfile():
                handle = archive.extractfile(member)
                if handle is not None:
                    found[wanted[relative]] = handle.read()
    missing = sorted(set(wanted.values()) - set(found))
    if missing:
        raise BrandError(f"el tarball de uupm no trae: {', '.join(missing)}")
    return found


def write_vendored(files: Mapping[str, bytes], dest: Path = VENDORED) -> dict[str, str]:
    """Write the vendored tree and its lock; returns `{path: sha256}`."""
    lock: dict[str, str] = {}
    for upstream, target in FILES.items():
        path = dest / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(files[upstream])
        lock[target] = sha256(files[upstream])
    (dest / "LICENSE").write_bytes(files[LICENSE_MEMBER])
    lock["LICENSE"] = sha256(files[LICENSE_MEMBER])
    document = {
        "repository": REPOSITORY,
        "version": VERSION,
        "commit": COMMIT,
        "files": dict(sorted(lock.items())),
    }
    (dest / LOCK_NAME).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return lock


def verify(dest: Path = VENDORED) -> list[str]:
    """What differs between the vendored tree and its lock. Empty means untouched."""
    lock_path = dest / LOCK_NAME
    if not lock_path.is_file():
        return [f"falta {LOCK_NAME}"]
    document = json.loads(lock_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for relative, expected in document["files"].items():
        path = dest / relative
        if not path.is_file():
            problems.append(f"falta {relative}")
        elif sha256(path.read_bytes()) != expected:
            problems.append(f"{relative} no coincide con upstream (¿editado a mano?)")
    return problems


# --- The overlay --------------------------------------------------------------------------

#: First match wins. A style that none of these names has no preset: the advisor still
#: reports it, and the proposal keeps the project's theme.
STYLE_RULES: tuple[tuple[str, str], ...] = (
    (r"neo.?brutal", "neo-brutalista"),
    (r"brutal|swiss|industrial", "brutalista"),
    (r"retro|y2k|vaporwave|pixel|90s|nostalg", "retro-y2k"),
    (r"terminal|cyber|hacker|developer|dark.?tech|code editor|neon", "oscuro-tecnologico"),
    (r"editorial|magazine|print|newspaper|typograph", "editorial"),
    (r"organic|natural|earthy|biophil|handmade|craft", "organico"),
    (r"dashboard|data.?dense|analytics|admin|back.?office|bento grid", "panel-de-datos"),
    (r"corporate|government|institution|enterprise|trust|formal|compliance", "institucional"),
    (r"liquid.?glass|glassmorph|\bios\b|apple|cupertino|frosted|translucen", "ios"),
    (r"soft|neumorph|claymorph|pastel|premium|luxury|elegan", "suave-premium"),
    (r"vibrant|playful|expressive|bold|maximal|gradient|aurora|kinetic|motion", "expresivo"),
    (r"minimal|clean|flat|simple|monochrom|zen|swiss minimal", "minimalista"),
    (r"material|default|standard|shadcn|neutral", "estandar-shadcn"),
)

#: Stack advice that cannot be followed here, and why. Checked against every field.
STACK_SKIP_RULES: tuple[tuple[str, str], ...] = (
    (r"cdn\.tailwindcss|unpkg\.com|cdn\.jsdelivr|cdnjs", "carga desde un CDN (ADR-0005, CSP)"),
    (r"fonts\.googleapis|fonts\.gstatic", "fuente por CDN: las fuentes son locales (ADR-0005)"),
    (
        r"tailwind\.config\.(?:js|ts|cjs)|postcss|\bnpm\b|\bnpx\b|\bpnpm\b|\byarn\b|\bvite\b|webpack",
        "requiere Node: no hay toolchain de JavaScript (ADR-0005)",
    ),
    (r"<script(?![^>]*\bsrc=)[^>]*>", "script en línea: la CSP de Kiro lo desaconseja (ADR-0010)"),
)

_FONT_CATEGORY = {"serif": "serif", "monospace": "mono"}


def _fontsource_category(category: str) -> str:
    return _FONT_CATEGORY.get(category.strip().lower().replace(" ", ""), "sans")


def _rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def build_fonts(
    typography: bytes,
    google_fonts: bytes,
    fontsource: Iterable[Mapping[str, object]],
) -> list[dict[str, str]]:
    """Every font uupm names, and the Fontsource family that stands for it."""
    available: dict[str, Mapping[str, object]] = {}
    for font in fontsource:
        subsets = font.get("subsets")
        weights = font.get("weights")
        if (
            isinstance(subsets, list)
            and "latin" in subsets
            and isinstance(weights, list)
            and 400 in weights
        ):
            available[str(font["family"]).casefold()] = font

    google_category = {
        row["Family"].casefold(): _fontsource_category(row["Category"])
        for row in _rows(google_fonts)
        if row.get("Family")
    }

    names: set[str] = set()
    for row in _rows(typography):
        names.update(row[key].strip() for key in ("Heading Font", "Body Font") if row.get(key))

    result = []
    for name in sorted(names, key=str.casefold):
        font = available.get(name.casefold())
        if font is not None:
            category = _fontsource_category(str(font.get("category", "")))
            family = str(font["family"])
            raw = font.get("weights")
            weights = (
                " ".join(str(w) for w in sorted(raw) if isinstance(w, int))
                if isinstance(raw, list)
                else ""
            )
        else:
            category = google_category.get(name.casefold(), "sans")
            family, weights = "", ""
        result.append(
            {"source_font": name, "fontsource": family, "category": category, "weights": weights}
        )
    return result


def _saturation(hex_value: str) -> float:
    r, g, b = parse_hex(hex_value)
    high, low = max(r, g, b), min(r, g, b)
    if high == low:
        return 0.0
    lightness = (high + low) / 2
    return (high - low) / (1 - abs(2 * lightness - 1))


def build_palettes(colors: bytes) -> list[dict[str, str]]:
    """Per product type: does uupm's primary pass AA with our compiler, and what else."""
    result = []
    for row in _rows(colors):
        product = row["Product Type"].strip()
        primary = row["Primary"].strip()
        try:
            palette = derive_palette(Brand.model_validate({"primary": primary}))
            ok = not palette.failures
            suggestion = "" if ok else (suggest_primary(primary) or "")
            _, chroma, hue = rgb_to_oklch(parse_hex(primary))
            saturation = _saturation(primary)
        except (BrandError, ValidationError, ValueError):
            result.append(
                {
                    "product_type": product,
                    "primary": primary,
                    "aa": "invalid",
                    "suggested": "",
                    "purple": "no",
                    "saturated": "no",
                }
            )
            continue
        result.append(
            {
                "product_type": product,
                "primary": primary,
                "aa": "ok" if ok else "fails",
                "suggested": suggestion,
                # OKLCH hue of purples and violets, with enough chroma to read as one.
                "purple": "yes" if 285 <= hue <= 335 and chroma >= 0.1 else "no",
                "saturated": "yes" if saturation > 0.8 else "no",
            }
        )
    return result


def nearest_preset(text: str, presets: Iterable[str] | None = None) -> str:
    """The Kiro preset whose character is closest to a uupm style description."""
    known = set(presets) if presets is not None else set(PRESETS)
    lowered = text.lower()
    for pattern, preset in STYLE_RULES:
        if preset in known and re.search(pattern, lowered):
            return preset
    return ""


def build_styles(styles: bytes, presets: Iterable[str] | None = None) -> list[dict[str, str]]:
    result = []
    for row in _rows(styles):
        identity = row.get("Style ID") or row.get("Style Category", "")
        # What the style is called decides first; its keywords only if the name says
        # nothing. "Best For" is left out on purpose: "modern enterprise apps" is
        # about who uses it, and would make half the catalogue look institutional.
        named = f"{row.get('Style Category', '')} {row.get('Aliases', '')}"
        preset = nearest_preset(named, presets) or nearest_preset(
            f"{named} {row.get('Keywords', '')}", presets
        )
        result.append(
            {
                "style_id": identity.strip(),
                "name": row.get("Style Category", "").strip(),
                "preset": preset,
            }
        )
    return result


def build_stack_skips(stack: bytes) -> list[dict[str, str]]:
    result = []
    for row in _rows(stack):
        blob = " ".join(row.values())
        for pattern, reason in STACK_SKIP_RULES:
            if re.search(pattern, blob, re.IGNORECASE):
                result.append(
                    {
                        "no": row.get("No", ""),
                        "guideline": row.get("Guideline", ""),
                        "reason": reason,
                    }
                )
                break
    return result


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]], header: Sequence[str]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(header), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def write_overlay(
    files: Mapping[str, bytes],
    fontsource: Iterable[Mapping[str, object]],
    dest: Path = OVERLAY,
) -> dict[str, int]:
    """Write the four overlay tables next to each other; returns their row counts."""
    dest.mkdir(parents=True, exist_ok=True)
    tables = {
        "fonts.csv": (
            build_fonts(files["data/typography.csv"], files["google-fonts.csv"], fontsource),
            ("source_font", "fontsource", "category", "weights"),
        ),
        "palettes.csv": (
            build_palettes(files["data/colors.csv"]),
            ("product_type", "primary", "aa", "suggested", "purple", "saturated"),
        ),
        "styles.csv": (build_styles(files["data/styles.csv"]), ("style_id", "name", "preset")),
        "stack-skip.csv": (
            build_stack_skips(files["data/stacks/html-tailwind.csv"]),
            ("no", "guideline", "reason"),
        ),
    }
    counts = {}
    for name, (rows, header) in tables.items():
        _write_csv(dest / name, rows, header)
        counts[name] = len(rows)
    (dest / "README.md").write_text(README, encoding="utf-8")
    return counts


README = f"""# uupm, translated to Kiro

Generated by `scripts/vendor_uupm.py` from uupm {VERSION} ({COMMIT[:7]}). Do not edit
by hand: `make vendor-uupm` rebuilds it, and a test checks it against the data.

- `fonts.csv`: each font uupm names, the Fontsource family that stands for it (empty
  if there is none), its category and the weights Fontsource has.
- `palettes.csv`: each product palette: does its primary pass AA with Kiro's
  compiler, the nearest hex that does, and taste's flags (purple, saturation over
  80 %).
- `styles.csv`: each uupm style and the nearest Kiro preset (empty if none).
- `stack-skip.csv`: the `html-tailwind` guidelines that cannot be followed here (a
  CDN, Node, an inline script) and why. Empty while upstream's advice for this stack
  has none.

Why: `references/constitution.md`. In short, the clashes between what uupm
recommends and what this platform allows are settled once, here, not in every
conversation.
"""


# --- Command line ---------------------------------------------------------------------------


def run(
    *,
    root: Path = ROOT,
    client: httpx2.Client | None = None,
    log: Callable[[str], None] = print,
) -> None:
    """Fetch, verify, write the vendored tree and rebuild the overlay."""
    log(f"descargando uupm {VERSION} ({COMMIT[:7]})...")
    tarball = fetch_bytes(TARBALL_URL, limit=MAX_TARBALL_BYTES, label="uupm", client=client)
    files = extract(tarball)
    lock = write_vendored(files, root / ".claude/skills/kiro-design/uupm")
    log(f"  {len(lock)} archivos escritos en uupm/ y su vendor.lock.json")
    fontsource = json.loads(
        fetch_bytes(FONTSOURCE_URL, limit=20 * 1024 * 1024, label="Fontsource", client=client)
    )
    counts = write_overlay(files, fontsource, root / ".claude/skills/kiro-design/uupm-kiro")
    for name, count in counts.items():
        log(f"  uupm-kiro/{name}: {count} filas")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("verify", help="comprobar que uupm/ coincide con su lock")
    args = parser.parse_args(argv)

    try:
        if args.command == "verify":
            problems = verify()
            for problem in problems:
                print(f"  ✗ {problem}", file=sys.stderr)
            print("uupm/ coincide con su lock" if not problems else f"{len(problems)} diferencias")
            return 1 if problems else 0
        run()
    except BrandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
