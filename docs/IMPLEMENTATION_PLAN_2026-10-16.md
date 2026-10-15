# Implementation Plan — Professional-Grade Website Generation

**Project:** `C:\Users\AYUSH\Documents\slm` (ReactAgent SLM workbench)
**Date:** 2026-10-16 · **Base commit:** `bd8a95d` ("Fix site planners; add audit and Qwen3 pipeline sources")
**Hardware:** RTX 4050 Laptop 6 GB · Python 3.13 · torch 2.14 + CUDA · transformers 5.5 · unsloth 2026.9.2 · Node 22 · Qwen3-4B base in `base-model/`

**Goal:** type a prompt into the workbench UI and get a website that looks like a professional
studio built it — real layout, typography and imagery, honest content, working navigation and
interactions, the UI/UX baseline in §8 and the motion system in §9 — on the local 4B model.

This plan supersedes nothing in `docs/AI_QUALITY_AUDIT_2026-10-16.md`; it verifies it, adds the
issues the audit missed, and turns everything into ordered, testable work for Claude Code.

---

## 0. How to execute this plan (instructions for Claude Code)

1. Work on a branch: `git checkout -b kit-generation`. Commit at the end of every phase with the
   phase number in the message. Never force-push.
2. Run the relevant tests after each task, and the full suite at the end of each phase:
   `set NO_AUTO_LOAD_MODEL=1 && python -m pytest tests --ignore=tests/e2e -q -p no:cacheprovider`
   (≈6 minutes). Baseline is **25 failed / 914 passed** (§2.3); a phase must not add failures.
3. Do phases in order. Phases 1–3 make the system work; 4–5 make it excellent; 6–7 make the
   gates honest; 8 is the end-to-end self-check in the workbench UI and is mandatory.
4. Python files are large (`server/app.py` 5.3k lines, `agent/agent.py` 3.2k). Read the exact
   line ranges cited before editing; line numbers refer to `bd8a95d`.
5. Do not delete datasets, models or `runs/`. Do not retrain anything (out of scope, §12).
6. Do not add npm/pip dependencies for generated sites. Everything here is native React/CSS/WebGL.

---

## 1. Definition of done

For each of the four self-check prompts in §11, submitted through the workbench chat box:

- The run finishes with all planned sections accepted (no blocked sections, no red debug boxes).
- Each site has a distinct art direction that fits its subject; fonts actually load.
- Imagery matches the subject or is a designed panel — never broken, never unrelated.
- Every requested section is present; nothing the prompt excluded appears.
- No instructions, style words or invented facts appear in the copy.
- All items in §8 (UI/UX) and §9 (motion) are verifiable in the browser.
- Project validation passes (typecheck, build, runtime, a11y, contract, motion), no console errors,
  no horizontal scroll at 375px and 1280px.

---

## 2. Current state (verified)

### 2.1 What users get today
- `scripts/run_web_ui.bat:11` defaults `MODEL_PATH` to `models/qwen3-siteagent-audit-v6-candidate`
  (39 training rows, ~20 optimizer steps, never passed a gate). Without it, `server/app.py:46-75`
  falls back to the untuned base model because `models/promoted_model.json` is `BLOCKED`.
- The agent asks the model to hand-write each section's TSX + CSS (≈1,600–2,200 tokens) from a
  ≈4k-token prompt mixing design plan, XML brief, style spec and contracts.
- Latest outputs (`runs/audit_v6_candidate/native/*/desktop.png`): system fonts on flat
  backgrounds, two items per section, no imagery, a nav link labelled "Hero", and prompt text
  printed as copy ("Warm ivory and dark terracotta.", "No invented address.").

### 2.2 Root cause
A 4B model can write good **copy** and make sensible **choices**, but cannot reliably author a
design system, responsive layouts and accessible interactions in one pass. Professional quality
must come from a curated design kit; the model writes content. This is the core change (§4).

### 2.3 Baseline test failures (25), from `pytest tests --ignore=tests/e2e` today
`test_auto_scaffold_repair` (3), `test_context_decision` (5), `test_diversity_evaluator` (1),
`test_doc_export_integrity` (2), `test_execute_qwen3_migration` (1), `test_full_website_benchmark` (3),
`test_interactive_curriculum` (1), `test_p1_quality_contracts` (1), `test_recovery_metrics` (1),
`test_retrain_qwen3_scratch` (1), `test_runtime_hardening` (1), `test_site_state_model` (2),
`test_training_methodology` (1), `test_training_preflight` (2). Handling: §10.4.

---

## 3. Issue register

### 3.1 From the audit, re-verified at `bd8a95d` (still present)

| ID | Issue | Location |
|---|---|---|
| A1 | Launcher defaults to the 39-row unpromoted candidate | `scripts/run_web_ui.bat:11` |
| A2 | Sampling fights Qwen3: temp 0.2–0.25, repetition_penalty 1.05, no top-p/top-k | `agent/agent.py:420-421, 2455` |
| A3 | Duplicate module identity: `agent.py` puts `agent/` on `sys.path` and imports bare `agent_protocol`; `agent/config.py` imports `agent.agent_protocol`. The tokenizer registered via `globals()["set_default_tokenizer"]` (agent.py:382-384, 396-398) lands in the bare module, so `ModelRuntimeConfig.count_tokens/format_chatml` use the legacy Qwen2.5 template | `agent/agent.py:56-60`; `agent/config.py:63-69` |
| A4 | ≈4k-token mixed prompt per section; minimal Arial/Georgia example the model copies | `agent/agent.py:2296-2310`; `agent/site_prompt.py` |
| A5 | Style and integrity directives leak into visible copy | brief `explicit_instructions` (`site_brief.py` ≈2150) |
| A6 | Sections generated blind to each other | `agent/agent.py:2345-2357` |
| A7 | Turn budget `max(len+4,10)` leaves ≈1 repair per section | `server/app.py:3424`; `agent/agent.py:2400` |
| A8 | Scaffold renders a red "⚠️ no valid React export" box inside the customer site | `server/app.py:1576-1581` |
| A9 | Style auto-adapt rewrites every 4–74px radius to the card radius (pill buttons → square) | `agent/agent.py:2697` |
| A10 | `synthesize_section_css` emits global selectors that restyle every section | `agent/agent.py:1560+` |
| A11 | Global `* {margin:0;padding:0}` and default `body {background:#000;color:#fff}` | `server/app.py:1665-1667` |
| A12 | Fonts from brief vs plan/preset (non-Google fonts like Roobert) → silent fallback | `server/app.py:1679-1683` |
| A13 | Photo catalog has 25 photos, none for most subjects | `agent/stock_photos.py:_PHOTO_ROWS` |
| A14 | Agent fabricates validation when `src/App.tsx` is absent (always — App.tsx is at the root) | `agent/agent.py:3039-3055` |
| A15 | Visual judge −3 for >85% near-white pixels (penalises airy layouts) | `agent/visual_judge.py:104-108` |
| A16 | Benchmark scores vacuous checks as 1.0 | `evaluation/site_benchmark_scorer.py:258, 284` |
| A17 | No gate for instruction leakage, placeholder images, broken images, dead anchors | `agent/site_acceptance.py` |
| A18 | Setup downloads Qwen2.5-Coder-3B; README describes the wrong model/adapter | `scripts/setup.sh:15-24`, `setup.bat`, `README.md` |
| A19 | Dead code (`rewrite_fallback_sections`, unused `brief_to_xml` import at agent.py:2172) | `agent/agent.py:1903, 2172` |

Audit items 3–5 (editorial preset hijack, identical design plan, negation-blind planner) were fixed
in `bd8a95d`.

### 3.2 New issues found in this analysis

| ID | Issue | Evidence / location |
|---|---|---|
| B1 | **Business name extraction is broken** for the most common prompt shape "Name — description". Results: "Aster & Kiln — handmade ceramics…" → `Kiln Warm Email`; "Northwind — a B2B analytics SaaS…" → `B2B Include Do`; "Saffron Table — modern Indian restaurant…" → `Table Indian We`; "A landing page for a yoga studio" → `My Business` | `site_brief.extract_business_name` (≈1039) — priority-3 fallback joins random capitalised words |
| B2 | Bare list sentences are not treated as sections: "Menu, about the chef, private dining." loses *private dining* | `extract_implicit_feature_sections` only scans `with/featuring/including …` |
| B3 | "Projects: Fern Studio rebrand, Halo app identity, Ostra packaging" is not parsed into items (only `section (a, b)` is) | `parse_section_spec` (≈1777) |
| B4 | Portfolio adds an unrequested `skills` section for any mention of designer/developer/engineer | `extract_sections_from_prompt`, portfolio branch |
| B5 | Domain defaults duplicate requested sections: gym prompt yields `programs` + `classes`, `pricing` + `membership` | same function; no synonym merge |
| B6 | `server/app.py:924` (`_worker`) calls `_store_task_failure`, defined at line 3309; the worker thread starts during import, so a task failing in that window raises `NameError` (observed in today's test run) | `server/app.py:825-1000, 3309` |
| B7 | Every generated `index.html` has meta description "<name> website built by ReactAgent SLM"; no OpenGraph, favicon, Apple touch icon, theme-color or 404 page | `server/app.py:1676-1703` |
| B8 | Heuristic brief **always** adds a motion plan (text_reveal on hero + scroll_reveal), so runtime motion checks always run; any generator must expose `data-motion` hooks or validation fails | `site_brief._build_heuristic_brief` ≈2091-2099; `project_validator._has_requested_motion` |
| B9 | Validator false positives that any generator will trip: (a) import scanner reads `'… from ' + x` inside strings as an import; (b) INERT BUTTON scanner `<button\b([^>]*)>` stops at the `>` of an arrow function, so a `ref={(el) => …}` before `onClick` reads as inert; (c) motion rules treat any `sticky`, `horizontal`, `:hover` text as motion features | `dependency_manager.external_imports`; `site_quality.collect_site_rendering_diagnostics`; `motion_patterns.validate_motion_rules` |
| B10 | Motion performance gate fails any loop >50 frames/s while idle (`window.__raf_counter`), so canvases must cap their frame rate and pause off-screen | `evaluation/motion_benchmark.py:1308-1320` |
| B11 | `web_ui_static/assets/` holds 140+ stale bundles from old builds (served directory bloat) | `web_ui_static/assets` |
| B12 | Stray root files from tooling: `.claude_baseline_tests.txt`, `runs/photo_vetting/` (created during this analysis; safe to delete) | project root |

---

## 4. Target architecture: Design Kit + content model

```
prompt ─► site_brief (fixed planner: name, sections, supplied items, facts, palette words)
            │
            ▼
       site_kit.KitSite ── one art direction (theme), one context (brand, email, location,
            │               store/checkout flags, section labels, image plan, tint rhythm)
            ▼
       per section (same order, same plan_update events as today):
         model ─► compact JSON content (≈150–700 tokens) using a ≈400-token prompt
                  → parse/repair JSON → normalise lengths & counts → integrity filters
                  → 1 retry if unusable → deterministic honest fallback
         kit   ─► src/components/<Section>.tsx + .css (token-driven, scoped, accessible)
            ▼
       scaffold: App.css = kit base stylesheet; index.html = kit fonts + head tags;
                 public/ = favicon.svg, apple-touch-icon.png, 404.html
            ▼
       existing verify → preview → workbench UI (unchanged contracts)
```

Why it works on a 4B model: output per section drops ≈5–10×, prompt drops ≈10×, code is correct
by construction (no tsc/parse failures, no blocked sections), design quality is owned by the kit,
and variety comes from 12 art directions × section variants × model-written content. Everything
downstream (files, events, sessions, edit flow, export) is unchanged.

**Proof of approach:** a prototype of this kit was built and exercised during the analysis (not
applied to the project). Twelve full sites from six prompts (with realistic model JSON and with
pure fallback content) compiled under `tsc --strict` and passed the project's own static lint,
contract, accessibility, motion-rules, rendering-contract and parser-preflight checks.

---

## 5. Phase 1 — Planner fixes (`agent/site_brief.py`)

**1.1 Business name (B1).** Add a priority-0 rule in `extract_business_name`, before the existing
rules: match a leading name followed by an em/en dash, colon, " - ", ", a/an/the …" or " is a/an":
```python
_NAME_LEAD_RE = re.compile(
    r"""^\s*(?:(?:build|create|make|design|generate)\s+(?:a\s+|an\s+|the\s+)?(?:website|site|landing page|homepage)\s+(?:for\s+)?)?"""
    r"""["“']?([A-Z0-9][\w&'’.+]*(?:\s+(?:&|and|of|the|de|la|[A-Z0-9][\w&'’.+]*)){0,4})["”']?\s*(?:[—–:]|\s-\s|,\s+(?:a|an|the)\b|\s+is\s+(?:a|an)\b)""")
```
Reject candidates whose first word is build/create/make/design/generate/website/portfolio/landing/
a/an/the/sections/include/modern/minimal, or longer than 40 chars. When the final result is
"My Business", derive a descriptive name from "for a/an/my/our <1–3 words>" ("A landing page for a
yoga studio" → "Yoga Studio").
*Accept:* the five examples in B1 give `Aster & Kiln`, `Northwind`, `Saffron Table`, `Maya Chen`,
`Crumb & Co` ("…bakery called Crumb & Co."), `Yoga Studio`.

**1.2 Bare list sections (B2).** In `extract_implicit_feature_sections`, also scan each sentence
(split on `.;\n`) that contains no colon and is a comma list (≥2 commas, or a comma plus "and")
whose parts are all ≤4 words; run it through the existing item filter. Map items starting with
"about" to `about`. Add `look, looks, technical, space, white, lots, colourful, colorful, playful,
luxurious, cozy, cosy` to `_NON_SECTION_ITEM_WORDS` so "Dark, technical look" stays style.
*Accept:* restaurant prompt (§11 #3) → `header, hero, menu, about, private-dining, contact, footer`;
"Minimal, lots of white space." and "Warm editorial photography, clay textures." add nothing.

**1.3 Colon item lists (B3).** In `parse_section_spec`, when no parenthesised list exists, read
`<Section>: a, b and c` (hyphens in slug matched as spaces) into `parsed_items` if 2–12 parts of
≤6 words each.
*Accept:* portfolio prompt (§11 #4) → `section_plans["projects"]["parsed_items"] == ["Fern Studio rebrand", "Halo app identity", "Ostra packaging"]` and no sections named after projects.

**1.4 Skills (B4).** Only add `skills` when the prompt says skills / tech stack / technologies / toolkit.

**1.5 Synonym merge (B5).** After assembling sections, collapse groups
`{programs, classes, courses, services}` and `{pricing, membership, plans, packages}`: keep members
whose words appear in the prompt; drop domain defaults that duplicate a requested member.
*Accept:* "Ironworks — a strength gym in Pune. Classes, coaches, membership pricing, FAQ, contact."
→ one class section, one pricing section, plus `coaches`, `faq`, `contact`.

**1.6 Tests:** extend `tests/test_planner_fidelity.py` with every *Accept* case above.

---

## 6. Phase 2 — The site kit (`agent/site_kit/`, new package)

Files: `__init__.py`, `themes.py`, `imagery.py`, `base_css.py`, `content.py`, `render.py`, `kit.py`.

### 6.1 `themes.py` — 12 art directions
Frozen `Theme` dataclass: `id, name, mode, colors{bg,surface,surface2,ink,muted,line,accent,
accent_ink,accent_soft[,accent2]}, display_font, body_font, font_query` (Google Fonts css2 query
listing only weights each family ships), `display_weight, display_tracking, display_line,
body_size, radius, button_radius, density` (section padding `clamp()`), `hero_styles, keywords,
heading_case, rule` (hairlines between sections).

| id | mode | display / body | bg · ink · accent | radius / button | heroes | subjects |
|---|---|---|---|---|---|---|
| atelier | light | Fraunces / Karla | #EEEAE3 · #28231E · #4D5B39 | 4px / 2px | split, fullbleed | ceramics, crafts, stationery, makers |
| clinic | light | Schibsted Grotesk / Source Sans 3 | **#FBFCFC** · #122030 · #0D6B70 | 14 / 10 | split | health, dental, law, finance, consulting |
| nocturne | dark | Cormorant Garamond / Jost | #14110E · #EFE7DA · #C9A46A | 0 / 0 | fullbleed | fine dining, wine, bar, hotel, jewellery |
| signal | dark | Space Grotesk / IBM Plex Sans | #0C1016 · #E7ECF2 · #7C95FF (+#41D3C0) | 14 / 10 | product | SaaS, AI, data, developer, logistics |
| verdant | light | DM Serif Display / Nunito Sans | #F2F4ED · #1D2A21 · #2E5B45 | 22 / pill | split, fullbleed | yoga, wellness, plants, florist, nonprofit |
| gallery | light | Instrument Serif / Inter Tight | #FAFAF7 · #121315 · #2343D1 | 0 / 0 | typographic, split | portfolio, design, architecture, photography |
| carnival | light | Bricolage Grotesque / Figtree | #FFF6E8 · #22183A · #D6383E (+#2563D9) | 24 / pill | split | kids, festivals, sweets, pets, playful |
| press | light | Newsreader / Libre Franklin | #F7F5F0 · #1A1917 · #7A2131 | 2 / 2 | typographic, split | publications, books, education, podcasts |
| forge | light | Anton (uppercase) / Archivo | #F1F0EC · #131313 · #E8551A | 0 / 0 | fullbleed, split | gym, sport, automotive, trades, barber |
| coastal | light | Marcellus / Mulish | #F5F8F8 · #0F2A33 · #1C6684 | 8 / 6 | fullbleed, split | travel, real estate, resorts |
| spice | dark | Libre Bodoni / Outfit | #1B1922 · #F4ECDF · #E3A33A | 6 / pill | fullbleed, split | restaurants (Indian, Thai, ramen, bistro…) |
| roast | light | Young Serif / Manrope | #F4F1EE · #2A1E18 · #2F4A3F | 12 / pill | split, fullbleed | coffee, bakery, brunch, patisserie |

Selection `select_theme(prompt, business_type, preferred)`: keyword hits ×3 (multi-word ×2,
negation-aware), +2.5 for the planner's business type mapping, ±2.5/−4 for explicit mode words
(dark/black/night/moody vs light/white/airy/minimal — hue phrases like "dark forest green" don't
count), tie-break by `sha256(prompt)`. No match → rotate among gallery/clinic/press/atelier/
coastal/signal honouring mode. `apply_requested_palette(theme, brief)`: user background colour
replaces bg/surfaces when its lightness matches the mode; user accent replaces accent if ≥3:1
against bg, with `accent_ink` chosen for best contrast; ink ≥7:1 and muted ≥4.6:1 are enforced by
mixing. Unit test: every theme's ink/bg ≥ 7, muted/bg ≥ 4.5, accent_ink/accent ≥ 4.5.

### 6.2 `imagery.py` — verified, subject-matched photography
Photos are `https://images.unsplash.com/photo-<id>?auto=format&fit=crop&w=<w>&q=80` (auto=format
serves WebP/AVIF). Every id below was downloaded and visually checked on 2026-10-16; use only these.

| topic | ids |
|---|---|
| coffee | 1495474472287-4d71bcdd2085, 1509042239860-f550ce710b93, 1447933601403-0c6688de566e, 1511920170033-f8396924c348, 1501339847302-ac426a4a7cbb |
| cafe_street | 1559925393-8be0ec4767c8 |
| restaurant | 1414235077428-338989a2e8c0, 1517248135467-4c7edcad34c4, 1555396273-367ea4eb4db5, 1504674900247-0877df9cc836, 1577219491135-ce391730fb2c |
| healthy_food | 1546069901-ba9599a7e63c, 1540189549336-e6e99c3679fe, 1512621776951-a57141f2eefd |
| indian_food | 1585937421612-70a008356fbe, 1631452180519-c014fe946bc7, 1596797038530-2c107229654b, 1601050690597-df0568f70950, 1565557623262-b51c2513a641, 1588166524941-3bf61a9c41db |
| bakery | 1509440159596-0249088772ff, 1517433670267-08bbd4be890f, 1555507036-ab1f4038808a, 1558961363-fa8fdf82db35, 1486427944299-d1955d23e34d |
| ceramics | 1565193566173-7a0ee3dbe261, 1610701596007-11502861dcfa, 1578749556568-bc2c40e68b61, 1493106641515-6b5631de4bb9 |
| yoga | 1544367567-0f2fcb009e0b, 1506126613408-eca07ce68773, 1545205597-3d9d02c29597, 1599901860904-17e6ed7083a0 |
| spa | 1540555700478-4be289fbecef |
| fitness | 1534438327276-14e5300c3a48, 1517836357463-d25dfeac3438, 1571019613454-1cb2f99b2d8b, 1583454110551-21f2fa2afe61 |
| fashion | 1445205170230-053b83016050, 1490481651871-ab68de25d43d, 1441986300917-64674bd600d8, 1483985988355-763728e1935b |
| florist | 1487070183336-b863922373d4, 1561181286-d3fee7d55364, 1490750967868-88aa4486c946, 1455659817273-f96807779a8a |
| interior | 1600210492486-724fe5c67fb0, 1586023492125-27b2c045efd7, 1618221195710-dd6b41faaea6, 1600607687939-ce8a6c25118c |
| architecture | 1600585154340-be6161a56a0c, 1487958449943-2429e8be8625, 1511818966892-d7d671e672a2, 1494526585095-c41746248156 |
| photography | 1452587925148-ce544e77e70d, 1516035069371-29a1b244cc32, 1502920917128-1aa500764cbd |
| design | 1561070791-2526d30994b5, 1558655146-9f40138edfeb, 1542744094-3a31f272c490 |
| tech | 1551288049-bebda4e38f71, 1460925895917-afdab827c52f, 1558494949-ef010cbdcc31, 1518770660439-4636190af475, 1550751827-4bd374c3f58b, 1531297484001-80022131f5a1 |
| office | 1497366216548-37526070297c, 1497366811353-6870744d04b2, 1521737711867-e3b97375f902, 1551434678-e076c223a692, 1522071820081-009f0129c71c |
| books | 1481627834876-b7833e8f5570, 1495446815901-a7297e633e8d |
| travel | 1507525428034-b723cf961d3e, 1501785888041-af3ef285b470, 1469474968028-56623f02e42e, 1506744038136-46273834b3fb |
| real_estate | 1564013799919-ab600027ffc6, 1570129477492-45c003edd2be, 1512917774080-9991f1c4c750 |
| wine | 1510812431401-41d2bd2722f3, 1506377247377-2a5b3b417ebb, 1474722883778-792e7990302f |
| music | 1511379938547-c1f69419868d, 1493225457124-a3eb161ffa5f, 1514525253161-7a46d19cd819 |
| education | 1503676260728-1c00da094a0b, 1524178232363-1fb2b075b655 |
| medical | 1576091160399-112ba8d25d1d, 1538108149393-fbbd81895907, 1588776814546-1ffcf47267a5 |
| dental | 1629909613654-28e377c37b09, 1606811971618-4486d14f3f99 |
| plants | 1485955900006-10f4d324d411, 1459411552884-841db9b3cc2a, 1416879595882-3373a0480b5b |
| jewelry | 1515562141207-7a88fb7ce338, 1599643478518-a784e5dc4c8f |
| stationery | 1455390582262-044cdead277a, 1517842645767-c639042777db, 1531346878377-a5be20888e57 |
| skincare | 1598440947619-2c35fc9aa908, 1570172619644-dfd03ed5d881 |
| pets | 1548199973-03cce0bbc87b, 1450778869180-41d0601e046e |
| event | 1540575467063-178a50c2df87, 1505373877841-8d25f7d46678, 1511578314322-379afb476865 |
| law | 1589829545856-d10d557cf95f, 1505664194779-8beaceb93744, 1450101499163-c8848c66ca85 |
| finance | 1554224155-6726b3ff858f, 1486406146926-c627a92ad1ab, 1611974789855-9c2a0a7236a3 |
| nature | 1441974231531-c6227db76b6e, 1470071459604-3b5ec3a7fe05 |
| craft | 1452860606245-08befc0ff44b |
| cars | 1492144534655-ae79c964c9d7, 1503376780353-7e6692767b70 |

Rejected during vetting (do not use): 1604176354204-9268737828e4 (jeans, not ceramics),
1572916122154-48a3e2e4e2ba and 1523050854058-8df90110c9f1 (dead), 1556228578-8c89e6adf883 and
1626785774573-4b799315345d (visible brands), 1513519245088-0e12902e5a38 (wrong subject).

Give each photo a descriptive alt (e.g. "Hands shaping clay on a pottery wheel"). Topic detection
is an ordered list of negation-aware regexes (ceramics before restaurant, indian_food before
restaurant, tech near the end, office/nature last). `ImagePlanner(prompt)`: topics = first two
matches; pool = primary topic rotated by prompt hash, then secondary; `take(n)` returns unused
photos first; disabled when the prompt says "no photos/images". When nothing matches, renderers
show the designed art panel (§6.3) — never an unrelated photo, never a placeholder host.

### 6.3 `base_css.py` — site stylesheet (written to `src/App.css`)
- `:root` tokens: `--k-bg … --k-accent-2`, `--k-font-display/body`, display weight/tracking/line,
  `--k-radius`, `--k-radius-btn`, `--k-density`, `--k-gutter: clamp(20px,5vw,64px)`, `--k-max: 1240px`,
  `--k-ease: cubic-bezier(0.22,1,0.36,1)`, `--k-ease-out: cubic-bezier(0.16,1,0.3,1)`,
  8px grid `--k-space-1…12` (0.5rem steps), `--k-tap: 44px`; plus compatibility aliases
  `--bg-color, --text-color, --font-body, --font-heading, --color-primary, --color-accent, --on-accent`
  and `color-scheme`.
- Sane reset (box-sizing; zero margins only on headings/p/lists/figure; `ul[class]` unstyled), body
  bg/ink/font, line-height 1.6, `:focus-visible` ring in accent, `scroll-padding-top: 88px`,
  `scroll-behavior: smooth` (auto !important under reduced motion).
- Primitives: `.k-container`, `.k-section` (+`--tint`, hairline between sections for `rule` themes),
  `.k-display` (clamp 2.6–5.6rem), `.k-h2`, `.k-h3`, `.k-lede` (38ch), `.k-text` (65ch),
  `.k-head` / `.k-head--split`, `.k-btn` (48px min height; `--primary`, `--ghost`; hover/focus
  lift 180ms; `:active { transform: scale(0.98) }`; `[disabled],[aria-busy=true]` state),
  `.k-actions`, `.k-link`, `.site-skip-link`, `.site-visually-hidden`/`.k-sr`.
- Media: `.k-media`/`.k-art` are layered radial gradients of accent/surfaces (variants 1–3 via
  `data-variant`) with an optional giant brand initial (`.k-art__mark`); `img` covers; `.is-missing`
  hides a failed image so the art panel shows.
- Motion primitives in §9.

Do not use `.btn`, `.section__inner/header/title` class names (the static lint treats them as shared).

### 6.4 `content.py` — section kinds, prompts, parsing, integrity
**Kinds** (first regex match on the slug wins): header, footer, hero, cart (cart|checkout|basket|bag),
menu, faq, pricing (pricing|plans|packages|rates|tiers|membership), quotes (testimonial|reviews|…),
team (team|people|instructors|staff|trainers|coaches|doctors|founders), contact (contact|booking|
reserv|enquir|visit|hours|location|find-us), cta (newsletter|cta|subscribe|signup|join|waitlist),
preview (preview|demo|product-tour|dashboard), products (products|shop|store|collection|catalog|
goods|pieces), work (gallery|work|projects|portfolio|case-stud|lookbook|showcase), articles
(blog|journal|notes|stories|news|posts|events|schedule), steps (process|how-it-works|steps|care|
guide|method|journey|timeline), story (about|story|chef|founder|studio|mission|philosophy|history|
approach|values|heritage), features (features|services|benefits|offerings|amenities|classes|
programs|why|treatments|expertise|stats), otherwise **split** (generic). Nav label = humanised slug
("glaze-stories" → "Glaze stories"); FAQ → "FAQ".

**System prompt** (≈150 tokens): "You write the words for one section of a website. A design system
already handles layout, colours, fonts and images, so you only write copy. Reply with a single JSON
object and nothing else. Write like a skilled brand copywriter for this specific business: concrete,
warm, plain verbs, sentence case, no hype, no clichés like elevate/unlock/seamless/world-class. Never
describe the design, colours, fonts, layout, sections or these instructions. Never mention that
something is a demo, placeholder or illustrative. Use only facts from the request. Do not invent
prices, phone numbers, addresses, opening hours, statistics, awards, client names, people's names
or reviews. Describe qualities and experiences instead."

**User message:** request, business name, business type, section label, "Use exactly these items
from the request, in this order: …" when supplied, item count, up to three already-written
headlines ("keep the same voice, don't repeat it"), and the JSON shape for the kind:
hero `{headline 5–9 words, lede 18–32 words, primary_cta, secondary_cta, tagline}`; features/steps
`{title, intro, items|steps:[{title,text}]}`; story `{title, paragraphs[2], highlights[3]}`; work
`{title, intro, items:[{title,caption}]}`; products `{title, intro, items:[{name,description}]}`;
menu `{title, intro, categories:[{name, items:[{name,description}]}]}`; faq `{title, intro,
items:[{q,a}]}`; articles `{title, intro, items:[{title,excerpt,tag}]}`; pricing `{title, intro,
tiers:[{name,description,features[3]}]}`; quotes `{title, intro, invite}`; team `{title, intro,
members:[{role,text}]}`; contact `{title, text, button}`; cta `{title, text, button}`; preview
`{title, intro, labels[3], points:[{title,text}]}`; split `{title, intro, paragraphs[1], bullets[3]}`.
Token caps: hero 260, contact 200, cta 160, cart 140, quotes 160, menu 700, faq 650, pricing 560,
story 520, split 480, others 480. Counts (min, max, ask): features 3–6 (3), work 3–6 (4), products
3–8 (4), steps 3–5 (4), faq 3–6 (4), articles 3–4 (3), pricing 2–4 (3), team 2–6 (3); supplied items
override counts.

**Parsing:** strip `<think>…</think>` and code fences; take from the first `{` with
`JSONDecoder.raw_decode`; on failure remove trailing commas and smart quotes; then close a
truncated object by trimming the dangling field and appending missing `]`/`}`.

**Integrity filters** (sentence level; built from the prompt):
- *Meta/leak:* drop sentences mentioning palette, hex code, font(s), typeface, typography, colour
  scheme, design system, css, this section, placeholder, lorem, illustrative, demo data, sample
  copy, this website/page, the user, as requested, (not) invented, fabricat-, user-supplied,
  supplied by, json, tbd, coming soon.
- *Style restatement:* split the prompt into clauses; for clauses containing style words (style,
  look, aesthetic, vibe, palette, colours, tones, fonts, typography, minimal, layout, photography,
  imagery, white space, editorial, textures, gradient…), drop generated sentences sharing ≥3 content
  words and ≥45% overlap; also drop any sentence naming palette/typography/fonts/aesthetic/colour
  scheme/layout/design language. ("Warm ivory and dark terracotta." is removed; "a terracotta glaze"
  in a product description survives.)
- *Invented facts:* drop sentences with emails not in the prompt, phone-like numbers, currency
  amounts or `N% / N+ / N customers / N years / N awards` whose digits aren't in the prompt,
  "CEO/founder/director of X", "award-winning / best in / #1 / voted / featured in / trusted by N",
  and opening hours when the prompt has none.
- Titles/labels pass the same filters and word caps; empty results fall back.

**Normalise:** enforce word caps and counts; for supplied items keep the user's names in order and
attach the best-matching model text (exact, then word overlap, then next unused); dedupe by name;
fill to the minimum from fallback; products take prices **only** from `brief["products"]`; menu
prices are never generated; pricing tiers have no price unless supplied ("Pricing on request").

**Fallback copy** per kind is deterministic and honest (brand, business type, location, supplied
items; e.g. contact: "Questions, ideas or plans: write to <email> and we'll reply personally.").
Never an instruction, never a fact.

### 6.5 `render.py` — renderers
Every renderer returns `(tsx, css)`. Rules that keep output valid and validator-clean:
- Content is embedded as `const DATA: any = <json.dumps(..., ensure_ascii=False) with "</" escaped>`
  and rendered through JSX expressions only; after assembly, rewrite `.map((x) =>` →
  `.map((x: any) =>` and `.map((x, i) =>` → `(x: any, i: number)` (strict mode rejects implicit any).
- Import only the React hooks actually used; `import './<Name>.css'`; named + default export.
- Root `<section id="<slug>" className="k-section [k-section--tint] k-<slug>" aria-labelledby="<slug>-title">`;
  all ids are literal strings; one `h1` (hero) site-wide.
- Every `<button>` has `onClick` (placed **first** in the attribute list, see B9b) or is a form submit.
- No `href="#"`; in-page links target real section ids only.
- Never write `'… from ' +` inside strings (B9a); use template literals.
- All CSS selectors scoped under `.k-<slug>`; every hover has a matching `:focus-visible`;
  transitions ≤ 250ms for micro-interactions; animate only transform/opacity; every motion has a
  `prefers-reduced-motion` override.
- Shared helpers injected per module as needed: `Media` (image with `width/height`,
  `loading`/`fetchPriority`/`decoding` by priority, `onError` → art panel), `useReveal` (§9),
  `useMagnet`, `tiltHandlers`, `ShaderBackdrop`.

| Kind | Layout & behaviour |
|---|---|
| header | Brand wordmark (not a heading) → `#site-main`; ≤6 nav links with scroll-spy `aria-current="location"` + accent underline; one CTA (to the contact section) on the right; sticky, hides on scroll-down after 120px and returns on scroll-up (not while menu/cart is open, not under reduced motion); mobile toggle (44px, `aria-expanded`, `aria-controls`) opening a full-screen drawer rendered **outside** `<header>` (backdrop-filter makes the header a containing block), fade/slide in, `inert` when closed, body scroll locked while open, Escape closes and returns focus; stores get a Cart button with `data-cart-count` and `aria-label="Cart, N items"` plus a panel listing lines and an honest checkout note; listens to `window` `kit-cart-add` events |
| hero | Styles: **split** (copy + tall photo/art, image priority, depth layer), **fullbleed** (photo background + dark gradient shade, white text, bottom-left), **typographic** (giant display headline, rule, lede + actions row, optional 21:9 photo strip), **product** (centred headline + illustrative app window with labelled tiles and bar chart, `figcaption` "Illustrative interface; not live data"). Headline `h1[data-motion="text-in"]`, lede `.k-rise-2`, actions `.k-rise-3`; primary CTA → first content section, secondary → contact; location as a fact line when known; magnetic primary CTA; WebGL shader backdrop on product hero and when the prompt asks for 3D/shader/WebGL/fluid/mesh gradient (§9) |
| features | Rule themes or 2/4 items: two-column rows separated by hairlines; else auto-fit grid with a 2px top rule per item and a small accent mark; reveal target |
| story | Image/art (4:5) beside title, paragraphs (first larger), highlight list with accent dashes; alternates side by section index |
| split (generic) | Story layout with intro + paragraphs + bullets |
| work | ≥4 items with photos → horizontal **reel** (native scroll-snap, focusable track, prev/next buttons scrolling 80% width, smooth unless reduced motion); otherwise asymmetric grid (lead item spans 4 of 6 columns × 2 rows); tilt + spotlight on signal/carnival/forge/spice |
| products | Cards: image (4:5), name, price (supplied only), description; stores: "Add to cart" (`aria-label="Add <name> to cart"`, dispatches `kit-cart-add`, shows "Added", polite live region); non-stores: "Ask about this piece" → `mailto:` with subject, or the contact section |
| cart | Listens to `kit-cart-add`; empty state; lines; total computed from supplied prices; honest note ("Online checkout isn't available yet. Email … with your list…") and "Email this order" mailto when an email exists |
| menu | Image + heading beside a board; categories as ARIA tabs (arrow/Home/End keys, roving tabindex, `aria-selected`, `tabpanel`); dish rows with dotted leader only when a price exists; tab change wrapped in `document.startViewTransition(() => flushSync(...))` when supported and motion allowed |
| steps | **Pinned scrollytelling**: sticky visual (photo/art + counter `01 / 04` + SVG progress line with `pathLength=1` and `stroke-dashoffset = 1 − progress`), steps list where an IntersectionObserver (rootMargin −45%) marks the current step (`aria-current="step"`, others dimmed); stacks normally under 860px |
| faq | Two-column; accordion of `h3 > button[aria-expanded][aria-controls]` + `region[aria-labelledby]`, first open, open animation |
| articles | Lead card spans two rows on accent-soft; tags; tilt on lively themes (wrapper carries reveal, card carries tilt) |
| pricing | Tier cards (middle featured when ≥3), price or "Pricing on request", features, CTA to contact ("Ask for a quote") |
| quotes | Only user-supplied quotes as `figure > blockquote + figcaption`; otherwise an honest invitation ("Worked with … ? We'd love to hear how it went.") with a feedback link |
| team | Supplied names (with model-written role text) or roles only — rendered with the features layout |
| contact | Intro + details (`dl`: email as mailto, location) beside a validated form (labelled name/email/message, inline errors with `aria-invalid`/`aria-describedby`, submit shows "Preparing…" + `aria-busy`; with an email it opens a prefilled mailto, otherwise it says honestly the form isn't connected yet) |
| cta | Accent band with title, text and inverted button to contact or mailto |
| preview | Copy + three points beside an illustrative app window (labelled tabs, progress rows, bar chart) |
| footer | Brand, tagline, secondary CTA; "Explore" sitemap links; "Contact" (email or form hint, location); base row with © year, a **Privacy** disclosure button revealing an honest notice (no analytics/advertising cookies; fonts and photos load from Google Fonts and Unsplash; messages used only to reply), and Back to top; 44px targets |

Tint rhythm: contact/cart/quotes tinted; alternate tints elsewhere; never two tinted sections in a row.

### 6.6 `kit.py` — `KitSite`
`KitSite(prompt, brief, sections)` builds: brand (§5.1 rules + descriptive fallback), business
type, email (brief contact or first email in prompt), location (`extract_location`: "<business noun>
… in/from <Capitalised Place>", rejecting React/TypeScript/etc.), supplied products, theme
(+ palette), ordered sections (dedupe; nav → header; force `header, hero, …, footer`; move
contact/cta kinds to the end), kinds, `is_store` (cart section or positive mention of
cart/add to cart/online store/e-commerce, negation- and "-unavailable"-aware),
`checkout_available` (positive "checkout" not negated), image planner, integrity, labels, reveal
section (first of features/products/articles/story/work), tints, contents, voice list.
Methods: `needs_model(slug)` (all kinds except header/footer), `max_tokens(slug)`, `messages(slug)`,
`is_usable(slug, text)` (valid JSON with a clean headline/title), `accept(slug, text)` →
(content, notes) storing hero style (`signal` → product; no photos → typographic/split; else seeded
from `hero_styles`), location fact, and shader flag; `render(slug)` → `[(tsx_path, tsx), (css_path, css)]`;
`base_css()`; `font_href()`; `head_tags()` and `public_files()` (§8); `theme_summary()`.

### 6.7 Kit tests (`tests/test_site_kit.py`)
- Theme contrast invariants; theme selection for the four §11 prompts gives
  atelier / signal / spice / gallery; dark/light words respected.
- `parse_json_object` on fenced, trailing-comma, and truncated JSON.
- Integrity: the two leaked sentences from §2.1 are removed; "$45 each" removed when the prompt has
  no 45; supplied products keep names and prices.
- Rendering: for six prompts (the four in §11 plus "Threadleaf stationery shop. Products: Notebook
  $12, Pencil set $8, Desk planner $24. Add to cart with a cart count. FAQ and contact." and
  "Ironworks — a strength gym in Pune. Classes, coaches, membership pricing, FAQ, contact.") with
  (a) realistic model JSON and (b) no model output: write the files plus a minimal `App.tsx` /
  `App.css`, then assert `tsc --noEmit --strict` passes and `run_static_lint`, `run_contract_check`,
  `run_accessibility_check`, `run_motion_rules_check`, `run_rendering_contract_check` and
  `preflight_section_files` return no errors. Mark the tsc part `@pytest.mark.slow` if needed.

---

## 7. Phase 3 — Integration

**3.1 Agent loop (`agent/agent.py`).** Add `strategy: str = "kit"` to `run_site_agent_on_example`.
When `"kit"`, run `_run_kit_site(...)` and return the same result dict shape:
- Build `KitSite`; emit the existing `plan` event (names = `pascal(slug)`) and a `design_plan` event
  carrying `kit.theme_summary()`.
- For each section: emit `plan_update` in_progress; if `needs_model`, call
  `runner.generate_turn(history=kit.messages(slug), max_new_tokens=kit.max_tokens(slug),
  temperature=0.7, top_p=0.8, top_k=20, repetition_penalty=1.0, stop_check=stop_check)` with the
  existing progress-status thread; if `not kit.is_usable`, retry once at temperature 0.55; then
  `kit.accept(...)`; render; run `preflight_section_files` (must pass — otherwise log and re-render
  with fallback content); write files; emit `plan_update` completed with notes; record
  `turn_logs`/`generation_metrics` as today. Respect `stop_check` between sections.
- `generation_quality`: `native` when every model section was usable, `repaired` when any used
  fallback copy, never `blocked`. Return `"kit": {"base_css", "font_href", "head_tags",
  "public_files", "theme"}` in the result.
- Skip the synthetic-validation block (A14) for kit runs; validation is done by the server.
- Keep the legacy freeform path as `strategy="freeform"`; select via `SITE_STRATEGY` env var
  (default `kit`) and a task field `strategy` in `/api/generate`.

**3.2 Runner (`AgentModelRunner.generate_turn`).** Accept `top_p`, `top_k` and pass them to
`model.generate` (`do_sample=True` when temperature > 0). The `</tool_call>` stop string is harmless
for JSON. Keep the generation log.

**3.3 Module identity (A3).** In `agent/agent.py` replace bare imports (`from agent_protocol import`,
`from site_brief import`, `from style_ingest import`, etc.) with `agent.`-qualified imports, and call
`agent.agent_protocol.set_default_tokenizer` explicitly after load. Keep the `sys.path` entries only
if other scripts need them. Add a test asserting `agent.config.ModelRuntimeConfig.count_tokens` uses
the registered tokenizer after a mock registration.

**3.4 Server (`server/app.py`).**
- `_run_site_generation` (3379+): pass `strategy`; after the agent returns, copy `result["kit"]`
  into `brief` (`kit_base_css`, `kit_font_href`, `kit_head_tags`, `kit_public_files`) before
  scaffolding; set `max_turns` only for freeform.
- `_scaffold_site_vite_runner` (1467+): when `brief["kit_base_css"]` exists, write it as
  `src/App.css` instead of root tokens + reset (fixes A11); use `kit_font_href` for the font link
  (fixes A12); inject `kit_head_tags` into `<head>` of both `index.html` and `static-preview.html`;
  write `kit_public_files` under `public/` (binary-safe for the PNG). Replace the red fallback box
  (A8) with `() => null` and a `console.warn`. Also apply the meta-description fix (B7) for freeform.
- Move `_store_task_failure` (3309) above `_worker` (825) or start the worker thread at the end of
  the module (B6).
- `scripts/run_web_ui.bat`: remove the default `MODEL_PATH` (base model is the right content
  writer); keep `MODEL_PATH` as an opt-in override.

**3.5 Edit flow.** Session edits (`_run_session_edit_turn`) keep working on the written files. Add
the kit's class/token summary (theme name, `--k-*` tokens, section class names) to the edit
prompt so the model edits in the same system.

---

## 8. Phase 4 — Professional UI/UX baseline (user checklist, built into the kit)

| Requirement | Implementation | Verify in browser |
|---|---|---|
| 3-second hero: who / what / what next | Brand in header + headline + lede + one primary CTA + secondary + relevant visual (photo, product preview, shader or art) | Above the fold at 1280×800 and 390×844 |
| 8px spatial grid, generous whitespace | `--k-space-*` tokens used for gaps/padding; section density `clamp()` | Computed styles are multiples of 4/8px |
| ≤2 font families, 65ch, line-height 1.5–1.6 | Theme pairs; `.k-text{max-width:65ch}`; body 1.6 | `document.fonts` shows the two families loaded |
| 60-30-10 colour; no pure #000/#FFF surfaces | Neutral bg, surfaces/lines/muted, accent only for CTAs/active/highlights; clinic bg #FBFCFC | Visual check |
| 4–6 nav items, CTA on the right | `links[:6]`, header CTA | Count links |
| Sticky / hide-on-scroll header | Header `is-tucked` logic (§6.5) | Scroll down 600px → hidden; scroll up → visible |
| Active wayfinding | Scroll-spy `aria-current` + underline (desktop) / accent (drawer) | Scroll to each section |
| 44×44 tap targets; animated drawer; scroll lock | `--k-tap`, drawer transitions, `body.style.overflow='hidden'` while open | At 390px measure targets; open menu and try to scroll |
| Footer safety net | Sitemap, contact, location, privacy notice, secondary CTA, back to top | Visual + click Privacy |
| Five interaction states | Default affordances; hover/focus 150–200ms with `:focus-visible`; `:active scale(.98)`; loading (`aria-busy`, "Preparing…"); inline errors; empty states (cart) | Tab through; submit empty form; submit valid form |
| Zero CLS | `width`/`height` + `aspect-ratio` on all media; fixed header height | CLS < 0.1 (motion gate reports it) |
| Fast LCP | Hero image `loading="eager" fetchPriority="high" decoding="sync"` + `<link rel="preload" as="image" href=hero fetchpriority="high">`; others lazy; WebP/AVIF via `auto=format` | Network panel |
| Fluid responsiveness | `clamp()` type; Grid/Flex; no horizontal scroll 320px→ultrawide | scrollWidth checks at 320/375/1280/1920 |
| WCAG AA | Contrast-checked tokens; landmarks; labelled controls; reduced motion | Accessibility check + `emulate_media(reduced_motion='reduce')` |
| 404, favicons, OpenGraph | `public/404.html` (themed, brand + "This page doesn't exist" + link home); `public/favicon.svg` (brand initial on accent); `public/apple-touch-icon.png` 180×180 (Pillow); head tags: description (hero lede), `theme-color`, `og:type/title/description/image` (hero photo URL or generated `public/og-image.png` 1200×630), `twitter:card=summary_large_image`, icon links | Open `/404.html`, inspect `<head>` |

---

## 9. Phase 5 — Motion system (attached motion brief; native, compositor-only)

| Brief item | Implementation |
|---|---|
| Staggered viewport reveals, once | `[data-motion="scroll-reveal"]` (opacity 0, translateY 20px → visible, 700ms `--k-ease`) with 70ms `nth-child` stagger; `useReveal` IntersectionObserver adds `is-visible`, `unobserve`s and `disconnect`s; applied to **one** section (the reveal section) to avoid generic fade-everything |
| Hero text reveal | `h1[data-motion="text-in"]` keyframe rise (900ms) + staggered lede/actions; visible immediately under reduced motion (satisfies the validator's text-reveal check without split spans) |
| Native scroll-driven animations | `@supports (animation-timeline: view())` + `prefers-reduced-motion: no-preference`: media images settle from scale 1.08 → 1 over `animation-range: entry 0% cover 35%` |
| Multi-plane micro-parallax | `.k-depth-slow` (hero media drifts 0 → 9vh over the first viewport, ≈0.85×) and `.k-depth-fast` (−6vh, ≈1.1×) via `animation-timeline: scroll(root)`, only for `(hover:hover) and (min-width:900px)` |
| Pinned scrollytelling | Steps renderer (§6.5) |
| Horizontal galleries | Work reel with native scroll-snap (no scroll conversion/hijacking) |
| Magnetic buttons | `useMagnet` on the hero primary CTA: ≤8px x / ≤6px y pull, mouse pointers only, `(hover:hover)` and motion allowed; reset on leave |
| Tilt + spotlight cards | `tiltHandlers` set `--k-rx/ry` (±3°/±4°), `--k-mx/my`, `--k-glow`; `.k-tilt` uses `perspective(1000px) rotateX/Y` and a radial spotlight `::after`; only on lively themes; none under reduced motion |
| WebGL shader backgrounds | `ShaderBackdrop`: one full-screen triangle, ≈20-line fragment shader (two sine fields mixing bg → accent → accent2, cursor glow, bottom fade to bg); colours from theme (dark: 50%/42% mixes, light: 22%/16%); `setTimeout` loop at ~30 fps (stays under the 50/s idle-loop gate, B10), paused by IntersectionObserver when off-screen and on `visibilitychange`, single static frame under reduced motion, DPR capped at 1.5, `ResizeObserver`, `WEBGL_lose_context` on unmount; CSS gradient fallback when WebGL is unavailable. Satisfies the 3D rendering diagnostic via `<canvas>` |
| SVG line drawing | Steps progress line via `stroke-dashoffset` |
| Spring-like easing, View Transitions | `--k-ease: cubic-bezier(0.22,1,0.36,1)` for drawers, accordions, reveals; menu tabs use `startViewTransition` + `flushSync` with `view-transition-name` on the panel |
| Golden rules | No scroll hijacking, no hidden cursors, only transform/opacity animated, heavy effects off on touch/small screens and under reduced motion |
| Deliberately excluded | Lenis/inertia scrolling, Three.js/R3F/Spline/GLB models, custom cursors — conflict with the project's package policy (`dependency_manager.PackagePolicy`), the idle-loop gate and mobile performance. Revisit only if the user explicitly requests them, through the existing dependency tools |

---

## 10. Phase 6–7 — Honest gates, bug fixes, hygiene

**10.1 Gates (A14–A17, B9).**
- A14: in `run_site_agent_on_example`, when no full project exists, return `validation=None`
  with `status="pending"` instead of synthesising passes; the server's `verify_and_repair_project`
  is the source of truth.
- A15: remove the near-white penalty; instead flag *uniform* screenshots (very low variance across
  the whole frame) as blank.
- A16: in `site_benchmark_scorer`, return `None`/"not applicable" (excluded from the mean) when a
  spec has no keywords or sections; feed planner sections into completion scoring; score content by
  absence of placeholder names/hosts rather than word count.
- A17: add to `check_site_files`: instruction-leak phrases (reuse the kit's meta regex), placeholder
  hosts (`via.placeholder.com`, `placehold.co`, `placekitten`, `picsum.photos`, `example.com`
  images), debug text ("has no valid React export"); add a runtime check for broken images
  (`check_broken_rendered_images` already exists — make it an error) and dead in-page anchors.
- B9: fix the import scanner to ignore string contents; make the INERT BUTTON scanner parse
  attributes with a JSX-aware regex (balanced `{…}`); make the motion rules key on actual APIs
  (`position: sticky` on a story container, not any `sticky`; `IntersectionObserver`; etc.).

**10.2 Freeform-path fixes (still used for `strategy="freeform"` and edits).**
- A2 sampling (temp 0.7/top-p 0.8/top-k 20, repetition penalty 1.0 for code), A9 (only adapt
  radii on card selectors; keep `--radius-buttons` for buttons), A10 (scope synthesised CSS to the
  section root class), A7 (per-section repair budget of 3 regardless of position), A6 (include the
  accepted sections' root class names and the token block in each section prompt), A19 dead code.

**10.3 Setup & docs (A18, B11, B12).** `setup.sh/.bat` download `Qwen/Qwen3-4B` into `base-model/`;
README: correct model, adapter status (no promoted adapter; base model by default), kit
architecture, `SITE_STRATEGY`; delete stale `web_ui_static/assets/*` not referenced by
`web_ui_static/index.html`; delete `.claude_baseline_tests.txt` and `runs/photo_vetting/`.

**10.4 The 25 failing tests.**
- Auto-scaffold/site-state/recovery (6): tests assert behaviour that was intentionally removed
  (fallback scaffolding). Rewrite them to assert the blocked/kit behaviour; delete
  `rewrite_fallback_sections` with its tests.
- Context decision, training preflight, methodology, retrain, migration (10): CLI/preflight contract
  changed; update tests to the current `training/` APIs (read `train_sft.py` preflight first).
- Benchmark/promotion gates (5): tests must provide the mandatory `mock` field; keep the gate
  fail-closed.
- Doc export (2): regenerate `docs/architecture_and_source.md` with
  `scripts/generate_architecture_and_source.py` after code changes, as the last step.
- `test_p1_quality_contracts::test_manifest_preserves_supplied_facts_and_cart_contract` and
  `test_runtime_hardening::test_timeout_retains_model_ownership_until_generation_exits`: real
  regressions — investigate with `superpowers:systematic-debugging` and fix the code, not the test.
Target: **0 failures**.

---

## 11. Phase 8 — Self-check through the workbench UI (mandatory)

Claude verifies its own work by using the product the way the user does.

**11.1 Start.** On the laptop: `cd C:\Users\AYUSH\Documents\slm && scripts\run_web_ui.bat`
(background process). Wait until the log shows `[Server] Model ready.` and
`GET /api/status` returns ready. If the frontend source changed, rebuild first
(`cd frontend && npm run build`).

**11.2 Drive the UI.** In the browser, open `http://127.0.0.1:5000`. For each prompt below: click the
chat input, type the prompt, press Enter, and watch the plan panel until every section shows
completed and the run reports done (≈2–4 minutes per site on the 4050). Open the preview pane. Take
screenshots at 1280×800 (top, then scrolled through every section) and at 390×844 (top, menu open,
footer). Save to `runs/ui_selfcheck_20261016/<name>/`.

Prompts:
1. `Aster & Kiln — handmade ceramics studio in Lisbon. Warm editorial photography, clay textures. Sections: collection, glaze stories, care guide, studio notes. Email hello@asterkiln.com. No online checkout.`
2. `Northwind — a B2B analytics SaaS for logistics teams. Dark, technical look. Include a product preview and FAQ. Do not show pricing.`
3. `Saffron Table — modern Indian restaurant in Dehradun. Menu, about the chef, private dining. We do not take online reservations.`
4. `Portfolio for Maya Chen, a brand designer. Minimal, lots of white space. Projects: Fern Studio rebrand, Halo app identity, Ostra packaging.`

**11.3 Expected per prompt.**
| # | Theme | Sections | Must also show |
|---|---|---|---|
| 1 | atelier | collection, glaze stories, care guide (scrollytelling), studio notes, footer | ceramic photos; "Ask about this piece" mailto (no cart, no checkout); email in contact/footer; location Lisbon |
| 2 | signal | features, faq, product preview | shader hero + illustrative app window; no pricing anywhere; FAQ accordion works |
| 3 | spice | menu (tabs), about, private dining, contact | Indian food photos; no reservation form wording; location Dehradun |
| 4 | gallery | projects (the three named projects, in order), contact | typographic hero; no "skills" section; no invented clients |

**11.4 Checks on every site (in the browser, not by reading code).** Everything in §1, plus the
§8 table's "Verify" column and §9: reveal fires once; reduced-motion emulation shows everything
static and visible; shader pauses when scrolled away (frame counter stops); header tucks/returns;
active nav underline follows scroll; Escape closes the drawer and focus returns; form errors appear
inline; no console errors; `document.documentElement.scrollWidth <= innerWidth` at 375 and 1280;
`/404.html` renders; `<head>` contains description, OG and icon tags.

**11.5 Iterate.** For any failure: identify the cause (planner, content filter, renderer, scaffold),
fix it, add a regression test, re-run that prompt. Repeat until all four pass. Then run one
unscripted prompt of a different kind (e.g. "A summer coding camp for kids in Bengaluru with
schedule, pricing and FAQ") to check generalisation.

**11.6 Report.** Write `runs/ui_selfcheck_20261016/REPORT.md`: prompt, theme, sections, timing,
pass/fail per check, screenshots, issues fixed during the loop.

---

## 12. Out of scope (later)

- Retraining: generate reviewed content-JSON trajectories in the exact kit prompt format
  (hundreds of sections across many subjects), LoRA r16, lr ≈1e-4, 10–15% held out; promote only
  through the existing gate with the §11 checks as part of the evidence.
- VLM/human visual review in the benchmark.
- Multi-page sites and real form backends.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Model returns invalid or empty JSON | Repair parser, one retry, deterministic fallback; never blocks a section |
| Copy becomes generic | Voice continuity, specific prompts, supplied items; retraining later |
| Kit sites look alike | 12 themes × hero styles × layout variants × subject photos; prompt-hash tie-breaks |
| Unsplash unavailable offline | `onError` → designed art panel; no layout shift (fixed aspect ratios) |
| `animation-timeline` unsupported (Firefox/Safari) | `@supports` guard; pages are complete without it |
| WebGL unavailable | CSS gradient fallback on the canvas element |
| Validator heuristics flag kit output | Patterns in §6.5; kit render tests run the real validators |
