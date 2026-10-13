# Origin of these files

## Vendored from taste-skill (MIT)

`minimalist.md`, `soft.md`, `brutalist.md`, `redesign.md` and `brandkit.md` are
verbatim copies of `skills/minimalist-skill`, `skills/soft-skill`,
`skills/brutalist-skill`, `skills/redesign-skill` and `skills/brandkit` from
[Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), MIT licensed
(see `LICENSE-taste-skill`).

They are written for React/Next/Framer projects in places. Where they say
"React", "Framer Motion" or name a CDN font, `SKILL.md` one level up wins: this
project is Jinja + HTMX + Tailwind, with nothing loaded from a CDN. Two things
in them do not work here and are worth knowing before following them:

- **`Cabinet Grotesk`, `Satoshi`, `General Sans`** are Fontshare fonts. They are
  not on Fontsource, so `make font` cannot install them. See `type-pairings.md`
  for families that are.
- **`https://picsum.photos/...` placeholders** are blocked by the CSP
  (`img-src 'self' data:`, ADR-0010). Use a local SVG or photo under
  `app/static/img/`.

`redesign.md` is the audit `/kiro-redesign` runs. `brandkit.md` describes how to
brief a brand-identity image; Kiro does not generate images, so use it as the
checklist for what a logo and a visual system should be, and for judging the
logo a person brings.

To refresh them from upstream:

    for s in minimalist brutalist soft redesign; do
      gh api repos/Leonxlnx/taste-skill/contents/skills/$s-skill/SKILL.md --jq .content | base64 -d > references/$s.md
    done
    gh api repos/Leonxlnx/taste-skill/contents/skills/brandkit/SKILL.md --jq .content | base64 -d > references/brandkit.md

(`redesign-skill` is saved as `redesign.md`, `minimalist-skill` as `minimalist.md`,
and so on: the `-skill` suffix is dropped.)

## Written for Kiro

`archetypes.md`, `type-pairings.md`, `expresivo.md`, `institucional.md`,
`panel-de-datos.md`, `editorial.md`, `neo-brutalista.md`, `retro-y2k.md`,
`organico.md` and `oscuro-tecnologico.md` are original to this project. They
follow the *method* of taste-skill (named styles with dials, anti-slop rules)
but are adapted to Jinja, HTMX, Basecoat and `design.toml`.
