# The design constitution

Kiro takes design input from several places: a preset, taste-skill, the uupm
advisor (nextlevelbuilder's *ui-ux-pro-max*), a pasted style brief (Refero or
free text), and a reference site extracted with skillui. They know different
things and they disagree. This file says **who decides what**, so a disagreement
is settled by a rule written here once and not by asking the user again.

The backbone is the uupm guide's own priority list: ten categories, from the
ones that must never be traded away to the ones that are taste.

## Who owns what

| # | Category | Priority | Owner | Enforced by | Can `DESIGN.md` relax it? |
|---|---|---|---|---|---|
| 1 | Accessibility | critical | uupm + WCAG | compiler (contrast AA, rule `D1`), UX-floor tests, review | **never** |
| 2 | Touch and interaction | critical | uupm (+ Apple HIG with the iOS kit) | compiled `kiro:a11y` block, review at 375 px | **never** |
| 3 | Performance | high | the platform (CSP, local fonts, motion levels) + uupm | `archcheck`, `design-check` (`D2`, `D3`) | **never** |
| 4 | Style selection | high | `DESIGN.md` (the user), filtered by taste; uupm proposes candidates | review | yes |
| 5 | Layout and responsive | high | function: uupm (mobile fallback, no horizontal scroll). Composition: taste (archetypes, variance) | pattern lint `P1`-`P6`, review | composition only |
| 6 | Typography and colour | medium | validity: the contract (AA, Fontsource). Choice: taste, with uupm's pairings as a reserve | compiler, review | the choice, yes |
| 7 | Animation | medium | Kiro's motion engine (levels, reduced motion); durations from uupm's `motion.csv` | `D4` | the level, yes |
| 8 | Forms and feedback | medium | uupm (states, inline errors) + Kiro's form helpers | UX-floor tests, review | no: the states are mandatory |
| 9 | Navigation | high | uupm (patterns) + Kiro's header archetypes | review | the shape, yes; the session logic, no |
| 10 | Charts and data | low | uupm's `charts.csv` | review | yes |

The table is in code as `app/design_engine/rules.py`; `design-check`, the
UX-floor tests and the review report use the same rule ids. A test fails if this
file names a rule that does not exist there.

## How a disagreement is settled

In this order:

1. **The higher category wins.** Categories 1, 2 and 3 and the laws of the stack
   (no Node, no CDN, server-rendered, one `design.toml`) are never relaxed.
2. **Within a category, its owner decides.** The other sources only advise.
3. **What the user wrote in `DESIGN.md` wins in the categories that can be
   relaxed.** It is recorded under *Decisiones de diseño* with its reason, so it
   is not asked twice. A rule allowed on purpose goes in `[rules] allow` of
   `design.toml`; the check reports it on every run instead of staying silent.
4. **If a proposal cannot be done on this platform, use the nearest thing that
   can**, and write down what changed and why. Nothing is dropped in silence.
5. **Only if it still cannot be settled, ask the human, once**, and apply rule 3.

## Conflicts settled in advance

| Conflict | Resolution |
|---|---|
| uupm gives a Google Fonts URL or `@import` | the Fontsource equivalent, precomputed; never a CDN |
| uupm or the iOS style ask for glass; taste-skill v2 bans it | Apple's HIG and Kiro agree: glass only on the navigation and controls layer (fixed bars, sheets, popovers, the tab bar), never on content that scrolls (`P6`). A solid surface when unsupported or when less transparency is asked for. v2's ban is not adopted |
| uupm's landing section order vs "no three equal cards" | uupm decides **which** sections and their order; taste decides **how** each is composed (bento, numbered, spec-sheet), never three equal cards (`P1`) |
| fintech and health need trust signals (uupm); taste bans the logo wall in the hero | the signals go below the hero, with real data (`logo-row`, `spec-sheet`); a wall of logos is `P2` |
| a uupm palette with purple or a gradient vs "no AI purple" | the hue stays if it is the brand's; saturation under 80 % and no glow |
| uupm suggests Inter or Roboto; taste says "not Inter by default" | Inter is allowed with the iOS kit (behind the system font), with the `institucional` style, or if `DESIGN.md` asks. Otherwise the nearest pairing in `type-pairings.md` |
| taste v2's bans (eyebrows, hairlines, `01/02`, monospace, floating pills, more than two families) vs Kiro's presets | Kiro follows taste-skill **v1**, pinned by commit (see `NOTICE.md`). v2's "tells" are advice that an explicit style overrides |
| taste v2 requires 4+ external photos and 8+ moving elements | not adopted: the CSP and the motion dial forbid it |
| skillui or Refero extract several accents | one stays, the most used on calls to action; the rest go to notes (`propose` does this) |
| a reference site uses a proprietary font | never copied; the Fontsource equivalent by category and metrics |
| Apple's system blue (`#007AFF`, `#0088FF`) fails AA with white text | `#0066CC` for the primary (white on it is 5.33:1, the colour of apple.com links); the system blue only as a non-text accent |
| uupm's `--persist` writes `design-system/<slug>/MASTER.md` into the current directory | always run with `-o .design/uupm`. In Kiro the master is `DESIGN.md` plus `design.toml`; per-page overrides go to UX notes in `DESIGN.md`, never to tokens (ADR-0014) |
| uupm ships a `kiro.json` target; `.kiro/` is the AWS Kiro IDE's folder | unrelated to this framework. Kiro's work folder is `.design/`, never `.kiro/` |

## One door in

`kiro-design` is the only design skill. uupm and taste-skill are vendored as
*references* under it, without a `SKILL.md` of their own that would compete.
`make design-check` warns if a competing design skill appears in
`.claude/skills/` (for example `ui-ux-pro-max`, `design-taste-frontend` or the
output of skillui).

## From a source to the project

Every source becomes a `DesignBrief`; `propose` turns it into a contract; a
person applies it.

```bash
make design-propose from=brief.json [base=advisor.json] [name=spa]   # writes .design/proposals/spa.{json,toml,md}
make design-apply proposal=spa [force=1]                              # design.toml, DESIGN.md, build, check
```

`propose` keeps one accent, makes it pass AA (moving it to the nearest colour
that does, recorded as rule `D1`), turns each font into its Fontsource family or
the catalogue font of its category, derives the Basecoat theme from the radius
and the density, and never drops something without writing it down. `apply`
refuses to replace an identity the project already has without `force=1`, saves
a backup in `.design/backup/`, and adds what was decided to *Decisiones de
diseño* and where it came from to *Procedencia* in `DESIGN.md`.
