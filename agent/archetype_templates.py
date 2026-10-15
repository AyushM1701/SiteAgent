"""
archetype_templates.py - Production Component Templates for Design Archetypes

Provides reusable, token-compliant React (TypeScript) and CSS component generators
for the core layout archetypes:
  1. Bento Grid (heterogeneous CSS Grid spans: 2x2 hero, 1x2 metric, 1x1 cards)
  2. Editorial Magazine (high-contrast serif headlines, asymmetric pull-quotes, multi-column prose)
  3. Tabs / Carousel Pattern (generalized interactive pattern: category tab filter & quote carousel)
  4. Split-Screen Hero (50/50 split with brand typography & interactive widget/terminal)
  5. Asymmetric Card Decks (staggered cards with sticky headers & interactive accordion panels)

Each renderer returns a tuple: (tsx_code: str, css_code: str).
"""

from typing import List, Dict, Any, Optional, Tuple
import json


def _sanitize_name(name: str) -> str:
    """Sanitizes a name into PascalCase for React component names."""
    clean = "".join(w.capitalize() for w in name.replace("-", "_").split("_") if w)
    return clean or "Component"


def _sanitize_prefix(prefix: str) -> str:
    """Sanitizes prefix for CSS BEM class names."""
    clean = "".join(c for c in prefix.lower() if c.isalnum() or c == "-")
    return clean or "site"


# ==============================================================================
# 1. Bento Grid Archetype Template
# ==============================================================================

def render_bento_grid(
    component_name: str,
    items: List[Dict[str, Any]],
    business_name: str = "Acme Platform",
    eyebrow: str = "",
    title: str = "",
    subtitle: str = "",
    prefix: str = "bento",
    primary_color: str = "#090d16",
    accent_color: str = "#38bdf8",
    accent_secondary: str = "#818cf8",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "12px",
    pill_buttons: bool = False,
) -> Tuple[str, str]:
    """
    Renders a Bento Grid component with heterogeneous CSS Grid spans:
    - Card 0: 2x2 Hero Featured card with status indicator and interactive code/preview
    - Card 1: 1x2 Tall Metric card with prominent stat and progress meter
    - Cards 2+: 1x1 Modular feature cards with tag, title, and action link
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = "var(--radius-buttons, 75px)" if pill_buttons else f"var(--radius-buttons, {border_radius})"
    radius_card = "var(--radius-cards, 0px)" if pill_buttons else f"var(--radius-cards, {border_radius})"

    # Render the supplied cardinality, including zero and more than four items.
    # JSON serialization keeps quotes, braces and newlines out of JSX syntax.
    sample_items = json.dumps([
        {"id": str(i), **{key: str(item.get(key) or "")
                           for key in ("title", "desc", "tag", "badge", "metric", "image")}}
        for i, item in enumerate(items)
    ], ensure_ascii=True)

    tsx = f"""import React from 'react';
import './{pascal}.css';

interface BentoItem {{
  id: string;
  title: string;
  desc: string;
  tag: string;
  badge?: string;
  metric?: string;
  image?: string;
}}

const BENTO_ITEMS: BentoItem[] = {sample_items};

export function {pascal}() {{
  return (
    <section className="{p}-bento" id="{pascal.lower()}" aria-labelledby="{p}-bento-title">
      <div className="{p}-bento__inner">
        <div className="{p}-bento__header">
          <span className="{p}-bento__eyebrow">{{{json.dumps(eyebrow)}}}</span>
          <h2 id="{p}-bento-title" className="{p}-bento__title">
            {{{json.dumps(title or business_name)}}}
          </h2>
          <p className="{p}-bento__subtitle">
            {{{json.dumps(subtitle)}}}
          </p>
        </div>

        <div className="{p}-bento__grid">
          {{BENTO_ITEMS.map((item, index) => (
            <article key={{item.id}} className={{`{p}-bento__card {p}-bento__card--${{index === 0 ? 'hero' : index === 1 ? 'metric' : 'standard'}}`}}>
              {{item.tag && <span className="{p}-bento__tag">{{item.tag}}</span>}}
              {{item.badge && <span className="{p}-bento__badge">{{item.badge}}</span>}}
              {{item.image && <div className="{p}-bento__img-wrap">
                <img src={{item.image}} alt={{item.title}} width="1200" height="800" loading="lazy" className="{p}-bento__card-img" />
              </div>}}
              {{item.metric && <span className="{p}-bento__metric-val">{{item.metric}}</span>}}
              <h3 className="{p}-bento__card-title">{{item.title}}</h3>
              {{item.desc && <p className="{p}-bento__card-desc">{{item.desc}}</p>}}
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""

    css = f""".{p}-bento {{
  position: relative;
  width: 100%;
  padding: 6rem 1.5rem;
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, {primary_color})));
  color: var(--color-paper, var(--text-color, #ffffff));
}}

.{p}-bento__inner {{
  max-width: var(--page-max-width, 1180px);
  margin: 0 auto;
}}

.{p}-bento__header {{
  text-align: center;
  max-width: 680px;
  margin: 0 auto 3.5rem;
}}

.{p}-bento__eyebrow {{
  display: inline-block;
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  margin-bottom: 0.75rem;
}}

.{p}-bento__title {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: clamp(2rem, 4vw, 2.75rem);
  font-weight: 800;
  color: var(--color-paper, var(--text-color, #ffffff));
  letter-spacing: -0.025em;
  line-height: 1.2;
  margin-bottom: 1rem;
}}

.{p}-bento__subtitle {{
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 1.05rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.7));
  line-height: 1.6;
}}

.{p}-bento__grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(210px, auto);
  gap: 1.5rem;
}}

.{p}-bento__card {{
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid {accent_color}30;
  border-radius: {radius_card};
  padding: var(--card-padding, 2rem);
  display: flex;
  flex-direction: column;
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
  overflow: hidden;
}}

.{p}-bento__card:hover {{
  transform: translateY(-4px);
  border-color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.45);
}}

/* Heterogeneous CSS Grid Spans */
.{p}-bento__card--hero {{
  grid-column: span 2;
  grid-row: span 2;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
}}

.{p}-bento__card--metric {{
  grid-column: span 1;
  grid-row: span 2;
  justify-content: space-between;
}}

.{p}-bento__card--standard {{
  grid-column: span 1;
  grid-row: span 1;
}}

.{p}-bento__card-top {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}}

.{p}-bento__badge {{
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 0.25rem 0.65rem;
  background: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  color: var(--color-paper, #ffffff);
  border-radius: {radius_btn};
}}

.{p}-bento__tag {{
  font-size: 0.78rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.6));
  font-family: monospace;
}}

.{p}-bento__card-title {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
  margin-bottom: 0.75rem;
}}

.{p}-bento__card-title--hero {{
  font-size: 1.65rem;
}}

.{p}-bento__card-desc {{
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 0.9375rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.7));
  line-height: 1.6;
  margin: 0 0 1.25rem;
}}

.{p}-bento__metric-wrap {{
  margin: 1.5rem 0;
}}

.{p}-bento__metric-val {{
  display: block;
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 3rem;
  font-weight: 800;
  color: var(--color-paper, #ffffff);
  line-height: 1;
  margin-bottom: 0.35rem;
}}

.{p}-bento__metric-label {{
  font-size: 0.8125rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.55));
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.{p}-bento__bar-meter {{
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 1rem;
}}

.{p}-bento__bar-fill {{
  height: 100%;
  background: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  border-radius: 999px;
}}

.{p}-bento__hero-visual {{
  margin-top: auto;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-bento__pill-track {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.75rem;
  background: {accent_color}15;
  border: 1px solid {accent_color}30;
  border-radius: var(--radius-buttons, 16px);
  font-size: 0.75rem;
  color: var(--color-paper, #ffffff);
  margin-bottom: 0.75rem;
}}

.{p}-bento__status-dot {{
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
}}

.{p}-bento__hero-code {{
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid {accent_color}25;
  border-radius: {radius_card};
  padding: 0.85rem 1rem;
  font-family: monospace;
  font-size: 0.8125rem;
  color: var(--color-ash-mist, #94a3b8);
  white-space: pre-wrap;
}}

.{p}-bento__card-action {{
  margin-top: auto;
}}

.{p}-bento__link {{
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s ease;
}}

.{p}-bento__link:hover {{
  opacity: 0.85;
}}

@media (max-width: 900px) {{
  .{p}-bento__grid {{
    grid-template-columns: 1fr;
  }}
  .{p}-bento__card--hero,
  .{p}-bento__card--metric,
  .{p}-bento__card--standard {{
    grid-column: span 1;
    grid-row: auto;
  }}
}}

.{p}-bento__card {{
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease;
}}
.{p}-bento__card:hover {{
  transform: translateY(-4px);
  border-color: {accent_color};
  box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.4);
}}

/* Bento Image Entrance: span-weighted stagger matching parent card + smooth hover zoom */
.{p}-bento__img-wrap {{
  width: 100%;
  height: 160px;
  border-radius: {radius_card};
  overflow: hidden;
  margin-bottom: 1rem;
}}
.{p}-bento__card-img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transform: scale(1.03);
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  display: block;
}}
.{p}-bento__card--hero .{p}-bento__card-img {{
  animation: {p}BentoImageEnter 0.55s ease 0ms forwards;
}}
.{p}-bento__card--metric .{p}-bento__card-img {{
  animation: {p}BentoImageEnter 0.55s ease 100ms forwards;
}}
.{p}-bento__card--standard .{p}-bento__card-img {{
  animation: {p}BentoImageEnter 0.55s ease 200ms forwards;
}}
@keyframes {p}BentoImageEnter {{
  to {{ opacity: 1; transform: scale(1); }}
}}
.{p}-bento__card:hover .{p}-bento__card-img {{
  transform: scale(1.04);
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-bento__card,
  .{p}-bento__card:hover,
  .{p}-bento__link,
  .{p}-bento__card-img,
  .{p}-bento__card:hover .{p}-bento__card-img {{
    transform: none !important;
    transition: none !important;
    animation: none !important;
    box-shadow: none !important;
    opacity: 1 !important;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 2. Editorial Magazine Archetype Template
# ==============================================================================

def render_editorial_layout(
    component_name: str,
    items: List[Dict[str, Any]],
    business_name: str = "Atelier Monograph",
    volume_tag: str = "EDITORIAL DISPATCH · VOL. 04",
    title: str = "Form, Space, and Typographic Discipline",
    pull_quote: str = "A typeface is not merely a vehicle for text; it is an architectural foundation governing the cadence of human comprehension across digital substrates.",
    quote_author: str = "Hélène Mercier, Director of Typographic Research",
    prose_paragraphs: Optional[List[str]] = None,
    prefix: str = "edit",
    primary_color: str = "#000000",
    accent_color: str = "#a02d25",
    accent_secondary: str = "#c9392f",
    font_heading: str = "Raleway",
    font_body: str = "Roobert",
    border_radius: str = "0px",
    pill_buttons: bool = True,
) -> Tuple[str, str]:
    """
    Renders an Editorial Magazine component:
    - High-contrast serif headlines
    - Asymmetric pull-quote with decorative typography
    - Multi-column narrative prose with drop-cap styling
    - Curated monograph/chapter cards with understated dividers
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = "var(--radius-buttons, 75px)" if pill_buttons else f"var(--radius-buttons, {border_radius})"
    radius_card = "var(--radius-cards, 0px)" if pill_buttons else f"var(--radius-cards, {border_radius})"

    prose = prose_paragraphs or [
        "Modernist typography emerged not as an aesthetic novelty, but as a severe response to industrial density. By distilling letterforms down to their elemental vertical metrics and geometric terminals, screen systems attain a degree of legibility unattainable through traditional decorative serif paradigms.",
        "In our contemporary landscape of high-density retina displays, spatial restraint has become the ultimate luxury. Every whitespace aperture, ink-trap carving, and line-height interval is calibrated to preserve cognitive calm amid relentless informational velocity."
    ]

    roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    sample_chapters = []
    for idx, item in enumerate(items):
        sample_chapters.append({
            "num": roman_numerals[idx % len(roman_numerals)],
            "title": item.get("title", f"Monograph {idx+1}"),
            "tag": item.get("tag", "Monograph"),
            "desc": item.get("desc", "Specialized treatise and critical research monograph."),
            "image": item.get("image", ""),
        })
    if not sample_chapters:
        sample_chapters = [
            {"num": "I", "title": "Variable Glyph Engineering", "tag": "Monograph", "desc": "Continuous interpolation along optical size and weight axes.", "image": ""},
            {"num": "II", "title": "The Geometry of Silence", "tag": "Critical Essay", "desc": "Analyzing negative space and architectural cadence.", "image": ""},
            {"num": "III", "title": "Subterranean Form", "tag": "Exhibition", "desc": "A photographic study of monolithic stone structures.", "image": ""},
        ]

    tsx = f"""import React from 'react';
import './{pascal}.css';

interface Chapter {{
  num: string;
  title: string;
  tag: string;
  desc: string;
  image?: string;
}}

const CHAPTERS: Chapter[] = {sample_chapters};

export function {pascal}() {{
  return (
    <section className="{p}-editorial" id="{pascal.lower()}" aria-labelledby="{p}-editorial-title">
      <div className="{p}-editorial__inner">
        {{/* 1. Masthead / Issue Header */}}
        <header className="{p}-editorial__masthead">
          <span className="{p}-editorial__volume">{volume_tag}</span>
          <span className="{p}-editorial__date">{{new Date().toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }})}}</span>
        </header>

        <hr className="{p}-editorial__rule" />

        {{/* 2. Headline & Asymmetric Pull-Quote */}}
        <div className="{p}-editorial__lead">
          <h2 id="{p}-editorial-title" className="{p}-editorial__headline">
            {title}
          </h2>

          <blockquote className="{p}-editorial__pullquote">
            <span className="{p}-editorial__quote-mark" aria-hidden="true">&ldquo;</span>
            <p className="{p}-editorial__quote-text">
              {pull_quote}
            </p>
            <cite className="{p}-editorial__quote-author">&mdash; {quote_author}</cite>
          </blockquote>
        </div>

        {{/* 3. Multi-Column Narrative Prose */}}
        <div className="{p}-editorial__prose">
          <p className="{p}-editorial__paragraph {p}-editorial__paragraph--dropcap">
            {prose[0]}
          </p>
          <p className="{p}-editorial__paragraph">
            {prose[1] if len(prose) > 1 else prose[0]}
          </p>
        </div>

        <hr className="{p}-editorial__rule" />

        {{/* 4. Curated Monograph Chapters */}}
        <div className="{p}-editorial__chapters">
          <div className="{p}-editorial__chapters-header">
            <span className="{p}-editorial__chapters-tag">CURATED FOLIO</span>
            <h3 className="{p}-editorial__chapters-title">Selected Monographs & Treatises</h3>
          </div>

          <div className="{p}-editorial__chapters-grid">
            {{CHAPTERS.map((ch) => (
              <article key={{ch.num}} className="{p}-editorial__chapter-card">
                <div className="{p}-editorial__chapter-top">
                  <span className="{p}-editorial__chapter-num">{{ch.num}}</span>
                  <span className="{p}-editorial__chapter-tag">{{ch.tag}}</span>
                </div>
                {{ch.image && (
                  <div className="{p}-editorial__img-wrap">
                    <img src={{ch.image}} alt={{ch.title}} className="{p}-editorial__card-img" />
                  </div>
                )}}
                <h4 className="{p}-editorial__chapter-title">{{ch.title}}</h4>
                <p className="{p}-editorial__chapter-desc">{{ch.desc}}</p>
                <a href="#contact" className="{p}-editorial__chapter-link">
                  Read Monograph &rarr;
                </a>
              </article>
            ))}}
          </div>
        </div>
      </div>
    </section>
  );
}}
"""

    css = f""".{p}-editorial {{
  width: 100%;
  padding: 6rem 1.5rem;
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, {primary_color})));
  color: var(--color-paper, var(--text-color, #ffffff));
}}

.{p}-editorial__inner {{
  max-width: var(--page-max-width, 1080px);
  margin: 0 auto;
}}

.{p}-editorial__masthead {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: monospace;
  font-size: 0.8125rem;
  letter-spacing: 0.1em;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.6));
  padding-bottom: 0.75rem;
}}

.{p}-editorial__rule {{
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  margin: 0 0 3.5rem;
}}

.{p}-editorial__lead {{
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 3.5rem;
  align-items: flex-start;
  margin-bottom: 3.5rem;
}}

.{p}-editorial__headline {{
  font-family: var(--font-heading, '{font_heading}', serif);
  font-size: clamp(2.4rem, 4.5vw, 3.75rem);
  font-weight: 800;
  color: var(--color-paper, var(--text-color, #ffffff));
  line-height: 1.1;
  letter-spacing: -0.03em;
  margin: 0;
}}

.{p}-editorial__pullquote {{
  position: relative;
  margin: 0;
  padding: 1.5rem 0 1.5rem 2rem;
  border-left: 2px solid var(--color-iridescent-fade, var(--accent-color, {accent_color}));
}}

.{p}-editorial__quote-mark {{
  position: absolute;
  top: -1.2rem;
  left: 1.5rem;
  font-family: var(--font-heading, serif);
  font-size: 4rem;
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  opacity: 0.35;
  line-height: 1;
}}

.{p}-editorial__quote-text {{
  font-family: var(--font-heading, '{font_heading}', serif);
  font-style: italic;
  font-size: 1.25rem;
  color: var(--color-paper, #ffffff);
  line-height: 1.6;
  margin: 0 0 1rem;
}}

.{p}-editorial__quote-author {{
  display: block;
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 0.8125rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.6));
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}

/* Multi-Column Prose */
.{p}-editorial__prose {{
  column-count: 2;
  column-gap: 3.5rem;
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.78));
  margin-bottom: 4rem;
  text-align: justify;
}}

.{p}-editorial__paragraph {{
  margin: 0 0 1.5rem;
}}

.{p}-editorial__paragraph--dropcap::first-letter {{
  float: left;
  font-family: var(--font-heading, '{font_heading}', serif);
  font-size: 3.8rem;
  line-height: 0.8;
  padding-right: 0.75rem;
  padding-top: 0.25rem;
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  font-weight: 700;
}}

/* Chapters List */
.{p}-editorial__chapters {{
  margin-top: 2rem;
}}

.{p}-editorial__chapters-header {{
  margin-bottom: 2rem;
}}

.{p}-editorial__chapters-tag {{
  display: inline-block;
  font-family: monospace;
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  margin-bottom: 0.5rem;
}}

.{p}-editorial__chapters-title {{
  font-family: var(--font-heading, '{font_heading}', serif);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
  margin: 0;
}}

.{p}-editorial__chapters-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
}}

.{p}-editorial__chapter-card {{
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid {accent_color}30;
  border-radius: {radius_card};
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s ease, transform 0.2s ease;
}}

.{p}-editorial__chapter-card:hover {{
  border-color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  transform: translateY(-3px);
}}

.{p}-editorial__chapter-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}}

.{p}-editorial__chapter-num {{
  font-family: var(--font-heading, '{font_heading}', serif);
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
}}

.{p}-editorial__chapter-tag {{
  font-size: 0.72rem;
  padding: 0.2rem 0.55rem;
  background: {accent_color}18;
  border: 1px solid {accent_color}35;
  border-radius: {radius_btn};
  color: var(--color-paper, #ffffff);
}}

.{p}-editorial__chapter-title {{
  font-family: var(--font-heading, '{font_heading}', serif);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
  margin: 0 0 0.75rem;
}}

.{p}-editorial__chapter-desc {{
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 0.875rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.65));
  line-height: 1.6;
  margin: 0 0 1.25rem;
  flex: 1;
}}

.{p}-editorial__chapter-link {{
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
}}

@media (max-width: 860px) {{
  .{p}-editorial__lead {{
    grid-template-columns: 1fr;
    gap: 2rem;
  }}
  .{p}-editorial__prose {{
    column-count: 1;
  }}
  .{p}-editorial__chapters-grid {{
    grid-template-columns: 1fr;
  }}
}}

.{p}-editorial__lead,
.{p}-editorial__prose,
.{p}-editorial__chapter-card {{
  opacity: 1;
  animation: {p}EditorialFade 0.65s ease-out;
}}

@keyframes {p}EditorialFade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}

/* Editorial Image Entrance: quiet, slow 0.85s ease-out fade-only reveal with zero lift/translation */
.{p}-editorial__img-wrap {{
  width: 100%;
  height: 180px;
  overflow: hidden;
  border-radius: {radius_card};
  margin-bottom: 1.25rem;
}}

.{p}-editorial__card-img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  display: block;
  animation: {p}EditorialImageFade 0.85s ease-out 100ms forwards;
}}

@keyframes {p}EditorialImageFade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-editorial__lead,
  .{p}-editorial__prose,
  .{p}-editorial__chapter-card,
  .{p}-editorial__chapter-card:hover,
  .{p}-editorial__chapter-link,
  .{p}-editorial__card-img {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 3. Tabs / Carousel Pattern Archetype Template
# ==============================================================================

def render_tabs_carousel(
    component_name: str,
    categories: Optional[List[str]] = None,
    items: Optional[List[Dict[str, Any]]] = None,
    reviews: Optional[List[Dict[str, Any]]] = None,
    business_name: str = "FlowSync Architecture",
    eyebrow: str = "PRODUCTION TELEMETRY",
    title: str = "Interactive Architecture & Live Case Studies",
    subtitle: str = "Switch between architectural tiers or paginate through verified production outcomes.",
    prefix: str = "tc",
    primary_color: str = "#090d16",
    accent_color: str = "#38bdf8",
    accent_secondary: str = "#6366f1",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "12px",
    pill_buttons: bool = False,
) -> Tuple[str, str]:
    """
    Renders an Interactive Tabs & Carousel component:
    - Tab switcher for category filtering with React useState
    - Grid view responding dynamically to the active tab
    - Testimonial / Showcase Carousel with prev/next controls, counter, and pagination
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = "var(--radius-buttons, 75px)" if pill_buttons else f"var(--radius-buttons, {border_radius})"
    radius_card = "var(--radius-cards, 0px)" if pill_buttons else f"var(--radius-cards, {border_radius})"

    cats = categories or ["all", "core", "security", "scale"]
    cat_labels = {
        "all": "All Capabilities",
        "core": "Core Engine",
        "security": "Security & Auth",
        "scale": "Scale & Telemetry"
    }

    sample_items = []
    if items:
        for idx, item in enumerate(items):
            sample_items.append({
                "id": str(item.get("id", idx + 1)),
                "category": item.get("category", "core"),
                "title": item.get("title", f"Capability {idx + 1}"),
                "desc": item.get("desc", "Verified production capability and architecture."),
                "badge": item.get("badge", "Active"),
                "image": item.get("image", ""),
            })
    else:
        sample_items = [
            {"id": "1", "category": "core", "title": "Autonomous Pipeline Engine", "desc": "Execute multi-turn agent loops with real-time streaming observations and live compiler feedback.", "badge": "Streaming", "image": ""},
            {"id": "2", "category": "core", "title": "Adaptive Adapter Switching", "desc": "Select task-specific LoRA weights on the fly based on contextual requirements.", "badge": "QLoRA", "image": ""},
            {"id": "3", "category": "security", "title": "Enterprise Sandboxing", "desc": "Containerized execution environments isolate untrusted generated code safely.", "badge": "SOC-2", "image": ""},
            {"id": "4", "category": "security", "title": "Cryptographic Ticket Auth", "desc": "Single-use HMAC-SHA256 authenticated tokens prevent cross-site hijack vulnerabilities.", "badge": "CSWSH Guard", "image": ""},
            {"id": "5", "category": "scale", "title": "Predictive Flamegraphs", "desc": "Full-depth latency tracing, memory allocation profiling, and automatic bottleneck identification.", "badge": "Telemetry", "image": ""},
            {"id": "6", "category": "scale", "title": "Deterministic STaR Harvest", "desc": "Automated rejection sampling loops harvest passing verified episodes directly to training sets.", "badge": "Self-Taught", "image": ""},
        ]

    sample_reviews = reviews or [
        {
            "id": "1",
            "quote": "Reduced our deployment triage time by 80%. Our engineering team moved from manual debugging to continuous delivery overnight.",
            "author": "Dr. Sarah Lin",
            "role": "VP of Engineering at CloudScale",
            "rating": 5,
        },
        {
            "id": "2",
            "quote": "The cleanest multi-step execution pipeline we have ever deployed. Our compilation pass rates skyrocketed to 99% within the first month.",
            "author": "Marcus Vance",
            "role": "Lead Architect at ScaleBase",
            "rating": 5,
        },
        {
            "id": "3",
            "quote": "Autonomous error correction and live test feedback transformed our product sprints. It feels like having a staff engineer on call 24/7.",
            "author": "Elena Rostova",
            "role": "Staff Product Director",
            "rating": 5,
        },
    ]

    tsx = f"""import React, {{ useState }} from 'react';
import './{pascal}.css';

interface Feature {{
  id: string;
  category: string;
  title: string;
  desc: string;
  badge: string;
  image?: string;
}}

interface Review {{
  id: string;
  quote: string;
  author: string;
  role: string;
  rating: number;
}}

const FEATURES: Feature[] = {sample_items};
const REVIEWS: Review[] = {sample_reviews};
const CATEGORIES: {{ id: string; label: string }}[] = {[{"id": c, "label": cat_labels.get(c, c.capitalize())} for c in cats]};

export function {pascal}() {{
  const [activeTab, setActiveTab] = useState<string>('all');
  const [activeSlide, setActiveSlide] = useState<number>(0);

  const filteredFeatures = activeTab === 'all'
    ? FEATURES
    : FEATURES.filter((f) => f.category === activeTab);

  const prevSlide = () => {{
    setActiveSlide((prev) => (prev - 1 + REVIEWS.length) % REVIEWS.length);
  }};

  const nextSlide = () => {{
    setActiveSlide((prev) => (prev + 1) % REVIEWS.length);
  }};

  const currentReview = REVIEWS[activeSlide];

  return (
    <section className="{p}-tabs" id="{pascal.lower()}" aria-labelledby="{p}-tabs-title">
      <div className="{p}-tabs__inner">
        {{/* 1. Header & Tab Navigation */}}
        <div className="{p}-tabs__header">
          <p className="{p}-tabs__eyebrow">{eyebrow}</p>
          <h2 id="{p}-tabs-title" className="{p}-tabs__title">
            {title}
          </h2>
          <p className="{p}-tabs__subtitle">
            {subtitle}
          </p>

          <div className="{p}-tabs__nav" role="tablist" aria-label="Feature categories">
            {{CATEGORIES.map((cat) => (
              <button
                key={{cat.id}}
                type="button"
                role="tab"
                aria-selected={{activeTab === cat.id}}
                className={{`{p}-tabs__tab${{activeTab === cat.id ? ' is-active' : ''}}`}}
                onClick={{() => setActiveTab(cat.id)}}
              >
                {{cat.label}}
              </button>
            ))}}
          </div>
        </div>

        {{/* 2. Filtered Cards Grid */}}
        <div className="{p}-tabs__grid">
          {{filteredFeatures.map((item) => (
            <div key={{item.id}} className="{p}-tabs__card">
              <div className="{p}-tabs__card-top">
                <span className="{p}-tabs__badge">{{item.badge}}</span>
                <span className="{p}-tabs__category">{{item.category}}</span>
              </div>
              {{item.image && (
                <div className="{p}-tabs__img-wrap">
                  <img src={{item.image}} alt={{item.title}} className="{p}-tabs__card-img" />
                </div>
              )}}
              <h3 className="{p}-tabs__card-title">{{item.title}}</h3>
              <p className="{p}-tabs__card-desc">{{item.desc}}</p>
            </div>
          ))}}
        </div>

        {{/* 3. Carousel Component — Testimonials & Proof */}}
        <div className="{p}-tabs__carousel" aria-label="Customer Testimonials">
          <div className="{p}-tabs__carousel-box">
            <div className="{p}-tabs__stars" aria-label="5 stars rating">
              {{'★'.repeat(currentReview.rating)}}
            </div>

            <blockquote className="{p}-tabs__quote">
              &ldquo;{{currentReview.quote}}&rdquo;
            </blockquote>

            <div className="{p}-tabs__author">
              <div className="{p}-tabs__author-avatar" aria-hidden="true">
                {{currentReview.author.split(' ').map((n) => n[0]).join('')}}
              </div>
              <div>
                <h4 className="{p}-tabs__author-name">{{currentReview.author}}</h4>
                <span className="{p}-tabs__author-role">{{currentReview.role}}</span>
              </div>
            </div>

            <div className="{p}-tabs__carousel-controls">
              <button
                type="button"
                onClick={{prevSlide}}
                className="{p}-tabs__carousel-btn"
                aria-label="Previous testimonial"
              >
                &larr;
              </button>
              <span className="{p}-tabs__carousel-counter">
                0{{activeSlide + 1}} / 0{{REVIEWS.length}}
              </span>
              <button
                type="button"
                onClick={{nextSlide}}
                className="{p}-tabs__carousel-btn"
                aria-label="Next testimonial"
              >
                &rarr;
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""

    css = f""".{p}-tabs {{
  width: 100%;
  padding: 6.5rem 1.5rem;
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, {primary_color})));
  color: var(--color-paper, var(--text-color, #ffffff));
}}

.{p}-tabs__inner {{
  max-width: var(--page-max-width, 1180px);
  margin: 0 auto;
}}

.{p}-tabs__header {{
  text-align: center;
  max-width: 720px;
  margin: 0 auto 3.5rem;
}}

.{p}-tabs__eyebrow {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  margin-bottom: 0.75rem;
}}

.{p}-tabs__title {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: clamp(2rem, 4vw, 2.75rem);
  font-weight: 800;
  color: var(--color-paper, var(--text-color, #ffffff));
  letter-spacing: -0.025em;
  margin-bottom: 1rem;
}}

.{p}-tabs__subtitle {{
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 1.05rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.7));
  line-height: 1.6;
  margin-bottom: 2.5rem;
}}

.{p}-tabs__nav {{
  display: inline-flex;
  background: {accent_color}10;
  padding: 0.35rem;
  border-radius: {radius_btn};
  border: 1px solid {accent_color}30;
  gap: 0.35rem;
  flex-wrap: wrap;
  justify-content: center;
}}

.{p}-tabs__tab {{
  background: {accent_color}08;
  border: 1px solid {accent_color}18;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.7));
  padding: 0.55rem 1.25rem;
  border-radius: {radius_btn};
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
}}

.{p}-tabs__tab:hover {{
  color: var(--color-paper, #ffffff);
}}

.{p}-tabs__tab.is-active {{
  background: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  color: var(--color-paper, #ffffff);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}}

.{p}-tabs__grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin-bottom: 4.5rem;
}}

.{p}-tabs__card {{
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid {accent_color}30;
  border-radius: {radius_card};
  padding: 2rem;
  display: flex;
  flex-direction: column;
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}}

.{p}-tabs__card:hover {{
  transform: translateY(-4px);
  border-color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4);
}}

.{p}-tabs__card-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}}

.{p}-tabs__badge {{
  padding: 0.25rem 0.65rem;
  background: rgba(56, 189, 248, 0.12);
  color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  border-radius: {radius_btn};
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}}

.{p}-tabs__category {{
  font-size: 0.75rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.5));
  text-transform: uppercase;
  font-family: monospace;
}}

.{p}-tabs__card-title {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
  margin-bottom: 0.75rem;
}}

.{p}-tabs__card-desc {{
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 0.9375rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.7));
  line-height: 1.6;
}}

/* Carousel Section */
.{p}-tabs__carousel {{
  max-width: 820px;
  margin: 0 auto;
}}

.{p}-tabs__carousel-box {{
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid {accent_color}30;
  border-radius: {radius_card};
  padding: 3rem 2.5rem;
  text-align: center;
}}

.{p}-tabs__stars {{
  color: #f59e0b;
  font-size: 1.25rem;
  letter-spacing: 0.2em;
  margin-bottom: 1.5rem;
}}

.{p}-tabs__quote {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: clamp(1.15rem, 2.5vw, 1.45rem);
  font-style: italic;
  color: var(--color-paper, #ffffff);
  line-height: 1.6;
  margin: 0 0 2rem;
}}

.{p}-tabs__author {{
  display: inline-flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  text-align: left;
}}

.{p}-tabs__author-avatar {{
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  color: var(--color-paper, #ffffff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.875rem;
}}

.{p}-tabs__author-name {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
  margin: 0;
}}

.{p}-tabs__author-role {{
  font-size: 0.8125rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.6));
}}

.{p}-tabs__carousel-controls {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
}}

.{p}-tabs__carousel-btn {{
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: {accent_color}15;
  border: 1px solid {accent_color}35;
  color: var(--color-paper, #ffffff);
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}}

.{p}-tabs__carousel-btn:hover {{
  background: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  border-color: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
}}

.{p}-tabs__carousel-counter {{
  font-family: monospace;
  font-size: 0.875rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.6));
}}

@media (max-width: 900px) {{
  .{p}-tabs__grid {{
    grid-template-columns: 1fr;
  }}
}}

.{p}-tabs__grid {{
  animation: {p}TabCrossfade 0.35s ease;
}}

@keyframes {p}TabCrossfade {{
  from {{ opacity: 0; transform: translateX(6px); }}
  to {{ opacity: 1; transform: translateX(0); }}
}}

/* Tabs Image Entrance: synchronized crossfade with subtle vertical drift */
.{p}-tabs__img-wrap {{
  width: 100%;
  height: 160px;
  overflow: hidden;
  border-radius: {radius_card};
  margin-bottom: 1.25rem;
}}

.{p}-tabs__card-img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transform: translateY(6px);
  animation: {p}TabImageEnter 0.35s ease-out forwards;
  display: block;
}}

@keyframes {p}TabImageEnter {{
  to {{
    opacity: 1;
    transform: translateY(0);
  }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-tabs__grid,
  .{p}-tabs__tab,
  .{p}-tabs__carousel-btn,
  .{p}-tabs__card,
  .{p}-tabs__card:hover,
  .{p}-tabs__card-img {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 4. Split-Screen Hero Archetype Template
# ==============================================================================

def render_split_hero(
    component_name: str,
    business_name: str = "OmniMind AI",
    tagline: str = "Autonomous neural agent swarms with self-refining code loops",
    subtitle: str = "Coordinate specialized small models with frontier reasoning kernels. Build, test, and correct complex full-stack code in automated micro-sandboxes.",
    cta_primary: str = "Install SDK (`npm i omnimind`)",
    cta_secondary: str = "Read Architecture ↗",
    metrics: Optional[List[Dict[str, str]]] = None,
    hero_url: Optional[str] = None,
    prefix: str = "sh",
    primary_color: str = "#030712",
    accent_color: str = "#8b5cf6",
    accent_secondary: str = "#c084fc",
    font_heading: str = "Inter",
    font_body: str = "Inter",
    border_radius: str = "8px",
    pill_buttons: bool = False,
) -> Tuple[str, str]:
    """
    Renders a 50/50 Split-Screen Hero component:
    - Left column: prominent typography, badges, dual CTAs, metric highlights
    - Right column: live interactive widget / terminal or coordinated hero image
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = "var(--radius-buttons, 75px)" if pill_buttons else f"var(--radius-buttons, {border_radius})"
    radius_card = "var(--radius-cards, 0px)" if pill_buttons else f"var(--radius-cards, {border_radius})"

    sample_metrics = metrics or [
        {"val": "100%", "label": "Verifiable ASTs"},
        {"val": "< 50ms", "label": "In-Memory Vitest"},
        {"val": "5.0★", "label": "Architect Rating"},
    ]

    if hero_url:
        widget_jsx = f"""        {{/* Right Column: Hero Visual Image Container */}}
        <div className="{p}-split-hero__widget" aria-label="Hero Visual Representation">
          <div className="{p}-split-hero__img-card">
            <img src="{hero_url}" alt="{business_name}" className="{p}-split-hero__hero-img" />
          </div>
        </div>"""
    else:
        widget_jsx = f"""        {{/* Right Column: Live Interactive Sandbox / Terminal */}}
        <div className="{p}-split-hero__widget" aria-label="Live Terminal Execution">
          <div className="{p}-split-hero__terminal">
            <div className="{p}-split-hero__terminal-bar">
              <div className="{p}-split-hero__dots">
                <span className="{p}-dot {p}-dot--red" />
                <span className="{p}-dot {p}-dot--yellow" />
                <span className="{p}-dot {p}-dot--green" />
              </div>
              <div className="{p}-split-hero__tabs">
                <button
                  type="button"
                  className={{`{p}-split-hero__tab${{activeTab === 'terminal' ? ' is-active' : ''}}`}}
                  onClick={{() => setActiveTab('terminal')}}
                >
                  agent_runner.sh
                </button>
                <button
                  type="button"
                  className={{`{p}-split-hero__tab${{activeTab === 'config' ? ' is-active' : ''}}`}}
                  onClick={{() => setActiveTab('config')}}
                >
                  swarm.config.ts
                </button>
              </div>
            </div>

            <div className="{p}-split-hero__terminal-body">
              {{activeTab === 'terminal' ? (
                <>
                  <div className="{p}-term-line {p}-term-line--dim">[00:00.04] Initializing runtime sandbox: Node v22.4, TypeScript 5.6</div>
                  <div className="{p}-term-line">[AGENT: Coder-3B] Generated component: `src/components/DataGrid.tsx`</div>
                  <div className="{p}-term-line {p}-term-line--amber">⚡ [TEST RUNNER] Executing Vitest harness...</div>
                  <div className="{p}-term-line {p}-term-line--red">✗ FAIL: Expected sort indicator to be aria-sort="ascending"</div>
                  <div className="{p}-term-line {p}-term-line--violet">↺ [SELF-CORRECTION] Re-prompting with syntax diagnostics...</div>
                  <div className="{p}-term-line {p}-term-line--cyan">[AGENT: Coder-3B] Applied patch to src/components/DataGrid.tsx</div>
                  <div className="{p}-term-line {p}-term-line--green">✓ PASS: All 12 unit tests and accessibility checks verified.</div>
                </>
              ) : (
                <pre className="{p}-term-code">
                  <code>{{`export default defineSwarm({{\n  planner: 'claude-3-5-sonnet',\n  coder: 'react-agent-3b-lora',\n  evaluator: 'vitest-in-memory',\n  maxRetries: 3,\n}});`}}</code>
                </pre>
              )}}
            </div>
          </div>
        </div>"""

    tsx = f"""import React, {{ useState }} from 'react';
import './{pascal}.css';

export function {pascal}() {{
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'terminal' | 'config'>('terminal');

  const handleCopy = () => {{
    navigator.clipboard.writeText('npm i omnimind');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }};

  return (
    <section className="{p}-split-hero" id="hero" aria-label="{business_name} Overview">
      <div className="{p}-split-hero__glow" aria-hidden="true" />
      <div className="{p}-split-hero__inner">
        {{/* Left Column: Brand Statement & Actions */}}
        <div className="{p}-split-hero__content">
          <div className="{p}-split-hero__badge">
            <span className="{p}-split-hero__badge-dot" />
            <span>NEURAL ORCHESTRATION ENGINE</span>
          </div>

          <h1 className="{p}-split-hero__title">
            {tagline}
          </h1>

          <p className="{p}-split-hero__sub">
            {subtitle}
          </p>

          <div className="{p}-split-hero__actions">
            <button type="button" onClick={{handleCopy}} className="{p}-split-hero__btn-primary">
              {{copied ? '✓ Copied to Clipboard' : '{cta_primary}'}}
            </button>
            <a href="#capabilities" className="{p}-split-hero__btn-secondary">
              {cta_secondary}
            </a>
          </div>

          <div className="{p}-split-hero__metrics" role="group" aria-label="Key Metrics">
            {{[
              {sample_metrics}
            ][0].map((m, idx) => (
              <div key={{idx}} className="{p}-split-hero__metric">
                <span className="{p}-split-hero__metric-val">{{m.val}}</span>
                <span className="{p}-split-hero__metric-label">{{m.label}}</span>
              </div>
            ))}}
          </div>
        </div>

{widget_jsx}
      </div>
    </section>
  );
}}
"""

    css = f""".{p}-split-hero {{
  position: relative;
  width: 100%;
  padding: 6.5rem 1.5rem 5rem;
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, {primary_color})));
  overflow: hidden;
}}

.{p}-split-hero__glow {{
  position: absolute;
  top: -150px;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 600px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.22) 0%, transparent 65%);
  pointer-events: none;
}}

.{p}-split-hero__inner {{
  max-width: var(--page-max-width, 1200px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 3.5rem;
  align-items: center;
}}

.{p}-split-hero__badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.9rem;
  background: rgba(139, 92, 246, 0.12);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: {radius_btn};
  color: var(--color-paper, #c4b5fd);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  margin-bottom: 1.5rem;
}}

.{p}-split-hero__badge-dot {{
  width: 6px;
  height: 6px;
  background: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  border-radius: 50%;
}}

.{p}-split-hero__title {{
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: clamp(2.2rem, 4vw, 3.4rem);
  font-weight: 800;
  color: var(--color-paper, var(--text-color, #ffffff));
  line-height: 1.15;
  letter-spacing: -0.03em;
  margin-bottom: 1.25rem;
}}

.{p}-split-hero__sub {{
  font-family: var(--font-body, '{font_body}', sans-serif);
  font-size: 1.05rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.72));
  line-height: 1.65;
  margin-bottom: 2rem;
}}

.{p}-split-hero__actions {{
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 3rem;
}}

.{p}-split-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: var(--color-iridescent-fade, var(--accent-color, {accent_color}));
  color: var(--color-paper, #ffffff);
  border: none;
  border-radius: {radius_btn};
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.15s ease;
}}

.{p}-split-hero__btn-primary:hover {{
  opacity: 0.92;
  transform: translateY(-2px);
}}

.{p}-split-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--color-paper, #ffffff);
  border-radius: {radius_btn};
  font-size: 0.95rem;
  font-weight: 600;
  text-decoration: none;
  transition: background-color 0.15s ease, color 0.15s ease;
}}

.{p}-split-hero__btn-secondary:hover {{
  background: rgba(255, 255, 255, 0.1);
}}

.{p}-split-hero__metrics {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-split-hero__metric-val {{
  display: block;
  font-family: var(--font-heading, '{font_heading}', sans-serif);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
}}

.{p}-split-hero__metric-label {{
  font-size: 0.78rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.55));
}}

/* Interactive Terminal Widget */
.{p}-split-hero__terminal {{
  background: #090d16;
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: {radius_card};
  overflow: hidden;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 30px rgba(139, 92, 246, 0.15);
}}

.{p}-split-hero__terminal-bar {{
  background: #0d1322;
  padding: 0.65rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-split-hero__dots {{
  display: flex;
  gap: 6px;
}}

.{p}-dot {{
  width: 10px;
  height: 10px;
  border-radius: 50%;
}}

.{p}-dot--red {{ background: #ef4444; }}
.{p}-dot--yellow {{ background: #f59e0b; }}
.{p}-dot--green {{ background: #10b981; }}

.{p}-split-hero__tabs {{
  display: flex;
  gap: 0.5rem;
}}

.{p}-split-hero__tab {{
  background: transparent;
  border: none;
  font-family: monospace;
  font-size: 0.78rem;
  color: #64748b;
  cursor: pointer;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}}

.{p}-split-hero__tab.is-active {{
  color: var(--color-paper, #ffffff);
  background: rgba(255, 255, 255, 0.08);
}}

.{p}-split-hero__terminal-body {{
  padding: 1.5rem;
  font-family: monospace;
  font-size: 0.84rem;
  line-height: 1.7;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-height: 250px;
}}

.{p}-term-line--dim {{ color: #475569; }}
.{p}-term-line--amber {{ color: #f59e0b; }}
.{p}-term-line--red {{ color: #f87171; }}
.{p}-term-line--violet {{ color: #c084fc; }}
.{p}-term-line--cyan {{ color: #38bdf8; }}
.{p}-term-line--green {{ color: #4ade80; font-weight: 600; }}

.{p}-term-code {{
  margin: 0;
  color: #cbd5e1;
}}

@media (max-width: 900px) {{
  .{p}-split-hero__inner {{
    grid-template-columns: 1fr;
    gap: 3rem;
  }}
}}

.{p}-split-hero__content {{
  animation: {p}SplitHeroLeftEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0ms both;
}}

.{p}-split-hero__visual,
.{p}-split-hero__widget {{
  animation: {p}SplitHeroRightEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 160ms both;
}}

@keyframes {p}SplitHeroLeftEnter {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes {p}SplitHeroRightEnter {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* Split Hero Image Entrance: coordinated 160ms offset matching right visual column */
.{p}-split-hero__img-card {{
  border-radius: {radius_card};
  overflow: hidden;
  border: 1px solid rgba(139, 92, 246, 0.3);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 30px rgba(139, 92, 246, 0.15);
  background: #090d16;
  aspect-ratio: 16 / 10;
}}

.{p}-split-hero__hero-img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  opacity: 0;
  transform: translateY(14px);
  animation: {p}SplitHeroImageEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 160ms both;
}}

@keyframes {p}SplitHeroImageEnter {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-split-hero__content,
  .{p}-split-hero__visual,
  .{p}-split-hero__widget,
  .{p}-split-hero__terminal,
  .{p}-split-hero__btn-primary,
  .{p}-split-hero__btn-secondary,
  .{p}-split-hero__hero-img {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 5. Master Dispatcher
# ==============================================================================

SUPPORTED_ARCHETYPE_ALIASES = {
    "bento": "bento", "grid": "bento", "editorial": "editorial", "tabs": "tabs", "split_hero": "split_hero",
    "magazine": "editorial", "timeline": "tabs", "asymmetric": "editorial",
    "product_stage": "product_stage", "product_stage_hero": "product_stage", "stage": "product_stage",
    "full_bleed_visual": "full_bleed_visual", "full_bleed_visual_hero": "full_bleed_visual",
    "terminal_data": "terminal_data", "terminal_data_hero": "terminal_data",
    "restrained_centered": "restrained_centered", "restrained_centered_hero": "restrained_centered",
}

def validate_archetype(archetype: str) -> str:
    key = str(archetype).lower().replace("-", "_").strip()
    if key not in SUPPORTED_ARCHETYPE_ALIASES:
        raise ValueError(f"Unknown layout archetype '{archetype}'. Planner must emit a registered archetype ID.")
    return SUPPORTED_ARCHETYPE_ALIASES[key]


def render_archetype_component(
    archetype: str,
    component_name: str,
    items: List[Dict[str, Any]],
    business_name: str = "Acme",
    tagline: str = "",
    primary_color: str = "#0b0f19",
    accent_color: str = "#2563eb",
    accent_secondary: str = "#06b6d4",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "8px",
    pill_buttons: bool = False,
    prefix: str = "site",
) -> Tuple[str, str]:
    """
    Renders (tsx_code, css_code) using the designated layout archetype template.
    Supported archetypes: 'bento', 'editorial', 'tabs', 'split_hero', 'grid'.
    """
    arch = validate_archetype(archetype)

    if arch == "bento":
        return render_bento_grid(
            component_name=component_name,
            items=items,
            business_name=business_name,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif arch == "editorial":
        return render_editorial_layout(
            component_name=component_name,
            items=items,
            business_name=business_name,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif arch == "tabs":
        return render_tabs_carousel(
            component_name=component_name,
            items=items,
            business_name=business_name,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif arch == "split_hero":
        hero_img = ""
        if items and isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
            hero_img = items[0].get("image", "") or items[0].get("hero_url", "")
        return render_split_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline or "Autonomous engineering intelligence for modern teams",
            hero_url=hero_img or None,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif arch in ("product_stage", "product_stage_hero", "stage"):
        return render_product_stage_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline or "Precision Engineered Architectural Stage",
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif arch in ("full_bleed_visual", "full_bleed_visual_hero", "full_bleed", "full_bleed_hero"):
        return render_full_bleed_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline or "Immersive Full-Bleed Visual Experience",
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif arch in ("terminal_data", "terminal_data_hero", "terminal", "terminal_code_hero"):
        return render_terminal_data_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline or "Deterministic Developer Infrastructure",
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif arch in ("restrained_centered", "restrained_centered_hero", "centered_hero", "centered"):
        return render_restrained_centered_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline or "Architectural Precision & Clean Typographic Rhythm",
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    else:
        raise ValueError(f"Unknown layout archetype '{arch}'. Planner must emit a registered archetype ID.")


# ==============================================================================
# 6. Product-Stage Hero Archetype Template (Section 3.B)
# ==============================================================================

def render_product_stage_hero(
    component_name: str = "ProductStageHero",
    business_name: str = "Aether Dynamics",
    tagline: str = "Architectural Hardware & Spatial Intelligence Platform",
    eyebrow: str = "FLAGSHIP PLATFORM",
    title: str = "Sculpted for Uncompromising Precision",
    subtitle: str = "An elevated interactive staging environment engineered with illuminated plinth acoustics and deterministic telemetry.",
    prefix: str = "stage",
    primary_color: str = "#07090e",
    accent_color: str = "#38bdf8",
    accent_secondary: str = "#818cf8",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "12px",
    pill_buttons: bool = False,
) -> Tuple[str, str]:
    """
    Renders an architectural product-stage hero with illuminated pedestal,
    interactive specification inspector, and floating telemetry readouts.
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = "var(--radius-buttons, 9999px)" if pill_buttons else f"var(--radius-buttons, {border_radius})"
    radius_card = f"var(--radius-cards, {border_radius})"

    tsx = f"""import React, {{ useState }} from 'react';
import './{pascal}.css';

export interface StageSpec {{
  id: string;
  label: string;
  value: string;
  metric: string;
}}

export default function {pascal}() {{
  const [activeSpec, setActiveSpec] = useState<string>('optics');
  const [rotation, setRotation] = useState<number>(0);

  const specs: StageSpec[] = [
    {{ id: 'optics', label: 'Photonic Array', value: '4K Micro-OLED', metric: '120 Hz Spatial Sync' }},
    {{ id: 'compute', label: 'Neural Engine', value: '8-Core SLM Core', metric: '<4.2ms In-Memory Latency' }},
    {{ id: 'materials', label: 'Chassis Alloy', value: 'Aero Titanium Grade 5', metric: '340g Total Weight' }},
  ];

  const current = specs.find(s => s.id === activeSpec) || specs[0];

  return (
    <section className="{p}-hero-stage product_stage product-stage" id="stage-hero" aria-label="{business_name} Product Stage">
      <div className="{p}-stage-ambient-glow" aria-hidden="true" />
      
      <div className="{p}-stage-header">
        <span className="{p}-stage-eyebrow">{eyebrow}</span>
        <h1 className="{p}-stage-title">{title}</h1>
        <p className="{p}-stage-subtitle">{subtitle}</p>
      </div>

      <div className="{p}-stage-plinth-wrapper">
        <div className="{p}-stage-plinth-pedestal">
          <div 
            className="{p}-stage-viewport"
            style={{{{ transform: `rotateY(${{rotation}}deg)` }}}}
          >
            <div className="{p}-stage-hologram">
              <div className="{p}-stage-core-orb" />
              <div className="{p}-stage-ring-outer" />
              <div className="{p}-stage-ring-inner" />
            </div>
          </div>
          <div className="{p}-stage-plinth-base" />
          <div className="{p}-stage-plinth-light" />
        </div>

        <div className="{p}-stage-readout-card">
          <div className="{p}-stage-spec-tabs" role="tablist">
            {{specs.map(s => (
              <button
                key={{s.id}}
                role="tab"
                aria-selected={{activeSpec === s.id}}
                className={{`{p}-stage-spec-btn ${{activeSpec === s.id ? 'active' : ''}}`}}
                onClick={{() => {{
                  setActiveSpec(s.id);
                  setRotation(r => r + 45);
                }}}}
              >
                {{s.label}}
              </button>
            ))}}
          </div>
          <div className="{p}-stage-spec-body">
            <div className="{p}-stage-spec-val">{{current.value}}</div>
            <div className="{p}-stage-spec-metric">{{current.metric}}</div>
          </div>
        </div>
      </div>

      <div className="{p}-stage-actions">
        <a href="#explore" className="{p}-stage-btn-primary">Reserve Flagship</a>
        <a href="#specs" className="{p}-stage-btn-secondary">Technical Blueprint</a>
      </div>
    </section>
  );
}}
"""

    css = f"""/* {pascal}.css - Product-Stage Hero Layout Archetype */
.{p}-hero-stage {{
  position: relative;
  min-height: 85vh;
  padding: 6rem 1.5rem 4rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: {primary_color};
  color: #f8fafc;
  overflow: hidden;
}}

.{p}-stage-ambient-glow {{
  position: absolute;
  top: 10%;
  left: 50%;
  transform: translateX(-50%);
  width: 650px;
  height: 450px;
  background: radial-gradient(circle, {accent_color}2b 0%, {accent_secondary}10 40%, transparent 70%);
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}}

.{p}-stage-header {{
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 780px;
  margin-bottom: 2.5rem;
}}

.{p}-stage-eyebrow {{
  display: inline-block;
  font-family: '{font_body}', sans-serif;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: {accent_color};
  padding: 0.35rem 0.85rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9999px;
  margin-bottom: 1.25rem;
}}

.{p}-stage-title {{
  font-family: '{font_heading}', sans-serif;
  font-size: clamp(2.2rem, 5vw, 3.8rem);
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -0.03em;
  margin: 0 0 1rem;
  background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}

.{p}-stage-subtitle {{
  font-family: '{font_body}', sans-serif;
  font-size: 1.1rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.72);
  margin: 0 auto;
  max-width: 620px;
}}

.{p}-stage-plinth-wrapper {{
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 2.5rem;
}}

.{p}-stage-plinth-pedestal {{
  position: relative;
  width: 320px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 900px;
}}

.{p}-stage-viewport {{
  position: relative;
  width: 180px;
  height: 180px;
  transition: transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transform-style: preserve-3d;
  display: flex;
  align-items: center;
  justify-content: center;
}}

.{p}-stage-core-orb {{
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #ffffff 0%, {accent_color} 50%, {primary_color} 100%);
  box-shadow: 0 0 35px {accent_color}88;
}}

.{p}-stage-ring-outer {{
  position: absolute;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  border: 1.5px dashed rgba(255, 255, 255, 0.3);
  animation: {p}Spin 16s linear infinite;
}}

.{p}-stage-ring-inner {{
  position: absolute;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 1px solid {accent_secondary}66;
  transform: rotateX(65deg);
}}

.{p}-stage-plinth-base {{
  position: absolute;
  bottom: 10px;
  width: 280px;
  height: 22px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.02) 70%, transparent 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-stage-plinth-light {{
  position: absolute;
  bottom: 0px;
  width: 200px;
  height: 12px;
  background: {accent_color};
  filter: blur(12px);
  opacity: 0.6;
}}

.{p}-stage-readout-card {{
  margin-top: 1.5rem;
  width: 100%;
  max-width: 480px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: {radius_card};
  padding: 1.25rem;
  backdrop-filter: blur(12px);
}}

.{p}-stage-spec-tabs {{
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 0.75rem;
  margin-bottom: 0.75rem;
}}

.{p}-stage-spec-btn {{
  flex: 1;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-family: '{font_body}', sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  transition: color 0.2s ease, background-color 0.2s ease;
}}

.{p}-stage-spec-btn.active {{
  color: #f8fafc;
  background: rgba(255, 255, 255, 0.08);
}}

.{p}-stage-spec-body {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.{p}-stage-spec-val {{
  font-family: '{font_heading}', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: #ffffff;
}}

.{p}-stage-spec-metric {{
  font-family: '{font_body}', sans-serif;
  font-size: 0.85rem;
  color: {accent_color};
  font-weight: 600;
}}

.{p}-stage-actions {{
  position: relative;
  z-index: 1;
  display: flex;
  gap: 1rem;
}}

.{p}-stage-btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: {accent_color};
  color: #07090e;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  border-radius: {radius_btn};
  text-decoration: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 4px 20px {accent_color}44;
}}

.{p}-stage-btn-primary:hover {{
  transform: translateY(-2px);
  box-shadow: 0 8px 28px {accent_color}66;
}}

.{p}-stage-btn-secondary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: rgba(255, 255, 255, 0.06);
  color: #f8fafc;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: {radius_btn};
  text-decoration: none;
  transition: background 0.2s ease;
}}

.{p}-stage-btn-secondary:hover {{
  background: rgba(255, 255, 255, 0.1);
}}

@keyframes {p}Spin {{
  from {{ transform: rotate(0deg); }}
  to {{ transform: rotate(360deg); }}
}}

@media (max-width: 640px) {{
  .{p}-hero-stage {{
    padding: 4rem 1rem 3rem;
  }}
  .{p}-stage-actions {{
    flex-direction: column;
    width: 100%;
    max-width: 320px;
  }}
  .{p}-stage-btn-primary, .{p}-stage-btn-secondary {{
    justify-content: center;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 7. Full-Bleed Visual Hero Archetype Template (Section 3.B)
# ==============================================================================

def render_full_bleed_hero(
    component_name: str = "FullBleedVisualHero",
    business_name: str = "Lumina Vista",
    tagline: str = "Immersive Spatial Architecture & Cinematic Horizons",
    eyebrow: str = "MONOLITHIC HORIZON",
    title: str = "Cinematic Presence Across Every Viewport",
    subtitle: str = "Unbroken full-bleed visual canvases coupled with architectural typography and contextual ambient gradients.",
    hero_url: Optional[str] = None,
    prefix: str = "bleed",
    primary_color: str = "#05070a",
    accent_color: str = "#38bdf8",
    accent_secondary: str = "#f59e0b",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "8px",
    pill_buttons: bool = True,
) -> Tuple[str, str]:
    """
    Renders an edge-to-edge full-bleed visual hero with vignette overlay,
    display typography, and telemetry cards.
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = "var(--radius-buttons, 9999px)" if pill_buttons else f"var(--radius-buttons, {border_radius})"
    img_url = hero_url or "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=2000&q=80"

    tsx = f"""import React from 'react';
import './{pascal}.css';

export default function {pascal}() {{
  return (
    <section className="{p}-hero-full-bleed full-bleed full_bleed visual-hero" id="hero" aria-label="{business_name}">
      <div 
        className="{p}-bleed-backdrop bg-cover object-cover" 
        style={{{{ backgroundImage: `url('{img_url}')` }}}}
        role="img"
        aria-label="{title}"
      />
      <div className="{p}-bleed-vignette" aria-hidden="true" />

      <div className="{p}-bleed-content">
        <span className="{p}-bleed-tag">{eyebrow}</span>
        <h1 className="{p}-bleed-title">{title}</h1>
        <p className="{p}-bleed-subtitle">{subtitle}</p>

        <div className="{p}-bleed-actions">
          <a href="#explore" className="{p}-bleed-btn-main">Experience Monolith</a>
          <a href="#gallery" className="{p}-bleed-btn-ghost">View Exhibition</a>
        </div>
      </div>

      <div className="{p}-bleed-footer-stats">
        <div className="{p}-bleed-stat">
          <span className="{p}-stat-num">100%</span>
          <span className="{p}-stat-lbl">Full-Bleed Responsive Canvas</span>
        </div>
        <div className="{p}-bleed-stat">
          <span className="{p}-stat-num">&lt; 16ms</span>
          <span className="{p}-stat-lbl">Frame Budget Execution</span>
        </div>
        <div className="{p}-bleed-stat">
          <span className="{p}-stat-num">Zero-Shift</span>
          <span className="{p}-stat-lbl">Layout Stability Guaranteed</span>
        </div>
      </div>
    </section>
  );
}}
"""

    css = f"""/* {pascal}.css - Full-Bleed Visual Hero Layout Archetype */
.{p}-hero-full-bleed {{
  position: relative;
  min-height: 90vh;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 6rem 2.5rem 3rem;
  overflow: hidden;
  color: #f8fafc;
}}

.{p}-bleed-backdrop {{
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  transform: scale(1.03);
  z-index: 0;
}}

.{p}-bleed-vignette {{
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg, 
    rgba(5, 7, 10, 0.3) 0%, 
    rgba(5, 7, 10, 0.75) 60%, 
    {primary_color} 100%
  );
  z-index: 1;
}}

.{p}-bleed-content {{
  position: relative;
  z-index: 2;
  max-width: 820px;
  margin-bottom: 4rem;
}}

.{p}-bleed-tag {{
  display: inline-block;
  font-family: '{font_body}', sans-serif;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: {accent_color};
  padding: 0.3rem 0.8rem;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 9999px;
  margin-bottom: 1.25rem;
}}

.{p}-bleed-title {{
  font-family: '{font_heading}', sans-serif;
  font-size: clamp(2.5rem, 6vw, 4.4rem);
  font-weight: 800;
  line-height: 1.08;
  letter-spacing: -0.035em;
  margin: 0 0 1.25rem;
  text-shadow: 0 4px 24px rgba(0,0,0,0.6);
}}

.{p}-bleed-subtitle {{
  font-family: '{font_body}', sans-serif;
  font-size: 1.15rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.85);
  max-width: 640px;
  margin: 0 0 2rem;
  text-shadow: 0 2px 12px rgba(0,0,0,0.5);
}}

.{p}-bleed-actions {{
  display: flex;
  gap: 1.2rem;
}}

.{p}-bleed-btn-main {{
  display: inline-flex;
  align-items: center;
  padding: 0.9rem 2rem;
  background: #ffffff;
  color: #05070a;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  border-radius: {radius_btn};
  text-decoration: none;
  transition: transform 0.2s ease, background 0.2s ease;
}}

.{p}-bleed-btn-main:hover {{
  transform: translateY(-2px);
  background: #e2e8f0;
}}

.{p}-bleed-btn-ghost {{
  display: inline-flex;
  align-items: center;
  padding: 0.9rem 2rem;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(12px);
  color: #ffffff;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: {radius_btn};
  text-decoration: none;
  transition: background 0.2s ease;
}}

.{p}-bleed-btn-ghost:hover {{
  background: rgba(0, 0, 0, 0.65);
}}

.{p}-bleed-footer-stats {{
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
}}

.{p}-stat-num {{
  display: block;
  font-family: '{font_heading}', sans-serif;
  font-size: 1.5rem;
  font-weight: 800;
  color: #ffffff;
}}

.{p}-stat-lbl {{
  display: block;
  font-family: '{font_body}', sans-serif;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.65);
}}

@media (max-width: 768px) {{
  .{p}-hero-full-bleed {{
    padding: 5rem 1.25rem 2rem;
  }}
  .{p}-bleed-footer-stats {{
    grid-template-columns: 1fr;
    gap: 1rem;
  }}
  .{p}-bleed-actions {{
    flex-direction: column;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 8. Terminal / Data Hero Archetype Template (Section 3.B)
# ==============================================================================

def render_terminal_data_hero(
    component_name: str = "TerminalDataHero",
    business_name: str = "KernelForge",
    tagline: str = "High-Throughput Autonomous Compute & Execution Fabrics",
    eyebrow: str = "DEVELOPER ENGINE",
    title: str = "Deterministic Infrastructure Controlled via Code",
    subtitle: str = "Deploy heterogeneous agent clusters and inspect real-time trace telemetry directly through a verified terminal interface.",
    prefix: str = "term",
    primary_color: str = "#080b11",
    accent_color: str = "#10b981",
    accent_secondary: str = "#06b6d4",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "8px",
    pill_buttons: bool = False,
) -> Tuple[str, str]:
    """
    Renders an engineering-first terminal hero with interactive CLI shell,
    tabbed commands, animated prompt, and live telemetry outputs.
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = f"var(--radius-buttons, {border_radius})"
    radius_card = f"var(--radius-cards, {border_radius})"

    tsx = f"""import React, {{ useState }} from 'react';
import './{pascal}.css';

interface TerminalTab {{
  id: string;
  command: string;
  lines: string[];
}}

export default function {pascal}() {{
  const [activeTab, setActiveTab] = useState<string>('deploy');
  const [copied, setCopied] = useState<boolean>(false);

  const tabs: Record<string, TerminalTab> = {{
    deploy: {{
      id: 'deploy',
      command: 'kernel deploy --model qwen3-4b --nodes 8',
      lines: [
        '✓ Base architecture verified: Qwen3ForCausalLM (qwen3)',
        '✓ Context window allocated: 8,192 tokens per stream',
        '✓ Cluster healthy: 8/8 worker pods online [latency: 3.8ms]',
        '🚀 Service endpoint active: https://api.kernelforge.internal/v1',
      ],
    }},
    verify: {{
      id: 'verify',
      command: 'kernel test --rigorous --fail-closed',
      lines: [
        '✓ Gate 1: TypeCheck (tsc v5.4) ... PASS',
        '✓ Gate 2: Production Build (vite v6.0) ... PASS',
        '✓ Gate 3: Accessibility & Contract ... 100% PASS',
        '✓ Anti-Collapse Diversity: Shannon H=0.884 [PASSED]',
      ],
    }},
    metrics: {{
      id: 'metrics',
      command: 'kernel telemetry --flamegraph',
      lines: [
        'Heap Allocated: 142.4 MiB / Peak: 198.1 MiB',
        'Token Generation: 114 tokens/sec [BF16 native]',
        'Self-Correction Loops: 0 fallback reliance (100% native)',
      ],
    }},
  }};

  const activeData = tabs[activeTab] || tabs.deploy;

  const handleCopy = () => {{
    navigator.clipboard?.writeText(activeData.command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }};

  return (
    <section className="{p}-hero-terminal terminal_data terminal_code_hero" id="terminal-hero" aria-label="{business_name}">
      <div className="{p}-term-left">
        <span className="{p}-term-eyebrow">{eyebrow}</span>
        <h1 className="{p}-term-title">{title}</h1>
        <p className="{p}-term-desc">{subtitle}</p>

        <div className="{p}-term-cta-row">
          <a href="#quickstart" className="{p}-term-btn-primary">Initialize CLI</a>
          <a href="#docs" className="{p}-term-btn-secondary">API Reference</a>
        </div>
      </div>

      <div className="{p}-term-right">
        <div className="{p}-terminal-window">
          <div className="{p}-terminal-chrome">
            <div className="{p}-chrome-dots">
              <span className="{p}-dot red" />
              <span className="{p}-dot yellow" />
              <span className="{p}-dot green" />
            </div>
            <div className="{p}-chrome-title">kernelforge-shell@cluster-01</div>
            <button className="{p}-chrome-copy-btn" onClick={{handleCopy}}>
              {{copied ? '✓ Copied' : 'Copy'}}
            </button>
          </div>

          <div className="{p}-terminal-tabs">
            <button 
              className={{`{p}-tab-btn ${{activeTab === 'deploy' ? 'active' : ''}}`}}
              onClick={{() => setActiveTab('deploy')}}
            >
              deploy.sh
            </button>
            <button 
              className={{`{p}-tab-btn ${{activeTab === 'verify' ? 'active' : ''}}`}}
              onClick={{() => setActiveTab('verify')}}
            >
              verify.sh
            </button>
            <button 
              className={{`{p}-tab-btn ${{activeTab === 'metrics' ? 'active' : ''}}`}}
              onClick={{() => setActiveTab('metrics')}}
            >
              telemetry.sh
            </button>
          </div>

          <div className="{p}-terminal-body">
            <div className="{p}-term-prompt-line">
              <span className="{p}-term-prefix">$</span>
              <span className="{p}-term-cmd">{{activeData.command}}</span>
              <span className="{p}-term-cursor" />
            </div>
            <pre className="{p}-term-output">
              {{activeData.lines.map((line, i) => (
                <div key={{i}} className="{p}-out-line">{{line}}</div>
              ))}}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""

    css = f"""/* {pascal}.css - Terminal/Data Hero Layout Archetype */
.{p}-hero-terminal {{
  display: grid;
  grid-template-columns: 1fr 1.15fr;
  gap: 3.5rem;
  align-items: center;
  min-height: 80vh;
  padding: 6rem 2rem 4rem;
  background: {primary_color};
  color: #f8fafc;
}}

.{p}-term-left {{
  max-width: 580px;
}}

.{p}-term-eyebrow {{
  display: inline-block;
  font-family: '{font_body}', sans-serif;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: {accent_color};
  margin-bottom: 1rem;
}}

.{p}-term-title {{
  font-family: '{font_heading}', sans-serif;
  font-size: clamp(2.2rem, 4.5vw, 3.6rem);
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -0.03em;
  margin: 0 0 1.25rem;
}}

.{p}-term-desc {{
  font-family: '{font_body}', sans-serif;
  font-size: 1.05rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.75);
  margin: 0 0 2rem;
}}

.{p}-term-cta-row {{
  display: flex;
  gap: 1rem;
}}

.{p}-term-btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: {accent_color};
  color: #080b11;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  border-radius: {radius_btn};
  text-decoration: none;
  transition: opacity 0.2s ease;
}}

.{p}-term-btn-primary:hover {{
  opacity: 0.9;
}}

.{p}-term-btn-secondary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: rgba(255, 255, 255, 0.05);
  color: #f8fafc;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: {radius_btn};
  text-decoration: none;
}}

.{p}-terminal-window {{
  background: #0d1117;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: {radius_card};
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 20px {accent_color}1a;
}}

.{p}-terminal-chrome {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #161b22;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-chrome-dots {{
  display: flex;
  gap: 6px;
}}

.{p}-dot {{
  width: 10px;
  height: 10px;
  border-radius: 50%;
}}
.{p}-dot.red {{ background: #ef4444; }}
.{p}-dot.yellow {{ background: #f59e0b; }}
.{p}-dot.green {{ background: #10b981; }}

.{p}-chrome-title {{
  font-family: monospace;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
}}

.{p}-chrome-copy-btn {{
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}}

.{p}-terminal-tabs {{
  display: flex;
  background: #0d1117;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-tab-btn {{
  background: transparent;
  border: none;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.5);
  font-family: monospace;
  font-size: 0.8rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
}}

.{p}-tab-btn.active {{
  background: rgba(255, 255, 255, 0.05);
  color: {accent_color};
  border-bottom: 2px solid {accent_color};
}}

.{p}-terminal-body {{
  padding: 1.25rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.88rem;
}}

.{p}-term-prompt-line {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}}

.{p}-term-prefix {{
  color: {accent_color};
  font-weight: bold;
}}

.{p}-term-cmd {{
  color: #f8fafc;
}}

.{p}-term-cursor {{
  display: inline-block;
  width: 8px;
  height: 15px;
  background: {accent_color};
  animation: {p}Blink 1s step-end infinite;
}}

.{p}-term-output {{
  margin: 0;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.7;
  white-space: pre-wrap;
}}

.{p}-out-line {{
  padding: 0.15rem 0;
}}

@keyframes {p}Blink {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0; }}
}}

@media (max-width: 900px) {{
  .{p}-hero-terminal {{
    grid-template-columns: 1fr;
    gap: 2.5rem;
    padding: 4rem 1.25rem;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 9. Restrained Centered Hero Archetype Template (Section 3.B)
# ==============================================================================

def render_restrained_centered_hero(
    component_name: str = "RestrainedCenteredHero",
    business_name: str = "Synthetix Design",
    tagline: str = "Architectural Minimalism Engineered for High-Density Applications",
    eyebrow: str = "RESTRAINED ARCHITECTURE",
    title: str = "Pure Typographic Structure and Zero Excess",
    subtitle: str = "A calibrated centered layout with bounded reading widths, high-contrast hierarchical display type, and balanced rhythm.",
    prefix: str = "restrained",
    primary_color: str = "#090d14",
    accent_color: str = "#38bdf8",
    accent_secondary: str = "#64748b",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "6px",
    pill_buttons: bool = True,
) -> Tuple[str, str]:
    """
    Renders an architectural restrained centered hero with balanced max-width,
    subtle badge pill, high-contrast typography, and trust badges.
    """
    pascal = _sanitize_name(component_name)
    p = _sanitize_prefix(prefix)
    radius_btn = "var(--radius-buttons, 9999px)" if pill_buttons else f"var(--radius-buttons, {border_radius})"

    tsx = f"""import React from 'react';
import './{pascal}.css';

export default function {pascal}() {{
  return (
    <section className="{p}-hero-centered restrained restrained_centered hero-center" id="hero" aria-label="{business_name}">
      <div className="{p}-centered-container text-center mx-auto items-center">
        <div className="{p}-centered-badge">
          <span className="{p}-badge-dot" />
          <span>{eyebrow}</span>
        </div>

        <h1 className="{p}-centered-title">{title}</h1>
        <p className="{p}-centered-subtitle">{subtitle}</p>

        <div className="{p}-centered-actions">
          <a href="#start" className="{p}-centered-btn-primary">Explore Platform</a>
          <a href="#learn" className="{p}-centered-btn-ghost">System Manifest →</a>
        </div>

        <div className="{p}-trust-strip">
          <span className="{p}-trust-caption">VALIDATED ACROSS HIGH-RELIABILITY STACKS</span>
          <div className="{p}-trust-logos">
            <span className="{p}-trust-item">HYPERION</span>
            <span className="{p}-trust-item">SYNTHESIS</span>
            <span className="{p}-trust-item">CORETECH</span>
            <span className="{p}-trust-item">VERIFIED</span>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""

    css = f"""/* {pascal}.css - Restrained Centered Hero Layout Archetype */
.{p}-hero-centered {{
  min-height: 75vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6rem 1.5rem 4rem;
  background: {primary_color};
  color: #f8fafc;
}}

.{p}-centered-container {{
  max-width: 840px;
  margin: 0 auto;
  text-align: center;
}}

.{p}-centered-badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: '{font_body}', sans-serif;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #e2e8f0;
  padding: 0.35rem 0.9rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 9999px;
  margin-bottom: 1.5rem;
}}

.{p}-badge-dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: {accent_color};
  box-shadow: 0 0 8px {accent_color};
}}

.{p}-centered-title {{
  font-family: '{font_heading}', sans-serif;
  font-size: clamp(2.4rem, 5.5vw, 4.2rem);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.035em;
  margin: 0 0 1.25rem;
  color: #ffffff;
}}

.{p}-centered-subtitle {{
  font-family: '{font_body}', sans-serif;
  font-size: 1.15rem;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.7);
  max-width: 640px;
  margin: 0 auto 2.25rem;
}}

.{p}-centered-actions {{
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 3.5rem;
}}

.{p}-centered-btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: {accent_color};
  color: #090d14;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  border-radius: {radius_btn};
  text-decoration: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.{p}-centered-btn-primary:hover {{
  transform: translateY(-2px);
  box-shadow: 0 6px 20px {accent_color}44;
}}

.{p}-centered-btn-ghost {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: transparent;
  color: #f8fafc;
  font-family: '{font_body}', sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: {radius_btn};
  text-decoration: none;
  transition: background 0.2s ease;
}}

.{p}-centered-btn-ghost:hover {{
  background: rgba(255, 255, 255, 0.08);
}}

.{p}-trust-strip {{
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 2rem;
}}

.{p}-trust-caption {{
  display: block;
  font-family: '{font_body}', sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.15em;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 1.25rem;
}}

.{p}-trust-logos {{
  display: flex;
  justify-content: center;
  gap: 2.5rem;
  flex-wrap: wrap;
}}

.{p}-trust-item {{
  font-family: '{font_heading}', sans-serif;
  font-size: 0.9rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.35);
}}

@media (max-width: 640px) {{
  .{p}-hero-centered {{
    padding: 4rem 1rem 3rem;
  }}
  .{p}-centered-actions {{
    flex-direction: column;
  }}
  .{p}-trust-logos {{
    gap: 1.5rem;
  }}
}}
"""
    return tsx, css


# ==============================================================================
# 10. Master Hero Archetype Dispatcher (7 Archetypes)
# ==============================================================================

def render_hero_archetype(
    archetype_name: str,
    component_name: str = "Hero",
    business_name: str = "Acme",
    tagline: str = "",
    prefix: str = "hero",
    primary_color: str = "#0b0f19",
    accent_color: str = "#38bdf8",
    accent_secondary: str = "#818cf8",
    font_heading: str = "Plus Jakarta Sans",
    font_body: str = "Inter",
    border_radius: str = "8px",
    pill_buttons: bool = False,
    items: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str]:
    """
    Renders one of the 7 balanced hero archetypes (Section 3.B):
    1. 'split'
    2. 'editorial_asymmetric'
    3. 'full_bleed_visual'
    4. 'bento'
    5. 'terminal_data'
    6. 'product_stage'
    7. 'restrained_centered'
    """
    clean = archetype_name.lower().replace("-", "_").strip()

    if clean in ("split", "split_hero", "split_screen"):
        return render_split_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline or "Autonomous engineering intelligence for modern teams",
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif clean in ("editorial", "editorial_asymmetric", "editorial_asymmetric_hero", "minimal_editorial_hero"):
        return render_editorial_layout(
            component_name=component_name,
            items=items or [],
            business_name=business_name,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif clean in ("full_bleed_visual", "full_bleed_visual_hero", "full_bleed", "full_bleed_hero"):
        return render_full_bleed_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif clean in ("bento", "bento_hero", "asymmetric_bento_hero"):
        return render_bento_grid(
            component_name=component_name,
            items=items or [],
            business_name=business_name,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif clean in ("terminal_data", "terminal_data_hero", "terminal", "terminal_code_hero"):
        return render_terminal_data_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif clean in ("product_stage", "product_stage_hero", "stage"):
        return render_product_stage_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    elif clean in ("restrained_centered", "restrained_centered_hero", "centered_hero", "centered"):
        return render_restrained_centered_hero(
            component_name=component_name,
            business_name=business_name,
            tagline=tagline,
            prefix=prefix,
            primary_color=primary_color,
            accent_color=accent_color,
            accent_secondary=accent_secondary,
            font_heading=font_heading,
            font_body=font_body,
            border_radius=border_radius,
            pill_buttons=pill_buttons,
        )

    else:
        raise ValueError(f"Unknown hero archetype '{clean}'. Planner must emit a registered archetype ID.")
