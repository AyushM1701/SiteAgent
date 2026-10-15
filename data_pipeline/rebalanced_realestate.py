"""
data_pipeline/rebalanced_realestate.py

Hand-authored full-site trajectories for Real Estate across Tabs, Bento, and Editorial archetypes
with rich structural trust-tier features (CalDRE broker numbers, NMLS, Equal Housing Opportunity, verified square footage).
"""

from build_rebalanced_dataset import make_traj

def get_realestate_trajectories():
    trajs = []

    # ==============================================================================
    # 1. Real Estate x Tabs: Meridian Penthouse Collection
    # ==============================================================================
    t1_brief = """<content_brief>
  <business_name>Meridian Penthouse Collection</business_name>
  <tagline>Exclusive Coastal Penthouses & Private Architectural Residences</tagline>
  <business_type>real_estate</business_type>
  <layout_archetype>tabs</layout_archetype>
  <layout_guidelines>Tabbed property architecture: interactive category tabs switching between Coastal Penthouses, Waterfront Estates, and Architectural Lofts with CalDRE #01928472 and Equal Housing Opportunity disclosures.</layout_guidelines>
  <sections>header, hero, property_tabs, licensing_disclosures, footer</sections>
  <contact>
    <address>100 Ocean Avenue, Suite 1200, Santa Monica, CA 90401</address>
    <phone>+1 (310) 555-0182</phone>
    <email>concierge@meridianpenthouses.com</email>
    <hours>Mon–Sun: 9am–7pm PST</hours>
  </contact>
</content_brief>"""

    t1_sections = [
        {
            "name": "Header",
            "instruction": "luxury real estate header with CalDRE broker badge and private viewing booking CTA. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header for Meridian with luxury coastal theme.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="meridian-header" role="banner">
      <div className="meridian-header__inner">
        <a href="#hero" className="meridian-header__logo" aria-label="Meridian Penthouse Collection Home">
          MERIDIAN <span className="meridian-header__sub">PENTHOUSES</span>
        </a>
        <div className="meridian-header__badge">
          <span>CalDRE Broker Lic #01928472</span>
        </div>
        <a href="#disclosures" className="meridian-header__cta">Private Showing</a>
      </div>
    </header>
  );
}""",
            "css": """.meridian-header {
  background: #0a0a0c;
  border-bottom: 1px solid rgba(212, 175, 55, 0.25);
  padding: 1.15rem 2rem;
  position: sticky;
  top: 0;
  z-index: 100;
}
.meridian-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.meridian-header__logo { font-family: 'Playfair Display', serif; font-size: 1.25rem; font-weight: 700; color: #f8fafc; text-decoration: none; letter-spacing: 0.05em; }
.meridian-header__sub { font-size: 0.75rem; color: #d4af37; font-family: sans-serif; letter-spacing: 0.1em; }
.meridian-header__badge { font-size: 0.75rem; color: #94a3b8; font-family: monospace; background: rgba(255, 255, 255, 0.04); padding: 0.35rem 0.75rem; border-radius: 4px; }
.meridian-header__cta { background: #d4af37; color: #0a0a0c; font-weight: 700; font-size: 0.8125rem; padding: 0.5rem 1.25rem; border-radius: 4px; text-decoration: none; }
@media (max-width: 768px) { .meridian-header__badge { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "luxury real estate hero banner with clifftop panorama copy, architectural pedigree, and transaction metrics. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero for Meridian Penthouses with high-contrast luxury serif styling.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="meridian-hero" id="hero" aria-label="Curated Coastal Residences">
      <div className="meridian-hero__inner">
        <span className="meridian-hero__tag">Santa Monica · Malibu · Pacific Palisades</span>
        <h1 className="meridian-hero__title">
          Exclusive Coastal Penthouses & Private Architectural Residences
        </h1>
        <p className="meridian-hero__desc">
          Unlisted oceanfront penthouses with 360-degree Pacific panoramas, private elevator vestibules, and cantilevered infinity terraces.
        </p>
        <div className="meridian-hero__metrics">
          <div>
            <span className="meridian-hero__num">$1.8B+</span>
            <span className="meridian-hero__lbl">Curated Closed Volume</span>
          </div>
          <div>
            <span className="meridian-hero__num">100%</span>
            <span className="meridian-hero__lbl">Verified Direct Title</span>
          </div>
          <div>
            <span className="meridian-hero__num">Top 0.1%</span>
            <span className="meridian-hero__lbl">California Luxury Brokerage</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.meridian-hero {
  padding: 6rem 1.5rem 4.5rem;
  background: radial-gradient(circle at 50% 15%, rgba(212, 175, 55, 0.07) 0%, #0a0a0c 80%);
  color: #f8fafc;
  text-align: center;
}
.meridian-hero__inner { max-width: 960px; margin: 0 auto; }
.meridian-hero__tag { font-size: 0.8125rem; color: #d4af37; text-transform: uppercase; letter-spacing: 0.15em; font-weight: 600; display: block; margin-bottom: 1.25rem; }
.meridian-hero__title { font-family: 'Playfair Display', serif; font-size: clamp(2.3rem, 4.8vw, 3.8rem); font-weight: 700; line-height: 1.15; margin: 0 0 1.5rem; }
.meridian-hero__desc { font-size: 1.15rem; color: #cbd5e1; line-height: 1.7; max-width: 760px; margin: 0 auto 3.5rem; }
.meridian-hero__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(212, 175, 55, 0.2);
}
.meridian-hero__num { font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 700; color: #d4af37; display: block; }
.meridian-hero__lbl { font-size: 0.8125rem; color: #94a3b8; }
@media (max-width: 650px) { .meridian-hero__metrics { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "PropertyTabs",
            "instruction": "interactive property tabs using React useState switching between Coastal Penthouses, Waterfront Villas, and Architectural Lofts with price and specs. Files: src/components/PropertyTabs.tsx + src/components/PropertyTabs.css",
            "tsx_path": "src/components/PropertyTabs.tsx",
            "css_path": "src/components/PropertyTabs.css",
            "thought": "Building stateful property filtering tabs for luxury residences.",
            "tsx": """import React, { useState } from 'react';
import './PropertyTabs.css';

interface Property {
  id: string;
  category: string;
  name: string;
  price: string;
  specs: string;
  sqft: string;
  description: string;
}

const PROPERTIES: Property[] = [
  {
    id: 'ocean-penthouse',
    category: 'penthouses',
    name: 'The Palisades Sky Villa',
    price: '$28,500,000',
    specs: '5 Beds · 7 Baths · 4-Car Gallery',
    sqft: '8,400 sq.ft. interior + 3,200 sq.ft. terrace',
    description: 'Crown penthouse occupying the entire 24th floor. Glass-bottomed heated cantilever pool, private elevator access, and unobstructed horizon ocean views.'
  },
  {
    id: 'malibu-estate',
    category: 'waterfront',
    name: 'Carbon Beach Modernist Haven',
    price: '$34,000,000',
    specs: '6 Beds · 8 Baths · Private Beach Access',
    sqft: '9,800 sq.ft. interior on 75ft beachfront',
    description: 'Direct dry-sand access. Board-formed architectural concrete, teak decking, radiant hydronic heating, and automated disappearing Fleetwood sliders.'
  },
  {
    id: 'lofts',
    category: 'architectural',
    name: 'Santa Monica Canyon Pavilion',
    price: '$19,800,000',
    specs: '4 Beds · 5 Baths · Historic Sycamore Grove',
    sqft: '6,600 sq.ft. interior on 0.85 acre lot',
    description: 'Steel-and-glass pavilion designed by Ray Kappe FAIA. Custom walnut cabinetry, internal courtyards, and integrated solar microgrid.'
  }
];

export function PropertyTabs() {
  const [activeCategory, setActiveCategory] = useState('penthouses');
  const current = PROPERTIES.find(p => p.category === activeCategory) || PROPERTIES[0];

  return (
    <section className="meridian-tabs" id="properties" aria-labelledby="meridian-tabs-title">
      <div className="meridian-tabs__inner">
        <header className="meridian-tabs__header">
          <p className="meridian-tabs__eyebrow">Curated Collection</p>
          <h2 id="meridian-tabs-title" className="meridian-tabs__title">Private Property Portfolios</h2>
        </header>

        <div className="meridian-tabs__bar" role="tablist" aria-label="Property Categories">
          <button
            type="button"
            role="tab"
            aria-selected={activeCategory === 'penthouses'}
            className={`meridian-tabs__btn ${activeCategory === 'penthouses' ? 'meridian-tabs__btn--active' : ''}`}
            onClick={() => setActiveCategory('penthouses')}
          >
            Coastal Penthouses
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeCategory === 'waterfront'}
            className={`meridian-tabs__btn ${activeCategory === 'waterfront' ? 'meridian-tabs__btn--active' : ''}`}
            onClick={() => setActiveCategory('waterfront')}
          >
            Waterfront Estates
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeCategory === 'architectural'}
            className={`meridian-tabs__btn ${activeCategory === 'architectural' ? 'meridian-tabs__btn--active' : ''}`}
            onClick={() => setActiveCategory('architectural')}
          >
            Architectural Masterpieces
          </button>
        </div>

        <div className="meridian-tabs__card" role="tabpanel">
          <div className="meridian-tabs__card-top">
            <div>
              <h3 className="meridian-tabs__card-title">{current.name}</h3>
              <p className="meridian-tabs__card-specs">{current.specs}</p>
            </div>
            <span className="meridian-tabs__card-price">{current.price}</span>
          </div>
          <p className="meridian-tabs__card-desc">{current.description}</p>
          <div className="meridian-tabs__card-meta">
            <span>Laser-Measured Verified Area: {current.sqft}</span>
            <a href="#disclosures" className="meridian-tabs__card-link">Request Private Dossier →</a>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.meridian-tabs {
  padding: 6rem 1.5rem;
  background: #08080a;
}
.meridian-tabs__inner { max-width: 1080px; margin: 0 auto; }
.meridian-tabs__header { text-align: center; margin-bottom: 3rem; }
.meridian-tabs__eyebrow { font-size: 0.8125rem; color: #d4af37; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 0.5rem; }
.meridian-tabs__title { font-family: 'Playfair Display', serif; font-size: 2.4rem; color: #f8fafc; margin: 0; }
.meridian-tabs__bar {
  display: flex;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(212, 175, 55, 0.2);
  border-radius: 6px;
  padding: 0.35rem;
  gap: 0.5rem;
  margin-bottom: 2.5rem;
}
.meridian-tabs__btn {
  flex: 1;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-family: 'Playfair Display', serif;
  font-size: 1.05rem;
  padding: 0.85rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.meridian-tabs__btn--active {
  background: rgba(212, 175, 55, 0.15);
  color: #d4af37;
  border: 1px solid rgba(212, 175, 55, 0.3);
}
.meridian-tabs__card {
  background: rgba(20, 20, 25, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-left: 3px solid #d4af37;
  border-radius: 8px;
  padding: 2.5rem;
}
.meridian-tabs__card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem; }
.meridian-tabs__card-title { font-family: 'Playfair Display', serif; font-size: 1.8rem; color: #f8fafc; margin: 0 0 0.5rem; }
.meridian-tabs__card-specs { font-size: 0.9375rem; color: #94a3b8; margin: 0; }
.meridian-tabs__card-price { font-family: 'Playfair Display', serif; font-size: 1.85rem; font-weight: 700; color: #d4af37; }
.meridian-tabs__card-desc { font-size: 1.05rem; color: #cbd5e1; line-height: 1.7; margin-bottom: 2rem; }
.meridian-tabs__card-meta { display: flex; justify-content: space-between; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 1.5rem; font-size: 0.875rem; color: #64748b; flex-wrap: wrap; gap: 1rem; }
.meridian-tabs__card-link { color: #d4af37; text-decoration: none; font-weight: 600; }
@media (max-width: 700px) { .meridian-tabs__bar { flex-direction: column; } }"""
        },
        {
            "name": "LicensingDisclosures",
            "instruction": "structured real estate trust section with Equal Housing Opportunity logo, CalDRE Broker Lic #01928472, NMLS #381920, and MLS IDX compliance statements. Files: src/components/LicensingDisclosures.tsx + src/components/LicensingDisclosures.css",
            "tsx_path": "src/components/LicensingDisclosures.tsx",
            "css_path": "src/components/LicensingDisclosures.css",
            "thought": "Building structured real estate licensing and Equal Housing Opportunity compliance block.",
            "tsx": """import React from 'react';
import './LicensingDisclosures.css';

export function LicensingDisclosures() {
  return (
    <section className="meridian-licensing" id="disclosures" aria-label="Real Estate Licensing & Fair Housing Disclosures">
      <div className="meridian-licensing__inner">
        <div className="meridian-licensing__eho-banner">
          <span className="meridian-licensing__eho-icon" aria-hidden="true">⌂</span>
          <div>
            <h4 className="meridian-licensing__eho-title">Equal Housing Opportunity</h4>
            <p className="meridian-licensing__eho-text">
              We are pledged to the letter and spirit of U.S. policy for the achievement of equal housing opportunity throughout the Nation. We encourage and support an affirmative advertising and marketing program in which there are no barriers to obtaining housing because of race, color, religion, sex, handicap, familial status, or national origin.
            </p>
          </div>
        </div>

        <div className="meridian-licensing__grid">
          <div className="meridian-licensing__card">
            <span className="meridian-licensing__label">California Brokerage License</span>
            <span className="meridian-licensing__val">CalDRE Lic #01928472</span>
            <p className="meridian-licensing__sub">Licensed Real Estate Broker Corporation in the State of California.</p>
          </div>
          <div className="meridian-licensing__card">
            <span className="meridian-licensing__label">Mortgage Regulatory System</span>
            <span className="meridian-licensing__val">NMLS ID #381920</span>
            <p className="meridian-licensing__sub">Registered originator under Nationwide Multistate Licensing System.</p>
          </div>
          <div className="meridian-licensing__card">
            <span className="meridian-licensing__label">MLS & Title Conformance</span>
            <span className="meridian-licensing__val">The MLS / CLAW Compliant</span>
            <p className="meridian-licensing__sub">All square footage verified by laser survey; buyer to verify all permits.</p>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.meridian-licensing {
  padding: 4rem 1.5rem;
  background: #050507;
  border-top: 1px solid rgba(212, 175, 55, 0.2);
}
.meridian-licensing__inner { max-width: 1080px; margin: 0 auto; }
.meridian-licensing__eho-banner {
  background: rgba(212, 175, 55, 0.04);
  border: 1px solid rgba(212, 175, 55, 0.2);
  border-radius: 8px;
  padding: 2rem;
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
  margin-bottom: 2.5rem;
}
.meridian-licensing__eho-icon { font-size: 2.5rem; color: #d4af37; line-height: 1; }
.meridian-licensing__eho-title { font-family: 'Playfair Display', serif; font-size: 1.25rem; color: #f8fafc; margin: 0 0 0.5rem; }
.meridian-licensing__eho-text { font-size: 0.8125rem; color: #94a3b8; line-height: 1.65; margin: 0; }
.meridian-licensing__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
.meridian-licensing__card { background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); padding: 1.5rem; border-radius: 6px; }
.meridian-licensing__label { font-size: 0.75rem; text-transform: uppercase; color: #d4af37; font-weight: 600; display: block; margin-bottom: 0.25rem; }
.meridian-licensing__val { font-size: 1.1rem; font-weight: 700; color: #f8fafc; font-family: monospace; display: block; margin-bottom: 0.5rem; }
.meridian-licensing__sub { font-size: 0.75rem; color: #64748b; line-height: 1.5; margin: 0; }
@media (max-width: 800px) {
  .meridian-licensing__eho-banner { flex-direction: column; }
  .meridian-licensing__grid { grid-template-columns: 1fr; }
}"""
        },
        {
            "name": "Footer",
            "instruction": "luxury real estate footer with Santa Monica Ocean Ave address and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified California brokerage address.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="meridian-footer" id="footer" role="contentinfo">
      <div className="meridian-footer__inner">
        <div>
          <span className="meridian-footer__logo">MERIDIAN PENTHOUSE COLLECTION</span>
          <p className="meridian-footer__tag">Prime Coastal Real Estate Brokerage</p>
        </div>
        <address className="meridian-footer__addr">
          <p>100 Ocean Avenue, Suite 1200</p>
          <p>Santa Monica, CA 90401</p>
          <p><a href="tel:+13105550182">+1 (310) 555-0182</a> · <a href="mailto:concierge@meridianpenthouses.com">concierge@meridianpenthouses.com</a></p>
        </address>
      </div>
      <div className="meridian-footer__bottom">
        <p>© {new Date().getFullYear()} Meridian Penthouse Collection Inc. All rights reserved. CalDRE #01928472.</p>
      </div>
    </footer>
  );
}""",
            "css": """.meridian-footer {
  background: #030305;
  padding: 4rem 1.5rem 2rem;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.meridian-footer__inner { max-width: 1080px; margin: 0 auto; display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2.5rem; flex-wrap: wrap; gap: 2rem; }
.meridian-footer__logo { font-family: 'Playfair Display', serif; font-size: 1.15rem; color: #f8fafc; font-weight: 700; display: block; margin-bottom: 0.25rem; }
.meridian-footer__tag { font-size: 0.8125rem; }
.meridian-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.meridian-footer__addr a { color: #d4af37; text-decoration: none; }
.meridian-footer__bottom { max-width: 1080px; margin: 0 auto; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; text-align: center; font-size: 0.75rem; }"""
        }
    ]
    trajs.append(make_traj("site_realestate_tabs_meridian", t1_brief, t1_sections))

    # ==============================================================================
    # 2. Real Estate x Bento: Halcyon Architectural Living
    # ==============================================================================
    t2_brief = """<content_brief>
  <business_name>Halcyon Architectural Living</business_name>
  <tagline>Mid-Century Modernist Masterpieces & Restored Heritage Estates</tagline>
  <business_type>real_estate</business_type>
  <layout_archetype>bento</layout_archetype>
  <layout_guidelines>Bento grid architecture: asymmetric spans (2x2 featured mid-century pavilion card, laser-verified square footage, architectural commission recognition, and CalDRE #02194832).</layout_guidelines>
  <sections>header, hero, architectural_bento, brokerage_compliance, footer</sections>
  <contact>
    <address>8400 Melrose Avenue, West Hollywood, CA 90069</address>
    <phone>+1 (323) 555-0193</phone>
    <email>estates@halcyonliving.com</email>
    <hours>Mon–Sat: 9am–6pm PST</hours>
  </contact>
</content_brief>"""

    t2_sections = [
        {
            "name": "Header",
            "instruction": "mid-century architectural header with modernist logo and private viewing CTA. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header for Halcyon with mid-century modernist typography.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="halcyon-header" role="banner">
      <div className="halcyon-header__inner">
        <a href="#hero" className="halcyon-header__logo" aria-label="Halcyon Living Home">
          HALCYON ARCHITECTURAL
        </a>
        <span className="halcyon-header__tag">CalDRE Broker #02194832</span>
        <a href="#compliance" className="halcyon-header__cta">Book Gallery Tour</a>
      </div>
    </header>
  );
}""",
            "css": """.halcyon-header {
  background: #181513;
  border-bottom: 1px solid rgba(224, 122, 95, 0.3);
  padding: 1rem 1.5rem;
}
.halcyon-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.halcyon-header__logo { font-family: 'Syne', sans-serif; font-size: 1.25rem; font-weight: 800; color: #f8fafc; text-decoration: none; letter-spacing: 0.05em; }
.halcyon-header__tag { font-size: 0.75rem; color: #e07a5f; font-family: monospace; background: rgba(224, 122, 95, 0.1); padding: 0.3rem 0.75rem; border-radius: 4px; }
.halcyon-header__cta { background: #e07a5f; color: #181513; font-weight: 700; font-size: 0.8125rem; padding: 0.45rem 1.1rem; border-radius: 4px; text-decoration: none; }
@media (max-width: 768px) { .halcyon-header__tag { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "modernist architectural hero with historic pedigree badge and laser-measured verified volume metrics. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero for Halcyon with architectural pedigree.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="halcyon-hero" id="hero" aria-label="Modernist Architecture Collection">
      <div className="halcyon-hero__inner">
        <div className="halcyon-hero__badge">
          <span>Historic Preservation Commission Recognized Brokerage</span>
        </div>
        <h1 className="halcyon-hero__title">
          Mid-Century Modernist Masterpieces & Restored Heritage Estates
        </h1>
        <p className="halcyon-hero__desc">
          Representing iconic post-and-beam residential sanctuaries crafted by Neutra, Lautner, Koenig, and Ellwood across Southern California.
        </p>
        <div className="halcyon-hero__stats">
          <div>
            <span className="halcyon-hero__num">42</span>
            <span className="halcyon-hero__lbl">Heritage Sites Restored</span>
          </div>
          <div>
            <span className="halcyon-hero__num">100%</span>
            <span className="halcyon-hero__lbl">Architectural Provenance Verified</span>
          </div>
          <div>
            <span className="halcyon-hero__num">$620M</span>
            <span className="halcyon-hero__lbl">Historic Volume Sold</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.halcyon-hero {
  padding: 5.5rem 1.5rem 4rem;
  background: #181513;
  color: #f8fafc;
  text-align: center;
}
.halcyon-hero__inner { max-width: 960px; margin: 0 auto; }
.halcyon-hero__badge {
  display: inline-block;
  background: rgba(224, 122, 95, 0.1);
  border: 1px solid rgba(224, 122, 95, 0.3);
  color: #e07a5f;
  font-size: 0.75rem;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  margin-bottom: 1.5rem;
}
.halcyon-hero__title { font-family: 'Syne', sans-serif; font-size: clamp(2.3rem, 4.8vw, 3.8rem); font-weight: 800; line-height: 1.15; margin: 0 0 1.25rem; }
.halcyon-hero__desc { font-size: 1.15rem; color: #a8a29e; line-height: 1.65; max-width: 720px; margin: 0 auto 3rem; }
.halcyon-hero__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.halcyon-hero__num { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800; color: #e07a5f; display: block; }
.halcyon-hero__lbl { font-size: 0.8125rem; color: #78716c; }
@media (max-width: 600px) { .halcyon-hero__stats { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "ArchitecturalBento",
            "instruction": "heterogeneous Bento Grid layout with 2x2 featured Case Study House residence, laser-verified square footage, and structural specs. Files: src/components/ArchitecturalBento.tsx + src/components/ArchitecturalBento.css",
            "tsx_path": "src/components/ArchitecturalBento.tsx",
            "css_path": "src/components/ArchitecturalBento.css",
            "thought": "Building Bento Grid with 2x2 featured Case Study House.",
            "tsx": """import React from 'react';
import './ArchitecturalBento.css';

export function ArchitecturalBento() {
  return (
    <section className="halcyon-bento" id="bento" aria-labelledby="halcyon-bento-title">
      <div className="halcyon-bento__inner">
        <header className="halcyon-bento__header">
          <p className="halcyon-bento__eyebrow">Curated Provenance</p>
          <h2 id="halcyon-bento-title" className="halcyon-bento__title">Architectural Portfolio Bento</h2>
        </header>

        <div className="halcyon-bento__grid">
          <article className="halcyon-card halcyon-card--featured">
            <span className="halcyon-card__tag">Case Study Program · 1958</span>
            <h3 className="halcyon-card__title">The Hollywood Hills Steel Cantilever</h3>
            <p className="halcyon-card__desc">
              Historic registered post-and-beam pavilion featuring 12-foot floor-to-ceiling glass walls, terrazzo floors, and an unencumbered city-to-ocean vista. Completely restored to original blueprints.
            </p>
            <div className="halcyon-card__meta">
              <span>Laser-Surveyed: 5,420 sq.ft.</span>
              <span>Lot: 0.62 Acres</span>
              <span>Status: Off-Market Exclusive</span>
            </div>
          </article>

          <article className="halcyon-card">
            <span className="halcyon-card__tag">Desert Modernism</span>
            <h3 className="halcyon-card__title">Palm Springs Boulder Pavilion</h3>
            <p className="halcyon-card__desc">
              Integrated natural rock outcroppings, deep shadow overhangs, and historic copper fascia.
            </p>
          </article>

          <article className="halcyon-card">
            <span className="halcyon-card__tag">Organic Architecture</span>
            <h3 className="halcyon-card__title">Brentwood Redwood Residence</h3>
            <p className="halcyon-card__desc">
              Old-growth redwood board-and-batten construction with central stone fireplace hearth.
            </p>
          </article>

          <article className="halcyon-card halcyon-card--wide">
            <span className="halcyon-card__tag">Architectural Survey Standards</span>
            <h3 className="halcyon-card__title">Laser-Point Cloud 3D As-Built Verification</h3>
            <p className="halcyon-card__desc">
              Every residence in our portfolio undergoes LiDAR scan verification to guarantee exact square footage, structural integrity, and historic preservation tax credits.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.halcyon-bento {
  padding: 6rem 1.5rem;
  background: #120f0d;
}
.halcyon-bento__inner { max-width: 1200px; margin: 0 auto; }
.halcyon-bento__header { text-align: center; margin-bottom: 3.5rem; }
.halcyon-bento__eyebrow { font-size: 0.8125rem; color: #e07a5f; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 0.5rem; }
.halcyon-bento__title { font-family: 'Syne', sans-serif; font-size: 2.4rem; color: #f8fafc; margin: 0; }
.halcyon-bento__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}
.halcyon-card {
  background: rgba(30, 25, 22, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
}
.halcyon-card--featured {
  grid-column: span 2;
  grid-row: span 2;
  background: linear-gradient(135deg, rgba(224, 122, 95, 0.1) 0%, rgba(30, 25, 22, 0.9) 100%);
  border-color: rgba(224, 122, 95, 0.35);
}
.halcyon-card--wide { grid-column: span 3; }
.halcyon-card__tag { font-size: 0.75rem; color: #e07a5f; text-transform: uppercase; font-weight: 700; margin-bottom: 0.75rem; }
.halcyon-card__title { font-family: 'Syne', sans-serif; font-size: 1.35rem; color: #f8fafc; margin: 0 0 0.75rem; }
.halcyon-card__desc { font-size: 0.9375rem; color: #a8a29e; line-height: 1.65; margin-bottom: 1.5rem; flex-grow: 1; }
.halcyon-card__meta { display: flex; gap: 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 1rem; font-size: 0.8125rem; color: #e07a5f; flex-wrap: wrap; }
@media (max-width: 900px) {
  .halcyon-bento__grid { grid-template-columns: 1fr; }
  .halcyon-card--featured, .halcyon-card--wide { grid-column: span 1; grid-row: span 1; }
}"""
        },
        {
            "name": "BrokerageCompliance",
            "instruction": "trust section detailing CalDRE #02194832, National Association of Realtors membership, and Equal Housing Opportunity lockup. Files: src/components/BrokerageCompliance.tsx + src/components/BrokerageCompliance.css",
            "tsx_path": "src/components/BrokerageCompliance.tsx",
            "css_path": "src/components/BrokerageCompliance.css",
            "thought": "Building structured real estate licensing and NAR compliance block.",
            "tsx": """import React from 'react';
import './BrokerageCompliance.css';

export function BrokerageCompliance() {
  return (
    <section className="halcyon-trust" id="compliance" aria-label="Brokerage Licensing & Industry Affiliations">
      <div className="halcyon-trust__inner">
        <div className="halcyon-trust__badges">
          <div className="halcyon-trust__item">
            <span className="halcyon-trust__h">California Brokerage License</span>
            <span className="halcyon-trust__val">CalDRE Lic #02194832</span>
            <p className="halcyon-trust__sub">Corporate Broker of Record: Halcyon Living Realty Inc.</p>
          </div>
          <div className="halcyon-trust__item">
            <span className="halcyon-trust__h">Industry Associations</span>
            <span className="halcyon-trust__val">NAR · CAR · Beverly Hills Board</span>
            <p className="halcyon-trust__sub">Active member with binding professional ethics adherence.</p>
          </div>
          <div className="halcyon-trust__item">
            <span className="halcyon-trust__h">Fair Housing Mandate</span>
            <span className="halcyon-trust__val">⌂ Equal Housing Opportunity</span>
            <p className="halcyon-trust__sub">We strictly support non-discriminatory housing access nationwide.</p>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.halcyon-trust {
  padding: 4rem 1.5rem;
  background: #181513;
  border-top: 1px solid rgba(224, 122, 95, 0.2);
}
.halcyon-trust__inner { max-width: 1200px; margin: 0 auto; }
.halcyon-trust__badges { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
.halcyon-trust__item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(224, 122, 95, 0.2);
  border-left: 3px solid #e07a5f;
  padding: 1.5rem;
  border-radius: 6px;
}
.halcyon-trust__h { font-size: 0.75rem; text-transform: uppercase; color: #e07a5f; font-weight: 700; display: block; margin-bottom: 0.25rem; }
.halcyon-trust__val { font-size: 1.1rem; font-weight: 700; color: #f8fafc; display: block; margin-bottom: 0.5rem; font-family: monospace; }
.halcyon-trust__sub { font-size: 0.75rem; color: #a8a29e; line-height: 1.5; margin: 0; }
@media (max-width: 768px) { .halcyon-trust__badges { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "Footer",
            "instruction": "architectural brokerage footer with Melrose Ave address and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified West Hollywood address.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="halcyon-footer" id="footer" role="contentinfo">
      <div className="halcyon-footer__inner">
        <div>
          <span className="halcyon-footer__logo">HALCYON ARCHITECTURAL LIVING</span>
          <p className="halcyon-footer__tagline">Historic & Mid-Century Modern Residential Provenance.</p>
        </div>
        <address className="halcyon-footer__addr">
          <p>8400 Melrose Avenue</p>
          <p>West Hollywood, CA 90069</p>
          <p><a href="tel:+13235550193">+1 (323) 555-0193</a> · <a href="mailto:estates@halcyonliving.com">estates@halcyonliving.com</a></p>
        </address>
      </div>
      <div className="halcyon-footer__bottom">
        <p>© {new Date().getFullYear()} Halcyon Living Realty Inc. All rights reserved. CalDRE #02194832.</p>
      </div>
    </footer>
  );
}""",
            "css": """.halcyon-footer {
  background: #0e0c0b;
  padding: 4rem 1.5rem 2rem;
  color: #78716c;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.halcyon-footer__inner { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2.5rem; flex-wrap: wrap; gap: 2rem; }
.halcyon-footer__logo { font-family: 'Syne', sans-serif; font-size: 1.15rem; color: #f8fafc; font-weight: 800; display: block; margin-bottom: 0.25rem; }
.halcyon-footer__tagline { font-size: 0.8125rem; }
.halcyon-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.halcyon-footer__addr a { color: #e07a5f; text-decoration: none; }
.halcyon-footer__bottom { max-width: 1200px; margin: 0 auto; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; font-size: 0.75rem; }"""
        }
    ]
    trajs.append(make_traj("site_realestate_bento_halcyon", t2_brief, t2_sections))

    # ==============================================================================
    # 3. Real Estate x Editorial: Amalfi Coast Historic Villas
    # ==============================================================================
    t3_brief = """<content_brief>
  <business_name>Amalfi Coast Historic Villas</business_name>
  <tagline>Century-Old Clifftop Palladian Villas on the Tyrrhenian Sea</tagline>
  <business_type>real_estate</business_type>
  <layout_archetype>editorial</layout_archetype>
  <layout_guidelines>Editorial architecture: high-contrast serif headlines, masthead volume and dispatch header, asymmetric pull-quote, multi-column narrative prose with dropcap, followed by Italian Heritage cadastral disclosures and REA #SA-491820.</layout_guidelines>
  <sections>header, hero, historic_monographs, cadastral_disclosures, footer</sections>
  <contact>
    <address>Via Panoramica 14, 84010 Ravello (SA), Italy</address>
    <phone>+39 089 555 0122</phone>
    <email>segreteria@amalasticvillas.it</email>
    <hours>Mon–Sat: 9:30–18:30 CET</hours>
  </contact>
</content_brief>"""

    t3_sections = [
        {
            "name": "Header",
            "instruction": "Italian heritage villa header with Italian Real Estate license indicator. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header for Amalfi Coast Historic Villas with Italian Mediterranean styling.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="amalfi-header" role="banner">
      <div className="amalfi-header__inner">
        <a href="#hero" className="amalfi-header__logo" aria-label="Amalfi Historic Villas Home">
          AMALFI HISTORIC VILLAS
        </a>
        <span className="amalfi-header__rea">Mediatore Immobiliare · REA #SA-491820</span>
        <a href="#cadastral" className="amalfi-header__cta">Private Dossier</a>
      </div>
    </header>
  );
}""",
            "css": """.amalfi-header {
  background: #12100e;
  border-bottom: 1px solid rgba(217, 119, 6, 0.25);
  padding: 1.15rem 2rem;
}
.amalfi-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.amalfi-header__logo { font-family: 'Cinzel', serif; font-size: 1.2rem; font-weight: 700; color: #f8fafc; text-decoration: none; letter-spacing: 0.06em; }
.amalfi-header__rea { font-size: 0.75rem; color: #d97706; font-family: monospace; }
.amalfi-header__cta { background: #d97706; color: #000000; font-weight: 700; font-size: 0.8125rem; padding: 0.45rem 1.1rem; border-radius: 4px; text-decoration: none; }
@media (max-width: 768px) { .amalfi-header__rea { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "editorial Italian villa hero banner with masthead date rule, serif typography, and clifftop altitude metrics. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero for Amalfi Historic Villas with Italian luxury editorial styling.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="amalfi-hero" id="hero" aria-label="Historic Italian Estates">
      <div className="amalfi-hero__inner">
        <div className="amalfi-hero__masthead">
          <span>RAVELLO · POSITANO · CAPRI</span>
          <span>SOPRINTENDENZA BENI CULTURALI REGISTRATION</span>
        </div>
        <hr className="amalfi-hero__rule" />
        <h1 className="amalfi-hero__title">
          Century-Old Clifftop Palladian Villas on the Tyrrhenian Sea
        </h1>
        <p className="amalfi-hero__desc">
          Perched 250 meters above the cobalt waters of the Amalfi Coast. Terraced lemon groves, private funicular sea access, and frescoed Renaissance salons.
        </p>
        <div className="amalfi-hero__metrics">
          <div>
            <span className="amalfi-hero__num">16</span>
            <span className="amalfi-hero__lbl">Historic Monument Estates</span>
          </div>
          <div>
            <span className="amalfi-hero__num">100%</span>
            <span className="amalfi-hero__lbl">Cadastral Title Verified</span>
          </div>
          <div>
            <span className="amalfi-hero__num">1880</span>
            <span className="amalfi-hero__lbl">Oldest Preserved Funicular</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.amalfi-hero {
  padding: 5.5rem 1.5rem 4rem;
  background: #12100e;
  color: #f8fafc;
  text-align: center;
}
.amalfi-hero__inner { max-width: 960px; margin: 0 auto; }
.amalfi-hero__masthead {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  font-family: monospace;
  color: #d97706;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
}
.amalfi-hero__rule { border: none; border-top: 1px solid rgba(217, 119, 6, 0.35); margin: 0 0 2.5rem; }
.amalfi-hero__title { font-family: 'Cinzel', serif; font-size: clamp(2.3rem, 4.8vw, 3.8rem); font-weight: 700; line-height: 1.15; margin: 0 0 1.5rem; }
.amalfi-hero__desc { font-size: 1.15rem; color: #d6d3d1; line-height: 1.7; max-width: 720px; margin: 0 auto 3.5rem; }
.amalfi-hero__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.amalfi-hero__num { font-family: 'Cinzel', serif; font-size: 2.2rem; font-weight: 700; color: #d97706; display: block; }
.amalfi-hero__lbl { font-size: 0.8125rem; color: #a8a29e; }
@media (max-width: 600px) { .amalfi-hero__metrics { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "HistoricMonographs",
            "instruction": "editorial two-column narrative prose with dropcap and monograph cards for Villa Bellissima and Palazzo Cimbrone. Files: src/components/HistoricMonographs.tsx + src/components/HistoricMonographs.css",
            "tsx_path": "src/components/HistoricMonographs.tsx",
            "css_path": "src/components/HistoricMonographs.css",
            "thought": "Building multi-column editorial prose with dropcap and historical estate monographs.",
            "tsx": """import React from 'react';
import './HistoricMonographs.css';

export function HistoricMonographs() {
  return (
    <section className="amalfi-editorial" id="monographs" aria-labelledby="amalfi-editorial-title">
      <div className="amalfi-editorial__inner">
        <div className="amalfi-editorial__lead">
          <h2 id="amalfi-editorial-title" className="amalfi-editorial__h2">Architectural Folio</h2>
          <blockquote className="amalfi-editorial__quote">
            <p>"To build upon the Amalfi cliffs is to carve a dialogue between volcanic limestone and Mediterranean horizon."</p>
            <cite>— Quaderni dei Beni Culturali di Salerno</cite>
          </blockquote>
        </div>

        <div className="amalfi-editorial__prose">
          <p className="amalfi-editorial__p amalfi-editorial__p--dropcap">
            The cliffside estates of Ravello and Positano represent an irreplaceable synthesis of Saracen masonry and 18th-century grand tour romanticism. Anchored into sheer sea cliffs by hand-cut limestone buttresses, these villas boast subterranean cisterns, pergolas draped in sfusato amalfitano lemon trees, and private moorings accessible only by funicular.
          </p>
          <p className="amalfi-editorial__p">
            Acquiring a listed landmark on the Amalfi coast requires meticulous legal adherence to Italian monumental heritage restrictions (Vincolo Monumentale). Our firm guides sovereign collectors and private family offices through direct cadastral title conveyancing under notarial supervision.
          </p>
        </div>

        <div className="amalfi-editorial__estates">
          <article className="amalfi-estate">
            <span className="amalfi-estate__ref">CADASTRAL REF #FG-14-M402</span>
            <h3 className="amalfi-estate__title">Villa Bellissima di Ravello</h3>
            <p className="amalfi-estate__desc">
              14-room historic palazzo with 1.2-hectare terraced gardens, private chapel, and heated cliffside pool overlooking the Gulf of Salerno.
            </p>
          </article>
          <article className="amalfi-estate">
            <span className="amalfi-estate__ref">CADASTRAL REF #FG-08-M119</span>
            <h3 className="amalfi-estate__title">Torre della Sirena di Positano</h3>
            <p className="amalfi-estate__desc">
              16th-century Norman watchtower transformed into a 4-suite private fortress with private sea cove and helicopter landing deck.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.amalfi-editorial {
  padding: 6rem 1.5rem;
  background: #0d0b09;
  color: #f8fafc;
}
.amalfi-editorial__inner { max-width: 1080px; margin: 0 auto; }
.amalfi-editorial__lead {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3.5rem;
  margin-bottom: 3.5rem;
}
.amalfi-editorial__h2 { font-family: 'Cinzel', serif; font-size: 2.6rem; color: #f8fafc; margin: 0; }
.amalfi-editorial__quote {
  margin: 0;
  padding: 0.5rem 0 0.5rem 1.75rem;
  border-left: 2px solid #d97706;
}
.amalfi-editorial__quote p { font-style: italic; font-size: 1.05rem; color: #e7e5e4; line-height: 1.6; margin: 0 0 0.5rem; }
.amalfi-editorial__quote cite { font-size: 0.75rem; color: #d97706; text-transform: uppercase; display: block; }
.amalfi-editorial__prose {
  column-count: 2;
  column-gap: 3.5rem;
  font-size: 1.02rem;
  line-height: 1.8;
  color: #d6d3d1;
  margin-bottom: 4rem;
  text-align: justify;
}
.amalfi-editorial__p { margin: 0 0 1.5rem; }
.amalfi-editorial__p--dropcap::first-letter {
  float: left;
  font-family: 'Cinzel', serif;
  font-size: 3.6rem;
  line-height: 0.8;
  padding-right: 0.6rem;
  padding-top: 0.2rem;
  color: #d97706;
}
.amalfi-editorial__estates {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  border-top: 1px solid rgba(217, 119, 6, 0.25);
  padding-top: 3rem;
}
.amalfi-estate { background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); padding: 2rem; border-radius: 4px; }
.amalfi-estate__ref { font-size: 0.6875rem; font-family: monospace; color: #d97706; display: block; margin-bottom: 0.5rem; }
.amalfi-estate__title { font-family: 'Cinzel', serif; font-size: 1.25rem; color: #f8fafc; margin: 0 0 0.75rem; }
.amalfi-estate__desc { font-size: 0.875rem; color: #a8a29e; line-height: 1.6; margin: 0; }
@media (max-width: 800px) {
  .amalfi-editorial__lead { grid-template-columns: 1fr; }
  .amalfi-editorial__prose { column-count: 1; }
  .amalfi-editorial__estates { grid-template-columns: 1fr; }
}"""
        },
        {
            "name": "CadastralDisclosures",
            "instruction": "trust section detailing Italian Real Estate Mediation License REA #SA-491820 and Cultural Heritage compliance. Files: src/components/CadastralDisclosures.tsx + src/components/CadastralDisclosures.css",
            "tsx_path": "src/components/CadastralDisclosures.tsx",
            "css_path": "src/components/CadastralDisclosures.css",
            "thought": "Building Italian legal disclosures and cadastral title certification block.",
            "tsx": """import React from 'react';
import './CadastralDisclosures.css';

export function CadastralDisclosures() {
  return (
    <section className="amalfi-legal" id="cadastral" aria-label="Italian Real Estate Mediation & Cultural Heritage Disclosures">
      <div className="amalfi-legal__inner">
        <div className="amalfi-legal__box">
          <span className="amalfi-legal__tag">REGOLAMENTAZIONE IMMOBILIARE ITALIANA</span>
          <h4 className="amalfi-legal__title">Ruolo Mediatori Immobiliari REA #SA-491820 · Camera di Commercio Salerno</h4>
          <p className="amalfi-legal__text">
            All featured estates are listed under exclusive bilateral mandates verified through the Italian Revenue Agency (Agenzia delle Entrate) and Land Registry (Catasto Edilizio Urbano). Monumental historic assets are subject to the Italian Cultural Heritage Code (D.Lgs. 42/2004) under the supervision of the Soprintendenza Archeologia, Belle Arti e Paesaggio di Salerno e Avellino.
          </p>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.amalfi-legal {
  padding: 4rem 1.5rem;
  background: #0a0807;
  border-top: 1px solid rgba(217, 119, 6, 0.2);
}
.amalfi-legal__inner { max-width: 1080px; margin: 0 auto; }
.amalfi-legal__box {
  background: rgba(217, 119, 6, 0.04);
  border: 1px solid rgba(217, 119, 6, 0.25);
  border-left: 3px solid #d97706;
  padding: 2rem;
  border-radius: 6px;
}
.amalfi-legal__tag { font-size: 0.75rem; font-family: monospace; color: #d97706; letter-spacing: 0.08em; display: block; margin-bottom: 0.5rem; font-weight: 700; }
.amalfi-legal__title { font-family: 'Cinzel', serif; font-size: 1.15rem; color: #f8fafc; margin: 0 0 0.75rem; }
.amalfi-legal__text { font-size: 0.8125rem; color: #a8a29e; line-height: 1.7; margin: 0; }"""
        },
        {
            "name": "Footer",
            "instruction": "Ravello estate footer with Italian contact details and international buyer legal copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified Italian address.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="amalfi-footer" id="footer" role="contentinfo">
      <div className="amalfi-footer__inner">
        <div>
          <span className="amalfi-footer__logo">AMALFI COAST HISTORIC VILLAS</span>
          <p className="amalfi-footer__desc">Bespoke Heritage Estate Brokerage in Ravello & Capri.</p>
        </div>
        <address className="amalfi-footer__addr">
          <p>Via Panoramica 14</p>
          <p>84010 Ravello (SA), Italy</p>
          <p><a href="tel:+390895550122">+39 089 555 0122</a> · <a href="mailto:segreteria@amalasticvillas.it">segreteria@amalasticvillas.it</a></p>
        </address>
      </div>
      <div className="amalfi-footer__bottom">
        <p>© {new Date().getFullYear()} Amalfi Coast Historic Villas S.r.l. REA #SA-491820. Partita IVA IT04918200651.</p>
      </div>
    </footer>
  );
}""",
            "css": """.amalfi-footer {
  background: #060504;
  padding: 4rem 1.5rem 2rem;
  color: #78716c;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.amalfi-footer__inner { max-width: 1080px; margin: 0 auto; display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2.5rem; flex-wrap: wrap; gap: 2rem; }
.amalfi-footer__logo { font-family: 'Cinzel', serif; font-size: 1.15rem; color: #f8fafc; font-weight: 700; display: block; margin-bottom: 0.25rem; }
.amalfi-footer__desc { font-size: 0.8125rem; }
.amalfi-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.amalfi-footer__addr a { color: #d97706; text-decoration: none; }
.amalfi-footer__bottom { max-width: 1080px; margin: 0 auto; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; font-size: 0.75rem; }"""
        }
    ]
    trajs.append(make_traj("site_realestate_editorial_amalfi", t3_brief, t3_sections))

    return trajs
