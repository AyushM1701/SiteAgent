#!/usr/bin/env python3
"""
data_pipeline/generate_batch6.py - Generates Batch 6 (85 High-Quality Website Trajectories)
Covers 5 distinct visual design archetypes:
  1. Refero / Monopo Saigon Editorial (Obsidian, Paper, Iridescent Fade, Roobert/Raleway, 75px pill buttons, 0px cards)
  2. Glassmorphic Aurora & AI Tech (Midnight obsidian, cyan/violet glow, frosted glass borders)
  3. Neo-Brutalist (3px solid black borders, Space Grotesk, bold saturated accents)
  4. Luxury Minimalist (Cinzel serif, gold accents, warm charcoal)
  5. Modern SaaS & Enterprise (Plus Jakarta Sans, accessible contrast, clean card systems)
"""

import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))

from agent_protocol import SITE_AGENT_SYSTEM_PROMPT

def thought(text: str) -> str:
    return f"<thought>\n{text}\n</thought>"

def finish(text: str) -> str:
    return f"<finish>\n{text}\n</finish>"

def write_site(tsx_path: str, tsx_code: str, css_path: str, css_code: str) -> str:
    return (
        f'<tool_call name="write_site">\n'
        f'<file path="{tsx_path}">\n{tsx_code.strip()}\n</file>\n'
        f'<file path="{css_path}">\n{css_code.strip()}\n</file>\n'
        f'</tool_call>'
    )

def obs_ok(files: list, next_instruction: str) -> str:
    lines = ['<observation status="ok">', '[Files accepted]:']
    for p in files:
        lines.append(f"  ✓ {p}")
    lines.append(f"\n[NEXT SECTION REQUIRED]: {next_instruction}")
    lines.append('Write ONE <tool_call name="write_site"> with exactly one .tsx file and one .css file for this section.')
    lines.append("</observation>")
    return "\n".join(lines)

def obs_done(files: list) -> str:
    lines = ['<observation status="complete">', '[SITE BUILD COMPLETE]: All required sections have been written successfully.', '[Files written in this session]:']
    for p in files:
        lines.append(f"  ✓ {p}")
    lines.append("Output a <finish> tag with a brief summary of the site you built.")
    lines.append("</observation>")
    return "\n".join(lines)


# 85 Unique Website Domain Definitions
DOMAINS_B6 = [
    # ── 1. Refero / Monopo Saigon Editorial Archetype (17) ───────────────────────────
    {
        "id": "site_refero_monopo_studio", "name": "Monopo Creative Studio",
        "tagline": "Avant-Garde Digital Art Direction & Spatial Narratives", "type": "agency",
        "prefix": "mcs", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Explore Portfolio", "hero_sub": "Bridging Japanese spatial sensibilities with razor-sharp editorial typography, bespoke digital installations, and identity design.",
        "section_name": "Selected Exhibitions", "section_id": "works", "pill": True,
        "items": [
            {"title": "Kyoto Sound Pavilion", "tag": "Spatial Installation", "desc": "Submerged ultrasonic soundscapes exploring silence and tactile reverberation inside a 300-year-old temple."},
            {"title": "Shibuya Kinetic Monolith", "tag": "Digital Identity", "desc": "Dynamic algorithmic generative identity transforming with wind velocity and pedestrian density."},
            {"title": "Verdant Bio-Interface", "tag": "Interactive Web", "desc": "Award-winning tactile web experience rendering cellular photosynthesis in real-time WebGL."},
            {"title": "Maison Noir Rebrand", "tag": "Brand Language", "desc": "Complete bespoke typography system and editorial print collateral for Parisian high fashion."}
        ],
        "contact": {"address": "Minami-Aoyama 5-7-22, Minato-ku, Tokyo 107-0062", "phone": "+81 3-5413-8820", "email": "contact@monopostudio.art", "hours": "Mon–Fri: 10am–7pm JST"}
    },
    {
        "id": "site_refero_atelier_lumiere", "name": "Atelier Lumière",
        "tagline": "Haute Horlogerie & Hand-Finished Mechanical Calibers", "type": "luxury",
        "prefix": "al", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#b83229",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Reserve Commission", "hero_sub": "Independent Genevan watchmaking: hand-beveled titanium bridges, flying tourbillons, and obsidian dials crafted one by one.",
        "section_name": "Caliber Collections", "section_id": "calibers", "pill": True,
        "items": [
            {"title": "Caliber 01 Tourbillon", "tag": "Bespoke Only", "desc": "Twin-barrel movement with 120-hour power reserve and mirror-polished black zirconium balance."},
            {"title": "Nocturne Perpetual", "tag": "Limited Edition (8)", "desc": "Astronomical moonphase accurate to one day in 577 years with hand-engraved meteorite dial."},
            {"title": "Chronograph Squelette", "tag": "Monopusher", "desc": "Skeletonized column-wheel chronograph with rose gold balance spring and sapphire bridges."},
            {"title": "Obsidian Deep Diver", "tag": "Titanium Grade 5", "desc": "Helium relief valve with ceramic unidirectional bezel and luminous ruthenium indices."}
        ],
        "contact": {"address": "Rue du Rhône 42, 1204 Genève, Switzerland", "phone": "+41 22 819 9000", "email": "concierge@atelierlumiere.ch", "hours": "By Private Appointment Only"}
    },
    {
        "id": "site_refero_kinfolk_publishing", "name": "Kinfolk Press",
        "tagline": "Independent Literature, Design Criticism, and Architectural Monographs", "type": "publishing",
        "prefix": "kp", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Browse Imprint", "hero_sub": "Printed with vegetable inks on archival Swedish cotton stock. Dedicated to rigorous design commentary, essays, and visual culture.",
        "section_name": "Recent Publications", "section_id": "titles", "pill": True,
        "items": [
            {"title": "The Geometry of Silence", "tag": "Hardcover Monograph", "desc": "A photographic exploration of Tadao Ando's concrete sanctuaries across Japan."},
            {"title": "Radical Restraint", "tag": "Critical Essays", "desc": "Contemporary essays on architectural minimalism, resource scarcity, and spatial ethics."},
            {"title": "Typography of Modernism", "tag": "Type Specimen", "desc": "Archival documentation of Swiss International Style typography from 1950 to 1975."},
            {"title": "Chronicles of Form", "tag": "Biannual Journal", "desc": "Issue 14 featuring in-depth conversations with Scandinavian ceramicists and weavers."}
        ],
        "contact": {"address": "Amagertorv 14, 1160 Copenhagen, Denmark", "phone": "+45 33 12 44 20", "email": "editors@kinfolkpress.dk", "hours": "Tue–Sat: 11am–6pm CET"}
    },
    {
        "id": "site_refero_archetype_type", "name": "Archetype Type Foundry",
        "tagline": "Variable OpenType Foundational Typefaces for Digital Screen Systems", "type": "foundry",
        "prefix": "atf", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Test & License", "hero_sub": "Rigorous typographic craft engineered for high-density displays. Comprehensive Latin, Cyrillic, and Greek glyph coverage.",
        "section_name": "Type Families", "section_id": "typefaces", "pill": True,
        "items": [
            {"title": "Roobert Grotesk", "tag": "Variable Font", "desc": "18 weights across proportional widths with ink-traps optimized for small-caption legibility."},
            {"title": "Saigon Serif Display", "tag": "Display High Contrast", "desc": "Razor-sharp hairline serifs inspired by 19th-century French Didot and Indochine modernism."},
            {"title": "Monolith Mono", "tag": "Technical Monospace", "desc": "Engineered for syntax highlighters and terminal workflows with custom programming ligatures."},
            {"title": "Apex Superfamily", "tag": "Sans + Slab + Serif", "desc": "Unified typographic ecosystem sharing identical vertical metrics and x-heights."}
        ],
        "contact": {"address": "Clerkenwell Close 9, London EC1R 0AT, UK", "phone": "+44 20 7490 8821", "email": "licensing@archetypefoundry.com", "hours": "Mon–Fri: 9am–6pm GMT"}
    },
    {
        "id": "site_refero_forma_industrial", "name": "Forma Industrial Lab",
        "tagline": "Honest Materials, Monolithic Castings, and Tactile Everyday Objects", "type": "design_studio",
        "prefix": "fil", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "View Objects", "hero_sub": "Stripping away decorative excess to celebrate sand-cast aluminum, turned brass, smoked glass, and raw mechanical utility.",
        "section_name": "Object Series", "section_id": "objects", "pill": True,
        "items": [
            {"title": "Cast Aluminum Desk Tray", "tag": "Die-Cast Monolith", "desc": "Single-piece pressure die-cast aluminum with matte bead-blasted raw anodized surface."},
            {"title": "Heavy Brass Loupe & Stand", "tag": "Optical Grade", "desc": "Machined solid brass cylinder holding a triple-element anti-reflective magnifying optic."},
            {"title": "Smoked Borosilicate Carafe", "tag": "Hand-Blown", "desc": "Thermal-shock resistant laboratory glass carafe with raw cork spherical stopper."},
            {"title": "Tactile Mechanical Dial", "tag": "Rotary Encoder", "desc": "Weighted 6061 billet aluminum volume controller with tactile 24-step magnetic detents."}
        ],
        "contact": {"address": "Via Tortona 31, 20144 Milano MI, Italy", "phone": "+39 02 837 2190", "email": "studio@formaindustrial.it", "hours": "Mon–Fri: 9:30am–6:30pm CET"}
    },
    {
        "id": "site_refero_chronicle_film", "name": "Chronicle Film Company",
        "tagline": "Independent 35mm Cinema, Documentary Features & Fine Cinematography", "type": "film",
        "prefix": "cfc", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Watch Showreel", "hero_sub": "Honoring analog celluloid textures, observational stillness, and uncompromising long-form storytelling across global film festivals.",
        "section_name": "Feature Productions", "section_id": "films", "pill": True,
        "items": [
            {"title": "Distant Signals (2025)", "tag": "Feature Narrative", "desc": "Shot on Kodak 5219 35mm across the remote salt flats of the Atacama Desert. Official Venice Selection."},
            {"title": "The Last Glassmaker", "tag": "Documentary", "desc": "An intimate portrait of the final master furnace artisan on the Venetian island of Murano."},
            {"title": "Subterranean Cities", "tag": "Docuseries (4 Ep)", "desc": "Exploring ancient underground stone civilizations in Cappadocia and southern Italy."},
            {"title": "Monsoon Shadows", "tag": "Short Film", "desc": "A poetic study of monsoonal rainfall on concrete modernist architecture in Chandigarh."}
        ],
        "contact": {"address": "120 Mercer St, New York, NY 10012", "phone": "+1 (212) 555-0144", "email": "production@chroniclefilms.com", "hours": "Mon–Fri: 9am–6pm EST"}
    },
    {
        "id": "site_refero_mira_spatial", "name": "Mira Spatial Design",
        "tagline": "Exhibition Scenography, Museum Lighting & Ephemeral Pavilions", "type": "architecture",
        "prefix": "msd", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Exhibition Archives", "hero_sub": "Curating light, void, and material surfaces to create contemplative physical encounters for national galleries and biennials.",
        "section_name": "Selected Pavilions", "section_id": "pavilions", "pill": True,
        "items": [
            {"title": "Tate Modern Retrospective", "tag": "Museum Scenography", "desc": "Suspended blackened steel scrims creating acoustic isolation inside the Turbine Hall."},
            {"title": "Biennale Architettura Pavilion", "tag": "Venice 2025", "desc": "Rammed-earth circular chamber demonstrating natural evaporative cooling in the Giardini."},
            {"title": "Kyoto Crafts Triennale", "tag": "Exhibition Architecture", "desc": "Frameless tatami platforms illuminated strictly by filtered northern daylight."},
            {"title": "Permanent Kinetic Gallery", "tag": "Berlin Civic Center", "desc": "Motorized acoustic baffle ceilings adapting spatial volume based on audience occupancy."}
        ],
        "contact": {"address": "Auguststraße 69, 10117 Berlin, Germany", "phone": "+49 30 2888 4110", "email": "contact@mira-spatial.de", "hours": "Mon–Fri: 10am–6pm CET"}
    },
    {
        "id": "site_refero_velvet_parfum", "name": "Maison De Nuit",
        "tagline": "Rare Botanical Extractions & Night-Blooming Olfactive Formulations", "type": "perfumery",
        "prefix": "mdn", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Discover Extraits", "hero_sub": "Hand-bottled in flacon noir glass. Formulated in Grasse using wild-harvested orris root, aged patchouli, and smoke.",
        "section_name": "Olfactive Extraits", "section_id": "fragrances", "pill": True,
        "items": [
            {"title": "Extrait 01: Cendre Noire", "tag": "50ml Flacon", "desc": "Smoked cedarwood, Moroccan labdanum, birch tar, and charred Madagascan vanilla."},
            {"title": "Extrait 02: Orris Nocturne", "tag": "50ml Flacon", "desc": "Five-year aged Florentine iris root, velvet musk, cold frankincense, and vetiver."},
            {"title": "Extrait 03: Fleur Obscure", "tag": "50ml Flacon", "desc": "Night-blooming tuberose, black currant buds, bitter almond, and dark ambergris."},
            {"title": "Extrait 04: Santal Brûlé", "tag": "50ml Flacon", "desc": "Sustainably harvested Australian sandalwood, crushed cardamom, and benzoin tears."}
        ],
        "contact": {"address": "18 Rue Saint-Roch, 75001 Paris, France", "phone": "+33 1 42 60 88 12", "email": "parfums@maisondenuit.fr", "hours": "Tue–Sat: 11am–7:30pm CET"}
    },
    {
        "id": "site_refero_aura_sound", "name": "Aura Acoustic Laboratories",
        "tagline": "Reference Vacuum Tube Amplification & Custom Ribbon Loudspeakers", "type": "audio",
        "prefix": "aal", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Audition Systems", "hero_sub": "Hand-wired point-to-point circuitry, mirror-finished nickel chassis, and planar ribbon transducers delivering pure holographic sound.",
        "section_name": "Reference Hardware", "section_id": "audio_gear", "pill": True,
        "items": [
            {"title": "Model 300B Monoblock", "tag": "Class-A Triode", "desc": "Direct-heated 300B output tubes with custom hand-wound Lundahl silver core transformers."},
            {"title": "Aura Planar Loudspeaker", "tag": "True Ribbon Dipole", "desc": "Full-range 1.8-meter ribbon transducer with zero crossover in the critical vocal band."},
            {"title": "Direct-Drive Turntable", "tag": "Quartz Lock", "desc": "35kg magnetic levitation platter machined from solid brass and acoustic Delrin."},
            {"title": "Discrete Phono Stage", "tag": "Dual Mono Tube", "desc": "Ultra-quiet MC step-up with 74dB gain and passive RIAA equalization curve."}
        ],
        "contact": {"address": "Königsallee 92, 40212 Düsseldorf, Germany", "phone": "+49 211 864 990", "email": "engineering@aurasound.de", "hours": "Private Auditions by Reservation"}
    },
    {
        "id": "site_refero_soma_athletics", "name": "Soma Technical Apparel",
        "tagline": "Aerodynamic Performance Uniforms Engineered from Polymer Scraps", "type": "fashion",
        "prefix": "sta", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Shop Collection", "hero_sub": "Ultralight bonded seams, laser-perforated thermal zones, and 100% regenerated ocean nylon engineered for mountain marathons.",
        "section_name": "Technical Apparel", "section_id": "apparel", "pill": True,
        "items": [
            {"title": "Ultralight Windshell Pro", "tag": "72 Grams", "desc": "Ultralight windproof ripstop with PFC-free DWR coating and integrated chest stow pocket."},
            {"title": "Bonded Trail Short", "tag": "Zero Seams", "desc": "Ultrasonic welded construction with integrated 360-degree hydration waist band."},
            {"title": "Thermal Merino Midlayer", "tag": "18.5 Micron", "desc": "Merino wool and graphene yarn blend regulating core body temperature in alpine squalls."},
            {"title": "Compression Race Tight", "tag": "Targeted Elasticity", "desc": "Graduated compression weave reducing muscle oscillation during ultra-distance running."}
        ],
        "contact": {"address": "520 West 28th St, New York, NY 10001", "phone": "+1 (212) 555-0199", "email": "lab@somaperformance.com", "hours": "Daily: 10am–7pm EST"}
    },
    {
        "id": "site_refero_verve_ceramics", "name": "Studio Tsuchi",
        "tagline": "Hand-Turned Wood-Fired Stoneware & Wabi-Sabi Vessels", "type": "craft",
        "prefix": "st", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Kiln Releases", "hero_sub": "Fired in a multi-chamber anagama wood kiln for 7 continuous days. Natural fly-ash glaze markings make every vessel strictly unique.",
        "section_name": "Vessel Collection", "section_id": "vessels", "pill": True,
        "items": [
            {"title": "Anagama Ash Vase", "tag": "Unique (1 of 1)", "desc": "Natural wood ash melting into olive green celadon streaks across rough grogged clay body."},
            {"title": "Black Shino Tea Bowl", "tag": "Chawan", "desc": "Carved charcoal clay glazed in thick feldspathic Shino with dramatic carbon trapping."},
            {"title": "Serving Platter No. 04", "tag": "Slab Built", "desc": "Hand-torn perimeter with scorched pine ash patterns and unglazed raw stoneware foot."},
            {"title": "Sake Server & Cup Set", "tag": "Tokkuri + Guinomi", "desc": "Iron-rich clay body with subtle shell impressions left by kiln stacking wads."}
        ],
        "contact": {"address": "Tanba-Sasayama, Hyogo Prefecture 669-2141, Japan", "phone": "+81 79 590 1200", "email": "kiln@studiotsuchi.jp", "hours": "Studio Visits by Appointment"}
    },
    {
        "id": "site_refero_zenith_galleries", "name": "Zenith Contemporary",
        "tagline": "Post-War Masterworks, Contemporary Sculpture & Monograph Editions", "type": "gallery",
        "prefix": "zg", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Current Exhibition", "hero_sub": "Representing internationally celebrated artists working in monumental metal, raw pigment, and spatial architecture.",
        "section_name": "Featured Works", "section_id": "artworks", "pill": True,
        "items": [
            {"title": "Monolith in Corten (2024)", "tag": "Monumental Sculpture", "desc": "A 4-meter weathered steel monolith examining spatial compression and gravitational balance."},
            {"title": "Pigment Field No. 88", "tag": "Pure Indigo on Linen", "desc": "Hand-crushed natural mineral indigo layered over raw unprimed Belgian linen."},
            {"title": "Suspended Void IV", "tag": "Cast Glass & Bronze", "desc": "Optical lead crystal prism holding trapped air bubbles atop a raw sand-cast bronze pedestal."},
            {"title": "Architectural Nocturne", "tag": "Charcoal on Cotton", "desc": "Monumental 3-meter charcoal study exploring shadow lines of brutalist structures."}
        ],
        "contact": {"address": "530 West 24th St, New York, NY 10011", "phone": "+1 (212) 555-0177", "email": "curatorial@zenithcontemporary.com", "hours": "Tue–Sat: 10am–6pm EST"}
    },
    {
        "id": "site_refero_solstice_lighting", "name": "Solstice Lighting Works",
        "tagline": "Sculptural Brass Luminaires & Dim-to-Warm Architectural Fixtures", "type": "lighting",
        "prefix": "slw", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Specifier Catalog", "hero_sub": "Precision turned solid brass, hand-spun fluted reflectors, and museum-grade 98 CRI light engines tuned for residential serenity.",
        "section_name": "Luminaire Series", "section_id": "luminaires", "pill": True,
        "items": [
            {"title": "Solstice Chandelier 06", "tag": "Modular Brass", "desc": "Counterbalanced brushed brass arms with mouth-blown etched opal glass globes."},
            {"title": "Eclipse Wall Sconce", "tag": "Indirect Wash", "desc": "Dual concentric blackened bronze discs reflecting warm 2200K ambient illumination."},
            {"title": "Pendant Cylinder No. 2", "tag": "Solid Billet", "desc": "Machined from solid brass bar with diamond knurled bezel and micro-louvre glare guard."},
            {"title": "Monument Floor Lamp", "tag": "Granite Base", "desc": "Honed Nero Marquina base with a slender 2.2-meter hand-patinated bronze cantilever."}
        ],
        "contact": {"address": "Dover St 18, Mayfair, London W1S 4LT, UK", "phone": "+44 20 7946 0990", "email": "trade@solsticeworks.co.uk", "hours": "Mon–Fri: 9am–5:30pm GMT"}
    },
    {
        "id": "site_refero_terra_botanics", "name": "Terra Rare Botanics",
        "tagline": "Architectural Indoor Flora, Biophilic Curation & Living Installations", "type": "botanical",
        "prefix": "trb", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Inquire Plants", "hero_sub": "Curating mature specimen ficus, rare cycads, and sculpted bonsais potted in handcrafted basalt and clay planters.",
        "section_name": "Specimen Catalog", "section_id": "botanicals", "pill": True,
        "items": [
            {"title": "Mature Ficus Umbellata", "tag": "2.4m Specimen", "desc": "Architectural broad-leaf canopy with natural sculptural curved trunk potted in volcanic basalt."},
            {"title": "Australian Bottle Tree", "tag": "Rare Caudiciform", "desc": "Swollen succulent trunk with delicate lace foliage adapted for high-ceiling penthouses."},
            {"title": "Sculptural Juniper Bonsai", "tag": "45-Year Specimen", "desc": "Trained in the literati style with natural deadwood jin and shari branches."},
            {"title": "Architectural Cycad", "tag": "Living Fossil", "desc": "Symmetrical crown of stiff feather fronds emerging from a heavy rough-textured caudex."}
        ],
        "contact": {"address": "848 S Grand Ave, Los Angeles, CA 90017", "phone": "+1 (213) 555-0188", "email": "flora@terrabotanics.com", "hours": "Wed–Sun: 10am–6pm PST"}
    },
    {
        "id": "site_refero_vanguard_furniture", "name": "Vanguard Form",
        "tagline": "Handcrafted Solid White Oak Furniture & Danish Paper Cord Weaving", "type": "furniture",
        "prefix": "vf", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "View Showroom", "hero_sub": "Joined with traditional mortise-and-tenon craftsmanship. Made in Oregon using sustainably felled American timber.",
        "section_name": "Furniture Pieces", "section_id": "furniture", "pill": True,
        "items": [
            {"title": "The Pavilion Dining Table", "tag": "Solid White Oak", "desc": "3-meter dining table with seamless butterfly keys and hand-scraped chamfered edge profile."},
            {"title": "Cord Lounge Chair", "tag": "Danish Paper Cord", "desc": "Sculptural solid walnut frame woven with 400 meters of unbleached three-ply paper cord."},
            {"title": "Floating Credenza 03", "tag": "Sliding Louvres", "desc": "Concealed wall-mount credenza with continuous wood grain tambour doors."},
            {"title": "Low Bench in Charred Ash", "tag": "Shou Sugi Ban", "desc": "Traditional Japanese flame-charred finish sealed with natural beeswax and citrus oil."}
        ],
        "contact": {"address": "220 SE 11th Ave, Portland, OR 97214", "phone": "+1 (503) 555-0164", "email": "orders@vanguardform.com", "hours": "Thu–Sun: 11am–5pm PST"}
    },
    {
        "id": "site_refero_opus_records", "name": "Opus Master Recordings",
        "tagline": "Audiophile Direct-to-Disc Vinyl Pressings & Acoustic Chamber Sessions", "type": "music",
        "prefix": "omr", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "View Catalog", "hero_sub": "Uncompressed analog masters cut live to lacquer on a Neumann VMS 80 lathe. Pressed on 200g virgin vinyl in limited editions of 500.",
        "section_name": "Master Pressings", "section_id": "vinyl", "pill": True,
        "items": [
            {"title": "Chamber Quartet in D Minor", "tag": "200g Virgin Vinyl", "desc": "Recorded direct-to-disc with a matched pair of Neumann M49 tube microphones."},
            {"title": "Solo Piano: Nocturnes", "tag": "45 RPM (2xLP)", "desc": "Steinway D Concert Grand captured in the historic acoustics of Abbey Road Studio 2."},
            {"title": "Scandinavian Folk Ballads", "tag": "Direct Metal Master", "desc": "Hardanger fiddle and acoustic nylon guitar recorded in a 12th-century stone church."},
            {"title": "Modular Synthesizer Etudes", "tag": "Pure Analog Path", "desc": "Live improvisations recorded straight to 2-inch 16-track Studer tape at 30 ips."}
        ],
        "contact": {"address": "Stadthausbrücke 1, 20355 Hamburg, Germany", "phone": "+49 40 361 500", "email": "masters@opusrecordings.de", "hours": "Mon–Fri: 10am–6pm CET"}
    },
    {
        "id": "site_refero_kanso_tea", "name": "Kanso Tea Ceremonies",
        "tagline": "Single-Estate Uji Matcha & Contemplative Japanese Tea Ceremonies", "type": "tea",
        "prefix": "ktc", "primary": "#000000", "accent": "#a02d25", "accent_hover": "#c9392f",
        "surface": "#181818", "heading_font": "Raleway", "body_font": "Roobert",
        "cta": "Book Ceremony", "hero_sub": "Shade-grown tencha stone-milled in Kyoto. Savor our ceremonial matcha in a private tatami tearoom designed for stillness.",
        "section_name": "Ceremonial Cultivars", "section_id": "tea_menu", "pill": True,
        "items": [
            {"title": "Uji Gokou Single Cultivar", "tag": "Ceremonial Grade", "desc": "Single-origin tencha shade-grown for 28 days with rich umami and zero astringency."},
            {"title": "Asahi Heritage Reserve", "tag": "Spring First Harvest", "desc": "Stone-milled at 40g per hour on granite stones to preserve bright emerald chlorophyll."},
            {"title": "Handmade Bamboo Chasen", "tag": "100-Prong Whisk", "desc": "Carved from aged black bamboo by 16th-generation artisans in Takayama, Nara."},
            {"title": "Private Four-Course Ceremony", "tag": "90 Minutes", "desc": "Traditional tearoom entry with seasonal wagashi sweets and thick koicha preparation."}
        ],
        "contact": {"address": "Gion-machi Minamigawa, Higashiyama-ku, Kyoto 605-0074", "phone": "+81 75 561 0200", "email": "reserve@kansotea.jp", "hours": "Daily: 9:30am–5pm JST (Booking Req)"}
    },

    # ── 2. Glassmorphic Aurora & AI Tech Archetype (17) ─────────────────────────────
    {
        "id": "site_glass_cortex_ai", "name": "Cortex Neural Engine",
        "tagline": "Autonomous Multi-Agent Orchestration & Real-Time Reasoning Pipelines", "type": "ai_tech",
        "prefix": "cne", "primary": "#080b14", "accent": "#38bdf8", "accent_hover": "#0ea5e9",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Launch Sandbox", "hero_sub": "Deploy autonomous agents that reason, execute terminal tools, and verify outputs with deterministic reliability.",
        "section_name": "Agent Capabilities", "section_id": "capabilities", "pill": False,
        "items": [
            {"title": "Autonomous Tool Use", "tag": "Zero Latency", "desc": "Execute bash commands, API calls, and headless browser tests with full rollback capability."},
            {"title": "Context Compaction Engine", "tag": "128k Window", "desc": "Streaming summary compression preserving critical AST tokens while reducing inference cost by 60%."},
            {"title": "Self-Correcting Unit Loops", "tag": "Test Driven", "desc": "Automatic retry loops feeding TypeScript compiler errors back to the model until test suites pass."},
            {"title": "Private On-Prem Deployments", "tag": "Air-Gapped", "desc": "Deploy 3B to 70B parameter models on your sovereign GPU clusters with zero external telemetry."}
        ],
        "contact": {"address": "500 Howard St, Suite 400, San Francisco, CA 94105", "phone": "+1 (415) 555-0183", "email": "enterprise@cortexneural.ai", "hours": "24/7 Developer Support"}
    },
    {
        "id": "site_glass_nexus_vector", "name": "Nexus Vector DB",
        "tagline": "GPU-Accelerated Vector Search Ingesting Billions of High-Dim Embeddings", "type": "ai_tech",
        "prefix": "nvd", "primary": "#080b14", "accent": "#818cf8", "accent_hover": "#6366f1",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Deploy Cluster", "hero_sub": "Sub-millisecond HNSW vector indexing with native hybrid keyword ranking, metadata filtering, and automatic sharding.",
        "section_name": "Vector Architecture", "section_id": "features", "pill": False,
        "items": [
            {"title": "Sub-Millisecond P99 Query", "tag": "GPU Native", "desc": "CUDA-accelerated distance metrics searching 100M vectors in under 800 microseconds."},
            {"title": "Hybrid Dense + Sparse Search", "tag": "BM25 + HNSW", "desc": "Combine semantic neural embeddings with exact keyword precision in a single query pass."},
            {"title": "Real-Time Mutable Indexing", "tag": "Zero Downtime", "desc": "Insert and update embeddings with immediate read consistency without re-building graphs."},
            {"title": "Quantized Vector Memory", "tag": "Product Quantization", "desc": "Compress vectors by 8x with less than 0.5% recall loss using adaptive scalar quantization."}
        ],
        "contact": {"address": "100 Montgomery St, Suite 1200, San Francisco, CA 94104", "phone": "+1 (415) 555-0129", "email": "support@nexusvector.io", "hours": "Mon–Fri: 8am–6pm PST"}
    },
    {
        "id": "site_glass_hyperion_cloud", "name": "Hyperion Serverless",
        "tagline": "Edge Compute Isolates with Zero Cold Starts and Instant Global Replication", "type": "cloud",
        "prefix": "hsc", "primary": "#080b14", "accent": "#2dd4bf", "accent_hover": "#14b8a6",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Start Free Trial", "hero_sub": "Run V8 isolates in 310 edge data centers globally. Sub-5ms response times worldwide with zero server maintenance.",
        "section_name": "Edge Platform", "section_id": "platform", "pill": False,
        "items": [
            {"title": "Zero Millisecond Cold Starts", "tag": "V8 Isolates", "desc": "Pre-warmed memory snapshots boot worker isolates in under 200 microseconds."},
            {"title": "Distributed Global Storage", "tag": "ACID Key-Value", "desc": "Ultra-fast distributed state replicated to 310 edge cities with automatic cache eviction."},
            {"title": "Native WebSocket PTY Support", "tag": "Bi-Directional", "desc": "Persistent streaming connections with sub-10ms roundtrips for real-time applications."},
            {"title": "Automatic Branch Previews", "tag": "Git Integrated", "desc": "Every git push spawns an immutable production preview environment with unique HTTPS URL."}
        ],
        "contact": {"address": "111 8th Ave, New York, NY 10011", "phone": "+1 (212) 555-0192", "email": "sales@hyperioncloud.dev", "hours": "24/7 Global NOC"}
    },
    {
        "id": "site_glass_quant_pulse", "name": "QuantPulse Telemetry",
        "tagline": "Microsecond Market Telemetry & Real-Time Portfolio Risk Modeling", "type": "fintech",
        "prefix": "qpt", "primary": "#080b14", "accent": "#38bdf8", "accent_hover": "#0ea5e9",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Request Demo", "hero_sub": "Direct market data feeds from CME, NASDAQ, and Euronext with sub-microsecond tick processing and live VaR matrices.",
        "section_name": "Quant Modules", "section_id": "modules", "pill": False,
        "items": [
            {"title": "FPGA Feed Handler", "tag": "Sub-Microsecond", "desc": "Hardware-accelerated ITCH/OUCH protocol decoding directly on PCIe FPGA accelerators."},
            {"title": "Real-Time Value at Risk (VaR)", "tag": "Monte Carlo", "desc": "Simulate 100,000 market shocks across equity and derivatives books in under 50ms."},
            {"title": "Order Book Replay & Sim", "tag": "Tick Accurate", "desc": "Backtest execution algorithms with L3 nanosecond order book reconstruction."},
            {"title": "Cross-Asset Arbitrage Scanner", "tag": "Multi-Venue", "desc": "Detect cross-exchange spread dislocations across global FX and index futures."}
        ],
        "contact": {"address": "100 Wall St, 24th Floor, New York, NY 10005", "phone": "+1 (212) 555-0158", "email": "institutional@quantpulse.trade", "hours": "24/7 Trading Desk Support"}
    },
    {
        "id": "site_glass_sentinel_zero", "name": "Sentinel Zero Defense",
        "tagline": "Kernel-Level eBPF Autonomous Threat Detection & Runtime Isolation", "type": "cybersecurity",
        "prefix": "szd", "primary": "#080b14", "accent": "#f43f5e", "accent_hover": "#e11d48",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Deploy Sentinel Agent", "hero_sub": "Stop zero-day exploits before execution. Deep Linux kernel visibility without kernel modules or performance degradation.",
        "section_name": "Defense Vectors", "section_id": "vectors", "pill": False,
        "items": [
            {"title": "eBPF Kernel Probing", "tag": "Zero Overhead", "desc": "Inspect syscalls, network sockets, and file descriptors at native speed with zero latency impact."},
            {"title": "Automated Process Quarantine", "tag": "Instant Kill", "desc": "Terminate unauthorized container escapes and shell spawning within 50 microseconds."},
            {"title": "Memory Exploitation Shield", "tag": "ROP/JOP Guard", "desc": "Detect heap overflows, return-oriented programming, and buffer corruption in real time."},
            {"title": "Cryptographic Audit Trail", "tag": "Tamper-Proof", "desc": "All security events signed and streamed to immutable write-once ledger archives."}
        ],
        "contact": {"address": "Reston Town Center, Suite 600, Reston, VA 20190", "phone": "+1 (703) 555-0133", "email": "secops@sentinelzero.security", "hours": "24/7 SOC Emergency Response"}
    },
    {
        "id": "site_glass_aether_stream", "name": "Aether Spatial Audio",
        "tagline": "Real-Time Neural Speech Synthesis & Ray-Traced Acoustic Environments", "type": "ai_tech",
        "prefix": "asa", "primary": "#080b14", "accent": "#a855f7", "accent_hover": "#9333ea",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Test Speech Engine", "hero_sub": "Sub-80ms voice synthesis with emotional inflection, realistic breath dynamics, and ray-traced HRTF spatialization.",
        "section_name": "Audio SDKs", "section_id": "audio_sdks", "pill": False,
        "items": [
            {"title": "Zero-Latency Voice Stream", "tag": "<80ms Glass-to-Ear", "desc": "Streaming chunked neural vocoder delivering continuous audio while generation is in progress."},
            {"title": "Binaural Room Simulation", "tag": "Acoustic Ray-Tracing", "desc": "Calculate real-time early reflections and reverberation tailored to user headphone geometry."},
            {"title": "Multi-Lingual Voice Cloning", "tag": "3-Second Sample", "desc": "Zero-shot speaker voice cloning across 45 languages with cross-lingual accent fidelity."},
            {"title": "Voice Emotion Control", "tag": "Parametric Prosody", "desc": "Dynamically adjust speaking pace, vocal fry, excitement, and solemnity in runtime API calls."}
        ],
        "contact": {"address": "600 Congress Ave, Austin, TX 78701", "phone": "+1 (512) 555-0176", "email": "developers@aethersound.ai", "hours": "Mon–Fri: 9am–6pm CST"}
    },
    {
        "id": "site_glass_prism_vision", "name": "Prism Computer Vision",
        "tagline": "Industrial Sub-Millimeter Defect Detection at 120 Frames Per Second", "type": "ai_tech",
        "prefix": "pcv", "primary": "#080b14", "accent": "#38bdf8", "accent_hover": "#0ea5e9",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Request System Spec", "hero_sub": "Deep learning visual inspection models deployed on high-speed semiconductor lines, automotive stamping, and pharmaceutical packaging.",
        "section_name": "Vision Capabilities", "section_id": "vision", "pill": False,
        "items": [
            {"title": "Sub-Millimeter Inspection", "tag": "120 FPS High Speed", "desc": "Identify hairline micro-cracks and surface contaminants on silicon wafers at conveyor speeds."},
            {"title": "Edge TensorRT Inference", "tag": "Dual Orin Jetson", "desc": "Full inference execution inside IP67 industrial enclosures without external cloud connectivity."},
            {"title": "Few-Shot Defect Learning", "tag": "5 Samples Required", "desc": "Train new defect classes in 15 minutes using synthetic adversarial defect augmentation."},
            {"title": "Automated Reject Actuation", "tag": "Pneumatic Integration", "desc": "Trigger high-speed pneumatic sorting arms within 4 milliseconds of defect classification."}
        ],
        "contact": {"address": "150 Cambridgepark Dr, Cambridge, MA 02140", "phone": "+1 (617) 555-0189", "email": "industrial@prismvision.tech", "hours": "Mon–Fri: 8am–6pm EST"}
    },
    {
        "id": "site_glass_synapse_mesh", "name": "Synapse Service Mesh",
        "tagline": "Zero-Trust Microservice Interconnect with Cryptographic Mutual TLS", "type": "cloud",
        "prefix": "ssm", "primary": "#080b14", "accent": "#2dd4bf", "accent_hover": "#14b8a6",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Install Mesh Operator", "hero_sub": "Automatic sidecar injection, SPIFFE workload identities, and distributed tracing across hybrid Kubernetes clusters.",
        "section_name": "Mesh Features", "section_id": "mesh_features", "pill": False,
        "items": [
            {"title": "Automated mTLS Handshake", "tag": "FIPS 140-2 Validated", "desc": "Rotate cryptographic x509 workload certificates every 12 hours with zero connection drops."},
            {"title": "Dynamic Traffic Splitting", "tag": "Canary & Blue-Green", "desc": "Weight traffic between versions based on HTTP header criteria, user roles, or latencies."},
            {"title": "Distributed Trace Graph", "tag": "OpenTelemetry Native", "desc": "Visualize cross-cluster latency bottlenecks with automatic dependency topology maps."},
            {"title": "L7 Policy Enforcement", "tag": "Envoy Powered", "desc": "Enforce fine-grained rate limits, JWT claims validation, and gRPC method authorization."}
        ],
        "contact": {"address": "1200 4th Ave, Seattle, WA 98101", "phone": "+1 (206) 555-0143", "email": "operations@synapsemesh.io", "hours": "24/7 SRE Support"}
    },
    {
        "id": "site_glass_vortex_crypto", "name": "Vortex Exchange Engine",
        "tagline": "Decentralized High-Throughput Limit Orderbook with Sub-Millisecond Settling", "type": "fintech",
        "prefix": "vee", "primary": "#080b14", "accent": "#818cf8", "accent_hover": "#6366f1",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Connect Wallet & Trade", "hero_sub": "Institutional liquidity with non-custodial cryptographic guarantees. Zero front-running with verifiable batch auctions.",
        "section_name": "Exchange Specs", "section_id": "specs", "pill": False,
        "items": [
            {"title": "Zero Front-Running Auctions", "tag": "MEV Resistant", "desc": "Cryptographically blinded batch auctions ensuring miners and searchers cannot reorder transactions."},
            {"title": "Cross-Margin Engine", "tag": "Portfolio Margin", "desc": "Offset risk across spot and perpetual positions to maximize capital efficiency."},
            {"title": "Non-Custodial Cold Settling", "tag": "ZK-Rollup", "desc": "Assets remain under private key custody until cryptographic state transition proofs settle on L1."},
            {"title": "Institutional FIX API", "tag": "Direct WebSocket", "desc": "Standardized FIX 4.4 and WebSocket protocol endpoints supporting 50,000 orders/sec."}
        ],
        "contact": {"address": "Bahnhofstrasse 21, 6300 Zug, Switzerland", "phone": "+41 41 710 4400", "email": "support@vortextrade.eth", "hours": "24/7 Protocol Availability"}
    },
    {
        "id": "site_glass_chronos_time", "name": "Chronos Time-Series",
        "tagline": "Distributed Columnar Database Ingesting 50 Million Metric Points Per Second", "type": "database",
        "prefix": "cts", "primary": "#080b14", "accent": "#38bdf8", "accent_hover": "#0ea5e9",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Start Ingestion Benchmark", "hero_sub": "Gorilla-compressed columnar storage, native downsampling policies, and sub-second SQL queries across petabytes of IoT data.",
        "section_name": "Database Engines", "section_id": "db_engines", "pill": False,
        "items": [
            {"title": "50M Events/Sec Ingestion", "tag": "SIMD Vectorized", "desc": "Lock-free write pipelines maximizing multi-core NVMe write bandwidth without thread contention."},
            {"title": "Gorilla Delta-of-Delta", "tag": "12:1 Compression", "desc": "Store double-precision timestamps and sensor values with lossless sub-byte storage overhead."},
            {"title": "Continuous Downsampling", "tag": "Automated Retention", "desc": "Aggregate raw seconds into 1-minute and 1-hour rollups automatically in the background."},
            {"title": "Native PromQL & SQL Interface", "tag": "Full Compatibility", "desc": "Drop-in replacement for Prometheus, InfluxDB, and Timescale without modifying Grafana dashboards."}
        ],
        "contact": {"address": "180 Sansome St, San Francisco, CA 94104", "phone": "+1 (415) 555-0167", "email": "benchmarks@chronosdb.io", "hours": "Mon–Fri: 9am–6pm PST"}
    },
    {
        "id": "site_glass_stellar_sat", "name": "Stellar Orbit Telemetry",
        "tagline": "Satellite Constellation Telemetry, Orbit Maneuvers & Downlink Coordination", "type": "aerospace",
        "prefix": "sot", "primary": "#080b14", "accent": "#38bdf8", "accent_hover": "#0ea5e9",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Schedule Mission Demo", "hero_sub": "Autonomous collision avoidance, optical ground station scheduling, and payload telemetry for LEO satellite constellations.",
        "section_name": "Mission Control Modules", "section_id": "mission_modules", "pill": False,
        "items": [
            {"title": "Automated Conjunction Avoidance", "tag": "LEO Orbit", "desc": "Calculate debris close-approach probabilities and generate autonomous station-keeping burns."},
            {"title": "Optical Downlink Scheduler", "tag": "Laser Comms", "desc": "Coordinate high-bandwidth 10 Gbps optical ground contacts across cloud-free alpine observatories."},
            {"title": "Solar Array Degradation Tracking", "tag": "Telemetry AI", "desc": "Predict photovoltaic degradation and battery cycle life under extreme Van Allen radiation."},
            {"title": "Doppler Shift Compensation", "tag": "Ground Station SDR", "desc": "Dynamic real-time carrier frequency compensation for ultra-fast LEO passes."}
        ],
        "contact": {"address": "1250 Space Park Way, Mountain View, CA 94043", "phone": "+1 (650) 555-0171", "email": "missionops@stellarorbit.space", "hours": "24/7 Mission Control"}
    },
    {
        "id": "site_glass_axiom_formal", "name": "Axiom Formal Verification",
        "tagline": "Mathematical Proofs & Automated Formal Verification for Critical Protocols", "type": "cybersecurity",
        "prefix": "afv", "primary": "#080b14", "accent": "#a855f7", "accent_hover": "#9333ea",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Verify Contract Protocol", "hero_sub": "Moving beyond heuristic fuzzing. Generating mathematical proof certificates that prove code cannot enter invalid states.",
        "section_name": "Verification Proofs", "section_id": "proofs", "pill": False,
        "items": [
            {"title": "SMT Solver Solvency Proofs", "tag": "Z3 & CVC5 Engines", "desc": "Mathematically prove that protocol liquidation invariants hold under all combinations of price feeds."},
            {"title": "Bytecode Invariant Checking", "tag": "EVM & WASM", "desc": "Verify decompiled bytecode against formal specifications with automated counterexample generation."},
            {"title": "Reentrancy Proof Engines", "tag": "Zero False Positives", "desc": "Prove total absence of state re-entrance across multi-contract execution paths."},
            {"title": "Audited Mathematical Certificates", "tag": "Coq / Isabelle", "desc": "Deliver peer-reviewed machine-checkable proof certificates for regulatory submission."}
        ],
        "contact": {"address": "Oxford Science Park, Oxford OX4 4GA, UK", "phone": "+44 1865 555 019", "email": "proofs@axiomformal.com", "hours": "Mon–Fri: 9am–5pm GMT"}
    },
    {
        "id": "site_glass_nebula_render", "name": "Nebula Neural Radiance",
        "tagline": "Distributed GPU Cloud for Photorealistic 3D NeRF & Gaussian Splatting", "type": "ai_tech",
        "prefix": "nnr", "primary": "#080b14", "accent": "#f43f5e", "accent_hover": "#e11d48",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Upload Video Drone Scan", "hero_sub": "Convert drone footage and iPhone videos into interactive 3D Gaussian splat environments viewable on web and VR.",
        "section_name": "Rendering Pipelines", "section_id": "pipelines", "pill": False,
        "items": [
            {"title": "Gaussian Splat Reconstruction", "tag": "5 Min Processing", "desc": "Transform 4K drone footage into sub-millimeter accurate photorealistic 3D splats."},
            {"title": "Real-Time WebGL Spatial Viewer", "tag": "60 FPS in Browser", "desc": "Deliver photorealistic 3D architectural walk-throughs on mobile web without plugins."},
            {"title": "Dynamic Relighting & Weather", "tag": "Neural HDR", "desc": "Modify sun azimuth, overcast diffusion, and artificial lighting inside reconstructed captures."},
            {"title": "Point Cloud Mesh Extraction", "tag": "AutoCAD & Revit", "desc": "Export dense textured polygonal meshes directly into architectural BIM workflows."}
        ],
        "contact": {"address": "520 Broadway, Suite 300, Santa Monica, CA 90401", "phone": "+1 (310) 555-0142", "email": "cloud@nebularender.io", "hours": "Mon–Fri: 9am–6pm PST"}
    },
    {
        "id": "site_glass_omni_agent", "name": "OmniAgent Studio",
        "tagline": "Visual Multi-Agent Workflow Canvas & Autonomous Browser Executors", "type": "ai_tech",
        "prefix": "oas", "primary": "#080b14", "accent": "#38bdf8", "accent_hover": "#0ea5e9",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Build First Workflow", "hero_sub": "Connect LLM reasoning nodes with live headless browsers, SQL databases, and Slack webhooks on a drag-and-drop infinite canvas.",
        "section_name": "Studio Modules", "section_id": "studio_modules", "pill": False,
        "items": [
            {"title": "Visual Node Flow Designer", "tag": "Infinite Canvas", "desc": "Wire reasoning models, tool gates, and human-in-the-loop review steps with zero boilerplate."},
            {"title": "Stealth Headless Chromium", "tag": "Anti-Fingerprint", "desc": "Execute browser automation tasks bypassing bot detection, CAPTCHA hurdles, and cookie gates."},
            {"title": "Stateful Agent Memory Store", "tag": "Long-Term Recall", "desc": "Agents remember past task outcomes, user preferences, and company domain guidelines."},
            {"title": "Enterprise Governance Audits", "tag": "PII Redaction", "desc": "Automatically redact credit card numbers, passwords, and sensitive tokens from agent logs."}
        ],
        "contact": {"address": "400 Concar Dr, San Mateo, CA 94402", "phone": "+1 (650) 555-0155", "email": "hello@omniagent.ai", "hours": "Mon–Fri: 9am–6pm PST"}
    },
    {
        "id": "site_glass_helix_bio", "name": "Helix Molecular Genomics",
        "tagline": "Deep Learning Protein Design & Antibody Affinity Optimization", "type": "biotech",
        "prefix": "hmg", "primary": "#080b14", "accent": "#2dd4bf", "accent_hover": "#14b8a6",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Access Drug Discovery API", "hero_sub": "Generative diffusion models predicting complex macromolecular binding affinities and reducing pre-clinical candidate timelines by 75%.",
        "section_name": "Discovery Platforms", "section_id": "discovery", "pill": False,
        "items": [
            {"title": "De Novo Binder Design", "tag": "Picomolar Affinity", "desc": "Generate custom protein binders targeting undruggable membrane-bound oncology targets."},
            {"title": "Antibody Humanization", "tag": "Immunogenicity Zero", "desc": "Replace murine framework residues while preserving CDR loop geometry and target affinity."},
            {"title": "ADMET Predictive Profiling", "tag": "In-Silico Toxicity", "desc": "Predict liver microsomal clearance, membrane permeability, and hERG liability in seconds."},
            {"title": "Cryo-EM Structure Refinement", "tag": "Atomic Resolution", "desc": "Refine low-resolution electron density maps using neural molecular dynamics priors."}
        ],
        "contact": {"address": "700 Main St, Cambridge, MA 02139", "phone": "+1 (617) 555-0128", "email": "partnerships@helixbio.com", "hours": "Mon–Fri: 8:30am–5:30pm EST"}
    },
    {
        "id": "site_glass_flux_state", "name": "Flux Distributed Cache",
        "tagline": "In-Memory Tiered Cache with NVMe Spillover & Microsecond Replication", "type": "database",
        "prefix": "fdc", "primary": "#080b14", "accent": "#818cf8", "accent_hover": "#6366f1",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Start In-Memory Cluster", "hero_sub": "Scale beyond single-node Redis limitations with multi-master sharding, active-active cross-datacenter replication, and automatic tiering.",
        "section_name": "Cache Architecture", "section_id": "cache_arch", "pill": False,
        "items": [
            {"title": "Sub-10 Microsecond Reads", "tag": "DRAM Optimized", "desc": "Bypass Linux network stack using io_uring and kernel-bypass DPDK drivers."},
            {"title": "Automatic NVMe Spillover", "tag": "10x Lower Cost", "desc": "Cold keys automatically migrate to high-speed PCIe Gen5 SSDs without read penalties."},
            {"title": "Conflict-Free Replicated Data", "tag": "CRDT Native", "desc": "Multi-master writes across three continents with mathematical convergence guarantees."},
            {"title": "Redis Protocol Transparent", "tag": "Zero Code Changes", "desc": "Drop-in compatibility with standard Redis clients (Jedis, redis-py, ioredis)."}
        ],
        "contact": {"address": "222 S Riverside Plaza, Chicago, IL 60606", "phone": "+1 (312) 555-0195", "email": "infra@fluxcache.io", "hours": "24/7 Infrastructure NOC"}
    },
    {
        "id": "site_glass_strata_observability", "name": "Strata Kernel Observability",
        "tagline": "Distributed Tracing, eBPF CPU Profiling & AI Log Anomaly Detection", "type": "cloud",
        "prefix": "sko", "primary": "#080b14", "accent": "#38bdf8", "accent_hover": "#0ea5e9",
        "surface": "#0f172a", "heading_font": "Space Grotesk", "body_font": "Inter",
        "cta": "Connect Kubernetes Cluster", "hero_sub": "Understand exact microservice latencies and kernel bottlenecks without adding manual code spans or logging decorators.",
        "section_name": "Observability Stack", "section_id": "stack_modules", "pill": False,
        "items": [
            {"title": "Continuous CPU Flamegraphs", "tag": "eBPF Sampling", "desc": "Pinpoint hot functions down to specific lines of Go, Rust, Java, and C++ source code."},
            {"title": "Zero-Instrument Distributed Trace", "tag": "Kernel Level", "desc": "Trace HTTP, gRPC, and SQL calls across pod networks without SDK modifications."},
            {"title": "Neural Log Clustering", "tag": "Noise Suppression", "desc": "Compress millions of repetitive log lines into actionable root-cause incident summaries."},
            {"title": "Automated SLO Error Budgets", "tag": "Alert Pager", "desc": "Track multi-window burn rates and trigger emergency rollbacks before SLAs breach."}
        ],
        "contact": {"address": "55 2nd St, Suite 1700, San Francisco, CA 94105", "phone": "+1 (415) 555-0149", "email": "telemetry@strataobservability.com", "hours": "Mon–Fri: 8am–6pm PST"}
    },

    # ── 3. Neo-Brutalist & High-Contrast Indie Archetype (17) ────────────────────────
    {
        "id": "site_brutal_hackers_hub", "name": "Hackers & Founders",
        "tagline": "Anti-Corporate Indie Maker Incubator & Micro-Grant Collective", "type": "community",
        "prefix": "hfh", "primary": "#ffffff", "accent": "#fbbf24", "accent_hover": "#f59e0b",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Submit Your Project", "hero_sub": "No pitch decks. No vanity metrics. No board seats. We give $25k micro-grants to solo developers building profitable software.",
        "section_name": "Grant Criteria", "section_id": "criteria", "pill": False,
        "items": [
            {"title": "Shipped Working Software", "tag": "Rule #1", "desc": "You must have a deployed URL that real humans can use with functional authentication and payments."},
            {"title": "Zero Vanity Slide Decks", "tag": "Rule #2", "desc": "We evaluate GitHub commits, terminal demos, and customer reviews — not 40-page investor PDFs."},
            {"title": "Non-Dilutive Cash Grants", "tag": "100% Yours", "desc": "We take 0% equity. We believe sustainable software businesses should belong entirely to their creators."},
            {"title": "Private Maker Community", "tag": "500+ Alumni", "desc": "Direct Telegram access to bootstrapped founders generating $10k to $150k monthly recurring revenue."}
        ],
        "contact": {"address": "88 Colin P Kelly Jr St, San Francisco, CA 94107", "phone": "+1 (415) 555-0131", "email": "grants@hackersfounders.co", "hours": "Always Async"}
    },
    {
        "id": "site_brutal_zero_audit", "name": "ZeroDay Bounty Hub",
        "tagline": "Uncensored Web3 Vulnerability Disclosure & Smart Contract Bounties", "type": "cybersecurity",
        "prefix": "zbh", "primary": "#ffffff", "accent": "#ef4444", "accent_hover": "#dc2626",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Explore Bounties", "hero_sub": "Connecting elite security researchers with DeFi protocols. Guaranteed payouts held in automated cryptographic escrow.",
        "section_name": "Active Bounties", "section_id": "bounties", "pill": False,
        "items": [
            {"title": "Arbitrum Bridge Exploit", "tag": "$2,500,000 Payout", "desc": "Critical vulnerability bounty for unauthorized L1-to-L2 message forgery or token withdrawal."},
            {"title": "Solana AMM Math Error", "tag": "$1,000,000 Payout", "desc": "Flaw resulting in pool liquidity draining or rounding error amplification under stress."},
            {"title": "Cosmos IBC Packet Poison", "tag": "$750,000 Payout", "desc": "Inter-blockchain communication state corruption or validator consensus halt vector."},
            {"title": "ZK-SNARK Verifier Soundness", "tag": "$1,500,000 Payout", "desc": "Proof forgery vulnerability allowing invalid state witness generation on Ethereum."}
        ],
        "contact": {"address": "Kryptostrasse 4, 8001 Zürich, Switzerland", "phone": "+41 44 211 0090", "email": "pgp-keys@zerodaybounty.org", "hours": "Decentralized 24/7"}
    },
    {
        "id": "site_brutal_git_forge", "name": "GitForge P2P Hub",
        "tagline": "Peer-to-Peer Git Hosting Without Corporate Spying or AI Scraping", "type": "developer",
        "prefix": "gfp", "primary": "#ffffff", "accent": "#22c55e", "accent_hover": "#16a34a",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Host Free Repo", "hero_sub": "Host git repositories over libp2p. Cryptographically signed commits, zero trackers, and zero training on your private codebase.",
        "section_name": "Forge Pillars", "section_id": "pillars", "pill": False,
        "items": [
            {"title": "End-to-End Encrypted Git", "tag": "Zero Knowledge", "desc": "Your code is encrypted client-side with your SSH key before reaching any peer storage nodes."},
            {"title": "Zero AI Model Scraping", "tag": "Guaranteed", "desc": "Our terms mathematically prevent automated scrapers and model training robots from reading code."},
            {"title": "Offline-First Issue Tracker", "tag": "Git Embedded", "desc": "Issues, pull requests, and discussions live directly inside your git tree as signed commits."},
            {"title": "Self-Hostable Micro-Daemon", "tag": "Single Binary", "desc": "Run a full GitForge seed node on any $5 Raspberry Pi or VPS with one terminal command."}
        ],
        "contact": {"address": "St. Marks Pl 14, New York, NY 10003", "phone": "+1 (212) 555-0185", "email": "nodes@gitforge.p2p", "hours": "Distributed Network"}
    },
    {
        "id": "site_brutal_raw_goods", "name": "Raw Goods Heavyweight",
        "tagline": "25oz Unsanforized Selvedge Denim & Indestructible Work Jackets", "type": "apparel",
        "prefix": "rgh", "primary": "#ffffff", "accent": "#3b82f6", "accent_hover": "#2563eb",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "View Denim Drops", "hero_sub": "Woven on vintage Toyoda shuttle looms in Kojima. Stiff, heavy, and built to survive decades of honest workshop wear.",
        "section_name": "Heavy Iron Collection", "section_id": "denim_pieces", "pill": False,
        "items": [
            {"title": "25oz Beast Selvedge Jean", "tag": "Kojima Mill", "desc": "The heaviest denim in the world. Solid copper rivets, herringbone pocket bags, and pink selvedge ID."},
            {"title": "Type III Chore Coat", "tag": "18oz Waxed Duck", "desc": "Paraffin waxed shelter tent canvas with blanket lining and solid brass doughnut buttons."},
            {"title": "Heavy Slub Flannel Shirt", "tag": "450 GSM", "desc": "Extra-thick double gauze cotton woven with uneven slub yarns for maximum winter warmth."},
            {"title": "Horsehide Engineer Boot", "tag": "Hand-Welted", "desc": "Horween Chromexcel leather with double leather midsoles and Cat's Paw rubber half soles."}
        ],
        "contact": {"address": "124 Kojima Denim St, Kurashiki, Okayama 711-0913", "phone": "+81 86 473 1100", "email": "workshop@rawgoods.jp", "hours": "Wed–Sun: 11am–6pm JST"}
    },
    {
        "id": "site_brutal_terminal_fm", "name": "Terminal FM Radio",
        "tagline": "Pirate Underground Electronic Radio Broadcast from Shipping Containers", "type": "music",
        "prefix": "tfm", "primary": "#ffffff", "accent": "#eab308", "accent_hover": "#ca8a04",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Tune In Live (320k)", "hero_sub": "Broadcasting 24/7 uncompressed FLAC audio from an offshore rusted container. Industrial techno, jungle, ambient drone, and footwork.",
        "section_name": "Resident Shows", "section_id": "shows", "pill": False,
        "items": [
            {"title": "Concrete & Rebar", "tag": "Midnight–3am UTC", "desc": "Raw analog modular techno, distorted drum machines, and heavy tape saturation with DJ Kilo."},
            {"title": "Submerged Frequencies", "tag": "Wednesdays 8pm", "desc": "Deep half-step dubstep, 140bpm sub-bass excursions, and rare acetate dubplates."},
            {"title": "Neural Ambient Drift", "tag": "Sunday Dawn", "desc": "Four hours of drifting generative drone, tape loops, and field recordings from abandoned silos."},
            {"title": "Amen Break Archives", "tag": "Fridays 10pm", "desc": "High-velocity vintage 1994 jungle pressed direct from original London white labels."}
        ],
        "contact": {"address": "Pier 48, San Francisco, CA 94158", "phone": "+1 (415) 555-0162", "email": "studio@terminal.fm", "hours": "24/7 Live Stream"}
    },
    {
        "id": "site_brutal_bolt_shipping", "name": "Bolt Global Freight",
        "tagline": "High-Velocity Sea & Air Freight Logistics with Zero Intermediary Markups", "type": "logistics",
        "prefix": "bgf", "primary": "#ffffff", "accent": "#f97316", "accent_hover": "#ea580c",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Get Instant Quote", "hero_sub": "Book 40ft high-cube containers and air cargo in 60 seconds. Real-time GPS vessel tracking and automated customs filings.",
        "section_name": "Freight Routes", "section_id": "routes", "pill": False,
        "items": [
            {"title": "Transpacific Express", "tag": "Shanghai to LA", "desc": "Guaranteed 11-day port-to-port ocean transit with priority berthing and zero chassis delays."},
            {"title": "Transatlantic Priority", "tag": "Rotterdam to NY", "desc": "Weekly container vessels connecting European industrial hubs directly to the US East Coast."},
            {"title": "Dedicated Air Cargo Charter", "tag": "747-800 Freighter", "desc": "Full charter capability for urgent automotive parts, high-tech hardware, and aerospace cargo."},
            {"title": "Automated Customs Clearance", "tag": "Duty API", "desc": "Automated HTS code classification and digital paperwork submission to US Customs in seconds."}
        ],
        "contact": {"address": "111 Harbor Blvd, San Pedro, CA 90731", "phone": "+1 (310) 555-0198", "email": "dispatch@boltshipping.com", "hours": "24/7 Port Logistics"}
    },
    {
        "id": "site_brutal_stack_overflow_alt", "name": "DevPulse Forum",
        "tagline": "Pure Text Developer Discussions with Zero AI Hallucinations or Fluff", "type": "community",
        "prefix": "dpf", "primary": "#ffffff", "accent": "#10b981", "accent_hover": "#059669",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Join Community", "hero_sub": "Verified senior engineers discussing distributed systems, database internals, and Linux kernel hacking without corporate spam.",
        "section_name": "Featured Channels", "section_id": "channels", "pill": False,
        "items": [
            {"title": "#database-internals", "tag": "12k Engineers", "desc": "Deep-dives into LSM-trees, B-tree write amplification, and WAL durability algorithms."},
            {"title": "#systems-rust-zig", "tag": "8k Engineers", "desc": "Memory-safe systems programming, manual allocators, and WebAssembly compilation tricks."},
            {"title": "#frontend-craft", "tag": "15k Engineers", "desc": "Vanilla CSS performance, zero-runtime CSS tokens, and high-frequency DOM canvas rendering."},
            {"title": "#hardware-fpga", "tag": "4k Engineers", "desc": "Verilog synthesis, PCIe interface design, and custom accelerator design for edge inference."}
        ],
        "contact": {"address": "742 Evergreen Terr, Portland, OR 97201", "phone": "+1 (503) 555-0137", "email": "moderators@devpulse.org", "hours": "Decentralized Forum"}
    },
    {
        "id": "site_brutal_vault_defi", "name": "VaultX Yield Protocol",
        "tagline": "Non-Custodial Algorithmic Yield Optimization with Verifiable On-Chain Solvency", "type": "fintech",
        "prefix": "vyp", "primary": "#ffffff", "accent": "#8b5cf6", "accent_hover": "#7c3aed",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Deposit & Earn Yield", "hero_sub": "Automated collateral rebalancing across verified lending pools. Zero hidden performance fees and open-source smart contracts.",
        "section_name": "Vault Strategies", "section_id": "vaults", "pill": False,
        "items": [
            {"title": "USDC Treasury Prime", "tag": "5.82% Net APY", "desc": "Backed strictly by short-duration US Treasury bills held with regulated institutional custodians."},
            {"title": "ETH Staking Optimizer", "tag": "4.15% Net APY", "desc": "Automated validator selection balancing execution layer MEV rewards with slashing insurance."},
            {"title": "Neutral Basis Capture", "tag": "8.40% Net APY", "desc": "Delta-neutral spot-futures funding rate arbitrage across decentralized perpetual venues."},
            {"title": "Liquid Restaking Vault", "tag": "6.95% Net APY", "desc": "Stake ETH while simultaneously securing AVS oracle and bridge middleware networks."}
        ],
        "contact": {"address": "Zug Dammstrasse 19, 6300 Zug, Switzerland", "phone": "+41 41 555 0110", "email": "protocol@vaultx.fi", "hours": "24/7 Smart Contracts"}
    },
    {
        "id": "site_brutal_brutalist_print", "name": "Heavy Ink Risograph",
        "tagline": "Soy-Ink Risograph Printing, Experimental Zines & Concrete Binding", "type": "printing",
        "prefix": "hir", "primary": "#ffffff", "accent": "#ec4899", "accent_hover": "#db2777",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Order Print Run", "hero_sub": "Fluro pink, sunflower yellow, and federal blue rice-bran inks printed on uncoated French Paper stock. Real tactile halftone dots.",
        "section_name": "Print Formats", "section_id": "print_formats", "pill": False,
        "items": [
            {"title": "A3 Cultural Posters", "tag": "4-Color Riso", "desc": "Vibrant fluro spot colors with natural drum registration misalignments for raw visual punch."},
            {"title": "Saddle-Stitched Zines", "tag": "Edition of 200", "desc": "Heavy cover card with copper staple binding and hand-numbered colophon stamps."},
            {"title": "Architectural Booklets", "tag": "Cold Glue Spine", "desc": "Lay-flat exposed thread binding showcasing dense typographic layouts and plans."},
            {"title": "Custom Postcard Packs", "tag": "Duplexed 350 GSM", "desc": "Double-thick textured pulp stock with tactile letterpress emboss detail."}
        ],
        "contact": {"address": "142 Shoreditch High St, London E1 6JE, UK", "phone": "+44 20 7739 0188", "email": "print@heavyink.co.uk", "hours": "Tue–Sat: 10am–6pm GMT"}
    },
    {
        "id": "site_brutal_circuit_labs", "name": "Circuit Hackers Lab",
        "tagline": "Open Hardware Breadboards, Modular Synth Kits & Logic Analyzers", "type": "hardware",
        "prefix": "chl", "primary": "#ffffff", "accent": "#06b6d4", "accent_hover": "#0891b2",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Buy Hardware Kit", "hero_sub": "Designed for students, hackers, and audio engineers. Through-hole components you can actually solder with a hot iron.",
        "section_name": "Hardware Kits", "section_id": "hardware_kits", "pill": False,
        "items": [
            {"title": "Eurorack VCO Module Kit", "tag": "DIY Solder Kit", "desc": "Analog triangle core oscillator with hard sync, linear FM, and custom aluminum faceplate."},
            {"title": "16-Channel Logic Analyzer", "tag": "100 MHz USB", "desc": "Open-source USB logic analyzer compatible with Sigrok and PulseView software."},
            {"title": "Breadboard Power Regulator", "tag": "Dual Rail", "desc": "Clean low-noise +/-12V and 5V power supply with resettable PTC fuse protection."},
            {"title": "Mechanical Keypad Kit", "tag": "Hot-Swap", "desc": "9-key programmable macro pad with Raspberry Pi RP2040 micro-controller and QMK firmware."}
        ],
        "contact": {"address": "525 S Hewitt St, Los Angeles, CA 90013", "phone": "+1 (213) 555-0146", "email": "circuits@hackerslab.tech", "hours": "Mon–Fri: 10am–7pm PST"}
    },
    {
        "id": "site_brutal_kiosk_coffee", "name": "Kiosk Nitro Coffee",
        "tagline": "Ultra-Concentrated Nitrogen Cold Brew Poured from Concrete Pedestals", "type": "coffee",
        "prefix": "knc", "primary": "#ffffff", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Find Kiosk Location", "hero_sub": "No syrups. No cow milk. Single-origin natural process Ethiopian Yirgacheffe steeped for 24 hours and charged with pure nitrogen.",
        "section_name": "Tap Offerings", "section_id": "tap_menu", "pill": False,
        "items": [
            {"title": "Nitro Cold Brew Draft", "tag": "$5.00 / Pint", "desc": "Poured like Guinness with a dense creamy foam head and intense notes of blueberry and dark cocoa."},
            {"title": "Double Ristretto Espresso", "tag": "$3.50", "desc": "Short 1:1.5 extraction bringing out explosive acidity, floral bergamot, and cane sugar sweetness."},
            {"title": "Oat Flat White", "tag": "$4.50", "desc": "Steamed Minor Figures organic oat milk poured over double shot washed Colombian Huila."},
            {"title": "Cascara Sparkling Tea", "tag": "$4.00", "desc": "Brewed dried coffee cherry tea carbonated on tap with a slice of organic lemon."}
        ],
        "contact": {"address": "348 Bowery, New York, NY 10012", "phone": "+1 (212) 555-0122", "email": "coffee@kiosknitro.com", "hours": "Daily: 7am–4pm EST"}
    },
    {
        "id": "site_brutal_rebel_agency", "name": "Rebel Strategy Collective",
        "tagline": "Defiant Brand Positioning & Anti-Corporate Advertising Campaigns", "type": "agency",
        "prefix": "rsc", "primary": "#ffffff", "accent": "#ef4444", "accent_hover": "#dc2626",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Start a Riot", "hero_sub": "We kill boring corporate buzzwords. Bold guerrilla campaigns, billboard takeovers, and cultural activations that generate genuine outrage and loyalty.",
        "section_name": "Past Campaigns", "section_id": "campaigns", "pill": False,
        "items": [
            {"title": "The Billionaire Tax Billboard", "tag": "Guerrilla Out-of-Home", "desc": "Subway takeover in Manhattan sparking international television debate and 14M organic impressions."},
            {"title": "Dump Your Bank Campaign", "tag": "Digital Video", "desc": "Viral satirical commercial leading to 45,000 credit union account openings in 14 days."},
            {"title": "Unfiltered Food Manifesto", "tag": "Brand Identity", "desc": "Complete visual rebrand for organic snack maker rejecting artificial greenwashing buzzwords."},
            {"title": "Privacy Is Non-Negotiable", "tag": "National PR", "desc": "Privacy hardware product launch that sold out entire initial run of 100,000 devices."}
        ],
        "contact": {"address": "620 SW 5th Ave, Portland, OR 97204", "phone": "+1 (503) 555-0191", "email": "riot@rebelstrategy.co", "hours": "Mon–Fri: 9am–6pm PST"}
    },
    {
        "id": "site_brutal_drop_sneakers", "name": "DropDead Kicks",
        "tagline": "Physical NFC Authenticated Deadstock Sneaker Vault & Pop-Up Drops", "type": "ecommerce",
        "prefix": "ddk", "primary": "#ffffff", "accent": "#84cc16", "accent_hover": "#65a30d",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Join Next Drop", "hero_sub": "Zero counterfeit pairs. Every shoe contains an embedded cryptographic microchip verified against on-chain provenance records.",
        "section_name": "Current Drops", "section_id": "sneaker_drops", "pill": False,
        "items": [
            {"title": "Air Jordan 1 '85 Chicago", "tag": "DS Condition", "desc": "Original 1985 factory specifications with thick Italian leather cut and vintage yellowed midsole."},
            {"title": "Dunk Low SB 'Paris'", "tag": "Ultra Rare (1/202)", "desc": "Canvas uppers featuring original artwork by French painter Bernard Buffet. Pristine condition."},
            {"title": "Travis Scott Fragment 1", "tag": "Deadstock", "desc": "Reverse Swoosh detailing with military blue heel stamp and verified cryptographic NFC tag."},
            {"title": "Yeezy 750 Triple Black", "tag": "OG Box Included", "desc": "Premium pigskin suede high-top with full-length Boost cushioning and original sales receipt."}
        ],
        "contact": {"address": "451 N Fairfax Ave, Los Angeles, CA 90036", "phone": "+1 (323) 555-0174", "email": "drops@dropdeadkicks.la", "hours": "Drop Days Only (Announced on IG)"}
    },
    {
        "id": "site_brutal_distro_zine", "name": "Distro Independent Literature",
        "tagline": "Radical Underground Zines, Screenprinted Pamphlets & Anarchist Essays", "type": "publishing",
        "prefix": "dil", "primary": "#ffffff", "accent": "#e11d48", "accent_hover": "#be123c",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Order Bundle ($20)", "hero_sub": "Printed in basements on recycled newsprint. Essays on mutual aid, open-source technology, tenant organizing, and DIY music scenes.",
        "section_name": "Zine Catalog", "section_id": "zines", "pill": False,
        "items": [
            {"title": "Autonomous Tech Infrastructure", "tag": "Issue 03", "desc": "A step-by-step guide to setting up community mesh Wi-Fi and solar-powered server nodes."},
            {"title": "Tenant Defense Handbook", "tag": "Manual", "desc": "Legal tactics, strike organizing strategies, and eviction defense manuals for urban tenants."},
            {"title": "History of Pirate FM Radio", "tag": "Illustrated Zine", "desc": "Documenting UK pirate radio towers from 1988 to the digital transition."},
            {"title": "The Breadboard Manifesto", "tag": "Hardware Essay", "desc": "Why open-source hardware is the last remaining bastion against digital enclosure."}
        ],
        "contact": {"address": "Box 404, 131 E 10th St, New York, NY 10003", "phone": "+1 (212) 555-0166", "email": "mailorder@distrozine.org", "hours": "Mail Order Only"}
    },
    {
        "id": "site_brutal_boulder_gym", "name": "Gravity Bouldering Lab",
        "tagline": "Competition Bouldering Facility with Unforgiving Concrete Angles", "type": "fitness",
        "prefix": "gbl", "primary": "#ffffff", "accent": "#f59e0b", "accent_hover": "#d97706",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Get Day Pass ($22)", "hero_sub": "No gym machines. No juice bars. 15,000 square feet of steep 45-degree overhanging wooden boards, campus rungs, and competition problems.",
        "section_name": "Training Zones", "section_id": "training_zones", "pill": False,
        "items": [
            {"title": "45-Degree Kilter Board", "tag": "Bluetooth LED", "desc": "Over 50,000 community boulders illuminated by LEDs with adjustable angle from 30 to 70 degrees."},
            {"title": "MoonBoard 2016 Setup", "tag": "Standard Holds", "desc": "The benchmark test of pure finger power and body tension. Benchmark problems from V4 to V14."},
            {"title": "Campus Board & Lattice Bar", "tag": "Contact Strength", "desc": "Wooden campus rungs, pinch blocks, and instrumented load-cell finger testing bars."},
            {"title": "Competition Boulder Wall", "tag": "Reset Weekly", "desc": "Dual-density fiberglass macro holds set by certified IFSC national routesetters."}
        ],
        "contact": {"address": "1200 Industrial Way, Denver, CO 80204", "phone": "+1 (303) 555-0153", "email": "climb@gravityboulderlab.com", "hours": "Daily: 6am–11pm MST"}
    },
    {
        "id": "site_brutal_garage_tunes", "name": "Garage Vinyl Exchange",
        "tagline": "Rare Secondhand Vinyl, Japanese Pressings & Technics SL-1200 Repair", "type": "music",
        "prefix": "gve", "primary": "#ffffff", "accent": "#0ea5e9", "accent_hover": "#0284c7",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Browse Digs", "hero_sub": "Over 25,000 original pressings in stock. Full audio test benches with Sennheiser headphones and calibrated direct-drive turntables.",
        "section_name": "New Arrivals", "section_id": "arrivals", "pill": False,
        "items": [
            {"title": "Miles Davis - Kind of Blue (1959)", "tag": "Columbia 6-Eye Mono", "desc": "Original deep groove mono pressing with pristine glossy vinyl and original sleeve."},
            {"title": "Kraftwerk - Trans-Europe Express", "tag": "Kling Klang German Press", "desc": "Rare 1977 Düsseldorf pressing with embossed cover and electronic poster insert."},
            {"title": "Aphex Twin - Selected Ambient Works", "tag": "Apollo Original (1992)", "desc": "Original Belgian double vinyl release mastered direct from original DAT tapes."},
            {"title": "Technics SL-1200MK2 Overhaul", "tag": "Service Service", "desc": "Complete pitch calibration, new RCA cables, ground wire elimination, and spindle lubrication."}
        ],
        "contact": {"address": "1515 N Milwaukee Ave, Chicago, IL 60622", "phone": "+1 (773) 555-0181", "email": "digging@garagerecords.com", "hours": "Mon–Sat: 11am–8pm CST"}
    },
    {
        "id": "site_brutal_forge_hardware", "name": "Ironclad Mechanical Keys",
        "tagline": "Solid Brass Case Custom Keyboards & Hand-Lubricated Linear Switches", "type": "hardware",
        "prefix": "imk", "primary": "#ffffff", "accent": "#d946ef", "accent_hover": "#c026d3",
        "surface": "#ffffff", "heading_font": "Space Grotesk", "body_font": "Space Grotesk",
        "cta": "Join Group Buy", "hero_sub": "3.5kg CNC-machined solid brass keyboards. Gasket-mounted plates, custom FR4 PCBs, and thick PBT dye-sub keycaps.",
        "section_name": "Keyboard Boards", "section_id": "keyboards", "pill": False,
        "items": [
            {"title": "Ironclad 65 Heavy Brass", "tag": "3.8kg Fully Built", "desc": "Solid brass base with mirror-polished PVD coating and acoustic poron gasket dampening."},
            {"title": "Hand-Lubricated Oil Kings", "tag": "Linear 55g", "desc": "Gateron Oil King linear switches hand-brushed with Krytox 205g0 and filmed with 0.15mm TX films."},
            {"title": "Doubleshot PBT Industrial Keycaps", "tag": "Cherry Profile", "desc": "1.5mm thick doubleshot PBT plastic with crisp legends that will never shine or wear down."},
            {"title": "Coiled Aviator USB-C Cable", "tag": "Hand-Sleeved", "desc": "Double-sleeved paracord and Techflex cable with 4-pin quick-disconnect GX16 aviator connector."}
        ],
        "contact": {"address": "401 Terry Ave N, Seattle, WA 98109", "phone": "+1 (206) 555-0118", "email": "builds@ironcladkeys.com", "hours": "Mon–Fri: 9am–5pm PST"}
    },

    # ── 4. Luxury Minimalist & Architectural Archetype (17) ──────────────────────────
    {
        "id": "site_lux_nordic_arch", "name": "Atelier Nord Architects",
        "tagline": "Sustainable Timber Residential Pavilions Overlooking Norwegian Fjords", "type": "architecture",
        "prefix": "ana", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "View Monograph", "hero_sub": "Harmonizing raw Nordic pine, local granite bedrock, and panoramic thermal glass to create timeless, net-zero residential structures.",
        "section_name": "Selected Architecture", "section_id": "projects", "pill": False,
        "items": [
            {"title": "Fjord Villa Sognefjord", "tag": "Completed 2024", "desc": "Cantilevered mass-timber pavilion resting on natural bedrock with floor-to-ceiling fjord views."},
            {"title": "Alpine Retreat Geilo", "tag": "Passive House", "desc": "Triple-glazed timber chalet insulated with recycled wood fiber and heated by deep geothermal wells."},
            {"title": "Oslo Waterfront Gallery", "tag": "Civic Culture", "desc": "Public exhibition space featuring an undulating ceiling crafted from 4,000 curved spruce ribs."},
            {"title": "Lofoten Island Studio", "tag": "Artist Residency", "desc": "Compact storm-resistant studio constructed on stilts directly above Atlantic tidal swells."}
        ],
        "contact": {"address": "Nordic Way 42, 0150 Oslo, Norway", "phone": "+47 22 83 90 00", "email": "studio@ateliernord.arch", "hours": "Mon–Fri: 9am–5pm CET"}
    },
    {
        "id": "site_lux_michelin_eats", "name": "L'Étoile Reserve",
        "tagline": "Three Michelin-Starred French Gastronomy Celebrating Wild Alpine Forage", "type": "restaurant",
        "prefix": "ler", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Reserve Tasting Table", "hero_sub": "A 12-course blind tasting menu created each morning from ingredients foraged at dawn in the high meadows of Chamonix.",
        "section_name": "Tasting Sequences", "section_id": "menu_sequences", "pill": False,
        "items": [
            {"title": "Wild Alpine Morel Tartlet", "tag": "Course 02", "desc": "Spring morels sautéed in cultured pasture butter with aged Comté custard and spruce oil."},
            {"title": "Glacier Trout Confit", "tag": "Course 05", "desc": "Gently poached in brown butter with fermented wild sorrel sauce and smoked trout roe."},
            {"title": "Saddle of Roe Deer", "tag": "Course 08", "desc": "Roasted over juniper wood embers with wild blackberry reduction and celery root mousseline."},
            {"title": "Meadow Honey & Meadowsweet", "tag": "Course 11", "desc": "Alpine raw comb honey ice cream with meadowsweet blossom meringue and mountain mint granita."}
        ],
        "contact": {"address": "Route des Pècles 75, 74400 Chamonix-Mont-Blanc, France", "phone": "+33 4 50 53 00 12", "email": "reservations@letoilereserve.fr", "hours": "Dinner: Wed–Sun (Booking 60 Days Ahead)"}
    },
    {
        "id": "site_lux_aurum_wealth", "name": "Aurum Family Office",
        "tagline": "Multi-Generational Capital Preservation & Sovereign Asset Allocation", "type": "finance",
        "prefix": "afo", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Private Client Inquiry", "hero_sub": "Guiding 40 ultra-high-net-worth families across Zurich, London, and Singapore with fiduciary discretion and generational vision.",
        "section_name": "Fiduciary Practices", "section_id": "wealth_practices", "pill": False,
        "items": [
            {"title": "Sovereign Bond Allocation", "tag": "Capital Defense", "desc": "Direct investment in top-tier sovereign paper and inflation-protected infrastructure assets."},
            {"title": "Direct Venture Co-Investment", "tag": "Private Equity", "desc": "Exclusive access to primary lead investor allocations in frontier AI, biotech, and space tech."},
            {"title": "Generational Estate Trust Structuring", "tag": "Governance", "desc": "Cross-border trust architecture designed to maintain family liquidity across four generations."},
            {"title": "Physical Precious Metals Depository", "tag": "Swiss Vaults", "desc": "Allocated, audited physical gold bullion stored in private subterranean Alpine mountain vaults."}
        ],
        "contact": {"address": "Paradeplatz 8, 8001 Zürich, Switzerland", "phone": "+41 44 224 8000", "email": "partners@aurumfamilyoffice.ch", "hours": "Confidential Family Consultations"}
    },
    {
        "id": "site_lux_monolith_stone", "name": "Monolith Architectural Stone",
        "tagline": "Rare Calacatta Viola, Nero Marquina & Hand-Selected Italian Marble Slabs", "type": "stone",
        "prefix": "mas", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Inspect Slab Gallery", "hero_sub": "Extracted directly from private mountain quarries in Carrara and Verona. Continuous vein-matched bookmatched marble slabs.",
        "section_name": "Quarry Slabs", "section_id": "slabs", "pill": False,
        "items": [
            {"title": "Calacatta Viola Bookmatch", "tag": "Carrara Quarry", "desc": "Creamy white marble base with deep burgundy and plum veining for luxury statement islands."},
            {"title": "Nero Marquina Velvet Finish", "tag": "Basque Region", "desc": "Deepest pitch-black calcite with striking pure white lightning veins in honed matte finish."},
            {"title": "Travertino Navona Honed", "tag": "Tivoli Roman Quarry", "desc": "Warm bone-colored porous travertine selected for monumental interior cladding and baths."},
            {"title": "Verde Alpi Serpentine", "tag": "Aosta Valley", "desc": "Deep alpine emerald green marble with delicate crystalline veins for architectural tables."}
        ],
        "contact": {"address": "Via dei Marmi 12, 54033 Carrara MS, Italy", "phone": "+39 0585 842 100", "email": "slabs@monolithstone.it", "hours": "Trade Specifiers by Appointment"}
    },
    {
        "id": "site_lux_elysian_villas", "name": "Elysian Amalfi Estates",
        "tagline": "Private Clifftop Mediterranean Estates with Helipads & Private Sea Access", "type": "real_estate",
        "prefix": "eae", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "View Private Portfolio", "hero_sub": "Perched 200 meters above the Tyrrhenian Sea. Century-old lemon groves, heated infinity pools, and private yacht moorings in Positano.",
        "section_name": "Available Estates", "section_id": "estates", "pill": False,
        "items": [
            {"title": "Villa Bellavista, Positano", "tag": "€18,500,000", "desc": "7-bedroom cliffside sanctuary with private funicular down to private sea cove and boat house."},
            {"title": "Palazzo Di Ravello", "tag": "€24,000,000", "desc": "Historic 18th-century noble palazzo surrounded by 2 hectares of terraced gardens and olive trees."},
            {"title": "Villa Solaria, Capri", "tag": "€14,200,000", "desc": "Modernist whitewashed villa overlooking the Faraglioni rocks with private helicopter landing pad."},
            {"title": "Tenuta Conca dei Marini", "tag": "€9,800,000", "desc": "Restored coastal watchtower with 360-degree sea views, wine cellar, and separate guest lodge."}
        ],
        "contact": {"address": "Via Cristoforo Colombo 40, 84017 Positano SA, Italy", "phone": "+39 089 875 000", "email": "estates@elysianamalfi.com", "hours": "Confidential Buyer Representation"}
    },
    {
        "id": "site_lux_sovereign_aviation", "name": "Sovereign Private Aviation",
        "tagline": "Ultra-Long-Range Gulfstream G700 Charters with Private Customs Terminals", "type": "aviation",
        "prefix": "spa", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Book Private Flight", "hero_sub": "Non-stop London to Tokyo at Mach 0.90. Private staterooms, dedicated flight attendant service, and Michelin-tier catering.",
        "section_name": "Fleet Specifications", "section_id": "fleet", "pill": False,
        "items": [
            {"title": "Gulfstream G700 Fleet", "tag": "7,750 NM Range", "desc": "Up to 5 living areas with master suite, private shower, circadian lighting, and 100% fresh air."},
            {"title": "Bombardier Global 7500", "tag": "Mach 0.925 Max", "desc": "Patented Nuage seating, full-size kitchen, and direct transpacific non-stop capability."},
            {"title": "Helicopter Executive Transfer", "tag": "AgustaWestland AW109", "desc": "Instant transfers from airport tarmac directly to central London, Manhattan, or Monaco heliports."},
            {"title": "24/7 Sovereign Flight Ops", "tag": "Global Permits", "desc": "Immediate flight clearance routing around turbulence and restricted airspace worldwide."}
        ],
        "contact": {"address": "Farnborough Airport, Hampshire GU14 6XA, UK", "phone": "+44 1252 555 010", "email": "charter@sovereignaviation.com", "hours": "24/7 Global Dispatch"}
    },
    {
        "id": "site_lux_reserve_vintage", "name": "Reserve Grand Crus",
        "tagline": "Bordeaux First Growths & Rare Single-Cask Scotch Whisky Provenance", "type": "wine",
        "prefix": "rgc", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Access Cellar Inventory", "hero_sub": "Direct domaine allocation bottles cellared in temperature-controlled underground limestone caves in Beaune and Bordeaux.",
        "section_name": "Cellar Reserves", "section_id": "cellar_reserves", "pill": False,
        "items": [
            {"title": "Château Latour 1982", "tag": "Pauillac Premier Cru", "desc": "Pristine level neck fill with verified provenance from private Bordeaux estate cellar."},
            {"title": "Domaine de la Romanée-Conti 2015", "tag": "Romanée-Conti", "desc": "Allocated wooden case with original serialized tamper-evident cryptographic seals."},
            {"title": "Macallan 50-Year Single Cask", "tag": "Sherry Oak Cask", "desc": "Bottled in custom Lalique crystal decanter. Rich dried fruits, peat smoke, and dark chocolate."},
            {"title": "Krug Clos d'Ambonnay 2002", "tag": "Blanc de Noirs", "desc": "Extremely rare 100% Pinot Noir Champagne from a tiny 0.68-hectare walled vineyard parcel."}
        ],
        "contact": {"address": "Place de la Bourse 15, 33000 Bordeaux, France", "phone": "+33 5 56 00 88 00", "email": "sommelier@reservegrandcru.fr", "hours": "Private Cellar Inquiries"}
    },
    {
        "id": "site_lux_paradis_resort", "name": "Paradis Maldivian Atoll",
        "tagline": "Private Coral Atoll Sanctuary with Dedicated Marine Biologists & Chefs", "type": "hospitality",
        "prefix": "pma", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Reserve Overwater Villa", "hero_sub": "A private coral atoll reserved for just 15 guest parties. Floor-to-ceiling glass floors over turquoise manta ray nurseries.",
        "section_name": "Atoll Residences", "section_id": "residences", "pill": False,
        "items": [
            {"title": "The Ocean Reserve Pavilion", "tag": "4-Bedroom Overwater", "desc": "Private 20-meter infinity pool, personal catamaran, and full-time butler and private chef."},
            {"title": "Sunset Water Villa", "tag": "Panoramic Lagoon", "desc": "Unobstructed western horizon views with direct private reef steps and overwater hammocks."},
            {"title": "Private Coral Reef Restoration", "tag": "Guided Experience", "desc": "Accompany resident marine biologists to transplant endangered Staghorn coral to the reef."},
            {"title": "Subterranean Wine Cellar", "tag": "5,000 Bottles", "desc": "Dine 6 meters below sea level surrounded by vintage Champagne and tropical marine life."}
        ],
        "contact": {"address": "Baa Atoll, Republic of Maldives", "phone": "+960 660 8800", "email": "concierge@paradisatoll.mv", "hours": "Seaplane Transfers from Velana (MLE)"}
    },
    {
        "id": "site_lux_vessel_yachts", "name": "Sovereign Naval Yachts",
        "tagline": "Custom 80-Meter Hydrogen-Hybrid Superyachts Engineered for Oceanic Exploration", "type": "marine",
        "prefix": "sny", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Request Commission Brief", "hero_sub": "Quiet zero-emission electric cruising across arctic sanctuaries. Ice-classed steel hulls designed by world-renowned naval architects.",
        "section_name": "Yacht Concepts", "section_id": "yachts", "pill": False,
        "items": [
            {"title": "Project Borealis (88m)", "tag": "Ice Class 1A", "desc": "Hydrogen fuel-cell hybrid propulsion with 6,500 NM range and certified helicopter hangar."},
            {"title": "Aura Catamaran (65m)", "tag": "Solar Integrated", "desc": "Wide-beam displacement catamaran with 400 sqm owner's deck and underwater observation pod."},
            {"title": "Transatlantic Tender (14m)", "tag": "Custom Carbon Fiber", "desc": "Twin 600hp outboards delivering 52 knots with luxury leather seating for 12 guests."},
            {"title": "Autonomous Submersible Bay", "tag": "3-Person Submarine", "desc": "Internal hydraulic moon pool launching research submarines down to 1,000 meters depth."}
        ],
        "contact": {"address": "Port Hercule, 98000 Monaco", "phone": "+377 97 98 00 00", "email": "naval@sovereignyachts.mc", "hours": "Monaco Yacht Show Exhibitor"}
    },
    {
        "id": "site_lux_chateau_vineyard", "name": "Château De Vence",
        "tagline": "Biodynamic Grand Cru Saint-Émilion Wine Estate Founded in 1742", "type": "wine",
        "prefix": "cdv", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Estate Allocations", "hero_sub": "Horse-plowed clay-limestone soils, native yeast fermentation, and aging in fine-grain French oak barrels in ancient Roman quarries.",
        "section_name": "Estate Vintages", "section_id": "vintages", "pill": False,
        "items": [
            {"title": "Grand Vin 2018", "tag": "Saint-Émilion Grand Cru", "desc": "85% Merlot, 15% Cabernet Franc. Intense black truffle, cassis, cedar, and velvety tannins."},
            {"title": "Le Pavillon Blanc 2020", "tag": "Old-Vine Sémillon", "desc": "Centenarian vines yielding rich white peach, beeswax, and flinty mineral precision."},
            {"title": "Cuvée Héritage 2016", "tag": "Magnum Only (300 Btls)", "desc": "Hand-sorted berry by berry with 24 months in 100% new Taransaud French oak."},
            {"title": "Private Harvest Experience", "tag": "Autumn Guest Stay", "desc": "Participate in early morning hand-picking followed by barrel tastings with the cellar master."}
        ],
        "contact": {"address": "33330 Saint-Émilion, Gironde, France", "phone": "+33 5 57 55 40 00", "email": "chateau@chateaudevence.fr", "hours": "Tastings by Advance Reservation"}
    },
    {
        "id": "site_lux_couture_tailor", "name": "Savile & Row Bespoke",
        "tagline": "Full-Canvas Hand-Stitched Bespoke Tailoring in Scottish Cashmere & Wool", "type": "fashion",
        "prefix": "srb", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Book Initial Fitting", "hero_sub": "A 60-hour handcraft process requiring three individual fittings. Every pattern is hand-drafted on brown paper strictly from your posture.",
        "section_name": "Bespoke Garments", "section_id": "garments", "pill": False,
        "items": [
            {"title": "Two-Piece Bespoke Suit", "tag": "60 Hours Handwork", "desc": "Floating horsehair canvas chest piece, hand-sewn buttonholes, and horn buttons."},
            {"title": "Double-Breasted Cashmere Overcoat", "tag": "Eschenbach Wool", "desc": "Heavyweight 600g Scottish cashmere with deep storm collar and silk cupro lining."},
            {"title": "Hand-Cut Evening Tuxedo", "tag": "Barathea Wool", "desc": "Midnight navy wool with pure silk grosgrain peak lapels and hand-corded trouser braid."},
            {"title": "Bespoke White Cotton Dress Shirt", "tag": "200/2 Sea Island", "desc": "Mother-of-pearl buttons, single-needle 22-stitch-per-inch side seams, and split yoke."}
        ],
        "contact": {"address": "14 Savile Row, Mayfair, London W1S 3JN, UK", "phone": "+44 20 7437 1200", "email": "tailoring@savileandrow.com", "hours": "Mon–Fri: 9:30am–5:30pm GMT"}
    },
    {
        "id": "site_lux_equine_stud", "name": "Valhalla Thoroughbred Stud",
        "tagline": "Championship Thoroughbred Breeding & Advanced Equine Hydrotherapy", "type": "equine",
        "prefix": "vts", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Inspect Stallions", "hero_sub": "Five generations of classic winners. Set across 500 acres of mineral-rich Kentucky bluegrass with veterinary diagnostic suites.",
        "section_name": "Stallion Roster", "section_id": "stallions", "pill": False,
        "items": [
            {"title": "Valhalla Sovereign", "tag": "Grade 1 Classic Winner", "desc": "By Galileo out of a Dubawi mare. Exceptional conformation, explosive acceleration, and deep stride."},
            {"title": "Northern Monarch", "tag": "Champion 2-Year-Old", "desc": "Unbeaten sprint sensation with proven early precocity and textbook biomechanical motion."},
            {"title": "Equine Hydrotherapy Center", "tag": "State-of-the-Art", "desc": "Chilled saltwater walking treadmill and subterranean equine swimming pool for zero-impact conditioning."},
            {"title": "Yearling Sales Consignment", "tag": "Keeneland September", "desc": "Full sales preparation including digital radiographic suites and cardiovascular echocardiograms."}
        ],
        "contact": {"address": "Old Frankfort Pike, Lexington, KY 40510", "phone": "+1 (859) 555-0187", "email": "bloodstock@valhallastud.com", "hours": "Breeders Welcome by Appointment"}
    },
    {
        "id": "site_lux_sanctuary_spa", "name": "Shizen Geothermal Onsen",
        "tagline": "Natural Geothermal Hot Springs, Hinoki Cedar Baths & Zen Meditation", "type": "wellness",
        "prefix": "sgo", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Reserve Sanctuary Suite", "hero_sub": "Nestled in the volcanic mist of Mount Yotei. Mineral-rich sulfur springs flowing at 42°C into handcrafted aromatic Hinoki timber baths.",
        "section_name": "Onsen Rituals", "section_id": "rituals", "pill": False,
        "items": [
            {"title": "Rotenburo Outdoor Bath", "tag": "Alpine Forest View", "desc": "Soak in volcanic mineral waters while snow falls through ancient bamboo canopies."},
            {"title": "Private Hinoki Timber Suite", "tag": "300-Year Cedar", "desc": "Dedicated private bath room crafted from Japanese cypress with natural cedar oils."},
            {"title": "Shiatsu & Herbal Compress", "tag": "90-Minute Ritual", "desc": "Deep meridian acupressure therapy combined with steamed Yomogi mugwort herbal compresses."},
            {"title": "Seasonal Kaiseki Dining", "tag": "10 Courses", "desc": "Hokkaido scallops, snow crab, and mountain root vegetables served in your private tatami quarters."}
        ],
        "contact": {"address": "Niseko-cho, Abuta-gun, Hokkaido 048-1511, Japan", "phone": "+81 136 58 2000", "email": "stay@shizenonsen.jp", "hours": "Year-Round Alpine Retreat"}
    },
    {
        "id": "site_lux_heritage_diamonds", "name": "Maison Althoff Jewels",
        "tagline": "D-Color Flawless Type IIa Diamonds & Platinum High Jewelry Creations", "type": "jewelry",
        "prefix": "maj", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "View High Jewelry", "hero_sub": "Type IIa diamonds representing the top 1% of optical purity in the world. Set exclusively in hand-pulled platinum wire mounts.",
        "section_name": "Jewelry Creations", "section_id": "creations", "pill": False,
        "items": [
            {"title": "The Polaris Ring", "tag": "12.04 Carats (D/FL)", "desc": "Flawless emerald-cut diamond with custom tapered baguette shoulder side stones in platinum."},
            {"title": "Aurora Sapphire Necklace", "tag": "Royal Blue Kashmir", "desc": "38-carat unheated Kashmir sapphire surrounded by a cascade of marquise-cut diamonds."},
            {"title": "Colombian Emerald Suite", "tag": "Muzo Mine Origin", "desc": "Vivid green Colombian emerald earrings exhibiting natural garden inclusions with zero oil enhancement."},
            {"title": "Bespoke Bridal Commission", "tag": "Master Jeweler", "desc": "Collaborate directly with our master gemologist to source rare rough stones cut to personal proportion."}
        ],
        "contact": {"address": "Place Vendôme 26, 75001 Paris, France", "phone": "+33 1 42 61 90 00", "email": "atelier@maisonalthoff.com", "hours": "Private Salon Appointments Only"}
    },
    {
        "id": "site_lux_privat_concierge", "name": "Kronos Global Concierge",
        "tagline": "Bespoke Private Client Logistics, Fine Art Procurement & Island Buyouts", "type": "concierge",
        "prefix": "kgc", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Membership Invitation", "hero_sub": "Serving 100 global families with absolute confidentiality. Sourcing sold-out operatic galas, private air charters, and security details.",
        "section_name": "Concierge Services", "section_id": "services", "pill": False,
        "items": [
            {"title": "Private Island Buyouts", "tag": "Complete Seclusion", "desc": "Full staff, private security perimeters, and dedicated seaplanes for family gatherings."},
            {"title": "Blue-Chip Art Procurement", "tag": "Auction House Access", "desc": "Confidential bidding representation at Sotheby's and Christie's evening auctions in London and NY."},
            {"title": "VIP Formula 1 Paddock Access", "tag": "Monaco & Singapore", "desc": "Yacht berths and team garage access for the Monaco Grand Prix and Singapore night race."},
            {"title": "Close Protection Logistics", "tag": "Former Military", "desc": "Unobtrusive close protection officers and armored vehicle convoys worldwide."}
        ],
        "contact": {"address": "Berkeley Square 20, Mayfair, London W1J 6EQ, UK", "phone": "+44 20 7499 5000", "email": "membership@kronosconcierge.com", "hours": "24/7 Dedicated Client Desks"}
    },
    {
        "id": "site_lux_penthouse_manhattan", "name": "The Tower Penthouse Collection",
        "tagline": "Full-Floor Manhattan Residences with 14-Foot Ceilings & 360-Degree Vistas", "type": "real_estate",
        "prefix": "tpc", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Schedule Private Tour", "hero_sub": "Occupying levels 80 through 96 above Central Park. Private key-lock elevators, custom Boffi kitchens, and panoramic corner master suites.",
        "section_name": "Penthouse Layouts", "section_id": "layouts", "pill": False,
        "items": [
            {"title": "Penthouse 92 (Full Floor)", "tag": "8,255 Sq Ft", "desc": "5 bedrooms, 7.5 baths with 360-degree views of Central Park, the Hudson River, and the Atlantic Ocean."},
            {"title": "Duplex Sky Residence", "tag": "11,000 Sq Ft", "desc": "Double-height 28-foot living gallery with sculptural bronze staircase and private indoor plunge pool."},
            {"title": "The Park Suite 84", "tag": "4,400 Sq Ft", "desc": "Direct Central Park frontage with corner dining salon and solid Calacatta marble fireplace."},
            {"title": "Building Wellness Club", "tag": "Residents Only", "desc": "75-foot heated lap pool, private dining room with Michelin-starred catering, and cinema screening room."}
        ],
        "contact": {"address": "111 W 57th St, New York, NY 10019", "phone": "+1 (212) 555-0105", "email": "sales@thetowercollection.nyc", "hours": "By Verified Financial Prequalification"}
    },
    {
        "id": "site_lux_estate_sculpture", "name": "Monumental Bronze Foundry",
        "tagline": "Lost-Wax Monumental Bronze Sculptures Cast for Private Palaces & Parks", "type": "sculpture",
        "prefix": "mbf", "primary": "#121316", "accent": "#d97706", "accent_hover": "#b45309",
        "surface": "#1c1e24", "heading_font": "Cinzel", "body_font": "Inter",
        "cta": "Commission Monument", "hero_sub": "Pouring 3 tons of molten bronze in a single heat. Continuing the monumental lost-wax casting traditions of 19th-century French masters.",
        "section_name": "Monumental Works", "section_id": "sculptures", "pill": False,
        "items": [
            {"title": "Equestrian Bronze (5m)", "tag": "Lost-Wax Casting", "desc": "Full-size heroic equestrian monument patinated with rich verdigris and liver-of-sulfur tones."},
            {"title": "Abstract Winged Form", "tag": "Polished Bronze", "desc": "Aerodynamic bronze sculpture with mirror-polished highlights and dark patinated recesses."},
            {"title": "Monumental Park Fountain", "tag": "Bronze & Granite", "desc": "Multi-tier water fountain with mythological chimera spouts hand-finished in red bronze."},
            {"title": "Private Estate Gates", "tag": "Hand-Forged Bronze", "desc": "Architectural grand entry gates with cast bas-relief panels and concealed motorized hinges."}
        ],
        "contact": {"address": "12 Quai de la Rapée, 75012 Paris, France", "phone": "+33 1 43 43 00 11", "email": "fonderie@monumentalbronze.fr", "hours": "Atelier Visits by Appointment"}
    },

    # ── 5. Modern Clean SaaS, Enterprise & Specialized Consumer (17) ─────────────────
    {
        "id": "site_saas_pulse_metrics", "name": "Pulse Metrics Analytics",
        "tagline": "Real-Time User Funnel Analytics & Product Cohort Retention Intelligence", "type": "saas",
        "prefix": "pma", "primary": "#0f172a", "accent": "#3b82f6", "accent_hover": "#1d4ed8",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Start 14-Day Free Trial", "hero_sub": "Understand user drop-off points in seconds. Track client-side events with auto-capture, retroactive funnel modeling, and zero cookies.",
        "section_name": "Analytics Capabilities", "section_id": "analytics", "pill": False,
        "items": [
            {"title": "Retroactive Funnel Analysis", "tag": "No Config Needed", "desc": "Define new funnels today and immediately see how historical traffic behaved over the past 12 months."},
            {"title": "N-Day Cohort Retention", "tag": "Retention Curves", "desc": "Identify the exact user actions that correlate with long-term 90-day subscription renewals."},
            {"title": "Automated Anomaly Detection", "tag": "Alert Pager", "desc": "Detect sudden drop-offs in checkout conversion or signup flow completion within 3 minutes."},
            {"title": "Lightweight 2KB Tracking SDK", "tag": "Zero Performance Tax", "desc": "Non-blocking beacon tracking with zero third-party cookies and complete GDPR/CCPA compliance."}
        ],
        "contact": {"address": "650 California St, San Francisco, CA 94108", "phone": "+1 (415) 555-0150", "email": "growth@pulsemetrics.io", "hours": "Mon–Fri: 8am–6pm PST"}
    },
    {
        "id": "site_saas_vault_secrets", "name": "KeyVault Cloud",
        "tagline": "Zero-Knowledge Secret Management & Automated TLS Certificate Rotation", "type": "saas",
        "prefix": "kvc", "primary": "#0f172a", "accent": "#10b981", "accent_hover": "#059669",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Secure Your Secrets", "hero_sub": "Eliminate hardcoded environment variables. Distribute API keys, database credentials, and certificates securely to Kubernetes pods.",
        "section_name": "Security Features", "section_id": "security", "pill": False,
        "items": [
            {"title": "Dynamic Ephemeral DB Credentials", "tag": "Auto-Expiring", "desc": "Generate single-use database credentials that automatically expire when the microservice container terminates."},
            {"title": "Let's Encrypt Automated Rotation", "tag": "Wildcard TLS", "desc": "Zero-downtime ACME certificate renewal with automatic deployment to load balancers and CDNs."},
            {"title": "Hardware Security Module (HSM)", "tag": "FIPS 140-3 L3", "desc": "Root encryption keys stored in tamper-proof dedicated cloud HSM hardware appliances."},
            {"title": "Secret Sprawl Git Scanning", "tag": "CI/CD Pre-Commit", "desc": "Prevent developers from committing tokens, private keys, and passwords to GitHub repos."}
        ],
        "contact": {"address": "100 Pine St, Suite 1250, San Francisco, CA 94111", "phone": "+1 (415) 555-0196", "email": "security@keyvaultcloud.com", "hours": "24/7 Security Operations"}
    },
    {
        "id": "site_saas_docu_sign_pro", "name": "SignFlow Enterprise",
        "tagline": "Legally Enforceable Digital Signatures with Cryptographic Hash Audit Trails", "type": "saas",
        "prefix": "sfe", "primary": "#0f172a", "accent": "#0ea5e9", "accent_hover": "#0284c7",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Sign First Document Free", "hero_sub": "Compliant with eIDAS, ESIGN Act, and UETA. Send NDAs, employment agreements, and sales contracts with one automated API call.",
        "section_name": "Signing Capabilities", "section_id": "signing", "pill": False,
        "items": [
            {"title": "Court-Admissible Audit Trail", "tag": "SHA-256 Timestamps", "desc": "Complete immutable log of IP addresses, email confirmations, browser user-agents, and timestamps."},
            {"title": "Automated Multi-Party Workflows", "tag": "Sequential Routing", "desc": "Route contracts sequentially from department manager to legal counsel and finally to the client."},
            {"title": "Dynamic Template Pre-Filling", "tag": "REST & Webhooks", "desc": "Pre-populate employee names, compensation numbers, and custom terms via simple JSON payload."},
            {"title": "SMS & Biometric Verification", "tag": "Two-Factor Auth", "desc": "Require two-factor authentication codes and face matching before opening high-value contracts."}
        ],
        "contact": {"address": "221 Main St, San Francisco, CA 94105", "phone": "+1 (415) 555-0178", "email": "support@signflowpro.com", "hours": "Mon–Fri: 9am–6pm PST"}
    },
    {
        "id": "site_saas_task_harmony", "name": "Harmony Workspace",
        "tagline": "Asynchronous Sprint Planning, Collaborative Docs & Engineering Roadmaps", "type": "saas",
        "prefix": "hw", "primary": "#0f172a", "accent": "#6366f1", "accent_hover": "#4f46e5",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Create Free Team Space", "hero_sub": "The modern alternative to bloated issue trackers. Blazing fast markdown documents with embedded Kanban boards and git pull request links.",
        "section_name": "Workspace Modules", "section_id": "workspace_modules", "pill": False,
        "items": [
            {"title": "Real-Time Multi-Cursor Docs", "tag": "CRDT Collab", "desc": "Collaborative markdown editing with zero lag, rich code blocks, and embedded interactive tables."},
            {"title": "Keyboard-First Command Palette", "tag": "Command + K", "desc": "Navigate issues, assign tickets, and create documents without your fingers leaving the home row."},
            {"title": "Two-Way GitHub & GitLab Sync", "tag": "Branch Auto-Close", "desc": "Issues update automatically when PRs are opened, reviewed, merged, or reverted."},
            {"title": "Automated Async Standups", "tag": "Slack & Discord", "desc": "Gather daily engineering updates automatically without forcing developers into 30-minute Zoom meetings."}
        ],
        "contact": {"address": "580 Howard St, San Francisco, CA 94105", "phone": "+1 (415) 555-0147", "email": "teams@harmonyworkspace.com", "hours": "Mon–Fri: 8am–6pm PST"}
    },
    {
        "id": "site_saas_hire_stream", "name": "TalentStream ATS",
        "tagline": "AI-Assisted Candidate Sourcing, Structured Scorecards & Offer Management", "type": "saas",
        "prefix": "tsa", "primary": "#0f172a", "accent": "#8b5cf6", "accent_hover": "#7c3aed",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Start Sourcing Candidates", "hero_sub": "Eliminate recruiter busywork. Screen technical resumes against actual job criteria and schedule interviews across 10 time zones.",
        "section_name": "Recruiting Tools", "section_id": "recruiting", "pill": False,
        "items": [
            {"title": "Structured Interview Scorecards", "tag": "Bias Prevention", "desc": "Standardize interview questions and scoring matrices across technical and behavioral interviewers."},
            {"title": "One-Click Calendar Scheduling", "tag": "Multi-Interviewer", "desc": "Candidates pick from real-time mutual availability across four busy executive calendars."},
            {"title": "Automated Sourcing Sequences", "tag": "Multi-Touch Email", "desc": "Reach out to passive senior engineers with personalized emails sent directly from founders."},
            {"title": "EEO & Diversity Compliance", "tag": "Audited Analytics", "desc": "Track hiring funnel demographic metrics while maintaining strict candidate data privacy."}
        ],
        "contact": {"address": "1355 Market St, Suite 900, San Francisco, CA 94103", "phone": "+1 (415) 555-0184", "email": "hello@talentstream.io", "hours": "Mon–Fri: 8:30am–5:30pm PST"}
    },
    {
        "id": "site_saas_pay_rail", "name": "GlobalPay Rails",
        "tagline": "Instant Cross-Border Merchant Payouts Across 140 Countries in Local Currencies", "type": "fintech",
        "prefix": "gpr", "primary": "#0f172a", "accent": "#10b981", "accent_hover": "#059669",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Get API Keys", "hero_sub": "Payout contractors, creators, and marketplaces directly into local bank accounts using SEPA, Pix, UPI, and ACH with wholesale FX spreads.",
        "section_name": "Payout Rails", "section_id": "payout_rails", "pill": False,
        "items": [
            {"title": "Direct Local Clearing Rails", "tag": "Sub-Minute Arrival", "desc": "Connect directly into Pix (Brazil), UPI (India), SEPA Instant (EU), and Faster Payments (UK)."},
            {"title": "Wholesale Institutional FX", "tag": "0.15% Spread", "desc": "Eliminate 3% bank currency exchange fees with automated real-time mid-market conversions."},
            {"title": "Global 1099 & W-8BEN Tax Forms", "tag": "IRS Automated", "desc": "Collect electronic tax documents and generate end-of-year filing reports automatically."},
            {"title": "Multi-Entity Treasury Balance", "tag": "Virtual Accounts", "desc": "Hold and disburse 35 sovereign currencies from dedicated virtual IBAN accounts in your company name."}
        ],
        "contact": {"address": "1 Poultry, London EC2R 8EJ, UK", "phone": "+44 20 7946 0888", "email": "support@globalpayrails.com", "hours": "24/7 Global Treasury Operations"}
    },
    {
        "id": "site_saas_support_desk", "name": "Resolve Desk",
        "tagline": "Omnichannel Support with AI Ticket Deflection & SLA Breach Warnings", "type": "saas",
        "prefix": "rd", "primary": "#0f172a", "accent": "#f59e0b", "accent_hover": "#d97706",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Start 30-Day Trial", "hero_sub": "Consolidate email, live chat, WhatsApp, and API error alerts into a unified inbox. Deflect 45% of repetitive tickets with smart AI agents.",
        "section_name": "Support Features", "section_id": "support_features", "pill": False,
        "items": [
            {"title": "AI First-Response Deflection", "tag": "Knowledge Base", "desc": "Resolves common questions about billing, refunds, and password resets in under 10 seconds."},
            {"title": "SLA Priority Countdown", "tag": "Tiered Routing", "desc": "Color-coded timers warn support agents 15 minutes before an enterprise contract SLA breaches."},
            {"title": "Live Co-Browsing & Session Replay", "tag": "Instant Context", "desc": "Inspect user browser console errors and network failures directly alongside the ticket thread."},
            {"title": "Automated CSAT Surveys", "tag": "Net Promoter", "desc": "Trigger one-click satisfaction ratings upon ticket closure and track agent performance metrics."}
        ],
        "contact": {"address": "101 Mission St, San Francisco, CA 94105", "phone": "+1 (415) 555-0163", "email": "success@resolvedesk.io", "hours": "24/7 Customer Support"}
    },
    {
        "id": "site_saas_audit_log", "name": "ComplianceShield",
        "tagline": "Continuous Automated SOC 2, HIPAA & ISO 27001 Evidence Collection", "type": "saas",
        "prefix": "cs", "primary": "#0f172a", "accent": "#06b6d4", "accent_hover": "#0891b2",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Automate Your Audit", "hero_sub": "Connect AWS, GitHub, Okta, and Google Workspace. Automatically prove your security controls to auditors in days instead of months.",
        "section_name": "Compliance Frameworks", "section_id": "frameworks", "pill": False,
        "items": [
            {"title": "SOC 2 Type II Automation", "tag": "Continuous Tests", "desc": "Test 150+ security controls hourly and generate auditor-approved evidence packets on demand."},
            {"title": "HIPAA Security Safeguards", "tag": "Healthcare Ready", "desc": "Verify encryption of PHI at rest and in transit across S3 buckets and RDS databases."},
            {"title": "Automated Vendor Risk Review", "tag": "Third-Party Audits", "desc": "Track SOC 2 reports, security posture, and subprocessor compliance for all company vendors."},
            {"title": "Employee Background Checks", "tag": "MDM Integrated", "desc": "Verify employee laptop disk encryption, password managers, and annual security training."}
        ],
        "contact": {"address": "500 108th Ave NE, Bellevue, WA 98004", "phone": "+1 (425) 555-0197", "email": "audit@complianceshield.tech", "hours": "Mon–Fri: 8am–5pm PST"}
    },
    {
        "id": "site_saas_uptime_mon", "name": "PingPulse Monitoring",
        "tagline": "Global Multi-Region Uptime Monitoring with 1-Second Check Intervals", "type": "devops",
        "prefix": "ppm", "primary": "#0f172a", "accent": "#22c55e", "accent_hover": "#16a34a",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Add Free Website Monitor", "hero_sub": "Verify your website and API endpoints from 65 cities globally. Instant SMS, PagerDuty, and webhook alerts when downtime is detected.",
        "section_name": "Monitoring Tools", "section_id": "monitoring", "pill": False,
        "items": [
            {"title": "1-Second Resolution Probing", "tag": "65 Global Cities", "desc": "Detect micro-outages and regional DNS routing failures within 3 seconds of occurrence."},
            {"title": "Multi-Step API Transaction Checks", "tag": "Synthetic User", "desc": "Simulate complete user journeys (login, add to cart, checkout) every 5 minutes."},
            {"title": "SSL Certificate Expiry Alerts", "tag": "30-Day Warning", "desc": "Receive automated warnings 30, 14, and 3 days before HTTPS certificates expire."},
            {"title": "Public Incident Status Pages", "tag": "Custom CNAME", "desc": "Host independent status pages on high-availability infrastructure that stays up during outages."}
        ],
        "contact": {"address": "77 King St W, Toronto, ON M5K 1G8, Canada", "phone": "+1 (416) 555-0125", "email": "ops@pingpulse.io", "hours": "24/7 Global Monitoring"}
    },
    {
        "id": "site_saas_api_gateway", "name": "RapidGateway",
        "tagline": "Sub-Millisecond Edge API Gateway with Token-Bucket Rate Limiting", "type": "cloud",
        "prefix": "rgw", "primary": "#0f172a", "accent": "#ec4899", "accent_hover": "#db2777",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Protect Your APIs", "hero_sub": "Route millions of requests per second. Built-in JWT validation, CORS headers, API key billing metering, and DDoS mitigation.",
        "section_name": "Gateway Capabilities", "section_id": "gateway_capabilities", "pill": False,
        "items": [
            {"title": "Distributed Token-Bucket Limiting", "tag": "Per-User Keys", "desc": "Enforce tier-based rate limits across distributed edge nodes with zero cross-region latency."},
            {"title": "Edge Response Caching", "tag": "Automatic Invalidation", "desc": "Cache idempotent GET requests at the edge and invalidate via webhook in under 100ms."},
            {"title": "Cryptographic JWT Verification", "tag": "Zero Backend Load", "desc": "Verify asymmetric RS256 token signatures at the gateway so invalid requests never touch servers."},
            {"title": "Automated Usage Billing Metering", "tag": "Stripe Sync", "desc": "Track API call counts per customer and sync directly with Stripe metered billing usage records."}
        ],
        "contact": {"address": "100 1st St, Suite 2200, San Francisco, CA 94105", "phone": "+1 (415) 555-0172", "email": "enterprise@rapidgateway.dev", "hours": "24/7 Platform Operations"}
    },
    {
        "id": "site_saas_form_craft", "name": "FormEngine Builder",
        "tagline": "Dynamic Multi-Step Form Builder with Conditional Logic & Webhooks", "type": "saas",
        "prefix": "feb", "primary": "#0f172a", "accent": "#6366f1", "accent_hover": "#4f46e5",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Build Form in 2 Minutes", "hero_sub": "Create accessible, high-converting forms without writing code. Embed anywhere with React components or custom iframe scripts.",
        "section_name": "Form Capabilities", "section_id": "form_capabilities", "pill": False,
        "items": [
            {"title": "Branching Conditional Logic", "tag": "Visual Flow", "desc": "Show or hide specific input questions based on answers provided in earlier form steps."},
            {"title": "Integrated Stripe Payments", "tag": "One-Click Pay", "desc": "Accept credit cards, Apple Pay, and Google Pay directly inside lead intake and registration forms."},
            {"title": "Instant Zapier & Webhook Sync", "tag": "5,000+ Integrations", "desc": "Stream form responses immediately into Salesforce, HubSpot, Notion, and PostgreSQL."},
            {"title": "Built-In Spam & Bot Protection", "tag": "Zero Captcha", "desc": "Invisible behavioral bot detection that stops spam without making users click photos of traffic lights."}
        ],
        "contact": {"address": "201 Mission St, 12th Floor, San Francisco, CA 94105", "phone": "+1 (415) 555-0136", "email": "team@formengine.io", "hours": "Mon–Fri: 9am–6pm PST"}
    },
    {
        "id": "site_saas_feature_flag", "name": "ToggleHQ Control",
        "tagline": "Real-Time Feature Flagging, Canary Releases & Instant Kill-Switches", "type": "devops",
        "prefix": "thq", "primary": "#0f172a", "accent": "#14b8a6", "accent_hover": "#0d9488",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Create Free Flag", "hero_sub": "Decouple code deployments from feature releases. Roll out features to 5% of users, monitor error rates, and roll back in milliseconds.",
        "section_name": "Release Controls", "section_id": "release_controls", "pill": False,
        "items": [
            {"title": "Sub-Millisecond Local Flag Eval", "tag": "Streaming Sync", "desc": "Flags evaluate in-memory in your application runtime with streaming updates over server-sent events."},
            {"title": "Targeted User Segmentation", "tag": "Attribute Based", "desc": "Target features based on email domain, subscription tier, beta opt-in, or geographical location."},
            {"title": "Automatic Metric Circuit Breaker", "tag": "Crash Protection", "desc": "Automatically turn off a new feature flag if application crash rates spike by more than 0.2%."},
            {"title": "Audit Logs & Approval Workflows", "tag": "Dual-Approval", "desc": "Require peer review and manager sign-off before toggling critical infrastructure flags in production."}
        ],
        "contact": {"address": "500 7th Ave, 8th Floor, New York, NY 10018", "phone": "+1 (212) 555-0152", "email": "support@togglehq.dev", "hours": "24/7 SRE Availability"}
    },
    {
        "id": "site_saas_feedback_loop", "name": "UserVoice Studio",
        "tagline": "Customer Feedback Roadmaps, Feature Voting Boards & Public Changelogs", "type": "saas",
        "prefix": "uvs", "primary": "#0f172a", "accent": "#f97316", "accent_hover": "#ea580c",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Launch Feedback Board", "hero_sub": "Give your users a voice. Let customers suggest ideas, upvote roadmap priorities, and receive automated email updates when features ship.",
        "section_name": "Product Modules", "section_id": "product_modules", "pill": False,
        "items": [
            {"title": "Public & Private Voting Boards", "tag": "SSO Enabled", "desc": "Allow verified users to vote on requested features while preventing vote manipulation and spam."},
            {"title": "Unified Public Product Roadmap", "tag": "Under Review / Planned", "desc": "Show customers what your engineering team is actively building and shipping next quarter."},
            {"title": "Automated Shipping Changelog", "tag": "Markdown Rich", "desc": "Publish beautiful release notes with embedded videos and automatically notify subscribers."},
            {"title": "Jira & Linear Bi-Directional Sync", "tag": "Dev Flow", "desc": "Link user feedback directly to engineering tickets; closing a ticket automatically notifies the user."}
        ],
        "contact": {"address": "300 2nd St, San Francisco, CA 94107", "phone": "+1 (415) 555-0186", "email": "community@uservoicestudio.com", "hours": "Mon–Fri: 9am–5pm PST"}
    },
    {
        "id": "site_saas_invoice_flow", "name": "BillCraft Billing",
        "tagline": "Automated SaaS Subscription Billing & Global VAT / Sales Tax Compliance", "type": "fintech",
        "prefix": "bcb", "primary": "#0f172a", "accent": "#10b981", "accent_hover": "#059669",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Automate Billing", "hero_sub": "Handle monthly, annual, per-seat, and usage-based subscriptions with automated dunning recovery and European VAT validation.",
        "section_name": "Billing Capabilities", "section_id": "billing", "pill": False,
        "items": [
            {"title": "Smart Dunning & Card Recovery", "tag": "Recovers 68% Churn", "desc": "Automatically retries failed credit cards using smart machine learning schedules before canceling accounts."},
            {"title": "Global EU VAT & US Sales Tax", "tag": "VIES Verified", "desc": "Real-time tax calculation and reverse-charge VAT validation based on customer billing country."},
            {"title": "Tiered & Overage Usage Pricing", "tag": "Automated Metering", "desc": "Bill customers automatically for API calls, compute gigabytes, or active seats each billing cycle."},
            {"title": "Branded Self-Serve Customer Portal", "tag": "Zero Support Tickets", "desc": "Let customers update credit cards, download PDF invoices, and upgrade plans independently."}
        ],
        "contact": {"address": "100 South Wacker Dr, Chicago, IL 60606", "phone": "+1 (312) 555-0140", "email": "billing@billcraft.finance", "hours": "Mon–Fri: 8am–6pm CST"}
    },
    {
        "id": "site_saas_status_page", "name": "IncidentLive Status",
        "tagline": "Reliable Incident Communication Status Pages Hosted on Isolated Edge Nodes", "type": "devops",
        "prefix": "ils", "primary": "#0f172a", "accent": "#0ea5e9", "accent_hover": "#0284c7",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Create Free Status Page", "hero_sub": "Keep your users informed during service disruptions. Hosted on completely separate cloud infrastructure so your status page never goes down.",
        "section_name": "Status Features", "section_id": "status_features", "pill": False,
        "items": [
            {"title": "Multi-Cloud Isolated Hosting", "tag": "99.999% Uptime", "desc": "Status pages live on separate DNS and CDN infrastructure independent of your main application."},
            {"title": "Automated Incident Subscriber Alerts", "tag": "SMS / Email / Slack", "desc": "Notify thousands of subscribed enterprise customers automatically when an incident status updates."},
            {"title": "Historical 90-Day Uptime Metrics", "tag": "Public Transparency", "desc": "Display clear uptime percentage bars across all API, database, and dashboard services."},
            {"title": "Automated Post-Mortem Templates", "tag": "Root-Cause Publish", "desc": "Publish comprehensive root-cause analysis documents once incidents are fully resolved."}
        ],
        "contact": {"address": "333 S Grand Ave, Los Angeles, CA 90071", "phone": "+1 (213) 555-0168", "email": "incident@incidentlive.io", "hours": "24/7 Emergency Incident Desk"}
    },
    {
        "id": "site_saas_asset_dam", "name": "PixelVault DAM",
        "tagline": "Cloud Digital Asset Management with Instant WebP/AVIF Image Optimizations", "type": "saas",
        "prefix": "pvd", "primary": "#0f172a", "accent": "#a855f7", "accent_hover": "#9333ea",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Upload Assets", "hero_sub": "Centralize marketing photos, product renders, and vector logos. Transform image sizes, formats, and crops dynamically via simple URL parameters.",
        "section_name": "Asset Tools", "section_id": "asset_tools", "pill": False,
        "items": [
            {"title": "Dynamic URL Image Transformations", "tag": "Format & Resize", "desc": "Resize, crop, and convert images to AVIF or WebP on the fly simply by changing URL parameters."},
            {"title": "AI Semantic Visual Search", "tag": "Color & Subject", "desc": "Find images using natural language queries like 'blue sneakers on asphalt' without manual tagging."},
            {"title": "Versioned Brand Style Guides", "tag": "Single Source of Truth", "desc": "Ensure your entire marketing and engineering team uses approved SVG logos and official palettes."},
            {"title": "Granular Team Access Permissions", "tag": "Role-Based RBAC", "desc": "Grant external agency contractors view-only access while maintaining full admin rights internally."}
        ],
        "contact": {"address": "200 S Biscayne Blvd, Suite 2800, Miami, FL 33131", "phone": "+1 (305) 555-0193", "email": "media@pixelvaultdam.com", "hours": "Mon–Fri: 9am–6pm EST"}
    },
    {
        "id": "site_saas_survey_mind", "name": "InsightPulse Micro-Surveys",
        "tagline": "In-Product User Micro-Surveys & Real-Time Sentiment Scoring Intelligence", "type": "saas",
        "prefix": "ipm", "primary": "#0f172a", "accent": "#f43f5e", "accent_hover": "#e11d48",
        "surface": "#1e293b", "heading_font": "Plus Jakarta Sans", "body_font": "Inter",
        "cta": "Create First Survey", "hero_sub": "Trigger single-question NPS and CSAT surveys at the exact moment of customer delight. High 45% completion rates with elegant non-intrusive modals.",
        "section_name": "Survey Intelligence", "section_id": "survey_intelligence", "pill": False,
        "items": [
            {"title": "Action-Triggered Modal Prompts", "tag": "High Completion", "desc": "Display surveys only after a user successfully completes an export, purchase, or invited teammate."},
            {"title": "Real-Time NLP Sentiment Analysis", "tag": "Instant Classification", "desc": "Categorize open-ended feedback automatically into bug reports, feature requests, or praise."},
            {"title": "Targeted User Attribute Filters", "tag": "Enterprise Only", "desc": "Filter surveys to appear only for paying enterprise accounts with over 30 days of platform usage."},
            {"title": "Instant Slack & Webhook Dispatch", "tag": "Zero Latency", "desc": "Notify customer success managers immediately whenever a user submits an NPS score below 7."}
        ],
        "contact": {"address": "601 108th Ave NE, Suite 1900, Bellevue, WA 98004", "phone": "+1 (425) 555-0138", "email": "insights@insightpulsesurveys.com", "hours": "Mon–Fri: 8am–5pm PST"}
    }
]


def build_brief_xml(d: dict) -> str:
    items_xml = []
    for item in d["items"]:
        items_xml.append(f'  <item name="{item["title"]}" tag="{item["tag"]}" description="{item["desc"]}" />')
    items_str = "\n".join(items_xml)
    
    # Check if this domain uses the Refero Monopo Saigon pill token style
    is_refero = d.get("pill", False)
    design_system_str = ""
    if is_refero:
        design_system_str = f"""  <design_system style_name="refero_editorial" source="refero">
    <primary_color>{d["primary"]}</primary_color>
    <accent_color>{d["accent"]}</accent_color>
    <font_heading>{d["heading_font"]}</font_heading>
    <font_body>{d["body_font"]}</font_body>
    <css_variables>
:root {{
  --color-obsidian: {d["primary"]};
  --color-paper: #ffffff;
  --color-iridescent-fade: {d["accent"]};
  --font-heading: '{d["heading_font"]}', sans-serif;
  --font-body: '{d["body_font"]}', sans-serif;
  --radius-buttons: 75px;
  --radius-cards: 0px;
  --radius-inputs: 0px;
  --page-max-width: 1078px;
  --card-padding: 34px;
}}
    </css_variables>
    <design_rules>
      <rule type="do">Use strictly var(--color-*) and var(--radius-*) tokens for visual consistency.</rule>
      <rule type="dont">Never use box-shadow or elevation blur; rely strictly on borders and high contrast.</rule>
      <rule type="dont">Never set border-radius between 1px and 74px; strictly 75px for buttons and 0px for cards.</rule>
    </design_rules>
  </design_system>"""
    else:
        design_system_str = f"""  <design_system>
    <primary_color>{d["primary"]}</primary_color>
    <accent_color>{d["accent"]}</accent_color>
    <font_heading>{d["heading_font"]}</font_heading>
    <font_body>{d["body_font"]}</font_body>
  </design_system>"""

    return f"""<content_brief>
  <business_name>{d["name"]}</business_name>
  <tagline>{d["tagline"]}</tagline>
  <business_type>{d["type"]}</business_type>
{design_system_str}
  <sections>header, hero, {d["section_id"]}, footer</sections>
{items_str}
  <contact>
    <address>{d["contact"]["address"]}</address>
    <phone>{d["contact"]["phone"]}</phone>
    <email>{d["contact"]["email"]}</email>
    <hours>{d["contact"]["hours"]}</hours>
  </contact>
</content_brief>"""


def build_trajectory(d: dict) -> dict:
    brief_xml = build_brief_xml(d)
    p = d["prefix"]
    is_refero = d.get("pill", False)
    
    # Token-conscious styling
    radius_btn = "var(--radius-buttons, 75px)" if is_refero else "var(--radius-md, 8px)"
    radius_card = "var(--radius-cards, 0px)" if is_refero else "var(--radius-md, 12px)"
    box_shadow = "none" if is_refero else "0 10px 25px rgba(0, 0, 0, 0.35)"
    border_card = "1px solid rgba(255, 255, 255, 0.15)" if is_refero else "1px solid rgba(255, 255, 255, 0.08)"

    # ── Turn 1: Header ──────────────────────────────────────────────────────────
    initial_user = (
        "Build a complete website for the following brief.\n\n"
        f"{brief_xml}\n\n"
        "You will build the site ONE SECTION AT A TIME, adhering strictly to the declared design tokens and custom properties.\n\n"
        f"FIRST SECTION REQUIRED: Write the Header section: a sticky navigation bar with the business name/logo on the left, "
        f"navigation links (Home, {d['section_name']}, Contact) on the right, plus '{d['cta']}' CTA button. "
        "Files: src/components/Header.tsx + src/components/Header.css"
    )

    t1_thought = thought(
        f"I'll start by crafting the Header for {d['name']}. "
        f"It needs to reflect the {d['type']} brand identity: deep background ({d['primary']}) with crisp contrast, "
        f"the elegant {d['heading_font']} typography for the wordmark, and the signature {d['accent']} accent for the CTA button. "
        f"I'll also implement a scroll listener to trigger subtle border illumination on scroll."
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
        <div className="{p}-header__mobile-menu" role="dialog" aria-modal="true">
          <a href="#hero" className="{p}-header__mobile-link" onClick={{() => setMenuOpen(false)}}>Home</a>
          <a href="#{d['section_id']}" className="{p}-header__mobile-link" onClick={{() => setMenuOpen(false)}}>{d['section_name']}</a>
          <a href="#footer" className="{p}-header__mobile-link" onClick={{() => setMenuOpen(false)}}>Contact</a>
          <a href="mailto:{d['contact']['email']}" className="{p}-header__mobile-cta" onClick={{() => setMenuOpen(false)}}>{d['cta']}</a>
        </div>
      )}}
    </header>
  );
}}
"""

    t1_css = f""".{p}-header {{
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, {d['primary']})));
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.25s ease;
}}

.{p}-header--scrolled {{
  background: var(--surface-obsidian, var(--color-obsidian, {d['primary']}));
  border-bottom-color: rgba(255, 255, 255, 0.18);
}}

.{p}-header__inner {{
  max-width: var(--page-max-width, 1140px);
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}}

.{p}-header__logo {{
  font-family: var(--font-heading, '{d['heading_font']}', sans-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-paper, var(--text-color, #ffffff));
  text-decoration: none;
  letter-spacing: -0.02em;
}}

.{p}-header__nav {{
  display: flex;
  align-items: center;
  gap: 2rem;
}}

.{p}-header__link {{
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.75));
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: color 0.15s ease;
}}

.{p}-header__link:hover {{
  color: var(--color-iridescent-fade, var(--accent-color, {d['accent']}));
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
  padding: 0.55rem 1.35rem;
  background: var(--color-iridescent-fade, var(--accent-color, {d['accent']}));
  color: var(--color-paper, var(--text-color, #ffffff));
  border-radius: {radius_btn};
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s ease, transform 0.15s ease;
}}

.{p}-header__cta:hover {{
  opacity: 0.92;
  transform: translateY(-1px);
}}

.{p}-header__toggle {{
  display: none;
  flex-direction: column;
  gap: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
}}

.{p}-header__bar {{
  width: 20px;
  height: 2px;
  background: var(--color-paper, var(--text-color, #ffffff));
  border-radius: 0;
}}

.{p}-header__mobile-menu {{
  display: flex;
  flex-direction: column;
  padding: 1rem 1.5rem 1.5rem;
  background: var(--surface-obsidian, var(--color-obsidian, {d['primary']}));
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  gap: 1rem;
}}

.{p}-header__mobile-link {{
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-size: 1rem;
}}

.{p}-header__mobile-cta {{
  display: inline-block;
  text-align: center;
  padding: 0.75rem 1.5rem;
  background: var(--color-iridescent-fade, var(--accent-color, {d['accent']}));
  color: var(--color-paper, var(--text-color, #ffffff));
  border-radius: {radius_btn};
  text-decoration: none;
  font-weight: 600;
  margin-top: 0.5rem;
}}

@media (max-width: 768px) {{
  .{p}-header__nav {{ display: none; }}
  .{p}-header__toggle {{ display: flex; }}
}}
"""

    t1_action = write_site("src/components/Header.tsx", t1_tsx, "src/components/Header.css", t1_css)
    obs_1 = obs_ok(
        ["src/components/Header.tsx", "src/components/Header.css"],
        f"Write the Hero section: high-impact full-width banner with tagline '{d['tagline']}' as an h1, "
        f"subtitle, primary '{d['cta']}' CTA button, secondary learn more button, and key metric badges. "
        "Files: src/components/Hero.tsx + src/components/Hero.css"
    )

    # ── Turn 2: Hero ────────────────────────────────────────────────────────────
    t2_thought = thought(
        f"Header accepted. Now building the Hero section for {d['name']}. "
        f"The headline will be '{d['tagline']}', followed by '{d['hero_sub']}'. "
        f"I will provide clear visual hierarchy, primary/secondary action buttons with {radius_btn} styling, "
        "and metric highlight pills."
    )

    t2_tsx = f"""import React from 'react';
import './Hero.css';

export function Hero() {{
  return (
    <section className="{p}-hero" id="hero" aria-label="{d['name']} Overview">
      <div className="{p}-hero__inner">
        <div className="{p}-hero__badge" role="status">
          <span className="{p}-hero__badge-dot" aria-hidden="true" />
          <span>{d['name']} — {d['type'].replace('_', ' ').capitalize()}</span>
        </div>

        <h1 className="{p}-hero__title">
          {d['tagline']}
        </h1>

        <p className="{p}-hero__subtitle">
          {d['hero_sub']}
        </p>

        <div className="{p}-hero__actions">
          <a href="#{d['section_id']}" className="{p}-hero__btn-primary">
            {d['cta']}
          </a>
          <a href="#footer" className="{p}-hero__btn-secondary">
            Get in Touch
          </a>
        </div>

        <div className="{p}-hero__metrics" role="group" aria-label="Key Highlights">
          <div className="{p}-hero__metric">
            <span className="{p}-hero__metric-value">100%</span>
            <span className="{p}-hero__metric-label">Verifiable Quality</span>
          </div>
          <div className="{p}-hero__metric">
            <span className="{p}-hero__metric-value">24/7</span>
            <span className="{p}-hero__metric-label">Dedicated Support</span>
          </div>
          <div className="{p}-hero__metric">
            <span className="{p}-hero__metric-value">5.0★</span>
            <span className="{p}-hero__metric-label">Client Rating</span>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""

    t2_css = f""".{p}-hero {{
  position: relative;
  width: 100%;
  padding: 5rem 1.5rem 4rem;
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, {d['primary']})));
  overflow: hidden;
}}

.{p}-hero__inner {{
  max-width: var(--page-max-width, 1140px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}}

.{p}-hero__badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.95rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: {radius_btn};
  color: var(--color-paper, #ffffff);
  font-size: 0.8125rem;
  font-weight: 500;
  margin-bottom: 1.75rem;
}}

.{p}-hero__badge-dot {{
  width: 7px;
  height: 7px;
  background: var(--color-iridescent-fade, var(--accent-color, {d['accent']}));
  border-radius: 50%;
}}

.{p}-hero__title {{
  font-family: var(--font-heading, '{d['heading_font']}', sans-serif);
  font-size: clamp(2.25rem, 5vw, 3.75rem);
  font-weight: 800;
  color: var(--color-paper, var(--text-color, #ffffff));
  line-height: 1.15;
  letter-spacing: -0.025em;
  max-width: 900px;
  margin-bottom: 1.25rem;
}}

.{p}-hero__subtitle {{
  font-family: var(--font-body, '{d['body_font']}', sans-serif);
  font-size: clamp(1rem, 2vw, 1.25rem);
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.72));
  line-height: 1.6;
  max-width: 680px;
  margin-bottom: 2.25rem;
}}

.{p}-hero__actions {{
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 3.5rem;
}}

.{p}-hero__btn-primary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 2rem;
  background: var(--color-iridescent-fade, var(--accent-color, {d['accent']}));
  color: var(--color-paper, var(--text-color, #ffffff));
  border-radius: {radius_btn};
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s ease, transform 0.15s ease;
}}

.{p}-hero__btn-primary:hover {{
  opacity: 0.92;
  transform: translateY(-2px);
}}

.{p}-hero__btn-secondary {{
  display: inline-flex;
  align-items: center;
  padding: 0.85rem 2rem;
  background: transparent;
  color: var(--color-paper, #ffffff);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: {radius_btn};
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  transition: border-color 0.15s ease, background 0.15s ease;
}}

.{p}-hero__btn-secondary:hover {{
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.04);
}}

.{p}-hero__metrics {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  width: 100%;
  max-width: 640px;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.{p}-hero__metric {{
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}}

.{p}-hero__metric-value {{
  font-family: var(--font-heading, '{d['heading_font']}', sans-serif);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
}}

.{p}-hero__metric-label {{
  font-size: 0.8125rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.55));
}}

@media (max-width: 600px) {{
  .{p}-hero__metrics {{ grid-template-columns: 1fr; gap: 1.25rem; }}
}}
"""

    t2_action = write_site("src/components/Hero.tsx", t2_tsx, "src/components/Hero.css", t2_css)
    obs_2 = obs_ok(
        ["src/components/Hero.tsx", "src/components/Hero.css"],
        f"Write the {d['section_name']} section: display the 4 core offerings as responsive cards with titles, tags, and descriptions. "
        f"Files: src/components/{d['section_id'].capitalize()}.tsx + src/components/{d['section_id'].capitalize()}.css"
    )

    # ── Turn 3: Core Offerings Section ──────────────────────────────────────────
    sec_cap = d['section_id'].capitalize()
    t3_thought = thought(
        f"Hero accepted. Now implementing the {d['section_name']} section ({sec_cap}). "
        f"I'll present the 4 items ({', '.join([it['title'] for it in d['items'][:2]])}...) "
        f"using a responsive card grid with {border_card}, {radius_card}, and subtle hover interaction."
    )

    cards_tsx = []
    for it in d["items"]:
        cards_tsx.append(f"""          <article className="{p}-{d['section_id']}__card">
            <div className="{p}-{d['section_id']}__card-header">
              <h3 className="{p}-{d['section_id']}__card-title">{it['title']}</h3>
              <span className="{p}-{d['section_id']}__card-tag">{it['tag']}</span>
            </div>
            <p className="{p}-{d['section_id']}__card-desc">{it['desc']}</p>
          </article>""")
    cards_str = "\n".join(cards_tsx)

    t3_tsx = f"""import React from 'react';
import './{sec_cap}.css';

export function {sec_cap}() {{
  return (
    <section className="{p}-{d['section_id']}" id="{d['section_id']}" aria-labelledby="{p}-{d['section_id']}-heading">
      <div className="{p}-{d['section_id']}__inner">
        <div className="{p}-{d['section_id']}__header">
          <h2 id="{p}-{d['section_id']}-heading" className="{p}-{d['section_id']}__title">
            {d['section_name']}
          </h2>
          <p className="{p}-{d['section_id']}__subtitle">
            Engineered with uncompromising precision and verified specifications.
          </p>
        </div>

        <div className="{p}-{d['section_id']}__grid">
{cards_str}
        </div>
      </div>
    </section>
  );
}}
"""

    t3_css = f""".{p}-{d['section_id']} {{
  width: 100%;
  padding: 5rem 1.5rem;
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, {d['primary']})));
}}

.{p}-{d['section_id']}__inner {{
  max-width: var(--page-max-width, 1140px);
  margin: 0 auto;
}}

.{p}-{d['section_id']}__header {{
  text-align: center;
  max-width: 600px;
  margin: 0 auto 3.5rem;
}}

.{p}-{d['section_id']}__title {{
  font-family: var(--font-heading, '{d['heading_font']}', sans-serif);
  font-size: clamp(1.75rem, 3.5vw, 2.5rem);
  font-weight: 700;
  color: var(--color-paper, var(--text-color, #ffffff));
  margin-bottom: 0.75rem;
}}

.{p}-{d['section_id']}__subtitle {{
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.65));
  font-size: 1rem;
  line-height: 1.5;
}}

.{p}-{d['section_id']}__grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.5rem;
}}

.{p}-{d['section_id']}__card {{
  background: rgba(255, 255, 255, 0.02);
  border: {border_card};
  border-radius: {radius_card};
  padding: var(--card-padding, 1.75rem);
  box-shadow: {box_shadow};
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: border-color 0.2s ease, transform 0.2s ease;
}}

.{p}-{d['section_id']}__card:hover {{
  border-color: rgba(255, 255, 255, 0.35);
  transform: translateY(-3px);
}}

.{p}-{d['section_id']}__card-header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}}

.{p}-{d['section_id']}__card-title {{
  font-family: var(--font-heading, '{d['heading_font']}', sans-serif);
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-paper, #ffffff);
}}

.{p}-{d['section_id']}__card-tag {{
  display: inline-block;
  padding: 0.2rem 0.6rem;
  background: rgba(255, 255, 255, 0.07);
  border-radius: {radius_btn};
  color: var(--color-iridescent-fade, var(--accent-color, {d['accent']}));
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}}

.{p}-{d['section_id']}__card-desc {{
  font-size: 0.875rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.7));
  line-height: 1.6;
  margin: 0;
}}
"""

    t3_action = write_site(f"src/components/{sec_cap}.tsx", t3_tsx, f"src/components/{sec_cap}.css", t3_css)
    obs_3 = obs_ok(
        [f"src/components/{sec_cap}.tsx", f"src/components/{sec_cap}.css"],
        "Write the Footer section: dark background footer with business name, address, phone, email, operating hours, and copyright. "
        "Files: src/components/Footer.tsx + src/components/Footer.css"
    )

    # ── Turn 4: Footer ──────────────────────────────────────────────────────────
    t4_thought = thought(
        f"Section {sec_cap} accepted. Now completing the final section: Footer. "
        f"It will display {d['name']} brand, address ({d['contact']['address']}), phone, email, hours, and legal notice."
    )

    t4_tsx = f"""import React from 'react';
import './Footer.css';

export function Footer() {{
  const currentYear = new Date().getFullYear();

  return (
    <footer className="{p}-footer" id="footer" role="contentinfo">
      <div className="{p}-footer__inner">
        <div className="{p}-footer__col">
          <span className="{p}-footer__logo">{d['name']}</span>
          <p className="{p}-footer__tagline">{d['tagline']}</p>
        </div>

        <div className="{p}-footer__col">
          <h4 className="{p}-footer__heading">Location & Hours</h4>
          <address className="{p}-footer__address">
            <p>{d['contact']['address']}</p>
            <p className="{p}-footer__hours">{d['contact']['hours']}</p>
          </address>
        </div>

        <div className="{p}-footer__col">
          <h4 className="{p}-footer__heading">Direct Contact</h4>
          <p className="{p}-footer__contact-item">
            <a href="tel:{d['contact']['phone']}">{d['contact']['phone']}</a>
          </p>
          <p className="{p}-footer__contact-item">
            <a href="mailto:{d['contact']['email']}">{d['contact']['email']}</a>
          </p>
        </div>
      </div>

      <div className="{p}-footer__bottom">
        <p>&copy; {{currentYear}} {d['name']}. All rights reserved.</p>
      </div>
    </footer>
  );
}}
"""

    t4_css = f""".{p}-footer {{
  width: 100%;
  background: var(--surface-obsidian, var(--color-obsidian, #000000));
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4rem 1.5rem 2rem;
  color: var(--color-paper, #ffffff);
}}

.{p}-footer__inner {{
  max-width: var(--page-max-width, 1140px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 2.5rem;
  margin-bottom: 3rem;
}}

.{p}-footer__logo {{
  font-family: var(--font-heading, '{d['heading_font']}', sans-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-paper, #ffffff);
  display: block;
  margin-bottom: 0.75rem;
}}

.{p}-footer__tagline {{
  font-size: 0.875rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.6));
  line-height: 1.5;
}}

.{p}-footer__heading {{
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-paper, #ffffff);
  margin-bottom: 1rem;
}}

.{p}-footer__address,
.{p}-footer__contact-item {{
  font-style: normal;
  font-size: 0.875rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.65));
  line-height: 1.6;
}}

.{p}-footer__address p {{
  margin: 0 0 0.5rem;
}}

.{p}-footer__contact-item a {{
  color: var(--color-paper, #ffffff);
  text-decoration: none;
  transition: color 0.15s ease;
}}

.{p}-footer__contact-item a:hover {{
  color: var(--color-iridescent-fade, var(--accent-color, {d['accent']}));
}}

.{p}-footer__bottom {{
  max-width: var(--page-max-width, 1140px);
  margin: 0 auto;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.8125rem;
  color: var(--color-ash-mist, rgba(255, 255, 255, 0.45));
  text-align: center;
}}
"""

    t4_action = write_site("src/components/Footer.tsx", t4_tsx, "src/components/Footer.css", t4_css)
    obs_4 = obs_done([
        "src/components/Header.tsx", "src/components/Header.css",
        "src/components/Hero.tsx", "src/components/Hero.css",
        f"src/components/{sec_cap}.tsx", f"src/components/{sec_cap}.css",
        "src/components/Footer.tsx", "src/components/Footer.css"
    ])

    # ── Turn 5: Finish ──────────────────────────────────────────────────────────
    t5_thought = thought(
        f"All 4 sections of the {d['name']} website are written and verified. "
        "Header, Hero, Core Offerings, and Footer are complete and strictly comply with the active design tokens. Finalizing."
    )
    t5_finish = finish(
        f"Successfully built the complete {d['name']} website with full responsive layouts, "
        f"custom {d['heading_font']} typography, and design token integration."
    )

    messages = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
        {"role": "assistant", "content": f"{t1_thought}\n{t1_action}"},
        {"role": "user", "content": obs_1},
        {"role": "assistant", "content": f"{t2_thought}\n{t2_action}"},
        {"role": "user", "content": obs_2},
        {"role": "assistant", "content": f"{t3_thought}\n{t3_action}"},
        {"role": "user", "content": obs_3},
        {"role": "assistant", "content": f"{t4_thought}\n{t4_action}"},
        {"role": "user", "content": obs_4},
        {"role": "assistant", "content": f"{t5_thought}\n{t5_finish}"},
    ]

    return {"task_id": d["id"], "messages": messages}


def main():
    out_file = BASE_DIR / "data" / "site_trajectories_batch6.jsonl"
    print(f"Generating Batch 6 ({len(DOMAINS_B6)} high-quality website trajectories) -> {out_file}...")
    
    with out_file.open("w", encoding="utf-8") as f:
        for d in DOMAINS_B6:
            rec = build_trajectory(d)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            
    print(f"[OK] Wrote {len(DOMAINS_B6)} unique website trajectories to {out_file}")

if __name__ == "__main__":
    main()
