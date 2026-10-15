"""Architecture check: the hard rules of AGENTS.md, enforced by a machine.

`mypy` and `ruff` catch what a type or a style rule can say. They cannot say
"this router builds SQL" or "this form has no CSRF token", and those are the
mistakes an AI agent (or a tired person) makes while the rest of the code is
fine. This script reads the project with `ast` and a few regular expressions,
nothing else, and fails with a message that says what to do instead.

    make archcheck              # what `make check` and CI run
    make archcheck rules=1      # print the rule table

Python rules (K) and template rules (J):

    K1  SQL outside a repository               AGENTS.md rule 1
    K2  commit / rollback outside app/db.py    rule 2
    K3  HTTP objects in an inner layer         "Architecture" table
    K4  a router writing through a repository  "Architecture" table
    K5  the environment read outside config    rule 6
    K6  `async def` handler with no `await`    rule 7
    K7  page handler that does not declare `user`   rule 10
    K8  model not imported in app/models       rule 5
    J1  partial with `extends`, page on base.html   "Frontend specifics"
    J2  POST form without the CSRF field       "Forms and CSRF"
    J3  hard-coded colour in a template        "Identity lives in tokens"
    J4  Basecoat class that no longer exists   "Frontend specifics"
    J5  inline script or external resource     ADR-0005, ADR-0010

**An exception needs a reason.** Put the comment on the offending line or the
one above it (above the decorators for a handler):

    async def webhook(...):  # kiro: allow K6 — awaits the provider in the next step
    {# kiro: allow J5 — the payment widget has no self-hosted build #}

Without the reason after the dash the exception does not count. Every exception
in force is listed in the summary, so they stay visible in review.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    fix: str
    reference: str


RULES: dict[str, Rule] = {
    rule.id: rule
    for rule in (
        Rule(
            "K1",
            "SQL fuera de un repositorio",
            "muévelo a un método de app/repositories/<nombre>.py y llámalo desde aquí",
            "AGENTS.md regla 1",
        ),
        Rule(
            "K2",
            "commit/rollback fuera de app/db.py",
            "quítalo: get_db confirma al terminar la petición y deshace ante una excepción",
            "AGENTS.md regla 2",
        ),
        Rule(
            "K3",
            "un módulo de una capa interna importa fastapi/starlette",
            "pasa el dato como argumento (el router lo saca del Request) "
            "y devuelve datos, no respuestas",
            "AGENTS.md, tabla de arquitectura",
        ),
        Rule(
            "K4",
            "un router escribe a través de un repositorio",
            "pon la escritura en un servicio de app/services/ y llámalo desde el router",
            "AGENTS.md, tabla de arquitectura",
        ),
        Rule(
            "K5",
            "lectura del entorno fuera de app/config.py",
            "añade el valor a Settings en app/config.py e inyéctalo (AppSettings)",
            "AGENTS.md regla 6",
        ),
        Rule(
            "K6",
            "async def sin ningún await",
            "usa def: FastAPI ejecuta los handlers síncronos en un pool de hilos (ADR-0002)",
            "AGENTS.md regla 7",
        ),
        Rule(
            "K7",
            "un handler que renderiza una página no declara quién la mira",
            "añade el parámetro `user: OptionalUser` (o CurrentUser) "
            "para que la cabecera sepa quién está dentro",
            "AGENTS.md regla 10",
        ),
        Rule(
            "K8",
            "modelo sin importar en app/models/__init__.py",
            "impórtalo ahí: Alembic solo ve las tablas importadas y el resto no genera migración",
            "AGENTS.md regla 5",
        ),
        Rule(
            "J1",
            "un partial extiende un layout, o una página extiende base.html",
            "los partials son fragmentos sin extends; las páginas extienden "
            "layouts/app.html o layouts/landing.html",
            "AGENTS.md, Frontend specifics",
        ),
        Rule(
            "J2",
            "formulario POST sin el campo CSRF",
            'añade {% include "components/csrf_field.html" %} dentro del <form>, '
            "o el POST dará 403",
            "AGENTS.md, Forms and CSRF",
        ),
        Rule(
            "J3",
            "color escrito a mano en una plantilla",
            "usa un token (bg-primary, text-muted-foreground, border-border...); "
            "el color vive en design.toml",
            "AGENTS.md, Identity lives in tokens",
        ),
        Rule(
            "J4",
            "clase de Basecoat que ya no existe",
            'Basecoat 1.0 usa atributos: class="btn" data-variant="primary" data-size="sm"',
            "AGENTS.md, Frontend specifics",
        ),
        Rule(
            "J5",
            "script en línea o recurso de otro dominio",
            "vendoriza el recurso en app/static/ y cárgalo con asset(); la CSP solo admite 'self'",
            "ADR-0005 y ADR-0010",
        ),
    )
}

# --- What each rule looks for -------------------------------------------------

#: Layers that must not know what HTTP is (K3). `routers`, `deps`, `main`,
#: `middleware` and `templating` are the HTTP layer and may import it.
INNER_LAYERS = (
    "services",
    "repositories",
    "models",
    "schemas",
    "design_engine",
    "emails",
    "analytics",
)

#: Names that build a query when imported from SQLAlchemy (K1). `Session`,
#: `Mapped` and the like are types and stay allowed anywhere.
QUERY_NAMES = frozenset(
    {"select", "insert", "update", "delete", "text", "func", "and_", "or_", "desc", "asc", "exists"}
)
SESSION_RECEIVERS = frozenset({"db", "session", "self.db", "self.session"})
SESSION_QUERY_CALLS = frozenset({"execute", "scalars", "scalar", "query"})
REPOSITORY_WRITES = frozenset({"create", "update", "delete", "add"})
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})

#: What makes a handler resolve the session cookie (K7).
VIEWER_TOKENS = ("OptionalUser", "CurrentUser", "require_role", "require_user", "get_optional_user")

OBSOLETE_BASECOAT = re.compile(
    r"(?<![\w-])(?:btn-(?:primary|secondary|outline|ghost|destructive|link|sm|lg|xs|icon)"
    r"|badge-(?:primary|secondary|outline|destructive))(?![\w-])"
)

HARDCODED_COLOUR = re.compile(
    r"""
      (?:bg|text|border|fill|stroke|from|to|via|ring|outline|decoration|shadow|accent|caret|divide)
        -\[\#[0-9a-fA-F]{3,8}\]                                   # Tailwind arbitrary value
    | \b(?:rgba?|hsla?)\(\s*[\d.]                                 # rgb(12, 34, 56)
    | \boklch\(\s*[\d.]                                           # oklch(0.5 0.1 200)
    | \b(?:fill|stroke|stop-color|color|background(?:-color)?|border(?:-color)?)
        \s*[:=]\s*["']?\s*\#[0-9a-fA-F]{3,8}\b                    # style="color: #fff"
    """,
    re.VERBOSE,
)

INLINE_SCRIPT = re.compile(r"<script\b(?![^>]*\bsrc\s*=)([^>]*)>", re.IGNORECASE)
DATA_SCRIPT_TYPE = re.compile(
    r"""type\s*=\s*["']application/(?:ld\+json|json)["']""", re.IGNORECASE
)
EXTERNAL_RESOURCE = re.compile(
    r"""<(?:script|link|img|iframe|source|video|audio)\b[^>]*?\b(?:src|href)\s*=\s*["'](?:https?:)?//""",
    re.IGNORECASE | re.DOTALL,
)
FORM_OPEN = re.compile(r"<form\b[^>]*>", re.IGNORECASE | re.DOTALL)
POST_METHOD = re.compile(r"""\bmethod\s*=\s*["']?post\b""", re.IGNORECASE)
EXTENDS = re.compile(r"""\{%-?\s*extends\s+["']([^"']+)["']""")
JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
CLASS_ATTRIBUTE = re.compile(r"""\bclass\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)

#: Templates that are exempt from the colour and resource rules: emails need
#: absolute URLs and inline-friendly colour, the vendored macros are upstream's,
#: and `/_design` exists to show raw values.
VENDORED_OR_SHOWCASE = ("basecoat/", "emails/", "pages/design.html")

ALLOW = re.compile(r"kiro:\s*allow\s+([KJ]\d+)(?:\s*[—:-]+\s*(\S.*?))?\s*(?:#\}|-->|\*/)?\s*$")


# --- Results ---------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    detail: str = ""

    def render(self) -> str:
        rule = RULES[self.rule]
        what = f"{rule.title}: {self.detail}" if self.detail else rule.title
        return f"{self.path}:{self.line}  {self.rule}  {what}\n    → {rule.fix} ({rule.reference})"


@dataclass(frozen=True)
class Waiver:
    rule: str
    path: str
    line: int
    reason: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    waivers: list[Waiver] = field(default_factory=list)
    files: int = 0

    @property
    def ok(self) -> bool:
        return not self.findings


class Source:
    """One file, with the bookkeeping that turns a match into a finding."""

    def __init__(self, root: Path, path: Path, report: Report) -> None:
        self.path = path
        self.rel = path.relative_to(root).as_posix()
        self.text = path.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.report = report
        report.files += 1

    def flag(
        self, rule: str, line: int, detail: str = "", *, span: tuple[int, int] | None = None
    ) -> None:
        """Record a violation unless a reasoned exception covers it.

        `span` is the range of lines (inclusive, 1-based) where an exception
        comment counts; by default the offending line and the one above it.
        """
        first, last = span if span else (max(line - 1, 1), line)
        for number in range(first, min(last, len(self.lines)) + 1):
            match = ALLOW.search(self.lines[number - 1])
            if match is None or match.group(1) != rule:
                continue
            reason = (match.group(2) or "").strip()
            if reason:
                self.report.waivers.append(Waiver(rule, self.rel, number, reason))
                return
            note = f"la excepción 'kiro: allow {rule}' necesita un motivo tras el guion"
            detail = f"{detail} ({note})".strip()
            break
        self.report.findings.append(Finding(rule, self.rel, line, detail))


# --- Python rules -----------------------------------------------------------------


def _dotted(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else ""
    return ""


def _own_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[ast.AST]:
    """Every node of a function's own body, not descending into nested definitions.

    A nested `def`, `lambda` or `class` is yielded (it is part of the body) but its
    insides are not: an `await` in an inner function does not make the outer one
    asynchronous in any useful sense.
    """
    stack: list[ast.AST] = list(function.body)
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def _is_route(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and dec.func.attr in HTTP_METHODS
        for dec in function.decorator_list
    )


def _handler_span(function: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
    """Where an exception for a whole handler may sit: above its decorators, up to `def`."""
    top = min([function.lineno, *(dec.lineno for dec in function.decorator_list)])
    return max(top - 1, 1), function.lineno


def _layer(rel: str) -> str:
    parts = rel.split("/")
    return parts[1] if len(parts) > 2 and parts[0] == "app" else ""


def _check_python(source: Source, tree: ast.Module) -> None:
    layer = _layer(source.rel)
    in_routers = layer == "routers"

    sqlalchemy_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            sqlalchemy_aliases.update(
                alias.asname or alias.name for alias in node.names if alias.name == "sqlalchemy"
            )

    for node in ast.walk(tree):
        # K1 — query builders imported into a router or a service.
        if layer in ("routers", "services") and isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "sqlalchemy" or module.startswith(
                ("sqlalchemy.sql", "sqlalchemy.dialects")
            ):
                names = sorted(a.name for a in node.names if a.name in QUERY_NAMES)
                if names:
                    source.flag("K1", node.lineno, f"importa {', '.join(names)} de {module}")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            receiver = _dotted(node.func.value)

            # K1 — `db.execute(...)`, `self.session.scalars(...)`, `sa.select(...)`.
            if layer in ("routers", "services"):
                on_session = attr in SESSION_QUERY_CALLS and receiver in SESSION_RECEIVERS
                on_module = attr in QUERY_NAMES and receiver in sqlalchemy_aliases
                if on_session or on_module:
                    source.flag("K1", node.lineno, f"{receiver}.{attr}(...)")

            # K2 — the transaction belongs to get_db.
            if attr in ("commit", "rollback") and source.rel != "app/db.py":
                source.flag("K2", node.lineno, f"{receiver or '...'}.{attr}()")

        # K3 — HTTP objects where the code should not know about HTTP.
        if layer in INNER_LAYERS and isinstance(node, ast.Import | ast.ImportFrom):
            if isinstance(node, ast.ImportFrom):
                modules = [node.module] if node.module else []
            else:
                modules = [alias.name for alias in node.names]
            for module in modules:
                if module.split(".")[0] in ("fastapi", "starlette"):
                    source.flag("K3", node.lineno, f"importa {module} en app/{layer}/")

        # K5 — one module reads the environment.
        if source.rel != "app/config.py":
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "os" and node.attr in ("getenv", "environ", "putenv"):
                    source.flag("K5", node.lineno, f"os.{node.attr}")
            elif isinstance(node, ast.ImportFrom) and node.module == "os":
                bad = sorted(a.name for a in node.names if a.name in ("getenv", "environ"))
                if bad:
                    source.flag("K5", node.lineno, f"importa {', '.join(bad)} de os")

    if in_routers:
        _check_routers(source, tree)


def _viewer_aliases(tree: ast.Module) -> set[str]:
    """Module-level aliases such as `AdminUser = Annotated[User, Depends(require_role(...))]`."""
    aliases: set[str] = set()
    for node in tree.body:
        value: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value, targets = node.value, list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, targets = node.value, [node.target]
        if value is None:
            continue
        text = ast.unparse(value)
        if any(token in text for token in VIEWER_TOKENS):
            aliases.update(t.id for t in targets if isinstance(t, ast.Name))
    return aliases


def _rendered_page(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the handler calls `render(request, "pages/...")`."""
    for node in _own_nodes(function):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "render"
        ):
            continue
        candidates: list[ast.expr] = list(node.args[1:2])
        candidates += [kw.value for kw in node.keywords if kw.arg == "template"]
        for candidate in candidates:
            if (
                isinstance(candidate, ast.Constant)
                and isinstance(candidate.value, str)
                and candidate.value.startswith("pages/")
            ):
                return True
    return False


def _check_routers(source: Source, tree: ast.Module) -> None:
    aliases = _viewer_aliases(tree)

    for function in _functions(tree):
        if not _is_route(function):
            continue
        span = _handler_span(function)

        # K6 — an async handler that never awaits only costs the thread pool.
        if isinstance(function, ast.AsyncFunctionDef):
            awaits = any(
                isinstance(n, ast.Await | ast.AsyncFor | ast.AsyncWith)
                for n in _own_nodes(function)
            )
            if not awaits:
                source.flag("K6", function.lineno, f"{function.name}()", span=span)

        # K7 — the handler of a page says who is looking at it.
        if _rendered_page(function):
            params = [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]
            declared = any(
                p.annotation is not None
                and (
                    any(token in ast.unparse(p.annotation) for token in VIEWER_TOKENS)
                    or any(alias in ast.unparse(p.annotation) for alias in aliases)
                )
                for p in params
            )
            if not declared:
                source.flag("K7", function.lineno, f"{function.name}()", span=span)

        # K4 — writes go through a service.
        repositories: set[str] = set()
        for node in _own_nodes(function):
            if isinstance(node, ast.Assign) and _is_repository_call(node.value):
                repositories.update(t.id for t in node.targets if isinstance(t, ast.Name))
        for node in _own_nodes(function):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr not in REPOSITORY_WRITES:
                continue
            receiver = node.func.value
            if _is_repository_call(receiver) or (
                isinstance(receiver, ast.Name) and receiver.id in repositories
            ):
                source.flag(
                    "K4",
                    node.lineno,
                    f"{_dotted(receiver) or 'Repository(...)'}.{node.func.attr}(...)",
                )


def _is_repository_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id.endswith("Repository")
    )


def _check_models(root: Path, report: Report) -> None:
    """K8 — every module in app/models/ is imported by app/models/__init__.py."""
    package = root / "app" / "models"
    init = package / "__init__.py"
    if not init.is_file():
        return
    source = Source(root, init, report)
    tree = ast.parse(source.text)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app.models."):
                imported.add(node.module.split(".")[2])
            elif node.level == 1 and node.module:
                imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            imported.update(
                a.name.split(".")[2] for a in node.names if a.name.startswith("app.models.")
            )

    for module in sorted(package.glob("*.py")):
        if module.stem in ("__init__", "base") or module.stem in imported:
            continue
        source.flag("K8", 1, f"app/models/{module.name} no está importado", span=(1, 1))


# --- Template rules ---------------------------------------------------------------


def _blank_comments(text: str) -> str:
    """Replace comments with spaces, keeping every newline so line numbers hold."""

    def blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return HTML_COMMENT.sub(blank, JINJA_COMMENT.sub(blank, text))


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _check_template(source: Source) -> None:
    rel = source.rel.removeprefix("app/templates/")
    code = _blank_comments(source.text)

    # J1 — fragments do not extend; pages extend a layout.
    for match in EXTENDS.finditer(code):
        line = _line_of(code, match.start())
        target = match.group(1)
        if rel.startswith("partials/"):
            source.flag("J1", line, f"{rel} extiende {target}")
        elif rel.startswith("pages/") and target == "base.html":
            source.flag("J1", line, f"{rel} extiende base.html")

    if rel.startswith(("emails/", "basecoat/")):
        return

    # J2 — a POST form carries the CSRF field.
    for match in FORM_OPEN.finditer(code):
        if not POST_METHOD.search(match.group(0)):
            continue
        end = code.find("</form", match.end())
        body = code[match.end() : end if end != -1 else len(code)]
        if "csrf_field.html" not in body:
            source.flag("J2", _line_of(code, match.start()), f"{rel}")

    if rel.startswith(VENDORED_OR_SHOWCASE):
        return

    # J3 — colour comes from tokens.
    for match in HARDCODED_COLOUR.finditer(code):
        source.flag("J3", _line_of(code, match.start()), match.group(0).strip())

    # J4 — classes from Basecoat 0.x.
    for match in CLASS_ATTRIBUTE.finditer(code):
        classes = match.group(1) or match.group(2) or ""
        for obsolete in OBSOLETE_BASECOAT.finditer(classes):
            source.flag("J4", _line_of(code, match.start()), obsolete.group(0))

    # J5 — nothing runs or loads from outside 'self'. The base template carries
    # the consent-gated GTM snippet and the layouts load motion: they are the
    # two places where a script is allowed on purpose.
    if rel == "base.html":
        return
    if not rel.startswith("layouts/"):
        for match in INLINE_SCRIPT.finditer(code):
            if DATA_SCRIPT_TYPE.search(match.group(1)):
                continue
            source.flag("J5", _line_of(code, match.start()), "<script> en línea")
    for match in EXTERNAL_RESOURCE.finditer(code):
        source.flag("J5", _line_of(code, match.start()), "recurso externo")


# --- Driver ----------------------------------------------------------------------


def _python_files(root: Path) -> list[Path]:
    return sorted(p for p in (root / "app").rglob("*.py") if "__pycache__" not in p.parts)


def _template_files(root: Path) -> list[Path]:
    base = root / "app" / "templates"
    return sorted(p for p in base.rglob("*") if p.suffix in (".html", ".jinja") and p.is_file())


def check_project(root: Path = ROOT) -> Report:
    """Run every rule over the project at `root`."""
    report = Report()

    for path in _python_files(root):
        source = Source(root, path, report)
        try:
            tree = ast.parse(source.text, filename=source.rel)
        except SyntaxError as exc:
            report.findings.append(
                Finding("K1", source.rel, exc.lineno or 1, f"no se pudo leer: {exc.msg}")
            )
            continue
        _check_python(source, tree)

    _check_models(root, report)

    for path in _template_files(root):
        rel = path.relative_to(root).as_posix().removeprefix("app/templates/")
        if rel.startswith("basecoat/"):
            continue
        _check_template(Source(root, path, report))

    report.findings.sort(key=lambda f: (f.path, f.line, f.rule))
    return report


def rule_table() -> str:
    width = max(len(rule.title) for rule in RULES.values())
    rows = [f"  {rule.id:<3} {rule.title:<{width}}  {rule.reference}" for rule in RULES.values()]
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Comprueba las reglas de arquitectura de AGENTS.md."
    )
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="raíz del proyecto (por defecto, este)"
    )
    parser.add_argument("--rules", action="store_true", help="muestra la tabla de reglas y termina")
    args = parser.parse_args(argv)

    if args.rules:
        print(rule_table())
        return 0

    report = check_project(args.root)

    for waiver in report.waivers:
        print(f"  excepción  {waiver.rule}  {waiver.path}:{waiver.line}  {waiver.reason}")
    if report.waivers:
        print()

    if report.ok:
        print(f"archcheck: {report.files} archivos, {len(RULES)} reglas, sin violaciones")
        return 0

    for finding in report.findings:
        print(finding.render(), file=sys.stderr)
    print(
        f"\narchcheck: {len(report.findings)} violaciones en {report.files} archivos "
        "(`make archcheck rules=1` lista las reglas)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
