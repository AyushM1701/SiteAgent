#!/usr/bin/env python3
"""
data_pipeline/generate_trajectories.py - Unified Trajectory Generator for ReactAgent SLM

Consolidates all gold-standard site trajectory batches into a single unified CLI:
  - Batch 1: Hand-crafted seed sites (Azure Food, DevSummit, Priya Sharma Portfolio)
  - Batch 2: 10 modern diverse domains (Miso & Soul, Prose.ai, Blanc Studio, etc.)
  - Batch 3: 10 premium domains (NexusPay, Lumina Dental, Atelier Nord, etc.)
  - Batch 4: 50 modern real-world commercial domains
  - Batch 5: 50 responsive enterprise & service domains
  - Interactive: Highly interactive SaaS landing pages (FlowSync AI with theme toggles & calculators)

Usage:
  python data_pipeline/generate_trajectories.py --batch all
  python data_pipeline/generate_trajectories.py --batch 1
  python data_pipeline/generate_trajectories.py --batch interactive
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_protocol import SITE_AGENT_SYSTEM_PROMPT


# ==============================================================================
# BATCH 1: Core Gold-Standard Hand-Crafted Sites
# ==============================================================================






# ── Observation helpers ────────────────────────────────────────────────────────

def obs_ok(files, next_instruction):
    lines = ['<observation status="ok">']
    lines.append("[Files accepted]:")
    for p in files:
        lines.append(f"  \u2713 {p}")
    lines.append(f"\n[NEXT SECTION REQUIRED]: {next_instruction}")
    lines.append('Write ONE <tool_call name="write_site"> with exactly one .tsx file and one .css file for this section.')
    lines.append("</observation>")
    return "\n".join(lines)

def obs_done(files):
    lines = ['<observation status="complete">']
    lines.append("[SITE BUILD COMPLETE]: All required sections have been written successfully.")
    lines.append("[Files written in this session]:")
    for p in files:
        lines.append(f"  \u2713 {p}")
    lines.append("Output a <finish> tag with a brief summary of the site you built.")
    lines.append("</observation>")
    return "\n".join(lines)

def write_site(tsx_path, tsx_code, css_path, css_code):
    return (
        f'<tool_call name="write_site">\n'
        f'<file path="{tsx_path}">\n{tsx_code}\n</file>\n'
        f'<file path="{css_path}">\n{css_code}\n</file>\n'
        f'</tool_call>'
    )

def thought(text):
    return f"<thought>\n{text}\n</thought>"

def finish(text):
    return f"<finish>\n{text}\n</finish>"

def assistant(thought_text, action_text):
    return thought_text + "\n" + action_text


# ==============================================================================
# TRAJECTORY 1: Restaurant — Azure Food Junction
# 4 sections: Header, Hero, Menu, Footer
# ==============================================================================

def trajectory_restaurant_01():
    brief_xml = """<content_brief>
  <business_name>Azure Food Junction</business_name>
  <tagline>Authentic flavors, unforgettable experiences</tagline>
  <business_type>restaurant</business_type>
  <primary_color>#0f172a</primary_color>
  <accent_color>#f59e0b</accent_color>
  <font_heading>Playfair Display</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, menu, footer</sections>
  <menu_category name="Starters">
    <item name="Spiced Lamb Kofta" price="$12">Grilled lamb with harissa yoghurt</item>
    <item name="Roasted Beet Hummus" price="$9">House-made hummus, sumac, za'atar flatbread</item>
    <item name="Calamari Fritti" price="$11">Lightly fried calamari with lemon aioli</item>
  </menu_category>
  <menu_category name="Mains">
    <item name="Saffron Chicken Tagine" price="$24">Slow-cooked with preserved lemon and olives</item>
    <item name="Grilled Swordfish" price="$28">Chermoula marinade, roasted fennel, couscous</item>
    <item name="Wild Mushroom Risotto" price="$19">Arborio rice, truffle oil, aged parmesan</item>
    <item name="Beef Short Rib" price="$32">48-hour braised, pommes puree, gremolata</item>
  </menu_category>
  <menu_category name="Desserts">
    <item name="Baklava Cheesecake" price="$10">Honey, pistachio, rosewater cream</item>
    <item name="Dark Chocolate Fondant" price="$11">Salted caramel, vanilla bean ice cream</item>
  </menu_category>
  <contact>
    <address>47 Crescent Lane, Melbourne VIC 3000</address>
    <phone>+61 3 9555 1234</phone>
    <email>reservations@azurefoodjunction.com.au</email>
    <hours>Tue-Sun 12pm-10pm | Closed Mondays</hours>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml +
        "\n\nYou will build the site ONE SECTION AT A TIME. "
        "Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the business name/logo on the left "
        "and navigation links (Home, Menu, About, Contact) on the right. "
        "Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──────────────────────────────────────────────────────────
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`header${scrolled ? ' header--scrolled' : ''}`}>
      <div className="header__inner">
        <a href="#" className="header__logo">Azure Food Junction</a>
        <nav className="header__nav" aria-label="Main navigation">
          <a href="#hero" className="header__link">Home</a>
          <a href="#menu" className="header__link">Menu</a>
          <a href="#footer" className="header__link">Contact</a>
        </nav>
        <a href="mailto:reservations@azurefoodjunction.com.au" className="header__cta">Reserve a Table</a>
      </div>
    </header>
  );
}"""

    header_css = """\
.header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(15, 23, 42, 0.96);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(245, 158, 11, 0.15);
  transition: box-shadow 0.3s ease;
}
.header--scrolled {
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
.header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}
.header__logo {
  font-family: 'Playfair Display', serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: #f59e0b;
  text-decoration: none;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.header__nav {
  display: flex;
  gap: 2rem;
  align-items: center;
}
.header__link {
  color: #cbd5e1;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  transition: color 0.2s;
}
.header__link:hover { color: #f59e0b; }
.header__cta {
  padding: 0.5rem 1.25rem;
  background: #f59e0b;
  color: #0f172a;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  text-decoration: none;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  transition: background 0.2s, transform 0.1s;
  white-space: nowrap;
}
.header__cta:hover { background: #fbbf24; transform: translateY(-1px); }
@media (max-width: 768px) {
  .header__nav { display: none; }
  .header__logo { font-size: 1.1rem; }
}"""

    t1_thought = thought(
        "I'll write the Header component first. It needs to be a sticky navbar with the Azure Food Junction branding, "
        "navigation links, and a call-to-action button. I'll use a scroll listener to add a shadow on scroll, "
        "and use the amber accent color from the brief for branding and the CTA."
    )
    t1_action = write_site("src/components/Header.tsx", header_tsx, "src/components/Header.css", header_css)
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: a full-width banner with a background image or gradient, the business tagline as an h1, "
        "a subheading, and a prominent CTA button. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    # ── Turn 2: Hero ────────────────────────────────────────────────────────────
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="hero" id="hero">
      <div className="hero__overlay" aria-hidden="true" />
      <div className="hero__content">
        <p className="hero__eyebrow">Est. 2018 · Melbourne</p>
        <h1 className="hero__title">Authentic flavors,<br />unforgettable experiences</h1>
        <p className="hero__subtitle">
          A celebration of Mediterranean and Middle Eastern cuisine crafted from
          the finest seasonal ingredients, served in the heart of the city.
        </p>
        <div className="hero__actions">
          <a href="#menu" className="hero__btn hero__btn--primary">View Our Menu</a>
          <a href="#footer" className="hero__btn hero__btn--secondary">Book a Table</a>
        </div>
      </div>
      <div className="hero__scroll-hint" aria-hidden="true">
        <span className="hero__scroll-line" />
      </div>
    </section>
  );
}"""

    hero_css = """\
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    linear-gradient(135deg, rgba(15,23,42,0.88) 0%, rgba(15,23,42,0.65) 60%, rgba(245,158,11,0.15) 100%),
    url('https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1600&q=80') center/cover no-repeat;
  overflow: hidden;
}
.hero__overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 70% 50%, rgba(245,158,11,0.08) 0%, transparent 60%);
  pointer-events: none;
}
.hero__content {
  position: relative;
  z-index: 1;
  max-width: 760px;
  padding: 2rem;
  text-align: center;
}
.hero__eyebrow {
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #f59e0b;
  margin: 0 0 1.25rem;
}
.hero__title {
  font-family: 'Playfair Display', serif;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  font-weight: 700;
  color: #f8fafc;
  line-height: 1.1;
  margin: 0 0 1.5rem;
}
.hero__subtitle {
  font-size: 1.125rem;
  color: #94a3b8;
  line-height: 1.7;
  max-width: 560px;
  margin: 0 auto 2.5rem;
}
.hero__actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}
.hero__btn {
  display: inline-block;
  padding: 0.875rem 2rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  letter-spacing: 0.03em;
  transition: all 0.2s ease;
}
.hero__btn--primary {
  background: #f59e0b;
  color: #0f172a;
}
.hero__btn--primary:hover { background: #fbbf24; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(245,158,11,0.35); }
.hero__btn--secondary {
  background: transparent;
  color: #f8fafc;
  border: 2px solid rgba(248,250,252,0.3);
}
.hero__btn--secondary:hover { border-color: #f59e0b; color: #f59e0b; transform: translateY(-2px); }
.hero__scroll-hint {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
}
.hero__scroll-line {
  display: block;
  width: 1px;
  height: 60px;
  background: linear-gradient(to bottom, transparent, #f59e0b);
  animation: scroll-pulse 2s ease-in-out infinite;
}
@keyframes scroll-pulse {
  0%, 100% { opacity: 0.3; transform: scaleY(0.6); }
  50% { opacity: 1; transform: scaleY(1); }
}"""

    t2_thought = thought(
        "The Header was accepted. Now I'll write the Hero section — a full-height banner with a cinematic restaurant image "
        "background, large serif heading using the Playfair Display font from the brief, the tagline from the content brief "
        "as the h1, and two CTAs: 'View Our Menu' and 'Book a Table'. I'll add a subtle scroll indicator animation."
    )
    t2_action = write_site("src/components/Hero.tsx", hero_tsx, "src/components/Hero.css", hero_css)
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Menu section: display the menu categories and items from the content brief. "
        "Use a card-grid layout with item name, price, and description. "
        "Files: src/components/Menu.tsx + src/components/Menu.css"
    )

    # ── Turn 3: Menu ────────────────────────────────────────────────────────────
    menu_tsx = """\
import React, { useState } from 'react';
import './Menu.css';

interface MenuItem { name: string; price: string; description: string; }
interface MenuCategory { name: string; items: MenuItem[]; }

const MENU_DATA: MenuCategory[] = [
  {
    name: 'Starters',
    items: [
      { name: 'Spiced Lamb Kofta', price: '$12', description: 'Grilled lamb with harissa yoghurt' },
      { name: 'Roasted Beet Hummus', price: '$9', description: "House-made hummus, sumac, za'atar flatbread" },
      { name: 'Calamari Fritti', price: '$11', description: 'Lightly fried calamari with lemon aioli' },
    ],
  },
  {
    name: 'Mains',
    items: [
      { name: 'Saffron Chicken Tagine', price: '$24', description: 'Slow-cooked with preserved lemon and olives' },
      { name: 'Grilled Swordfish', price: '$28', description: 'Chermoula marinade, roasted fennel, couscous' },
      { name: 'Wild Mushroom Risotto', price: '$19', description: 'Arborio rice, truffle oil, aged parmesan' },
      { name: 'Beef Short Rib', price: '$32', description: '48-hour braised, pommes puree, gremolata' },
    ],
  },
  {
    name: 'Desserts',
    items: [
      { name: 'Baklava Cheesecake', price: '$10', description: 'Honey, pistachio, rosewater cream' },
      { name: 'Dark Chocolate Fondant', price: '$11', description: 'Salted caramel, vanilla bean ice cream' },
    ],
  },
];

export function Menu() {
  const [active, setActive] = useState('Starters');
  const current = MENU_DATA.find(c => c.name === active) ?? MENU_DATA[0];

  return (
    <section className="menu" id="menu" aria-labelledby="menu-heading">
      <div className="menu__inner">
        <div className="menu__header">
          <p className="menu__eyebrow">Our Menu</p>
          <h2 id="menu-heading" className="menu__title">Crafted with Passion</h2>
          <p className="menu__subtitle">Seasonal ingredients. Bold flavours. Unforgettable plates.</p>
        </div>

        <div className="menu__tabs" role="tablist" aria-label="Menu categories">
          {MENU_DATA.map(cat => (
            <button
              key={cat.name}
              role="tab"
              aria-selected={active === cat.name}
              className={`menu__tab${active === cat.name ? ' menu__tab--active' : ''}`}
              onClick={() => setActive(cat.name)}
            >
              {cat.name}
            </button>
          ))}
        </div>

        <div
          className="menu__grid"
          role="tabpanel"
          aria-label={current.name}
        >
          {current.items.map(item => (
            <article key={item.name} className="menu__card">
              <div className="menu__card-top">
                <h3 className="menu__item-name">{item.name}</h3>
                <span className="menu__item-price">{item.price}</span>
              </div>
              <p className="menu__item-desc">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""

    menu_css = """\
.menu {
  padding: 7rem 2rem;
  background: #0f172a;
}
.menu__inner {
  max-width: 1100px;
  margin: 0 auto;
}
.menu__header {
  text-align: center;
  margin-bottom: 3.5rem;
}
.menu__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #f59e0b;
  margin: 0 0 0.75rem;
}
.menu__title {
  font-family: 'Playfair Display', serif;
  font-size: clamp(2rem, 4vw, 3rem);
  color: #f8fafc;
  margin: 0 0 1rem;
  font-weight: 700;
}
.menu__subtitle {
  color: #64748b;
  font-size: 1.05rem;
  margin: 0;
  line-height: 1.6;
}
.menu__tabs {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 3rem;
  flex-wrap: wrap;
}
.menu__tab {
  padding: 0.6rem 1.5rem;
  border: 2px solid #1e293b;
  background: transparent;
  color: #94a3b8;
  border-radius: 2rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.04em;
}
.menu__tab:hover { border-color: #f59e0b; color: #f59e0b; }
.menu__tab--active {
  background: #f59e0b;
  border-color: #f59e0b;
  color: #0f172a;
}
.menu__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
}
.menu__card {
  background: #1e293b;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 1.5rem;
  transition: transform 0.2s, border-color 0.2s;
}
.menu__card:hover {
  transform: translateY(-3px);
  border-color: rgba(245,158,11,0.3);
}
.menu__card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.75rem;
}
.menu__item-name {
  font-family: 'Playfair Display', serif;
  font-size: 1.1rem;
  color: #f8fafc;
  margin: 0;
  font-weight: 600;
  line-height: 1.3;
}
.menu__item-price {
  font-size: 1rem;
  font-weight: 700;
  color: #f59e0b;
  white-space: nowrap;
}
.menu__item-desc {
  font-size: 0.88rem;
  color: #64748b;
  margin: 0;
  line-height: 1.6;
}"""

    t3_thought = thought(
        "Hero accepted. Now the Menu section. The brief has three categories with multiple items each. "
        "I'll implement a tab-based menu with accessible role=tablist/tab/tabpanel. "
        "Each menu item gets a card with name, price and description. I'll keep the dark navy palette "
        "with amber accent for prices. Tabbed navigation avoids a wall of text."
    )
    t3_action = write_site("src/components/Menu.tsx", menu_tsx, "src/components/Menu.css", menu_css)
    t3_obs = obs_ok(
        ["src/components/Menu.tsx", "src/components/Menu.css"],
        "Write the Footer section: a dark background footer with the business name, brief nav links, "
        "contact info (address, phone, email, hours), and a copyright notice. "
        "Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    # ── Turn 4: Footer ──────────────────────────────────────────────────────────
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="footer" id="footer" aria-label="Site footer">
      <div className="footer__inner">
        <div className="footer__brand">
          <p className="footer__logo">Azure Food Junction</p>
          <p className="footer__tagline">Authentic flavors, unforgettable experiences</p>
        </div>

        <nav className="footer__nav" aria-label="Footer navigation">
          <h3 className="footer__nav-heading">Navigate</h3>
          <a href="#hero" className="footer__link">Home</a>
          <a href="#menu" className="footer__link">Menu</a>
          <a href="#footer" className="footer__link">Contact</a>
        </nav>

        <address className="footer__contact">
          <h3 className="footer__nav-heading">Visit Us</h3>
          <p>47 Crescent Lane<br />Melbourne VIC 3000</p>
          <a href="tel:+61395551234" className="footer__link">+61 3 9555 1234</a>
          <a href="mailto:reservations@azurefoodjunction.com.au" className="footer__link">
            reservations@azurefoodjunction.com.au
          </a>
          <p className="footer__hours">Tue–Sun 12pm–10pm · Closed Mondays</p>
        </address>
      </div>

      <div className="footer__bottom">
        <p>&copy; {year} Azure Food Junction. All rights reserved.</p>
        <p>Melbourne&apos;s premier Mediterranean dining experience.</p>
      </div>
    </footer>
  );
}"""

    footer_css = """\
.footer {
  background: #020617;
  border-top: 1px solid rgba(245,158,11,0.2);
  padding: 5rem 2rem 0;
}
.footer__inner {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1.5fr;
  gap: 3rem;
  padding-bottom: 3rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.footer__logo {
  font-family: 'Playfair Display', serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: #f59e0b;
  margin: 0 0 0.5rem;
}
.footer__tagline {
  font-size: 0.9rem;
  color: #475569;
  margin: 0;
  line-height: 1.6;
  max-width: 260px;
}
.footer__nav {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.footer__nav-heading {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #f59e0b;
  margin: 0 0 0.75rem;
}
.footer__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.2s;
  display: block;
}
.footer__link:hover { color: #f8fafc; }
.footer__contact {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-style: normal;
  font-size: 0.9rem;
  color: #94a3b8;
  line-height: 1.6;
}
.footer__hours {
  font-size: 0.85rem;
  color: #475569;
  margin-top: 0.25rem;
}
.footer__bottom {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: #334155;
}
@media (max-width: 768px) {
  .footer__inner { grid-template-columns: 1fr; gap: 2rem; }
  .footer__bottom { flex-direction: column; text-align: center; }
}"""

    t4_thought = thought(
        "All three main content sections are done. Now the Footer — the last required section. "
        "I'll use a three-column grid: brand/tagline, navigation, and contact info from the brief. "
        "Dark background with the amber accent for the logo and section headings. "
        "I'll include the address, phone, email and hours exactly as specified in the content brief."
    )
    t4_action = write_site("src/components/Footer.tsx", footer_tsx, "src/components/Footer.css", footer_css)

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Menu.tsx", "src/components/Menu.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)

    t5_thought = thought(
        "All four sections have been accepted: Header, Hero, Menu, and Footer. "
        "The site is complete with a dark navy/amber palette, Playfair Display headings, "
        "sticky navigation, hero banner, tabbed menu with all items from the brief, and a full contact footer."
    )
    t5_action = finish(
        "Built the complete Azure Food Junction restaurant website with 4 sections:\n"
        "- Header: sticky navbar with amber branding, nav links and CTA button\n"
        "- Hero: full-viewport banner with restaurant image, tagline h1, and two CTAs\n"
        "- Menu: tabbed interface showing all 9 menu items across 3 categories\n"
        "- Footer: three-column layout with brand, navigation, and full contact info from brief\n"
        "Color scheme: navy (#0f172a) primary, amber (#f59e0b) accent, Playfair Display headings."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_restaurant_azure_food_junction", "messages": messages}


# ==============================================================================
# TRAJECTORY 2: SaaS — FlowSync (productivity tool)
# 4 sections: Header, Hero, Features, Footer
# ==============================================================================

def trajectory_saas_01():
    brief_xml = """<content_brief>
  <business_name>FlowSync</business_name>
  <tagline>The smarter way to manage your team</tagline>
  <business_type>saas</business_type>
  <primary_color>#0d1117</primary_color>
  <accent_color>#6366f1</accent_color>
  <font_heading>Inter</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, features, footer</sections>
  <feature icon="zap" title="Real-Time Sync" description="All changes propagate instantly across every device and team member — zero delay, zero conflicts." />
  <feature icon="shield" title="Enterprise Security" description="SOC 2 Type II certified, end-to-end encryption, SSO, and granular permissions built in." />
  <feature icon="chart" title="Smart Analytics" description="AI-powered dashboards surface bottlenecks before they block your team." />
  <feature icon="users" title="Team Automations" description="Build no-code workflows that handle handoffs, reminders, and approvals automatically." />
  <feature icon="plug" title="1000+ Integrations" description="Connect with Slack, Jira, GitHub, Salesforce, and every tool your team already uses." />
  <feature icon="clock" title="Time Tracking" description="Streamlined timesheets, billable hours tracking, and budget forecasting in one place." />
  <contact>
    <email>hello@flowsync.io</email>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml +
        "\n\nYou will build the site ONE SECTION AT A TIME. "
        "Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the business name/logo on the left "
        "and navigation links (Features, Pricing, Docs, Login) on the right, plus a 'Start Free Trial' CTA button. "
        "Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──────────────────────────────────────────────────────────
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <header className={`fs-header${scrolled ? ' fs-header--bg' : ''}`} role="banner">
      <div className="fs-header__inner">
        <a href="#" className="fs-header__logo" aria-label="FlowSync home">
          <svg className="fs-header__logo-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#6366f1" stroke="#6366f1" strokeWidth="0.5"/>
          </svg>
          FlowSync
        </a>

        <nav className="fs-header__nav" aria-label="Main navigation">
          <a href="#hero" className="fs-nav__link">Overview</a>
          <a href="#features" className="fs-nav__link">Features</a>
          <a href="#footer" className="fs-nav__link">Support</a>
        </nav>

        <div className="fs-header__actions">
          <a href="#" className="fs-btn fs-btn--ghost">Log In</a>
          <a href="#" className="fs-btn fs-btn--primary">Start Free Trial</a>
        </div>

        <button
          className="fs-header__burger"
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(o => !o)}
        >
          <span /><span /><span />
        </button>
      </div>

      {menuOpen && (
        <nav className="fs-header__mobile-nav" aria-label="Mobile navigation">
          <a href="#hero" className="fs-nav__link" onClick={() => setMenuOpen(false)}>Overview</a>
          <a href="#features" className="fs-nav__link" onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#footer" className="fs-nav__link" onClick={() => setMenuOpen(false)}>Support</a>
        </nav>
      )}
    </header>
  );
}"""

    header_css = """\
.fs-header {
  position: sticky;
  top: 0;
  z-index: 200;
  width: 100%;
  transition: background 0.3s, border-color 0.3s, box-shadow 0.3s;
  border-bottom: 1px solid transparent;
}
.fs-header--bg {
  background: rgba(13, 17, 23, 0.95);
  backdrop-filter: blur(16px);
  border-color: rgba(99, 102, 241, 0.15);
  box-shadow: 0 2px 32px rgba(0,0,0,0.5);
}
.fs-header__inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 68px;
  display: flex;
  align-items: center;
  gap: 2rem;
}
.fs-header__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 800;
  font-size: 1.2rem;
  color: #f1f5f9;
  text-decoration: none;
  letter-spacing: -0.02em;
  margin-right: auto;
}
.fs-header__logo-icon { width: 24px; height: 24px; }
.fs-header__nav {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}
.fs-nav__link {
  padding: 0.4rem 0.85rem;
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.fs-nav__link:hover { color: #f1f5f9; background: rgba(255,255,255,0.05); }
.fs-header__actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.fs-btn {
  padding: 0.5rem 1.1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;
}
.fs-btn--ghost { color: #94a3b8; background: transparent; }
.fs-btn--ghost:hover { color: #f1f5f9; background: rgba(255,255,255,0.06); }
.fs-btn--primary { background: #6366f1; color: white; }
.fs-btn--primary:hover { background: #4f46e5; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99,102,241,0.35); }
.fs-header__burger { display: none; flex-direction: column; gap: 4px; background: none; border: none; cursor: pointer; padding: 4px; }
.fs-header__burger span { display: block; width: 20px; height: 2px; background: #94a3b8; border-radius: 2px; }
.fs-header__mobile-nav {
  display: flex;
  flex-direction: column;
  padding: 1rem 2rem;
  background: rgba(13,17,23,0.98);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  gap: 0.25rem;
}
@media (max-width: 768px) {
  .fs-header__nav { display: none; }
  .fs-header__actions { display: none; }
  .fs-header__burger { display: flex; }
}"""

    t1_thought = thought(
        "I'll build the FlowSync header. SaaS headers need to feel polished and professional — "
        "transparent at top, blurred glass background on scroll. I'll include the lightning bolt icon, "
        "navigation links, and a two-button actions group (Login + primary CTA). "
        "I'll also add a mobile hamburger menu for responsiveness."
    )
    t1_action = write_site("src/components/Header.tsx", header_tsx, "src/components/Header.css", header_css)
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: a full-width hero with a large headline, subheading, CTA buttons, "
        "and a dashboard/app mockup visual. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    # ── Turn 2: Hero ────────────────────────────────────────────────────────────
    hero_tsx = """\
import React from 'react';
import './Hero.css';

const STATS = [
  { value: '50k+', label: 'Teams' },
  { value: '99.9%', label: 'Uptime' },
  { value: '4.9★', label: 'Rating' },
  { value: '<200ms', label: 'Latency' },
];

export function Hero() {
  return (
    <section className="fsh" id="hero" aria-labelledby="fsh-headline">
      <div className="fsh__glow" aria-hidden="true" />
      <div className="fsh__inner">
        <div className="fsh__content">
          <div className="fsh__badge">
            <span className="fsh__badge-dot" aria-hidden="true" />
            Now with AI-powered task prediction
          </div>
          <h1 id="fsh-headline" className="fsh__headline">
            The smarter way<br />to manage your team
          </h1>
          <p className="fsh__sub">
            FlowSync gives growing teams real-time collaboration, automated workflows,
            and deep analytics — all in one beautifully simple platform.
          </p>
          <div className="fsh__actions">
            <a href="#" className="fsh__btn fsh__btn--primary">
              Start for Free
              <svg viewBox="0 0 20 20" fill="currentColor" className="fsh__btn-icon" aria-hidden="true">
                <path fillRule="evenodd" d="M10.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L12.586 11H5a1 1 0 110-2h7.586l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd"/>
              </svg>
            </a>
            <a href="#features" className="fsh__btn fsh__btn--secondary">See Features</a>
          </div>
          <ul className="fsh__stats" aria-label="Key statistics">
            {STATS.map(s => (
              <li key={s.label} className="fsh__stat">
                <span className="fsh__stat-value">{s.value}</span>
                <span className="fsh__stat-label">{s.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="fsh__visual" aria-hidden="true">
          <div className="fsh__mockup">
            <div className="fsh__mock-bar">
              <span className="fsh__dot fsh__dot--red" />
              <span className="fsh__dot fsh__dot--yellow" />
              <span className="fsh__dot fsh__dot--green" />
              <span className="fsh__mock-title">FlowSync — Q4 Sprint</span>
            </div>
            <div className="fsh__mock-body">
              {['Design System', 'API Integration', 'User Testing', 'Performance', 'Launch Prep'].map((task, i) => (
                <div key={task} className="fsh__task-row">
                  <div className={`fsh__task-check${i < 3 ? ' fsh__task-check--done' : ''}`}>
                    {i < 3 && <svg viewBox="0 0 12 12" fill="none"><path d="M2 6l3 3 5-5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/></svg>}
                  </div>
                  <span className={`fsh__task-name${i < 3 ? ' fsh__task-name--done' : ''}`}>{task}</span>
                  <span className="fsh__task-tag" style={{background: ['#6366f1','#06b6d4','#10b981','#f59e0b','#6366f1'][i] + '22', color: ['#818cf8','#67e8f9','#6ee7b7','#fcd34d','#818cf8'][i]}}>
                    {['Design','Dev','QA','Ops','All'][i]}
                  </span>
                </div>
              ))}
              <div className="fsh__progress-row">
                <span className="fsh__progress-label">Sprint Progress</span>
                <div className="fsh__progress-bar"><div className="fsh__progress-fill" style={{width:'60%'}} /></div>
                <span className="fsh__progress-pct">60%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}"""

    hero_css = """\
.fsh {
  position: relative;
  overflow: hidden;
  padding: 7rem 2rem 5rem;
  background: #0d1117;
}
.fsh__glow {
  position: absolute;
  top: -20%;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(99,102,241,0.18) 0%, transparent 65%);
  pointer-events: none;
}
.fsh__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4rem;
  align-items: center;
}
.fsh__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.9rem;
  border-radius: 2rem;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.3);
  font-size: 0.8rem;
  color: #a5b4fc;
  font-weight: 500;
  margin-bottom: 1.5rem;
}
.fsh__badge-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #6366f1;
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.7); }
}
.fsh__headline {
  font-size: clamp(2.2rem, 4.5vw, 3.75rem);
  font-weight: 800;
  color: #f1f5f9;
  line-height: 1.1;
  letter-spacing: -0.03em;
  margin: 0 0 1.25rem;
}
.fsh__sub {
  font-size: 1.1rem;
  color: #64748b;
  line-height: 1.75;
  margin: 0 0 2.5rem;
  max-width: 480px;
}
.fsh__actions { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 3rem; }
.fsh__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  transition: all 0.2s;
}
.fsh__btn-icon { width: 16px; height: 16px; }
.fsh__btn--primary { background: #6366f1; color: white; }
.fsh__btn--primary:hover { background: #4f46e5; box-shadow: 0 8px 24px rgba(99,102,241,0.4); transform: translateY(-2px); }
.fsh__btn--secondary { background: rgba(255,255,255,0.06); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1); }
.fsh__btn--secondary:hover { background: rgba(255,255,255,0.1); color: #f1f5f9; }
.fsh__stats {
  display: flex;
  gap: 2rem;
  list-style: none;
  margin: 0;
  padding: 0;
  flex-wrap: wrap;
}
.fsh__stat { display: flex; flex-direction: column; gap: 0.1rem; }
.fsh__stat-value { font-size: 1.4rem; font-weight: 800; color: #f1f5f9; letter-spacing: -0.03em; }
.fsh__stat-label { font-size: 0.75rem; color: #475569; font-weight: 500; text-transform: uppercase; letter-spacing: 0.1em; }
.fsh__mockup {
  background: #161b22;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(99,102,241,0.1);
}
.fsh__mock-bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.75rem 1rem;
  background: #0d1117;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.fsh__dot { display: block; width: 10px; height: 10px; border-radius: 50%; }
.fsh__dot--red { background: #ff5f56; }
.fsh__dot--yellow { background: #febc2e; }
.fsh__dot--green { background: #27c840; }
.fsh__mock-title { font-size: 0.78rem; color: #475569; margin-left: 0.5rem; }
.fsh__mock-body { padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; }
.fsh__task-row { display: flex; align-items: center; gap: 0.75rem; }
.fsh__task-check {
  width: 18px; height: 18px;
  border-radius: 5px;
  border: 2px solid #1e293b;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.fsh__task-check--done { background: #6366f1; border-color: #6366f1; }
.fsh__task-check svg { width: 10px; height: 10px; }
.fsh__task-name { font-size: 0.88rem; color: #cbd5e1; flex: 1; }
.fsh__task-name--done { text-decoration: line-through; color: #475569; }
.fsh__task-tag { font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 4px; }
.fsh__progress-row { display: flex; align-items: center; gap: 0.75rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.06); }
.fsh__progress-label { font-size: 0.78rem; color: #475569; white-space: nowrap; }
.fsh__progress-bar { flex: 1; height: 5px; background: #1e293b; border-radius: 3px; overflow: hidden; }
.fsh__progress-fill { height: 100%; background: #6366f1; border-radius: 3px; transition: width 0.8s ease; }
.fsh__progress-pct { font-size: 0.78rem; color: #6366f1; font-weight: 600; white-space: nowrap; }
@media (max-width: 900px) {
  .fsh__inner { grid-template-columns: 1fr; }
  .fsh__visual { order: -1; }
}"""

    t2_thought = thought(
        "Header accepted. Now the hero section. SaaS heroes work best with a split layout: "
        "copy on the left, a product mockup on the right. I'll build an interactive-looking app mockup "
        "using pure CSS/JSX (no images needed) showing a task list with progress. "
        "The indigo accent color gives it that modern SaaS feel. Stats row beneath the CTAs adds credibility."
    )
    t2_action = write_site("src/components/Hero.tsx", hero_tsx, "src/components/Hero.css", hero_css)
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Features section: display each feature from the content brief as a card with icon (use SVG or emoji), "
        "title, and description. Use a responsive 3-column grid. "
        "Files: src/components/Features.tsx + src/components/Features.css"
    )

    # ── Turn 3: Features ────────────────────────────────────────────────────────
    features_tsx = """\
import React from 'react';
import './Features.css';

interface Feature { icon: string; title: string; description: string; }

const FEATURES: Feature[] = [
  { icon: '\u26a1', title: 'Real-Time Sync', description: 'All changes propagate instantly across every device and team member \u2014 zero delay, zero conflicts.' },
  { icon: '\uD83D\uDEE1\uFE0F', title: 'Enterprise Security', description: 'SOC 2 Type II certified, end-to-end encryption, SSO, and granular permissions built in.' },
  { icon: '\uD83D\uDCCA', title: 'Smart Analytics', description: 'AI-powered dashboards surface bottlenecks before they block your team.' },
  { icon: '\uD83D\uDC65', title: 'Team Automations', description: 'Build no-code workflows that handle handoffs, reminders, and approvals automatically.' },
  { icon: '\uD83D\uDD0C', title: '1000+ Integrations', description: 'Connect with Slack, Jira, GitHub, Salesforce, and every tool your team already uses.' },
  { icon: '\u23F0', title: 'Time Tracking', description: 'Streamlined timesheets, billable hours tracking, and budget forecasting in one place.' },
];

export function Features() {
  return (
    <section className="feat" id="features" aria-labelledby="feat-heading">
      <div className="feat__inner">
        <div className="feat__header">
          <p className="feat__eyebrow">Everything you need</p>
          <h2 id="feat-heading" className="feat__title">Built for teams that move fast</h2>
          <p className="feat__subtitle">
            Six powerful capabilities, one unified workspace. No juggling tools, no context switching.
          </p>
        </div>
        <ul className="feat__grid" aria-label="Product features">
          {FEATURES.map((f, i) => (
            <li key={f.title} className="feat__card" style={{'--i': i} as React.CSSProperties}>
              <div className="feat__icon" aria-hidden="true">{f.icon}</div>
              <h3 className="feat__card-title">{f.title}</h3>
              <p className="feat__card-desc">{f.description}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}"""

    features_css = """\
.feat {
  padding: 7rem 2rem;
  background: linear-gradient(180deg, #0d1117 0%, #0a0e18 100%);
  border-top: 1px solid rgba(255,255,255,0.04);
}
.feat__inner { max-width: 1200px; margin: 0 auto; }
.feat__header { text-align: center; margin-bottom: 4rem; }
.feat__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #6366f1;
  margin: 0 0 0.75rem;
}
.feat__title {
  font-size: clamp(1.8rem, 3.5vw, 2.75rem);
  font-weight: 800;
  color: #f1f5f9;
  margin: 0 0 1rem;
  letter-spacing: -0.02em;
}
.feat__subtitle {
  font-size: 1.05rem;
  color: #475569;
  max-width: 520px;
  margin: 0 auto;
  line-height: 1.7;
}
.feat__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.feat__card {
  padding: 1.75rem;
  background: #161b22;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  transition: border-color 0.25s, transform 0.25s, box-shadow 0.25s;
  animation: feat-in 0.5s ease both;
  animation-delay: calc(var(--i, 0) * 80ms);
}
.feat__card:hover {
  border-color: rgba(99,102,241,0.35);
  transform: translateY(-4px);
  box-shadow: 0 16px 48px rgba(0,0,0,0.4), 0 0 0 1px rgba(99,102,241,0.12);
}
@keyframes feat-in {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
.feat__icon {
  font-size: 1.75rem;
  line-height: 1;
  margin-bottom: 1rem;
  display: block;
}
.feat__card-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 0.6rem;
  letter-spacing: -0.01em;
}
.feat__card-desc {
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.65;
  margin: 0;
}
@media (max-width: 900px) { .feat__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .feat__grid { grid-template-columns: 1fr; } }"""

    t3_thought = thought(
        "Hero accepted. Now the Features section. The brief has 6 features. I'll use a 3x2 grid "
        "with card hover effects and staggered entrance animations (using CSS custom property --i). "
        "Emoji icons work perfectly here — no SVG sprite needed. The indigo glow on hover "
        "maintains visual consistency with the hero section."
    )
    t3_action = write_site("src/components/Features.tsx", features_tsx, "src/components/Features.css", features_css)
    t3_obs = obs_ok(
        ["src/components/Features.tsx", "src/components/Features.css"],
        "Write the Footer section: a dark footer with the FlowSync logo/brand, brief links, "
        "contact email, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    # ── Turn 4: Footer ──────────────────────────────────────────────────────────
    footer_tsx = """\
import React from 'react';
import './Footer.css';

const LINKS = [
  { heading: 'Product', links: ['Features', 'Pricing', 'Changelog', 'Roadmap'] },
  { heading: 'Company', links: ['About', 'Blog', 'Careers', 'Press'] },
  { heading: 'Resources', links: ['Documentation', 'API Reference', 'Status', 'Security'] },
];

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="fsf" id="footer" aria-label="Site footer">
      <div className="fsf__inner">
        <div className="fsf__brand">
          <p className="fsf__logo">
            <svg viewBox="0 0 24 24" fill="none" className="fsf__logo-icon" aria-hidden="true">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#6366f1"/>
            </svg>
            FlowSync
          </p>
          <p className="fsf__tagline">The smarter way to manage your team.</p>
          <a href="mailto:hello@flowsync.io" className="fsf__email">hello@flowsync.io</a>
        </div>
        {LINKS.map(col => (
          <nav key={col.heading} className="fsf__col" aria-label={col.heading}>
            <h3 className="fsf__col-heading">{col.heading}</h3>
            {col.links.map(l => <a key={l} href="#" className="fsf__link">{l}</a>)}
          </nav>
        ))}
      </div>
      <div className="fsf__bottom">
        <p>&copy; {year} FlowSync, Inc. All rights reserved.</p>
        <div className="fsf__legal">
          <a href="#" className="fsf__legal-link">Privacy</a>
          <a href="#" className="fsf__legal-link">Terms</a>
          <a href="#" className="fsf__legal-link">Cookies</a>
        </div>
      </div>
    </footer>
  );
}"""

    footer_css = """\
.fsf {
  background: #020617;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding: 5rem 2rem 0;
}
.fsf__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 3rem;
  padding-bottom: 3rem;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.fsf__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.15rem;
  font-weight: 800;
  color: #f1f5f9;
  margin: 0 0 0.75rem;
  letter-spacing: -0.02em;
}
.fsf__logo-icon { width: 20px; height: 20px; }
.fsf__tagline { font-size: 0.9rem; color: #334155; line-height: 1.6; margin: 0 0 1rem; max-width: 240px; }
.fsf__email { font-size: 0.875rem; color: #6366f1; text-decoration: none; }
.fsf__email:hover { color: #818cf8; text-decoration: underline; }
.fsf__col { display: flex; flex-direction: column; gap: 0.6rem; }
.fsf__col-heading {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #f1f5f9;
  margin: 0 0 0.5rem;
}
.fsf__link { font-size: 0.875rem; color: #475569; text-decoration: none; transition: color 0.15s; }
.fsf__link:hover { color: #94a3b8; }
.fsf__bottom {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: #1e293b;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.fsf__legal { display: flex; gap: 1.5rem; }
.fsf__legal-link { color: #1e293b; text-decoration: none; }
.fsf__legal-link:hover { color: #475569; }
@media (max-width: 900px) {
  .fsf__inner { grid-template-columns: 1fr 1fr; }
  .fsf__brand { grid-column: 1 / -1; }
}"""

    t4_thought = thought(
        "Features section done. Now the Footer. I'll use a 4-column grid layout "
        "(brand column + 3 link columns matching standard SaaS footer patterns) with the contact email "
        "from the brief, copyright, and legal links. The indigo logo icon provides visual continuity."
    )
    t4_action = write_site("src/components/Footer.tsx", footer_tsx, "src/components/Footer.css", footer_css)

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Features.tsx", "src/components/Features.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)

    t5_thought = thought("All four sections built and accepted. The FlowSync site is complete.")
    t5_action = finish(
        "Built the complete FlowSync SaaS landing page with 4 sections:\n"
        "- Header: transparent-to-glass sticky nav with mobile hamburger, Login and CTA buttons\n"
        "- Hero: split layout with headline, stats, two CTAs, and animated app task-list mockup\n"
        "- Features: 3-column grid of all 6 features from the brief with stagger animations\n"
        "- Footer: 4-column layout with brand, product/company/resources links, email and legal\n"
        "Color scheme: near-black (#0d1117), indigo (#6366f1) accent, Inter throughout."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_saas_flowsync", "messages": messages}


# ==============================================================================
# TRAJECTORY 3: Portfolio — Developer personal site
# 3 sections: Header, Hero (with projects inline), Footer
# ==============================================================================

def trajectory_portfolio_01():
    brief_xml = """<content_brief>
  <business_name>Priya Sharma</business_name>
  <tagline>Full-Stack Engineer &amp; Open Source Contributor</tagline>
  <business_type>portfolio</business_type>
  <primary_color>#0a0a0f</primary_color>
  <accent_color>#22d3ee</accent_color>
  <font_heading>Inter</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, footer</sections>
  <projects>
    <project name="Nexus ORM" description="Type-safe database query builder for Node.js with zero runtime overhead." tech="TypeScript, Node.js, PostgreSQL" />
    <project name="VizBoard" description="Open-source real-time analytics dashboard with drag-and-drop widgets." tech="React, WebSockets, D3.js" />
    <project name="Patchwork CLI" description="Git-powered patch management tool used by 8k+ developers." tech="Rust, Git, CLI" />
  </projects>
  <skills>TypeScript, React, Node.js, Rust, PostgreSQL, AWS, Docker, GraphQL</skills>
  <contact>
    <email>priya@priyasharma.dev</email>
    <github>github.com/priyasharma</github>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml +
        "\n\nYou will build the site ONE SECTION AT A TIME. "
        "Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a minimal sticky header with the developer name on the left "
        "and links to Projects, Skills, and Contact on the right. "
        "Files: src/components/Header.tsx + src/components/Header.css"
    )

    header_tsx = """\
import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="pf-header" role="banner">
      <div className="pf-header__inner">
        <a href="#" className="pf-header__name" aria-label="Priya Sharma - Home">
          Priya Sharma<span className="pf-header__cursor" aria-hidden="true">_</span>
        </a>
        <nav className="pf-header__nav" aria-label="Main navigation">
          <a href="#projects" className="pf-header__link">Projects</a>
          <a href="#skills" className="pf-header__link">Skills</a>
          <a href="#contact" className="pf-header__link">Contact</a>
          <a
            href="https://github.com/priyasharma"
            className="pf-header__gh"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub profile"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="pf-header__gh-icon">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
          </a>
        </nav>
      </div>
    </header>
  );
}"""

    header_css = """\
.pf-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(10, 10, 15, 0.92);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.pf-header__inner {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pf-header__name {
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
  text-decoration: none;
  letter-spacing: -0.02em;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
.pf-header__cursor {
  color: #22d3ee;
  animation: blink 1.2s step-start infinite;
}
@keyframes blink { 50% { opacity: 0; } }
.pf-header__nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.pf-header__link {
  padding: 0.35rem 0.75rem;
  color: #64748b;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.pf-header__link:hover { color: #f1f5f9; background: rgba(255,255,255,0.06); }
.pf-header__gh {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  color: #64748b;
  transition: color 0.15s, background 0.15s;
  margin-left: 0.25rem;
}
.pf-header__gh:hover { color: #22d3ee; background: rgba(34,211,238,0.08); }
.pf-header__gh-icon { width: 18px; height: 18px; }"""

    t1_thought = thought(
        "Building a developer portfolio header. I'll go minimal and terminal-inspired: "
        "monospace name with a blinking cursor in the cyan accent color, "
        "simple nav links, and a GitHub icon button. Very clean, developer-appropriate."
    )
    t1_action = write_site("src/components/Header.tsx", header_tsx, "src/components/Header.css", header_css)
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: developer intro with name/title, a short bio, CTA buttons (View Projects, Contact), "
        "a skills/tech stack list, and a projects showcase grid. Include all 3 projects from the brief. "
        "Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    hero_tsx = """\
import React from 'react';
import './Hero.css';

const SKILLS = ['TypeScript', 'React', 'Node.js', 'Rust', 'PostgreSQL', 'AWS', 'Docker', 'GraphQL'];

interface Project { name: string; description: string; tech: string[]; }
const PROJECTS: Project[] = [
  { name: 'Nexus ORM', description: 'Type-safe database query builder for Node.js with zero runtime overhead.', tech: ['TypeScript', 'Node.js', 'PostgreSQL'] },
  { name: 'VizBoard', description: 'Open-source real-time analytics dashboard with drag-and-drop widgets.', tech: ['React', 'WebSockets', 'D3.js'] },
  { name: 'Patchwork CLI', description: 'Git-powered patch management tool used by 8k+ developers.', tech: ['Rust', 'Git', 'CLI'] },
];

export function Hero() {
  return (
    <main>
      <section className="pf-intro" aria-labelledby="pf-name">
        <div className="pf-intro__inner">
          <div className="pf-intro__content">
            <p className="pf-intro__greeting" aria-hidden="true">Hi, I&apos;m</p>
            <h1 id="pf-name" className="pf-intro__name">Priya Sharma</h1>
            <p className="pf-intro__title">Full-Stack Engineer &amp; Open Source Contributor</p>
            <p className="pf-intro__bio">
              I build high-performance systems and beautiful interfaces.
              Currently focusing on developer tooling and real-time web infrastructure.
              Open to senior IC and staff engineer roles.
            </p>
            <div className="pf-intro__actions">
              <a href="#projects" className="pf-intro__btn pf-intro__btn--primary">View Projects</a>
              <a href="mailto:priya@priyasharma.dev" className="pf-intro__btn pf-intro__btn--secondary">Contact Me</a>
            </div>
            <div className="pf-intro__skills" id="skills" aria-label="Technical skills">
              {SKILLS.map(s => <span key={s} className="pf-skill">{s}</span>)}
            </div>
          </div>
          <div className="pf-intro__avatar" aria-hidden="true">
            <div className="pf-avatar-ring">
              <div className="pf-avatar-inner">PS</div>
            </div>
            <div className="pf-avatar-badge">\uD83D\uDCBB Available</div>
          </div>
        </div>
      </section>

      <section className="pf-projects" id="projects" aria-labelledby="proj-heading">
        <div className="pf-projects__inner">
          <h2 id="proj-heading" className="pf-projects__heading">Featured Projects</h2>
          <div className="pf-projects__grid">
            {PROJECTS.map(p => (
              <article key={p.name} className="pf-proj-card">
                <div className="pf-proj-card__top">
                  <svg className="pf-proj-card__folder" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" stroke="#22d3ee" strokeWidth="1.5"/>
                  </svg>
                  <div className="pf-proj-card__links">
                    <a href="https://github.com/priyasharma" target="_blank" rel="noopener noreferrer" aria-label={`${p.name} on GitHub`}>
                      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="pf-proj-card__icon">
                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                      </svg>
                    </a>
                  </div>
                </div>
                <h3 className="pf-proj-card__name">{p.name}</h3>
                <p className="pf-proj-card__desc">{p.description}</p>
                <ul className="pf-proj-card__tech" aria-label="Technologies used">
                  {p.tech.map(t => <li key={t} className="pf-tech-badge">{t}</li>)}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}"""

    hero_css = """\
.pf-intro {
  padding: 8rem 2rem 5rem;
  background: #0a0a0f;
}
.pf-intro__inner {
  max-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4rem;
  align-items: center;
}
.pf-intro__greeting {
  font-size: 0.9rem;
  color: #22d3ee;
  font-family: 'JetBrains Mono', monospace;
  margin: 0 0 0.5rem;
}
.pf-intro__name {
  font-size: clamp(2.5rem, 5vw, 4rem);
  font-weight: 800;
  color: #f1f5f9;
  margin: 0 0 0.5rem;
  letter-spacing: -0.03em;
}
.pf-intro__title {
  font-size: 1.1rem;
  color: #22d3ee;
  font-weight: 600;
  margin: 0 0 1.5rem;
}
.pf-intro__bio {
  font-size: 1rem;
  color: #64748b;
  line-height: 1.75;
  margin: 0 0 2rem;
  max-width: 480px;
}
.pf-intro__actions { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 2rem; }
.pf-intro__btn {
  padding: 0.65rem 1.4rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  transition: all 0.2s;
}
.pf-intro__btn--primary { background: #22d3ee; color: #0a0a0f; }
.pf-intro__btn--primary:hover { background: #67e8f9; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(34,211,238,0.25); }
.pf-intro__btn--secondary { background: transparent; color: #94a3b8; border: 1px solid rgba(255,255,255,0.12); }
.pf-intro__btn--secondary:hover { border-color: #22d3ee; color: #22d3ee; }
.pf-intro__skills { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.pf-skill {
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(34,211,238,0.08);
  border: 1px solid rgba(34,211,238,0.2);
  color: #22d3ee;
}
.pf-avatar-ring {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: conic-gradient(from 0deg, #22d3ee, #6366f1, #f59e0b, #22d3ee);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: avatar-spin 12s linear infinite;
}
@keyframes avatar-spin { to { transform: rotate(360deg); } }
.pf-avatar-inner {
  width: 148px;
  height: 148px;
  border-radius: 50%;
  background: #161b22;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  font-weight: 800;
  color: #f1f5f9;
  letter-spacing: -0.05em;
}
.pf-avatar-badge {
  margin-top: 0.75rem;
  text-align: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: #22d3ee;
  background: rgba(34,211,238,0.1);
  border: 1px solid rgba(34,211,238,0.25);
  padding: 0.25rem 0.75rem;
  border-radius: 2rem;
}
.pf-projects {
  padding: 5rem 2rem 7rem;
  background: #0a0a0f;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.pf-projects__inner { max-width: 1000px; margin: 0 auto; }
.pf-projects__heading {
  font-size: 1.75rem;
  font-weight: 800;
  color: #f1f5f9;
  margin: 0 0 2.5rem;
  letter-spacing: -0.02em;
}
.pf-projects__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}
.pf-proj-card {
  padding: 1.5rem;
  background: #161b22;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: border-color 0.2s, transform 0.2s;
}
.pf-proj-card:hover { border-color: rgba(34,211,238,0.3); transform: translateY(-4px); }
.pf-proj-card__top { display: flex; justify-content: space-between; align-items: flex-start; }
.pf-proj-card__folder { width: 36px; height: 36px; }
.pf-proj-card__links { display: flex; gap: 0.5rem; }
.pf-proj-card__icon { width: 18px; height: 18px; }
.pf-proj-card__links a { color: #475569; transition: color 0.15s; }
.pf-proj-card__links a:hover { color: #22d3ee; }
.pf-proj-card__name { font-size: 1.05rem; font-weight: 700; color: #f1f5f9; margin: 0; }
.pf-proj-card__desc { font-size: 0.875rem; color: #475569; line-height: 1.6; margin: 0; flex: 1; }
.pf-proj-card__tech { display: flex; flex-wrap: wrap; gap: 0.4rem; list-style: none; margin: 0; padding: 0; }
.pf-tech-badge { font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
.pf-tech-badge:not(:last-child)::after { content: ' · '; color: #334155; }
@media (max-width: 900px) { .pf-projects__grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 600px) {
  .pf-intro__inner { grid-template-columns: 1fr; }
  .pf-intro__avatar { display: none; }
  .pf-projects__grid { grid-template-columns: 1fr; }
}"""

    t2_thought = thought(
        "For the developer portfolio, I'll combine the intro/hero and projects into one component "
        "(the brief has only 3 sections, and this section is meant to cover both intro and projects). "
        "The rotating gradient avatar ring gives a distinctive visual, and the cyan accent matches the brief. "
        "I'll use monospace fonts for the tech badges to reinforce the developer aesthetic. "
        "All three projects from the brief are rendered as cards."
    )
    t2_action = write_site("src/components/Hero.tsx", hero_tsx, "src/components/Hero.css", hero_css)
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Footer section: a minimal footer with the developer name, email, GitHub link, and copyright. "
        "Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="pf-footer" id="contact" aria-label="Site footer">
      <div className="pf-footer__inner">
        <div className="pf-footer__brand">
          <p className="pf-footer__name">Priya Sharma</p>
          <p className="pf-footer__tagline">Full-Stack Engineer &amp; Open Source Contributor</p>
        </div>
        <div className="pf-footer__links" aria-label="Contact links">
          <a href="mailto:priya@priyasharma.dev" className="pf-footer__link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="pf-footer__link-icon" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
            </svg>
            priya@priyasharma.dev
          </a>
          <a href="https://github.com/priyasharma" target="_blank" rel="noopener noreferrer" className="pf-footer__link">
            <svg viewBox="0 0 24 24" fill="currentColor" className="pf-footer__link-icon" aria-hidden="true">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            github.com/priyasharma
          </a>
        </div>
        <p className="pf-footer__copy">&copy; {year} Priya Sharma. Built with React + TypeScript.</p>
      </div>
    </footer>
  );
}"""

    footer_css = """\
.pf-footer {
  background: #020617;
  border-top: 1px solid rgba(255,255,255,0.06);
  padding: 3rem 2rem;
}
.pf-footer__inner {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  text-align: center;
}
.pf-footer__name {
  font-size: 1.15rem;
  font-weight: 800;
  color: #f1f5f9;
  margin: 0;
  letter-spacing: -0.02em;
}
.pf-footer__tagline { font-size: 0.875rem; color: #334155; margin: 0.25rem 0 0; }
.pf-footer__links {
  display: flex;
  gap: 2rem;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
}
.pf-footer__link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #475569;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.15s;
}
.pf-footer__link:hover { color: #22d3ee; }
.pf-footer__link-icon { width: 16px; height: 16px; flex-shrink: 0; }
.pf-footer__copy { font-size: 0.78rem; color: #1e293b; margin: 0; }"""

    t3_thought = thought(
        "Hero and projects accepted. Final section: a minimal centered footer with the developer name, "
        "tagline, email and GitHub links from the brief, plus a copyright line. "
        "Very clean, appropriate for a developer portfolio."
    )
    t3_action = write_site("src/components/Footer.tsx", footer_tsx, "src/components/Footer.css", footer_css)

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)

    t4_thought = thought("All three sections complete. The portfolio site is built.")
    t4_action = finish(
        "Built the complete Priya Sharma developer portfolio with 3 sections:\n"
        "- Header: monospace name with blinking cursor, nav links, GitHub icon\n"
        "- Hero + Projects: intro with rotating gradient avatar, bio, CTAs, tech skill badges, and 3 project cards\n"
        "- Footer: centered minimal layout with email and GitHub links\n"
        "Color scheme: near-black (#0a0a0f), cyan (#22d3ee) accent, Inter/monospace typography."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
    ]
    return {"task_id": "site_portfolio_priya_sharma", "messages": messages}


# ==============================================================================
# MAIN: generate and write JSONL
# ==============================================================================


# ==============================================================================
# BATCH 2: 10 Modern Domains
# ==============================================================================


# ─────────────────────────────────────────────────────────────────────────
# 1. trajectory_restaurant_02 — Miso & Soul (ramen bar)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_restaurant_02():
    brief_xml = """<content_brief>
  <business_name>Miso & Soul</business_name>
  <tagline>Broth-first ramen, made from scratch daily</tagline>
  <business_type>restaurant</business_type>
  <primary_color>#0d0d0d</primary_color>
  <accent_color>#dc2626</accent_color>
  <font_heading>Noto Serif JP</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, menu, footer</sections>
  <menu_category name="Ramen">
    <item name="Tonkotsu Classic" price="$16">18-hour pork bone broth, chashu, ajitama, nori</item>
    <item name="Spicy Miso" price="$17">Fermented miso broth, ground pork, chili oil, corn</item>
    <item name="Shoyu Chicken" price="$15">Clear soy broth, roast chicken, menma, scallion</item>
    <item name="Vegan Shiitake" price="$14">Shiitake-kombu broth, tofu, mushrooms, seasonal greens</item>
  </menu_category>
  <menu_category name="Sides">
    <item name="Karaage" price="$9">Japanese fried chicken thigh, yuzu kosho mayo</item>
    <item name="Gyoza (5pc)" price="$8">Pan-seared pork dumplings, chili vinegar</item>
    <item name="Steamed Bao (2pc)" price="$7">Pork belly, hoisin, pickled cucumber</item>
  </menu_category>
  <menu_category name="Drinks">
    <item name="Ramune" price="$4">Classic Japanese marble soda</item>
    <item name="Asahi Draft" price="$8">Japanese lager, 425ml</item>
    <item name="Iced Genmaicha" price="$5">Roasted brown rice green tea</item>
  </menu_category>
  <contact>
    <address>88 Ramen Row, Sydney NSW 2000</address>
    <phone>+61 2 9333 8888</phone>
    <email>hello@misoandsoul.com.au</email>
    <hours>Mon-Sun 11am-11pm</hours>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the "
        "business name/logo on the left and navigation links (Home, Menu, About, Contact) on "
        "the right. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`ms-header${scrolled ? ' ms-header--scrolled' : ''}`}>
      <div className="ms-header__inner">
        <a href="#" className="ms-header__logo">Miso &amp; Soul</a>
        <nav className="ms-header__nav" aria-label="Main navigation">
          <a href="#hero" className="ms-header__link">Home</a>
          <a href="#menu" className="ms-header__link">Menu</a>
          <a href="#footer" className="ms-header__link">Contact</a>
        </nav>
      </div>
    </header>
  );
}"""
    header_css = """\
.ms-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(13, 13, 13, 0.9);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(220, 38, 38, 0.15);
  transition: box-shadow 0.3s ease, background 0.3s ease;
}
.ms-header--scrolled {
  background: rgba(13, 13, 13, 0.98);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}
.ms-header__inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ms-header__logo {
  font-family: 'Noto Serif JP', serif;
  font-size: 1.3rem;
  font-weight: 700;
  color: #f5f5f4;
  text-decoration: none;
  letter-spacing: 0.02em;
}
.ms-header__nav {
  display: flex;
  gap: 2rem;
}
.ms-header__link {
  color: #a8a29e;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  transition: color 0.2s;
  position: relative;
}
.ms-header__link:hover { color: #dc2626; }
@media (max-width: 700px) {
  .ms-header__nav { gap: 1.1rem; }
  .ms-header__logo { font-size: 1.1rem; }
}"""
    t1_thought = thought(
        "Building the Miso & Soul header. Ramen bars benefit from a dark, moody, "
        "restaurant-noir feel, so I'm using near-black background with a subtle red "
        "accent border that appears on scroll. The logo uses the Noto Serif JP heading "
        "font for an authentic Japanese typographic touch, while nav links stay in "
        "Inter for legibility."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: a full-width banner with a background image or gradient, "
        "the business tagline as an h1, a subheading, and a prominent CTA button. "
        "Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="ms-hero" id="hero">
      <div className="ms-hero__overlay" aria-hidden="true" />
      <div className="ms-hero__content">
        <p className="ms-hero__eyebrow">Sydney &middot; Est. Ramen Bar</p>
        <h1 className="ms-hero__title">Broth-first ramen,<br />made from scratch daily</h1>
        <p className="ms-hero__subtitle">
          Every bowl starts with a broth simmered for up to 18 hours. No shortcuts,
          no powders &mdash; just bones, time, and patience.
        </p>
        <a href="#menu" className="ms-hero__cta">View the Menu</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.ms-hero {
  position: relative;
  min-height: 92vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    linear-gradient(160deg, rgba(13,13,13,0.92) 0%, rgba(13,13,13,0.7) 55%, rgba(220,38,38,0.18) 100%),
    url('https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=1600&q=80') center/cover no-repeat;
}
.ms-hero__overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 30% 60%, rgba(220,38,38,0.12) 0%, transparent 60%);
  pointer-events: none;
}
.ms-hero__content {
  position: relative;
  z-index: 1;
  max-width: 720px;
  padding: 2rem;
  text-align: center;
}
.ms-hero__eyebrow {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #dc2626;
  margin: 0 0 1.25rem;
}
.ms-hero__title {
  font-family: 'Noto Serif JP', serif;
  font-size: clamp(2.2rem, 5.5vw, 4rem);
  font-weight: 700;
  color: #fafaf9;
  line-height: 1.15;
  margin: 0 0 1.5rem;
}
.ms-hero__subtitle {
  font-size: 1.05rem;
  color: #a8a29e;
  line-height: 1.7;
  margin: 0 auto 2.25rem;
  max-width: 520px;
}
.ms-hero__cta {
  display: inline-block;
  padding: 0.85rem 2.1rem;
  background: #dc2626;
  color: #fafaf9;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: 0.03em;
  text-decoration: none;
  text-transform: uppercase;
  transition: background 0.2s, transform 0.15s;
}
.ms-hero__cta:hover { background: #ef4444; transform: translateY(-2px); }"""
    t2_thought = thought(
        "The hero needs to feel warm and appetizing despite the dark palette, so I'm "
        "using a moody ramen photograph with a red-tinted gradient overlay rather than "
        "flat color. The tagline from the brief becomes the h1 in the Noto Serif JP "
        "font, and a single strong red CTA drives straight to the menu."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Menu section: display the menu categories and items from the content "
        "brief. Use a card-grid layout with item name, price, and description. "
        "Files: src/components/Menu.tsx + src/components/Menu.css",
    )

    # ── Turn 3: Menu ──
    menu_tsx = """\
import React, { useState } from 'react';
import './Menu.css';

interface MenuItem { name: string; price: string; description: string; }
interface MenuCategory { name: string; items: MenuItem[]; }

const MENU_DATA: MenuCategory[] = [
  {
    name: 'Ramen',
    items: [
      { name: 'Tonkotsu Classic', price: '$16', description: '18-hour pork bone broth, chashu, ajitama, nori' },
      { name: 'Spicy Miso', price: '$17', description: 'Fermented miso broth, ground pork, chili oil, corn' },
      { name: 'Shoyu Chicken', price: '$15', description: 'Clear soy broth, roast chicken, menma, scallion' },
      { name: 'Vegan Shiitake', price: '$14', description: 'Shiitake-kombu broth, tofu, mushrooms, seasonal greens' },
    ],
  },
  {
    name: 'Sides',
    items: [
      { name: 'Karaage', price: '$9', description: 'Japanese fried chicken thigh, yuzu kosho mayo' },
      { name: 'Gyoza (5pc)', price: '$8', description: 'Pan-seared pork dumplings, chili vinegar' },
      { name: 'Steamed Bao (2pc)', price: '$7', description: 'Pork belly, hoisin, pickled cucumber' },
    ],
  },
  {
    name: 'Drinks',
    items: [
      { name: 'Ramune', price: '$4', description: 'Classic Japanese marble soda' },
      { name: 'Asahi Draft', price: '$8', description: 'Japanese lager, 425ml' },
      { name: 'Iced Genmaicha', price: '$5', description: 'Roasted brown rice green tea' },
    ],
  },
];

export function Menu() {
  const [active, setActive] = useState('Ramen');
  const current = MENU_DATA.find(c => c.name === active) ?? MENU_DATA[0];

  return (
    <section className="ms-menu" id="menu" aria-labelledby="ms-menu-heading">
      <div className="ms-menu__inner">
        <div className="ms-menu__header">
          <p className="ms-menu__eyebrow">The Menu</p>
          <h2 id="ms-menu-heading" className="ms-menu__title">Bowls Worth the Wait</h2>
        </div>
        <div className="ms-menu__tabs" role="tablist" aria-label="Menu categories">
          {MENU_DATA.map(cat => (
            <button
              key={cat.name}
              role="tab"
              aria-selected={active === cat.name}
              className={`ms-menu__tab${active === cat.name ? ' ms-menu__tab--active' : ''}`}
              onClick={() => setActive(cat.name)}
            >
              {cat.name}
            </button>
          ))}
        </div>
        <div className="ms-menu__grid" role="tabpanel" aria-label={current.name}>
          {current.items.map(item => (
            <article key={item.name} className="ms-menu__card">
              <div className="ms-menu__card-top">
                <h3 className="ms-menu__item-name">{item.name}</h3>
                <span className="ms-menu__item-price">{item.price}</span>
              </div>
              <p className="ms-menu__item-desc">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""
    menu_css = """\
.ms-menu {
  padding: 6.5rem 2rem;
  background: #141414;
}
.ms-menu__inner { max-width: 1080px; margin: 0 auto; }
.ms-menu__header { text-align: center; margin-bottom: 3rem; }
.ms-menu__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #dc2626;
  margin: 0 0 0.75rem;
}
.ms-menu__title {
  font-family: 'Noto Serif JP', serif;
  font-size: clamp(1.9rem, 3.8vw, 2.75rem);
  color: #fafaf9;
  margin: 0;
}
.ms-menu__tabs {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 3rem;
  flex-wrap: wrap;
}
.ms-menu__tab {
  padding: 0.55rem 1.4rem;
  border: 2px solid #292524;
  background: transparent;
  color: #a8a29e;
  border-radius: 2rem;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.ms-menu__tab:hover { border-color: #dc2626; color: #dc2626; }
.ms-menu__tab--active { background: #dc2626; border-color: #dc2626; color: #fafaf9; }
.ms-menu__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.1rem;
}
.ms-menu__card {
  background: #1c1917;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 1.4rem;
  transition: transform 0.2s, border-color 0.2s;
}
.ms-menu__card:hover { transform: translateY(-3px); border-color: rgba(220,38,38,0.3); }
.ms-menu__card-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.6rem;
}
.ms-menu__item-name {
  font-family: 'Noto Serif JP', serif;
  font-size: 1.05rem;
  color: #fafaf9;
  margin: 0;
}
.ms-menu__item-price { font-weight: 700; color: #dc2626; white-space: nowrap; }
.ms-menu__item-desc { font-size: 0.87rem; color: #78716c; margin: 0; line-height: 1.6; }"""
    t3_thought = thought(
        "With three menu categories in the brief (Ramen, Sides, Drinks), a tabbed "
        "interface keeps things scannable instead of one long scroll. Prices stay in "
        "the red accent color for quick visual scanning, and cards get a subtle red "
        "glow on hover to tie back to the header/hero palette."
    )
    t3_action = write_site(
        "src/components/Menu.tsx", menu_tsx,
        "src/components/Menu.css", menu_css,
    )
    t3_obs = obs_ok(
        ["src/components/Menu.tsx", "src/components/Menu.css"],
        "Write the Footer section: a dark background footer with the business name, "
        "brief nav links, contact info (address, phone, email, hours), and a copyright "
        "notice. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 4: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="ms-footer" id="footer" aria-label="Site footer">
      <div className="ms-footer__inner">
        <div className="ms-footer__brand">
          <p className="ms-footer__logo">Miso &amp; Soul</p>
          <p className="ms-footer__tagline">Broth-first ramen, made from scratch daily</p>
        </div>
        <nav className="ms-footer__nav" aria-label="Footer navigation">
          <h3 className="ms-footer__heading">Navigate</h3>
          <a href="#hero" className="ms-footer__link">Home</a>
          <a href="#menu" className="ms-footer__link">Menu</a>
          <a href="#footer" className="ms-footer__link">Contact</a>
        </nav>
        <address className="ms-footer__contact">
          <h3 className="ms-footer__heading">Visit Us</h3>
          <p>88 Ramen Row<br />Sydney NSW 2000</p>
          <a href="tel:+61293338888" className="ms-footer__link">+61 2 9333 8888</a>
          <a href="mailto:hello@misoandsoul.com.au" className="ms-footer__link">hello@misoandsoul.com.au</a>
          <p className="ms-footer__hours">Mon&ndash;Sun 11am&ndash;11pm</p>
        </address>
      </div>
      <div className="ms-footer__bottom">
        <p>&copy; {year} Miso &amp; Soul. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.ms-footer {
  background: #0a0a0a;
  border-top: 1px solid rgba(220,38,38,0.2);
  padding: 4.5rem 2rem 0;
}
.ms-footer__inner {
  max-width: 1080px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1.5fr;
  gap: 3rem;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.ms-footer__logo {
  font-family: 'Noto Serif JP', serif;
  font-size: 1.3rem;
  color: #dc2626;
  margin: 0 0 0.5rem;
}
.ms-footer__tagline { font-size: 0.88rem; color: #57534e; margin: 0; max-width: 260px; line-height: 1.6; }
.ms-footer__nav { display: flex; flex-direction: column; gap: 0.6rem; }
.ms-footer__heading {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #dc2626;
  margin: 0 0 0.75rem;
}
.ms-footer__link { color: #a8a29e; text-decoration: none; font-size: 0.88rem; display: block; transition: color 0.2s; }
.ms-footer__link:hover { color: #fafaf9; }
.ms-footer__contact { font-style: normal; display: flex; flex-direction: column; gap: 0.5rem; color: #a8a29e; font-size: 0.88rem; line-height: 1.6; }
.ms-footer__hours { color: #57534e; font-size: 0.82rem; }
.ms-footer__bottom {
  max-width: 1080px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.78rem;
  color: #292524;
}
@media (max-width: 700px) {
  .ms-footer__inner { grid-template-columns: 1fr; gap: 2rem; }
}"""
    t4_thought = thought(
        "Final section. Following the three-column footer pattern from the header/hero/"
        "menu palette: brand + tagline, quick nav, and full contact block with the "
        "exact address, phone, email, and hours from the brief."
    )
    t4_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Menu.tsx", "src/components/Menu.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)
    t5_thought = thought(
        "All four sections were accepted: Header, Hero, Menu, and Footer, each using "
        "the near-black/red palette and Noto Serif JP headings from the brief."
    )
    t5_action = finish(
        "Built the complete Miso & Soul ramen bar website with 4 sections:\n"
        "- Header: sticky dark nav with logo and links\n"
        "- Hero: full-viewport ramen photo banner with tagline and CTA\n"
        "- Menu: tabbed Ramen/Sides/Drinks categories with all items from the brief\n"
        "- Footer: brand, nav, and full contact info\n"
        "Color scheme: near-black (#0d0d0d) with red (#dc2626) accent, Noto Serif JP headings."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_restaurant_miso_soul", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 2. trajectory_event_01 — DevSummit 2025 (conference)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_event_01():
    brief_xml = """<content_brief>
  <business_name>DevSummit 2025</business_name>
  <tagline>Where builders come to level up</tagline>
  <business_type>event</business_type>
  <primary_color>#030712</primary_color>
  <accent_color>#2563eb</accent_color>
  <font_heading>Inter</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, speakers, schedule, footer</sections>
  <speaker name="Sarah Chen" role="Staff Engineer, Stripe" />
  <speaker name="Marcus Odom" role="VP Engineering, Vercel" />
  <speaker name="Ayesha Khan" role="Principal Researcher, DeepMind" />
  <speaker name="Diego Fuentes" role="Founder, OpenRuntime" />
  <schedule_track name="Morning Keynotes" time="9:00am - 12:00pm" description="Opening keynotes on the future of developer tooling and platform engineering." />
  <schedule_track name="Afternoon Workshops" time="1:00pm - 5:00pm" description="Hands-on workshops covering distributed systems, AI infra, and dev experience." />
  <schedule_track name="Evening Networking" time="6:00pm - 9:00pm" description="Sponsor showcase, drinks, and structured networking by track." />
  <contact>
    <location>Sydney Convention Centre</location>
    <dates>April 12-13, 2025</dates>
    <email>tickets@devsummit.io</email>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the "
        "event name/logo on the left, nav links (Speakers, Schedule, Contact) on the right, "
        "and a 'Get Tickets' CTA button. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`ds-header${scrolled ? ' ds-header--scrolled' : ''}`}>
      <div className="ds-header__inner">
        <a href="#" className="ds-header__logo">DevSummit<span className="ds-header__year">2025</span></a>
        <nav className="ds-header__nav" aria-label="Main navigation">
          <a href="#speakers" className="ds-header__link">Speakers</a>
          <a href="#schedule" className="ds-header__link">Schedule</a>
          <a href="#footer" className="ds-header__link">Contact</a>
        </nav>
        <a href="mailto:tickets@devsummit.io" className="ds-header__cta">Get Tickets</a>
      </div>
    </header>
  );
}"""
    header_css = """\
.ds-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(3, 7, 18, 0.85);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(37, 99, 235, 0.15);
  transition: background 0.3s, box-shadow 0.3s;
}
.ds-header--scrolled {
  background: rgba(3, 7, 18, 0.97);
  box-shadow: 0 4px 24px rgba(0,0,0,0.5);
}
.ds-header__inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.ds-header__logo {
  font-weight: 800;
  font-size: 1.1rem;
  color: #f8fafc;
  text-decoration: none;
  letter-spacing: -0.02em;
}
.ds-header__year { color: #2563eb; margin-left: 0.25rem; }
.ds-header__nav { display: flex; gap: 1.75rem; align-items: center; }
.ds-header__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s;
}
.ds-header__link:hover { color: #f8fafc; }
.ds-header__cta {
  padding: 0.5rem 1.2rem;
  background: #2563eb;
  color: #f8fafc;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.2s, transform 0.15s;
}
.ds-header__cta:hover { background: #3b82f6; transform: translateY(-1px); }
@media (max-width: 700px) {
  .ds-header__nav { display: none; }
}"""
    t1_thought = thought(
        "For a developer conference the header should feel technical and confident: "
        "near-black background, a bold two-tone logo (name in white, year in the blue "
        "accent), and a single high-contrast 'Get Tickets' CTA since ticket conversion "
        "is the header's main job."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: full-width banner with the tagline as h1, a date/"
        "location badge, subheading, and a CTA button. "
        "Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="ds-hero" id="hero">
      <div className="ds-hero__grid" aria-hidden="true" />
      <div className="ds-hero__content">
        <div className="ds-hero__badge">
          <span className="ds-hero__badge-dot" aria-hidden="true" />
          April 12&ndash;13, 2025 &middot; Sydney Convention Centre
        </div>
        <h1 className="ds-hero__title">Where builders come to level up</h1>
        <p className="ds-hero__subtitle">
          Two days of keynotes, hands-on workshops, and networking with the engineers
          building the tools you use every day.
        </p>
        <a href="mailto:tickets@devsummit.io" className="ds-hero__cta">Reserve Your Seat</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.ds-hero {
  position: relative;
  min-height: 88vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #030712;
}
.ds-hero__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(37,99,235,0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(37,99,235,0.08) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse at center, black 20%, transparent 75%);
}
.ds-hero__content {
  position: relative;
  z-index: 1;
  max-width: 760px;
  padding: 2rem;
  text-align: center;
}
.ds-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 1rem;
  border-radius: 2rem;
  background: rgba(37,99,235,0.1);
  border: 1px solid rgba(37,99,235,0.3);
  font-size: 0.85rem;
  color: #93c5fd;
  font-weight: 500;
  margin-bottom: 1.75rem;
}
.ds-hero__badge-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #2563eb;
  animation: ds-pulse 2s ease-in-out infinite;
}
@keyframes ds-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.ds-hero__title {
  font-size: clamp(2.4rem, 5.5vw, 4.2rem);
  font-weight: 800;
  color: #f8fafc;
  line-height: 1.1;
  letter-spacing: -0.03em;
  margin: 0 0 1.5rem;
}
.ds-hero__subtitle {
  font-size: 1.1rem;
  color: #64748b;
  line-height: 1.75;
  margin: 0 auto 2.5rem;
  max-width: 560px;
}
.ds-hero__cta {
  display: inline-block;
  padding: 0.9rem 2.2rem;
  background: #2563eb;
  color: #f8fafc;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}
.ds-hero__cta:hover { background: #3b82f6; transform: translateY(-2px); box-shadow: 0 8px 28px rgba(37,99,235,0.4); }"""
    t2_thought = thought(
        "The hero needs to establish credibility fast. I'm using a subtle animated "
        "grid background (pure CSS gradients, no images) which reads as 'technical "
        "conference' immediately, a pulsing badge with the exact date and venue from "
        "the brief, and the tagline as a large bold h1."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Speakers section: display all 4 speakers from the brief as cards "
        "with name and role, in a responsive grid. "
        "Files: src/components/Speakers.tsx + src/components/Speakers.css",
    )

    # ── Turn 3: Speakers ──
    speakers_tsx = """\
import React from 'react';
import './Speakers.css';

interface Speaker { name: string; role: string; }

const SPEAKERS: Speaker[] = [
  { name: 'Sarah Chen', role: 'Staff Engineer, Stripe' },
  { name: 'Marcus Odom', role: 'VP Engineering, Vercel' },
  { name: 'Ayesha Khan', role: 'Principal Researcher, DeepMind' },
  { name: 'Diego Fuentes', role: 'Founder, OpenRuntime' },
];

function initials(name: string): string {
  return name.split(' ').map(p => p[0]).join('');
}

export function Speakers() {
  return (
    <section className="ds-speakers" id="speakers" aria-labelledby="ds-speakers-heading">
      <div className="ds-speakers__inner">
        <div className="ds-speakers__header">
          <p className="ds-speakers__eyebrow">Line-up</p>
          <h2 id="ds-speakers-heading" className="ds-speakers__title">Speakers</h2>
        </div>
        <ul className="ds-speakers__grid">
          {SPEAKERS.map(s => (
            <li key={s.name} className="ds-speaker-card">
              <div className="ds-speaker-card__avatar" aria-hidden="true">{initials(s.name)}</div>
              <h3 className="ds-speaker-card__name">{s.name}</h3>
              <p className="ds-speaker-card__role">{s.role}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}"""
    speakers_css = """\
.ds-speakers {
  padding: 6.5rem 2rem;
  background: #050914;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.ds-speakers__inner { max-width: 1160px; margin: 0 auto; }
.ds-speakers__header { text-align: center; margin-bottom: 3.5rem; }
.ds-speakers__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #2563eb;
  margin: 0 0 0.75rem;
}
.ds-speakers__title {
  font-size: clamp(1.9rem, 3.6vw, 2.75rem);
  font-weight: 800;
  color: #f8fafc;
  margin: 0;
  letter-spacing: -0.02em;
}
.ds-speakers__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.ds-speaker-card {
  background: #0d1424;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 2rem 1.25rem;
  text-align: center;
  transition: transform 0.2s, border-color 0.2s;
}
.ds-speaker-card:hover { transform: translateY(-4px); border-color: rgba(37,99,235,0.35); }
.ds-speaker-card__avatar {
  width: 64px;
  height: 64px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #1e3a8a);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f8fafc;
  font-weight: 700;
  font-size: 1.1rem;
}
.ds-speaker-card__name { font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin: 0 0 0.35rem; }
.ds-speaker-card__role { font-size: 0.85rem; color: #64748b; margin: 0; line-height: 1.5; }
@media (max-width: 900px) { .ds-speakers__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 520px) { .ds-speakers__grid { grid-template-columns: 1fr; } }"""
    t3_thought = thought(
        "For the 4 speakers I'm using a clean 4-column grid with generated initials "
        "avatars (gradient circles) instead of missing photos, since no images were "
        "provided in the brief. Each card keeps name and role exactly as given."
    )
    t3_action = write_site(
        "src/components/Speakers.tsx", speakers_tsx,
        "src/components/Speakers.css", speakers_css,
    )
    t3_obs = obs_ok(
        ["src/components/Speakers.tsx", "src/components/Speakers.css"],
        "Write the Schedule section: display the 3 schedule tracks from the brief as a "
        "vertical timeline with time, name, and description. "
        "Files: src/components/Schedule.tsx + src/components/Schedule.css",
    )

    # ── Turn 4: Schedule ──
    schedule_tsx = """\
import React from 'react';
import './Schedule.css';

interface Track { name: string; time: string; description: string; }

const TRACKS: Track[] = [
  { name: 'Morning Keynotes', time: '9:00am - 12:00pm', description: 'Opening keynotes on the future of developer tooling and platform engineering.' },
  { name: 'Afternoon Workshops', time: '1:00pm - 5:00pm', description: 'Hands-on workshops covering distributed systems, AI infra, and dev experience.' },
  { name: 'Evening Networking', time: '6:00pm - 9:00pm', description: 'Sponsor showcase, drinks, and structured networking by track.' },
];

export function Schedule() {
  return (
    <section className="ds-schedule" id="schedule" aria-labelledby="ds-schedule-heading">
      <div className="ds-schedule__inner">
        <div className="ds-schedule__header">
          <p className="ds-schedule__eyebrow">Agenda</p>
          <h2 id="ds-schedule-heading" className="ds-schedule__title">Schedule</h2>
        </div>
        <ol className="ds-schedule__timeline">
          {TRACKS.map((track, i) => (
            <li key={track.name} className="ds-schedule__item">
              <div className="ds-schedule__marker" aria-hidden="true">{i + 1}</div>
              <div className="ds-schedule__body">
                <span className="ds-schedule__time">{track.time}</span>
                <h3 className="ds-schedule__name">{track.name}</h3>
                <p className="ds-schedule__desc">{track.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}"""
    schedule_css = """\
.ds-schedule {
  padding: 6.5rem 2rem;
  background: #030712;
}
.ds-schedule__inner { max-width: 780px; margin: 0 auto; }
.ds-schedule__header { text-align: center; margin-bottom: 3.5rem; }
.ds-schedule__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #2563eb;
  margin: 0 0 0.75rem;
}
.ds-schedule__title { font-size: clamp(1.9rem, 3.6vw, 2.75rem); font-weight: 800; color: #f8fafc; margin: 0; }
.ds-schedule__timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  position: relative;
}
.ds-schedule__timeline::before {
  content: '';
  position: absolute;
  left: 21px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: rgba(37,99,235,0.2);
}
.ds-schedule__item {
  display: flex;
  gap: 1.5rem;
  padding-bottom: 2.5rem;
  position: relative;
}
.ds-schedule__item:last-child { padding-bottom: 0; }
.ds-schedule__marker {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #2563eb;
  color: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  z-index: 1;
}
.ds-schedule__time {
  font-size: 0.8rem;
  font-weight: 700;
  color: #93c5fd;
  letter-spacing: 0.04em;
}
.ds-schedule__name { font-size: 1.2rem; font-weight: 700; color: #f8fafc; margin: 0.35rem 0 0.5rem; }
.ds-schedule__desc { font-size: 0.9rem; color: #64748b; line-height: 1.7; margin: 0; }"""
    t4_thought = thought(
        "The 3 schedule tracks map naturally onto a vertical timeline with numbered "
        "markers connected by a line, which communicates progression through the day "
        "better than plain cards. Time badges use the lighter blue tint to separate "
        "them from the track name."
    )
    t4_action = write_site(
        "src/components/Schedule.tsx", schedule_tsx,
        "src/components/Schedule.css", schedule_css,
    )
    t4_obs = obs_ok(
        ["src/components/Schedule.tsx", "src/components/Schedule.css"],
        "Write the Footer section: dark footer with event name, location, dates, "
        "contact email, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 5: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="ds-footer" id="footer" aria-label="Site footer">
      <div className="ds-footer__inner">
        <div className="ds-footer__brand">
          <p className="ds-footer__logo">DevSummit<span className="ds-footer__year">2025</span></p>
          <p className="ds-footer__tagline">Where builders come to level up</p>
        </div>
        <div className="ds-footer__details">
          <p className="ds-footer__detail">Sydney Convention Centre</p>
          <p className="ds-footer__detail">April 12&ndash;13, 2025</p>
          <a href="mailto:tickets@devsummit.io" className="ds-footer__link">tickets@devsummit.io</a>
        </div>
      </div>
      <div className="ds-footer__bottom">
        <p>&copy; {year} DevSummit. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.ds-footer {
  background: #010409;
  border-top: 1px solid rgba(37,99,235,0.2);
  padding: 4rem 2rem 0;
}
.ds-footer__inner {
  max-width: 1160px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 2rem;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.ds-footer__logo { font-weight: 800; font-size: 1.2rem; color: #f8fafc; margin: 0 0 0.5rem; }
.ds-footer__year { color: #2563eb; margin-left: 0.25rem; }
.ds-footer__tagline { font-size: 0.9rem; color: #475569; margin: 0; }
.ds-footer__details { display: flex; flex-direction: column; gap: 0.5rem; text-align: right; }
.ds-footer__detail { font-size: 0.9rem; color: #94a3b8; margin: 0; }
.ds-footer__link { font-size: 0.9rem; color: #2563eb; text-decoration: none; }
.ds-footer__link:hover { color: #3b82f6; text-decoration: underline; }
.ds-footer__bottom {
  max-width: 1160px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.8rem;
  color: #1e293b;
}
@media (max-width: 640px) {
  .ds-footer__inner { flex-direction: column; }
  .ds-footer__details { text-align: left; }
}"""
    t5_thought = thought(
        "Final section: a simple two-column footer with the brand on the left and "
        "logistics (venue, dates, ticket email) right-aligned on the right, closing "
        "with a copyright line."
    )
    t5_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Speakers.tsx", "src/components/Speakers.css",
        "src/components/Schedule.tsx", "src/components/Schedule.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought(
        "All five sections accepted: Header, Hero, Speakers, Schedule, Footer."
    )
    t6_action = finish(
        "Built the complete DevSummit 2025 conference website with 5 sections:\n"
        "- Header: sticky nav with logo, links, and ticket CTA\n"
        "- Hero: animated grid background with date/location badge and CTA\n"
        "- Speakers: 4-card grid with all speakers from the brief\n"
        "- Schedule: vertical timeline with all 3 tracks\n"
        "- Footer: brand, venue/date details, contact email\n"
        "Color scheme: near-black (#030712), blue (#2563eb) accent, Inter throughout."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_event_devsummit_2025", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 3. trajectory_saas_02 — Prose.ai (AI writing assistant)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_saas_02():
    brief_xml = """<content_brief>
  <business_name>Prose.ai</business_name>
  <tagline>Write faster. Sound like you, only sharper.</tagline>
  <business_type>saas</business_type>
  <primary_color>#0f0f23</primary_color>
  <accent_color>#7c3aed</accent_color>
  <font_heading>Inter</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, features, pricing, footer</sections>
  <feature icon="autocomplete" title="Smart Autocomplete" description="Context-aware suggestions that finish your sentences the way you would." />
  <feature icon="tone" title="Tone Rewriter" description="Instantly shift a paragraph from casual to formal, or blunt to diplomatic." />
  <feature icon="seo" title="SEO Optimizer" description="Real-time keyword and readability scoring as you write, no plugins required." />
  <feature icon="plagiarism" title="Plagiarism Check" description="Scan against billions of web pages and academic sources in seconds." />
  <feature icon="language" title="Multilingual" description="Write and get suggestions in over 30 languages, switch mid-document." />
  <feature icon="history" title="Version History" description="Every draft saved automatically, restore any version with one click." />
  <pricing_tier name="Free" price="$0/mo" description="For casual writers getting started">
    <perk>5,000 words / month</perk>
    <perk>Basic autocomplete</perk>
    <perk>1 tone preset</perk>
  </pricing_tier>
  <pricing_tier name="Pro" price="$19/mo" description="For professionals who write daily" featured="true">
    <perk>Unlimited words</perk>
    <perk>Full tone rewriter</perk>
    <perk>SEO optimizer</perk>
    <perk>Plagiarism check</perk>
  </pricing_tier>
  <pricing_tier name="Team" price="$49/mo" description="For teams writing together">
    <perk>Everything in Pro</perk>
    <perk>Shared style guides</perk>
    <perk>Admin controls</perk>
    <perk>Priority support</perk>
  </pricing_tier>
  <contact>
    <email>hello@prose.ai</email>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky nav with the Prose.ai "
        "logo on the left, links (Features, Pricing, Docs) on the right, and a 'Start "
        "Writing Free' CTA. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`pr-header${scrolled ? ' pr-header--bg' : ''}`}>
      <div className="pr-header__inner">
        <a href="#" className="pr-header__logo">Prose<span className="pr-header__logo-dot">.ai</span></a>
        <nav className="pr-header__nav" aria-label="Main navigation">
          <a href="#features" className="pr-header__link">Features</a>
          <a href="#pricing" className="pr-header__link">Pricing</a>
          <a href="#" className="pr-header__link">Docs</a>
        </nav>
        <a href="mailto:hello@prose.ai" className="pr-header__cta">Start Writing Free</a>
      </div>
    </header>
  );
}"""
    header_css = """\
.pr-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  transition: background 0.3s, border-color 0.3s;
  border-bottom: 1px solid transparent;
}
.pr-header--bg {
  background: rgba(15, 15, 35, 0.92);
  backdrop-filter: blur(14px);
  border-color: rgba(124, 58, 237, 0.15);
}
.pr-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 66px;
  display: flex;
  align-items: center;
  gap: 2rem;
}
.pr-header__logo {
  font-weight: 800;
  font-size: 1.15rem;
  color: #f1f5f9;
  text-decoration: none;
  margin-right: auto;
  letter-spacing: -0.02em;
}
.pr-header__logo-dot { color: #a78bfa; }
.pr-header__nav { display: flex; gap: 1.5rem; }
.pr-header__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s;
}
.pr-header__link:hover { color: #f1f5f9; }
.pr-header__cta {
  padding: 0.5rem 1.15rem;
  background: #7c3aed;
  color: #f8fafc;
  border-radius: 8px;
  font-size: 0.86rem;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
}
.pr-header__cta:hover { background: #8b5cf6; transform: translateY(-1px); }
@media (max-width: 720px) { .pr-header__nav { display: none; } }"""
    t1_thought = thought(
        "Prose.ai's header follows the SaaS convention: transparent-to-glass on "
        "scroll, purple as the single accent color reserved for the logo dot and CTA "
        "so it stays distinctive against the deep indigo background."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: headline, subheading, CTA buttons, and a live "
        "editor mockup built purely in JSX/CSS (no external images). "
        "Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="pr-hero" id="hero">
      <div className="pr-hero__glow" aria-hidden="true" />
      <div className="pr-hero__inner">
        <div className="pr-hero__content">
          <h1 className="pr-hero__title">Write faster.<br />Sound like you, only sharper.</h1>
          <p className="pr-hero__sub">
            Prose.ai suggests, rewrites, and polishes as you type &mdash; without
            flattening your voice into generic AI-speak.
          </p>
          <div className="pr-hero__actions">
            <a href="mailto:hello@prose.ai" className="pr-hero__btn pr-hero__btn--primary">Start Writing Free</a>
            <a href="#features" className="pr-hero__btn pr-hero__btn--secondary">See Features</a>
          </div>
        </div>
        <div className="pr-hero__mockup" aria-hidden="true">
          <div className="pr-editor">
            <div className="pr-editor__bar">
              <span className="pr-editor__dot" />
              <span className="pr-editor__dot" />
              <span className="pr-editor__dot" />
              <span className="pr-editor__title">Untitled Draft</span>
            </div>
            <div className="pr-editor__body">
              <p className="pr-editor__line">The quarterly report shows strong growth
                <span className="pr-editor__suggestion"> across every region</span>
                <span className="pr-editor__cursor" />
              </p>
              <p className="pr-editor__line pr-editor__line--dim">
                Our customer retention rate improved to 94%...
              </p>
              <div className="pr-editor__toolbar">
                <span className="pr-editor__chip">Tone: Confident</span>
                <span className="pr-editor__chip">SEO: 92</span>
                <span className="pr-editor__chip pr-editor__chip--accent">Suggest</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}"""
    hero_css = """\
.pr-hero {
  position: relative;
  overflow: hidden;
  padding: 7rem 2rem 5rem;
  background: #0f0f23;
}
.pr-hero__glow {
  position: absolute;
  top: -15%;
  right: 5%;
  width: 700px;
  height: 500px;
  background: radial-gradient(ellipse, rgba(124,58,237,0.22) 0%, transparent 65%);
  pointer-events: none;
}
.pr-hero__inner {
  position: relative;
  max-width: 1160px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3.5rem;
  align-items: center;
}
.pr-hero__title {
  font-size: clamp(2.1rem, 4.3vw, 3.4rem);
  font-weight: 800;
  color: #f1f5f9;
  line-height: 1.15;
  letter-spacing: -0.03em;
  margin: 0 0 1.25rem;
}
.pr-hero__sub {
  font-size: 1.05rem;
  color: #6b7280;
  line-height: 1.75;
  margin: 0 0 2.25rem;
  max-width: 460px;
}
.pr-hero__actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.pr-hero__btn {
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  font-weight: 700;
  font-size: 0.92rem;
  text-decoration: none;
  transition: all 0.2s;
}
.pr-hero__btn--primary { background: #7c3aed; color: #f8fafc; }
.pr-hero__btn--primary:hover { background: #8b5cf6; box-shadow: 0 8px 24px rgba(124,58,237,0.4); transform: translateY(-2px); }
.pr-hero__btn--secondary { background: rgba(255,255,255,0.06); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1); }
.pr-hero__btn--secondary:hover { background: rgba(255,255,255,0.1); }
.pr-editor {
  background: #17172e;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 32px 80px rgba(0,0,0,0.5);
}
.pr-editor__bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.7rem 1rem;
  background: #0f0f23;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.pr-editor__dot { width: 9px; height: 9px; border-radius: 50%; background: #3f3f5f; }
.pr-editor__title { font-size: 0.75rem; color: #4b5563; margin-left: 0.5rem; }
.pr-editor__body { padding: 1.5rem; display: flex; flex-direction: column; gap: 0.9rem; }
.pr-editor__line { font-size: 0.92rem; color: #cbd5e1; line-height: 1.7; margin: 0; }
.pr-editor__line--dim { color: #4b5563; }
.pr-editor__suggestion {
  background: rgba(124,58,237,0.18);
  border-bottom: 1px dashed #a78bfa;
  color: #c4b5fd;
  padding: 0 2px;
}
.pr-editor__cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: #a78bfa;
  margin-left: 2px;
  animation: pr-blink 1s step-start infinite;
  vertical-align: middle;
}
@keyframes pr-blink { 50% { opacity: 0; } }
.pr-editor__toolbar { display: flex; gap: 0.5rem; flex-wrap: wrap; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.06); }
.pr-editor__chip { font-size: 0.72rem; padding: 0.3rem 0.65rem; border-radius: 6px; background: rgba(255,255,255,0.06); color: #9ca3af; font-weight: 600; }
.pr-editor__chip--accent { background: #7c3aed; color: #f8fafc; }
@media (max-width: 900px) { .pr-hero__inner { grid-template-columns: 1fr; } }"""
    t2_thought = thought(
        "The hero needs to show the product, not just describe it, so I built a live "
        "editor mockup entirely in JSX/CSS: an inline text suggestion highlighted in "
        "purple, a blinking cursor, and a toolbar of tone/SEO chips. This communicates "
        "the product's core value (autocomplete + tone + SEO) without any images."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Features section: all 6 features from the brief as cards with icon, "
        "title, and description in a responsive grid. "
        "Files: src/components/Features.tsx + src/components/Features.css",
    )

    # ── Turn 3: Features ──
    features_tsx = """\
import React from 'react';
import './Features.css';

interface Feature { icon: string; title: string; description: string; }

const FEATURES: Feature[] = [
  { icon: '\\u2328\\ufe0f', title: 'Smart Autocomplete', description: 'Context-aware suggestions that finish your sentences the way you would.' },
  { icon: '\\ud83c\\udfad', title: 'Tone Rewriter', description: 'Instantly shift a paragraph from casual to formal, or blunt to diplomatic.' },
  { icon: '\\ud83d\\udd0d', title: 'SEO Optimizer', description: 'Real-time keyword and readability scoring as you write, no plugins required.' },
  { icon: '\\u2705', title: 'Plagiarism Check', description: 'Scan against billions of web pages and academic sources in seconds.' },
  { icon: '\\ud83c\\udf10', title: 'Multilingual', description: 'Write and get suggestions in over 30 languages, switch mid-document.' },
  { icon: '\\ud83d\\udd50', title: 'Version History', description: 'Every draft saved automatically, restore any version with one click.' },
];

export function Features() {
  return (
    <section className="pr-feat" id="features" aria-labelledby="pr-feat-heading">
      <div className="pr-feat__inner">
        <div className="pr-feat__header">
          <p className="pr-feat__eyebrow">Capabilities</p>
          <h2 id="pr-feat-heading" className="pr-feat__title">Everything a writer needs</h2>
        </div>
        <ul className="pr-feat__grid">
          {FEATURES.map((f, i) => (
            <li key={f.title} className="pr-feat__card" style={{'--i': i} as React.CSSProperties}>
              <div className="pr-feat__icon" aria-hidden="true">{f.icon}</div>
              <h3 className="pr-feat__card-title">{f.title}</h3>
              <p className="pr-feat__card-desc">{f.description}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}"""
    features_css = """\
.pr-feat {
  padding: 6.5rem 2rem;
  background: #0c0c1e;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.pr-feat__inner { max-width: 1160px; margin: 0 auto; }
.pr-feat__header { text-align: center; margin-bottom: 3.5rem; }
.pr-feat__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #7c3aed;
  margin: 0 0 0.75rem;
}
.pr-feat__title { font-size: clamp(1.8rem, 3.4vw, 2.6rem); font-weight: 800; color: #f1f5f9; margin: 0; }
.pr-feat__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.2rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.pr-feat__card {
  padding: 1.75rem;
  background: #17172e;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  transition: transform 0.2s, border-color 0.2s;
  animation: pr-in 0.5s ease both;
  animation-delay: calc(var(--i, 0) * 70ms);
}
.pr-feat__card:hover { transform: translateY(-4px); border-color: rgba(124,58,237,0.35); }
@keyframes pr-in { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
.pr-feat__icon { font-size: 1.6rem; margin-bottom: 1rem; }
.pr-feat__card-title { font-size: 1.02rem; font-weight: 700; color: #e2e8f0; margin: 0 0 0.5rem; }
.pr-feat__card-desc { font-size: 0.88rem; color: #6b7280; line-height: 1.65; margin: 0; }
@media (max-width: 900px) { .pr-feat__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .pr-feat__grid { grid-template-columns: 1fr; } }"""
    t3_thought = thought(
        "Six features fit a clean 3x2 emoji-icon grid, matching the SaaS convention "
        "established in the hero. Staggered entrance animation via a --i custom "
        "property adds polish without JS."
    )
    t3_action = write_site(
        "src/components/Features.tsx", features_tsx,
        "src/components/Features.css", features_css,
    )
    t3_obs = obs_ok(
        ["src/components/Features.tsx", "src/components/Features.css"],
        "Write the Pricing section: 3 tiers (Free, Pro, Team) from the brief with "
        "price, description, and perks, highlighting the featured Pro tier. "
        "Files: src/components/Pricing.tsx + src/components/Pricing.css",
    )

    # ── Turn 4: Pricing ──
    pricing_tsx = """\
import React from 'react';
import './Pricing.css';

interface Tier { name: string; price: string; description: string; perks: string[]; featured?: boolean; }

const TIERS: Tier[] = [
  { name: 'Free', price: '$0/mo', description: 'For casual writers getting started', perks: ['5,000 words / month', 'Basic autocomplete', '1 tone preset'] },
  { name: 'Pro', price: '$19/mo', description: 'For professionals who write daily', featured: true, perks: ['Unlimited words', 'Full tone rewriter', 'SEO optimizer', 'Plagiarism check'] },
  { name: 'Team', price: '$49/mo', description: 'For teams writing together', perks: ['Everything in Pro', 'Shared style guides', 'Admin controls', 'Priority support'] },
];

export function Pricing() {
  return (
    <section className="pr-pricing" id="pricing" aria-labelledby="pr-pricing-heading">
      <div className="pr-pricing__inner">
        <div className="pr-pricing__header">
          <p className="pr-pricing__eyebrow">Pricing</p>
          <h2 id="pr-pricing-heading" className="pr-pricing__title">Simple plans, no surprises</h2>
        </div>
        <div className="pr-pricing__grid">
          {TIERS.map(tier => (
            <article
              key={tier.name}
              className={`pr-tier${tier.featured ? ' pr-tier--featured' : ''}`}
            >
              {tier.featured && <span className="pr-tier__badge">Most Popular</span>}
              <h3 className="pr-tier__name">{tier.name}</h3>
              <p className="pr-tier__price">{tier.price}</p>
              <p className="pr-tier__desc">{tier.description}</p>
              <ul className="pr-tier__perks">
                {tier.perks.map(perk => (
                  <li key={perk} className="pr-tier__perk">
                    <svg viewBox="0 0 20 20" fill="currentColor" className="pr-tier__check" aria-hidden="true">
                      <path fillRule="evenodd" d="M16.7 5.3a1 1 0 010 1.4l-7 7a1 1 0 01-1.4 0l-3-3a1 1 0 111.4-1.4L9 11.6l6.3-6.3a1 1 0 011.4 0z" clipRule="evenodd" />
                    </svg>
                    {perk}
                  </li>
                ))}
              </ul>
              <a href="mailto:hello@prose.ai" className={`pr-tier__btn${tier.featured ? ' pr-tier__btn--primary' : ''}`}>
                {tier.name === 'Free' ? 'Get Started' : `Choose ${tier.name}`}
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""
    pricing_css = """\
.pr-pricing {
  padding: 6.5rem 2rem;
  background: #0f0f23;
}
.pr-pricing__inner { max-width: 1080px; margin: 0 auto; }
.pr-pricing__header { text-align: center; margin-bottom: 3.5rem; }
.pr-pricing__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #7c3aed;
  margin: 0 0 0.75rem;
}
.pr-pricing__title { font-size: clamp(1.8rem, 3.4vw, 2.6rem); font-weight: 800; color: #f1f5f9; margin: 0; }
.pr-pricing__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  align-items: start;
}
.pr-tier {
  position: relative;
  padding: 2rem 1.75rem;
  background: #17172e;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.pr-tier--featured {
  border-color: #7c3aed;
  background: #1b1638;
  box-shadow: 0 16px 48px rgba(124,58,237,0.25);
  transform: scale(1.03);
}
.pr-tier__badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: #7c3aed;
  color: #f8fafc;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.3rem 0.9rem;
  border-radius: 2rem;
  letter-spacing: 0.03em;
}
.pr-tier__name { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; margin: 0.5rem 0 0; }
.pr-tier__price { font-size: 2rem; font-weight: 800; color: #f1f5f9; margin: 0; letter-spacing: -0.02em; }
.pr-tier__desc { font-size: 0.85rem; color: #6b7280; margin: 0 0 1rem; }
.pr-tier__perks { list-style: none; margin: 0 0 1.5rem; padding: 0; display: flex; flex-direction: column; gap: 0.6rem; flex: 1; }
.pr-tier__perk { display: flex; align-items: center; gap: 0.5rem; font-size: 0.87rem; color: #cbd5e1; }
.pr-tier__check { width: 16px; height: 16px; color: #7c3aed; flex-shrink: 0; }
.pr-tier__btn {
  text-align: center;
  padding: 0.7rem 1rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.9rem;
  text-decoration: none;
  background: rgba(255,255,255,0.06);
  color: #cbd5e1;
  transition: background 0.2s;
}
.pr-tier__btn--primary { background: #7c3aed; color: #f8fafc; }
.pr-tier__btn--primary:hover { background: #8b5cf6; }
.pr-tier__btn:not(.pr-tier__btn--primary):hover { background: rgba(255,255,255,0.1); }
@media (max-width: 900px) {
  .pr-pricing__grid { grid-template-columns: 1fr; }
  .pr-tier--featured { transform: none; }
}"""
    t4_thought = thought(
        "Three pricing tiers get a classic side-by-side layout with the Pro tier "
        "visually emphasized (scaled up, purple border, 'Most Popular' badge) since "
        "it's marked featured in the brief. Checkmark icons in the accent purple "
        "reinforce the perk lists."
    )
    t4_action = write_site(
        "src/components/Pricing.tsx", pricing_tsx,
        "src/components/Pricing.css", pricing_css,
    )
    t4_obs = obs_ok(
        ["src/components/Pricing.tsx", "src/components/Pricing.css"],
        "Write the Footer section: dark footer with Prose.ai brand, contact email, "
        "and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 5: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="pr-footer" aria-label="Site footer">
      <div className="pr-footer__inner">
        <p className="pr-footer__logo">Prose<span className="pr-footer__logo-dot">.ai</span></p>
        <p className="pr-footer__tagline">Write faster. Sound like you, only sharper.</p>
        <a href="mailto:hello@prose.ai" className="pr-footer__email">hello@prose.ai</a>
      </div>
      <div className="pr-footer__bottom">
        <p>&copy; {year} Prose.ai. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.pr-footer {
  background: #08081a;
  border-top: 1px solid rgba(124,58,237,0.18);
  padding: 4rem 2rem 0;
}
.pr-footer__inner {
  max-width: 1160px;
  margin: 0 auto;
  text-align: center;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.pr-footer__logo { font-weight: 800; font-size: 1.2rem; color: #f1f5f9; margin: 0 0 0.5rem; }
.pr-footer__logo-dot { color: #a78bfa; }
.pr-footer__tagline { font-size: 0.9rem; color: #4b5563; margin: 0 0 1rem; }
.pr-footer__email { font-size: 0.9rem; color: #7c3aed; text-decoration: none; }
.pr-footer__email:hover { color: #a78bfa; text-decoration: underline; }
.pr-footer__bottom {
  max-width: 1160px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.8rem;
  color: #2d2d4a;
}"""
    t5_thought = thought(
        "Simple centered footer to close the page: brand, tagline restated, and the "
        "single contact email from the brief, plus copyright."
    )
    t5_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Features.tsx", "src/components/Features.css",
        "src/components/Pricing.tsx", "src/components/Pricing.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought("All five sections accepted: Header, Hero, Features, Pricing, Footer.")
    t6_action = finish(
        "Built the complete Prose.ai SaaS landing page with 5 sections:\n"
        "- Header: glass sticky nav with logo and CTA\n"
        "- Hero: headline plus a pure CSS/JSX live editor mockup\n"
        "- Features: 3x2 grid of all 6 features\n"
        "- Pricing: Free/Pro/Team tiers with Pro highlighted as featured\n"
        "- Footer: centered brand and contact email\n"
        "Color scheme: deep indigo (#0f0f23), purple (#7c3aed) accent, Inter throughout."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_saas_prose_ai", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 4. trajectory_ecommerce_01 — Blanc Studio (light-theme luxury fashion)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_ecommerce_01():
    brief_xml = """<content_brief>
  <business_name>Blanc Studio</business_name>
  <tagline>Quiet luxury, made to last</tagline>
  <business_type>ecommerce</business_type>
  <primary_color>#fafaf9</primary_color>
  <text_color>#1c1917</text_color>
  <accent_color>#d97706</accent_color>
  <font_heading>Cormorant Garamond</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, products, footer</sections>
  <product name="Linen Wrap Dress" price="$320" category="Dresses" />
  <product name="Cashmere Turtleneck" price="$480" category="Knitwear" />
  <product name="Tailored Blazer" price="$560" category="Outerwear" />
  <product name="Wide-Leg Trousers" price="$290" category="Bottoms" />
  <product name="Silk Cami" price="$180" category="Tops" />
  <product name="Merino Coat" price="$720" category="Outerwear" />
  <contact>
    <website>blanc-studio.com</website>
    <email>studio@blanc-studio.com</email>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a minimal, transparent "
        "sticky header with the brand name centered and small nav links (Shop, About, "
        "Contact) below or beside it. This is a LIGHT theme with off-white background "
        "and dark text. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`bl-header${scrolled ? ' bl-header--solid' : ''}`}>
      <div className="bl-header__inner">
        <a href="#" className="bl-header__logo">BLANC STUDIO</a>
        <nav className="bl-header__nav" aria-label="Main navigation">
          <a href="#hero" className="bl-header__link">Home</a>
          <a href="#products" className="bl-header__link">Collection</a>
          <a href="#footer" className="bl-header__link">Contact</a>
        </nav>
      </div>
    </header>
  );
}"""
    header_css = """\
.bl-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(250, 250, 249, 0.6);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid transparent;
  transition: background 0.3s, border-color 0.3s;
}
.bl-header--solid {
  background: rgba(250, 250, 249, 0.96);
  border-bottom-color: rgba(28, 25, 23, 0.08);
}
.bl-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 84px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.bl-header__logo {
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  color: #1c1917;
  text-decoration: none;
}
.bl-header__nav { display: flex; gap: 2.25rem; }
.bl-header__link {
  color: #1c1917;
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding-bottom: 4px;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s, color 0.2s;
}
.bl-header__link:hover { border-color: #d97706; color: #d97706; }
@media (max-width: 640px) {
  .bl-header__nav { gap: 1.1rem; }
  .bl-header__logo { font-size: 1.1rem; letter-spacing: 0.1em; }
}"""
    t1_thought = thought(
        "This is a light editorial luxury theme, so the header stays minimal: an "
        "off-white translucent bar that solidifies subtly on scroll, a wide-tracked "
        "serif wordmark, and understated uppercase nav links with a small amber "
        "underline on hover rather than a bold background change."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: a full-bleed editorial hero with a large serif "
        "headline (the tagline), a subheading, and a CTA. Light off-white theme. "
        "Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="bl-hero" id="hero">
      <div className="bl-hero__content">
        <p className="bl-hero__eyebrow">New Season Edit</p>
        <h1 className="bl-hero__title">Quiet luxury,<br />made to last</h1>
        <p className="bl-hero__subtitle">
          Considered silhouettes in natural fibers, designed to be worn for years,
          not seasons.
        </p>
        <a href="#products" className="bl-hero__cta">Shop the Edit</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.bl-hero {
  position: relative;
  min-height: 86vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    linear-gradient(180deg, rgba(250,250,249,0.2) 0%, rgba(250,250,249,0.85) 90%),
    url('https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1600&q=80') center 30%/cover no-repeat;
}
.bl-hero__content {
  max-width: 680px;
  padding: 2rem;
  text-align: center;
}
.bl-hero__eyebrow {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: #d97706;
  margin: 0 0 1.5rem;
}
.bl-hero__title {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(2.6rem, 6vw, 4.6rem);
  font-weight: 500;
  color: #1c1917;
  line-height: 1.1;
  margin: 0 0 1.5rem;
}
.bl-hero__subtitle {
  font-size: 1.05rem;
  color: #57534e;
  line-height: 1.75;
  margin: 0 auto 2.5rem;
  max-width: 460px;
}
.bl-hero__cta {
  display: inline-block;
  padding: 0.85rem 2.25rem;
  background: #1c1917;
  color: #fafaf9;
  border-radius: 0;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-decoration: none;
  transition: background 0.25s;
}
.bl-hero__cta:hover { background: #d97706; }"""
    t2_thought = thought(
        "The hero uses a soft editorial fashion photograph faded into the off-white "
        "background from below, so the page never feels like it has a hard 'section "
        "break'. The Cormorant Garamond serif headline in dark charcoal, not black, "
        "keeps things soft; the CTA is a sharp-cornered black button that inverts to "
        "amber on hover as the one bold gesture on an otherwise quiet page."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Featured Products section: all 6 products from the brief as cards "
        "with name, price, and category tag, in a responsive grid. Light theme. "
        "Files: src/components/Products.tsx + src/components/Products.css",
    )

    # ── Turn 3: Products ──
    products_tsx = """\
import React from 'react';
import './Products.css';

interface Product { name: string; price: string; category: string; }

const PRODUCTS: Product[] = [
  { name: 'Linen Wrap Dress', price: '$320', category: 'Dresses' },
  { name: 'Cashmere Turtleneck', price: '$480', category: 'Knitwear' },
  { name: 'Tailored Blazer', price: '$560', category: 'Outerwear' },
  { name: 'Wide-Leg Trousers', price: '$290', category: 'Bottoms' },
  { name: 'Silk Cami', price: '$180', category: 'Tops' },
  { name: 'Merino Coat', price: '$720', category: 'Outerwear' },
];

export function Products() {
  return (
    <section className="bl-products" id="products" aria-labelledby="bl-products-heading">
      <div className="bl-products__inner">
        <div className="bl-products__header">
          <p className="bl-products__eyebrow">Shop</p>
          <h2 id="bl-products-heading" className="bl-products__title">Featured Pieces</h2>
        </div>
        <div className="bl-products__grid">
          {PRODUCTS.map(p => (
            <article key={p.name} className="bl-product-card">
              <div className="bl-product-card__image" aria-hidden="true">
                <span className="bl-product-card__tag">{p.category}</span>
              </div>
              <h3 className="bl-product-card__name">{p.name}</h3>
              <p className="bl-product-card__price">{p.price}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""
    products_css = """\
.bl-products {
  padding: 6.5rem 2rem;
  background: #fafaf9;
}
.bl-products__inner { max-width: 1180px; margin: 0 auto; }
.bl-products__header { text-align: center; margin-bottom: 3.5rem; }
.bl-products__eyebrow {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #d97706;
  margin: 0 0 0.75rem;
}
.bl-products__title {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(2rem, 3.8vw, 3rem);
  font-weight: 500;
  color: #1c1917;
  margin: 0;
}
.bl-products__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem 1.5rem;
}
.bl-product-card { display: flex; flex-direction: column; gap: 0.5rem; }
.bl-product-card__image {
  aspect-ratio: 3 / 4;
  background: linear-gradient(155deg, #e7e5e4 0%, #d6d3d1 100%);
  border-radius: 2px;
  position: relative;
  overflow: hidden;
}
.bl-product-card__tag {
  position: absolute;
  bottom: 0.9rem;
  left: 0.9rem;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: rgba(250,250,249,0.92);
  color: #57534e;
  padding: 0.3rem 0.65rem;
}
.bl-product-card__name {
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.2rem;
  font-weight: 500;
  color: #1c1917;
  margin: 0.3rem 0 0;
}
.bl-product-card__price { font-size: 0.9rem; color: #78716c; margin: 0; }
@media (max-width: 900px) { .bl-products__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .bl-products__grid { grid-template-columns: 1fr; } }"""
    t3_thought = thought(
        "Six products get a clean 3-column grid with a 3:4 portrait 'image' block "
        "(a soft neutral gradient placeholder since no actual photos were supplied) "
        "and a category tag overlaid in the corner, echoing fashion e-commerce "
        "conventions. Name in the serif heading font, price understated in gray below."
    )
    t3_action = write_site(
        "src/components/Products.tsx", products_tsx,
        "src/components/Products.css", products_css,
    )
    t3_obs = obs_ok(
        ["src/components/Products.tsx", "src/components/Products.css"],
        "Write the Footer section: light minimal footer with brand, website, contact "
        "email, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 4: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="bl-footer" id="footer" aria-label="Site footer">
      <div className="bl-footer__inner">
        <p className="bl-footer__logo">BLANC STUDIO</p>
        <p className="bl-footer__tagline">Quiet luxury, made to last</p>
        <div className="bl-footer__contact">
          <a href="https://blanc-studio.com" className="bl-footer__link">blanc-studio.com</a>
          <a href="mailto:studio@blanc-studio.com" className="bl-footer__link">studio@blanc-studio.com</a>
        </div>
      </div>
      <div className="bl-footer__bottom">
        <p>&copy; {year} Blanc Studio. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.bl-footer {
  background: #f5f5f4;
  border-top: 1px solid rgba(28,25,23,0.08);
  padding: 4rem 2rem 0;
}
.bl-footer__inner {
  max-width: 1180px;
  margin: 0 auto;
  text-align: center;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(28,25,23,0.06);
}
.bl-footer__logo {
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.3rem;
  letter-spacing: 0.16em;
  color: #1c1917;
  margin: 0 0 0.5rem;
}
.bl-footer__tagline { font-size: 0.88rem; color: #78716c; margin: 0 0 1.25rem; }
.bl-footer__contact { display: flex; justify-content: center; gap: 1.75rem; flex-wrap: wrap; }
.bl-footer__link { font-size: 0.85rem; color: #57534e; text-decoration: none; }
.bl-footer__link:hover { color: #d97706; }
.bl-footer__bottom {
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.78rem;
  color: #a8a29e;
}"""
    t4_thought = thought(
        "The footer keeps the same restrained light palette: centered brand, tagline, "
        "and the two contact points from the brief on one line, closing with a quiet "
        "gray copyright."
    )
    t4_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Products.tsx", "src/components/Products.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)
    t5_thought = thought("All four sections accepted: Header, Hero, Products, Footer.")
    t5_action = finish(
        "Built the complete Blanc Studio e-commerce site with 4 sections:\n"
        "- Header: minimal transparent-to-solid nav with wide-tracked wordmark\n"
        "- Hero: full-bleed editorial photo hero with serif tagline headline\n"
        "- Products: 6-product grid with category tags and prices\n"
        "- Footer: centered brand, website, and contact email\n"
        "Color scheme: off-white (#fafaf9) background, charcoal (#1c1917) text, "
        "amber (#d97706) accent, Cormorant Garamond headings on Inter body."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_ecommerce_blanc_studio", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 5. trajectory_portfolio_02 — Marcus Bell (UX Designer)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_portfolio_02():
    brief_xml = """<content_brief>
  <business_name>Marcus Bell</business_name>
  <tagline>UX Designer &amp; Product Strategist</tagline>
  <business_type>portfolio</business_type>
  <primary_color>#0c0c0c</primary_color>
  <accent_color>#f97316</accent_color>
  <font_heading>Plus Jakarta Sans</font_heading>
  <font_body>Plus Jakarta Sans</font_body>
  <sections>header, hero, projects, contact, footer</sections>
  <project name="Fintech Rebrand" role="Lead Designer" outcome="Increased sign-up conversion by 34% after a full visual and UX overhaul." />
  <project name="Healthcare App" role="Product Strategy" outcome="Defined the product roadmap for a patient-engagement app now used by 40+ clinics." />
  <project name="E-comm Platform" role="UX Lead" outcome="Redesigned checkout flow, cutting cart abandonment by 21%." />
  <project name="SaaS Dashboard" role="Design System" outcome="Built a component library adopted across 6 product teams." />
  <contact>
    <email>hello@marcusbell.design</email>
    <social>@marcusbell on Twitter/Dribbble</social>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a minimal sticky header "
        "with the designer's name on the left and links to Projects and Contact on "
        "the right. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="mb-header" role="banner">
      <div className="mb-header__inner">
        <a href="#" className="mb-header__name">Marcus Bell</a>
        <nav className="mb-header__nav" aria-label="Main navigation">
          <a href="#projects" className="mb-header__link">Projects</a>
          <a href="#contact" className="mb-header__link">Contact</a>
        </nav>
      </div>
    </header>
  );
}"""
    header_css = """\
.mb-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(12, 12, 12, 0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(249, 115, 22, 0.12);
}
.mb-header__inner {
  max-width: 980px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 66px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mb-header__name {
  font-weight: 700;
  font-size: 1.05rem;
  color: #f5f5f4;
  text-decoration: none;
  letter-spacing: -0.01em;
}
.mb-header__nav { display: flex; gap: 0.5rem; }
.mb-header__link {
  padding: 0.4rem 0.9rem;
  color: #a3a3a3;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 500;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}
.mb-header__link:hover { color: #f97316; background: rgba(249,115,22,0.08); }"""
    t1_thought = thought(
        "For a design portfolio, restraint is the design statement itself: a plain "
        "dark bar, name in white, two nav links that light up orange on hover. "
        "Nothing competes with the work shown further down the page."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: name/title intro with an animated typing role text "
        "that cycles through 3 roles using pure CSS, a short bio, and CTA buttons. "
        "Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="mb-hero" id="hero" aria-labelledby="mb-hero-name">
      <div className="mb-hero__inner">
        <p className="mb-hero__greeting">Hi, I&apos;m</p>
        <h1 id="mb-hero-name" className="mb-hero__name">Marcus Bell</h1>
        <p className="mb-hero__roles" aria-label="UX Designer, Product Strategist, Design Systems Lead">
          <span className="mb-hero__role-cycle">
            <span>UX Designer</span>
            <span>Product Strategist</span>
            <span>Design Systems Lead</span>
          </span>
        </p>
        <p className="mb-hero__bio">
          I turn ambiguous product problems into clear, usable interfaces &mdash;
          from early strategy through pixel-level execution.
        </p>
        <div className="mb-hero__actions">
          <a href="#projects" className="mb-hero__btn mb-hero__btn--primary">View Projects</a>
          <a href="#contact" className="mb-hero__btn mb-hero__btn--secondary">Get in Touch</a>
        </div>
      </div>
    </section>
  );
}"""
    hero_css = """\
.mb-hero {
  padding: 8rem 2rem 5.5rem;
  background: #0c0c0c;
  text-align: center;
}
.mb-hero__inner { max-width: 640px; margin: 0 auto; }
.mb-hero__greeting {
  font-size: 0.95rem;
  color: #f97316;
  margin: 0 0 0.5rem;
  font-weight: 600;
}
.mb-hero__name {
  font-size: clamp(2.4rem, 5.5vw, 3.75rem);
  font-weight: 800;
  color: #f5f5f4;
  margin: 0 0 1rem;
  letter-spacing: -0.03em;
}
.mb-hero__roles {
  height: 1.8rem;
  overflow: hidden;
  margin: 0 0 1.75rem;
}
.mb-hero__role-cycle {
  display: flex;
  flex-direction: column;
  animation: mb-cycle 6s steps(1) infinite;
}
.mb-hero__role-cycle span {
  font-size: 1.2rem;
  font-weight: 600;
  color: #d4d4d4;
  height: 1.8rem;
  line-height: 1.8rem;
}
@keyframes mb-cycle {
  0%, 30% { transform: translateY(0); }
  33%, 63% { transform: translateY(-1.8rem); }
  66%, 96% { transform: translateY(-3.6rem); }
  100% { transform: translateY(0); }
}
.mb-hero__bio {
  font-size: 1.02rem;
  color: #737373;
  line-height: 1.75;
  margin: 0 auto 2.25rem;
  max-width: 480px;
}
.mb-hero__actions { display: flex; justify-content: center; gap: 0.75rem; flex-wrap: wrap; }
.mb-hero__btn {
  padding: 0.75rem 1.6rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.9rem;
  text-decoration: none;
  transition: all 0.2s;
}
.mb-hero__btn--primary { background: #f97316; color: #0c0c0c; }
.mb-hero__btn--primary:hover { background: #fb923c; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(249,115,22,0.3); }
.mb-hero__btn--secondary { background: transparent; color: #d4d4d4; border: 1px solid rgba(255,255,255,0.14); }
.mb-hero__btn--secondary:hover { border-color: #f97316; color: #f97316; }"""
    t2_thought = thought(
        "The animated role text is built with a pure-CSS vertical-cycle animation: "
        "three role labels stacked in a fixed-height, overflow-hidden container, "
        "translated up on a keyframe loop with steps(1) so each role holds fully "
        "before the next appears (no third-party libraries needed). I kept the visible "
        "aria-label static for accessibility so screen readers get the full role list."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Projects section: all 4 case studies from the brief as large cards "
        "with project name, role, and outcome. Files: src/components/Projects.tsx + src/components/Projects.css",
    )

    # ── Turn 3: Projects ──
    projects_tsx = """\
import React from 'react';
import './Projects.css';

interface Project { name: string; role: string; outcome: string; }

const PROJECTS: Project[] = [
  { name: 'Fintech Rebrand', role: 'Lead Designer', outcome: 'Increased sign-up conversion by 34% after a full visual and UX overhaul.' },
  { name: 'Healthcare App', role: 'Product Strategy', outcome: 'Defined the product roadmap for a patient-engagement app now used by 40+ clinics.' },
  { name: 'E-comm Platform', role: 'UX Lead', outcome: 'Redesigned checkout flow, cutting cart abandonment by 21%.' },
  { name: 'SaaS Dashboard', role: 'Design System', outcome: 'Built a component library adopted across 6 product teams.' },
];

export function Projects() {
  return (
    <section className="mb-projects" id="projects" aria-labelledby="mb-projects-heading">
      <div className="mb-projects__inner">
        <h2 id="mb-projects-heading" className="mb-projects__heading">Selected Work</h2>
        <div className="mb-projects__list">
          {PROJECTS.map((p, i) => (
            <article key={p.name} className="mb-proj-card">
              <span className="mb-proj-card__index">{String(i + 1).padStart(2, '0')}</span>
              <div className="mb-proj-card__body">
                <div className="mb-proj-card__top">
                  <h3 className="mb-proj-card__name">{p.name}</h3>
                  <span className="mb-proj-card__role">{p.role}</span>
                </div>
                <p className="mb-proj-card__outcome">{p.outcome}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""
    projects_css = """\
.mb-projects {
  padding: 6rem 2rem;
  background: #111111;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.mb-projects__inner { max-width: 900px; margin: 0 auto; }
.mb-projects__heading {
  font-size: clamp(1.7rem, 3.2vw, 2.4rem);
  font-weight: 800;
  color: #f5f5f4;
  margin: 0 0 2.75rem;
  letter-spacing: -0.02em;
}
.mb-projects__list { display: flex; flex-direction: column; }
.mb-proj-card {
  display: flex;
  gap: 1.75rem;
  padding: 1.75rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  transition: padding-left 0.25s;
}
.mb-proj-card:hover { padding-left: 0.5rem; }
.mb-proj-card__index {
  font-size: 0.85rem;
  font-weight: 700;
  color: #f97316;
  min-width: 32px;
  padding-top: 0.2rem;
}
.mb-proj-card__body { flex: 1; }
.mb-proj-card__top {
  display: flex;
  align-items: baseline;
  gap: 0.9rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}
.mb-proj-card__name { font-size: 1.25rem; font-weight: 700; color: #f5f5f4; margin: 0; }
.mb-proj-card__role {
  font-size: 0.78rem;
  font-weight: 600;
  color: #f97316;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.mb-proj-card__outcome { font-size: 0.95rem; color: #a3a3a3; line-height: 1.7; margin: 0; max-width: 640px; }"""
    t3_thought = thought(
        "Rather than photo-heavy cards (no images were provided), I built an editorial "
        "numbered list layout: large index numbers in orange, project name and role "
        "on one line, outcome copy beneath. A subtle hover indent gives interactivity "
        "without needing imagery."
    )
    t3_action = write_site(
        "src/components/Projects.tsx", projects_tsx,
        "src/components/Projects.css", projects_css,
    )
    t3_obs = obs_ok(
        ["src/components/Projects.tsx", "src/components/Projects.css"],
        "Write the Contact section: a form-like layout with the email and social "
        "handle from the brief, styled like a call-to-action block. "
        "Files: src/components/Contact.tsx + src/components/Contact.css",
    )

    # ── Turn 4: Contact ──
    contact_tsx = """\
import React from 'react';
import './Contact.css';

export function Contact() {
  return (
    <section className="mb-contact" id="contact" aria-labelledby="mb-contact-heading">
      <div className="mb-contact__inner">
        <p className="mb-contact__eyebrow">Let&apos;s Work Together</p>
        <h2 id="mb-contact-heading" className="mb-contact__heading">
          Have a project in mind?
        </h2>
        <p className="mb-contact__sub">
          I&apos;m currently taking on new design engagements. Reach out and let&apos;s talk.
        </p>
        <a href="mailto:hello@marcusbell.design" className="mb-contact__email">
          hello@marcusbell.design
        </a>
        <p className="mb-contact__social">@marcusbell on Twitter/Dribbble</p>
      </div>
    </section>
  );
}"""
    contact_css = """\
.mb-contact {
  padding: 7rem 2rem;
  background: #0c0c0c;
  text-align: center;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.mb-contact__inner { max-width: 620px; margin: 0 auto; }
.mb-contact__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #f97316;
  margin: 0 0 1rem;
}
.mb-contact__heading {
  font-size: clamp(1.8rem, 3.6vw, 2.6rem);
  font-weight: 800;
  color: #f5f5f4;
  margin: 0 0 1rem;
  letter-spacing: -0.02em;
}
.mb-contact__sub {
  font-size: 1rem;
  color: #737373;
  line-height: 1.7;
  margin: 0 0 2.25rem;
}
.mb-contact__email {
  display: inline-block;
  font-size: 1.4rem;
  font-weight: 700;
  color: #f97316;
  text-decoration: none;
  border-bottom: 2px solid rgba(249,115,22,0.3);
  padding-bottom: 4px;
  margin-bottom: 1rem;
  transition: border-color 0.2s;
}
.mb-contact__email:hover { border-color: #f97316; }
.mb-contact__social { font-size: 0.88rem; color: #525252; margin: 0; }"""
    t4_thought = thought(
        "The brief calls for a form-like CTA block rather than an actual input form "
        "since only an email and social handle were provided. I designed it as a big "
        "centered 'get in touch' moment with the email as the dominant clickable "
        "element, styled like a headline rather than a plain link."
    )
    t4_action = write_site(
        "src/components/Contact.tsx", contact_tsx,
        "src/components/Contact.css", contact_css,
    )
    t4_obs = obs_ok(
        ["src/components/Contact.tsx", "src/components/Contact.css"],
        "Write the Footer section: minimal dark footer with name, email, social "
        "handle, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 5: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mb-footer" aria-label="Site footer">
      <div className="mb-footer__inner">
        <p className="mb-footer__name">Marcus Bell</p>
        <div className="mb-footer__links">
          <a href="mailto:hello@marcusbell.design" className="mb-footer__link">hello@marcusbell.design</a>
          <span className="mb-footer__social">@marcusbell on Twitter/Dribbble</span>
        </div>
        <p className="mb-footer__copy">&copy; {year} Marcus Bell. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.mb-footer {
  background: #080808;
  border-top: 1px solid rgba(249,115,22,0.15);
  padding: 3rem 2rem;
}
.mb-footer__inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
}
.mb-footer__name { font-size: 1.05rem; font-weight: 700; color: #f5f5f4; margin: 0; }
.mb-footer__links { display: flex; gap: 1.25rem; flex-wrap: wrap; justify-content: center; align-items: center; }
.mb-footer__link { font-size: 0.88rem; color: #f97316; text-decoration: none; }
.mb-footer__link:hover { text-decoration: underline; }
.mb-footer__social { font-size: 0.85rem; color: #525252; }
.mb-footer__copy { font-size: 0.78rem; color: #333333; margin: 0.5rem 0 0; }"""
    t5_thought = thought(
        "Closing footer keeps to the minimal spirit of the whole site: name, the two "
        "contact points from the brief on one row, and a quiet copyright line."
    )
    t5_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Projects.tsx", "src/components/Projects.css",
        "src/components/Contact.tsx", "src/components/Contact.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought("All five sections accepted: Header, Hero, Projects, Contact, Footer.")
    t6_action = finish(
        "Built the complete Marcus Bell design portfolio with 5 sections:\n"
        "- Header: minimal sticky bar with name and two links\n"
        "- Hero: intro with a pure-CSS cycling role animation and bio\n"
        "- Projects: numbered editorial list of all 4 case studies\n"
        "- Contact: large centered CTA block with email and social handle\n"
        "- Footer: minimal closing bar with contact links\n"
        "Color scheme: near-black (#0c0c0c), orange (#f97316) accent, Plus Jakarta Sans throughout."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_portfolio_marcus_bell", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 6. trajectory_nonprofit_01 — Green Horizon Alliance (environmental nonprofit)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_nonprofit_01():
    brief_xml = """<content_brief>
  <business_name>Green Horizon Alliance</business_name>
  <tagline>Restoring wild places, one acre at a time</tagline>
  <business_type>nonprofit</business_type>
  <primary_color>#0b1f14</primary_color>
  <accent_color>#84cc16</accent_color>
  <font_heading>Merriweather</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, impact, footer</sections>
  <impact_stat label="Acres Reforested" value="42,000+" />
  <impact_stat label="Trees Planted" value="1.8M" />
  <impact_stat label="Local Partners" value="63" />
  <impact_stat label="Volunteer Hours" value="210,000" />
  <contact>
    <address>14 Wetland Way, Portland OR 97201</address>
    <email>connect@greenhorizonalliance.org</email>
    <donate_note>100% of public donations go directly to field programs</donate_note>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky nav with the "
        "organization name on the left, links (Our Work, Impact, Contact) on the "
        "right, and a 'Donate' CTA button. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`gh-header${scrolled ? ' gh-header--scrolled' : ''}`}>
      <div className="gh-header__inner">
        <a href="#" className="gh-header__logo">Green Horizon Alliance</a>
        <nav className="gh-header__nav" aria-label="Main navigation">
          <a href="#hero" className="gh-header__link">Our Work</a>
          <a href="#impact" className="gh-header__link">Impact</a>
          <a href="#footer" className="gh-header__link">Contact</a>
        </nav>
        <a href="mailto:connect@greenhorizonalliance.org" className="gh-header__cta">Donate</a>
      </div>
    </header>
  );
}"""
    header_css = """\
.gh-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(11, 31, 20, 0.9);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(132, 204, 22, 0.15);
  transition: box-shadow 0.3s;
}
.gh-header--scrolled { box-shadow: 0 4px 20px rgba(0,0,0,0.35); }
.gh-header__inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.gh-header__logo {
  font-family: 'Merriweather', serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: #f0fdf4;
  text-decoration: none;
}
.gh-header__nav { display: flex; gap: 1.75rem; }
.gh-header__link {
  color: #a7bfae;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 500;
  transition: color 0.2s;
}
.gh-header__link:hover { color: #84cc16; }
.gh-header__cta {
  padding: 0.5rem 1.25rem;
  background: #84cc16;
  color: #0b1f14;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.2s, transform 0.15s;
}
.gh-header__cta:hover { background: #a3e635; transform: translateY(-1px); }
@media (max-width: 680px) { .gh-header__nav { display: none; } }"""
    t1_thought = thought(
        "Environmental nonprofits need to feel grounded and trustworthy rather than "
        "flashy, so I used a deep forest-green background with a single lime-green "
        "accent reserved almost entirely for the Donate button, making the action the "
        "most visually urgent element in the header."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: full-width banner with the tagline as h1, a "
        "supporting subheading, and a donate CTA. "
        "Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="gh-hero" id="hero">
      <div className="gh-hero__overlay" aria-hidden="true" />
      <div className="gh-hero__content">
        <h1 className="gh-hero__title">Restoring wild places,<br />one acre at a time</h1>
        <p className="gh-hero__subtitle">
          We partner with local communities to reforest degraded land, restore
          wetlands, and protect biodiversity for the long term.
        </p>
        <a href="mailto:connect@greenhorizonalliance.org" className="gh-hero__cta">Support Our Work</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.gh-hero {
  position: relative;
  min-height: 88vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    linear-gradient(160deg, rgba(11,31,20,0.9) 0%, rgba(11,31,20,0.6) 55%, rgba(132,204,22,0.1) 100%),
    url('https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1600&q=80') center/cover no-repeat;
}
.gh-hero__overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 25% 70%, rgba(132,204,22,0.1) 0%, transparent 60%);
  pointer-events: none;
}
.gh-hero__content {
  position: relative;
  z-index: 1;
  max-width: 720px;
  padding: 2rem;
  text-align: center;
}
.gh-hero__title {
  font-family: 'Merriweather', serif;
  font-size: clamp(2.2rem, 5vw, 3.75rem);
  font-weight: 700;
  color: #f0fdf4;
  line-height: 1.2;
  margin: 0 0 1.5rem;
}
.gh-hero__subtitle {
  font-size: 1.05rem;
  color: #cbd8ce;
  line-height: 1.75;
  margin: 0 auto 2.25rem;
  max-width: 540px;
}
.gh-hero__cta {
  display: inline-block;
  padding: 0.85rem 2.1rem;
  background: #84cc16;
  color: #0b1f14;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
}
.gh-hero__cta:hover { background: #a3e635; transform: translateY(-2px); }"""
    t2_thought = thought(
        "The hero pairs a real forest photograph with a deep green gradient overlay "
        "so the lime accent color reads clearly against it. The tagline becomes the "
        "serif h1 for warmth, and one lime donate CTA remains the sole point of high "
        "contrast in the composition."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Impact section: display all 4 impact stats from the brief as a "
        "large stat grid with number and label. "
        "Files: src/components/Impact.tsx + src/components/Impact.css",
    )

    # ── Turn 3: Impact ──
    impact_tsx = """\
import React from 'react';
import './Impact.css';

interface Stat { label: string; value: string; }

const STATS: Stat[] = [
  { label: 'Acres Reforested', value: '42,000+' },
  { label: 'Trees Planted', value: '1.8M' },
  { label: 'Local Partners', value: '63' },
  { label: 'Volunteer Hours', value: '210,000' },
];

export function Impact() {
  return (
    <section className="gh-impact" id="impact" aria-labelledby="gh-impact-heading">
      <div className="gh-impact__inner">
        <div className="gh-impact__header">
          <p className="gh-impact__eyebrow">Our Impact</p>
          <h2 id="gh-impact-heading" className="gh-impact__title">Numbers That Matter</h2>
        </div>
        <ul className="gh-impact__grid">
          {STATS.map(s => (
            <li key={s.label} className="gh-stat">
              <span className="gh-stat__value">{s.value}</span>
              <span className="gh-stat__label">{s.label}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}"""
    impact_css = """\
.gh-impact {
  padding: 6.5rem 2rem;
  background: #0f2a1c;
  border-top: 1px solid rgba(132,204,22,0.1);
}
.gh-impact__inner { max-width: 1080px; margin: 0 auto; }
.gh-impact__header { text-align: center; margin-bottom: 3.5rem; }
.gh-impact__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #84cc16;
  margin: 0 0 0.75rem;
}
.gh-impact__title {
  font-family: 'Merriweather', serif;
  font-size: clamp(1.8rem, 3.4vw, 2.6rem);
  color: #f0fdf4;
  margin: 0;
}
.gh-impact__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.gh-stat {
  text-align: center;
  padding: 2rem 1rem;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(132,204,22,0.12);
  border-radius: 12px;
  transition: transform 0.2s, border-color 0.2s;
}
.gh-stat:hover { transform: translateY(-3px); border-color: rgba(132,204,22,0.35); }
.gh-stat__value {
  display: block;
  font-family: 'Merriweather', serif;
  font-size: 2.2rem;
  font-weight: 700;
  color: #a3e635;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}
.gh-stat__label {
  display: block;
  font-size: 0.85rem;
  color: #9cb0a1;
  font-weight: 500;
}
@media (max-width: 800px) { .gh-impact__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .gh-impact__grid { grid-template-columns: 1fr; } }"""
    t3_thought = thought(
        "The 4 impact stats are the organization's proof of credibility, so they get "
        "a dedicated large-number stat grid with the lime accent reserved for the "
        "numbers themselves, making them the visual focus of the whole section."
    )
    t3_action = write_site(
        "src/components/Impact.tsx", impact_tsx,
        "src/components/Impact.css", impact_css,
    )
    t3_obs = obs_ok(
        ["src/components/Impact.tsx", "src/components/Impact.css"],
        "Write the Footer section: dark green footer with org name, address, "
        "contact email, donate note, and copyright. "
        "Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 4: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="gh-footer" id="footer" aria-label="Site footer">
      <div className="gh-footer__inner">
        <div className="gh-footer__brand">
          <p className="gh-footer__logo">Green Horizon Alliance</p>
          <p className="gh-footer__tagline">Restoring wild places, one acre at a time</p>
        </div>
        <address className="gh-footer__contact">
          <p>14 Wetland Way<br />Portland OR 97201</p>
          <a href="mailto:connect@greenhorizonalliance.org" className="gh-footer__link">
            connect@greenhorizonalliance.org
          </a>
          <p className="gh-footer__note">
            100% of public donations go directly to field programs
          </p>
        </address>
      </div>
      <div className="gh-footer__bottom">
        <p>&copy; {year} Green Horizon Alliance. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.gh-footer {
  background: #071711;
  border-top: 1px solid rgba(132,204,22,0.18);
  padding: 4rem 2rem 0;
}
.gh-footer__inner {
  max-width: 1080px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 2.5rem;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.gh-footer__logo {
  font-family: 'Merriweather', serif;
  font-size: 1.15rem;
  color: #f0fdf4;
  margin: 0 0 0.5rem;
}
.gh-footer__tagline { font-size: 0.88rem; color: #6f8776; margin: 0; }
.gh-footer__contact { font-style: normal; display: flex; flex-direction: column; gap: 0.5rem; color: #a7bfae; font-size: 0.88rem; line-height: 1.6; text-align: right; }
.gh-footer__link { color: #84cc16; text-decoration: none; }
.gh-footer__link:hover { text-decoration: underline; }
.gh-footer__note { font-size: 0.8rem; color: #5c7263; }
.gh-footer__bottom {
  max-width: 1080px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.78rem;
  color: #24352b;
}
@media (max-width: 640px) {
  .gh-footer__inner { grid-template-columns: 1fr; }
  .gh-footer__contact { text-align: left; }
}"""
    t4_thought = thought(
        "Closing footer places brand and mission on the left, and full contact "
        "details plus the donation transparency note on the right, since that note "
        "builds trust and belongs near the contact info rather than buried elsewhere."
    )
    t4_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Impact.tsx", "src/components/Impact.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)
    t5_thought = thought("All four sections accepted: Header, Hero, Impact, Footer.")
    t5_action = finish(
        "Built the complete Green Horizon Alliance nonprofit site with 4 sections:\n"
        "- Header: sticky nav with org name, links, and Donate CTA\n"
        "- Hero: forest photo banner with tagline and donate CTA\n"
        "- Impact: 4-stat grid with large lime numbers\n"
        "- Footer: brand, address, contact email, and donation transparency note\n"
        "Color scheme: deep forest green (#0b1f14), lime (#84cc16) accent, Merriweather headings on Inter body."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_nonprofit_green_horizon", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 7. trajectory_fitness_01 — IronClad Performance Gym
# ─────────────────────────────────────────────────────────────────────────
def trajectory_fitness_01():
    brief_xml = """<content_brief>
  <business_name>IronClad Performance</business_name>
  <tagline>Train hard. Recover smart. Perform better.</tagline>
  <business_type>fitness</business_type>
  <primary_color>#111111</primary_color>
  <accent_color>#eab308</accent_color>
  <font_heading>Barlow Condensed</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, classes, footer</sections>
  <class_type name="Strength &amp; Conditioning" duration="60 min" description="Barbell-based strength work paired with metabolic conditioning finishers." />
  <class_type name="HIIT Circuit" duration="45 min" description="High-intensity interval stations rotating through the full floor." />
  <class_type name="Mobility &amp; Recovery" duration="40 min" description="Guided stretching, foam rolling, and breathwork for active recovery." />
  <class_type name="Olympic Lifting" duration="75 min" description="Technical coaching on the snatch and clean &amp; jerk for all levels." />
  <contact>
    <address>219 Foundry Street, Denver CO 80202</address>
    <phone>+1 303 555 0147</phone>
    <email>train@ironcladperformance.com</email>
    <hours>Mon-Fri 5am-10pm | Sat-Sun 7am-6pm</hours>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a bold sticky nav with the "
        "gym name on the left, links (Classes, Schedule, Contact) on the right, and a "
        "'Book a Free Trial' CTA. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 14);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`ic-header${scrolled ? ' ic-header--scrolled' : ''}`}>
      <div className="ic-header__inner">
        <a href="#" className="ic-header__logo">IRONCLAD</a>
        <nav className="ic-header__nav" aria-label="Main navigation">
          <a href="#hero" className="ic-header__link">Home</a>
          <a href="#classes" className="ic-header__link">Classes</a>
          <a href="#footer" className="ic-header__link">Contact</a>
        </nav>
        <a href="mailto:train@ironcladperformance.com" className="ic-header__cta">Book a Free Trial</a>
      </div>
    </header>
  );
}"""
    header_css = """\
.ic-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(17, 17, 17, 0.92);
  border-bottom: 2px solid transparent;
  transition: border-color 0.3s;
}
.ic-header--scrolled { border-bottom-color: #eab308; }
.ic-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.ic-header__logo {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #fafaf9;
  text-decoration: none;
}
.ic-header__nav { display: flex; gap: 2rem; }
.ic-header__link {
  color: #a3a3a3;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  transition: color 0.2s;
}
.ic-header__link:hover { color: #eab308; }
.ic-header__cta {
  padding: 0.55rem 1.4rem;
  background: #eab308;
  color: #111111;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.2s, transform 0.15s;
}
.ic-header__cta:hover { background: #facc15; transform: translateY(-1px); }
@media (max-width: 700px) { .ic-header__nav { display: none; } }"""
    t1_thought = thought(
        "A performance gym brand needs to feel aggressive and confident, so I used "
        "the condensed Barlow font for a tight, athletic wordmark, near-black "
        "background, and a bright yellow-gold accent that reads as energy/warning-"
        "tape adjacent — appropriate for a strength gym."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: full-width banner with the tagline as h1, subheading, "
        "and a prominent CTA button. Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="ic-hero" id="hero">
      <div className="ic-hero__overlay" aria-hidden="true" />
      <div className="ic-hero__content">
        <h1 className="ic-hero__title">Train hard.<br />Recover smart.<br />Perform better.</h1>
        <p className="ic-hero__subtitle">
          Strength, conditioning, and recovery programming built by coaches who
          compete themselves.
        </p>
        <a href="mailto:train@ironcladperformance.com" className="ic-hero__cta">Book a Free Trial</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.ic-hero {
  position: relative;
  min-height: 92vh;
  display: flex;
  align-items: center;
  overflow: hidden;
  background:
    linear-gradient(100deg, rgba(17,17,17,0.95) 25%, rgba(17,17,17,0.55) 70%),
    url('https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1600&q=80') center/cover no-repeat;
}
.ic-hero__overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 60%, rgba(234,179,8,0.08) 100%);
  pointer-events: none;
}
.ic-hero__content {
  position: relative;
  z-index: 1;
  max-width: 620px;
  padding: 2rem 2rem 2rem 4rem;
}
.ic-hero__title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: clamp(3rem, 7vw, 5.5rem);
  font-weight: 700;
  color: #fafaf9;
  line-height: 1.02;
  letter-spacing: 0.01em;
  text-transform: uppercase;
  margin: 0 0 1.5rem;
}
.ic-hero__subtitle {
  font-size: 1.05rem;
  color: #d4d4d4;
  line-height: 1.7;
  margin: 0 0 2.25rem;
  max-width: 460px;
}
.ic-hero__cta {
  display: inline-block;
  padding: 0.9rem 2.25rem;
  background: #eab308;
  color: #111111;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
}
.ic-hero__cta:hover { background: #facc15; transform: translateY(-2px); }
@media (max-width: 700px) { .ic-hero__content { padding-left: 2rem; } }"""
    t2_thought = thought(
        "The hero uses a left-aligned, oversized condensed headline (a common gym-"
        "brand convention) over a strength-training photo with a strong dark gradient "
        "so text stays legible. The gold CTA continues the header's visual language."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Classes section: all 4 class types from the brief as cards with "
        "name, duration, and description, in a responsive grid. "
        "Files: src/components/Classes.tsx + src/components/Classes.css",
    )

    # ── Turn 3: Classes ──
    classes_tsx = """\
import React from 'react';
import './Classes.css';

interface ClassType { name: string; duration: string; description: string; }

const CLASSES: ClassType[] = [
  { name: 'Strength & Conditioning', duration: '60 min', description: 'Barbell-based strength work paired with metabolic conditioning finishers.' },
  { name: 'HIIT Circuit', duration: '45 min', description: 'High-intensity interval stations rotating through the full floor.' },
  { name: 'Mobility & Recovery', duration: '40 min', description: 'Guided stretching, foam rolling, and breathwork for active recovery.' },
  { name: 'Olympic Lifting', duration: '75 min', description: 'Technical coaching on the snatch and clean & jerk for all levels.' },
];

export function Classes() {
  return (
    <section className="ic-classes" id="classes" aria-labelledby="ic-classes-heading">
      <div className="ic-classes__inner">
        <div className="ic-classes__header">
          <p className="ic-classes__eyebrow">Programming</p>
          <h2 id="ic-classes-heading" className="ic-classes__title">Our Classes</h2>
        </div>
        <div className="ic-classes__grid">
          {CLASSES.map(c => (
            <article key={c.name} className="ic-class-card">
              <div className="ic-class-card__top">
                <h3 className="ic-class-card__name">{c.name}</h3>
                <span className="ic-class-card__duration">{c.duration}</span>
              </div>
              <p className="ic-class-card__desc">{c.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""
    classes_css = """\
.ic-classes {
  padding: 6.5rem 2rem;
  background: #171717;
}
.ic-classes__inner { max-width: 1080px; margin: 0 auto; }
.ic-classes__header { text-align: center; margin-bottom: 3.5rem; }
.ic-classes__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #eab308;
  margin: 0 0 0.75rem;
}
.ic-classes__title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: clamp(2.2rem, 4vw, 3.2rem);
  text-transform: uppercase;
  color: #fafaf9;
  margin: 0;
  letter-spacing: 0.02em;
}
.ic-classes__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}
.ic-class-card {
  padding: 1.75rem;
  background: #1f1f1f;
  border-left: 3px solid #eab308;
  border-radius: 6px;
  transition: transform 0.2s, background 0.2s;
}
.ic-class-card:hover { transform: translateX(4px); background: #262626; }
.ic-class-card__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.6rem;
}
.ic-class-card__name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 1.3rem;
  text-transform: uppercase;
  color: #fafaf9;
  margin: 0;
  letter-spacing: 0.01em;
}
.ic-class-card__duration { font-size: 0.85rem; font-weight: 700; color: #eab308; white-space: nowrap; }
.ic-class-card__desc { font-size: 0.9rem; color: #a3a3a3; line-height: 1.65; margin: 0; }
@media (max-width: 640px) { .ic-classes__grid { grid-template-columns: 1fr; } }"""
    t3_thought = thought(
        "The 4 class types get a 2-column grid of cards with a left gold accent bar "
        "instead of a full border, evoking gym signage. Duration is called out in "
        "gold next to the class name so schedule-scanning users can compare at a "
        "glance."
    )
    t3_action = write_site(
        "src/components/Classes.tsx", classes_tsx,
        "src/components/Classes.css", classes_css,
    )
    t3_obs = obs_ok(
        ["src/components/Classes.tsx", "src/components/Classes.css"],
        "Write the Footer section: dark footer with gym name, address, phone, email, "
        "hours, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 4: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="ic-footer" id="footer" aria-label="Site footer">
      <div className="ic-footer__inner">
        <div className="ic-footer__brand">
          <p className="ic-footer__logo">IRONCLAD</p>
          <p className="ic-footer__tagline">Train hard. Recover smart. Perform better.</p>
        </div>
        <address className="ic-footer__contact">
          <p>219 Foundry Street<br />Denver CO 80202</p>
          <a href="tel:+13035550147" className="ic-footer__link">+1 303 555 0147</a>
          <a href="mailto:train@ironcladperformance.com" className="ic-footer__link">
            train@ironcladperformance.com
          </a>
          <p className="ic-footer__hours">Mon&ndash;Fri 5am&ndash;10pm &middot; Sat&ndash;Sun 7am&ndash;6pm</p>
        </address>
      </div>
      <div className="ic-footer__bottom">
        <p>&copy; {year} IronClad Performance. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.ic-footer {
  background: #0a0a0a;
  border-top: 2px solid #eab308;
  padding: 4rem 2rem 0;
}
.ic-footer__inner {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 2rem;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.ic-footer__logo {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 1.5rem;
  letter-spacing: 0.06em;
  color: #fafaf9;
  margin: 0 0 0.5rem;
}
.ic-footer__tagline { font-size: 0.88rem; color: #737373; margin: 0; }
.ic-footer__contact { font-style: normal; display: flex; flex-direction: column; gap: 0.5rem; color: #d4d4d4; font-size: 0.88rem; line-height: 1.6; text-align: right; }
.ic-footer__link { color: #eab308; text-decoration: none; }
.ic-footer__link:hover { text-decoration: underline; }
.ic-footer__hours { font-size: 0.82rem; color: #737373; }
.ic-footer__bottom {
  max-width: 1080px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.78rem;
  color: #262626;
}
@media (max-width: 640px) {
  .ic-footer__inner { flex-direction: column; }
  .ic-footer__contact { text-align: left; }
}"""
    t4_thought = thought(
        "Footer uses a thick gold top border echoing gym floor tape, brand on the "
        "left, and full contact block including hours right-aligned so it reads like "
        "a poster/signage layout."
    )
    t4_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Classes.tsx", "src/components/Classes.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)
    t5_thought = thought("All four sections accepted: Header, Hero, Classes, Footer.")
    t5_action = finish(
        "Built the complete IronClad Performance gym site with 4 sections:\n"
        "- Header: bold sticky nav with condensed wordmark and trial CTA\n"
        "- Hero: left-aligned oversized headline over a training photo\n"
        "- Classes: 2-column grid of all 4 class types with durations\n"
        "- Footer: brand, address, phone, email, and hours\n"
        "Color scheme: near-black (#111111), gold (#eab308) accent, Barlow Condensed headings on Inter body."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_fitness_ironclad", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 8. trajectory_agency_01 — Pixel Forge (creative/design agency)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_agency_01():
    brief_xml = """<content_brief>
  <business_name>Pixel Forge</business_name>
  <tagline>Brands that don't blend in</tagline>
  <business_type>agency</business_type>
  <primary_color>#141414</primary_color>
  <accent_color>#ec4899</accent_color>
  <font_heading>Space Grotesk</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, services, footer</sections>
  <service name="Brand Identity" description="Logo systems, visual language, and brand guidelines built to scale." />
  <service name="Web Design" description="Conversion-focused websites that still feel like art." />
  <service name="Motion &amp; Video" description="Launch films, product demos, and social-first motion design." />
  <service name="Product Design" description="End-to-end UI/UX for apps and platforms, from wireframe to ship." />
  <contact>
    <email>studio@pixelforge.co</email>
    <instagram>@pixelforge.co</instagram>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a bold sticky header with "
        "the agency name on the left and a 'Start a Project' CTA on the right (no "
        "nav links needed, single page agency site). Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="pf-header" role="banner">
      <div className="pf-header__inner">
        <a href="#" className="pf-header__logo">Pixel Forge</a>
        <a href="mailto:studio@pixelforge.co" className="pf-header__cta">Start a Project</a>
      </div>
    </header>
  );
}"""
    header_css = """\
.pf-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: #141414;
  border-bottom: 1px solid rgba(236, 72, 153, 0.15);
}
.pf-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pf-header__logo {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.3rem;
  font-weight: 700;
  color: #fafafa;
  text-decoration: none;
  letter-spacing: -0.01em;
}
.pf-header__cta {
  padding: 0.65rem 1.5rem;
  background: #ec4899;
  color: #141414;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
}
.pf-header__cta:hover { background: #f472b6; transform: translateY(-1px); }"""
    t1_thought = thought(
        "As a single-page creative agency site, the header stays deliberately sparse: "
        "just the wordmark and one pill-shaped magenta CTA — no nav clutter, since the "
        "brief only calls for header/hero/services/footer sections that all live on "
        "one scrolling page."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: bold full-width banner with the tagline as a huge "
        "h1, subheading, and a CTA. Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="pf-hero" id="hero">
      <div className="pf-hero__blob" aria-hidden="true" />
      <div className="pf-hero__content">
        <h1 className="pf-hero__title">Brands that<br />don&apos;t blend in.</h1>
        <p className="pf-hero__subtitle">
          We&apos;re a small studio that builds identities, sites, and products for
          brands who'd rather stand out than fit in.
        </p>
        <a href="mailto:studio@pixelforge.co" className="pf-hero__cta">Start a Project</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.pf-hero {
  position: relative;
  min-height: 88vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #141414;
}
.pf-hero__blob {
  position: absolute;
  top: -10%;
  right: -10%;
  width: 700px;
  height: 700px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(236,72,153,0.28) 0%, transparent 65%);
  filter: blur(10px);
  pointer-events: none;
}
.pf-hero__content {
  position: relative;
  z-index: 1;
  max-width: 780px;
  padding: 2rem;
  text-align: center;
}
.pf-hero__title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(2.8rem, 7vw, 5.5rem);
  font-weight: 700;
  color: #fafafa;
  line-height: 1.02;
  letter-spacing: -0.03em;
  margin: 0 0 1.75rem;
}
.pf-hero__subtitle {
  font-size: 1.1rem;
  color: #a3a3a3;
  line-height: 1.75;
  margin: 0 auto 2.5rem;
  max-width: 520px;
}
.pf-hero__cta {
  display: inline-block;
  padding: 0.9rem 2.4rem;
  background: #ec4899;
  color: #141414;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.98rem;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}
.pf-hero__cta:hover { background: #f472b6; transform: translateY(-2px); box-shadow: 0 12px 32px rgba(236,72,153,0.35); }"""
    t2_thought = thought(
        "For a creative agency the hero should look like a portfolio piece itself: a "
        "massive Space Grotesk headline of the tagline, a soft glowing magenta blob "
        "behind it for depth, and a pill CTA that matches the rounded, confident "
        "branding established in the header."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Services section: all 4 services from the brief as large cards "
        "with name and description in a responsive grid. "
        "Files: src/components/Services.tsx + src/components/Services.css",
    )

    # ── Turn 3: Services ──
    services_tsx = """\
import React from 'react';
import './Services.css';

interface Service { name: string; description: string; }

const SERVICES: Service[] = [
  { name: 'Brand Identity', description: 'Logo systems, visual language, and brand guidelines built to scale.' },
  { name: 'Web Design', description: 'Conversion-focused websites that still feel like art.' },
  { name: 'Motion & Video', description: 'Launch films, product demos, and social-first motion design.' },
  { name: 'Product Design', description: 'End-to-end UI/UX for apps and platforms, from wireframe to ship.' },
];

export function Services() {
  return (
    <section className="pf-services" id="services" aria-labelledby="pf-services-heading">
      <div className="pf-services__inner">
        <h2 id="pf-services-heading" className="pf-services__heading">What We Do</h2>
        <div className="pf-services__grid">
          {SERVICES.map((s, i) => (
            <article key={s.name} className="pf-service-card">
              <span className="pf-service-card__num">{String(i + 1).padStart(2, '0')}</span>
              <h3 className="pf-service-card__name">{s.name}</h3>
              <p className="pf-service-card__desc">{s.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""
    services_css = """\
.pf-services {
  padding: 6.5rem 2rem;
  background: #191919;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.pf-services__inner { max-width: 1080px; margin: 0 auto; }
.pf-services__heading {
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(1.9rem, 3.6vw, 2.75rem);
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 3rem;
  letter-spacing: -0.02em;
}
.pf-services__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}
.pf-service-card {
  padding: 2.25rem;
  background: #212121;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.06);
  transition: transform 0.2s, border-color 0.2s, background 0.2s;
}
.pf-service-card:hover { transform: translateY(-4px); border-color: rgba(236,72,153,0.4); background: #242024; }
.pf-service-card__num {
  display: block;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  color: #ec4899;
  margin-bottom: 1rem;
}
.pf-service-card__name {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
  letter-spacing: -0.01em;
}
.pf-service-card__desc { font-size: 0.95rem; color: #a3a3a3; line-height: 1.7; margin: 0; }
@media (max-width: 700px) { .pf-services__grid { grid-template-columns: 1fr; } }"""
    t3_thought = thought(
        "The 4 services get large, generously padded cards in a 2x2 grid rather than "
        "tight 4-column tiles, since an agency's service list should feel spacious "
        "and confident rather than cramped. Numbered labels in magenta reinforce the "
        "editorial, portfolio-like tone of the hero."
    )
    t3_action = write_site(
        "src/components/Services.tsx", services_tsx,
        "src/components/Services.css", services_css,
    )
    t3_obs = obs_ok(
        ["src/components/Services.tsx", "src/components/Services.css"],
        "Write the Footer section: dark footer with agency name, email, Instagram "
        "handle, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 4: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="pf-footer" aria-label="Site footer">
      <div className="pf-footer__inner">
        <p className="pf-footer__logo">Pixel Forge</p>
        <div className="pf-footer__links">
          <a href="mailto:studio@pixelforge.co" className="pf-footer__link">studio@pixelforge.co</a>
          <span className="pf-footer__handle">@pixelforge.co</span>
        </div>
      </div>
      <div className="pf-footer__bottom">
        <p>&copy; {year} Pixel Forge. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.pf-footer {
  background: #0f0f0f;
  border-top: 1px solid rgba(236,72,153,0.2);
  padding: 3.5rem 2rem 0;
}
.pf-footer__inner {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1.5rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.pf-footer__logo {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0;
}
.pf-footer__links { display: flex; gap: 1.5rem; align-items: center; }
.pf-footer__link { color: #ec4899; text-decoration: none; font-size: 0.9rem; font-weight: 600; }
.pf-footer__link:hover { text-decoration: underline; }
.pf-footer__handle { color: #737373; font-size: 0.9rem; }
.pf-footer__bottom {
  max-width: 1080px;
  margin: 0 auto;
  padding: 1.25rem 0;
  text-align: center;
  font-size: 0.78rem;
  color: #333333;
}"""
    t4_thought = thought(
        "Closing footer keeps the confident minimal style: wordmark on the left, "
        "email and Instagram handle on the right, brief copyright line at the bottom."
    )
    t4_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Services.tsx", "src/components/Services.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)
    t5_thought = thought("All four sections accepted: Header, Hero, Services, Footer.")
    t5_action = finish(
        "Built the complete Pixel Forge agency site with 4 sections:\n"
        "- Header: minimal sticky bar with wordmark and pill CTA\n"
        "- Hero: oversized tagline headline with a glowing magenta blob backdrop\n"
        "- Services: 2x2 grid of all 4 services with numbered labels\n"
        "- Footer: wordmark, email, and Instagram handle\n"
        "Color scheme: near-black (#141414), magenta (#ec4899) accent, Space Grotesk headings on Inter body."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_agency_pixel_forge", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 9. trajectory_realestate_01 — Harbor View Realty
# ─────────────────────────────────────────────────────────────────────────
def trajectory_realestate_01():
    brief_xml = """<content_brief>
  <business_name>Harbor View Realty</business_name>
  <tagline>Coastal homes, expertly matched to you</tagline>
  <business_type>real_estate</business_type>
  <primary_color>#0c1e2e</primary_color>
  <accent_color>#0ea5a4</accent_color>
  <font_heading>Libre Baskerville</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, listings, footer</sections>
  <listing name="Cliffside Modern" price="$1,850,000" details="4 bed, 3 bath, 3,200 sqft, ocean view" />
  <listing name="Harbor Cottage" price="$695,000" details="2 bed, 1 bath, 1,100 sqft, walk to marina" />
  <listing name="The Lighthouse Estate" price="$3,200,000" details="5 bed, 4.5 bath, 5,600 sqft, private dock" />
  <contact>
    <address>200 Marina Boulevard, Newport RI 02840</address>
    <phone>+1 401 555 0199</phone>
    <email>info@harborviewrealty.com</email>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky nav with the "
        "agency name on the left, links (Listings, About, Contact) on the right, and "
        "a 'Schedule a Showing' CTA. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`hv-header${scrolled ? ' hv-header--scrolled' : ''}`}>
      <div className="hv-header__inner">
        <a href="#" className="hv-header__logo">Harbor View Realty</a>
        <nav className="hv-header__nav" aria-label="Main navigation">
          <a href="#hero" className="hv-header__link">Home</a>
          <a href="#listings" className="hv-header__link">Featured Listings</a>
          <a href="#footer" className="hv-header__link">Contact</a>
        </nav>
        <a href="mailto:info@harborviewrealty.com" className="hv-header__cta">Schedule a Showing</a>
      </div>
    </header>
  );
}"""
    header_css = """\
.hv-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(12, 30, 46, 0.9);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(14, 165, 164, 0.15);
  transition: box-shadow 0.3s;
}
.hv-header--scrolled { box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
.hv-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.hv-header__logo {
  font-family: 'Libre Baskerville', serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #f0f9f9;
  text-decoration: none;
}
.hv-header__nav { display: flex; gap: 1.75rem; }
.hv-header__link {
  color: #9fb8c4;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 500;
  transition: color 0.2s;
}
.hv-header__link:hover { color: #0ea5a4; }
.hv-header__cta {
  padding: 0.55rem 1.3rem;
  background: #0ea5a4;
  color: #0c1e2e;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.2s, transform 0.15s;
}
.hv-header__cta:hover { background: #2dd4bf; transform: translateY(-1px); }
@media (max-width: 700px) { .hv-header__nav { display: none; } }"""
    t1_thought = thought(
        "Real estate needs to feel trustworthy and coastal-premium, so I paired a "
        "deep navy background with a teal accent that evokes water, and used the "
        "Libre Baskerville serif for the wordmark to signal established credibility."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: full-width banner with the tagline as h1, "
        "subheading, and a CTA. Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="hv-hero" id="hero">
      <div className="hv-hero__overlay" aria-hidden="true" />
      <div className="hv-hero__content">
        <h1 className="hv-hero__title">Coastal homes,<br />expertly matched to you</h1>
        <p className="hv-hero__subtitle">
          From waterfront cottages to full harbor estates, we know this coastline
          street by street.
        </p>
        <a href="#listings" className="hv-hero__cta">View Listings</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.hv-hero {
  position: relative;
  min-height: 88vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    linear-gradient(160deg, rgba(12,30,46,0.9) 0%, rgba(12,30,46,0.55) 60%, rgba(14,165,164,0.15) 100%),
    url('https://images.unsplash.com/photo-1505843513577-22bb7d21e455?w=1600&q=80') center/cover no-repeat;
}
.hv-hero__overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 70% 40%, rgba(14,165,164,0.1) 0%, transparent 60%);
  pointer-events: none;
}
.hv-hero__content {
  position: relative;
  z-index: 1;
  max-width: 720px;
  padding: 2rem;
  text-align: center;
}
.hv-hero__title {
  font-family: 'Libre Baskerville', serif;
  font-size: clamp(2.1rem, 5vw, 3.6rem);
  font-weight: 700;
  color: #f0f9f9;
  line-height: 1.25;
  margin: 0 0 1.5rem;
}
.hv-hero__subtitle {
  font-size: 1.05rem;
  color: #b6ccd4;
  line-height: 1.75;
  margin: 0 auto 2.25rem;
  max-width: 520px;
}
.hv-hero__cta {
  display: inline-block;
  padding: 0.85rem 2.1rem;
  background: #0ea5a4;
  color: #0c1e2e;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
}
.hv-hero__cta:hover { background: #2dd4bf; transform: translateY(-2px); }"""
    t2_thought = thought(
        "The hero uses a coastal property photograph with a navy-to-teal gradient "
        "overlay so the water tones in both the photo and the accent color reinforce "
        "each other. The serif tagline headline keeps the premium, established-agency "
        "feel from the header."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Listings section: all 3 listings from the brief as cards with "
        "name, price, and details, in a responsive grid. "
        "Files: src/components/Listings.tsx + src/components/Listings.css",
    )

    # ── Turn 3: Listings ──
    listings_tsx = """\
import React from 'react';
import './Listings.css';

interface Listing { name: string; price: string; details: string; }

const LISTINGS: Listing[] = [
  { name: 'Cliffside Modern', price: '$1,850,000', details: '4 bed, 3 bath, 3,200 sqft, ocean view' },
  { name: 'Harbor Cottage', price: '$695,000', details: '2 bed, 1 bath, 1,100 sqft, walk to marina' },
  { name: 'The Lighthouse Estate', price: '$3,200,000', details: '5 bed, 4.5 bath, 5,600 sqft, private dock' },
];

export function Listings() {
  return (
    <section className="hv-listings" id="listings" aria-labelledby="hv-listings-heading">
      <div className="hv-listings__inner">
        <div className="hv-listings__header">
          <p className="hv-listings__eyebrow">Featured Homes</p>
          <h2 id="hv-listings-heading" className="hv-listings__title">Current Listings</h2>
        </div>
        <div className="hv-listings__grid">
          {LISTINGS.map(l => (
            <article key={l.name} className="hv-listing-card">
              <div className="hv-listing-card__image" aria-hidden="true" />
              <div className="hv-listing-card__body">
                <div className="hv-listing-card__top">
                  <h3 className="hv-listing-card__name">{l.name}</h3>
                  <span className="hv-listing-card__price">{l.price}</span>
                </div>
                <p className="hv-listing-card__details">{l.details}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}"""
    listings_css = """\
.hv-listings {
  padding: 6.5rem 2rem;
  background: #102938;
  border-top: 1px solid rgba(14,165,164,0.1);
}
.hv-listings__inner { max-width: 1100px; margin: 0 auto; }
.hv-listings__header { text-align: center; margin-bottom: 3.5rem; }
.hv-listings__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #0ea5a4;
  margin: 0 0 0.75rem;
}
.hv-listings__title {
  font-family: 'Libre Baskerville', serif;
  font-size: clamp(1.8rem, 3.4vw, 2.6rem);
  color: #f0f9f9;
  margin: 0;
}
.hv-listings__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}
.hv-listing-card {
  background: #14344a;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s, border-color 0.2s;
}
.hv-listing-card:hover { transform: translateY(-4px); border-color: rgba(14,165,164,0.4); }
.hv-listing-card__image {
  aspect-ratio: 4 / 3;
  background: linear-gradient(150deg, #1e4a63 0%, #0ea5a4 130%);
}
.hv-listing-card__body { padding: 1.5rem; }
.hv-listing-card__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 0.6rem;
  flex-wrap: wrap;
}
.hv-listing-card__name {
  font-family: 'Libre Baskerville', serif;
  font-size: 1.1rem;
  color: #f0f9f9;
  margin: 0;
}
.hv-listing-card__price { font-size: 1rem; font-weight: 700; color: #2dd4bf; white-space: nowrap; }
.hv-listing-card__details { font-size: 0.85rem; color: #8fa8b3; margin: 0; line-height: 1.6; }
@media (max-width: 900px) { .hv-listings__grid { grid-template-columns: 1fr; } }"""
    t3_thought = thought(
        "The 3 listings get a photo-style card grid with a teal-navy gradient "
        "placeholder in place of an actual property photo, price called out in "
        "bright teal so it's the first thing scanned, and details (beds/baths/sqft) "
        "kept compact below the name."
    )
    t3_action = write_site(
        "src/components/Listings.tsx", listings_tsx,
        "src/components/Listings.css", listings_css,
    )
    t3_obs = obs_ok(
        ["src/components/Listings.tsx", "src/components/Listings.css"],
        "Write the Footer section: dark navy footer with agency name, address, "
        "phone, email, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 4: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="hv-footer" id="footer" aria-label="Site footer">
      <div className="hv-footer__inner">
        <div className="hv-footer__brand">
          <p className="hv-footer__logo">Harbor View Realty</p>
          <p className="hv-footer__tagline">Coastal homes, expertly matched to you</p>
        </div>
        <address className="hv-footer__contact">
          <p>200 Marina Boulevard<br />Newport RI 02840</p>
          <a href="tel:+14015550199" className="hv-footer__link">+1 401 555 0199</a>
          <a href="mailto:info@harborviewrealty.com" className="hv-footer__link">info@harborviewrealty.com</a>
        </address>
      </div>
      <div className="hv-footer__bottom">
        <p>&copy; {year} Harbor View Realty. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.hv-footer {
  background: #081722;
  border-top: 1px solid rgba(14,165,164,0.2);
  padding: 4rem 2rem 0;
}
.hv-footer__inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 2rem;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.hv-footer__logo {
  font-family: 'Libre Baskerville', serif;
  font-size: 1.2rem;
  color: #f0f9f9;
  margin: 0 0 0.5rem;
}
.hv-footer__tagline { font-size: 0.88rem; color: #5f7c88; margin: 0; }
.hv-footer__contact { font-style: normal; display: flex; flex-direction: column; gap: 0.5rem; color: #9fb8c4; font-size: 0.88rem; line-height: 1.6; text-align: right; }
.hv-footer__link { color: #0ea5a4; text-decoration: none; }
.hv-footer__link:hover { text-decoration: underline; }
.hv-footer__bottom {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.78rem;
  color: #24404f;
}
@media (max-width: 640px) {
  .hv-footer__inner { flex-direction: column; }
  .hv-footer__contact { text-align: left; }
}"""
    t4_thought = thought(
        "Footer closes with brand/tagline on the left and the full address, phone, "
        "and email on the right, consistent with the two-column pattern established "
        "for professional-services footers in this palette."
    )
    t4_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Listings.tsx", "src/components/Listings.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)
    t5_thought = thought("All four sections accepted: Header, Hero, Listings, Footer.")
    t5_action = finish(
        "Built the complete Harbor View Realty site with 4 sections:\n"
        "- Header: sticky nav with serif wordmark and showing-request CTA\n"
        "- Hero: coastal photo banner with tagline and CTA\n"
        "- Listings: 3-card grid with price, beds/baths/sqft details\n"
        "- Footer: brand, address, phone, and email\n"
        "Color scheme: deep navy (#0c1e2e), teal (#0ea5a4) accent, Libre Baskerville headings on Inter body."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_realestate_harbor_view", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 10. trajectory_education_01 — CodeCraft Academy (coding bootcamp)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_education_01():
    brief_xml = """<content_brief>
  <business_name>CodeCraft Academy</business_name>
  <tagline>From zero to hired engineer in 16 weeks</tagline>
  <business_type>education</business_type>
  <primary_color>#0a0e1a</primary_color>
  <accent_color>#22c55e</accent_color>
  <font_heading>Sora</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, curriculum, footer</sections>
  <curriculum_module name="Foundations" weeks="4" description="Programming fundamentals, git, and computer science basics in JavaScript and Python." />
  <curriculum_module name="Full-Stack Web" weeks="6" description="React, Node.js, REST APIs, and relational databases, building 3 shipped projects." />
  <curriculum_module name="Systems &amp; Deployment" weeks="3" description="Docker, CI/CD, cloud deployment on AWS, and basic system design." />
  <curriculum_module name="Career Sprint" weeks="3" description="Portfolio polish, mock interviews, and 1:1 hiring support with partner companies." />
  <contact>
    <email>admissions@codecraftacademy.io</email>
    <phone>+1 415 555 0123</phone>
    <note>92% job placement rate within 6 months of graduation</note>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        + brief_xml
        + "\n\nYou will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky nav with the "
        "academy name on the left, links (Curriculum, Outcomes, Contact) on the "
        "right, and an 'Apply Now' CTA. Files: src/components/Header.tsx + src/components/Header.css"
    )

    # ── Turn 1: Header ──
    header_tsx = """\
import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`cc-header${scrolled ? ' cc-header--scrolled' : ''}`}>
      <div className="cc-header__inner">
        <a href="#" className="cc-header__logo">CodeCraft Academy</a>
        <nav className="cc-header__nav" aria-label="Main navigation">
          <a href="#hero" className="cc-header__link">Home</a>
          <a href="#curriculum" className="cc-header__link">Curriculum</a>
          <a href="#footer" className="cc-header__link">Admissions</a>
        </nav>
        <a href="mailto:admissions@codecraftacademy.io" className="cc-header__cta">Apply Now</a>
      </div>
    </header>
  );
}"""
    header_css = """\
.cc-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba(10, 14, 26, 0.9);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(34, 197, 94, 0.15);
  transition: box-shadow 0.3s;
}
.cc-header--scrolled { box-shadow: 0 4px 20px rgba(0,0,0,0.35); }
.cc-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.cc-header__logo {
  font-family: 'Sora', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: #f1f5f9;
  text-decoration: none;
}
.cc-header__nav { display: flex; gap: 1.75rem; }
.cc-header__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 500;
  transition: color 0.2s;
}
.cc-header__link:hover { color: #22c55e; }
.cc-header__cta {
  padding: 0.55rem 1.3rem;
  background: #22c55e;
  color: #0a0e1a;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.2s, transform 0.15s;
}
.cc-header__cta:hover { background: #4ade80; transform: translateY(-1px); }
@media (max-width: 700px) { .cc-header__nav { display: none; } }"""
    t1_thought = thought(
        "A coding bootcamp header should feel outcomes-driven and modern: dark navy "
        "base with a green accent that reads as 'go/growth', a clean Sora wordmark, "
        "and an unmissable Apply Now button since admissions conversion is the site's "
        "main goal."
    )
    t1_action = write_site(
        "src/components/Header.tsx", header_tsx,
        "src/components/Header.css", header_css,
    )
    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: full-width banner with the tagline as h1, "
        "subheading, the job placement stat, and a CTA. "
        "Files: src/components/Hero.tsx + src/components/Hero.css",
    )

    # ── Turn 2: Hero ──
    hero_tsx = """\
import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="cc-hero" id="hero">
      <div className="cc-hero__glow" aria-hidden="true" />
      <div className="cc-hero__content">
        <div className="cc-hero__badge">
          <span className="cc-hero__badge-dot" aria-hidden="true" />
          92% job placement rate within 6 months of graduation
        </div>
        <h1 className="cc-hero__title">From zero to hired engineer<br />in 16 weeks</h1>
        <p className="cc-hero__subtitle">
          A full-time, project-based curriculum built with hiring partners, ending
          with dedicated career support until you land the job.
        </p>
        <a href="mailto:admissions@codecraftacademy.io" className="cc-hero__cta">Apply Now</a>
      </div>
    </section>
  );
}"""
    hero_css = """\
.cc-hero {
  position: relative;
  min-height: 86vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #0a0e1a;
}
.cc-hero__glow {
  position: absolute;
  top: -20%;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(34,197,94,0.16) 0%, transparent 65%);
  pointer-events: none;
}
.cc-hero__content {
  position: relative;
  z-index: 1;
  max-width: 720px;
  padding: 2rem;
  text-align: center;
}
.cc-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 1rem;
  border-radius: 2rem;
  background: rgba(34,197,94,0.1);
  border: 1px solid rgba(34,197,94,0.3);
  font-size: 0.85rem;
  color: #86efac;
  font-weight: 500;
  margin-bottom: 1.75rem;
}
.cc-hero__badge-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }
.cc-hero__title {
  font-family: 'Sora', sans-serif;
  font-size: clamp(2.2rem, 5vw, 3.75rem);
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 0 0 1.5rem;
}
.cc-hero__subtitle {
  font-size: 1.05rem;
  color: #64748b;
  line-height: 1.75;
  margin: 0 auto 2.5rem;
  max-width: 540px;
}
.cc-hero__cta {
  display: inline-block;
  padding: 0.9rem 2.25rem;
  background: #22c55e;
  color: #0a0e1a;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}
.cc-hero__cta:hover { background: #4ade80; transform: translateY(-2px); box-shadow: 0 8px 28px rgba(34,197,94,0.35); }"""
    t2_thought = thought(
        "The placement rate is the single most persuasive fact in the brief, so it "
        "leads the hero as a badge above the headline rather than being buried in the "
        "footer. A soft green glow behind the content reinforces the 'growth' "
        "association of the accent color."
    )
    t2_action = write_site(
        "src/components/Hero.tsx", hero_tsx,
        "src/components/Hero.css", hero_css,
    )
    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Curriculum section: all 4 curriculum modules from the brief as a "
        "timeline/list with name, weeks, and description. "
        "Files: src/components/Curriculum.tsx + src/components/Curriculum.css",
    )

    # ── Turn 3: Curriculum ──
    curriculum_tsx = """\
import React from 'react';
import './Curriculum.css';

interface Module { name: string; weeks: string; description: string; }

const MODULES: Module[] = [
  { name: 'Foundations', weeks: '4', description: 'Programming fundamentals, git, and computer science basics in JavaScript and Python.' },
  { name: 'Full-Stack Web', weeks: '6', description: 'React, Node.js, REST APIs, and relational databases, building 3 shipped projects.' },
  { name: 'Systems & Deployment', weeks: '3', description: 'Docker, CI/CD, cloud deployment on AWS, and basic system design.' },
  { name: 'Career Sprint', weeks: '3', description: 'Portfolio polish, mock interviews, and 1:1 hiring support with partner companies.' },
];

export function Curriculum() {
  return (
    <section className="cc-curriculum" id="curriculum" aria-labelledby="cc-curriculum-heading">
      <div className="cc-curriculum__inner">
        <div className="cc-curriculum__header">
          <p className="cc-curriculum__eyebrow">16-Week Program</p>
          <h2 id="cc-curriculum-heading" className="cc-curriculum__title">Curriculum</h2>
        </div>
        <ol className="cc-curriculum__list">
          {MODULES.map((m, i) => (
            <li key={m.name} className="cc-module">
              <div className="cc-module__marker" aria-hidden="true">{i + 1}</div>
              <div className="cc-module__body">
                <div className="cc-module__top">
                  <h3 className="cc-module__name">{m.name}</h3>
                  <span className="cc-module__weeks">{m.weeks} weeks</span>
                </div>
                <p className="cc-module__desc">{m.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}"""
    curriculum_css = """\
.cc-curriculum {
  padding: 6.5rem 2rem;
  background: #0d1220;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.cc-curriculum__inner { max-width: 820px; margin: 0 auto; }
.cc-curriculum__header { text-align: center; margin-bottom: 3.5rem; }
.cc-curriculum__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #22c55e;
  margin: 0 0 0.75rem;
}
.cc-curriculum__title {
  font-family: 'Sora', sans-serif;
  font-size: clamp(1.9rem, 3.6vw, 2.75rem);
  font-weight: 700;
  color: #f1f5f9;
  margin: 0;
}
.cc-curriculum__list {
  list-style: none;
  margin: 0;
  padding: 0;
  position: relative;
}
.cc-curriculum__list::before {
  content: '';
  position: absolute;
  left: 21px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: rgba(34,197,94,0.2);
}
.cc-module { display: flex; gap: 1.5rem; padding-bottom: 2.5rem; position: relative; }
.cc-module:last-child { padding-bottom: 0; }
.cc-module__marker {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #22c55e;
  color: #0a0e1a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  z-index: 1;
}
.cc-module__top { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
.cc-module__name { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; margin: 0; }
.cc-module__weeks { font-size: 0.8rem; font-weight: 700; color: #86efac; white-space: nowrap; }
.cc-module__desc { font-size: 0.9rem; color: #64748b; line-height: 1.7; margin: 0.5rem 0 0; }"""
    t3_thought = thought(
        "The 4 curriculum modules progress in a fixed sequence (16 weeks total), so a "
        "numbered vertical timeline communicates that structure far better than a "
        "grid of cards. Week counts are called out in light green next to each module "
        "name for quick scanning."
    )
    t3_action = write_site(
        "src/components/Curriculum.tsx", curriculum_tsx,
        "src/components/Curriculum.css", curriculum_css,
    )
    t3_obs = obs_ok(
        ["src/components/Curriculum.tsx", "src/components/Curriculum.css"],
        "Write the Footer section: dark footer with academy name, contact email, "
        "phone, placement stat note, and copyright. "
        "Files: src/components/Footer.tsx + src/components/Footer.css",
    )

    # ── Turn 4: Footer ──
    footer_tsx = """\
import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="cc-footer" id="footer" aria-label="Site footer">
      <div className="cc-footer__inner">
        <div className="cc-footer__brand">
          <p className="cc-footer__logo">CodeCraft Academy</p>
          <p className="cc-footer__tagline">From zero to hired engineer in 16 weeks</p>
        </div>
        <div className="cc-footer__contact">
          <a href="mailto:admissions@codecraftacademy.io" className="cc-footer__link">
            admissions@codecraftacademy.io
          </a>
          <a href="tel:+14155550123" className="cc-footer__link">+1 415 555 0123</a>
          <p className="cc-footer__note">92% job placement rate within 6 months of graduation</p>
        </div>
      </div>
      <div className="cc-footer__bottom">
        <p>&copy; {year} CodeCraft Academy. All rights reserved.</p>
      </div>
    </footer>
  );
}"""
    footer_css = """\
.cc-footer {
  background: #060810;
  border-top: 1px solid rgba(34,197,94,0.18);
  padding: 4rem 2rem 0;
}
.cc-footer__inner {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 2rem;
  padding-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.cc-footer__logo { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.1rem; color: #f1f5f9; margin: 0 0 0.5rem; }
.cc-footer__tagline { font-size: 0.88rem; color: #475569; margin: 0; }
.cc-footer__contact { display: flex; flex-direction: column; gap: 0.5rem; text-align: right; }
.cc-footer__link { font-size: 0.88rem; color: #22c55e; text-decoration: none; }
.cc-footer__link:hover { text-decoration: underline; }
.cc-footer__note { font-size: 0.82rem; color: #64748b; margin: 0.25rem 0 0; }
.cc-footer__bottom {
  max-width: 1080px;
  margin: 0 auto;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.78rem;
  color: #1e293b;
}
@media (max-width: 640px) {
  .cc-footer__inner { flex-direction: column; }
  .cc-footer__contact { text-align: left; }
}"""
    t4_thought = thought(
        "Footer restates the placement stat once more alongside contact details "
        "since it's the academy's strongest trust signal, closing with brand and "
        "tagline on the left and admissions contact plus the stat on the right."
    )
    t4_action = write_site(
        "src/components/Footer.tsx", footer_tsx,
        "src/components/Footer.css", footer_css,
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Curriculum.tsx", "src/components/Curriculum.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t4_obs = obs_done(all_files)
    t5_thought = thought("All four sections accepted: Header, Hero, Curriculum, Footer.")
    t5_action = finish(
        "Built the complete CodeCraft Academy bootcamp site with 4 sections:\n"
        "- Header: sticky nav with wordmark, links, and Apply Now CTA\n"
        "- Hero: placement-rate badge, tagline headline, and CTA\n"
        "- Curriculum: numbered vertical timeline of all 4 modules\n"
        "- Footer: brand, contact details, and placement stat\n"
        "Color scheme: dark navy (#0a0e1a), green (#22c55e) accent, Sora headings on Inter body."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
    ]
    return {"task_id": "site_education_codecraft_academy", "messages": messages}


BATCH_2 = [
    trajectory_restaurant_02,
    trajectory_event_01,
    trajectory_saas_02,
    trajectory_ecommerce_01,
    trajectory_portfolio_02,
    trajectory_nonprofit_01,
    trajectory_fitness_01,
    trajectory_agency_01,
    trajectory_realestate_01,
    trajectory_education_01,
]


# ==============================================================================
# BATCH 3: 10 Premium Domains
# ==============================================================================



# ─────────────────────────────────────────────────────────────────────────
# 1. trajectory_fintech_01 — NexusPay (B2B cross-border treasury)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_fintech_01():
    brief_xml = """<content_brief>
  <business_name>NexusPay</business_name>
  <tagline>Frictionless global payments and multi-currency treasury</tagline>
  <business_type>fintech</business_type>
  <primary_color>#0a0f1d</primary_color>
  <accent_color>#06b6d4</accent_color>
  <font_heading>Inter</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, features, pricing, footer</sections>
  <feature icon="globe" title="130+ Currencies" description="Send, hold, and settle international wire transfers in seconds with institutional FX spreads." />
  <feature icon="shield" title="Tier-1 Compliance" description="Automated AML/KYC screening, FDIC pass-through insurance up to $5M, and biometric authorizations." />
  <feature icon="terminal" title="Developer-First API" description="Unified REST and GraphQL endpoints with webhooks, 99.999% SLA, and zero-downtime ledger migration." />
  <feature icon="chart" title="Real-Time Liquidity" description="AI cashflow forecasting predicts working capital shortfalls before month-end closing." />
  <pricing_tier name="Starter" price="$0/mo" features="Up to $50k monthly volume, 15 local accounts, basic dashboard, community support" />
  <pricing_tier name="Growth" price="$249/mo" highlighted="true" features="Unlimited volume, 40+ virtual debit cards, wholesale FX rates, dedicated Slack channel" />
  <pricing_tier name="Enterprise" price="Custom" features="Dedicated treasury manager, custom ERP sync (NetSuite, SAP), custom SLA and underwriting" />
  <contact>
    <email>support@nexuspay.io</email>
    <phone>+1 (800) 555-0192</phone>
    <address>100 Montgomery St, Suite 2400, San Francisco, CA 94104</address>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        f"{brief_xml}\n\n"
        "You will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the business name/logo on the left and navigation links (Features, Solutions, Pricing, Developers) on the right, plus 'Sign In' and 'Open Account' CTA buttons. Files: src/components/Header.tsx + src/components/Header.css"
    )

    t1_thought = thought(
        "I'll start with the NexusPay Header. For a high-trust B2B fintech, the navbar needs to feel secure and sleek: "
        "dark navy background (#0a0f1d) with a glowing electric cyan accent (#06b6d4), glassmorphism on scroll, "
        "and clear hierarchy between secondary links and the primary CTA."
    )
    t1_action = write_site(
        "src/components/Header.tsx",
        """import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`nexus-header ${scrolled ? 'nexus-header--scrolled' : ''}`}>
      <div className="nexus-header__container">
        <a href="#" className="nexus-header__logo" aria-label="NexusPay Home">
          <span className="nexus-header__logo-icon">❖</span>
          <span className="nexus-header__logo-text">Nexus<span>Pay</span></span>
        </a>

        <nav className="nexus-header__nav" aria-label="Main Navigation">
          <a href="#hero" className="nexus-header__link">Overview</a>
          <a href="#features" className="nexus-header__link">Capabilities</a>
          <a href="#pricing" className="nexus-header__link">Pricing</a>
          <a href="#footer" className="nexus-header__link">Security</a>
        </nav>

        <div className="nexus-header__actions">
          <a href="#pricing" className="nexus-btn nexus-btn--primary">Get Started</a>
        </div>

        <button 
          className="nexus-header__toggle"
          aria-label="Toggle Navigation"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          <span /><span /><span />
        </button>
      </div>

      {mobileOpen && (
        <div className="nexus-header__mobile-menu">
          <a href="#hero" onClick={() => setMobileOpen(false)}>Overview</a>
          <a href="#features" onClick={() => setMobileOpen(false)}>Capabilities</a>
          <a href="#pricing" onClick={() => setMobileOpen(false)}>Pricing</a>
          <a href="#footer" onClick={() => setMobileOpen(false)}>Security</a>
          <div className="nexus-header__mobile-actions">
            <a href="#pricing" className="nexus-btn nexus-btn--primary" onClick={() => setMobileOpen(false)}>Get Started</a>
          </div>
        </div>
      )}
    </header>
  );
}
""",
        "src/components/Header.css",
        """.nexus-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: rgba(10, 15, 29, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.nexus-header--scrolled {
  background: rgba(10, 15, 29, 0.96);
  border-color: rgba(6, 182, 212, 0.25);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}
.nexus-header__container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.nexus-header__logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #f8fafc;
}
.nexus-header__logo-icon {
  color: #06b6d4;
  font-size: 1.5rem;
  text-shadow: 0 0 16px rgba(6, 182, 212, 0.6);
}
.nexus-header__logo-text span {
  color: #06b6d4;
}
.nexus-header__nav {
  display: flex;
  gap: 2.2rem;
  align-items: center;
}
.nexus-header__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 500;
  transition: color 0.2s ease;
}
.nexus-header__link:hover {
  color: #06b6d4;
}
.nexus-header__actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.nexus-btn {
  padding: 0.6rem 1.35rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.nexus-btn--ghost {
  color: #cbd5e1;
  background: transparent;
}
.nexus-btn--ghost:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.05);
}
.nexus-btn--primary {
  background: #06b6d4;
  color: #0a0f1d;
  box-shadow: 0 0 20px rgba(6, 182, 212, 0.35);
}
.nexus-btn--primary:hover {
  background: #22d3ee;
  transform: translateY(-2px);
  box-shadow: 0 0 28px rgba(6, 182, 212, 0.55);
}
.nexus-header__toggle {
  display: none;
  flex-direction: column;
  gap: 5px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
}
.nexus-header__toggle span {
  width: 22px;
  height: 2px;
  background: #cbd5e1;
  border-radius: 2px;
}
.nexus-header__mobile-menu {
  display: flex;
  flex-direction: column;
  padding: 1.5rem 2rem;
  background: #0a0f1d;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  gap: 1rem;
}
.nexus-header__mobile-menu a {
  color: #cbd5e1;
  text-decoration: none;
  font-size: 1rem;
}
.nexus-header__mobile-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}
@media (max-width: 860px) {
  .nexus-header__nav, .nexus-header__actions {
    display: none;
  }
  .nexus-header__toggle {
    display: flex;
  }
}
"""
    )

    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: a high-impact fintech hero with a badge, large title with gradient text, subtitle, two CTA buttons, trust badges, and an interactive real-time multi-currency transaction card preview. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    t2_thought = thought(
        "Header accepted. Now writing the Hero section. A high-converting fintech hero requires an animated status badge "
        "('Real-Time FX Engine Live'), prominent headline highlighting global money movement, dual CTAs, live transaction card preview, "
        "and stats showing $14B+ settled and 99.999% uptime."
    )
    t2_action = write_site(
        "src/components/Hero.tsx",
        """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="nexus-hero" id="hero">
      <div className="nexus-hero__glow" aria-hidden="true" />
      <div className="nexus-hero__container">
        <div className="nexus-hero__content">
          <div className="nexus-hero__badge">
            <span className="nexus-hero__badge-pulse" />
            Zero-spread FX engine now live across 130+ markets
          </div>
          <h1 className="nexus-hero__title">
            Frictionless global payments &amp; <span className="nexus-hero__gradient">multi-currency treasury</span>
          </h1>
          <p className="nexus-hero__subtitle">
            Scale your international business with high-throughput settlement rails, institutional liquidity pools, 
            and programmatic bank accounts in 35+ local jurisdictions.
          </p>
          <div className="nexus-hero__actions">
            <a href="#pricing" className="nexus-btn nexus-btn--primary nexus-btn--lg">
              Start Free Trial →
            </a>
            <a href="#footer" className="nexus-btn nexus-btn--outline nexus-btn--lg">
              Book Live Demo
            </a>
          </div>
          <div className="nexus-hero__metrics">
            <div className="nexus-metric">
              <span className="nexus-metric__val">$14.2B+</span>
              <span className="nexus-metric__label">Annual Volume</span>
            </div>
            <div className="nexus-metric">
              <span className="nexus-metric__val">130+</span>
              <span className="nexus-metric__label">Countries Supported</span>
            </div>
            <div className="nexus-metric">
              <span className="nexus-metric__val">&lt;850ms</span>
              <span className="nexus-metric__label">Avg Settlement</span>
            </div>
          </div>
        </div>

        <div className="nexus-hero__visual" aria-hidden="true">
          <div className="nexus-card-preview">
            <div className="nexus-card-preview__header">
              <div className="nexus-card-preview__dots">
                <span /><span /><span />
              </div>
              <span className="nexus-card-preview__tag">TREASURY STREAM</span>
            </div>
            <div className="nexus-card-preview__balance">
              <span className="nexus-card-preview__sub">Total Liquid Reserves</span>
              <span className="nexus-card-preview__amount">$4,892,140.80</span>
            </div>
            <div className="nexus-card-preview__trans">
              <div className="nexus-trans-row">
                <div className="nexus-trans-flag">🇪🇺</div>
                <div className="nexus-trans-info">
                  <div className="nexus-trans-title">Stripe Ireland EU Settlement</div>
                  <div className="nexus-trans-meta">SEPA Instant · 2s ago</div>
                </div>
                <div className="nexus-trans-val text-green">+€124,500.00</div>
              </div>
              <div className="nexus-trans-row">
                <div className="nexus-trans-flag">🇯🇵</div>
                <div className="nexus-trans-info">
                  <div className="nexus-trans-title">Tokyo Cloud CDN Tier 1</div>
                  <div className="nexus-trans-meta">Zengin Rail · 41s ago</div>
                </div>
                <div className="nexus-trans-val text-muted">-¥3,480,000</div>
              </div>
              <div className="nexus-trans-row">
                <div className="nexus-trans-flag">🇬🇧</div>
                <div className="nexus-trans-info">
                  <div className="nexus-trans-title">London Venture Partner Payout</div>
                  <div className="nexus-trans-meta">CHAPS Real-Time · 2m ago</div>
                </div>
                <div className="nexus-trans-val text-green">+£450,000.00</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Hero.css",
        """.nexus-hero {
  position: relative;
  overflow: hidden;
  padding: 6.5rem 2rem 5rem;
  background: radial-gradient(circle at 50% -20%, #152347 0%, #0a0f1d 70%);
}
.nexus-hero__glow {
  position: absolute;
  top: -100px;
  right: 10%;
  width: 650px;
  height: 650px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.18) 0%, transparent 70%);
  pointer-events: none;
}
.nexus-hero__container {
  max-width: 1240px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 4rem;
  align-items: center;
}
.nexus-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 1rem;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 9999px;
  color: #38bdf8;
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
}
.nexus-hero__badge-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #06b6d4;
  box-shadow: 0 0 10px #06b6d4;
  animation: pulse-ring 2s infinite ease-in-out;
}
@keyframes pulse-ring {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.4; }
}
.nexus-hero__title {
  font-size: clamp(2.5rem, 5vw, 4rem);
  font-weight: 800;
  line-height: 1.1;
  color: #ffffff;
  letter-spacing: -0.03em;
  margin-bottom: 1.4rem;
}
.nexus-hero__gradient {
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #93c5fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.nexus-hero__subtitle {
  font-size: 1.12rem;
  line-height: 1.7;
  color: #94a3b8;
  max-width: 580px;
  margin-bottom: 2.5rem;
}
.nexus-hero__actions {
  display: flex;
  gap: 1.2rem;
  margin-bottom: 3.5rem;
  flex-wrap: wrap;
}
.nexus-btn--lg {
  padding: 0.85rem 2rem;
  font-size: 1rem;
}
.nexus-btn--outline {
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f8fafc;
  background: transparent;
}
.nexus-btn--outline:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: #06b6d4;
}
.nexus-hero__metrics {
  display: flex;
  gap: 2.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 2rem;
}
.nexus-metric__val {
  display: block;
  font-size: 1.8rem;
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.02em;
}
.nexus-metric__label {
  font-size: 0.8rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.nexus-card-preview {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  padding: 1.8rem;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
.nexus-card-preview__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.nexus-card-preview__dots {
  display: flex;
  gap: 6px;
}
.nexus-card-preview__dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #334155;
}
.nexus-card-preview__tag {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #06b6d4;
}
.nexus-card-preview__balance {
  margin-bottom: 1.8rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.nexus-card-preview__sub {
  display: block;
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 0.3rem;
}
.nexus-card-preview__amount {
  font-size: 2.2rem;
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.02em;
}
.nexus-card-preview__trans {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.nexus-trans-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
}
.nexus-trans-flag {
  font-size: 1.5rem;
}
.nexus-trans-info {
  flex: 1;
}
.nexus-trans-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #f1f5f9;
}
.nexus-trans-meta {
  font-size: 0.75rem;
  color: #64748b;
}
.nexus-trans-val {
  font-size: 0.9rem;
  font-weight: 700;
}
.text-green { color: #10b981; }
.text-muted { color: #94a3b8; }
@media (max-width: 990px) {
  .nexus-hero__container {
    grid-template-columns: 1fr;
  }
}
"""
    )

    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Features section: display the 4 features from the content brief (130+ Currencies, Tier-1 Compliance, Developer-First API, Real-Time Liquidity) in a responsive 2x2 grid with SVG icons, subtle hover lift, and glow borders. Files: src/components/Features.tsx + src/components/Features.css"
    )

    t3_thought = thought(
        "Hero accepted. Now implementing the Features section with the 4 pillars from the brief. "
        "Each card will use clean modern cards with dark glass backgrounds, cyan icon containers, "
        "and clean typography."
    )
    t3_action = write_site(
        "src/components/Features.tsx",
        """import React from 'react';
import './Features.css';

interface FeatureItem {
  icon: string;
  title: string;
  desc: string;
  metric: string;
}

const FEATURES: FeatureItem[] = [
  {
    icon: '🌐',
    title: '130+ Currencies & Local Rails',
    desc: 'Send, hold, and settle international wire transfers in seconds with wholesale institutional FX spreads and direct clearing connections.',
    metric: 'Instant ACH, SEPA & Faster Payments'
  },
  {
    icon: '🛡️',
    title: 'Tier-1 Security & Bank Grade',
    desc: 'Automated AML/KYC screening, FDIC pass-through insurance up to $5M, SOC 2 Type II compliance, and granular role permissions.',
    metric: 'Hardware Token & Biometric Auth'
  },
  {
    icon: '⚡',
    title: 'Developer-First REST & Webhooks',
    desc: 'Unified REST and GraphQL endpoints with idempotency keys, webhooks, 99.999% SLA, and zero-downtime ledger migration.',
    metric: '<120ms P99 API Latency'
  },
  {
    icon: '📊',
    title: 'Real-Time Treasury Liquidity',
    desc: 'AI cashflow forecasting predicts working capital shortfalls across international entities before month-end financial closing.',
    metric: 'Multi-Entity Reconciliation'
  }
];

export function Features() {
  return (
    <section className="nexus-features" id="features">
      <div className="nexus-features__container">
        <div className="nexus-features__header">
          <span className="nexus-badge">ENTERPRISE INFRASTRUCTURE</span>
          <h2 className="nexus-features__title">Built for modern financial engineering</h2>
          <p className="nexus-features__sub">
            A complete suite of programmatic payment rails designed to eliminate payment failures and foreign exchange drag.
          </p>
        </div>

        <div className="nexus-features__grid">
          {FEATURES.map((item) => (
            <div key={item.title} className="nexus-feature-card">
              <div className="nexus-feature-card__icon" aria-hidden="true">{item.icon}</div>
              <h3 className="nexus-feature-card__title">{item.title}</h3>
              <p className="nexus-feature-card__desc">{item.desc}</p>
              <div className="nexus-feature-card__metric">
                <span>✓</span> {item.metric}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Features.css",
        """.nexus-features {
  padding: 6.5rem 2rem;
  background: #0a0f1d;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.nexus-features__container {
  max-width: 1240px;
  margin: 0 auto;
}
.nexus-features__header {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 4.5rem;
}
.nexus-badge {
  display: inline-block;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #06b6d4;
  margin-bottom: 0.8rem;
}
.nexus-features__title {
  font-size: clamp(2rem, 3.5vw, 3rem);
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.02em;
  margin-bottom: 1rem;
}
.nexus-features__sub {
  font-size: 1.05rem;
  line-height: 1.6;
  color: #94a3b8;
}
.nexus-features__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2rem;
}
.nexus-feature-card {
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  padding: 2.4rem;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.nexus-feature-card:hover {
  transform: translateY(-4px);
  border-color: rgba(6, 182, 212, 0.4);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 0 0 24px rgba(6, 182, 212, 0.1);
}
.nexus-feature-card__icon {
  font-size: 2rem;
  margin-bottom: 1.2rem;
}
.nexus-feature-card__title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 0.8rem;
}
.nexus-feature-card__desc {
  font-size: 0.95rem;
  line-height: 1.65;
  color: #94a3b8;
  margin-bottom: 1.4rem;
}
.nexus-feature-card__metric {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #06b6d4;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 1rem;
}
@media (max-width: 768px) {
  .nexus-features__grid {
    grid-template-columns: 1fr;
  }
}
"""
    )

    t3_obs = obs_ok(
        ["src/components/Features.tsx", "src/components/Features.css"],
        "Write the Pricing section: display the 3 tiers from the content brief (Starter $0/mo, Growth $249/mo highlighted, Enterprise Custom) in a 3-column card grid with feature checkmarks and primary/secondary CTA buttons. Files: src/components/Pricing.tsx + src/components/Pricing.css"
    )

    t4_thought = thought(
        "Features accepted. Writing the Pricing section now. The Growth plan ($249/mo) will be visually highlighted "
        "with an electric cyan border and 'MOST POPULAR' pill. Clear checklist of items per tier."
    )
    t4_action = write_site(
        "src/components/Pricing.tsx",
        """import React from 'react';
import './Pricing.css';

interface PlanTier {
  name: string;
  price: string;
  period: string;
  desc: string;
  highlight?: boolean;
  features: string[];
  cta: string;
}

const TIERS: PlanTier[] = [
  {
    name: 'Starter',
    price: '$0',
    period: '/month',
    desc: 'For early-stage startups testing global product payments.',
    features: [
      'Up to $50k monthly volume',
      '15 multi-currency local accounts',
      'Real-time API access & webhooks',
      'Standard automated AML checks',
      'Community & email support'
    ],
    cta: 'Start with Free'
  },
  {
    name: 'Growth',
    price: '$249',
    period: '/month',
    desc: 'For scaling tech companies with international suppliers & teams.',
    highlight: true,
    features: [
      'Unlimited monthly volume',
      '40+ physical & virtual debit cards',
      'Wholesale interbank FX rates',
      'Automated batch payroll wires',
      'Dedicated Slack & engineer SLA'
    ],
    cta: 'Launch Growth Plan'
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    desc: 'For global platforms needing bespoke liquidity lines and ERP sync.',
    features: [
      'Dedicated treasury relationship manager',
      'Custom ERP integration (NetSuite, SAP)',
      'Underwritten credit & liquidity lines',
      '99.999% SLA uptime guarantee',
      'Multi-entity governance hierarchy'
    ],
    cta: 'Contact Sales'
  }
];

export function Pricing() {
  return (
    <section className="nexus-pricing" id="pricing">
      <div className="nexus-pricing__container">
        <div className="nexus-pricing__header">
          <span className="nexus-badge">TRANSPARENT PRICING</span>
          <h2 className="nexus-pricing__title">Predictable plans for global scale</h2>
          <p className="nexus-pricing__sub">Zero hidden foreign exchange markups. Upgrade or downgrade anytime.</p>
        </div>

        <div className="nexus-pricing__grid">
          {TIERS.map((tier) => (
            <div 
              key={tier.name} 
              className={`nexus-price-card ${tier.highlight ? 'nexus-price-card--highlight' : ''}`}
            >
              {tier.highlight && <div className="nexus-price-card__badge">MOST POPULAR</div>}
              <h3 className="nexus-price-card__name">{tier.name}</h3>
              <p className="nexus-price-card__desc">{tier.desc}</p>
              <div className="nexus-price-card__price">
                <span className="nexus-price-card__num">{tier.price}</span>
                <span className="nexus-price-card__period">{tier.period}</span>
              </div>
              <ul className="nexus-price-card__features" aria-label={`Features for ${tier.name}`}>
                {tier.features.map((feat) => (
                  <li key={feat}>
                    <span className="nexus-check">✓</span>
                    {feat}
                  </li>
                ))}
              </ul>
              <a 
                href="#footer" 
                className={`nexus-btn ${tier.highlight ? 'nexus-btn--primary' : 'nexus-btn--outline'} w-full`}
              >
                {tier.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Pricing.css",
        """.nexus-pricing {
  padding: 6.5rem 2rem;
  background: #0d1326;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.nexus-pricing__container {
  max-width: 1240px;
  margin: 0 auto;
}
.nexus-pricing__header {
  text-align: center;
  max-width: 680px;
  margin: 0 auto 4.5rem;
}
.nexus-pricing__title {
  font-size: clamp(2rem, 3.5vw, 3rem);
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.02em;
  margin-bottom: 0.8rem;
}
.nexus-pricing__sub {
  font-size: 1.05rem;
  color: #94a3b8;
}
.nexus-pricing__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  align-items: stretch;
}
.nexus-price-card {
  position: relative;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 2.5rem;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}
.nexus-price-card--highlight {
  border-color: #06b6d4;
  background: radial-gradient(circle at 50% 0%, rgba(6, 182, 212, 0.15) 0%, rgba(15, 23, 42, 0.95) 70%);
  transform: translateY(-8px);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 30px rgba(6, 182, 212, 0.2);
}
.nexus-price-card__badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: #06b6d4;
  color: #0a0f1d;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  padding: 0.3rem 0.9rem;
  border-radius: 9999px;
}
.nexus-price-card__name {
  font-size: 1.4rem;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 0.5rem;
}
.nexus-price-card__desc {
  font-size: 0.9rem;
  color: #94a3b8;
  line-height: 1.5;
  margin-bottom: 1.8rem;
  min-height: 42px;
}
.nexus-price-card__price {
  margin-bottom: 2rem;
  display: flex;
  align-items: baseline;
  gap: 0.3rem;
}
.nexus-price-card__num {
  font-size: 2.8rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.03em;
}
.nexus-price-card__period {
  font-size: 1rem;
  color: #64748b;
  font-weight: 500;
}
.nexus-price-card__features {
  list-style: none;
  padding: 0;
  margin: 0 0 2.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  flex: 1;
}
.nexus-price-card__features li {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  font-size: 0.92rem;
  color: #cbd5e1;
  line-height: 1.4;
}
.nexus-check {
  color: #06b6d4;
  font-weight: 700;
}
.w-full {
  width: 100%;
  text-align: center;
}
@media (max-width: 960px) {
  .nexus-pricing__grid {
    grid-template-columns: 1fr;
    max-width: 500px;
    margin: 0 auto;
  }
  .nexus-price-card--highlight {
    transform: none;
  }
}
"""
    )

    t4_obs = obs_ok(
        ["src/components/Pricing.tsx", "src/components/Pricing.css"],
        "Write the Footer section: dark 4-column footer with the NexusPay brand, legal compliance disclaimers, contact details (email, phone, address), product links, and copyright notice. Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    t5_thought = thought(
        "Pricing accepted. Writing the final Footer section with full legal compliance disclaimers, "
        "contact info (San Francisco address, phone, email), column links, and copyright."
    )
    t5_action = write_site(
        "src/components/Footer.tsx",
        """import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="nexus-footer" id="footer">
      <div className="nexus-footer__container">
        <div className="nexus-footer__top">
          <div className="nexus-footer__brand">
            <a href="#" className="nexus-footer__logo">
              <span className="nexus-footer__logo-icon">❖</span>
              Nexus<span>Pay</span>
            </a>
            <p className="nexus-footer__desc">
              Next-generation treasury automation, international settlement, and business payment rails.
            </p>
            <div className="nexus-footer__contact">
              <p>📍 100 Montgomery St, Suite 2400, San Francisco, CA 94104</p>
              <p>📞 <a href="tel:+18005550192">+1 (800) 555-0192</a></p>
              <p>✉️ <a href="mailto:support@nexuspay.io">support@nexuspay.io</a></p>
            </div>
          </div>

          <div className="nexus-footer__col">
            <h4 className="nexus-footer__col-title">Platform</h4>
            <a href="#features">Global Accounts</a>
            <a href="#features">Real-Time FX</a>
            <a href="#features">Corporate Cards</a>
            <a href="#features">Liquidity Engine</a>
          </div>

          <div className="nexus-footer__col">
            <h4 className="nexus-footer__col-title">Developers</h4>
            <a href="#features">API Documentation</a>
            <a href="#features">System Status</a>
            <a href="#features">Sandbox Testing</a>
            <a href="#features">Node &amp; Python SDKs</a>
          </div>

          <div className="nexus-footer__col">
            <h4 className="nexus-footer__col-title">Compliance</h4>
            <a href="#footer">Privacy Shield</a>
            <a href="#footer">Terms of Service</a>
            <a href="#footer">SOC 2 Report</a>
            <a href="#footer">FDIC Disclosures</a>
          </div>
        </div>

        <div className="nexus-footer__disclaimer">
          NexusPay is a financial technology company, not a chartered bank. Banking services provided by Evolve Bank &amp; Trust, 
          Member FDIC. FDIC insurance only covers the failure of an insured depository institution.
        </div>

        <div className="nexus-footer__bottom">
          <p>© {year} NexusPay Technologies Inc. All rights reserved.</p>
          <div className="nexus-footer__socials">
            <a href="https://twitter.com" aria-label="Twitter" target="_blank" rel="noreferrer">𝕏</a>
            <a href="https://linkedin.com" aria-label="LinkedIn" target="_blank" rel="noreferrer">in</a>
            <a href="https://github.com" aria-label="GitHub" target="_blank" rel="noreferrer">gh</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
""",
        "src/components/Footer.css",
        """.nexus-footer {
  background: #060a14;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 5rem 2rem 2rem;
  color: #94a3b8;
}
.nexus-footer__container {
  max-width: 1240px;
  margin: 0 auto;
}
.nexus-footer__top {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 3rem;
  margin-bottom: 3.5rem;
}
.nexus-footer__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.4rem;
  font-weight: 800;
  color: #f8fafc;
  text-decoration: none;
  margin-bottom: 1rem;
}
.nexus-footer__logo-icon {
  color: #06b6d4;
}
.nexus-footer__logo span {
  color: #06b6d4;
}
.nexus-footer__desc {
  font-size: 0.92rem;
  line-height: 1.6;
  max-width: 320px;
  margin-bottom: 1.5rem;
}
.nexus-footer__contact {
  font-size: 0.85rem;
  line-height: 1.7;
}
.nexus-footer__contact a {
  color: #38bdf8;
  text-decoration: none;
}
.nexus-footer__col {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.nexus-footer__col-title {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #f8fafc;
  margin-bottom: 0.5rem;
}
.nexus-footer__col a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.2s;
}
.nexus-footer__col a:hover {
  color: #06b6d4;
}
.nexus-footer__disclaimer {
  font-size: 0.78rem;
  line-height: 1.6;
  color: #475569;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 1.8rem 0;
}
.nexus-footer__bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 1.5rem;
}
.nexus-footer__socials {
  display: flex;
  gap: 1.2rem;
  font-size: 1.1rem;
}
.nexus-footer__socials a {
  color: #64748b;
  text-decoration: none;
}
.nexus-footer__socials a:hover {
  color: #06b6d4;
}
@media (max-width: 860px) {
  .nexus-footer__top {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 520px) {
  .nexus-footer__top {
    grid-template-columns: 1fr;
  }
}
"""
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Features.tsx", "src/components/Features.css",
        "src/components/Pricing.tsx", "src/components/Pricing.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought(
        "All 5 sections of the NexusPay fintech website are complete: Header, Hero, Features, Pricing, and Footer. "
        "The site utilizes institutional dark navy (#0a0f1d) and electric cyan (#06b6d4), glassmorphism, responsive grids, "
        "and complete CSS."
    )
    t6_action = finish(
        "Built the complete NexusPay B2B fintech website with 5 sections:\n"
        "- Header: sticky glassmorphic navbar with logo, nav links, and CTA buttons\n"
        "- Hero: gradient headline, live FX badge, treasury preview card with real-time settlement feeds\n"
        "- Features: 2x2 responsive grid detailing currencies, security, APIs, and liquidity\n"
        "- Pricing: 3 tiers (Starter, Growth highlighted, Enterprise) with feature checklist\n"
        "- Footer: 4-column layout with banking compliance disclaimers, San Francisco address, and contact info\n"
        "Palette: dark navy (#0a0f1d) with electric cyan (#06b6d4) accent."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_fintech_nexus_pay", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 2. trajectory_healthcare_01 — Lumina Dental & Aesthetic Studio
# ─────────────────────────────────────────────────────────────────────────
def trajectory_healthcare_01():
    brief_xml = """<content_brief>
  <business_name>Lumina Dental</business_name>
  <tagline>Modern dentistry, aesthetic perfection, and gentle care</tagline>
  <business_type>healthcare</business_type>
  <primary_color>#0f172a</primary_color>
  <accent_color>#0d9488</accent_color>
  <font_heading>Playfair Display</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, services, testimonials, footer</sections>
  <service name="Cosmetic Veneers" description="Custom porcelain laminates hand-crafted for natural light reflection and natural smile contouring." price="From $950" />
  <service name="Invisalign Clear Aligners" description="3D digital smile mapping and discreet teeth straightening without traditional metal brackets." price="From $3,200" />
  <service name="Laser Teeth Whitening" description="In-chair light accelerated whitening achieving up to 8 shades whiter in a single 60-minute session." price="$490" />
  <service name="Gentle Family Hygiene" description="Ultra-quiet ultrasonic plaque removal, periodontal screening, and enamel remineralization therapy." price="$180" />
  <testimonial quote="The most comfortable dental experience of my life. Dr. Vance transformed my confidence with porcelain veneers." patient="Elena Rostova" procedure="Cosmetic Restoration" rating="5.0" />
  <testimonial quote="Zero anxiety, state-of-the-art 3D imaging, and warm friendly staff. Truly a five-star clinical practice." patient="David Campbell" procedure="Invisalign Aligners" rating="5.0" />
  <contact>
    <address>450 Lexington Avenue, Suite 1200, New York, NY 10017</address>
    <phone>+1 (212) 555-7832</phone>
    <email>concierge@luminadental.com</email>
    <hours>Mon-Fri: 8am - 6pm | Sat: 9am - 3pm</hours>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        f"{brief_xml}\n\n"
        "You will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: sticky white/navy navigation with the Lumina Dental branding, links (Services, Technology, Results, Reviews), phone number, and a 'Book Consultation' CTA button. Files: src/components/Header.tsx + src/components/Header.css"
    )

    t1_thought = thought(
        "I'll write the Lumina Dental Header. Premium boutique dental clinic needs an elegant, calming aesthetic: "
        "dark navy primary (#0f172a) with calming teal (#0d9488), refined serif logo (Playfair Display), "
        "phone link for emergency bookings, and a high-visibility 'Book Consultation' button."
    )
    t1_action = write_site(
        "src/components/Header.tsx",
        """import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`lumina-header ${scrolled ? 'lumina-header--scrolled' : ''}`}>
      <div className="lumina-header__container">
        <a href="#" className="lumina-header__logo" aria-label="Lumina Dental Home">
          <span className="lumina-header__logo-leaf">✦</span>
          <span>Lumina <small>Dental Studio</small></span>
        </a>

        <nav className="lumina-header__nav" aria-label="Main Navigation">
          <a href="#hero" className="lumina-header__link">Home</a>
          <a href="#services" className="lumina-header__link">Services</a>
          <a href="#testimonials" className="lumina-header__link">Patient Reviews</a>
          <a href="#footer" className="lumina-header__link">Contact</a>
        </nav>

        <div className="lumina-header__actions">
          <a href="tel:+12125557832" className="lumina-header__phone">
            <span>📞</span> (212) 555-7832
          </a>
          <a href="mailto:care@luminadental.com" className="lumina-btn lumina-btn--teal">
            Book Consultation
          </a>
        </div>
      </div>
    </header>
  );
}
""",
        "src/components/Header.css",
        """.lumina-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  transition: all 0.3s ease;
}
.lumina-header--scrolled {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.98);
}
.lumina-header__container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.lumina-header__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  font-family: 'Playfair Display', serif;
  font-size: 1.45rem;
  font-weight: 700;
  color: #0f172a;
}
.lumina-header__logo-leaf {
  color: #0d9488;
  font-size: 1.2rem;
}
.lumina-header__logo small {
  font-family: 'Inter', sans-serif;
  font-size: 0.72rem;
  font-weight: 600;
  color: #0d9488;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  display: block;
}
.lumina-header__nav {
  display: flex;
  gap: 2rem;
}
.lumina-header__link {
  color: #475569;
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 500;
  transition: color 0.2s ease;
}
.lumina-header__link:hover {
  color: #0d9488;
}
.lumina-header__actions {
  display: flex;
  align-items: center;
  gap: 1.4rem;
}
.lumina-header__phone {
  color: #0f172a;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
}
.lumina-btn {
  padding: 0.65rem 1.4rem;
  border-radius: 9999px;
  font-size: 0.88rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
}
.lumina-btn--teal {
  background: #0d9488;
  color: #ffffff;
}
.lumina-btn--teal:hover {
  background: #0f766e;
  box-shadow: 0 4px 14px rgba(13, 148, 136, 0.35);
}
@media (max-width: 860px) {
  .lumina-header__nav { display: none; }
}
"""
    )

    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: warm clinical aesthetic, prominent heading, reassurance points (Painless Laser, 3D Digital Scans, Private Suites), consultation form card, and doctor credential badges. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    t2_thought = thought(
        "Header accepted. Now writing Hero section for Lumina Dental. "
        "The hero combines calming light typography, tranquil teal badges, and a quick booking card "
        "allowing patients to request a free smile assessment directly."
    )
    t2_action = write_site(
        "src/components/Hero.tsx",
        """import React, { useState } from 'react';
import './Hero.css';

export function Hero() {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name && phone) setSubmitted(true);
  };

  return (
    <section className="lumina-hero" id="hero">
      <div className="lumina-hero__container">
        <div className="lumina-hero__content">
          <span className="lumina-hero__eyebrow">AESTHETIC &amp; RESTORATIVE EXCELLENCE</span>
          <h1 className="lumina-hero__title">
            Modern dentistry,<br />
            <em>gentle touch</em>, and radiant smiles.
          </h1>
          <p className="lumina-hero__subtitle">
            Experience state-of-the-art private suite dentistry in Midtown Manhattan. 
            From painless laser hygiene to bespoke porcelain veneers, your comfort is our priority.
          </p>

          <div className="lumina-hero__perks">
            <div className="lumina-perk">
              <span className="lumina-perk__icon">✨</span>
              <span>Painless Waterlase Technology</span>
            </div>
            <div className="lumina-perk">
              <span className="lumina-perk__icon">🔬</span>
              <span>3D Digital iTero Scanners</span>
            </div>
            <div className="lumina-perk">
              <span className="lumina-perk__icon">☕</span>
              <span>Private Patient Lounges</span>
            </div>
          </div>
        </div>

        <div className="lumina-hero__card-wrap">
          <div className="lumina-booking-card">
            <h3 className="lumina-booking-card__title">Request Smile Consultation</h3>
            <p className="lumina-booking-card__sub">Complimentary 30-min digital smile simulation.</p>

            {submitted ? (
              <div className="lumina-booking-card__success">
                <span className="lumina-success-icon">✓</span>
                <h4>Thank you, {name}!</h4>
                <p>Our concierge team will call you within 2 hours to confirm your preferred suite time.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="lumina-booking-form">
                <label className="lumina-label">
                  Your Full Name
                  <input 
                    type="text" 
                    required 
                    placeholder="e.g. Jessica Miller" 
                    value={name} 
                    onChange={(e) => setName(e.target.value)} 
                    className="lumina-input"
                  />
                </label>
                <label className="lumina-label">
                  Phone Number
                  <input 
                    type="tel" 
                    required 
                    placeholder="(212) 000-0000" 
                    value={phone} 
                    onChange={(e) => setPhone(e.target.value)} 
                    className="lumina-input"
                  />
                </label>
                <label className="lumina-label">
                  Primary Interest
                  <select className="lumina-select" defaultValue="veneers">
                    <option value="veneers">Cosmetic Porcelain Veneers</option>
                    <option value="invisalign">Invisalign Clear Aligners</option>
                    <option value="whitening">Laser Teeth Whitening</option>
                    <option value="hygiene">Comprehensive Checkup &amp; Clean</option>
                  </select>
                </label>
                <button type="submit" className="lumina-btn lumina-btn--teal lumina-btn--block">
                  Confirm Free Assessment
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Hero.css",
        """.lumina-hero {
  padding: 6rem 2rem;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 60%, #e6f4f1 100%);
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
}
.lumina-hero__container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 4rem;
  align-items: center;
}
.lumina-hero__eyebrow {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #0d9488;
  margin-bottom: 1rem;
}
.lumina-hero__title {
  font-family: 'Playfair Display', serif;
  font-size: clamp(2.4rem, 4.5vw, 3.8rem);
  color: #0f172a;
  line-height: 1.15;
  margin-bottom: 1.4rem;
  font-weight: 700;
}
.lumina-hero__title em {
  font-style: italic;
  color: #0d9488;
}
.lumina-hero__subtitle {
  font-size: 1.1rem;
  line-height: 1.7;
  color: #475569;
  max-width: 560px;
  margin-bottom: 2.2rem;
}
.lumina-hero__perks {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.lumina-perk {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
}
.lumina-perk__icon {
  font-size: 1.2rem;
}
.lumina-booking-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 2.4rem;
  box-shadow: 0 15px 45px rgba(15, 23, 42, 0.08);
  border: 1px solid rgba(13, 148, 136, 0.15);
}
.lumina-booking-card__title {
  font-family: 'Playfair Display', serif;
  font-size: 1.4rem;
  color: #0f172a;
  margin-bottom: 0.4rem;
}
.lumina-booking-card__sub {
  font-size: 0.88rem;
  color: #64748b;
  margin-bottom: 1.6rem;
}
.lumina-booking-form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}
.lumina-label {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #334155;
}
.lumina-input, .lumina-select {
  padding: 0.75rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  font-size: 0.92rem;
  color: #0f172a;
  outline: none;
  transition: border-color 0.2s;
}
.lumina-input:focus, .lumina-select:focus {
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.15);
}
.lumina-btn--block {
  width: 100%;
  margin-top: 0.5rem;
  padding: 0.85rem;
  font-size: 0.95rem;
  border: none;
  cursor: pointer;
}
.lumina-booking-card__success {
  text-align: center;
  padding: 2rem 0;
}
.lumina-success-icon {
  display: inline-flex;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #0d9488;
  color: white;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin-bottom: 1rem;
}
@media (max-width: 900px) {
  .lumina-hero__container {
    grid-template-columns: 1fr;
  }
}
"""
    )

    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Services section: display the 4 clinical services from the brief (Cosmetic Veneers, Invisalign, Laser Whitening, Family Hygiene) with pricing badges, detailed descriptions, and high-contrast card styling. Files: src/components/Services.tsx + src/components/Services.css"
    )

    t3_thought = thought(
        "Hero accepted. Writing the Services section. 4 cards presenting each dental service with pricing, "
        "subtle hover effect, and bullet points."
    )
    t3_action = write_site(
        "src/components/Services.tsx",
        """import React from 'react';
import './Services.css';

interface DentalService {
  name: string;
  desc: string;
  price: string;
  tag: string;
}

const SERVICES: DentalService[] = [
  {
    name: 'Cosmetic Veneers',
    desc: 'Custom porcelain laminates hand-crafted for natural light reflection, flawless contouring, and durable smile enhancement.',
    price: 'From $950 / tooth',
    tag: 'Smile Makeover'
  },
  {
    name: 'Invisalign Clear Aligners',
    desc: '3D digital smile mapping and discreet teeth straightening without metal brackets or dietary restrictions.',
    price: 'From $3,200',
    tag: 'Orthodontics'
  },
  {
    name: 'Laser Teeth Whitening',
    desc: 'In-chair light accelerated whitening achieving up to 8 shades whiter in a single comfortable 60-minute session.',
    price: '$490 complete',
    tag: 'Express Radiance'
  },
  {
    name: 'Gentle Family Hygiene',
    desc: 'Ultra-quiet ultrasonic plaque removal, periodontal screening, oral cancer scan, and enamel remineralization therapy.',
    price: '$180 per visit',
    tag: 'Preventative'
  }
];

export function Services() {
  return (
    <section className="lumina-services" id="services">
      <div className="lumina-services__container">
        <div className="lumina-services__header">
          <span className="lumina-services__tag">OUR CLINICAL EXPERTISE</span>
          <h2 className="lumina-services__title">Personalized aesthetic &amp; restorative care</h2>
          <p className="lumina-services__sub">Every procedure is conducted in tranquil private suites equipped with ceiling entertainment.</p>
        </div>

        <div className="lumina-services__grid">
          {SERVICES.map((srv) => (
            <div key={srv.name} className="lumina-service-card">
              <span className="lumina-service-card__tag">{srv.tag}</span>
              <h3 className="lumina-service-card__title">{srv.name}</h3>
              <p className="lumina-service-card__desc">{srv.desc}</p>
              <div className="lumina-service-card__footer">
                <span className="lumina-service-card__price">{srv.price}</span>
                <a href="#footer" className="lumina-service-card__link">Book Procedure →</a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Services.css",
        """.lumina-services {
  padding: 6.5rem 2rem;
  background: #ffffff;
}
.lumina-services__container {
  max-width: 1200px;
  margin: 0 auto;
}
.lumina-services__header {
  text-align: center;
  max-width: 700px;
  margin: 0 auto 4rem;
}
.lumina-services__tag {
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #0d9488;
  display: inline-block;
  margin-bottom: 0.8rem;
}
.lumina-services__title {
  font-family: 'Playfair Display', serif;
  font-size: clamp(2rem, 3.5vw, 2.8rem);
  color: #0f172a;
  margin-bottom: 0.8rem;
}
.lumina-services__sub {
  color: #64748b;
  font-size: 1.05rem;
}
.lumina-services__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2rem;
}
.lumina-service-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 2.4rem;
  display: flex;
  flex-direction: column;
  transition: all 0.25s ease;
}
.lumina-service-card:hover {
  border-color: #0d9488;
  transform: translateY(-3px);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}
.lumina-service-card__tag {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #0d9488;
  margin-bottom: 0.8rem;
}
.lumina-service-card__title {
  font-family: 'Playfair Display', serif;
  font-size: 1.45rem;
  color: #0f172a;
  margin-bottom: 0.8rem;
}
.lumina-service-card__desc {
  font-size: 0.95rem;
  line-height: 1.6;
  color: #475569;
  margin-bottom: 1.8rem;
  flex: 1;
}
.lumina-service-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #e2e8f0;
  padding-top: 1.2rem;
}
.lumina-service-card__price {
  font-weight: 700;
  color: #0f172a;
  font-size: 1rem;
}
.lumina-service-card__link {
  color: #0d9488;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
}
.lumina-service-card__link:hover {
  text-decoration: underline;
}
@media (max-width: 768px) {
  .lumina-services__grid {
    grid-template-columns: 1fr;
  }
}
"""
    )

    t3_obs = obs_ok(
        ["src/components/Services.tsx", "src/components/Services.css"],
        "Write the Testimonials section: display the patient reviews from the brief with star ratings, quotes, patient names, and procedure labels. Files: src/components/Testimonials.tsx + src/components/Testimonials.css"
    )

    t4_thought = thought(
        "Services accepted. Writing Testimonials section. Patient reviews build confidence for clinical decisions. "
        "Two prominent cards showcasing Elena Rostova and David Campbell with 5-star ratings."
    )
    t4_action = write_site(
        "src/components/Testimonials.tsx",
        """import React from 'react';
import './Testimonials.css';

interface PatientReview {
  quote: string;
  patient: string;
  procedure: string;
  rating: string;
}

const REVIEWS: PatientReview[] = [
  {
    quote: 'The most comfortable dental experience of my life. Dr. Vance transformed my confidence with porcelain veneers. Zero pain and the results look completely natural.',
    patient: 'Elena Rostova',
    procedure: 'Cosmetic Restoration',
    rating: '★★★★★'
  },
  {
    quote: 'Zero anxiety, state-of-the-art 3D imaging, and warm friendly staff. I finished my Invisalign in 7 months without anyone noticing I had aligners in.',
    patient: 'David Campbell',
    procedure: 'Invisalign Aligners',
    rating: '★★★★★'
  }
];

export function Testimonials() {
  return (
    <section className="lumina-reviews" id="testimonials">
      <div className="lumina-reviews__container">
        <div className="lumina-reviews__header">
          <span className="lumina-reviews__badge">REAL SMILE TRANSFORMATIONS</span>
          <h2 className="lumina-reviews__title">Hear from our patients</h2>
        </div>

        <div className="lumina-reviews__grid">
          {REVIEWS.map((rev) => (
            <div key={rev.patient} className="lumina-review-card">
              <div className="lumina-review-card__stars" aria-label="5 stars">{rev.rating}</div>
              <blockquote className="lumina-review-card__quote">
                &ldquo;{rev.quote}&rdquo;
              </blockquote>
              <div className="lumina-review-card__author">
                <span className="lumina-review-card__name">{rev.patient}</span>
                <span className="lumina-review-card__proc">{rev.procedure}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Testimonials.css",
        """.lumina-reviews {
  padding: 6.5rem 2rem;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}
.lumina-reviews__container {
  max-width: 1100px;
  margin: 0 auto;
}
.lumina-reviews__header {
  text-align: center;
  margin-bottom: 3.5rem;
}
.lumina-reviews__badge {
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #0d9488;
  display: inline-block;
  margin-bottom: 0.8rem;
}
.lumina-reviews__title {
  font-family: 'Playfair Display', serif;
  font-size: clamp(2rem, 3.5vw, 2.8rem);
  color: #0f172a;
}
.lumina-reviews__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2.5rem;
}
.lumina-review-card {
  background: #ffffff;
  border-radius: 18px;
  padding: 2.5rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}
.lumina-review-card__stars {
  color: #f59e0b;
  font-size: 1.2rem;
  letter-spacing: 2px;
  margin-bottom: 1.2rem;
}
.lumina-review-card__quote {
  font-family: 'Playfair Display', serif;
  font-size: 1.15rem;
  line-height: 1.7;
  color: #334155;
  margin: 0 0 1.8rem;
  font-style: italic;
}
.lumina-review-card__name {
  display: block;
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  color: #0f172a;
  font-size: 0.95rem;
}
.lumina-review-card__proc {
  font-size: 0.82rem;
  color: #0d9488;
  font-weight: 600;
}
@media (max-width: 768px) {
  .lumina-reviews__grid {
    grid-template-columns: 1fr;
  }
}
"""
    )

    t4_obs = obs_ok(
        ["src/components/Testimonials.tsx", "src/components/Testimonials.css"],
        "Write the Footer section: dark navy background (#0f172a) with Lumina Dental brand, clinical hours, address (Lexington Ave NY), emergency phone, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    t5_thought = thought(
        "Testimonials accepted. Writing Footer section to conclude the Lumina Dental site. "
        "Features Lexington Ave address, operating hours, emergency phone number, and patient concierge email."
    )
    t5_action = write_site(
        "src/components/Footer.tsx",
        """import React from 'react';
import './Footer.css';

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="lumina-footer" id="footer">
      <div className="lumina-footer__container">
        <div className="lumina-footer__grid">
          <div className="lumina-footer__brand">
            <h3 className="lumina-footer__logo">Lumina <span>Dental Studio</span></h3>
            <p className="lumina-footer__tagline">
              Elevating oral health into an art form. Providing cosmetic, restorative, and surgical excellence in New York City.
            </p>
          </div>

          <div className="lumina-footer__col">
            <h4>Hours</h4>
            <p>Monday – Friday: 8:00am – 6:00pm</p>
            <p>Saturday: 9:00am – 3:00pm</p>
            <p>Sunday: Closed (Emergency on-call)</p>
          </div>

          <div className="lumina-footer__col">
            <h4>Location</h4>
            <address>
              450 Lexington Avenue, Suite 1200<br />
              Grand Central Area<br />
              New York, NY 10017
            </address>
          </div>

          <div className="lumina-footer__col">
            <h4>Contact</h4>
            <p>📞 <a href="tel:+12125557832">(212) 555-7832</a></p>
            <p>✉️ <a href="mailto:concierge@luminadental.com">concierge@luminadental.com</a></p>
          </div>
        </div>

        <div className="lumina-footer__bottom">
          <p>© {year} Lumina Dental Studio LLC. All rights reserved.</p>
          <p>ADA &amp; AACD Accredited Cosmetic Specialists.</p>
        </div>
      </div>
    </footer>
  );
}
""",
        "src/components/Footer.css",
        """.lumina-footer {
  background: #0f172a;
  color: #94a3b8;
  padding: 5rem 2rem 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.lumina-footer__container {
  max-width: 1200px;
  margin: 0 auto;
}
.lumina-footer__grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: 3rem;
  margin-bottom: 3.5rem;
}
.lumina-footer__logo {
  font-family: 'Playfair Display', serif;
  font-size: 1.4rem;
  color: #ffffff;
  margin-bottom: 0.8rem;
}
.lumina-footer__logo span {
  font-family: 'Inter', sans-serif;
  font-size: 0.75rem;
  color: #0d9488;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  display: block;
}
.lumina-footer__tagline {
  font-size: 0.9rem;
  line-height: 1.6;
  max-width: 280px;
}
.lumina-footer__col h4 {
  color: #ffffff;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.9rem;
}
.lumina-footer__col p, .lumina-footer__col address {
  font-size: 0.88rem;
  line-height: 1.7;
  font-style: normal;
}
.lumina-footer__col a {
  color: #2dd4bf;
  text-decoration: none;
}
.lumina-footer__bottom {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 1.8rem;
  font-size: 0.82rem;
  color: #64748b;
}
@media (max-width: 860px) {
  .lumina-footer__grid {
    grid-template-columns: 1fr 1fr;
  }
}
"""
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Services.tsx", "src/components/Services.css",
        "src/components/Testimonials.tsx", "src/components/Testimonials.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought(
        "Lumina Dental site is complete: Header, Hero with appointment card, Services, Testimonials, and Footer. "
        "The site applies calming teal (#0d9488) accents, Playfair Display typography, and fully responsive CSS."
    )
    t6_action = finish(
        "Built the complete Lumina Dental & Aesthetic Studio healthcare website with 5 sections:\n"
        "- Header: elegant navbar with phone hotline and consultation booking CTA\n"
        "- Hero: calming banner with reassurance perks and interactive appointment booking form\n"
        "- Services: 4 clinical services with transparent pricing (Veneers, Invisalign, Whitening, Hygiene)\n"
        "- Testimonials: patient reviews with star ratings\n"
        "- Footer: operating hours, Midtown NYC address, and clinical accreditation notice\n"
        "Palette: calm navy (#0f172a) with medical teal (#0d9488) and Playfair Display serif headings."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_healthcare_lumina_dental", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 3. trajectory_ai_platform_01 — OmniMind AI
# ─────────────────────────────────────────────────────────────────────────
def trajectory_ai_platform_01():
    brief_xml = """<content_brief>
  <business_name>OmniMind AI</business_name>
  <tagline>Autonomous neural workflows and multi-agent coordination</tagline>
  <business_type>ai_platform</business_type>
  <primary_color>#030712</primary_color>
  <accent_color>#8b5cf6</accent_color>
  <font_heading>Inter</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, capabilities, code_preview, footer</sections>
  <capability title="Self-Refining Loops" description="Agents test their own outputs against runtime sandboxes and automatically re-prompt on compilation errors." />
  <capability title="Heterogeneous Swarms" description="Deploy specialized small models for drafting and frontier LLMs for reflection and architectural judgment." />
  <capability title="Persistent Vector Memory" description="Sub-millisecond retrieval across petabyte-scale knowledge graphs with transactional state rollback." />
  <capability title="Telemetry &amp; Guardrails" description="Full token-level observability, hallucination detection, and semantic firewalls out of the box." />
  <contact>
    <email>founders@omnimind.ai</email>
    <github>github.com/omnimind-ai</github>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        f"{brief_xml}\n\n"
        "You will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: dark futuristic navbar with glowing violet logo, links (Agents, Benchmarks, Docs, Pricing), GitHub stars badge, and 'Deploy Agent' button. Files: src/components/Header.tsx + src/components/Header.css"
    )

    t1_thought = thought(
        "I'll start with the OmniMind AI Header. Futuristic developer/AI platform needs an obsidian black canvas (#030712) "
        "with electric violet (#8b5cf6) accents, monospace badge accents, and GitHub star integration."
    )
    t1_action = write_site(
        "src/components/Header.tsx",
        """import React, { useState } from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="omni-header">
      <div className="omni-header__container">
        <a href="#" className="omni-header__logo" aria-label="OmniMind Home">
          <span className="omni-header__logo-node">⬡</span>
          <span>Omni<span>Mind</span></span>
          <span className="omni-header__version">v2.4</span>
        </a>

        <nav className="omni-header__nav" aria-label="Main Navigation">
          <a href="#hero">Overview</a>
          <a href="#capabilities">Architecture</a>
          <a href="#code">SDK &amp; Sandbox</a>
        </nav>

        <div className="omni-header__actions">
          <a href="https://github.com/omnimind-ai" className="omni-header__gh" target="_blank" rel="noreferrer">
            <span>★ 14.8k</span>
          </a>
          <a href="#code" className="omni-btn omni-btn--violet">
            Explore SDK →
          </a>
        </div>
      </div>
    </header>
  );
}
""",
        "src/components/Header.css",
        """.omni-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: rgba(3, 7, 18, 0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(139, 92, 246, 0.15);
}
.omni-header__container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.omni-header__logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  font-size: 1.3rem;
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.02em;
}
.omni-header__logo-node {
  color: #8b5cf6;
  font-size: 1.5rem;
  text-shadow: 0 0 14px rgba(139, 92, 246, 0.8);
}
.omni-header__logo span span {
  color: #8b5cf6;
}
.omni-header__version {
  font-family: monospace;
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  border-radius: 4px;
  border: 1px solid rgba(139, 92, 246, 0.3);
}
.omni-header__nav {
  display: flex;
  gap: 2rem;
}
.omni-header__nav a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s;
}
.omni-header__nav a:hover {
  color: #c4b5fd;
}
.omni-header__actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.omni-header__gh {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  color: #cbd5e1;
  font-family: monospace;
  font-size: 0.82rem;
  text-decoration: none;
}
.omni-btn {
  padding: 0.6rem 1.3rem;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
}
.omni-btn--violet {
  background: #8b5cf6;
  color: #ffffff;
  box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
}
.omni-btn--violet:hover {
  background: #7c3aed;
  box-shadow: 0 0 28px rgba(139, 92, 246, 0.65);
}
@media (max-width: 800px) {
  .omni-header__nav { display: none; }
}
"""
    )

    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: dark high-contrast hero with neural mesh background glow, large typography, dual CTAs (SDK Quickstart, Read Technical Paper), and an interactive terminal showing real-time agent multi-turn reflection. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    t2_thought = thought(
        "Header accepted. Building Hero section for OmniMind AI with live agentic loop terminal visual, "
        "highlighting autonomous problem-solving and self-healing code synthesis."
    )
    t2_action = write_site(
        "src/components/Hero.tsx",
        """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="omni-hero" id="hero">
      <div className="omni-hero__glow" aria-hidden="true" />
      <div className="omni-hero__container">
        <div className="omni-hero__badge">
          <span>NEURAL ORCHESTRATION ENGINE</span>
        </div>
        <h1 className="omni-hero__title">
          Autonomous multi-agent swarms with <span className="omni-hero__violet">self-refining code loops</span>
        </h1>
        <p className="omni-hero__sub">
          Coordinate specialized small models with frontier reasoning kernels. Build, test, and correct 
          complex full-stack code in automated micro-sandboxes with zero human intervention.
        </p>

        <div className="omni-hero__actions">
          <a href="#code" className="omni-btn omni-btn--violet omni-btn--lg">
            Install SDK (`npm i omnimind`)
          </a>
          <a href="#capabilities" className="omni-btn omni-btn--dark omni-btn--lg">
            Read Architecture ↗
          </a>
        </div>

        <div className="omni-terminal" aria-label="Terminal demonstration of OmniMind agentic execution">
          <div className="omni-terminal__bar">
            <span className="dot dot--red" /><span className="dot dot--yellow" /><span className="dot dot--green" />
            <span className="omni-terminal__title">omnimind-runner · swarm-cluster-04 · Vitest Loop</span>
          </div>
          <div className="omni-terminal__body">
            <div className="term-line term-line--dim">[00:00.04] Initializing runtime sandbox: Node v22.4, TypeScript 5.6</div>
            <div className="term-line">[AGENT: Coder-3B] Generated component: `src/components/DataGrid.tsx`</div>
            <div className="term-line term-line--amber">⚡ [TEST RUNNER] Executing Vitest harness...</div>
            <div className="term-line term-line--red">✗ FAIL: Expected sort indicator to be aria-sort="ascending", found "none"</div>
            <div className="term-line term-line--violet">↺ [SELF-CORRECTION LOOP] Feeding stderr back to agent context...</div>
            <div className="term-line term-line--cyan">[AGENT: Coder-3B] Patch applied: aria-sort update on sortKey change</div>
            <div className="term-line term-line--green">✓ PASS: All 12 unit tests and accessibility checks verified. Trajectory saved.</div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Hero.css",
        """.omni-hero {
  position: relative;
  padding: 6.5rem 2rem 5rem;
  background: #030712;
  overflow: hidden;
  text-align: center;
}
.omni-hero__glow {
  position: absolute;
  top: -150px;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 600px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.22) 0%, transparent 65%);
  pointer-events: none;
}
.omni-hero__container {
  max-width: 1040px;
  margin: 0 auto;
}
.omni-hero__badge {
  display: inline-block;
  padding: 0.35rem 0.9rem;
  background: rgba(139, 92, 246, 0.12);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 9999px;
  color: #c4b5fd;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  margin-bottom: 1.5rem;
}
.omni-hero__title {
  font-size: clamp(2.4rem, 5vw, 4rem);
  font-weight: 800;
  color: #f8fafc;
  line-height: 1.15;
  letter-spacing: -0.03em;
  margin-bottom: 1.4rem;
}
.omni-hero__violet {
  background: linear-gradient(135deg, #a78bfa 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.omni-hero__sub {
  font-size: 1.15rem;
  color: #94a3b8;
  line-height: 1.7;
  max-width: 720px;
  margin: 0 auto 2.5rem;
}
.omni-hero__actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 4rem;
  flex-wrap: wrap;
}
.omni-btn--lg {
  padding: 0.85rem 1.8rem;
  font-size: 0.96rem;
}
.omni-btn--dark {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #cbd5e1;
}
.omni-btn--dark:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}
.omni-terminal {
  background: #090d16;
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 30px rgba(139, 92, 246, 0.15);
  text-align: left;
}
.omni-terminal__bar {
  background: #0d1322;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot--red { background: #ef4444; }
.dot--yellow { background: #f59e0b; }
.dot--green { background: #10b981; }
.omni-terminal__title {
  font-family: monospace;
  font-size: 0.78rem;
  color: #64748b;
  margin-left: 0.5rem;
}
.omni-terminal__body {
  padding: 1.4rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.88rem;
  line-height: 1.7;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.term-line--dim { color: #475569; }
.term-line--amber { color: #f59e0b; }
.term-line--red { color: #f87171; }
.term-line--violet { color: #c084fc; }
.term-line--cyan { color: #38bdf8; }
.term-line--green { color: #4ade80; font-weight: 600; }
"""
    )

    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Capabilities section: display the 4 architecture capabilities from the brief (Self-Refining Loops, Heterogeneous Swarms, Persistent Vector Memory, Telemetry & Guardrails) in a responsive grid. Files: src/components/Capabilities.tsx + src/components/Capabilities.css"
    )

    t3_thought = thought(
        "Hero accepted. Writing Capabilities section now. 4 technical pillars presented with dark glassmorphism "
        "and clean metrics."
    )
    t3_action = write_site(
        "src/components/Capabilities.tsx",
        """import React from 'react';
import './Capabilities.css';

interface Pillar {
  tag: string;
  title: string;
  desc: string;
}

const PILLARS: Pillar[] = [
  {
    tag: 'AUTONOMOUS FEEDBACK',
    title: 'Self-Refining Runtime Loops',
    desc: 'Agents execute generated code directly against in-memory Vitest and TSC runners, automatically diagnosing stack traces and self-correcting syntax or test failures.'
  },
  {
    tag: 'MODEL ROUTING',
    title: 'Heterogeneous Model Swarms',
    desc: 'Deploy fast, local 3B code models for rapid drafting and escalate complex architectural reviews to frontier reasoning models only when needed.'
  },
  {
    tag: 'CONTEXT RETRIEVAL',
    title: 'Persistent Vector Memory',
    desc: 'Sub-millisecond retrieval across codebase ASTs and multi-turn conversation logs with transactional rollback for corrupted state.'
  },
  {
    tag: 'PRODUCTION HARDENED',
    title: 'Telemetry & Guardrails',
    desc: 'Complete token-level observability, hallucination mitigation filters, and prompt injection defense layers ready for enterprise scale.'
  }
];

export function Capabilities() {
  return (
    <section className="omni-caps" id="capabilities">
      <div className="omni-caps__container">
        <div className="omni-caps__header">
          <span className="omni-badge">CORE CAPABILITIES</span>
          <h2 className="omni-caps__title">Engineered for agentic autonomy</h2>
        </div>

        <div className="omni-caps__grid">
          {PILLARS.map((p) => (
            <div key={p.title} className="omni-cap-card">
              <span className="omni-cap-card__tag">{p.tag}</span>
              <h3 className="omni-cap-card__title">{p.title}</h3>
              <p className="omni-cap-card__desc">{p.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Capabilities.css",
        """.omni-caps {
  padding: 6rem 2rem;
  background: #050914;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.omni-caps__container {
  max-width: 1200px;
  margin: 0 auto;
}
.omni-caps__header {
  text-align: center;
  margin-bottom: 4rem;
}
.omni-badge {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #8b5cf6;
  margin-bottom: 0.6rem;
  display: inline-block;
}
.omni-caps__title {
  font-size: clamp(2rem, 3.5vw, 2.8rem);
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.02em;
}
.omni-caps__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2rem;
}
.omni-cap-card {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(139, 92, 246, 0.18);
  border-radius: 16px;
  padding: 2.2rem;
  transition: all 0.25s ease;
}
.omni-cap-card:hover {
  border-color: rgba(139, 92, 246, 0.45);
  transform: translateY(-3px);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
}
.omni-cap-card__tag {
  font-family: monospace;
  font-size: 0.75rem;
  color: #8b5cf6;
  font-weight: 700;
  margin-bottom: 0.8rem;
  display: block;
}
.omni-cap-card__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 0.8rem;
}
.omni-cap-card__desc {
  font-size: 0.95rem;
  line-height: 1.65;
  color: #94a3b8;
}
@media (max-width: 768px) {
  .omni-caps__grid {
    grid-template-columns: 1fr;
  }
}
"""
    )

    t3_obs = obs_ok(
        ["src/components/Capabilities.tsx", "src/components/Capabilities.css"],
        "Write the Code Preview section: an interactive TypeScript code snippet demonstrating how to define an autonomous self-correcting agent swarm with `omnimind/swarm` SDK. Files: src/components/CodePreview.tsx + src/components/CodePreview.css"
    )

    t4_thought = thought(
        "Capabilities accepted. Writing CodePreview section with clean syntax styling and copy-to-clipboard button."
    )
    t4_action = write_site(
        "src/components/CodePreview.tsx",
        """import React, { useState } from 'react';
import './CodePreview.css';

const SAMPLE_CODE = `import { Swarm, AgentRunner } from '@omnimind/core';

// Initialize self-correcting agent loop
const swarm = new Swarm({
  planner: 'claude-3-5-sonnet',
  coder: 'qwen-2.5-coder-3b',
  sandbox: { runtime: 'vitest-in-memory', timeoutMs: 5000 }
});

const result = await swarm.executeTask({
  task: 'Build responsive pricing table with toggle',
  maxIterations: 3
});

console.log(result.verifiedSolution);`;

export function CodePreview() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(SAMPLE_CODE);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="omni-code" id="code">
      <div className="omni-code__container">
        <div className="omni-code__card">
          <div className="omni-code__top">
            <span className="omni-code__file">agent_runner.ts</span>
            <button onClick={handleCopy} className="omni-code__copy">
              {copied ? '✓ Copied' : 'Copy Snippet'}
            </button>
          </div>
          <pre className="omni-code__block">
            <code>{SAMPLE_CODE}</code>
          </pre>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/CodePreview.css",
        """.omni-code {
  padding: 4rem 2rem 6rem;
  background: #030712;
}
.omni-code__container {
  max-width: 900px;
  margin: 0 auto;
}
.omni-code__card {
  background: #0b101f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden;
}
.omni-code__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1.4rem;
  background: #070a14;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.omni-code__file {
  font-family: monospace;
  font-size: 0.85rem;
  color: #94a3b8;
}
.omni-code__copy {
  background: rgba(139, 92, 246, 0.15);
  border: 1px solid rgba(139, 92, 246, 0.3);
  color: #c4b5fd;
  border-radius: 6px;
  padding: 0.3rem 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
}
.omni-code__block {
  margin: 0;
  padding: 1.8rem;
  color: #e2e8f0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.92rem;
  line-height: 1.6;
  overflow-x: auto;
}
"""
    )

    t4_obs = obs_ok(
        ["src/components/CodePreview.tsx", "src/components/CodePreview.css"],
        "Write the Footer section: dark minimal footer with GitHub link, contact email, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    t5_thought = thought(
        "Code preview accepted. Writing Footer section to complete OmniMind AI."
    )
    t5_action = write_site(
        "src/components/Footer.tsx",
        """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="omni-footer">
      <div className="omni-footer__container">
        <div className="omni-footer__brand">
          <span className="omni-footer__logo">⬡ OmniMind AI</span>
          <p>The open architecture for autonomous multi-turn coding swarms.</p>
        </div>
        <div className="omni-footer__links">
          <a href="https://github.com/omnimind-ai">GitHub</a>
          <a href="mailto:founders@omnimind.ai">founders@omnimind.ai</a>
          <a href="https://discord.gg/omnimind" target="_blank" rel="noreferrer">Discord Community</a>
        </div>
        <div className="omni-footer__bottom">
          <p>© {new Date().getFullYear()} OmniMind AI Inc. Open-core Apache 2.0.</p>
        </div>
      </div>
    </footer>
  );
}
""",
        "src/components/Footer.css",
        """.omni-footer {
  background: #02040a;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 4rem 2rem 2rem;
  color: #64748b;
  font-size: 0.88rem;
}
.omni-footer__container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
.omni-footer__brand {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.omni-footer__logo {
  font-size: 1.15rem;
  font-weight: 700;
  color: #f8fafc;
}
.omni-footer__links {
  display: flex;
  gap: 1.5rem;
}
.omni-footer__links a {
  color: #94a3b8;
  text-decoration: none;
}
.omni-footer__links a:hover {
  color: #8b5cf6;
}
.omni-footer__bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 1.5rem;
}
"""
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Capabilities.tsx", "src/components/Capabilities.css",
        "src/components/CodePreview.tsx", "src/components/CodePreview.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought("OmniMind AI platform site is complete across all 5 sections.")
    t6_action = finish(
        "Built the complete OmniMind AI platform website with 5 sections:\n"
        "- Header: futuristic glass navbar with GitHub star badge and deployment button\n"
        "- Hero: neural glow mesh with interactive terminal displaying runtime agentic reflection\n"
        "- Capabilities: 4 core pillars for self-refining loops and multi-model swarms\n"
        "- CodePreview: copyable TypeScript snippet for `@omnimind/core` SDK\n"
        "- Footer: minimal open-core credits and community links\n"
        "Palette: obsidian black (#030712) with electric violet (#8b5cf6) accent."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_ai_agent_omnimind", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 4. trajectory_architecture_01 — Atelier Nord (Nordic architecture)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_architecture_01():
    brief_xml = """<content_brief>
  <business_name>Atelier Nord</business_name>
  <tagline>Quiet architecture, natural light, and enduring materiality</tagline>
  <business_type>architecture</business_type>
  <primary_color>#18181b</primary_color>
  <accent_color>#d97706</accent_color>
  <font_heading>Cormorant Garamond</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, projects, philosophy, footer</sections>
  <project name="Villa Fjord" location="Bergen, Norway" area="420 m²" year="2024" description="Cantilevered timber and black granite residence framing unbroken Arctic water views." />
  <project name="The Glass Pavilion" location="Stockholm, Sweden" area="280 m²" year="2023" description="Double-glazed minimalist woodland studio with integrated geothermal slab heating." />
  <project name="Klar Studio House" location="Copenhagen, Denmark" area="350 m²" year="2024" description="Adaptive reuse of a 19th-century brick warehouse into hybrid residential galleries." />
  <contact>
    <studio>Dronningens Gate 14, 0152 Oslo, Norway</studio>
    <email>inquiries@ateliernord.no</email>
    <phone>+47 22 33 44 55</phone>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        f"{brief_xml}\n\n"
        "You will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: minimalist dark header with serif branding, links (Selected Works, Philosophy, Publications, Contact), and an 'Inquire' button. Files: src/components/Header.tsx + src/components/Header.css"
    )

    t1_thought = thought(
        "I'll write the Header for Atelier Nord. Minimalist Scandinavian architecture requires spacious, understated luxury: "
        "dark zinc charcoal (#18181b) with warm ochre (#d97706), wide letter-spacing, and Cormorant Garamond typography."
    )
    t1_action = write_site(
        "src/components/Header.tsx",
        """import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <header className={`nord-header ${scrolled ? 'nord-header--scrolled' : ''}`}>
      <div className="nord-header__container">
        <a href="#" className="nord-header__logo">
          Atelier <span>Nord</span>
        </a>

        <nav className="nord-header__nav" aria-label="Main Navigation">
          <a href="#hero">Studio</a>
          <a href="#projects">Selected Works</a>
          <a href="#philosophy">Philosophy</a>
        </nav>

        <a href="#contact" className="nord-header__cta">
          Inquire
        </a>
      </div>
    </header>
  );
}
""",
        "src/components/Header.css",
        """.nord-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: rgba(24, 24, 27, 0.9);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s ease;
}
.nord-header--scrolled {
  background: rgba(24, 24, 27, 0.98);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}
.nord-header__container {
  max-width: 1300px;
  margin: 0 auto;
  padding: 0 2.5rem;
  height: 84px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.nord-header__logo {
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.6rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #f4f4f5;
  text-decoration: none;
  text-transform: uppercase;
}
.nord-header__logo span {
  font-weight: 300;
  color: #d97706;
}
.nord-header__nav {
  display: flex;
  gap: 2.8rem;
}
.nord-header__nav a {
  color: #a1a1aa;
  text-decoration: none;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  transition: color 0.2s;
}
.nord-header__nav a:hover {
  color: #d97706;
}
.nord-header__cta {
  padding: 0.55rem 1.4rem;
  border: 1px solid rgba(217, 119, 6, 0.4);
  color: #f4f4f5;
  text-decoration: none;
  font-size: 0.82rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: all 0.2s;
}
.nord-header__cta:hover {
  background: #d97706;
  color: #18181b;
}
@media (max-width: 800px) {
  .nord-header__nav { display: none; }
}
"""
    )

    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: cinematic editorial layout with large serif heading, understated metadata, architectural quotation, and smooth scroll indicator. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    t2_thought = thought(
        "Header accepted. Now writing Hero section for Atelier Nord with editorial serif headline, "
        "subdued architectural description, and Oslo/Copenhagen studio coordinates."
    )
    t2_action = write_site(
        "src/components/Hero.tsx",
        """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="nord-hero" id="hero">
      <div className="nord-hero__container">
        <div className="nord-hero__eyebrow">
          <span>OSLO</span> · <span>COPENHAGEN</span> · <span>STOCKHOLM</span>
        </div>
        <h1 className="nord-hero__title">
          Quiet architecture, natural light,<br />
          and <em>enduring materiality</em>.
        </h1>
        <p className="nord-hero__sub">
          We practice architectural reductionism — designing private residences, cultural spaces, 
          and bespoke furniture that converse in quiet contemplation with the Nordic landscape.
        </p>
        <div className="nord-hero__footer">
          <a href="#projects" className="nord-hero__scroll">
            <span>Explore Works</span>
            <span className="arrow">↓</span>
          </a>
          <div className="nord-hero__meta">
            <span>RIBA International Award 2024</span>
            <span>Mies Crown Americas Finalist</span>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Hero.css",
        """.nord-hero {
  padding: 8rem 2.5rem 6rem;
  background: radial-gradient(circle at 80% 20%, #27272a 0%, #18181b 70%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.nord-hero__container {
  max-width: 1300px;
  margin: 0 auto;
}
.nord-hero__eyebrow {
  font-size: 0.75rem;
  letter-spacing: 0.25em;
  color: #d97706;
  margin-bottom: 2rem;
  font-weight: 600;
}
.nord-hero__title {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(2.8rem, 6vw, 5rem);
  font-weight: 300;
  line-height: 1.1;
  color: #fafafa;
  margin-bottom: 2rem;
  max-width: 900px;
}
.nord-hero__title em {
  font-style: italic;
  color: #d97706;
  font-weight: 400;
}
.nord-hero__sub {
  font-size: 1.15rem;
  line-height: 1.8;
  color: #a1a1aa;
  max-width: 650px;
  margin-bottom: 4.5rem;
}
.nord-hero__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 2rem;
}
.nord-hero__scroll {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  color: #f4f4f5;
  text-decoration: none;
  font-size: 0.82rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.nord-hero__scroll .arrow {
  color: #d97706;
}
.nord-hero__meta {
  display: flex;
  gap: 2rem;
  font-size: 0.78rem;
  color: #71717a;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
@media (max-width: 768px) {
  .nord-hero__footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 1.5rem;
  }
}
"""
    )

    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Projects section: display the 3 architectural monographs from the brief (Villa Fjord, Glass Pavilion, Klar Studio) with locations, square meters, year, and detailed spatial narratives. Files: src/components/Projects.tsx + src/components/Projects.css"
    )

    t3_thought = thought(
        "Hero accepted. Writing Projects section. Each project is presented with clean typography, "
        "specifications (sq meters, year, location), and elegant border dividing lines."
    )
    t3_action = write_site(
        "src/components/Projects.tsx",
        """import React from 'react';
import './Projects.css';

interface ProjectItem {
  name: string;
  location: string;
  area: string;
  year: string;
  desc: string;
}

const PROJECTS: ProjectItem[] = [
  {
    name: 'Villa Fjord',
    location: 'Bergen, Norway',
    area: '420 m²',
    year: '2024',
    desc: 'Cantilevered charred timber and black granite residence framing unbroken Arctic water views with recessed passive thermal envelope.'
  },
  {
    name: 'The Glass Pavilion',
    location: 'Stockholm, Sweden',
    area: '280 m²',
    year: '2023',
    desc: 'Double-glazed minimalist woodland studio with integrated geothermal radiant slab heating and native pinewood joinery.'
  },
  {
    name: 'Klar Studio House',
    location: 'Copenhagen, Denmark',
    area: '350 m²',
    year: '2024',
    desc: 'Adaptive reuse of a 19th-century brick warehouse into hybrid residential galleries, celebrating patina and raw steel trusses.'
  }
];

export function Projects() {
  return (
    <section className="nord-projects" id="projects">
      <div className="nord-projects__container">
        <div className="nord-projects__header">
          <span className="nord-projects__tag">INDEX OF WORKS</span>
          <h2 className="nord-projects__title">Selected Spatial Commissions</h2>
        </div>

        <div className="nord-projects__list">
          {PROJECTS.map((proj, idx) => (
            <article key={proj.name} className="nord-proj-row">
              <div className="nord-proj-row__num">0{idx + 1}</div>
              <div className="nord-proj-row__main">
                <h3 className="nord-proj-row__name">{proj.name}</h3>
                <p className="nord-proj-row__desc">{proj.desc}</p>
              </div>
              <div className="nord-proj-row__meta">
                <span>{proj.location}</span>
                <span>{proj.area}</span>
                <span>{proj.year}</span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Projects.css",
        """.nord-projects {
  padding: 7rem 2.5rem;
  background: #18181b;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.nord-projects__container {
  max-width: 1300px;
  margin: 0 auto;
}
.nord-projects__header {
  margin-bottom: 4.5rem;
}
.nord-projects__tag {
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  color: #d97706;
  display: block;
  margin-bottom: 0.8rem;
}
.nord-projects__title {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(2.2rem, 4vw, 3.4rem);
  font-weight: 300;
  color: #fafafa;
}
.nord-projects__list {
  display: flex;
  flex-direction: column;
}
.nord-proj-row {
  display: grid;
  grid-template-columns: 80px 1.5fr 1fr;
  gap: 3rem;
  padding: 3rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  align-items: baseline;
  transition: all 0.25s ease;
}
.nord-proj-row:hover {
  background: rgba(255, 255, 255, 0.015);
  padding-left: 1rem;
}
.nord-proj-row__num {
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.4rem;
  color: #d97706;
}
.nord-proj-row__name {
  font-family: 'Cormorant Garamond', serif;
  font-size: 2rem;
  font-weight: 400;
  color: #ffffff;
  margin-bottom: 0.8rem;
}
.nord-proj-row__desc {
  font-size: 0.95rem;
  line-height: 1.65;
  color: #a1a1aa;
  max-width: 540px;
}
.nord-proj-row__meta {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #71717a;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
@media (max-width: 860px) {
  .nord-proj-row {
    grid-template-columns: 1fr;
    gap: 1.2rem;
  }
}
"""
    )

    t3_obs = obs_ok(
        ["src/components/Projects.tsx", "src/components/Projects.css"],
        "Write the Philosophy section: an architectural manifesto on materiality, light, acoustics, and permanence. Files: src/components/Philosophy.tsx + src/components/Philosophy.css"
    )

    t4_thought = thought(
        "Projects accepted. Writing Philosophy section — two-column manifesto on spatial reductionism and craft."
    )
    t4_action = write_site(
        "src/components/Philosophy.tsx",
        """import React from 'react';
import './Philosophy.css';

export function Philosophy() {
  return (
    <section className="nord-philosophy" id="philosophy">
      <div className="nord-philosophy__container">
        <div className="nord-philosophy__lead">
          <span className="nord-philosophy__tag">MANIFESTO</span>
          <h2 className="nord-philosophy__title">
            &ldquo;A building is not an object; it is an instrument through which the sky, weather, and light are experienced.&rdquo;
          </h2>
        </div>

        <div className="nord-philosophy__body">
          <p>
            We reject the transient visual noise of contemporary development. Every project begins with an intensive 
            geological survey, sun-path analysis, and acoustic mapping of the terrain.
          </p>
          <p>
            By sourcing Gotland limestone, slow-grown pine, and handmade blackened iron, our structures are designed 
            to weather with grace over centuries rather than degrade over decades.
          </p>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Philosophy.css",
        """.nord-philosophy {
  padding: 8rem 2.5rem;
  background: #121214;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.nord-philosophy__container {
  max-width: 1300px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 5rem;
  align-items: center;
}
.nord-philosophy__tag {
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  color: #d97706;
  display: block;
  margin-bottom: 1.5rem;
}
.nord-philosophy__title {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(2rem, 3.5vw, 3rem);
  font-weight: 300;
  line-height: 1.35;
  color: #f4f4f5;
  font-style: italic;
}
.nord-philosophy__body {
  display: flex;
  flex-direction: column;
  gap: 1.8rem;
  font-size: 1.05rem;
  line-height: 1.8;
  color: #a1a1aa;
}
@media (max-width: 860px) {
  .nord-philosophy__container {
    grid-template-columns: 1fr;
    gap: 3rem;
  }
}
"""
    )

    t4_obs = obs_ok(
        ["src/components/Philosophy.tsx", "src/components/Philosophy.css"],
        "Write the Footer section: dark minimalist footer with Atelier Nord Oslo studio address, direct contact email, commission inquiries, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    t5_thought = thought(
        "Philosophy accepted. Writing Footer section to conclude Atelier Nord."
    )
    t5_action = write_site(
        "src/components/Footer.tsx",
        """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="nord-footer" id="contact">
      <div className="nord-footer__container">
        <div className="nord-footer__col">
          <span className="nord-footer__brand">Atelier Nord</span>
          <p>Architects &amp; Spatial Researchers</p>
        </div>

        <div className="nord-footer__col">
          <h4>Oslo Studio</h4>
          <address>
            Dronningens Gate 14<br />
            0152 Oslo, Norway<br />
            +47 22 33 44 55
          </address>
        </div>

        <div className="nord-footer__col">
          <h4>Inquiries</h4>
          <p><a href="mailto:inquiries@ateliernord.no">inquiries@ateliernord.no</a></p>
          <p><a href="mailto:press@ateliernord.no">press@ateliernord.no</a></p>
        </div>

        <div className="nord-footer__col">
          <h4>Archive</h4>
          <p>© {new Date().getFullYear()} Atelier Nord AS</p>
          <p>All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
""",
        "src/components/Footer.css",
        """.nord-footer {
  padding: 6rem 2.5rem 3rem;
  background: #0d0d0f;
  color: #71717a;
  font-size: 0.88rem;
}
.nord-footer__container {
  max-width: 1300px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: 3rem;
}
.nord-footer__brand {
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.4rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #f4f4f5;
  display: block;
  margin-bottom: 0.5rem;
}
.nord-footer__col h4 {
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #d97706;
  margin-bottom: 1rem;
}
.nord-footer__col address {
  font-style: normal;
  line-height: 1.7;
}
.nord-footer__col a {
  color: #d4d4d8;
  text-decoration: none;
}
.nord-footer__col a:hover {
  color: #d97706;
}
@media (max-width: 800px) {
  .nord-footer__container {
    grid-template-columns: 1fr 1fr;
  }
}
"""
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Projects.tsx", "src/components/Projects.css",
        "src/components/Philosophy.tsx", "src/components/Philosophy.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought("Atelier Nord architecture website is complete across all 5 sections.")
    t6_action = finish(
        "Built the complete Atelier Nord Scandinavian architecture studio website with 5 sections:\n"
        "- Header: spacious minimalist navigation with serif branding and inquiry button\n"
        "- Hero: poetic editorial serif heading, studio coordinates, and international awards\n"
        "- Projects: monographs for Villa Fjord, The Glass Pavilion, and Klar Studio with square meters\n"
        "- Philosophy: architectural manifesto on light, acoustics, and endurance\n"
        "- Footer: Oslo studio address and direct partner inquiry channels\n"
        "Palette: dark charcoal (#18181b) with warm ochre (#d97706) and Cormorant Garamond typography."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_architecture_atelier_nord", "messages": messages}


# ─────────────────────────────────────────────────────────────────────────
# 5. trajectory_coffee_01 — Solace Coffee Roasters (artisan single-origin)
# ─────────────────────────────────────────────────────────────────────────
def trajectory_coffee_01():
    brief_xml = """<content_brief>
  <business_name>Solace Roasters</business_name>
  <tagline>Direct-trade single-origin coffees roasted with scientific rigor</tagline>
  <business_type>ecommerce</business_type>
  <primary_color>#1c1917</primary_color>
  <accent_color>#ea580c</accent_color>
  <font_heading>Fraunces</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, catalog, story, footer</sections>
  <coffee_item name="Yirgacheffe Floral" origin="Gedeo Zone, Ethiopia" process="Washed" notes="Bergamot, jasmine, candied lemon" price="$22" />
  <coffee_item name="Huila Pink Bourbon" origin="San Agustin, Colombia" process="Anaerobic 72h" notes="Blood orange, guava, cacao nibs" price="$26" />
  <coffee_item name="Antigua Peaberry" origin="Finca Medina, Guatemala" process="Natural" notes="Dark chocolate, marzipan, plum" price="$20" />
  <contact>
    <roastery>744 Industrial Way, Portland, OR 97209</roastery>
    <email>orders@solaceroasters.com</email>
    <phone>+1 (503) 555-0149</phone>
  </contact>
</content_brief>"""

    initial_user = (
        "Build a complete website for the following brief.\n\n"
        f"{brief_xml}\n\n"
        "You will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        "FIRST SECTION REQUIRED: Write the Header section: warm espresso-themed navbar with coffee logo, links (Coffees, Subscriptions, Origins, Brew Guides), shopping cart drawer trigger, and 'Shop Direct' button. Files: src/components/Header.tsx + src/components/Header.css"
    )

    t1_thought = thought(
        "I'll write the Solace Roasters Header. Specialty coffee eCommerce calls for an organic, tactile aesthetic: "
        "dark espresso brown (#1c1917) paired with flame terracotta orange (#ea580c), Fraunces serif typography, "
        "and direct shopping cart access."
    )
    t1_action = write_site(
        "src/components/Header.tsx",
        """import React, { useState } from 'react';
import './Header.css';

export function Header() {
  const [cartCount, setCartCount] = useState(2);

  return (
    <header className="solace-header">
      <div className="solace-header__container">
        <a href="#" className="solace-header__brand">
          <span className="solace-header__icon">♨</span>
          <span>Solace <em>Roasters</em></span>
        </a>

        <nav className="solace-header__nav" aria-label="Main Navigation">
          <a href="#hero">Home</a>
          <a href="#catalog">Single Origins</a>
          <a href="#story">Direct Trade</a>
        </nav>

        <div className="solace-header__actions">
          <span className="solace-header__cart" aria-label="Cart items">
            <span>Bag ({cartCount})</span>
          </span>
          <a href="#catalog" className="solace-btn solace-btn--orange">
            Shop Fresh Crop
          </a>
        </div>
      </div>
    </header>
  );
}
""",
        "src/components/Header.css",
        """.solace-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: #1c1917;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.solace-header__container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 78px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.solace-header__brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  font-family: 'Fraunces', serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: #fafaf9;
}
.solace-header__icon {
  color: #ea580c;
  font-size: 1.4rem;
}
.solace-header__brand em {
  font-style: italic;
  color: #fdba74;
  font-weight: 400;
}
.solace-header__nav {
  display: flex;
  gap: 2.2rem;
}
.solace-header__nav a {
  color: #d6d3d1;
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 500;
  transition: color 0.2s;
}
.solace-header__nav a:hover {
  color: #ea580c;
}
.solace-header__actions {
  display: flex;
  align-items: center;
  gap: 1.4rem;
}
.solace-header__cart {
  color: #fafaf9;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
}
.solace-btn {
  padding: 0.6rem 1.4rem;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
}
.solace-btn--orange {
  background: #ea580c;
  color: #ffffff;
}
.solace-btn--orange:hover {
  background: #c2410c;
}
@media (max-width: 820px) {
  .solace-header__nav { display: none; }
}
"""
    )

    t1_obs = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: sensory coffee banner highlighting roast date freshness, origin traceability, tasting notes tag pill, and dual CTA buttons. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    t2_thought = thought(
        "Header accepted. Now writing the Hero for Solace Roasters with rich flavor profiles and sensory roast details."
    )
    t2_action = write_site(
        "src/components/Hero.tsx",
        """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="solace-hero" id="hero">
      <div className="solace-hero__container">
        <div className="solace-hero__content">
          <span className="solace-hero__badge">ROASTED TO ORDER IN PORTLAND, OR</span>
          <h1 className="solace-hero__title">
            Direct-trade coffees roasted with <em>scientific clarity</em>.
          </h1>
          <p className="solace-hero__sub">
            We partner directly with family estates in Huila, Yirgacheffe, and Antigua. 
            Roasted on custom Loring smart convection roasters to celebrate terroir, not charcoal.
          </p>

          <div className="solace-hero__actions">
            <a href="#catalog" className="solace-btn solace-btn--orange solace-btn--lg">
              Explore Current Releases
            </a>
            <a href="#story" className="solace-btn solace-btn--outline solace-btn--lg">
              Join The Roaster's Club
            </a>
          </div>

          <div className="solace-hero__badges">
            <div className="solace-badge-item">
              <span className="badge-num">100%</span>
              <span className="badge-label">Direct Farm Trade</span>
            </div>
            <div className="solace-badge-item">
              <span className="badge-num">87+</span>
              <span className="badge-label">SCA Cup Scores</span>
            </div>
            <div className="solace-badge-item">
              <span className="badge-num">&lt;48h</span>
              <span className="badge-label">Roast to Ship</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Hero.css",
        """.solace-hero {
  padding: 7rem 2rem 5.5rem;
  background: radial-gradient(circle at 75% 30%, #292524 0%, #1c1917 65%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.solace-hero__container {
  max-width: 1240px;
  margin: 0 auto;
}
.solace-hero__content {
  max-width: 780px;
}
.solace-hero__badge {
  display: inline-block;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #ea580c;
  margin-bottom: 1.2rem;
}
.solace-hero__title {
  font-family: 'Fraunces', serif;
  font-size: clamp(2.5rem, 5vw, 4.2rem);
  font-weight: 700;
  color: #fafaf9;
  line-height: 1.15;
  margin-bottom: 1.5rem;
}
.solace-hero__title em {
  font-style: italic;
  color: #fdba74;
}
.solace-hero__sub {
  font-size: 1.15rem;
  line-height: 1.7;
  color: #a8a29e;
  margin-bottom: 2.8rem;
}
.solace-hero__actions {
  display: flex;
  gap: 1.2rem;
  margin-bottom: 3.5rem;
  flex-wrap: wrap;
}
.solace-btn--lg {
  padding: 0.85rem 1.8rem;
  font-size: 0.98rem;
}
.solace-btn--outline {
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fafaf9;
  background: transparent;
}
.solace-btn--outline:hover {
  background: rgba(255, 255, 255, 0.05);
}
.solace-hero__badges {
  display: flex;
  gap: 3rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 2rem;
}
.solace-badge-item {
  display: flex;
  flex-direction: column;
}
.badge-num {
  font-family: 'Fraunces', serif;
  font-size: 2rem;
  font-weight: 700;
  color: #fafaf9;
}
.badge-label {
  font-size: 0.78rem;
  text-transform: uppercase;
  color: #78716c;
  letter-spacing: 0.08em;
}
"""
    )

    t2_obs = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        "Write the Catalog section: display the 3 coffees from the brief (Yirgacheffe Floral, Huila Pink Bourbon, Antigua Peaberry) with origins, process methods, tasting notes, prices, and 'Add to Bag' interactive buttons. Files: src/components/Catalog.tsx + src/components/Catalog.css"
    )

    t3_thought = thought(
        "Hero accepted. Writing Catalog section with tasting notes and interactive Add to Bag counters."
    )
    t3_action = write_site(
        "src/components/Catalog.tsx",
        """import React, { useState } from 'react';
import './Catalog.css';

interface Coffee {
  name: string;
  origin: string;
  process: string;
  notes: string;
  price: string;
  altitude: string;
}

const COFFEES: Coffee[] = [
  {
    name: 'Yirgacheffe Floral',
    origin: 'Gedeo Zone, Ethiopia',
    process: 'Washed',
    notes: 'Bergamot, jasmine, candied lemon zest',
    price: '$22.00',
    altitude: '2,100 MASL'
  },
  {
    name: 'Huila Pink Bourbon',
    origin: 'San Agustin, Colombia',
    process: 'Anaerobic 72h',
    notes: 'Blood orange, guava, cacao nibs',
    price: '$26.00',
    altitude: '1,850 MASL'
  },
  {
    name: 'Antigua Peaberry',
    origin: 'Finca Medina, Guatemala',
    process: 'Sun-Dried Natural',
    notes: 'Dark chocolate, marzipan, spiced plum',
    price: '$20.00',
    altitude: '1,600 MASL'
  }
];

export function Catalog() {
  const [added, setAdded] = useState<string | null>(null);

  const handleAdd = (name: string) => {
    setAdded(name);
    setTimeout(() => setAdded(null), 1800);
  };

  return (
    <section className="solace-catalog" id="catalog">
      <div className="solace-catalog__container">
        <div className="solace-catalog__header">
          <span className="solace-tag">DIRECT TRADE RELEASES</span>
          <h2 className="solace-catalog__title">Single-Origin Roast Index</h2>
          <p className="solace-catalog__sub">Each 250g bag shipped in nitrogen-flushed compostable valve bags.</p>
        </div>

        <div className="solace-catalog__grid">
          {COFFEES.map((c) => (
            <div key={c.name} className="solace-card">
              <div className="solace-card__header">
                <span className="solace-card__process">{c.process}</span>
                <span className="solace-card__alt">{c.altitude}</span>
              </div>
              <h3 className="solace-card__title">{c.name}</h3>
              <div className="solace-card__origin">📍 {c.origin}</div>
              <div className="solace-card__notes">
                <strong>Tasting Notes:</strong> {c.notes}
              </div>
              <div className="solace-card__footer">
                <span className="solace-card__price">{c.price}</span>
                <button 
                  onClick={() => handleAdd(c.name)} 
                  className="solace-btn solace-btn--orange"
                >
                  {added === c.name ? '✓ Added' : 'Add to Bag'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Catalog.css",
        """.solace-catalog {
  padding: 6.5rem 2rem;
  background: #141210;
}
.solace-catalog__container {
  max-width: 1240px;
  margin: 0 auto;
}
.solace-catalog__header {
  text-align: center;
  max-width: 680px;
  margin: 0 auto 4rem;
}
.solace-tag {
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #ea580c;
  display: inline-block;
  margin-bottom: 0.8rem;
}
.solace-catalog__title {
  font-family: 'Fraunces', serif;
  font-size: clamp(2rem, 3.5vw, 3rem);
  color: #fafaf9;
  margin-bottom: 0.8rem;
}
.solace-catalog__sub {
  color: #a8a29e;
  font-size: 1.05rem;
}
.solace-catalog__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
}
.solace-card {
  background: #1c1917;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 2.2rem;
  display: flex;
  flex-direction: column;
  transition: all 0.25s ease;
}
.solace-card:hover {
  border-color: #ea580c;
  transform: translateY(-4px);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.5);
}
.solace-card__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.solace-card__process {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #ea580c;
}
.solace-card__alt {
  font-size: 0.75rem;
  color: #78716c;
}
.solace-card__title {
  font-family: 'Fraunces', serif;
  font-size: 1.5rem;
  color: #fafaf9;
  margin-bottom: 0.5rem;
}
.solace-card__origin {
  font-size: 0.85rem;
  color: #a8a29e;
  margin-bottom: 1.2rem;
}
.solace-card__notes {
  font-size: 0.92rem;
  line-height: 1.6;
  color: #d6d3d1;
  background: rgba(255, 255, 255, 0.03);
  padding: 0.8rem;
  border-radius: 8px;
  margin-bottom: 1.8rem;
  flex: 1;
}
.solace-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 1.2rem;
}
.solace-card__price {
  font-family: 'Fraunces', serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: #fafaf9;
}
@media (max-width: 900px) {
  .solace-catalog__grid {
    grid-template-columns: 1fr;
    max-width: 480px;
    margin: 0 auto;
  }
}
"""
    )

    t3_obs = obs_ok(
        ["src/components/Catalog.tsx", "src/components/Catalog.css"],
        "Write the Story section: two-column narrative on direct-trade farm pricing, 300% above Fair Trade minimums, and roast thermodynamics. Files: src/components/Story.tsx + src/components/Story.css"
    )

    t4_thought = thought(
        "Catalog accepted. Writing Story section highlighting farm premiums and roasting ethics."
    )
    t4_action = write_site(
        "src/components/Story.tsx",
        """import React from 'react';
import './Story.css';

export function Story() {
  return (
    <section className="solace-story" id="story">
      <div className="solace-story__container">
        <div className="solace-story__grid">
          <div className="solace-story__text">
            <span className="solace-tag">ETHICS &amp; PRICING TRANSPARENCY</span>
            <h2 className="solace-story__title">We pay 300% above Fair Trade minimums</h2>
            <p>
              Commodity coffee pricing exploits the producers who take on the greatest agricultural risk. 
              At Solace, we contract directly with smallholder farmers, pre-financing harvests and paying 
              transparent quality premiums tied to SCA cupping grades.
            </p>
            <p>
              By eliminating brokers, 74% of the green coffee FOB price goes directly to farm infrastructure, 
              organic soil management, and worker health funds.
            </p>
          </div>
          <div className="solace-story__stat-box">
            <div className="stat-card">
              <span className="stat-card__num">$4.85</span>
              <span className="stat-card__label">Average Price Paid per Lb (vs $1.80 C-Market)</span>
            </div>
            <div className="stat-card">
              <span className="stat-card__num">6 Years</span>
              <span className="stat-card__label">Average Producer Partnership Length</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
        "src/components/Story.css",
        """.solace-story {
  padding: 6.5rem 2rem;
  background: #1c1917;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.solace-story__container {
  max-width: 1240px;
  margin: 0 auto;
}
.solace-story__grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 4rem;
  align-items: center;
}
.solace-story__title {
  font-family: 'Fraunces', serif;
  font-size: clamp(2.2rem, 4vw, 3.2rem);
  color: #fafaf9;
  margin-bottom: 1.4rem;
}
.solace-story__text p {
  font-size: 1.05rem;
  line-height: 1.75;
  color: #a8a29e;
  margin-bottom: 1.2rem;
}
.solace-story__stat-box {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.stat-card {
  background: #141210;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 2rem;
}
.stat-card__num {
  font-family: 'Fraunces', serif;
  font-size: 2.8rem;
  font-weight: 700;
  color: #ea580c;
  display: block;
  margin-bottom: 0.4rem;
}
.stat-card__label {
  font-size: 0.9rem;
  color: #a8a29e;
}
@media (max-width: 860px) {
  .solace-story__grid {
    grid-template-columns: 1fr;
  }
}
"""
    )

    t4_obs = obs_ok(
        ["src/components/Story.tsx", "src/components/Story.css"],
        "Write the Footer section: dark warm footer with Portland roastery address, contact phone, order support email, newsletter signup, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    t5_thought = thought(
        "Story accepted. Writing Footer section to conclude Solace Coffee Roasters."
    )
    t5_action = write_site(
        "src/components/Footer.tsx",
        """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="solace-footer">
      <div className="solace-footer__container">
        <div className="solace-footer__top">
          <div className="solace-footer__brand">
            <span className="solace-footer__logo">♨ Solace Roasters</span>
            <p>Direct-trade small batch coffee roasters based in the Pacific Northwest.</p>
          </div>

          <div className="solace-footer__col">
            <h4>Roastery Lab</h4>
            <address>
              744 Industrial Way<br />
              Pearl District<br />
              Portland, OR 97209
            </address>
          </div>

          <div className="solace-footer__col">
            <h4>Support</h4>
            <p>📞 +1 (503) 555-0149</p>
            <p>✉️ <a href="mailto:orders@solaceroasters.com">orders@solaceroasters.com</a></p>
          </div>
        </div>

        <div className="solace-footer__bottom">
          <p>© {new Date().getFullYear()} Solace Roasters Co. B-Corp Certified.</p>
          <p>Fresh roasted daily · Carbon neutral shipping worldwide.</p>
        </div>
      </div>
    </footer>
  );
}
""",
        "src/components/Footer.css",
        """.solace-footer {
  background: #0f0e0c;
  padding: 5rem 2rem 2.5rem;
  color: #78716c;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.solace-footer__container {
  max-width: 1240px;
  margin: 0 auto;
}
.solace-footer__top {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 3rem;
  margin-bottom: 3.5rem;
}
.solace-footer__logo {
  font-family: 'Fraunces', serif;
  font-size: 1.4rem;
  color: #fafaf9;
  display: block;
  margin-bottom: 0.8rem;
}
.solace-footer__brand p {
  font-size: 0.92rem;
  line-height: 1.6;
  max-width: 320px;
}
.solace-footer__col h4 {
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #ea580c;
  margin-bottom: 0.8rem;
}
.solace-footer__col address, .solace-footer__col p {
  font-style: normal;
  font-size: 0.88rem;
  line-height: 1.7;
}
.solace-footer__col a {
  color: #fdba74;
  text-decoration: none;
}
.solace-footer__bottom {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 1.8rem;
  font-size: 0.82rem;
}
@media (max-width: 768px) {
  .solace-footer__top {
    grid-template-columns: 1fr;
  }
}
"""
    )

    all_files = [
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        "src/components/Catalog.tsx", "src/components/Catalog.css",
        "src/components/Story.tsx", "src/components/Story.css",
        "src/components/Footer.tsx", "src/components/Footer.css",
    ]
    t5_obs = obs_done(all_files)
    t6_thought = thought("Solace Roasters coffee eCommerce site is complete across all 5 sections.")
    t6_action = finish(
        "Built the complete Solace Roasters specialty coffee eCommerce website with 5 sections:\n"
        "- Header: warm espresso navbar with coffee branding, origin links, and cart badge\n"
        "- Hero: sensory roast headline, direct-trade badges, and origin freshness callout\n"
        "- Catalog: 3 single-origin coffees (Ethiopia, Colombia, Guatemala) with tasting notes and Add to Bag\n"
        "- Story: transparency section detailing 300% premium paid above Fair Trade baseline\n"
        "- Footer: Portland roastery coordinates, customer support, and carbon-neutral badge\n"
        "Palette: espresso (#1c1917) with flame terracotta (#ea580c) and Fraunces serif typography."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": assistant(t1_thought, t1_action)},
        {"role": "user", "content": t1_obs},
        {"role": "assistant", "content": assistant(t2_thought, t2_action)},
        {"role": "user", "content": t2_obs},
        {"role": "assistant", "content": assistant(t3_thought, t3_action)},
        {"role": "user", "content": t3_obs},
        {"role": "assistant", "content": assistant(t4_thought, t4_action)},
        {"role": "user", "content": t4_obs},
        {"role": "assistant", "content": assistant(t5_thought, t5_action)},
        {"role": "user", "content": t5_obs},
        {"role": "assistant", "content": assistant(t6_thought, t6_action)},
    ]
    return {"task_id": "site_ecommerce_solace_coffee", "messages": messages}


BATCH_3 = [
    trajectory_fintech_01,
    trajectory_healthcare_01,
    trajectory_ai_platform_01,
    trajectory_architecture_01,
    trajectory_coffee_01,
]



# ==============================================================================
# BATCH 4: 50 Real-World Domains
# ==============================================================================

import json
import re
import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")





def thought(text):
    return f"<thought>\n{text}\n</thought>"


def finish(text):
    return f"<finish>\n{text}\n</finish>"


# ── 50 Domain Specifications ──────────────────────────────────────────────────

DOMAINS_B4 = [
    {
        "id": "site_bakery_golden_crumb",
        "name": "Golden Crumb Bakery",
        "tagline": "Handcrafted Sourdough and Parisian Patisserie",
        "type": "bakery",
        "prefix": "gc",
        "primary": "#221914",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#2d221c",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Pre-Order Bakes",
        "hero_sub": "Wild-fermented European breads, flaky cultured butter croissants, and seasonal fruit tarts baked fresh before dawn.",
        "section_name": "Pastries & Breads",
        "section_id": "bakes",
        "items": [
            {"title": "Country Sourdough Boule", "tag": "$9.50", "desc": "36-hour cold ferment with stone-ground heritage whole wheat and caramelized blistered crust."},
            {"title": "Cardamom Almond Croissant", "tag": "$6.25", "desc": "Twice-baked laminated viennoiserie soaked in orange blossom syrup with toasted almond frangipane."},
            {"title": "Valrhona Chocolate Babka", "tag": "$14.00", "desc": "Brioche loaf braided with 70% dark chocolate fudge, Ceylon cinnamon, and crystal sugar syrup."},
            {"title": "Miso Hazelnut Kouign-Amann", "tag": "$5.75", "desc": "Breton butter pastry caramelized with salted white miso honey and roasted Piedmont hazelnuts."}
        ],
        "contact": {
            "address": "144 Artisan Way, Portland, OR 97209",
            "phone": "+1 (503) 555-0182",
            "email": "orders@goldencrumb.com",
            "hours": "Wed–Sun: 7am–3pm (or until sold out)"
        }
    },
    {
        "id": "site_law_vance_holloway",
        "name": "Vance & Holloway LLP",
        "tagline": "Strategic Counsel for Emerging Tech and IP Litigation",
        "type": "law_firm",
        "prefix": "vh",
        "primary": "#0c1524",
        "accent": "#c5a059",
        "accent_hover": "#dfb76c",
        "surface": "#142136",
        "heading_font": "Merriweather",
        "body_font": "Inter",
        "cta": "Schedule Consultation",
        "hero_sub": "Protecting foundational innovations, defending patents in federal court, and structuring high-stakes venture transactions across Silicon Valley and New York.",
        "section_name": "Practice Areas",
        "section_id": "practices",
        "items": [
            {"title": "Patent & IP Litigation", "tag": "Federal Defense", "desc": "First-chair trial defense in patent infringement, trademark disputes, and trade secret misappropriation."},
            {"title": "Venture & M&A Transactions", "tag": "Corporate", "desc": "Structuring priced rounds, cross-border acquisitions, and convertible securities for high-growth tech firms."},
            {"title": "AI & Regulatory Compliance", "tag": "Advisory", "desc": "Navigating generative AI copyright, EU AI Act compliance, and autonomous systems liability frameworks."},
            {"title": "Executive Compensation & Equity", "tag": "Governance", "desc": "Designing tax-advantaged stock option plans, founder vesting agreements, and board governance charters."}
        ],
        "contact": {
            "address": "555 California St, Suite 3200, San Francisco, CA 94104",
            "phone": "+1 (415) 555-0199",
            "email": "intake@vanceholloway.com",
            "hours": "Mon–Fri: 8am–6:30pm"
        }
    },
    {
        "id": "site_travel_wanderlust_expeditions",
        "name": "Wanderlust Expeditions",
        "tagline": "Uncharted Luxury and Regenerative Wildlife Safaris",
        "type": "travel",
        "prefix": "wl",
        "primary": "#122018",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "surface": "#1b3024",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Book Expedition",
        "hero_sub": "Bespoke small-group journeys led by certified field biologists and mountaineers into Earth's most remote and pristine ecosystems.",
        "section_name": "Featured Journeys",
        "section_id": "expeditions",
        "items": [
            {"title": "Serengeti Migration & Crater", "tag": "10 Days", "desc": "Mobile luxury canvas tenting tracking seasonal wildebeest crossings with private Maasai guides."},
            {"title": "Patagonia Fjords & Glaciers", "tag": "12 Days", "desc": "Catamaran navigation through southern ice fields paired with Torres del Paine backcountry horse treks."},
            {"title": "Svalbard Polar Bear Quest", "tag": "8 Days", "desc": "Small expedition ice-class vessel cruising Spitsbergen pack ice under the midnight sun."},
            {"title": "Raja Ampat Coral Diving", "tag": "11 Days", "desc": "Traditional wooden phinisi yacht liveaboard exploring the biodiverse epicentre of the Coral Triangle."}
        ],
        "contact": {
            "address": "820 2nd Ave, Suite 700, Seattle, WA 98104",
            "phone": "+1 (206) 555-0144",
            "email": "concierge@wanderlustexpeditions.com",
            "hours": "Mon–Sat: 9am–7pm"
        }
    },
    {
        "id": "site_vet_paws_claws_hospital",
        "name": "Paws & Claws Animal Hospital",
        "tagline": "Compassionate Medicine and Advanced 24/7 Veterinary Care",
        "type": "veterinary",
        "prefix": "pc",
        "primary": "#0f202b",
        "accent": "#14b8a6",
        "accent_hover": "#0d9488",
        "surface": "#173041",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Book Appointment",
        "hero_sub": "Board-certified surgeons, feline-friendly exam rooms, low-stress handling, and on-site CT diagnostic imaging for your companions.",
        "section_name": "Clinical Services",
        "section_id": "services",
        "items": [
            {"title": "24/7 Emergency & ICU Care", "tag": "Always Open", "desc": "Immediate critical care with oxygen therapy cages, blood transfusions, and continuous telemetry monitoring."},
            {"title": "Minimally Invasive Surgery", "tag": "Specialized", "desc": "Laparoscopic spays, soft tissue reconstructions, and orthopedic stifle stabilization with rapid recovery."},
            {"title": "Advanced Digital Radiology", "tag": "Diagnostics", "desc": "In-house 64-slice CT scans, high-resolution ultrasound, and certified board radiologist evaluations."},
            {"title": "Dental Prophylaxis & Surgery", "tag": "Preventative", "desc": "Full-mouth digital radiographs, ultrasonic scaling, and subgingival laser periodontal treatments."}
        ],
        "contact": {
            "address": "4020 W Sunset Blvd, Los Angeles, CA 90027",
            "phone": "+1 (323) 555-0120",
            "email": "care@pawsandclawsvet.com",
            "hours": "24 Hours / 7 Days a Week"
        }
    },
    {
        "id": "site_podcast_the_future_syntax",
        "name": "The Future Syntax",
        "tagline": "Conversations on Deep Tech, Neural Models, and Cybernetics",
        "type": "podcast",
        "prefix": "fs",
        "primary": "#0b0e17",
        "accent": "#a855f7",
        "accent_hover": "#9333ea",
        "surface": "#141926",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Listen on Spotify",
        "hero_sub": "Weekly uncensored technical interviews with the research scientists, chip architects, and founders building superintelligence.",
        "section_name": "Latest Episodes",
        "section_id": "episodes",
        "items": [
            {"title": "Ep 84: Neuromorphic Silicon & Sub-1nm Nodes", "tag": "74 min", "desc": "Dr. Aris Thorne discusses optical interconnects, non-volatile analog compute, and thermal dissipation limits."},
            {"title": "Ep 83: Frontier RL & Multi-Turn Verification", "tag": "68 min", "desc": "Deep dive into reward model collapse, synthetic tree search, and automated formal theorem proving."},
            {"title": "Ep 82: Brain-Machine Bandwidth & Neural Stents", "tag": "81 min", "desc": "Endovascular electrode arrays, chronic bio-compatibility, and decoding motor cortex intent at 10kHz."},
            {"title": "Ep 81: Autonomous Robotics in Zero-G Space", "tag": "62 min", "desc": "Orbital assembly, visual slam in direct solar glare, and fault-tolerant distributed actuators."}
        ],
        "contact": {
            "address": "Studio 4B, 180 Varick St, New York, NY 10014",
            "phone": "+1 (212) 555-0177",
            "email": "producers@futuresyntaxpodcast.com",
            "hours": "New Episodes Every Tuesday at 6am EST"
        }
    },
    {
        "id": "site_coworking_the_hive_collective",
        "name": "The Hive Collective",
        "tagline": "Architect-Designed Workspaces for Creators and Founders",
        "type": "coworking",
        "prefix": "th",
        "primary": "#18181b",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
        "surface": "#27272a",
        "heading_font": "DM Sans",
        "body_font": "Inter",
        "cta": "Book a Day Pass",
        "hero_sub": "Ergonomic Herman Miller seating, 10Gbps fiber internet, soundproof podcast booths, and barista-pulled espresso in the heart of downtown.",
        "section_name": "Membership Tiers",
        "section_id": "memberships",
        "items": [
            {"title": "Hot Desk Flexible", "tag": "$249/mo", "desc": "Access to open communal lounges, quiet library zones, phone booths, and unlimited specialty drip coffee."},
            {"title": "Dedicated Desk", "tag": "$429/mo", "desc": "Your own motorized standing desk, lockable filing drawer, dual 4K monitors, and meeting room credits."},
            {"title": "Private Team Office", "tag": "$1,450/mo", "desc": "Fully enclosed acoustic glass suite for 4–12 people with private whiteboard walls and server racks."},
            {"title": "Virtual Business Address", "tag": "$89/mo", "desc": "Prestigious commercial postal address, secure mail forwarding, and discounted conference room booking."}
        ],
        "contact": {
            "address": "720 S Colorado Blvd, Denver, CO 80246",
            "phone": "+1 (303) 555-0158",
            "email": "community@thehivecollective.co",
            "hours": "24/7 Access for Members | Staffed Mon–Fri 8am–6pm"
        }
    },
    {
        "id": "site_brewery_hop_craft_brewing",
        "name": "Hop & Barrel Brewing Co.",
        "tagline": "Bold Unfiltered IPAs and Barrel-Aged Imperial Stouts",
        "type": "brewery",
        "prefix": "hb",
        "primary": "#1a1614",
        "accent": "#ea580c",
        "accent_hover": "#c2410c",
        "surface": "#26201c",
        "heading_font": "Barlow Condensed",
        "body_font": "Inter",
        "cta": "Explore Taplist",
        "hero_sub": "Independent grain-to-glass brewery featuring 24 rotating taps, wood-fired sourdough pizzas, and an open dog-friendly beer garden.",
        "section_name": "Current Taplist",
        "section_id": "taplist",
        "items": [
            {"title": "Citra Haze Double NEIPA", "tag": "8.2% ABV", "desc": "Triple dry-hopped with Citra, Mosaic, and Galaxy hops. Unfiltered mango, papaya, and citrus aromatics."},
            {"title": "Bourbon Cask Imperial Stout", "tag": "11.5% ABV", "desc": "Aged 14 months in Kentucky rye barrels with Madagascar vanilla beans and toasted cacao nibs."},
            {"title": "Pacific Northwest Pine Pilsner", "tag": "5.1% ABV", "desc": "Crisp German pilsner malt lagered cold for 8 weeks with delicate herbal and noble pine hop bitterness."},
            {"title": "Raspberry Marionberry Wild Sour", "tag": "6.4% ABV", "desc": "Oak foeder-fermented wild ale conditioned on 200 lbs of fresh Willamette Valley berries."}
        ],
        "contact": {
            "address": "1204 Industrial Way, Austin, TX 78702",
            "phone": "+1 (512) 555-0163",
            "email": "taproom@hopandbarrelbrewing.com",
            "hours": "Tue–Thu: 3pm–10pm | Fri–Sat: 12pm–12am | Sun: 12pm–8pm"
        }
    },
    {
        "id": "site_interior_lumina_living",
        "name": "Lumina Living Studio",
        "tagline": "Organic Minimalism and Bespoke Residential Architecture",
        "type": "interior_design",
        "prefix": "ll",
        "primary": "#191919",
        "accent": "#e2b170",
        "accent_hover": "#c99552",
        "surface": "#262626",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "View Portfolio",
        "hero_sub": "Transforming spaces through tactile natural stones, hand-finished lime plaster walls, and custom Japanese-Nordic millwork.",
        "section_name": "Signature Projects",
        "section_id": "projects",
        "items": [
            {"title": "The Tribeca Penthouse", "tag": "New York", "desc": "4,200 sqft full-floor loft balancing raw poured concrete columns with bleached white oak flooring."},
            {"title": "Carmel Coastal Retreat", "tag": "California", "desc": "Dune-facing sanctuary featuring floor-to-ceiling travertine fireplaces and custom bronze lighting."},
            {"title": "Kitsilano Modern Villa", "tag": "Vancouver", "desc": "Biophilic family home with central indoor maple atrium, shoji-inspired screens, and radiant basalt floors."},
            {"title": "Aspen Mountain Chalet", "tag": "Colorado", "desc": "Contemporary timber chalet integrating reclaimed cedar beams, wool textiles, and sculptural brass fixtures."}
        ],
        "contact": {
            "address": "342 W 14th St, Floor 4, New York, NY 10014",
            "phone": "+1 (212) 555-0133",
            "email": "studio@luminaliving.design",
            "hours": "By Private Consultation Mon–Fri"
        }
    },
    {
        "id": "site_music_neon_sound_fest",
        "name": "Neon Sound Festival",
        "tagline": "3 Nights of Immersive Electronic and Holographic Music",
        "type": "festival",
        "prefix": "ns",
        "primary": "#090814",
        "accent": "#06b6d4",
        "accent_hover": "#0891b2",
        "surface": "#121124",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Buy Festival Passes",
        "hero_sub": "Over 60 world-class live acts and visual artists across 4 stages with spatial audio dome soundscapes and kinetic laser shows.",
        "section_name": "Headlining Stages",
        "section_id": "stages",
        "items": [
            {"title": "The Cyber Dome", "tag": "Stage 01", "desc": "360-degree spatial L-Acoustics array with real-time reactive AI visual projections and synthwave headliners."},
            {"title": "Subterranean Bass Hall", "tag": "Stage 02", "desc": "Industrial warehouse acoustics engineered for heavy analog sub-bass, experimental dubstep, and glitch art."},
            {"title": "Solstice Outdoor Arena", "tag": "Stage 03", "desc": "Open-air lakeside amphitheater for sunset melodic techno, live orchestral electronica, and drone shows."},
            {"title": "Ambient Chill Sanctuary", "tag": "Stage 04", "desc": "Binaural meditation dome with zero-gravity hammocks, herbal elixir bars, and modular synth live jams."}
        ],
        "contact": {
            "address": "Desert Oasis Grounds, Indio, CA 92201",
            "phone": "+1 (760) 555-0195",
            "email": "tickets@neonsoundfest.com",
            "hours": "Festival Dates: October 16–18, 2026 | Gates Open 2pm Daily"
        }
    },
    {
        "id": "site_accounting_apex_advisory",
        "name": "Apex Advisory Partners",
        "tagline": "Modern Fractional CFO and Tax Strategy for Scale",
        "type": "accounting",
        "prefix": "aa",
        "primary": "#0a1322",
        "accent": "#38bdf8",
        "accent_hover": "#0284c7",
        "surface": "#132138",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Request Audit",
        "hero_sub": "Equipping Series A through C technology founders with automated real-time financial models, R&D tax credit capture, and Board audit readiness.",
        "section_name": "Advisory Capabilities",
        "section_id": "services",
        "items": [
            {"title": "Fractional CFO & Runway Modeling", "tag": "Strategic", "desc": "Multi-scenario cash burn forecasting, capital allocation roadmaps, and investor board deck preparation."},
            {"title": "R&D Tax Credit Optimization", "tag": "Tax", "desc": "Maximizing federal and state research incentives to reclaim up to $250k annually against payroll taxes."},
            {"title": "Automated Cloud Accounting", "tag": "Operations", "desc": "Full QuickBooks and NetSuite migration with automated Stripe reconciliation and multi-currency ledgers."},
            {"title": "SOC 1 & GAAP Audit Prep", "tag": "Compliance", "desc": "Rigorous balance sheet substantiation, revenue recognition (ASC 606), and external auditor management."}
        ],
        "contact": {
            "address": "111 W Washington St, Suite 1800, Chicago, IL 60602",
            "phone": "+1 (312) 555-0188",
            "email": "partners@apexadvisorycfo.com",
            "hours": "Mon–Fri: 8:30am–5:30pm CST"
        }
    }
]

# We will programmatically generate 40 additional domain entries to reach 50 unique domains.
ADDITIONAL_DOMAINS_DATA = [
    ("site_photography_elena_voss", "Elena Voss Photography", "Editorial, Fashion and High-End Portraiture", "photography", "ev", "#121214", "#fafafa", "#d4d4d8", "#222226", "Cinzel", "Inter", "Book Editorial", "Featured Portfolios", "portfolios", [("Haute Couture Paris", "Runway", "Backstage and front-row fashion documentation."), ("The Coastal Series", "Landscape", "35mm analog prints of windswept Icelandic cliffs."), ("Architectural Silhouettes", "Commercial", "Clean lines and stark shadows for global design houses."), ("Intimate Studio Portraits", "Editorial", "Monochrome character studies captured on medium format film.")]),
    ("site_spa_serene_lotus_wellness", "Serene Lotus Sanctuary", "Hydrotherapy, Thermal Baths, and Japanese Onsen", "spa", "sl", "#141d1a", "#2dd4bf", "#0d9488", "#1f2e2a", "Cinzel", "Inter", "Reserve Experience", "Therapeutic Rituals", "rituals", [("Hot Spring Hydrotherapy", "90 min", "Mineral-rich soaking pools with guided breathwork."), ("Aromatherapy Herbal Massage", "60 min", "Wild mountain botanicals and heated river basalt stones."), ("Bamboo Charcoal Sauna", "45 min", "Infrared detoxification and contrast ice bath plunge."), ("Rejuvenating Pearl Facial", "75 min", "Organic marine collagen infusion and lymphatic sculpting.")]),
    ("site_solar_helios_clean_energy", "Helios Clean Energy", "Residential Battery Storage and Rooftop Solar", "solar", "he", "#0a1520", "#eab308", "#ca8a04", "#132333", "Plus Jakarta Sans", "Inter", "Get Solar Quote", "Solar Solutions", "solutions", [("High-Efficiency Monocrystalline Panels", "25yr Warranty", "Sleek all-black panels boasting 22.8% energy conversion."), ("Smart Lithium Home Battery", "13.5 kWh", "Instant backup power during grid blackouts with app controls."), ("EV Supercharger Integration", "Level 2 Fast", "Direct clean solar charging for electric vehicles."), ("Commercial Micro-Grid Systems", "Custom", "Zero-downtime decentralized solar for industrial warehouses.")]),
    ("site_cybersecurity_aegis_shield", "Aegis Zero-Trust Security", "AI Threat Telemetry and Cloud Infrastructure Defense", "cybersecurity", "az", "#070b14", "#6366f1", "#4f46e5", "#101626", "Space Grotesk", "Inter", "Deploy Platform", "Security Architecture", "platform", [("Identity & Behavioral IAM", "Zero Trust", "Continuous biometric and contextual risk authentication."), ("Cloud Workload Protection", "Kubernetes", "Real-time anomaly detection inside containerized clusters."), ("Automated Ransomware Killswitch", "Endpoint", "Kernel-level file encryption blocking in under 12 milliseconds."), ("24/7 Managed SOC Telemetry", "Enterprise", "Human and machine threat hunting monitoring 10M+ events/sec.")]),
    ("site_barbershop_iron_shears", "Iron & Shears Parlour", "Traditional Straight-Razor Shaves and Scissor Cuts", "barbershop", "is", "#1a1614", "#d97706", "#b45309", "#27211e", "Barlow Condensed", "Inter", "Book Appointment", "Grooming Menu", "services", [("Signature Scissor Cut & Style", "$45", "Precision haircut with hot towel neck shave and tonic massage."), ("Traditional Straight-Razor Shave", "$40", "Pre-shave essential oils, warm lather, and cold stone finish."), ("Beard Sculpting & Conditioning", "$30", "Crisp line definition, shears tapering, and beard butter treatment."), ("The Executive Combo Experience", "$70", "Full haircut, complete hot-lather shave, and facial scrub.")]),
    ("site_optometry_clarity_eye_studio", "Clarity Eye Studio", "Handcrafted Acetate Eyewear and Vision Health", "optometry", "ce", "#0c1b24", "#0ea5e9", "#0284c7", "#152c3b", "Outfit", "Inter", "Book Eye Exam", "Eyewear Collections", "collections", [("Titanium Featherweight Series", "Japan Made", "Laser-cut Japanese titanium frames weighing only 12 grams."), ("Vintage Block Acetate", "Italian Craft", "Bio-acetate cured for 6 months with custom 7-barrel hinges."), ("Advanced Wavefront Eye Exam", "Diagnostic", "Digital retina topography measuring optical aberrations."), ("Blue-Light Anti-Glare Optics", "Precision", "Scratch-resistant coated lenses engineered for heavy screen use.")]),
    ("site_catering_savory_roots", "Savory Roots Catering", "Organic Farm-to-Table Dining for Weddings and Galas", "catering", "sr", "#181c14", "#84cc16", "#65a30d", "#252b1f", "Cinzel", "Inter", "Request Tasting", "Seasonal Menus", "menus", [("Wild Morel & Duck Confit", "Canapés", "Crispy polenta bites with caramelized shallot marmalade."), ("Pan-Seared Pacific Halibut", "Mains", "Spring pea purée, roasted baby leeks, and Meyer lemon emulsion."), ("Braised Wagyu Beef Short Rib", "Mains", "Truffled parsnip mash with heritage blackberry demi-glace."), ("Cardamom Poached Pear Tart", "Dessert", "Almond sablé crust with whipped goat cheese mascarpone.")]),
    ("site_florist_botanica_atelier", "Botanica Floral Atelier", "Sculptural Botanical Arrangements and Events", "florist", "ba", "#181416", "#f43f5e", "#e11d48", "#272024", "Cinzel", "Inter", "Order Floral Design", "Signature Arrangements", "arrangements", [("The Ikebana Minimalist", "$120", "Architectural branches, single heirloom peonies, and raku ceramic vase."), ("Meadow Wildflower Centerpiece", "$180", "Lush garden roses, chamomile, Queen Anne's lace, and eucalyptus."), ("Monochrome Dahlia Cascade", "$210", "Deep burgundy dinnerplate dahlias with cascading amaranthus."), ("Bespoke Wedding Arch Installation", "Custom", "Floor-to-ceiling dried florals, pampas grass, and live orchids.")]),
    ("site_cleaning_spark_clean_co", "SparkClean Facilities", "Eco-Friendly Commercial & High-Rise Office Janitorial", "cleaning", "sc", "#081924", "#38bdf8", "#0284c7", "#102a3d", "Plus Jakarta Sans", "Inter", "Get Facility Quote", "Commercial Solutions", "services", [("Nightly Green Janitorial", "Daily Service", "Non-toxic HEPA vacuuming, surface sanitation, and waste sorting."), ("Commercial Carpet Deep Extraction", "Periodic", "Hot-water extraction neutralizing stains and deep allergens."), ("High-Rise Exterior Window Washing", "Specialized", "OSHA-compliant rope-access glass cleaning for glass facades."), ("Post-Construction Terminal Clean", "Turnkey", "Complete dust abatement and scrubbing ready for tenant handover.")]),
    ("site_logistics_vanguard_freight", "Vanguard Global Freight", "Air, Sea, and Rail Intermodal Supply Chain Logistics", "logistics", "vg", "#0a1324", "#2563eb", "#1d4ed8", "#121f3b", "Inter", "Inter", "Track Shipment", "Logistics Networks", "network", [("Ocean Cargo Container Shipping", "Full & LCL", "Global direct sailings with automated customs broker clearing."), ("Expedited Next-Flight Cargo", "Air Freight", "Guaranteed time-definite cargo charters and bonded warehousing."), ("Intermodal Cross-Country Rail", "Dry & Reefers", "Cost-effective temperature-controlled long-haul transport."), ("API Supply Chain Visibility", "Software", "Real-time satellite GPS tracking with container temperature alerts.")]),
    ("site_hotel_azure_cove_resort", "Azure Cove Beach Resort", "Secluded Oceanfront Villas with Private Infinity Pools", "hospitality", "ac", "#0b1b28", "#38bdf8", "#0284c7", "#132d42", "Cinzel", "Inter", "Reserve Suite", "Private Villas", "suites", [("Cliffside Sunset Pavilion", "2,400 sqft", "Panoramic sea views, private plunge pool, and butler service."), ("Overwater Coral Bungalow", "1,800 sqft", "Glass floor viewing panels and direct ladder into the lagoon."), ("The Presidential Beach Villa", "5,200 sqft", "4 private master suites, chef's kitchen, and private cabana."), ("Secluded Garden Sanctuary", "1,500 sqft", "Open-air outdoor stone rain showers and lush tropical garden.")]),
    ("site_gaming_nova_strike_studios", "Nova Strike Studios", "Indie Cyberpunk ARPG and Immersive Simulations", "gaming", "ns", "#080812", "#8b5cf6", "#7c3aed", "#131326", "Space Grotesk", "Inter", "Wishlist on Steam", "Active Games", "titles", [("Neon Syndicate: 2088", "ARPG", "Fast-paced isometric hack-and-slash with neural augmentation."), ("Void Walker Chronicles", "Roguelite", "Procedural gravity-shifting space derelict exploration."), ("Chrono Surge Tactics", "Turn-Based", "Deep deterministic combat with timeline-manipulating heroes."), ("Zero Horizon VR", "Simulation", "Photorealistic planetary atmospheric flight physics.")]),
    ("site_mental_health_mindful_pathways", "Mindful Pathways Therapy", "Integrative Psychotherapy and Emotional Healing", "therapy", "mp", "#121d1a", "#14b8a6", "#0d9488", "#1a2c27", "Cinzel", "Inter", "Book Initial Intake", "Clinical Specialties", "specialties", [("Cognitive Behavioral Therapy (CBT)", "Individual", "Evidence-based strategies to unlearn negative cognitive spirals."), ("EMDR Trauma Processing", "Specialized", "Bilateral eye movement desensitization for PTSD and trauma."), ("Couples Emotionally Focused Therapy", "Relationship", "De-escalating recurring conflict and rebuilding secure attachment."), ("Mindfulness Stress Reduction", "Group Series", "Breathwork and somatic techniques to regulate the nervous system.")]),
    ("site_recruiting_talent_forge", "TalentForge Search Partners", "Retained Executive and Engineering Talent Placement", "recruiting", "tf", "#0c1322", "#6366f1", "#4f46e5", "#131e36", "Plus Jakarta Sans", "Inter", "Hire Top Talent", "Search Practices", "practices", [("VP & C-Suite Executive Search", "Leadership", "Vetting board-level CTOs, CMOs, and VPs of Engineering."), ("AI & Machine Learning Researchers", "Specialized", "Connecting frontier labs with PhD scientists in PyTorch & CUDA."), ("Full-Stack Platform Engineers", "Growth Teams", "Senior distributed systems engineers and product developers."), ("Post-Offer Talent Onboarding", "Advisory", "Structured 90-day retention and executive coaching roadmaps.")]),
    ("site_print_shop_press_and_paper", "Press & Paper Studio", "Artisan Foil Stamping and Vintage Letterpress", "print_shop", "pp", "#1c1815", "#fbbf24", "#d97706", "#29241f", "Cinzel", "Inter", "Order Sample Pack", "Print Techniques", "techniques", [("Deep Impression Letterpress", "100% Cotton", "Hand-cranked 1950s Heidelberg presses creating deep tactile indentations."), ("Metallic Hot Foil Stamping", "Luxury Foil", "Mirrored gold, copper, and holographic foil fused with heat."), ("Precision Custom Die-Cutting", "Specialty", "Bespoke curves, rounded corners, and structural packaging sleeves."), ("Hand-Gilded Colored Edges", "Finishing", "Matte color and foil edge gilding on ultra-thick 600gsm stock.")]),
    ("site_winery_valle_di_pietra", "Valle di Pietra Estate", "Estate-Grown Biodynamic Wines and Hillside Vines", "winery", "vp", "#1c1116", "#be185d", "#9d174d", "#2b1b22", "Cinzel", "Inter", "Shop Allocations", "Current Vintages", "vintages", [("2021 Reserve Cabernet Sauvignon", "96 Points", "French oak aged 22 months. Notes of cassis, graphite, and violet."), ("2023 Estate Old-Vine Chardonnay", "94 Points", "Native yeast fermentation with crisp brioche and green apple minerality."), ("2022 Hillside Syrah", "95 Points", "Whole-cluster pressed with black peppercorn, blackberry, and smoked meat."), ("Late Harvest Botrytis Semillon", "Dessert", "Golden nectar featuring candied apricot, wild honeycomb, and bright acidity.")]),
    ("site_roofer_summit_shield_roofing", "Summit Shield Roofing", "Commercial Metal Roofing and Storm Restoration", "roofing", "ss", "#0f151e", "#f97316", "#ea580c", "#18212e", "Barlow Condensed", "Inter", "Get Free Roof Drone Scan", "Roofing Services", "services", [("Standing Seam Architectural Metal", "50yr Life", "Zero-exposed fastener metal panels resistant to 140mph winds."), ("Impact-Resistant Class 4 Shingles", "Storm Proof", "Hail-rated asphalt shingles qualifying for major insurance discounts."), ("Commercial TPO Flat Roof Systems", "Commercial", "Heat-welded waterproof membranes for energy-efficient flat roofs."), ("Emergency Tarping & Drone Inspection", "24/7 Response", "High-res thermal drone scans detecting subsurface water intrusion.")]),
    ("site_dentistry_pearl_dental_spa", "Pearl Aesthetic Dentistry", "Cosmetic Veneers, Clear Aligners, and Smile Makeovers", "dentistry", "pd", "#0a1924", "#06b6d4", "#0891b2", "#122838", "Outfit", "Inter", "Book Smile Consult", "Smile Treatments", "treatments", [("Handcrafted Porcelain Veneers", "Cosmetic", "Ultra-thin custom porcelain shells correcting shape and spacing."), ("Invisalign Clear Aligners", "Orthodontics", "Discreet orthodontic tooth straightening monitored via 3D scanning."), ("Laser Teeth Brightening", "Whitening", "Safe in-office laser activation brightening smiles up to 8 shades in 60m."), ("Guided Ceramic Dental Implants", "Restorative", "Biocompatible zirconia implants permanently replacing missing teeth.")]),
    ("site_plumbing_flow_pro_services", "FlowPro Master Plumbers", "24/7 Emergency Drain Clearing and Tankless Water Heaters", "plumbing", "fp", "#0e1824", "#0284c7", "#0369a1", "#152538", "Inter", "Inter", "Call Emergency Dispatch", "Plumbing Services", "services", [("24/7 Emergency Leak Repair", "Rapid Response", "Slab leak detection and burst pipe repairs dispatched in under 45m."), ("Hydro-Jetting & Drain Snaking", "Rooter", "High-pressure 4000 PSI water blasting eliminating stubborn grease & roots."), ("Tankless Water Heater Installation", "Energy Efficient", "Endless instant hot water with Navien and Rinnai gas units."), ("Trenchless Sewer Line Replacement", "No-Dig", "Cured-in-place pipe lining restoring cracked sewers without digging yards.")]),
    ("site_crypto_zenith_vault", "Zenith Institutional Vault", "Multi-Signature MPC Custody and On-Chain Staking", "crypto_custody", "zv", "#070b13", "#10b981", "#059669", "#111b2b", "Space Grotesk", "Inter", "Open Custody Account", "Security Architecture", "security", [("Threshold Multi-Party Computation (MPC)", "Hardware Isolation", "Eliminating single points of failure with distributed private key shares."), ("Segregated Institutional Cold Storage", "$500M Insured", "Bank-grade underground bunker vaults protected against physical & cyber coercion."), ("Native Proof-of-Stake Delegations", "High Yield", "Zero-slashing verified staking validators across Ethereum, Solana, and Cosmos."), ("Programmatic Automated Treasury API", "REST / Webhooks", "Whitelisted address routing with multi-tier managerial approval policies.")]),
    ("site_jewelry_aurelia_fine_gems", "Aurelia Ethical Fine Jewelry", "Lab-Grown Diamonds and Bespoke Recycled Gold Rings", "jewelry", "au", "#161317", "#e0b0ff", "#c084fc", "#241f26", "Cinzel", "Inter", "Design Custom Ring", "Fine Collections", "collections", [("The Solitaire Engagement Ring", "Certified VVS1", "Hand-set lab-grown oval diamond in 18k recycled yellow gold."), ("Pavé Diamond Tennis Bracelet", "4.5 Carats", "Continuous brilliant sparkle featuring lab diamonds set in platinum."), ("Eternity Wedding Bands", "Custom Fit", "Shared-prong brilliant cut diamonds calibrated for daily comfort."), ("Bespoke Bridal Commission", "One-of-a-Kind", "Collaborate directly with master goldsmiths from sketch to 3D wax model.")]),
    ("site_martial_arts_ronin_bjj", "Ronin Martial Arts Academy", "Brazilian Jiu-Jitsu, Muay Thai, and Submission Grappling", "martial_arts", "ro", "#121214", "#dc2626", "#b91c1c", "#1f1f24", "Barlow Condensed", "Inter", "Claim Free Trial Class", "Academy Programs", "programs", [("Adult Brazilian Jiu-Jitsu (Gi)", "All Levels", "Fundamental positional control, escapes, guard passing, and submissions."), ("No-Gi Submission Grappling", "Advanced", "Wrestling takedowns, leg locks, and rapid transitional pressure."), ("Authentic Muay Thai Striking", "Cardio & Technique", "Dutch kickboxing combinations, heavy bag circuits, and clinch sparring."), ("Youth Champions Martial Arts", "Ages 5–14", "Bully prevention, discipline, self-defense, and balance fundamentals.")]),
    ("site_bookstore_the_inkwell_shelf", "The Inkwell Rare Books", "First Edition Classics, Antiquarian Maps, and Literary Cafe", "bookstore", "iw", "#1c1613", "#d97706", "#b45309", "#2b221d", "Cinzel", "Inter", "Browse Catalog", "Rare Volumes", "volumes", [("F. Scott Fitzgerald First Editions", "1925 Scribner", "Original cloth bindings in remarkably preserved collector condition."), ("Hand-Illuminated Medieval Folios", "15th Century", "Vellum manuscripts painted with gold leaf and lapis lazuli pigments."), ("18th Century Cartography & Atlases", "Antique Maps", "Copperplate engraved hand-colored navigational charts of the Americas."), ("Signed Literary Modernism", "Rare Author Inscriptions", "Authenticated signatures from Hemingway, Woolf, Joyce, and Baldwin.")]),
    ("site_landscaping_terra_verve", "TerraVerve Landscapes", "Drought-Resilient Outdoor Living and Architectural Hardscapes", "landscaping", "tv", "#101d16", "#22c55e", "#16a34a", "#1b2e23", "Plus Jakarta Sans", "Inter", "Request Site Design", "Landscape Disciplines", "disciplines", [("Architectural Paver Patios & Firepits", "Hardscapes", "Permeable bluestone paving with integrated natural gas fire features."), ("Native Xeriscape Plantings", "Water-Wise", "Drought-tolerant ornamental grasses, lavender, and drip irrigation."), ("Custom Outdoor Kitchens & Pergolas", "Outdoor Living", "Built-in stainless grills, pizza ovens, and cedar timber shade structures."), ("Low-Voltage LED Landscape Lighting", "Illumination", "Subtle warm-wash illumination highlighting specimen trees and pathways.")]),
    ("site_auto_detailing_apex_ceramic", "Apex Ceramic Studio", "Multi-Stage Paint Correction and Self-Healing PPF Film", "detailing", "ap", "#0f0f12", "#ef4444", "#dc2626", "#1c1c21", "Barlow Condensed", "Inter", "Reserve Detail Slot", "Protection Packages", "packages", [("Two-Stage Paint Correction", "Mirror Finish", "Compounding and jeweling polish removing 90%+ of swirl marks and scratches."), ("9H Ceramic Nano-Coating", "5yr Warranty", "Ultra-hydrophobic ceramic glass coating repelling water, dirt, and UV rays."), ("Full Front Paint Protection Film (PPF)", "Self-Healing", "Optically clear polyurethane shield protecting bumper, hood, and mirrors."), ("Concourse Interior Restoration", "Deep Detail", "Steam cleaning, leather ceramic protection, and ozone odor elimination.")]),
    ("site_insurance_shield_harbor", "Shield Harbor Marine Insurance", "Commercial Hull, Superyacht, and Cargo Risk Protection", "insurance", "sh", "#0a1626", "#38bdf8", "#0284c7", "#12253d", "Merriweather", "Inter", "Request Marine Quote", "Coverage Policies", "policies", [("Luxury Yacht Hull & Machinery", "Agreed Value", "Comprehensive worldwide navigation coverage including tender and crew liability."), ("Commercial Cargo in Transit", "Ocean & Air", "All-risk cargo protection covering warehouse-to-warehouse international freight."), ("Marina & Shipyard Operator Liability", "Commercial", "Pollution indemnity, ship repairer legal liability, and storm surge damage."), ("Crew Healthcare & P&I Coverage", "Protection & Indemnity", "Medical evacuation and maritime employer liability for international crews.")]),
    ("site_pottery_earth_and_kiln", "Earth & Kiln Studio", "Handmade Functional Stoneware and Pottery Classes", "pottery", "ek", "#191512", "#f59e0b", "#d97706", "#27211d", "Cinzel", "Inter", "Book Potter's Wheel Class", "Studio Offerings", "offerings", [("Beginner Wheel Throwing Workshop", "3hr Intensive", "Hands-on guidance centering clay, opening, and pulling cylinder forms."), ("Handmade Stoneware Tableware", "Ceramic Shop", "Microwave and dishwasher-safe speckled clay dinner plates and mugs."), ("Wood-Fired Anagama Kiln Residencies", "Master Class", "48-hour continuous wood firings creating natural ash glaze patinas."), ("Monthly Open Studio Membership", "24/7 Access", "Dedicated shelf space, studio glazes, and unlimited high-fire kiln firings.")]),
    ("site_moving_smooth_move_logistics", "SmoothMove Elite Movers", "White-Glove Residential Moving and Climate-Controlled Storage", "moving", "sm", "#0d1824", "#0ea5e9", "#0284c7", "#142538", "DM Sans", "Inter", "Get Instant Moving Estimate", "Moving Services", "services", [("White-Glove Luxury Moving", "Full Service", "Full packing with custom wooden crating for fine art, mirrors, and pianos."), ("Interstate Long-Distance Moving", "Coast-to-Coast", "Guaranteed direct delivery dates without multi-client truck sharing."), ("Climate-Controlled Vault Storage", "Secure Storage", "Private wooden vault containers inside 24/7 guarded, humidity-regulated hubs."), ("Office & Commercial Relocation", "Business Moving", "Weekend technology disconnect, rolling server racks, and desk reassembly.")]),
    ("site_apparel_terra_wear", "TerraWear Sustainable Activewear", "Performance Sportswear from Regenerated Ocean Plastics", "apparel", "tw", "#101814", "#10b981", "#059669", "#182620", "Outfit", "Inter", "Shop Sustainable Drop", "Core Performance Gear", "collection", [("Aero-Weave Running Shorts", "$68", "Lightweight four-way stretch recycled poly with anti-chafing compression liner."), ("Thermal Meridian Training Hoodie", "$118", "Brushed organic bamboo fleece providing thermoregulation and odor resistance."), ("High-Impact Precision Leggings", "$88", "Squat-proof compression knit crafted from retrieved deep-ocean fishing nets."), ("Weatherproof Summit Shell Jacket", "$198", "Breathable 3-layer waterproof membrane made with 100% recycled nylon.")]),
    ("site_museum_metropolitan_modern", "Metropolitan Digital Art Hall", "Immersive Audio-Visual Exhibits and Interactive Holography", "museum", "mm", "#080711", "#d946ef", "#c026d3", "#131024", "Space Grotesk", "Inter", "Reserve Timed Entry", "Current Exhibitions", "exhibitions", [("Infinite Horizons: Light in Void", "Gallery 01", "Laser light refractions creating floating geometric optical illusions."), ("Synthetic Dreams & Artificial Mind", "Gallery 02", "Autonomous generative video environments reacting to visitor heartbeats."), ("Resonance: Spatial Sound Labyrinth", "Gallery 03", "128-speaker ambisonic acoustic chambers exploring vibrational meditation."), ("The Quantum Canvas Experience", "Gallery 04", "Interactive touchscreens allowing visitors to paint with fluid particle physics.")]),
    ("site_pest_control_eco_guard", "EcoGuard Botanical Defense", "Non-Toxic Pest Exclusion and Organic Perimeter Defense", "pest_control", "eg", "#0f1c14", "#4ade80", "#22c55e", "#192e21", "Plus Jakarta Sans", "Inter", "Schedule Inspection", "Pest Solutions", "solutions", [("Botanical Barrier Home Perimeter", "Child & Pet Safe", "Organic essential oil barrier keeping ants, spiders, and roaches out."), ("Structural Rodent Proofing", "Permanent", "Sealing foundational entry points with heavy gauge steel mesh & copper wire."), ("Eco-Friendly Termite Interception", "Monitoring", "Subterranean baiting stations eliminating colonies without pumping chemical poisons."), ("Mosquito & Tick Yard Misting", "Seasonal", "Garlic and thyme oil micro-fogging drastically cutting biting insect counts.")]),
    ("site_charter_blue_horizon_sailing", "Blue Horizon Yacht Charters", "Private Crewed Catamarans and Virgin Island Sailing", "sailing", "bh", "#081729", "#00d2d3", "#00b4b5", "#10233b", "Cinzel", "Inter", "Book Yacht Charter", "Charter Fleet", "fleet", [("Lagoon 52 Luxury Catamaran", "Up to 8 Guests", "Air-conditioned staterooms, onboard chef, tender boat, and paddleboards."), ("Sunseeker 65 Sport Yacht", "Day Charters", "High-speed cruising with flybridge sunbeds and hydraulic swim platform."), ("Bavaria 46 Monohull Cruiser", "Bareboat", "Pure sailing performance equipped with twin helms and Raymarine radar."), ("All-Inclusive VIP Island Package", "Weekly Charter", "Custom gourmet dining, open bar, provisioning, and professional captain.")]),
    ("site_tutoring_quant_masters", "QuantMasters Academy", "Olympiad Math, Physics, and Competitive Algorithmic Coding", "tutoring", "qm", "#091224", "#6366f1", "#4f46e5", "#121e38", "Space Grotesk", "Inter", "Take Diagnostic Assessment", "Academy Tracks", "curriculum", [("Mathematical Olympiad Prep", "AMC 10/12 & AIME", "Number theory, combinatorics, and synthetic Euclidean geometry proofs."), ("AP & Competitive Physics", "Mechanics & E&M", "Calculus-based physics mastery with experimental problem-solving labs."), ("USACO Algorithmic Coding", "Silver to Platinum", "Dynamic programming, graph algorithms, and segment trees in C++ and Python."), ("Ivy League STEM Admissions Mentorship", "Advisory", "Guiding high schoolers in independent peer-reviewed STEM research publications.")]),
    ("site_coffee_roasters_elevation_roast", "Elevation Roastery", "High-Altitude Volcanic Specialty Coffee and Tasting Flights", "coffee", "er", "#191310", "#ea580c", "#c2410c", "#291f1a", "Barlow Condensed", "Inter", "Shop Whole Bean", "Single-Origin Lots", "coffees", [("Ethiopia Yirgacheffe Natural", "$22 / 12oz", "Heirloom varietal with jasmine floral aroma, bergamot, and sweet blueberry."), ("Colombia Huila Pink Bourbon", "$24 / 12oz", "Anaerobic honey process yielding crisp guava, passionfruit, and panela sugar."), ("Guatemala Antigua Washed", "$20 / 12oz", "Volcanic soil cultivation with dark chocolate, candied almond, and orange peel."), ("Nitro Cold Brew Keg Service", "Commercial", "Creamy draft nitro cold brew delivered weekly to modern tech offices.")]),
    ("site_security_sentinel_patrol", "Sentinel Protective Services", "Autonomous Drone Surveillance and Executive Close Protection", "security", "sp", "#0a111a", "#eab308", "#ca8a04", "#132130", "Inter", "Inter", "Request Security Assessment", "Protection Tiers", "tiers", [("Autonomous Thermal Drone Patrols", "Perimeter", "Automated scheduled drone flyovers with AI optical intrusion alerts."), ("Executive Close Protection Details", "Armed Escort", "Former military special forces bodyguards for dignitaries and executives."), ("Access Control & CCTV Integration", "Smart Systems", "Biometric facial scanning, turnstile control, and cloud-monitored video."), ("Rapid Armed Response Vehicles", "24/7 Mobile", "Guaranteed under-10-minute on-site dispatch during triggered alarm events.")]),
    ("site_tattoo_sacred_ink_collective", "Sacred Ink Tattoo Studio", "Fine-Line Micro Realism and Custom Botanical Blackwork", "tattoo", "si", "#111114", "#d4d4d8", "#a1a1aa", "#1c1c21", "Cinzel", "Inter", "Submit Tattoo Inquiry", "Resident Artists", "artists", [("Master Kai: Micro Realism", "Portraits & Animals", "Photorealistic wildlife and classical sculpture tattoos rendered with fine needles."), ("Elena S: Botanical Fine-Line", "Florals & Flora", "Delicate anatomical botanical illustrations with soft charcoal stippling."), ("Marcus Cole: Japanese Neo-Trad", "Dragons & Waves", "Bold dynamic waves, irezumi mythology, and sweeping sleeve compositions."), ("Sterile Single-Use Studio Standards", "Hospital Grade", "Hospital-grade autoclaves, 100% vegan organic inks, and medical aftercare.")]),
    ("site_cinema_the_starlight_indie", "The Starlight Picturehouse", "35mm Analog Screenings, Cult Cinema, and Cocktail Bar", "cinema", "sl", "#140c11", "#f43f5e", "#e11d48", "#24151e", "Cinzel", "Inter", "Reserve Cinema Seats", "Now Showing", "films", [("2001: A Space Odyssey (70mm)", "Kubrick Classic", "Original 70mm roadshow print with restored six-track magnetic audio."), ("Blade Runner: The Final Cut", "Sci-Fi Cult", "Neon-drenched cyberpunk masterpiece presented with custom bourbon cocktails."), ("Chungking Express (35mm)", "Wong Kar-wai", "Vibrant 1994 Hong Kong romance film screened on original 35mm stock."), ("Midnight Shadow Horror Club", "Double Feature", "Late-night analog screenings of 1970s Italian Giallo and psychological horror.")]),
    ("site_bakery_gluten_free_crumbles", "Crumbles Dedicated Bakery", "100% Certified Gluten-Free Breads and Celebration Cakes", "gf_bakery", "cb", "#191510", "#d97706", "#b45309", "#27211a", "Outfit", "Inter", "Order Custom Cake", "Daily Gluten-Free Menu", "menu", [("Artisan Artisan Sourdough Loaf", "$11.00", "Certified celiac safe sourdough with crunchy blistered crust and soft crumb."), ("Salted Caramel Celebration Cake", "$55.00", "Fluffy vanilla sponge layered with house-made salted caramel and buttercream."), ("Cinnamon Pecan Sticky Rolls", "$5.50", "Warm brioche-style rolls baked with maple glaze and toasted Georgia pecans."), ("Savory Cheddar Chive Scones", "$4.75", "Flaky aged sharp cheddar scones brushed with melted garlic herb butter.")]),
    ("site_event_space_the_foundry_loft", "The Foundry Urban Loft", "Historic 1920s Brick Warehouse Wedding and Gala Venue", "venue", "fo", "#141414", "#d4af37", "#b89628", "#222222", "Cinzel", "Inter", "Schedule Venue Tour", "Event Spaces", "spaces", [("The Main Grand Brick Atrium", "Up to 350 Guests", "Original 30ft timber ceilings, exposed brick arches, and iron chandeliers."), ("The Open-Air Rooftop Terrace", "Up to 150 Guests", "Panoramic city skyline views with fire pits and built-in copper bar."), ("Bridal Dressing Suite", "Private Lounge", "Full-length lighted mirrors, velvet furnishings, and private champagne bar."), ("Chef's Commercial Prep Kitchen", "Catering Ready", "Industrial stainless steel prep stations and walk-in refrigeration for caterers.")]),
    ("site_medtech_pulse_biometrics", "Pulse Biometrics Systems", "Wearable Continuous Biomarker and Glucose Telemetry", "medtech", "pb", "#06101c", "#06b6d4", "#0891b2", "#0f1e30", "Space Grotesk", "Inter", "Request Clinical Trial", "Diagnostic Hardware", "hardware", [("Non-Invasive Micro-Needle Sensor", "Clinical Grade", "Continuous interstitial glucose and lactate tracking with 14-day wear time."), ("Sub-Second Bluetooth Sync", "Mobile App", "Real-time biometric telemetry stream sent directly to patient and physician apps."), ("AI Metabolic Trend Analysis", "Predictive", "Algorithms identifying hypoglycemic dips and cardiovascular spikes hours early."), ("HIPAA Compliant Cloud Dashboard", "EHR Integrated", "Direct HL7 FHIR sync into Epic, Cerner, and hospital electronic health systems.")])
]

# Convert ADDITIONAL_DOMAINS_DATA into full domain dicts
for entry in ADDITIONAL_DOMAINS_DATA:
    d_id, d_name, d_tagline, d_type, d_prefix, d_prim, d_acc, d_acc_hov, d_surf, d_head, d_body, d_cta, d_sec_name, d_sec_id, d_items = entry
    DOMAINS_B4.append({
        "id": d_id,
        "name": d_name,
        "tagline": d_tagline,
        "type": d_type,
        "prefix": d_prefix,
        "primary": d_prim,
        "accent": d_acc,
        "accent_hover": d_acc_hov,
        "surface": d_surf,
        "heading_font": d_head,
        "body_font": d_body,
        "cta": d_cta,
        "hero_sub": f"Dedicated to {d_tagline.lower()}, delivering highest-caliber standards, transparent pricing, and world-class client service.",
        "section_name": d_sec_name,
        "section_id": d_sec_id,
        "items": [{"title": title, "tag": tag, "desc": desc} for title, tag, desc in d_items],
        "contact": {
            "address": "100 Grand Avenue, Suite 400, Metropolitan City, NY 10001",
            "phone": "+1 (800) 555-0199",
            "email": f"contact@{d_id.replace('site_', '').replace('_', '')}.com",
            "hours": "Mon–Fri: 8am–6pm | Sat: 9am–2pm"
        }
    })


def build_brief_xml(d):
    items_xml = []
    for item in d["items"]:
        items_xml.append(f'  <item name="{item["title"]}" tag="{item["tag"]}" description="{item["desc"]}" />')
    items_str = "\n".join(items_xml)
    
    return f"""<content_brief>
  <business_name>{d["name"]}</business_name>
  <tagline>{d["tagline"]}</tagline>
  <business_type>{d["type"]}</business_type>
  <primary_color>{d["primary"]}</primary_color>
  <accent_color>{d["accent"]}</accent_color>
  <font_heading>{d["heading_font"]}</font_heading>
  <font_body>{d["body_font"]}</font_body>
  <sections>header, hero, {d["section_id"]}, footer</sections>
{items_str}
  <contact>
    <address>{d["contact"]["address"]}</address>
    <phone>{d["contact"]["phone"]}</phone>
    <email>{d["contact"]["email"]}</email>
    <hours>{d["contact"]["hours"]}</hours>
  </contact>
</content_brief>"""


def _hex_to_rgb(hex_str: str):
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if len(hex_str) >= 6:
        return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return (15, 23, 42)

def get_domain_section_desc(d: dict) -> str:
    """Generates authentic, domain-specific section introductory copy without generic filler."""
    t = d.get("type", "").lower()
    name = d.get("name", "")
    sec_name = d.get("section_name", "")
    
    if any(k in t for k in ("bakery", "coffee", "roast", "food", "cafe", "pastry")):
        return "Handcrafted daily in small batches using single-origin harvests, heritage grains, and traditional fermentation methods."
    elif any(k in t for k in ("law", "legal", "counsel", "litigation")):
        return "Strategic counsel tailored to safeguard enterprise value, proprietary intellectual property, and complex commercial agreements."
    elif any(k in t for k in ("database", "saas", "tech", "cloud", "security", "telemetry", "dev", "api", "ai")):
        return "High-throughput architecture and fault-tolerant data pipelines engineered for mission-critical production scale."
    elif any(k in t for k in ("oncology", "medical", "health", "biometric", "clinic", "therapy", "dental", "optometry")):
        return "Clinical-grade diagnostics, patient telemetry, and rigorous therapeutic protocols adhering to strict medical standards."
    elif any(k in t for k in ("jewelry", "luxury", "watch", "craft", "keyboards", "leather", "tailor")):
        return "Meticulously hand-finished with exceptional precious materials, exacting tolerances, and timeless design proportions."
    elif any(k in t for k in ("insurance", "cargo", "logistics", "freight", "marine")):
        return "Comprehensive risk mitigation and worldwide supply chain protection backed by rated underwriting syndicates."
    elif any(k in t for k in ("sailing", "charter", "yacht", "resort", "hotel", "hospitality", "safari")):
        return "Curated private expeditions and luxury accommodations designed for unmatched privacy and natural immersion."
    elif any(k in t for k in ("fitness", "bouldering", "climbing", "martial_arts", "apparel", "sport")):
        return "Technical gear, standardized benchmark walls, and movement training engineered for peak physical demands."
    elif any(k in t for k in ("architecture", "interior", "rendering", "sound", "audio", "cinema", "museum", "art", "pottery")):
        return "Site-specific spatial compositions uniting acoustic precision, authentic materials, and bold geometric form."
    else:
        return f"Explore our dedicated {sec_name.lower()} developed to provide verified quality and measurable results for {name} clients."

def build_diverse_domain_trajectory(d: dict, domain_idx: int = 0) -> dict:
    brief_xml = build_brief_xml(d)
    p = d["prefix"]
    sec_ts_name = d["section_name"].replace(" ", "").replace("&", "").replace("'", "").replace("-", "")
    items_json = json.dumps(d["items"], indent=2)
    sec_desc = get_domain_section_desc(d)
    style_variant = domain_idx % 4

    r_prim, g_prim, b_prim = _hex_to_rgb(d["primary"])
    r_acc, g_acc, b_acc = _hex_to_rgb(d["accent"])

    # ── Turn 1: Header ──────────────────────────────────────────────────────────
    initial_user = (
        "Build a complete website for the following brief.\n\n"
        f"{brief_xml}\n\n"
        "You will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
        f"FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the business name/logo on the left, "
        f"navigation links (Home, {d['section_name']}, Contact) on the right, plus '{d['cta']}' CTA button. "
        "Files: src/components/Header.tsx + src/components/Header.css"
    )

    t1_thought = thought(
        f"I'll start by crafting the Header for {d['name']}. "
        f"It needs to reflect the {d['type']} brand identity: deep background ({d['primary']}) with crisp contrast, "
        f"the elegant {d['heading_font']} typography for the wordmark, and the signature {d['accent']} accent for the CTA button. "
        "I'll also implement a scroll listener to trigger glassmorphism and subtle border illumination on scroll."
    )

    t1_tsx = f"""import React, {{ useState, useEffect }} from 'react';
import './Header.css';

export function Header() {{
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {{
    const onScroll = () => setScrolled(window.scrollY > 15);
    window.addEventListener('scroll', onScroll, {{ passive: true }});
    return () => window.removeEventListener('scroll', onScroll);
  }}, []);

  return (
    <header className={{`{p}-header${{scrolled ? ' {p}-header--scrolled' : ''}}`}} role="banner">
      <div className="{p}-header__inner">
        <a href="#" className="{p}-header__logo" aria-label="{d['name']} Home">
          {d['name']}
        </a>

        <nav className="{p}-header__nav" aria-label="Main Navigation">
          <a href="#hero" className="{p}-header__link">Home</a>
          <a href="#{d['section_id']}" className="{p}-header__link">{d['section_name']}</a>
          <a href="#footer" className="{p}-header__link">Contact</a>
        </nav>

        <div className="{p}-header__actions">
          <a href="mailto:{d['contact']['email']}" className="{p}-header__cta">
            {d['cta']}
          </a>
          <button
            type="button"
            className="{p}-header__toggle"
            aria-label="Toggle navigation menu"
            aria-expanded={{menuOpen}}
            onClick={{() => setMenuOpen(!menuOpen)}}
          >
            <span className="{p}-header__bar" />
            <span className="{p}-header__bar" />
          </button>
        </div>
      </div>

      {{menuOpen && (
        <div className="{p}-header__mobile-menu">
          <a href="#hero" onClick={{() => setMenuOpen(false)}}>Home</a>
          <a href="#{d['section_id']}" onClick={{() => setMenuOpen(false)}}>{d['section_name']}</a>
          <a href="#footer" onClick={{() => setMenuOpen(false)}}>Contact</a>
        </div>
      )}}
    </header>
  );
}}
"""

    t1_css = f""".{p}-header {{
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  background: rgba({r_prim}, {g_prim}, {b_prim}, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}}

.{p}-header--scrolled {{
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
  border-bottom-color: {d['accent']};
}}

.{p}-header__inner {{
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}}

.{p}-header__logo {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: #fafafa;
  text-decoration: none;
  letter-spacing: -0.01em;
}}

.{p}-header__nav {{
  display: flex;
  gap: 2rem;
  align-items: center;
}}

.{p}-header__link {{
  color: #a1a1aa;
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 500;
  transition: color 0.2s ease;
}}

.{p}-header__link:hover {{
  color: {d['accent']};
}}

.{p}-header__actions {{
  display: flex;
  align-items: center;
  gap: 1rem;
}}

.{p}-header__cta {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.6rem 1.4rem;
  background: {d['accent']};
  color: #0c0d12;
  font-size: 0.88rem;
  font-weight: 700;
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.2s ease;
}}

.{p}-header__cta:hover {{
  background: {d['accent_hover']};
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba({r_acc}, {g_acc}, {b_acc}, 0.35);
}}

.{p}-header__toggle {{
  display: none;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  flex-direction: column;
  gap: 5px;
}}

.{p}-header__bar {{
  display: block;
  width: 22px;
  height: 2px;
  background: #fafafa;
  border-radius: 1px;
}}

.{p}-header__mobile-menu {{
  display: none;
}}

@media (max-width: 768px) {{
  .{p}-header__nav {{ display: none; }}
  .{p}-header__toggle {{ display: flex; }}
  .{p}-header__mobile-menu {{
    display: flex;
    flex-direction: column;
    background: {d['primary']};
    padding: 1.5rem 2rem;
    gap: 1.25rem;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }}
  .{p}-header__mobile-menu a {{
    color: #fafafa;
    text-decoration: none;
    font-size: 1.1rem;
    font-weight: 500;
  }}
}}
"""

    t1_action = write_site("src/components/Header.tsx", t1_tsx, "src/components/Header.css", t1_css)

    # ── Turn 2: Hero (Variant-driven structure) ──────────────────────────────
    t2_user = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        "Write the Hero section: a responsive banner tailored to the brand with the tagline as h1, "
        f"subheading, and dual CTA buttons. Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    if style_variant == 0:
        # Style 0: Split-Hero (Left content, Right floating showcase card)
        t2_thought = thought(
            f"Header was approved. Now I'll create a responsive two-column Split Hero section for {d['name']}. "
            f"The left column renders an editorial category badge, headline in {d['heading_font']} typography, "
            f"and dual CTAs. The right column houses a floating showcase card featuring primary specifications."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--split" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__inner {p}-hero__inner--split">
        <div className="{p}-hero__content">
          <div className="{p}-hero__badge">
            <span>{d['type'].replace('_', ' ').upper()} // SIGNATURE</span>
          </div>
          <h1 id="{p}-hero-title" className="{p}-hero__title">
            {d['tagline']}
          </h1>
          <p className="{p}-hero__subtitle">
            {d['hero_sub']}
          </p>
          <div className="{p}-hero__actions">
            <a href="mailto:{d['contact']['email']}" className="{p}-hero__btn-primary">
              {d['cta']}
            </a>
            <a href="#{d['section_id']}" className="{p}-hero__btn-secondary">
              View {d['section_name']}
            </a>
          </div>
        </div>

        <div className="{p}-hero__showcase">
          <div className="{p}-hero__card">
            <div className="{p}-hero__card-tag">Signature Highlight</div>
            <h3 className="{p}-hero__card-title">{d['items'][0]['title']}</h3>
            <p className="{p}-hero__card-desc">{d['items'][0]['desc']}</p>
            <div className="{p}-hero__card-meta">
              <span className="{p}-hero__card-pill">{d['items'][0]['tag']}</span>
              <a href="#{d['section_id']}" className="{p}-hero__card-link">Explore Details &rarr;</a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 85vh;
  display: flex;
  align-items: center;
  background: {d['primary']};
  padding: 5rem 2rem;
}}

.{p}-hero__inner--split {{
  max-width: 1240px;
  margin: 0 auto;
  width: 100%;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 3.5rem;
  align-items: center;
}}

.{p}-hero__badge {{
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {d['accent']};
  margin-bottom: 1.25rem;
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.2rem, 4.5vw, 3.4rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.15;
  margin: 0 0 1.2rem;
  letter-spacing: -0.02em;
}}

.{p}-hero__subtitle {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0 0 2rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: {d['accent']};
  color: #0c0d12;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-primary:hover {{
  background: {d['accent_hover']};
  transform: translateY(-1px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fafafa;
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-secondary:hover {{
  background: rgba(255, 255, 255, 0.1);
}}

.{p}-hero__card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 2.2rem;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
}}

.{p}-hero__card-tag {{
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {d['accent']};
  margin-bottom: 0.75rem;
}}

.{p}-hero__card-title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.3rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-hero__card-desc {{
  font-size: 0.92rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0 0 1.5rem;
}}

.{p}-hero__card-meta {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-hero__card-pill {{
  background: rgba({r_acc}, {g_acc}, {b_acc}, 0.15);
  color: {d['accent']};
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}}

.{p}-hero__card-link {{
  color: {d['accent']};
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
}}

@media (max-width: 900px) {{
  .{p}-hero__inner--split {{
    grid-template-columns: 1fr;
    gap: 2.5rem;
  }}
}}
"""

    elif style_variant == 1:
        # Style 1: Editorial Centered Hero with Credibility Metric Strip
        t2_thought = thought(
            f"Header was approved. Now I'll create an editorial centered Hero section for {d['name']} with high-impact "
            f"{d['heading_font']} typography, paired with an integrated three-metric credibility strip below the CTAs."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--editorial" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__inner">
        <div className="{p}-hero__pill">
          <span>VERIFIED STANDARDS &bull; {d['name'].upper()}</span>
        </div>

        <h1 id="{p}-hero-title" className="{p}-hero__title">
          {d['tagline']}
        </h1>

        <p className="{p}-hero__subtitle">
          {d['hero_sub']}
        </p>

        <div className="{p}-hero__actions">
          <a href="mailto:{d['contact']['email']}" className="{p}-hero__btn-primary">
            {d['cta']}
          </a>
          <a href="#{d['section_id']}" className="{p}-hero__btn-secondary">
            Browse {d['section_name']}
          </a>
        </div>

        <div className="{p}-hero__metrics">
          <div className="{p}-metric-item">
            <span className="{p}-metric-val">100%</span>
            <span className="{p}-metric-lbl">Direct Sourcing</span>
          </div>
          <div className="{p}-metric-item">
            <span className="{p}-metric-val">24/7</span>
            <span className="{p}-metric-lbl">Client Support</span>
          </div>
          <div className="{p}-metric-item">
            <span className="{p}-metric-val">&lt; 15m</span>
            <span className="{p}-metric-lbl">Response Time</span>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: {d['primary']};
  padding: 5rem 2rem;
  text-align: center;
}}

.{p}-hero__inner {{
  max-width: 840px;
  margin: 0 auto;
}}

.{p}-hero__pill {{
  display: inline-block;
  padding: 0.4rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 9999px;
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin-bottom: 1.5rem;
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.4rem, 5vw, 3.8rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.12;
  margin: 0 0 1.25rem;
  letter-spacing: -0.02em;
}}

.{p}-hero__subtitle {{
  font-size: 1.1rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0 auto 2.5rem;
  max-width: 680px;
}}

.{p}-hero__actions {{
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 3.5rem;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: {d['accent']};
  color: #0c0d12;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-primary:hover {{
  background: {d['accent_hover']};
  transform: translateY(-1px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fafafa;
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__metrics {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-metric-item {{
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}}

.{p}-metric-val {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.8rem;
  font-weight: 800;
  color: #fafafa;
}}

.{p}-metric-lbl {{
  font-size: 0.85rem;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

@media (max-width: 640px) {{
  .{p}-hero__metrics {{ grid-template-columns: 1fr; gap: 1.25rem; }}
}}
"""

    elif style_variant == 2:
        # Style 2: Angular Minimalist Hero with Geometric Divider
        t2_thought = thought(
            f"Header was approved. For {d['name']}, I'll implement an angular architectural Hero section featuring a clean "
            f"geometric divider, high-contrast kicker text, and sharp focus on the primary value proposition."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--angular" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__divider" aria-hidden="true" />
      <div className="{p}-hero__inner">
        <p className="{p}-hero__kicker">Precision Engineering // {d['type'].replace('_', ' ').title()}</p>

        <h1 id="{p}-hero-title" className="{p}-hero__title">
          {d['tagline']}
        </h1>

        <p className="{p}-hero__subtitle">
          {d['hero_sub']}
        </p>

        <div className="{p}-hero__actions">
          <a href="mailto:{d['contact']['email']}" className="{p}-hero__btn-solid">
            {d['cta']}
          </a>
          <a href="#{d['section_id']}" className="{p}-hero__btn-outline">
            Direct Overview
          </a>
        </div>
      </div>
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 82vh;
  display: flex;
  align-items: center;
  background: {d['primary']};
  padding: 5.5rem 2rem;
  overflow: hidden;
}}

.{p}-hero__divider {{
  position: absolute;
  top: 0;
  right: 0;
  width: 45%;
  height: 100%;
  background: rgba({r_acc}, {g_acc}, {b_acc}, 0.03);
  clip-path: polygon(25% 0, 100% 0, 100% 100%, 0% 100%);
  pointer-events: none;
}}

.{p}-hero__inner {{
  max-width: 900px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}}

.{p}-hero__kicker {{
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: {d['accent']};
  margin: 0 0 1.25rem;
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.3rem, 4.8vw, 3.6rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.15;
  margin: 0 0 1.25rem;
  letter-spacing: -0.02em;
}}

.{p}-hero__subtitle {{
  font-size: 1.1rem;
  color: #a1a1aa;
  line-height: 1.7;
  margin: 0 0 2.25rem;
  max-width: 720px;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
}}

.{p}-hero__btn-solid {{
  display: inline-flex;
  align-items: center;
  padding: 0.9rem 2rem;
  background: {d['accent']};
  color: #0c0d12;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-solid:hover {{
  background: {d['accent_hover']};
  transform: translateY(-1px);
}}

.{p}-hero__btn-outline {{
  display: inline-flex;
  align-items: center;
  padding: 0.9rem 2rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fafafa;
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-outline:hover {{
  border-color: {d['accent']};
  color: {d['accent']};
}}
"""

    else:
        # Style 3: Framed Showcase Hero Container
        t2_thought = thought(
            f"Header was approved. I will create a modern framed Hero section for {d['name']} featuring a glassmorphic "
            f"container border, brand badges, and responsive action triggers."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--framed" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__frame">
        <div className="{p}-hero__badge">
          <span>CURATED PORTFOLIO &bull; {d['name'].upper()}</span>
        </div>

        <h1 id="{p}-hero-title" className="{p}-hero__title">
          {d['tagline']}
        </h1>

        <p className="{p}-hero__subtitle">
          {d['hero_sub']}
        </p>

        <div className="{p}-hero__actions">
          <a href="mailto:{d['contact']['email']}" className="{p}-hero__btn-primary">
            {d['cta']}
          </a>
          <a href="#{d['section_id']}" className="{p}-hero__btn-secondary">
            Explore {d['section_name']}
          </a>
        </div>
      </div>
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: {d['primary']};
  padding: 5rem 2rem;
}}

.{p}-hero__frame {{
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  padding: 4rem 3rem;
  background: rgba({int(r_prim * 0.85)}, {int(g_prim * 0.85)}, {int(b_prim * 0.85)}, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(16px);
  text-align: center;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
}}

.{p}-hero__badge {{
  display: inline-block;
  padding: 0.35rem 0.9rem;
  background: rgba({r_acc}, {g_acc}, {b_acc}, 0.12);
  color: {d['accent']};
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin-bottom: 1.5rem;
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.3rem, 4.5vw, 3.6rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.15;
  margin: 0 0 1.25rem;
  letter-spacing: -0.02em;
}}

.{p}-hero__subtitle {{
  font-size: 1.1rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0 auto 2.5rem;
  max-width: 700px;
}}

.{p}-hero__actions {{
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: {d['accent']};
  color: #0c0d12;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-primary:hover {{
  background: {d['accent_hover']};
  transform: translateY(-1px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 1.8rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fafafa;
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

@media (max-width: 640px) {{
  .{p}-hero__frame {{ padding: 2.5rem 1.5rem; }}
}}
"""

    t2_action = write_site("src/components/Hero.tsx", t2_tsx, "src/components/Hero.css", t2_css)

    # ── Turn 3: Core Section / Catalog (Variant-driven structure) ─────────────
    t3_user = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        f"Write the '{sec_ts_name}' component ({d['section_name']}): display the core offerings/features. "
        f"Files: src/components/{sec_ts_name}.tsx + src/components/{sec_ts_name}.css"
    )

    if style_variant == 0:
        # Style 0: Balanced 3-column / Auto-fit Grid
        t3_thought = thought(
            f"Now creating the core content component '{sec_ts_name}' for {d['name']}. "
            f"I'll lay out the {len(d['items'])} items in a balanced multi-column responsive grid. "
            f"Each card features authentic domain copy, category badge, and an interactive action link."
        )
        t3_tsx = f"""import React from 'react';
import './{sec_ts_name}.css';

interface Item {{
  title: string;
  tag: string;
  desc: string;
}}

const ITEMS: Item[] = {items_json};

export function {sec_ts_name}() {{
  return (
    <section className="{p}-catalog" id="{d['section_id']}" aria-labelledby="{p}-catalog-title">
      <div className="{p}-catalog__inner">
        <div className="{p}-catalog__header">
          <p className="{p}-catalog__eyebrow">Signature Collection</p>
          <h2 id="{p}-catalog-title" className="{p}-catalog__title">
            {d['section_name']}
          </h2>
          <p className="{p}-catalog__desc">
            {sec_desc}
          </p>
        </div>

        <div className="{p}-catalog__grid">
          {{ITEMS.map((item) => (
            <article key={{item.title}} className="{p}-card">
              <div className="{p}-card__top">
                <span className="{p}-card__tag">{{item.tag}}</span>
              </div>
              <h3 className="{p}-card__title">{{item.title}}</h3>
              <p className="{p}-card__desc">{{item.desc}}</p>
              <div className="{p}-card__footer">
                <a href="#footer" className="{p}-card__action">Inquire &rarr;</a>
              </div>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-catalog {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}}

.{p}-catalog__inner {{
  max-width: 1200px;
  margin: 0 auto;
}}

.{p}-catalog__header {{
  text-align: center;
  max-width: 720px;
  margin: 0 auto 3.5rem;
}}

.{p}-catalog__eyebrow {{
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {d['accent']};
  margin: 0 0 0.75rem;
}}

.{p}-catalog__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(1.8rem, 3.5vw, 2.6rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-catalog__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-catalog__grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.75rem;
}}

.{p}-card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, border-color 0.2s ease;
}}

.{p}-card:hover {{
  transform: translateY(-3px);
  border-color: rgba({r_acc}, {g_acc}, {b_acc}, 0.35);
}}

.{p}-card__top {{
  margin-bottom: 1rem;
}}

.{p}-card__tag {{
  display: inline-block;
  padding: 0.3rem 0.8rem;
  background: rgba({r_acc}, {g_acc}, {b_acc}, 0.12);
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  border-radius: 4px;
}}

.{p}-card__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-card__desc {{
  font-size: 0.92rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0 0 1.5rem;
  flex: 1;
}}

.{p}-card__footer {{
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}}

.{p}-card__action {{
  color: {d['accent']};
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
}}
"""

    elif style_variant == 1:
        # Style 1: Asymmetric Spotlight Grid
        t3_thought = thought(
            f"Now creating the core content component '{sec_ts_name}' for {d['name']}. "
            f"I'll structure it as an asymmetric spotlight grid where the initial card holds priority showcase framing, "
            f"paired with complementary offerings."
        )
        t3_tsx = f"""import React from 'react';
import './{sec_ts_name}.css';

interface Item {{
  title: string;
  tag: string;
  desc: string;
}}

const ITEMS: Item[] = {items_json};

export function {sec_ts_name}() {{
  return (
    <section className="{p}-catalog" id="{d['section_id']}" aria-labelledby="{p}-catalog-title">
      <div className="{p}-catalog__inner">
        <div className="{p}-catalog__header">
          <p className="{p}-catalog__eyebrow">Collection Spotlight</p>
          <h2 id="{p}-catalog-title" className="{p}-catalog__title">
            {d['section_name']}
          </h2>
          <p className="{p}-catalog__desc">
            {sec_desc}
          </p>
        </div>

        <div className="{p}-catalog__asymmetric">
          {{ITEMS.map((item, idx) => (
            <article key={{item.title}} className={{`{p}-card ${{idx === 0 ? '{p}-card--spotlight' : ''}}`}}>
              <div className="{p}-card__meta">
                <span className="{p}-card__tag">{{item.tag}}</span>
                {{idx === 0 && <span className="{p}-card__flag">Featured Focus</span>}}
              </div>
              <h3 className="{p}-card__title">{{item.title}}</h3>
              <p className="{p}-card__desc">{{item.desc}}</p>
              <div className="{p}-card__action-row">
                <a href="mailto:{d['contact']['email']}" className="{p}-card__btn">Request Allocation &rarr;</a>
              </div>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-catalog {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}}

.{p}-catalog__inner {{
  max-width: 1200px;
  margin: 0 auto;
}}

.{p}-catalog__header {{
  max-width: 680px;
  margin-bottom: 3.5rem;
}}

.{p}-catalog__eyebrow {{
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {d['accent']};
  margin: 0 0 0.75rem;
}}

.{p}-catalog__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(1.8rem, 3.5vw, 2.6rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-catalog__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-catalog__asymmetric {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.75rem;
}}

.{p}-card--spotlight {{
  grid-column: 1 / -1;
  background: linear-gradient(135deg, {d['surface']}, rgba({r_acc}, {g_acc}, {b_acc}, 0.08));
  border-color: rgba({r_acc}, {g_acc}, {b_acc}, 0.35);
}}

.{p}-card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
}}

.{p}-card__meta {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}}

.{p}-card__tag {{
  display: inline-block;
  padding: 0.3rem 0.8rem;
  background: rgba({r_acc}, {g_acc}, {b_acc}, 0.12);
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  border-radius: 4px;
}}

.{p}-card__flag {{
  font-size: 0.75rem;
  font-weight: 700;
  color: {d['accent']};
  text-transform: uppercase;
  letter-spacing: 0.08em;
}}

.{p}-card__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.3rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-card__desc {{
  font-size: 0.95rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0 0 1.5rem;
  flex: 1;
}}

.{p}-card__btn {{
  color: {d['accent']};
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
}}

@media (max-width: 800px) {{
  .{p}-catalog__asymmetric {{ grid-template-columns: 1fr; }}
}}
"""

    elif style_variant == 2:
        # Style 2: Linear Specification Table / Row List
        t3_thought = thought(
            f"Now creating the core content component '{sec_ts_name}' for {d['name']}. "
            f"I'll present the offerings as an elegant linear specification list with clear horizontal dividers, "
            f"lead markers, and direct selection links."
        )
        t3_tsx = f"""import React from 'react';
import './{sec_ts_name}.css';

interface Item {{
  title: string;
  tag: string;
  desc: string;
}}

const ITEMS: Item[] = {items_json};

export function {sec_ts_name}() {{
  return (
    <section className="{p}-catalog" id="{d['section_id']}" aria-labelledby="{p}-catalog-title">
      <div className="{p}-catalog__inner">
        <div className="{p}-catalog__header">
          <p className="{p}-catalog__eyebrow">Service & Capability Index</p>
          <h2 id="{p}-catalog-title" className="{p}-catalog__title">
            {d['section_name']}
          </h2>
          <p className="{p}-catalog__desc">
            {sec_desc}
          </p>
        </div>

        <div className="{p}-catalog__list">
          {{ITEMS.map((item) => (
            <div key={{item.title}} className="{p}-spec-row">
              <div className="{p}-spec-row__lead">
                <span className="{p}-spec-row__bullet">&mdash;</span>
                <h3 className="{p}-spec-row__title">{{item.title}}</h3>
              </div>
              <p className="{p}-spec-row__desc">{{item.desc}}</p>
              <div className="{p}-spec-row__meta">
                <span className="{p}-spec-row__tag">{{item.tag}}</span>
                <a href="mailto:{d['contact']['email']}" className="{p}-spec-row__link">Select &rarr;</a>
              </div>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-catalog {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}}

.{p}-catalog__inner {{
  max-width: 1100px;
  margin: 0 auto;
}}

.{p}-catalog__header {{
  max-width: 700px;
  margin-bottom: 4rem;
}}

.{p}-catalog__eyebrow {{
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {d['accent']};
  margin: 0 0 0.75rem;
}}

.{p}-catalog__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(1.8rem, 3.5vw, 2.6rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-catalog__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-catalog__list {{
  display: flex;
  flex-direction: column;
}}

.{p}-spec-row {{
  display: grid;
  grid-template-columns: 1.2fr 2fr 1fr;
  gap: 2rem;
  align-items: center;
  padding: 1.8rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: background 0.2s ease;
}}

.{p}-spec-row:first-child {{
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-spec-row__lead {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
}}

.{p}-spec-row__bullet {{
  color: {d['accent']};
  font-weight: 700;
}}

.{p}-spec-row__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0;
}}

.{p}-spec-row__desc {{
  font-size: 0.92rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-spec-row__meta {{
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1.25rem;
}}

.{p}-spec-row__tag {{
  display: inline-block;
  padding: 0.25rem 0.7rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fafafa;
  font-size: 0.78rem;
  font-weight: 600;
  border-radius: 4px;
}}

.{p}-spec-row__link {{
  color: {d['accent']};
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
}}

@media (max-width: 860px) {{
  .{p}-spec-row {{
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }}
  .{p}-spec-row__meta {{
    justify-content: flex-start;
  }}
}}
"""

    else:
        # Style 3: Horizontal Scroll-Snap Carousel Deck
        t3_thought = thought(
            f"Now creating the core content component '{sec_ts_name}' for {d['name']}. "
            f"I'll build an interactive horizontal scroll-snap card strip providing focused tactile exploration."
        )
        t3_tsx = f"""import React from 'react';
import './{sec_ts_name}.css';

interface Item {{
  title: string;
  tag: string;
  desc: string;
}}

const ITEMS: Item[] = {items_json};

export function {sec_ts_name}() {{
  return (
    <section className="{p}-catalog" id="{d['section_id']}" aria-labelledby="{p}-catalog-title">
      <div className="{p}-catalog__inner">
        <div className="{p}-catalog__header">
          <p className="{p}-catalog__eyebrow">Curated Showcase</p>
          <h2 id="{p}-catalog-title" className="{p}-catalog__title">
            {d['section_name']}
          </h2>
          <p className="{p}-catalog__desc">
            {sec_desc}
          </p>
        </div>

        <div className="{p}-catalog__carousel">
          {{ITEMS.map((item) => (
            <article key={{item.title}} className="{p}-carousel-card">
              <div className="{p}-carousel-card__badge">{{item.tag}}</div>
              <h3 className="{p}-carousel-card__title">{{item.title}}</h3>
              <p className="{p}-carousel-card__desc">{{item.desc}}</p>
              <div className="{p}-carousel-card__footer">
                <a href="#footer" className="{p}-carousel-card__cta">View Specifications &rarr;</a>
              </div>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-catalog {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}}

.{p}-catalog__inner {{
  max-width: 1240px;
  margin: 0 auto;
}}

.{p}-catalog__header {{
  max-width: 720px;
  margin-bottom: 3.5rem;
}}

.{p}-catalog__eyebrow {{
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {d['accent']};
  margin: 0 0 0.75rem;
}}

.{p}-catalog__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(1.8rem, 3.5vw, 2.6rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-catalog__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-catalog__carousel {{
  display: flex;
  gap: 1.75rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding: 1rem 0 2rem;
}}

.{p}-carousel-card {{
  scroll-snap-align: start;
  flex: 0 0 320px;
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 2.2rem;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
}}

.{p}-carousel-card__badge {{
  display: inline-block;
  align-self: flex-start;
  padding: 0.3rem 0.8rem;
  background: rgba({r_acc}, {g_acc}, {b_acc}, 0.12);
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  border-radius: 4px;
  margin-bottom: 1.25rem;
}}

.{p}-carousel-card__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-carousel-card__desc {{
  font-size: 0.92rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0 0 1.75rem;
  flex: 1;
}}

.{p}-carousel-card__footer {{
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}}

.{p}-carousel-card__cta {{
  color: {d['accent']};
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
}}
"""

    t3_action = write_site(f"src/components/{sec_ts_name}.tsx", t3_tsx, f"src/components/{sec_ts_name}.css", t3_css)

    # ── Turn 4: Footer ──────────────────────────────────────────────────────────
    t4_user = obs_ok(
        [f"src/components/{sec_ts_name}.tsx", f"src/components/{sec_ts_name}.css"],
        "Write the Footer section: dark footer with business name, address, phone, email, hours, and copyright. "
        "Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    t4_thought = thought(
        f"Writing the final section, Footer, for {d['name']}. "
        "I'll organize it into a structured multi-column layout containing the brand wordmark, "
        f"tagline, contact card (address: {d['contact']['address']}, phone: {d['contact']['phone']}, email: {d['contact']['email']}), "
        "operating hours, and an automatic copyright line."
    )

    t4_tsx = f"""import React from 'react';
import './Footer.css';

export function Footer() {{
  const year = new Date().getFullYear();

  return (
    <footer className="{p}-footer" id="footer" aria-label="Site Footer">
      <div className="{p}-footer__inner">
        <div className="{p}-footer__brand">
          <p className="{p}-footer__logo">{d['name']}</p>
          <p className="{p}-footer__tagline">{d['tagline']}</p>
        </div>

        <address className="{p}-footer__contact">
          <h4 className="{p}-footer__heading">Visit & Connect</h4>
          <p>{d['contact']['address']}</p>
          <p><a href="tel:{d['contact']['phone']}">{d['contact']['phone']}</a></p>
          <p><a href="mailto:{d['contact']['email']}">{d['contact']['email']}</a></p>
        </address>

        <div className="{p}-footer__hours">
          <h4 className="{p}-footer__heading">Hours of Operation</h4>
          <p>{d['contact']['hours']}</p>
        </div>
      </div>

      <div className="{p}-footer__bottom">
        <p>&copy; {{year}} {d['name']}. All rights reserved.</p>
      </div>
    </footer>
  );
}}
"""

    t4_css = f""".{p}-footer {{
  background: #08080a;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4.5rem 2rem 2rem;
  color: #a1a1aa;
}}

.{p}-footer__inner {{
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1.5fr 1.5fr;
  gap: 3rem;
  padding-bottom: 3rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}}

.{p}-footer__logo {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-footer__tagline {{
  font-size: 0.95rem;
  line-height: 1.6;
  max-width: 320px;
  margin: 0;
}}

.{p}-footer__heading {{
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {d['accent']};
  margin: 0 0 1rem;
}}

.{p}-footer__contact,
.{p}-footer__hours {{
  font-style: normal;
  font-size: 0.92rem;
  line-height: 1.7;
}}

.{p}-footer__contact a {{
  color: #fafafa;
  text-decoration: none;
  transition: color 0.2s ease;
}}

.{p}-footer__contact a:hover {{
  color: {d['accent']};
}}

.{p}-footer__bottom {{
  max-width: 1200px;
  margin: 2rem auto 0;
  text-align: center;
  font-size: 0.85rem;
  color: #71717a;
}}

@media (max-width: 768px) {{
  .{p}-footer__inner {{
    grid-template-columns: 1fr;
    gap: 2rem;
  }}
}}
"""

    t4_action = write_site("src/components/Footer.tsx", t4_tsx, "src/components/Footer.css", t4_css)

    # ── Turn 5: Complete & Finish ───────────────────────────────────────────────
    t5_user = obs_done([
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        f"src/components/{sec_ts_name}.tsx", f"src/components/{sec_ts_name}.css",
        "src/components/Footer.tsx", "src/components/Footer.css"
    ])

    t5_thought = thought(
        f"All 4 sections have been built and accepted for {d['name']}. "
        "The site is complete with cohesive design tokens, responsive layouts, "
        "valid TypeScript components, and scoped modern CSS."
    )

    t5_finish = finish(
        f"Built the complete {d['name']} ({d['type']}) website with 4 sections:\n"
        f"- Header: sticky navbar with logo, nav links, CTA button, and mobile menu\n"
        f"- Hero: distinctive responsive hero banner styled with {['split layout', 'metric strip', 'angular divider', 'framed showcase'][style_variant]}\n"
        f"- {d['section_name']}: {['multi-column card grid', 'asymmetric spotlight grid', 'linear specification table', 'scroll-snap carousel'][style_variant]} displaying all {len(d['items'])} items\n"
        f"- Footer: structured layout with business info, full address, phone, email, and hours\n"
        f"Color scheme: primary ({d['primary']}), accent ({d['accent']}), {d['heading_font']} headings on {d['body_font']} body."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": f"{t1_thought}\n{t1_action}"},
        {"role": "user", "content": t2_user},
        {"role": "assistant", "content": f"{t2_thought}\n{t2_action}"},
        {"role": "user", "content": t3_user},
        {"role": "assistant", "content": f"{t3_thought}\n{t3_action}"},
        {"role": "user", "content": t4_user},
        {"role": "assistant", "content": f"{t4_thought}\n{t4_action}"},
        {"role": "user", "content": t5_user},
        {"role": "assistant", "content": f"{t5_thought}\n{t5_finish}"}
    ]

    return {
        "task_id": d["id"],
        "messages": messages
    }

def build_trajectory_b4(d: dict, idx: int = 0) -> dict:
    return build_diverse_domain_trajectory(d, idx)


def build_trajectory_b5(d: dict, idx: int = 0) -> dict:
    return build_diverse_domain_trajectory(d, idx)


build_trajectory = build_diverse_domain_trajectory




# ==============================================================================
# BATCH 5: 50 Real-World Domains
# ==============================================================================

import json
import re
import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")





def thought(text):
    return f"<thought>\n{text}\n</thought>"


def finish(text):
    return f"<finish>\n{text}\n</finish>"


# ── 50 Domain Specifications ──────────────────────────────────────────────────

DOMAINS_B5 = [
    # 1. Advanced AI & Dev Tools
    {
        "id": "site_ai_vector_scale_db",
        "name": "VectorScale DB",
        "tagline": "Sub-Millisecond Approximate Nearest Neighbors at Billion-Vector Scale",
        "type": "database",
        "prefix": "vs",
        "primary": "#080c14",
        "accent": "#38bdf8",
        "accent_hover": "#0ea5e9",
        "surface": "#0f172a",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Deploy Cluster",
        "hero_sub": "Purpose-built HNSW and IVF-PQ indexing with SIMD hardware acceleration, zero-downtime replication, and native hybrid sparse-dense filtering.",
        "section_name": "Engine Capabilities",
        "section_id": "capabilities",
        "items": [
            {"title": "Billion-Scale HNSW Indexing", "tag": "< 2ms Latency", "desc": "Hardware-accelerated hierarchical graphs with quantised product embeddings and real-time live graph rebalancing."},
            {"title": "Hybrid Sparse-Dense Search", "tag": "BM25 + Dense", "desc": "Unified ranking pipeline blending keyword lexical relevance with high-dimensional transformer representations in a single pass."},
            {"title": "Zero-Copy Memory Mapping", "tag": "mmap Direct", "desc": "Direct disk-to-NVMe zero-copy memory mapping allowing terabytes of vectors per host with minimal RAM overhead."},
            {"title": "Multi-Tenant VPC Peering", "tag": "SOC 2 Type II", "desc": "Isolated enterprise namespaces, row-level vector security filters, and automated end-to-end TLS encryption."}
        ],
        "contact": {
            "address": "400 Howard St, Suite 500, San Francisco, CA 94105",
            "phone": "+1 (415) 555-0201",
            "email": "infra@vectorscaledb.com",
            "hours": "24/7 Global Enterprise Support"
        }
    },
    {
        "id": "site_devops_ebpf_telemetry",
        "name": "K-Trace Observability",
        "tagline": "Zero-Overhead Linux Kernel Observability Powered by eBPF",
        "type": "observability",
        "prefix": "kt",
        "primary": "#0a0a0f",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "surface": "#14141f",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Install DaemonSet",
        "hero_sub": "Trace distributed service requests, kernel TCP drops, and container memory leaks without modifying code or injecting invasive sidecar proxies.",
        "section_name": "Telemetry Engines",
        "section_id": "engines",
        "items": [
            {"title": "Kernel-Level TCP Tracing", "tag": "Zero Overhead", "desc": "Monitor SYN packet drops, socket retransmissions, and round-trip jitter directly inside the Linux socket layer."},
            {"title": "Distributed Trace Graph", "tag": "Automatic", "desc": "Autonomous trace reconstruction across microservices via kernel context propagation with zero application bytecode instrumentation."},
            {"title": "Security Anomaly Detection", "tag": "Real-Time", "desc": "Trap unauthorized execve syscalls, root privilege escalations, and suspicious outbound DNS queries in milliseconds."},
            {"title": "OTel Native Exporter", "tag": "OpenTelemetry", "desc": "Stream high-fidelity kernel metrics into existing Prometheus, Datadog, and Grafana pipelines directly."}
        ],
        "contact": {
            "address": "185 Berry St, Suite 3000, San Francisco, CA 94107",
            "phone": "+1 (415) 555-0202",
            "email": "ops@ktrace.io",
            "hours": "Mon–Fri: 9am–6pm PST"
        }
    },
    {
        "id": "site_ai_llm_gateway",
        "name": "Nexus Gateway",
        "tagline": "Intelligent Model Routing, Semantic Caching, and Fallback Resilience",
        "type": "ai_infrastructure",
        "prefix": "ng",
        "primary": "#0c0d14",
        "accent": "#8b5cf6",
        "accent_hover": "#7c3aed",
        "surface": "#161726",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Connect API Key",
        "hero_sub": "Unify OpenAI, Anthropic, Mistral, and local Ollama nodes behind a single ultra-low-latency proxy with automated rate-limit failover.",
        "section_name": "Gateway Features",
        "section_id": "features",
        "items": [
            {"title": "Semantic Vector Caching", "tag": "85% Cost Drop", "desc": "Instantly return cached completions for semantically identical prompts using fast vector cosine thresholds."},
            {"title": "Intelligent Model Routing", "tag": "Lowest Latency", "desc": "Dynamically route queries based on prompt token complexity, provider health status, and cost budgets."},
            {"title": "PII Redaction & Guardrails", "tag": "Compliance", "desc": "Detect and mask sensitive credit cards, SSNs, and personal data before prompt tokens leave your private cloud boundary."},
            {"title": "Real-Time Token Analytics", "tag": "Per-User Quotas", "desc": "Track prompt and completion token expenditures by team, user ID, and API key with live spending alerts."}
        ],
        "contact": {
            "address": "520 Broadway, 11th Floor, New York, NY 10012",
            "phone": "+1 (212) 555-0203",
            "email": "team@nexusgateway.ai",
            "hours": "Mon–Fri: 8am–7pm EST"
        }
    },
    {
        "id": "site_cloud_finops_optimizer",
        "name": "CloudLedger FinOps",
        "tagline": "Autonomous Kubernetes and Cloud Infrastructure Cost Elimination",
        "type": "finops",
        "prefix": "cl",
        "primary": "#0f172a",
        "accent": "#06b6d4",
        "accent_hover": "#0891b2",
        "surface": "#1e293b",
        "heading_font": "DM Sans",
        "body_font": "Inter",
        "cta": "Audit Cloud Spend",
        "hero_sub": "Right-size overprovisioned container clusters, automate spot instance bidding, and eliminate orphaned cloud volumes across AWS, GCP, and Azure.",
        "section_name": "Optimization Tools",
        "section_id": "tools",
        "items": [
            {"title": "Automated Spot Interruption Management", "tag": "Up to 70% Off", "desc": "Predict spot termination notices 120 seconds ahead and gracefully drain pods to available on-demand capacity."},
            {"title": "Autonomous Pod Right-Sizing", "tag": "Kubernetes VPA", "desc": "Continuous machine-learning recommendations for memory and CPU requests without restarting production workloads."},
            {"title": "Reserved Instance Portfolio Arbitrage", "tag": "Savings Plans", "desc": "Buy, sell, and rebalance 1-year and 3-year commitments in secondary marketplaces to prevent commitment waste."},
            {"title": "Orphaned Storage Reaper", "tag": "Disk Waste", "desc": "Detect and terminate unattached EBS volumes, abandoned snapshots, and unreferenced load balancers safely."}
        ],
        "contact": {
            "address": "222 Merchandise Mart Plaza, Chicago, IL 60654",
            "phone": "+1 (312) 555-0204",
            "email": "savings@cloudledger.io",
            "hours": "Mon–Fri: 8:30am–5:30pm CST"
        }
    },
    {
        "id": "site_dev_api_contract_test",
        "name": "SpecVigil API Testing",
        "tagline": "Continuous OpenAPI Contract Verification and Synthetic Mocking",
        "type": "devtools",
        "prefix": "sv",
        "primary": "#111318",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
        "surface": "#1c1f26",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Test Your API",
        "hero_sub": "Catch breaking API changes, schema drifts, and undocumented payload mutations before they reach production staging environments.",
        "section_name": "Test Suites",
        "section_id": "suites",
        "items": [
            {"title": "Automated Contract Regression", "tag": "CI/CD Native", "desc": "Diff pull requests against live OpenAPI 3.1 schemas to flag backward-incompatible breaking field removals."},
            {"title": "Stateful Mock Servers", "tag": "Faker Engine", "desc": "Spin up ultra-fast ephemeral mock servers with realistic relational data and latency simulation for frontend teams."},
            {"title": "Fuzzing & Boundary Testing", "tag": "Security Fuzz", "desc": "Generate thousands of malicious payloads to uncover unhandled null pointers and SQL/NoSQL injections."},
            {"title": "SDK Generation Pipeline", "tag": "TypeScript/Go/Py", "desc": "Compile bulletproof, strongly-typed client libraries directly from your validated contract specifications."}
        ],
        "contact": {
            "address": "700 E 4th St, Austin, TX 78701",
            "phone": "+1 (512) 555-0205",
            "email": "support@specvigil.dev",
            "hours": "Mon–Fri: 9am–6pm CST"
        }
    },
    {
        "id": "site_infra_bare_metal_cloud",
        "name": "Apex BareMetal Cloud",
        "tagline": "Direct GPU Hardware Access with Zero Virtualization Jitter",
        "type": "cloud_infrastructure",
        "prefix": "ab",
        "primary": "#07090e",
        "accent": "#22c55e",
        "accent_hover": "#16a34a",
        "surface": "#11151f",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Provision Cluster",
        "hero_sub": "Dedicated HGX H100 and B200 8-GPU nodes interconnected with 3.2Tbps Quantum-2 InfiniBand for LLM pretraining and low-latency inference.",
        "section_name": "Hardware Configurations",
        "section_id": "hardware",
        "items": [
            {"title": "NVIDIA H100 SXM5 8-Way", "tag": "640GB HBM3", "desc": "Full NVLink 900GB/s GPU-to-GPU fabric designed for multi-node distributed gradient synchronization."},
            {"title": "3.2Tbps Quantum-2 InfiniBand", "tag": "RoCEv2 RDMA", "desc": "Direct memory access across compute racks without CPU interrupt overhead or packet drop degradation."},
            {"title": "Direct Liquid Cooling", "tag": "PUE < 1.08", "desc": "Custom cold-plate liquid loops ensuring sustained 700W TDP boost clocks without thermal throttling."},
            {"title": "Sub-Minute OS Provisioning", "tag": "iPXE Fast Boot", "desc": "Boot custom Ubuntu, Rocky Linux, or container OS images directly onto raw physical NVMe arrays."}
        ],
        "contact": {
            "address": "1201 3rd Ave, Suite 2200, Seattle, WA 98101",
            "phone": "+1 (206) 555-0206",
            "email": "sales@apexmetal.cloud",
            "hours": "24/7 Tier-1 Technical Support"
        }
    },
    {
        "id": "site_database_distributed_sql",
        "name": "TitanSQL Distributed",
        "tagline": "Global Strong Consistency with Familiar Postgres Semantics",
        "type": "database",
        "prefix": "ts",
        "primary": "#0e1117",
        "accent": "#6366f1",
        "accent_hover": "#4f46e5",
        "surface": "#191d26",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Create Free Cluster",
        "hero_sub": "A globally distributed database featuring Raft consensus, distributed ACID transactions, and wire-compatible PostgreSQL dialect.",
        "section_name": "Architecture Highlights",
        "section_id": "architecture",
        "items": [
            {"title": "Distributed Multi-Raft Consensus", "tag": "Strict Serializability", "desc": "Shards partition ranges into autonomous Raft consensus groups with sub-10ms intra-region commit latency."},
            {"title": "Wire-Compatible PostgreSQL", "tag": "pgwire", "desc": "Connect standard ORMs, pgvector, Prisma, and Drizzle directly without rewriting application queries."},
            {"title": "Global Multi-Region Latency", "tag": "Geo-Partitioning", "desc": "Pin user table rows to sovereign jurisdictions to satisfy GDPR data residency and reduce local read latency."},
            {"title": "Automated Online Schema Migration", "tag": "Zero Table Lock", "desc": "Execute complex DDL alter table migrations on multi-terabyte tables without holding blocking locks."}
        ],
        "contact": {
            "address": "100 Montgomery St, San Francisco, CA 94104",
            "phone": "+1 (415) 555-0207",
            "email": "team@titansql.com",
            "hours": "Mon–Fri: 9am–6pm PST"
        }
    },
    {
        "id": "site_quantum_circuits_lab",
        "name": "Helios Quantum Lab",
        "tagline": "Superconducting Qubit Compilers and Noisy Intermediate-Scale Simulation",
        "type": "deep_tech",
        "prefix": "hq",
        "primary": "#050b14",
        "accent": "#00f0ff",
        "accent_hover": "#00c8d6",
        "surface": "#0c1524",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Simulate Circuit",
        "hero_sub": "Design, optimize, and simulate variational quantum algorithms with state-of-the-art pulse-level pulse control and tensor network contraction.",
        "section_name": "Research Modules",
        "section_id": "modules",
        "items": [
            {"title": "Tensor Network Circuit Simulator", "tag": "MPS & PEPS", "desc": "Simulate quantum circuits up to 100 qubits with low entanglement entropy using matrix product states."},
            {"title": "Pulse-Level Microwave Calibration", "tag": "15mK Dilution", "desc": "Optimize DRAG pulse shapes and cross-resonance gates to suppress leakage into higher Transmon states."},
            {"title": "Quantum Error Mitigation", "tag": "Zero-Noise Extrapolation", "desc": "Recover ground-state energies from noisy hardware results using probabilistic error cancellation."},
            {"title": "VQE Chemistry Solver", "tag": "Molecular Orbitals", "desc": "Calculate complex chemical bond dissociation curves and transition state energies for catalyst discovery."}
        ],
        "contact": {
            "address": "77 Massachusetts Ave, Building 38, Cambridge, MA 02139",
            "phone": "+1 (617) 555-0208",
            "email": "research@heliosquantum.org",
            "hours": "Mon–Fri: 9am–5pm EST"
        }
    },

    # 2. Specialized Healthcare & Clinical
    {
        "id": "site_telehealth_neurology",
        "name": "Synapse TeleNeurology",
        "tagline": "Board-Certified Neurological Teleconsultation and Remote EEG Analytics",
        "type": "medical",
        "prefix": "sn",
        "primary": "#0d1b2a",
        "accent": "#0ea5e9",
        "accent_hover": "#0284c7",
        "surface": "#1b263b",
        "heading_font": "Merriweather",
        "body_font": "Inter",
        "cta": "Schedule Evaluation",
        "hero_sub": "Expert clinical evaluation for refractory migraines, epilepsy, tremor disorders, and sleep pathology from the comfort of home.",
        "section_name": "Specialized Clinics",
        "section_id": "clinics",
        "items": [
            {"title": "Refractory Migraine Protocol", "tag": "CGRP Therapy", "desc": "Comprehensive clinical titration of monoclonal antibodies, botulinum neurotoxin, and neuromodulation devices."},
            {"title": "Continuous Ambulatory EEG", "tag": "72-Hour Tracing", "desc": "High-density wireless home EEG monitoring interpreted by fellowship-trained clinical neurophysiologists."},
            {"title": "Movement Disorders & Tremor", "tag": "Video Assessment", "desc": "Standardized UPDRS video evaluations for Parkinsonian syndromes and deep brain stimulation (DBS) adjustments."},
            {"title": "Cognitive & Memory Review", "tag": "Neuropsychology", "desc": "Digital psychometric testing and neuroimaging correlation for early-stage mild cognitive impairment."}
        ],
        "contact": {
            "address": "750 E Adams St, Syracuse, NY 13210",
            "phone": "+1 (315) 555-0209",
            "email": "intake@synapseneuro.com",
            "hours": "Mon–Sat: 8am–6pm EST"
        }
    },
    {
        "id": "site_biomechanics_sports_rehab",
        "name": "Kinetic Lab Sports Medicine",
        "tagline": "3D Optical Motion Capture and Elite Biomechanical Rehabilitation",
        "type": "sports_medicine",
        "prefix": "kl",
        "primary": "#0f1715",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "surface": "#182622",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Book Assessment",
        "hero_sub": "High-speed infrared marker tracking, dual force plate kinetic analysis, and objective return-to-sport criteria for competitive athletes.",
        "section_name": "Rehab Protocols",
        "section_id": "protocols",
        "items": [
            {"title": "ACL Reconstruction Return-to-Play", "tag": "Force Plate Symmetry", "desc": "Isokinetic dynamometry and triple hop symmetry testing to eliminate secondary graft re-tear risks."},
            {"title": "High-Speed Running Gait Analysis", "tag": "Qualisys 3D Mocap", "desc": "12-camera motion analysis quantifying pelvic drop, braking forces, and ground contact asymmetries."},
            {"title": "Overhead Throwing Arm Protocol", "tag": "Electromyography", "desc": "Valgus torque assessment and scapular dyskinesis correction for baseball pitchers and tennis players."},
            {"title": "Blood Flow Restriction Training", "tag": "Delfi Personalized BFR", "desc": "Hypertrophy and strength gains at low joint loads to accelerate post-operative tendon healing."}
        ],
        "contact": {
            "address": "1240 S Figueroa St, Los Angeles, CA 90015",
            "phone": "+1 (213) 555-0210",
            "email": "clinic@kineticlab.com",
            "hours": "Mon–Fri: 6:30am–7:30pm | Sat: 8am–1pm"
        }
    },
    {
        "id": "site_dermatology_precision_skin",
        "name": "Aura Dermatology & Laser",
        "tagline": "Physician-Led Medical Dermatology and Advanced Laser Resurfacing",
        "type": "dermatology",
        "prefix": "ad",
        "primary": "#1a151b",
        "accent": "#e11d48",
        "accent_hover": "#be123c",
        "surface": "#281f2a",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Consult Specialist",
        "hero_sub": "Dual-wavelength picosecond lasers, Mohs micrographic surgery, and targeted medical therapies for inflammatory skin conditions.",
        "section_name": "Clinical Treatments",
        "section_id": "treatments",
        "items": [
            {"title": "Fractional CO2 Laser Resurfacing", "tag": "Deep Remodeling", "desc": "Ablative micro-thermal zones stimulating neo-collagenesis for deep acne scarring and photodamage."},
            {"title": "Mohs Micrographic Surgery", "tag": "99% Clear Margins", "desc": "Same-day microscopic margin mapping for basal and squamous cell carcinomas with aesthetic reconstruction."},
            {"title": "Vascular Laser Therapy", "tag": "Candela Vbeam", "desc": "Pulsed dye laser specifically targeting facial telangiectasias, rosacea redness, and port-wine stains."},
            {"title": "Biologic Immunotherapy for Psoriasis", "tag": "IL-17/IL-23 Inhibitors", "desc": "Targeted biologic regimens achieving 90–100% skin clearance for chronic severe plaque psoriasis."}
        ],
        "contact": {
            "address": "450 Sutter St, Suite 1800, San Francisco, CA 94108",
            "phone": "+1 (415) 555-0211",
            "email": "concierge@auraderm.com",
            "hours": "Mon–Fri: 8:30am–5pm"
        }
    },
    {
        "id": "site_pediatric_sensory_therapy",
        "name": "Little Steps Pediatric Therapy",
        "tagline": "Sensory Integration, Speech Pathology, and Pediatric Occupational Therapy",
        "type": "pediatrics",
        "prefix": "ls",
        "primary": "#121b24",
        "accent": "#38bdf8",
        "accent_hover": "#0ea5e9",
        "surface": "#1e2c3a",
        "heading_font": "DM Sans",
        "body_font": "Inter",
        "cta": "Request Evaluation",
        "hero_sub": "Play-based sensory gyms, vestibular swings, and evidence-based motor planning therapies designed to help every child thrive.",
        "section_name": "Therapy Programs",
        "section_id": "programs",
        "items": [
            {"title": "Sensory Integration Gym", "tag": "Ayres Sensory", "desc": "Suspended swings, climbing walls, and tactile obstacle courses supporting vestibular and proprioceptive regulation."},
            {"title": "Pediatric Speech & Language", "tag": "PROMPT Certified", "desc": "Articulatory placement, receptive language development, and augmentative alternative communication (AAC)."},
            {"title": "Fine Motor & Handwriting Clinic", "tag": "Handwriting Without Tears", "desc": "Bilateral coordination, pencil grasp stabilization, and scissor skills for school-readiness."},
            {"title": "Feeding Therapy Protocol", "tag": "SOS Approach", "desc": "Gradual desensitization and motor oral therapies for selective eaters and sensory food aversion."}
        ],
        "contact": {
            "address": "3200 Northline Ave, Suite 140, Greensboro, NC 27408",
            "phone": "+1 (336) 555-0212",
            "email": "admissions@littlestepstherapy.org",
            "hours": "Mon–Fri: 8am–5:30pm"
        }
    },
    {
        "id": "site_cardiology_heart_rhythm",
        "name": "Apex Heart Rhythm Institute",
        "tagline": "Advanced Cardiac Electrophysiology and Arrhythmia Management",
        "type": "cardiology",
        "prefix": "ar",
        "primary": "#141014",
        "accent": "#f43f5e",
        "accent_hover": "#e11d48",
        "surface": "#241a24",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Refer a Patient",
        "hero_sub": "State-of-the-art 3D electro-anatomical mapping, pulsed field ablation (PFA), and leadless pacemaker implantation.",
        "section_name": "Clinical Procedures",
        "section_id": "procedures",
        "items": [
            {"title": "Pulsed Field Ablation (PFA)", "tag": "Non-Thermal", "desc": "Tissue-selective irreversible electroporation for atrial fibrillation, preserving esophageal and nerve integrity."},
            {"title": "Leadless Pacemaker Implantation", "tag": "Transcatheter", "desc": "Minimally invasive intracardiac micro-capsules implanted through femoral access with zero chest incisions."},
            {"title": "3D Electro-Anatomical Mapping", "tag": "CARTO 3 & EnSite", "desc": "High-density ventricular tachycardia substrate mapping to precisely pinpoint ectopic rhythm origins."},
            {"title": "Subcutaneous ICD (S-ICD)", "tag": "Extravascular", "desc": "Defibrillation therapy positioned completely outside the vascular tree, preventing endovascular infection risks."}
        ],
        "contact": {
            "address": "6720 Bertner Ave, Houston, TX 77030",
            "phone": "+1 (713) 555-0213",
            "email": "clinical@apexheartrhythm.org",
            "hours": "Mon–Fri: 7:30am–5pm"
        }
    },
    {
        "id": "site_fertility_nova_origins",
        "name": "Nova Origins Reproductive Sciences",
        "tagline": "Next-Generation Embryology, Pre-implantation Genetics, and IVF Care",
        "type": "fertility",
        "prefix": "no",
        "primary": "#1c1418",
        "accent": "#ec4899",
        "accent_hover": "#db2777",
        "surface": "#2d1f27",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Schedule Consultation",
        "hero_sub": "Time-lapse embryo incubation, PGT-A chromosomal screening, and individualized ovarian stimulation protocols overseen by expert reproductive endocrinologists.",
        "section_name": "Clinical Pathways",
        "section_id": "pathways",
        "items": [
            {"title": "Time-Lapse Embryo Monitoring", "tag": "EmbryoScope+", "desc": "Continuous artificial intelligence assessment of blastocyst cellular division kinetics without incubator disruption."},
            {"title": "PGT-A Chromosomal Screening", "tag": "Next-Gen Sequencing", "desc": "Comprehensive 24-chromosome aneuploidy detection to maximize single embryo transfer implantation success."},
            {"title": "Social Egg Vitrification", "tag": "Flash Cryopreservation", "desc": "Ultra-fast vitrification preventing ice crystal formation with >95% post-thaw oocyte survival rates."},
            {"title": "Recurrent Implantation Failure Panel", "tag": "Immunology & Endometrium", "desc": "ERA endometrial receptivity array, microbiome testing, and natural killer (NK) cell balance analysis."}
        ],
        "contact": {
            "address": "1110 2nd Ave, Suite 400, New York, NY 10022",
            "phone": "+1 (212) 555-0214",
            "email": "care@novaoriginsivf.com",
            "hours": "Mon–Fri: 7am–4pm | Sat–Sun: 7am–11am"
        }
    },
    {
        "id": "site_oncology_immunotherapy_inst",
        "name": "Vanguard Immuno-Oncology",
        "tagline": "Pioneering Cellular Immunotherapies and Molecular Oncology",
        "type": "oncology",
        "prefix": "vi",
        "primary": "#0a131a",
        "accent": "#06b6d4",
        "accent_hover": "#0891b2",
        "surface": "#13212c",
        "heading_font": "Merriweather",
        "body_font": "Inter",
        "cta": "Clinical Trials",
        "hero_sub": "Translating advanced CAR-T cell constructs, neoantigen cancer vaccines, and immune checkpoint combinations into life-saving clinical remissions.",
        "section_name": "Therapeutic Pillars",
        "section_id": "pillars",
        "items": [
            {"title": "Autologous CAR-T Cell Therapy", "tag": "Cellular Engine", "desc": "Engineered chimeric antigen receptor T-cells specifically targeting refractory leukemias, lymphomas, and myelomas."},
            {"title": "Personalized Neoantigen Vaccines", "tag": "mRNA Vaccine", "desc": "Deep sequencing of tumor exomes to manufacture synthetic mRNA peptides priming cytotoxic CD8+ immune response."},
            {"title": "Bispecific T-Cell Engagers (BiTEs)", "tag": "Immune Synapse", "desc": "Engineered dual-antibody molecules bridging patient cytotoxic T-cells directly into malignant tumor surface receptors."},
            {"title": "Comprehensive Genomic Profiling", "tag": "500+ Gene Panel", "desc": "Next-generation liquid biopsy circulating tumor DNA (ctDNA) tracking treatment response and actionable mutations."}
        ],
        "contact": {
            "address": "450 Brookline Ave, Boston, MA 02215",
            "phone": "+1 (617) 555-0215",
            "email": "intake@vanguardimmunooncology.org",
            "hours": "Mon–Fri: 8am–6pm EST"
        }
    },

    # 3. Luxury & Bespoke Commerce
    {
        "id": "site_keyboards_bespoke_keebs",
        "name": "Aether Keyboards",
        "tagline": "Precision CNC-Milled Aluminium Keyboards and Custom Mechanical Switches",
        "type": "luxury_craft",
        "prefix": "ak",
        "primary": "#121417",
        "accent": "#c084fc",
        "accent_hover": "#a855f7",
        "surface": "#1e2229",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Join Next Group Buy",
        "hero_sub": "Gasket-mounted acoustic dampening, mirror-polished PVD brass weights, and hand-lubricated tactile switches crafted for discerning typists.",
        "section_name": "Flagship Editions",
        "section_id": "editions",
        "items": [
            {"title": "Aether 65 Founders Edition", "tag": "Solid Brass Weight", "desc": "Monolithic 6063 aerospace aluminium chassis with leaf-spring mounted FR4 plate and custom silicone acoustic dampener."},
            {"title": "Eclipse TKL Monolith", "tag": "Anodized Slate", "desc": "Tenkeyless layout featuring hot-swappable south-facing per-key RGB PCB and screw-in PCB stabilizers."},
            {"title": "Crystalline Linear Switches", "tag": "Factory Hand-Lubed", "desc": "Custom nylon housing, POM stem, and 62g dual-stage progressive gold-plated springs lubed with Krytox 205g0."},
            {"title": "Dye-Sub PBT Keycap Set", "tag": "Cherry Profile", "desc": "1.6mm thick dye-sublimated PBT keycaps with crisp legends and rich textured resistance to finger oil shine."}
        ],
        "contact": {
            "address": "1540 Market St, San Francisco, CA 94102",
            "phone": "+1 (415) 555-0216",
            "email": "concierge@aetherkeyboards.com",
            "hours": "Studio Visits by Private Appointment"
        }
    },
    {
        "id": "site_perfumery_botanical_scents",
        "name": "Maison Botanique",
        "tagline": "Haute Parfumerie from Wild-Harvested Rare Botanical Extracts",
        "type": "perfumery",
        "prefix": "mb",
        "primary": "#191512",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#26201b",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Order Sample Discovery Set",
        "hero_sub": "Aged Mysore sandalwood, Grasse rose absolute, and wild French orris root compounded in organic grape spirits in limited annual micro-batches.",
        "section_name": "Signature Extraits",
        "section_id": "extraits",
        "items": [
            {"title": "Oud Éternel Extrait de Parfum", "tag": "30% Concentration", "desc": "Wild Assamese agarwood aged 18 years layered with smoked saffron, frankincense resin, and Bourbon vanilla."},
            {"title": "Rose de Mai & Ambre Gris", "tag": "Grasse Harvest", "desc": "Early morning May roses distilled in copper stills resting upon authentic oceanic ambergris and aged patchouli."},
            {"title": "Orris Pallida & Velvet Cedar", "tag": "Florence Root", "desc": "Powdery Tuscan iris butter aged 5 years in dark barrels enriched with Atlas cedar and white musk accords."},
            {"title": "Santal Impérial", "tag": "Vintage 2011", "desc": "Creamy Santalum album harvested sustainably in East India accented with cardamom pods and black tea leaves."}
        ],
        "contact": {
            "address": "28 Rue Saint-Honoré, 75001 Paris, France",
            "phone": "+33 1 42 68 55 00",
            "email": "atelier@maisonbotanique.fr",
            "hours": "Mon–Sat: 10:30am–7:30pm CET"
        }
    },
    {
        "id": "site_horology_vintage_watches",
        "name": "Vanguard Horology Atelier",
        "tagline": "Restoration of Rare Mechanical Chronometers and Curated Estate Timepieces",
        "type": "horology",
        "prefix": "vh",
        "primary": "#0e1318",
        "accent": "#eab308",
        "accent_hover": "#ca8a04",
        "surface": "#182028",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "View Private Vault",
        "hero_sub": "Master watchmakers restoring column-wheel chronographs, perpetual calendars, and high-frequency tourbillons with original factory tooling.",
        "section_name": "Vault Highlights",
        "section_id": "vault",
        "items": [
            {"title": "1968 Ref. 105.012 Pre-Moon Chronograph", "tag": "Calibre 321", "desc": "Unpolished asymmetrical case with original stepped dial, dot-over-90 bezel, and fully serviced column-wheel movement."},
            {"title": "1972 Gérald Genta Jumbo Steel", "tag": "Ultra-Thin Cal. 2121", "desc": "Monobloc hand-finished stainless steel case with petit tapisserie dial and original Gay Frères integrated bracelet."},
            {"title": "1954 Yellow Gold Triple Calendar Moonphase", "tag": "Valjoux 72C", "desc": "Flawless champagne dial with applied teardrop indices, blued date pointer hand, and English day-month discs."},
            {"title": "High-Complication Complete Overhaul", "tag": "Geneva Seal Standard", "desc": "Complete ultrasonic teardown, pivot polishing, escapement escapement timing, and 100m pressure chamber certification."}
        ],
        "contact": {
            "address": "12 New Bond St, Mayfair, London W1S 3RR, UK",
            "phone": "+44 20 7946 0912",
            "email": "timepieces@vanguardhorology.com",
            "hours": "By Private Appointment Only"
        }
    },
    {
        "id": "site_ceramics_stone_and_ember",
        "name": "Stone & Ember Ceramics",
        "tagline": "Wood-Fired Stoneware and Architectural Ceramics for Michelin Dining",
        "type": "ceramics",
        "prefix": "se",
        "primary": "#1c1815",
        "accent": "#f97316",
        "accent_hover": "#ea580c",
        "surface": "#2c2621",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Commission Dinnerware",
        "hero_sub": "Four-day anagama kiln firings where melting wood ash, natural fly-ash glazes, and iron-rich river clays forge elemental tactile vessels.",
        "section_name": "Kiln Collections",
        "section_id": "collections",
        "items": [
            {"title": "Anagama Ash Tasting Plates", "tag": "Wood Fired 1300°C", "desc": "Natural wood ash vitrification creating rough crustaceous textures and subtle amber flash marks."},
            {"title": "Shino Glazed Tea Bowls (Chawan)", "tag": "Carbon Trapped", "desc": "High-alumina field clay coated in feldspathic glaze with rich iron-bloom speckling and warm tactile rim."},
            {"title": "Monolithic Architectural Vessels", "tag": "Hand Coiled", "desc": "Large-scale raw textured sculptural jars balancing organic asymmetry with quiet minimalist presence."},
            {"title": "Pour-Over Dripper & Server Suite", "tag": "Custom Wheel Turned", "desc": "Precision fluted ceramic dripper with thermal mass retention and matching unglazed stoneware decanter."}
        ],
        "contact": {
            "address": "88 Studio Lane, Ojai, CA 93023",
            "phone": "+1 (805) 555-0217",
            "email": "clay@stoneandember.com",
            "hours": "Open for Studio Tours First Saturday of Every Month"
        }
    },
    {
        "id": "site_olive_oil_estate_grove",
        "name": "Domaine de L'Olivier",
        "tagline": "Single-Estate Cold-Extracted High-Polyphenol Extra Virgin Olive Oil",
        "type": "gourmet",
        "prefix": "do",
        "primary": "#151912",
        "accent": "#84cc16",
        "accent_hover": "#65a30d",
        "surface": "#21281d",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Reserve Harvest Allocation",
        "hero_sub": "Centuries-old organic groves in the sunlit hills of Crete cold-milled within three hours of hand harvest to capture peerless grassy vibrancy.",
        "section_name": "Harvest Reserves",
        "section_id": "reserves",
        "items": [
            {"title": "Early Harvest Reserve (Agourelaio)", "tag": "740 mg/kg Polyphenols", "desc": "Intense green aromas of artichoke leaf, green almond, and a robust peppery antioxidant finish."},
            {"title": "Monovarietal Koroneiki Classic", "tag": "Estate Bottled", "desc": "Harmonious and versatile extra virgin oil with notes of fresh-cut grass, green tomato, and golden apple."},
            {"title": "Smoked Oak Wood-Infused Oil", "tag": "Slow Cold Infused", "desc": "Estate olive oil gently cold-steeped over natural wild French oak shavings for grilled meats and roasted vegetables."},
            {"title": "Truffle Infused Special Reserve", "tag": "White Alba Truffles", "desc": "Ultra-premium oil steeped with shaved Italian Tuber magnatum pico truffles for finishing risottos and fresh pastas."}
        ],
        "contact": {
            "address": "Chania Olive Valley, 73004 Crete, Greece",
            "phone": "+30 2821 055100",
            "email": "orders@domaineolivier.gr",
            "hours": "Mon–Fri: 9am–5pm EET"
        }
    },
    {
        "id": "site_tailor_savile_bespoke",
        "name": "Kingsman & Vance Bespoke",
        "tagline": "Hand-Canvassed Bespoke Suits and Heritage Tailoring",
        "type": "tailoring",
        "prefix": "kv",
        "primary": "#0d1117",
        "accent": "#c5a059",
        "accent_hover": "#b38c45",
        "surface": "#181f29",
        "heading_font": "Merriweather",
        "body_font": "Inter",
        "cta": "Book Fitting Consultation",
        "hero_sub": "More than 60 hours of bench hand-stitching, floating horsehair chest canvas, and rare Scottish wools custom cut to your unique silhouette.",
        "section_name": "Bespoke Services",
        "section_id": "services",
        "items": [
            {"title": "Full Two-Piece Bespoke Suit", "tag": "60+ Hours Hand Craft", "desc": "Hand-drafted personal paper pattern, three bespoke fittings, horn buttons, and functional buttonhole stitching."},
            {"title": "Overcoats in Pure Cashmere", "tag": "Fox Brothers Wool", "desc": "Substantial double-faced 650g heavy wool and Mongolian cashmere guard coats tailored for cold elegance."},
            {"title": "Black Tie Dinner Suits", "tag": "Silk Grosgrain Facings", "desc": "Midnight navy and classic jet black single-button peak lapel tuxedos with hand-sewn satin trouser braids."},
            {"title": "Handmade Sea Island Cotton Shirts", "tag": "Mother-of-Pearl", "desc": "Single-needle French seams, hand-sewn collar bands, and australian mother-of-pearl buttons."}
        ],
        "contact": {
            "address": "15 Savile Row, Mayfair, London W1S 3PJ, UK",
            "phone": "+44 20 7946 0880",
            "email": "tailors@kingsmanvance.co.uk",
            "hours": "Mon–Fri: 9am–6pm | Sat: By Appointment"
        }
    },
    {
        "id": "site_audio_vacuum_tube_amps",
        "name": "Sonus Valve Audio",
        "tagline": "Handcrafted Single-Ended Triode Vacuum Tube Amplifiers",
        "type": "audio",
        "prefix": "sa",
        "primary": "#14110e",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
        "surface": "#221d19",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Request Audition",
        "hero_sub": "Point-to-point silver wire circuitry, hand-wound permalloy output transformers, and legendary 300B triodes delivering pure holographic analog realism.",
        "section_name": "Amplifier Series",
        "section_id": "amplifiers",
        "items": [
            {"title": "Reference 300B Monoblocks", "tag": "Pure Class A (8W)", "desc": "Zero negative feedback topology, Hashimoto audio transformers, and dual valve rectifier choke-input power supplies."},
            {"title": "Aura KT88 Push-Pull Integrated", "tag": "45W Ultra-Linear", "desc": "Dynamic speaker driving response with stepped ladder attenuator and precision DC filament bias regulation."},
            {"title": "Valvola Tube Phono Preamplifier", "tag": "Passive RIAA EQ", "desc": "Two-box chassis with isolated power supply, 12AX7 low-noise input tubes, and switchable MC step-up transformers."},
            {"title": "Custom Solid Walnut Chassis", "tag": "Aircraft Aluminium", "desc": "Acoustically damped solid kiln-dried American walnut timber frame topped with brushed anodized top plates."}
        ],
        "contact": {
            "address": "420 Sound Way, Boulder, CO 80302",
            "phone": "+1 (303) 555-0218",
            "email": "listening@sonusvalve.com",
            "hours": "Listening Sessions by Appointment"
        }
    },
    {
        "id": "site_knives_damascus_forge",
        "name": "Kurogane Cutlery Forge",
        "tagline": "Multi-Layer Hand-Forged Damascus Kitchen Knives",
        "type": "cutlery",
        "prefix": "kc",
        "primary": "#111417",
        "accent": "#e2e8f0",
        "accent_hover": "#cbd5e1",
        "surface": "#1e242b",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Browse Knives",
        "hero_sub": "Shirogami White Paper steel cores clad in 67 layers of hammer-patterned Damascus, heat treated to 63 HRC for surgical culinary precision.",
        "section_name": "Master Blades",
        "section_id": "blades",
        "items": [
            {"title": "Gyuto 240mm Chef Knife", "tag": "Shirogami #1 Core", "desc": "The quintessential all-rounder blade with convex distal taper, laser-thin edge geometry, and stabilized ebony handle."},
            {"title": "Kiritsuke 210mm Multi-Purpose", "tag": "Tsuchime Hammered", "desc": "Traditional angled k-tip blade with dual bevel for precision vegetable push-cuts and protein slicing."},
            {"title": "Santoku 180mm Three Virtues", "tag": "67-Layer Damascus", "desc": "Lightweight and perfectly balanced for meat, fish, and herbs with octagonal charred chestnut wa-handle."},
            {"title": "Custom Water Stone Sharpening Service", "tag": "Mirror Polish 8000 Grit", "desc": "Hand-sharpened on Japanese natural whetstones, thinning bevels and resetting hair-whittling sharpness."}
        ],
        "contact": {
            "address": "Takefu Knife Village, Echizen, Fukui 915-0000, Japan",
            "phone": "+81 778 27 2000",
            "email": "orders@kuroganeforge.jp",
            "hours": "Mon–Fri: 9am–5pm JST"
        }
    },
    {
        "id": "site_tea_ancient_puerh_vault",
        "name": "Cloud Mist Tea Reserve",
        "tagline": "Rare Wild Arbor Aged Pu-erh and High Mountain Single-Garden Teas",
        "type": "tea",
        "prefix": "cm",
        "primary": "#171511",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#26221c",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Explore Tea Vault",
        "hero_sub": "Sun-dried wild tea leaves harvested from 500-year-old ancient arbor trees in Yunnan, naturally cellared under precision humidity.",
        "section_name": "Reserve Cakes & Loose Leaf",
        "section_id": "reserves",
        "items": [
            {"title": "2006 Bulang Mountain Raw Pu-erh (Sheng)", "tag": "Aged 20 Years", "desc": "Rich golden liquor with notes of wild dried plum, camphor, wet slate stone, and deep lingering sweet cha qi."},
            {"title": "Gufeng Ripe Pu-erh Brick (Shou)", "tag": "Traditional Wet Pile", "desc": "Thick burgundy brew offering smooth dark chocolate, aged oak barrel, forest petrichor, and zero bitterness."},
            {"title": "Alishan High Mountain Oolong", "tag": "Elevation 1800m", "desc": "Hand-picked whole rolled spheres unfurling with crisp gardenia floral notes, creamy butter, and fresh bamboo."},
            {"title": "Silver Needle White Tea (Bai Hao Yin Zhen)", "tag": "First Spring Pluck", "desc": "Pure unopened downy buds steeped to yield a delicate melon sweetness, honeysuckle, and silk mouthfeel."}
        ],
        "contact": {
            "address": "88 Cantonment Rd, Singapore 089769",
            "phone": "+65 6789 0122",
            "email": "curator@cloudmisttea.com",
            "hours": "Tue–Sun: 11am–8pm SGT"
        }
    },

    # 4. Creative Studios & Design Agencies
    {
        "id": "site_studio_vivid_3d_motion",
        "name": "Vivid Chroma Studio",
        "tagline": "Award-Winning 3D Motion Graphics, Title Design, and Visual Worlds",
        "type": "creative_agency",
        "prefix": "vc",
        "primary": "#0a0a0c",
        "accent": "#ec4899",
        "accent_hover": "#db2777",
        "surface": "#141419",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "View Showreel",
        "hero_sub": "We build kinetic digital identities, brand films, and surreal visual worlds using Cinema 4D, Houdini procedural simulations, and Redshift.",
        "section_name": "Studio Highlights",
        "section_id": "works",
        "items": [
            {"title": "Global Tech Keynote Title Sequence", "tag": "C4D & Redshift", "desc": "Opening cinematic journey weaving abstract silicon pathways and fluid chromatic refraction simulations."},
            {"title": "Procedural Houdini Brand Idents", "tag": "Cloth & Particle Vellum", "desc": "Hyper-realistic micro-simulations exploring fluid dynamics, tactile soft-body physics, and dynamic lighting."},
            {"title": "Luxury Fragrance Commercial CGI", "tag": "Photoreal Materials", "desc": "Microscopic botanical petal unfurling with photoreal caustics and atmospheric volumetric fog."},
            {"title": "Interactive WebGL 3D Canvas", "tag": "Three.js & GLSL", "desc": "Real-time shaders and reactive mouse-driven particle meshes engineered for modern digital flagship websites."}
        ],
        "contact": {
            "address": "439 N Canon Dr, Penthouse, Beverly Hills, CA 90210",
            "phone": "+1 (310) 555-0219",
            "email": "producer@vividchroma.tv",
            "hours": "Mon–Fri: 9:30am–6:30pm PST"
        }
    },
    {
        "id": "site_arch_viz_hyper_real",
        "name": "Atelier Lumos ArchViz",
        "tagline": "Photorealistic Architectural Visualization and Real-Time Immersive VR",
        "type": "architecture",
        "prefix": "al",
        "primary": "#121417",
        "accent": "#38bdf8",
        "accent_hover": "#0ea5e9",
        "surface": "#1b2026",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Commission Renderings",
        "hero_sub": "Breathing life into visionary masterplans, civic museums, and luxury residential towers with physically-accurate lighting and material textures.",
        "section_name": "Portfolio Studies",
        "section_id": "portfolio",
        "items": [
            {"title": "Nordic Cultural Pavilion", "tag": "Winter Twilight", "desc": "Warm timber interiors glowing against snow-covered landscapes with accurate ray-traced glass reflections."},
            {"title": "Canal-Side Residential High-Rise", "tag": "Golden Hour Sunlight", "desc": "Micro-faceted bronze cladding interacting with sunset water caustics and urban pedestrian atmospheres."},
            {"title": "Unreal Engine 5 Real-Time Tour", "tag": "Lumen & Nanite", "desc": "Fully interactive virtual reality walkthrough allowing clients to toggle interior finishes and daylight hours live."},
            {"title": "Drone Photogrammetry Integration", "tag": "Context Alignment", "desc": "Direct 3D compositing of proposed architectural forms into live high-resolution drone survey footage."}
        ],
        "contact": {
            "address": "Kungsbron 1, 111 22 Stockholm, Sweden",
            "phone": "+46 8 555 0190",
            "email": "projects@atelierlumos.se",
            "hours": "Mon–Fri: 8:30am–5:30pm CET"
        }
    },
    {
        "id": "site_audio_film_scoring_lab",
        "name": "Apex Sonic Scoring",
        "tagline": "Cinematic Orchestral Composition, Modular Synthesis, and Spatial Audio",
        "type": "sound_design",
        "prefix": "as",
        "primary": "#080b10",
        "accent": "#a855f7",
        "accent_hover": "#9333ea",
        "surface": "#111620",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Listen to Showreel",
        "hero_sub": "Custom music scores combining 80-piece live symphonic orchestras with rare vintage Eurorack modular synths and Dolby Atmos spatial mastering.",
        "section_name": "Scoring Works",
        "section_id": "works",
        "items": [
            {"title": "Sci-Fi Feature Original Score", "tag": "London Symphony Orchestra", "desc": "Haunting low-brass clusters intertwined with Buchla 200e analog modular synthesis and microtonal cello solos."},
            {"title": "Documentary Series Theme Suite", "tag": "Acoustic Folk Strings", "desc": "Intimate Norwegian hardanger fiddle, hammered dulcimer, and field recordings captured across the Arctic Circle."},
            {"title": "AAA Game Dynamic Music System", "tag": "Interactive Wwise/FMOD", "desc": "Multi-tiered adaptive stem compositions shifting dynamically between ambient exploration and high-intensity battle."},
            {"title": "Dolby Atmos 7.1.4 Spatial Mixing", "tag": "Avid Pro Tools HDX", "desc": "Precision spatial placement of sonic elements creating an immersive three-dimensional acoustic soundstage."}
        ],
        "contact": {
            "address": "1024 N Orange Dr, Los Angeles, CA 90038",
            "phone": "+1 (323) 555-0220",
            "email": "studio@apexsonicscoring.com",
            "hours": "24/7 Production by Project Schedule"
        }
    },
    {
        "id": "site_brand_collective_monolith",
        "name": "Monolith Brand Collective",
        "tagline": "Disruptive Identity Systems and Custom Typography for Global Innovators",
        "type": "branding",
        "prefix": "mc",
        "primary": "#0f0f12",
        "accent": "#fafafa",
        "accent_hover": "#e4e4e7",
        "surface": "#1a1a21",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Inquire for Q3",
        "hero_sub": "We sculpt brand architectures, bespoke variable typefaces, and distinctive graphic systems for visionary tech and lifestyle ventures.",
        "section_name": "Selected Case Studies",
        "section_id": "cases",
        "items": [
            {"title": "Fintech Decacorn Visual Rebrand", "tag": "Brand Architecture", "desc": "Unified design system covering product UI, corporate livery, guidelines, and custom financial typography."},
            {"title": "Autonomous EV Brand Identity", "tag": "Variable Font & Symbol", "desc": "Custom multi-axis variable typeface engineered for optimal legibility across automotive HUDs and billboards."},
            {"title": "Sustainable Fashion House Packaging", "tag": "Mushroom Mycelium Box", "desc": "Minimalist unbleached biodegradable packaging system embossed with vegetable soy inks."},
            {"title": "Digital Flagship Design System", "tag": "Component Tokens", "desc": "Comprehensive Figma token libraries and guidelines synchronizing engineering codebases with brand design."}
        ],
        "contact": {
            "address": "120 Wooster St, New York, NY 10012",
            "phone": "+1 (212) 555-0221",
            "email": "hello@monolithcollective.design",
            "hours": "Mon–Fri: 9am–6pm EST"
        }
    },
    {
        "id": "site_lighting_architectural_lumen",
        "name": "Lumen & Shade Lighting",
        "tagline": "Museum-Grade Architectural Lighting Design and Daylight Engineering",
        "type": "lighting_design",
        "prefix": "ls",
        "primary": "#121110",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
        "surface": "#1f1d1b",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Consult Lighting Team",
        "hero_sub": "Balancing illumination, shadows, and circadian rhythms for art museums, heritage cathedrals, and private estates.",
        "section_name": "Signature Projects",
        "section_id": "projects",
        "items": [
            {"title": "Metropolitan Art Gallery Wing", "tag": "CRI 98+ Zero UV", "desc": "Custom tunable white LED fixtures with precision framing projectors to reveal true paint pigment vitality."},
            {"title": "Gothic Cathedral Illumination", "tag": "Concealed DMX Controls", "desc": "Architecturally integrated graze luminaires highlighting vaulted stone ribs without visible conduit runs."},
            {"title": "Luxury Penthouse Circadian System", "tag": "Dynamic Kelvin Tuning", "desc": "Automated solar tracking shifting from crisp 4500K morning light to warm 1800K candle warmth at night."},
            {"title": "Outdoor Botanical Garden Light Trail", "tag": "IP68 Dark Sky Compliant", "desc": "Low-level shielded luminaires guiding night walkers while protecting nocturnal insect and bird habitats."}
        ],
        "contact": {
            "address": "77 King St W, Suite 4000, Toronto, ON M5K 0A1, Canada",
            "phone": "+1 (416) 555-0222",
            "email": "lighting@lumenshade.com",
            "hours": "Mon–Fri: 8:30am–5:30pm EST"
        }
    },
    {
        "id": "site_vfx_virtual_production",
        "name": "Hyperion Virtual Stages",
        "tagline": "Real-Time In-Camera VFX and Curved LED Volume Stages",
        "type": "film_production",
        "prefix": "hv",
        "primary": "#08090d",
        "accent": "#00f0ff",
        "accent_hover": "#00c8d6",
        "surface": "#11141d",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Book Stage Time",
        "hero_sub": "Shoot realistic international locations on our 180-degree Roe Visual LED wall with live camera tracking and photoreal Unreal Engine 5 backgrounds.",
        "section_name": "Stage Capabilities",
        "section_id": "capabilities",
        "items": [
            {"title": "180° MicroLED Volume Stage", "tag": "1.5mm Pixel Pitch", "desc": "Curved 60ft x 20ft LED wall paired with motorized motorized LED ceiling panels for realistic interactive reflections."},
            {"title": "Sub-Millimeter Camera Tracking", "tag": "Stype & Mo-Sys", "desc": "Optical marker arrays synchronizing cinema camera movements with real-time viewport perspective shifts."},
            {"title": "Real-Time Unreal Engine 5 Environments", "tag": "Nanite & Lumen", "desc": "Physically accurate virtual environments running at locked 60fps genlocked to camera shutter angles."},
            {"title": "On-Set Live DIT & Color Grading", "tag": "ACES Pipeline", "desc": "Real-time color matching between practical stage foreground props and digital background LED panels."}
        ],
        "contact": {
            "address": "5700 Wilshire Blvd, Suite 100, Los Angeles, CA 90036",
            "phone": "+1 (323) 555-0223",
            "email": "stages@hyperionvfx.com",
            "hours": "24/7 Production Availability"
        }
    },

    # 5. Hospitality, Leisure & Wellness
    {
        "id": "site_chalet_alpen_solitude",
        "name": "Chalet Alpen Solitude",
        "tagline": "Ski-In Ski-Out Timber Chalet in the Swiss Alps with Private Spa",
        "type": "hospitality",
        "prefix": "ca",
        "primary": "#191512",
        "accent": "#e0a96d",
        "accent_hover": "#c89357",
        "surface": "#27211d",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Reserve Chalet",
        "hero_sub": "Hand-hewn larch wood beams, panoramic Matterhorn views, private Finnish sauna, heated infinity pool, and a private culinary chef.",
        "section_name": "Chalet Amenities",
        "section_id": "amenities",
        "items": [
            {"title": "Ski-In / Ski-Out Access", "tag": "Direct Slope Entry", "desc": "Step straight from heated boot-drying rooms onto pristine groomed alpine runs with personal ski butler."},
            {"title": "Private Alpine Wellness Spa", "tag": "Cedar & Granite", "desc": "Panoramic Finnish sauna, outdoor heated cedar hot tub overlooking snow-clad peaks, and steam room."},
            {"title": "Dedicated Private Chef Service", "tag": "Farm-to-Table", "desc": "Multi-course evening dinners paired with regional Swiss Valais wines prepared fresh in your open kitchen."},
            {"title": "Grand Stone Fireplace Lounge", "tag": "Firewood & Views", "desc": "Expansive cathedral ceilings with floor-to-ceiling glass windows capturing pink alpine glow at sunset."}
        ],
        "contact": {
            "address": "Riedweg 45, 3920 Zermatt, Switzerland",
            "phone": "+41 27 966 88 00",
            "email": "concierge@alpensolitude.ch",
            "hours": "24/7 Guest Concierge Services"
        }
    },
    {
        "id": "site_train_silk_road_express",
        "name": "Silk Road Grand Express",
        "tagline": "Luxury Heritage Sleeper Train Voyages Traversing the Ancient Silk Road",
        "type": "travel",
        "prefix": "sr",
        "primary": "#141016",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#221a25",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "View Itineraries",
        "hero_sub": "Mahogany-paneled private suites, crystal dining cars, and guided explorations through Samarkand, Bukhara, and the oasis cities of Central Asia.",
        "section_name": "Voyage Highlights",
        "section_id": "voyages",
        "items": [
            {"title": "Imperial Suite Carriage", "tag": "Private Ensuite", "desc": "Spacious double bedroom with brass bedstead, private hot shower, writing desk, and dedicated 24-hour steward."},
            {"title": "Fine Dining Car 'Samarkand'", "tag": "Culinary Journey", "desc": "White linen silver service serving regional saffron lamb plov, Caspian caviar, and Georgian vintage wines."},
            {"title": "Observation Lounge & Bar", "tag": "Pianist & Cocktails", "desc": "Panoramic bay windows with nightly live classical piano performances as desert dunes sweep past."},
            {"title": "Private Architectural Excursions", "tag": "Historian Led", "desc": "Skip-the-line guided visits to turquoise tiled madrasas, ancient desert fortresses, and spice bazaars."}
        ],
        "contact": {
            "address": "16 St James's St, London SW1A 1ER, UK",
            "phone": "+44 20 7946 0777",
            "email": "reservations@silkroadexpress.com",
            "hours": "Mon–Fri: 9am–6pm GMT"
        }
    },
    {
        "id": "site_lodge_savanna_canopy",
        "name": "Savanna Canopy Eco-Lodge",
        "tagline": "Off-Grid Solar Luxury Treetop Lodge in the Okavango Delta",
        "type": "safari",
        "prefix": "sc",
        "primary": "#161611",
        "accent": "#84cc16",
        "accent_hover": "#65a30d",
        "surface": "#23231b",
        "heading_font": "DM Sans",
        "body_font": "Inter",
        "cta": "Book Safari Stay",
        "hero_sub": "Raised wooden decks immersed in ancient leadwood trees, silent solar-electric game drive cruisers, and uninterrupted views of elephant herds.",
        "section_name": "Lodge Experiences",
        "section_id": "experiences",
        "items": [
            {"title": "Canopy Tented Suites", "tag": "Canopy Height 8m", "desc": "Expansive canvas pavilions with outdoor open-air soaking tubs and wrap-around viewing decks over the floodplains."},
            {"title": "Silent Electric Game Drives", "tag": "Zero Emissions", "desc": "Approach prides of lions and rare African wild dogs in whisper-quiet 4x4 electric vehicles without engine roar."},
            {"title": "Traditional Mokoro Water Trails", "tag": "Gliding Safari", "desc": "Drift along crystal channels navigated by skilled local polers to observe waterlilies and reed frogs."},
            {"title": "Star Bed Sleepout Deck", "tag": "Open Night Sky", "desc": "Spend a night beneath the Southern Cross galaxy on a private raised open-air platform deep in the reserve."}
        ],
        "contact": {
            "address": "Okavango Delta Concession NG32, Maun, Botswana",
            "phone": "+267 686 1234",
            "email": "reservations@savannacanopy.com",
            "hours": "Mon–Sun: 7am–7pm CAT"
        }
    },
    {
        "id": "site_matcha_kyoto_ceremony",
        "name": "Kyoto Kanso Tea House",
        "tagline": "Single-Cultivar Ceremonial Matcha and Minimalist Japanese Tea Garden",
        "type": "tea_house",
        "prefix": "kk",
        "primary": "#141713",
        "accent": "#22c55e",
        "accent_hover": "#16a34a",
        "surface": "#1f241d",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Reserve Tea Ceremony",
        "hero_sub": "Shade-grown tencha stone-ground before your eyes, whisked with spring water, and served in hand-carved Raku bowls beside a tranquil moss garden.",
        "section_name": "Ceremonial Offerings",
        "section_id": "offerings",
        "items": [
            {"title": "Asahi Single-Cultivar Matcha", "tag": "Uji Heritage", "desc": "Vibrant emerald green bowl with profound umami sweetness, creamy texture, and zero astringency."},
            {"title": "Traditional Chado Ceremony", "tag": "60 Minutes", "desc": "Guided meditative tea ceremony in an authentic tatami room observing ancestral four principles of harmony and respect."},
            {"title": "Seasonal Handmade Wagashi", "tag": "Daily Artisan", "desc": "Sculptural confections of sweetened white bean paste and seasonal fruit designed to complement matcha depth."},
            {"title": "Stone-Ground Workshop", "tag": "Granite Mill", "desc": "Experience turning a heavy granite mill to crush raw tencha leaves into microscopic silk green matcha powder."}
        ],
        "contact": {
            "address": "52 Higashiyama-ku, Kyoto 605-0001, Japan",
            "phone": "+81 75 561 0988",
            "email": "welcome@kyotokanso.jp",
            "hours": "Wed–Mon: 10am–6pm JST (Closed Tuesdays)"
        }
    },
    {
        "id": "site_bathhouse_nordic_sauna",
        "name": "Nordic Fjord Bathhouse",
        "tagline": "Traditional Birch Whisk Saunas, Cold Plunge, and Geothermal Mineral Baths",
        "type": "wellness",
        "prefix": "nf",
        "primary": "#111618",
        "accent": "#06b6d4",
        "accent_hover": "#0891b2",
        "surface": "#1b2326",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Book Bathhouse Pass",
        "hero_sub": "Rejuvenate your body through authentic thermal contrast therapy: 90°C smoke saunas followed by 4°C natural ice river plunges.",
        "section_name": "Thermal Circuit",
        "section_id": "circuit",
        "items": [
            {"title": "Authentic Smoke Sauna (Savusauna)", "tag": "90°C Dry Heat", "desc": "Wood-fired stone hearth infusing gentle thermal waves and natural birch wood smoke aromas."},
            {"title": "Glacial Fjord Cold Plunge", "tag": "4°C Deep Reset", "desc": "Continuous circulation cold plunge pools triggering immediate vasoconstriction and dopamine release."},
            {"title": "Geothermal Mineral Soak", "tag": "38°C Salt Rich", "desc": "Subterranean geothermal pools infused with magnesium and dead sea mineral salts to dissolve muscle tension."},
            {"title": "Aufguss Sauna Ritual", "tag": "Essential Oils", "desc": "Sauna master wafting aromatic steam towel choreography with pine, eucalyptus, and lavender snowballs."}
        ],
        "contact": {
            "address": "Fjordveien 12, 5003 Bergen, Norway",
            "phone": "+47 55 21 00 90",
            "email": "booking@nordicfjordbath.no",
            "hours": "Daily: 7am–10pm CET"
        }
    },
    {
        "id": "site_retreat_zen_monastery",
        "name": "Cloud Peak Zen Sanctuary",
        "tagline": "Silent Mindfulness Retreats and Mountain Forest Meditation",
        "type": "retreat",
        "prefix": "cp",
        "primary": "#161513",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#23211e",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Apply for Retreat",
        "hero_sub": "Unplug from digital noise with silent Zazen meditation, mindful vegetarian temple cuisine, and contemplative walks through ancient pine ridges.",
        "section_name": "Sanctuary Programs",
        "section_id": "programs",
        "items": [
            {"title": "7-Day Silent Zazen Retreat", "tag": "Total Digital Detox", "desc": "Structured sitting and walking meditation cycles in quiet cedar halls guided by resident Zen practitioners."},
            {"title": "Shojin Ryori Temple Dining", "tag": "Pure Vegetarian", "desc": "Mindfully prepared seasonal vegan meals emphasizing local mushrooms, mountain roots, and fresh handmade tofu."},
            {"title": "Kin-hin Pine Forest Walking", "tag": "Walking Meditation", "desc": "Deliberate rhythmic walking meditation on forested mountain ridges listening to wind and stream waters."},
            {"title": "One-on-One Dokusan Dialogues", "tag": "Personal Guidance", "desc": "Private interviews with senior teachers to investigate personal mindfulness practice and inquiry."}
        ],
        "contact": {
            "address": "4500 Cloud Peak Trail, Big Sur, CA 93920",
            "phone": "+1 (831) 555-0224",
            "email": "admissions@cloudpeakzen.org",
            "hours": "Resident Retreats Open Year-Round"
        }
    },
    {
        "id": "site_vineyard_domaine_solis",
        "name": "Domaine Solis Biodynamic Wines",
        "tagline": "Wild-Fermented Amphora Wines from Sun-Drenched Provencal Terraces",
        "type": "winery",
        "prefix": "ds",
        "primary": "#171214",
        "accent": "#e11d48",
        "accent_hover": "#be123c",
        "surface": "#261d21",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Book Vineyard Tasting",
        "hero_sub": "Zero-intervention natural wines aged in terracotta amphorae and French oak casks, harvested by hand under celestial moon cycles.",
        "section_name": "Estate Vintages",
        "section_id": "vintages",
        "items": [
            {"title": "Cuvée Terra Cotta 2021", "tag": "Amphora Aged", "desc": "Old-vine Grenache and Syrah macerated on skins in porous clay jars, yielding notes of crushed blackberry and wild thyme."},
            {"title": "Blanc de Gypse 2023", "tag": "Limestone Soil", "desc": "Rolle and Roussanne with laser-like mineral tension, white peach blossom, and saline maritime finish."},
            {"title": "Rosé Pét-Nat Ancestral", "tag": "Naturally Sparkling", "desc": "Unfiltered cloudy sparkling rosé bottled during primary fermentation with vibrant wild strawberry and crisp lime zest."},
            {"title": "Private Cellar Degustation", "tag": "Cave Tasting", "desc": "Tasting flight of six rare library vintages paired with local artisanal goat cheeses in our subterranean barrel vault."}
        ],
        "contact": {
            "address": "Route des Maures, 83680 La Garde-Freinet, France",
            "phone": "+33 4 94 43 20 10",
            "email": "domaine@domainesolis.fr",
            "hours": "Tue–Sun: 10am–6pm CET"
        }
    },
    {
        "id": "site_resort_coral_atoll_overwater",
        "name": "Solitude Atoll Private Island",
        "tagline": "Solar-Powered Overwater Villas and Marine Bio-Sanctuary in the Maldives",
        "type": "resort",
        "prefix": "sa",
        "primary": "#08131a",
        "accent": "#00f0ff",
        "accent_hover": "#00c8d6",
        "surface": "#10212d",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Reserve Villa",
        "hero_sub": "Float above a living coral reef in glass-floored luxury pavilions powered 100% by offshore solar arrays and silent desalination.",
        "section_name": "Resort Highlights",
        "section_id": "highlights",
        "items": [
            {"title": "Grand Overwater Lagoon Villa", "tag": "Private Infinity Pool", "desc": "Direct stairs into turquoise lagoon, retractable glass bedroom roof for stargazing, and private catamaran hammock."},
            {"title": "Subsurface Dining Room", "tag": "6m Below Sea", "desc": "Dine surrounded by reef sharks and sea turtles through 180-degree curved acrylic viewing domes."},
            {"title": "Manta Ray Night Snorkeling", "tag": "Marine Biologist Led", "desc": "Swim alongside feeding giant oceanic manta rays illuminated under soft blue bioluminescent lights."},
            {"title": "Ayurvedic Water Spa", "tag": "Open Ocean Pavilions", "desc": "Holistic treatments featuring virgin coconut oils and warm ocean salt compresses over the gentle sound of waves."}
        ],
        "contact": {
            "address": "Baa Atoll Biosphere Reserve, Republic of Maldives",
            "phone": "+960 660 8899",
            "email": "escape@solitudeatoll.com",
            "hours": "24/7 Island Concierge & Seaplane Transfer"
        }
    },

    # 6. Modern Engineering, Services & Sustainable Tech
    {
        "id": "site_solar_microgrid_energy",
        "name": "TerraVolt Microgrids",
        "tagline": "Autonomous Commercial Microgrids and Industrial Iron-Flow Battery Storage",
        "type": "clean_energy",
        "prefix": "tv",
        "primary": "#0c1514",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "surface": "#162422",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Request Feasibility Study",
        "hero_sub": "Insulate your enterprise from grid blackouts and peak demand surcharges with automated on-site solar generation and 12-hour duration battery systems.",
        "section_name": "System Architecture",
        "section_id": "architecture",
        "items": [
            {"title": "Industrial Iron-Flow Batteries", "tag": "20,000 Cycles Zero Fade", "desc": "Non-flammable, non-toxic electrolyte storage providing 12+ hours of continuous full-load factory operation."},
            {"title": "Bifacial Solar Canopies", "tag": "Tier-1 Photovoltaics", "desc": "High-efficiency double-sided solar arrays harvesting direct sunlight and pavement albedo reflection."},
            {"title": "Sub-16ms Islanding Switchgear", "tag": "Zero Flicker", "desc": "Instantaneous automatic transition from utility grid to islanded mode during unexpected blackouts without data center interruption."},
            {"title": "AI Peak Shaving Dispatch", "tag": "Automated FinOps", "desc": "Predictive algorithms discharging stored energy during peak utility tariff hours to slash utility bills by up to 60%."}
        ],
        "contact": {
            "address": "4401 E 52nd Ave, Denver, CO 80216",
            "phone": "+1 (303) 555-0225",
            "email": "grids@terravoltenergy.com",
            "hours": "Mon–Fri: 8am–6pm MST"
        }
    },
    {
        "id": "site_yacht_electric_marine",
        "name": "Voltaic Marine Hydrofoils",
        "tagline": "Zero-Emission Hydrofoil Electric Yachts Flying Above the Waves",
        "type": "maritime",
        "prefix": "vm",
        "primary": "#070e17",
        "accent": "#38bdf8",
        "accent_hover": "#0ea5e9",
        "surface": "#101927",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Schedule Sea Trial",
        "hero_sub": "Computer-controlled underwater carbon wings lift the hull clear of the sea, reducing hydrodynamic drag by 80% for silent 35-knot cruising.",
        "section_name": "Yacht Features",
        "section_id": "features",
        "items": [
            {"title": "Computer-Stabilized Carbon Foils", "tag": "100Hz Sensor Loop", "desc": "Autonomous flight control adjusting foil angles 100 times per second to eliminate sea sickness and slamming."},
            {"title": "Dual Liquid-Cooled Pod Motors", "tag": "Silent Propulsion", "desc": "Submerged electric pods generating zero wake, zero exhaust smell, and whisper-quiet operation across marine sanctuaries."},
            {"title": "120kWh Marine Battery System", "tag": "IP67 High Density", "desc": "Waterproof automotive-grade lithium battery pack with DC fast charging replenishing 80% charge in 35 minutes."},
            {"title": "Carbon Fiber Monocoque Hull", "tag": "Pre-Preg Autoclave", "desc": "Ultra-rigid lightweight carbon sandwich construction with minimalist Scandinavian teak deck styling."}
        ],
        "contact": {
            "address": "Port Hercule, 98000 Monaco",
            "phone": "+377 93 50 12 34",
            "email": "yachts@voltaicmarine.mc",
            "hours": "Mon–Sat: 9am–6:30pm CET"
        }
    },
    {
        "id": "site_leather_artisan_saddlery",
        "name": "Oak & Awl Leatherworks",
        "tagline": "Traditional Saddle-Stitched Full-Grain Leather Goods Built for Generations",
        "type": "leather_craft",
        "prefix": "oa",
        "primary": "#18130f",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#271f1a",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Explore Leather Goods",
        "hero_sub": "Hand-cut vegetable-tanned Italian bridle leathers sewn with twin harness needles and waxed Irish linen thread with burnished beeswax edges.",
        "section_name": "Atelier Goods",
        "section_id": "goods",
        "items": [
            {"title": "Traditional English Bridle Briefcase", "tag": "Solid Brass Hardware", "desc": "Classic structured silhouette with solid sand-cast brass lock, reinforced handle, and lifetime repair guarantee."},
            {"title": "Minimalist Bifold Card Wallet", "tag": "Horween Shell Cordovan", "desc": "Dense equine leather that will never crease or peel, developing an extraordinary mirror-like gloss patina."},
            {"title": "Heritage Field Duffel Bag", "tag": "20oz Heavy Canvas & Leather", "desc": "Water-resistant waxed cotton canvas trimmed with heavy 9oz harness leather and indestructible Riri zippers."},
            {"title": "Bespoke Belt Customization", "tag": "Hand Burnished", "desc": "Cut to your exact waist measurement with hand-stitched leather keeper and solid nickel or antique brass buckle."}
        ],
        "contact": {
            "address": "742 Commercial St, Emporia, KS 66801",
            "phone": "+1 (620) 555-0226",
            "email": "orders@oakandawl.com",
            "hours": "Tue–Sat: 10am–6pm CST"
        }
    },
    {
        "id": "site_acoustics_soundproofing_pro",
        "name": "Decibel Zero Studio Acoustics",
        "tagline": "Floating Room-in-Room Acoustic Isolation and Precision Studio Design",
        "type": "acoustics",
        "prefix": "dz",
        "primary": "#0e1014",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
        "surface": "#181b22",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Request Studio Survey",
        "hero_sub": "Eliminate subway rumble and street traffic with calibrated elastomeric spring floating floors, double stud isolation, and tuned membrane bass traps.",
        "section_name": "Engineering Services",
        "section_id": "services",
        "items": [
            {"title": "Floating Room-in-Room Isolation", "tag": "STC 75+ Rating", "desc": "Completely decoupled concrete slab floating on calibrated elastomeric springs to halt subterranean structure-borne noise."},
            {"title": "Custom Tuned Helmholtz Resonators", "tag": "Sub-40Hz Control", "desc": "Targeted narrow-band acoustic resonators eliminating problematic room standing waves and modal boominess."},
            {"title": "Bespoke Quadratic Diffusers", "tag": "QRD Mathematical", "desc": "Solid timber diffusers scattering acoustic reflections evenly to preserve natural room life and stereo imaging."},
            {"title": "Acoustic Noise Commissioning", "tag": "NC-15 Certified", "desc": "High-precision sound level meter surveys certifying HVAC silencers and mechanical acoustic compliance."}
        ],
        "contact": {
            "address": "285 Franklin St, Nashville, TN 37204",
            "phone": "+1 (615) 555-0227",
            "email": "acoustics@decibelzerolabs.com",
            "hours": "Mon–Fri: 8am–6pm CST"
        }
    },
    {
        "id": "site_neon_artisan_glassworks",
        "name": "Luminescent Neon Works",
        "tagline": "Hand-Bent Glass Argon and Neon Sculptures for Architectural Spaces",
        "type": "neon_art",
        "prefix": "ln",
        "primary": "#08090f",
        "accent": "#ec4899",
        "accent_hover": "#db2777",
        "surface": "#121524",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Commission Neon Art",
        "hero_sub": "Master glassblowers heating lead glass over ribbon fires, hand-bending fluid forms, and filling tubes with pure noble gases that glow forever.",
        "section_name": "Sculptural Works",
        "section_id": "works",
        "items": [
            {"title": "Custom Architectural Neon Installations", "tag": "Argon & Mercury Glow", "desc": "Large-scale linear glass installations tailored to wrap around staircases, gallery atriums, and hospitality venues."},
            {"title": "Bespoke Typography Signage", "tag": "True Glass Craft", "desc": "Crisp cursive and geometric letterforms bent from single continuous glass tubes with solid silicone transformers."},
            {"title": "Cold-Cathode Commercial Lighting", "tag": "50,000hr Lifespan", "desc": "Dimming-compatible architectural cove lighting emitting rich warm 2200K vintage amber glow."},
            {"title": "Historic Neon Restoration", "tag": "Tube Repumping", "desc": "Rewiring vintage roadside signs, replacing degraded electrodes, and evacuating air with high-voltage bombardment."}
        ],
        "contact": {
            "address": "1040 N Miami Ave, Miami, FL 33136",
            "phone": "+1 (305) 555-0228",
            "email": "atelier@luminescentneon.com",
            "hours": "Mon–Fri: 10am–7pm EST"
        }
    },
    {
        "id": "site_bike_aerodynamic_fit_lab",
        "name": "Velocita Aerodynamic Fit Lab",
        "tagline": "Wind-Tunnel Validated Bike Fitting and Custom Carbon Frame Geometry",
        "type": "cycling",
        "prefix": "va",
        "primary": "#0d1017",
        "accent": "#22c55e",
        "accent_hover": "#16a34a",
        "surface": "#181d29",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Schedule Aero Fitting",
        "hero_sub": "Optimize your coefficient of aerodynamic drag (CdA) using 3D motion sensors, saddle pressure mapping, and real-time wind speed telemetry.",
        "section_name": "Fitting Modules",
        "section_id": "modules",
        "items": [
            {"title": "3D Dynamic Motion Capture Fit", "tag": "Retül 3D Sensors", "desc": "Real-time LED infrared tracking of knee extension, hip angle, and ankle tilt across changing wattage loads."},
            {"title": "GebioMized Saddle Pressure Mapping", "tag": "64 Sensor Array", "desc": "Eliminate pelvic numbness and hot spots through calibrated visual pressure heatmaps across multiple saddle shapes."},
            {"title": "Aero Drag Optimization (CdA)", "tag": "Virtual Wind Tunnel", "desc": "Aerobar position titration shaving up to 25 watts of aerodynamic resistance over 40-kilometer time trials."},
            {"title": "Custom Molded Carbon Insoles", "tag": "Custom Footbeds", "desc": "Thermal molded orthotics stabilizing the medial arch for direct uncompromised power transfer through pedal strokes."}
        ],
        "contact": {
            "address": "2500 6th St, Boulder, CO 80304",
            "phone": "+1 (303) 555-0229",
            "email": "fit@velocitalab.com",
            "hours": "Mon–Sat: 8am–6pm MST"
        }
    },
    {
        "id": "site_drone_lidar_mapping",
        "name": "GeoScan Aerial LiDAR",
        "tagline": "Survey-Grade UAV Airborne LiDAR and Volumetric Topographic Surveys",
        "type": "geospatial",
        "prefix": "gs",
        "primary": "#0b1219",
        "accent": "#0ea5e9",
        "accent_hover": "#0284c7",
        "surface": "#14202d",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Request Drone Survey",
        "hero_sub": "Deploying dual-frequency RTK enterprise drones equipped with triple-return lasers capable of penetrating dense forest canopies with 2cm accuracy.",
        "section_name": "Survey Solutions",
        "section_id": "solutions",
        "items": [
            {"title": "Dense Canopy Penetration LiDAR", "tag": "Triple Return", "desc": "Capture true bare-earth digital terrain models (DTM) through heavy brush and forest foliage."},
            {"title": "Quarry & Earthwork Volumetrics", "tag": "Cut & Fill Calculations", "desc": "Accurate calculation of stockpiles, excavation volumes, and site mass balance within 48 hours of flight."},
            {"title": "High-Voltage Utility Corridor Inspection", "tag": "Thermal & RGB", "desc": "Detect vegetation encroachment, thermal hotspots on transformers, and structural wire sag anomalies."},
            {"title": "Millimeter Orthomosaic Generation", "tag": "Sub-Centimeter GSD", "desc": "High-resolution georeferenced aerial maps compatible with ArcGIS, AutoCAD Civil 3D, and QGIS."}
        ],
        "contact": {
            "address": "1100 Lincoln Mall, Suite 400, Lincoln, NE 68508",
            "phone": "+1 (402) 555-0230",
            "email": "surveys@geoscanlidar.com",
            "hours": "Mon–Fri: 7am–5pm CST"
        }
    },
    {
        "id": "site_hydroponics_urban_harvest",
        "name": "Verdant Tower Aeroponics",
        "tagline": "Vertical Aeroponic Micro-Farming Delivering Greens within Hours of Harvest",
        "type": "agriculture",
        "prefix": "vt",
        "primary": "#0f1712",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "surface": "#19261e",
        "heading_font": "DM Sans",
        "body_font": "Inter",
        "cta": "Order Wholesale Harvest",
        "hero_sub": "Using 95% less water than soil agriculture, our enclosed sterile vertical towers mist plant roots with oxygenated nutrient waters under full-spectrum LEDs.",
        "section_name": "Fresh Harvests",
        "section_id": "harvests",
        "items": [
            {"title": "Artisanal Butterhead Bibb Lettuce", "tag": "Harvested Live Roots", "desc": "Tender crisp leaves delivered with roots intact in fresh water for weeks of sweet, pesticide-free crispness."},
            {"title": "Spicy Microgreen Medley", "tag": "7-Day Growth Cycle", "desc": "Vibrant blend of radish, red cabbage, broccoli, and pea tendrils packed with 40x higher nutrient density."},
            {"title": "Genovese Sweet Basil Towers", "tag": "Intense Essential Oils", "desc": "Deep green fragrant basil leaves grown without chemical sprays, packed same-day for local pizzerias and bistros."},
            {"title": "Chefs Tasting Subscription", "tag": "Delivered Twice Weekly", "desc": "Curated selection of edible nasturtium flowers, baby sorrel, and rare brassicas direct to restaurant kitchens."}
        ],
        "contact": {
            "address": "620 S 3rd St, Brooklyn, NY 11211",
            "phone": "+1 (718) 555-0231",
            "email": "greens@verdanttower.farm",
            "hours": "Mon–Sat: 6am–4pm EST"
        }
    },
    {
        "id": "site_restoration_midcentury_modern",
        "name": "Nordic Heritage Restorations",
        "tagline": "Restoration of Iconic Danish Teak and Mid-Century Modern Furniture",
        "type": "furniture_restoration",
        "prefix": "nh",
        "primary": "#191411",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#261e1a",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Inquire for Restoration",
        "hero_sub": "Reviving original Arne Jacobsen chairs, Hans Wegner cord seats, and Finn Juhl floating tables using traditional joinery and natural hand-rubbed oil finishes.",
        "section_name": "Restoration Specialities",
        "section_id": "specialities",
        "items": [
            {"title": "Danish Paper Cord Weaving", "tag": "Hans Wegner Certified", "desc": "Authentic L-weaves and envelope patterns woven tight using 3-ply unbleached natural Danish paper cord."},
            {"title": "Solid Brazilian Rosewood & Teak Refinishing", "tag": "Hand-Rubbed Danish Oil", "desc": "Gentle scraping to preserve factory veneer thickness followed by multi-coat natural oxidising oil finishes."},
            {"title": "Molded Plywood Structural Repair", "tag": "Vacuum Press Relamination", "desc": "Rebonding delaminated veneers and cracked shock mounts on vintage Eames lounge chairs with original specs."},
            {"title": "Period-Correct Wool Upholstery", "tag": "Kvadrat Textiles", "desc": "Complete rebuilds using horsehair, jute webbing, and architectural wools from iconic Scandinavian textile mills."}
        ],
        "contact": {
            "address": "1420 NW Lovejoy St, Portland, OR 97209",
            "phone": "+1 (503) 555-0232",
            "email": "restoration@nordicheritage.com",
            "hours": "Tue–Sat: 10am–5:30pm PST"
        }
    },
    {
        "id": "site_coffee_single_origin_lab",
        "name": "Meridian Coffee Roasters",
        "tagline": "Direct-Trade Micro-Lot Coffees Roasted on Cast Iron Probat Drums",
        "type": "coffee_roastery",
        "prefix": "mr",
        "primary": "#161210",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
        "surface": "#241d1a",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Subscribe to Roaster's Choice",
        "hero_sub": "Sourcing rare anaerobic Gesha beans, natural Ethiopian heirlooms, and slow-fermented Kenyan microlots roasted light to celebrate terroir.",
        "section_name": "Current Microlots",
        "section_id": "microlots",
        "items": [
            {"title": "Panama Boquete Geisha Anaerobic", "tag": "Elevation 1900m", "desc": "Explosive floral jasmine aroma, bergamot tea, white peach, and sparkling champagne acidity."},
            {"title": "Ethiopia Yirgacheffe Idido Natural", "tag": "Heirloom Varietals", "desc": "Intense blueberry jam, ripe papaya sweetness, candied lemon zest, and a silken milk chocolate body."},
            {"title": "Kenya Nyeri Hill SL28 Peaberry", "tag": "Washed Double Ferment", "desc": "Bright blackcurrant, ruby red grapefruit, brown sugar complexity, and a crisp phosphoric finish."},
            {"title": "Cold Brew Reserve Concentrate", "tag": "Steeped 24 Hours", "desc": "Slow room-temperature steeped concentrate highlighting dark stone fruit and Dutch cocoa without bitterness."}
        ],
        "contact": {
            "address": "333 11th Ave E, Seattle, WA 98102",
            "phone": "+1 (206) 555-0233",
            "email": "beans@meridianroasters.com",
            "hours": "Daily: 6:30am–6pm PST"
        }
    },
    {
        "id": "site_climbing_summit_bouldering",
        "name": "Summit Vault Bouldering Gym",
        "tagline": "Olympic-Standard Bouldering Walls, Tension Boards, and Athlete Training",
        "type": "fitness",
        "prefix": "sv",
        "primary": "#111217",
        "accent": "#f43f5e",
        "accent_hover": "#e11d48",
        "surface": "#1a1c24",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Buy Day Pass",
        "hero_sub": "Over 15,000 square feet of unbroken climbing terrain, adjustable LED Kilter and Tension boards, campus rungs, and continuous air purification.",
        "section_name": "Facility Highlights",
        "section_id": "facility",
        "items": [
            {"title": "Competition Bouldering Wall", "tag": "IFSC Certified Angles", "desc": "Steep 45-degree roof sections and delicate technical slabs reset weekly by national-level route setters."},
            {"title": "Adjustable LED Kilter & Tension Boards", "tag": "App Controlled 0–70°", "desc": "Thousands of standardized benchmark problems with smart LED hold illumination for progressive finger training."},
            {"title": "Athlete Recovery Suite", "tag": "Sauna & Cold Plunge", "desc": "Post-session dry sauna, cold plunge tubs, and foam rolling zones designed to accelerate forearm recovery."},
            {"title": "Introductory Movement Classes", "tag": "Beginner Friendly", "desc": "Small group sessions teaching heel hooks, drop knees, body tension, and safe dynamic falling mechanics."}
        ],
        "contact": {
            "address": "400 S Temple St, Salt Lake City, UT 84111",
            "phone": "+1 (801) 555-0234",
            "email": "climb@summitvaultbouldering.com",
            "hours": "Mon–Fri: 6am–11pm | Sat–Sun: 8am–9pm"
        }
    },
    {
        "id": "site_whiskey_highland_cask",
        "name": "Highland Cask & Co.",
        "tagline": "Independent Bottler of Un-Chillfiltered Cask Strength Single Malt Scotch",
        "type": "spirits",
        "prefix": "hc",
        "primary": "#17130f",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#261f19",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Join the Cask Society",
        "hero_sub": "Hand-selected single casks from silent and legendary Scottish distilleries, bottled at natural cask strength with zero added caramel coloring.",
        "section_name": "Single Cask Releases",
        "section_id": "releases",
        "items": [
            {"title": "Islay 1998 Peated Single Cask #42", "tag": "56.4% ABV (26 Years)", "desc": "Smoked sea salt, kipper smoke, medicinal peat embers, balanced by luscious dark sultana and charred oak."},
            {"title": "Speyside 2005 First-Fill Oloroso Sherry Butt", "tag": "58.2% ABV", "desc": "Decadent fruitcake, sticky medjool dates, cinnamon bark, roasted walnuts, and a heavy viscous mouthfeel."},
            {"title": "Campbeltown 2012 Refill Bourbon Hogshead", "tag": "54.1% ABV", "desc": "Coastal maritime brine, damp engine oil, green orchard apples, and creamy vanilla toffee sweetness."},
            {"title": "Highland Cask Society Membership", "tag": "Quarterly Allocations", "desc": "Guaranteed access to limited single cask releases, warehouse tasting events, and custom engraved crystal glasses."}
        ],
        "contact": {
            "address": "48 High St, Royal Mile, Edinburgh EH1 1TB, Scotland",
            "phone": "+44 131 555 0235",
            "email": "casks@highlandcask.scot",
            "hours": "Mon–Sat: 10am–6pm GMT"
        }
    }
]


# (build_trajectory for B5 delegates to build_diverse_domain_trajectory)



# ==============================================================================
# INTERACTIVE: Dynamic SaaS & Web Application Trajectories
# ==============================================================================

import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")




def obs_ok(files, next_instruction):
    lines = ['<observation status="ok">']
    lines.append("[Files accepted]:")
    for p in files:
        lines.append(f"  ✓ {p}")
    lines.append(f"\n[NEXT SECTION REQUIRED]: {next_instruction}")
    lines.append('Write ONE <tool_call name="write_site"> with exactly one .tsx file and one .css file for this section.')
    lines.append("</observation>")
    return "\n".join(lines)


def obs_done(files):
    lines = ['<observation status="complete">']
    lines.append("[SITE BUILD COMPLETE]: All required sections have been written successfully.")
    lines.append("[Files written in this session]:")
    for p in files:
        lines.append(f"  ✓ {p}")
    lines.append("Output a <finish> tag with a brief summary of the site you built.")
    lines.append("</observation>")
    return "\n".join(lines)


def write_site(tsx_path, tsx_code, css_path, css_code):
    return (
        f'<tool_call name="write_site">\n'
        f'<file path="{tsx_path}">\n{tsx_code}\n</file>\n'
        f'<file path="{css_path}">\n{css_code}\n</file>\n'
        f'</tool_call>'
    )


def thought(text):
    return f"<thought>\n{text.strip()}\n</thought>"


def finish(text):
    return f"<finish>\n{text.strip()}\n</finish>"


def build_flowsync_trajectory():
    prompt = (
        'Build a modern responsive SaaS landing page website for "FlowSync AI" with a sticky navigation bar '
        'with dark/light mode toggle, a hero section with animated metric badges, an interactive 3-tier pricing calculator '
        'with annual/monthly toggle, a feature showcase grid with tabbed filtering, and a customer testimonials carousel.'
    )

    brief_xml = """<content_brief>
  <business_name>FlowSync AI</business_name>
  <tagline>FlowSync AI - Autonomous intelligence and high-velocity workflows for modern teams</tagline>
  <business_type>saas</business_type>
  <primary_color>#090d16</primary_color>
  <accent_color>#38bdf8</accent_color>
  <font_heading>Inter</font_heading>
  <font_body>Inter</font_body>
  <sections>header, hero, features, pricing, testimonials, footer</sections>
  <feature icon="bolt" title="Autonomous Pipeline Engine">Orchestrate agent workflows with real-time streaming and zero latency.</feature>
  <feature icon="shield" title="Enterprise Guardrails">Automated sandboxing, audit telemetry, and SOC-2 security standards.</feature>
  <feature icon="sliders" title="Adaptive Model Tuning">Dynamic LoRA adapter selection tailored to each task and workload complexity.</feature>
  <feature icon="chart" title="Predictive Telemetry">Live visual tracking, execution flamegraphs, and automated root-cause analysis.</feature>
  <pricing_tier name="Starter" price="$29" period="month" recommended="false">
    <feature>Up to 5 Team Members</feature>
    <feature>10,000 Operations / mo</feature>
    <feature>Community Discord Support</feature>
  </pricing_tier>
  <pricing_tier name="Pro" price="$79" period="month" recommended="true">
    <feature>Unlimited Team Members</feature>
    <feature>250,000 Operations / mo</feature>
    <feature>Priority 24/7 SLA & Direct Chat</feature>
    <feature>Advanced Execution Telemetry</feature>
  </pricing_tier>
  <pricing_tier name="Enterprise" price="$199" period="month" recommended="false">
    <feature>Dedicated VPC Infrastructure</feature>
    <feature>Unlimited Operations</feature>
    <feature>Custom SAML / SSO Governance</feature>
    <feature>Dedicated Solutions Architect</feature>
  </pricing_tier>
  <testimonial author="Dr. Sarah Lin" role="VP of Engineering at CloudScale" rating="5">FlowSync AI eliminated 80% of our manual workflow triage. An indispensable platform for high-velocity teams.</testimonial>
  <testimonial author="Marcus Vance" role="Lead Architect at ScaleBase" rating="5">The cleanest execution pipeline we have ever integrated. Our deployment pass rates doubled within two weeks.</testimonial>
  <testimonial author="Elena Rostova" role="Staff Product Director" rating="5">Self-correcting agent loops with live compilation feedback completely redefined our delivery velocity.</testimonial>
  <contact>
    <email>support@flowsync.ai</email>
  </contact>
</content_brief>"""

    # Section 1: Header
    header_tsx = """import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    document.documentElement.setAttribute('data-theme', nextDark ? 'dark' : 'light');
  };

  return (
    <header className={`fs-header${scrolled ? ' fs-header--scrolled' : ''}`} role="banner">
      <div className="fs-header__inner">
        <a href="#" className="fs-header__logo" aria-label="FlowSync AI Home">
          <span className="fs-header__logo-icon">⚡</span>
          <span>FlowSync<span className="fs-header__logo-accent">AI</span></span>
        </a>

        <nav className="fs-header__nav" aria-label="Main Navigation">
          <a href="#hero" onClick={() => setMenuOpen(false)}>Overview</a>
          <a href="#features" onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
          <a href="#testimonials" onClick={() => setMenuOpen(false)}>Testimonials</a>
        </nav>

        <div className="fs-header__actions">
          <button
            type="button"
            className="fs-header__theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
          >
            {isDark ? '☀️ Light' : '🌙 Dark'}
          </button>
          <a href="#pricing" className="fs-header__cta">
            Get Started
          </a>
          <button
            type="button"
            className="fs-header__menu-btn"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle navigation menu"
          >
            <span className="fs-header__bar" />
            <span className="fs-header__bar" />
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="fs-header__mobile-drawer">
          <a href="#hero" onClick={() => setMenuOpen(false)}>Overview</a>
          <a href="#features" onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
          <a href="#testimonials" onClick={() => setMenuOpen(false)}>Testimonials</a>
        </div>
      )}
    </header>
  );
}
"""
    header_css = """.fs-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: rgba(9, 13, 22, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.fs-header--scrolled {
  background: rgba(9, 13, 22, 0.95);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  border-bottom-color: rgba(56, 189, 248, 0.2);
}

.fs-header__inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}

.fs-header__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 800;
  color: #fafafa;
  text-decoration: none;
  letter-spacing: -0.02em;
}

.fs-header__logo-icon {
  font-size: 1.2rem;
}

.fs-header__logo-accent {
  color: #38bdf8;
  margin-left: 2px;
}

.fs-header__nav {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.fs-header__nav a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s ease;
}

.fs-header__nav a:hover {
  color: #38bdf8;
}

.fs-header__actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.fs-header__theme-toggle {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #e2e8f0;
  padding: 0.4rem 0.8rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.fs-header__theme-toggle:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: #38bdf8;
  color: #38bdf8;
}

.fs-header__cta {
  display: inline-flex;
  align-items: center;
  padding: 0.55rem 1.2rem;
  background: linear-gradient(135deg, #38bdf8 0%, #6366f1 100%);
  color: #040810;
  font-size: 0.85rem;
  font-weight: 700;
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.2s ease;
}

.fs-header__cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(56, 189, 248, 0.35);
}

.fs-header__menu-btn {
  display: none;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px;
  flex-direction: column;
  gap: 5px;
}

.fs-header__bar {
  display: block;
  width: 22px;
  height: 2px;
  background: #fafafa;
  border-radius: 2px;
}

.fs-header__mobile-drawer {
  display: flex;
  flex-direction: column;
  padding: 1rem 2rem;
  background: #090d16;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  gap: 0.85rem;
}

.fs-header__mobile-drawer a {
  color: #e2e8f0;
  text-decoration: none;
  font-size: 0.95rem;
  padding: 0.3rem 0;
}

@media (max-width: 768px) {
  .fs-header__nav { display: none; }
  .fs-header__menu-btn { display: flex; }
}
"""

    # Section 2: Hero
    hero_tsx = """import React, { useState, useEffect } from 'react';
import './Hero.css';

export function Hero() {
  const [metricCount, setMetricCount] = useState(0);

  useEffect(() => {
    const target = 99.4;
    const duration = 1200;
    const intervalTime = 30;
    const steps = duration / intervalTime;
    const increment = target / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setMetricCount(target);
        clearInterval(timer);
      } else {
        setMetricCount(Number(current.toFixed(1)));
      }
    }, intervalTime);

    return () => clearInterval(timer);
  }, []);

  return (
    <section className="fs-hero" id="hero" aria-labelledby="fs-hero-title">
      <div className="fs-hero__glow" aria-hidden="true" />

      <div className="fs-hero__inner">
        <div className="fs-hero__pill">
          <span className="fs-hero__pill-dot" aria-hidden="true" />
          <span>v2.4 Engine Release: Sub-millisecond Execution</span>
        </div>

        <h1 id="fs-hero-title" className="fs-hero__title">
          Autonomous Intelligence for <span className="fs-hero__title-gradient">High-Velocity Teams</span>
        </h1>

        <p className="fs-hero__subtitle">
          FlowSync orchestrates AI agent workflows, live type diagnostics, and multi-turn compiler feedback into turnkey enterprise production pipelines.
        </p>

        <div className="fs-hero__cta-group">
          <a href="#pricing" className="fs-hero__btn-primary">
            Start Free Trial
          </a>
          <a href="#features" className="fs-hero__btn-secondary">
            Explore Architecture →
          </a>
        </div>

        <div className="fs-hero__metrics">
          <div className="fs-hero__metric-card">
            <span className="fs-hero__metric-num">{metricCount}%</span>
            <span className="fs-hero__metric-label">Compiler First-Pass Rate</span>
          </div>
          <div className="fs-hero__metric-card">
            <span className="fs-hero__metric-num">3.2x</span>
            <span className="fs-hero__metric-label">Faster Production Deployments</span>
          </div>
          <div className="fs-hero__metric-card">
            <span className="fs-hero__metric-num">100k+</span>
            <span className="fs-hero__metric-label">Verified SFT Rollouts Run</span>
          </div>
        </div>
      </div>
    </section>
  );
}
"""
    hero_css = """.fs-hero {
  position: relative;
  min-height: 88vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #090d16;
  overflow: hidden;
  padding: 6rem 2rem 5rem;
}

.fs-hero__glow {
  position: absolute;
  top: 15%;
  left: 50%;
  transform: translateX(-50%);
  width: 780px;
  height: 480px;
  border-radius: 50%;
  background: radial-gradient(ellipse at center, rgba(56, 189, 248, 0.18) 0%, rgba(99, 102, 241, 0.12) 45%, transparent 75%);
  pointer-events: none;
  filter: blur(48px);
}

.fs-hero__inner {
  position: relative;
  z-index: 1;
  max-width: 920px;
  margin: 0 auto;
  text-align: center;
}

.fs-hero__pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 1.1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 9999px;
  color: #38bdf8;
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 2rem;
}

.fs-hero__pill-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 10px #38bdf8;
}

.fs-hero__title {
  font-size: clamp(2.5rem, 5.5vw, 4.2rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.12;
  letter-spacing: -0.03em;
  margin: 0 0 1.5rem;
}

.fs-hero__title-gradient {
  background: linear-gradient(135deg, #38bdf8 20%, #818cf8 80%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.fs-hero__subtitle {
  font-size: 1.15rem;
  color: #94a3b8;
  line-height: 1.7;
  max-width: 680px;
  margin: 0 auto 2.5rem;
}

.fs-hero__cta-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
  margin-bottom: 4rem;
}

.fs-hero__btn-primary {
  padding: 0.85rem 2rem;
  background: linear-gradient(135deg, #38bdf8 0%, #6366f1 100%);
  color: #040810;
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.fs-hero__btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(56, 189, 248, 0.4);
}

.fs-hero__btn-secondary {
  padding: 0.85rem 1.8rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #f1f5f9;
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.fs-hero__btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #38bdf8;
}

.fs-hero__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 2.5rem;
}

.fs-hero__metric-card {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.fs-hero__metric-num {
  font-size: 2.2rem;
  font-weight: 800;
  color: #fafafa;
  font-family: monospace;
  letter-spacing: -0.02em;
}

.fs-hero__metric-label {
  font-size: 0.85rem;
  color: #64748b;
  margin-top: 0.25rem;
}

@media (max-width: 640px) {
  .fs-hero__metrics { grid-template-columns: 1fr; gap: 2rem; }
  .fs-hero__cta-group { flex-direction: column; width: 100%; }
  .fs-hero__btn-primary, .fs-hero__btn-secondary { width: 100%; text-align: center; }
}
"""

    # Section 3: Features
    features_tsx = """import React, { useState } from 'react';
import './Features.css';

interface FeatureItem {
  id: string;
  category: 'core' | 'security' | 'scale';
  title: string;
  desc: string;
  badge: string;
}

const FEATURES: FeatureItem[] = [
  { id: '1', category: 'core', title: 'Autonomous Pipeline Engine', desc: 'Execute multi-turn agent loops with real-time streaming observations and live test harness feedback.', badge: 'Streaming' },
  { id: '2', category: 'core', title: 'Adaptive Adapter Switching', desc: 'Select the optimal task-specific LoRA weights on the fly based on prompt complexity and context requirements.', badge: 'QLoRA' },
  { id: '3', category: 'security', title: 'Enterprise Sandboxing', desc: 'Containerized execution environments enforce memory boundaries and isolate untrusted generated code safely.', badge: 'SOC-2' },
  { id: '4', category: 'security', title: 'Cryptographic Ticket Auth', desc: 'Short-lived single-use HMAC-SHA256 authenticated tokens prevent cross-site hijack vulnerabilities.', badge: 'CSWSH Guard' },
  { id: '5', category: 'scale', title: 'Predictive Flamegraphs', desc: 'Full-depth latency tracing, memory allocation profiling, and automatic bottleneck identification.', badge: 'Telemetry' },
  { id: '6', category: 'scale', title: 'Deterministic STaR Harvest', desc: 'Automated rejection sampling loops harvest passing verified episodes directly to training sets.', badge: 'Self-Taught' },
];

export function Features() {
  const [activeTab, setActiveTab] = useState<'all' | 'core' | 'security' | 'scale'>('all');

  const filtered = activeTab === 'all' ? FEATURES : FEATURES.filter((f) => f.category === activeTab);

  return (
    <section className="fs-features" id="features" aria-labelledby="fs-features-title">
      <div className="fs-features__inner">
        <div className="fs-features__header">
          <p className="fs-features__eyebrow">Production Architecture</p>
          <h2 id="fs-features-title" className="fs-features__title">
            Engineered for Uncompromising Reliability
          </h2>
          <p className="fs-features__subtitle">
            Every layer of FlowSync AI is built to turn small language models into high-precision, self-correcting engineering agents.
          </p>

          <div className="fs-features__tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'all'}
              className={`fs-features__tab${activeTab === 'all' ? ' fs-features__tab--active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              All Capabilities
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'core'}
              className={`fs-features__tab${activeTab === 'core' ? ' fs-features__tab--active' : ''}`}
              onClick={() => setActiveTab('core')}
            >
              Core Engine
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'security'}
              className={`fs-features__tab${activeTab === 'security' ? ' fs-features__tab--active' : ''}`}
              onClick={() => setActiveTab('security')}
            >
              Security & Auth
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'scale'}
              className={`fs-features__tab${activeTab === 'scale' ? ' fs-features__tab--active' : ''}`}
              onClick={() => setActiveTab('scale')}
            >
              Telemetry & Scale
            </button>
          </div>
        </div>

        <div className="fs-features__grid">
          {filtered.map((item) => (
            <div key={item.id} className="fs-feature-card">
              <div className="fs-feature-card__top">
                <span className="fs-feature-card__badge">{item.badge}</span>
                <span className="fs-feature-card__category">{item.category}</span>
              </div>
              <h3 className="fs-feature-card__title">{item.title}</h3>
              <p className="fs-feature-card__desc">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
"""
    features_css = """.fs-features {
  padding: 7rem 2rem;
  background: #090d16;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.fs-features__inner {
  max-width: 1200px;
  margin: 0 auto;
}

.fs-features__header {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 3.5rem;
}

.fs-features__eyebrow {
  color: #38bdf8;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 0.75rem;
}

.fs-features__title {
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 800;
  color: #fafafa;
  letter-spacing: -0.02em;
  margin-bottom: 1rem;
}

.fs-features__subtitle {
  font-size: 1.05rem;
  color: #94a3b8;
  line-height: 1.65;
  margin-bottom: 2.5rem;
}

.fs-features__tabs {
  display: inline-flex;
  background: #101626;
  padding: 0.35rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  gap: 0.4rem;
}

.fs-features__tab {
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 0.5rem 1.2rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.fs-features__tab:hover {
  color: #f1f5f9;
}

.fs-features__tab--active {
  background: #1e293b;
  color: #38bdf8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.fs-features__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.fs-feature-card {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 2rem;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
}

.fs-feature-card:hover {
  transform: translateY(-4px);
  border-color: rgba(56, 189, 248, 0.3);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4);
}

.fs-feature-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.fs-feature-card__badge {
  padding: 0.25rem 0.65rem;
  background: rgba(56, 189, 248, 0.1);
  color: #38bdf8;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.fs-feature-card__category {
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
  font-weight: 600;
}

.fs-feature-card__title {
  font-size: 1.2rem;
  font-weight: 700;
  color: #fafafa;
  margin-bottom: 0.75rem;
}

.fs-feature-card__desc {
  font-size: 0.92rem;
  color: #94a3b8;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .fs-features__grid { grid-template-columns: 1fr; }
  .fs-features__tabs { flex-wrap: wrap; justify-content: center; }
}
"""

    # Section 4: Pricing
    pricing_tsx = """import React, { useState } from 'react';
import './Pricing.css';

interface Tier {
  name: string;
  monthlyPrice: number;
  desc: string;
  recommended: boolean;
  features: string[];
}

const TIERS: Tier[] = [
  {
    name: 'Starter',
    monthlyPrice: 29,
    desc: 'For individual builders exploring autonomous agentic workflows.',
    recommended: false,
    features: ['Up to 5 Team Members', '10,000 Operations / mo', 'Community Discord Support', 'Standard VRAM Quantization'],
  },
  {
    name: 'Pro',
    monthlyPrice: 79,
    desc: 'For high-velocity product teams scaling self-correcting agent loops.',
    recommended: true,
    features: ['Unlimited Team Members', '250,000 Operations / mo', 'Priority 24/7 SLA & Live Support', 'Custom QLoRA Task Adapters', 'Full Visual Telemetry Reports'],
  },
  {
    name: 'Enterprise',
    monthlyPrice: 199,
    desc: 'Dedicated private infrastructure with guaranteed SLA throughput.',
    recommended: false,
    features: ['Dedicated VPC / On-Prem Deploy', 'Unlimited Operations & Runs', 'SOC-2 & SAML SSO Governance', 'Custom Base-Model Pre-training', 'Dedicated Solutions Architect'],
  },
];

export function Pricing() {
  const [isAnnual, setIsAnnual] = useState(true);

  return (
    <section className="fs-pricing" id="pricing" aria-labelledby="fs-pricing-title">
      <div className="fs-pricing__inner">
        <div className="fs-pricing__header">
          <p className="fs-pricing__eyebrow">Transparent Value</p>
          <h2 id="fs-pricing-title" className="fs-pricing__title">
            Simple, High-Yield Pricing
          </h2>
          <p className="fs-pricing__subtitle">
            Scale from prototype to global enterprise cluster with zero unexpected charges.
          </p>

          <div className="fs-pricing__toggle-wrap">
            <button
              type="button"
              className={`fs-pricing__toggle-btn${!isAnnual ? ' active' : ''}`}
              onClick={() => setIsAnnual(false)}
            >
              Monthly Billing
            </button>
            <button
              type="button"
              className={`fs-pricing__toggle-btn${isAnnual ? ' active' : ''}`}
              onClick={() => setIsAnnual(true)}
            >
              Annual Billing <span className="fs-pricing__save-pill">Save 20%</span>
            </button>
          </div>
        </div>

        <div className="fs-pricing__grid">
          {TIERS.map((tier) => {
            const price = isAnnual ? Math.round(tier.monthlyPrice * 0.8) : tier.monthlyPrice;
            return (
              <div
                key={tier.name}
                className={`fs-pricing-card${tier.recommended ? ' fs-pricing-card--popular' : ''}`}
              >
                {tier.recommended && <span className="fs-pricing-card__banner">Most Popular</span>}
                <h3 className="fs-pricing-card__name">{tier.name}</h3>
                <p className="fs-pricing-card__desc">{tier.desc}</p>
                <div className="fs-pricing-card__price">
                  <span className="fs-pricing-card__amt">${price}</span>
                  <span className="fs-pricing-card__period">/ user / mo</span>
                </div>

                <ul className="fs-pricing-card__list">
                  {tier.features.map((feat) => (
                    <li key={feat}>
                      <span className="fs-pricing-card__check">✓</span>
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>

                <button
                  type="button"
                  className={`fs-pricing-card__btn${tier.recommended ? ' fs-pricing-card__btn--highlight' : ''}`}
                >
                  Choose {tier.name}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
"""
    pricing_css = """.fs-pricing {
  padding: 7rem 2rem;
  background: #060911;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.fs-pricing__inner {
  max-width: 1200px;
  margin: 0 auto;
}

.fs-pricing__header {
  text-align: center;
  max-width: 680px;
  margin: 0 auto 3.5rem;
}

.fs-pricing__eyebrow {
  color: #38bdf8;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 0.75rem;
}

.fs-pricing__title {
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 800;
  color: #fafafa;
  margin-bottom: 1rem;
}

.fs-pricing__subtitle {
  font-size: 1.05rem;
  color: #94a3b8;
  line-height: 1.6;
  margin-bottom: 2rem;
}

.fs-pricing__toggle-wrap {
  display: inline-flex;
  background: #101626;
  padding: 0.3rem;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.fs-pricing__toggle-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 0.5rem 1.4rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
}

.fs-pricing__toggle-btn.active {
  background: #1e293b;
  color: #fafafa;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.fs-pricing__save-pill {
  font-size: 0.7rem;
  padding: 0.15rem 0.45rem;
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  border-radius: 9999px;
}

.fs-pricing__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  align-items: stretch;
}

.fs-pricing-card {
  position: relative;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 2.5rem 2rem;
  display: flex;
  flex-direction: column;
  transition: all 0.25s ease;
}

.fs-pricing-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.4);
}

.fs-pricing-card--popular {
  border-color: #38bdf8;
  background: #111a33;
  box-shadow: 0 8px 32px rgba(56, 189, 248, 0.15);
}

.fs-pricing-card__banner {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #38bdf8 0%, #6366f1 100%);
  color: #040810;
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
  padding: 0.25rem 0.85rem;
  border-radius: 9999px;
  letter-spacing: 0.05em;
}

.fs-pricing-card__name {
  font-size: 1.4rem;
  font-weight: 800;
  color: #fafafa;
  margin-bottom: 0.5rem;
}

.fs-pricing-card__desc {
  font-size: 0.9rem;
  color: #94a3b8;
  line-height: 1.5;
  margin-bottom: 1.5rem;
  min-height: 42px;
}

.fs-pricing-card__price {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.fs-pricing-card__amt {
  font-size: 2.8rem;
  font-weight: 800;
  color: #fafafa;
  font-family: monospace;
}

.fs-pricing-card__period {
  font-size: 0.85rem;
  color: #64748b;
}

.fs-pricing-card__list {
  list-style: none;
  padding: 0;
  margin: 0 0 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  flex: 1;
}

.fs-pricing-card__list li {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.9rem;
  color: #e2e8f0;
}

.fs-pricing-card__check {
  color: #38bdf8;
  font-weight: 800;
}

.fs-pricing-card__btn {
  width: 100%;
  padding: 0.85rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #fafafa;
  border-radius: 8px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.fs-pricing-card__btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: #38bdf8;
}

.fs-pricing-card__btn--highlight {
  background: linear-gradient(135deg, #38bdf8 0%, #6366f1 100%);
  color: #040810;
  border: none;
}

.fs-pricing-card__btn--highlight:hover {
  box-shadow: 0 4px 16px rgba(56, 189, 248, 0.4);
}

@media (max-width: 900px) {
  .fs-pricing__grid { grid-template-columns: 1fr; }
}
"""

    # Section 5: Testimonials
    testimonials_tsx = """import React, { useState } from 'react';
import './Testimonials.css';

interface Review {
  id: string;
  quote: string;
  author: string;
  role: string;
  avatar: string;
}

const REVIEWS: Review[] = [
  {
    id: '1',
    quote: 'FlowSync AI reduced our deployment triage time by 80%. Our engineering team moved from manual debugging to continuous delivery overnight.',
    author: 'Dr. Sarah Lin',
    role: 'VP of Engineering at CloudScale',
    avatar: 'SL'
  },
  {
    id: '2',
    quote: 'The cleanest multi-step execution pipeline we have ever deployed. Our compilation pass rates skyrocketed to 99% within the first month.',
    author: 'Marcus Vance',
    role: 'Lead Architect at ScaleBase',
    avatar: 'MV'
  },
  {
    id: '3',
    quote: 'Autonomous error correction and live test feedback transformed our product sprints. It feels like having a staff engineer on call 24/7.',
    author: 'Elena Rostova',
    role: 'Staff Product Director',
    avatar: 'ER'
  }
];

export function Testimonials() {
  const [active, setActive] = useState(0);

  const next = () => setActive((prev) => (prev + 1) % REVIEWS.length);
  const prev = () => setActive((prev) => (prev - 1 + REVIEWS.length) % REVIEWS.length);

  const cur = REVIEWS[active];

  return (
    <section className="fs-reviews" id="testimonials" aria-labelledby="fs-reviews-title">
      <div className="fs-reviews__inner">
        <div className="fs-reviews__header">
          <p className="fs-reviews__eyebrow">Trusted by Architects</p>
          <h2 id="fs-reviews-title" className="fs-reviews__title">
            Proven Results in High-Yield Teams
          </h2>
        </div>

        <div className="fs-reviews__carousel">
          <div className="fs-reviews__stars" aria-label="5 out of 5 stars">
            {'★★★★★'}
          </div>

          <blockquote className="fs-reviews__quote">
            "{cur.quote}"
          </blockquote>

          <div className="fs-reviews__author-wrap">
            <div className="fs-reviews__avatar" aria-hidden="true">{cur.avatar}</div>
            <div>
              <h4 className="fs-reviews__author">{cur.author}</h4>
              <span className="fs-reviews__role">{cur.role}</span>
            </div>
          </div>

          <div className="fs-reviews__nav">
            <button
              type="button"
              onClick={prev}
              className="fs-reviews__nav-btn"
              aria-label="Previous testimonial"
            >
              ←
            </button>
            <span className="fs-reviews__counter">
              0{active + 1} / 0{REVIEWS.length}
            </span>
            <button
              type="button"
              onClick={next}
              className="fs-reviews__nav-btn"
              aria-label="Next testimonial"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
"""
    testimonials_css = """.fs-reviews {
  padding: 7rem 2rem;
  background: #090d16;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.fs-reviews__inner {
  max-width: 900px;
  margin: 0 auto;
}

.fs-reviews__header {
  text-align: center;
  margin-bottom: 3.5rem;
}

.fs-reviews__eyebrow {
  color: #38bdf8;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 0.5rem;
}

.fs-reviews__title {
  font-size: clamp(2rem, 4vw, 2.8rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0;
}

.fs-reviews__carousel {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 3.5rem 3rem;
  text-align: center;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.3);
}

.fs-reviews__stars {
  color: #fbbf24;
  font-size: 1.4rem;
  margin-bottom: 1.5rem;
  letter-spacing: 4px;
}

.fs-reviews__quote {
  font-size: 1.3rem;
  font-style: italic;
  color: #f1f5f9;
  line-height: 1.65;
  max-width: 720px;
  margin: 0 auto 2.5rem;
}

.fs-reviews__author-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.fs-reviews__avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #38bdf8 0%, #6366f1 100%);
  color: #040810;
  font-weight: 800;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fs-reviews__author {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.2rem;
}

.fs-reviews__role {
  font-size: 0.85rem;
  color: #38bdf8;
}

.fs-reviews__nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.fs-reviews__nav-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.fs-reviews__nav-btn:hover {
  background: #38bdf8;
  color: #040810;
}

.fs-reviews__counter {
  font-size: 0.85rem;
  color: #64748b;
  font-family: monospace;
}
"""

    # Section 6: Footer
    footer_tsx = """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="fs-footer" role="contentinfo" aria-label="Site Footer">
      <div className="fs-footer__inner">
        <div className="fs-footer__col-brand">
          <a href="#" className="fs-footer__logo">
            ⚡ FlowSync<span className="fs-footer__logo-accent">AI</span>
          </a>
          <p className="fs-footer__tagline">
            Autonomous intelligence and high-velocity workflows for modern software teams.
          </p>
        </div>

        <nav className="fs-footer__col-nav" aria-label="Footer Navigation">
          <h4>Platform</h4>
          <ul>
            <li><a href="#hero">Overview</a></li>
            <li><a href="#features">Features</a></li>
            <li><a href="#pricing">Pricing</a></li>
            <li><a href="#testimonials">Testimonials</a></li>
          </ul>
        </nav>

        <div className="fs-footer__col-contact">
          <h4>Connect</h4>
          <p>Email: <a href="mailto:support@flowsync.ai">support@flowsync.ai</a></p>
          <div className="fs-footer__social">
            <a href="https://github.com" target="_blank" rel="noreferrer" aria-label="GitHub">GitHub</a>
            <a href="https://twitter.com" target="_blank" rel="noreferrer" aria-label="Twitter">Twitter</a>
            <a href="https://discord.com" target="_blank" rel="noreferrer" aria-label="Discord">Discord</a>
          </div>
        </div>
      </div>

      <div className="fs-footer__bottom">
        <p>&copy; {new Date().getFullYear()} FlowSync AI, Inc. All rights reserved.</p>
      </div>
    </footer>
  );
}
"""
    footer_css = """.fs-footer {
  background: #05080e;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 5rem 2rem 2rem;
  color: #94a3b8;
}

.fs-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 3rem;
  padding-bottom: 3rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.fs-footer__logo {
  font-size: 1.3rem;
  font-weight: 800;
  color: #fafafa;
  text-decoration: none;
  display: inline-block;
  margin-bottom: 0.75rem;
}

.fs-footer__logo-accent {
  color: #38bdf8;
}

.fs-footer__tagline {
  font-size: 0.92rem;
  line-height: 1.6;
  max-width: 380px;
  margin: 0;
}

.fs-footer__col-nav h4,
.fs-footer__col-contact h4 {
  color: #fafafa;
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0 0 1rem;
}

.fs-footer__col-nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.fs-footer__col-nav a,
.fs-footer__col-contact a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.2s ease;
}

.fs-footer__col-nav a:hover,
.fs-footer__col-contact a:hover {
  color: #38bdf8;
}

.fs-footer__social {
  display: flex;
  gap: 1rem;
  margin-top: 0.85rem;
}

.fs-footer__bottom {
  max-width: 1200px;
  margin: 2rem auto 0;
  text-align: center;
  font-size: 0.82rem;
  color: #64748b;
}

@media (max-width: 768px) {
  .fs-footer__inner { grid-template-columns: 1fr; gap: 2.5rem; }
}
"""

    initial_msg = (
        f"User Instruction: {prompt}\n\n"
        f"Content Brief:\n{brief_xml}\n\n"
        f"You will build the site ONE SECTION AT A TIME, reconciling the brief with any specific requested features in the user instruction. "
        f"Start with the first section now.\n\n"
        f"FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the business name/logo on the left, "
        f"navigation links in the center, and action controls on the right. If the prompt requests a theme toggle, "
        f"include a functional dark/light mode toggle switch using useState. Include a responsive mobile drawer toggle. "
        f"Files: src/components/Header.tsx + src/components/Header.css"
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_msg},
        {
            "role": "assistant",
            "content": thought("I will implement the Header section for FlowSync AI. The user requested a sticky navbar with dark/light mode toggle, so I'll maintain an isDark state and update document attribute.") + "\n" +
            write_site("src/components/Header.tsx", header_tsx, "src/components/Header.css", header_css)
        },
        {
            "role": "user",
            "content": obs_ok(["src/components/Header.tsx", "src/components/Header.css"], "Write the Hero section: a high-impact full-width banner with background gradient, business tagline as an h1, a compelling subtitle, primary/secondary action buttons, and animated or styled metric badges if requested. Files: src/components/Hero.tsx + src/components/Hero.css")
        },
        {
            "role": "assistant",
            "content": thought("Now I will implement the Hero section with an animated metric counter, glowing radial backdrop, and high-conversion action buttons.") + "\n" +
            write_site("src/components/Hero.tsx", hero_tsx, "src/components/Hero.css", hero_css)
        },
        {
            "role": "user",
            "content": obs_ok(["src/components/Hero.tsx", "src/components/Hero.css"], "Write the Features section: display each feature as a card with icon, title, and description. If the prompt requests tabbed filtering or category switching, implement functional tab buttons with useState. Files: src/components/Features.tsx + src/components/Features.css")
        },
        {
            "role": "assistant",
            "content": thought("I will implement the Features section with interactive category tab filtering (Core, Security, Scale) and styled capability cards.") + "\n" +
            write_site("src/components/Features.tsx", features_tsx, "src/components/Features.css", features_css)
        },
        {
            "role": "user",
            "content": obs_ok(["src/components/Features.tsx", "src/components/Features.css"], "Write the Pricing section: display 3 pricing tier cards (e.g. Starter, Pro/Recommended, Enterprise). If the prompt requests an interactive pricing calculator or billing toggle, implement an annual/monthly billing toggle switch with discounted calculation using useState. Files: src/components/Pricing.tsx + src/components/Pricing.css")
        },
        {
            "role": "assistant",
            "content": thought("I will implement the Pricing section with an interactive annual/monthly billing toggle (20% discount on annual), recommended badge for Pro, and comprehensive tier feature lists.") + "\n" +
            write_site("src/components/Pricing.tsx", pricing_tsx, "src/components/Pricing.css", pricing_css)
        },
        {
            "role": "user",
            "content": obs_ok(["src/components/Pricing.tsx", "src/components/Pricing.css"], "Write the Testimonials section: display customer quotes, author names, roles, and star ratings. If requested, build an interactive carousel card with previous and next pagination buttons tracking active index using useState. Files: src/components/Testimonials.tsx + src/components/Testimonials.css")
        },
        {
            "role": "assistant",
            "content": thought("I will implement the Testimonials section as an interactive review carousel with active quote index tracking, previous/next controls, star ratings, and avatars.") + "\n" +
            write_site("src/components/Testimonials.tsx", testimonials_tsx, "src/components/Testimonials.css", testimonials_css)
        },
        {
            "role": "user",
            "content": obs_ok(["src/components/Testimonials.tsx", "src/components/Testimonials.css"], "Write the Footer section: a dark background footer with the business name, brief nav links, contact info, and a copyright notice. Files: src/components/Footer.tsx + src/components/Footer.css")
        },
        {
            "role": "assistant",
            "content": thought("Finally, I will implement the Footer section with brand overview, quick navigation anchors, social links, and copyright statement.") + "\n" +
            write_site("src/components/Footer.tsx", footer_tsx, "src/components/Footer.css", footer_css)
        },
        {
            "role": "user",
            "content": obs_done([
                "src/components/Header.tsx", "src/components/Header.css",
                "src/components/Hero.tsx", "src/components/Hero.css",
                "src/components/Features.tsx", "src/components/Features.css",
                "src/components/Pricing.tsx", "src/components/Pricing.css",
                "src/components/Testimonials.tsx", "src/components/Testimonials.css",
                "src/components/Footer.tsx", "src/components/Footer.css"
            ])
        },
        {
            "role": "assistant",
            "content": finish("Successfully constructed the complete FlowSync AI SaaS landing page. Generated 6 responsive sections: Header with theme toggle, Hero with animated metrics, Features with tab filtering, Pricing with interactive annual billing toggle, Testimonials with quote carousel, and Footer.")
        }
    ]

    return {
        "task_id": "site_interactive_saas_flowsync",
        "messages": messages
    }





# ==============================================================================
# Batch Module-Level Lists
# ==============================================================================

BATCH_1 = [
    trajectory_restaurant_01,
    trajectory_saas_01,
    trajectory_portfolio_01,
]

INTERACTIVE = [
    build_flowsync_trajectory,
]


def run_batch(batch_name: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_name = str(batch_name).lower().strip()

    if batch_name in ["1", "batch1"]:
        out_file = out_dir / "site_trajectories.jsonl"
        print(f"Generating Batch 1 ({len(BATCH_1)} trajectories) -> {out_file}...")
        with out_file.open("w", encoding="utf-8") as f:
            for gen in BATCH_1:
                rec = gen()
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        print(f"  ✓ Wrote {len(BATCH_1)} trajectories to {out_file}")

    elif batch_name in ["2", "batch2"]:
        out_file = out_dir / "site_trajectories_batch2.jsonl"
        print(f"Generating Batch 2 ({len(BATCH_2)} trajectories) -> {out_file}...")
        with out_file.open("w", encoding="utf-8") as f:
            for gen in BATCH_2:
                rec = gen()
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        print(f"  ✓ Wrote {len(BATCH_2)} trajectories to {out_file}")

    elif batch_name in ["3", "batch3"]:
        out_file = out_dir / "site_trajectories_batch3.jsonl"
        print(f"Generating Batch 3 ({len(BATCH_3)} trajectories) -> {out_file}...")
        with out_file.open("w", encoding="utf-8") as f:
            for gen in BATCH_3:
                rec = gen()
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        print(f"  ✓ Wrote {len(BATCH_3)} trajectories to {out_file}")

    elif batch_name in ["4", "batch4"]:
        out_file = out_dir / "site_trajectories_batch4.jsonl"
        print(f"Generating Batch 4 ({len(DOMAINS_B4)} domains) -> {out_file}...")
        with out_file.open("w", encoding="utf-8") as f:
            for idx, d in enumerate(DOMAINS_B4):
                rec = build_trajectory_b4(d, idx)
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        print(f"  ✓ Wrote {len(DOMAINS_B4)} trajectories to {out_file}")

    elif batch_name in ["5", "batch5"]:
        out_file = out_dir / "site_trajectories_batch5.jsonl"
        print(f"Generating Batch 5 ({len(DOMAINS_B5)} domains) -> {out_file}...")
        with out_file.open("w", encoding="utf-8") as f:
            for idx, d in enumerate(DOMAINS_B5):
                rec = build_trajectory_b5(d, idx)
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        print(f"  ✓ Wrote {len(DOMAINS_B5)} trajectories to {out_file}")

    elif batch_name in ["interactive"]:
        out_file = out_dir / "site_trajectories_interactive.jsonl"
        print(f"Generating Interactive ({len(INTERACTIVE)} trajectories) -> {out_file}...")
        with out_file.open("w", encoding="utf-8") as f:
            for gen in INTERACTIVE:
                rec = gen()
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        print(f"  ✓ Wrote {len(INTERACTIVE)} trajectories to {out_file}")

    elif batch_name == "all":
        for b in ["1", "2", "3", "4", "5", "interactive"]:
            run_batch(b, out_dir)
    else:
        print(f"Error: Unknown batch '{batch_name}'. Choose from: 1, 2, 3, 4, 5, interactive, all.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Unified Trajectory Generator for ReactAgent SLM",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--batch", choices=["1", "2", "3", "4", "5", "interactive", "all"], default="all",
        help="Which trajectory batch to generate (default: all)"
    )
    parser.add_argument(
        "--out", "--output-dir", dest="out_dir", default=str(DATA_DIR),
        help="Target output directory (default: data/)"
    )

    args = parser.parse_args()
    run_batch(args.batch, Path(args.out_dir))


if __name__ == "__main__":
    main()
