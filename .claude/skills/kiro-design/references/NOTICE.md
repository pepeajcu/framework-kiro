# Origin of these files

`minimalist.md`, `soft.md` and `brutalist.md` are verbatim copies of
`skills/minimalist-skill`, `skills/soft-skill` and `skills/brutalist-skill` from
[Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), MIT licensed
(see `LICENSE-taste-skill`).

They are written for React/Next/Framer projects in places. Where they say
"React", "Framer Motion" or name a CDN font, `SKILL.md` one level up wins: this
project is Jinja + HTMX + Tailwind, with nothing loaded from a CDN.

To refresh them from upstream:

    gh api repos/Leonxlnx/taste-skill/contents/skills/minimalist-skill/SKILL.md --jq .content | base64 -d > references/minimalist.md
