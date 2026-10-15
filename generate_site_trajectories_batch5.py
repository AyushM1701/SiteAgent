#!/usr/bin/env python3
"""
generate_site_trajectories_batch5.py - Batch 5 of Gold-Standard Site Trajectories (50 Modern Real-World Domains).

Generates 50 complete, multi-turn, full-website trajectories adhering strictly to
the ChatML schema and XML tool-calling protocol defined in agent_protocol.py.
Integrates layout archetyping (grid, timeline, tabs, split_hero, editorial, bento),
domain-specific authentic copy, and scoped modern CSS.

Outputs:
  site_trajectories_batch5.jsonl
  data/site_trajectories_batch5.jsonl
"""

import json
import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))

from agent_protocol import SITE_AGENT_SYSTEM_PROMPT
from site_brief import LayoutArchetype, select_layout_archetype, _LAYOUT_ARCHETYPE_GUIDELINES, _MOTION_VOCABULARY


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
    return f"<thought>\n{text}\n</thought>"


def finish(text):
    return f"<finish>\n{text}\n</finish>"


# ── 50 Domain Specifications ──────────────────────────────────────────────────


DOMAINS = [
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
            {"title": "OTel Native Exporter", "tag": "OpenTelemetry", "desc": "Stream high-fidelity kernel metrics into existing Prometheus, Datadog, and Grafana pipelines seamlessly."}
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
        "primary": "#0e1526",
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
        "hero_sub": "Translating cutting-edge CAR-T cell constructs, neoantigen cancer vaccines, and immune checkpoint combinations into life-saving clinical remissions.",
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
            {"title": "Aether 65 Founders Edition", "tag": "Solid Brass Weight", "desc": "Seamless 6063 aerospace aluminium chassis with leaf-spring mounted FR4 plate and custom silicone acoustic dampener."},
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
            {"title": "Aura KT88 Push-Pull Integrated", "tag": "45W Ultra-Linear", "desc": "Effortless speaker driving dynamics with stepped ladder attenuator and precision DC filament bias regulation."},
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
            {"title": "Drone Photogrammetry Integration", "tag": "Context Alignment", "desc": "Seamless 3D compositing of proposed architectural forms into live high-resolution drone survey footage."}
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
            {"title": "AAA Game Dynamic Music System", "tag": "Interactive Wwise/FMOD", "desc": "Multi-tiered adaptive stem compositions shifting seamlessly between ambient exploration and high-intensity battle."},
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
        "primary": "#181a17",
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
        "hero_sub": "Elevated wooden decks immersed in ancient leadwood trees, silent solar-electric game drive cruisers, and uninterrupted views of elephant herds.",
        "section_name": "Lodge Experiences",
        "section_id": "experiences",
        "items": [
            {"title": "Canopy Tented Suites", "tag": "Elevated 8m", "desc": "Expansive canvas pavilions with outdoor open-air soaking tubs and wrap-around viewing decks over the floodplains."},
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
            {"title": "Sub-16ms Islanding Switchgear", "tag": "Zero Flicker", "desc": "Seamless automatic transition from utility grid to islanded mode during unexpected blackouts without data center interruption."},
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
        "hero_sub": "Over 15,000 square feet of seamless climbing terrain, adjustable LED Kilter and Tension boards, campus rungs, and continuous air purification.",
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



# Guarantee 100% unique accents across all domains
_seen_accents = set()
for _i, _d in enumerate(DOMAINS):
    _acc = _d["accent"]
    if _acc in _seen_accents:
        _r = int(_acc[1:3], 16)
        _g = int(_acc[3:5], 16)
        _b = int(_acc[5:7], 16)
        _r = min(255, max(0, _r + ((_i * 7) % 23) - 10))
        _g = min(255, max(0, _g + ((_i * 11) % 23) - 10))
        _b = min(255, max(0, _b + ((_i * 13) % 23) - 10))
        _d["accent"] = f"#{_r:02x}{_g:02x}{_b:02x}"
    _seen_accents.add(_d["accent"])

DOMAIN_ARCHETYPES = {
    "site_ai_vector_scale_db": "bento",
    "site_devops_ebpf_telemetry": "timeline",
    "site_ai_llm_gateway": "split_hero",
    "site_cloud_finops_optimizer": "bento",
    "site_dev_api_contract_test": "grid",
    "site_infra_bare_metal_cloud": "tabs",
    "site_database_distributed_sql": "bento",
    "site_quantum_circuits_lab": "editorial",
    "site_telehealth_neurology": "tabs",
    "site_biomechanics_sports_rehab": "timeline",
    "site_dermatology_precision_skin": "grid",
    "site_pediatric_sensory_therapy": "split_hero",
    "site_cardiology_heart_rhythm": "bento",
    "site_fertility_nova_origins": "timeline",
    "site_oncology_immunotherapy_inst": "editorial",
    "site_keyboards_bespoke_keebs": "bento",
    "site_perfumery_botanical_scents": "editorial",
    "site_horology_vintage_watches": "editorial",
    "site_ceramics_stone_and_ember": "timeline",
    "site_olive_oil_estate_grove": "grid",
    "site_tailor_savile_bespoke": "editorial",
    "site_audio_vacuum_tube_amps": "split_hero",
    "site_knives_damascus_forge": "timeline",
    "site_tea_ancient_puerh_vault": "editorial",
    "site_studio_vivid_3d_motion": "split_hero",
    "site_arch_viz_hyper_real": "editorial",
    "site_audio_film_scoring_lab": "split_hero",
    "site_brand_collective_monolith": "tabs",
    "site_lighting_architectural_lumen": "grid",
    "site_vfx_virtual_production": "bento",
    "site_chalet_alpen_solitude": "tabs",
    "site_train_silk_road_express": "timeline",
    "site_lodge_savanna_canopy": "tabs",
    "site_matcha_kyoto_ceremony": "editorial",
    "site_bathhouse_nordic_sauna": "grid",
    "site_retreat_zen_monastery": "editorial",
    "site_vineyard_domaine_solis": "timeline",
    "site_resort_coral_atoll_overwater": "tabs",
    "site_solar_microgrid_energy": "bento",
    "site_yacht_electric_marine": "split_hero",
    "site_leather_artisan_saddlery": "grid",
    "site_acoustics_soundproofing_pro": "tabs",
    "site_neon_artisan_glassworks": "split_hero",
    "site_bike_aerodynamic_fit_lab": "timeline",
    "site_drone_lidar_mapping": "bento",
    "site_hydroponics_urban_harvest": "grid",
    "site_restoration_midcentury_modern": "editorial",
    "site_coffee_single_origin_lab": "tabs",
    "site_climbing_summit_bouldering": "split_hero",
    "site_whiskey_highland_cask": "grid"
}

DOMAIN_DESCRIPTIONS = {
    "site_ai_vector_scale_db": "Sub-millisecond approximate nearest neighbor indexing, SIMD acceleration, and multi-tenant vector clustering at scale.",
    "site_devops_ebpf_telemetry": "Kernel-level eBPF packet tracing, zero-overhead Kubernetes container telemetry, and distributed latency profiling.",
    "site_ai_llm_gateway": "Unified multi-provider LLM routing, latency-based load balancing, automated failover, and real-time semantic caching.",
    "site_cloud_finops_optimizer": "Automated cloud spend anomaly detection, idle resource remediation, and spot instance lifecycle management.",
    "site_dev_api_contract_test": "Automated OpenAPI and GraphQL schema validation, contract drift detection, and synthetic mock environment testing.",
    "site_infra_bare_metal_cloud": "High-performance unvirtualized bare-metal servers, NVMe storage fabrics, and 100Gbps redundant network interconnects.",
    "site_database_distributed_sql": "Globally distributed ACID transactions, raft consensus replication, and horizontal sharding for mission-critical data.",
    "site_quantum_circuits_lab": "Fault-tolerant superconducting qubit simulations, quantum gate benchmarking, and hybrid classical-quantum algorithms.",
    "site_telehealth_neurology": "Specialized virtual neurological consultations, continuous EEG monitoring analysis, and remote stroke follow-up care.",
    "site_biomechanics_sports_rehab": "High-speed 3D motion capture, force-plate kinetic assessments, and customized neuromuscular return-to-sport protocols.",
    "site_dermatology_precision_skin": "Advanced laser skin resurfacing, digital dermoscopy mole mapping, and personalized dermatological medical therapies.",
    "site_pediatric_sensory_therapy": "Sensory integration therapy, pediatric occupational therapy gyms, and neurodivergent developmental support.",
    "site_cardiology_heart_rhythm": "Electrophysiology study mapping, catheter arrhythmia ablation, and pacemaker telemetry monitoring for cardiac health.",
    "site_fertility_nova_origins": "Next-generation IVF embryology, pre-implantation genetic screening, and fertility preservation reproductive care.",
    "site_oncology_immunotherapy_inst": "Cellular CAR-T therapies, checkpoint inhibitor regimens, and personalized genomic tumor profiling for targeted treatments.",
    "site_keyboards_bespoke_keebs": "CNC-machined aluminum mechanical keyboards, hand-lubed linear switches, and gasket-mounted acoustics for enthusiasts.",
    "site_perfumery_botanical_scents": "Artisanal natural perfumery, rare botanical enfleurage extractions, and small-batch macerations hand-poured in Grasse.",
    "site_horology_vintage_watches": "Curated vintage mechanical timepieces, historical reference chronographs, and certified master horological restorations.",
    "site_ceramics_stone_and_ember": "Hand-built sculptural stoneware, wood-fired ash glazes, and minimalist ceramic vessels crafted from local clays.",
    "site_olive_oil_estate_grove": "Cold-pressed extra virgin olive oils from ancient Tuscan groves, estate bottled with certified polyphenol counts.",
    "site_tailor_savile_bespoke": "Hand-stitched bespoke two-piece suits, British wool fabrics, and traditional floating canvas tailoring on Savile Row.",
    "site_audio_vacuum_tube_amps": "Point-to-point wired single-ended triode vacuum tube amplifiers engineered for pristine audiophile harmonic warmth.",
    "site_knives_damascus_forge": "Hand-forged multi-layer Damascus kitchen knives, custom stabilized burls, and razor-sharp traditional Japanese bevels.",
    "site_tea_ancient_puerh_vault": "Centuries-old wild arbor puerh tea cakes, clean underground dry storage, and ceremonial Gongfu tasting flights.",
    "site_studio_vivid_3d_motion": "Photorealistic 3D product animations, kinetic title typography, and dynamic visual simulations for global brands.",
    "site_arch_viz_hyper_real": "Hyper-realistic architectural CGI renderings, spatial lighting simulations, and real-time interactive interior walkthroughs.",
    "site_audio_film_scoring_lab": "Orchestral composition, bespoke analog synthesizer soundscapes, and surround acoustic mixing for cinematic productions.",
    "site_brand_collective_monolith": "End-to-end brand identity architecture, design systems, and digital packaging experiences for category leaders.",
    "site_lighting_architectural_lumen": "Specification-grade architectural LED fixtures, human-centric circadian control, and integrated museum optics.",
    "site_vfx_virtual_production": "Real-time LED volume virtual production stages, camera tracking, and in-camera VFX environments powered by Unreal Engine.",
    "site_chalet_alpen_solitude": "Exclusive alpine ski chalets featuring panoramic mountain views, private cedar saunas, and slopeside concierge services.",
    "site_train_silk_road_express": "Luxury transcontinental train journeys across ancient trade routes with private en-suite sleeper cars and fine dining.",
    "site_lodge_savanna_canopy": "Sustainable eco-lodge accommodations nestled in the Serengeti canopy, offering zero-emission solar safari excursions.",
    "site_matcha_kyoto_ceremony": "Ceremonial stone-ground Uji matcha, seasonal handmade wagashi confections, and traditional tea ceremony sessions.",
    "site_bathhouse_nordic_sauna": "Nordic thermal cycling facilities, wood-fired Finnish saunas, cold plunge waterfalls, and eucalyptus steam rooms.",
    "site_retreat_zen_monastery": "Silent meditation retreats, Soto Zen zazen practice, and mindful monastic living in the forested Pacific Northwest mountains.",
    "site_vineyard_domaine_solis": "Demeter-certified biodynamic viticulture, low-intervention fermentation, and limestone-mineral estate wines.",
    "site_resort_coral_atoll_overwater": "Private overwater thatched villas suspended above a protected coral lagoon with direct access to house reef diving.",
    "site_solar_microgrid_energy": "Decentralized industrial microgrid systems combining high-capacity battery storage and intelligent grid-islanding.",
    "site_yacht_electric_marine": "Hydrofoil electric marine yachts delivering silent, zero-emission coastal cruising with solar-assisted recharging.",
    "site_leather_artisan_saddlery": "Hand-stitched vegetable-tanned leather goods, solid brass hardware, and heirloom equestrian accessories made to last.",
    "site_acoustics_soundproofing_pro": "Broadcast studio acoustic isolation, custom diffusion paneling, and calibrated noise mitigation engineering.",
    "site_neon_artisan_glassworks": "Hand-bent gas-discharge neon sculptures, custom typography installations, and architectural vintage neon restorations.",
    "site_bike_aerodynamic_fit_lab": "Wind-tunnel validated cycling biomechanics, custom 3D printed saddles, and precision cleat alignment optimizations.",
    "site_drone_lidar_mapping": "High-density airborne LiDAR terrain mapping, 3D point cloud generation, and volumetric infrastructure surveys.",
    "site_hydroponics_urban_harvest": "Controlled-environment vertical aeroponic farms producing pesticide-free culinary herbs and greens year-round.",
    "site_restoration_midcentury_modern": "Master conservation of Scandinavian teak furniture, Danish paper cord weaving, and period-correct lacquer restoration.",
    "site_coffee_single_origin_lab": "Direct-trade anaerobic coffee microlots, sensory cupping evaluations, and tailored roast profiles for specialty caf\u00e9s.",
    "site_climbing_summit_bouldering": "World-class competition bouldering terrain, hydraulic adjustable training boards, and comprehensive athletic conditioning.",
    "site_whiskey_highland_cask": "Single cask cask-strength Scottish highland whiskies aged in bespoke first-fill Oloroso sherry and bourbon casks."
}

# Enrich domains with archetype and authentic domain-specific copy
for d in DOMAINS:
    d["layout_archetype"] = DOMAIN_ARCHETYPES.get(d["id"], "grid")
    d["catalog_desc"] = DOMAIN_DESCRIPTIONS.get(
        d["id"],
        f"Dedicated to {d['tagline'].lower()}, delivering highest-caliber standards and verified quality."
    )


def build_brief_xml(d, layout_archetype="grid"):
    items_xml = []
    for item in d["items"]:
        items_xml.append(f'  <item name="{item["title"]}" tag="{item["tag"]}" description="{item["desc"]}" />')
    items_str = "\n".join(items_xml)
    guidelines = _LAYOUT_ARCHETYPE_GUIDELINES.get(layout_archetype, "")
    motion_obj = _MOTION_VOCABULARY.get(layout_archetype, "")
    motion_guidelines = motion_obj.get("guidelines", str(motion_obj)) if isinstance(motion_obj, dict) else str(motion_obj)

    return f"""<content_brief>
  <business_name>{d["name"]}</business_name>
  <tagline>{d["tagline"]}</tagline>
  <business_type>{d["type"]}</business_type>
  <layout_archetype>{layout_archetype}</layout_archetype>
  <layout_guidelines>{guidelines}</layout_guidelines>
  <motion_guidelines>{motion_guidelines}</motion_guidelines>
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


def make_hero_code(p, d, layout_archetype):
    accent_r = int(d['accent'][1:3], 16)
    accent_g = int(d['accent'][3:5], 16)
    accent_b = int(d['accent'][5:7], 16)

    if layout_archetype == "bento":
        t2_user = (
            f"Write the Hero section: high-tech centered banner with tagline as h1, ambient radial glow, "
            f"subheading, dual CTAs, and a high-impact metric highlight strip. Files: src/components/Hero.tsx + src/components/Hero.css"
        )
        t2_thought = (
            f"Header was approved. Now I'll create the Hero section for {d['name']} using the Bento high-tech layout. "
            f"The headline will render the tagline in {d['heading_font']} typography. "
            f"I'll add radial ambient glowing backdrops using {d['accent']} at 16% opacity, supporting copy, "
            f"a primary '{d['cta']}' button, secondary link to #{d['section_id']}, and a live metric highlights strip."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--bento" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__glow" aria-hidden="true" />
      <div className="{p}-hero__inner">
        <div className="{p}-hero__badge">
          <span className="{p}-hero__badge-pulse" aria-hidden="true" />
          <span>{d['name']} · Verified</span>
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

        <div className="{p}-hero__metrics" role="group" aria-label="Key Highlights">
          <div className="{p}-hero__metric">
            <span className="{p}-hero__metric-value">99.9%</span>
            <span className="{p}-hero__metric-label">Reliability Index</span>
          </div>
          <div className="{p}-hero__metric">
            <span className="{p}-hero__metric-value">24/7</span>
            <span className="{p}-hero__metric-label">Dedicated Support</span>
          </div>
          <div className="{p}-hero__metric">
            <span className="{p}-hero__metric-value">5.0★</span>
            <span className="{p}-hero__metric-label">Client Trust Score</span>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 86vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: {d['primary']};
  overflow: hidden;
  padding: 5rem 2rem;
}}

.{p}-hero__glow {{
  position: absolute;
  top: 10%;
  left: 50%;
  transform: translateX(-50%);
  width: 750px;
  height: 500px;
  border-radius: 50%;
  background: radial-gradient(ellipse at center, rgba({accent_r}, {accent_g}, {accent_b}, 0.16) 0%, transparent 70%);
  pointer-events: none;
  filter: blur(24px);
}}

.{p}-hero__inner {{
  position: relative;
  z-index: 1;
  max-width: 880px;
  margin: 0 auto;
  text-align: center;
}}

.{p}-hero__badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 1rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.08);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.22);
  border-radius: 999px;
  color: #e4e4e7;
  font-size: 0.82rem;
  font-weight: 500;
  margin-bottom: 1.5rem;
}}

.{p}-hero__badge-pulse {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: {d['accent']};
  box-shadow: 0 0 8px {d['accent']};
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.4rem, 5.5vw, 4.2rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.12;
  letter-spacing: -0.02em;
  margin: 0 0 1.5rem;
}}

.{p}-hero__subtitle {{
  font-size: 1.15rem;
  color: #a1a1aa;
  line-height: 1.7;
  max-width: 640px;
  margin: 0 auto 2.5rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 3rem;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
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
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba({accent_r}, {accent_g}, {accent_b}, 0.35);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.04);
  color: #fafafa;
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.32);
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-secondary:hover {{
  border-color: {d['accent']};
  color: {d['accent']};
  transform: translateY(-2px);
}}

.{p}-hero__metrics {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  max-width: 640px;
  margin: 0 auto;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-hero__metric {{
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}}

.{p}-hero__metric-value {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: #fafafa;
}}

.{p}-hero__metric-label {{
  font-size: 0.8rem;
  color: #71717a;
}}

@media (max-width: 600px) {{
  .{p}-hero__metrics {{ grid-template-columns: 1fr; gap: 1rem; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-hero,
  .{p}-hero__btn-primary,
  .{p}-hero__btn-secondary,
  .{p}-hero__atmosphere {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }}
}}
"""

    elif layout_archetype == "split_hero":
        t2_user = (
            f"Write the Hero section: 50/50 split-screen layout with tagline as h1 and dual CTAs on the left, "
            f"and an interactive preview card with ambient glow on the right. Files: src/components/Hero.tsx + src/components/Hero.css"
        )
        t2_thought = (
            f"Header approved. Building split-screen Hero for {d['name']}. "
            f"The left column showcases the tagline and primary CTAs. The right column displays an interactive preview card "
            f"with ambient glow highlighting {d['name']}'s flagship capabilities."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--split" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__inner">
        <div className="{p}-hero__left">
          <div className="{p}-hero__badge">
            <span className="{p}-hero__badge-pulse" aria-hidden="true" />
            <span>{d['name']} Platform</span>
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

        <div className="{p}-hero__right">
          <div className="{p}-hero__aura" aria-hidden="true" />
          <div className="{p}-hero__card">
            <div className="{p}-hero__card-header">
              <span className="{p}-hero__card-dot" />
              <span className="{p}-hero__card-dot" />
              <span className="{p}-hero__card-dot" />
              <span className="{p}-hero__card-status">LIVE SYSTEM ACTIVE</span>
            </div>
            <div className="{p}-hero__card-body">
              <p className="{p}-hero__card-title">{d['items'][0]['title']}</p>
              <p className="{p}-hero__card-desc">{d['items'][0]['desc']}</p>
              <div className="{p}-hero__card-stat">
                <span className="{p}-hero__card-tag">{d['items'][0]['tag']}</span>
                <span className="{p}-hero__card-metric">Optimized</span>
              </div>
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
  min-height: 86vh;
  display: flex;
  align-items: center;
  background: {d['primary']};
  overflow: hidden;
  padding: 5rem 2rem;
}}

.{p}-hero__inner {{
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 4rem;
  align-items: center;
  position: relative;
  z-index: 1;
}}

.{p}-hero__badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 1rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.08);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.22);
  border-radius: 999px;
  color: #e4e4e7;
  font-size: 0.82rem;
  font-weight: 500;
  margin-bottom: 1.5rem;
}}

.{p}-hero__badge-pulse {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: {d['accent']};
  box-shadow: 0 0 8px {d['accent']};
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.2rem, 4.5vw, 3.6rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.14;
  letter-spacing: -0.02em;
  margin: 0 0 1.5rem;
}}

.{p}-hero__subtitle {{
  font-size: 1.1rem;
  color: #a1a1aa;
  line-height: 1.7;
  margin: 0 0 2.2rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2rem;
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
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba({accent_r}, {accent_g}, {accent_b}, 0.35);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.04);
  color: #fafafa;
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.32);
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-secondary:hover {{
  border-color: {d['accent']};
  color: {d['accent']};
  transform: translateY(-2px);
}}

.{p}-hero__right {{
  position: relative;
}}

.{p}-hero__aura {{
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 420px;
  height: 420px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba({accent_r}, {accent_g}, {accent_b}, 0.24) 0%, transparent 70%);
  filter: blur(32px);
  pointer-events: none;
}}

.{p}-hero__card {{
  position: relative;
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 2rem;
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.4);
}}

.{p}-hero__card-header {{
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-hero__card-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}}

.{p}-hero__card-status {{
  margin-left: auto;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: {d['accent']};
}}

.{p}-hero__card-title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-hero__card-desc {{
  font-size: 0.95rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0 0 1.5rem;
}}

.{p}-hero__card-stat {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.{p}-hero__card-tag {{
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 600;
}}

.{p}-hero__card-metric {{
  color: #fafafa;
  font-size: 0.85rem;
  font-weight: 600;
}}

@media (max-width: 900px) {{
  .{p}-hero__inner {{ grid-template-columns: 1fr; gap: 3rem; }}
}}

.{p}-hero__left {{
  animation: {p}HeroLeftEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0ms both;
}}

.{p}-hero__right {{
  animation: {p}HeroRightEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 160ms both;
}}

@keyframes {p}HeroLeftEnter {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes {p}HeroRightEnter {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-hero__left,
  .{p}-hero__right,
  .{p}-hero__btn-primary,
  .{p}-hero__btn-secondary {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""

    elif layout_archetype == "editorial":
        t2_user = (
            f"Write the Hero section: typography-dominant editorial magazine banner with serif title, masthead issue tag, "
            f"subheading, and minimal CTAs. Files: src/components/Hero.tsx + src/components/Hero.css"
        )
        t2_thought = (
            f"Header approved. Building Editorial Hero for {d['name']}. "
            f"Highlighting high-contrast {d['heading_font']} typography, a masthead volume header, "
            f"literary prose, and clean architectural button borders without glowing artifacts."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--editorial" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__inner">
        <div className="{p}-hero__masthead">
          <span>{d['name'].upper()} · ARCHIVAL FOLIO</span>
          <span>EST. 2026</span>
        </div>

        <hr className="{p}-hero__divider" />

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
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 82vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: {d['primary']};
  padding: 5rem 2rem;
}}

.{p}-hero__inner {{
  max-width: 920px;
  margin: 0 auto;
  text-align: center;
}}

.{p}-hero__masthead {{
  display: flex;
  justify-content: space-between;
  font-family: monospace;
  font-size: 0.8rem;
  letter-spacing: 0.14em;
  color: {d['accent']};
  margin-bottom: 1.25rem;
}}

.{p}-hero__divider {{
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  margin: 0 0 2.5rem;
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', serif;
  font-size: clamp(2.5rem, 5.5vw, 4.4rem);
  font-weight: 700;
  color: #fafafa;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin: 0 0 1.75rem;
}}

.{p}-hero__subtitle {{
  font-size: 1.15rem;
  font-style: italic;
  color: #a1a1aa;
  line-height: 1.75;
  max-width: 680px;
  margin: 0 auto 2.75rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1.25rem;
  justify-content: center;
  flex-wrap: wrap;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
  background: {d['accent']};
  color: #0c0d12;
  font-weight: 700;
  font-size: 0.92rem;
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-primary:hover {{
  background: {d['accent_hover']};
  transform: translateY(-1px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.04);
  color: #fafafa;
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.32);
  font-weight: 600;
  font-size: 0.92rem;
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-secondary:hover {{
  border-color: {d['accent']};
  color: {d['accent']};
}}

.{p}-hero__inner {{
  animation: {p}EditorialHeroFade 0.65s ease-out;
}}

@keyframes {p}EditorialHeroFade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-hero__inner,
  .{p}-hero__btn-primary,
  .{p}-hero__btn-secondary {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""

    elif layout_archetype == "timeline":
        t2_user = (
            f"Write the Hero section: roadmap and process-driven banner with step indicator, "
            f"tagline as h1, subtitle, and sequential CTAs. Files: src/components/Hero.tsx + src/components/Hero.css"
        )
        t2_thought = (
            f"Header approved. Building Timeline-focused Hero for {d['name']}. "
            f"Emphasizing sequential roadmap progression, clear step indicators, and purposeful typography "
            f"without glowing ambient blobs."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--timeline" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__inner">
        <div className="{p}-hero__step-badge">
          <span className="{p}-hero__step-dot" />
          <span>Step 01 // Overview & Initiation</span>
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
            Follow the Roadmap &rarr;
          </a>
        </div>
      </div>
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 84vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: {d['primary']};
  padding: 5rem 2rem;
}}

.{p}-hero__inner {{
  max-width: 860px;
  margin: 0 auto;
  text-align: center;
}}

.{p}-hero__step-badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 1.1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  color: {d['accent']};
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
}}

.{p}-hero__step-dot {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: {d['accent']};
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.3rem, 5vw, 4rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 0 0 1.5rem;
}}

.{p}-hero__subtitle {{
  font-size: 1.15rem;
  color: #a1a1aa;
  line-height: 1.7;
  max-width: 640px;
  margin: 0 auto 2.5rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
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
  transform: translateY(-2px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.04);
  color: #fafafa;
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.32);
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-secondary:hover {{
  border-color: {d['accent']};
  color: {d['accent']};
}}

.{p}-hero__inner {{
  animation: {p}EditorialHeroFade 0.65s ease-out;
}}

@keyframes {p}EditorialHeroFade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-hero__inner,
  .{p}-hero__btn-primary,
  .{p}-hero__btn-secondary {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""

    elif layout_archetype == "tabs":
        t2_user = (
            f"Write the Hero section: directory-style showcase banner with category chips preview, "
            f"tagline as h1, subtitle, and dual action buttons. Files: src/components/Hero.tsx + src/components/Hero.css"
        )
        t2_thought = (
            f"Header approved. Building Tabs-aligned Hero for {d['name']}. "
            f"Highlighting interactive exploration with directory category tags, clean typography, "
            f"and zero ambient gradient artifacts."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--tabs" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__inner">
        <div className="{p}-hero__badge">
          <span>Explore Directory</span>
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

        <div className="{p}-hero__chips">
          <span className="{p}-hero__chip">Interactive Views</span>
          <span className="{p}-hero__chip">Instant Filtering</span>
          <span className="{p}-hero__chip">Full Specifications</span>
        </div>
      </div>
    </section>
  );
}}
"""
        t2_css = f""".{p}-hero {{
  position: relative;
  min-height: 84vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: {d['primary']};
  padding: 5rem 2rem;
}}

.{p}-hero__inner {{
  max-width: 860px;
  margin: 0 auto;
  text-align: center;
}}

.{p}-hero__badge {{
  display: inline-flex;
  padding: 0.35rem 1rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.08);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.22);
  border-radius: 999px;
  color: {d['accent']};
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.3rem, 5vw, 4rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 0 0 1.5rem;
}}

.{p}-hero__subtitle {{
  font-size: 1.15rem;
  color: #a1a1aa;
  line-height: 1.7;
  max-width: 640px;
  margin: 0 auto 2.5rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 2.5rem;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
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
  transform: translateY(-2px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.04);
  color: #fafafa;
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.32);
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-secondary:hover {{
  border-color: {d['accent']};
  color: {d['accent']};
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-hero,
  .{p}-hero__btn-primary,
  .{p}-hero__btn-secondary {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }}
}}

.{p}-hero__chips {{
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}}

.{p}-hero__chip {{
  padding: 0.35rem 0.85rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.06);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.18);
  border-radius: 6px;
  font-size: 0.78rem;
  color: #a1a1aa;
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-hero,
  .{p}-hero__btn-primary,
  .{p}-hero__btn-secondary {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }}
}}
"""

    else:  # grid
        t2_user = (
            f"Write the Hero section: clean structured catalog hero with tagline as h1, "
            f"subtitle, and dual CTAs. Files: src/components/Hero.tsx + src/components/Hero.css"
        )
        t2_thought = (
            f"Header approved. Building Grid-oriented Hero for {d['name']}. "
            f"Clean presentation of the brand headline, supporting copy, and direct links without glow effects."
        )
        t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero {p}-hero--grid" id="hero" aria-labelledby="{p}-hero-title">
      <div className="{p}-hero__inner">
        <div className="{p}-hero__badge">
          <span>{d['name']} Catalog</span>
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
  min-height: 84vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: {d['primary']};
  padding: 5rem 2rem;
}}

.{p}-hero__inner {{
  max-width: 860px;
  margin: 0 auto;
  text-align: center;
}}

.{p}-hero__badge {{
  display: inline-flex;
  padding: 0.35rem 1rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.08);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.22);
  border-radius: 999px;
  color: {d['accent']};
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
}}

.{p}-hero__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2.3rem, 5vw, 4rem);
  font-weight: 800;
  color: #fafafa;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 0 0 1.5rem;
}}

.{p}-hero__subtitle {{
  font-size: 1.15rem;
  color: #a1a1aa;
  line-height: 1.7;
  max-width: 640px;
  margin: 0 auto 2.5rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
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
  transform: translateY(-2px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.85rem 2.2rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.04);
  color: #fafafa;
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.32);
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-hero__btn-secondary:hover {{
  border-color: {d['accent']};
  color: {d['accent']};
}}

.{p}-hero__inner {{
  animation: {p}EditorialHeroFade 0.65s ease-out;
}}

@keyframes {p}EditorialHeroFade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-hero__inner,
  .{p}-hero__btn-primary,
  .{p}-hero__btn-secondary {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""

    return t2_user, t2_thought, t2_tsx, t2_css


def make_turn3_code(p, d, layout_archetype):
    accent_r = int(d['accent'][1:3], 16)
    accent_g = int(d['accent'][3:5], 16)
    accent_b = int(d['accent'][5:7], 16)
    sec_ts_name = d["section_name"].replace(" ", "").replace("&", "")
    items_json = json.dumps(d["items"], indent=2)
    catalog_desc = d["catalog_desc"]
    accent_r = int(d['accent'][1:3], 16)
    accent_g = int(d['accent'][3:5], 16)
    accent_b = int(d['accent'][5:7], 16)

    if layout_archetype == "bento":
        t3_user = (
            f"Write the {d['section_name']} section using a modern bento grid layout with heterogeneous card spans "
            f"(2x2 featured card with live status, 1x2 tall metric card with progress meter, and 1x1 modular cards). "
            f"Files: src/components/{sec_ts_name}.tsx + src/components/{sec_ts_name}.css"
        )
        t3_thought = (
            f"Now creating the core content component '{sec_ts_name}' for {d['name']} using the Bento Grid layout archetype. "
            f"I'll structure the {len(d['items'])} items with heterogeneous spans: a featured 2x2 showcase card, a tall 1x2 metric card, "
            f"and modular 1x1 cards with subtle borders ({d['surface']}) and accent highlights."
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
    <section className="{p}-bento" id="{d['section_id']}" aria-labelledby="{p}-bento-title">
      <div className="{p}-bento__inner">
        <div className="{p}-bento__header">
          <p className="{p}-bento__eyebrow">Modular Architecture</p>
          <h2 id="{p}-bento-title" className="{p}-bento__title">
            {d['section_name']}
          </h2>
          <p className="{p}-bento__desc">
            {catalog_desc}
          </p>
        </div>

        <div className="{p}-bento__grid">
          {{ITEMS.length > 0 && (
            <article className="{p}-bento__card {p}-bento__card--featured">
              <div className="{p}-bento__card-top">
                <span className="{p}-bento__badge">FLAGSHIP SYSTEM</span>
                <span className="{p}-bento__tag">{{ITEMS[0].tag}}</span>
              </div>
              <h3 className="{p}-bento__card-title">{{ITEMS[0].title}}</h3>
              <p className="{p}-bento__card-desc">{{ITEMS[0].desc}}</p>
              <div className="{p}-bento__card-footer">
                <span className="{p}-bento__status-dot" aria-hidden="true" />
                <span className="{p}-bento__status-text">Production Verified</span>
              </div>
            </article>
          )}}

          {{ITEMS.length > 1 && (
            <article className="{p}-bento__card {p}-bento__card--tall">
              <div className="{p}-bento__card-top">
                <span className="{p}-bento__index">02</span>
                <span className="{p}-bento__tag">{{ITEMS[1].tag}}</span>
              </div>
              <h3 className="{p}-bento__card-title">{{ITEMS[1].title}}</h3>
              <p className="{p}-bento__card-desc">{{ITEMS[1].desc}}</p>
              <div className="{p}-bento__meter">
                <div className="{p}-bento__meter-bar">
                  <div className="{p}-bento__meter-fill" style={{{{ width: '92%' }}}} />
                </div>
                <span className="{p}-bento__meter-label">92% Operational Efficiency</span>
              </div>
            </article>
          )}}

          {{ITEMS.slice(2).map((item, idx) => (
            <article key={{item.title}} className="{p}-bento__card {p}-bento__card--compact">
              <div className="{p}-bento__card-top">
                <span className="{p}-bento__index">0{{idx + 3}}</span>
                <span className="{p}-bento__tag">{{item.tag}}</span>
              </div>
              <h3 className="{p}-bento__card-title">{{item.title}}</h3>
              <p className="{p}-bento__card-desc">{{item.desc}}</p>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-bento {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}}

.{p}-bento__inner {{
  max-width: 1200px;
  margin: 0 auto;
}}

.{p}-bento__header {{
  text-align: center;
  max-width: 720px;
  margin: 0 auto 3.5rem;
}}

.{p}-bento__eyebrow {{
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin: 0 0 0.5rem;
}}

.{p}-bento__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-bento__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-bento__grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}}

.{p}-bento__card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}

.{p}-bento__card:hover {{
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}}

.{p}-bento__card--featured {{
  grid-column: span 2;
  grid-row: span 2;
  background: linear-gradient(145deg, {d['surface']} 0%, rgba(255, 255, 255, 0.03) 100%);
  border-color: rgba(255, 255, 255, 0.12);
}}

.{p}-bento__card--tall {{
  grid-column: span 1;
  grid-row: span 2;
}}

.{p}-bento__card--compact {{
  grid-column: span 1;
}}

.{p}-bento__card-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}}

.{p}-bento__badge {{
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: {d['accent']};
  text-transform: uppercase;
}}

.{p}-bento__index {{
  font-size: 0.85rem;
  font-weight: 700;
  color: #71717a;
}}

.{p}-bento__tag {{
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.08);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.2);
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  color: {d['accent']};
}}

.{p}-bento__card-title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-bento__card-desc {{
  font-size: 0.95rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0 0 1.5rem;
  flex: 1;
}}

.{p}-bento__card-footer {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}}

.{p}-bento__status-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: {d['accent']};
  box-shadow: 0 0 8px {d['accent']};
}}

.{p}-bento__status-text {{
  font-size: 0.82rem;
  font-weight: 600;
  color: #e4e4e7;
}}

.{p}-bento__meter {{
  margin-top: auto;
  padding-top: 1rem;
}}

.{p}-bento__meter-bar {{
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}

.{p}-bento__meter-fill {{
  height: 100%;
  background: {d['accent']};
  border-radius: 3px;
}}

.{p}-bento__meter-label {{
  font-size: 0.78rem;
  color: #a1a1aa;
  font-weight: 500;
}}

@media (max-width: 900px) {{
  .{p}-bento__grid {{
    grid-template-columns: 1fr;
  }}
  .{p}-bento__card--featured,
  .{p}-bento__card--tall {{
    grid-column: span 1;
    grid-row: span 1;
  }}
}}

.{p}-bento__card {{
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease;
}}

.{p}-bento__card--featured {{ animation: {p}BentoCardEnter 0.55s ease 0ms forwards; }}
.{p}-bento__card--tall {{ animation: {p}BentoCardEnter 0.55s ease 100ms forwards; }}
.{p}-bento__card--standard {{ animation: {p}BentoCardEnter 0.55s ease 200ms forwards; }}

@keyframes {p}BentoCardEnter {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.{p}-bento__card:hover {{
  transform: translateY(-4px);
  border-color: {d['accent']};
  box-shadow: 0 12px 32px -8px rgba({accent_r}, {accent_g}, {accent_b}, 0.28);
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-bento__card,
  .{p}-bento__card:hover,
  .{p}-bento__card--featured,
  .{p}-bento__card--tall,
  .{p}-bento__card--standard {{
    opacity: 1 !important;
    transform: none !important;
    animation: none !important;
    transition: none !important;
    box-shadow: none !important;
  }}
}}
"""

    elif layout_archetype == "editorial":
        t3_user = (
            f"Write the {d['section_name']} section using an editorial magazine layout: high-contrast serif typography, "
            f"masthead volume/date header, asymmetric pull-quote, multi-column narrative prose, and curated monograph cards. "
            f"Files: src/components/{sec_ts_name}.tsx + src/components/{sec_ts_name}.css"
        )
        t3_thought = (
            f"Now creating the core content component '{sec_ts_name}' for {d['name']} using the Editorial layout archetype. "
            f"I'll present the {len(d['items'])} items with literary sophistication: a masthead header, asymmetric pull-quote, "
            f"two-column prose, and numbered monograph chapters with Roman numerals."
        )
        chapters_data = [
            {"num": ["I", "II", "III", "IV", "V", "VI"][idx % 6], "title": it["title"], "tag": it["tag"], "desc": it["desc"]}
            for idx, it in enumerate(d["items"])
        ]
        chapters_json = json.dumps(chapters_data, indent=2)

        t3_tsx = f"""import React from 'react';
import './{sec_ts_name}.css';

interface Chapter {{
  num: string;
  title: string;
  tag: string;
  desc: string;
}}

const CHAPTERS: Chapter[] = {chapters_json};

export function {sec_ts_name}() {{
  return (
    <section className="{p}-editorial" id="{d['section_id']}" aria-labelledby="{p}-editorial-title">
      <div className="{p}-editorial__inner">
        <header className="{p}-editorial__masthead">
          <span className="{p}-editorial__volume">{d['name'].upper()} · ARCHIVAL FOLIO</span>
          <span className="{p}-editorial__date">EST. 2026</span>
        </header>

        <hr className="{p}-editorial__rule" />

        <div className="{p}-editorial__lead">
          <h2 id="{p}-editorial-title" className="{p}-editorial__headline">
            {d['section_name']}
          </h2>

          <blockquote className="{p}-editorial__pullquote">
            <span className="{p}-editorial__quote-mark" aria-hidden="true">&ldquo;</span>
            <p className="{p}-editorial__quote-text">
              {catalog_desc}
            </p>
            <cite className="{p}-editorial__quote-author">&mdash; Strategic Practice, {d['name']}</cite>
          </blockquote>
        </div>

        <div className="{p}-editorial__prose">
          <p className="{p}-editorial__paragraph {p}-editorial__paragraph--dropcap">
            Excellence within our discipline demands rigorous precision and deliberate execution. Every engagement is structured with unwavering focus, ensuring lasting client outcomes and institutional reliability.
          </p>
          <p className="{p}-editorial__paragraph">
            Through proven methodologies and decades of collective experience, we navigate complex landscapes with clarity, providing authoritative leadership and measurable strategic results.
          </p>
        </div>

        <hr className="{p}-editorial__rule" />

        <div className="{p}-editorial__chapters">
          <div className="{p}-editorial__chapters-header">
            <span className="{p}-editorial__chapters-tag">CURATED MONOGRAPHS</span>
            <h3 className="{p}-editorial__chapters-title">Selected Case Monographs & Treatises</h3>
          </div>

          <div className="{p}-editorial__chapters-grid">
            {{CHAPTERS.map((ch) => (
              <article key={{ch.title}} className="{p}-editorial__chapter-card">
                <div className="{p}-editorial__chapter-top">
                  <span className="{p}-editorial__chapter-num">{{ch.num}}</span>
                  <span className="{p}-editorial__chapter-tag">{{ch.tag}}</span>
                </div>
                <h4 className="{p}-editorial__chapter-title">{{ch.title}}</h4>
                <p className="{p}-editorial__chapter-desc">{{ch.desc}}</p>
                <a href="#footer" className="{p}-editorial__chapter-link">
                  Consult Portfolio &rarr;
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
        t3_css = f""".{p}-editorial {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  color: #fafafa;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-editorial__inner {{
  max-width: 1100px;
  margin: 0 auto;
}}

.{p}-editorial__masthead {{
  display: flex;
  justify-content: space-between;
  font-family: monospace;
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  color: {d['accent']};
  padding-bottom: 0.75rem;
}}

.{p}-editorial__rule {{
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
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
  font-family: '{d['heading_font']}', serif;
  font-size: clamp(2.4rem, 4.5vw, 3.6rem);
  font-weight: 700;
  color: #fafafa;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin: 0;
}}

.{p}-editorial__pullquote {{
  position: relative;
  margin: 0;
  padding: 1rem 0 1rem 2rem;
  border-left: 2px solid {d['accent']};
}}

.{p}-editorial__quote-mark {{
  position: absolute;
  top: -1.2rem;
  left: 1.2rem;
  font-size: 3.8rem;
  color: {d['accent']};
  opacity: 0.35;
  line-height: 1;
}}

.{p}-editorial__quote-text {{
  font-family: '{d['heading_font']}', serif;
  font-style: italic;
  font-size: 1.2rem;
  color: #fafafa;
  line-height: 1.6;
  margin: 0 0 0.75rem;
}}

.{p}-editorial__quote-author {{
  display: block;
  font-size: 0.8rem;
  color: #a1a1aa;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}

.{p}-editorial__prose {{
  column-count: 2;
  column-gap: 3.5rem;
  font-size: 1.05rem;
  line-height: 1.8;
  color: #a1a1aa;
  margin-bottom: 4rem;
}}

.{p}-editorial__paragraph {{
  margin: 0 0 1.5rem;
}}

.{p}-editorial__paragraph--dropcap::first-letter {{
  float: left;
  font-family: '{d['heading_font']}', serif;
  font-size: 3.6rem;
  line-height: 0.8;
  padding-right: 0.75rem;
  padding-top: 0.25rem;
  color: {d['accent']};
  font-weight: 700;
}}

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
  color: {d['accent']};
  margin-bottom: 0.5rem;
}}

.{p}-editorial__chapters-title {{
  font-family: '{d['heading_font']}', serif;
  font-size: 1.75rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0;
}}

.{p}-editorial__chapters-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.75rem;
}}

.{p}-editorial__chapter-card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
}}

.{p}-editorial__chapter-card:hover {{
  border-color: {d['accent']};
  transform: translateY(-2px);
}}

.{p}-editorial__chapter-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}}

.{p}-editorial__chapter-num {{
  font-family: '{d['heading_font']}', serif;
  font-size: 1.4rem;
  font-weight: 800;
  color: {d['accent']};
}}

.{p}-editorial__chapter-tag {{
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.12);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.25);
  border-radius: 4px;
  color: {d['accent']};
}}

.{p}-editorial__chapter-title {{
  font-family: '{d['heading_font']}', serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-editorial__chapter-desc {{
  font-size: 0.92rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0 0 1.25rem;
  flex: 1;
}}

.{p}-editorial__chapter-link {{
  color: {d['accent']};
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
}}

@media (max-width: 860px) {{
  .{p}-editorial__lead {{ grid-template-columns: 1fr; gap: 2rem; }}
  .{p}-editorial__prose {{ column-count: 1; }}
  .{p}-editorial__chapters-grid {{ grid-template-columns: 1fr; }}
}}

.{p}-editorial__lead,
.{p}-editorial__prose,
.{p}-editorial__chapter-card {{
  animation: {p}EditorialMonographFade 0.65s ease-out;
}}

@keyframes {p}EditorialMonographFade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-editorial__lead,
  .{p}-editorial__prose,
  .{p}-editorial__chapter-card {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""

    elif layout_archetype == "tabs":
        t3_user = (
            f"Write the {d['section_name']} section using an interactive tabs pattern: category tab switcher with useState, "
            f"active showcase panel, and responsive cards grid. Files: src/components/{sec_ts_name}.tsx + src/components/{sec_ts_name}.css"
        )
        t3_thought = (
            f"Now creating the core content component '{sec_ts_name}' for {d['name']} with the Tabs layout archetype. "
            f"I'll implement active category switching with React useState, displaying an interactive showcase panel for the selected item, "
            f"followed by a directory grid of all available {d['section_name'].lower()}."
        )
        t3_tsx = f"""import React, {{ useState }} from 'react';
import './{sec_ts_name}.css';

interface Item {{
  title: string;
  tag: string;
  desc: string;
}}

const ITEMS: Item[] = {items_json};

export function {sec_ts_name}() {{
  const [activeTab, setActiveTab] = useState(0);

  return (
    <section className="{p}-tabs" id="{d['section_id']}" aria-labelledby="{p}-tabs-title">
      <div className="{p}-tabs__inner">
        <div className="{p}-tabs__header">
          <p className="{p}-tabs__eyebrow">Interactive Directory</p>
          <h2 id="{p}-tabs-title" className="{p}-tabs__title">
            {d['section_name']}
          </h2>
          <p className="{p}-tabs__desc">
            {catalog_desc}
          </p>
        </div>

        <div className="{p}-tabs__nav" role="tablist" aria-label="{d['section_name']} Tabs">
          {{ITEMS.map((item, idx) => (
            <button
              key={{item.title}}
              type="button"
              role="tab"
              aria-selected={{activeTab === idx}}
              className={{`{p}-tabs__tab${{activeTab === idx ? ' {p}-tabs__tab--active' : ''}}`}}
              onClick={{() => setActiveTab(idx)}}
            >
              {{item.title}}
            </button>
          ))}}
        </div>

        <div className="{p}-tabs__showcase" role="tabpanel">
          <div className="{p}-tabs__panel-top">
            <span className="{p}-tabs__panel-tag">{{ITEMS[activeTab]?.tag}}</span>
            <span className="{p}-tabs__panel-index">Tier 0{{activeTab + 1}}</span>
          </div>
          <h3 className="{p}-tabs__panel-title">{{ITEMS[activeTab]?.title}}</h3>
          <p className="{p}-tabs__panel-desc">{{ITEMS[activeTab]?.desc}}</p>
          <div className="{p}-tabs__panel-footer">
            <a href="mailto:{d['contact']['email']}" className="{p}-tabs__btn">
              Inquire About {{ITEMS[activeTab]?.title}}
            </a>
          </div>
        </div>

        <div className="{p}-tabs__grid">
          {{ITEMS.map((item, idx) => (
            <div
              key={{item.title}}
              className={{`{p}-tabs__card${{activeTab === idx ? ' {p}-tabs__card--active' : ''}}`}}
              onClick={{() => setActiveTab(idx)}}
            >
              <div className="{p}-tabs__card-top">
                <span className="{p}-tabs__card-num">0{{idx + 1}}</span>
                <span className="{p}-tabs__card-tag">{{item.tag}}</span>
              </div>
              <h4 className="{p}-tabs__card-title">{{item.title}}</h4>
              <p className="{p}-tabs__card-desc">{{item.desc}}</p>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-tabs {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}}

.{p}-tabs__inner {{
  max-width: 1160px;
  margin: 0 auto;
}}

.{p}-tabs__header {{
  text-align: center;
  max-width: 700px;
  margin: 0 auto 3rem;
}}

.{p}-tabs__eyebrow {{
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin: 0 0 0.5rem;
}}

.{p}-tabs__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-tabs__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-tabs__nav {{
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 2.5rem;
}}

.{p}-tabs__tab {{
  padding: 0.65rem 1.4rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.05);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.2);
  border-radius: 8px;
  color: #a1a1aa;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}}

.{p}-tabs__tab:hover {{
  color: #fafafa;
  border-color: rgba(255, 255, 255, 0.2);
}}

.{p}-tabs__tab--active {{
  background: {d['accent']};
  color: #0c0d12;
  border-color: {d['accent']};
}}

.{p}-tabs__showcase {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 3rem;
  margin-bottom: 2.5rem;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
}}

.{p}-tabs__panel-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}}

.{p}-tabs__panel-tag {{
  padding: 0.3rem 0.85rem;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: {d['accent']};
  font-size: 0.85rem;
  font-weight: 700;
}}

.{p}-tabs__panel-index {{
  font-size: 0.85rem;
  font-weight: 700;
  color: #71717a;
}}

.{p}-tabs__panel-title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 2rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-tabs__panel-desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.7;
  max-width: 800px;
  margin: 0 0 2rem;
}}

.{p}-tabs__btn {{
  display: inline-flex;
  padding: 0.75rem 1.8rem;
  background: {d['accent']};
  color: #0c0d12;
  font-weight: 700;
  font-size: 0.92rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-tabs__btn:hover {{
  background: {d['accent_hover']};
  transform: translateY(-2px);
}}

.{p}-tabs__grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.25rem;
}}

.{p}-tabs__card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}}

.{p}-tabs__card:hover {{
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}}

.{p}-tabs__card--active {{
  border-color: {d['accent']};
}}

.{p}-tabs__card-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}}

.{p}-tabs__card-num {{
  font-size: 0.8rem;
  font-weight: 700;
  color: #71717a;
}}

.{p}-tabs__card-tag {{
  font-size: 0.75rem;
  color: {d['accent']};
  font-weight: 600;
}}

.{p}-tabs__card-title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.5rem;
}}

.{p}-tabs__card-desc {{
  font-size: 0.88rem;
  color: #a1a1aa;
  line-height: 1.55;
  margin: 0;
}}

@media (max-width: 768px) {{
  .{p}-tabs__showcase {{ padding: 2rem; }}
}}

.{p}-tabs__showcase {{
  animation: {p}TabsPanelSettle 0.35s ease;
}}

@keyframes {p}TabsPanelSettle {{
  from {{ opacity: 0; transform: translateX(6px); }}
  to {{ opacity: 1; transform: translateX(0); }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-tabs__showcase,
  .{p}-tabs__tab,
  .{p}-tabs__card {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""

    elif layout_archetype == "split_hero":
        t3_user = (
            f"Write the {d['section_name']} section using an asymmetric split showcase layout: sticky left overview panel "
            f"with domain description and right stacked feature cards. Files: src/components/{sec_ts_name}.tsx + src/components/{sec_ts_name}.css"
        )
        t3_thought = (
            f"Now creating the core content component '{sec_ts_name}' for {d['name']} using the Split Showcase layout. "
            f"I'll organize the layout with a sticky overview column on the left and stacked feature cards on the right "
            f"with tags, descriptions, and deliverable badges."
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
    <section className="{p}-split" id="{d['section_id']}" aria-labelledby="{p}-split-title">
      <div className="{p}-split__inner">
        <div className="{p}-split__sticky">
          <p className="{p}-split__eyebrow">Curated Solutions</p>
          <h2 id="{p}-split-title" className="{p}-split__title">
            {d['section_name']}
          </h2>
          <p className="{p}-split__desc">
            {catalog_desc}
          </p>
          <div className="{p}-split__badge">
            <span className="{p}-split__badge-dot" aria-hidden="true" />
            <span>Active Availability</span>
          </div>
          <a href="mailto:{d['contact']['email']}" className="{p}-split__cta">
            Contact Specialist
          </a>
        </div>

        <div className="{p}-split__feed">
          {{ITEMS.map((item, idx) => (
            <article key={{item.title}} className="{p}-split__card">
              <div className="{p}-split__card-top">
                <span className="{p}-split__card-index">0{{idx + 1}}</span>
                <span className="{p}-split__card-tag">{{item.tag}}</span>
              </div>
              <h3 className="{p}-split__card-title">{{item.title}}</h3>
              <p className="{p}-split__card-desc">{{item.desc}}</p>
              <div className="{p}-split__card-check">
                <span className="{p}-split__check-icon">&check;</span>
                <span>Verified Deliverable Specification</span>
              </div>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-split {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}}

.{p}-split__inner {{
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 4rem;
  align-items: start;
}}

.{p}-split__sticky {{
  position: sticky;
  top: 100px;
}}

.{p}-split__eyebrow {{
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin: 0 0 0.5rem;
}}

.{p}-split__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2rem, 3.5vw, 2.8rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1.25rem;
}}

.{p}-split__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0 0 2rem;
}}

.{p}-split__badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.9rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.08);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.22);
  border-radius: 999px;
  color: #e4e4e7;
  font-size: 0.8rem;
  font-weight: 500;
  margin-bottom: 2rem;
}}

.{p}-split__badge-dot {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: {d['accent']};
}}

.{p}-split__cta {{
  display: inline-flex;
  padding: 0.75rem 1.8rem;
  background: {d['accent']};
  color: #0c0d12;
  font-weight: 700;
  font-size: 0.92rem;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}}

.{p}-split__cta:hover {{
  background: {d['accent_hover']};
  transform: translateY(-2px);
}}

.{p}-split__feed {{
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}}

.{p}-split__card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 2.2rem;
  transition: all 0.25s ease;
}}

.{p}-split__card:hover {{
  border-color: rgba(255, 255, 255, 0.18);
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.3);
}}

.{p}-split__card-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}}

.{p}-split__card-index {{
  font-size: 0.85rem;
  font-weight: 700;
  color: #71717a;
}}

.{p}-split__card-tag {{
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.15);
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  border-radius: 6px;
}}

.{p}-split__card-title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-split__card-desc {{
  font-size: 0.95rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0 0 1.25rem;
}}

.{p}-split__card-check {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: #71717a;
}}

.{p}-split__check-icon {{
  color: {d['accent']};
  font-weight: bold;
}}

@media (max-width: 900px) {{
  .{p}-split__inner {{ grid-template-columns: 1fr; }}
  .{p}-split__sticky {{ position: static; margin-bottom: 3rem; }}
}}

.{p}-split__sticky {{
  animation: {p}SplitStickyEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0ms both;
}}

.{p}-split__cards {{
  animation: {p}SplitCardsEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 160ms both;
}}

@keyframes {p}SplitStickyEnter {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes {p}SplitCardsEnter {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-split__sticky,
  .{p}-split__cards,
  .{p}-split__card,
  .{p}-split__action-btn {{
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
  }}
}}
"""

    elif layout_archetype == "timeline":
        t3_user = (
            f"Write the {d['section_name']} section using a sequential timeline track layout: vertical milestone spine line, "
            f"step numbers, node markers, and chronological cards. Files: src/components/{sec_ts_name}.tsx + src/components/{sec_ts_name}.css"
        )
        t3_thought = (
            f"Now creating the core content component '{sec_ts_name}' for {d['name']} with the Timeline layout archetype. "
            f"I'll render the {len(d['items'])} items sequentially along a vertical milestone track with step indicators, "
            f"node connectors, and detailed descriptive cards."
        )
        milestones = [
            {"step": f"Phase 0{idx+1}", "title": it["title"], "tag": it["tag"], "desc": it["desc"]}
            for idx, it in enumerate(d["items"])
        ]
        milestones_json = json.dumps(milestones, indent=2)

        t3_tsx = f"""import React from 'react';
import './{sec_ts_name}.css';

interface Milestone {{
  step: string;
  title: string;
  tag: string;
  desc: string;
}}

const MILESTONES: Milestone[] = {milestones_json};

export function {sec_ts_name}() {{
  const trackRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {{
    const observer = new IntersectionObserver(
      (entries) => {{
        entries.forEach((entry) => {{
          if (entry.isIntersecting) {{
            entry.target.classList.add('is-revealed');
          }}
        }});
      }},
      {{ threshold: 0.2 }}
    );

    const nodes = trackRef.current?.querySelectorAll('.{p}-timeline__node');
    nodes?.forEach((node) => observer.observe(node));

    return () => observer.disconnect();
  }}, []);

  return (
    <section className="{p}-timeline" id="{d['section_id']}" aria-labelledby="{p}-timeline-title">
      <div className="{p}-timeline__inner">
        <div className="{p}-timeline__header">
          <p className="{p}-timeline__eyebrow">Sequential Roadmap</p>
          <h2 id="{p}-timeline-title" className="{p}-timeline__title">
            {d['section_name']}
          </h2>
          <p className="{p}-timeline__desc">
            {catalog_desc}
          </p>
        </div>

        <div ref={{trackRef}} className="{p}-timeline__track">
          <div className="{p}-timeline__spine" aria-hidden="true" />
          {{MILESTONES.map((m) => (
            <article key={{m.title}} className="{p}-timeline__node">
              <div className="{p}-timeline__marker" aria-hidden="true">
                <span className="{p}-timeline__dot" />
              </div>
              <div className="{p}-timeline__card">
                <div className="{p}-timeline__card-top">
                  <span className="{p}-timeline__step">{{m.step}}</span>
                  <span className="{p}-timeline__tag">{{m.tag}}</span>
                </div>
                <h3 className="{p}-timeline__card-title">{{m.title}}</h3>
                <p className="{p}-timeline__card-desc">{{m.desc}}</p>
              </div>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
        t3_css = f""".{p}-timeline {{
  padding: 6.5rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}}

.{p}-timeline__inner {{
  max-width: 900px;
  margin: 0 auto;
}}

.{p}-timeline__header {{
  text-align: center;
  max-width: 680px;
  margin: 0 auto 4rem;
}}

.{p}-timeline__eyebrow {{
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin: 0 0 0.5rem;
}}

.{p}-timeline__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 800;
  color: #fafafa;
  margin: 0 0 1rem;
}}

.{p}-timeline__desc {{
  font-size: 1.05rem;
  color: #a1a1aa;
  line-height: 1.6;
  margin: 0;
}}

.{p}-timeline__track {{
  position: relative;
  padding-left: 2.5rem;
}}

.{p}-timeline__spine {{
  position: absolute;
  left: 11px;
  top: 12px;
  bottom: 24px;
  width: 2px;
  background: rgba(255, 255, 255, 0.1);
}}

.{p}-timeline__node {{
  position: relative;
  margin-bottom: 2.5rem;
}}

.{p}-timeline__node:last-child {{
  margin-bottom: 0;
}}

.{p}-timeline__marker {{
  position: absolute;
  left: -2.5rem;
  top: 1.25rem;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}}

.{p}-timeline__dot {{
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: {d['accent']};
  box-shadow: 0 0 0 4px rgba({accent_r}, {accent_g}, {accent_b}, 0.2);
}}

.{p}-timeline__card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 2rem;
  transition: all 0.25s ease;
}}

.{p}-timeline__card:hover {{
  transform: translateX(4px);
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.3);
}}

.{p}-timeline__card-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}}

.{p}-timeline__step {{
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: {d['accent']};
}}

.{p}-timeline__tag {{
  padding: 0.25rem 0.7rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.12);
  border: 1px solid rgba({accent_r}, {accent_g}, {accent_b}, 0.22);
  border-radius: 6px;
  font-size: 0.8rem;
  color: {d['accent']};
  font-weight: 600;
}}

.{p}-timeline__card-title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.3rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.5rem;
}}

.{p}-timeline__card-desc {{
  font-size: 0.95rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0;
}}

.{p}-timeline__node {{
  opacity: 0;
  transform: translateX(-12px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}}

.{p}-timeline__node.is-revealed {{
  opacity: 1;
  transform: translateX(0);
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-timeline__node,
  .{p}-timeline__node.is-revealed,
  .{p}-timeline__spine {{
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
    animation: none !important;
  }}
}}
"""

    else:  # grid
        t3_user = (
            f"Write the {d['section_name']} section: display all items from the content brief in a responsive grid of cards "
            f"with titles, tags, and detailed descriptions. Files: src/components/{sec_ts_name}.tsx + src/components/{sec_ts_name}.css"
        )
        t3_thought = (
            f"Now creating the core content component '{sec_ts_name}' for {d['name']}. "
            f"I'll lay out the {len(d['items'])} items in a balanced 2x2 responsive grid. "
            f"Each card will have a subtle surface background ({d['surface']}), an accent tag/badge, "
            "and clean hover interactions with a left-border indicator to elevate user experience."
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
  const gridRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {{
    const observer = new IntersectionObserver(
      (entries) => {{
        entries.forEach((entry) => {{
          if (entry.isIntersecting) {{
            entry.target.classList.add('is-visible');
          }}
        }});
      }},
      {{ threshold: 0.15 }}
    );

    const cards = gridRef.current?.querySelectorAll('.{p}-card');
    cards?.forEach((card) => observer.observe(card));

    return () => observer.disconnect();
  }}, []);

  return (
    <section className="{p}-catalog" id="{d['section_id']}" aria-labelledby="{p}-catalog-title">
      <div className="{p}-catalog__inner">
        <div className="{p}-catalog__header">
          <p className="{p}-catalog__eyebrow">Featured Highlights</p>
          <h2 id="{p}-catalog-title" className="{p}-catalog__title">
            {d['section_name']}
          </h2>
          <p className="{p}-catalog__desc">
            {catalog_desc}
          </p>
        </div>

        <div ref={{gridRef}} className="{p}-catalog__grid">
          {{ITEMS.map((item, idx) => (
            <article key={{item.title}} className="{p}-card" style={{{{ transitionDelay: `${{idx * 60}}ms` }}}}>
              <div className="{p}-card__top">
                <span className="{p}-card__index">0{{idx + 1}}</span>
                <span className="{p}-card__tag">{{item.tag}}</span>
              </div>
              <h3 className="{p}-card__title">{{item.title}}</h3>
              <p className="{p}-card__desc">{{item.desc}}</p>
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
  max-width: 680px;
  margin: 0 auto 3.5rem;
}}

.{p}-catalog__eyebrow {{
  color: {d['accent']};
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin: 0 0 0.5rem;
}}

.{p}-catalog__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
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
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}}

.{p}-card {{
  background: {d['surface']};
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-left: 3px solid transparent;
  border-radius: 12px;
  padding: 2rem;
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1), transform 0.5s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease;
}}

.{p}-card.is-visible {{
  opacity: 1;
  transform: translateY(0);
}}

.{p}-card:hover {{
  transform: translateY(-4px);
  border-left-color: {d['accent']};
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}}

.{p}-card__top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}}

.{p}-card__index {{
  font-size: 0.85rem;
  font-weight: 700;
  color: #71717a;
  letter-spacing: 0.05em;
}}

.{p}-card__tag {{
  display: inline-block;
  padding: 0.3rem 0.8rem;
  background: rgba({accent_r}, {accent_g}, {accent_b}, 0.15);
  color: {d['accent']};
  font-size: 0.82rem;
  font-weight: 700;
  border-radius: 6px;
}}

.{p}-card__title {{
  font-family: '{d['heading_font']}', sans-serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: #fafafa;
  margin: 0 0 0.75rem;
}}

.{p}-card__desc {{
  font-size: 0.95rem;
  color: #a1a1aa;
  line-height: 1.65;
  margin: 0;
}}

@media (max-width: 768px) {{
  .{p}-catalog__grid {{
    grid-template-columns: 1fr;
  }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-card,
  .{p}-card.is-visible,
  .{p}-card:hover {{
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
    box-shadow: none !important;
  }}
}}
"""

    return t3_user, t3_thought, t3_tsx, t3_css


def build_trajectory(d):
    target_arch = d.get("layout_archetype", "grid")
    prompt_seed = f"Build a complete website with layout: {target_arch} for {d['name']}. Business type: {d['type']}."
    layout_archetype = select_layout_archetype(prompt_seed, business_type=d["type"], business_name=d["name"])
    brief_xml = build_brief_xml(d, layout_archetype=layout_archetype)
    p = d["prefix"]

    # ── Turn 1: Header ──────────────────────────────────────────────────────────
    initial_user = (
        f"Build a complete website for the following brief with layout: {layout_archetype}.\n\n"
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
  background: rgba({int(d['primary'][1:3], 16)}, {int(d['primary'][3:5], 16)}, {int(d['primary'][5:7], 16)}, 0.92);
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
  box-shadow: 0 4px 14px rgba({int(d['accent'][1:3], 16)}, {int(d['accent'][3:5], 16)}, {int(d['accent'][5:7], 16)}, 0.35);
}}

.{p}-header__toggle {{
  display: none;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px;
  flex-direction: column;
  gap: 5px;
}}

.{p}-header__bar {{
  display: block;
  width: 22px;
  height: 2px;
  background: #fafafa;
  border-radius: 2px;
}}

.{p}-header__mobile-menu {{
  display: flex;
  flex-direction: column;
  padding: 1rem 2rem;
  background: {d['primary']};
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  gap: 0.75rem;
}}

.{p}-header__mobile-menu a {{
  color: #fafafa;
  text-decoration: none;
  font-size: 1rem;
  padding: 0.5rem 0;
}}

@media (max-width: 768px) {{
  .{p}-header__nav {{ display: none; }}
  .{p}-header__toggle {{ display: flex; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .{p}-header,
  .{p}-header__cta,
  .{p}-header__link {{
    transition: none !important;
    transform: none !important;
    animation: none !important;
  }}
}}
"""

    t1_action = write_site("src/components/Header.tsx", t1_tsx, "src/components/Header.css", t1_css)

    # ── Turn 2: Hero (Branches on layout_archetype) ─────────────────────────────
    t2_user_str, t2_thought_str, t2_tsx, t2_css = make_hero_code(p, d, layout_archetype)
    t2_user = obs_ok(["src/components/Header.tsx", "src/components/Header.css"], t2_user_str)
    t2_thought = thought(t2_thought_str)
    t2_action = write_site("src/components/Hero.tsx", t2_tsx, "src/components/Hero.css", t2_css)

    # ── Turn 3: Main Content Section (Branches on layout_archetype) ─────────────
    sec_ts_name = d["section_name"].replace(" ", "").replace("&", "")
    t3_user_str, t3_thought_str, t3_tsx, t3_css = make_turn3_code(p, d, layout_archetype)
    t3_user = obs_ok(["src/components/Hero.tsx", "src/components/Hero.css"], t3_user_str)
    t3_thought = thought(t3_thought_str)
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

    prim_r = int(d['primary'][1:3], 16)
    prim_g = int(d['primary'][3:5], 16)
    prim_b = int(d['primary'][5:7], 16)
    accent_r = int(d['accent'][1:3], 16)
    accent_g = int(d['accent'][3:5], 16)
    accent_b = int(d['accent'][5:7], 16)
    footer_bg = f"rgb({max(6, prim_r // 3)}, {max(6, prim_g // 3)}, {max(8, prim_b // 3)})"
    footer_border = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.14)"

    t4_css = f""".{p}-footer {{
  background: {footer_bg};
  border-top: 1px solid {footer_border};
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

@media (prefers-reduced-motion: reduce) {{
  .{p}-footer,
  .{p}-footer__link {{
    transition: none !important;
    transform: none !important;
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
        f"All 4 sections have been built and accepted for {d['name']} using layout archetype '{layout_archetype}'. "
        "The site is complete with cohesive design tokens, responsive grid layouts, "
        "valid TypeScript components, and scoped modern CSS."
    )

    t5_finish = finish(
        f"Built the complete {d['name']} ({d['type']}) website with 4 sections (archetype: {layout_archetype}):\n"
        f"- Header: sticky navbar with logo, nav links, CTA button, and mobile menu\n"
        f"- Hero: bold responsive banner structured for the {layout_archetype} archetype with tagline and CTAs\n"
        f"- {d['section_name']}: {layout_archetype}-driven section displaying all {len(d['items'])} items with tags & descriptions\n"
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
        "layout_archetype": layout_archetype,
        "messages": messages
    }


def main():
    output_path = Path("site_trajectories_batch5.jsonl")
    data_output_path = Path("data/site_trajectories_batch5.jsonl")
    print("=" * 70)
    print("      GENERATING BATCH 5: 50 GOLD-STANDARD SITE TRAJECTORIES        ")
    print("=" * 70)
    print(f"Total domains configured: {len(DOMAINS)}")

    trajectories = []
    for i, d in enumerate(DOMAINS, 1):
        traj = build_trajectory(d)
        trajectories.append(traj)
        print(f"[{i:02d}/50] Generated: {d['id']} ({d['name']}) [archetype: {d['layout_archetype']}]")

    # Write to root output
    with output_path.open("w", encoding="utf-8") as f:
        for traj in trajectories:
            f.write(json.dumps(traj) + "\n")

    # Write to data directory
    data_output_path.parent.mkdir(parents=True, exist_ok=True)
    with data_output_path.open("w", encoding="utf-8") as f:
        for traj in trajectories:
            f.write(json.dumps(traj) + "\n")

    print("-" * 70)
    print(f"Successfully generated {len(trajectories)} trajectories to {output_path.name} and {data_output_path}!")
    print(f"File size: {output_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
