"""Writing into `DESIGN.md` without owning it.

`DESIGN.md` is the project's prose, filled in by `/kiro-init` and edited by
people. The engine only ever adds lines to two sections, `Decisiones de diseño`
and `Procedencia`, so that a decision made once (a rule allowed on purpose, a
colour that had to move for contrast, where a style came from) is written down
where the next session reads it. Everything else in the file is left alone, and
adding the same line twice changes nothing.
"""

from __future__ import annotations

import re

DECISIONS_HEADING = "## Decisiones de diseño"
PROVENANCE_HEADING = "## Procedencia"

_HEADING = re.compile(r"^## .*$", re.MULTILINE)
_DIALS = {
    "variance": "DESIGN_VARIANCE",
    "motion": "MOTION_INTENSITY",
    "density": "VISUAL_DENSITY",
}


def read_dials(text: str) -> dict[str, int]:
    """The three dials a project wrote in `DESIGN.md` (1 to 10); absent or `TODO` are skipped."""
    found: dict[str, int] = {}
    for key, label in _DIALS.items():
        match = re.search(rf"{label}`?\s*\|\s*(\d+)\s*\|", text)
        if match and 1 <= int(match.group(1)) <= 10:
            found[key] = int(match.group(1))
    return found


def add_lines(text: str, heading: str, lines: list[str]) -> str:
    """Append `lines` to the section `heading`, creating it at the end if absent.

    Lines already present in the section are skipped, so applying a proposal
    twice does not repeat itself.
    """
    if not lines:
        return text
    match = re.search(rf"^{re.escape(heading)}[ \t]*$", text, re.MULTILINE)
    if match is None:
        body = "\n".join(lines)
        return f"{text.rstrip()}\n\n{heading}\n\n{body}\n"

    following = _HEADING.search(text, match.end())
    end = following.start() if following else len(text)
    section = text[match.end() : end]
    fresh = [line for line in lines if line not in section]
    if not fresh:
        return text

    kept = section.rstrip()
    # After a placeholder comment (guidance for the next person, not content to
    # replace) or an empty section, leave a blank line; after a list, continue it.
    continues_a_list = bool(kept.strip()) and not kept.endswith("-->")
    addition = kept + ("\n" if continues_a_list else "\n\n") + "\n".join(fresh) + "\n"
    tail = "\n" if following else ""
    return f"{text[: match.end()]}{addition}{tail}{text[end:]}"
