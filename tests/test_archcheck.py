"""`scripts/archcheck.py`: every rule fires on a violation and stays quiet otherwise.

A check that passes on the real project proves nothing by itself: it may simply
never fire. So each rule gets a bad snippet that must be reported, with its line
number, and a good one that must not.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from scripts.archcheck import ROOT, RULES, check_project, main

ROUTER = """\
from fastapi import APIRouter, Request
from app.deps import CurrentUser, OptionalUser
from app.templating import render

router = APIRouter()
"""


def build(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content))
    return tmp_path


def rules_found(tmp_path: Path, files: dict[str, str]) -> list[tuple[str, int]]:
    report = check_project(build(tmp_path, files))
    return [(f.rule, f.line) for f in report.findings]


def router(body: str) -> str:
    return ROUTER + textwrap.dedent(body)


# --- K1: SQL outside a repository ------------------------------------------------


def test_k1_a_router_that_imports_a_query_builder(tmp_path):
    files = {"app/routers/a.py": "from sqlalchemy import select\n"}

    assert rules_found(tmp_path, files) == [("K1", 1)]


def test_k1_a_service_that_runs_a_query(tmp_path):
    files = {
        "app/services/a.py": """\
            class Service:
                def run(self):
                    return self.session.execute("select 1")
            """
    }

    assert rules_found(tmp_path, files) == [("K1", 3)]


def test_k1_a_query_through_the_module_alias(tmp_path):
    files = {"app/services/a.py": "import sqlalchemy as sa\n\nquery = sa.select(1)\n"}

    assert rules_found(tmp_path, files) == [("K1", 3)]


def test_k1_types_and_repositories_are_fine(tmp_path):
    files = {
        "app/services/a.py": "from sqlalchemy.orm import Session\n",
        "app/repositories/a.py": "from sqlalchemy import select\n\nq = select(1)\n",
    }

    assert rules_found(tmp_path, files) == []


# --- K2: the transaction belongs to get_db ---------------------------------------


def test_k2_commit_outside_the_session_dependency(tmp_path):
    files = {"app/services/a.py": "def f(session):\n    session.commit()\n"}

    assert rules_found(tmp_path, files) == [("K2", 2)]


def test_k2_get_db_may_commit_and_rollback(tmp_path):
    files = {"app/db.py": "def f(session):\n    session.commit()\n    session.rollback()\n"}

    assert rules_found(tmp_path, files) == []


# --- K3: HTTP objects in an inner layer ------------------------------------------


@pytest.mark.parametrize("layer", ["services", "repositories", "emails", "design_engine"])
@pytest.mark.parametrize("statement", ["from fastapi import Request", "import starlette.requests"])
def test_k3_an_inner_layer_importing_http(tmp_path, layer, statement):
    files = {f"app/{layer}/a.py": f"{statement}\n"}

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K3"]


def test_k3_the_http_layer_may_import_it(tmp_path):
    files = {
        "app/routers/a.py": "from fastapi import Request\n",
        "app/middleware/a.py": "from starlette.requests import Request\n",
        "app/deps.py": "from fastapi import Depends\n",
    }

    assert rules_found(tmp_path, files) == []


# --- K4: a router writes through a service ---------------------------------------


def test_k4_a_router_writing_through_a_repository_chain(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.post("/x")
            def create(request: Request, db, user: OptionalUser):
                NoteRepository(db).create(title="t")
            """
        )
    }

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K4"]


def test_k4_a_router_writing_through_a_variable(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.delete("/x")
            def remove(db, user: OptionalUser):
                notes = NoteRepository(db)
                notes.delete(1)
            """
        )
    }

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K4"]


def test_k4_reads_and_services_are_fine(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.get("/x")
            def listing(db, user: OptionalUser):
                NoteRepository(db).list_for_user(1)
                NoteService(db).create(title="t")
            """
        ),
        "app/services/a.py": "def f(db):\n    NoteRepository(db).create(title='t')\n",
    }

    assert rules_found(tmp_path, files) == []


# --- K5: only config.py reads the environment ------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "import os\nx = os.getenv('A')\n",
        "import os\nx = os.environ['A']\n",
        "from os import environ\n",
    ],
)
def test_k5_the_environment_read_elsewhere(tmp_path, code):
    assert [r for r, _ in rules_found(tmp_path, {"app/a.py": code})] == ["K5"]


def test_k5_config_may_read_it(tmp_path):
    assert rules_found(tmp_path, {"app/config.py": "import os\nx = os.getenv('A')\n"}) == []


# --- K6: async def without await -------------------------------------------------


def test_k6_an_async_handler_that_never_awaits(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.get("/x")
            async def page(request: Request):
                return 1
            """
        )
    }

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K6"]


def test_k6_an_await_in_a_nested_function_does_not_count(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.get("/x")
            async def page(request: Request):
                async def inner():
                    await something()
                return inner
            """
        )
    }

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K6"]


def test_k6_an_async_handler_that_awaits_and_a_sync_one_are_fine(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.post("/x")
            async def form(request: Request):
                return await request.form()

            @router.get("/y")
            def plain(request: Request):
                return 1
            """
        )
    }

    assert rules_found(tmp_path, files) == []


# --- K7: a page handler declares who is looking ----------------------------------


def test_k7_a_page_handler_without_the_viewer(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.get("/x")
            def page(request: Request):
                return render(request, "pages/x.html")
            """
        )
    }

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K7"]


def test_k7_a_post_that_rerenders_the_form_is_a_page_handler_too(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.post("/x")
            def submit(request: Request):
                return render(request, "pages/x.html", status_code=400)
            """
        )
    }

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K7"]


def test_k7_any_way_of_declaring_the_viewer_counts(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            AdminUser = Annotated[User, Depends(require_role("admin"))]

            @router.get("/a")
            def optional(request: Request, user: OptionalUser):
                return render(request, "pages/a.html")

            @router.get("/b")
            def required(request: Request, user: CurrentUser):
                return render(request, "pages/b.html")

            @router.get("/c")
            def role(request: Request, user: AdminUser):
                return render(request, "pages/c.html")
            """
        )
    }

    assert rules_found(tmp_path, files) == []


def test_k7_fragments_and_redirects_need_no_viewer(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            @router.get("/x")
            def fragment(request: Request):
                return render(request, "partials/x.html")

            @router.get("/y")
            def redirect():
                return None
            """
        )
    }

    assert rules_found(tmp_path, files) == []


# --- K8: every model is imported -------------------------------------------------


def test_k8_a_model_that_is_not_imported(tmp_path):
    files = {
        "app/models/__init__.py": "from app.models.note import Note\n",
        "app/models/base.py": "",
        "app/models/note.py": "",
        "app/models/provider.py": "",
    }

    report = check_project(build(tmp_path, files))

    assert [(f.rule, "provider.py" in f.detail) for f in report.findings] == [("K8", True)]


def test_k8_relative_imports_and_the_base_module_are_fine(tmp_path):
    files = {
        "app/models/__init__.py": "from .note import Note\n",
        "app/models/base.py": "",
        "app/models/note.py": "",
    }

    assert rules_found(tmp_path, files) == []


# --- J1: fragments and layouts ---------------------------------------------------


def test_j1_a_partial_that_extends(tmp_path):
    files = {"app/templates/partials/x.html": '\n{% extends "layouts/app.html" %}\n'}

    assert rules_found(tmp_path, files) == [("J1", 2)]


def test_j1_a_page_on_base_html(tmp_path):
    files = {"app/templates/pages/x.html": '{% extends "base.html" %}\n'}

    assert rules_found(tmp_path, files) == [("J1", 1)]


def test_j1_pages_on_layouts_and_layouts_on_base_are_fine(tmp_path):
    files = {
        "app/templates/pages/x.html": '{% extends "layouts/app.html" %}\n',
        "app/templates/layouts/app.html": '{% extends "base.html" %}\n',
    }

    assert rules_found(tmp_path, files) == []


# --- J2: CSRF --------------------------------------------------------------------


def test_j2_a_post_form_without_the_token(tmp_path):
    files = {"app/templates/pages/x.html": '<p></p>\n<form method="post" action="/x">\n</form>\n'}

    assert rules_found(tmp_path, files) == [("J2", 2)]


def test_j2_a_token_in_a_comment_does_not_count(tmp_path):
    files = {
        "app/templates/pages/x.html": (
            '<form method="POST">{# {% include "components/csrf_field.html" %} #}</form>\n'
        )
    }

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["J2"]


def test_j2_a_form_with_the_token_or_a_get_form_is_fine(tmp_path):
    files = {
        "app/templates/pages/x.html": (
            '<form method="post">{% include "components/csrf_field.html" %}</form>\n'
            '<form method="get" action="/search"></form>\n'
            '<form hx-post="/x"></form>\n'
        )
    }

    assert rules_found(tmp_path, files) == []


# --- J3: colour comes from tokens ------------------------------------------------


@pytest.mark.parametrize(
    "markup",
    [
        '<div class="bg-[#ff0000]"></div>',
        '<p style="color: #fff">x</p>',
        '<p style="background:rgb(1, 2, 3)">x</p>',
        '<path fill="#123456"/>',
        '<div style="color: oklch(0.5 0.1 200)"></div>',
    ],
)
def test_j3_a_hard_coded_colour(tmp_path, markup):
    files = {"app/templates/pages/x.html": f"<main>\n{markup}\n</main>\n"}

    assert rules_found(tmp_path, files) == [("J3", 2)]


def test_j3_tokens_anchors_and_comments_are_fine(tmp_path):
    files = {
        "app/templates/pages/x.html": (
            '<a href="#face">salto</a>\n'
            '<div class="bg-primary text-muted-foreground"></div>\n'
            '<path fill="currentColor"/>\n'
            "{# bg-[#fff] está prohibido #}\n"
            '<!-- style="color: #fff" -->\n'
            '<p style="color: color-mix(in oklch, var(--primary) 50%, transparent)">x</p>\n'
        ),
        "app/templates/emails/x.html": '<td style="color: #333333">x</td>\n',
        "app/templates/pages/design.html": '<i class="bg-[#fff]"></i>\n',
    }

    assert rules_found(tmp_path, files) == []


# --- J4: Basecoat classes that no longer exist -----------------------------------


@pytest.mark.parametrize("cls", ["btn-primary", "btn-sm", "badge-secondary", "btn-outline"])
def test_j4_a_class_from_basecoat_zero(tmp_path, cls):
    files = {"app/templates/pages/x.html": f'<button class="btn {cls}">x</button>\n'}

    assert rules_found(tmp_path, files) == [("J4", 1)]


def test_j4_the_attribute_api_is_fine(tmp_path):
    files = {
        "app/templates/pages/x.html": (
            '<button class="btn" data-variant="primary" data-size="sm">x</button>\n'
            '<div class="btn-group">x</div>\n'
        )
    }

    assert rules_found(tmp_path, files) == []


# --- J5: nothing runs or loads from outside 'self' -------------------------------


@pytest.mark.parametrize(
    "markup",
    [
        "<script>alert(1)</script>",
        '<script src="https://cdn.example.com/x.js"></script>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X">',
        '<img src="//picsum.photos/200">',
    ],
)
def test_j5_inline_scripts_and_external_resources(tmp_path, markup):
    files = {"app/templates/pages/x.html": f"<main>\n{markup}\n</main>\n"}

    assert rules_found(tmp_path, files) == [("J5", 2)]


def test_j5_local_scripts_data_blocks_links_and_the_allowed_places_are_fine(tmp_path):
    files = {
        "app/templates/pages/x.html": (
            "<script src=\"{{ asset('js/x.js') }}\" defer></script>\n"
            '<script type="application/ld+json">{"a": 1}</script>\n'
            '<a href="https://example.com">fuera</a>\n'
        ),
        "app/templates/base.html": "<script>(function(){})()</script>\n",
        "app/templates/layouts/landing.html": "<script>window.x = 1</script>\n",
        "app/templates/emails/x.html": '<img src="https://example.com/logo.png">\n',
    }

    assert rules_found(tmp_path, files) == []


# --- Exceptions need a reason ----------------------------------------------------


def test_an_exception_with_a_reason_silences_the_rule_and_is_listed(tmp_path):
    files = {
        "app/routers/a.py": router(
            """
            # kiro: allow K6 — awaits the provider in the next commit
            @router.get("/x")
            async def page(request: Request):
                return 1
            """
        )
    }

    report = check_project(build(tmp_path, files))

    assert report.findings == []
    assert [(w.rule, w.reason) for w in report.waivers] == [
        ("K6", "awaits the provider in the next commit")
    ]


def test_an_exception_without_a_reason_does_not_count(tmp_path):
    files = {"app/templates/pages/x.html": "{# kiro: allow J5 #}\n<script>x</script>\n"}

    report = check_project(build(tmp_path, files))

    assert [f.rule for f in report.findings] == ["J5"]
    assert "necesita un motivo" in report.findings[0].detail
    assert report.waivers == []


def test_a_jinja_exception_with_a_reason(tmp_path):
    files = {
        "app/templates/pages/x.html": (
            "{# kiro: allow J5 — el widget de pago no tiene build propio #}\n<script>x</script>\n"
        )
    }

    report = check_project(build(tmp_path, files))

    assert report.findings == []
    assert report.waivers[0].reason == "el widget de pago no tiene build propio"


def test_an_exception_for_another_rule_does_not_apply(tmp_path):
    files = {"app/a.py": "import os\n# kiro: allow K6 — otra cosa\nx = os.getenv('A')\n"}

    assert [rule for rule, _ in rules_found(tmp_path, files)] == ["K5"]


# --- Output ----------------------------------------------------------------------


def test_the_message_says_where_what_and_how_to_fix_it(tmp_path, capsys):
    build(tmp_path, {"app/routers/a.py": "\nfrom sqlalchemy import select\n"})

    code = main(["--root", str(tmp_path)])

    err = capsys.readouterr().err
    assert code == 1
    assert "app/routers/a.py:2  K1" in err
    assert "app/repositories/" in err
    assert "AGENTS.md regla 1" in err


def test_a_clean_project_exits_zero(tmp_path, capsys):
    build(tmp_path, {"app/a.py": "x = 1\n"})

    assert main(["--root", str(tmp_path)]) == 0
    assert "sin violaciones" in capsys.readouterr().out


def test_every_rule_has_a_fix_and_a_reference():
    for rule in RULES.values():
        assert rule.fix and rule.reference and rule.title, rule.id


def test_the_rule_table_is_printed(capsys):
    assert main(["--rules"]) == 0
    printed = capsys.readouterr().out

    assert all(rule_id in printed for rule_id in RULES)


# --- The project itself ----------------------------------------------------------


def test_the_project_follows_its_own_rules():
    report = check_project(ROOT)

    assert report.ok, "\n".join(f.render() for f in report.findings)


def test_agents_md_documents_every_rule():
    """The rules are only worth having if the agents that read AGENTS.md know them."""
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    missing = [rule_id for rule_id in RULES if rule_id not in agents]
    assert not missing, f"AGENTS.md no menciona: {missing}"
    assert "make archcheck" in agents
