"""Add or replace one of the project's fonts.

    make font name="Fraunces" weights="400,700" role=display
    make font name="Geist" weights="400,600" role=body
    make font name="JetBrains Mono" weights=400 role=mono

Fonts are local woff2 files (ADR-0005): this checks the family exists on
Fontsource, records it in `design.toml`, and runs `make design build`, which
downloads the files into `app/static/fonts/` and writes the `@font-face` rules.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx2

from app.branding import BrandError
from app.design_engine.contract import (
    DesignContract,
    DesignError,
    contract_from_data,
    contract_to_data,
    dump_contract,
    font_face_from_values,
    font_slug,
    load_contract,
)
from app.design_engine.paths import Paths
from scripts.design import build, print_report, write_atomically

API = "https://api.fontsource.org/v1/fonts"
ROLES = ("display", "body", "mono")
# Fontsource's `category` to the generic family the fallback stack should end in.
_FALLBACK_BY_CATEGORY = {"serif": "serif", "monospace": "mono"}


def lookup(slug: str, *, client: httpx2.Client | None = None) -> dict[str, Any] | None:
    """Fontsource's metadata for `slug`, or None if the API cannot be reached.

    A 404 is *not* None: it raises, because "this family does not exist" is a
    fact worth stopping for. An unreachable API only skips the extra checks.
    """
    http = client or httpx2.Client(timeout=10.0, follow_redirects=True)
    try:
        response = http.get(f"{API}/{slug}")
    except httpx2.HTTPError:
        return None
    finally:
        if client is None:
            http.close()
    if response.status_code == 404:
        raise DesignError(
            f"'{slug}' no existe en Fontsource. Búscala en https://fontsource.org/fonts "
            "(Satoshi, Cabinet Grotesk y General Sans no están: son de Fontshare)"
        )
    if response.status_code != 200:
        return None
    data = response.json()
    return data if isinstance(data, dict) else None


def add_font(
    contract: DesignContract,
    role: str,
    name: str,
    weights: list[int],
    *,
    fallback: str | None,
    client: httpx2.Client | None = None,
) -> tuple[DesignContract, list[str]]:
    """`contract` with `role` set to the family, plus any notes for the user."""
    if role not in ROLES:
        raise DesignError(f"role debe ser uno de: {' | '.join(ROLES)}")
    face = font_face_from_values(name, weights, fallback)

    notes: list[str] = []
    info = lookup(face.slug, client=client)
    if info is None:
        notes.append("no pude consultar Fontsource; compruebo la familia al descargarla")
    else:
        available = [int(w) for w in info.get("weights", [])]
        missing = [w for w in face.weights if w not in available]
        if missing:
            raise DesignError(
                f"{face.name} no tiene los pesos {', '.join(map(str, missing))}; "
                f"disponibles: {', '.join(map(str, available))}"
            )
        if "latin" not in info.get("subsets", []):
            raise DesignError(f"{face.name} no tiene el subconjunto latin")
        if fallback is None:
            inferred = _FALLBACK_BY_CATEGORY.get(str(info.get("category")))
            if inferred and inferred != {"mono": "mono"}.get(role, "sans"):
                face = face.model_copy(update={"fallback": inferred})
                notes.append(f"familia {info['category']}: la reserva será {inferred}")

    data = contract_to_data(contract)
    data["type"][role] = face.model_dump(exclude_none=True)
    return contract_from_data(data), notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--name", required=True, help='familia de Fontsource, ej. "Fraunces"')
    parser.add_argument("--weights", default="400", help="pesos separados por coma, ej. 400,700")
    parser.add_argument("--role", required=True, choices=ROLES)
    parser.add_argument("--fallback", choices=("sans", "serif", "mono"), help="familia de reserva")
    args = parser.parse_args(argv)

    try:
        weights = [int(w) for w in args.weights.split(",") if w.strip()]
    except ValueError:
        print("error: weights debe ser una lista de números, ej. 400,700", file=sys.stderr)
        return 1

    paths = Paths()
    try:
        contract, notes = add_font(
            load_contract(paths.contract),
            args.role,
            args.name,
            weights,
            fallback=args.fallback,
        )
        write_atomically(paths.contract, dump_contract(contract))
        print(
            f"{args.name} ({font_slug(args.name)}) anotada como fuente {args.role} en design.toml"
        )
        for note in notes:
            print(f"  {note}")
        print_report(build(paths), paths)
    except BrandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
