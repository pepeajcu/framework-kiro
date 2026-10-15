"""Helpers shared by every schema."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from pydantic import BaseModel, ValidationError

#: Fields whose value is never sent back to the browser, even in a re-rendered form.
SECRET_MARKERS = ("password", "secret", "token")


def form_errors(exc: ValidationError) -> dict[str, str]:
    """Turn a `ValidationError` into `{field: message}` for a template.

    Only the first error per field survives, which is what a form should show:
    a list of five complaints about one password teaches nobody anything.
    """
    errors: dict[str, str] = {}
    for error in exc.errors():
        field_name = str(error["loc"][0]) if error["loc"] else "__all__"
        errors.setdefault(field_name, error["msg"])
    return errors


@dataclass(frozen=True)
class FormResult[ModelT: BaseModel]:
    """What a submitted form turned into: the validated data, or what to show instead.

    - `ok` / `data`: the model, when every field passed.
    - `values`: what the visitor typed, **without** passwords, secrets and tokens, so a
      rejected form can be shown again with their input intact.
    - `errors`: `{field: message}`; `__all__` is for a problem that belongs to no field.

    The templates' `field`, `textarea`, `select` and `checkbox` macros take it as `form=`
    and read value, error and `aria-*` from it; the handler only decides the status code.
    """

    data: ModelT | None = None
    values: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.data is not None

    def with_errors(self, extra: dict[str, str]) -> FormResult[ModelT]:
        """The same input with another complaint: wrong credentials, a taken address."""
        return replace(self, data=None, errors={**self.errors, **extra})


def validate_form[ModelT: BaseModel](model: type[ModelT], **raw: str) -> FormResult[ModelT]:
    """Validate raw form fields against `model`. Never raises.

        form = validate_form(NoteCreate, title=title, body=body)
        if not form.ok:
            return render(request, "pages/notes/index.html", {"form": form}, status_code=400)
        NoteService(db).create_for_user(user, title=form.data.title, body=form.data.body)

    A rejected form is answered with a 400 and the same form again (post/redirect/get
    on success); there is nothing to copy by hand into the template context.
    """
    values = {
        name: value
        for name, value in raw.items()
        if not any(marker in name.lower() for marker in SECRET_MARKERS)
    }
    try:
        return FormResult(data=model(**raw), values=values)
    except ValidationError as exc:
        return FormResult(values=values, errors=form_errors(exc))
