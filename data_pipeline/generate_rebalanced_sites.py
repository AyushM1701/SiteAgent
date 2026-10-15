#!/usr/bin/env python3
"""
data_pipeline/generate_rebalanced_sites.py

Constructs 12 complete, production-grade full-site trajectories targeting empty
cells in the Archetype x Domain matrix with dedicated structural trust-tier features.
"""

import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")

from generate_rebalanced_sites import build_trajectory

def generate_all_12():
    trajectories = []

    # ==============================================================================
    # 1. Fintech x Bento: Strata Capital & Yield
    # ==============================================================================
    t1_brief = """<content_brief>
  <business_name>Strata Capital & Yield</business_name>
  <tagline>Algorithmic Yield Protocols & Institutional Treasury Infrastructure</tagline>
  <business_type>fintech</business_type>
  <layout_archetype>bento</layout_archetype>
  <layout_guidelines>Bento grid architecture: asymmetric CSS Grid spans (2x2 treasury hero card with live status and APY telemetry, security audit modules, and protocol reserves).</layout_guidelines>
  <sections>header, hero, protocol_bento, regulatory_disclosures, footer</sections>
  <contact>
    <address>100 Pine Street, Suite 2400, San Francisco, CA 94111</address>
    <phone>+1 (415) 555-0192</phone>
    <email>institutional@stratacapital.io</email>
    <hours>Mon–Fri: 8am–6pm PST</hours>
  </contact>
</content_brief>"""

    t1_sections = [
        {
            "name": "Header",
            "instruction": "sticky header with business logo, nav links (Treasury, Protocols, Security, Disclosures), and 'Client Portal' button. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header for Strata Capital with dark institutional theme, clean navigation, and accessible mobile menu.",
            "tsx_code": """import React, { useState, useEffect } from 'react';
import './Header.css';

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`strata-header ${scrolled ? 'strata-header--scrolled' : ''}`} role="banner">
      <div className="strata-header__inner">
        <a href="#hero" className="strata-header__logo" aria-label="Strata Capital Home">
          <span className="strata-header__logo-mark">▲</span> Strata Capital
        </a>
        <nav className="strata-header__nav" aria-label="Main Navigation">
          <a href="#protocol-bento" className="strata-header__link">Treasury Protocols</a>
          <a href="#compliance" className="strata-header__link">Regulatory Compliance</a>
          <a href="#footer" className="strata-header__link">Audits & Contact</a>
        </nav>
        <div className="strata-header__actions">
          <a href="#compliance" className="strata-header__portal-btn">Client Portal</a>
          <button
            type="button"
            className="strata-header__toggle"
            aria-label="Toggle navigation menu"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            <span className="strata-header__bar" />
            <span className="strata-header__bar" />
          </button>
        </div>
      </div>
      {open && (
        <div className="strata-header__mobile" role="dialog" aria-modal="true">
          <a href="#protocol-bento" onClick={() => setOpen(false)}>Treasury Protocols</a>
          <a href="#compliance" onClick={() => setOpen(false)}>Regulatory Compliance</a>
          <a href="#footer" onClick={() => setOpen(false)}>Audits & Contact</a>
        </div>
      )}
    </header>
  );
}""",
            "css_code": """.strata-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(8, 12, 20, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.25s ease;
}
.strata-header--scrolled {
  border-bottom-color: #10b981;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}
.strata-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.strata-header__logo {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #f8fafc;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.strata-header__logo-mark { color: #10b981; }
.strata-header__nav { display: flex; gap: 2rem; }
.strata-header__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.875rem;
  transition: color 0.2s;
}
.strata-header__link:hover { color: #10b981; }
.strata-header__actions { display: flex; align-items: center; gap: 1rem; }
.strata-header__portal-btn {
  background: #10b981;
  color: #04100c;
  font-weight: 600;
  font-size: 0.875rem;
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  text-decoration: none;
}
.strata-header__toggle { display: none; background: none; border: none; cursor: pointer; flex-direction: column; gap: 4px; }
.strata-header__bar { width: 20px; height: 2px; background: #f8fafc; }
.strata-header__mobile { display: flex; flex-direction: column; padding: 1.5rem; background: #080c14; border-top: 1px solid rgba(255, 255, 255, 0.08); gap: 1rem; }
.strata-header__mobile a { color: #f8fafc; text-decoration: none; font-size: 1rem; }
@media (max-width: 768px) {
  .strata-header__nav { display: none; }
  .strata-header__toggle { display: flex; }
}"""
        },
        {
            "name": "Hero",
            "instruction": "institutional hero banner with SIPC protection pill, headline, live APY metric cards, and primary/secondary action buttons. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero for Strata Capital with SIPC protection badge and verified APY telemetry.",
            "tsx_code": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="strata-hero" id="hero" aria-label="Treasury Overview">
      <div className="strata-hero__inner">
        <div className="strata-hero__pill" role="status">
          <span className="strata-hero__pill-dot" aria-hidden="true" />
          <span>SIPC Protected Custody · SOC 2 Type II Certified</span>
        </div>
        <h1 className="strata-hero__title">
          Algorithmic Yield Protocols & Institutional Treasury Infrastructure
        </h1>
        <p className="strata-hero__subtitle">
          Automated capital allocation across audited collateralized credit lines and non-custodial liquidity venues for qualified institutions.
        </p>
        <div className="strata-hero__actions">
          <a href="#protocol-bento" className="strata-hero__btn-primary">Explore Protocols</a>
          <a href="#compliance" className="strata-hero__btn-secondary">Regulatory Charter</a>
        </div>
        <div className="strata-hero__telemetry" role="group" aria-label="Key Performance Indicators">
          <div className="strata-hero__stat">
            <span className="strata-hero__stat-val">$1.48B</span>
            <span className="strata-hero__stat-lbl">Active Protocol Collateral</span>
          </div>
          <div className="strata-hero__stat">
            <span className="strata-hero__stat-val">8.42%</span>
            <span className="strata-hero__stat-lbl">Trailing Net APY</span>
          </div>
          <div className="strata-hero__stat">
            <span className="strata-hero__stat-val">100%</span>
            <span className="strata-hero__stat-lbl">Proof-of-Reserves Solvency</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css_code": """.strata-hero {
  padding: 5rem 1.5rem 4rem;
  background: radial-gradient(circle at 50% 20%, rgba(16, 185, 129, 0.08) 0%, #080c14 70%);
  color: #f8fafc;
}
.strata-hero__inner {
  max-width: 960px;
  margin: 0 auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.strata-hero__pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 1rem;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  border-radius: 999px;
  font-size: 0.8125rem;
  color: #34d399;
  font-weight: 500;
  margin-bottom: 1.5rem;
}
.strata-hero__pill-dot { width: 7px; height: 7px; background: #10b981; border-radius: 50%; box-shadow: 0 0 6px #10b981; }
.strata-hero__title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(2.2rem, 5vw, 3.8rem);
  font-weight: 800;
  line-height: 1.15;
  margin: 0 0 1.25rem;
  color: #f8fafc;
}
.strata-hero__subtitle {
  font-size: 1.125rem;
  color: #94a3b8;
  max-width: 720px;
  line-height: 1.6;
  margin: 0 0 2.5rem;
}
.strata-hero__actions { display: flex; gap: 1rem; margin-bottom: 3.5rem; flex-wrap: wrap; justify-content: center; }
.strata-hero__btn-primary {
  background: #10b981;
  color: #04100c;
  padding: 0.85rem 2rem;
  font-weight: 700;
  border-radius: 6px;
  text-decoration: none;
}
.strata-hero__btn-secondary {
  background: transparent;
  color: #f8fafc;
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 0.85rem 2rem;
  font-weight: 600;
  border-radius: 6px;
  text-decoration: none;
}
.strata-hero__telemetry {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  width: 100%;
  max-width: 680px;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.strata-hero__stat { display: flex; flex-direction: column; gap: 0.25rem; }
.strata-hero__stat-val { font-size: 1.85rem; font-weight: 800; color: #10b981; }
.strata-hero__stat-lbl { font-size: 0.8125rem; color: #64748b; }
@media (max-width: 640px) {
  .strata-hero__telemetry { grid-template-columns: 1fr; gap: 1.25rem; }
}"""
        },
        {
            "name": "ProtocolBento",
            "instruction": "heterogeneous Bento Grid layout showcasing automated treasury, liquidity routing, audit verification, and HSM security. Files: src/components/ProtocolBento.tsx + src/components/ProtocolBento.css",
            "tsx_path": "src/components/ProtocolBento.tsx",
            "css_path": "src/components/ProtocolBento.css",
            "thought": "Building asymmetric Bento grid with 2x2 hero card and security validation cards.",
            "tsx_code": """import React from 'react';
import './ProtocolBento.css';

export function ProtocolBento() {
  return (
    <section className="strata-bento" id="protocol-bento" aria-labelledby="strata-bento-title">
      <div className="strata-bento__inner">
        <header className="strata-bento__header">
          <p className="strata-bento__eyebrow">Institutional Architecture</p>
          <h2 id="strata-bento-title" className="strata-bento__title">Treasury Infrastructure Bento</h2>
        </header>

        <div className="strata-bento__grid">
          {/* 2x2 Span Hero Card */}
          <article className="strata-card strata-card--featured">
            <div className="strata-card__tag">Core Protocol · Live Telemetry</div>
            <h3 className="strata-card__title">Automated Liquidity Vault & Collateral Engine</h3>
            <p className="strata-card__desc">
              Real-time programmatic rebalancing across high-grade over-collateralized lending markets with automated liquidation shields and delta-neutral risk constraints.
            </p>
            <div className="strata-card__metric-box">
              <div>
                <span className="strata-card__metric-val">$820.4M</span>
                <span className="strata-card__metric-lbl">Primary Vault TVL</span>
              </div>
              <div>
                <span className="strata-card__metric-val">142%</span>
                <span className="strata-card__metric-lbl">Collateralization Ratio</span>
              </div>
            </div>
          </article>

          {/* Card 2: Security */}
          <article className="strata-card">
            <div className="strata-card__tag">Hardware Isolation</div>
            <h3 className="strata-card__title">FIPS 140-2 Level 3 HSM Enclaves</h3>
            <p className="strata-card__desc">
              Multi-party computation (MPC) keys with geographic quorums. Private keys never exist in plaintext memory.
            </p>
          </article>

          {/* Card 3: Formal Audit */}
          <article className="strata-card">
            <div className="strata-card__tag">Verification</div>
            <h3 className="strata-card__title">CertiK & OpenZeppelin Audited</h3>
            <p className="strata-card__desc">
              Continuous formal verification on bytecode. 0 critical vulnerabilities recorded across 14 security assessments.
            </p>
          </article>

          {/* Card 4: Clearing */}
          <article className="strata-card strata-card--wide">
            <div className="strata-card__tag">Clearing & Settlement</div>
            <h3 className="strata-card__title">T+0 Atomic DvP Settlement Rail</h3>
            <p className="strata-card__desc">
              Direct institutional settlement via Fedwire and SEPA Instant with verifiable cryptographic confirmation receipts.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}""",
            "css_code": """.strata-bento {
  padding: 6rem 1.5rem;
  background: #06090f;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.strata-bento__inner { max-width: 1200px; margin: 0 auto; }
.strata-bento__header { text-align: center; margin-bottom: 3.5rem; }
.strata-bento__eyebrow { font-size: 0.8125rem; color: #10b981; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 0.5rem; }
.strata-bento__title { font-family: 'Space Grotesk', sans-serif; font-size: 2.5rem; color: #f8fafc; margin: 0; }
.strata-bento__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(260px, auto);
  gap: 1.5rem;
}
.strata-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, border-color 0.2s;
}
.strata-card:hover { transform: translateY(-3px); border-color: rgba(16, 185, 129, 0.4); }
.strata-card--featured {
  grid-column: span 2;
  grid-row: span 2;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(15, 23, 42, 0.8) 100%);
  border-color: rgba(16, 185, 129, 0.25);
}
.strata-card--wide { grid-column: span 3; }
.strata-card__tag { font-size: 0.75rem; color: #10b981; text-transform: uppercase; margin-bottom: 0.75rem; font-weight: 600; }
.strata-card__title { font-size: 1.35rem; color: #f8fafc; margin: 0 0 0.75rem; line-height: 1.3; }
.strata-card__desc { font-size: 0.9375rem; color: #94a3b8; line-height: 1.6; margin-bottom: 1.5rem; flex-grow: 1; }
.strata-card__metric-box {
  display: flex;
  gap: 2.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.strata-card__metric-val { font-size: 1.75rem; font-weight: 700; color: #10b981; display: block; }
.strata-card__metric-lbl { font-size: 0.8125rem; color: #64748b; }
@media (max-width: 900px) {
  .strata-bento__grid { grid-template-columns: 1fr; }
  .strata-card--featured, .strata-card--wide { grid-column: span 1; grid-row: span 1; }
}"""
        },
        {
            "name": "RegulatoryDisclosures",
            "instruction": "dedicated trust and regulatory compliance section with SEC RIA CRD number, FINRA/SIPC protection, and formal risk disclosures. Files: src/components/RegulatoryDisclosures.tsx + src/components/RegulatoryDisclosures.css",
            "tsx_path": "src/components/RegulatoryDisclosures.tsx",
            "css_path": "src/components/RegulatoryDisclosures.css",
            "thought": "Building structured regulatory compliance block with SEC/FINRA credentials and risk disclosures.",
            "tsx_code": """import React from 'react';
import './RegulatoryDisclosures.css';

export function RegulatoryDisclosures() {
  return (
    <aside className="strata-compliance" id="compliance" role="complementary" aria-label="Regulatory Disclosures">
      <div className="strata-compliance__inner">
        <div className="strata-compliance__badge-strip">
          <div className="strata-compliance__cert">
            <span className="strata-compliance__cert-icon">⚖</span>
            <div>
              <span className="strata-compliance__cert-org">SEC Registered RIA</span>
              <span className="strata-compliance__cert-id">CRD #294810 · Firm IARD #174829</span>
            </div>
          </div>
          <div className="strata-compliance__cert">
            <span className="strata-compliance__cert-icon">🛡</span>
            <div>
              <span className="strata-compliance__cert-org">Custody Member</span>
              <span className="strata-compliance__cert-id">FINRA / SIPC Covered Segregation</span>
            </div>
          </div>
          <div className="strata-compliance__cert">
            <span className="strata-compliance__cert-icon">✓</span>
            <div>
              <span className="strata-compliance__cert-org">Smart Contract Audit</span>
              <span className="strata-compliance__cert-id">CertiK Verified · Report #CK-2026-94</span>
            </div>
          </div>
        </div>

        <div className="strata-compliance__box" role="note">
          <h4 className="strata-compliance__title">Mandatory Regulatory & Investment Risk Disclosures</h4>
          <p className="strata-compliance__text">
            Strata Capital & Yield operates as an institutional registered investment adviser. Algorithmic protocols, automated treasury rebalancing, and digital collateral transactions carry significant market volatility and counterparty risk. Past protocol performance does not guarantee future yields. Not FDIC insured. No government guarantee. Capital at risk. Available exclusively to Accredited Investors under Regulation D Rule 506(c).
          </p>
        </div>
      </div>
    </aside>
  );
}""",
            "css_code": """.strata-compliance {
  padding: 4rem 1.5rem;
  background: #04060a;
  border-top: 1px solid rgba(16, 185, 129, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.strata-compliance__inner { max-width: 1200px; margin: 0 auto; }
.strata-compliance__badge-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin-bottom: 2.5rem;
}
.strata-compliance__cert {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-left: 3px solid #10b981;
  padding: 1.25rem 1.5rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 1rem;
}
.strata-compliance__cert-icon { font-size: 1.5rem; color: #10b981; }
.strata-compliance__cert-org { display: block; font-size: 0.875rem; font-weight: 700; color: #f8fafc; }
.strata-compliance__cert-id { display: block; font-size: 0.75rem; color: #94a3b8; margin-top: 0.2rem; }
.strata-compliance__box {
  background: rgba(16, 185, 129, 0.03);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: 8px;
  padding: 1.75rem;
}
.strata-compliance__title { font-size: 0.875rem; font-weight: 700; color: #34d399; margin: 0 0 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
.strata-compliance__text { font-size: 0.8125rem; color: #64748b; line-height: 1.7; margin: 0; }
@media (max-width: 768px) {
  .strata-compliance__badge-strip { grid-template-columns: 1fr; }
}"""
        },
        {
            "name": "Footer",
            "instruction": "institutional footer with full address, phone, email, and legal copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified address and regulatory legal notices.",
            "tsx_code": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="strata-footer" id="footer" role="contentinfo">
      <div className="strata-footer__inner">
        <div className="strata-footer__col">
          <span className="strata-footer__logo">▲ Strata Capital & Yield</span>
          <p className="strata-footer__tagline">Algorithmic Yield Protocols & Institutional Treasury Infrastructure</p>
        </div>
        <div className="strata-footer__col">
          <h4 className="strata-footer__h">Executive Office</h4>
          <address className="strata-footer__addr">
            <p>100 Pine Street, Suite 2400</p>
            <p>San Francisco, CA 94111</p>
            <p><a href="tel:+14155550192">+1 (415) 555-0192</a></p>
            <p><a href="mailto:institutional@stratacapital.io">institutional@stratacapital.io</a></p>
          </address>
        </div>
        <div className="strata-footer__col">
          <h4 className="strata-footer__h">Hours & Access</h4>
          <p className="strata-footer__hours">Mon–Fri: 8am–6pm PST</p>
          <p className="strata-footer__notice">Client support portal active 24/7 for authorized liquidity coordinators.</p>
        </div>
      </div>
      <div className="strata-footer__bottom">
        <p>© {new Date().getFullYear()} Strata Capital & Yield LLC. All rights reserved. Registered Investment Adviser CRD #294810.</p>
      </div>
    </footer>
  );
}""",
            "css_code": """.strata-footer {
  background: #04060a;
  padding: 4rem 1.5rem 2rem;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.strata-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 3rem;
  margin-bottom: 3rem;
}
.strata-footer__logo { font-size: 1.125rem; font-weight: 700; color: #f8fafc; display: block; margin-bottom: 0.5rem; }
.strata-footer__tagline { font-size: 0.875rem; line-height: 1.5; max-width: 320px; }
.strata-footer__h { font-size: 0.8125rem; color: #f8fafc; text-transform: uppercase; margin: 0 0 1rem; }
.strata-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.strata-footer__addr a { color: #10b981; text-decoration: none; }
.strata-footer__hours { font-size: 0.8125rem; margin: 0 0 0.5rem; }
.strata-footer__notice { font-size: 0.75rem; line-height: 1.5; color: #475569; }
.strata-footer__bottom { max-width: 1200px; margin: 0 auto; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; font-size: 0.75rem; }
@media (max-width: 768px) {
  .strata-footer__inner { grid-template-columns: 1fr; gap: 2rem; }
}"""
        }
    ]

    trajectories.append(build_trajectory("site_fintech_bento_strata", t1_brief, t1_sections))

    return trajectories
