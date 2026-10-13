"""Vendor the motion libraries a project's `[motion] level` needs.

    make motion level=motion      # Motion (motion.dev), for levels 7-8
    make motion level=gsap        # GSAP + ScrollTrigger, for levels 9-10

Nothing here is committed to the framework: each project downloads what its
level asks for, so each accepts the library's licence for itself (GSAP's is not
the MIT of the rest of Kiro: see the NOTICE this writes). `make design build`
calls this on its own when a level needs a file that is missing.

Every file is pinned to an exact version *and* a SHA-256. npm versions are
immutable, so a mismatch means the origin served something else, and the file
is refused rather than shipped.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx2

from app.branding import BrandError
from app.design_engine.contract import DesignError
from app.design_engine.motion import engine_for
from app.design_engine.paths import Paths
from scripts.fetch import fetch_bytes

JSDELIVR = "https://cdn.jsdelivr.net/npm"
VENDOR_DIR = "js/vendor"
NOTICE = f"{VENDOR_DIR}/NOTICE.md"
MAX_BYTES = 200_000


@dataclass(frozen=True)
class VendorFile:
    url: str
    dest: str  # relative to app/static/
    sha256: str


@dataclass(frozen=True)
class Library:
    key: str
    title: str
    version: str
    license_name: str
    license_url: str
    notes: str
    files: tuple[VendorFile, ...]


LIBRARIES: dict[str, Library] = {
    "motion": Library(
        key="motion",
        title="Motion One (npm: motion)",
        version="10.18.0",
        license_name="MIT",
        license_url="https://github.com/motiondivision/motion/blob/main/LICENSE.md",
        notes=(
            "La línea 10.x, a propósito: desde la 11 el paquete `motion` incorpora Framer Motion "
            "y su bundle pasa de 25 KB a 150 KB (más que GSAP y ScrollTrigger juntos)."
        ),
        files=(
            VendorFile(
                f"{JSDELIVR}/motion@10.18.0/dist/motion.min.js",
                f"{VENDOR_DIR}/motion.min.js",
                "f850f9428bf40bdb140a37225af409224f1cb8f2b7eb3d7e4e9f82888e3b2b6e",
            ),
        ),
    ),
    "gsap": Library(
        key="gsap",
        title="GSAP y ScrollTrigger (npm: gsap)",
        version="3.15.0",
        license_name="GSAP Standard 'no charge' license",
        license_url="https://gsap.com/standard-license",
        notes=(
            "Uso comercial permitido y gratuito. Prohibido usarlo en herramientas que permitan "
            "construir animaciones visuales sin código y compitan con Webflow, y quitar los "
            "avisos de propiedad de los archivos. Estos archivos se descargan en TU proyecto "
            "bajo tu aceptación de esa licencia; el framework Kiro no los redistribuye."
        ),
        files=(
            VendorFile(
                f"{JSDELIVR}/gsap@3.15.0/dist/gsap.min.js",
                f"{VENDOR_DIR}/gsap.min.js",
                "92bb9a96476f983d212a2bc4f54c889039c1696dd4461d40a736860938570fbb",
            ),
            VendorFile(
                f"{JSDELIVR}/gsap@3.15.0/dist/ScrollTrigger.min.js",
                f"{VENDOR_DIR}/ScrollTrigger.min.js",
                "b0b14d67b55b0c43c756ac0b106cfcb09d0879945f6ead64451065b0672916a2",
            ),
        ),
    ),
}


def library_for_level(level: int) -> Library | None:
    """The library `level` needs, or None for the levels that need none."""
    engine = engine_for(level)
    return LIBRARIES.get(engine)


def vendor_library(
    library: Library, static_dir: Path, *, client: httpx2.Client | None = None
) -> tuple[str, ...]:
    """Download and verify any file of `library` that is missing. Returns what it wrote."""
    written: list[str] = []
    for file in library.files:
        target = static_dir / file.dest
        if target.is_file() and _sha256(target.read_bytes()) == file.sha256:
            continue
        data = fetch_bytes(file.url, limit=MAX_BYTES, label=Path(file.dest).name, client=client)
        digest = _sha256(data)
        if digest != file.sha256:
            raise DesignError(
                f"{Path(file.dest).name}: el origen devolvió un archivo distinto del esperado "
                f"(sha256 {digest[:12]}…, esperado {file.sha256[:12]}…). No lo instalo"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        written.append(file.dest)
    write_notice(static_dir)
    return tuple(written)


def vendor_for_level(
    level: int, static_dir: Path, *, client: httpx2.Client | None = None
) -> tuple[str, ...]:
    library = library_for_level(level)
    if library is None:
        return ()
    return vendor_library(library, static_dir, client=client)


def render_notice(static_dir: Path) -> str | None:
    """`NOTICE.md` for the libraries whose files are present, or None if none are."""
    sections: list[str] = []
    for library in LIBRARIES.values():
        if not all((static_dir / f.dest).is_file() for f in library.files):
            continue
        files = "\n".join(
            f"  - `{Path(f.dest).name}` (sha256 `{f.sha256[:16]}…`)" for f in library.files
        )
        sections.append(
            f"## {library.title} {library.version}\n\n"
            f"- Licencia: **{library.license_name}**: {library.license_url}\n"
            f"- Origen: {library.files[0].url.rsplit('/', 1)[0]}/\n"
            f"- Archivos:\n{files}\n\n"
            f"{library.notes}\n"
        )
    if not sections:
        return None
    return (
        "# Librerías de motion vendorizadas\n\n"
        "Las instala `make design build` (o `make motion level=…`) según `[motion] level` en "
        "`design.toml`. No las edites: se reemplazan al volver a vendorizar. Ver "
        "`docs/decisions/0015-motion-vendorizado-por-niveles.md`.\n\n" + "\n".join(sections)
    )


def write_notice(static_dir: Path) -> None:
    notice = render_notice(static_dir)
    target = static_dir / NOTICE
    if notice is None:
        target.unlink(missing_ok=True)
    else:
        target.write_text(notice, encoding="utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--level", required=True, choices=("motion", "gsap"))
    args = parser.parse_args(argv)

    paths = Paths()
    try:
        library = LIBRARIES[args.level]
        written = vendor_library(library, paths.static)
    except BrandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if written:
        print(f"{library.title} {library.version} instalado: {', '.join(written)}")
    else:
        print(f"{library.title} {library.version} ya estaba instalado y verificado")
    print(f"licencia: {library.license_name} ({library.license_url})")
    print(
        f"para usarlo, design.toml necesita [motion] level >= {7 if args.level == 'motion' else 9}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
