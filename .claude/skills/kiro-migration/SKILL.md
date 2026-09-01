---
name: kiro-migration
description: Creating, reviewing and troubleshooting Alembic migrations in a Kiro project. Use whenever a model changes, a migration fails, or `make migrations-check` reports drift.
---

# Migrations in Kiro

## The normal flow

```bash
make revision m="add is_featured to providers"   # generate from the models
# READ the generated file in migrations/versions/
make migrate                                     # apply
make migrations-check                            # confirm no drift remains
```

## Always read the generated file

Autogenerate produces a draft, not an answer. It reliably gets these wrong:

- **Renames.** A renamed column comes out as `drop_column` + `add_column`, which
  destroys the data. Replace it with `op.alter_column(..., new_column_name=...)`.
- **Data migrations.** It never generates them. If a new NOT NULL column needs
  values for existing rows, add the backfill yourself: add the column nullable,
  `op.execute()` the backfill, then alter it to NOT NULL.
- **`downgrade()`.** Check it actually reverses `upgrade()`. This is what turns a
  bad deploy into a two-minute rollback instead of a restore from backup.

## Common failures

**"Target database is not up to date"** — there are unapplied migrations. Run
`make migrate` before generating a new one.

**Autogenerate produced an empty migration** — the model is not imported in
`app/models/__init__.py`. Alembic only sees what is registered on
`Base.metadata`, and that only happens on import.

**Autogenerate wants to drop a table you still use** — same cause. Do not
commit it. Fix the import and regenerate.

**Constraint names look random in the diff** — they should not. `NAMING_CONVENTION`
in `app/models/base.py` makes every constraint name deterministic. If you see
random names, the model is not inheriting from `Base`.

**Migrations conflict after a merge** — two branches both branched from the same
revision. Fix the `down_revision` of the later one to point at the earlier one;
do not use `alembic merge` unless the branches are genuinely independent.

## Rules

- One logical change per migration. Easier to review, easier to roll back.
- Never edit a migration that has already run in production. Write a new one.
- Never delete a migration file that has run anywhere. The chain breaks.
- Adding an index to a large table? Use `postgresql_concurrently=True` and
  `op.get_context().autocommit_block()` — a plain `CREATE INDEX` locks writes.
