"""Set the project's brand: logo and colours.

    make logo src=./mi-logo.svg
    make logo src=https://example.com/logo.png
    make brand-colors primary="#0F766E" [radius=0.5rem] [neutral=warm] [surface=cream]
                      [secondary="#1E3A5F"]

The logic lives in `app/branding.py` and `app/design_engine/` (pure, tested); this
file only does the I/O. `colors` is a shortcut: it writes the `[brand]` table of
`design.toml` and runs `make design build`, so the contract and the CSS never
disagree. Both commands are idempotent: run them again to replace the value.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx2

from app.branding import (
    BRAND_DIR,
    LOGO_NAMES,
    MAX_LOGO_BYTES,
    BrandError,
    validate_logo,
)
from app.design_engine.contract import (
    contract_from_data,
    contract_to_data,
    dump_contract,
    load_contract,
)
from app.design_engine.paths import Paths
from scripts.design import build, print_report, write_atomically


def _read_source(src: str) -> bytes:
    """Bytes of a local path or an http(s) URL, capped at the logo size limit."""
    if src.startswith(("http://", "https://")):
        data = bytearray()
        try:
            with httpx2.stream("GET", src, follow_redirects=True, timeout=10.0) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_LOGO_BYTES:
                        raise BrandError(f"el logo supera {MAX_LOGO_BYTES // 1000} KB")
        except httpx2.HTTPError as exc:
            raise BrandError(f"no pude descargar el logo: {exc}") from exc
        return bytes(data)

    path = Path(src).expanduser()
    if not path.is_file():
        raise BrandError(f"no existe el archivo: {path}")
    return path.read_bytes()


def set_logo(src: str) -> None:
    data = _read_source(src)
    check = validate_logo(data)

    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    # One logo at a time: a stale logo.png would otherwise survive a new logo.svg.
    for name in LOGO_NAMES:
        (BRAND_DIR / name).unlink(missing_ok=True)
    target = BRAND_DIR / f"logo{check.extension}"
    target.write_bytes(data)

    print(f"logo guardado en {target.relative_to(Path.cwd())}")
    if check.warning:
        print(f"aviso: {check.warning}", file=sys.stderr)
    print("se mostrará en la cabecera y como favicon; recarga la página")


def set_colors(
    primary: str,
    *,
    radius: str | None,
    neutral: str | None,
    surface: str | None,
    secondary: str | None,
    paths: Paths | None = None,
) -> None:
    """Write the `[brand]` table of design.toml and rebuild. Unset options keep their value."""
    paths = paths or Paths()
    data = contract_to_data(load_contract(paths.contract))
    data["brand"]["primary"] = primary
    for key, value in (
        ("radius", radius),
        ("neutral", neutral),
        ("surface", surface),
        ("secondary", secondary),
    ):
        if value is not None:
            data["brand"][key] = value
    contract = contract_from_data(data)
    write_atomically(paths.contract, dump_contract(contract))
    print_report(build(paths), paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    sub = parser.add_subparsers(dest="command", required=True)

    logo = sub.add_parser("logo", help="importar el logo (ruta o URL; SVG o PNG 1:1)")
    logo.add_argument("src")

    colors = sub.add_parser("colors", help="escribir los tokens de color de la marca")
    colors.add_argument("--primary", required=True, help="hex del color de marca, ej. #0F766E")
    colors.add_argument("--radius", help="radio de esquinas, ej. 0.5rem o 0")
    colors.add_argument("--neutral", choices=("pure", "warm", "cool", "tinted"), help="grises")
    colors.add_argument("--surface", choices=("light", "cream", "dark"), help="superficie")
    colors.add_argument("--secondary", help='segundo color de marca; "" para quitarlo')

    args = parser.parse_args()
    try:
        if args.command == "logo":
            set_logo(args.src)
        else:
            set_colors(
                args.primary,
                radius=args.radius,
                neutral=args.neutral,
                surface=args.surface,
                secondary=args.secondary,
            )
    except BrandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
