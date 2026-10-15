"""The site stylesheet written to src/App.css for kit-built sites.

Tokens, a sane reset, layout/type primitives and the native motion system.
Component stylesheets only add scoped rules on top of these primitives.
"""
from __future__ import annotations

from .themes import Theme, _ensure_contrast, _rgb, contrast, mix

SERIF_FONTS = {
    "Fraunces", "Cormorant Garamond", "DM Serif Display", "Instrument Serif", "Newsreader", "Marcellus",
    "Libre Bodoni", "Young Serif",
}


def font_stack(name: str, display: bool = False) -> str:
    if name in SERIF_FONTS:
        return f'"{name}", Georgia, "Times New Roman", serif'
    if name == "Anton":
        return f'"{name}", Impact, "Arial Narrow Bold", sans-serif'
    return f'"{name}", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'


def derived_colors(theme: Theme) -> dict:
    """Secondary tokens computed from the theme so every pair stays legible."""
    c = theme.colors
    dark = theme.mode == "dark"
    accent_text = _ensure_contrast(c["accent"], c["bg"], 4.5, c["ink"])
    hover = mix(c["accent"], "#FFFFFF" if dark else "#000000", 0.12)
    if contrast(c["accent_ink"], hover) < 4.5:
        hover = c["accent"]
    r, g, b = (round(v * 255) for v in _rgb(c["bg"]))
    return {
        "accent_text": accent_text,
        "accent_hover": hover,
        "line_strong": mix(c["line"], c["ink"], 0.35),
        "glass": f"rgba({r}, {g}, {b}, 0.86)",
        "shade": "rgba(8, 8, 10, 0.72)" if not dark else "rgba(0, 0, 0, 0.74)",
        "accent2": c.get("accent2", mix(c["accent"], c["ink"], 0.4)),
    }


def build_base_css(theme: Theme) -> str:
    c = theme.colors
    d = derived_colors(theme)
    space = "\n".join(f"  --k-space-{i}: {i * 0.5:g}rem;" for i in range(1, 13))
    rule_css = (
        ".k-section + .k-section { border-top: 1px solid var(--k-line); }\n"
        ".k-section--tint + .k-section, .k-section + .k-section--tint { border-top-color: transparent; }\n"
    ) if theme.rule else ""
    return f"""/* {theme.name} — kit art direction. Tokens first; every component reads them. */
:root {{
  color-scheme: {theme.mode};
  --k-bg: {c['bg']};
  --k-surface: {c['surface']};
  --k-surface-2: {c['surface2']};
  --k-ink: {c['ink']};
  --k-muted: {c['muted']};
  --k-line: {c['line']};
  --k-line-strong: {d['line_strong']};
  --k-accent: {c['accent']};
  --k-accent-ink: {c['accent_ink']};
  --k-accent-soft: {c['accent_soft']};
  --k-accent-text: {d['accent_text']};
  --k-accent-hover: {d['accent_hover']};
  --k-accent-2: {d['accent2']};
  --k-glass: {d['glass']};
  --k-shade: {d['shade']};
  --k-font-display: {font_stack(theme.display_font, True)};
  --k-font-body: {font_stack(theme.body_font)};
  --k-display-weight: {theme.display_weight};
  --k-display-tracking: {theme.display_tracking};
  --k-display-line: {theme.display_line};
  --k-display-case: {theme.heading_case};
  --k-body-size: {theme.body_size};
  --k-radius: {theme.radius};
  --k-radius-btn: {theme.button_radius};
  --k-density: {theme.density};
  --k-gutter: clamp(20px, 5vw, 64px);
  --k-max: 1240px;
  --k-header-h: 72px;
  --k-ease: cubic-bezier(0.22, 1, 0.36, 1);
  --k-ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --k-tap: 44px;
{space}
  /* Compatibility aliases for edit turns written against the legacy token names. */
  --bg-color: var(--k-bg);
  --text-color: var(--k-ink);
  --font-body: var(--k-font-body);
  --font-heading: var(--k-font-display);
  --color-primary: var(--k-accent);
  --color-accent: var(--k-accent);
  --on-accent: var(--k-accent-ink);
}}

*, *::before, *::after {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; text-size-adjust: 100%; scroll-padding-top: 88px; scroll-behavior: smooth; }}
body {{
  margin: 0;
  background-color: var(--k-bg);
  color: var(--k-ink);
  font-family: var(--k-font-body);
  font-size: var(--k-body-size);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}}
h1, h2, h3, h4, p, figure, blockquote, dl, dd {{ margin: 0; }}
ul[class], ol[class] {{ list-style: none; margin: 0; padding: 0; }}
img, svg, video, canvas {{ display: block; max-width: 100%; }}
button, input, textarea, select {{ font: inherit; color: inherit; }}
button {{ cursor: pointer; }}
a {{ color: inherit; }}
:focus-visible {{ outline: 2px solid var(--k-accent-text); outline-offset: 3px; }}
::selection {{ background-color: var(--k-accent); color: var(--k-accent-ink); }}

.site-root {{ display: flex; flex-direction: column; min-height: 100vh; }}
#site-main {{ display: block; flex: 1 0 auto; }}
#site-main:focus {{ outline: none; }}
.site-skip-link {{
  position: fixed; top: -120px; left: 16px; z-index: 100;
  padding: 12px 18px; border-radius: var(--k-radius-btn);
  background-color: var(--k-ink); color: var(--k-bg); font-weight: 600; text-decoration: none;
}}
.site-skip-link:focus {{ top: 12px; }}
.site-visually-hidden, .k-sr {{
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}}

/* Layout and type primitives */
.k-container {{ width: 100%; max-width: calc(var(--k-max) + 2 * var(--k-gutter)); margin-inline: auto; padding-inline: var(--k-gutter); }}
.k-section {{ position: relative; padding-block: var(--k-density); background-color: var(--k-bg); }}
.k-section--tint {{ background-color: var(--k-surface); }}
{rule_css}.k-eyebrow {{ font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--k-muted); }}
.k-display {{
  font-family: var(--k-font-display); font-weight: var(--k-display-weight);
  font-size: clamp(2.6rem, 6.4vw, 5.6rem); line-height: var(--k-display-line);
  letter-spacing: var(--k-display-tracking); text-transform: var(--k-display-case); text-wrap: balance;
}}
.k-h2 {{
  font-family: var(--k-font-display); font-weight: var(--k-display-weight);
  font-size: clamp(2rem, 4.2vw, 3.4rem); line-height: 1.06;
  letter-spacing: var(--k-display-tracking); text-transform: var(--k-display-case); text-wrap: balance;
}}
.k-h3 {{ font-family: var(--k-font-display); font-weight: var(--k-display-weight); font-size: clamp(1.25rem, 1.7vw, 1.5rem); line-height: 1.2; letter-spacing: -0.01em; text-wrap: balance; }}
.k-lede {{ font-size: clamp(1.125rem, 1.6vw, 1.3125rem); line-height: 1.5; max-width: 38ch; color: var(--k-muted); }}
.k-text {{ max-width: 65ch; }}
.k-muted {{ color: var(--k-muted); }}
.k-head {{ display: grid; gap: var(--k-space-3); max-width: 760px; margin-bottom: clamp(40px, 6vw, 72px); }}
.k-head--split {{ max-width: none; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); align-items: end; column-gap: var(--k-space-8); }}
@media (max-width: 860px) {{ .k-head--split {{ grid-template-columns: minmax(0, 1fr); }} }}

.k-btn {{
  display: inline-flex; align-items: center; justify-content: center; gap: 0.5em;
  min-height: 48px; padding: 0 1.5rem; border: 1px solid transparent; border-radius: var(--k-radius-btn);
  font-weight: 600; font-size: 1rem; line-height: 1.1; text-decoration: none; white-space: nowrap;
  transition: transform 180ms var(--k-ease), background-color 180ms ease, color 180ms ease, border-color 180ms ease;
}}
.k-btn--primary {{ background-color: var(--k-accent); color: var(--k-accent-ink); }}
.k-btn--primary:hover, .k-btn--primary:focus-visible {{ background-color: var(--k-accent-hover); transform: translateY(-2px); }}
.k-btn--ghost {{ background-color: transparent; color: var(--k-ink); border-color: var(--k-line-strong); }}
.k-btn--ghost:hover, .k-btn--ghost:focus-visible {{ border-color: var(--k-ink); transform: translateY(-2px); }}
.k-btn:active {{ transform: scale(0.98); }}
.k-btn[disabled], .k-btn[aria-busy="true"] {{ opacity: 0.62; cursor: progress; transform: none; }}
.k-actions {{ display: flex; flex-wrap: wrap; gap: var(--k-space-2); }}
.k-link {{ color: var(--k-accent-text); text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 0.22em; transition: text-decoration-thickness 150ms ease; }}
.k-link:hover, .k-link:focus-visible {{ text-decoration-thickness: 2px; }}

/* Media: an art panel sits behind every image, so a failed photo still looks designed. */
.k-media {{ position: relative; overflow: hidden; border-radius: var(--k-radius); isolation: isolate; }}
.k-art {{
  background-color: var(--k-surface-2);
  background-image:
    radial-gradient(120% 90% at 18% 12%, var(--k-accent-soft) 0%, transparent 58%),
    radial-gradient(90% 80% at 88% 92%, var(--k-surface) 0%, transparent 62%),
    linear-gradient(160deg, var(--k-surface-2), var(--k-surface));
}}
.k-art[data-variant="2"] {{
  background-image:
    radial-gradient(80% 70% at 82% 18%, var(--k-accent-soft) 0%, transparent 60%),
    linear-gradient(200deg, var(--k-surface), var(--k-surface-2) 70%);
}}
.k-art[data-variant="3"] {{
  background-image:
    radial-gradient(70% 60% at 30% 80%, var(--k-accent-soft) 0%, transparent 64%),
    radial-gradient(60% 50% at 75% 20%, var(--k-surface) 0%, transparent 70%),
    linear-gradient(120deg, var(--k-surface-2), var(--k-surface-2));
}}
.k-art__mark {{
  position: absolute; right: 6%; bottom: -0.12em; z-index: 0;
  font-family: var(--k-font-display); font-size: clamp(7rem, 22vw, 18rem); line-height: 1;
  color: var(--k-accent); opacity: 0.16; pointer-events: none; user-select: none;
}}
.k-media img {{ position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; object-fit: cover; }}
.k-media img.is-missing {{ display: none; }}

/* Motion: compositor-only, once, and fully static under reduced motion. */
[data-motion="scroll-reveal"] {{ opacity: 0; transform: translateY(20px); transition: opacity 600ms var(--k-ease), transform 600ms var(--k-ease); }}
[data-motion="scroll-reveal"].is-visible {{ opacity: 1; transform: none; }}
.k-stagger > :nth-child(2) {{ transition-delay: 70ms; }}
.k-stagger > :nth-child(3) {{ transition-delay: 140ms; }}
.k-stagger > :nth-child(4) {{ transition-delay: 210ms; }}
.k-stagger > :nth-child(5) {{ transition-delay: 280ms; }}
.k-stagger > :nth-child(n + 6) {{ transition-delay: 350ms; }}
@keyframes k-rise {{ from {{ opacity: 0; transform: translateY(24px); }} to {{ opacity: 1; transform: none; }} }}
[data-motion="text-in"] {{ animation: k-rise 900ms var(--k-ease-out) both; }}
.k-rise-2 {{ animation: k-rise 900ms var(--k-ease-out) 120ms both; }}
.k-rise-3 {{ animation: k-rise 900ms var(--k-ease-out) 240ms both; }}
.k-tilt {{ position: relative; transform: perspective(1000px) rotateX(var(--k-rx, 0deg)) rotateY(var(--k-ry, 0deg)); transition: transform 220ms var(--k-ease); }}
.k-tilt::after {{
  content: ""; position: absolute; inset: 0; z-index: 2; border-radius: inherit; pointer-events: none;
  background: radial-gradient(420px circle at var(--k-mx, 50%) var(--k-my, 50%), rgba(255, 255, 255, var(--k-glow, 0)), transparent 62%);
  transition: opacity 220ms ease;
}}
@keyframes k-settle {{ from {{ transform: scale(1.08); }} to {{ transform: scale(1); }} }}
@keyframes k-drift-slow {{ from {{ transform: translate3d(0, 0, 0); }} to {{ transform: translate3d(0, 9vh, 0); }} }}
@keyframes k-drift-fast {{ from {{ transform: translate3d(0, 0, 0); }} to {{ transform: translate3d(0, -6vh, 0); }} }}
@supports (animation-timeline: view()) {{
  @media (prefers-reduced-motion: no-preference) {{
    .k-settle img {{ animation: k-settle linear both; animation-timeline: view(); animation-range: entry 0% cover 35%; }}
  }}
}}
@supports (animation-timeline: scroll()) {{
  @media (hover: hover) and (min-width: 900px) and (prefers-reduced-motion: no-preference) {{
    .k-depth-slow {{ animation: k-drift-slow linear both; animation-timeline: scroll(root); animation-range: 0 100vh; }}
    .k-depth-fast {{ animation: k-drift-fast linear both; animation-timeline: scroll(root); animation-range: 0 100vh; }}
  }}
}}
::view-transition-old(k-menu-panel), ::view-transition-new(k-menu-panel) {{ animation-duration: 260ms; animation-timing-function: var(--k-ease); }}

@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto !important; }}
  *, *::before, *::after {{ animation-duration: 1ms !important; animation-iteration-count: 1 !important; transition-duration: 1ms !important; scroll-behavior: auto !important; }}
  [data-motion], .k-rise-2, .k-rise-3 {{ opacity: 1 !important; transform: none !important; animation: none !important; transition: none !important; }}
  .k-tilt {{ transform: none !important; }}
  .k-tilt::after {{ display: none; }}
  .k-depth-slow, .k-depth-fast, .k-settle img {{ animation: none !important; transform: none !important; }}
}}
"""
