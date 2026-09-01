---
name: kiro-adr
description: Recording an architecture decision as an ADR in docs/decisions/. Use when the user makes a technical decision worth remembering, or when a Kiro default is deliberately overridden.
---

# Writing an ADR

ADRs live in `docs/decisions/`, numbered sequentially. They exist so nobody —
human or agent — re-litigates a settled decision every few sessions.

## When to write one

- A stack default was deliberately overridden (a Kiro rule broken on purpose).
- A choice was made between real alternatives and the reasoning matters later.
- Something was tried and rejected. **Recording rejections is the highest-value
  case:** without it, the same bad idea gets proposed again.

Do not write one for routine implementation choices. If nobody would ever ask
"why is it like this?", it is not an ADR.

## Format

```markdown
# NNNN — Short imperative title

**Estado:** Aceptada | Provisional | Reemplazada por ADR-XXXX · YYYY-MM-DD

## Contexto

What made this a decision. The forces in tension, the alternatives that were
real. Facts, not narrative.

## Decisión

What was decided, stated plainly. One paragraph.

## Consecuencias

What this makes easy, what it makes hard, and what to watch out for. Include
the costs honestly — an ADR that only lists benefits is marketing, and the next
reader will not trust it.
```

## Steps

1. `ls docs/decisions/` to get the next number.
2. Write the file as `NNNN-titulo-en-kebab-case.md`.
3. Add a row to the table in `docs/decisions/README.md`.
4. If it reverses an earlier ADR, mark that one **Reemplazada por ADR-NNNN** —
   never delete it. The history is the point.
