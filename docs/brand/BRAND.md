# Mahsool AI — Brand & UI Spec

This is the visual system for the Mahsool AI web app. It is the same look as the LinkedIn carousel in `reference/` (open those 6 PNGs first). The app must look like it belongs to the same family: parchment ground, Multani blue-tile colours, an ajrak-style diamond border, Nastaliq Urdu, and a calm, readable content area.

Source: a folk-art design system ("Geometric Ornamental" family, light density), adapted for a tax tool. Rule of thumb: **ornament lives in the frame, headers and dividers; the reading and answer areas stay calm and plain.**

---

## 1. Colour tokens

Define these as CSS variables on `:root` (light) and override them for dark mode (see §1.2). Components use tokens only, never raw hex.

### 1.1 Light (default)

| Token | Hex | Use |
| --- | --- | --- |
| `--bg` | `#F3EBDD` | Page ground (parchment) |
| `--surface` | `#FBF6EC` | Cards, input box, answer card |
| `--surface-2` | `#F4EAD6` | Card header strips, table header, hover fill |
| `--ink` | `#1C1B19` | Main text |
| `--ink-2` | `#3F3A33` | Secondary text |
| `--muted` | `#5E5448` | Captions, footers, labels |
| `--line` | `#D8C9AE` | Hairlines, table rules |
| `--indigo` | `#1F3A6B` | Primary structure: borders, lattice band, step markers, citation chips |
| `--green` | `#0B5E45` | Brand / primary action (Ask button), success, "after" bars |
| `--green-soft` | `#E3EEE7` | Success/answer highlight background |
| `--terracotta` | `#B5532F` | Warnings, refusals, "before" emphasis, corner tiles |
| `--ochre` | `#D9A441` | Small accents only (lattice dots, divider centre diamond, star centres) |
| `--turquoise` | `#2F7F83` | Medallion petals only |
| `--bar-muted` | `#BBA98C` | Chart "before" bars |
| `--bar-track` | `#E8DCC7` | Chart tracks, score-bar background |

### 1.2 Dark

The carousel is light. For dark mode keep the same roles with a deep indigo-charcoal ground:

| Token | Hex |
| --- | --- |
| `--bg` | `#11151B` |
| `--surface` | `#1A2029` |
| `--surface-2` | `#222A35` |
| `--ink` | `#EFE7D8` |
| `--ink-2` | `#D2C8B6` |
| `--muted` | `#A2977F` |
| `--line` | `#34404F` |
| `--indigo` | `#8FAEE0` (lines, chips) — lattice band background uses `#1F3A6B` in both themes |
| `--green` | `#46B98A` (button fill `#0B5E45` with text `#F3EBDD` still OK) |
| `--green-soft` | `#173127` |
| `--terracotta` | `#E08A63` |
| `--ochre` | `#E3B45C` |
| `--bar-muted` | `#6E6553` |
| `--bar-track` | `#2A323D` |

Theme: follow `prefers-color-scheme`, default light. Body must set `background: var(--bg)`. Text contrast ≥ 4.5:1 in both themes.

---

## 2. Typography

Load from Google Fonts: **Young Serif** (display), **Hanken Grotesk** 400/500/600/700 (UI and body), **Gulzar** (Urdu Nastaliq). Give each a fallback stack.

| Role | Font | Size / weight |
| --- | --- | --- |
| Page title ("Ask about Pakistani income tax") | Young Serif | 40–48px, 400 |
| Section titles, card titles, law section titles | Young Serif | 22–28px |
| Eyebrow labels ("SALARIED", "SOURCES") | Hanken Grotesk | 13–14px, 600, uppercase, letter-spacing 0.14em, `--green` |
| Body, answers, UI | Hanken Grotesk | 17–18px, line-height 1.6 |
| Captions, meta ("Tax year 2027 · 7.4 s") | Hanken Grotesk | 14px, `--muted` |
| Law text inside citation cards | Hanken Grotesk 16px (long text) — Young Serif only for short quotes | |
| Urdu script (questions, answers, placeholder words) | Gulzar | 1.15× the Latin size, line-height 2.0–2.2, `dir="rtl"`, `lang="ur"` |

Any element that can contain Urdu script must use `dir="auto"` and include Gulzar in its font stack so Urdu never falls back to a random font (this is why the placeholder currently shows a blank).

---

## 3. Ornament (use the SVGs in `assets/`)

- **Lattice band** (`assets/lattice-tile.svg`, 30×30 repeat): indigo tile, cream diamond outline, ochre centre dot. Use as a 14–18px high band **under the header** and **above the footer**, and as the frame of the landing hero on wide screens. Never behind text.
- **Star tile** (`assets/star-tile.svg`): terracotta square with a cream 8-point star. Use at the ends of the lattice band (corners), and as the small bullet for "done" items. Max 30px.
- **Divider** (`assets/divider.svg`): hairline + three small diamonds (indigo, ochre, indigo). Use under page/section titles and between the answer and the sources.
- **Medallion** (`assets/medallion.svg`): the 8-petal kashi flower. It is the **logo mark** (use `assets/logo-mark.svg` at 36–44px in the header) and a 160–200px hero image on the empty state.
- **Diamond step markers**: rotated squares (indigo fill, ochre numeral in Young Serif), as on slide 3. Use them for the answer progress stages (1 Understanding → 2 Rewriting → 3 Searching the law → 4 Re-ranking → 5 Writing the answer) and for numbered citations.

Ornament density: light. One lattice band top, one bottom, dividers under titles. No ornament inside answer text, tables or inputs.

---

## 4. Layout and components

**Header**: parchment, logo mark + "Mahsool AI" (Young Serif 22px) + "محصول" (Gulzar, `--green`), nav links right ("Ask", "Evaluation"), active link underlined with a 2px `--green` bar. Lattice band directly under the header.

**Content width**: 880–960px centred, 24px side gutter, stacks to one column under 720px.

**Empty state (landing)**: medallion (160px), page title in Young Serif, one-line intro, divider, then three starter groups (Salaried, Freelancers, Businesses & Landlords) as cards:
- card: `--surface`, 1.5px `--indigo` border, radius 6px, 20px padding; eyebrow label in `--green`;
- each starter question is a button inside the card: full width, left-aligned, 16px, `--surface-2` on hover, Urdu ones RTL in Gulzar.

**Question box** (bottom, sticky): `--surface`, 2px `--indigo` border, radius 8px; textarea with placeholder `Ask in English, اردو, or Roman Urdu — e.g. "filer na hon to kya hoga?"` (Urdu word in Gulzar); tax-year select styled with `--line` border; **Ask** button: `--green` fill, `#F3EBDD` text, 600, radius 6px, min 44px tall.

**Progress while answering**: a row of the 5 diamond step markers; the current one filled `--green`, done ones `--indigo`, upcoming ones outline only. Label under it ("Searching the law…").

**Answer card**: `--surface`, 1.5px `--indigo` border, radius 8px. Eyebrow "ANSWER". Body 18px. Inline citations as small indigo pills `[1]` (Hanken 13px, `--indigo` text on `--surface-2`), clickable to scroll to the source. Meta line: "Tax year 2027 · 7.4 s". Disclaimer at the bottom in `--muted` with a small info icon (inline SVG, no emoji).

**Refusal / not found**: same card, eyebrow "NOT IN THE LAW I COVER" in `--terracotta`, calm wording, no red alarm styling.

**Citation cards (sources)**: header strip `--surface-2` with law name (Hanken 14px `--muted`) and section title (Young Serif 20px), "Open FBR PDF, p. N ↗" link in `--green`; body = law text 16px; rate tables as real tables (header row `--surface-2`, hairlines `--line`, tabular numbers).

**Sources table**: columns #, Section, Found by, Score; score shown as a small bar (`--bar-track` track, `--green` fill) plus the number.

**Feedback**: "Was this helpful?" + two icon buttons (inline stroke SVG thumbs), `aria-label`s, no emoji. Selected state fills `--green-soft`.

**Offline / resting banner**: `--surface-2` with an ochre star tile, text "Mahsool AI is resting right now. Please try again later." (and the same in Urdu/Roman Urdu if the question was in Urdu).

**Limit reached**: same banner style, "You've used today's free questions. Please come back tomorrow."

**Footer**: lattice band, then disclaimer line + "Built on FBR's published law texts" + GitHub link, `--muted`.

**Evaluation page**: title "How well does Mahsool find the law?", divider, then the results as horizontal bar pairs exactly like slide 4 (before = `--bar-muted`, after = `--green`, track `--bar-track`, values at bar end, tabular numbers), legend above, note "on 168 held-out test questions". Tables for the other metrics with the same table style.

---

## 5. Don'ts

- No gradients, glossy effects, glassmorphism, drop-shadow-heavy cards.
- No emoji anywhere in the UI (replace ⚠️ ⏳ 👍 👎 with inline SVG icons).
- Don't put lattice or tiles behind text, or inside answers, tables or inputs.
- Don't use Inter/Roboto/Arial as the main face.
- Don't use more than one accent per component; ochre and turquoise are small accents only.
- Don't let Urdu render without Gulzar or without RTL.

## 6. Accessibility

Contrast ≥ 4.5:1 (3:1 for 24px+). Visible focus ring: 2px `--green` outline with 2px offset. Buttons ≥ 44px tall. Respect `prefers-reduced-motion`. All icons have `aria-label` or are `aria-hidden` with visible text next to them.
