#!/usr/bin/env python3
"""
data_pipeline/regenerate_7domains.py

Regenerates a trajectory pull across the 7 audited domains:
1. bakery
2. law firm (legal)
3. travel agency (travel)
4. ramen restaurant (restaurant)
5. nonprofit
6. real estate
7. education

Each site is generated with distinct structural archetypes (bento, editorial, tabs, split_hero),
distinct visual typography, color themes, and domain-authentic copy (strictly zero clichés).
Outputs to data/eval/regenerated_7domains.jsonl.
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "eval" / "regenerated_7domains.jsonl"

from build_rebalanced_dataset import make_traj

def get_regenerated_7domain_trajectories():
    trajs = []

    # ==============================================================================
    # 1. BAKERY: Maison Dorée Artisanal Boulangerie (Editorial Archetype)
    # ==============================================================================
    t1_brief = """<content_brief>
  <business_name>Maison Dorée Artisanal Boulangerie</business_name>
  <tagline>Slow-Fermented Heritage Breads & French Viennoiserie</tagline>
  <business_type>bakery</business_type>
  <layout_archetype>editorial</layout_archetype>
  <layout_guidelines>Editorial bakery monograph featuring heritage flour provenance, fermentation timeline, daily oven allocations, and artisan baker credentials.</layout_guidelines>
  <sections>header, hero, flour_monograph, daily_bakes, footer</sections>
  <contact>
    <address>42 Rue des Artisans, Portland, OR 97209</address>
    <phone>+1 (503) 555-0142</phone>
    <email>bonjour@maisondoree-bakes.com</email>
    <hours>Wed–Sun: 7am–2pm (or until daily flour batch sells out)</hours>
  </contact>
</content_brief>"""

    t1_sections = [
        {
            "name": "Header",
            "instruction": "editorial bakery header with warm cream tones, serif masthead, and daily batch allocation badge. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Crafting editorial Header for Maison Dorée using refined serif typography and daily allocation indicator.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="md-header" role="banner">
      <div className="md-header__container">
        <div className="md-header__left">
          <span className="md-header__batch-pill">BATCH #142 • 48H FERMENT</span>
        </div>
        <a href="#hero" className="md-header__brand" aria-label="Maison Dorée Home">
          <span className="md-header__title">MAISON DORÉE</span>
          <span className="md-header__sub">BOULANGERIE & PATISSERIE</span>
        </a>
        <nav className="md-header__nav" aria-label="Bakery Navigation">
          <a href="#monograph" className="md-header__link">Our Grains</a>
          <a href="#bakes" className="md-header__link">Daily Bakes</a>
          <a href="#hours" className="md-header__link">Oven Times</a>
          <a href="#contact" className="md-header__btn">Reserve Loaf</a>
        </nav>
      </div>
    </header>
  );
}
""",
            "css": """.md-header {
  background-color: #fdfbf7;
  border-bottom: 1px solid #e7dfd5;
  position: sticky;
  top: 0;
  z-index: 50;
  font-family: "Georgia", serif;
}

.md-header__container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.md-header__batch-pill {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  background-color: #f5ebe0;
  color: #78350f;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  border: 1px solid #e6ccb2;
}

.md-header__brand {
  text-decoration: none;
  text-align: center;
  display: flex;
  flex-direction: column;
}

.md-header__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #292524;
  letter-spacing: 0.06em;
}

.md-header__sub {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.65rem;
  font-weight: 600;
  color: #92400e;
  letter-spacing: 0.12em;
}

.md-header__nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.md-header__link {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #57534e;
  text-decoration: none;
  transition: color 0.15s ease;
}

.md-header__link:hover {
  color: #b45309;
}

.md-header__btn {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  padding: 0.5rem 1rem;
  background-color: #78350f;
  color: #fdfbf7;
  border-radius: 4px;
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 768px) {
  .md-header__left, .md-header__link { display: none; }
}
"""
        },
        {
            "name": "Hero",
            "instruction": "editorial longform bakery hero with dropcap monograph opening, grain mill credentials, and daily bake schedule. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building editorial hero with dropcap layout and grain provenance highlights.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="md-hero" id="hero">
      <div className="md-hero__container">
        <div className="md-hero__monograph-header">
          <span className="md-hero__kicker">THE DAILY HARVEST MONOGRAPH</span>
          <h1 className="md-hero__headline">
            Where Stone-Ground Heritage Rye Meets Forty-Eight Hours of Wild Fermentation.
          </h1>
          <div className="md-hero__meta-strip">
            <span>Written by Head Baker <strong>Henri Chamonix</strong></span>
            <span>•</span>
            <span>Milled at Camas Country Mill, Willamette Valley</span>
            <span>•</span>
            <span>100% Certified Organic Grains</span>
          </div>
        </div>

        <div className="md-hero__body">
          <p className="md-hero__lead">
            Every loaf born from our hearth begins with organic Rouge de Bordeaux and Edison heritage wheats, milled fresh each dawn on natural granite millstones. We preserve an unhurried 48-hour cold sourdough fermentation that transforms complex starches into caramelized, digestible crumb structures without commercial yeast or artificial dough conditioners.
          </p>
        </div>

        <div className="md-hero__schedule-grid">
          <div className="md-hero__schedule-card">
            <span className="md-hero__time">06:30 AM</span>
            <span className="md-hero__item-name">Country Levain Boules</span>
            <span className="md-hero__item-note">First hearth bake • blistered crust</span>
          </div>
          <div className="md-hero__schedule-card">
            <span className="md-hero__time">07:45 AM</span>
            <span className="md-hero__item-name">Kouign-Amann & Croissants</span>
            <span className="md-hero__item-note">Normandy butter • 84% butterfat</span>
          </div>
          <div className="md-hero__schedule-card">
            <span className="md-hero__time">09:15 AM</span>
            <span className="md-hero__item-name">Valrhona Babka & Cardamom Buns</span>
            <span className="md-hero__item-note">Braided brioche • Ceylon spiced</span>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.md-hero {
  background-color: #fdfbf7;
  padding: 4.5rem 1.5rem 3.5rem;
  border-bottom: 1px solid #e7dfd5;
  font-family: "Georgia", serif;
}

.md-hero__container {
  max-width: 1040px;
  margin: 0 auto;
}

.md-hero__monograph-header {
  margin-bottom: 2rem;
}

.md-hero__kicker {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #92400e;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
  display: block;
}

.md-hero__headline {
  font-size: 2.85rem;
  line-height: 1.18;
  font-weight: 700;
  color: #292524;
  margin: 0 0 1.25rem 0;
  letter-spacing: -0.01em;
}

.md-hero__meta-strip {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  color: #78716c;
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.md-hero__meta-strip strong {
  color: #292524;
}

.md-hero__body {
  margin-bottom: 3rem;
}

.md-hero__lead {
  font-size: 1.25rem;
  line-height: 1.75;
  color: #44403c;
  margin: 0;
}

.md-hero__schedule-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.md-hero__schedule-card {
  background-color: #f5ebe0;
  border: 1px solid #e6ccb2;
  padding: 1.5rem;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}

.md-hero__time {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 1.25rem;
  font-weight: 800;
  color: #78350f;
  margin-bottom: 0.35rem;
}

.md-hero__item-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: #292524;
  margin-bottom: 0.25rem;
}

.md-hero__item-note {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.75rem;
  color: #78716c;
}

@media (max-width: 800px) {
  .md-hero__headline { font-size: 2.1rem; }
  .md-hero__schedule-grid { grid-template-columns: 1fr; }
}
"""
        },
        {
            "name": "DailyBakes",
            "instruction": "curated bakery provisions with ingredient provenance, hydration percentages, and pricing. Files: src/components/DailyBakes.tsx + src/components/DailyBakes.css",
            "tsx_path": "src/components/DailyBakes.tsx",
            "css_path": "src/components/DailyBakes.css",
            "thought": "Building DailyBakes menu with artisanal grain specifications and prices.",
            "tsx": """import React from 'react';
import './DailyBakes.css';

export function DailyBakes() {
  const bakes = [
    {
      name: "Heritage Pain au Levain",
      price: "$9.50",
      flour: "85% Edison White Wheat, 15% Dark Rye",
      hydration: "82% Hydration • 48H Ferment",
      notes: "Open custard-like crumb with caramelized mahogany crust and natural wild sour notes."
    },
    {
      name: "Normandy Cultured Butter Croissant",
      price: "$5.75",
      flour: "T55 French Pastry Flour",
      hydration: "27 Laminated Layers • 84% Isigny Butter",
      notes: "Honeycomb interior with delicate shattered flaky petals and sweet hazelnut aromatics."
    },
    {
      name: "Kouign-Amann Fleur de Sel",
      price: "$6.25",
      flour: "Stone-Ground Spelt & French T55",
      hydration: "Caramelized Breton Cane Sugar & Salt",
      notes: "Crisp caramelized base yielding to buttery, melt-in-mouth laminated brioche dough."
    },
    {
      name: "Valrhona Guanaja 70% Babka",
      price: "$14.00",
      flour: "Brioche enriched with pasture eggs",
      hydration: "70% Single-Estate Dark Ganache",
      notes: "Twisted babka loaf infused with ground cardamom, dark cocoa swirl, and vanilla glaze."
    }
  ];

  return (
    <section className="md-bakes" id="bakes">
      <div className="md-bakes__container">
        <div className="md-bakes__header">
          <span className="md-bakes__tag">DAILY PROVISIONS</span>
          <h2 className="md-bakes__title">The Hearth Collection</h2>
          <p className="md-bakes__desc">
            Baked in our wood-fired hearth using single-origin Pacific Northwest grain harvests.
          </p>
        </div>

        <div className="md-bakes__list">
          {bakes.map((b, idx) => (
            <article key={idx} className="md-bakes__item">
              <div className="md-bakes__item-top">
                <h3 className="md-bakes__item-name">{b.name}</h3>
                <span className="md-bakes__item-price">{b.price}</span>
              </div>
              <div className="md-bakes__specs">
                <span className="md-bakes__spec-chip">{b.flour}</span>
                <span className="md-bakes__spec-chip">{b.hydration}</span>
              </div>
              <p className="md-bakes__item-notes">{b.notes}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.md-bakes {
  background-color: #fdfbf7;
  padding: 4.5rem 1.5rem;
  border-bottom: 1px solid #e7dfd5;
  font-family: "Georgia", serif;
}

.md-bakes__container {
  max-width: 960px;
  margin: 0 auto;
}

.md-bakes__header {
  margin-bottom: 3rem;
  text-align: center;
}

.md-bakes__tag {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #92400e;
  text-transform: uppercase;
}

.md-bakes__title {
  font-size: 2.2rem;
  color: #292524;
  margin: 0.4rem 0 0.5rem 0;
}

.md-bakes__desc {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.9375rem;
  color: #78716c;
}

.md-bakes__list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.md-bakes__item {
  background-color: #ffffff;
  border: 1px solid #e7dfd5;
  padding: 1.75rem;
  border-radius: 6px;
}

.md-bakes__item-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.5rem;
}

.md-bakes__item-name {
  font-size: 1.3rem;
  font-weight: 700;
  color: #292524;
  margin: 0;
}

.md-bakes__item-price {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 1.15rem;
  font-weight: 800;
  color: #78350f;
}

.md-bakes__specs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.md-bakes__spec-chip {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.7rem;
  font-weight: 600;
  background-color: #f5ebe0;
  color: #78350f;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.md-bakes__item-notes {
  font-size: 0.9375rem;
  line-height: 1.55;
  color: #57534e;
  margin: 0;
}
"""
        },
        {
            "name": "Footer",
            "instruction": "warm bakery footer with organic grain certifications, address, and pre-order policy. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building warm bakery footer with organic grain sourcing disclosures.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="md-footer" role="contentinfo">
      <div className="md-footer__container">
        <div className="md-footer__grid">
          <div className="md-footer__brand-col">
            <span className="md-footer__title">Maison Dorée Artisanal Boulangerie</span>
            <p className="md-footer__bio">
              Preserving ancient wood-hearth breadcraft through organic heritage grains, pure mountain spring water, and unhurried wild fermentation.
            </p>
            <div className="md-footer__cert">
              <span>USDA Organic Certified Facility • ID #OR-BIO-9402</span>
            </div>
          </div>

          <div className="md-footer__col">
            <h4 className="md-footer__heading">Boulangerie Hearth</h4>
            <address className="md-footer__addr">
              42 Rue des Artisans<br />
              Portland, OR 97209<br />
              +1 (503) 555-0142<br />
              bonjour@maisondoree-bakes.com
            </address>
          </div>

          <div className="md-footer__col">
            <h4 className="md-footer__heading">Bakery Hours</h4>
            <p className="md-footer__hours">
              Wednesday – Sunday<br />
              7:00 AM – 2:00 PM<br />
              <em>Baked fresh daily until sold out.</em>
            </p>
          </div>
        </div>

        <div className="md-footer__bottom">
          <span>© {new Date().getFullYear()} Maison Dorée Boulangerie. All rights reserved.</span>
          <div className="md-footer__links">
            <a href="#flour">Flour Mill Provenance</a>
            <a href="#allergens">Allergen Safety</a>
            <a href="#privacy">Privacy</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
""",
            "css": """.md-footer {
  background-color: #292524;
  color: #d6d3d1;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  padding: 3.5rem 1.5rem 2rem;
}

.md-footer__container {
  max-width: 1040px;
  margin: 0 auto;
}

.md-footer__grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 2.5rem;
  margin-bottom: 2.5rem;
}

.md-footer__title {
  font-family: "Georgia", serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #fdfbf7;
  display: block;
  margin-bottom: 0.5rem;
}

.md-footer__bio {
  line-height: 1.6;
  color: #a8a29e;
  margin: 0 0 1rem 0;
  max-width: 400px;
}

.md-footer__cert {
  font-size: 0.75rem;
  color: #f5ebe0;
  font-weight: 600;
}

.md-footer__heading {
  font-size: 0.75rem;
  font-weight: 700;
  color: #fdfbf7;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem 0;
}

.md-footer__addr, .md-footer__hours {
  font-style: normal;
  line-height: 1.6;
  color: #a8a29e;
  margin: 0;
}

.md-footer__bottom {
  border-top: 1px solid #44403c;
  padding-top: 1.5rem;
  display: flex;
  justify-content: space-between;
  color: #78716c;
  font-size: 0.75rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.md-footer__links {
  display: flex;
  gap: 1.25rem;
}

.md-footer__links a {
  color: #a8a29e;
  text-decoration: none;
}

@media (max-width: 768px) {
  .md-footer__grid { grid-template-columns: 1fr; }
}
"""
        }
    ]
    trajs.append(make_traj("site_bakery_maison_doree", t1_brief, t1_sections))

    # ==============================================================================
    # 2. LAW FIRM: Vanguard & Holloway Appellate Law (Split-Hero Archetype)
    # ==============================================================================
    t2_brief = """<content_brief>
  <business_name>Vanguard & Holloway Appellate Law</business_name>
  <tagline>First-Chair Appellate Defense & Federal Constitutional Litigation</tagline>
  <business_type>legal</business_type>
  <layout_archetype>split_hero</layout_archetype>
  <layout_guidelines>Split-hero legal layout with Supreme Court case docket, State Bar of California Bar #294819, Rule 7.1 notice, and appellate win statistics.</layout_guidelines>
  <sections>header, hero, appellate_docket, practice_areas, footer</sections>
  <contact>
    <address>555 California St, Suite 3200, San Francisco, CA 94104</address>
    <phone>+1 (415) 555-0199</phone>
    <email>intake@vanguard-appellate.com</email>
    <hours>Mon–Fri: 8:00am–6:00pm PST | 24/7 Injunction Emergency Line</hours>
  </contact>
</content_brief>"""

    t2_sections = [
        {
            "name": "Header",
            "instruction": "legal header with state bar certification badge and intake contact. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building legal header with State Bar credentials.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="vg-header" role="banner">
      <div className="vg-header__container">
        <div className="vg-header__brand">
          <a href="#hero" className="vg-header__logo">
            <span className="vg-header__logo-text">VANGUARD & HOLLOWAY</span>
            <span className="vg-header__sub">APPELLATE & CONSTITUTIONAL COUNSEL</span>
          </a>
          <span className="vg-header__bar-badge">CALIFORNIA BAR #294819 • NY BAR #4819201</span>
        </div>
        <nav className="vg-header__nav">
          <a href="#docket">Active Docket</a>
          <a href="#practices">Appellate Areas</a>
          <a href="#contact" className="vg-header__cta">Retain Counsel</a>
        </nav>
      </div>
    </header>
  );
}
""",
            "css": """.vg-header {
  background-color: #0b1329;
  border-bottom: 1px solid #1e293b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  position: sticky;
  top: 0;
  z-index: 50;
}

.vg-header__container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0.9rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.vg-header__brand {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.vg-header__logo {
  text-decoration: none;
  display: flex;
  flex-direction: column;
}

.vg-header__logo-text {
  font-family: "Georgia", serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: 0.04em;
}

.vg-header__sub {
  font-size: 0.65rem;
  color: #94a3b8;
  letter-spacing: 0.08em;
}

.vg-header__bar-badge {
  background-color: #1e293b;
  color: #cbd5e1;
  font-size: 0.7rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.vg-header__nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.vg-header__nav a {
  color: #cbd5e1;
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 600;
}

.vg-header__cta {
  background-color: #2563eb;
  color: #ffffff !important;
  padding: 0.45rem 0.95rem;
  border-radius: 4px;
}

@media (max-width: 800px) {
  .vg-header__bar-badge { display: none; }
}
"""
        },
        {
            "name": "Hero",
            "instruction": "split hero layout with appellate docket statistics and constitutional case study. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Split-Hero for Vanguard & Holloway with appellate win statistics.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="vg-hero" id="hero">
      <div className="vg-hero__container">
        <div className="vg-hero__grid">
          <div className="vg-hero__left">
            <span className="vg-hero__tag">SUPREME COURT & FEDERAL CIRCUIT PRACTICE</span>
            <h1 className="vg-hero__title">
              Preserving Lower Court Victories. Reversing Erroneous Precedent.
            </h1>
            <p className="vg-hero__lead">
              Our partners have argued 14 appeals before the Supreme Court of the United States and over 120 federal en banc and circuit proceedings, establishing landmark precedent in patent eligibility, constitutional commerce, and administrative law.
            </p>
            <div className="vg-hero__actions">
              <a href="#docket" className="vg-hero__btn-primary">View Federal Docket</a>
              <a href="#contact" className="vg-hero__btn-secondary">Conflict Screening</a>
            </div>
          </div>

          <div className="vg-hero__right">
            <div className="vg-hero__docket-card">
              <div className="vg-hero__card-top">
                <span className="vg-hero__case-status">● CERT GRANTED</span>
                <span className="vg-hero__court">SCOTUS No. 25-849</span>
              </div>
              <h3 className="vg-hero__case-name">Axiom BioTech v. Federal Trade Commission</h3>
              <p className="vg-hero__case-summary">
                First-chair representation challenging administrative adjudication boundaries under Article III and the Due Process Clause.
              </p>
              <div className="vg-hero__stat-row">
                <div>
                  <strong className="vg-hero__stat-num">89.4%</strong>
                  <span className="vg-hero__stat-lbl">Circuit Reversal Rate</span>
                </div>
                <div>
                  <strong className="vg-hero__stat-num">14</strong>
                  <span className="vg-hero__stat-lbl">SCOTUS Arguments</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.vg-hero {
  background-color: #0b1329;
  color: #f8fafc;
  padding: 5rem 1.5rem;
  border-bottom: 1px solid #1e293b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.vg-hero__container {
  max-width: 1200px;
  margin: 0 auto;
}

.vg-hero__grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 3.5rem;
  align-items: center;
}

.vg-hero__tag {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #60a5fa;
  display: block;
  margin-bottom: 1rem;
}

.vg-hero__title {
  font-family: "Georgia", serif;
  font-size: 2.85rem;
  line-height: 1.15;
  color: #ffffff;
  margin: 0 0 1.25rem 0;
}

.vg-hero__lead {
  font-size: 1.05rem;
  line-height: 1.6;
  color: #94a3b8;
  margin: 0 0 2rem 0;
}

.vg-hero__actions {
  display: flex;
  gap: 1rem;
}

.vg-hero__btn-primary {
  background-color: #2563eb;
  color: #ffffff;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  font-weight: 600;
  text-decoration: none;
}

.vg-hero__btn-secondary {
  border: 1px solid #334155;
  color: #cbd5e1;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  font-weight: 600;
  text-decoration: none;
}

.vg-hero__docket-card {
  background-color: #111c38;
  border: 1px solid #1e293b;
  border-left: 3px solid #2563eb;
  padding: 2rem;
  border-radius: 6px;
}

.vg-hero__card-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
  font-size: 0.75rem;
}

.vg-hero__case-status {
  color: #34d399;
  font-weight: 700;
}

.vg-hero__court {
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.vg-hero__case-name {
  font-family: "Georgia", serif;
  font-size: 1.25rem;
  color: #ffffff;
  margin: 0 0 0.75rem 0;
}

.vg-hero__case-summary {
  font-size: 0.875rem;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0 0 1.5rem 0;
}

.vg-hero__stat-row {
  display: flex;
  gap: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #1e293b;
}

.vg-hero__stat-num {
  display: block;
  font-size: 1.5rem;
  color: #ffffff;
}

.vg-hero__stat-lbl {
  font-size: 0.75rem;
  color: #64748b;
}

@media (max-width: 900px) {
  .vg-hero__grid { grid-template-columns: 1fr; }
}
"""
        },
        {
            "name": "Footer",
            "instruction": "legal footer with State Bar Rule 7.1 advertising notice and disclaimers. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building legal footer with statutory advertising notice.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="vg-footer" role="contentinfo">
      <div className="vg-footer__container">
        <div className="vg-footer__top">
          <div className="vg-footer__brand">
            <span className="vg-footer__firm-name">Vanguard & Holloway Appellate Law</span>
            <p className="vg-footer__disclaimer">
              ATTORNEY ADVERTISING: Prior results do not guarantee a similar outcome. The information on this website is for informational purposes only and does not constitute legal advice. No attorney-client relationship is created until an engagement letter is signed.
            </p>
            <span className="vg-footer__bar-info">Responsible Managing Partner: Arthur Vance (CA State Bar #294819).</span>
          </div>
          <div className="vg-footer__col">
            <h4>Chambers</h4>
            <address>
              555 California St, Suite 3200<br />
              San Francisco, CA 94104<br />
              Direct: +1 (415) 555-0199
            </address>
          </div>
        </div>
        <div className="vg-footer__bottom">
          <span>© {new Date().getFullYear()} Vanguard & Holloway LLP. All rights reserved.</span>
          <div className="vg-footer__links">
            <a href="#disclaimer">Disclaimers</a>
            <a href="#privacy">Privacy</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
""",
            "css": """.vg-footer {
  background-color: #070c1a;
  color: #64748b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  padding: 3rem 1.5rem 2rem;
}

.vg-footer__container {
  max-width: 1200px;
  margin: 0 auto;
}

.vg-footer__top {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2.5rem;
  margin-bottom: 2rem;
}

.vg-footer__firm-name {
  font-family: "Georgia", serif;
  font-size: 1.05rem;
  color: #f8fafc;
  display: block;
  margin-bottom: 0.5rem;
}

.vg-footer__disclaimer {
  font-size: 0.75rem;
  line-height: 1.5;
  color: #64748b;
  margin: 0 0 0.5rem 0;
}

.vg-footer__bar-info {
  font-size: 0.75rem;
  color: #94a3b8;
}

.vg-footer__col h4 {
  color: #f8fafc;
  font-size: 0.75rem;
  text-transform: uppercase;
  margin: 0 0 0.5rem 0;
}

.vg-footer__col address {
  font-style: normal;
  line-height: 1.5;
}

.vg-footer__bottom {
  border-top: 1px solid #1e293b;
  padding-top: 1.5rem;
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.vg-footer__links {
  display: flex;
  gap: 1rem;
}

.vg-footer__links a {
  color: #64748b;
  text-decoration: none;
}
"""
        }
    ]
    trajs.append(make_traj("site_legal_vanguard_appellate", t2_brief, t2_sections))

    # ==============================================================================
    # 3. TRAVEL AGENCY: Aurora Expeditions & Polar Voyages (Bento Archetype)
    # ==============================================================================
    t3_brief = """<content_brief>
  <business_name>Aurora Expeditions & Polar Voyages</business_name>
  <tagline>Scientific Exploration & High-Latitude Polar Itineraries</tagline>
  <business_type>travel</business_type>
  <layout_archetype>bento</layout_archetype>
  <layout_guidelines>Bento-grid expedition architecture featuring IAATO eco-permit #2026-88, ice-class PC6 polar vessels, and naturalist telemetry.</layout_guidelines>
  <sections>header, hero, bento_expeditions, footer</sections>
  <contact>
    <address>100 Harbor Way, Pier 3, Seattle, WA 98101</address>
    <phone>+1 (206) 555-0188</phone>
    <email>expeditions@aurora-polar.com</email>
    <hours>Mon–Fri: 8:00am–5:00pm PST</hours>
  </contact>
</content_brief>"""

    t3_sections = [
        {
            "name": "Header",
            "instruction": "polar expedition header with IAATO membership badge. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building polar expedition header.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="ae-header" role="banner">
      <div className="ae-header__inner">
        <a href="#hero" className="ae-header__brand">
          <span className="ae-header__logo-mark">▲</span>
          <span className="ae-header__name">AURORA EXPEDITIONS</span>
        </a>
        <span className="ae-header__permit">IAATO PERMIT #2026-88 • PC6 ICE-CLASS</span>
        <nav className="ae-header__nav">
          <a href="#expeditions">Polar Routes</a>
          <a href="#vessel">Ice Fleet</a>
          <a href="#contact" className="ae-header__btn">Request Berth</a>
        </nav>
      </div>
    </header>
  );
}
""",
            "css": """.ae-header {
  background-color: #030712;
  border-bottom: 1px solid #1f2937;
  color: #f9fafb;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  position: sticky;
  top: 0;
  z-index: 50;
}

.ae-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0.9rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ae-header__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: #ffffff;
}

.ae-header__logo-mark {
  color: #38bdf8;
  font-size: 1rem;
}

.ae-header__name {
  font-weight: 800;
  letter-spacing: 0.05em;
  font-size: 1rem;
}

.ae-header__permit {
  font-size: 0.6875rem;
  font-family: ui-monospace, SFMono-Regular, monospace;
  background-color: #0c4a6e;
  color: #bae6fd;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
}

.ae-header__nav {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.ae-header__nav a {
  color: #9ca3af;
  text-decoration: none;
  font-size: 0.8125rem;
}

.ae-header__btn {
  background-color: #0284c7;
  color: #ffffff !important;
  padding: 0.45rem 1rem;
  border-radius: 4px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .ae-header__permit { display: none; }
}
"""
        },
        {
            "name": "BentoExpeditions",
            "instruction": "asymmetric bento grid of polar routes, wildlife telemetry, and ice conditions. Files: src/components/BentoExpeditions.tsx + src/components/BentoExpeditions.css",
            "tsx_path": "src/components/BentoExpeditions.tsx",
            "css_path": "src/components/BentoExpeditions.css",
            "thought": "Building BentoExpeditions layout with varied card spans.",
            "tsx": """import React from 'react';
import './BentoExpeditions.css';

export function BentoExpeditions() {
  return (
    <section className="ae-bento" id="expeditions">
      <div className="ae-bento__container">
        <div className="ae-bento__header">
          <span className="ae-bento__tag">EXPEDITION MANIFEST</span>
          <h2 className="ae-bento__title">Asymmetric Bento Polar Routes</h2>
        </div>

        <div className="ae-bento__grid">
          <div className="ae-bento__card ae-bento__card--wide">
            <span className="ae-bento__pill">DEEP SOUTH EXPEDITION</span>
            <h3 className="ae-bento__card-title">Antarctic Peninsula & Weddell Sea</h3>
            <p className="ae-bento__card-body">
              18-day exploratory voyage charting Emperor penguin rookeries and tabular iceberg alleys aboard our PC6 ice-class expedition vessel. Led by glaciologists and ornithologists.
            </p>
            <div className="ae-bento__card-stats">
              <span><strong>18 Days</strong> Duration</span>
              <span><strong>132 Pax</strong> Max Capacity</span>
              <span><strong>PC6</strong> Hull Strength</span>
            </div>
          </div>

          <div className="ae-bento__card">
            <span className="ae-bento__pill">HIGH ARCTIC</span>
            <h3 className="ae-bento__card-title">Svalbard Pack Ice</h3>
            <p className="ae-bento__card-body">
              Circumnavigating Spitsbergen to 82° North during peak midnight sun. Zodiac cruising alongside blue whales and walrus colonies.
            </p>
          </div>

          <div className="ae-bento__card">
            <span className="ae-bento__pill">SCIENTIFIC CITIZENRY</span>
            <h3 className="ae-bento__card-title">NASA Ocean Cloud Albedo Study</h3>
            <p className="ae-bento__card-body">
              En-route atmospheric aerosol measurements contributing directly to global climatology models.
            </p>
          </div>

          <div className="ae-bento__card ae-bento__card--wide">
            <span className="ae-bento__pill">IAATO CERTIFICATION</span>
            <h3 className="ae-bento__card-title">Zero-Impact Eco-Protocol</h3>
            <p className="ae-bento__card-body">
              100% wastewater purification, single-use plastic prohibition, and biological quarantine wash stations conforming to IAATO Antarctica treaty guidelines.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.ae-bento {
  background-color: #030712;
  color: #f9fafb;
  padding: 4.5rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.ae-bento__container {
  max-width: 1200px;
  margin: 0 auto;
}

.ae-bento__header {
  margin-bottom: 2.5rem;
}

.ae-bento__tag {
  color: #38bdf8;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.ae-bento__title {
  font-size: 2.2rem;
  font-weight: 800;
  margin: 0.35rem 0 0 0;
}

.ae-bento__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.ae-bento__card {
  background-color: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 1.75rem;
}

.ae-bento__card--wide {
  grid-column: span 2;
}

.ae-bento__pill {
  font-size: 0.6875rem;
  font-weight: 700;
  color: #38bdf8;
  background-color: #0c4a6e;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.ae-bento__card-title {
  font-size: 1.3rem;
  margin: 0.75rem 0 0.5rem 0;
}

.ae-bento__card-body {
  font-size: 0.875rem;
  color: #94a3b8;
  line-height: 1.5;
}

.ae-bento__card-stats {
  display: flex;
  gap: 1.5rem;
  margin-top: 1rem;
  font-size: 0.8125rem;
  color: #cbd5e1;
}

@media (max-width: 800px) {
  .ae-bento__grid { grid-template-columns: 1fr; }
  .ae-bento__card--wide { grid-column: span 1; }
}
"""
        },
        {
            "name": "Footer",
            "instruction": "polar expedition footer with IAATO eco-permit and vessel coordinates. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building polar expedition footer.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="ae-footer" role="contentinfo">
      <div className="ae-footer__container">
        <div className="ae-footer__top">
          <div>
            <span className="ae-footer__brand">Aurora Expeditions & Polar Voyages</span>
            <p className="ae-footer__desc">International Association of Antarctica Tour Operators Member #2026-88.</p>
          </div>
          <address className="ae-footer__addr">
            100 Harbor Way, Pier 3<br />
            Seattle, WA 98101<br />
            expeditions@aurora-polar.com
          </address>
        </div>
        <div className="ae-footer__bottom">
          <span>© {new Date().getFullYear()} Aurora Expeditions Inc. All rights reserved.</span>
        </div>
      </div>
    </footer>
  );
}
""",
            "css": """.ae-footer {
  background-color: #020617;
  color: #64748b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  padding: 3rem 1.5rem;
  border-top: 1px solid #1e293b;
}

.ae-footer__container {
  max-width: 1200px;
  margin: 0 auto;
}

.ae-footer__top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.ae-footer__brand {
  font-weight: 700;
  color: #f8fafc;
  display: block;
}

.ae-footer__desc {
  margin: 0.25rem 0 0 0;
  color: #94a3b8;
}

.ae-footer__addr {
  font-style: normal;
  line-height: 1.5;
}

.ae-footer__bottom {
  border-top: 1px solid #1e293b;
  padding-top: 1rem;
}
"""
        }
    ]
    trajs.append(make_traj("site_travel_aurora_polar", t3_brief, t3_sections))

    # ==============================================================================
    # 4. RAMEN RESTAURANT: Kuroshio Craft Ramen & Izakaya (Tabs Archetype)
    # ==============================================================================
    t4_brief = """<content_brief>
  <business_name>Kuroshio Craft Ramen & Izakaya</business_name>
  <tagline>Twenty-Hour Simmered Broth, Hand-Pulled Wheat Noodles & Izakaya Small Plates</tagline>
  <business_type>restaurant</business_type>
  <layout_archetype>tabs</layout_archetype>
  <layout_guidelines>Tabbed noodle/broth architecture switching between Tonkotsu, Tori Paitan, Tsukemen, and Izakaya with allergen matrix.</layout_guidelines>
  <sections>header, hero, noodle_tabs, footer</sections>
  <contact>
    <address>124 Little Tokyo Way, Los Angeles, CA 90012</address>
    <phone>+1 (213) 555-0192</phone>
    <email>kitchen@kuroshio-ramen.com</email>
    <hours>Daily: 11:30am–10:30pm (Broth allocated fresh daily)</hours>
  </contact>
</content_brief>"""

    t4_sections = [
        {
            "name": "Header",
            "instruction": "ramen bar header with broth allocation status. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building ramen header.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="kr-header" role="banner">
      <div className="kr-header__inner">
        <a href="#hero" className="kr-header__brand">
          <span className="kr-header__kanji">黒潮</span>
          <span className="kr-header__name">KUROSHIO RAMEN</span>
        </a>
        <span className="kr-header__broth-meter">TODAY'S TONKOTSU: 20H REDUCTION • 84 BOWLS LEFT</span>
        <nav className="kr-header__nav">
          <a href="#menu">Noodle Tabs</a>
          <a href="#hours">Kitchen Hours</a>
        </nav>
      </div>
    </header>
  );
}
""",
            "css": """.kr-header {
  background-color: #17120e;
  border-bottom: 1px solid #2d241d;
  color: #fafaf9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  position: sticky;
  top: 0;
  z-index: 50;
}

.kr-header__inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0.85rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kr-header__brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  color: #fafaf9;
}

.kr-header__kanji {
  font-size: 1.25rem;
  color: #ea580c;
  font-weight: 800;
}

.kr-header__name {
  font-weight: 800;
  letter-spacing: 0.05em;
  font-size: 0.9375rem;
}

.kr-header__broth-meter {
  font-size: 0.6875rem;
  font-family: ui-monospace, SFMono-Regular, monospace;
  background-color: #431407;
  color: #fdba74;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
}

.kr-header__nav a {
  color: #d6d3d1;
  text-decoration: none;
  font-size: 0.8125rem;
  margin-left: 1.25rem;
}

@media (max-width: 768px) {
  .kr-header__broth-meter { display: none; }
}
"""
        },
        {
            "name": "NoodleTabs",
            "instruction": "stateful tabs switching between Tonkotsu, Tori Paitan, Tsukemen, and Small Plates. Files: src/components/NoodleTabs.tsx + src/components/NoodleTabs.css",
            "tsx_path": "src/components/NoodleTabs.tsx",
            "css_path": "src/components/NoodleTabs.css",
            "thought": "Building stateful NoodleTabs component.",
            "tsx": """import React, { useState } from 'react';
import './NoodleTabs.css';

export function NoodleTabs() {
  const [tab, setTab] = useState('tonkotsu');

  const categories: Record<string, any> = {
    tonkotsu: {
      name: "Signature 20-Hour Tonkotsu",
      broth: "Kagoshima Berkshire pork femur & knuckle simmered 20 hours",
      noodle: "Thin 26-gauge Hakata straight noodle • firm bite",
      price: "$18.50",
      toppings: ["Slow-braised Kurobuta chashu", "Ajitama molten egg", "Charred black garlic mayu oil", "Wood-ear mushroom"]
    },
    paitan: {
      name: "Kyoto White Feather Tori Paitan",
      broth: "Pasture chicken collagen broth with yuzu kosho reduction",
      noodle: "Medium wavy whole-wheat noodle • high springiness",
      price: "$19.00",
      toppings: ["Sous-vide chicken breast", "Menma bamboo shoots", "Shiso leaf", "Crispy shallots"]
    },
    tsukemen: {
      name: "Double-Reduction Dipping Tsukemen",
      broth: "Ultra-concentrated pork and dried katsuobushi dip broth",
      noodle: "Thick 14-gauge cold-rinsed chewy wheat noodle",
      price: "$20.50",
      toppings: ["Thick-cut seared chashu", "Nori sheets", "Lime wedge", "Soup-wari broth finish"]
    }
  };

  const cur = categories[tab] || categories.tonkotsu;

  return (
    <section className="kr-tabs" id="menu">
      <div className="kr-tabs__container">
        <div className="kr-tabs__header">
          <span className="kr-tabs__tag">ARTISANAL BROTHS</span>
          <h2 className="kr-tabs__title">Craft Ramen Modalities</h2>
        </div>

        <div className="kr-tabs__nav" role="tablist">
          <button
            type="button"
            className={`kr-tabs__btn ${tab === 'tonkotsu' ? 'is-active' : ''}`}
            onClick={() => setTab('tonkotsu')}
          >
            Tonkotsu
          </button>
          <button
            type="button"
            className={`kr-tabs__btn ${tab === 'paitan' ? 'is-active' : ''}`}
            onClick={() => setTab('paitan')}
          >
            Tori Paitan
          </button>
          <button
            type="button"
            className={`kr-tabs__btn ${tab === 'tsukemen' ? 'is-active' : ''}`}
            onClick={() => setTab('tsukemen')}
          >
            Dipping Tsukemen
          </button>
        </div>

        <div className="kr-tabs__panel">
          <div className="kr-tabs__top">
            <h3 className="kr-tabs__name">{cur.name}</h3>
            <span className="kr-tabs__price">{cur.price}</span>
          </div>
          <div className="kr-tabs__spec">
            <strong>Broth:</strong> {cur.broth}
          </div>
          <div className="kr-tabs__spec">
            <strong>Noodle:</strong> {cur.noodle}
          </div>
          <div className="kr-tabs__toppings">
            <strong>Key Accompaniments:</strong>
            <ul>
              {cur.toppings.map((t: string, idx: number) => (
                <li key={idx}>• {t}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.kr-tabs {
  background-color: #17120e;
  color: #fafaf9;
  padding: 4.5rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.kr-tabs__container {
  max-width: 900px;
  margin: 0 auto;
}

.kr-tabs__header {
  margin-bottom: 2.5rem;
  text-align: center;
}

.kr-tabs__tag {
  color: #ea580c;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.kr-tabs__title {
  font-size: 2.2rem;
  margin: 0.35rem 0 0 0;
}

.kr-tabs__nav {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.kr-tabs__btn {
  background-color: #292019;
  border: 1px solid #443528;
  color: #d6d3d1;
  padding: 0.6rem 1.25rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.kr-tabs__btn.is-active {
  background-color: #ea580c;
  color: #ffffff;
  border-color: #ea580c;
}

.kr-tabs__panel {
  background-color: #221a14;
  border: 1px solid #36291e;
  border-radius: 8px;
  padding: 2rem;
}

.kr-tabs__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1.25rem;
}

.kr-tabs__name {
  font-size: 1.4rem;
  color: #ffffff;
  margin: 0;
}

.kr-tabs__price {
  font-size: 1.25rem;
  color: #ea580c;
  font-weight: 800;
}

.kr-tabs__spec {
  font-size: 0.875rem;
  margin-bottom: 0.6rem;
  color: #d6d3d1;
}

.kr-tabs__toppings {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid #36291e;
  font-size: 0.875rem;
}

.kr-tabs__toppings ul {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  color: #a8a29e;
}
"""
        },
        {
            "name": "Footer",
            "instruction": "ramen restaurant footer with address and noodle craft statement. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building ramen footer.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="kr-footer" role="contentinfo">
      <div className="kr-footer__container">
        <div>
          <span className="kr-footer__brand">Kuroshio Craft Ramen & Izakaya</span>
          <p className="kr-footer__addr">124 Little Tokyo Way, Los Angeles, CA 90012 | +1 (213) 555-0192</p>
        </div>
        <span className="kr-footer__copy">© {new Date().getFullYear()} Kuroshio Ramen. All rights reserved.</span>
      </div>
    </footer>
  );
}
""",
            "css": """.kr-footer {
  background-color: #0d0a08;
  color: #78716c;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  padding: 2.5rem 1.5rem;
  border-top: 1px solid #241c15;
}

.kr-footer__container {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.kr-footer__brand {
  color: #fafaf9;
  font-weight: 700;
  display: block;
}

.kr-footer__addr {
  margin: 0.25rem 0 0 0;
}
"""
        }
    ]
    trajs.append(make_traj("site_restaurant_kuroshio_ramen", t4_brief, t4_sections))

    # ==============================================================================
    # 5. NONPROFIT: Blue Horizon Marine Conservation (Split-Hero Archetype)
    # ==============================================================================
    t5_brief = """<content_brief>
  <business_name>Blue Horizon Marine Conservation</business_name>
  <tagline>Protecting Pelagic Habitats & Coral Reef Biodiversity</tagline>
  <business_type>nonprofit</business_type>
  <layout_archetype>split_hero</layout_archetype>
  <layout_guidelines>Split-hero nonprofit layout featuring 501(c)(3) tax exempt ID #84-1920481, real-time telemetry metrics, and donation tiers.</layout_guidelines>
  <sections>header, hero, impact_tiers, footer</sections>
  <contact>
    <address>200 Ocean Drive, Suite 500, Monterey, CA 93940</address>
    <phone>+1 (831) 555-0144</phone>
    <email>impact@bluehorizon-marine.org</email>
    <hours>Mon–Fri: 9:00am–5:00pm PST</hours>
  </contact>
</content_brief>"""

    t5_sections = [
        {
            "name": "Header",
            "instruction": "nonprofit header with 501(c)(3) verification seal. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building nonprofit header with tax-exempt disclosure.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="bh-header" role="banner">
      <div className="bh-header__inner">
        <a href="#hero" className="bh-header__logo">
          <span className="bh-header__mark">🌊</span>
          <span className="bh-header__name">BLUE HORIZON MARINE</span>
        </a>
        <span className="bh-header__501c3">501(C)(3) PUBLIC CHARITY • EIN #84-1920481</span>
        <nav className="bh-header__nav">
          <a href="#impact">Reef Impact</a>
          <a href="#donate" className="bh-header__donate-btn">Support Sanctuary</a>
        </nav>
      </div>
    </header>
  );
}
""",
            "css": """.bh-header {
  background-color: #082f49;
  color: #f0f9ff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  padding: 0.85rem 1.5rem;
  position: sticky;
  top: 0;
  z-index: 50;
  border-bottom: 1px solid #0c4a6e;
}

.bh-header__inner {
  max-width: 1150px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bh-header__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: #f0f9ff;
  font-weight: 800;
}

.bh-header__501c3 {
  font-size: 0.6875rem;
  font-family: ui-monospace, SFMono-Regular, monospace;
  background-color: #0369a1;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.bh-header__nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.bh-header__nav a {
  color: #bae6fd;
  text-decoration: none;
  font-size: 0.8125rem;
}

.bh-header__donate-btn {
  background-color: #0284c7;
  color: #ffffff !important;
  padding: 0.45rem 1rem;
  border-radius: 4px;
  font-weight: 700;
}

@media (max-width: 768px) {
  .bh-header__501c3 { display: none; }
}
"""
        },
        {
            "name": "Hero",
            "instruction": "split hero with coral reef restoration telemetry and donation tiers. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building split hero for Blue Horizon.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="bh-hero" id="hero">
      <div className="bh-hero__container">
        <div className="bh-hero__grid">
          <div className="bh-hero__content">
            <span className="bh-hero__tag">OPEN OCEAN STEWARDSHIP</span>
            <h1 className="bh-hero__title">
              Restoring 10,000 Hectares of Living Coral Bio-Sanctuary.
            </h1>
            <p className="bh-hero__desc">
              Blue Horizon combines micro-fragmentation coral nursery technology with autonomous marine patrol drones to protect endangered pelagic breeding corridors.
            </p>
            <div className="bh-hero__actions">
              <a href="#donate" className="bh-hero__cta">Fund Nursery Outplant</a>
              <a href="#impact" className="bh-hero__link">View 2026 Audit Report</a>
            </div>
          </div>

          <div className="bh-hero__telemetry">
            <div className="bh-hero__stat-card">
              <span className="bh-hero__stat-label">Corals Outplanted</span>
              <strong className="bh-hero__stat-num">48,290</strong>
              <span className="bh-hero__stat-sub">Across 14 Pacific Barrier Reef sites</span>
            </div>
            <div className="bh-hero__stat-card">
              <span className="bh-hero__stat-label">Patrol Coverage</span>
              <strong className="bh-hero__stat-num">98.2%</strong>
              <span className="bh-hero__stat-sub">Zero illegal longline incursions in 2025</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.bh-hero {
  background: linear-gradient(180deg, #082f49 0%, #0c4a6e 100%);
  color: #f0f9ff;
  padding: 5rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.bh-hero__container {
  max-width: 1150px;
  margin: 0 auto;
}

.bh-hero__grid {
  display: grid;
  grid-template-columns: 1.3fr 0.7fr;
  gap: 3rem;
  align-items: center;
}

.bh-hero__tag {
  color: #38bdf8;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  display: block;
  margin-bottom: 0.75rem;
}

.bh-hero__title {
  font-size: 2.85rem;
  line-height: 1.15;
  margin: 0 0 1.25rem 0;
  font-weight: 800;
}

.bh-hero__desc {
  font-size: 1.05rem;
  line-height: 1.6;
  color: #bae6fd;
  margin: 0 0 2rem 0;
}

.bh-hero__actions {
  display: flex;
  gap: 1.25rem;
  align-items: center;
}

.bh-hero__cta {
  background-color: #38bdf8;
  color: #082f49;
  font-weight: 700;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  text-decoration: none;
}

.bh-hero__link {
  color: #e0f2fe;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 600;
}

.bh-hero__telemetry {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.bh-hero__stat-card {
  background-color: rgba(12, 74, 110, 0.6);
  border: 1px solid #0369a1;
  padding: 1.5rem;
  border-radius: 8px;
}

.bh-hero__stat-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #7dd3fc;
  display: block;
}

.bh-hero__stat-num {
  font-size: 2.2rem;
  font-weight: 800;
  color: #ffffff;
  display: block;
  margin: 0.25rem 0;
}

.bh-hero__stat-sub {
  font-size: 0.75rem;
  color: #bae6fd;
}

@media (max-width: 800px) {
  .bh-hero__grid { grid-template-columns: 1fr; }
}
"""
        },
        {
            "name": "Footer",
            "instruction": "nonprofit footer with 501(c)(3) tax exempt disclosures and audited financials link. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building nonprofit footer.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="bh-footer" role="contentinfo">
      <div className="bh-footer__container">
        <div>
          <span className="bh-footer__name">Blue Horizon Marine Conservation Foundation</span>
          <p className="bh-footer__tax">501(c)(3) Tax-Exempt Non-Profit Organization • EIN: 84-1920481</p>
        </div>
        <address className="bh-footer__addr">
          200 Ocean Drive, Suite 500, Monterey, CA 93940 | impact@bluehorizon-marine.org
        </address>
        <div className="bh-footer__copy">
          © {new Date().getFullYear()} Blue Horizon Foundation. Donations are tax-deductible to the extent allowed by law.
        </div>
      </div>
    </footer>
  );
}
""",
            "css": """.bh-footer {
  background-color: #031e30;
  color: #7dd3fc;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  padding: 2.5rem 1.5rem;
}

.bh-footer__container {
  max-width: 1150px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.bh-footer__name {
  font-weight: 700;
  color: #f0f9ff;
  font-size: 0.9375rem;
}

.bh-footer__tax {
  margin: 0.2rem 0 0 0;
  color: #38bdf8;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.bh-footer__addr {
  font-style: normal;
  color: #bae6fd;
}

.bh-footer__copy {
  border-top: 1px solid #0c4a6e;
  padding-top: 1rem;
  font-size: 0.75rem;
  color: #7dd3fc;
}
"""
        }
    ]
    trajs.append(make_traj("site_nonprofit_blue_horizon", t5_brief, t5_sections))

    # ==============================================================================
    # 6. REAL ESTATE: Meridian Architectural Lofts & Penthouses (Bento Archetype)
    # ==============================================================================
    t6_brief = """<content_brief>
  <business_name>Meridian Architectural Lofts & Penthouses</business_name>
  <tagline>Custom Coastal Residences & Award-Winning Mid-Century Living</tagline>
  <business_type>real_estate</business_type>
  <layout_archetype>bento</layout_archetype>
  <layout_guidelines>Bento-grid architectural property showcase with CalDRE Broker Lic #01928472, NMLS #381920, and LiDAR floor specifications.</layout_guidelines>
  <sections>header, hero, bento_properties, footer</sections>
  <contact>
    <address>100 Ocean Avenue, Suite 1200, Santa Monica, CA 90401</address>
    <phone>+1 (310) 555-0182</phone>
    <email>concierge@meridian-lofts.com</email>
    <hours>Mon–Sun: 9:00am–7:00pm PST</hours>
  </contact>
</content_brief>"""

    t6_sections = [
        {
            "name": "Header",
            "instruction": "real estate header with CalDRE license number. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building real estate header with licensing metadata.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="ml-header" role="banner">
      <div className="ml-header__container">
        <a href="#hero" className="ml-header__brand">MERIDIAN LOFTS</a>
        <span className="ml-header__lic">CalDRE #01928472 • NMLS #381920</span>
        <nav className="ml-header__nav">
          <a href="#properties">Penthouses</a>
          <a href="#contact" className="ml-header__cta">Private Showing</a>
        </nav>
      </div>
    </header>
  );
}
""",
            "css": """.ml-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 1rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  position: sticky;
  top: 0;
  z-index: 50;
}

.ml-header__container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ml-header__brand {
  font-weight: 800;
  color: #111827;
  text-decoration: none;
  letter-spacing: 0.05em;
  font-size: 1.1rem;
}

.ml-header__lic {
  font-size: 0.75rem;
  color: #6b7280;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.ml-header__nav {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.ml-header__nav a {
  color: #374151;
  text-decoration: none;
  font-size: 0.875rem;
}

.ml-header__cta {
  background-color: #111827;
  color: #ffffff !important;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 600;
}
"""
        },
        {
            "name": "BentoProperties",
            "instruction": "bento grid architectural property catalog with laser-surveyed LiDAR specs. Files: src/components/BentoProperties.tsx + src/components/BentoProperties.css",
            "tsx_path": "src/components/BentoProperties.tsx",
            "css_path": "src/components/BentoProperties.css",
            "thought": "Building BentoProperties architectural cards.",
            "tsx": """import React from 'react';
import './BentoProperties.css';

export function BentoProperties() {
  return (
    <section className="ml-bento" id="properties">
      <div className="ml-bento__container">
        <div className="ml-bento__header">
          <span className="ml-bento__tag">EXCLUSIVE LISTINGS</span>
          <h2 className="ml-bento__title">Architectural Bento Collection</h2>
        </div>

        <div className="ml-bento__grid">
          <div className="ml-bento__card ml-bento__card--wide">
            <span className="ml-bento__pill">SANTA MONICA WATERFRONT</span>
            <h3 className="ml-bento__name">The Pacific Coastline Sky-Villa</h3>
            <p className="ml-bento__desc">
              Four-bedroom full-floor penthouse with 360-degree marine horizon views, cantilevered cedar terrace, and private direct elevator foyer.
            </p>
            <div className="ml-bento__specs">
              <span><strong>4,850</strong> Sq Ft (LiDAR Surveyed)</span>
              <span><strong>4 Bed</strong> / 4.5 Bath</span>
              <span><strong>$14,250,000</strong></span>
            </div>
          </div>

          <div className="ml-bento__card">
            <span className="ml-bento__pill">VENICE CANALS</span>
            <h3 className="ml-bento__name">The Modernist Glass Pavilion</h3>
            <p className="ml-bento__desc">
              Architectural residence designed by Ray Kappe FAIA featuring exposed board-formed concrete, board-formed teak, and zen atrium.
            </p>
            <div className="ml-bento__specs">
              <span><strong>3,100</strong> Sq Ft</span>
              <span><strong>$7,900,000</strong></span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.ml-bento {
  background-color: #f9fafb;
  padding: 4.5rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.ml-bento__container {
  max-width: 1200px;
  margin: 0 auto;
}

.ml-bento__header {
  margin-bottom: 2.5rem;
}

.ml-bento__tag {
  font-size: 0.75rem;
  font-weight: 700;
  color: #4b5563;
  letter-spacing: 0.08em;
}

.ml-bento__title {
  font-size: 2.2rem;
  color: #111827;
  margin: 0.35rem 0 0 0;
  font-weight: 800;
}

.ml-bento__grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

.ml-bento__card {
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  padding: 2rem;
  border-radius: 8px;
}

.ml-bento__pill {
  font-size: 0.6875rem;
  font-weight: 700;
  background-color: #f3f4f6;
  color: #374151;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
}

.ml-bento__name {
  font-size: 1.4rem;
  color: #111827;
  margin: 0.75rem 0 0.5rem 0;
}

.ml-bento__desc {
  font-size: 0.875rem;
  color: #4b5563;
  line-height: 1.5;
  margin: 0 0 1.5rem 0;
}

.ml-bento__specs {
  display: flex;
  gap: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #f3f4f6;
  font-size: 0.8125rem;
  color: #111827;
}

@media (max-width: 800px) {
  .ml-bento__grid { grid-template-columns: 1fr; }
}
"""
        },
        {
            "name": "Footer",
            "instruction": "real estate footer with Equal Housing Opportunity disclosure and license verification. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building real estate footer.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="ml-footer" role="contentinfo">
      <div className="ml-footer__container">
        <div>
          <span className="ml-footer__firm">Meridian Architectural Lofts & Penthouses</span>
          <p className="ml-footer__lic">California Department of Real Estate Broker License #01928472 | Equal Housing Opportunity Provider</p>
        </div>
        <address className="ml-footer__addr">
          100 Ocean Avenue, Suite 1200, Santa Monica, CA 90401 | concierge@meridian-lofts.com
        </address>
        <span className="ml-footer__copy">© {new Date().getFullYear()} Meridian Lofts Inc. All rights reserved.</span>
      </div>
    </footer>
  );
}
""",
            "css": """.ml-footer {
  background-color: #111827;
  color: #9ca3af;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  padding: 3rem 1.5rem;
}

.ml-footer__container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.ml-footer__firm {
  color: #ffffff;
  font-weight: 700;
  font-size: 0.9375rem;
}

.ml-footer__lic {
  margin: 0.25rem 0 0 0;
  color: #d1d5db;
}

.ml-footer__addr {
  font-style: normal;
}

.ml-footer__copy {
  border-top: 1px solid #1f2937;
  padding-top: 1rem;
  font-size: 0.75rem;
}
"""
        }
    ]
    trajs.append(make_traj("site_realestate_meridian_architectural", t6_brief, t6_sections))

    # ==============================================================================
    # 7. EDUCATION: Quantum STEM & Computational Robotics Academy (Tabs Archetype)
    # ==============================================================================
    t7_brief = """<content_brief>
  <business_name>Quantum STEM & Robotics Academy</business_name>
  <tagline>Pioneering Algorithmic Computer Science, Embedded Robotics & Applied AI</tagline>
  <business_type>education</business_type>
  <layout_archetype>tabs</layout_archetype>
  <layout_guidelines>Tabbed curriculum architecture switching between Robotics, Autonomous Systems, and Full-Ride Fellowships with WASC accreditation #928401.</layout_guidelines>
  <sections>header, hero, curriculum_tabs, footer</sections>
  <contact>
    <address>500 Technology Square, Cambridge, MA 02139</address>
    <phone>+1 (617) 555-0190</phone>
    <email>admissions@quantum-stem.edu</email>
    <hours>Mon–Fri: 8:00am–6:00pm EST</hours>
  </contact>
</content_brief>"""

    t7_sections = [
        {
            "name": "Header",
            "instruction": "STEM education header with WASC accreditation badge. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building STEM academy header.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="qs-header" role="banner">
      <div className="qs-header__inner">
        <a href="#hero" className="qs-header__logo">
          <span className="qs-header__symbol">⚡</span>
          <span className="qs-header__name">QUANTUM STEM ACADEMY</span>
        </a>
        <span className="qs-header__wasc">WASC ACCREDITED INSTITUTION #928401</span>
        <nav className="qs-header__nav">
          <a href="#curriculum">Curriculum Tracks</a>
          <a href="#admissions" className="qs-header__apply-btn">Apply for Fall 2026</a>
        </nav>
      </div>
    </header>
  );
}
""",
            "css": """.qs-header {
  background-color: #0f172a;
  border-bottom: 1px solid #1e293b;
  color: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  padding: 0.85rem 1.5rem;
  position: sticky;
  top: 0;
  z-index: 50;
}

.qs-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.qs-header__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: #f8fafc;
  font-weight: 800;
}

.qs-header__symbol {
  color: #818cf8;
}

.qs-header__wasc {
  font-size: 0.6875rem;
  font-family: ui-monospace, SFMono-Regular, monospace;
  background-color: #1e1b4b;
  color: #c7d2fe;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.qs-header__nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.qs-header__nav a {
  color: #cbd5e1;
  text-decoration: none;
  font-size: 0.8125rem;
}

.qs-header__apply-btn {
  background-color: #4f46e5;
  color: #ffffff !important;
  padding: 0.45rem 1rem;
  border-radius: 4px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .qs-header__wasc { display: none; }
}
"""
        },
        {
            "name": "CurriculumTabs",
            "instruction": "stateful curriculum tabs switching between Embedded Robotics, Neural Networks, and Fellowship Tracks. Files: src/components/CurriculumTabs.tsx + src/components/CurriculumTabs.css",
            "tsx_path": "src/components/CurriculumTabs.tsx",
            "css_path": "src/components/CurriculumTabs.css",
            "thought": "Building stateful CurriculumTabs.",
            "tsx": """import React, { useState } from 'react';
import './CurriculumTabs.css';

export function CurriculumTabs() {
  const [track, setTrack] = useState('robotics');

  const tracks: Record<string, any> = {
    robotics: {
      title: "Embedded Robotics & Kinematics",
      duration: "16 Weeks • 40 Lab Hours/Week",
      focus: "Hardware-in-the-loop motor controllers, ROS2 micro-ros, and brushless actuator design.",
      stack: ["C++20", "ROS2 Humble", "STM32 Arm Cortex-M7", "Gazebo Physics Sim"]
    },
    neural: {
      title: "Applied AI & Visual SLAM",
      duration: "16 Weeks • GPU Cluster Access",
      focus: "LiDAR odometry, Transformer vision backbones, and real-time tensor inference on edge compute.",
      stack: ["PyTorch 2.4", "CUDA C++", "TensorRT", "NVIDIA Jetson Orin"]
    }
  };

  const active = tracks[track] || tracks.robotics;

  return (
    <section className="qs-curriculum" id="curriculum">
      <div className="qs-curriculum__container">
        <div className="qs-curriculum__header">
          <span className="qs-curriculum__tag">TECHNICAL ACCELERATION</span>
          <h2 className="qs-curriculum__title">Curriculum Specializations</h2>
        </div>

        <div className="qs-curriculum__nav" role="tablist">
          <button
            type="button"
            className={`qs-curriculum__btn ${track === 'robotics' ? 'is-active' : ''}`}
            onClick={() => setTrack('robotics')}
          >
            Robotics & Kinematics
          </button>
          <button
            type="button"
            className={`qs-curriculum__btn ${track === 'neural' ? 'is-active' : ''}`}
            onClick={() => setTrack('neural')}
          >
            Neural Systems & SLAM
          </button>
        </div>

        <div className="qs-curriculum__panel">
          <div className="qs-curriculum__panel-header">
            <h3 className="qs-curriculum__panel-title">{active.title}</h3>
            <span className="qs-curriculum__duration">{active.duration}</span>
          </div>
          <p className="qs-curriculum__focus">{active.focus}</p>
          <div className="qs-curriculum__stack-row">
            <strong>Laboratory Technologies:</strong>
            <div className="qs-curriculum__badges">
              {active.stack.map((s: string, idx: number) => (
                <span key={idx} className="qs-curriculum__badge">{s}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.qs-curriculum {
  background-color: #0f172a;
  color: #f8fafc;
  padding: 4.5rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.qs-curriculum__container {
  max-width: 960px;
  margin: 0 auto;
}

.qs-curriculum__header {
  margin-bottom: 2.5rem;
  text-align: center;
}

.qs-curriculum__tag {
  color: #818cf8;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.qs-curriculum__title {
  font-size: 2.2rem;
  margin: 0.35rem 0 0 0;
  font-weight: 800;
}

.qs-curriculum__nav {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.qs-curriculum__btn {
  background-color: #1e293b;
  border: 1px solid #334155;
  color: #cbd5e1;
  padding: 0.6rem 1.25rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.qs-curriculum__btn.is-active {
  background-color: #4f46e5;
  color: #ffffff;
  border-color: #4f46e5;
}

.qs-curriculum__panel {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 2rem;
}

.qs-curriculum__panel-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1rem;
}

.qs-curriculum__panel-title {
  font-size: 1.35rem;
  color: #ffffff;
  margin: 0;
}

.qs-curriculum__duration {
  font-size: 0.8125rem;
  color: #818cf8;
  font-weight: 600;
}

.qs-curriculum__focus {
  font-size: 0.9375rem;
  line-height: 1.55;
  color: #94a3b8;
  margin: 0 0 1.5rem 0;
}

.qs-curriculum__stack-row {
  border-top: 1px solid #334155;
  padding-top: 1rem;
  font-size: 0.8125rem;
}

.qs-curriculum__badges {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.qs-curriculum__badge {
  background-color: #0f172a;
  border: 1px solid #475569;
  color: #c7d2fe;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, monospace;
}
"""
        },
        {
            "name": "Footer",
            "instruction": "STEM education footer with WASC accreditation and admissions office contacts. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building STEM academy footer.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="qs-footer" role="contentinfo">
      <div className="qs-footer__container">
        <div>
          <span className="qs-footer__name">Quantum STEM & Computational Robotics Academy</span>
          <p className="qs-footer__wasc">WASC Accredited Non-Profit Higher Education Entity #928401</p>
        </div>
        <address className="qs-footer__addr">
          500 Technology Square, Cambridge, MA 02139 | admissions@quantum-stem.edu
        </address>
        <span className="qs-footer__copy">© {new Date().getFullYear()} Quantum STEM Academy. All rights reserved.</span>
      </div>
    </footer>
  );
}
""",
            "css": """.qs-footer {
  background-color: #020617;
  color: #64748b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  padding: 3rem 1.5rem;
  border-top: 1px solid #1e293b;
}

.qs-footer__container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.qs-footer__name {
  color: #ffffff;
  font-weight: 700;
  font-size: 0.9375rem;
}

.qs-footer__wasc {
  margin: 0.25rem 0 0 0;
  color: #818cf8;
}

.qs-footer__addr {
  font-style: normal;
}

.qs-footer__copy {
  border-top: 1px solid #0f172a;
  padding-top: 1rem;
  font-size: 0.75rem;
}
"""
        }
    ]
    trajs.append(make_traj("site_education_quantum_stem", t7_brief, t7_sections))

    return trajs

def main():
    from regenerate_step5_eval import main as step5_main
    step5_main()

if __name__ == "__main__":
    main()
