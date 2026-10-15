"""
data_pipeline/rebalanced_legal.py

Hand-authored full-site trajectories for Legal across Editorial, Bento, and Split-Hero archetypes
with rich structural trust-tier features (State Bar numbers, ethics notices, jurisdictional disclaimers).
"""

from build_rebalanced_dataset import make_traj

def get_legal_trajectories():
    trajs = []

    # ==============================================================================
    # 1. Legal x Editorial: Vance & Sterling LLP
    # ==============================================================================
    t1_brief = """<content_brief>
  <business_name>Vance & Sterling LLP</business_name>
  <tagline>Trial Counsel for High-Stakes Patent Defense & Complex Commercial Disputes</tagline>
  <business_type>legal</business_type>
  <layout_archetype>editorial</layout_archetype>
  <layout_guidelines>Editorial magazine legal architecture: high-contrast serif headlines, masthead volume and date header, asymmetric pull-quote, multi-column narrative prose with dropcap, followed by State Bar #294819 ethics disclosures.</layout_guidelines>
  <sections>header, hero, practice_monographs, ethics_disclosures, footer</sections>
  <contact>
    <address>555 California Street, Suite 3200, San Francisco, CA 94104</address>
    <phone>+1 (415) 555-0199</phone>
    <email>intake@vancesterling.com</email>
    <hours>Mon–Fri: 8am–6:30pm PST</hours>
  </contact>
</content_brief>"""

    t1_sections = [
        {
            "name": "Header",
            "instruction": "sticky legal header with firm wordmark, practice navigation, and 'Consultation' button. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header for Vance & Sterling with dark editorial law firm styling.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="vs-header" role="banner">
      <div className="vs-header__inner">
        <a href="#hero" className="vs-header__logo" aria-label="Vance and Sterling LLP Home">
          VANCE & STERLING <span className="vs-header__sub">LLP</span>
        </a>
        <nav className="vs-header__nav" aria-label="Main Navigation">
          <a href="#practices" className="vs-header__link">Practice Monographs</a>
          <a href="#ethics" className="vs-header__link">Bar Admissions & Ethics</a>
          <a href="#footer" className="vs-header__link">Contact</a>
        </nav>
        <a href="#ethics" className="vs-header__cta">Schedule Consultation</a>
      </div>
    </header>
  );
}""",
            "css": """.vs-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #0d131f;
  border-bottom: 1px solid rgba(197, 160, 89, 0.25);
  padding: 1.15rem 2rem;
}
.vs-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.vs-header__logo {
  font-family: 'Cinzel', serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #f8fafc;
  text-decoration: none;
  letter-spacing: 0.06em;
}
.vs-header__sub { font-size: 0.75rem; color: #c5a059; font-family: 'Inter', sans-serif; }
.vs-header__nav { display: flex; gap: 2rem; }
.vs-header__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.2s;
}
.vs-header__link:hover { color: #c5a059; }
.vs-header__cta {
  background: #c5a059;
  color: #0c1524;
  font-weight: 700;
  font-size: 0.8125rem;
  padding: 0.5rem 1.25rem;
  border-radius: 4px;
  text-decoration: none;
  letter-spacing: 0.04em;
}
@media (max-width: 768px) { .vs-header__nav { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "editorial legal hero banner with masthead date rule, high-contrast serif headline, and federal court jury verdict metrics. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero for Vance & Sterling with editorial typography and federal docket track record.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="vs-hero" id="hero" aria-label="Firm Overview">
      <div className="vs-hero__inner">
        <div className="vs-hero__masthead">
          <span>VOL. XXXIV · TRIAL BRIEF DISPATCH</span>
          <span>FEDERAL FIRST-CHAIR TRIAL COUNSEL</span>
        </div>
        <hr className="vs-hero__rule" />
        <h1 className="vs-hero__title">
          Trial Counsel for High-Stakes Patent Defense & Complex Commercial Disputes
        </h1>
        <p className="vs-hero__desc">
          Defending market-defining technologies in federal district courts, the International Trade Commission (ITC), and the Court of Appeals for the Federal Circuit.
        </p>
        <div className="vs-hero__verdicts">
          <div className="vs-hero__v-item">
            <span className="vs-hero__v-num">$2.4B+</span>
            <span className="vs-hero__v-lbl">Defense Claims Defeated</span>
          </div>
          <div className="vs-hero__v-item">
            <span className="vs-hero__v-num">84%</span>
            <span className="vs-hero__v-lbl">Pre-Trial Summary Judgments</span>
          </div>
          <div className="vs-hero__v-item">
            <span className="vs-hero__v-num">100%</span>
            <span className="vs-hero__v-lbl">Partner Trial Attention</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.vs-hero {
  padding: 5rem 1.5rem 4rem;
  background: #0d131f;
  color: #f8fafc;
}
.vs-hero__inner { max-width: 960px; margin: 0 auto; }
.vs-hero__masthead {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  font-family: monospace;
  color: #c5a059;
  letter-spacing: 0.12em;
  margin-bottom: 0.5rem;
}
.vs-hero__rule { border: none; border-top: 1px solid rgba(197, 160, 89, 0.35); margin: 0 0 2.5rem; }
.vs-hero__title {
  font-family: 'Cinzel', serif;
  font-size: clamp(2.3rem, 4.8vw, 3.8rem);
  font-weight: 700;
  line-height: 1.16;
  margin: 0 0 1.5rem;
  color: #f8fafc;
}
.vs-hero__desc { font-size: 1.15rem; color: #cbd5e1; line-height: 1.7; margin: 0 0 3.5rem; }
.vs-hero__verdicts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.vs-hero__v-item { display: flex; flex-direction: column; gap: 0.25rem; }
.vs-hero__v-num { font-family: 'Cinzel', serif; font-size: 2.2rem; font-weight: 700; color: #c5a059; }
.vs-hero__v-lbl { font-size: 0.8125rem; color: #94a3b8; }
@media (max-width: 600px) { .vs-hero__verdicts { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "PracticeMonographs",
            "instruction": "editorial two-column narrative prose with dropcap and monograph cards for Patent Litigation, Trade Secrets, and Appellate Advocacy. Files: src/components/PracticeMonographs.tsx + src/components/PracticeMonographs.css",
            "tsx_path": "src/components/PracticeMonographs.tsx",
            "css_path": "src/components/PracticeMonographs.css",
            "thought": "Building multi-column editorial prose and monograph cases with dropcap typography.",
            "tsx": """import React from 'react';
import './PracticeMonographs.css';

export function PracticeMonographs() {
  return (
    <section className="vs-editorial" id="practices" aria-labelledby="vs-editorial-title">
      <div className="vs-editorial__inner">
        <div className="vs-editorial__lead">
          <h2 id="vs-editorial-title" className="vs-editorial__h2">Core Trial Practices</h2>
          <blockquote className="vs-editorial__quote">
            <p>
              "Trial advocacy is not an exercise in volume. It is the surgical destruction of an adversary's theory before an empaneled jury."
            </p>
            <cite>— Vance & Sterling Litigation Review</cite>
          </blockquote>
        </div>

        <div className="vs-editorial__prose">
          <p className="vs-editorial__p vs-editorial__p--dropcap">
            Litigation in the federal courts has evolved into a war of attrition. Technical patents in machine learning, semiconductor architectures, and wireless communications are routinely litigated across multiple venues simultaneously. Our firm limits representation to a concentrated docket of high-stakes disputes where our partners stand first-chair in courtroom arguments.
          </p>
          <p className="vs-editorial__p">
            By avoiding the institutional bloat of national mega-firms, we maintain ruthless agility. From preliminary injunction hearings to post-trial motions and Federal Circuit appeals, our partners draft the briefs, depose the principal technical experts, and deliver the opening arguments to the jury.
          </p>
        </div>

        <div className="vs-editorial__cases">
          <article className="vs-case">
            <span className="vs-case__index">PRACTICE MONOGRAPH I</span>
            <h3 className="vs-case__title">Patent Infringement Defense</h3>
            <p className="vs-case__desc">
              First-chair defense of generative AI models, EDA silicon design systems, and memory controller architectures in the Northern District of California and Delaware.
            </p>
          </article>
          <article className="vs-case">
            <span className="vs-case__index">PRACTICE MONOGRAPH II</span>
            <h3 className="vs-case__title">Trade Secrets & DTSA Injunctions</h3>
            <p className="vs-case__desc">
              Emergency preliminary injunction defense under the Defend Trade Secrets Act involving executive departures, neural weights, and source code misappropriation.
            </p>
          </article>
          <article className="vs-case">
            <span className="vs-case__index">PRACTICE MONOGRAPH III</span>
            <h3 className="vs-case__title">ITC Section 337 Investigations</h3>
            <p className="vs-case__desc">
              Defending cross-border technology importers against exclusion orders before the United States International Trade Commission in Washington, D.C.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.vs-editorial {
  padding: 6rem 1.5rem;
  background: #090e18;
  color: #f8fafc;
}
.vs-editorial__inner { max-width: 1080px; margin: 0 auto; }
.vs-editorial__lead {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3.5rem;
  margin-bottom: 3.5rem;
}
.vs-editorial__h2 { font-family: 'Cinzel', serif; font-size: 2.8rem; color: #f8fafc; margin: 0; line-height: 1.15; }
.vs-editorial__quote {
  margin: 0;
  padding: 0.5rem 0 0.5rem 1.75rem;
  border-left: 2px solid #c5a059;
}
.vs-editorial__quote p { font-style: italic; font-size: 1.05rem; color: #e2e8f0; line-height: 1.6; margin: 0 0 0.5rem; }
.vs-editorial__quote cite { font-size: 0.75rem; color: #c5a059; text-transform: uppercase; letter-spacing: 0.08em; display: block; }
.vs-editorial__prose {
  column-count: 2;
  column-gap: 3.5rem;
  font-size: 1.02rem;
  line-height: 1.8;
  color: #cbd5e1;
  margin-bottom: 4rem;
  text-align: justify;
}
.vs-editorial__p { margin: 0 0 1.5rem; }
.vs-editorial__p--dropcap::first-letter {
  float: left;
  font-family: 'Cinzel', serif;
  font-size: 3.6rem;
  line-height: 0.8;
  padding-right: 0.6rem;
  padding-top: 0.2rem;
  color: #c5a059;
}
.vs-editorial__cases {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  border-top: 1px solid rgba(197, 160, 89, 0.25);
  padding-top: 3rem;
}
.vs-case {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1.75rem;
  border-radius: 4px;
}
.vs-case__index { font-size: 0.6875rem; font-family: monospace; color: #c5a059; letter-spacing: 0.1em; margin-bottom: 0.5rem; display: block; }
.vs-case__title { font-family: 'Cinzel', serif; font-size: 1.15rem; color: #f8fafc; margin: 0 0 0.75rem; }
.vs-case__desc { font-size: 0.875rem; color: #94a3b8; line-height: 1.6; margin: 0; }
@media (max-width: 800px) {
  .vs-editorial__lead { grid-template-columns: 1fr; }
  .vs-editorial__prose { column-count: 1; }
  .vs-editorial__cases { grid-template-columns: 1fr; }
}"""
        },
        {
            "name": "EthicsDisclosures",
            "instruction": "dedicated trust section with State Bar #294819 accreditation, attorney advertising disclaimer, and prior results notice. Files: src/components/EthicsDisclosures.tsx + src/components/EthicsDisclosures.css",
            "tsx_path": "src/components/EthicsDisclosures.tsx",
            "css_path": "src/components/EthicsDisclosures.css",
            "thought": "Building structured legal ethics and bar admissions disclosure block.",
            "tsx": """import React from 'react';
import './EthicsDisclosures.css';

export function EthicsDisclosures() {
  return (
    <section className="vs-ethics" id="ethics" aria-label="Bar Admissions & Ethics Notices">
      <div className="vs-ethics__inner">
        <div className="vs-ethics__bar-grid">
          <div className="vs-ethics__card">
            <span className="vs-ethics__tag">State Bar of California</span>
            <span className="vs-ethics__num">Bar #294819 · Active Fiduciary</span>
            <p className="vs-ethics__sub">Admitted to all California Courts and U.S. District Court, N.D. Cal.</p>
          </div>
          <div className="vs-ethics__card">
            <span className="vs-ethics__tag">New York State Bar Association</span>
            <span className="vs-ethics__num">Member #4819201 · S.D.N.Y. Admitted</span>
            <p className="vs-ethics__sub">Admitted to Second Circuit and Federal Circuit Courts of Appeals.</p>
          </div>
        </div>

        <div className="vs-ethics__notice" role="note">
          <h4 className="vs-ethics__notice-h">Legal Disclaimer & Attorney Advertising Notice</h4>
          <p className="vs-ethics__notice-p">
            This website constitutes Attorney Advertising under Rule 7.1 of the Rules of Professional Conduct. Prior case results, verdicts, and pre-trial settlements described herein do not guarantee, warrant, or predict a similar outcome in future legal representation. No attorney-client relationship is created by visiting this website, reviewing trial monographs, or transmitting electronic correspondence.
          </p>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.vs-ethics {
  padding: 4rem 1.5rem;
  background: #070b13;
  border-top: 1px solid rgba(197, 160, 89, 0.2);
}
.vs-ethics__inner { max-width: 1080px; margin: 0 auto; }
.vs-ethics__bar-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-bottom: 2.5rem;
}
.vs-ethics__card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(197, 160, 89, 0.3);
  border-left: 3px solid #c5a059;
  padding: 1.5rem;
  border-radius: 4px;
}
.vs-ethics__tag { font-size: 0.75rem; text-transform: uppercase; color: #c5a059; font-weight: 700; letter-spacing: 0.08em; display: block; }
.vs-ethics__num { font-size: 1.05rem; font-weight: 700; color: #f8fafc; display: block; margin: 0.25rem 0 0.5rem; font-family: monospace; }
.vs-ethics__sub { font-size: 0.8125rem; color: #94a3b8; line-height: 1.5; margin: 0; }
.vs-ethics__notice {
  background: rgba(197, 160, 89, 0.03);
  border: 1px solid rgba(197, 160, 89, 0.15);
  padding: 1.75rem;
  border-radius: 4px;
}
.vs-ethics__notice-h { font-size: 0.8125rem; text-transform: uppercase; color: #c5a059; margin: 0 0 0.5rem; font-weight: 700; }
.vs-ethics__notice-p { font-size: 0.8125rem; color: #64748b; line-height: 1.7; margin: 0; }
@media (max-width: 700px) { .vs-ethics__bar-grid { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "Footer",
            "instruction": "formal law firm footer with California St address, telephone, email, and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified law firm address and licensing notice.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="vs-footer" id="footer" role="contentinfo">
      <div className="vs-footer__inner">
        <div>
          <span className="vs-footer__logo">VANCE & STERLING LLP</span>
          <p className="vs-footer__tagline">Trial Counsel for Emerging Tech & Patent Defense</p>
        </div>
        <address className="vs-footer__addr">
          <p>555 California Street, Suite 3200</p>
          <p>San Francisco, CA 94104</p>
          <p><a href="tel:+14155550199">+1 (415) 555-0199</a> · <a href="mailto:intake@vancesterling.com">intake@vancesterling.com</a></p>
        </address>
      </div>
      <div className="vs-footer__bottom">
        <p>© {new Date().getFullYear()} Vance & Sterling LLP. All rights reserved. State Bar #294819.</p>
      </div>
    </footer>
  );
}""",
            "css": """.vs-footer {
  background: #040810;
  padding: 4rem 1.5rem 2rem;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.vs-footer__inner {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2.5rem;
  flex-wrap: wrap;
  gap: 2rem;
}
.vs-footer__logo { font-family: 'Cinzel', serif; font-size: 1.15rem; color: #f8fafc; font-weight: 700; display: block; margin-bottom: 0.25rem; }
.vs-footer__tagline { font-size: 0.8125rem; }
.vs-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.vs-footer__addr a { color: #c5a059; text-decoration: none; }
.vs-footer__bottom { max-width: 1080px; margin: 0 auto; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; text-align: center; font-size: 0.75rem; }"""
        }
    ]
    trajs.append(make_traj("site_legal_editorial_vance", t1_brief, t1_sections))

    # ==============================================================================
    # 2. Legal x Bento: CyberLex Patent Group
    # ==============================================================================
    t2_brief = """<content_brief>
  <business_name>CyberLex Patent Group</business_name>
  <tagline>Patent Prosecution for Generative AI, Robotics & Silicon Architectures</tagline>
  <business_type>legal</business_type>
  <layout_archetype>bento</layout_archetype>
  <layout_guidelines>Bento grid architecture: asymmetric spans (2x2 patent prosecution velocity card, AI copyright briefs, trade secret protection, and USPTO registered attorney credentials).</layout_guidelines>
  <sections>header, hero, ip_bento, patent_bar_credentials, footer</sections>
  <contact>
    <address>1100 K Street NW, Suite 800, Washington, DC 20005</address>
    <phone>+1 (202) 555-0177</phone>
    <email>filings@cyberlexip.com</email>
    <hours>Mon–Fri: 8:30am–6pm EST</hours>
  </contact>
</content_brief>"""

    t2_sections = [
        {
            "name": "Header",
            "instruction": "modern IP law header with USPTO registration indicator and patent audit CTA. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header for CyberLex with USPTO indicator.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="cl-header" role="banner">
      <div className="cl-header__inner">
        <a href="#hero" className="cl-header__logo" aria-label="CyberLex Patent Group Home">
          <span className="cl-header__icon">§</span> CYBERLEX IP
        </a>
        <div className="cl-header__bar-reg">USPTO Registered Patent Bar #71,204</div>
        <a href="#credentials" className="cl-header__btn">Patent Portfolio Audit</a>
      </div>
    </header>
  );
}""",
            "css": """.cl-header {
  background: #080f1e;
  border-bottom: 1px solid rgba(56, 189, 248, 0.2);
  padding: 1rem 1.5rem;
}
.cl-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cl-header__logo { font-family: 'Space Grotesk', sans-serif; font-size: 1.2rem; font-weight: 700; color: #f8fafc; text-decoration: none; display: flex; align-items: center; gap: 0.5rem; }
.cl-header__icon { color: #38bdf8; }
.cl-header__bar-reg { font-size: 0.75rem; color: #94a3b8; font-family: monospace; background: rgba(56, 189, 248, 0.08); padding: 0.35rem 0.85rem; border-radius: 4px; }
.cl-header__btn { background: #38bdf8; color: #04101e; font-weight: 700; font-size: 0.8125rem; padding: 0.45rem 1.1rem; border-radius: 4px; text-decoration: none; }
@media (max-width: 768px) { .cl-header__bar-reg { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "tech-forward legal hero with docket statistics and USPTO grant velocity metrics. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero for CyberLex with patent docket velocity.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="cl-hero" id="hero" aria-label="IP Practice Overview">
      <div className="cl-hero__inner">
        <h1 className="cl-hero__title">
          Patent Prosecution for Generative AI, Robotics & Silicon Architectures
        </h1>
        <p className="cl-hero__desc">
          Crafting defensible global patent claims for foundation models, custom ASICs, and autonomous multi-agent software systems before the USPTO and EPO.
        </p>
        <div className="cl-hero__stats">
          <div className="cl-hero__stat">
            <span className="cl-hero__stat-num">98.2%</span>
            <span className="cl-hero__stat-lbl">USPTO First-Action Allowance Rate</span>
          </div>
          <div className="cl-hero__stat">
            <span className="cl-hero__stat-num">1,400+</span>
            <span className="cl-hero__stat-lbl">Granted AI & Hardware Patents</span>
          </div>
          <div className="cl-hero__stat">
            <span className="cl-hero__stat-num">14 Mo</span>
            <span className="cl-hero__stat-lbl">Avg. Track One Grant Velocity</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.cl-hero {
  padding: 5rem 1.5rem 4rem;
  background: radial-gradient(circle at 50% 10%, rgba(56, 189, 248, 0.08) 0%, #080f1e 80%);
  color: #f8fafc;
  text-align: center;
}
.cl-hero__inner { max-width: 960px; margin: 0 auto; }
.cl-hero__title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(2.2rem, 4.5vw, 3.6rem);
  font-weight: 800;
  line-height: 1.18;
  margin: 0 0 1.25rem;
}
.cl-hero__desc { font-size: 1.15rem; color: #94a3b8; line-height: 1.65; margin: 0 0 3rem; }
.cl-hero__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.cl-hero__stat { display: flex; flex-direction: column; gap: 0.25rem; }
.cl-hero__stat-num { font-size: 2.1rem; font-weight: 800; color: #38bdf8; }
.cl-hero__stat-lbl { font-size: 0.8125rem; color: #64748b; }
@media (max-width: 600px) { .cl-hero__stats { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "IPBento",
            "instruction": "heterogeneous Bento grid for patent prosecution, AI trade secrets, licensing, and portfolio defense. Files: src/components/IPBento.tsx + src/components/IPBento.css",
            "tsx_path": "src/components/IPBento.tsx",
            "css_path": "src/components/IPBento.css",
            "thought": "Building Bento Grid with 2x2 featured AI patent prosecution card.",
            "tsx": """import React from 'react';
import './IPBento.css';

export function IPBento() {
  return (
    <section className="cl-bento" id="ip-bento" aria-labelledby="cl-bento-title">
      <div className="cl-bento__inner">
        <header className="cl-bento__header">
          <p className="cl-bento__eyebrow">Patent Portfolio Strategy</p>
          <h2 id="cl-bento-title" className="cl-bento__title">Intellectual Property Bento</h2>
        </header>

        <div className="cl-bento__grid">
          <article className="cl-card cl-card--featured">
            <span className="cl-card__tag">Primary Practice</span>
            <h3 className="cl-card__title">Generative AI Patent Portfolio Architecture</h3>
            <p className="cl-card__desc">
              Drafting Section 101-resilient patent specifications for transformer attention routing, mixture-of-experts scheduling, synthetic training data synthesis, and RLHF alignment engines.
            </p>
            <div className="cl-card__badges">
              <span>Section 101 Resilient</span>
              <span>USPTO Track One</span>
              <span>Prior Art Fortress</span>
            </div>
          </article>

          <article className="cl-card">
            <span className="cl-card__tag">Hardware IP</span>
            <h3 className="cl-card__title">Semiconductor & Optical Compute</h3>
            <p className="cl-card__desc">
              Silicon photonics, neuromorphic crossbars, and systolic array interconnect claims.
            </p>
          </article>

          <article className="cl-card">
            <span className="cl-card__tag">Trade Secrets</span>
            <h3 className="cl-card__title">Weight Encryption Protocols</h3>
            <p className="cl-card__desc">
              DTSA-compliant governance for foundation model weights and fine-tuning datasets.
            </p>
          </article>

          <article className="cl-card cl-card--wide">
            <span className="cl-card__tag">Cross-Border Prosecution</span>
            <h3 className="cl-card__title">PCT International Patent Filings</h3>
            <p className="cl-card__desc">
              Simultaneous European Patent Office (EPO) and Japan Patent Office (JPO) national stage entries with uniform claim scopes.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.cl-bento {
  padding: 6rem 1.5rem;
  background: #060b16;
}
.cl-bento__inner { max-width: 1200px; margin: 0 auto; }
.cl-bento__header { text-align: center; margin-bottom: 3.5rem; }
.cl-bento__eyebrow { font-size: 0.8125rem; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 0.5rem; }
.cl-bento__title { font-family: 'Space Grotesk', sans-serif; font-size: 2.4rem; color: #f8fafc; margin: 0; }
.cl-bento__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}
.cl-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
}
.cl-card--featured {
  grid-column: span 2;
  grid-row: span 2;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(15, 23, 42, 0.8) 100%);
  border-color: rgba(56, 189, 248, 0.3);
}
.cl-card--wide { grid-column: span 3; }
.cl-card__tag { font-size: 0.75rem; color: #38bdf8; font-weight: 700; text-transform: uppercase; margin-bottom: 0.75rem; }
.cl-card__title { font-size: 1.35rem; color: #f8fafc; margin: 0 0 0.75rem; }
.cl-card__desc { font-size: 0.9375rem; color: #94a3b8; line-height: 1.6; margin-bottom: 1.5rem; flex-grow: 1; }
.cl-card__badges { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.cl-card__badges span { background: rgba(56, 189, 248, 0.12); color: #7dd3fc; font-size: 0.75rem; padding: 0.25rem 0.65rem; border-radius: 4px; font-weight: 600; }
@media (max-width: 900px) {
  .cl-bento__grid { grid-template-columns: 1fr; }
  .cl-card--featured, .cl-card--wide { grid-column: span 1; grid-row: span 1; }
}"""
        },
        {
            "name": "PatentBarCredentials",
            "instruction": "trust section detailing USPTO Registered Patent Bar #71,204 credentials, conflicts checking protocol, and ethics callouts. Files: src/components/PatentBarCredentials.tsx + src/components/PatentBarCredentials.css",
            "tsx_path": "src/components/PatentBarCredentials.tsx",
            "css_path": "src/components/PatentBarCredentials.css",
            "thought": "Building USPTO registered credentials and conflicts disclosure block.",
            "tsx": """import React from 'react';
import './PatentBarCredentials.css';

export function PatentBarCredentials() {
  return (
    <aside className="cl-credentials" id="credentials" role="complementary" aria-label="Patent Bar Credentials">
      <div className="cl-credentials__inner">
        <div className="cl-credentials__badge">
          <span className="cl-credentials__seal">USPTO REGISTRATION</span>
          <span className="cl-credentials__id">Patent Bar #71,204 · Registered Practitioners</span>
          <p className="cl-credentials__p">
            All drafting attorneys hold degrees in Electrical Engineering, Computer Science, or Physics and are licensed before the United States Patent and Trademark Office.
          </p>
        </div>
        <div className="cl-credentials__ethics" role="note">
          <span className="cl-credentials__ethics-title">Conflicts Checking Protocol</span>
          <p className="cl-credentials__ethics-body">
            Patent prosecution requires strict conflict clearing. Submitting invention disclosures or provisional drafts through electronic portals does not establish attorney-client privilege.
          </p>
        </div>
      </div>
    </aside>
  );
}""",
            "css": """.cl-credentials {
  padding: 4rem 1.5rem;
  background: #040812;
  border-top: 1px solid rgba(56, 189, 248, 0.2);
}
.cl-credentials__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 2rem;
}
.cl-credentials__badge {
  background: rgba(56, 189, 248, 0.04);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-left: 3px solid #38bdf8;
  padding: 1.75rem;
  border-radius: 6px;
}
.cl-credentials__seal { font-size: 0.75rem; font-family: monospace; color: #38bdf8; letter-spacing: 0.08em; display: block; margin-bottom: 0.25rem; font-weight: 700; }
.cl-credentials__id { font-size: 1.15rem; font-weight: 700; color: #f8fafc; display: block; margin-bottom: 0.5rem; }
.cl-credentials__p { font-size: 0.875rem; color: #94a3b8; line-height: 1.6; margin: 0; }
.cl-credentials__ethics {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1.75rem;
  border-radius: 6px;
}
.cl-credentials__ethics-title { font-size: 0.8125rem; color: #cbd5e1; text-transform: uppercase; font-weight: 700; display: block; margin-bottom: 0.5rem; }
.cl-credentials__ethics-body { font-size: 0.8125rem; color: #64748b; line-height: 1.6; margin: 0; }
@media (max-width: 768px) { .cl-credentials__inner { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "Footer",
            "instruction": "IP firm footer with Washington D.C. office and regulatory legal copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified Washington DC address.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="cl-footer" id="footer" role="contentinfo">
      <div className="cl-footer__inner">
        <div>
          <span className="cl-footer__logo">§ CyberLex Patent Group PLLC</span>
          <p className="cl-footer__desc">Patent Prosecution, Invalidation Defense & Federal Circuit Appeals.</p>
        </div>
        <address className="cl-footer__addr">
          <p>1100 K Street NW, Suite 800</p>
          <p>Washington, DC 20005</p>
          <p><a href="tel:+12025550177">+1 (202) 555-0177</a> · <a href="mailto:filings@cyberlexip.com">filings@cyberlexip.com</a></p>
        </address>
      </div>
      <div className="cl-footer__bottom">
        <p>© {new Date().getFullYear()} CyberLex Patent Group PLLC. Registered Patent Attorneys USPTO #71,204.</p>
      </div>
    </footer>
  );
}""",
            "css": """.cl-footer {
  background: #02050b;
  padding: 4rem 1.5rem 2rem;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.cl-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 3rem;
  margin-bottom: 2.5rem;
}
.cl-footer__logo { font-size: 1.1rem; color: #f8fafc; font-weight: 700; display: block; margin-bottom: 0.25rem; }
.cl-footer__desc { font-size: 0.8125rem; }
.cl-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.cl-footer__addr a { color: #38bdf8; text-decoration: none; }
.cl-footer__bottom { max-width: 1200px; margin: 0 auto; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; font-size: 0.75rem; }
@media (max-width: 700px) { .cl-footer__inner { grid-template-columns: 1fr; } }"""
        }
    ]
    trajs.append(make_traj("site_legal_bento_cyberlex", t2_brief, t2_sections))

    # ==============================================================================
    # 3. Legal x Split-Hero: Sovereign Fiduciary Counsel
    # ==============================================================================
    t3_brief = """<content_brief>
  <business_name>Sovereign Fiduciary Counsel</business_name>
  <tagline>Generational Wealth Governance, Dynastic Trusts & Estate Counsel</tagline>
  <business_type>legal</business_type>
  <layout_archetype>split_hero</layout_archetype>
  <layout_guidelines>Split-hero architecture: fiduciary mandate on left and dynastic estate metrics on right, followed by a chronological governance timeline and SEC RIA Registry #801-92841 disclosures.</layout_guidelines>
  <sections>header, hero, fiduciary_timeline, regulatory_charter, footer</sections>
  <contact>
    <address>100 Crescent Court, Suite 1400, Dallas, TX 75201</address>
    <phone>+1 (214) 555-0163</phone>
    <email>fiduciary@sovereigncounsel.com</email>
    <hours>Mon–Fri: 8am–5pm CST</hours>
  </contact>
</content_brief>"""

    t3_sections = [
        {
            "name": "Header",
            "instruction": "fiduciary counsel header with certified estate specialist seal. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header for Sovereign Fiduciary Counsel.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="sfc-header" role="banner">
      <div className="sfc-header__inner">
        <a href="#hero" className="sfc-header__logo" aria-label="Sovereign Fiduciary Counsel Home">
          SOVEREIGN <span className="sfc-header__sub">FIDUCIARY COUNSEL</span>
        </a>
        <div className="sfc-header__fiduciary-seal">
          <span>⚖ Certified Trust & Estate Specialist</span>
        </div>
        <a href="#charter" className="sfc-header__cta">Client Charter</a>
      </div>
    </header>
  );
}""",
            "css": """.sfc-header {
  background: #0e141b;
  border-bottom: 1px solid rgba(217, 119, 6, 0.25);
  padding: 1.1rem 2rem;
}
.sfc-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sfc-header__logo { font-family: 'Cinzel', serif; font-size: 1.15rem; font-weight: 700; color: #f8fafc; text-decoration: none; }
.sfc-header__sub { font-size: 0.75rem; color: #d97706; font-family: sans-serif; }
.sfc-header__fiduciary-seal { font-size: 0.75rem; color: #d97706; background: rgba(217, 119, 6, 0.1); padding: 0.35rem 0.85rem; border-radius: 4px; }
.sfc-header__cta { background: #d97706; color: #000; font-weight: 700; font-size: 0.8125rem; padding: 0.45rem 1.1rem; border-radius: 4px; text-decoration: none; }
@media (max-width: 768px) { .sfc-header__fiduciary-seal { display: none; } }"""
        },
        {
            "name": "Hero",
            "instruction": "split hero with fiduciary oath on left and generational capital stewardship metrics on right. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Split Hero for Sovereign Fiduciary Counsel.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="sfc-hero" id="hero" aria-label="Fiduciary Counsel Overview">
      <div className="sfc-hero__inner">
        <div className="sfc-hero__left">
          <span className="sfc-hero__oath-tag">Bound by Absolute Fiduciary Duty</span>
          <h1 className="sfc-hero__title">
            Generational Wealth Governance, Dynastic Trusts & Private Estate Counsel
          </h1>
          <p className="sfc-hero__desc">
            We structure multi-generational wealth vehicles designed to withstand tax code revisions, family transitions, and litigation across centuries.
          </p>
        </div>
        <div className="sfc-hero__right">
          <div className="sfc-hero__card">
            <h3 className="sfc-hero__card-title">Stewardship Metrics</h3>
            <div className="sfc-hero__stat-row">
              <div>
                <span className="sfc-hero__num">$4.2B+</span>
                <span className="sfc-hero__lbl">Trust Assets Stewarded</span>
              </div>
              <div>
                <span className="sfc-hero__num">3+</span>
                <span className="sfc-hero__lbl">Generations Advised</span>
              </div>
            </div>
            <p className="sfc-hero__notice">Zero commissions. Zero revenue-sharing. Pure fee-only counsel.</p>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.sfc-hero {
  padding: 5rem 1.5rem;
  background: #0e141b;
  color: #f8fafc;
}
.sfc-hero__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 4rem;
  align-items: center;
}
.sfc-hero__oath-tag { font-size: 0.8125rem; color: #d97706; text-transform: uppercase; font-weight: 700; letter-spacing: 0.08em; display: block; margin-bottom: 1rem; }
.sfc-hero__title { font-family: 'Cinzel', serif; font-size: clamp(2.2rem, 4vw, 3.4rem); font-weight: 700; line-height: 1.2; margin: 0 0 1.25rem; }
.sfc-hero__desc { font-size: 1.1rem; color: #94a3b8; line-height: 1.65; margin: 0; }
.sfc-hero__card { background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(217, 119, 6, 0.3); border-radius: 8px; padding: 2.25rem; }
.sfc-hero__card-title { font-family: 'Cinzel', serif; font-size: 1.25rem; color: #f8fafc; margin: 0 0 1.5rem; }
.sfc-hero__stat-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
.sfc-hero__num { font-family: 'Cinzel', serif; font-size: 2.2rem; font-weight: 700; color: #d97706; display: block; }
.sfc-hero__lbl { font-size: 0.75rem; color: #94a3b8; }
.sfc-hero__notice { font-size: 0.8125rem; color: #cbd5e1; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 1rem; margin: 0; font-style: italic; }
@media (max-width: 900px) { .sfc-hero__inner { grid-template-columns: 1fr; } }"""
        },
        {
            "name": "FiduciaryTimeline",
            "instruction": "structured timeline detailing Generation I Wealth Creation, Dynasty Trust Settlement, and Multi-Generational Transition. Files: src/components/FiduciaryTimeline.tsx + src/components/FiduciaryTimeline.css",
            "tsx_path": "src/components/FiduciaryTimeline.tsx",
            "css_path": "src/components/FiduciaryTimeline.css",
            "thought": "Building structured legal timeline for dynastic estate governance.",
            "tsx": """import React from 'react';
import './FiduciaryTimeline.css';

export function FiduciaryTimeline() {
  return (
    <section className="sfc-timeline" id="timeline" aria-labelledby="sfc-timeline-title">
      <div className="sfc-timeline__inner">
        <h2 id="sfc-timeline-title" className="sfc-timeline__title">Generational Governance Milestones</h2>
        <div className="sfc-timeline__track">
          <div className="sfc-timeline__item">
            <span className="sfc-timeline__step">STAGE 01</span>
            <h3 className="sfc-timeline__h3">Entity Structuring & Asset Protection</h3>
            <p className="sfc-timeline__p">Establishment of irrevocable trusts, family limited partnerships (FLPs), and private trust companies in top-tier jurisdictions.</p>
          </div>
          <div className="sfc-timeline__item">
            <span className="sfc-timeline__step">STAGE 02</span>
            <h3 className="sfc-timeline__h3">Dynasty Trust Settlement</h3>
            <p className="sfc-timeline__p">Perpetual generation-skipping transfer (GST) tax-exempt trusts shielding assets from estate taxation and future creditor claims.</p>
          </div>
          <div className="sfc-timeline__item">
            <span className="sfc-timeline__step">STAGE 03</span>
            <h3 className="sfc-timeline__h3">Family Constitution & Leadership</h3>
            <p className="sfc-timeline__p">Formal governance charters, next-generation trustee education, and voting protocol codification for private enterprises.</p>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.sfc-timeline {
  padding: 6rem 1.5rem;
  background: #090e14;
}
.sfc-timeline__inner { max-width: 1000px; margin: 0 auto; }
.sfc-timeline__title { font-family: 'Cinzel', serif; font-size: 2.2rem; color: #f8fafc; text-align: center; margin: 0 0 3.5rem; }
.sfc-timeline__track { display: flex; flex-direction: column; gap: 2rem; border-left: 2px solid rgba(217, 119, 6, 0.4); padding-left: 2rem; margin-left: 1rem; }
.sfc-timeline__item { position: relative; }
.sfc-timeline__item::before {
  content: '';
  position: absolute;
  left: -2.45rem;
  top: 0.3rem;
  width: 12px;
  height: 12px;
  background: #d97706;
  border-radius: 50%;
}
.sfc-timeline__step { font-size: 0.75rem; color: #d97706; font-family: monospace; font-weight: 700; display: block; margin-bottom: 0.25rem; }
.sfc-timeline__h3 { font-family: 'Cinzel', serif; font-size: 1.25rem; color: #f8fafc; margin: 0 0 0.5rem; }
.sfc-timeline__p { font-size: 0.9375rem; color: #94a3b8; line-height: 1.6; margin: 0; }"""
        },
        {
            "name": "RegulatoryCharter",
            "instruction": "dedicated trust section with fiduciary oath and SEC RIA Registry #801-92841 disclosures. Files: src/components/RegulatoryCharter.tsx + src/components/RegulatoryCharter.css",
            "tsx_path": "src/components/RegulatoryCharter.tsx",
            "css_path": "src/components/RegulatoryCharter.css",
            "thought": "Building fiduciary charter and SEC RIA disclosure section.",
            "tsx": """import React from 'react';
import './RegulatoryCharter.css';

export function RegulatoryCharter() {
  return (
    <section className="sfc-charter" id="charter" aria-label="Fiduciary Oath & Governance Disclosures">
      <div className="sfc-charter__inner">
        <div className="sfc-charter__box" role="note">
          <span className="sfc-charter__badge">FIDUCIARY STANDARD OF CARE</span>
          <h4 className="sfc-charter__title">Section 206 Investment Advisers Act of 1940 & State Bar Governance</h4>
          <p className="sfc-charter__desc">
            Sovereign Fiduciary Counsel is bound by legal oath to operate solely in the best interests of client trusts and beneficiaries. We refuse soft-dollar arrangements, brokerage commissions, referral incentives, and product distribution fees.
          </p>
          <div className="sfc-charter__meta">
            <span>SEC RIA Registry #801-92841</span>
            <span>State Bar Board Certified Specialist</span>
            <span>CRD #194821</span>
          </div>
        </div>
      </div>
    </section>
  );
}""",
            "css": """.sfc-charter {
  padding: 4rem 1.5rem;
  background: #0b1118;
  border-top: 1px solid rgba(217, 119, 6, 0.2);
}
.sfc-charter__inner { max-width: 1000px; margin: 0 auto; }
.sfc-charter__box { background: rgba(217, 119, 6, 0.03); border: 1px solid rgba(217, 119, 6, 0.25); border-left: 4px solid #d97706; padding: 2rem; border-radius: 6px; }
.sfc-charter__badge { font-size: 0.75rem; color: #d97706; font-weight: 700; letter-spacing: 0.08em; display: block; margin-bottom: 0.5rem; }
.sfc-charter__title { font-family: 'Cinzel', serif; font-size: 1.15rem; color: #f8fafc; margin: 0 0 0.75rem; }
.sfc-charter__desc { font-size: 0.875rem; color: #94a3b8; line-height: 1.65; margin: 0 0 1.25rem; }
.sfc-charter__meta { display: flex; gap: 1.5rem; font-size: 0.75rem; color: #64748b; font-family: monospace; flex-wrap: wrap; }"""
        },
        {
            "name": "Footer",
            "instruction": "executive legal footer with Dallas Crescent Court address and copyright. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building Footer with verified Texas address.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="sfc-footer" id="footer" role="contentinfo">
      <div className="sfc-footer__inner">
        <div>
          <span className="sfc-footer__logo">SOVEREIGN FIDUCIARY COUNSEL</span>
          <p className="sfc-footer__desc">Private Trust & Estate Administration for Family Offices.</p>
        </div>
        <address className="sfc-footer__addr">
          <p>100 Crescent Court, Suite 1400</p>
          <p>Dallas, TX 75201</p>
          <p><a href="tel:+12145550163">+1 (214) 555-0163</a> · <a href="mailto:fiduciary@sovereigncounsel.com">fiduciary@sovereigncounsel.com</a></p>
        </address>
      </div>
      <div className="sfc-footer__bottom">
        <p>© {new Date().getFullYear()} Sovereign Fiduciary Counsel PLLC. All rights reserved.</p>
      </div>
    </footer>
  );
}""",
            "css": """.sfc-footer {
  background: #05080c;
  padding: 4rem 1.5rem 2rem;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.sfc-footer__inner { max-width: 1000px; margin: 0 auto; display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2.5rem; flex-wrap: wrap; gap: 2rem; }
.sfc-footer__logo { font-family: 'Cinzel', serif; font-size: 1.1rem; color: #f8fafc; font-weight: 700; display: block; margin-bottom: 0.25rem; }
.sfc-footer__desc { font-size: 0.8125rem; }
.sfc-footer__addr { font-style: normal; font-size: 0.8125rem; line-height: 1.6; }
.sfc-footer__addr a { color: #d97706; text-decoration: none; }
.sfc-footer__bottom { max-width: 1000px; margin: 0 auto; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; font-size: 0.75rem; }"""
        }
    ]
    trajs.append(make_traj("site_legal_splithero_fiduciary", t3_brief, t3_sections))

    return trajs
