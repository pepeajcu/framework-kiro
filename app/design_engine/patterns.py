"""Generic page patterns: the shapes that make a project look like every other one.

Pure functions over the text of one template. `checks.py` walks the project and
turns each `Hit` into a warning. They are heuristics on markup, not an analysis
of the rendered page, so they are warnings and a project can allow any of them
with `[rules] allow` in `design.toml` (rule table: `rules.py`).

What they look at is the *shape* taste-skill names as the first thing that makes
a page read as generated: a centred headline over three equal cards, the logo
wall, the three identical pricing columns, a carousel of testimonials; plus the
small tells (emoji, `h-screen`, blur on scrolling content, a vocabulary, an em
dash, a placeholder name).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser

_JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.DOTALL | re.IGNORECASE)
# The tab title and the meta description are metadata, not copy on the page.
_METADATA_BLOCK = re.compile(
    r"\{%-?\s*block\s+(?:title|description|og_image)\s*-?%\}.*?\{%-?\s*endblock[^%]*%\}", re.DOTALL
)
_JINJA_TAG = re.compile(r"\{%.*?%\}|\{\{.*?\}\}", re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>", re.DOTALL)
_CLASS_ATTRIBUTE = re.compile(r"""\bclass\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
_H1 = re.compile(r"<h1\b", re.IGNORECASE)

_EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿⭐⭕️]")
_VOCABULARY = re.compile(
    r"\b(elevate[sd]?|seamless(?:ly)?|unleash(?:es|ed)?|next-gen(?:eration)?|"
    r"game-chang(?:er|ing)|delve[sd]?)\b",
    re.IGNORECASE,
)
_PLACEHOLDER = re.compile(r"\b(John Doe|Jane Doe|Acme(?: Corp| Inc)?|Lorem ipsum)\b", re.IGNORECASE)
_TRUST_WALL = re.compile(
    r"conf[ií]an en nosotros|empresas que conf[ií]an|nuestros clientes|"
    r"trusted by|as seen (?:in|on)|companies (?:that )?trust",
    re.IGNORECASE,
)
_PRICING_WORD = re.compile(r"\b(pricing|precios?|planes?)\b", re.IGNORECASE)
_PRICE = re.compile(
    r"[$€£]\s?\d|\d\s?(?:€|\$|USD|EUR)\b|/\s?(?:mes|month|año|year)\b", re.IGNORECASE
)
_CAROUSEL = re.compile(r"carousel|carrusel|swiper|slider|snap-x", re.IGNORECASE)
_TESTIMONIAL = re.compile(r"testimonial|testimonio", re.IGNORECASE)
_THREE_COLUMNS = re.compile(r"(?<![\w-])(?:[a-z0-9]+:)*grid-cols-3(?![\w-])")
_CARD_CLASS = re.compile(r"""\bclass\s*=\s*["'][^"']*(?<![\w-])card(?![\w-])""", re.IGNORECASE)
_CENTRED = re.compile(r"(?<![\w-])text-center(?![\w-])")
_FIXED = re.compile(r"(?:^|[\s:])(?:fixed|sticky)(?:\s|$)")
_H_SCREEN = re.compile(r"(?:^|[\s:])h-screen(?:\s|$)")


@dataclass(frozen=True)
class Hit:
    rule: str
    detail: str


def strip_comments(text: str) -> str:
    """The template without Jinja and HTML comments: a comment that documents a
    pattern (the scaffolding's own does) is not a use of it."""
    return _HTML_COMMENT.sub("", _JINJA_COMMENT.sub("", text))


def visible_text(code: str) -> str:
    """What a visitor reads: no scripts, styles, tags, Jinja or page metadata."""
    code = _SCRIPT_OR_STYLE.sub(" ", code)
    code = _METADATA_BLOCK.sub(" ", code)
    code = _JINJA_TAG.sub(" ", code)
    return html.unescape(_HTML_TAG.sub(" ", code))


def _classes(code: str) -> list[str]:
    return [m.group(1) or m.group(2) or "" for m in _CLASS_ATTRIBUTE.finditer(code)]


def scan(code: str) -> list[Hit]:
    """Every generic pattern found in one template (already without comments)."""
    hits: list[Hit] = []
    text = visible_text(code)
    classes = _classes(code)
    cards_after_h1 = _cards_after_first_h1(code)

    # P1: a centred headline, then a 3-column grid of cards.
    h1 = _H1.search(code)
    if h1 and cards_after_h1 >= 3:
        before = code[max(0, h1.start() - 400) : h1.end() + 200]
        if _CENTRED.search(before) and _THREE_COLUMNS.search(code[h1.start() :]):
            hits.append(Hit("P1", f"titular centrado y {cards_after_h1} tarjetas en 3 columnas"))

    # P2: the "trusted by" wall.
    wall = _TRUST_WALL.search(text)
    if wall:
        hits.append(Hit("P2", f"«{wall.group(0).strip()}»"))

    # P3: testimonials in a carousel.
    if _TESTIMONIAL.search(code) and _CAROUSEL.search(code):
        hits.append(Hit("P3", "testimonios en carrusel"))

    # P4: pricing in three identical columns.
    if (
        _THREE_COLUMNS.search(code)
        and _PRICING_WORD.search(text)
        and len(_PRICE.findall(text)) >= 3
        and len(_CARD_CLASS.findall(code)) >= 3
    ):
        hits.append(Hit("P4", "tres planes con el mismo formato"))

    # P5: h-screen.
    if any(_H_SCREEN.search(value) for value in classes):
        hits.append(Hit("P5", "h-screen"))

    # P6: blur that is not on, or inside, a fixed or sticky bar.
    if _blur_outside_a_bar(code):
        hits.append(Hit("P6", "backdrop-blur sin fixed ni sticky"))

    # P7: emoji (in markup, not only in the visible text: an alt or a title too).
    emoji = _EMOJI.search(_SCRIPT_OR_STYLE.sub(" ", code))
    if emoji:
        hits.append(Hit("P7", f"«{emoji.group(0)}»"))

    # P8: the vocabulary.
    word = _VOCABULARY.search(text)
    if word:
        hits.append(Hit("P8", f"«{word.group(0)}»"))

    # P9: the em dash.
    if "—" in text:
        hits.append(Hit("P9", "—"))

    # P10: placeholder names.
    name = _PLACEHOLDER.search(text)
    if name:
        hits.append(Hit("P10", f"«{name.group(0)}»"))

    return hits


_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
)


class _BlurWatcher(HTMLParser):
    """Walks the tags, remembering whether an enclosing element is fixed or sticky."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stack: list[tuple[str, bool]] = []
        self.found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        value = dict(attrs).get("class") or ""
        pinned = bool(_FIXED.search(value))
        inside_bar = pinned or any(flag for _, flag in self.stack)
        if "backdrop-blur" in value and not inside_bar:
            self.found = True
        if tag not in _VOID:
            self.stack.append((tag, pinned))

    def handle_endtag(self, tag: str) -> None:
        # Drop everything up to the matching open tag; markup with Jinja around
        # it is not always balanced and must not make the stack drift.
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def _blur_outside_a_bar(code: str) -> bool:
    watcher = _BlurWatcher()
    watcher.feed(code)
    return watcher.found


def _cards_after_first_h1(code: str) -> int:
    h1 = _H1.search(code)
    return len(_CARD_CLASS.findall(code[h1.start() :])) if h1 else 0
