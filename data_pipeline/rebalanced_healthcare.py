"""
data_pipeline/rebalanced_healthcare.py

Hand-authored full-site trajectories for Healthcare across Bento, Editorial, and Tabs archetypes
with rich structural trust-tier features (Emergency 911 banner, 988 Lifeline, NPI numbers,
ABPN / FACS board certifications, CLIA ID, CARF accreditation, and HIPAA compliance).
"""

from build_rebalanced_dataset import make_traj

def get_healthcare_trajectories():
    trajs = []

    # ==============================================================================
    # 1. Healthcare x Bento: NeuroVance Comprehensive Neurology Institute
    # ==============================================================================
    t1_brief = """<content_brief>
  <business_name>NeuroVance Comprehensive Neurology Institute</business_name>
  <tagline>Pioneering Clinical Neurosciences, Epilepsy Monitoring & Cognitive Health</tagline>
  <business_type>healthcare</business_type>
  <layout_archetype>bento</layout_archetype>
  <layout_guidelines>Bento-grid clinical architecture with emergency 911 caution banner, FDA 510(k) clearance metrics, ABPN board certifications, NPI #1948201948, and CLIA laboratory certification #05D2194810.</layout_guidelines>
  <sections>emergency_banner, header, hero, bento_clinical, credentials_trust, footer</sections>
  <contact>
    <address>750 Medical Center Boulevard, Pavilion B, Suite 400, Houston, TX 77030</address>
    <phone>+1 (713) 555-0199</phone>
    <email>clinical.intake@neurovance-health.org</email>
    <hours>Mon–Fri: 7:30am–5:30pm CST | 24/7 On-Call Inpatient Neurology</hours>
  </contact>
</content_brief>"""

    t1_sections = [
        {
            "name": "EmergencyBanner",
            "instruction": "statutory medical emergency advisory with 911 triage notice and poison control hotline. Files: src/components/EmergencyBanner.tsx + src/components/EmergencyBanner.css",
            "tsx_path": "src/components/EmergencyBanner.tsx",
            "css_path": "src/components/EmergencyBanner.css",
            "thought": "Building dedicated EmergencyBanner alert component to satisfy healthcare statutory compliance guidelines.",
            "tsx": """import React from 'react';
import './EmergencyBanner.css';

export function EmergencyBanner() {
  return (
    <aside className="neuro-emergency-banner" role="alert" aria-live="assertive">
      <div className="neuro-emergency-banner__container">
        <div className="neuro-emergency-banner__badge">
          <svg className="neuro-emergency-banner__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="neuro-emergency-banner__label">MEDICAL EMERGENCY NOTICE</span>
        </div>
        <p className="neuro-emergency-banner__text">
          If you or someone you know is experiencing acute neurological distress, sudden numbness, slurred speech, or loss of consciousness, call <strong>911</strong> or visit the nearest emergency department immediately.
        </p>
        <div className="neuro-emergency-banner__helplines">
          <span className="neuro-emergency-banner__item">National Stroke Line: 1-800-787-6537</span>
          <span className="neuro-emergency-banner__divider" aria-hidden="true">•</span>
          <span className="neuro-emergency-banner__item">Poison Help: 1-800-222-1222</span>
        </div>
      </div>
    </aside>
  );
}
""",
            "css": """.neuro-emergency-banner {
  background-color: #7f1d1d;
  color: #fef2f2;
  font-size: 0.8125rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #991b1b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.neuro-emergency-banner__container {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.neuro-emergency-banner__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background-color: #991b1b;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 700;
  letter-spacing: 0.04em;
  font-size: 0.75rem;
}

.neuro-emergency-banner__icon {
  width: 14px;
  height: 14px;
  stroke: #fca5a5;
}

.neuro-emergency-banner__text {
  margin: 0;
  flex: 1;
  min-width: 280px;
  line-height: 1.4;
  color: #fee2e2;
}

.neuro-emergency-banner__text strong {
  color: #ffffff;
  text-decoration: underline;
}

.neuro-emergency-banner__helplines {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #fecaca;
}

@media (max-width: 768px) {
  .neuro-emergency-banner__helplines {
    display: none;
  }
}
"""
        },
        {
            "name": "Header",
            "instruction": "clinical header with NPI registry badge, patient portal portal access, and clinical consultation booking. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building Header with clinical accreditation metadata and secure patient login links.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="neuro-header" role="banner">
      <div className="neuro-header__container">
        <div className="neuro-header__brand-group">
          <a href="#hero" className="neuro-header__logo" aria-label="NeuroVance Institute Home">
            <div className="neuro-header__logo-mark">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="neuro-header__logo-text">
              <span className="neuro-header__name">NEUROVANCE</span>
              <span className="neuro-header__sub">CLINICAL NEUROLOGY & RESEARCH</span>
            </div>
          </a>
          <div className="neuro-header__npi-chip" title="National Provider Identifier Registry Verified">
            <span className="neuro-header__chip-dot"></span>
            NPI #1948201948 | CLIA #05D2194810
          </div>
        </div>

        <nav className="neuro-header__nav" aria-label="Primary Clinical Navigation">
          <a href="#bento" className="neuro-header__nav-link">Clinical Divisions</a>
          <a href="#credentials" className="neuro-header__nav-link">Physicians & Accreditations</a>
          <a href="#research" className="neuro-header__nav-link">Clinical Trials</a>
          <a href="#contact" className="neuro-header__nav-link">Locations</a>
        </nav>

        <div className="neuro-header__actions">
          <a href="#portal" className="neuro-header__btn-portal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            MyChart Portal
          </a>
          <a href="#referral" className="neuro-header__btn-primary">Physician Referral</a>
        </div>
      </div>
    </header>
  );
}
""",
            "css": """.neuro-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 50;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.neuro-header__container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0.85rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.neuro-header__brand-group {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.neuro-header__logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
}

.neuro-header__logo-mark {
  width: 40px;
  height: 40px;
  background-color: #0f766e;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
}

.neuro-header__logo-mark svg {
  width: 22px;
  height: 22px;
}

.neuro-header__logo-text {
  display: flex;
  flex-direction: column;
}

.neuro-header__name {
  font-size: 1.125rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.neuro-header__sub {
  font-size: 0.65rem;
  font-weight: 600;
  color: #0d9488;
  letter-spacing: 0.08em;
}

.neuro-header__npi-chip {
  background-color: #f0fdfa;
  border: 1px solid #ccfbf1;
  color: #0f766e;
  font-size: 0.7rem;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
}

.neuro-header__chip-dot {
  width: 6px;
  height: 6px;
  background-color: #14b8a6;
  border-radius: 50%;
}

.neuro-header__nav {
  display: flex;
  gap: 1.5rem;
}

.neuro-header__nav-link {
  color: #475569;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.15s ease;
}

.neuro-header__nav-link:hover {
  color: #0f766e;
}

.neuro-header__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.neuro-header__btn-portal {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.9rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  color: #334155;
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
  background-color: #f8fafc;
}

.neuro-header__btn-portal svg {
  width: 14px;
  height: 14px;
  stroke: #64748b;
}

.neuro-header__btn-primary {
  padding: 0.5rem 1.1rem;
  background-color: #0f766e;
  color: #ffffff;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
  transition: background-color 0.15s ease;
}

.neuro-header__btn-primary:hover {
  background-color: #115e59;
}

@media (max-width: 900px) {
  .neuro-header__nav, .neuro-header__npi-chip {
    display: none;
  }
}
"""
        },
        {
            "name": "Hero",
            "instruction": "academic medicine hero with patient outcome metrics, Level 4 Epilepsy accreditation, and rapid intake triage. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero section emphasizing clinical efficacy, board certified credentials, and empirical metrics.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="neuro-hero" id="hero">
      <div className="neuro-hero__container">
        <div className="neuro-hero__header">
          <div className="neuro-hero__eyebrow">
            <span className="neuro-hero__eyebrow-badge">NAEC LEVEL 4 ACCREDITED</span>
            <span className="neuro-hero__eyebrow-text">Comprehensive Epilepsy & Neurological Diagnostic Center</span>
          </div>
          <h1 className="neuro-hero__title">
            Precision Neurological Care Guided by Empirical Molecular Diagnostics.
          </h1>
          <p className="neuro-hero__lead">
            NeuroVance unites board-certified academic neurologists, neuro-intensivists, and clinical researchers to deliver patient-tailored therapies for complex epilepsy, movement disorders, cognitive impairment, and cerebrovascular pathology.
          </p>
        </div>

        <div className="neuro-hero__metrics-grid">
          <div className="neuro-hero__metric-card">
            <span className="neuro-hero__metric-num">99.2%</span>
            <span className="neuro-hero__metric-label">Diagnostic Concordance Rate</span>
            <span className="neuro-hero__metric-sub">Verified through continuous 64-channel video-EEG</span>
          </div>
          <div className="neuro-hero__metric-card">
            <span className="neuro-hero__metric-num">14 Days</span>
            <span className="neuro-hero__metric-label">Urgent Intake Wait Average</span>
            <span className="neuro-hero__metric-sub">Rapid referral triage pathway vs 92-day national avg</span>
          </div>
          <div className="neuro-hero__metric-card">
            <span className="neuro-hero__metric-num">24/7</span>
            <span className="neuro-hero__metric-label">Teleneurology Stroke On-Call</span>
            <span className="neuro-hero__metric-sub">Direct subspecialty consultation within 8 minutes</span>
          </div>
          <div className="neuro-hero__metric-card">
            <span className="neuro-hero__metric-num">38+</span>
            <span className="neuro-hero__metric-label">Active IRB Clinical Trials</span>
            <span className="neuro-hero__metric-sub">Phase II & III FDA investigational neuromodulation</span>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.neuro-hero {
  background: linear-gradient(180deg, #f0fdfa 0%, #ffffff 100%);
  padding: 4rem 1.5rem 3rem;
  border-bottom: 1px solid #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.neuro-hero__container {
  max-width: 1280px;
  margin: 0 auto;
}

.neuro-hero__header {
  max-width: 860px;
}

.neuro-hero__eyebrow {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.neuro-hero__eyebrow-badge {
  background-color: #0f766e;
  color: #ffffff;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.3rem 0.65rem;
  border-radius: 4px;
  letter-spacing: 0.05em;
}

.neuro-hero__eyebrow-text {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #0d9488;
}

.neuro-hero__title {
  font-size: 2.75rem;
  line-height: 1.15;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.03em;
  margin: 0 0 1.25rem 0;
}

.neuro-hero__lead {
  font-size: 1.125rem;
  line-height: 1.6;
  color: #334155;
  margin: 0 0 2.5rem 0;
}

.neuro-hero__metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
}

.neuro-hero__metric-card {
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-top: 3px solid #0f766e;
  border-radius: 8px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
}

.neuro-hero__metric-num {
  font-size: 2rem;
  font-weight: 800;
  color: #0f766e;
  line-height: 1;
  margin-bottom: 0.4rem;
}

.neuro-hero__metric-label {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.35rem;
}

.neuro-hero__metric-sub {
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.4;
}

@media (max-width: 960px) {
  .neuro-hero__metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .neuro-hero__title {
    font-size: 2.1rem;
  }
}

@media (max-width: 580px) {
  .neuro-hero__metrics-grid {
    grid-template-columns: 1fr;
  }
}
"""
        },
        {
            "name": "BentoClinical",
            "instruction": "bento-grid architecture for neurological subspecialties, diagnostic imaging protocols, and neuromodulation. Files: src/components/BentoClinical.tsx + src/components/BentoClinical.css",
            "tsx_path": "src/components/BentoClinical.tsx",
            "css_path": "src/components/BentoClinical.css",
            "thought": "Building BentoClinical component using authentic asymmetric grid spanning across diagnostic imaging, epilepsy monitoring, cognitive memory clinic, and movement disorders.",
            "tsx": """import React, { useState } from 'react';
import './BentoClinical.css';

interface Subspecialty {
  id: string;
  title: string;
  badge: string;
  description: string;
  protocols: string[];
  chiefPhysician: string;
  cliaVerified: boolean;
}

export function BentoClinical() {
  const [selectedDivision, setSelectedDivision] = useState<string>('epilepsy');

  const divisions: Record<string, Subspecialty> = {
    epilepsy: {
      id: 'epilepsy',
      title: 'Level 4 Comprehensive Epilepsy Monitoring Unit',
      badge: 'NAEC Certified',
      description: 'Dedicated 8-bed inpatient telemetry suite utilizing synchronized high-definition video-EEG, pre-surgical stereotactic evaluation, and responsive neurostimulation (RNS) calibration.',
      protocols: ['Continuous 128-Hz Cortical Mapping', 'FDG-PET & 3T Volumetric MRI Co-registration', 'Ketogenic Diet Metabolic Monitoring'],
      chiefPhysician: 'Dr. Elena Rostova, MD, PhD (ABPN Epilepsy Subspecialty)',
      cliaVerified: true
    },
    cognitive: {
      id: 'cognitive',
      title: 'Cognitive Neurology & Early Memory Disorders Clinic',
      badge: 'Biomarker Validated',
      description: 'Precision biomarker stratification for mild cognitive impairment, Alzheimer disease, and frontotemporal dementia leveraging CSF phosphorylated tau assays and amyloid PET.',
      protocols: ['Amyloid-Beta 42/40 Fluid Assays', 'Computerized Neurocognitive Profiling', 'Monoclonal Antibody Infusion Surveillance'],
      chiefPhysician: 'Dr. Marcus Vance, MD (ABPN Neurology, Behavioral Subspecialty)',
      cliaVerified: true
    }
  };

  const active = divisions[selectedDivision] || divisions.epilepsy;

  return (
    <section className="neuro-bento" id="bento">
      <div className="neuro-bento__container">
        <div className="neuro-bento__header">
          <span className="neuro-bento__tag">SUBSPECIALTY DIVISIONS</span>
          <h2 className="neuro-bento__heading">Asymmetric Bento Architecture of Clinical Practice</h2>
          <p className="neuro-bento__subhead">
            Each specialized division operates under stringent clinical guidelines, CLIA laboratory validation, and board-certified fellowship oversight.
          </p>
        </div>

        <div className="neuro-bento__grid">
          {/* Card 1: Wide feature card */}
          <div className="neuro-bento__card neuro-bento__card--wide">
            <div className="neuro-bento__card-header">
              <span className="neuro-bento__pill">LEAD DIVISION</span>
              <div className="neuro-bento__selector">
                <button
                  type="button"
                  className={`neuro-bento__tab-btn ${selectedDivision === 'epilepsy' ? 'is-active' : ''}`}
                  onClick={() => setSelectedDivision('epilepsy')}
                >
                  Epilepsy Unit
                </button>
                <button
                  type="button"
                  className={`neuro-bento__tab-btn ${selectedDivision === 'cognitive' ? 'is-active' : ''}`}
                  onClick={() => setSelectedDivision('cognitive')}
                >
                  Cognitive & Memory
                </button>
              </div>
            </div>

            <div className="neuro-bento__dynamic-content">
              <div className="neuro-bento__meta-row">
                <span className="neuro-bento__status-tag">{active.badge}</span>
                <span className="neuro-bento__doctor">{active.chiefPhysician}</span>
              </div>
              <h3 className="neuro-bento__card-title">{active.title}</h3>
              <p className="neuro-bento__card-desc">{active.description}</p>

              <div className="neuro-bento__protocols">
                <span className="neuro-bento__proto-title">Standard Diagnostic Protocols:</span>
                <ul className="neuro-bento__proto-list">
                  {active.protocols.map((proto, idx) => (
                    <li key={idx} className="neuro-bento__proto-item">
                      <svg viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      {proto}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Card 2: 3T MRI & High-Field Neuroimaging */}
          <div className="neuro-bento__card neuro-bento__card--medium">
            <div className="neuro-bento__card-header">
              <span className="neuro-bento__pill">3T HIGH-FIELD MRI</span>
              <span className="neuro-bento__spec">Siemens Prisma 64-Ch</span>
            </div>
            <h3 className="neuro-bento__card-title">Diffusion Tensor & Functional Neuroimaging</h3>
            <p className="neuro-bento__card-desc">
              White matter tractography and resting-state fMRI mapping for pre-surgical resection boundary demarcation and traumatic brain injury evaluation.
            </p>
            <div className="neuro-bento__stat-strip">
              <div>
                <strong className="neuro-bento__stat-val">0.7mm</strong>
                <span className="neuro-bento__stat-lbl">Isotropic Voxel Resolution</span>
              </div>
              <div>
                <strong className="neuro-bento__stat-val">ACR</strong>
                <span className="neuro-bento__stat-lbl">Diagnostic Imaging Accredited</span>
              </div>
            </div>
          </div>

          {/* Card 3: Neuromodulation & Deep Brain Stimulation */}
          <div className="neuro-bento__card neuro-bento__card--small">
            <div className="neuro-bento__card-header">
              <span className="neuro-bento__pill">THERAPEUTICS</span>
            </div>
            <h3 className="neuro-bento__card-title">FDA 510(k) Neuromodulation</h3>
            <p className="neuro-bento__card-desc">
              Transcranial Magnetic Stimulation (rTMS) and Vagus Nerve Stimulation (VNS) for pharmacoresistant neurological disorders.
            </p>
            <div className="neuro-bento__fda-seal">
              <span>FDA Cleared • Device ID #K213948</span>
            </div>
          </div>

          {/* Card 4: CLIA Certified Molecular Laboratory */}
          <div className="neuro-bento__card neuro-bento__card--small">
            <div className="neuro-bento__card-header">
              <span className="neuro-bento__pill">PATHOLOGY</span>
            </div>
            <h3 className="neuro-bento__card-title">CLIA Molecular Testing</h3>
            <p className="neuro-bento__card-desc">
              Next-generation targeted gene panels for hereditary neuropathies, channelopathies, and pharmacogenomic drug metabolism screening.
            </p>
            <div className="neuro-bento__clia-seal">
              <span>CLIA Certificate #05D2194810</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.neuro-bento {
  background-color: #f8fafc;
  padding: 4.5rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.neuro-bento__container {
  max-width: 1280px;
  margin: 0 auto;
}

.neuro-bento__header {
  margin-bottom: 2.5rem;
}

.neuro-bento__tag {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #0f766e;
  text-transform: uppercase;
}

.neuro-bento__heading {
  font-size: 2.2rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0.4rem 0 0.6rem 0;
  letter-spacing: -0.02em;
}

.neuro-bento__subhead {
  font-size: 1rem;
  color: #64748b;
  max-width: 680px;
  line-height: 1.5;
  margin: 0;
}

.neuro-bento__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.neuro-bento__card {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.neuro-bento__card--wide {
  grid-column: span 2;
}

.neuro-bento__card--medium {
  grid-column: span 1;
}

.neuro-bento__card--small {
  grid-column: span 1;
}

.neuro-bento__card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.neuro-bento__pill {
  font-size: 0.7rem;
  font-weight: 700;
  background-color: #f1f5f9;
  color: #475569;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  letter-spacing: 0.04em;
}

.neuro-bento__spec {
  font-size: 0.75rem;
  color: #0f766e;
  font-weight: 600;
}

.neuro-bento__selector {
  display: flex;
  background-color: #f1f5f9;
  padding: 3px;
  border-radius: 6px;
  gap: 4px;
}

.neuro-bento__tab-btn {
  border: none;
  background: transparent;
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.neuro-bento__tab-btn.is-active {
  background-color: #ffffff;
  color: #0f766e;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}

.neuro-bento__meta-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.6rem;
}

.neuro-bento__status-tag {
  background-color: #ccfbf1;
  color: #0f766e;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.neuro-bento__doctor {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #334155;
}

.neuro-bento__card-title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.75rem 0;
  letter-spacing: -0.01em;
}

.neuro-bento__card-desc {
  font-size: 0.875rem;
  color: #475569;
  line-height: 1.55;
  margin: 0 0 1.25rem 0;
}

.neuro-bento__protocols {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid #f1f5f9;
}

.neuro-bento__proto-title {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  color: #334155;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.neuro-bento__proto-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.neuro-bento__proto-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #334155;
}

.neuro-bento__proto-item svg {
  width: 14px;
  height: 14px;
  fill: #0d9488;
  flex-shrink: 0;
}

.neuro-bento__stat-strip {
  margin-top: auto;
  display: flex;
  gap: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid #f1f5f9;
}

.neuro-bento__stat-val {
  display: block;
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f766e;
}

.neuro-bento__stat-lbl {
  font-size: 0.7rem;
  color: #64748b;
}

.neuro-bento__fda-seal, .neuro-bento__clia-seal {
  margin-top: auto;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  background-color: #f8fafc;
  border: 1px dashed #cbd5e1;
  color: #475569;
}

@media (max-width: 900px) {
  .neuro-bento__grid {
    grid-template-columns: 1fr;
  }
  .neuro-bento__card--wide, .neuro-bento__card--medium, .neuro-bento__card--small {
    grid-column: span 1;
  }
}
"""
        },
        {
            "name": "CredentialsTrust",
            "instruction": "dedicated structural clinical trust section with ABPN board certifications, state medical licenses, HIPAA privacy policies, and institutional affiliations. Files: src/components/CredentialsTrust.tsx + src/components/CredentialsTrust.css",
            "tsx_path": "src/components/CredentialsTrust.tsx",
            "css_path": "src/components/CredentialsTrust.css",
            "thought": "Building structural trust-tier section housing board certifications, license registry numbers, and HIPAA security compliance.",
            "tsx": """import React from 'react';
import './CredentialsTrust.css';

export function CredentialsTrust() {
  const credentials = [
    {
      name: "Dr. Elena Rostova, MD, PhD",
      role: "Director of Comprehensive Epilepsy Center",
      degrees: "Johns Hopkins SOM (MD), Harvard University (PhD Neurobiology)",
      boards: "American Board of Psychiatry and Neurology (ABPN Cert #59102)",
      npi: "NPI: 1482019482 | TX Medical Lic: #P84920",
      fellowship: "Mayo Clinic Neurophysiology Fellowship"
    },
    {
      name: "Dr. Marcus Vance, MD",
      role: "Director of Behavioral & Cognitive Neurology",
      degrees: "Columbia University Vagelos College of Physicians and Surgeons",
      boards: "American Board of Psychiatry and Neurology (ABPN Cert #62810)",
      npi: "NPI: 1029481938 | TX Medical Lic: #R92841",
      fellowship: "UCSF Memory and Aging Center Fellowship"
    },
    {
      name: "Dr. Sanjay Bhatt, MD, FAAN",
      role: "Chief of Neurovascular & Stroke Intervention",
      degrees: "University of Pennsylvania Perelman School of Medicine",
      boards: "ABPN Vascular Neurology Subspecialty (Cert #48192)",
      npi: "NPI: 1849201832 | TX Medical Lic: #Q10948",
      fellowship: "Mass General Vascular Neurology Fellowship"
    }
  ];

  return (
    <section className="neuro-trust" id="credentials">
      <div className="neuro-trust__container">
        <div className="neuro-trust__header">
          <span className="neuro-trust__tag">STRUCTURAL CREDIBILITY & GOVERNANCE</span>
          <h2 className="neuro-trust__title">Board Certifications, Licensure & Statutory Disclosures</h2>
          <p className="neuro-trust__desc">
            All NeuroVance attending neurologists maintain active subspecialty board certifications, verifiable state licensure, and university faculty appointments.
          </p>
        </div>

        <div className="neuro-trust__grid">
          {credentials.map((doc, idx) => (
            <div key={idx} className="neuro-trust__card">
              <div className="neuro-trust__badge-row">
                <span className="neuro-trust__seal-pill">ABPN BOARD CERTIFIED</span>
                <span className="neuro-trust__reg">{doc.npi.split('|')[0].trim()}</span>
              </div>
              <h3 className="neuro-trust__physician">{doc.name}</h3>
              <p className="neuro-trust__role">{doc.role}</p>
              <div className="neuro-trust__details">
                <div className="neuro-trust__line">
                  <span className="neuro-trust__label">Education:</span>
                  <span className="neuro-trust__val">{doc.degrees}</span>
                </div>
                <div className="neuro-trust__line">
                  <span className="neuro-trust__label">Board:</span>
                  <span className="neuro-trust__val">{doc.boards}</span>
                </div>
                <div className="neuro-trust__line">
                  <span className="neuro-trust__label">Fellowship:</span>
                  <span className="neuro-trust__val">{doc.fellowship}</span>
                </div>
                <div className="neuro-trust__line">
                  <span className="neuro-trust__label">Licensure:</span>
                  <span className="neuro-trust__val">{doc.npi.split('|')[1].trim()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <aside className="neuro-trust__compliance-panel" role="complementary">
          <div className="neuro-trust__compliance-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <div>
              <h4 className="neuro-trust__compliance-title">HIPAA Security Safeguards & Regulatory Compliance</h4>
              <p className="neuro-trust__compliance-sub">In accordance with 45 CFR Part 160 and Part 164, Subparts A and E.</p>
            </div>
          </div>
          <p className="neuro-trust__compliance-text">
            NeuroVance Comprehensive Neurology Institute complies with applicable Federal civil rights laws and does not discriminate on the basis of race, color, national origin, age, disability, or sex. Protected Health Information (PHI) is encrypted at rest (AES-256) and in transit (TLS 1.3). CLIA Laboratory Certificate of Compliance ID: <strong>05D2194810</strong>.
          </p>
        </aside>
      </div>
    </section>
  );
}
""",
            "css": """.neuro-trust {
  background-color: #ffffff;
  padding: 4.5rem 1.5rem;
  border-top: 1px solid #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.neuro-trust__container {
  max-width: 1280px;
  margin: 0 auto;
}

.neuro-trust__header {
  margin-bottom: 2.5rem;
}

.neuro-trust__tag {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #0f766e;
  text-transform: uppercase;
}

.neuro-trust__title {
  font-size: 2.2rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0.4rem 0 0.6rem 0;
  letter-spacing: -0.02em;
}

.neuro-trust__desc {
  font-size: 1rem;
  color: #64748b;
  max-width: 720px;
  line-height: 1.5;
  margin: 0;
}

.neuro-trust__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin-bottom: 2.5rem;
}

.neuro-trust__card {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
}

.neuro-trust__badge-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.neuro-trust__seal-pill {
  background-color: #0f766e;
  color: #ffffff;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  letter-spacing: 0.04em;
}

.neuro-trust__reg {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
}

.neuro-trust__physician {
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.35rem 0;
}

.neuro-trust__role {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #0d9488;
  margin: 0 0 1.25rem 0;
}

.neuro-trust__details {
  border-top: 1px solid #e2e8f0;
  padding-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.neuro-trust__line {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.neuro-trust__label {
  font-weight: 700;
  color: #475569;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.neuro-trust__val {
  color: #1e293b;
  line-height: 1.35;
}

.neuro-trust__compliance-panel {
  background-color: #f0fdfa;
  border: 1px solid #ccfbf1;
  border-left: 4px solid #0f766e;
  border-radius: 8px;
  padding: 1.5rem;
}

.neuro-trust__compliance-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.neuro-trust__compliance-header svg {
  width: 24px;
  height: 24px;
  stroke: #0f766e;
  flex-shrink: 0;
}

.neuro-trust__compliance-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.neuro-trust__compliance-sub {
  font-size: 0.75rem;
  color: #0d9488;
  margin: 0.1rem 0 0 0;
}

.neuro-trust__compliance-text {
  font-size: 0.8125rem;
  color: #334155;
  line-height: 1.5;
  margin: 0;
}

@media (max-width: 960px) {
  .neuro-trust__grid {
    grid-template-columns: 1fr;
  }
}
"""
        },
        {
            "name": "Footer",
            "instruction": "clinical footer with medical disclaimer, HIPAA statement, NPI number, and emergency 911 restatement. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building clinical footer with statutory disclosures and accessibility statements.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="neuro-footer" role="contentinfo">
      <div className="neuro-footer__container">
        <div className="neuro-footer__top">
          <div className="neuro-footer__col neuro-footer__col--brand">
            <span className="neuro-footer__brand-title">NeuroVance Comprehensive Neurology Institute</span>
            <p className="neuro-footer__brand-desc">
              Academic outpatient and diagnostic neurology center dedicated to patient outcome excellence, advanced neuromodulation, and translational neuroscience.
            </p>
            <div className="neuro-footer__meta-list">
              <span>NPI Organization ID: #1948201948</span>
              <span>CLIA Lab Certification: #05D2194810</span>
              <span>NAEC Level 4 Center: Epilepsy ID #77-TX-902</span>
            </div>
          </div>

          <div className="neuro-footer__col">
            <h4 className="neuro-footer__heading">Clinical Inquiries</h4>
            <address className="neuro-footer__address">
              750 Medical Center Boulevard, Pavilion B<br />
              Suite 400, Houston, TX 77030<br />
              Direct: +1 (713) 555-0199<br />
              Referrals Fax: +1 (713) 555-0198<br />
              clinical.intake@neurovance-health.org
            </address>
          </div>

          <div className="neuro-footer__col">
            <h4 className="neuro-footer__heading">Emergency & Triage</h4>
            <p className="neuro-footer__disclaimer">
              This website provides general information regarding clinical services and should not be construed as medical diagnosis or medical advice. If you are experiencing a medical emergency, call 911 immediately.
            </p>
          </div>
        </div>

        <div className="neuro-footer__bottom">
          <div className="neuro-footer__copyright">
            © {new Date().getFullYear()} NeuroVance Comprehensive Neurology Institute. All rights reserved.
          </div>
          <div className="neuro-footer__legal-links">
            <a href="#hipaa">HIPAA Privacy Practices</a>
            <a href="#nondiscrimination">Notice of Non-Discrimination</a>
            <a href="#terms">Terms of Care</a>
            <a href="#accessibility">Accessibility Statement</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
""",
            "css": """.neuro-footer {
  background-color: #0f172a;
  color: #94a3b8;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.8125rem;
  padding: 3.5rem 1.5rem 2rem;
  border-top: 1px solid #1e293b;
}

.neuro-footer__container {
  max-width: 1280px;
  margin: 0 auto;
}

.neuro-footer__top {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 2.5rem;
  margin-bottom: 2.5rem;
}

.neuro-footer__brand-title {
  display: block;
  font-size: 1.05rem;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 0.5rem;
}

.neuro-footer__brand-desc {
  line-height: 1.5;
  color: #94a3b8;
  margin: 0 0 1rem 0;
  max-width: 460px;
}

.neuro-footer__meta-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #2dd4bf;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.neuro-footer__heading {
  font-size: 0.875rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 0.75rem 0;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.neuro-footer__address {
  font-style: normal;
  line-height: 1.6;
  color: #94a3b8;
}

.neuro-footer__disclaimer {
  line-height: 1.5;
  color: #94a3b8;
  margin: 0;
}

.neuro-footer__bottom {
  padding-top: 2rem;
  border-top: 1px solid #1e293b;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}

.neuro-footer__copyright {
  color: #64748b;
  font-size: 0.75rem;
}

.neuro-footer__legal-links {
  display: flex;
  gap: 1.25rem;
}

.neuro-footer__legal-links a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.75rem;
  transition: color 0.15s ease;
}

.neuro-footer__legal-links a:hover {
  color: #2dd4bf;
}

@media (max-width: 768px) {
  .neuro-footer__top {
    grid-template-columns: 1fr;
  }
}
"""
        }
    ]
    trajs.append(make_traj("site_healthcare_bento_neuro", t1_brief, t1_sections))

    # ==============================================================================
    # 2. Healthcare x Editorial: Apex Cardiothoracic Institute
    # ==============================================================================
    t2_brief = """<content_brief>
  <business_name>Apex Cardiothoracic & Minimally Invasive Heart Center</business_name>
  <tagline>Pioneering Structural Heart Therapies & Robotic Cardiac Surgery</tagline>
  <business_type>healthcare</business_type>
  <layout_archetype>editorial</layout_archetype>
  <layout_guidelines>Editorial clinical architecture featuring Joint Commission Gold Seal, FACS surgical credentials, CA Medical Board Lic #A-149820, STS National Database 3-star rating, and peer-reviewed surgical outcome treatises.</layout_guidelines>
  <sections>header, hero, surgical_treatise, clinical_credentials, outcome_metrics, footer</sections>
  <contact>
    <address>1200 Wilshire Blvd, Heart Center Tower 8, Los Angeles, CA 90017</address>
    <phone>+1 (213) 555-0144</phone>
    <email>surgical.coordinator@apex-cardiothoracic.org</email>
    <hours>Mon–Fri: 8:00am–6:00pm PST | 24/7 Acute Aortic Dissection Team</hours>
  </contact>
</content_brief>"""

    t2_sections = [
        {
            "name": "Header",
            "instruction": "prestigious surgical center editorial header with Joint Commission accreditation badge and surgical intake hotline. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building editorial header with Joint Commission Gold Seal citation and serif typography.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="apex-header" role="banner">
      <div className="apex-header__top-bar">
        <div className="apex-header__top-container">
          <span className="apex-header__seal">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Joint Commission Gold Seal of Approval • Complex Cardiovascular Surgery
          </span>
          <span className="apex-header__lic">NPI #1092837465 | CA Med Lic #A-149820</span>
        </div>
      </div>

      <div className="apex-header__main">
        <div className="apex-header__main-container">
          <a href="#hero" className="apex-header__brand">
            <span className="apex-header__title">APEX CARDIOTHORACIC</span>
            <span className="apex-header__subtitle">INSTITUTE FOR STRUCTURAL HEART & ROBOTIC SURGERY</span>
          </a>

          <nav className="apex-header__nav" aria-label="Clinical Editorial Navigation">
            <a href="#treatise" className="apex-header__nav-link">Surgical Protocols</a>
            <a href="#credentials" className="apex-header__nav-link">Surgeon Profiles</a>
            <a href="#outcomes" className="apex-header__nav-link">STS Registry Data</a>
            <a href="#contact" className="apex-header__nav-link">Referrals</a>
          </nav>

          <a href="#consultation" className="apex-header__cta">Urgent Case Evaluation</a>
        </div>
      </div>
    </header>
  );
}
""",
            "css": """.apex-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e7e5e4;
  font-family: "Georgia", serif;
  position: sticky;
  top: 0;
  z-index: 50;
}

.apex-header__top-bar {
  background-color: #1c1917;
  color: #e7e5e4;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.75rem;
  padding: 0.4rem 1.5rem;
}

.apex-header__top-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.apex-header__seal {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #facc15;
  font-weight: 600;
}

.apex-header__seal svg {
  width: 14px;
  height: 14px;
}

.apex-header__lic {
  color: #a8a29e;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.apex-header__main {
  padding: 1.25rem 1.5rem;
}

.apex-header__main-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.apex-header__brand {
  text-decoration: none;
  display: flex;
  flex-direction: column;
}

.apex-header__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #1c1917;
  letter-spacing: 0.06em;
}

.apex-header__subtitle {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.65rem;
  font-weight: 700;
  color: #991b1b;
  letter-spacing: 0.12em;
  margin-top: 0.15rem;
}

.apex-header__nav {
  display: flex;
  gap: 2rem;
}

.apex-header__nav-link {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #44403c;
  transition: color 0.15s ease;
}

.apex-header__nav-link:hover {
  color: #991b1b;
}

.apex-header__cta {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  padding: 0.55rem 1.1rem;
  background-color: #991b1b;
  color: #ffffff;
  border-radius: 4px;
  font-size: 0.8125rem;
  font-weight: 700;
  text-decoration: none;
}

@media (max-width: 860px) {
  .apex-header__nav, .apex-header__lic {
    display: none;
  }
}
"""
        },
        {
            "name": "Hero",
            "instruction": "editorial longform hero with surgical masthead, STS 3-star quality badge, and clinical case volume. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero in an editorial format with high-contrast serif typography and official surgical ratings.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="apex-hero" id="hero">
      <div className="apex-hero__container">
        <div className="apex-hero__masthead">
          <div className="apex-hero__kicker">CLINICAL MONOGRAPH & SURGICAL DISPATCH</div>
          <h1 className="apex-hero__headline">
            Minimally Invasive Valve Reconstruction & Transcatheter Therapeutics: A Ten-Year Clinical Review
          </h1>
          <div className="apex-hero__byline">
            <span>By <strong>Julian Sterling, MD, FACS, FACC</strong> — Surgical Director</span>
            <span className="apex-hero__byline-div">|</span>
            <span>Published by the Apex Clinical Academic Council</span>
            <span className="apex-hero__byline-div">|</span>
            <span>IRB Protocol #2026-441</span>
          </div>
        </div>

        <div className="apex-hero__editorial-lead">
          <p className="apex-hero__dropcap-para">
            Over the past decade, the transition from traditional full sternotomy to endoscopic and robotic-assisted mitral valve repair has demonstrated a statistically significant reduction in 30-day perioperative mortality and hospital length-of-stay. At Apex Cardiothoracic Institute, our prospective observational cohort of 2,410 consecutive robotic cardiac reconstructions achieved an unadjusted 99.4% procedural survival rate, earning consecutive three-star designations—the highest tier—from the Society of Thoracic Surgeons (STS) National Database.
          </p>
        </div>

        <div className="apex-hero__rating-strip">
          <div className="apex-hero__rating-box">
            <span className="apex-hero__rating-source">SOCIETY OF THORACIC SURGEONS</span>
            <div className="apex-hero__stars">★★★</div>
            <span className="apex-hero__rating-desc">Top 4% of North American Centers for Composite Mitral & Aortic Quality</span>
          </div>
          <div className="apex-hero__rating-box">
            <span className="apex-hero__rating-source">PROCEDURAL VOLUME</span>
            <div className="apex-hero__big-num">2,410+</div>
            <span className="apex-hero__rating-desc">Consecutive Robotic Structural Procedures (2016–2026)</span>
          </div>
          <div className="apex-hero__rating-box">
            <span className="apex-hero__rating-source">PERIOPERATIVE SURVIVAL</span>
            <div className="apex-hero__big-num">99.4%</div>
            <span className="apex-hero__rating-desc">STS Risk-Adjusted Operative Concordance Benchmark</span>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.apex-hero {
  background-color: #fafaf9;
  padding: 4.5rem 1.5rem 3.5rem;
  border-bottom: 1px solid #e7e5e4;
  font-family: "Georgia", serif;
}

.apex-hero__container {
  max-width: 1080px;
  margin: 0 auto;
}

.apex-hero__kicker {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  color: #991b1b;
  text-transform: uppercase;
  margin-bottom: 1rem;
}

.apex-hero__headline {
  font-size: 3rem;
  line-height: 1.15;
  color: #1c1917;
  font-weight: 700;
  margin: 0 0 1.5rem 0;
  letter-spacing: -0.01em;
}

.apex-hero__byline {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.8125rem;
  color: #78716c;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #d6d3d1;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.apex-hero__byline strong {
  color: #1c1917;
}

.apex-hero__byline-div {
  color: #d6d3d1;
}

.apex-hero__dropcap-para {
  font-size: 1.25rem;
  line-height: 1.7;
  color: #292524;
  margin-bottom: 3rem;
}

.apex-hero__rating-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.apex-hero__rating-box {
  background-color: #ffffff;
  border: 1px solid #e7e5e4;
  padding: 1.5rem;
  border-top: 3px solid #991b1b;
  display: flex;
  flex-direction: column;
}

.apex-hero__rating-source {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.7rem;
  font-weight: 700;
  color: #78716c;
  letter-spacing: 0.08em;
  margin-bottom: 0.5rem;
}

.apex-hero__stars {
  color: #b45309;
  font-size: 1.75rem;
  letter-spacing: 0.2em;
  line-height: 1;
  margin-bottom: 0.5rem;
}

.apex-hero__big-num {
  font-size: 2.25rem;
  font-weight: 700;
  color: #1c1917;
  line-height: 1;
  margin-bottom: 0.5rem;
}

.apex-hero__rating-desc {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.75rem;
  color: #57534e;
  line-height: 1.4;
}

@media (max-width: 800px) {
  .apex-hero__headline {
    font-size: 2.2rem;
  }
  .apex-hero__rating-strip {
    grid-template-columns: 1fr;
  }
}
"""
        },
        {
            "name": "SurgicalTreatise",
            "instruction": "two-column editorial clinical treatise contrasting transcatheter vs robotic approaches with peer-reviewed references. Files: src/components/SurgicalTreatise.tsx + src/components/SurgicalTreatise.css",
            "tsx_path": "src/components/SurgicalTreatise.tsx",
            "css_path": "src/components/SurgicalTreatise.css",
            "thought": "Building SurgicalTreatise component in a two-column newspaper editorial layout.",
            "tsx": """import React from 'react';
import './SurgicalTreatise.css';

export function SurgicalTreatise() {
  return (
    <article className="apex-treatise" id="treatise">
      <div className="apex-treatise__container">
        <header className="apex-treatise__header">
          <span className="apex-treatise__chapter">SECTION II: OPERATIVE MODALITIES</span>
          <h2 className="apex-treatise__title">Comparative Analysis of Structural Approaches</h2>
        </header>

        <div className="apex-treatise__columns">
          <div className="apex-treatise__col">
            <h3 className="apex-treatise__col-heading">Robotic-Assisted Mitral Valve Repair</h3>
            <p>
              Under high-magnification 3D stereoscopic vision via the da Vinci Xi surgical console, our attending surgeons access the left atrium through four intercostal ports of less than 8mm each. This eliminates sternal division, reducing median ICU duration to 18 hours.
            </p>
            <p>
              In our longitudinal study (Sterling et al., <em>Journal of Thoracic and Cardiovascular Surgery</em>, 2025), freedom from moderate or severe recurrent mitral regurgitation at 5 years reached 96.8% with artificial chordal Gore-Tex transposition.
            </p>
            <blockquote className="apex-treatise__pullquote">
              "The surgical preservation of the native valve architecture remains the gold standard in longevity and stroke prevention."
            </blockquote>
          </div>

          <div className="apex-treatise__col">
            <h3 className="apex-treatise__col-heading">Transcatheter Aortic Valve Replacement (TAVR)</h3>
            <p>
              For severe symptomatic aortic stenosis across low, intermediate, and high surgical risk strata, transfemoral TAVR offers rapid hemodynamic normalization without cardiopulmonary bypass. Apex maintains a dedicated Heart Valve Team evaluating multi-detector CT ring geometry.
            </p>
            <p>
              Median fluoroscopy time was 11.2 minutes, with zero disabling strokes in the 2025–2026 registry reporting period. Patients receive non-contrast cerebral embolic protection as standard institutional protocol.
            </p>
            <div className="apex-treatise__footnote">
              <strong>Source Citations:</strong><br />
              1. STS Adult Cardiac Surgery Database Fall 2025 Harvest.<br />
              2. California Department of Public Health Licensure Standard Section 70433.<br />
              3. Institutional Review Board Protocol Approved under HHS 45 CFR 46.
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}
""",
            "css": """.apex-treatise {
  background-color: #ffffff;
  padding: 4.5rem 1.5rem;
  border-bottom: 1px solid #e7e5e4;
  font-family: "Georgia", serif;
}

.apex-treatise__container {
  max-width: 1080px;
  margin: 0 auto;
}

.apex-treatise__header {
  margin-bottom: 2.5rem;
  text-align: center;
}

.apex-treatise__chapter {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  color: #991b1b;
  display: block;
  margin-bottom: 0.5rem;
}

.apex-treatise__title {
  font-size: 2.2rem;
  color: #1c1917;
  font-weight: 700;
  margin: 0;
}

.apex-treatise__columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3.5rem;
  font-size: 1rem;
  line-height: 1.75;
  color: #292524;
}

.apex-treatise__col-heading {
  font-size: 1.35rem;
  font-weight: 700;
  color: #1c1917;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #d6d3d1;
}

.apex-treatise__pullquote {
  margin: 2rem 0;
  padding: 1rem 1.5rem;
  border-left: 3px solid #991b1b;
  background-color: #fafaf9;
  font-style: italic;
  font-size: 1.125rem;
  color: #44403c;
  line-height: 1.5;
}

.apex-treatise__footnote {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.75rem;
  color: #78716c;
  background-color: #fafaf9;
  border: 1px solid #e7e5e4;
  padding: 1rem;
  border-radius: 4px;
  line-height: 1.5;
  margin-top: 2rem;
}

@media (max-width: 800px) {
  .apex-treatise__columns {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
}
"""
        },
        {
            "name": "ClinicalCredentials",
            "instruction": "surgical faculty credentials with FACS fellowship, American Board of Thoracic Surgery certification, and California Medical Board license numbers. Files: src/components/ClinicalCredentials.tsx + src/components/ClinicalCredentials.css",
            "tsx_path": "src/components/ClinicalCredentials.tsx",
            "css_path": "src/components/ClinicalCredentials.css",
            "thought": "Building structural trust-tier section with ABTS board numbers and FACS surgical fellow disclosures.",
            "tsx": """import React from 'react';
import './ClinicalCredentials.css';

export function ClinicalCredentials() {
  const surgeons = [
    {
      name: "Dr. Julian Sterling, MD, FACS, FACC",
      title: "Chief of Cardiothoracic Surgery & Structural Heart Director",
      board: "American Board of Thoracic Surgery (Cert #19482)",
      license: "CA Med Board Lic #A-149820 | NPI #1092837465",
      training: "Stanford Medical Center Residency; Cleveland Clinic Aortic Fellowship",
      volume: "3,800+ career bypass and valve surgeries"
    },
    {
      name: "Dr. Vivienne Chen-Alvarez, MD, FACS",
      title: "Director of Robotic Thoracic & Minimally Invasive Surgery",
      board: "American Board of Thoracic Surgery (Cert #22841)",
      license: "CA Med Board Lic #A-168420 | NPI #1982019481",
      training: "Brigham and Women's Hospital / Harvard Medical School Fellowship",
      volume: "1,950+ da Vinci robotic surgical repairs"
    }
  ];

  return (
    <section className="apex-credentials" id="credentials">
      <div className="apex-credentials__container">
        <div className="apex-credentials__header">
          <span className="apex-credentials__kicker">FACULTY CERTIFICATIONS</span>
          <h2 className="apex-credentials__title">Board-Certified Attending Surgeons</h2>
          <p className="apex-credentials__lead">
            Every surgical procedure at Apex is directed by board-certified fellows of the American College of Surgeons (FACS) who participate in the STS National Registry.
          </p>
        </div>

        <div className="apex-credentials__grid">
          {surgeons.map((surg, idx) => (
            <div key={idx} className="apex-credentials__card">
              <div className="apex-credentials__badge-bar">
                <span className="apex-credentials__facs-seal">FACS FELLOW</span>
                <span className="apex-credentials__abts">ABTS CERTIFIED</span>
              </div>
              <h3 className="apex-credentials__name">{surg.name}</h3>
              <p className="apex-credentials__role">{surg.title}</p>
              
              <div className="apex-credentials__spec-table">
                <div className="apex-credentials__row">
                  <span className="apex-credentials__label">Board Certification:</span>
                  <span className="apex-credentials__val">{surg.board}</span>
                </div>
                <div className="apex-credentials__row">
                  <span className="apex-credentials__label">State Licensure:</span>
                  <span className="apex-credentials__val">{surg.license}</span>
                </div>
                <div className="apex-credentials__row">
                  <span className="apex-credentials__label">Clinical Training:</span>
                  <span className="apex-credentials__val">{surg.training}</span>
                </div>
                <div className="apex-credentials__row">
                  <span className="apex-credentials__label">Surgical Caseload:</span>
                  <span className="apex-credentials__val">{surg.volume}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.apex-credentials {
  background-color: #fafaf9;
  padding: 4.5rem 1.5rem;
  border-bottom: 1px solid #e7e5e4;
  font-family: "Georgia", serif;
}

.apex-credentials__container {
  max-width: 1080px;
  margin: 0 auto;
}

.apex-credentials__header {
  margin-bottom: 2.5rem;
}

.apex-credentials__kicker {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  color: #991b1b;
  display: block;
  margin-bottom: 0.4rem;
}

.apex-credentials__title {
  font-size: 2.2rem;
  color: #1c1917;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
}

.apex-credentials__lead {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.9375rem;
  color: #57534e;
  max-width: 700px;
  margin: 0;
  line-height: 1.5;
}

.apex-credentials__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.apex-credentials__card {
  background-color: #ffffff;
  border: 1px solid #e7e5e4;
  padding: 2rem;
  border-radius: 4px;
}

.apex-credentials__badge-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.apex-credentials__facs-seal {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: #1c1917;
  color: #ffffff;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 2px;
}

.apex-credentials__abts {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: #fee2e2;
  color: #991b1b;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 2px;
}

.apex-credentials__name {
  font-size: 1.35rem;
  font-weight: 700;
  color: #1c1917;
  margin: 0 0 0.35rem 0;
}

.apex-credentials__role {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #991b1b;
  margin: 0 0 1.25rem 0;
}

.apex-credentials__spec-table {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  border-top: 1px solid #f5f5f4;
  padding-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  font-size: 0.8125rem;
}

.apex-credentials__row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.apex-credentials__label {
  font-size: 0.7rem;
  font-weight: 700;
  color: #78716c;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.apex-credentials__val {
  color: #292524;
  line-height: 1.4;
}

@media (max-width: 800px) {
  .apex-credentials__grid {
    grid-template-columns: 1fr;
  }
}
"""
        },
        {
            "name": "Footer",
            "instruction": "prestigious surgical editorial footer with statutory medical disclaimer, emergency hotline, and Joint Commission compliance. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building surgical center footer with statutory disclaimers.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="apex-footer" role="contentinfo">
      <div className="apex-footer__container">
        <div className="apex-footer__primary">
          <div className="apex-footer__col-main">
            <span className="apex-footer__brand">Apex Cardiothoracic & Minimally Invasive Heart Center</span>
            <p className="apex-footer__lead">
              A specialized cardiac surgical facility providing tertiary and quaternary cardiovascular interventions. Accredited by The Joint Commission.
            </p>
            <div className="apex-footer__statutory">
              <span>CA Medical Board License: #A-149820</span>
              <span>National Provider Identifier: #1092837465</span>
              <span>STS Participant ID: #940182</span>
            </div>
          </div>

          <div className="apex-footer__col">
            <h4 className="apex-footer__title">Hospital Tower Location</h4>
            <address className="apex-footer__addr">
              1200 Wilshire Blvd, Tower 8<br />
              Los Angeles, CA 90017<br />
              Coordinator: +1 (213) 555-0144<br />
              surgical.coordinator@apex-cardiothoracic.org
            </address>
          </div>

          <div className="apex-footer__col">
            <h4 className="apex-footer__title">Emergency Notice</h4>
            <p className="apex-footer__notice">
              This site provides clinical institutional information and does not establish a physician-patient relationship. In acute cardiac emergency, call 911 immediately.
            </p>
          </div>
        </div>

        <div className="apex-footer__secondary">
          <div className="apex-footer__copy">
            © {new Date().getFullYear()} Apex Cardiothoracic Institute. All rights reserved.
          </div>
          <div className="apex-footer__links">
            <a href="#privacy">HIPAA Notice of Privacy</a>
            <a href="#accreditation">Joint Commission Seal</a>
            <a href="#ethics">Institutional Ethics Board</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
""",
            "css": """.apex-footer {
  background-color: #1c1917;
  color: #a8a29e;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.8125rem;
  padding: 3.5rem 1.5rem 2rem;
}

.apex-footer__container {
  max-width: 1200px;
  margin: 0 auto;
}

.apex-footer__primary {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 3rem;
  margin-bottom: 2.5rem;
}

.apex-footer__brand {
  font-family: "Georgia", serif;
  display: block;
  font-size: 1.15rem;
  font-weight: 700;
  color: #f5f5f4;
  margin-bottom: 0.5rem;
}

.apex-footer__lead {
  color: #a8a29e;
  line-height: 1.5;
  margin: 0 0 1rem 0;
  max-width: 440px;
}

.apex-footer__statutory {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.75rem;
  color: #facc15;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.apex-footer__title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #f5f5f4;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem 0;
}

.apex-footer__addr {
  font-style: normal;
  line-height: 1.6;
  color: #a8a29e;
}

.apex-footer__notice {
  line-height: 1.5;
  color: #a8a29e;
  margin: 0;
}

.apex-footer__secondary {
  border-top: 1px solid #292524;
  padding-top: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.apex-footer__copy {
  font-size: 0.75rem;
  color: #78716c;
}

.apex-footer__links {
  display: flex;
  gap: 1.5rem;
}

.apex-footer__links a {
  color: #a8a29e;
  text-decoration: none;
  font-size: 0.75rem;
  transition: color 0.15s ease;
}

.apex-footer__links a:hover {
  color: #f5f5f4;
}

@media (max-width: 800px) {
  .apex-footer__primary {
    grid-template-columns: 1fr;
  }
}
"""
        }
    ]
    trajs.append(make_traj("site_healthcare_editorial_apex", t2_brief, t2_sections))

    # ==============================================================================
    # 3. Healthcare x Tabs: Solace Integrative Psychiatric & Behavioral Health
    # ==============================================================================
    t3_brief = """<content_brief>
  <business_name>Solace Integrative Psychiatric & Behavioral Health</business_name>
  <tagline>Evidence-Based Psychotherapy, Interventional TMS & Behavioral Medicine</tagline>
  <business_type>healthcare</business_type>
  <layout_archetype>tabs</layout_archetype>
  <layout_guidelines>Tabbed behavioral medicine architecture featuring 988 Suicide & Crisis Lifeline statutory banner, CARF 3-year accreditation, APA licensed psychologist credentials #PSY-29184, and interactive treatment modality tabs (Adult Psychiatry, Intensive Outpatient IOP, TMS Therapy, KAP).</layout_guidelines>
  <sections>lifeline_banner, header, hero, modality_tabs, insurance_verification, footer</sections>
  <contact>
    <address>450 Sutter Street, Suite 1800, San Francisco, CA 94108</address>
    <phone>+1 (415) 555-0177</phone>
    <email>intake@solace-psych.org</email>
    <hours>Mon–Fri: 8:00am–7:00pm PST | Sat: 9:00am–2:00pm PST</hours>
  </contact>
</content_brief>"""

    t3_sections = [
        {
            "name": "LifelineBanner",
            "instruction": "statutory 988 Suicide & Crisis Lifeline alert banner with one-touch crisis dialing and text support. Files: src/components/LifelineBanner.tsx + src/components/LifelineBanner.css",
            "tsx_path": "src/components/LifelineBanner.tsx",
            "css_path": "src/components/LifelineBanner.css",
            "thought": "Building statutory 988 Suicide & Crisis Lifeline banner as an alert component.",
            "tsx": """import React from 'react';
import './LifelineBanner.css';

export function LifelineBanner() {
  return (
    <aside className="solace-lifeline" role="alert" aria-live="assertive">
      <div className="solace-lifeline__container">
        <div className="solace-lifeline__brand">
          <span className="solace-lifeline__number">988</span>
          <span className="solace-lifeline__badge">SUICIDE & CRISIS LIFELINE</span>
        </div>
        <p className="solace-lifeline__text">
          If you or someone you care about is experiencing thoughts of suicide, mental health crisis, or substance distress, free and confidential support is available 24/7. Call or text <strong>988</strong> or chat online at 988lifeline.org.
        </p>
        <div className="solace-lifeline__actions">
          <a href="tel:988" className="solace-lifeline__call-btn">Call 988</a>
          <span className="solace-lifeline__or">or text HOME to 741741</span>
        </div>
      </div>
    </aside>
  );
}
""",
            "css": """.solace-lifeline {
  background-color: #1e3a8a;
  color: #eff6ff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.8125rem;
  padding: 0.55rem 1.5rem;
  border-bottom: 1px solid #2563eb;
}

.solace-lifeline__container {
  max-width: 1240px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.solace-lifeline__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.solace-lifeline__number {
  background-color: #f59e0b;
  color: #1e293b;
  font-weight: 900;
  font-size: 0.875rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.solace-lifeline__badge {
  font-weight: 700;
  letter-spacing: 0.05em;
  font-size: 0.75rem;
  color: #bfdbfe;
}

.solace-lifeline__text {
  margin: 0;
  flex: 1;
  min-width: 300px;
  color: #dbeafe;
  line-height: 1.4;
}

.solace-lifeline__text strong {
  color: #ffffff;
}

.solace-lifeline__actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.75rem;
}

.solace-lifeline__call-btn {
  background-color: #f59e0b;
  color: #0f172a;
  text-decoration: none;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
}

.solace-lifeline__or {
  color: #bfdbfe;
}

@media (max-width: 768px) {
  .solace-lifeline__actions {
    display: none;
  }
}
"""
        },
        {
            "name": "Header",
            "instruction": "psychiatric clinic header with CARF accreditation badge, HIPAA secure intake button, and direct phone. Files: src/components/Header.tsx + src/components/Header.css",
            "tsx_path": "src/components/Header.tsx",
            "css_path": "src/components/Header.css",
            "thought": "Building clinical header with CARF 3-year accreditation notice and patient navigation.",
            "tsx": """import React from 'react';
import './Header.css';

export function Header() {
  return (
    <header className="solace-header" role="banner">
      <div className="solace-header__container">
        <div className="solace-header__brand-group">
          <a href="#hero" className="solace-header__logo" aria-label="Solace Psychiatric Home">
            <div className="solace-header__mark">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <div className="solace-header__text">
              <span className="solace-header__title">SOLACE PSYCHIATRIC</span>
              <span className="solace-header__subtitle">INTEGRATIVE BEHAVIORAL HEALTH</span>
            </div>
          </a>
          <span className="solace-header__carf-tag">CARF 3-YEAR ACCREDITED</span>
        </div>

        <nav className="solace-header__nav" aria-label="Main Navigation">
          <a href="#modalities" className="solace-header__nav-link">Treatments</a>
          <a href="#insurance" className="solace-header__nav-link">Insurance & Rates</a>
          <a href="#clinicians" className="solace-header__nav-link">Clinicians</a>
          <a href="#contact" className="solace-header__nav-link">San Francisco Clinic</a>
        </nav>

        <div className="solace-header__cta-group">
          <span className="solace-header__phone">+1 (415) 555-0177</span>
          <a href="#intake" className="solace-header__btn-intake">Confidential Intake</a>
        </div>
      </div>
    </header>
  );
}
""",
            "css": """.solace-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 40;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.solace-header__container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0.9rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.solace-header__brand-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.solace-header__logo {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  text-decoration: none;
}

.solace-header__mark {
  width: 36px;
  height: 36px;
  background-color: #4338ca;
  color: #ffffff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.solace-header__mark svg {
  width: 20px;
  height: 20px;
}

.solace-header__text {
  display: flex;
  flex-direction: column;
}

.solace-header__title {
  font-size: 1.1rem;
  font-weight: 800;
  color: #1e1b4b;
  letter-spacing: -0.01em;
}

.solace-header__subtitle {
  font-size: 0.65rem;
  font-weight: 700;
  color: #6366f1;
  letter-spacing: 0.08em;
}

.solace-header__carf-tag {
  background-color: #eef2ff;
  border: 1px solid #c7d2fe;
  color: #4338ca;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  letter-spacing: 0.04em;
}

.solace-header__nav {
  display: flex;
  gap: 1.75rem;
}

.solace-header__nav-link {
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  color: #475569;
  transition: color 0.15s ease;
}

.solace-header__nav-link:hover {
  color: #4338ca;
}

.solace-header__cta-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.solace-header__phone {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #334155;
}

.solace-header__btn-intake {
  background-color: #4338ca;
  color: #ffffff;
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: background-color 0.15s ease;
}

.solace-header__btn-intake:hover {
  background-color: #3730a3;
}

@media (max-width: 860px) {
  .solace-header__nav, .solace-header__phone, .solace-header__carf-tag {
    display: none;
  }
}
"""
        },
        {
            "name": "Hero",
            "instruction": "empathetic psychiatric hero with evidence-based badges, APA licensure notes, and rapid intake availability. Files: src/components/Hero.tsx + src/components/Hero.css",
            "tsx_path": "src/components/Hero.tsx",
            "css_path": "src/components/Hero.css",
            "thought": "Building Hero section communicating clinical credibility and evidence-based compassion.",
            "tsx": """import React from 'react';
import './Hero.css';

export function Hero() {
  return (
    <section className="solace-hero" id="hero">
      <div className="solace-hero__container">
        <div className="solace-hero__badge-row">
          <span className="solace-hero__badge">BOARD-CERTIFIED PSYCHIATRISTS & LICENSED PSYCHOLOGISTS</span>
          <span className="solace-hero__sub">In-Network with Major Health Plans</span>
        </div>
        <h1 className="solace-hero__headline">
          Comprehensive Psychiatric Medicine Grounded in Neuroscience & Compassion.
        </h1>
        <p className="solace-hero__lead">
          Solace offers an integrated continuum of adult psychiatric care, combining evidence-based psychotherapy, precision pharmacogenomic medication management, and FDA-cleared interventional neuromodulation (rTMS).
        </p>

        <div className="solace-hero__trust-strip">
          <div className="solace-hero__trust-item">
            <span className="solace-hero__trust-num">72 Hours</span>
            <span className="solace-hero__trust-label">Initial Assessment Window</span>
            <span className="solace-hero__trust-desc">Guaranteed priority intake slot for urgent referrals</span>
          </div>
          <div className="solace-hero__trust-item">
            <span className="solace-hero__trust-num">100%</span>
            <span className="solace-hero__trust-label">Licensed Doctoral Staff</span>
            <span className="solace-hero__trust-desc">All sessions conducted by MDs or PhD/PsyD clinicians</span>
          </div>
          <div className="solace-hero__trust-item">
            <span className="solace-hero__trust-num">CARF</span>
            <span className="solace-hero__trust-label">Three-Year Accreditation</span>
            <span className="solace-hero__trust-desc">Conforming to highest national behavioral standards</span>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.solace-hero {
  background: linear-gradient(180deg, #f5f3ff 0%, #ffffff 100%);
  padding: 4.5rem 1.5rem 3.5rem;
  border-bottom: 1px solid #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.solace-hero__container {
  max-width: 1080px;
  margin: 0 auto;
  text-align: center;
}

.solace-hero__badge-row {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  background-color: #ede9fe;
  padding: 0.35rem 0.85rem;
  border-radius: 9999px;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  justify-content: center;
}

.solace-hero__badge {
  font-size: 0.7rem;
  font-weight: 800;
  color: #5b21b6;
  letter-spacing: 0.05em;
}

.solace-hero__sub {
  font-size: 0.75rem;
  color: #6d28d9;
  font-weight: 600;
}

.solace-hero__headline {
  font-size: 2.75rem;
  line-height: 1.2;
  font-weight: 800;
  color: #1e1b4b;
  margin: 0 0 1.25rem 0;
  letter-spacing: -0.02em;
}

.solace-hero__lead {
  font-size: 1.125rem;
  line-height: 1.6;
  color: #475569;
  max-width: 780px;
  margin: 0 auto 3rem auto;
}

.solace-hero__trust-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  text-align: left;
}

.solace-hero__trust-item {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-top: 3px solid #6366f1;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

.solace-hero__trust-num {
  font-size: 1.85rem;
  font-weight: 800;
  color: #4338ca;
  display: block;
  margin-bottom: 0.35rem;
}

.solace-hero__trust-label {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #1e293b;
  display: block;
  margin-bottom: 0.25rem;
}

.solace-hero__trust-desc {
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.4;
}

@media (max-width: 768px) {
  .solace-hero__headline {
    font-size: 2rem;
  }
  .solace-hero__trust-strip {
    grid-template-columns: 1fr;
  }
}
"""
        },
        {
            "name": "ModalityTabs",
            "instruction": "stateful treatment modality tabs switching between Adult Psychiatry, Intensive Outpatient IOP, TMS Therapy, and Psychotherapy with clinical details. Files: src/components/ModalityTabs.tsx + src/components/ModalityTabs.css",
            "tsx_path": "src/components/ModalityTabs.tsx",
            "css_path": "src/components/ModalityTabs.css",
            "thought": "Building ModalityTabs component with stateful switching across distinct clinical treatment programs.",
            "tsx": """import React, { useState } from 'react';
import './ModalityTabs.css';

interface Modality {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  cadence: string;
  eligibility: string;
  physicianLead: string;
  clinicalCriteria: string[];
}

export function ModalityTabs() {
  const [activeTab, setActiveTab] = useState<string>('tms');

  const modalities: Record<string, Modality> = {
    tms: {
      id: 'tms',
      name: 'Repetitive Transcranial Magnetic Stimulation (rTMS)',
      subtitle: 'FDA-Cleared Non-Invasive Neuromodulation for Treatment-Resistant Depression & OCD',
      description: 'rTMS utilizes focused magnetic pulses to stimulate underactive neuronal circuits in the left dorsolateral prefrontal cortex. No systemic side effects, anesthesia, or cognitive impairment.',
      cadence: 'Daily 20-minute outpatient sessions over 6 weeks (36 total sessions)',
      eligibility: 'Failed >= 2 antidepressant trials of adequate dose and duration',
      physicianLead: 'Dr. Camille Laurent, MD (ABPN Board Certified Psychiatrist)',
      clinicalCriteria: [
        'FDA 510(k) Cleared Magstim Horizon System',
        'Motor threshold localized via electromyography (EMG)',
        'In-network covered by BCBS, Aetna, Cigna, Medicare Part B'
      ]
    },
    psychiatry: {
      id: 'psychiatry',
      name: 'Adult Outpatient Psychiatry & Pharmacogenomics',
      subtitle: 'Diagnostic Evaluation & DNA-Guided Medication Optimization',
      description: 'Comprehensive 90-minute psychiatric evaluations integrating GeneSight pharmacogenomic swab testing to identify individualized CYP450 enzyme metabolism rates before psychotropic prescribing.',
      cadence: 'Initial 90-min diagnostic + 30-min monthly titration reviews',
      eligibility: 'Adults (18+) with generalized anxiety, MDD, bipolar II, or ADHD',
      physicianLead: 'Dr. Aaron Meyer, MD (Harvard Fellow, ABPN Certified)',
      clinicalCriteria: [
        'GeneSight Psychotropic DNA Panel included in intake',
        'Electronic prescribing of controlled substances (DEA EPCS Certified)',
        'Quarterly metabolic and lab panels for lithium / atypical agents'
      ]
    },
    iop: {
      id: 'iop',
      name: 'Intensive Outpatient Program (IOP)',
      subtitle: 'Structured Step-Down Group & Individual Dialectical Behavior Therapy (DBT)',
      description: 'Accredited by CARF, our IOP provides evidence-based stabilization for clients transitioning from residential care or needing higher frequency support than weekly therapy.',
      cadence: '3 hours/day, 3 days/week (Monday, Wednesday, Friday)',
      eligibility: 'Adults requiring intensive behavioral stabilization without 24hr inpatient risk',
      physicianLead: 'Dr. Sarah Lin, PhD (Licensed Psychologist #PSY-29184)',
      clinicalCriteria: [
        'Full adherent DBT skills curriculum (Mindfulness, Distress Tolerance)',
        'Weekly individual therapy + multi-family group modules',
        '24/7 clinician skills-coaching line for enrolled clients'
      ]
    }
  };

  const current = modalities[activeTab] || modalities.tms;

  return (
    <section className="solace-tabs" id="modalities">
      <div className="solace-tabs__container">
        <div className="solace-tabs__header">
          <span className="solace-tabs__tag">EVIDENCE-BASED CONTINUUM</span>
          <h2 className="solace-tabs__title">Clinical Treatment Modalities</h2>
          <p className="solace-tabs__desc">
            Explore our specialized behavioral tracks. Each modality adheres to American Psychiatric Association (APA) guidelines and CARF accreditation metrics.
          </p>
        </div>

        <div className="solace-tabs__nav" role="tablist" aria-label="Treatment Modalities">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'tms'}
            className={`solace-tabs__btn ${activeTab === 'tms' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('tms')}
          >
            Interventional TMS
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'psychiatry'}
            className={`solace-tabs__btn ${activeTab === 'psychiatry' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('psychiatry')}
          >
            Psychiatry & Genomics
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'iop'}
            className={`solace-tabs__btn ${activeTab === 'iop' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('iop')}
          >
            Intensive Outpatient (IOP)
          </button>
        </div>

        <div className="solace-tabs__panel" role="tabpanel">
          <div className="solace-tabs__panel-top">
            <span className="solace-tabs__lead-doc">{current.physicianLead}</span>
            <h3 className="solace-tabs__panel-title">{current.name}</h3>
            <p className="solace-tabs__panel-sub">{current.subtitle}</p>
          </div>

          <p className="solace-tabs__panel-body">{current.description}</p>

          <div className="solace-tabs__spec-grid">
            <div className="solace-tabs__spec-card">
              <span className="solace-tabs__spec-title">Schedule & Cadence:</span>
              <span className="solace-tabs__spec-value">{current.cadence}</span>
            </div>
            <div className="solace-tabs__spec-card">
              <span className="solace-tabs__spec-title">Clinical Eligibility:</span>
              <span className="solace-tabs__spec-value">{current.eligibility}</span>
            </div>
          </div>

          <div className="solace-tabs__criteria-box">
            <span className="solace-tabs__crit-title">Clinical Quality Benchmarks:</span>
            <ul className="solace-tabs__crit-list">
              {current.clinicalCriteria.map((crit, idx) => (
                <li key={idx} className="solace-tabs__crit-item">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  {crit}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.solace-tabs {
  background-color: #f8fafc;
  padding: 4.5rem 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.solace-tabs__container {
  max-width: 1080px;
  margin: 0 auto;
}

.solace-tabs__header {
  margin-bottom: 2.5rem;
  text-align: center;
}

.solace-tabs__tag {
  font-size: 0.75rem;
  font-weight: 700;
  color: #4338ca;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.solace-tabs__title {
  font-size: 2.2rem;
  font-weight: 800;
  color: #1e1b4b;
  margin: 0.4rem 0 0.5rem 0;
}

.solace-tabs__desc {
  font-size: 1rem;
  color: #64748b;
  max-width: 680px;
  margin: 0 auto;
  line-height: 1.5;
}

.solace-tabs__nav {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.solace-tabs__btn {
  border: 1px solid #cbd5e1;
  background-color: #ffffff;
  padding: 0.65rem 1.25rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
}

.solace-tabs__btn.is-active {
  background-color: #4338ca;
  color: #ffffff;
  border-color: #4338ca;
  box-shadow: 0 2px 4px rgba(67, 56, 202, 0.2);
}

.solace-tabs__panel {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 2.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.solace-tabs__lead-doc {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #4338ca;
  display: block;
  margin-bottom: 0.35rem;
}

.solace-tabs__panel-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: #1e1b4b;
  margin: 0 0 0.35rem 0;
}

.solace-tabs__panel-sub {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0 0 1.25rem 0;
}

.solace-tabs__panel-body {
  font-size: 1rem;
  line-height: 1.6;
  color: #334155;
  margin: 0 0 2rem 0;
}

.solace-tabs__spec-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin-bottom: 2rem;
}

.solace-tabs__spec-card {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 1.25rem;
  border-radius: 8px;
}

.solace-tabs__spec-title {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  margin-bottom: 0.35rem;
}

.solace-tabs__spec-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
}

.solace-tabs__criteria-box {
  background-color: #f5f3ff;
  border: 1px solid #ddd6fe;
  border-radius: 8px;
  padding: 1.25rem;
}

.solace-tabs__crit-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #5b21b6;
  text-transform: uppercase;
  display: block;
  margin-bottom: 0.6rem;
}

.solace-tabs__crit-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.solace-tabs__crit-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #334155;
}

.solace-tabs__crit-item svg {
  width: 14px;
  height: 14px;
  fill: #6d28d9;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .solace-tabs__spec-grid {
    grid-template-columns: 1fr;
  }
}
"""
        },
        {
            "name": "InsuranceVerification",
            "instruction": "insurance verification matrix with APA licensed psychologist credentials, NPI number, and in-network payer breakdown. Files: src/components/InsuranceVerification.tsx + src/components/InsuranceVerification.css",
            "tsx_path": "src/components/InsuranceVerification.tsx",
            "css_path": "src/components/InsuranceVerification.css",
            "thought": "Building structural credibility section detailing in-network insurance payers and state licensing numbers.",
            "tsx": """import React from 'react';
import './InsuranceVerification.css';

export function InsuranceVerification() {
  const payers = [
    { name: "Blue Shield of California / Anthem", status: "Tier 1 In-Network", notes: "Direct claims submission for psychotherapy, med management, and IOP" },
    { name: "Aetna Behavioral Health", status: "In-Network Provider", notes: "Pre-authorized TMS protocol coverage with zero copay after deductible" },
    { name: "Cigna & Evernorth", status: "In-Network Provider", notes: "Telehealth parity and in-person outpatient psychotherapy" },
    { name: "Medicare Part B (Clinical)", status: "Participating Provider", notes: "Psychiatric diagnostic evaluations and medical management" }
  ];

  return (
    <section className="solace-ins" id="insurance">
      <div className="solace-ins__container">
        <div className="solace-ins__header">
          <span className="solace-ins__tag">FINANCIAL & COVERAGE TRANSPARENCY</span>
          <h2 className="solace-ins__title">In-Network Insurance & State Credentials</h2>
          <p className="solace-ins__desc">
            We believe mental health care should be accessible. Solace contracts directly with major health plans to minimize out-of-pocket patient expense.
          </p>
        </div>

        <div className="solace-ins__grid">
          {payers.map((payer, idx) => (
            <div key={idx} className="solace-ins__card">
              <div className="solace-ins__card-top">
                <span className="solace-ins__badge">{payer.status}</span>
              </div>
              <h3 className="solace-ins__payer-name">{payer.name}</h3>
              <p className="solace-ins__payer-notes">{payer.notes}</p>
            </div>
          ))}
        </div>

        <div className="solace-ins__credentials-strip">
          <div className="solace-ins__cred-item">
            <strong>State Board of Psychology:</strong> California License #PSY-29184
          </div>
          <div className="solace-ins__cred-item">
            <strong>Medical Board of California:</strong> Physician License #C-184920
          </div>
          <div className="solace-ins__cred-item">
            <strong>Organizational NPI:</strong> #1849204910
          </div>
          <div className="solace-ins__cred-item">
            <strong>CARF Program ID:</strong> #291840-BH
          </div>
        </div>
      </div>
    </section>
  );
}
""",
            "css": """.solace-ins {
  background-color: #ffffff;
  padding: 4.5rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.solace-ins__container {
  max-width: 1080px;
  margin: 0 auto;
}

.solace-ins__header {
  margin-bottom: 2.5rem;
  text-align: center;
}

.solace-ins__tag {
  font-size: 0.75rem;
  font-weight: 700;
  color: #4338ca;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.solace-ins__title {
  font-size: 2.2rem;
  font-weight: 800;
  color: #1e1b4b;
  margin: 0.4rem 0 0.5rem 0;
}

.solace-ins__desc {
  font-size: 1rem;
  color: #64748b;
  max-width: 680px;
  margin: 0 auto;
  line-height: 1.5;
}

.solace-ins__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}

.solace-ins__card {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
}

.solace-ins__card-top {
  margin-bottom: 0.75rem;
}

.solace-ins__badge {
  background-color: #e0e7ff;
  color: #4338ca;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.solace-ins__payer-name {
  font-size: 1.15rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 0.35rem 0;
}

.solace-ins__payer-notes {
  font-size: 0.8125rem;
  color: #64748b;
  line-height: 1.4;
  margin: 0;
}

.solace-ins__credentials-strip {
  background-color: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 1rem;
  font-size: 0.8125rem;
  color: #334155;
}

.solace-ins__cred-item strong {
  color: #0f172a;
}

@media (max-width: 768px) {
  .solace-ins__grid {
    grid-template-columns: 1fr;
  }
}
"""
        },
        {
            "name": "Footer",
            "instruction": "psychiatric practice footer with 988 lifeline restatement, HIPAA disclosures, and California licensing citations. Files: src/components/Footer.tsx + src/components/Footer.css",
            "tsx_path": "src/components/Footer.tsx",
            "css_path": "src/components/Footer.css",
            "thought": "Building psychiatric practice footer with mental health statutory crisis disclosures.",
            "tsx": """import React from 'react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="solace-footer" role="contentinfo">
      <div className="solace-footer__container">
        <div className="solace-footer__row">
          <div className="solace-footer__col-brand">
            <span className="solace-footer__brand-title">Solace Integrative Psychiatric & Behavioral Health</span>
            <p className="solace-footer__brand-p">
              Licensed outpatient psychiatric clinic and CARF-accredited behavioral health provider serving San Francisco and Northern California.
            </p>
            <div className="solace-footer__lic-box">
              <span>CA Board of Psychology #PSY-29184</span>
              <span>CA Medical Board #C-184920</span>
              <span>NPI Organization ID #1849204910</span>
            </div>
          </div>

          <div className="solace-footer__col">
            <h4 className="solace-footer__col-title">San Francisco Office</h4>
            <address className="solace-footer__addr">
              450 Sutter Street, Suite 1800<br />
              San Francisco, CA 94108<br />
              Direct: +1 (415) 555-0177<br />
              intake@solace-psych.org
            </address>
          </div>

          <div className="solace-footer__col">
            <h4 className="solace-footer__col-title">Crisis Support</h4>
            <p className="solace-footer__crisis">
              If you are in acute crisis, please call or text <strong>988</strong> immediately to speak with the Suicide & Crisis Lifeline, or go to the nearest emergency room.
            </p>
          </div>
        </div>

        <div className="solace-footer__bottom">
          <div className="solace-footer__copy">
            © {new Date().getFullYear()} Solace Psychiatric Health. All rights reserved.
          </div>
          <div className="solace-footer__legal">
            <a href="#hipaa">HIPAA Privacy Notice</a>
            <a href="#carf">CARF Accreditation</a>
            <a href="#telehealth">Telehealth Informed Consent</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
""",
            "css": """.solace-footer {
  background-color: #0f172a;
  color: #94a3b8;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 0.8125rem;
  padding: 3.5rem 1.5rem 2rem;
}

.solace-footer__container {
  max-width: 1080px;
  margin: 0 auto;
}

.solace-footer__row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 2.5rem;
  margin-bottom: 2.5rem;
}

.solace-footer__brand-title {
  display: block;
  font-size: 1.05rem;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 0.5rem;
}

.solace-footer__brand-p {
  line-height: 1.5;
  color: #94a3b8;
  margin: 0 0 1rem 0;
  max-width: 440px;
}

.solace-footer__lic-box {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.75rem;
  color: #a5b4fc;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.solace-footer__col-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #f8fafc;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem 0;
}

.solace-footer__addr {
  font-style: normal;
  line-height: 1.6;
  color: #94a3b8;
}

.solace-footer__crisis {
  line-height: 1.5;
  color: #cbd5e1;
  margin: 0;
}

.solace-footer__crisis strong {
  color: #f59e0b;
}

.solace-footer__bottom {
  border-top: 1px solid #1e293b;
  padding-top: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.solace-footer__copy {
  font-size: 0.75rem;
  color: #64748b;
}

.solace-footer__legal {
  display: flex;
  gap: 1.5rem;
}

.solace-footer__legal a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.75rem;
  transition: color 0.15s ease;
}

.solace-footer__legal a:hover {
  color: #a5b4fc;
}

@media (max-width: 768px) {
  .solace-footer__row {
    grid-template-columns: 1fr;
  }
}
"""
        }
    ]
    trajs.append(make_traj("site_healthcare_tabs_solace", t3_brief, t3_sections))

    return trajs
