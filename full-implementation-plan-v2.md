# Full Implementation Plan — ReactAgent SLM (v2)

Everything below is organized into phases with dependencies. **Every item has a
Verify step — a concrete command or test you run yourself.** Given that the
last two rounds produced detailed changelogs describing work that wasn't
actually in the code, don't accept "done" from the coding agent for any item
until its Verify step passes. Paste this to your coding agent one phase at a
time; run the phase's Verify block before starting the next phase.

**v2 changes:** added a sub-step on not trusting narrative documentation as
ground truth, added a git-baseline step, split Phase 2 into what's already
done vs. still needed, added missing verify checks (heading fonts, CSS
conformance function existence, confirm-modal existence), and added an
optional automated eval step after Phase 3. See inline notes marked **[v2]**.

---

## Phase 0 — Process fix (do this first, it's what's been missing)

**Problem:** the last two update rounds shipped changelogs claiming 10–15
specific fixes each, and on inspection almost none of the code matched the
claims (functions that don't exist, strings that were never removed, UI
features that appear once in the changelog text and nowhere in the actual
`index.html`).

**Fix:** for every item in this plan, require the agent to output, alongside
its summary, the actual diff hunk or a `grep -n` result proving the change
landed — not prose describing the change. Reject any completion claim that
isn't accompanied by that evidence. Concretely:

1. **[v2] Establish a git baseline before touching anything.** If the
   workspace isn't already a git repo, run `git init && git add -A && git
   commit -m "baseline before remediation plan"` first. Without this, the
   `git diff --stat` check in step 2 below has nothing to compare against and
   is a no-op. Confirm with `git log --oneline -1` that a baseline commit
   exists before Phase 1 starts.
2. **[v2] Treat any existing "architecture and source" or changelog-style
   document as unverified narrative, not ground truth — including any prose
   sections describing "Phase N" work as complete.** If such a document is
   fed to the coding agent as context, explicitly instruct it that prose
   claiming a fix landed is not evidence; only a `grep`/`view` of the actual
   current source file counts. This project already has a live example: a
   supplied architecture document's narrative sections (covering explicit
   section parsing, visual-judge fixes, font/theme diversification, CSS
   conformance checks, and the entire UI accessibility/reconnect/modal pass)
   all claim to be done, and none of them are present in that same
   document's own embedded source code. Don't let the agent "confirm" a
   phase is finished by citing that narrative — require a fresh grep against
   the actual working files every time.
3. After each phase, run `git diff --stat` (or equivalent) yourself and
   confirm the file/line-count changes are in the ballpark of what the phase
   requires — a claimed "full accessibility and SSE-reconnect rebuild" that
   shows a 20-line diff is a red flag before you even read the code.
4. Run this repo's own Verify commands (below) yourself, not by asking the
   agent to run and summarize them.
5. Don't let a later phase build on an earlier phase's claimed-but-unverified
   work — if Phase 1's Verify fails, stop and fix Phase 1 before starting
   Phase 2.

---

## Phase 1 — Explicit section parsing (the actual Issue-1 fix, done for real)

**Files:** `agent/site_brief.py`, `agent/agent.py`

1. Add a real function:
   ```python
   def extract_explicit_sections(prompt: str) -> Optional[List[Tuple[str, str]]]:
       """Detect a user-authored numbered/bulleted section list in the prompt.
       Returns [(slug, description), ...] in order, or None if no explicit
       list structure is present (≥2 matches required to count as a list)."""
   ```
   Match patterns like `^\s*\d+[.)]\s*([A-Z][\w\s/&-]+):\s*(.+)$` and
   `^\s*[-*•]\s*([A-Z][\w\s/&-]+):\s*(.+)$`. Slugify the captured label
   (lowercase, spaces→underscores, strip punctuation).
2. In `generate_content_brief()` / the heuristic brief builder: call
   `extract_explicit_sections(prompt)` **before** `detect_business_type()`.
   If it returns a non-empty list, use those slugs as `brief["sections"]`
   directly and skip the domain-template `middle` assembly. Only fall back
   to `detect_business_type()` when no explicit list is found.
3. Feed each captured description into a **per-run override** of
   `_SECTION_INSTRUCTIONS` in `agent.py`, keyed by the section slug for that
   task only — don't mutate the shared static dict.
4. In `_build_section_synonyms()`: delete the hardcoded block entirely —
   ```python
   if "product" in sec.lower():
       existing.update(["products", "product", "sculptures", "sculpture",
                         "hardware", "spatialproducts", "spatialproduct", "spatialaudio"])
   ```
   and also remove `"sculptures"` from the static `_SECTION_SYNONYMS["features"]`
   entry. The generic word-stemming path already above this block should
   handle arbitrary section names — if it doesn't handle multi-word names
   correctly, fix the stemmer (stem each word in a multi-word slug, not just
   the joined slug) rather than adding another special case.

**[v2] Note:** confirmed via direct source inspection that
`extract_explicit_sections` does not currently exist anywhere in the
codebase, and the hardcoded `"sculptures"`/`"spatialaudio"` block is still
present verbatim — despite prior documentation claiming both were already
fixed. This phase is genuinely un-started; treat it as such.

**Verify:**
```bash
grep -n "def extract_explicit_sections" agent/site_brief.py   # must exist
grep -rn "sculptures\|spatialaudio" agent/                    # must return nothing
```
Then run two prompts end-to-end:
- The AURA Spatial Audio prompt verbatim — plan must come back
  `header -> hero -> spatial-products -> footer`.
- A **new** prompt you write yourself with an unrelated numbered section list
  (e.g. a law firm: "1. Header 2. Hero 3. Practice Areas 4. Attorneys 5.
  Footer") — plan must come back with those 5 slugs, not a generic template.
  This second test is the one that actually proves generality; don't skip it.

---

## Phase 2 — Visual judge: fix the signal and wire it up

**Files:** `agent/visual_judge.py`, `server/app.py`, `generate_star.py`

**[v2] Status check before starting:** direct inspection shows the score
*computation and storage* piece already exists — `server/app.py` already
computes `v_res = _score_screenshot_heuristic(ss)` and stores it as
`"visual_score": visual_score` inside `site_entry` (and therefore into
history/session JSON). Don't re-do that part or let the agent claim credit
for adding it. What's actually missing is items 1, 3, 4, and 5 below —
scope the work and the verify block accordingly.

1. In `_score_screenshot_heuristic()`: remove the `top_brightness > 220`
   penalty (a light header is not a defect) — **confirmed still present at
   the time of writing**. Replace it with an actual nav-bar check if you want
   one — e.g. detect a horizontal band near the top with a background color
   distinct from the section below it, independent of whether that color is
   light or dark.
2. ~~In the site-generation worker (`app.py`): store the computed score...~~
   **[v2] Already done** — `visual_score` is computed and persisted into
   `site_entry`. Confirm it's *also* being threaded into `turn_record` for
   follow-up conversational edit turns (`_run_session_edit_turn`), since that
   path is separate from initial site generation and may not carry it yet.
3. Surface it in `generate_post_generation_summary()`'s Status section, e.g.
   `Visual check: 4/5 — footer region may be missing`. **[v2] Confirmed
   currently absent** — the summary function has no such line today.
4. If `visual_score["score"] < 3` and turn budget remains, schedule one
   corrective turn targeting the specific issue(s) reported, the same way
   `[CSS MISSING]` already triggers a corrective turn — don't just report the
   low score and move on.
5. Import and use `visual_judge` in `generate_star.py`'s rejection-sampling
   pipeline: filter candidate trajectories by `visual_threshold` in addition
   to the existing TS/build checks. **[v2] Confirmed currently absent** —
   `generate_star.py` has no `visual_judge` import today; only the existing
   component-level `run_star_pipeline` is present, with no site-specific
   equivalent.

**Verify:**
```bash
grep -n "may lack navigation bar" agent/visual_judge.py   # must return nothing
grep -n "top_brightness > 220" agent/visual_judge.py       # must return nothing (item 1)
grep -n "visual_score" server/app.py                       # must show it stored on result AND threaded into turn_record for edit turns, not just initial generation
grep -n "Visual check" server/app.py                       # must show it in the summary-building call, not just printed (item 3)
grep -n "visual_judge" generate_star.py                    # must show a real import + call, not zero hits (item 5)
```
Generate one site with a deliberately light/white header design-system
override and confirm it does **not** get docked for that in the printed
score breakdown. Then generate a site, force `visual_score < 3` (e.g. by
capping turns), and confirm a corrective turn actually fires rather than the
low score just being logged.

---

## Phase 3 — Fix the training-data template homogeneity (the real design-quality root cause)

This is new since the last audit and is the biggest lever on "why does
everything look the same." Across ~220 site trajectories, one skeleton
repeats near-verbatim 100+ times: the filler line *"Carefully curated
offerings tailored to provide exceptional quality and reliability,"* the
`__ambient` radial-glow hero div, the `{BusinessName} Official` pulsing
badge, and the `0{idx+1}` card index badge — reused identically across
totally unrelated industries.

1. **Deduplicate the template at the source.** In whichever generator
   produced this batch (`generate_site_trajectories_batch4.py`,
   `_batch5.py`, and siblings), find wherever these four snippets are
   emitted and confirm whether they're literally copy-pasted per domain
   entry or generated by one shared helper function applied to every domain.
   If it's a shared helper, that's the actual bug — the helper needs to
   *vary* structure per domain, not just swap the color token.
2. **Write real per-domain structural variation**, not just per-domain
   colors: at minimum, vary (a) the hero's supporting visual element (not
   every hero needs a radial ambient glow — try a split-image layout, a
   stat strip, a diagonal divider for some domains), (b) the card grid shape
   (not always 2×2 — try a horizontal scroll strip, an asymmetric
   masonry, a numbered list for others), (c) drop the generic filler
   description sentence and replace it with domain-specific copy — if a
   generation script is auto-filling this sentence as a default, remove the
   default and require real copy per domain entry.
3. **Regenerate a fresh trajectory batch** using the fixed generator and
   spot-check for the four patterns above — they should now vary, not repeat.
4. This is naturally where the de-cliché pass belongs too — while touching
   this generator, grep for and rewrite any remaining instances of
   "elevate," "seamless," "effortless," "empower," "unlock," "cutting-edge"
   in the copy these generators produce.
5. **Don't retrain until this is done.** Fine-tuning on a corpus that still
   has the duplicated skeleton just re-teaches the same generic output with
   extra steps.

**Verify:**
```bash
grep -c "Carefully curated offerings tailored to provide exceptional quality and reliability" <new-batch-file>
grep -c "__ambient" <new-batch-file>
grep -c "0{idx + 1}" <new-batch-file>
```
All three counts should be near-zero (a few coincidental matches are fine;
100+ identical repeats is the bug). Then spot-check 5 random trajectories
from the new batch across different domains and confirm their hero layout,
card grid shape, and description copy are visibly different from each other,
not just recolored.

**[v2] Optional but recommended — replace pure spot-checking with a
measurable signal.** Human spot-checking 5 trajectories is a reasonable
smoke test but doesn't scale and is exactly the kind of "looks fine to me"
judgment this plan is otherwise trying to eliminate. If an eval/benchmark
harness already exists in the repo (there's a fine-tuning/eval pipeline
referenced elsewhere in this codebase), before regenerating the batch:
1. Compute a simple template-similarity metric across the *old* batch (e.g.
   n-gram/Jaccard overlap of hero-section markup across trajectories from
   different domains, or a count of shared multi-word phrases above some
   length threshold).
2. Regenerate the batch per steps 1–4 above.
3. Recompute the same metric on the *new* batch and confirm it dropped
   substantially, not just that your 5 spot-checked samples happened to look
   different. This gives you an objective before/after number instead of
   relying entirely on manual review.

---

## Phase 4 — Domain theme diversification

**File:** `agent/site_brief.py` (`_DOMAIN_THEMES`)

1. Give each of the 15+ domains 2–3 alternate palette options, including at
   least one light/paper option per domain (a bakery, wedding photographer,
   or coffee shop defaulting to dark navy is a real mismatch). Select
   between them deterministically seeded by business name (so re-running the
   same prompt gives the same result) rather than 1:1 domain→theme.
2. Vary `font_body` **and `font_heading`** — pull from a small curated set
   (Inter, Manrope, Source Sans 3, IBM Plex Sans, Work Sans for body; a
   distinct curated set for headings) and pair deliberately with each other
   instead of defaulting every domain to the same fonts. **[v2] Confirmed
   currently: `font_body` is `"Inter"` in essentially every domain entry, and
   only 4 distinct `font_heading` values exist across all domains — both
   need fixing, not just body font.**
3. Give `accent_color` a duotone/secondary-accent option per domain instead
   of one flat hex.
4. **[v2] Before claiming CSS conformance/typography-hierarchy validation is
   "enhanced," confirm the underlying function exists at all.** A prior
   changelog claimed `validate_css_conformance()` in `agent/style_ingest.py`
   was enhanced with heading-to-body font-size-ratio checks and spacing
   scale progression validation. Direct inspection shows **no function of
   that name exists anywhere in the current source.** If typographic/spacing
   conformance checking is in scope for this phase, it needs to be built
   from scratch, not "enhanced" — scope this explicitly before starting so
   it isn't silently dropped.

**Verify:**
```bash
grep -c '"font_body": "Inter"' agent/site_brief.py    # should now be well under the domain count, not equal to it
grep -o '"font_heading": "[^"]*"' agent/site_brief.py | sort -u | wc -l   # should be >= 6 distinct values, not 4
grep -n "def validate_css_conformance" agent/style_ingest.py             # confirm it exists before assuming it can be "enhanced"; build it if absent and typography checks are in scope
```
Generate 5 sites across 5 different domains with no custom design system
supplied. Confirm at least 2 of the 5 land on a visibly different
palette/typography pairing, not all near-black with Inter body text.

---

## Phase 5 — Auto-recovery quality (depends on Phase 1's per-section descriptions)

**File:** `agent/agent.py` (`auto_scaffold_section`, `synthesize_section_css`)

1. Parse the per-section description text (now captured for real in Phase 1)
   for an implied item count ("4 flagship sound sculptures" → 4 cards) and
   named items in parentheses/bullets ("Aura One, Aura Studio, ..."). Scaffold
   that many differentiated cards, not one generic filler card.
2. Parse named data fields mentioned in the description ("product name,
   frequency response tag, acoustic architectural specs") and use them as
   the placeholder field labels per card.
3. Keep `auto_recovered: true` in the turn log regardless — the goal is a
   respectable fallback, not hiding that one happened.

**Verify:** re-run the AURA prompt with a section budget deliberately capped
low enough to force auto-recovery on the products section (e.g. reduce
`max_turns`), and confirm the recovered section renders 4 distinct product
cards with the named fields, not one generic card.

---

## Phase 6 — Workbench UI redesign (Claude/ChatGPT-style chat)

This is the largest phase. Land it after Phases 1–5 so the UI has real
signals (visual score, per-section plan, auto-recovery flags) to display.

### 6.1 Layout
- Centered message column (~680–760px max-width), generous vertical rhythm.
- Collapsible left sidebar for session history (business name + last-message
  time, not code-editor chrome).
- No permanent fixed-width right pane — code/preview/terminal become a
  slide-over panel or bottom sheet opened on demand.
- Prompt input pinned to the bottom of the message column, auto-growing
  textarea.

### 6.2 Message rendering
- User turns: plain text block with light background tint, not a heavy
  speech-bubble.
- Assistant turns: render the post-generation summary as real typeset
  markdown (actual heading sizes, spacing, bullet lists) instead of inline
  `<p style="...">` tags per line.
- Streaming reveal of the summary text as it arrives over SSE.
- File-touched chips and diff/preview action buttons as a quiet footer row.
- The visual-score badge from Phase 2 and the auto-recovery flag from Phase 5
  surfaced inline on the relevant assistant turn.

### 6.3 Visual language
- Warmer, more neutral palette (soft off-white or muted warm-gray dark mode,
  one restrained accent) instead of the current dark-indigo dev-tool look.
  Build an actual light mode, not just imply one.
- Fix `--text-3` to at least 4.5:1 contrast against whichever base color you
  land on — check the specific hex pair with a contrast calculator, don't
  eyeball it. **[v2] Confirmed current value is `#6b7280`, not the `#9ca3af`
  a prior changelog claimed — check this pair's actual contrast ratio before
  assuming it already meets AA.**
- Real type scale (5–6 defined steps) instead of ad hoc `11px/11.5px/12px`
  values scattered through the stylesheet.

### 6.4 Accessibility (do this as part of the redesign, not after)
- `aria-label` on every icon-only control.
- `<label>` on every form input.
- `role="dialog"` + `aria-modal="true"` + focus trap on any modal/slide-over.
- Check every text/background pairing you introduce against WCAG AA.
- Real responsive breakpoints — the centered-column layout should make this
  much simpler than the old fixed three-pane layout, since side panels
  become overlays instead of permanent flex children.

### 6.5 Robustness
- SSE reconnect-with-backoff: on `es.onerror`, poll a lightweight
  `/api/task/<id>/status` once; if the task is still active server-side,
  reopen the `EventSource` and show "Reconnecting…" instead of declaring the
  generation dead. A generation can run 20–40 minutes — a transient network
  blip should not silently truncate progress visibility. **[v2] Confirmed
  the current `es.onerror` handler just closes the connection and gives up
  (`es.close(); _setGenerating(false); finishProgress();`) — there is no
  reconnect logic today despite a prior claim of exponential backoff.**
- Replace native blocking `confirm()` calls with the redesign's own modal
  component. **[v2] Confirmed 4 native `confirm(...)` calls still exist in
  `web_ui_static/index.html`, and no `showConfirmModal` (or equivalent)
  function exists anywhere in the source yet — this needs to be built, not
  just wired up.**
- Persist sidebar state, active theme, and last-opened panel to
  `localStorage`.

**Verify (this is where the last two rounds failed — check the actual file, not the summary):**
```bash
grep -c "aria-label=" web_ui_static/index.html          # should be roughly one per interactive icon control
grep -n -- "--text-3:" web_ui_static/index.html         # confirm the hex value, then check its contrast ratio yourself
grep -c "@media" web_ui_static/index.html               # should be several, not one
grep -n "onerror" web_ui_static/index.html              # confirm it reopens an EventSource, not just closes+idles
grep -c "confirm(" web_ui_static/index.html             # native confirm() calls should now be zero
grep -n "showConfirmModal" web_ui_static/index.html     # [v2] must exist and be called from the sites where confirm() used to be — confirms the replacement was actually built, not just deleted
```
Load the app at 1280px, 1024px, and 768px and visually confirm the layout
holds. Kill network for ~10 seconds mid-generation and confirm the UI shows
a reconnecting state and resumes, rather than going idle.

---

## Suggested order and why

1. **Phase 0** first, including the git baseline and the instruction to
   distrust narrative-only documentation — without these, every later
   Verify step is checking against an unreliable starting point.
2. **Phase 1** next — it's the original reported bug, it's small, and it's
   testable in isolation.
3. **Phase 2** next — cheap, and Phase 5's quality depends on having a real
   quality signal to react to. Scope it to the sub-items confirmed still
   missing (see the Phase 2 status note) rather than redoing what's already
   there.
4. **Phase 3** before any retraining — this is the actual root cause of
   generic-looking output; skipping it means Phases 4–5 are polishing a
   corpus that's still fundamentally repetitive.
5. **Phase 4** and **Phase 5** together — both depend on Phase 1's captured
   per-section descriptions and are independent of the UI work.
6. **Phase 6** last, and largest — land 6.1–6.2 (layout/message rendering)
   first since 6.3–6.5 are easiest to verify once the new structure exists.

At the end of each phase, re-run that phase's Verify block yourself before
telling the agent to proceed — that's the only thing that would have caught
the last two rounds of unimplemented changelogs before they shipped.
