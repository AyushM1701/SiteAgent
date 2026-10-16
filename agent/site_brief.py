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
import html
import os
import re
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple

try:
    from agent.stock_photos import (
        _map_to_concrete_photo_query, _is_valid_photograph,
        _resolve_curated_stock_photo, _STOCK_PHOTO_CURATED_CATALOG,
        fetch_single_image, resolve_site_images,
    )
except ImportError:
    from stock_photos import (
        _map_to_concrete_photo_query, _is_valid_photograph,
        _resolve_curated_stock_photo, _STOCK_PHOTO_CURATED_CATALOG,
        fetch_single_image, resolve_site_images,
    )

try:
    from agent.style_ingest import (
        StyleSpec,
        parse_css_tokens,
        PRESET_STYLES,
        resolve_style_preset,
        get_available_style_presets,
        spec_to_css_root,
        spec_to_prompt_instructions,
    )
except ImportError:
    from style_ingest import (
        StyleSpec,
        parse_css_tokens,
        PRESET_STYLES,
        resolve_style_preset,
        get_available_style_presets,
        spec_to_css_root,
        spec_to_prompt_instructions,
    )

try:
    from agent.motion_patterns import (
        MotionSpec,
        MotionType,
        extract_motion_requirements,
        motion_plan_to_xml,
    )
except ImportError:
    from motion_patterns import (
        MotionSpec,
        MotionType,
        extract_motion_requirements,
        motion_plan_to_xml,
    )



# ==============================================================================
# 1. Unified Domain Registry (15+ Domains)
# ==============================================================================

_BUSINESS_TYPE_WEIGHTS: dict[str, dict[str, int]] = {
    "saas": {
        "saas": 12, "software": 9, "ai platform": 9, "dashboard": 6,
        "analytics platform": 8, "cloud platform": 8, "workflow automation": 8,
        "subscription software": 9,
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
        "health": 10, "diagnostic": 9, "diagnostics": 9, "physician": 9,
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
        "consultancy": 8, "client showcase": 8, "law": 10, "legal": 10, "litigation": 10, "attorneys": 10, "counsel": 10,
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

class ThemeVariantList(list):
    """
    A list of theme variant dicts that also acts as a dict delegating to the primary (first) variant.
    Ensures 100% backward compatibility for any caller doing _DOMAIN_THEMES['saas']['primary_color'].
    """
    def __getitem__(self, item):
        if isinstance(item, str):
            return self[0][item]
        return super().__getitem__(item)

    def get(self, key, default=None):
        if isinstance(key, str) and len(self) > 0:
            return self[0].get(key, default)
        return default

# 15+ Domains with 2-3 alternate palette options each, including at least one light/paper option per domain.
# Body fonts drawn from curated set: Inter, Manrope, Source Sans 3, IBM Plex Sans, Work Sans, Space Grotesk.
# Heading fonts drawn from curated set: Plus Jakarta Sans, Outfit, Space Grotesk, Fraunces, DM Serif Display,
# Playfair Display, Syne, Cabinet Grotesk, Cormorant Garamond, Cinzel, Bricolage Grotesque, Newsreader.
# Every variant features a duotone accent pair: accent_color and accent_secondary.

_DOMAIN_THEMES = {
    "saas": ThemeVariantList([
        {
            "variant_name": "obsidian",
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
        {
            "variant_name": "clean_paper",
            "primary_color": "#f8fafc",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#0f172a",
            "accent_color": "#4f46e5",
            "accent_secondary": "#0ea5e9",
            "font_heading": "Outfit",
            "font_body": "Manrope",
            "border_radius": "8px",
            "default_tagline": "Modern infrastructure automation and release telemetry for engineering teams",
        },
        {
            "variant_name": "deep_slate",
            "primary_color": "#0f172a",
            "primary_color_light": "#f1f5f9",
            "primary_color_dark": "#020617",
            "accent_color": "#0d9488",
            "accent_secondary": "#10b981",
            "font_heading": "Space Grotesk",
            "font_body": "IBM Plex Sans",
            "border_radius": "4px",
            "default_tagline": "Fault-tolerant data pipelines and cloud observability at global scale",
        },
    ]),
    "restaurant": ThemeVariantList([
        {
            "variant_name": "warm_cream_paper",
            "primary_color": "#fdfbf7",
            "primary_color_light": "#fdfbf7",
            "primary_color_dark": "#1c1917",
            "accent_color": "#c2410c",
            "accent_secondary": "#d97706",
            "font_heading": "Fraunces",
            "font_body": "Manrope",
            "border_radius": "8px",
            "default_tagline": "Handcrafted seasonal dishes sourced from regional farms and prepared over open woodfire",
        },
        {
            "variant_name": "intimate_bistro_dark",
            "primary_color": "#1c140e",
            "primary_color_light": "#faf5f0",
            "primary_color_dark": "#140d09",
            "accent_color": "#f59e0b",
            "accent_secondary": "#ef4444",
            "font_heading": "DM Serif Display",
            "font_body": "Work Sans",
            "border_radius": "6px",
            "default_tagline": "Candlelit dining, curated natural wines, and rustic seasonal heritage recipes",
        },
        {
            "variant_name": "nordic_cafe_stone_paper",
            "primary_color": "#f5f5f4",
            "primary_color_light": "#fafaf9",
            "primary_color_dark": "#292524",
            "accent_color": "#854d0e",
            "accent_secondary": "#15803d",
            "font_heading": "Playfair Display",
            "font_body": "Source Sans 3",
            "border_radius": "2px",
            "default_tagline": "Artisanal bakery, organic sourdough, and single-origin morning espresso",
        },
    ]),
    "portfolio": ThemeVariantList([
        {
            "variant_name": "studio_noir_dark",
            "primary_color": "#121214",
            "primary_color_light": "#fafafa",
            "primary_color_dark": "#0a0a0c",
            "accent_color": "#059669",
            "accent_secondary": "#7c3aed",
            "font_heading": "Syne",
            "font_body": "Work Sans",
            "border_radius": "0px",
            "default_tagline": "Selected design systems, product architecture, and human-computer interfaces",
        },
        {
            "variant_name": "gallery_paper_light",
            "primary_color": "#fbfbfa",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#18181b",
            "accent_color": "#e11d48",
            "accent_secondary": "#2563eb",
            "font_heading": "Cabinet Grotesk",
            "font_body": "IBM Plex Sans",
            "border_radius": "0px",
            "default_tagline": "Spatial art direction, editorial publications, and digital identity systems",
        },
        {
            "variant_name": "editorial_zinc_dark",
            "primary_color": "#18181b",
            "primary_color_light": "#f4f4f5",
            "primary_color_dark": "#09090b",
            "accent_color": "#d97706",
            "accent_secondary": "#6366f1",
            "font_heading": "Cormorant Garamond",
            "font_body": "Source Sans 3",
            "border_radius": "4px",
            "default_tagline": "Interactive computational design and generative software engineering",
        },
    ]),
    "ecommerce": ThemeVariantList([
        {
            "variant_name": "clean_white_paper",
            "primary_color": "#ffffff",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#0f172a",
            "accent_color": "#0284c7",
            "accent_secondary": "#e11d48",
            "font_heading": "Outfit",
            "font_body": "Source Sans 3",
            "border_radius": "9999px",
            "default_tagline": "Functional goods and technical apparel engineered for daily durability",
        },
        {
            "variant_name": "luxury_boutique_dark",
            "primary_color": "#141416",
            "primary_color_light": "#f5f5f7",
            "primary_color_dark": "#0d0d0f",
            "accent_color": "#e2b170",
            "accent_secondary": "#9333ea",
            "font_heading": "Cinzel",
            "font_body": "Work Sans",
            "border_radius": "4px",
            "default_tagline": "Bespoke fine jewelry, chronographs, and rare mechanical objects",
        },
        {
            "variant_name": "streetwear_slate",
            "primary_color": "#0f172a",
            "primary_color_light": "#f8fafc",
            "primary_color_dark": "#020617",
            "accent_color": "#f97316",
            "accent_secondary": "#06b6d4",
            "font_heading": "Bricolage Grotesque",
            "font_body": "Manrope",
            "border_radius": "6px",
            "default_tagline": "Limited-edition footwear, tactical accessories, and modular outerwear",
        },
    ]),
    "fitness": ThemeVariantList([
        {
            "variant_name": "iron_forge_dark",
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
        {
            "variant_name": "performance_chalk_paper",
            "primary_color": "#f4f4f5",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#18181b",
            "accent_color": "#0284c7",
            "accent_secondary": "#10b981",
            "font_heading": "Space Grotesk",
            "font_body": "Source Sans 3",
            "border_radius": "6px",
            "default_tagline": "High-output athletic conditioning and biometric movement telemetry",
        },
        {
            "variant_name": "movement_linen_warm",
            "primary_color": "#fdf8f4",
            "primary_color_light": "#fffbf7",
            "primary_color_dark": "#27272a",
            "accent_color": "#059669",
            "accent_secondary": "#d97706",
            "font_heading": "Outfit",
            "font_body": "Work Sans",
            "border_radius": "12px",
            "default_tagline": "Holistic mobility studio, restorative hot yoga, and guided breathwork",
        },
    ]),
    "event": ThemeVariantList([
        {
            "variant_name": "summit_night_dark",
            "primary_color": "#090d16",
            "primary_color_light": "#faf5ff",
            "primary_color_dark": "#090d16",
            "accent_color": "#db2777",
            "accent_secondary": "#7c3aed",
            "font_heading": "Space Grotesk",
            "font_body": "IBM Plex Sans",
            "border_radius": "12px",
            "default_tagline": "Two days of deep technical talks, systems architecture, and design workshops",
        },
        {
            "variant_name": "biennale_lilac_paper",
            "primary_color": "#faf5ff",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#1e1b4b",
            "accent_color": "#6366f1",
            "accent_secondary": "#ec4899",
            "font_heading": "Cabinet Grotesk",
            "font_body": "Work Sans",
            "border_radius": "8px",
            "default_tagline": "International festival of contemporary typography, media art, and architecture",
        },
        {
            "variant_name": "executive_slate",
            "primary_color": "#0f172a",
            "primary_color_light": "#f8fafc",
            "primary_color_dark": "#020617",
            "accent_color": "#0284c7",
            "accent_secondary": "#eab308",
            "font_heading": "Plus Jakarta Sans",
            "font_body": "Source Sans 3",
            "border_radius": "6px",
            "default_tagline": "Global economic symposium, private roundtables, and keynote assemblies",
        },
    ]),
    "blog": ThemeVariantList([
        {
            "variant_name": "newsprint_paper_light",
            "primary_color": "#fefefe",
            "primary_color_light": "#fefefe",
            "primary_color_dark": "#18181b",
            "accent_color": "#2563eb",
            "accent_secondary": "#4f46e5",
            "font_heading": "Newsreader",
            "font_body": "Source Sans 3",
            "border_radius": "2px",
            "default_tagline": "Longform essays on distributed infrastructure, compiler internals, and software craftsmanship",
        },
        {
            "variant_name": "code_charcoal_dark",
            "primary_color": "#18181b",
            "primary_color_light": "#fafafa",
            "primary_color_dark": "#09090b",
            "accent_color": "#10b981",
            "accent_secondary": "#06b6d4",
            "font_heading": "Space Grotesk",
            "font_body": "IBM Plex Sans",
            "border_radius": "4px",
            "default_tagline": "Technical retrospectives, systems benchmarks, and kernel engineering dispatches",
        },
        {
            "variant_name": "warm_parchment_paper",
            "primary_color": "#fcf8f2",
            "primary_color_light": "#fffdf9",
            "primary_color_dark": "#292524",
            "accent_color": "#9a3412",
            "accent_secondary": "#d97706",
            "font_heading": "Cormorant Garamond",
            "font_body": "Work Sans",
            "border_radius": "0px",
            "default_tagline": "Philosophical inquiries, cultural critique, and slow-form critical thought",
        },
    ]),
    "fintech": ThemeVariantList([
        {
            "variant_name": "institutional_navy_dark",
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
        {
            "variant_name": "treasury_paper_light",
            "primary_color": "#f8fafc",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#0f172a",
            "accent_color": "#059669",
            "accent_secondary": "#0284c7",
            "font_heading": "Outfit",
            "font_body": "Manrope",
            "border_radius": "8px",
            "default_tagline": "Real-time treasury yields, corporate card issuance, and automated accounting sync",
        },
        {
            "variant_name": "algorithmic_obsidian_dark",
            "primary_color": "#0b1120",
            "primary_color_light": "#f1f5f9",
            "primary_color_dark": "#020617",
            "accent_color": "#6366f1",
            "accent_secondary": "#14b8a6",
            "font_heading": "Space Grotesk",
            "font_body": "IBM Plex Sans",
            "border_radius": "6px",
            "default_tagline": "Quantitative arbitrage infrastructure and high-throughput execution engines",
        },
    ]),
    "healthcare": ThemeVariantList([
        {
            "variant_name": "clinical_mint_paper",
            "primary_color": "#f0fdf4",
            "primary_color_light": "#f0fdf4",
            "primary_color_dark": "#0a1a24",
            "accent_color": "#0d9488",
            "accent_secondary": "#0284c7",
            "font_heading": "Outfit",
            "font_body": "Source Sans 3",
            "border_radius": "8px",
            "default_tagline": "Evidence-based preventative medicine, diagnostic imaging, and dedicated physician care",
        },
        {
            "variant_name": "diagnostic_deep_navy",
            "primary_color": "#0a1a24",
            "primary_color_light": "#f0fdfa",
            "primary_color_dark": "#051017",
            "accent_color": "#14b8a6",
            "accent_secondary": "#38bdf8",
            "font_heading": "Plus Jakarta Sans",
            "font_body": "Manrope",
            "border_radius": "6px",
            "default_tagline": "Specialized oncology research, genomic diagnostics, and precision surgical centers",
        },
        {
            "variant_name": "sanitary_pure_paper",
            "primary_color": "#ffffff",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#1e293b",
            "accent_color": "#0284c7",
            "accent_secondary": "#10b981",
            "font_heading": "Fraunces",
            "font_body": "Work Sans",
            "border_radius": "12px",
            "default_tagline": "Family dentistry, orthodontic aesthetics, and gentle restorative treatments",
        },
    ]),
    "realestate": ThemeVariantList([
        {
            "variant_name": "coastal_sand_paper",
            "primary_color": "#fbf8f2",
            "primary_color_light": "#fbf8f2",
            "primary_color_dark": "#1c1917",
            "accent_color": "#b45309",
            "accent_secondary": "#4338ca",
            "font_heading": "Cormorant Garamond",
            "font_body": "Source Sans 3",
            "border_radius": "0px",
            "default_tagline": "Architectural estates, private coastal properties, and historic city residences",
        },
        {
            "variant_name": "penthouse_charcoal_dark",
            "primary_color": "#141416",
            "primary_color_light": "#fafaf9",
            "primary_color_dark": "#0a0a0c",
            "accent_color": "#d97706",
            "accent_secondary": "#0d9488",
            "font_heading": "Cinzel",
            "font_body": "Work Sans",
            "border_radius": "2px",
            "default_tagline": "Skyline penthouses, bespoke high-rise residences, and private broker concierge",
        },
        {
            "variant_name": "limestone_paper_light",
            "primary_color": "#f5f5f4",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#292524",
            "accent_color": "#047857",
            "accent_secondary": "#b45309",
            "font_heading": "Playfair Display",
            "font_body": "Manrope",
            "border_radius": "4px",
            "default_tagline": "Modern sustainable developments, passive solar villas, and hillside sanctuaries",
        },
    ]),
    "education": ThemeVariantList([
        {
            "variant_name": "campus_slate_paper",
            "primary_color": "#f8f9fa",
            "primary_color_light": "#f8f9fa",
            "primary_color_dark": "#090d16",
            "accent_color": "#4f46e5",
            "accent_secondary": "#0284c7",
            "font_heading": "Outfit",
            "font_body": "IBM Plex Sans",
            "border_radius": "6px",
            "default_tagline": "Rigorous cohort courses in systems programming, distributed databases, and security",
        },
        {
            "variant_name": "polytechnic_navy_dark",
            "primary_color": "#090d16",
            "primary_color_light": "#f1f5f9",
            "primary_color_dark": "#030712",
            "accent_color": "#06b6d4",
            "accent_secondary": "#10b981",
            "font_heading": "Space Grotesk",
            "font_body": "Source Sans 3",
            "border_radius": "4px",
            "default_tagline": "Hands-on machine learning fellowships, GPU cluster access, and mentor code reviews",
        },
        {
            "variant_name": "parchment_library_paper",
            "primary_color": "#fcfaf6",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#262626",
            "accent_color": "#b45309",
            "accent_secondary": "#4338ca",
            "font_heading": "Newsreader",
            "font_body": "Work Sans",
            "border_radius": "8px",
            "default_tagline": "Classical seminar intensives in literature, epistemology, and historical philosophy",
        },
    ]),
    "nonprofit": ThemeVariantList([
        {
            "variant_name": "sage_conservation_paper",
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
        {
            "variant_name": "evergreen_canopy_dark",
            "primary_color": "#042f2e",
            "primary_color_light": "#ecfdf5",
            "primary_color_dark": "#021e1d",
            "accent_color": "#10b981",
            "accent_secondary": "#f59e0b",
            "font_heading": "Fraunces",
            "font_body": "Source Sans 3",
            "border_radius": "6px",
            "default_tagline": "Old-growth rainforest purchase, watershed defense, and indigenous rights advocacy",
        },
        {
            "variant_name": "solar_warm_paper",
            "primary_color": "#fffbeb",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#1c1917",
            "accent_color": "#ea580c",
            "accent_secondary": "#0d9488",
            "font_heading": "Bricolage Grotesque",
            "font_body": "Work Sans",
            "border_radius": "12px",
            "default_tagline": "Community nutrition networks, clean drinking water wells, and rural clinic logistics",
        },
    ]),
    "agency": ThemeVariantList([
        {
            "variant_name": "brutalist_studio_dark",
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
        {
            "variant_name": "swiss_creative_paper",
            "primary_color": "#fafaf9",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#18181b",
            "accent_color": "#2563eb",
            "accent_secondary": "#f97316",
            "font_heading": "Syne",
            "font_body": "Work Sans",
            "border_radius": "0px",
            "default_tagline": "Grid systems, typographic art direction, and high-performance interactive motion",
        },
        {
            "variant_name": "midnight_atelier_indigo",
            "primary_color": "#0e131f",
            "primary_color_light": "#f5f7ff",
            "primary_color_dark": "#05070d",
            "accent_color": "#8b5cf6",
            "accent_secondary": "#06b6d4",
            "font_heading": "Outfit",
            "font_body": "Manrope",
            "border_radius": "6px",
            "default_tagline": "End-to-end venture building, digital transformation, and scalable design infrastructure",
        },
    ]),
    "architecture": ThemeVariantList([
        {
            "variant_name": "limestone_paper_light",
            "primary_color": "#f5f5f4",
            "primary_color_light": "#f5f5f4",
            "primary_color_dark": "#1c1917",
            "accent_color": "#57534e",
            "accent_secondary": "#d97706",
            "font_heading": "Cinzel",
            "font_body": "Source Sans 3",
            "border_radius": "0px",
            "default_tagline": "Monolithic timber pavilions, passive solar dwellings, and landscape-integrated spaces",
        },
        {
            "variant_name": "charred_cedar_dark",
            "primary_color": "#141414",
            "primary_color_light": "#f5f5f5",
            "primary_color_dark": "#0a0a0a",
            "accent_color": "#c5a059",
            "accent_secondary": "#78716c",
            "font_heading": "Cormorant Garamond",
            "font_body": "Work Sans",
            "border_radius": "0px",
            "default_tagline": "Minimalist concrete compounds, cantilevered private retreats, and acoustic chambers",
        },
        {
            "variant_name": "glass_steel_slate",
            "primary_color": "#0f172a",
            "primary_color_light": "#f8fafc",
            "primary_color_dark": "#020617",
            "accent_color": "#0284c7",
            "accent_secondary": "#e2b170",
            "font_heading": "Space Grotesk",
            "font_body": "IBM Plex Sans",
            "border_radius": "2px",
            "default_tagline": "High-density civic infrastructure, public library atriums, and urban revitalizations",
        },
    ]),
    "coffee": ThemeVariantList([
        {
            "variant_name": "oat_milk_parchment_paper",
            "primary_color": "#faf6f0",
            "primary_color_light": "#faf6f0",
            "primary_color_dark": "#292524",
            "accent_color": "#b45309",
            "accent_secondary": "#78716c",
            "font_heading": "DM Serif Display",
            "font_body": "Work Sans",
            "border_radius": "8px",
            "default_tagline": "Direct-trade heirloom varietals freshly roasted weekly in small batches",
        },
        {
            "variant_name": "espresso_bar_dark",
            "primary_color": "#1f1612",
            "primary_color_light": "#fdfaf7",
            "primary_color_dark": "#120c09",
            "accent_color": "#d97706",
            "accent_secondary": "#dc2626",
            "font_heading": "Fraunces",
            "font_body": "Manrope",
            "border_radius": "6px",
            "default_tagline": "Single-origin micro-lots, precision lever pulls, and roasted cacao notes",
        },
        {
            "variant_name": "artisan_flax_linen_paper",
            "primary_color": "#f7f3ed",
            "primary_color_light": "#ffffff",
            "primary_color_dark": "#292524",
            "accent_color": "#854d0e",
            "accent_secondary": "#059669",
            "font_heading": "Playfair Display",
            "font_body": "Source Sans 3",
            "border_radius": "4px",
            "default_tagline": "Washed Ethiopian high-elevation coffees roasted to preserve crisp jasmine aromatics",
        },
    ]),
}

_GENERAL_THEME = {
    "primary_color": "#18212f",
    "primary_color_light": "#f7f7f4",
    "primary_color_dark": "#101827",
    "accent_color": "#4f7087",
    "accent_secondary": "#b97854",
    "font_heading": "Outfit",
    "font_body": "Inter",
    "border_radius": "8px",
    "default_tagline": "",
}


def get_domain_theme(business_type: str, business_name: str = "") -> dict:
    """
    Selects deterministically from the 2-3 palette & typography variants
    configured for this business type, seeded by the business name.
    """
    import hashlib
    variants = _DOMAIN_THEMES.get(business_type)
    if not variants:
        return dict(_GENERAL_THEME)
    if isinstance(variants, list) and variants:
        clean = (business_name or business_type).strip().lower()
        seed = int(hashlib.sha256(clean.encode("utf-8")).hexdigest()[:8], 16)
        return variants[seed % len(variants)]
    elif isinstance(variants, dict):
        return variants
    return dict(_GENERAL_THEME)



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

_NAME_LEAD_RE = re.compile(
    r"""^\s*(?i:(?:build|create|make|design|generate)\s+(?:a\s+|an\s+|the\s+)?(?:website|site|landing page|homepage)\s+(?:for\s+)?)?"""
    r"""["“']?([A-Z0-9][\w&'’.+]*(?:\s+(?:&|and|of|the|de|la|[A-Z0-9][\w&'’.+]*)){0,4})["”']?\s*(?:[—–:]|\s-\s|,\s+(?:a|an|the)\b|\s+is\s+(?:a|an)\b)""",
)
# "Threadleaf stationery shop." — a leading name followed by a lowercase business noun.
_NAME_NOUN_RE = re.compile(
    r"""^\s*([A-Z][\w&'’]+(?:\s+(?:&\s+)?[A-Z][\w&'’]+){0,2})\s+(?:[a-z][\w-]*\s+){0,2}"""
    r"""(?:shop|store|studio|cafe|café|bakery|restaurant|bistro|bar|gym|salon|clinic|agency|boutique|gallery|atelier|co)\b""")
_NAME_REJECT_FIRST = {
    "build", "create", "make", "design", "generate", "website", "portfolio", "landing", "a", "an", "the",
    "sections", "section", "include", "modern", "minimal", "note", "notes", "style", "colors", "colours",
    "palette", "requirements", "my", "our", "restaurant", "bakery", "shop", "store", "new", "please", "write",
    # Field labels that start structured prompts ("Tone: calm", "Hero: big headline").
    "name", "brand", "business", "company", "client", "project", "title", "tagline", "goal", "goals", "audience",
    "tone", "vibe", "mood", "fonts", "font", "typography", "pages", "page", "home", "homepage", "site", "hero",
    "header", "footer", "nav", "navigation", "features", "products", "services", "menu", "contact", "about",
    "faq", "pricing", "important", "update", "request", "brief", "task", "idea", "concept", "summary", "context",
    "background", "overview", "description", "target", "theme", "layout", "look", "feel", "images", "photos",
    "content", "copy", "requirement", "constraints", "must", "avoid", "no", "todo", "deadline", "budget",
    # Greetings and pronouns ("Hi — I need…", "I'm Maya, a…").
    "hi", "hello", "hey", "dear", "i", "i'm", "i’m", "im", "we", "we're", "we’re", "me", "us", "you", "this",
}
_DESCRIPTIVE_NAME_STOP = {"with", "in", "at", "that", "which", "called", "named", "and", "or", "for", "from", "near", "on", "by"}


def _valid_lead_name(candidate: str) -> bool:
    words = candidate.split()
    return bool(words) and words[0].lower() not in _NAME_REJECT_FIRST and len(candidate) <= 40


def _descriptive_business_name(prompt: str) -> Optional[str]:
    """"A landing page for a yoga studio" -> "Yoga Studio"."""
    m = re.search(r"\bfor\s+(?:a|an|my|our)\s+([a-z][\w-]*(?:\s+[a-z][\w-]*){0,2})", prompt)
    if not m:
        return None
    words: list[str] = []
    for word in m.group(1).split():
        if word in _DESCRIPTIVE_NAME_STOP:
            break
        words.append(word)
    return " ".join(w.capitalize() for w in words) or None


_LABELLED_NAME_RES = (
    re.compile(r"""(?im)^[ \t]*(?:(?:business|brand|company|studio|shop|store|project|site|website|restaurant|product)\s+)?"""
               r"""name\s*(?:[:—–]|\s-\s)\s*["“']?([^\n"”'.;,—–]+)"""),
    re.compile(r"""(?im)^[ \t]*(?:brand|business|company|client|studio)\s*(?:[:—–]|\s-\s)\s*["“']?([^\n"”'.;,—–]+)"""),
)
_SELF_INTRO_RE = re.compile(
    r"""^\s*(?i:(?:hi|hello|hey)\b[\s,!.—–-]*)?(?i:i['’]m|i\s+am|we['’]re|we\s+are|this\s+is)\s+["“']?"""
    r"""([A-Z][\w&'’.+-]*(?:\s+(?:&|and|of|the|[A-Z][\w&'’.+-]*)){0,3})""")


def _labelled_or_introduced_name(prompt: str) -> Optional[str]:
    """"Name: Lumen Studio", "Business name - Copperleaf", "I'm Maya, a…", "we are Copper Kettle"."""
    for pattern in _LABELLED_NAME_RES:
        for m in pattern.finditer(prompt):
            value = re.split(r"\s+-\s+", m.group(1).strip())[0].strip()
            if value and (value[0].isupper() or value[0].isdigit()) and len(value) <= 40:
                return value
    m = _SELF_INTRO_RE.match(prompt)
    if m and _valid_lead_name(m.group(1).strip()):
        return m.group(1).strip()
    return None


def extract_business_name(prompt: str) -> str:
    """Attempts to pull a business/project name from the prompt."""
    labelled = _labelled_or_introduced_name(prompt)
    if labelled:
        return labelled
    # Priority 0: a leading name followed by a dash, colon, ", a …" or " is a …"
    # ("Aster & Kiln — handmade ceramics…", "Northwind: a B2B SaaS").
    m = _NAME_LEAD_RE.match(prompt)
    if m and _valid_lead_name(m.group(1).strip()):
        return m.group(1).strip()
    m = _NAME_NOUN_RE.match(prompt)
    if m and _valid_lead_name(m.group(1).strip()):
        return m.group(1).strip()

    name = _extract_business_name_legacy(prompt)
    # A capitalised place after "in/from/based in" is where the business is,
    # not what it is called ("A summer coding camp for kids in Bengaluru").
    if name != "My Business" and re.search(rf"\b(?:in|from|based in|near)\s+{re.escape(name)}\b", prompt):
        name = "My Business"
    if name == "My Business":
        return _descriptive_business_name(prompt) or _leading_noun_phrase_name(prompt) or name
    return name


def _leading_noun_phrase_name(prompt: str) -> Optional[str]:
    """"A summer coding camp for kids in …" -> "Summer Coding Camp"."""
    m = re.match(r"\s*(?:a|an)\s+([a-z][\w-]*(?:\s+[a-z][\w-]*){0,3}?)\s+(?:for|in|with|that|which|near|from|called|named)\b", prompt, re.I)
    if not m:
        return None
    words = [w for w in m.group(1).split() if w.lower() not in {"website", "site", "landing", "page", "homepage"}]
    return " ".join(w.capitalize() for w in words) or None


_RUN_CONNECTORS = {"&", "and", "of", "the", "de", "la", "du", "von", "van"}
_RUN_TRAIL_STOP = {"showcase", "website", "landing", "page", "app", "platform", "tool", "site", "portfolio"}
_QUOTES = "\"'“”‘’`"


def _name_blocklist() -> set[str]:
    try:
        from agent.design_leaks import _DIRECTION_VOCAB as style_vocab
    except ImportError:  # pragma: no cover - script context
        from design_leaks import _DIRECTION_VOCAB as style_vocab  # type: ignore
    return {
        "write", "create", "build", "make", "design", "generate", "develop", "a", "an", "the", "my", "our", "new",
        "react", "typescript", "javascript", "website", "page", "site", "landing", "full", "complete", "modern",
        "beautiful", "restaurant", "portfolio", "saas", "blog", "event", "shop", "store", "sections", "include",
        "email", "cta", "svg", "css", "html", "api", "ui", "ux", "seo", "faq", "nav",
    } | style_vocab | _NON_SECTION_ITEM_WORDS | _NAME_REJECT_FIRST


def _capitalised_run(text: str) -> str:
    """Read a name from the start of text: capitalised words (any script) joined by
    connectors like "&" or "of"; a closing quote, comma or full stop ends it."""
    words: list[str] = []
    opened = text[:1] in _QUOTES
    body = text[1:] if opened else text
    for raw in body.split():
        token = raw.strip(_QUOTES + ",.;:!?()")
        if not token:
            break
        is_name_word = token[0].isupper() or token[0].isdigit()
        if not is_name_word and not (words and token.lower() in _RUN_CONNECTORS):
            break
        words.append(token)
        if raw[-1:] in _QUOTES + ",.;:!?)" or (opened and raw[-1:] in _QUOTES):
            break
        if len(words) >= 5:
            break
    while words and words[-1].lower() in _RUN_CONNECTORS | _RUN_TRAIL_STOP:
        words.pop()
    return " ".join(words)


def _extract_business_name_legacy(prompt: str) -> str:
    blocked = _name_blocklist()

    def acceptable(name: str) -> bool:
        first = name.split()[0].lower() if name else ""
        return bool(name) and first not in blocked and len(name) <= 40

    # Priority 1: "for <Name>", "called <Name>", "named <Name>" (quoted or not, any script).
    for m in re.finditer(r"\b(?:for|called|named|by|at)\s+", prompt):
        name = _capitalised_run(prompt[m.end():])
        if m.group(0).split()[0] in {"by", "at"} and len(name.split()) < 2:
            continue  # "by Monday", "at Home" are not names
        if acceptable(name):
            return name

    # Priority 2: a quoted capitalised name near the start of the prompt.
    for m in re.finditer(r"[\"'“‘](?=[^\W\d_])", prompt[:160]):
        name = _capitalised_run(prompt[m.start():])
        if acceptable(name) and not name.lower().startswith(("http", "www")):
            return name

    # Priority 3: inside a sentence, a run of adjacent capitalised words that is not
    # style vocabulary or a label — at least two words, or one CamelCase brand word
    # ("NexaFlow"). Words from different parts of the prompt are never stitched
    # together ("Kiln Warm Email"), and lone words ("CTA", "Guidelines") are ignored.
    for m in re.finditer(r"(?<=[a-z,;] )(?=[^\W\d_])", prompt):
        name = _capitalised_run(prompt[m.start():])
        words = name.split()
        if not words or any(w.lower() in blocked for w in words if w.lower() not in _RUN_CONNECTORS):
            continue
        camel = len(words) == 1 and re.search(r"[a-z][A-Z]", words[0])
        if len(words) >= 2 or camel:
            return name

    return "My Business"


def detect_business_type(prompt: str) -> str:
    """
    Detects the business type from prompt using weighted confidence scoring.
    Covers all 15+ domains in the unified registry with deterministic priority.
    """
    prompt_lower = prompt.lower()
    # An explicit requested site format outranks incidental subject vocabulary.
    # A coffee ecommerce store is still a store; a cluster health dashboard is
    # still a dashboard rather than a healthcare website.
    format_patterns = (
        ("ecommerce", r"\b(?:e-?commerce|online store|online shop|shopping website|storefront|direct-to-consumer)\b"),
        ("dashboard", r"\b(?:dashboard|admin panel|control panel)\b"),
        ("editorial", r"\b(?:editorial (?:site|website|publication|magazine)|publication|periodical|online magazine|news website|journalism website)\b"),
    )
    for site_type, pattern in format_patterns:
        if re.search(pattern, prompt_lower):
            return site_type
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

    return "general"


def _parse_section_line(line: str) -> tuple[str, str]:
    """Parse a single section bullet/line into (name, description)."""
    cleaned = re.sub(r'^(?:(?:\d+[\.\)\:]|\(\d+\))|[-*•\u2022])\s*', '', line).strip()
    if not cleaned:
        return "", ""

    if re.search(r"\bcase stud(?:y|ies)\b", " ".join(cleaned.split()[:5]), re.I):
        return "Case Studies", cleaned

    delim_m = re.split(r'\s+[:\-–—]\s+', cleaned, maxsplit=1)
    if len(delim_m) == 2 and delim_m[0].strip() and len(delim_m[0].strip()) <= 40:
        return delim_m[0].strip(), cleaned

    canonical_keywords = [
        "Masthead", "Case Studies", "Lightbox", "Manifesto", "Dashboard",
        "Header", "Hero", "Navigation", "Navbar", "Bento Grid", "Features",
        "Propulsion Bento Grid", "Mission Profile", "Narrative", "Calculator",
        "Telemetry Calculator", "Specifications", "Technical Specifications",
        "Testimonials", "Pricing", "FAQ", "Contact", "Footer", "About", "Services",
        "Showcase", "Gallery", "Portfolio", "Timeline", "Stats", "Metrics"
    ]
    for kw in canonical_keywords:
        if re.search(rf'\b{re.escape(kw)}\b', cleaned, re.IGNORECASE):
            return kw, cleaned

    cut_m = re.split(r'\s+(?:with|section|featuring|showcasing|for)\b', cleaned, maxsplit=1, flags=re.IGNORECASE)
    if cut_m and cut_m[0].strip():
        cand = cut_m[0].strip()
        words = cand.split()
        if len(words) <= 4:
            return cand, cleaned

    words = cleaned.split()
    short_name = " ".join(words[:min(3, len(words))])
    return short_name, cleaned


def extract_explicit_sections(prompt: str) -> Optional[List[Tuple[str, str]]]:
    """Detect a user-authored numbered/bulleted section list in the prompt.
    Returns [(slug, description), ...] in order, or None if no explicit
    list structure is present (≥2 matches required to count as a list)."""
    if not prompt or not isinstance(prompt, str):
        return None

    # Exclude common non-section bullet headers (e.g. "Design requirements:", "Color palette:")
    NON_SECTION_PREFIXES = {
        "design", "requirement", "requirements", "color", "palette", "typography",
        "font", "button", "card", "styling", "rules", "guidelines", "constraint", "constraints",
        "tech", "stack", "note", "notes", "overview", "theme", "aesthetic", "aesthetics",
        "motion", "kinetic", "stateful", "react", "interactivity", "interactive", "key",
        "architecture", "architectural", "system", "systems", "atmosphere", "page structure",
        "site structure"
    }

    matches: List[Tuple[str, str]] = []

    # Strategy 1: Check for an explicit "Sections:" or "Sections to Generate:" block
    sec_block_m = re.search(
        r'(?:^|\n)\s*(?:[-*•\u2022]|\d+[\.\)])?\s*(?:Sections?(?:\s+(?:to\s+(?:generate|build|create|include)|required|needed|list|overview|breakdown|structure))?|Pages?(?:\s+(?:to\s+(?:generate|build|create|include)|required|needed|list))?|(?:Page|Site|Key|Website)\s*Structure|Structure|Components?(?:\s+(?:to\s+(?:generate|build|create|include)|required|needed|list))?)\s*:\s*\n([\s\S]+?)(?=\n\s*(?:(?:Technical|Design|Accessibility|Code|Motion)\s+[^:\n]+:|[A-Z][a-zA-Z0-9\s_-]{2,30}:|\Z)|\Z)',
        prompt,
        re.IGNORECASE
    )
    if sec_block_m:
        block_text = sec_block_m.group(1)
        top_num_iter = list(re.finditer(r'(?:^|\n)\s*(?:\d+[\.\)]|\(\d+\))\s+', block_text))
        if len(top_num_iter) >= 2:
            for i, m_num in enumerate(top_num_iter):
                start_p = m_num.end()
                end_p = top_num_iter[i + 1].start() if i + 1 < len(top_num_iter) else len(block_text)
                chunk = block_text[start_p:end_p].strip()
                lines = chunk.splitlines()
                first_line = lines[0].strip() if lines else ""
                desc_lines = [l.strip() for l in lines[1:] if l.strip()]
                raw_name, line_desc = _parse_section_line(first_line)
                first_word = raw_name.lower().split()[0] if raw_name else ""
                if raw_name and first_word not in NON_SECTION_PREFIXES and len(raw_name) <= 50:
                    combined_desc = "\n".join([line_desc] + desc_lines) if desc_lines else (line_desc or f"Write the {raw_name} section.")
                    matches.append((raw_name, combined_desc))
        else:
            for l in block_text.splitlines():
                if l.startswith("   ") or l.startswith("\t"):
                    continue
                l = l.strip()
                if not l:
                    continue
                raw_name, raw_desc = _parse_section_line(l)
                first_word = raw_name.lower().split()[0] if raw_name else ""
                if raw_name and first_word not in NON_SECTION_PREFIXES and len(raw_name) <= 50:
                    matches.append((raw_name, raw_desc or f"Write the {raw_name} section."))

    # Strategy 2: Explicit numbered markers e.g. "1. Header", "1) Header" (strictly line-start only)
    if len(matches) < 2:
        marker_iter = list(re.finditer(r'(?:^|\n)\s*(?:\d+[\.\)]|\(\d+\))\s+', prompt))
        if len(marker_iter) >= 2:
            first_start = marker_iter[0].start()
            prefix_text = prompt[:first_start]
            is_content_list = bool(re.search(
                r'(?:projects?|products?|features?|work|portfolio|portfolio of|links?|articles?|books?|tools?|case studies)\b[^:\n]*:\s*$',
                prefix_text,
                re.IGNORECASE
            ))
            has_urls = bool(re.search(r'https?://|[a-zA-Z0-9-]+\.(?:org|com|app|net|io|dev|duckdns|vercel|onrender)\b', prompt[first_start:]))

            if not is_content_list and not has_urls:
                num_matches: List[Tuple[str, str]] = []
                for i, m in enumerate(marker_iter):
                    start_pos = m.end()
                    end_pos = marker_iter[i + 1].start() if i + 1 < len(marker_iter) else len(prompt)
                    item_text = prompt[start_pos:end_pos].strip()
                    lines = item_text.splitlines()
                    first_line = lines[0].strip() if lines else ""
                    desc_lines = [l.strip() for l in lines[1:] if l.strip()]

                    raw_name, line_desc = _parse_section_line(first_line)
                    first_word = raw_name.lower().split()[0] if raw_name else ""
                    if raw_name and first_word not in NON_SECTION_PREFIXES and 2 <= len(raw_name) <= 50:
                        combined_desc = "\n".join([line_desc] + desc_lines) if desc_lines else (line_desc or f"Write the {raw_name} section.")
                        num_matches.append((raw_name, combined_desc))
                if len(num_matches) >= 2:
                    matches = num_matches

    # Strategy 3: Multiline bulleted items e.g. "- Header: ...", "* Header: ...", "• Header: ..."
    if len(matches) < 2:
        bullet_pattern = re.compile(
            r'^\s*[-*•\u2022]\s*([A-Za-z0-9][\w\s/&-]+?)(?:\s*[:\-–—]\s*(.+))?$',
            re.MULTILINE
        )
        bullet_matches: List[Tuple[str, str]] = []
        for m in bullet_pattern.finditer(prompt):
            label = m.group(1).strip()
            desc = (m.group(2) or "").strip() or f"Write the {label} section."
            if re.search(r'https?://|[a-zA-Z0-9-]+\.(?:org|com|app|net|io|dev|duckdns|vercel|onrender)\b', label + desc):
                continue
            first_word = label.lower().split()[0] if label else ""
            if first_word not in NON_SECTION_PREFIXES and 2 <= len(label) <= 50:
                bullet_matches.append((label, desc))
        if len(bullet_matches) >= 2:
            matches = bullet_matches

    # Strategy 4: Inline "Sections:" lists. Split only at top-level commas so
    # category lists inside parentheses do not become separate site sections.
    if len(matches) < 2:
        inline_m = re.search(r"\bsections?\s*:\s*([^\n]+)", prompt, re.I)
        include_list = False
        if not inline_m:
            # "Include: header, hero, features, footer." is a section list only
            # when its items name sections (not "Include: dark mode, animations").
            inline_m = re.search(r"\b(?:include|includes|including)\s*:\s*([^\n]+)", prompt, re.I)
            include_list = bool(inline_m)
        if inline_m:
            candidate = inline_m.group(1)
            chunks: List[str] = []
            depth = 0
            start = 0
            for i, char in enumerate(candidate):
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth = max(0, depth - 1)
                elif depth == 0 and char in ",.":
                    chunks.append(candidate[start:i].strip())
                    start = i + 1
                    if char == ".":
                        break
            else:
                chunks.append(candidate[start:].strip())
            inline_matches: List[Tuple[str, str]] = []
            for chunk in chunks:
                chunk = re.sub(r"^and\s+", "", chunk.strip(), flags=re.I)
                label, desc = _parse_section_line(chunk)
                if label and label.lower().split()[0] not in NON_SECTION_PREFIXES:
                    inline_matches.append((label, desc or chunk))
            if include_list and any(len(_LEADING_DETERMINERS_RE.sub("", re.sub(r"^and\s+", "", c.strip(), flags=re.I)).split()) > 3
                                    for c in chunks if c.strip()):
                # Descriptive items ("a sticky nav with a CTA") are left to the
                # heuristic planner, which maps them onto canonical sections.
                inline_matches = []
            if include_list:
                known = [label for label, _ in inline_matches
                         if re.fullmatch(r"(?:header|nav|navbar|navigation|hero|footer|banner)", label.lower())
                         or any(re.search(pattern, label.lower()) for pattern in _SECTION_KEYWORD_PATTERNS.values())]
                if len(known) * 2 < max(1, len(inline_matches)):
                    inline_matches = []
            if len(inline_matches) >= 2:
                matches = inline_matches

    # Strategy 5: Explicit list following "with" or "sections:"
    # e.g. "with Header, Hero, Spatial Products, and Footer."
    if len(matches) < 2:
        with_m = re.search(r'(?:with|sections?\s*:)\s+([A-Z][\w\s/&-]+(?:,\s*(?:and\s+)?[A-Z][\w\s/&-]+)+)', prompt)
        if with_m:
            candidate_list = with_m.group(1)
            items = re.split(r',\s*(?:and\s+)?|\s+and\s+', candidate_list)
            with_cands: List[Tuple[str, str]] = []
            for item in items:
                lbl = item.strip().rstrip('.')
                if lbl and len(lbl) <= 50 and lbl.lower() not in NON_SECTION_PREFIXES:
                    with_cands.append((lbl, f"Write the {lbl} section."))
            if len(with_cands) >= 2:
                matches = with_cands

    if len(matches) < 2:
        return None

    def _slugify(text: str) -> str:
        cleaned = re.sub(r'[^a-z0-9\s_-]+', '', text.lower()).strip()
        slug = re.sub(r'[\s_]+', '-', cleaned).strip('-')
        if slug and slug[0].isdigit():
            slug = f"sec-{slug}"
        return slug

    results: List[Tuple[str, str]] = []
    seen = set()
    for raw_label, desc in matches:
        slug = _slugify(raw_label)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        results.append((slug, desc))

    # If footer is present, ensure it is at the end
    footer_tuples = [t for t in results if t[0] == "footer"]
    if footer_tuples:
        results = [t for t in results if t[0] != "footer"] + footer_tuples

    return results if len(results) >= 2 else None


def extract_explicit_sections_and_instructions(prompt: str) -> tuple[Optional[list[str]], dict[str, str]]:
    """Legacy compatibility helper returning (slugs_list, instructions_dict)."""
    res = extract_explicit_sections(prompt)
    if not res:
        return None, {}
    slugs = [slug for slug, _ in res]
    instructions = {}
    for slug, desc in res:
        words = [w for w in re.split(r'[-_]', slug) if w]
        pascal_name = "".join(w.capitalize() for w in words)
        raw_name = " ".join(w.capitalize() for w in words)
        full_desc = desc if desc else f"High-quality, responsive {raw_name} section."
        instructions[slug] = (
            f"Write the {raw_name} section: {full_desc} "
            f"Files: src/components/{pascal_name}.tsx + src/components/{pascal_name}.css"
        )
    return slugs, instructions


def extract_explicit_section_instructions(prompt: str) -> dict[str, str]:
    """Extracts custom section instruction overrides parsed from explicit prompt declarations."""
    _, instrs = extract_explicit_sections_and_instructions(prompt)
    return instrs


def _complete_inline_site_frame(prompt: str, sections: list[str], business_type: str) -> list[str]:
    """Inline feature lists usually omit the page frame; add it unless excluded."""
    if not re.search(r"\bsections?\s*:\s*\S", prompt, re.I):
        return sections
    if re.search(r"\b(?:only|exactly|strictly)\s+(?:these\s+)?sections\b", prompt, re.I):
        return sections
    result = list(sections)
    has_header = any(re.search(r"header|masthead|navbar|navigation|^nav$|^top-bar$", item) for item in result)
    has_hero = any(re.search(r"hero|banner|cover-story|featured-paper", item) for item in result)
    if not has_header and not re.search(r"\b(?:no|without)\s+(?:header|navigation)\b", prompt, re.I):
        result.insert(0, "header")
    if business_type != "dashboard" and not has_hero and not re.search(r"\b(?:no|without)\s+hero\b", prompt, re.I):
        header_at = next((i for i, item in enumerate(result) if re.search(r"header|masthead|navbar|navigation|^nav$", item)), -1)
        result.insert(header_at + 1, "hero")
    if "footer" not in result and not re.search(r"\b(?:no|without)\s+footer\b", prompt, re.I):
        result.append("footer")
    return result


# Negation words that turn a following section keyword into an exclusion
# ("no contact form", "do not show pricing", "without testimonials").
_NEGATION_RE = re.compile(
    r"\b(?:no(?!-)|not|never|without|avoid|exclude|excluding|skip|omit|nor|cannot)\b|n't\b"
)
# Words that end a negation's scope inside the same clause.
_NEGATION_RESET_RE = re.compile(
    r"\b(?:but|however|instead|although|yet|except|featuring|including|include|includes|plus|also|while)\b"
)
# A keyword immediately qualified as unavailable is also an exclusion
# ("checkout-unavailable messaging", "booking is not available").
_POSTFIX_NEGATION_RE = re.compile(
    r"^[\s-]*(?:(?:is|are)\s+)?(?:unavailable|not available|disabled|not needed|not required|not offered)\b"
)

# Section slug -> pattern used both to request and to exclude that section.
_SECTION_KEYWORD_PATTERNS: dict[str, str] = {
    "about": r"\b(?:about us|about section|our story|our mission|manifesto)\b",
    "services": r"\bservices?\b",
    "products": r"\b(?:products?|catalog|shop the collection)\b",
    "collections": r"\bcollections?\b",
    "cart": r"\b(?:cart|basket|shopping bag)\b",
    "checkout": r"\bcheckout\b",
    "gallery": r"\bgallery\b",
    "projects": r"\b(?:projects?|case studies|portfolio work)\b",
    "articles": r"\b(?:articles?|blog posts?|journal entries)\b",
    "archives": r"\barchives?\b",
    "contributors": r"\b(?:contributors?|author directory)\b",
    "schedule": r"\b(?:schedule|agenda|itinerary)\b",
    "events": r"\b(?:events?|calendar|meetups?)\b",
    "speakers": r"\b(?:speakers?|presenters?|performers?)\b",
    "tickets": r"\b(?:tickets?|registration passes)\b",
    "faq": r"\b(?:faq|frequently asked questions)\b",
    "booking": r"\b(?:booking|bookings|reservations?|appointments?)\b",
    "newsletter": r"\bnewsletter\b",
    "team": r"\b(?:team|staff|people)\b",
    "location": r"\b(?:location|directions|opening hours)\b",
    "membership": r"\b(?:memberships?|join the club|become a member)\b",
    "contact": r"\b(?:contact|inquir(?:y|ies)|enquir(?:y|ies))\b",
    "pricing": r"\b(?:pricing|prices?|price list|calculator|tiers?|subscriptions?|billing|plans)\b",
    "testimonials": r"\b(?:testimonials?|reviews?|customer stories)\b",
    "architecture": r"\b(?:workflow |system |technical )?architecture(?: diagram| section)?\b",
    "menu": r"\bmenus?\b",
    "donate": r"\b(?:donate|donation|donations|fundrais\w*)\b",
    "features": r"\bfeatures?\b",
}

# Words that mark a "with A, B and C" item as styling or behaviour, not a section.
_NON_SECTION_ITEM_WORDS = {
    "color", "colors", "colour", "colours", "palette", "font", "fonts", "type", "typography",
    "serif", "sans", "motion", "animation", "animations", "animated", "transition", "transitions",
    "hover", "parallax", "reveal", "reveals", "scroll", "scrolling", "effect", "effects", "texture",
    "textures", "gradient", "gradients", "shadow", "shadows", "layout", "spacing", "whitespace",
    "accessible", "accessibility", "responsive", "mobile", "mode", "theme", "tone", "vibe", "feel",
    "style", "styling", "aesthetic", "imagery", "image", "images", "photo", "photos", "photography",
    "illustration", "illustrations", "icon", "icons", "contrast", "filter", "filters", "filtering",
    "search", "sort", "sorting", "toggle", "toggles", "button", "buttons", "link", "links", "state",
    "interaction", "interactions", "keyboard", "focus", "dark", "light", "warm", "cool", "minimal",
    "bold", "clean", "modern", "premium", "elegant", "accent", "accents", "background", "backgrounds",
    "border", "borders", "radius", "corners", "copy", "react", "typescript", "css", "tailwind",
    "messaging", "message", "messages", "data", "facts",
    "look", "looks", "technical", "space", "white", "lots", "colourful", "colorful", "playful",
    "luxurious", "cozy", "cosy",
}
_LEADING_DETERMINERS_RE = re.compile(r"^(?:a|an|the|our|their|its|his|her|some|short|simple|dedicated)\s+", re.I)


def _is_negated(text: str, start: int, end: int) -> bool:
    """True when the keyword at text[start:end] is excluded by nearby negation."""
    clause_start = max(text.rfind(ch, 0, start) for ch in ".;!?\n") + 1
    window = text[max(clause_start, start - 60):start]
    negations = list(_NEGATION_RE.finditer(window))
    if negations and not _NEGATION_RESET_RE.search(window[negations[-1].end():]):
        return True
    return bool(_POSTFIX_NEGATION_RE.match(text[end:end + 40]))


def _first_positive_mention(text: str, pattern: str) -> Optional[int]:
    """Position of the first non-negated match of pattern, or None."""
    for match in re.finditer(pattern, text):
        if not _is_negated(text, match.start(), match.end()):
            return match.start()
    return None


def _mentions(text: str, pattern: str) -> bool:
    return _first_positive_mention(text, pattern) is not None


def _explicitly_excluded(text: str, pattern: str) -> bool:
    """The prompt mentions the keyword, and every mention is negated."""
    matches = list(re.finditer(pattern, text))
    return bool(matches) and all(_is_negated(text, m.start(), m.end()) for m in matches)


def _slugify_section(label: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s_-]+", "", label.lower()).strip()
    slug = re.sub(r"[\s_]+", "-", cleaned).strip("-")
    if slug and slug[0].isdigit():
        slug = f"sec-{slug}"
    return slug


def extract_implicit_feature_sections(prompt: str) -> list[str]:
    """Sections named in prose lists, e.g. "a storefront with glaze stories,
    product detail, care guide and studio notes".

    Lists that describe styling or behaviour ("with warm colours, serif type
    and subtle motion") are ignored. Items naming a known section map to its
    canonical slug so "transparent pricing" does not duplicate "pricing".
    """
    lower = prompt.lower()
    found: list[str] = []

    def _add(raw_items: list[str]) -> None:
        kept = _filter_section_list_items(raw_items)
        if len(kept) >= 2 and len(kept) * 2 >= len(raw_items):
            for slug in kept:
                if slug not in found:
                    found.append(slug)

    for intro in re.finditer(r"\b(?:with|featuring|including|includes?:?|covering)\s+([^.;:\n]+)", lower):
        body = intro.group(1)
        if "," not in body and " and " not in body:
            continue
        raw_items = [item.strip() for item in re.split(r",\s*(?:and\s+|or\s+)?|\s+and\s+|\s+&\s+", body) if item.strip()]
        if len(raw_items) >= 2:
            _add(raw_items)

    # Bare list sentences: "Menu, about the chef, private dining."
    for sentence in re.split(r"[.;\n]", lower):
        sentence = sentence.strip()
        if not sentence or ":" in sentence:
            continue
        commas = sentence.count(",")
        if not (commas >= 2 or (commas >= 1 and re.search(r"\band\b", sentence))):
            continue
        raw_items = [item.strip() for item in re.split(r",\s*(?:and\s+|or\s+)?|\s+and\s+|\s+&\s+", sentence) if item.strip()]
        if len(raw_items) < 2 or any(len(item.split()) > 4 for item in raw_items):
            continue
        _add(raw_items)
    return found


def _filter_section_list_items(raw_items: list[str]) -> list[str]:
    """Map prose list items to section slugs, dropping style/behaviour words."""
    kept: list[str] = []
    for item in raw_items:
        # "a pricing section with a toggle" -> "pricing section"; drop "(6 cards)".
        item = re.split(r"\s+(?:with|for|that|which|where|showing|using)\s+", item)[0]
        item = re.sub(r"\([^)]*\)", "", item)
        item = _LEADING_DETERMINERS_RE.sub("", item).strip()
        item = re.sub(r"^(?:sticky|fixed|full-width|large|small)\s+", "", item)
        if re.fullmatch(r"(?:nav|navbar|navigation|header|hero|footer|cta|call to action)(?: section| bar| banner)?", item):
            continue  # page frame / inline control, planned separately
        words = item.split()
        if not words or len(words) > 4:
            continue
        if words[0] == "about":
            kept.append("about")
            continue
        # "transparent pricing" / "contact form" are the canonical section;
        # "product detail" names a different section than "products".
        canonical = next((slug for slug, pattern in _SECTION_KEYWORD_PATTERNS.items()
                          if (m := re.search(pattern, item)) and item[m.end():].strip()
                          in {"", "form", "section", "page", "area", "block", "list", "grid", "table"}), None)
        if canonical:
            kept.append(canonical)
            continue
        if any(word.strip("-") in _NON_SECTION_ITEM_WORDS for word in re.split(r"[\s-]+", item)):
            continue
        if words[0] in {"add", "filter", "toggle", "switch", "show", "use", "make", "keep", "click", "open", "build", "create"}:
            continue
        slug = _slugify_section(item)
        if slug:
            kept.append(slug)
    return kept


_SYNONYM_SECTION_GROUPS = (
    ("programs", "classes", "courses", "services"),
    ("pricing", "membership", "plans", "packages"),
)


def _section_word_requested(lower: str, slug: str, group: tuple[str, ...]) -> bool:
    """The slug's word appears in the prompt as a head noun, not only as a
    modifier of another group member ("membership pricing" requests pricing)."""
    stem = slug.rstrip("s")
    others = "|".join(re.escape(o.rstrip("s")) for o in group if o != slug)
    for m in re.finditer(rf"\b{re.escape(stem)}s?\b", lower):
        if _is_negated(lower, m.start(), m.end()):
            continue
        if not re.match(rf"\s+(?:{others})s?\b", lower[m.end():]):
            return True
    return False


def _merge_synonym_sections(middle: list[str], lower: str) -> list[str]:
    """Collapse duplicated synonyms (programs/classes, pricing/membership):
    keep members the prompt names, drop domain defaults that duplicate them."""
    result = list(middle)
    for group in _SYNONYM_SECTION_GROUPS:
        present = [sec for sec in result if sec in group]
        if len(present) < 2:
            continue
        requested = [sec for sec in present if _section_word_requested(lower, sec, group)]
        keep = requested or present[:1]
        # The kept member takes the slot of the first (default) member it replaces.
        slot = result.index(present[0])
        result = [sec for sec in result if sec not in group]
        result[slot:slot] = keep
    return result


def extract_sections_from_prompt(prompt: str, business_type: str) -> list[str]:
    """
    Dynamically infers the required sections from the user prompt and business domain.
    Explicit user-authored section structure always overrides domain-template heuristics.
    Keywords are matched on word boundaries; negated mentions ("no contact form",
    "do not show pricing", "checkout-unavailable") never add a section and remove
    domain defaults. Sections named in prose lists are kept.
    """
    explicit = extract_explicit_sections(prompt)
    if explicit:
        return _complete_inline_site_frame(prompt, [slug for slug, _ in explicit], business_type)

    lower = prompt.lower()

    wants_pricing = _mentions(lower, _SECTION_KEYWORD_PATTERNS["pricing"])
    wants_testimonials = _mentions(lower, _SECTION_KEYWORD_PATTERNS["testimonials"])
    wants_architecture = _mentions(lower, _SECTION_KEYWORD_PATTERNS["architecture"])
    wants_features = _mentions(lower, r"\b(?:features?|showcase|services?|capabilit(?:y|ies)|solutions?)\b")
    wants_contact = _mentions(lower, r"\b(?:contact|reach (?:us|out)|hire|inquir(?:y|ies)|enquir(?:y|ies))\b")
    wants_cta = _mentions(lower, r"\b(?:cta|sign ?up|get started|newsletter|donate)\b")

    middle: list[str] = []

    if business_type == "saas":
        middle.append("features")
        if wants_architecture:
            middle.append("architecture")
        if wants_pricing and not any(k in lower for k in ["free only", "no pricing"]):
            middle.append("pricing")
        if wants_testimonials:
            middle.append("testimonials")
        if wants_contact:
            middle.append("contact")
        elif re.search(r"\b(?:cta|call to action|signup)\s+section\b", lower):
            middle.append("cta")

    elif business_type == "restaurant":
        middle.append("menu")
        middle.append("about")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "portfolio":
        middle.append("gallery" if re.search(r"\b(?:artist|photograph\w*|gallery|artwork|illustrat\w*)\b", lower) else "projects")
        if re.search(r"\b(?:skills|tech stack|technologies|toolkit)\b", lower):
            middle.append("skills")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "ecommerce":
        middle.append("products")
        middle.append("cart")
        if re.search(r"\bcheckout\b", lower): middle.append("checkout")
        if wants_testimonials: middle.append("testimonials")

    elif business_type == "fintech":
        middle.append("features")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "healthcare":
        middle.append("services")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "realestate":
        middle.append("properties")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "education":
        middle.append("courses")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "nonprofit":
        middle.append("mission")
        middle.append("impact")
        if wants_testimonials: middle.append("testimonials")
        if re.search(r"\b(?:donate|donation|fundrais)\w*\b", lower): middle.append("donate")
        middle.append("contact")

    elif business_type == "agency":
        middle.append("services")
        middle.append("projects")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "architecture":
        middle.append("projects")
        middle.append("services")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "coffee":
        middle.append("products")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "fitness":
        middle.append("programs")
        if wants_pricing: middle.append("pricing")
        if wants_testimonials: middle.append("testimonials")
        middle.append("contact")

    elif business_type == "blog":
        middle.append("articles")
        if re.search(r"\b(newsletter|subscribe|subscription)\b", lower): middle.append("newsletter")

    elif business_type == "editorial":
        middle.append("articles")
        if re.search(r"\b(?:issue|archive)\b", lower): middle.append("archives")
        if re.search(r"\b(?:authors?|contributors?)\b", lower): middle.append("contributors")

    elif business_type == "dashboard":
        middle.append("dashboard")

    elif business_type == "event":
        middle.append("schedule")
        if re.search(r"\b(speakers?|presenters?|performers?|artists?)\b", lower): middle.append("speakers")
        middle.append("tickets")

    else:
        middle = []

    requested_sections = (
        "about", "services", "products", "collections", "cart", "checkout", "gallery",
        "projects", "articles", "archives", "contributors", "schedule", "events", "speakers",
        "tickets", "faq", "booking", "newsletter", "team", "location", "membership", "contact",
    )
    requested = sorted(
        (position, section)
        for section in requested_sections
        if (position := _first_positive_mention(lower, _SECTION_KEYWORD_PATTERNS[section])) is not None
    )
    for _, section in requested:
        if section in {"products", "collections", "cart", "checkout"} and business_type not in {"ecommerce", "coffee"}:
            if not re.search(r"\b(?:shop|store|sell|catalog)\b", lower):
                continue
        if section == "tickets" and business_type != "event" and not re.search(r"\b(?:concert|festival|conference)\b", lower):
            continue
        if section == "projects" and business_type in {"saas", "fintech", "healthcare", "education"}:
            if not re.search(r"\b(?:project gallery|case studies|portfolio)\b", lower):
                continue
        if section not in middle:
            middle.append(section)
    for section in extract_implicit_feature_sections(prompt):
        if section not in middle:
            middle.append(section)

    # Domain defaults never override an explicit "no X" / "X unavailable".
    middle = [sec for sec in middle
              if not (sec in _SECTION_KEYWORD_PATTERNS and _explicitly_excluded(lower, _SECTION_KEYWORD_PATTERNS[sec]))]
    middle = _merge_synonym_sections(middle, lower)
    # Contact closes the page; sections the prompt lists after a domain default stay ahead of it.
    if "contact" in middle:
        middle = [sec for sec in middle if sec != "contact"] + ["contact"]
    if not middle:
        middle = [sec for sec in ("about", "contact")
                  if not _explicitly_excluded(lower, _SECTION_KEYWORD_PATTERNS[sec])] or ["about"]

    assembled = ["header"]
    if business_type != "dashboard" and not _explicitly_excluded(lower, r"hero(?: section| banner)?"):
        assembled.append("hero")
    seen = set(assembled)
    for sec in middle:
        if sec not in seen:
            seen.add(sec)
            assembled.append(sec)
    if not _explicitly_excluded(lower, r"footer"):
        assembled.append("footer")
    return assembled


def extract_projects_from_prompt(prompt: str) -> list[dict]:
    """Extracts project details, titles, URLs, and descriptions from prompt."""
    projects = []
    marker_iter = list(re.finditer(r'(?:^|\n|\s)(?:(?:\d+[\.\)]|\(\d+\)))\s*', prompt))
    if not marker_iter:
        return projects

    url_re = re.compile(r'https?://[^\s",\'\)\]]+')

    for i, m in enumerate(marker_iter):
        start_pos = m.end()
        end_pos = marker_iter[i + 1].start() if i + 1 < len(marker_iter) else len(prompt)
        raw_text = prompt[start_pos:end_pos].strip()

        url = ""
        url_m = url_re.search(raw_text)
        if url_m:
            url = url_m.group(0).rstrip(".,;'\"")

        title = ""
        q_m = re.match(r'^["\']([^"\']+)["\']', raw_text)
        if q_m:
            inner = q_m.group(1).strip()
            inner = url_re.sub('', inner).strip().rstrip(':-–— ')
            title = inner.split('\n')[0].strip()

        if not title:
            first_line = raw_text.split('\n')[0].strip().strip('"\'')
            first_line = url_re.sub('', first_line).strip().rstrip(':-–— ')
            title = first_line[:50].strip()

        title = title.strip('"\' -–—:')

        desc_text = raw_text.strip('"\'')
        desc_clean = desc_text
        if title:
            desc_clean = re.sub(r'^["\']?' + re.escape(title) + r'["\']?', '', desc_clean, flags=re.IGNORECASE).strip()
        if url:
            desc_clean = desc_clean.replace(url, '')
        desc_clean = desc_clean.strip(':-–— \t\r\n",\'')
        desc_clean = re.sub(r'(?:,\s*)?(?:add\s+)?(?:scrolling animations?|text reveal|scroll reveal|animations?).*$', '', desc_clean, flags=re.IGNORECASE).strip()
        desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()

        tech_tags = []
        for kw in ["React", "TypeScript", "JavaScript", "Python", "FastAPI", "Gemini", "OCR", "EPUB", "NLP", "Machine Learning", "ML", "Node.js", "Render", "Vercel", "WebSockets"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', raw_text, re.IGNORECASE):
                tech_tags.append(kw)

        if title:
            projects.append({
                "name": title,
                "url": url,
                "description": desc_clean,
                "tech": tech_tags or ["React", "TypeScript", "Web"],
            })

    return projects


def parse_section_spec(section: str, prompt: str) -> dict:
    """Extract explicit section items and counts without turning layout counts into copy."""
    match = re.search(rf"\b{re.escape(section)}\b(?:\s+\w+){{0,2}}\s*\(([^)]*)\)", prompt, re.I)
    raw = match.group(1).strip() if match else ""
    count = re.search(r"\b(\d+)\s+(?:cards?|items?|tiers?)\b", raw, re.I)
    items = [] if count else [part.strip() for part in raw.split(",") if part.strip()]
    if not match:
        # "Projects: Fern Studio rebrand, Halo app identity and Ostra packaging."
        label = r"[\s-]+".join(re.escape(word) for word in re.split(r"[-_]+", section) if word)
        colon = re.search(rf"\b{label}\s*:\s*([^\n.;]+)", prompt, re.I) if label else None
        if colon:
            parts = [part.strip() for part in re.split(r",\s*(?:and\s+)?|\s+and\s+", colon.group(1)) if part.strip()]
            if 2 <= len(parts) <= 12 and all(len(part.split()) <= 6 for part in parts):
                items = parts
    return {"parsed_items": items, "target_count": int(count.group(1)) if count else (len(items) or None)}


# ── P2-01: Layout Archetype Planner ─────────────────────────────────────────
# The previous implementation did: `detect_prompt_layout_signal(prompt) or "grid"`
# This means any prompt without an explicit "layout: X" keyword defaulted to grid,
# producing homogeneous 3-column card matrices across unrelated businesses.
#
# The planner below follows a 3-tier priority:
#   Tier 1 — explicit syntax wins (layout:editorial, layout:bento, etc.)
#   Tier 2 — domain-semantic inference from prompt vocabulary + business type
#   Tier 3 — entropy seeding from business name, distributing across non-grid archetypes
#
# Grid is now intentional (explicit product grids, dashboards) — never silent default.

class LayoutArchetype(str, Enum):
    EDITORIAL = "editorial"
    BENTO = "bento"
    SPLIT_HERO = "split_hero"
    MAGAZINE = "magazine"
    TIMELINE = "timeline"
    TABS = "tabs"
    ASYMMETRIC = "asymmetric"
    GRID = "grid"


_LAYOUT_ARCHETYPES = [
    "editorial",    # bold asymmetric type-led sections, large headline blocks
    "bento",        # mosaic of variable-size info tiles, dashboard-like
    "split_hero",   # side-by-side hero with strong CTA, alternating content blocks
    "magazine",     # editorial grid with hero + article cluster + sidebar flow
    "timeline",     # chronological vertical story, history/roadmap/process
    "tabs",         # tabbed or accordion primary navigation for dense feature sets
    "asymmetric",   # off-centre typographic composition, creative/portfolio
    "grid",         # uniform product/portfolio card grid (intentional only)
]

_LAYOUT_ARCHETYPE_GUIDELINES: dict[str, str] = {
    "editorial": "Type-led composition with oversized display headers, generous whitespace, pulled quotes, and article narrative blocks.",
    "bento": "Mosaic grid with variable-span tiles (2x1, 1x2, 2x2), card grouping with distinct visual hierarchy, metric badges, and interactive tiles.",
    "split_hero": "Asymmetric 50/50 or 60/40 two-column hero with prominent headline + CTA on one side and showcase visual on the other.",
    "magazine": "Editorial publication layout with dominant featured story, secondary card clusters, and curated sidebar column.",
    "timeline": "Vertical sequential chronological narrative spine with milestone markers, date chips, and connecting lines.",
    "tabs": "Tabbed/segmented navigation switching between content panels with clear active states and accessible aria-selected bindings.",
    "asymmetric": "Off-center expressive typography, overlapping visual elements, creative editorial rhythm, and dynamic negative space.",
    "grid": "Clean uniform card/portfolio grid structure with consistent aspect ratio, responsive columns (1-col mobile, 2-3 col desktop).",
}

_MOTION_VOCABULARY: dict[str, dict[str, str]] = {
    "editorial": {
        "guidelines": "Restrained quiet fade-only prose reveal (0.6s ease-out), no aggressive bounce or scale transforms, high typographic dignity, with @media (prefers-reduced-motion: reduce) instant opacity.",
        "reduced_motion": "instant opacity, no transforms",
        "primary_pattern": "fade_prose_reveal",
    },
    "bento": {
        "guidelines": "Span-weighted tile entrance stagger (50ms offset), subtle hover lift (translateY -4px) and accent border-glow, with @media (prefers-reduced-motion: reduce) fallback.",
        "reduced_motion": "instant display, static borders",
        "primary_pattern": "staggered_tile_entrance",
    },
    "split_hero": {
        "guidelines": "Coordinated asymmetric entrance with 150ms offset delay between dominant headline copy and media visual, with @media (prefers-reduced-motion: reduce) fallback.",
        "reduced_motion": "simultaneous instant appearance",
        "primary_pattern": "asymmetric_hero_entrance",
    },
    "magazine": {
        "guidelines": "Editorial article cluster entrance with lead story emphasis, subtle column stagger, and hover elevation on cards, with prefers-reduced-motion fallback.",
        "reduced_motion": "instant static cards",
        "primary_pattern": "cluster_stagger",
    },
    "timeline": {
        "guidelines": "Sequential chronological milestone reveal on scroll, staggered node markers, and progressive connecting spine draw-in, with prefers-reduced-motion fallback.",
        "reduced_motion": "fully drawn spine, visible milestones",
        "primary_pattern": "timeline_draw_and_node_reveal",
    },
    "tabs": {
        "guidelines": "Tab panel state crossfade/slide settling transition with active indicator slide pill and instant opacity response, with prefers-reduced-motion fallback.",
        "reduced_motion": "instant tab switch, no slide",
        "primary_pattern": "tab_crossfade_settle",
    },
    "asymmetric": {
        "guidelines": "Layered typographic offset entry with dynamic depth, subtle floating parallax accents, and staggered compositional reveal, with prefers-reduced-motion fallback.",
        "reduced_motion": "flat static layout",
        "primary_pattern": "offset_typographic_entry",
    },
    "grid": {
        "guidelines": "Scroll-staggered card reveal (via IntersectionObserver or staggered index delay) with subtle hover lift and smooth transition, with @media (prefers-reduced-motion: reduce) fallback.",
        "reduced_motion": "instant card visibility, no hover transform",
        "primary_pattern": "grid_scroll_stagger_and_hover_lift",
    },
}

# Domain → default archetype when no explicit keyword is found.
# These are informed by how professional agencies design for each sector.
_DOMAIN_DEFAULT_ARCHETYPE: dict[str, str] = {
    "portfolio":      "asymmetric",  # creative, unexpected compositions
    "agency":         "asymmetric",  # bold typographic identity
    "architecture":   "editorial",   # monolithic type-led presentation
    "blog":           "editorial",   # longform reading-optimised flow
    "restaurant":     "magazine",    # food-photography-heavy story layout
    "coffee":         "magazine",    # artisanal editorial feel
    "ecommerce":      "magazine",    # editorial product story (not a grid!)
    "fitness":        "split_hero",  # high-energy side-by-side impact
    "event":          "split_hero",  # countdown + programme split
    "saas":           "bento",       # dashboard-native information density
    "fintech":        "bento",       # data-rich tile layout
    "education":      "tabs",        # curriculum navigation, course tabs
    "healthcare":     "tabs",        # service/treatment navigation
    "nonprofit":      "timeline",    # impact journey / mission story
    "realestate":     "split_hero",  # property image + details split
}

# Prompt vocabulary → explicit archetype signals (beyond the layout: syntax)
_LAYOUT_KEYWORD_SIGNALS: list[tuple[str, str]] = [
    # editorial
    (r"\b(editorial|longform|essay|manifesto|type.led|typographic|narrative|story.?tell)\b", "editorial"),
    (r"\b(magazine.style|publication|journal.layout|editorial.grid)\b", "magazine"),
    # bento
    (r"\b(bento|mosaic|dashboard.?layout|tile.?grid|info.?tiles?|metric.?cards?)\b", "bento"),
    # split hero
    (r"\b(split.hero|half.?and.?half|side.by.side|hero.split|two.?column.?hero)\b", "split_hero"),
    # timeline
    (r"\b(timeline|roadmap|milestones?|chronolog|history|process.?steps?|journey)\b", "timeline"),
    # tabs
    (r"\b(tabs?|tabbed|accordion|feature.?tabs?|service.?tabs?|product.?tabs?)\b", "tabs"),
    # asymmetric
    (r"\b(asymmetric|off.?centre|collage|overlap|layered.?text|poster.?style)\b", "asymmetric"),
    # grid (intentional)
    (r"\b(product.?grid|card.?grid|team.?grid|gallery.?grid|masonry)\b", "grid"),
]

# Business-name entropy slots: after domain default is applied, the remaining
# entropy distributes across these non-grid archetypes to increase variety.
_ENTROPY_POOL: list[str] = [
    "editorial", "bento", "split_hero", "magazine", "asymmetric",
    "editorial", "split_hero", "magazine",  # weighted toward cinematic/editorial
]


def detect_prompt_layout_signal(prompt: str) -> Optional[str]:
    """Tier-1: Return archetype if the user supplied an explicit layout declaration.

    Recognizes both the formal 'layout: X' syntax and strong keyword signals
    (editorial website, bento dashboard, etc.).
    """
    # Formal syntax: layout: editorial / layout archetype: bento / etc.
    formal = re.search(
        r"\blayout(?:\s+archetype)?\s*:\s*(editorial|bento|split[_ -]?hero|magazine|grid|timeline|tabs|asymmetric)\b",
        prompt, re.I,
    )
    if formal:
        return formal.group(1).lower().replace(" ", "_").replace("-", "_")

    # Strong opening signal: "editorial website / magazine layout / ..."
    if re.search(r"^\s*(editorial|magazine)\s+(?:website|landing|page|layout)\b", prompt, re.I):
        return "editorial"
    if re.search(r"^\s*bento\s+(?:layout|grid|style)\b", prompt, re.I):
        return "bento"

    # Vocabulary keyword signals
    for pattern, archetype in _LAYOUT_KEYWORD_SIGNALS:
        if re.search(pattern, prompt, re.I):
            return archetype

    return None


def plan_layout_archetype(prompt: str, business_type: str = "", business_name: str = "") -> str:
    """Plan a compositionally appropriate layout archetype for any prompt.

    Priority
    --------
    1. Explicit syntax / strong keyword from detect_prompt_layout_signal()
    2. Domain-semantic inference: business_type → _DOMAIN_DEFAULT_ARCHETYPE
    3. Entropy fallback: hash of business_name → _ENTROPY_POOL
       (distributes across editorial/bento/split_hero/magazine/asymmetric;
       never silently returns "grid")
    """
    # Tier 1: explicit
    explicit = detect_prompt_layout_signal(prompt)
    if explicit:
        return explicit

    # Tier 2: domain-semantic
    domain = (business_type or "").strip().lower()
    if domain in _DOMAIN_DEFAULT_ARCHETYPE:
        return _DOMAIN_DEFAULT_ARCHETYPE[domain]

    # Tier 3: entropy seeding — never "grid"
    import hashlib
    seed_text = (business_name or prompt[:80]).strip().lower()
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:8], 16)
    return _ENTROPY_POOL[seed % len(_ENTROPY_POOL)]


def select_layout_archetype(prompt: str, business_name: str = "", business_type: str = "") -> str:
    """Public API wrapper (backward-compatible signature).

    Previously: `detect_prompt_layout_signal(prompt) or "grid"`  ← always grid
    Now: delegates to plan_layout_archetype() which plans, not just extracts.
    """
    return plan_layout_archetype(prompt, business_type=business_type, business_name=business_name)


_NAMED_PALETTE_COLORS = {
    "warm cream": "#f6f1e7", "warm ivory": "#f6f1e7", "cream": "#fffaf0", "ivory": "#fffff0", "ink": "#1c1917",
    "forest green": "#203b2b", "sage green": "#9caf88", "sage": "#9caf88",
    "charcoal": "#263238", "navy": "#14213d", "terracotta": "#b5654b",
    "burgundy": "#6b2138", "espresso": "#3b2a23", "cobalt": "#2454a6",
    "lavender": "#b6a6cf", "black": "#111111", "white": "#ffffff",
}


def extract_prompt_palette(prompt: str) -> dict[str, str]:
    """Extract explicit named or hex palette colors without using domain defaults."""
    lower = prompt.lower()
    matches: list[tuple[int, str, str]] = []
    occupied: list[tuple[int, int]] = []
    for phrase, color in sorted(_NAMED_PALETTE_COLORS.items(), key=lambda entry: -len(entry[0])):
        for match in re.finditer(r"\b" + re.escape(phrase) + r"\b", lower):
            sentence_start = max(lower.rfind(".", 0, match.start()), lower.rfind("\n", 0, match.start())) + 1
            if not re.search(r"\b(?:use|with|palette|colors?|tones?|theme|background|accent|style|dark|light)\b", lower[sentence_start:match.start()]):
                continue
            if any(match.start() < end and start < match.end() for start, end in occupied):
                continue
            occupied.append(match.span())
            matches.append((match.start(), phrase, color))
    for match in re.finditer(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", prompt):
        matches.append((match.start(), match.group(0), match.group(0)))
    matches.sort()
    if not matches:
        return {}
    light_names = {"warm cream", "warm ivory", "cream", "ivory", "white"}
    result = {"requested_palette": ", ".join(name for _, name, _ in matches)}
    light = next((color for _, name, color in matches if name in light_names), None)
    dark = next((color for _, name, color in matches if name not in light_names), None)
    if light:
        result["background_color"] = light
    if dark:
        result["primary_color"] = dark
        result["accent_color"] = matches[-1][2] if len(matches) > 2 else dark
    elif light:
        result["primary_color"] = light
    return result


def extract_supplied_products(prompt: str) -> list[dict[str, str]]:
    """Read products with explicit prices from a user-authored catalog clause."""
    # A decimal point in a price is not the end of the catalog sentence.
    catalogs = re.finditer(r"\b(?:products|catalog|items)\s*:\s*(.+?)(?=\.(?!\d)|\n|$)", prompt, re.I)
    products: list[dict[str, str]] = []
    for catalog in catalogs:
        for part in re.split(r",\s*(?:and\s+)?|;\s*|\s+and\s+", catalog.group(1)):
            item = re.sub(r"^and\s+", "", part.strip(), flags=re.I)
            match = re.fullmatch(r"([^\d\W][\w '&-]{0,80}?)\s*(?:(?:at|for)\s+|[-–—:]\s*)?([$€£₹]\s*\d+(?:,\d{3})*(?:\.\d{1,2})?)", item, re.I)
            if match:
                product = {"name": match.group(1).strip(), "price": match.group(2).strip()}
                if product not in products:
                    products.append(product)
    return products


def _build_heuristic_brief(prompt: str, style_spec: Optional[StyleSpec] = None) -> dict:
    """Builds a rich, domain-tailored structured content brief using the unified domain registry and optional StyleSpec."""
    explicit_sections = extract_explicit_sections(prompt)
    if explicit_sections:
        business_type = detect_business_type(prompt)
        dynamic_sections = _complete_inline_site_frame(prompt, [slug for slug, _ in explicit_sections], business_type)
        explicit_instructions = {}
        for slug, desc in explicit_sections:
            words = [w for w in re.split(r'[-_]', slug) if w]
            pascal_name = "".join(w.capitalize() for w in words)
            raw_name = " ".join(w.capitalize() for w in words)
            full_desc = desc if desc else f"High-quality, responsive {raw_name} section."
            if "Files:" not in full_desc:
                full_desc = f"{full_desc} Files: src/components/{pascal_name}.tsx + src/components/{pascal_name}.css"
            explicit_instructions[slug] = full_desc
            explicit_instructions[slug.replace("-", "_")] = full_desc
            explicit_instructions[slug.replace("_", "-")] = full_desc
    else:
        business_type = detect_business_type(prompt)
        dynamic_sections = extract_sections_from_prompt(prompt, business_type)
        explicit_instructions = {}

    business_name = extract_business_name(prompt)
    # Registry examples illustrate layouts; they are not facts about this user.
    # Passing sample products, prices, projects or endorsements into the model
    # causes it to publish invented business content across unrelated sites.
    template = {
        "business_type": business_type,
        "features": [], "pricing_tiers": [], "projects": [], "skills": [],
        "menu_categories": [], "testimonials": [], "contact": {}, "products": [],
    }
    theme = get_domain_theme(business_type, business_name)

    lower_prompt = prompt.lower()
    if style_spec:
        primary_color = style_spec.get_primary_color()
    elif _mentions(lower_prompt, r"\b(?:dark|black|night|obsidian)\b"):
        primary_color = theme.get("primary_color_dark", theme["primary_color"])
    elif _mentions(lower_prompt, r"\b(?:light|paper|white|bright|clean|minimal)\b"):
        primary_color = theme.get("primary_color_light", theme["primary_color"])
    else:
        primary_color = theme["primary_color"]

    accent_color = style_spec.get_accent_color() if style_spec else theme["accent_color"]
    font_heading = style_spec.get_heading_font() if style_spec else theme["font_heading"]
    font_body = style_spec.get_body_font() if style_spec else theme["font_body"]

    # Extract motion requirements decoupled from section parsing
    motion_plan = extract_motion_requirements(prompt, available_sections=dynamic_sections)
    if not motion_plan:
        default_feature_sec = "features" if "features" in dynamic_sections else ("projects" if "projects" in dynamic_sections else (dynamic_sections[1] if len(dynamic_sections) > 1 else dynamic_sections[0]))
        motion_plan = []
        if "hero" in dynamic_sections:
            motion_plan.append(MotionSpec(type=MotionType.TEXT_REVEAL, target_section="hero", intensity="subtle"))
        if default_feature_sec not in {"header", "footer"}:
            motion_plan.append(MotionSpec(type=MotionType.SCROLL_REVEAL, target_section=default_feature_sec, intensity="subtle"))

    res = {
        **template,
        "business_name": business_name,
        "business_type": business_type,
        "sections": dynamic_sections,
        "custom_section_instructions": explicit_instructions,
        "tagline": business_name,
        "primary_color": primary_color,
        "primary_color_light": theme.get("primary_color_light", "#ffffff"),
        "primary_color_dark": theme.get("primary_color_dark", "#0b0f19"),
        "accent_color": accent_color,
        "accent_secondary": theme.get("accent_secondary", "#6366f1"),
        "font_heading": font_heading,
        "font_body": font_body,
        "border_radius": theme.get("border_radius", "6px"),
        "motion_plan": motion_plan,
        "layout_archetype": select_layout_archetype(prompt, business_name=business_name, business_type=business_type),
        "section_plans": {
            section: {
                **parse_section_spec(section, prompt),
                "target_count": parse_section_spec(section, prompt)["target_count"] or (3 if section == "pricing" else None),
            }
            for section in dynamic_sections
        },
        "source": "heuristic",
        "source_prompt": prompt,
    }

    if not style_spec:
        res.update(extract_prompt_palette(prompt))
        if res.get("requested_palette"):
            res.pop("accent_secondary", None)
            if res.get("background_color"):
                res["primary_color_light"] = res["background_color"]
    res["products"] = extract_supplied_products(prompt)

    tagline_match = re.search(r"\btagline\s*:\s*([^\n.]+)", prompt, re.I)
    if tagline_match:
        res["tagline"] = tagline_match.group(1).strip().strip('"\'')
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", prompt)
    if email_match:
        res["contact"]["email"] = email_match.group(0)
    for section, plan in res["section_plans"].items():
        supplied = plan.get("parsed_items") or []
        count = plan.get("target_count")
        if not supplied and not count:
            continue
        details = []
        if supplied:
            details.append("Use these user-supplied items: " + ", ".join(supplied) + ".")
        if count:
            details.append(f"Render exactly {count} items.")
        details.append("Do not invent business facts or working links.")
        explicit_instructions.setdefault(section, f"Write the {section} section. " + " ".join(details))
    if re.search(r"\bInter\b", prompt):
        res["font_heading"] = res["font_body"] = "Inter"

    # If prompt provided real projects (e.g. portfolio with links and descriptions), inject them
    extracted_projects = extract_projects_from_prompt(prompt) if "projects" in dynamic_sections else []
    if extracted_projects:
        res["projects"] = extracted_projects
        proj_lines = []
        for p in extracted_projects:
            p_name = p.get("name", "")
            p_url = p.get("url", "")
            p_desc = p.get("description", "")
            p_tech = ", ".join(p.get("tech", []))
            proj_lines.append(f"- {p_name} ({p_url}): {p_desc} [Tech: {p_tech}]")
        proj_instruction = (
            "Write the Projects section showcasing the following real projects with clickable external links "
            "(target='_blank' rel='noopener noreferrer'), tech stack tags, live preview cards, and interactive filters.\n"
            "Projects:\n" + "\n".join(proj_lines) + "\n"
            "Files: src/components/Projects.tsx + src/components/Projects.css"
        )
        if "projects" in dynamic_sections:
            explicit_instructions["projects"] = proj_instruction
            explicit_instructions["Projects"] = proj_instruction

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
    "Support any website type. Use only facts supplied in the request. Never fabricate products, prices, projects, testimonials or contact details."
)


def _ground_provider_brief(prompt: str, provider_brief: dict, style_spec: Optional[StyleSpec]) -> dict:
    """Keep provider layout ideas while deriving business facts from the request."""
    grounded = _build_heuristic_brief(prompt, style_spec=style_spec)
    if not extract_explicit_sections(prompt):
        proposed = provider_brief.get("sections")
        if isinstance(proposed, list) and 2 <= len(proposed) <= 12:
            planned: list[str] = []
            prompt_words = set(re.findall(r"[a-z0-9]+", prompt.lower()))
            for item in proposed:
                if not isinstance(item, str) or len(item) > 40:
                    planned = []
                    break
                slug = re.sub(r"[^a-z0-9]+", "-", item.lower()).strip("-")
                if not slug or slug[0].isdigit():
                    planned = []
                    break
                if slug == "pricing" and not re.search(r"\b(?:pricing|prices?|tiers?|plans?|billing|subscription)\b", prompt, re.I):
                    continue
                if slug == "testimonials" and not re.search(r"\b(?:testimonials?|reviews?|quotes?)\b", prompt, re.I):
                    continue
                section_words = {word for word in slug.split("-") if len(word) > 3}
                if (slug not in {"header", "hero", "footer", "about", "contact"}
                        and slug not in grounded["sections"]
                        and not section_words.intersection(prompt_words)):
                    continue
                if slug not in planned:
                    planned.append(slug)
            if len(planned) >= 2:
                for section in grounded["sections"]:
                    if section not in planned:
                        insert_at = planned.index("footer") if "footer" in planned else len(planned)
                        planned.insert(insert_at, section)
                grounded["sections"] = planned
                grounded["section_plans"] = {section: parse_section_spec(section, prompt) for section in planned}
    for key in ("primary_color", "accent_color", "font_heading", "font_body"):
        value = provider_brief.get(key)
        if not style_spec and not (key in {"primary_color", "accent_color"} and grounded.get("requested_palette")) and isinstance(value, str) and value.strip():
            grounded[key] = value.strip()
    grounded["source"] = str(provider_brief.get("source", "provider")) + "+grounded"
    if re.search(r"\b(photo|photograph|photography|stock image|imagery|illustrations?)\b", prompt, re.I):
        grounded = resolve_site_images(grounded)
    return grounded


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
    from agent.site_requirements import build_requirement_manifest
    # 1. Resolve StyleSpec
    resolved_style: Optional[StyleSpec] = None
    if style_tokens and "--" in style_tokens:
        resolved_style = parse_css_tokens(style_tokens, name="Custom Ingested Tokens", source="refero" if "refero" in style_tokens.lower() else "custom")
    elif style_preset and str(style_preset).lower() != "auto":
        resolved_style = resolve_style_preset(style_preset) or PRESET_STYLES.get(style_preset)
    elif ":root" in prompt and "--" in prompt:
        resolved_style = parse_css_tokens(prompt, name="Prompt Embedded Tokens", source="prompt")
    elif not extract_prompt_palette(prompt):
        # Detect archetype keywords in prompt
        # A preset replaces the whole palette and type system, so only a request
        # for that *style* selects it. "warm editorial photography" or "luxury
        # ceramics" describe content, not the black/white/red editorial preset.
        low_prompt = prompt.lower()
        style_words = r"(?:style|styled|design|look|aesthetic|theme|preset|monochrome|layout|feel)"
        if _mentions(low_prompt, r"\b(?:refero|monopo)\b") or _mentions(low_prompt, rf"\beditorial[- ]{style_words}\b"):
            resolved_style = PRESET_STYLES.get("editorial") or PRESET_STYLES.get("refero_editorial")
        elif _mentions(low_prompt, r"\b(?:neo-?)?brutalis[mt]\b"):
            resolved_style = PRESET_STYLES.get("brutalist") or PRESET_STYLES.get("neo_brutalist")
        elif _mentions(low_prompt, r"\bglassmorph(?:ic|ism)\b"):
            resolved_style = PRESET_STYLES.get("experimental") or PRESET_STYLES.get("glassmorphic_aurora")
        elif _mentions(low_prompt, rf"\bluxury[- ](?:minimalist|minimal|{style_words})\b"):
            resolved_style = PRESET_STYLES.get("luxury") or PRESET_STYLES.get("luxury_minimalist")
        elif _mentions(low_prompt, r"\bcyberpunk\b"):
            resolved_style = PRESET_STYLES.get("cyberpunk_neon")

    # 2. Brief synthesis
    explicit_sections = extract_explicit_sections(prompt)

    if provider in ("auto", "gemini"):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            try:
                brief = _call_gemini_brief(prompt, api_key)
                if brief and "business_name" in brief:
                    brief["source"] = "gemini"
                    brief = _ground_provider_brief(prompt, brief, resolved_style)
                    if style_preset:
                        brief["style_preset"] = style_preset
                    brief["requirement_manifest"] = build_requirement_manifest(prompt, brief)
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
                    brief = _ground_provider_brief(prompt, brief, resolved_style)
                    if style_preset:
                        brief["style_preset"] = style_preset
                    brief["requirement_manifest"] = build_requirement_manifest(prompt, brief)
                    return brief
            except Exception as e:
                print(f"[site_brief] OpenAI API call failed, falling back: {e}")

    brief = _build_heuristic_brief(prompt, style_spec=resolved_style)
    if re.search(r"\b(photo|photograph|photography|stock image|imagery|illustrations?)\b", prompt, re.I):
        brief = resolve_site_images(brief)
    if style_preset:
        brief["style_preset"] = style_preset
    brief["requirement_manifest"] = build_requirement_manifest(prompt, brief)
    return brief


# ==============================================================================
# 5. XML Serialization for Agent Prompting
# ==============================================================================

def brief_to_xml(brief: dict) -> str:
    """Formats a structured brief into XML tags consumed by the site agent."""
    lines = ["<content_brief>"]
    lines.append("  <content_integrity>Use illustrative demo data only when labeled illustrative demo data; do not invent business facts, prices, testimonials, or contact details.</content_integrity>")
    if brief.get("style_preset"):
        lines.append(f"  <style_preset>{brief['style_preset']}</style_preset>")
    lines.append(f"  <business_name>{brief.get('business_name', 'My Business')}</business_name>")
    lines.append(f"  <business_type>{brief.get('business_type', 'general')}</business_type>")
    lines.append(f"  <tagline>{brief.get('tagline', '')}</tagline>")
    layout_id = str(brief.get("layout_archetype", "editorial"))
    layout_guideline = _LAYOUT_ARCHETYPE_GUIDELINES.get(layout_id, "")
    lines.append(f'  <layout_archetype id="{html.escape(layout_id, quote=True)}">')
    lines.append(f"    <guidelines>{html.escape(layout_guideline)}</guidelines>")
    lines.append("  </layout_archetype>")
    images = brief.get("images") or {}
    if images.get("hero"):
        hero_photo = images["hero"]
        lines.append(f"  <hero_image url={json.dumps(hero_photo['url'])} alt={json.dumps(hero_photo['alt'])} credit={json.dumps(hero_photo['credit'])} />")
    if images.get("items"):
        lines.append("  <section_images>")
        for photo in images["items"]:
            lines.append(f"    <image url={json.dumps(photo['url'])} alt={json.dumps(photo['alt'])} credit={json.dumps(photo['credit'])} />")
        lines.append("  </section_images>")
    if brief.get("media_expectation"):
        lines.append(f'  <media_expectation decision="{html.escape(str(brief.get("media_decision", "none")), quote=True)}">{html.escape(brief["media_expectation"])}</media_expectation>')

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
        if brief.get("background_color"):
            lines.append(f"    <background_color>{brief['background_color']}</background_color>")
        if brief.get("requested_palette"):
            lines.append(f"    <requested_palette>{html.escape(brief['requested_palette'])}</requested_palette>")
        if brief.get("accent_secondary"):
            lines.append(f"    <accent_secondary>{brief['accent_secondary']}</accent_secondary>")
        lines.append(f"    <font_heading>{brief.get('font_heading', 'Inter')}</font_heading>")
        lines.append(f"    <font_body>{brief.get('font_body', 'Inter')}</font_body>")
        lines.append("  </design_system>")

    lines.append("  <sections>")
    for sec in brief.get("sections", ["header", "hero", "about", "contact", "footer"]):
        lines.append(f"    <section>{sec}</section>")
    lines.append("  </sections>")
    manifest = brief.get("requirement_manifest") or {}
    if manifest:
        lines.append("  <requirement_manifest>")
        for fact in manifest.get("exact_facts", []):
            lines.append(f"    <exact_fact>{html.escape(str(fact))}</exact_fact>")
        for interaction in manifest.get("interactions", []):
            lines.append(f"    <required_interaction>{html.escape(str(interaction))}</required_interaction>")
        for contract in manifest.get("cross_section_contracts", []):
            lines.append(f"    <shared_state producer=\"{html.escape(contract['producer'], quote=True)}\" consumer=\"{html.escape(contract['consumer'], quote=True)}\">{html.escape(contract['state'])}</shared_state>")
        for requirement in manifest.get("three_d_constraints", []):
            lines.append(f'    <required_3d engine="{html.escape(requirement["engine"], quote=True)}">{html.escape(json.dumps(requirement, ensure_ascii=False))}</required_3d>')
        for requirement in manifest.get("motion_constraints", []):
            lines.append(f'    <required_motion>{html.escape(json.dumps(requirement, ensure_ascii=False))}</required_motion>')
        for requirement in manifest.get("interaction_constraints", []):
            lines.append(f'    <interaction_contract>{html.escape(json.dumps(requirement, ensure_ascii=False))}</interaction_contract>')
        lines.append("  </requirement_manifest>")

    motion_plan = brief.get("motion_plan")
    if motion_plan:
        if isinstance(motion_plan, list) and motion_plan:
            lines.append("  <motion_plan>")
            for m in motion_plan:
                if hasattr(m, "type"):
                    m_type = m.type.value if hasattr(m.type, "value") else str(m.type)
                    target = getattr(m, "target_section", "general")
                    intensity = getattr(m, "intensity", "subtle")
                    lines.append(f'    <motion type="{m_type}" section="{target}" intensity="{intensity}" />')
                elif isinstance(m, dict):
                    m_type = m.get("type", "scroll_reveal")
                    target = m.get("target_section", "general")
                    intensity = m.get("intensity", "subtle")
                    lines.append(f'    <motion type="{m_type}" section="{target}" intensity="{intensity}" />')
            lines.append("  </motion_plan>")
        elif isinstance(motion_plan, str) and "<motion" in motion_plan:
            lines.append(f"  {motion_plan.strip()}")

    if brief.get("products"):
        lines.append("  <products>")
        for product in brief["products"]:
            name = html.escape(product.get("name", ""), quote=True)
            price = html.escape(product.get("price", ""), quote=True)
            lines.append(f'    <product name="{name}" price="{price}" />')
        lines.append("  </products>")

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
