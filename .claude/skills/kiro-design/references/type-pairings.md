# Type pairings

Twenty-six pairs of families that exist on [Fontsource](https://fontsource.org),
so `make font` can install them as local woff2 files (the CSP is
`font-src 'self'`; nothing loads from a CDN). Every family and weight below was
checked against Fontsource's API and its Latin file downloaded and validated.

**Not installable here:** Satoshi, Cabinet Grotesk and General Sans (Fontshare),
and any commercial face. If a brand names one, say so and offer the closest row.

## How to use this file

1. Pick the row by the style and by what the *display* face must do (carry a
   headline, a number, a wordmark). Display = `h1`-`h3`; body = everything else.
2. Install the three roles with `make font`, or write them in `design.toml`:

   ```bash
   make font name="Fraunces" weights="400,600" role=display
   make font name="Plus Jakarta Sans" weights="400,600" role=body
   make font name="JetBrains Mono" weights="400" role=mono
   ```

3. Two roles are the norm. The mono role is for code, figures and metadata, and
   only when the project has any. Three families on a page is the ceiling.
4. At most two weights per family unless the display face is a single heavy weight
   (then it is one). Each weight is a file the browser downloads.
5. Check the pair on `/_design` at 375 px and 1280 px: the type scale section
   shows both faces at every size, and the hero section shows them at the size
   that matters.

The columns are `Family weights`, comma-separated, in the form the contract
takes. `serif` after a name sets `fallback = "serif"`, so the system serif shows
while the font loads. A dash means "not used".

| # | Style | Display | Body | Mono | Reads as |
|---|---|---|---|---|---|
| 1 | suave-premium | Fraunces 400,600 serif | Plus Jakarta Sans 400,600 | - | Warm, soft, expensive; the default of `suave-premium` |
| 2 | minimalista | Newsreader 400,600 serif | Geist 400,600 | - | Document-like editorial; the default of `minimalista` |
| 3 | minimalista | Instrument Serif 400 serif | Instrument Sans 400,600 | - | Contemporary, light, a little fashionable |
| 4 | editorial | Playfair Display 700 serif | Public Sans 400,600 | - | Classic magazine masthead; use once and mean it |
| 5 | editorial | DM Serif Display 400 serif | DM Sans 400,600 | - | Friendly editorial, good at short headlines |
| 6 | institucional | Source Serif 4 600,700 serif | Public Sans 400,600 | - | Public sector, health; the default of `institucional` |
| 7 | organico | Young Serif 400 serif | Figtree 400,600 | - | Bookish and warm: food, craft, small farms |
| 8 | editorial | Gloock 400 serif | Hanken Grotesk 400,600 | - | High-contrast display, fashion and culture |
| 9 | editorial | Bodoni Moda 500,700 serif | Karla 400,600 | - | Luxury and fashion; needs large sizes and air |
| 10 | suave-premium | Cormorant Garamond 500,700 serif | Manrope 400,600 | - | Hospitality, spas, boutique |
| 11 | expresivo | Bricolage Grotesque 600,800 | Figtree 400,600 | - | Quirky grotesque with weight; the default of `expresivo` |
| 12 | oscuro-tecnologico | Space Grotesk 500,700 | Hanken Grotesk 400,600 | IBM Plex Mono 400 | Technical but friendly: tools, startups |
| 13 | suave-premium | Outfit 500,700 | DM Sans 400,600 | - | Geometric and calm; consumer apps |
| 14 | institucional | Sora 600,700 | Onest 400,500 | - | Finance and fintech without the usual blue-and-Inter |
| 15 | expresivo | Syne 600,800 | Manrope 400,600 | - | Art, culture, events; unusual wide letterforms |
| 16 | expresivo | Unbounded 500,700 | Albert Sans 400,600 | - | Playful and heavy: launches, games, youth |
| 17 | editorial | Schibsted Grotesk 500,800 | Geist 400,600 | - | News and media; dense and serious |
| 18 | brutalista | Archivo Black 400 | Archivo 400,600 | JetBrains Mono 400 | Swiss print, loud and flat; the default of `brutalista` |
| 19 | neo-brutalista | Big Shoulders Display 700,800 | Barlow 400,600 | - | Industrial, condensed, sports and posters |
| 20 | neo-brutalista | Barlow Condensed 600,700 | Barlow 400,600 | Space Mono 400 | Poster type with a tidy body |
| 21 | oscuro-tecnologico | JetBrains Mono 400,700 | Geist 400,600 | - | Developer tools; mono is the voice |
| 22 | panel-de-datos | IBM Plex Sans 600 | IBM Plex Sans 400,600 | IBM Plex Mono 400,500 | Back-office; the default of `panel-de-datos` |
| 23 | retro-y2k | Space Mono 700 | Space Grotesk 400,500 | - | Retro-tech, early web, a little ironic |
| 24 | oscuro-tecnologico | Martian Mono 400,700 | Hanken Grotesk 400,600 | - | Cold and precise; dark surfaces |
| 25 | retro-y2k | Pixelify Sans 400,700 | Rubik 400,500 | Silkscreen 400 | Pixel-era, playful; keep body copy short |
| 26 | ios | - | Inter 400,600 system | - | Only with the `ios` kit (San Francisco first, Inter local after) or `institucional` |

## Notes that save a redo

- **The display face sets `h1`-`h3` for the whole site.** If a heading inside a
  card or a table should stay in the body face, put `font-sans` on it.
- **Single-weight displays** (Archivo Black, Instrument Serif, DM Serif Display,
  Young Serif, Gloock) are already bold or already light: do not add
  `font-bold` on top, the browser would fake a heavier cut.
- **Variable fonts are not used.** Each weight is a static woff2; the weights
  above are the ones that exist.
- **Body size.** A body face with a small x-height (Cormorant, Bodoni) needs
  `text-lg` for running text; the table above assumes it is for headlines.
- **Spanish.** Every row was chosen for full Latin coverage: `á é í ó ú ñ ü ¿ ¡`
  render in all of them.
- **Replacing a pair** is `make font` again with the same `role`: it overwrites
  that role in `design.toml` and rebuilds. Remove the old files with
  `make design-check`'s orphan warning as the guide.
