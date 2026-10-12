"""Set the project's brand: logo and colours.

    make logo src=./mi-logo.svg
    make logo src=https://example.com/logo.png
    make brand-colors primary="#0F766E" [radius=0.5rem]

The logic lives in `app/branding.py` (pure, tested); this file only does the I/O.
Both commands are idempotent: run them again with another value to replace it.
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
    STATIC_DIR,
    BrandError,
    apply_brand_block,
    brand_tokens,
    render_brand_block,
    validate_logo,
)

INPUT_CSS = STATIC_DIR / "css" / "input.css"
# WCAG AA for normal text. Below this the button label is hard to read.
MIN_CONTRAST = 4.5


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


def set_colors(primary: str, radius: str | None) -> None:
    tokens = brand_tokens(primary)
    block = render_brand_block(tokens, radius=radius, primary_hex=primary)
    INPUT_CSS.write_text(apply_brand_block(INPUT_CSS.read_text(encoding="utf-8"), block), "utf-8")

    print(f"tokens escritos en {INPUT_CSS.relative_to(Path.cwd())}")
    for mode, ratio in (("claro", tokens.contrast_light), ("oscuro", tokens.contrast_dark)):
        verdict = "ok" if ratio >= MIN_CONTRAST else "BAJO"
        print(f"  contraste del botón primario, modo {mode}: {ratio:.1f}:1 ({verdict})")
    if min(tokens.contrast_light, tokens.contrast_dark) < MIN_CONTRAST:
        print(
            f"aviso: algún modo queda por debajo de {MIN_CONTRAST}:1 (WCAG AA). "
            "Prueba un tono más oscuro o más claro de la marca",
            file=sys.stderr,
        )
    print("ahora: make css")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    sub = parser.add_subparsers(dest="command", required=True)

    logo = sub.add_parser("logo", help="importar el logo (ruta o URL; SVG o PNG 1:1)")
    logo.add_argument("src")

    colors = sub.add_parser("colors", help="escribir los tokens de color de la marca")
    colors.add_argument("--primary", required=True, help="hex del color de marca, ej. #0F766E")
    colors.add_argument("--radius", help="radio de esquinas, ej. 0.5rem")

    args = parser.parse_args()
    try:
        if args.command == "logo":
            set_logo(args.src)
        else:
            set_colors(args.primary, args.radius)
    except BrandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
