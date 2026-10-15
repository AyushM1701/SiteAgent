"""
data_pipeline/rebalanced_fintech.py

Hand-authored full-site trajectories for Fintech across Bento, Tabs, and Split-Hero archetypes
with rich structural trust-tier features (SEC/FINRA disclosures, SIPC protection, CertiK audit, MPC custody).
"""

from build_rebalanced_dataset import make_traj

def get_fintech_trajectories():
    trajs = []

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
            "tsx": """import React, { useState, useEffect } from 'react';
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
            "css": """.strata-header {
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
            "tsx": """import React from 'react';
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
            "css": """.strata-hero {
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
            "tsx": """import React from 'react';
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

          <article className="strata-card">
            <div className="strata-card__tag">Hardware Isolation</div>
            <h3 className="strata-card__title">FIPS 140-2 Level 3 HSM Enclaves</h3>
            <p className="strata-card__desc">
              Multi-party computation (MPC) keys with geographic quorums. Private keys never exist in plaintext memory.
            </p>
          </article>

          <article className="strata-card">
            <div className="strata-card__tag">Verification</div>
            <h3 className="strata-card__title">CertiK & OpenZeppelin Audited</h3>
            <p className="strata-card__desc">
              Continuous formal verification on bytecode. 0 critical vulnerabilities recorded across 14 security assessments.
            </p>
          </article>

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
            "css": """.strata-bento {
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
            "tsx": """import React from 'react';
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
            "css": """.strata-compliance {
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
            "tsx": """import React from 'react';
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
            "css": """.strata-footer {
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
    trajs.append(make_traj("site_fintech_bento_strata", t1_brief, t1_sections))

    # ==============================================================================
    # 2. Fintech x Tabs: Apex Quantitative Fund
    # ==============================================================================
    t2_brief = """<content_brief>
  <business_name>Apex Quantitative Fund</business_name>
  <tagline>Multi-Strategy Quantitative Alpha & Low-Latency Systematic Execution</tagline>
  <business_type>fintech</business_type>
  <layout_archetype>tabs</layout_archetype>
  <layout_guidelines>Tabbed strategy architecture: stateful React tab bar switching between Long/Short Equity, Statistical Arbitrage, and Global Macro with dynamic risk-adjusted returns and Form ADV Part 2A disclosure.</layout_guidelines>
  <sections>header, hero, strategy_tabs, investor_gating, footer</sections>
  <contact>
    <address>590 Madison Avenue, 38th Floor, New York, NY 10022</address>
    <phone>+1 (212) 555-0144</phone>
    <email>ir@apexquantfund.com</email>
    <hours>Mon–Fri: 7:30am–6pm EST</hours>
  </contact>
</content_brief>"""

    t2_sections = [
        {
            "name": "Header",
            "instruction": "minimal institutional header with SEC RIA badge and Investor Access button. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building institutional header for Apex Quantitative Fund with SEC RIA designation.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="apex-header" role="banner">
      <div className="apex-header__inner">
        <a href="#hero" className="apex-header__brand" aria-label="Apex Quantitative Fund Home">
          <span className="apex-header__symbol">◈</span> APEX QUANTITATIVE
        </a>
        <span className="apex-header__ria">SEC Registered Investment Adviser · Form ADV Part 2A</span>
        <a href="#investor-gating" className="apex-header__login">Investor Portal</a>
      </div>
    </header>
  );
}""",
            "css": """.apex-header {
  background: #05080e;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1.25rem 2rem;
}
.apex-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.apex-header__brand {
  font-family: 'Outfit', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #f8fafc;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.apex-header__symbol { color: #3b82f6; }
.apex-header__ria { font-size: 0.75rem; color: #64748b; letter-spacing: 0.04em; text-transform: uppercase; }
.apex-header__login {
  background: transparent;
  border: 1px solid rgba(59, 130, 246, 0.4);
  color: #93c5fd;
  padding: 0.4rem 1rem;
  border-radius: 4px;
  font-size: 0.8125rem;
  text-decoration: none;
  transition: all 0.2s;
}
.apex-header__login:hover { background: rgba(59, 130, 246, 0.1); border-color: #3b82f6; }
@media (max-width: 768px) { .apex-header__ria { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "hero with headline, SEC RIA Registry number, strategy capital deployment, and Sharpe ratio highlights. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero for Apex Quant with mathematical precision and SEC credentials.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="apex-hero" id="hero" aria-label="Fund Strategy Overview">
      <div className="apex-hero__inner">
        <div className="apex-hero__cert-badge" role="status">
          <span>SEC RIA Registry #801-92841 · LEI #549300APEXQNT18204</span>
        </div>
        <h1 className="apex-hero__title">
          Multi-Strategy Quantitative Alpha & Systematic Execution
        </h1>
        <p className="apex-hero__desc">
          Exploiting statistical micro-inefficiencies across global equities, liquid futures, and rates with rigorous risk constraints and orthogonal return streams.
        </p>
        <div className="apex-hero__metrics">
          <div className="apex-hero__item">
            <span className="apex-hero__val">2.84</span>
            <span className="apex-hero__lbl">10-Year Sharpe Ratio</span>
          </div>
          <div className="apex-hero__item">
            <span className="apex-hero__val">&lt; 0.05</span>
            <span className="apex-hero__lbl">S&P 500 Correlation</span>
          </div>
          <div className="apex-hero__item">
            <span className="apex-hero__val">$3.2B</span>
            <span className="apex-hero__lbl">Institutional AUM</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.apex-hero {
  padding: 5.5rem 1.5rem 4rem;
  background: #05080e;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  text-align: center;
}
.apex-hero__inner { max-width: 900px; margin: 0 auto; }
.apex-hero__cert-badge {
  display: inline-block;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: #60a5fa;
  font-size: 0.75rem;
  padding: 0.3rem 0.9rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  font-family: monospace;
}
.apex-hero__title {
  font-family: 'Outfit', sans-serif;
  font-size: clamp(2.2rem, 4.5vw, 3.6rem);
  font-weight: 800;
  color: #f8fafc;
  line-height: 1.18;
  margin: 0 0 1.25rem;
}
.apex-hero__desc { font-size: 1.1rem; color: #94a3b8; line-height: 1.65; margin: 0 0 3rem; }
.apex-hero__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.apex-hero__item { display: flex; flex-direction: column; gap: 0.25rem; }
.apex-hero__val { font-size: 2rem; font-weight: 800; color: #3b82f6; }
.apex-hero__lbl { font-size: 0.8125rem; color: #64748b; }
@media (max-width: 600px) { .apex-hero__metrics { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "StrategyTabs",
            "instruction": "interactive strategy tabs using React useState to toggle between Long/Short Equity, Statistical Arbitrage, and Global Macro with live risk metrics. Files: src/components/StrategyTabs.tsx + src/components/StrategyTabs.css",
            "tsx_path": "src/components/StrategyTabs.tsx",
            "css_path": "src/components/StrategyTabs.css",
            "thought": "Building interactive strategy tabs with React state for quantitative portfolio views.",
            "tsx": """import React, { useState } from 'react';
import './StrategyTabs.css';

interface Strategy {
  id: string;
  name: string;
  subtitle: string;
  sharpe: string;
  holdingPeriod: string;
  capacity: string;
  description: string;
}

const STRATEGIES: Strategy[] = [
  {
    id: 'equity-ls',
    name: 'Equity Long/Short',
    subtitle: 'Factor-Neutral Cross-Sectional Alpha',
    sharpe: '2.92',
    holdingPeriod: '2.4 Days',
    capacity: '$1.2B',
    description: 'Systematic ranking of 4,000 liquid global equities across proprietary sentiment, alternative data exhaust, and earnings momentum vectors.'
  },
  {
    id: 'stat-arb',
    name: 'Statistical Arbitrage',
    subtitle: 'High-Frequency Mean Reversion & Order Flow',
    sharpe: '3.41',
    holdingPeriod: '18 Minutes',
    capacity: '$800M',
    description: 'Co-located FPGA execution capturing transitory price dislocations across ETF baskets, cross-venue books, and index constituents.'
  },
  {
    id: 'macro',
    name: 'Global Macro',
    subtitle: 'Sovereign Rates & Commodities Trend Following',
    sharpe: '2.45',
    holdingPeriod: '14 Days',
    capacity: '$1.5B',
    description: 'Bayesian regime-switching models trading G10 government bond yields, foreign exchange spreads, and energy futures contracts.'
  }
];

export function StrategyTabs() {
  const [activeTab, setActiveTab] = useState('equity-ls');
  const current = STRATEGIES.find(s => s.id === activeTab) || STRATEGIES[0];

  return (
    <section className="apex-tabs" id="strategy-tabs" aria-labelledby="apex-tabs-title">
      <div className="apex-tabs__inner">
        <header className="apex-tabs__header">
          <p className="apex-tabs__eyebrow">Portfolio Construction</p>
          <h2 id="apex-tabs-title" className="apex-tabs__title">Systematic Investment Strategies</h2>
        </header>

        <div className="apex-tabs__bar" role="tablist" aria-label="Investment Strategies">
          {STRATEGIES.map(s => (
            <button
              key={s.id}
              type="button"
              role="tab"
              aria-selected={activeTab === s.id}
              className={`apex-tabs__btn ${activeTab === s.id ? 'apex-tabs__btn--active' : ''}`}
              onClick={() => setActiveTab(s.id)}
            >
              {s.name}
            </button>
          ))}
        </div>

        <div className="apex-tabs__panel" role="tabpanel">
          <div className="apex-tabs__panel-top">
            <div>
              <h3 className="apex-tabs__panel-title">{current.name}</h3>
              <p className="apex-tabs__panel-subtitle">{current.subtitle}</p>
            </div>
            <span className="apex-tabs__capacity-badge">Capacity: {current.capacity}</span>
          </div>

          <p className="apex-tabs__panel-desc">{current.description}</p>

          <div className="apex-tabs__panel-grid">
            <div className="apex-tabs__stat-card">
              <span className="apex-tabs__stat-key">Simulated / Live Sharpe</span>
              <span className="apex-tabs__stat-num">{current.sharpe}</span>
            </div>
            <div className="apex-tabs__stat-card">
              <span className="apex-tabs__stat-key">Avg Holding Period</span>
              <span className="apex-tabs__stat-num">{current.holdingPeriod}</span>
            </div>
            <div className="apex-tabs__stat-card">
              <span className="apex-tabs__stat-key">Target Volatility</span>
              <span className="apex-tabs__stat-num">8.0% Ann.</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.apex-tabs {
  padding: 6rem 1.5rem;
  background: #070b14;
}
.apex-tabs__inner { max-width: 1000px; margin: 0 auto; }
.apex-tabs__header { text-align: center; margin-bottom: 3rem; }
.apex-tabs__eyebrow { font-size: 0.8125rem; color: #3b82f6; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 0.5rem; }
.apex-tabs__title { font-family: 'Outfit', sans-serif; font-size: 2.3rem; color: #f8fafc; margin: 0; }
.apex-tabs__bar {
  display: flex;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 0.35rem;
  gap: 0.5rem;
  margin-bottom: 2rem;
}
.apex-tabs__btn {
  flex: 1;
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 0.85rem 1rem;
  font-size: 0.9375rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.apex-tabs__btn--active {
  background: #1e293b;
  color: #60a5fa;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
.apex-tabs__panel {
  background: #0d1527;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  padding: 2.5rem;
}
.apex-tabs__panel-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}
.apex-tabs__panel-title { font-size: 1.75rem; color: #f8fafc; margin: 0 0 0.25rem; }
.apex-tabs__panel-subtitle { font-size: 0.875rem; color: #64748b; margin: 0; }
.apex-tabs__capacity-badge {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #93c5fd;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
}
.apex-tabs__panel-desc { font-size: 1.05rem; color: #cbd5e1; line-height: 1.7; margin-bottom: 2rem; }
.apex-tabs__panel-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.apex-tabs__stat-card { background: rgba(15, 23, 42, 0.5); padding: 1rem 1.25rem; border-radius: 6px; }
.apex-tabs__stat-key { display: block; font-size: 0.75rem; color: #64748b; margin-bottom: 0.25rem; }
.apex-tabs__stat-num { font-size: 1.35rem; font-weight: 700; color: #38bdf8; }
@media (max-width: 650px) {
  .apex-tabs__bar { flex-direction: column; }
  .apex-tabs__panel-grid { grid-template-columns: 1fr; }
}"""
        },
        {
            "name": "InvestorGating",
            "instruction": "dedicated trust and compliance callout section detailing Regulation D Rule 506(c) accredited investor restrictions and Form ADV Part 2A availability. Files: src/components/InvestorGating.tsx + src/components/InvestorGating.css",
            "tsx_path": "src/components/InvestorGating.tsx",
            "css_path": "src/components/InvestorGating.css",
            "thought": "Building structured legal disclosures and accredited investor eligibility restrictions.",
            "tsx": """import React from 'react';
import './InvestorGating.css';

export function InvestorGating() {
  return (
    <section className="apex-gating" id="investor-gating" aria-label="Regulatory Disclosures & Investor Eligibility">
      <div className="apex-gating__inner">
        <div className="apex-gating__callout" role="note">
          <div className="apex-gating__header">
            <span className="apex-gating__seal">SEC REGULATION D · RULE 506(c)</span>
            <h4 className="apex-gating__title">Strict Institutional & Accredited Investor Verification</h4>
          </div>
          <p className="apex-gating__body">
            Interests in funds managed by Apex Quantitative Fund Management LP are offered exclusively to verified "Accredited Investors" as defined in Rule 501 of Regulation D under the U.S. Securities Act of 1933, as amended, and "Qualified Purchasers" under Section 2(a)(51) of the U.S. Investment Company Act of 1940. This site does not constitute an offer to sell or a solicitation of an offer to buy any securities. Past performance is no guarantee of future returns.
          </p>
          <div className="apex-gating__meta">
            <span>SEC File Number: 801-92841</span>
            <span>CRD #184920</span>
            <span>Form ADV Part 2A Brochure available via IAPD</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.apex-gating {
  padding: 4rem 1.5rem;
  background: #05080e;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.apex-gating__inner { max-width: 1000px; margin: 0 auto; }
.apex-gating__callout {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-left: 4px solid #3b82f6;
  border-radius: 8px;
  padding: 2rem;
}
.apex-gating__header { margin-bottom: 1rem; }
.apex-gating__seal { font-size: 0.75rem; font-family: monospace; color: #60a5fa; letter-spacing: 0.08em; display: block; margin-bottom: 0.25rem; }
.apex-gating__title { font-size: 1.15rem; color: #f8fafc; margin: 0; }
.apex-gating__body { font-size: 0.875rem; color: #94a3b8; line-height: 1.7; margin: 0 0 1.5rem; }
.apex-gating__meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.75rem;
  color: #64748b;
  font-family: monospace;
  flex-wrap: wrap;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}"""
        },
        {
            "name": "Footer",
            "instruction": "fund footer with New York office, custodian references, and statutory copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified institutional contact details.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="apex-footer" id="footer" role="contentinfo">
      <div className="apex-footer__inner">
        <div className="apex-footer__brand">
          <span className="apex-footer__logo">◈ Apex Quantitative Fund LP</span>
          <p className="apex-footer__copy">
            Systematic global macro and quantitative equity hedge fund manager registered with the U.S. Securities and Exchange Commission.
          </p>
        </div>
        <address className="apex-footer__contact">
          <p className="apex-footer__h">Headquarters</p>
          <p>590 Madison Avenue, 38th Floor</p>
          <p>New York, NY 10022</p>
          <p><a href="tel:+12125550144">+1 (212) 555-0144</a> · <a href="mailto:ir@apexquantfund.com">ir@apexquantfund.com</a></p>
        </address>
      </div>
      <div className="apex-footer__bottom">
        <p>© {new Date().getFullYear()} Apex Quantitative Fund Management LP. All rights reserved.</p>
      </div>
    </footer>
  );
}""",
            "css": """.apex-footer {
  background: #030508;
  padding: 4rem 1.5rem 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  color: #64748b;
}
.apex-footer__inner {
  max-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 3rem;
  margin-bottom: 2.5rem;
}
.apex-footer__logo { font-size: 1.1rem; color: #f8fafc; font-weight: 700; display: block; margin-bottom: 0.5rem; }
.apex-footer__copy { font-size: 0.8125rem; line-height: 1.6; max-width: 440px; }
.apex-footer__contact { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.apex-footer__h { font-size: 0.75rem; text-transform: uppercase; color: #f8fafc; margin: 0 0 0.5rem; font-weight: 700; }
.apex-footer__contact a { color: #3b82f6; text-decoration: none; }
.apex-footer__bottom { max-width: 1000px; margin: 0 auto; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; text-align: center; font-size: 0.75rem; }
@media (max-width: 700px) { .apex-footer__inner { grid-template-columns: 1fr; } }"""
        }
    ]
    trajs.append(make_traj("site_fintech_tabs_apex_alpha", t2_brief, t2_sections))

    # ==============================================================================
    # 3. Fintech x Split-Hero: Veritas Global Custody
    # ==============================================================================
    t3_brief = """<content_brief>
  <business_name>Veritas Global Custody</business_name>
  <tagline>Tier-1 Qualified Custody & Cryptographic Cold Vault Settlement</tagline>
  <business_type>fintech</business_type>
  <layout_archetype>split_hero</layout_archetype>
  <layout_guidelines>Split hero architecture: dual-column viewport banner with custody charter on left and real-time MPC vault telemetry on right, followed by bankruptcy-remote legal tiers and Lloyd's of London crime insurance disclosures.</layout_guidelines>
  <sections>header, hero, custody_tiers, insurance_disclosures, footer</sections>
  <contact>
    <address>200 West Street, 19th Floor, New York, NY 10282</address>
    <phone>+1 (212) 555-0188</phone>
    <email>vault@veritascustody.com</email>
    <hours>Mon–Fri: 24/7 Institutional Desk</hours>
  </contact>
</content_brief>"""

    t3_sections = [
        {
            "name": "Header",
            "instruction": "vault custody header with Lloyd's insurance status and institutional login. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building custody header for Veritas with insurance pill and clean brand logo.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="veritas-header" role="banner">
      <div className="veritas-header__inner">
        <a href="#hero" className="veritas-header__brand" aria-label="Veritas Global Custody Home">
          <span className="veritas-header__shield">🛡</span> VERITAS CUSTODY
        </a>
        <div className="veritas-header__insurance">
          <span className="veritas-header__dot" aria-hidden="true" />
          <span>$500M Specie Insurance · Lloyd's Policy #LL-948201</span>
        </div>
        <a href="#insurance" className="veritas-header__cta">Verify Reserves</a>
      </div>
    </header>
  );
}""",
            "css": """.veritas-header {
  background: #090d14;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1rem 1.5rem;
  position: sticky;
  top: 0;
  z-index: 100;
}
.veritas-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.veritas-header__brand {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #f8fafc;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.veritas-header__shield { color: #6366f1; }
.veritas-header__insurance {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.1);
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  border: 1px solid rgba(99, 102, 241, 0.25);
}
.veritas-header__dot { width: 6px; height: 6px; background: #6366f1; border-radius: 50%; }
.veritas-header__cta {
  background: #6366f1;
  color: #ffffff;
  padding: 0.45rem 1.1rem;
  font-size: 0.8125rem;
  font-weight: 600;
  border-radius: 6px;
  text-decoration: none;
}
@media (max-width: 768px) { .veritas-header__insurance { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "split hero layout with charter on left and real-time MPC cold vault telemetry on right. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Split Hero for Veritas with side-by-side custody charter and live cryptographic telemetry.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="veritas-hero" id="hero" aria-label="Qualified Custody Overview">
      <div className="veritas-hero__inner">
        <div className="veritas-hero__content">
          <div className="veritas-hero__tier-tag">SEC Rule 206(4)-2 Qualified Custodian</div>
          <h1 className="veritas-hero__title">
            Institutional Cold Vault Custody with Bankruptcy-Remote Legal Segregation
          </h1>
          <p className="veritas-hero__desc">
            Direct segregated asset ownership. Your balances are never pooled or lent. Verified continuous cryptographic proof of reserves for family offices and asset managers.
          </p>
          <div className="veritas-hero__actions">
            <a href="#custody-tiers" className="veritas-hero__btn-primary">View Custody Architecture</a>
            <a href="#insurance" className="veritas-hero__btn-secondary">Audit & Disclosures</a>
          </div>
        </div>

        <div className="veritas-hero__vault-telemetry" role="region" aria-label="Live Vault Telemetry">
          <div className="veritas-hero__vault-header">
            <span className="veritas-hero__vault-status">● HSM Enclaves Online</span>
            <span className="veritas-hero__vault-time">FIPS 140-2 Level 3</span>
          </div>
          <div className="veritas-hero__stat-row">
            <div>
              <span className="veritas-hero__stat-num">$8.4B</span>
              <span className="veritas-hero__stat-lbl">Total Assets Under Custody</span>
            </div>
            <div>
              <span className="veritas-hero__stat-num">100%</span>
              <span className="veritas-hero__stat-lbl">Air-Gapped Cold Storage</span>
            </div>
          </div>
          <div className="veritas-hero__vault-footer">
            <span>SOC 1 Type II & SOC 2 Type II Certified by EY</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.veritas-hero {
  padding: 5rem 1.5rem;
  background: #090d14;
}
.veritas-hero__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 4rem;
  align-items: center;
}
.veritas-hero__tier-tag {
  font-size: 0.8125rem;
  color: #818cf8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  margin-bottom: 1rem;
}
.veritas-hero__title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: clamp(2.2rem, 4vw, 3.4rem);
  font-weight: 800;
  color: #f8fafc;
  line-height: 1.2;
  margin: 0 0 1.25rem;
}
.veritas-hero__desc { font-size: 1.05rem; color: #94a3b8; line-height: 1.65; margin: 0 0 2.5rem; }
.veritas-hero__actions { display: flex; gap: 1rem; flex-wrap: wrap; }
.veritas-hero__btn-primary {
  background: #6366f1;
  color: #ffffff;
  padding: 0.85rem 1.75rem;
  font-weight: 600;
  border-radius: 6px;
  text-decoration: none;
}
.veritas-hero__btn-secondary {
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f8fafc;
  padding: 0.85rem 1.75rem;
  font-weight: 600;
  border-radius: 6px;
  text-decoration: none;
}
.veritas-hero__vault-telemetry {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
}
.veritas-hero__vault-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #10b981;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 1.5rem;
}
.veritas-hero__vault-time { color: #64748b; font-family: monospace; }
.veritas-hero__stat-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
.veritas-hero__stat-num { font-size: 2rem; font-weight: 800; color: #f8fafc; display: block; }
.veritas-hero__stat-lbl { font-size: 0.75rem; color: #94a3b8; }
.veritas-hero__vault-footer {
  font-size: 0.75rem;
  color: #a5b4fc;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
@media (max-width: 900px) { .veritas-hero__inner { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "CustodyTiers",
            "instruction": "three structured custody tiers detailing Air-Gapped Cold Storage, MPC Treasury, and Escrow Settlement. Files: src/components/CustodyTiers.tsx + src/components/CustodyTiers.css",
            "tsx_path": "src/components/CustodyTiers.tsx",
            "css_path": "src/components/CustodyTiers.css",
            "thought": "Building structured custody tiers with hardware isolation details.",
            "tsx": """import React from 'react';
import './CustodyTiers.css';

export function CustodyTiers() {
  return (
    <section className="veritas-tiers" id="custody-tiers" aria-labelledby="veritas-tiers-title">
      <div className="veritas-tiers__inner">
        <header className="veritas-tiers__header">
          <p className="veritas-tiers__eyebrow">Institutional Vaulting</p>
          <h2 id="veritas-tiers-title" className="veritas-tiers__title">Custody Architecture & Tiers</h2>
        </header>

        <div className="veritas-tiers__grid">
          <div className="veritas-tiers__card">
            <span className="veritas-tiers__card-tier">Tier 1</span>
            <h3 className="veritas-tiers__card-title">Air-Gapped Deep Cold Storage</h3>
            <p className="veritas-tiers__card-desc">
              Physical Swiss underground nuclear bunker vaults. 4-of-7 geographical key ceremony required for egress.
            </p>
            <ul className="veritas-tiers__list">
              <li>SLA: 24-Hour Settlement</li>
              <li>Underwritten Lloyd's Specie Policy</li>
              <li>Quarterly Big-4 Proof of Reserves</li>
            </ul>
          </div>

          <div className="veritas-tiers__card veritas-tiers__card--accent">
            <span className="veritas-tiers__card-tier">Tier 2</span>
            <h3 className="veritas-tiers__card-title">MPC Warm Treasury Operations</h3>
            <p className="veritas-tiers__card-desc">
              Multi-Party Computation key shares with quorum-based automated consensus for active institutional treasury movements.
            </p>
            <ul className="veritas-tiers__list">
              <li>SLA: 15-Minute Broadcast</li>
              <li>Hardware Biometric Approvals</li>
              <li>Configurable Daily Velocity Limits</li>
            </ul>
          </div>

          <div className="veritas-tiers__card">
            <span className="veritas-tiers__card-tier">Tier 3</span>
            <h3 className="veritas-tiers__card-title">Tri-Party Collateral Escrow</h3>
            <p className="veritas-tiers__card-desc">
              Independent custody verification for prime brokerage financing, bilateral OTC lending, and derivatives margin.
            </p>
            <ul className="veritas-tiers__list">
              <li>SLA: Atomic Real-Time DvP</li>
              <li>Automated Rehypothecation Lock</li>
              <li>Legal Title in Client Name</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.veritas-tiers {
  padding: 6rem 1.5rem;
  background: #06090e;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.veritas-tiers__inner { max-width: 1200px; margin: 0 auto; }
.veritas-tiers__header { text-align: center; margin-bottom: 3.5rem; }
.veritas-tiers__eyebrow { font-size: 0.8125rem; color: #818cf8; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 0.5rem; }
.veritas-tiers__title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2.4rem; color: #f8fafc; margin: 0; }
.veritas-tiers__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.75rem;
}
.veritas-tiers__card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 2.25rem;
  display: flex;
  flex-direction: column;
}
.veritas-tiers__card--accent {
  border-color: rgba(99, 102, 241, 0.4);
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, rgba(15, 23, 42, 0.8) 100%);
}
.veritas-tiers__card-tier { font-size: 0.75rem; color: #818cf8; font-weight: 700; text-transform: uppercase; margin-bottom: 0.5rem; }
.veritas-tiers__card-title { font-size: 1.25rem; color: #f8fafc; margin: 0 0 1rem; }
.veritas-tiers__card-desc { font-size: 0.9375rem; color: #94a3b8; line-height: 1.6; margin-bottom: 1.5rem; flex-grow: 1; }
.veritas-tiers__list { list-style: none; padding: 0; margin: 0; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 1rem; }
.veritas-tiers__list li { font-size: 0.8125rem; color: #cbd5e1; padding: 0.35rem 0; }
@media (max-width: 900px) { .veritas-tiers__grid { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "InsuranceDisclosures",
            "instruction": "structured trust section detailing Lloyd's of London crime insurance policy #LL-948201 and bankruptcy-remote legal mandate. Files: src/components/InsuranceDisclosures.tsx + src/components/InsuranceDisclosures.css",
            "tsx_path": "src/components/InsuranceDisclosures.tsx",
            "css_path": "src/components/InsuranceDisclosures.css",
            "thought": "Building institutional disclosures with Lloyd's of London policy details.",
            "tsx": """import React from 'react';
import './InsuranceDisclosures.css';

export function InsuranceDisclosures() {
  return (
    <aside className="veritas-disclosures" id="insurance" role="complementary" aria-label="Insurance & Regulatory Protections">
      <div className="veritas-disclosures__inner">
        <div className="veritas-disclosures__box">
          <div className="veritas-disclosures__meta">
            <span className="veritas-disclosures__badge">LLOYD'S SYNDICATE SPECIE COVERAGE</span>
            <span className="veritas-disclosures__policy">Policy #LL-948201 · Underwritten through Arch & Canopius</span>
          </div>
          <h4 className="veritas-disclosures__title">$500,000,000 Institutional Crime & Physical Specie Insurance</h4>
          <p className="veritas-disclosures__p">
            Veritas maintains comprehensive coverage against employee theft, computer fraud, physical vault intrusion, and transit damage underwritten by Lloyd's of London syndicates. Assets are held in designated bankruptcy-remote special purpose trusts (SPVs) and are legally insulated from Veritas Global Custody corporate liabilities pursuant to SEC Rule 206(4)-2.
          </p>
        </div>
      </div>
    </aside>
  );
}""",
            "css": """.veritas-disclosures {
  padding: 4rem 1.5rem;
  background: #04070c;
  border-top: 1px solid rgba(99, 102, 241, 0.2);
}
.veritas-disclosures__inner { max-width: 1200px; margin: 0 auto; }
.veritas-disclosures__box {
  background: rgba(99, 102, 241, 0.04);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  padding: 2rem;
}
.veritas-disclosures__meta { display: flex; justify-content: space-between; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem; }
.veritas-disclosures__badge { font-size: 0.75rem; font-family: monospace; color: #818cf8; font-weight: 700; }
.veritas-disclosures__policy { font-size: 0.75rem; font-family: monospace; color: #64748b; }
.veritas-disclosures__title { font-size: 1.15rem; color: #f8fafc; margin: 0 0 0.75rem; }
.veritas-disclosures__p { font-size: 0.875rem; color: #94a3b8; line-height: 1.7; margin: 0; }"""
        },
        {
            "name": "Footer",
            "instruction": "institutional footer with 200 West Street address and regulatory legal notices. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified regulatory address and legal copyright.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="veritas-footer" id="footer" role="contentinfo">
      <div className="veritas-footer__inner">
        <div>
          <span className="veritas-footer__logo">🛡 Veritas Global Custody Trust Company</span>
          <p className="veritas-footer__desc">
            Chartered special-purpose trust company providing Tier-1 qualified custody under state banking department supervision.
          </p>
        </div>
        <address className="veritas-footer__addr">
          <p className="veritas-footer__h">Executive Office</p>
          <p>200 West Street, 19th Floor</p>
          <p>New York, NY 10282</p>
          <p><a href="tel:+12125550188">+1 (212) 555-0188</a> · <a href="mailto:vault@veritascustody.com">vault@veritascustody.com</a></p>
        </address>
      </div>
      <div className="veritas-footer__bottom">
        <p>© {new Date().getFullYear()} Veritas Global Custody Trust Company. All rights reserved.</p>
      </div>
    </footer>
  );
}""",
            "css": """.veritas-footer {
  background: #030509;
  padding: 4rem 1.5rem 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  color: #64748b;
}
.veritas-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 3rem;
  margin-bottom: 2.5rem;
}
.veritas-footer__logo { font-size: 1.1rem; color: #f8fafc; font-weight: 700; display: block; margin-bottom: 0.5rem; }
.veritas-footer__desc { font-size: 0.8125rem; line-height: 1.6; max-width: 480px; }
.veritas-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.veritas-footer__h { font-size: 0.75rem; text-transform: uppercase; color: #f8fafc; margin: 0 0 0.5rem; font-weight: 700; }
.veritas-footer__addr a { color: #6366f1; text-decoration: none; }
.veritas-footer__bottom { max-width: 1200px; margin: 0 auto; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; font-size: 0.75rem; }
@media (max-width: 768px) { .veritas-footer__inner { grid-template-columns: 1fr; } }"""
        }
    ]
    trajs.append(make_traj("site_fintech_splithero_veritas", t3_brief, t3_sections))

    return trajs
