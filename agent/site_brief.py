"""
site_brief.py - Two-Stage Structured Content Brief Generator for the Site Pipeline

Transforms a one-line user prompt into a structured, highly detailed XML content brief.
Provides a unified Domain Registry covering 15+ business domains with domain-authentic
copy, color palettes, Google typography tokens, dynamic section flows, and XML entities.

Pipeline Stages:
  Stage 1: Heuristic or LLM-based structured brief synthesis with weighted domain classification.
  Stage 2: Formatting as a high-density <content_brief> XML document consumed by the agent.
"""

import json
import os
import re
from typing import Optional, Dict, Any, List

from style_ingest import (
    StyleSpec,
    parse_css_tokens,
    PRESET_STYLES,
    spec_to_css_root,
    spec_to_prompt_instructions,
)


# ==============================================================================
# 1. Unified Domain Registry (15+ Domains)
# ==============================================================================

_BUSINESS_TYPE_WEIGHTS: dict[str, dict[str, int]] = {
    "saas": {
        "saas": 12, "software": 7, "ai platform": 9, "platform": 6, "dashboard": 6,
        "pricing calculator": 9, "pricing": 6, "startup": 6, "analytics": 6, "cloud": 5,
        "workflow": 6, "automation": 6, "app": 2, "tool": 3, "product": 3,
    },
    "restaurant": {
        "restaurant": 12, "food": 7, "cafe": 9, "bistro": 9, "kitchen": 7, "eatery": 9,
        "dining": 8, "menu": 9, "cuisine": 9, "pizza": 10, "sushi": 10, "burger": 10,
        "diner": 9, "bakery": 9, "ramen": 10, "trattoria": 10, "bar": 4,
    },
    "portfolio": {
        "portfolio": 12, "my work": 9, "freelance": 8, "resume": 9, "cv": 9,
        "hire me": 9, "designer portfolio": 10, "developer portfolio": 10, "personal website": 8,
    },
    "ecommerce": {
        "shop": 8, "store": 8, "ecommerce": 12, "cart": 7, "checkout": 7, "products": 6,
        "clothing": 7, "brand store": 9, "merchandise": 8, "apparel": 8,
    },
    "event": {
        "conference": 10, "summit": 10, "event": 8, "meetup": 8, "festival": 9, "concert": 9, "tickets": 8, "expo": 9,
    },
    "fitness": {
        "gym": 10, "fitness": 10, "workout": 8, "crossfit": 10, "trainer": 8, "training": 5, "pilates": 9, "wellness club": 8,
    },
    "blog": {
        "blog": 10, "article": 7, "posts": 7, "journal": 8, "newsletter": 7, "publication": 8, "magazine": 8,
    },
    "fintech": {
        "fintech": 12, "payments": 9, "treasury": 9, "banking": 9, "fx": 9, "currency": 8, "crypto": 8,
        "investment": 8, "ledger": 8, "payroll": 8, "invoicing": 8, "b2b payment": 10,
    },
    "healthcare": {
        "dental": 12, "dentistry": 12, "clinic": 10, "doctor": 9, "healthcare": 11, "medical": 9,
        "aesthetic": 9, "patient": 8, "therapy": 8, "hospital": 8, "wellness clinic": 9,
    },
    "realestate": {
        "real estate": 12, "realestate": 12, "villa": 10, "apartments": 9, "property": 9, "rental": 8,
        "realtor": 10, "broker": 8, "housing": 8, "penthouse": 10, "charter": 8, "estates": 9, "villas": 10,
    },
    "education": {
        "bootcamp": 11, "academy": 10, "course": 9, "courses": 9, "curriculum": 9, "learn": 7,
        "education": 10, "school": 8, "tutoring": 8, "syllabus": 9, "students": 7,
    },
    "nonprofit": {
        "nonprofit": 12, "non-profit": 12, "charity": 11, "conservation": 10, "foundation": 9,
        "donate": 9, "donation": 9, "volunteer": 8, "cause": 7, "wildlife": 9, "ngo": 11,
    },
    "agency": {
        "agency": 12, "design studio": 10, "creative studio": 10, "branding": 8, "marketing agency": 10,
        "consultancy": 8, "client showcase": 8,
    },
    "architecture": {
        "architecture": 12, "architect": 11, "architectural": 11, "blueprint": 9, "atelier": 9,
        "interior design": 9, "spatial": 8, "blueprint gallery": 10,
    },
    "coffee": {
        "coffee": 12, "roaster": 11, "roastery": 11, "roasters": 11, "beans": 9, "espresso": 10,
        "single origin": 10, "brew": 8, "roast": 8,
    },
}

_DOMAIN_THEMES: dict[str, dict] = {
    "saas": {
        "primary_color": "#0b0f19",
        "primary_color_light": "#f8fafc",
        "primary_color_dark": "#0b0f19",
        "accent_color": "#2563eb",
        "accent_secondary": "#06b6d4",
        "font_heading": "Plus Jakarta Sans",
        "font_body": "Inter",
        "border_radius": "6px",
        "default_tagline": "Operational intelligence and automated release cycles for distributed engineering teams",
    },
    "restaurant": {
        "primary_color": "#fdfbf7",
        "primary_color_light": "#fdfbf7",
        "primary_color_dark": "#1c1917",
        "accent_color": "#ea580c",
        "accent_secondary": "#c2410c",
        "font_heading": "Fraunces",
        "font_body": "Outfit",
        "border_radius": "8px",
        "default_tagline": "Handcrafted seasonal dishes sourced from regional farms and prepared over open woodfire",
    },
    "portfolio": {
        "primary_color": "#121214",
        "primary_color_light": "#fafafa",
        "primary_color_dark": "#121214",
        "accent_color": "#059669",
        "accent_secondary": "#7c3aed",
        "font_heading": "Syne",
        "font_body": "DM Sans",
        "border_radius": "0px",
        "default_tagline": "Selected design systems, product architecture, and human-computer interfaces",
    },
    "ecommerce": {
        "primary_color": "#ffffff",
        "primary_color_light": "#ffffff",
        "primary_color_dark": "#0f172a",
        "accent_color": "#0284c7",
        "accent_secondary": "#e11d48",
        "font_heading": "Outfit",
        "font_body": "Plus Jakarta Sans",
        "border_radius": "9999px",
        "default_tagline": "Functional goods and technical apparel engineered for daily durability",
    },
    "fitness": {
        "primary_color": "#09090b",
        "primary_color_light": "#f4f4f5",
        "primary_color_dark": "#09090b",
        "accent_color": "#dc2626",
        "accent_secondary": "#f97316",
        "font_heading": "Syne",
        "font_body": "Manrope",
        "border_radius": "4px",
        "default_tagline": "Structured strength programming, conditioning metrics, and recovery protocols",
    },
    "event": {
        "primary_color": "#090d16",
        "primary_color_light": "#faf5ff",
        "primary_color_dark": "#090d16",
        "accent_color": "#db2777",
        "accent_secondary": "#7c3aed",
        "font_heading": "Space Grotesk",
        "font_body": "DM Sans",
        "border_radius": "12px",
        "default_tagline": "Two days of deep technical talks, systems architecture, and design workshops",
    },
    "blog": {
        "primary_color": "#fefefe",
        "primary_color_light": "#fefefe",
        "primary_color_dark": "#18181b",
        "accent_color": "#2563eb",
        "accent_secondary": "#4f46e5",
        "font_heading": "Newsreader",
        "font_body": "Newsreader",
        "border_radius": "2px",
        "default_tagline": "Longform essays on distributed infrastructure, compiler internals, and software craftsmanship",
    },
    "fintech": {
        "primary_color": "#061325",
        "primary_color_light": "#f8fafc",
        "primary_color_dark": "#061325",
        "accent_color": "#0284c7",
        "accent_secondary": "#059669",
        "font_heading": "Plus Jakarta Sans",
        "font_body": "Inter",
        "border_radius": "4px",
        "default_tagline": "Programmatic settlement, foreign exchange rails, and unified liquidity ledgers",
    },
    "healthcare": {
        "primary_color": "#f0fdf4",
        "primary_color_light": "#f0fdf4",
        "primary_color_dark": "#0a1a24",
        "accent_color": "#0d9488",
        "accent_secondary": "#0284c7",
        "font_heading": "Outfit",
        "font_body": "Plus Jakarta Sans",
        "border_radius": "8px",
        "default_tagline": "Evidence-based preventative medicine, diagnostic imaging, and dedicated physician care",
    },
    "realestate": {
        "primary_color": "#fbf8f2",
        "primary_color_light": "#fbf8f2",
        "primary_color_dark": "#1c1917",
        "accent_color": "#b45309",
        "accent_secondary": "#4338ca",
        "font_heading": "Cormorant Garamond",
        "font_body": "Outfit",
        "border_radius": "0px",
        "default_tagline": "Architectural estates, private coastal properties, and historic city residences",
    },
    "education": {
        "primary_color": "#f8f9fa",
        "primary_color_light": "#f8f9fa",
        "primary_color_dark": "#090d16",
        "accent_color": "#4f46e5",
        "accent_secondary": "#0284c7",
        "font_heading": "Outfit",
        "font_body": "DM Sans",
        "border_radius": "6px",
        "default_tagline": "Rigorous cohort courses in systems programming, distributed databases, and security",
    },
    "nonprofit": {
        "primary_color": "#f0fdf4",
        "primary_color_light": "#f0fdf4",
        "primary_color_dark": "#042f2e",
        "accent_color": "#059669",
        "accent_secondary": "#0284c7",
        "font_heading": "Outfit",
        "font_body": "Manrope",
        "border_radius": "8px",
        "default_tagline": "Direct ecological restoration, wildlife corridor preservation, and community land stewardship",
    },
    "agency": {
        "primary_color": "#09090b",
        "primary_color_light": "#f8fafc",
        "primary_color_dark": "#09090b",
        "accent_color": "#ec4899",
        "accent_secondary": "#4f46e5",
        "font_heading": "Cabinet Grotesk",
        "font_body": "Space Grotesk",
        "border_radius": "0px",
        "default_tagline": "Brand identity, bespoke web platforms, and digital product craft for emerging companies",
    },
    "architecture": {
        "primary_color": "#f5f5f4",
        "primary_color_light": "#f5f5f4",
        "primary_color_dark": "#1c1917",
        "accent_color": "#57534e",
        "accent_secondary": "#d97706",
        "font_heading": "Cinzel",
        "font_body": "Raleway",
        "border_radius": "0px",
        "default_tagline": "Monolithic timber pavilions, passive solar dwellings, and landscape-integrated spaces",
    },
    "coffee": {
        "primary_color": "#faf6f0",
        "primary_color_light": "#faf6f0",
        "primary_color_dark": "#292524",
        "accent_color": "#b45309",
        "accent_secondary": "#78716c",
        "font_heading": "DM Serif Display",
        "font_body": "Outfit",
        "border_radius": "8px",
        "default_tagline": "Direct-trade heirloom varietals freshly roasted weekly in small batches",
    },
}

# ── Domain Templates ──────────────────────────────────────────────────────────

_SAAS_TEMPLATE: dict = {
    "business_type": "saas",
    "features": [
        {"icon": "bolt", "title": "Real-Time Pipeline Execution", "description": "Orchestrate agent workflows with millisecond streaming and zero latency."},
        {"icon": "shield-halved", "title": "Enterprise Security", "description": "End-to-end encryption, role-based access control, and SOC-2 compliance out of the box."},
        {"icon": "chart-simple", "title": "Predictive Telemetry", "description": "Interactive visual dashboards with automated error detection and root-cause tracing."},
        {"icon": "sliders", "title": "Custom Integration Nodes", "description": "Plug into any external API, database, or LLM with one-click configurable nodes."},
    ],
    "pricing_tiers": [
        {"name": "Starter", "price": "$29", "period": "month", "features": ["5 Team Members", "10,000 Operations / mo", "Community Support", "Basic Analytics"]},
        {"name": "Pro", "price": "$79", "period": "month", "recommended": True, "features": ["Unlimited Team Members", "250,000 Operations / mo", "Priority 24/7 SLA", "Advanced Telemetry", "Custom Integrations"]},
        {"name": "Enterprise", "price": "$199", "period": "month", "features": ["Dedicated Infrastructure", "Unlimited Operations", "Custom SLA & Account Manager", "SSO & SAML Security", "On-Prem Deployment"]},
    ],
    "testimonials": [
        {"quote": "Reduced our deployment triage time by 75%. An indispensable tool for our team.", "author": "Dr. Sarah Lin", "role": "VP of Engineering at CloudScale", "rating": 5},
        {"quote": "The cleanest multi-step workflow platform we have ever integrated. Flawless dev experience.", "author": "Marcus Vance", "role": "Lead Architect at ScaleBase", "rating": 5},
        {"quote": "Autonomous error correction and live feedback transformed our sprint delivery pace.", "author": "Elena Rostova", "role": "Staff Product Director", "rating": 5},
    ],
    "contact": {"email": "support@saas.com", "sales": "sales@saas.com"},
}

_RESTAURANT_TEMPLATE: dict = {
    "business_type": "restaurant",
    "menu_categories": [
        {
            "name": "Starters",
            "items": [
                {"name": "Garlic Bruschetta", "price": "$8", "description": "Crispy artisanal sourdough with heirloom tomatoes and garlic basil oil"},
                {"name": "Soup of the Day", "price": "$7", "description": "Chef seasonal homemade veloute with toasted brioche"},
                {"name": "Charcuterie Board", "price": "$14", "description": "Artisanal cured meats, local cheeses, and fig compote"},
            ]
        },
        {
            "name": "Mains",
            "items": [
                {"name": "Grilled Wild Salmon", "price": "$24", "description": "Pan-seared Atlantic salmon with lemon dill butter and asparagus"},
                {"name": "Prime Ribeye Steak", "price": "$34", "description": "12oz aged grass-fed cut with rosemary truffle jus and fries"},
                {"name": "Truffle Gnocchi", "price": "$18", "description": "Handmade potato gnocchi with wild mushrooms and parmesan cream"},
            ]
        },
    ],
    "contact": {"address": "123 Culinary Avenue, Food District", "phone": "555-123-4567", "email": "reservations@dining.com"},
}

_PORTFOLIO_TEMPLATE: dict = {
    "business_type": "portfolio",
    "projects": [
        {"name": "AI Workflow Automation", "description": "Full-stack agent orchestration platform with real-time streaming", "tech": ["React", "TypeScript", "Node.js", "Tailwind CSS"]},
        {"name": "Financial Analytics Dashboard", "description": "High-frequency interactive telemetry visuals and metrics engine", "tech": ["Next.js", "D3.js", "PostgreSQL", "WebSocket"]},
        {"name": "Component Design System", "description": "Accessible Headless UI primitives with comprehensive unit test suites", "tech": ["React", "TypeScript", "CSS Modules", "Vitest"]},
    ],
    "skills": ["React", "TypeScript", "Node.js", "Python", "PostgreSQL", "Tailwind CSS", "Docker", "AWS"],
    "contact": {"email": "hello@developer.io", "github": "github.com/developer", "linkedin": "linkedin.com/in/developer"},
}

_ECOMMERCE_TEMPLATE: dict = {
    "business_type": "ecommerce",
    "features": [
        {"icon": "truck-fast", "title": "Worldwide Express Shipping", "description": "Delivered to your doorstep within 48 hours with full live GPS tracking."},
        {"icon": "shield-check", "title": "Lifetime Quality Guarantee", "description": "Engineered from sustainable premium materials built to last a lifetime."},
        {"icon": "arrow-rotate-left", "title": "Hassle-Free 30-Day Returns", "description": "Not completely satisfied? Exchange or return with pre-printed return labels."},
    ],
    "pricing_tiers": [
        {"name": "Essential Pack", "price": "$49", "period": "pack", "features": ["Core Daily Essentials", "Free Standard Shipping", "Recycled Packaging"]},
        {"name": "Signature Kit", "price": "$99", "period": "kit", "recommended": True, "features": ["Full Product Selection", "Priority 2-Day Air Shipping", "Custom Monogramming", "1-Year Care Kit"]},
    ],
    "testimonials": [
        {"quote": "Outstanding craftsmanship. The texture and attention to detail exceed expectations.", "author": "Julian Ross", "role": "Verified Buyer", "rating": 5},
        {"quote": "Arrived in 24 hours. The packaging alone felt like opening a bespoke luxury gift.", "author": "Claire Montgomery", "role": "Design Director", "rating": 5},
    ],
    "contact": {"email": "support@store.com", "phone": "1-800-555-SHOP"},
}

_FINTECH_TEMPLATE: dict = {
    "business_type": "fintech",
    "features": [
        {"icon": "globe", "title": "Global Treasury Management", "description": "Hold, exchange, and disburse in 42+ currencies with real-time interbank rates."},
        {"icon": "shield-halved", "title": "SOC-2 & PCI-DSS Level 1", "description": "Bank-grade biometric cryptography, automated AML monitoring, and zero-loss ledger architecture."},
        {"icon": "calculator", "title": "Live FX Fee Optimizer", "description": "Instant transparency on payment rails with zero hidden conversion spreads."},
        {"icon": "bolt", "title": "Sub-Second Global Settlements", "description": "Execute high-volume cross-border payouts via local automated clearing networks."},
    ],
    "pricing_tiers": [
        {"name": "Growth Treasury", "price": "$99", "period": "month", "features": ["Up to $250k / mo volume", "15 Currencies", "Standard API Access", "Next-Day Settlements"]},
        {"name": "Global Scale", "price": "$299", "period": "month", "recommended": True, "features": ["Up to $2M / mo volume", "42+ Currencies", "Real-Time FX Hedging", "Sub-Second Settlements", "Dedicated Compliance Lead"]},
        {"name": "Institutional", "price": "$799", "period": "month", "features": ["Unlimited Volume", "Custom Liquidity Routing", "Tailored API SLA", "On-Prem Key Management"]},
    ],
    "testimonials": [
        {"quote": "NexusPay eliminated foreign transaction surcharges across our 12 regional subsidiaries.", "author": "Marcus Vance", "role": "CFO at HyperGrowth Inc", "rating": 5},
        {"quote": "The cleanest payments API we have ever implemented. Our engineering team finished integration in two days.", "author": "Elena Rostova", "role": "Head of Engineering at OmniTech", "rating": 5},
    ],
    "contact": {"email": "enterprise@fintech.com", "phone": "1-800-FINTECH"},
}

_HEALTHCARE_TEMPLATE: dict = {
    "business_type": "healthcare",
    "features": [
        {"icon": "tooth", "title": "State-of-the-Art Aesthetic Care", "description": "High-precision digital 3D smile design, pain-free laser whitening, and porcelain veneers."},
        {"icon": "user-doctor", "title": "Board-Certified Specialists", "description": "Decades of combined clinical experience trained at world-renowned surgical institutions."},
        {"icon": "heart-pulse", "title": "Holistic Patient Comfort", "description": "Private spa-like recovery suites, gentle sedation dentistry, and personalized care coordinators."},
        {"icon": "calendar-check", "title": "Seamless Digital Booking", "description": "Select appointments, upload pre-op history, and chat directly with clinicians online."},
    ],
    "testimonials": [
        {"quote": "The most gentle, transparent medical experience I have ever had. Completely changed my smile.", "author": "Dr. Sarah Lin", "role": "Patient & Research Scientist", "rating": 5},
        {"quote": "Modern, pristine facilities with a clinical team that genuinely listens and personalizes treatment.", "author": "David Chen", "role": "Architect", "rating": 5},
    ],
    "contact": {"address": "450 Health Sciences Parkway, Suite 300", "phone": "555-987-CARE", "email": "care@healthstudio.com"},
}

_REALESTATE_TEMPLATE: dict = {
    "business_type": "realestate",
    "features": [
        {"icon": "house", "title": "Prime Waterfront Locations", "description": "Exclusive access to off-market coastal estates, luxury penthouses, and private islands."},
        {"icon": "compass", "title": "Virtual 3D Architectural Tours", "description": "Immersive 4K interactive walkthroughs and photorealistic daylight simulations."},
        {"icon": "handshake", "title": "Private Concierge Advisory", "description": "End-to-end legal title coordination, property management, and wealth preservation guidance."},
    ],
    "pricing_tiers": [
        {"name": "Villa Serenity", "price": "$1,450", "period": "night", "features": ["5 Bedrooms Waterfront", "Private Infinity Pool", "Dedicated Butler & Private Chef", "Yacht Mooring"]},
        {"name": "Azure Horizon", "price": "$2,200", "period": "night", "recommended": True, "features": ["7 Bedrooms Cliffside", "Helipad Access", "Full Luxury Chauffeur Service", "Private Wine Cellar"]},
    ],
    "testimonials": [
        {"quote": "Elysian Escapes curated our summer family retreat with flawless discretion and five-star service.", "author": "Lord Alexander Thorne", "role": "Private Client", "rating": 5},
        {"quote": "Every detail from pre-arrival provisioning to yacht charters was executed to perfection.", "author": "Sophia Laurent", "role": "Managing Director", "rating": 5},
    ],
    "contact": {"email": "concierge@luxuryvillas.com", "phone": "+1-800-VILLAS"},
}

_EDUCATION_TEMPLATE: dict = {
    "business_type": "education",
    "features": [
        {"icon": "code", "title": "Hands-On Engineering Syllabus", "description": "Build production microservices, distributed systems, and modern React web applications from day one."},
        {"icon": "users", "title": "1-on-1 Staff Mentorship", "description": "Weekly code reviews and architecture guidance from senior engineers at top tech firms."},
        {"icon": "briefcase", "title": "94% Career Placement Rate", "description": "Dedicated career coaching, resume workshops, and direct hiring partner introductions."},
    ],
    "pricing_tiers": [
        {"name": "Self-Paced Track", "price": "$499", "period": "course", "features": ["Full Curriculum Access", "Discord Community Support", "12 Practical Projects", "Certificate of Completion"]},
        {"name": "Immersive Cohort", "price": "$1,899", "period": "cohort", "recommended": True, "features": ["Live Lectures & Workshops", "Weekly 1-on-1 Mentorship", "Mock Technical Interviews", "Hiring Partner Introductions"]},
    ],
    "testimonials": [
        {"quote": "The curriculum bridged the gap between toy tutorials and real enterprise codebase engineering.", "author": "Priya Sharma", "role": "Software Engineer at Stripe", "rating": 5},
        {"quote": "Transitioned from non-tech to frontend engineer in 6 months. Best educational investment I have made.", "author": "Lucas Vance", "role": "Frontend Developer", "rating": 5},
    ],
    "contact": {"email": "admissions@academy.edu", "phone": "555-LEARN-NOW"},
}

_NONPROFIT_TEMPLATE: dict = {
    "business_type": "nonprofit",
    "features": [
        {"icon": "tree", "title": "Habitat Reforestation", "description": "Over 2.4 million indigenous trees planted across endangered biodiversity corridors."},
        {"icon": "water", "title": "Clean Water Initiatives", "description": "Providing clean, solar-powered drinking water infrastructure to remote rural communities."},
        {"icon": "scale-balanced", "title": "Transparent Financial Impact", "description": "91 cents of every dollar goes directly into field operations and grassroots conservation."},
    ],
    "testimonials": [
        {"quote": "Green Horizon demonstrates how grassroots conservation can create lasting systemic ecological change.", "author": "Dr. Jane Goodall", "role": "Honorary Patron", "rating": 5},
        {"quote": "Complete transparency, audited field metrics, and genuine community empowerment.", "author": "David Attenborough", "role": "Conservation Advocate", "rating": 5},
    ],
    "contact": {"email": "impact@conservation.org", "phone": "1-800-4-NATURE"},
}

_AGENCY_TEMPLATE: dict = {
    "business_type": "agency",
    "features": [
        {"icon": "palette", "title": "Brand Strategy & Visual Identity", "description": "Cohesive brand guidelines, typography systems, and narrative design languages."},
        {"icon": "laptop-code", "title": "Flagship Digital Products", "description": "Ultra-fast headless web experiences and native mobile apps built with modern React and TypeScript."},
        {"icon": "arrow-trend-up", "title": "Conversion Rate Optimization", "description": "Data-informed UX experiments that turn curious visitors into loyal high-value customers."},
    ],
    "testimonials": [
        {"quote": "Pixel Forge redesigned our entire platform. In 90 days our sign-up conversion increased 48%.", "author": "Marcus Bell", "role": "CEO at TechVentures", "rating": 5},
        {"quote": "Incredible craft, proactive communication, and delivery ahead of schedule.", "author": "Rachel Green", "role": "Head of Product", "rating": 5},
    ],
    "contact": {"email": "newbusiness@agency.studio", "phone": "555-CREATE"},
}

_ARCHITECTURE_TEMPLATE: dict = {
    "business_type": "architecture",
    "features": [
        {"icon": "compass-drafting", "title": "Sustainable Passive Design", "description": "Net-zero energy residential and civic structures maximizing natural daylight and airflow."},
        {"icon": "cube", "title": "Raw Natural Materiality", "description": "Hand-selected Nordic timber, exposed architectural concrete, and locally quarried stone."},
        {"icon": "ruler-combined", "title": "Precision BIM Modeling", "description": "End-to-end 3D parametric blueprint execution from schematic concepts to construction oversight."},
    ],
    "testimonials": [
        {"quote": "Atelier Nord crafted a home that harmonizes completely with its surrounding mountain landscape.", "author": "Henrik Lindqvist", "role": "Private Homeowner", "rating": 5},
        {"quote": "Remarkable restraint and timeless modern geometry. A masterclass in Scandinavian spatial poetry.", "author": "Architectural Review", "role": "Design Journal", "rating": 5},
    ],
    "contact": {"address": "Nordic Way 42, Oslo, Norway", "email": "studio@ateliernord.arch"},
}

_COFFEE_TEMPLATE: dict = {
    "business_type": "coffee",
    "features": [
        {"icon": "mug-hot", "title": "Micro-Lot Direct Trade", "description": "Paying 250% above fair-trade prices directly to independent generational farmers in Ethiopia and Colombia."},
        {"icon": "fire-flame-curved", "title": "Precision Loring Roasting", "description": "Small-batch convection roasting tailored to highlight delicate floral notes and complex fruit sweetness."},
        {"icon": "box", "title": "Peak Freshness Delivery", "description": "Roasted to order and shipped within 24 hours in 100% compostable oxygen-valved bags."},
    ],
    "pricing_tiers": [
        {"name": "Explorer Tier", "price": "$22", "period": "bag", "features": ["1 Bag (12oz) / month", "Rotating Single Origin", "Free Shipping", "Tasting Notes Card"]},
        {"name": "Aficionado Tier", "price": "$38", "period": "month", "recommended": True, "features": ["2 Bags (12oz each)", "Micro-Lot Reserves", "Grind Size Customization", "Priority Dispatch"]},
    ],
    "testimonials": [
        {"quote": "The Ethiopian Yirgacheffe has an intoxicating bergamot aroma. Hands down the best coffee in the city.", "author": "James Hoffman", "role": "Coffee Enthusiast", "rating": 5},
        {"quote": "Every delivery is consistent, impeccably roasted, and packed with origin documentation.", "author": "Maya Lin", "role": "Barista Champion", "rating": 5},
    ],
    "contact": {"email": "hello@solaceroasters.com", "phone": "555-ROAST"},
}

_FITNESS_TEMPLATE: dict = {
    "business_type": "fitness",
    "features": [
        {"icon": "dumbbell", "title": "Elite Training Equipment", "description": "Olympic lifting platforms, Eleiko barbells, and calibrated strength training machines."},
        {"icon": "heart-pulse", "title": "Biometric Heart-Rate Coaching", "description": "Live workout telemetry monitoring output, zone duration, and optimal recovery times."},
        {"icon": "spa", "title": "Recovery Lounge & Cryotherapy", "description": "Infrared saunas, cold plunge baths, and guided mobility recovery sessions."},
    ],
    "pricing_tiers": [
        {"name": "Standard Access", "price": "$89", "period": "month", "features": ["Full Gym Floor Access", "Locker Room & Sauna", "2 Group Classes / mo", "Fitness Assessment"]},
        {"name": "Performance Pro", "price": "$149", "period": "month", "recommended": True, "features": ["Unlimited Group Training", "Cryo & Sauna Access", "Monthly Body Composition Scan", "Nutritional Guide"]},
    ],
    "testimonials": [
        {"quote": "IronClad transformed my athletic performance. Incredible coaches and supportive community.", "author": "Marcus Bell", "role": "Crossfit Competitor", "rating": 5},
    ],
    "contact": {"email": "join@ironcladgym.com", "phone": "555-FIT-CLUB"},
}

_EVENT_TEMPLATE: dict = {
    "business_type": "event",
    "features": [
        {"icon": "microphone", "title": "40+ Visionary Keynotes", "description": "Hear from principal engineers, AI researchers, and startup founders redefining software."},
        {"icon": "network-wired", "title": "Curated Peer Networking", "description": "Meet 1,500+ attendees during structured breakout sessions, dinners, and evening social events."},
        {"icon": "laptop-code", "title": "Interactive Deep-Dive Labs", "description": "Hands-on coding workshops tackling real-world agent orchestration and model deployment."},
    ],
    "pricing_tiers": [
        {"name": "Virtual Pass", "price": "$149", "period": "pass", "features": ["Live Stream Access", "Workshop Recordings", "Discord Networking"]},
        {"name": "All-Access Pass", "price": "$599", "period": "pass", "recommended": True, "features": ["In-Person Mainstage Entry", "Catered Lunch & Reception", "VIP Speaker Meet & Greet", "Workshop Swag Bag"]},
    ],
    "testimonials": [
        {"quote": "The best developer conference of the year. The technical depth of the talks was unmatched.", "author": "Sarah Lin", "role": "Staff Engineer", "rating": 5},
    ],
    "contact": {"email": "tickets@devsummit.com"},
}

_BLOG_TEMPLATE: dict = {
    "business_type": "blog",
    "features": [
        {"icon": "newspaper", "title": "In-Depth Architectural Essays", "description": "Weekly deep-dives into compiler internals, distributed consensus, and TypeScript paradigms."},
        {"icon": "envelope-open", "title": "Bi-Weekly Newsletter", "description": "Curated links, industry analysis, and engineering highlights delivered to 45,000+ readers."},
    ],
    "testimonials": [
        {"quote": "Consistently the highest signal-to-noise technical engineering publication on the web.", "author": "Elena Rostova", "role": "Lead Architect", "rating": 5},
    ],
    "contact": {"email": "editor@techblog.io"},
}

_DOMAIN_TEMPLATES: dict[str, dict] = {
    "saas": _SAAS_TEMPLATE,
    "restaurant": _RESTAURANT_TEMPLATE,
    "portfolio": _PORTFOLIO_TEMPLATE,
    "ecommerce": _ECOMMERCE_TEMPLATE,
    "fintech": _FINTECH_TEMPLATE,
    "healthcare": _HEALTHCARE_TEMPLATE,
    "realestate": _REALESTATE_TEMPLATE,
    "education": _EDUCATION_TEMPLATE,
    "nonprofit": _NONPROFIT_TEMPLATE,
    "agency": _AGENCY_TEMPLATE,
    "architecture": _ARCHITECTURE_TEMPLATE,
    "coffee": _COFFEE_TEMPLATE,
    "fitness": _FITNESS_TEMPLATE,
    "event": _EVENT_TEMPLATE,
    "blog": _BLOG_TEMPLATE,
}


# ==============================================================================
# 2. Heuristic Business Name & Domain Classification
# ==============================================================================

def extract_business_name(prompt: str) -> str:
    """Attempts to pull a business/project name from the prompt."""
    m = re.search(r'''["']([A-Z][a-zA-Z0-9 \-]{2,40})["']''', prompt)
    if m:
        return m.group(1).strip()

    m = re.search(
        r'''(?:for|called|named)\s+["']?([A-Z][a-zA-Z0-9]*(?:\s+[A-Za-z][a-zA-Z0-9]*)*)["']?(?:\s*$|\s*,|\s*\.)''',
        prompt
    )
    if m:
        name = m.group(1).strip()
        words = name.split()
        _TRAIL_STOP = {"showcase", "website", "landing", "page", "app", "platform", "tool", "site"}
        while words and words[-1].lower() in _TRAIL_STOP:
            words = words[:-1]
        if words:
            return " ".join(words)

    STOP = {
        "Write", "Create", "Build", "Make", "Design", "Generate", "Develop",
        "A", "An", "The", "My", "Our", "New", "React", "TypeScript", "Website",
        "Page", "Site", "Landing", "Full", "Complete", "Modern", "Beautiful",
        "Restaurant", "Portfolio", "SaaS", "Blog", "Event", "Shop", "Store",
    }
    words = re.findall(r'[A-Z][a-zA-Z0-9]+', prompt)
    candidates = [w for w in words if w not in STOP]
    if len(candidates) >= 2:
        return " ".join(candidates[:3])
    if candidates:
        return candidates[0]

    return "My Business"


def detect_business_type(prompt: str) -> str:
    """
    Detects the business type from prompt using weighted confidence scoring.
    Covers all 15+ domains in the unified registry with deterministic priority.
    """
    prompt_lower = prompt.lower()
    scores: dict[str, int] = {k: 0 for k in _BUSINESS_TYPE_WEIGHTS}

    for btype, kw_weights in _BUSINESS_TYPE_WEIGHTS.items():
        for kw, weight in kw_weights.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', prompt_lower):
                scores[btype] += weight

    best_type = max(scores, key=scores.get)
    if scores[best_type] > 0:
        return best_type

    # Fallback to broad keyword scan
    if any(k in prompt_lower for k in ["food", "restaurant", "menu", "cafe", "bistro", "ramen"]):
        return "restaurant"
    if any(k in prompt_lower for k in ["portfolio", "freelance", "resume", "designer"]):
        return "portfolio"
    if any(k in prompt_lower for k in ["payment", "fintech", "banking", "treasury"]):
        return "fintech"
    if any(k in prompt_lower for k in ["dental", "dentistry", "clinic", "doctor", "healthcare"]):
        return "healthcare"
    if any(k in prompt_lower for k in ["villa", "estate", "property", "realty"]):
        return "realestate"
    if any(k in prompt_lower for k in ["charity", "nonprofit", "conservation", "wildlife"]):
        return "nonprofit"
    if any(k in prompt_lower for k in ["bootcamp", "academy", "curriculum", "syllabus", "course"]):
        return "education"
    if any(k in prompt_lower for k in ["architect", "blueprint", "atelier"]):
        return "architecture"
    if any(k in prompt_lower for k in ["coffee", "roast", "beans"]):
        return "coffee"
    if any(k in prompt_lower for k in ["store", "shop", "ecommerce", "cart"]):
        return "ecommerce"
    if any(k in prompt_lower for k in ["gym", "workout", "crossfit", "fitness"]):
        return "fitness"

    return "saas"


def extract_explicit_sections_and_instructions(prompt: str) -> tuple[Optional[list[str]], dict[str, str]]:
    """
    Parses prompt for explicit numbered/bulleted section declarations.
    Detects numbered lists (1., 1), (1), 1:) and bulleted lists (-, *, •).
    Extracts user-authored section labels and custom instructions.
    Returns (sections_list, custom_instructions_dict) or (None, {}).
    """
    # Exclude common non-section bullet headers (e.g. "Design requirements:", "Color palette:")
    NON_SECTION_PREFIXES = {
        "design", "requirement", "requirements", "color", "palette", "typography",
        "font", "button", "card", "styling", "rules", "guidelines", "constraint", "constraints",
        "tech", "stack", "note", "notes", "overview"
    }

    matches: list[tuple[str, str]] = []

    # Strategy 1: Check for an explicit "Sections:" or "Pages:" or "Structure:" block
    sec_block_m = re.search(
        r'(?:^|\n)\s*(?:[-*•\u2022]|\d+[\.\)])?\s*(?:Sections?|Pages?|Structure|Components?)\s*:\s*\n([\s\S]+?)(?=\n\s*(?:[A-Z][a-zA-Z\s_-]+:|\Z))',
        prompt,
        re.IGNORECASE
    )
    if sec_block_m:
        block_text = sec_block_m.group(1)
        # Parse items in the block (numbered or bulleted)
        item_pattern = re.compile(
            r'(?:^|\n)\s*(?:(?:\d+[\.\)\:]|\(\d+\))|[-*•\u2022])\s*([A-Za-z0-9][\w\s/&-]+?)(?:\s*[-:\u2013\u2014]\s*([^\n]+(?:\n(?!\s*(?:(?:\d+[\.\)\:]|\(\d+\))|[-*•\u2022]))[^\n]+)*)|\s*$(?:\n|$))',
            re.MULTILINE
        )
        for m in item_pattern.finditer(block_text):
            raw_name = m.group(1).strip()
            raw_desc = (m.group(2) or "").strip()
            slug_cand = re.sub(r'[^a-z0-9]+', '_', raw_name.lower()).strip('_')
            if slug_cand and slug_cand not in NON_SECTION_PREFIXES:
                matches.append((raw_name, raw_desc))

    # Strategy 2: If no block found or fewer than 2 items, look for numbered sections anywhere:
    # 1. Header: ... 2. Hero: ... or 1) Practice Areas ... 2) Attorneys ...
    if len(matches) < 2:
        matches = []
        numbered_pattern = re.compile(
            r'(?:^|\n)\s*(?:(?:\d+[\.\)\:]|\(\d+\)))\s*([A-Za-z0-9][\w\s/&-]+?)(?:\s*[-:\u2013\u2014]\s*([^\n]+(?:\n(?!\s*(?:(?:\d+[\.\)\:]|\(\d+\))|[-*•\u2022]))[^\n]+)*)|\s*$(?:\n|$))',
            re.MULTILINE
        )
        for m in numbered_pattern.finditer(prompt):
            raw_name = m.group(1).strip()
            raw_desc = (m.group(2) or "").strip()
            slug_cand = re.sub(r'[^a-z0-9]+', '_', raw_name.lower()).strip('_')
            if slug_cand and slug_cand not in NON_SECTION_PREFIXES and len(slug_cand) <= 40:
                matches.append((raw_name, raw_desc))

    # Strategy 3: Top-level bulleted list if items look like distinct sections
    if len(matches) < 2:
        bullet_pattern = re.compile(
            r'(?:^|\n)\s*[-*•\u2022]\s*([A-Za-z0-9][\w\s/&-]+?)(?:\s*[-:\u2013\u2014]\s*([^\n]+(?:\n(?!\s*[-*•\u2022]))[^\n]+)*|\s*$(?:\n|$))',
            re.MULTILINE
        )
        candidate_bullets = []
        for m in bullet_pattern.finditer(prompt):
            raw_name = m.group(1).strip()
            raw_desc = (m.group(2) or "").strip()
            first_word = raw_name.lower().split()[0] if raw_name else ""
            if first_word in NON_SECTION_PREFIXES:
                continue
            slug_cand = re.sub(r'[^a-z0-9]+', '_', raw_name.lower()).strip('_')
            if slug_cand and len(slug_cand) <= 35:
                candidate_bullets.append((raw_name, raw_desc))
        if len(candidate_bullets) >= 2:
            matches = candidate_bullets

    if not matches or len(matches) < 2:
        return None, {}

    sections: list[str] = []
    instructions: dict[str, str] = {}
    for raw_name, raw_desc in matches:
        raw_name = raw_name.strip()
        slug = re.sub(r'[^a-z0-9]+', '_', raw_name.lower()).strip('_')
        if not slug:
            continue
        words = [w for w in slug.split('_') if w]
        pascal_name = "".join(w.capitalize() for w in words)
        desc = re.sub(r'\s+', ' ', raw_desc.strip()) if raw_desc else f"High-quality, responsive {raw_name} section."
        sections.append(slug)
        instructions[slug] = (
            f"Write the {raw_name} section: {desc} "
            f"Files: src/components/{pascal_name}.tsx + src/components/{pascal_name}.css"
        )

    # If footer is present, ensure it is at the end
    if "footer" in sections:
        sections = [s for s in sections if s != "footer"] + ["footer"]

    return (sections, instructions) if len(sections) >= 2 else (None, {})


def extract_explicit_sections(prompt: str) -> Optional[list[str]]:
    """
    Detects numbered lists (1., 1), etc.) and bulleted lists (-, *, •) in the raw user prompt.
    Extracts the section names/labels the user wrote themselves (e.g., 'Flagship Products', 'Practice Areas').
    Returns None (not an empty list) when no explicit structure is detected, so callers know
    to fall back to the heuristic planner.
    """
    sections, _ = extract_explicit_sections_and_instructions(prompt)
    return sections


def extract_explicit_section_instructions(prompt: str) -> dict[str, str]:
    """Extracts custom section instruction overrides parsed from explicit prompt declarations."""
    _, instrs = extract_explicit_sections_and_instructions(prompt)
    return instrs


def extract_sections_from_prompt(prompt: str, business_type: str) -> list[str]:
    """
    Dynamically infers the required sections from the user prompt and business domain.
    Explicit user-authored section structure always overrides domain-template heuristics.
    """
    explicit = extract_explicit_sections(prompt)
    if explicit:
        return explicit

    lower = prompt.lower()

    wants_pricing = any(k in lower for k in ["pricing", "price", "calculator", "tier", "subscription", "billing", "plans"])
    wants_testimonials = any(k in lower for k in ["testimonial", "testimonials", "review", "reviews", "carousel", "quote"])
    wants_features = any(k in lower for k in ["feature", "features", "showcase", "services", "capability", "solutions"])
    wants_contact = any(k in lower for k in ["contact", "contact us", "reach", "hire", "inquiry"])
    wants_cta = any(k in lower for k in ["cta", "signup", "get started", "newsletter", "donate"])

    middle: list[str] = []

    if business_type == "saas":
        middle.append("features")
        if wants_pricing or not any(k in lower for k in ["free only", "no pricing"]):
            middle.append("pricing")
        if wants_testimonials or "carousel" in lower:
            middle.append("testimonials")
        middle.append("cta" if wants_cta else "contact")

    elif business_type == "restaurant":
        middle.append("menu")
        middle.append("about")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "portfolio":
        middle.append("projects")
        middle.append("skills")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "ecommerce":
        middle.append("features")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("cta")

    elif business_type == "fintech":
        middle.append("features")
        middle.append("pricing")
        if wants_testimonials or "review" in lower: middle.append("testimonials")
        middle.append("cta")

    elif business_type == "healthcare":
        middle.append("features")
        if wants_testimonials or "review" in lower: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "realestate":
        middle.append("features")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "education":
        middle.append("features")
        middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("cta")

    elif business_type == "nonprofit":
        middle.append("features")
        if wants_testimonials: middle.append("testimonials")
        middle.append("cta")  # Donate CTA rather than commercial pricing

    elif business_type == "agency":
        middle.append("features")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "architecture":
        middle.append("features")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "coffee":
        middle.append("features")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "fitness":
        middle.append("features")
        middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "blog":
        middle.append("features")
        middle.append("cta")  # Newsletter CTA

    else:
        middle = ["features", "testimonials", "contact"]

    seen = {"header", "hero"}
    assembled = ["header", "hero"]
    for sec in middle:
        if sec not in seen:
            seen.add(sec)
            assembled.append(sec)
    assembled.append("footer")
    return assembled


# ==============================================================================
# 3. Heuristic Brief Builder
# ==============================================================================

def _build_heuristic_brief(prompt: str, style_spec: Optional[StyleSpec] = None) -> dict:
    """Builds a rich, domain-tailored structured content brief using the unified domain registry and optional StyleSpec."""
    business_name = extract_business_name(prompt)
    business_type = detect_business_type(prompt)

    template = dict(_DOMAIN_TEMPLATES.get(business_type, _SAAS_TEMPLATE))
    theme = _DOMAIN_THEMES.get(business_type, _DOMAIN_THEMES["saas"])
    
    explicit_sections = extract_explicit_sections(prompt)
    if explicit_sections:
        dynamic_sections = explicit_sections
        explicit_instructions = extract_explicit_section_instructions(prompt)
    else:
        dynamic_sections = extract_sections_from_prompt(prompt, business_type)
        explicit_instructions = {}

    lower_prompt = prompt.lower()
    if style_spec:
        primary_color = style_spec.get_primary_color()
    elif any(k in lower_prompt for k in ["dark", "black", "night", "obsidian"]):
        primary_color = theme.get("primary_color_dark", theme["primary_color"])
    elif any(k in lower_prompt for k in ["light", "paper", "white", "bright", "clean", "minimal"]):
        primary_color = theme.get("primary_color_light", theme["primary_color"])
    else:
        primary_color = theme["primary_color"]

    accent_color = style_spec.get_accent_color() if style_spec else theme["accent_color"]
    font_heading = style_spec.get_heading_font() if style_spec else theme["font_heading"]
    font_body = style_spec.get_body_font() if style_spec else theme["font_body"]

    res = {
        **template,
        "business_name": business_name,
        "business_type": business_type,
        "sections": dynamic_sections,
        "custom_section_instructions": explicit_instructions,
        "tagline": f"{business_name} - {theme['default_tagline']}",
        "primary_color": primary_color,
        "primary_color_light": theme.get("primary_color_light", "#ffffff"),
        "primary_color_dark": theme.get("primary_color_dark", "#0b0f19"),
        "accent_color": accent_color,
        "accent_secondary": theme.get("accent_secondary", "#6366f1"),
        "font_heading": font_heading,
        "font_body": font_body,
        "border_radius": theme.get("border_radius", "6px"),
        "source": "heuristic",
    }
    if style_spec:
        res["style_spec"] = style_spec
    return res


# ==============================================================================
# 4. LLM-Powered Brief Builder & Public API
# ==============================================================================

_BRIEF_SYSTEM_PROMPT = (
    "You are a web content strategist. Given a one-line website request, produce a structured JSON content brief. "
    "Respond with ONLY valid JSON - no markdown fences, no explanation. "
    "Required keys: business_name, tagline, business_type, primary_color, accent_color, "
    "font_heading, font_body, sections (list), contact (dict). "
    "For restaurants add menu_categories. For SaaS/portfolio add features."
)


def _call_gemini_brief(prompt: str, api_key: str, model: str = "gemini-2.0-flash") -> Optional[dict]:
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": _BRIEF_SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": f"Website request: {prompt}"}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _call_openai_brief(prompt: str, api_key: str, base_url: str = "https://api.openai.com/v1",
                       model: str = "gpt-4o-mini") -> Optional[dict]:
    import urllib.request
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _BRIEF_SYSTEM_PROMPT},
            {"role": "user", "content": f"Website request: {prompt}"},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return json.loads(body["choices"][0]["message"]["content"])


def generate_content_brief(
    prompt: str,
    provider: str = "auto",
    style_tokens: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> dict:
    """
    Expands a one-line user prompt into a structured content brief for the site pipeline.
    Decouples visual aesthetics by checking for custom style_tokens, style_preset, or prompt :root tokens.
    """
    # 1. Resolve StyleSpec
    resolved_style: Optional[StyleSpec] = None
    if style_tokens and "--" in style_tokens:
        resolved_style = parse_css_tokens(style_tokens, name="Custom Ingested Tokens", source="refero" if "refero" in style_tokens.lower() else "custom")
    elif style_preset and style_preset in PRESET_STYLES:
        resolved_style = PRESET_STYLES[style_preset]
    elif ":root" in prompt and "--" in prompt:
        resolved_style = parse_css_tokens(prompt, name="Prompt Embedded Tokens", source="prompt")
    else:
        # Detect archetype keywords in prompt
        low_prompt = prompt.lower()
        if "refero" in low_prompt or "monopo" in low_prompt or "editorial" in low_prompt:
            resolved_style = PRESET_STYLES["refero_editorial"]
        elif "brutalist" in low_prompt or "brutalism" in low_prompt:
            resolved_style = PRESET_STYLES["neo_brutalist"]
        elif "glassmorphic" in low_prompt or "glassmorphism" in low_prompt:
            resolved_style = PRESET_STYLES["glassmorphic_aurora"]
        elif "luxury" in low_prompt or "champagne" in low_prompt:
            resolved_style = PRESET_STYLES["luxury_minimalist"]
        elif "cyberpunk" in low_prompt:
            resolved_style = PRESET_STYLES["cyberpunk_neon"]

    # 2. Brief synthesis
    if provider in ("auto", "gemini"):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            try:
                brief = _call_gemini_brief(prompt, api_key)
                if brief and "business_name" in brief:
                    brief["source"] = "gemini"
                    if resolved_style:
                        brief["style_spec"] = resolved_style
                        brief["primary_color"] = resolved_style.get_primary_color()
                        brief["accent_color"] = resolved_style.get_accent_color()
                        brief["font_heading"] = resolved_style.get_heading_font()
                        brief["font_body"] = resolved_style.get_body_font()
                    return brief
            except Exception as e:
                print(f"[site_brief] Gemini API call failed, falling back: {e}")

    if provider in ("auto", "openai"):
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
                brief = _call_openai_brief(prompt, api_key, base_url)
                if brief and "business_name" in brief:
                    brief["source"] = "openai"
                    if resolved_style:
                        brief["style_spec"] = resolved_style
                        brief["primary_color"] = resolved_style.get_primary_color()
                        brief["accent_color"] = resolved_style.get_accent_color()
                        brief["font_heading"] = resolved_style.get_heading_font()
                        brief["font_body"] = resolved_style.get_body_font()
                    return brief
            except Exception as e:
                print(f"[site_brief] OpenAI API call failed, falling back: {e}")

    return _build_heuristic_brief(prompt, style_spec=resolved_style)


# ==============================================================================
# 5. XML Serialization for Agent Prompting
# ==============================================================================

def brief_to_xml(brief: dict) -> str:
    """Formats a structured brief into XML tags consumed by the site agent."""
    lines = ["<content_brief>"]
    lines.append(f"  <business_name>{brief.get('business_name', 'My Business')}</business_name>")
    lines.append(f"  <business_type>{brief.get('business_type', 'general')}</business_type>")
    lines.append(f"  <tagline>{brief.get('tagline', '')}</tagline>")

    spec: Optional[StyleSpec] = brief.get("style_spec")
    if spec:
        lines.append(f'  <design_system style_name="{spec.name}" source="{spec.source}">')
        lines.append(f"    <primary_color>{spec.get_primary_color()}</primary_color>")
        lines.append(f"    <accent_color>{spec.get_accent_color()}</accent_color>")
        lines.append(f"    <font_heading>{spec.get_heading_font()}</font_heading>")
        lines.append(f"    <font_body>{spec.get_body_font()}</font_body>")
        lines.append("    <css_variables>")
        lines.append(spec.raw_css if spec.raw_css else spec_to_css_root(spec))
        lines.append("    </css_variables>")
        if spec.dos or spec.donts:
            lines.append("    <design_rules>")
            for d in spec.dos:
                lines.append(f'      <rule type="do">{d}</rule>')
            for d in spec.donts:
                lines.append(f'      <rule type="dont">{d}</rule>')
            lines.append("    </design_rules>")
        lines.append("  </design_system>")
    else:
        lines.append("  <design_system>")
        lines.append(f"    <primary_color>{brief.get('primary_color', '#0f172a')}</primary_color>")
        lines.append(f"    <accent_color>{brief.get('accent_color', '#38bdf8')}</accent_color>")
        if brief.get("accent_secondary"):
            lines.append(f"    <accent_secondary>{brief['accent_secondary']}</accent_secondary>")
        lines.append(f"    <font_heading>{brief.get('font_heading', 'Inter')}</font_heading>")
        lines.append(f"    <font_body>{brief.get('font_body', 'Inter')}</font_body>")
        lines.append("  </design_system>")

    lines.append("  <sections>")
    for sec in brief.get("sections", ["header", "hero", "features", "footer"]):
        lines.append(f"    <section>{sec}</section>")
    lines.append("  </sections>")

    if "features" in brief and brief["features"]:
        lines.append("  <features>")
        for feat in brief["features"]:
            icon = feat.get('icon', 'bolt')
            title = feat.get('title', '')
            desc = feat.get('description', '')
            lines.append(f'    <feature icon="{icon}" title="{title}">{desc}</feature>')
        lines.append("  </features>")

    if "pricing_tiers" in brief and brief["pricing_tiers"]:
        lines.append("  <pricing_tiers>")
        for tier in brief["pricing_tiers"]:
            rec = ' recommended="true"' if tier.get('recommended') else ''
            t_name = tier.get('name', '')
            t_price = tier.get('price', '')
            t_period = tier.get('period', 'month')
            lines.append(f'    <tier name="{t_name}" price="{t_price}" period="{t_period}"{rec}>')
            for f in tier.get("features", []):
                lines.append(f"      <item>{f}</item>")
            lines.append("    </tier>")
        lines.append("  </pricing_tiers>")

    if "testimonials" in brief and brief["testimonials"]:
        lines.append("  <testimonials>")
        for t in brief["testimonials"]:
            author = t.get('author', 'Verified Client')
            role = t.get('role', '')
            quote = t.get('quote', '')
            rating = t.get('rating', 5)
            lines.append(f'    <testimonial author="{author}" role="{role}" rating="{rating}">')
            lines.append(f"      <quote>{quote}</quote>")
            lines.append("    </testimonial>")
        lines.append("  </testimonials>")

    if "menu_categories" in brief and brief["menu_categories"]:
        lines.append("  <menu>")
        for cat in brief["menu_categories"]:
            cat_name = cat.get('name', '')
            lines.append(f'    <category name="{cat_name}">')
            for item in cat.get("items", []):
                price = item.get('price', '')
                name = item.get('name', '')
                desc = item.get('description', '')
                lines.append(f'      <item name="{name}" price="{price}">{desc}</item>')
            lines.append("    </category>")
        lines.append("  </menu>")

    if "projects" in brief and brief["projects"]:
        lines.append("  <projects>")
        for proj in brief["projects"]:
            name = proj.get('name', '')
            desc = proj.get('description', '')
            tech = ", ".join(proj.get('tech', []))
            lines.append(f'    <project name="{name}" tech="{tech}">{desc}</project>')
        lines.append("  </projects>")

    if "skills" in brief and brief["skills"]:
        lines.append(f"  <skills>{', '.join(brief['skills'])}</skills>")

    if "contact" in brief and brief["contact"]:
        lines.append("  <contact>")
        for k, v in brief["contact"].items():
            lines.append(f"    <{k}>{v}</{k}>")
        lines.append("  </contact>")

    lines.append("</content_brief>")
    return "\n".join(lines)
