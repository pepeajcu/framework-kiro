"""Brand assets: logo validation, colour tokens, and the logo reaching the page."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import branding
from app.branding import (
    BrandError,
    apply_brand_block,
    brand_tokens,
    contrast_ratio,
    find_logo,
    parse_hex,
    render_brand_block,
    validate_logo,
)

SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    b'<circle cx="16" cy="16" r="8"/></svg>'
)


def make_png(width: int, height: int) -> bytes:
    """A minimal valid PNG of the given size (all-black pixels)."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body)
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


# --- Logo validation --------------------------------------------------------


def test_accepts_a_clean_svg() -> None:
    check = validate_logo(SVG)

    assert check.extension == ".svg"
    assert check.warning is None


def test_accepts_a_square_png() -> None:
    check = validate_logo(make_png(256, 256))

    assert check.extension == ".png"
    assert check.warning is None


def test_rejects_a_non_square_png() -> None:
    with pytest.raises(BrandError, match="cuadrado"):
        validate_logo(make_png(256, 128))


def test_warns_about_a_tiny_png() -> None:
    assert validate_logo(make_png(32, 32)).warning is not None


@pytest.mark.parametrize(
    "payload",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.test/x.png"/></svg>',
        b'<!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg"></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"/></svg>',
    ],
)
def test_rejects_active_content_in_svg(payload: bytes) -> None:
    with pytest.raises(BrandError):
        validate_logo(payload)


def test_allows_internal_svg_references() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><defs><g id="a"/></defs><use href="#a"/></svg>'

    assert validate_logo(svg).extension == ".svg"


def test_warns_when_svg_is_not_square() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 40"></svg>'

    assert validate_logo(svg).warning is not None


@pytest.mark.parametrize("payload", [b"", b"<html><body>hola</body></html>", b"\xff\xfe\x00"])
def test_rejects_things_that_are_not_images(payload: bytes) -> None:
    with pytest.raises(BrandError):
        validate_logo(payload)


def test_rejects_an_oversized_file() -> None:
    with pytest.raises(BrandError, match="máximo"):
        validate_logo(SVG + b" " * branding.MAX_LOGO_BYTES)


def test_format_is_sniffed_not_trusted() -> None:
    """HTML saved as logo.png is not a PNG, whatever the file name says."""
    with pytest.raises(BrandError):
        validate_logo(b"<html><script>alert(1)</script></html>")


# --- find_logo --------------------------------------------------------------


def test_find_logo_returns_none_when_empty(tmp_path: Path) -> None:
    assert find_logo(tmp_path) is None


def test_find_logo_prefers_svg_over_png(tmp_path: Path) -> None:
    (tmp_path / "logo.png").write_bytes(make_png(64, 64))
    (tmp_path / "logo.svg").write_bytes(SVG)

    found = find_logo(tmp_path)

    assert found is not None
    assert found.name == "logo.svg"


# --- Colour -----------------------------------------------------------------


def test_parse_hex_accepts_short_and_long_forms() -> None:
    assert parse_hex("#fff") == parse_hex("FFFFFF") == (1.0, 1.0, 1.0)


def test_parse_hex_rejects_garbage() -> None:
    with pytest.raises(BrandError):
        parse_hex("teal")


def test_contrast_ratio_matches_the_wcag_extremes() -> None:
    assert contrast_ratio((0, 0, 0), (1, 1, 1)) == pytest.approx(21.0)


def test_dark_brand_gets_a_light_foreground() -> None:
    tokens = brand_tokens("#0F766E")

    assert tokens.light["--primary-foreground"].startswith("oklch(0.985")
    assert tokens.contrast_light >= 4.5


def test_pale_brand_gets_a_dark_foreground() -> None:
    """Yellow with white text is the classic unreadable button."""
    tokens = brand_tokens("#FACC15")

    assert tokens.light["--primary-foreground"].startswith("oklch(0.145")
    assert tokens.contrast_light >= 4.5


def test_dark_mode_lifts_a_dark_brand_colour() -> None:
    tokens = brand_tokens("#1E1B4B")

    light_l = float(tokens.light["--primary"].split()[0].removeprefix("oklch("))
    dark_l = float(tokens.dark["--primary"].split()[0].removeprefix("oklch("))
    assert dark_l >= 0.72 > light_l


def test_apply_brand_block_is_idempotent() -> None:
    css = '@import "tailwindcss";\n@source "../../../app/**/*.py";\n\n:root {}\n'
    first = apply_brand_block(css, render_brand_block(brand_tokens("#0F766E")))
    second = apply_brand_block(first, render_brand_block(brand_tokens("#B91C1C")))

    assert second.count("kiro:brand:start") == 1
    assert "#B91C1C" not in second  # source hex is only a comment when passed
    assert first != second


def test_apply_brand_block_fails_loudly_without_an_anchor() -> None:
    with pytest.raises(BrandError):
        apply_brand_block("body {}", render_brand_block(brand_tokens("#0F766E")))


def test_radius_lands_in_root() -> None:
    block = render_brand_block(brand_tokens("#0F766E"), radius="0.25rem")

    assert "--radius: 0.25rem;" in block


# --- The logo reaches the page ----------------------------------------------


def test_header_shows_the_logo_when_the_project_has_one(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "logo.svg").write_bytes(SVG)
    monkeypatch.setattr(branding, "BRAND_DIR", tmp_path)
    monkeypatch.setattr(
        "app.templating.find_logo", lambda: branding.find_logo(tmp_path), raising=True
    )

    html = client.get("/").text

    assert "/static/brand/logo.svg" in html
    assert 'type="image/svg+xml"' in html


def test_header_falls_back_to_text_without_a_logo(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.templating.find_logo", lambda: None, raising=True)

    html = client.get("/").text

    assert "/static/brand/" not in html
    assert "favicon.svg" in html
