#!/usr/bin/env python3
"""
generate_site_trajectories_batch4.py - Batch 4 of Gold-Standard Site Trajectories (50 Modern Real-World Domains).

Generates 50 complete, multi-turn, full-website trajectories adhering strictly to
the ChatML schema and XML tool-calling protocol defined in agent_protocol.py.
Integrates layout archetyping (grid, timeline, tabs, split_hero, editorial, bento),
domain-specific authentic copy, and scoped modern CSS.

Outputs:
  site_trajectories_batch4.jsonl
  data/site_trajectories_batch4.jsonl
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
    {
        "id": "site_bakery_golden_crumb",
        "name": "Golden Crumb Bakery",
        "tagline": "Handcrafted Sourdough and Parisian Patisserie",
        "type": "bakery",
        "prefix": "gc",
        "primary": "#221914",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "surface": "#2d221c",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "Pre-Order Bakes",
        "hero_sub": "Wild-fermented European breads, flaky cultured butter croissants, and seasonal fruit tarts baked fresh before dawn.",
        "section_name": "Pastries & Breads",
        "section_id": "bakes",
        "items": [
            {"title": "Country Sourdough Boule", "tag": "$9.50", "desc": "36-hour cold ferment with stone-ground heritage whole wheat and caramelized blistered crust."},
            {"title": "Cardamom Almond Croissant", "tag": "$6.25", "desc": "Twice-baked laminated viennoiserie soaked in orange blossom syrup with toasted almond frangipane."},
            {"title": "Valrhona Chocolate Babka", "tag": "$14.00", "desc": "Brioche loaf braided with 70% dark chocolate fudge, Ceylon cinnamon, and crystal sugar syrup."},
            {"title": "Miso Hazelnut Kouign-Amann", "tag": "$5.75", "desc": "Breton butter pastry caramelized with salted white miso honey and roasted Piedmont hazelnuts."}
        ],
        "contact": {
            "address": "144 Artisan Way, Portland, OR 97209",
            "phone": "+1 (503) 555-0182",
            "email": "orders@goldencrumb.com",
            "hours": "Wed–Sun: 7am–3pm (or until sold out)"
        }
    },
    {
        "id": "site_law_vance_holloway",
        "name": "Vance & Holloway LLP",
        "tagline": "Strategic Counsel for Emerging Tech and IP Litigation",
        "type": "law_firm",
        "prefix": "vh",
        "primary": "#0c1524",
        "accent": "#c5a059",
        "accent_hover": "#dfb76c",
        "surface": "#142136",
        "heading_font": "Merriweather",
        "body_font": "Inter",
        "cta": "Schedule Consultation",
        "hero_sub": "Protecting foundational innovations, defending patents in federal court, and structuring high-stakes venture transactions across Silicon Valley and New York.",
        "section_name": "Practice Areas",
        "section_id": "practices",
        "items": [
            {"title": "Patent & IP Litigation", "tag": "Federal Defense", "desc": "First-chair trial defense in patent infringement, trademark disputes, and trade secret misappropriation."},
            {"title": "Venture & M&A Transactions", "tag": "Corporate", "desc": "Structuring priced rounds, cross-border acquisitions, and convertible securities for high-growth tech firms."},
            {"title": "AI & Regulatory Compliance", "tag": "Advisory", "desc": "Navigating generative AI copyright, EU AI Act compliance, and autonomous systems liability frameworks."},
            {"title": "Executive Compensation & Equity", "tag": "Governance", "desc": "Designing tax-advantaged stock option plans, founder vesting agreements, and board governance charters."}
        ],
        "contact": {
            "address": "555 California St, Suite 3200, San Francisco, CA 94104",
            "phone": "+1 (415) 555-0199",
            "email": "intake@vanceholloway.com",
            "hours": "Mon–Fri: 8am–6:30pm"
        }
    },
    {
        "id": "site_travel_wanderlust_expeditions",
        "name": "Wanderlust Expeditions",
        "tagline": "Uncharted Luxury and Regenerative Wildlife Safaris",
        "type": "travel",
        "prefix": "wl",
        "primary": "#122018",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "surface": "#1b3024",
        "heading_font": "Outfit",
        "body_font": "Inter",
        "cta": "Book Expedition",
        "hero_sub": "Bespoke small-group journeys led by certified field biologists and mountaineers into Earth's most remote and pristine ecosystems.",
        "section_name": "Featured Journeys",
        "section_id": "expeditions",
        "items": [
            {"title": "Serengeti Migration & Crater", "tag": "10 Days", "desc": "Mobile luxury canvas tenting tracking seasonal wildebeest crossings with private Maasai guides."},
            {"title": "Patagonia Fjords & Glaciers", "tag": "12 Days", "desc": "Catamaran navigation through southern ice fields paired with Torres del Paine backcountry horse treks."},
            {"title": "Svalbard Polar Bear Quest", "tag": "8 Days", "desc": "Small expedition ice-class vessel cruising Spitsbergen pack ice under the midnight sun."},
            {"title": "Raja Ampat Coral Diving", "tag": "11 Days", "desc": "Traditional wooden phinisi yacht liveaboard exploring the biodiverse epicentre of the Coral Triangle."}
        ],
        "contact": {
            "address": "820 2nd Ave, Suite 700, Seattle, WA 98104",
            "phone": "+1 (206) 555-0144",
            "email": "concierge@wanderlustexpeditions.com",
            "hours": "Mon–Sat: 9am–7pm"
        }
    },
    {
        "id": "site_vet_paws_claws_hospital",
        "name": "Paws & Claws Animal Hospital",
        "tagline": "Compassionate Medicine and Advanced 24/7 Veterinary Care",
        "type": "veterinary",
        "prefix": "pc",
        "primary": "#0f202b",
        "accent": "#14b8a6",
        "accent_hover": "#0d9488",
        "surface": "#173041",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Book Appointment",
        "hero_sub": "Board-certified surgeons, feline-friendly exam rooms, low-stress handling, and on-site CT diagnostic imaging for your companions.",
        "section_name": "Clinical Services",
        "section_id": "services",
        "items": [
            {"title": "24/7 Emergency & ICU Care", "tag": "Always Open", "desc": "Immediate critical care with oxygen therapy cages, blood transfusions, and continuous telemetry monitoring."},
            {"title": "Minimally Invasive Surgery", "tag": "Specialized", "desc": "Laparoscopic spays, soft tissue reconstructions, and orthopedic stifle stabilization with rapid recovery."},
            {"title": "Advanced Digital Radiology", "tag": "Diagnostics", "desc": "In-house 64-slice CT scans, high-resolution ultrasound, and certified board radiologist evaluations."},
            {"title": "Dental Prophylaxis & Surgery", "tag": "Preventative", "desc": "Full-mouth digital radiographs, ultrasonic scaling, and subgingival laser periodontal treatments."}
        ],
        "contact": {
            "address": "4020 W Sunset Blvd, Los Angeles, CA 90027",
            "phone": "+1 (323) 555-0120",
            "email": "care@pawsandclawsvet.com",
            "hours": "24 Hours / 7 Days a Week"
        }
    },
    {
        "id": "site_podcast_the_future_syntax",
        "name": "The Future Syntax",
        "tagline": "Conversations on Deep Tech, Neural Models, and Cybernetics",
        "type": "podcast",
        "prefix": "fs",
        "primary": "#0b0e17",
        "accent": "#a855f7",
        "accent_hover": "#9333ea",
        "surface": "#141926",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Listen on Spotify",
        "hero_sub": "Weekly uncensored technical interviews with the research scientists, chip architects, and founders building superintelligence.",
        "section_name": "Latest Episodes",
        "section_id": "episodes",
        "items": [
            {"title": "Ep 84: Neuromorphic Silicon & Sub-1nm Nodes", "tag": "74 min", "desc": "Dr. Aris Thorne discusses optical interconnects, non-volatile analog compute, and thermal dissipation limits."},
            {"title": "Ep 83: Frontier RL & Multi-Turn Verification", "tag": "68 min", "desc": "Deep dive into reward model collapse, synthetic tree search, and automated formal theorem proving."},
            {"title": "Ep 82: Brain-Machine Bandwidth & Neural Stents", "tag": "81 min", "desc": "Endovascular electrode arrays, chronic bio-compatibility, and decoding motor cortex intent at 10kHz."},
            {"title": "Ep 81: Autonomous Robotics in Zero-G Space", "tag": "62 min", "desc": "Orbital assembly, visual slam in direct solar glare, and fault-tolerant distributed actuators."}
        ],
        "contact": {
            "address": "Studio 4B, 180 Varick St, New York, NY 10014",
            "phone": "+1 (212) 555-0177",
            "email": "producers@futuresyntaxpodcast.com",
            "hours": "New Episodes Every Tuesday at 6am EST"
        }
    },
    {
        "id": "site_coworking_the_hive_collective",
        "name": "The Hive Collective",
        "tagline": "Architect-Designed Workspaces for Creators and Founders",
        "type": "coworking",
        "prefix": "th",
        "primary": "#18181b",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
        "surface": "#27272a",
        "heading_font": "DM Sans",
        "body_font": "Inter",
        "cta": "Book a Day Pass",
        "hero_sub": "Ergonomic Herman Miller seating, 10Gbps fiber internet, soundproof podcast booths, and barista-pulled espresso in the heart of downtown.",
        "section_name": "Membership Tiers",
        "section_id": "memberships",
        "items": [
            {"title": "Hot Desk Flexible", "tag": "$249/mo", "desc": "Access to open communal lounges, quiet library zones, phone booths, and unlimited specialty drip coffee."},
            {"title": "Dedicated Desk", "tag": "$429/mo", "desc": "Your own motorized standing desk, lockable filing drawer, dual 4K monitors, and meeting room credits."},
            {"title": "Private Team Office", "tag": "$1,450/mo", "desc": "Fully enclosed acoustic glass suite for 4–12 people with private whiteboard walls and server racks."},
            {"title": "Virtual Business Address", "tag": "$89/mo", "desc": "Prestigious commercial postal address, secure mail forwarding, and discounted conference room booking."}
        ],
        "contact": {
            "address": "720 S Colorado Blvd, Denver, CO 80246",
            "phone": "+1 (303) 555-0158",
            "email": "community@thehivecollective.co",
            "hours": "24/7 Access for Members | Staffed Mon–Fri 8am–6pm"
        }
    },
    {
        "id": "site_brewery_hop_craft_brewing",
        "name": "Hop & Barrel Brewing Co.",
        "tagline": "Bold Unfiltered IPAs and Barrel-Aged Imperial Stouts",
        "type": "brewery",
        "prefix": "hb",
        "primary": "#1a1614",
        "accent": "#ea580c",
        "accent_hover": "#c2410c",
        "surface": "#26201c",
        "heading_font": "Barlow Condensed",
        "body_font": "Inter",
        "cta": "Explore Taplist",
        "hero_sub": "Independent grain-to-glass brewery featuring 24 rotating taps, wood-fired sourdough pizzas, and an open dog-friendly beer garden.",
        "section_name": "Current Taplist",
        "section_id": "taplist",
        "items": [
            {"title": "Citra Haze Double NEIPA", "tag": "8.2% ABV", "desc": "Triple dry-hopped with Citra, Mosaic, and Galaxy hops. Unfiltered mango, papaya, and citrus aromatics."},
            {"title": "Bourbon Cask Imperial Stout", "tag": "11.5% ABV", "desc": "Aged 14 months in Kentucky rye barrels with Madagascar vanilla beans and toasted cacao nibs."},
            {"title": "Pacific Northwest Pine Pilsner", "tag": "5.1% ABV", "desc": "Crisp German pilsner malt lagered cold for 8 weeks with delicate herbal and noble pine hop bitterness."},
            {"title": "Raspberry Marionberry Wild Sour", "tag": "6.4% ABV", "desc": "Oak foeder-fermented wild ale conditioned on 200 lbs of fresh Willamette Valley berries."}
        ],
        "contact": {
            "address": "1204 Industrial Way, Austin, TX 78702",
            "phone": "+1 (512) 555-0163",
            "email": "taproom@hopandbarrelbrewing.com",
            "hours": "Tue–Thu: 3pm–10pm | Fri–Sat: 12pm–12am | Sun: 12pm–8pm"
        }
    },
    {
        "id": "site_interior_lumina_living",
        "name": "Lumina Living Studio",
        "tagline": "Organic Minimalism and Bespoke Residential Architecture",
        "type": "interior_design",
        "prefix": "ll",
        "primary": "#191919",
        "accent": "#e2b170",
        "accent_hover": "#c99552",
        "surface": "#262626",
        "heading_font": "Cinzel",
        "body_font": "Inter",
        "cta": "View Portfolio",
        "hero_sub": "Transforming spaces through tactile natural stones, hand-finished lime plaster walls, and custom Japanese-Nordic millwork.",
        "section_name": "Signature Projects",
        "section_id": "projects",
        "items": [
            {"title": "The Tribeca Penthouse", "tag": "New York", "desc": "4,200 sqft full-floor loft balancing raw poured concrete columns with bleached white oak flooring."},
            {"title": "Carmel Coastal Retreat", "tag": "California", "desc": "Dune-facing sanctuary featuring floor-to-ceiling travertine fireplaces and custom bronze lighting."},
            {"title": "Kitsilano Modern Villa", "tag": "Vancouver", "desc": "Biophilic family home with central indoor maple atrium, shoji-inspired screens, and radiant basalt floors."},
            {"title": "Aspen Mountain Chalet", "tag": "Colorado", "desc": "Contemporary timber chalet integrating reclaimed cedar beams, wool textiles, and sculptural brass fixtures."}
        ],
        "contact": {
            "address": "342 W 14th St, Floor 4, New York, NY 10014",
            "phone": "+1 (212) 555-0133",
            "email": "studio@luminaliving.design",
            "hours": "By Private Consultation Mon–Fri"
        }
    },
    {
        "id": "site_music_neon_sound_fest",
        "name": "Neon Sound Festival",
        "tagline": "3 Nights of Immersive Electronic and Holographic Music",
        "type": "festival",
        "prefix": "ns",
        "primary": "#090814",
        "accent": "#06b6d4",
        "accent_hover": "#0891b2",
        "surface": "#121124",
        "heading_font": "Space Grotesk",
        "body_font": "Inter",
        "cta": "Buy Festival Passes",
        "hero_sub": "Over 60 world-class live acts and visual artists across 4 stages with spatial audio dome soundscapes and kinetic laser shows.",
        "section_name": "Headlining Stages",
        "section_id": "stages",
        "items": [
            {"title": "The Cyber Dome", "tag": "Stage 01", "desc": "360-degree spatial L-Acoustics array with real-time reactive AI visual projections and synthwave headliners."},
            {"title": "Subterranean Bass Hall", "tag": "Stage 02", "desc": "Industrial warehouse acoustics engineered for heavy analog sub-bass, experimental dubstep, and glitch art."},
            {"title": "Solstice Outdoor Arena", "tag": "Stage 03", "desc": "Open-air lakeside amphitheater for sunset melodic techno, live orchestral electronica, and drone shows."},
            {"title": "Ambient Chill Sanctuary", "tag": "Stage 04", "desc": "Binaural meditation dome with zero-gravity hammocks, herbal elixir bars, and modular synth live jams."}
        ],
        "contact": {
            "address": "Desert Oasis Grounds, Indio, CA 92201",
            "phone": "+1 (760) 555-0195",
            "email": "tickets@neonsoundfest.com",
            "hours": "Festival Dates: October 16–18, 2026 | Gates Open 2pm Daily"
        }
    },
    {
        "id": "site_accounting_apex_advisory",
        "name": "Apex Advisory Partners",
        "tagline": "Modern Fractional CFO and Tax Strategy for Scale",
        "type": "accounting",
        "prefix": "aa",
        "primary": "#0a1322",
        "accent": "#38bdf8",
        "accent_hover": "#0284c7",
        "surface": "#132138",
        "heading_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "cta": "Request Audit",
        "hero_sub": "Empowering Series A through C technology founders with automated real-time financial models, R&D tax credit capture, and Board audit readiness.",
        "section_name": "Advisory Capabilities",
        "section_id": "services",
        "items": [
            {"title": "Fractional CFO & Runway Modeling", "tag": "Strategic", "desc": "Multi-scenario cash burn forecasting, capital allocation roadmaps, and investor board deck preparation."},
            {"title": "R&D Tax Credit Optimization", "tag": "Tax", "desc": "Maximizing federal and state research incentives to reclaim up to $250k annually against payroll taxes."},
            {"title": "Automated Cloud Accounting", "tag": "Operations", "desc": "Full QuickBooks and NetSuite migration with automated Stripe reconciliation and multi-currency ledgers."},
            {"title": "SOC 1 & GAAP Audit Prep", "tag": "Compliance", "desc": "Rigorous balance sheet substantiation, revenue recognition (ASC 606), and external auditor management."}
        ],
        "contact": {
            "address": "111 W Washington St, Suite 1800, Chicago, IL 60602",
            "phone": "+1 (312) 555-0188",
            "email": "partners@apexadvisorycfo.com",
            "hours": "Mon–Fri: 8:30am–5:30pm CST"
        }
    }
]

# We will programmatically generate 40 additional domain entries to reach 50 unique domains.
ADDITIONAL_DOMAINS_DATA = [
    ("site_photography_elena_voss", "Elena Voss Photography", "Editorial, Fashion and High-End Portraiture", "photography", "ev", "#121214", "#fafafa", "#d4d4d8", "#222226", "Cinzel", "Inter", "Book Editorial", "Featured Portfolios", "portfolios", [("Haute Couture Paris", "Runway", "Backstage and front-row fashion documentation."), ("The Coastal Series", "Landscape", "35mm analog prints of windswept Icelandic cliffs."), ("Architectural Silhouettes", "Commercial", "Clean lines and stark shadows for global design houses."), ("Intimate Studio Portraits", "Editorial", "Monochrome character studies captured on medium format film.")]),
    ("site_spa_serene_lotus_wellness", "Serene Lotus Sanctuary", "Hydrotherapy, Thermal Baths, and Japanese Onsen", "spa", "sl", "#141d1a", "#2dd4bf", "#0d9488", "#1f2e2a", "Cinzel", "Inter", "Reserve Experience", "Therapeutic Rituals", "rituals", [("Hot Spring Hydrotherapy", "90 min", "Mineral-rich soaking pools with guided breathwork."), ("Aromatherapy Herbal Massage", "60 min", "Wild mountain botanicals and heated river basalt stones."), ("Bamboo Charcoal Sauna", "45 min", "Infrared detoxification and contrast ice bath plunge."), ("Rejuvenating Pearl Facial", "75 min", "Organic marine collagen infusion and lymphatic sculpting.")]),
    ("site_solar_helios_clean_energy", "Helios Clean Energy", "Residential Battery Storage and Rooftop Solar", "solar", "he", "#0a1520", "#eab308", "#ca8a04", "#132333", "Plus Jakarta Sans", "Inter", "Get Solar Quote", "Solar Solutions", "solutions", [("High-Efficiency Monocrystalline Panels", "25yr Warranty", "Sleek all-black panels boasting 22.8% energy conversion."), ("Smart Lithium Home Battery", "13.5 kWh", "Instant backup power during grid blackouts with app controls."), ("EV Supercharger Integration", "Level 2 Fast", "Direct clean solar charging for electric vehicles."), ("Commercial Micro-Grid Systems", "Custom", "Zero-downtime decentralized solar for industrial warehouses.")]),
    ("site_cybersecurity_aegis_shield", "Aegis Zero-Trust Security", "AI Threat Telemetry and Cloud Infrastructure Defense", "cybersecurity", "az", "#070b14", "#6366f1", "#4f46e5", "#101626", "Space Grotesk", "Inter", "Deploy Platform", "Security Architecture", "platform", [("Identity & Behavioral IAM", "Zero Trust", "Continuous biometric and contextual risk authentication."), ("Cloud Workload Protection", "Kubernetes", "Real-time anomaly detection inside containerized clusters."), ("Automated Ransomware Killswitch", "Endpoint", "Kernel-level file encryption blocking in under 12 milliseconds."), ("24/7 Managed SOC Telemetry", "Enterprise", "Human and machine threat hunting monitoring 10M+ events/sec.")]),
    ("site_barbershop_iron_shears", "Iron & Shears Parlour", "Traditional Straight-Razor Shaves and Scissor Cuts", "barbershop", "is", "#1a1614", "#d97706", "#b45309", "#27211e", "Barlow Condensed", "Inter", "Book Appointment", "Grooming Menu", "services", [("Signature Scissor Cut & Style", "$45", "Precision haircut with hot towel neck shave and tonic massage."), ("Traditional Straight-Razor Shave", "$40", "Pre-shave essential oils, warm lather, and cold stone finish."), ("Beard Sculpting & Conditioning", "$30", "Crisp line definition, shears tapering, and beard butter treatment."), ("The Executive Combo Experience", "$70", "Full haircut, complete hot-lather shave, and facial scrub.")]),
    ("site_optometry_clarity_eye_studio", "Clarity Eye Studio", "Handcrafted Acetate Eyewear and Vision Health", "optometry", "ce", "#0c1b24", "#0ea5e9", "#0284c7", "#152c3b", "Outfit", "Inter", "Book Eye Exam", "Eyewear Collections", "collections", [("Titanium Featherweight Series", "Japan Made", "Laser-cut Japanese titanium frames weighing only 12 grams."), ("Vintage Block Acetate", "Italian Craft", "Bio-acetate cured for 6 months with custom 7-barrel hinges."), ("Advanced Wavefront Eye Exam", "Diagnostic", "Digital retina topography measuring optical aberrations."), ("Blue-Light Anti-Glare Optics", "Precision", "Scratch-resistant coated lenses engineered for heavy screen use.")]),
    ("site_catering_savory_roots", "Savory Roots Catering", "Organic Farm-to-Table Dining for Weddings and Galas", "catering", "sr", "#181c14", "#84cc16", "#65a30d", "#252b1f", "Cinzel", "Inter", "Request Tasting", "Seasonal Menus", "menus", [("Wild Morel & Duck Confit", "Canapés", "Crispy polenta bites with caramelized shallot marmalade."), ("Pan-Seared Pacific Halibut", "Mains", "Spring pea purée, roasted baby leeks, and Meyer lemon emulsion."), ("Braised Wagyu Beef Short Rib", "Mains", "Truffled parsnip mash with heritage blackberry demi-glace."), ("Cardamom Poached Pear Tart", "Dessert", "Almond sablé crust with whipped goat cheese mascarpone.")]),
    ("site_florist_botanica_atelier", "Botanica Floral Atelier", "Sculptural Botanical Arrangements and Events", "florist", "ba", "#181416", "#f43f5e", "#e11d48", "#272024", "Cinzel", "Inter", "Order Floral Design", "Signature Arrangements", "arrangements", [("The Ikebana Minimalist", "$120", "Architectural branches, single heirloom peonies, and raku ceramic vase."), ("Meadow Wildflower Centerpiece", "$180", "Lush garden roses, chamomile, Queen Anne's lace, and eucalyptus."), ("Monochrome Dahlia Cascade", "$210", "Deep burgundy dinnerplate dahlias with cascading amaranthus."), ("Bespoke Wedding Arch Installation", "Custom", "Floor-to-ceiling dried florals, pampas grass, and live orchids.")]),
    ("site_cleaning_spark_clean_co", "SparkClean Facilities", "Eco-Friendly Commercial & High-Rise Office Janitorial", "cleaning", "sc", "#081924", "#38bdf8", "#0284c7", "#102a3d", "Plus Jakarta Sans", "Inter", "Get Facility Quote", "Commercial Solutions", "services", [("Nightly Green Janitorial", "Daily Service", "Non-toxic HEPA vacuuming, surface sanitation, and waste sorting."), ("Commercial Carpet Deep Extraction", "Periodic", "Hot-water extraction neutralizing stains and deep allergens."), ("High-Rise Exterior Window Washing", "Specialized", "OSHA-compliant rope-access glass cleaning for glass facades."), ("Post-Construction Terminal Clean", "Turnkey", "Complete dust abatement and scrubbing ready for tenant handover.")]),
    ("site_logistics_vanguard_freight", "Vanguard Global Freight", "Air, Sea, and Rail Intermodal Supply Chain Logistics", "logistics", "vg", "#0a1324", "#2563eb", "#1d4ed8", "#121f3b", "Inter", "Inter", "Track Shipment", "Logistics Networks", "network", [("Ocean Cargo Container Shipping", "Full & LCL", "Global direct sailings with automated customs broker clearing."), ("Expedited Next-Flight Cargo", "Air Freight", "Guaranteed time-definite cargo charters and bonded warehousing."), ("Intermodal Cross-Country Rail", "Dry & Reefers", "Cost-effective temperature-controlled long-haul transport."), ("API Supply Chain Visibility", "Software", "Real-time satellite GPS tracking with container temperature alerts.")]),
    ("site_hotel_azure_cove_resort", "Azure Cove Beach Resort", "Secluded Oceanfront Villas with Private Infinity Pools", "hospitality", "ac", "#0b1b28", "#38bdf8", "#0284c7", "#132d42", "Cinzel", "Inter", "Reserve Suite", "Private Villas", "suites", [("Cliffside Sunset Pavilion", "2,400 sqft", "Panoramic sea views, private plunge pool, and butler service."), ("Overwater Coral Bungalow", "1,800 sqft", "Glass floor viewing panels and direct ladder into the lagoon."), ("The Presidential Beach Villa", "5,200 sqft", "4 private master suites, chef's kitchen, and private cabana."), ("Secluded Garden Sanctuary", "1,500 sqft", "Open-air outdoor stone rain showers and lush tropical garden.")]),
    ("site_gaming_nova_strike_studios", "Nova Strike Studios", "Indie Cyberpunk ARPG and Immersive Simulations", "gaming", "ns", "#080812", "#8b5cf6", "#7c3aed", "#131326", "Space Grotesk", "Inter", "Wishlist on Steam", "Active Games", "titles", [("Neon Syndicate: 2088", "ARPG", "Fast-paced isometric hack-and-slash with neural augmentation."), ("Void Walker Chronicles", "Roguelite", "Procedural gravity-shifting space derelict exploration."), ("Chrono Surge Tactics", "Turn-Based", "Deep deterministic combat with timeline-manipulating heroes."), ("Zero Horizon VR", "Simulation", "Photorealistic planetary atmospheric flight physics.")]),
    ("site_mental_health_mindful_pathways", "Mindful Pathways Therapy", "Integrative Psychotherapy and Emotional Healing", "therapy", "mp", "#121d1a", "#14b8a6", "#0d9488", "#1a2c27", "Cinzel", "Inter", "Book Initial Intake", "Clinical Specialties", "specialties", [("Cognitive Behavioral Therapy (CBT)", "Individual", "Evidence-based strategies to unlearn negative cognitive spirals."), ("EMDR Trauma Processing", "Specialized", "Bilateral eye movement desensitization for PTSD and trauma."), ("Couples Emotionally Focused Therapy", "Relationship", "De-escalating recurring conflict and rebuilding secure attachment."), ("Mindfulness Stress Reduction", "Group Series", "Breathwork and somatic techniques to regulate the nervous system.")]),
    ("site_recruiting_talent_forge", "TalentForge Search Partners", "Retained Executive and Engineering Talent Placement", "recruiting", "tf", "#0c1322", "#6366f1", "#4f46e5", "#131e36", "Plus Jakarta Sans", "Inter", "Hire Top Talent", "Search Practices", "practices", [("VP & C-Suite Executive Search", "Leadership", "Vetting board-level CTOs, CMOs, and VPs of Engineering."), ("AI & Machine Learning Researchers", "Specialized", "Connecting frontier labs with PhD scientists in PyTorch & CUDA."), ("Full-Stack Platform Engineers", "Growth Teams", "Senior distributed systems engineers and product developers."), ("Post-Offer Talent Onboarding", "Advisory", "Structured 90-day retention and executive coaching roadmaps.")]),
    ("site_print_shop_press_and_paper", "Press & Paper Studio", "Artisan Foil Stamping and Vintage Letterpress", "print_shop", "pp", "#1c1815", "#fbbf24", "#d97706", "#29241f", "Cinzel", "Inter", "Order Sample Pack", "Print Techniques", "techniques", [("Deep Impression Letterpress", "100% Cotton", "Hand-cranked 1950s Heidelberg presses creating deep tactile indentations."), ("Metallic Hot Foil Stamping", "Luxury Foil", "Mirrored gold, copper, and holographic foil fused with heat."), ("Precision Custom Die-Cutting", "Specialty", "Bespoke curves, rounded corners, and structural packaging sleeves."), ("Hand-Gilded Colored Edges", "Finishing", "Matte color and foil edge gilding on ultra-thick 600gsm stock.")]),
    ("site_winery_valle_di_pietra", "Valle di Pietra Estate", "Estate-Grown Biodynamic Wines and Hillside Vines", "winery", "vp", "#1c1116", "#be185d", "#9d174d", "#2b1b22", "Cinzel", "Inter", "Shop Allocations", "Current Vintages", "vintages", [("2021 Reserve Cabernet Sauvignon", "96 Points", "French oak aged 22 months. Notes of cassis, graphite, and violet."), ("2023 Estate Old-Vine Chardonnay", "94 Points", "Native yeast fermentation with crisp brioche and green apple minerality."), ("2022 Hillside Syrah", "95 Points", "Whole-cluster pressed with black peppercorn, blackberry, and smoked meat."), ("Late Harvest Botrytis Semillon", "Dessert", "Golden nectar featuring candied apricot, wild honeycomb, and bright acidity.")]),
    ("site_roofer_summit_shield_roofing", "Summit Shield Roofing", "Commercial Metal Roofing and Storm Restoration", "roofing", "ss", "#0f151e", "#f97316", "#ea580c", "#18212e", "Barlow Condensed", "Inter", "Get Free Roof Drone Scan", "Roofing Services", "services", [("Standing Seam Architectural Metal", "50yr Life", "Zero-exposed fastener metal panels resistant to 140mph winds."), ("Impact-Resistant Class 4 Shingles", "Storm Proof", "Hail-rated asphalt shingles qualifying for major insurance discounts."), ("Commercial TPO Flat Roof Systems", "Commercial", "Heat-welded waterproof membranes for energy-efficient flat roofs."), ("Emergency Tarping & Drone Inspection", "24/7 Response", "High-res thermal drone scans detecting subsurface water intrusion.")]),
    ("site_dentistry_pearl_dental_spa", "Pearl Aesthetic Dentistry", "Cosmetic Veneers, Clear Aligners, and Smile Makeovers", "dentistry", "pd", "#0a1924", "#06b6d4", "#0891b2", "#122838", "Outfit", "Inter", "Book Smile Consult", "Smile Treatments", "treatments", [("Handcrafted Porcelain Veneers", "Cosmetic", "Ultra-thin custom porcelain shells correcting shape and spacing."), ("Invisalign Clear Aligners", "Orthodontics", "Discreet orthodontic tooth straightening monitored via 3D scanning."), ("Laser Teeth Brightening", "Whitening", "Safe in-office laser activation brightening smiles up to 8 shades in 60m."), ("Guided Ceramic Dental Implants", "Restorative", "Biocompatible zirconia implants permanently replacing missing teeth.")]),
    ("site_plumbing_flow_pro_services", "FlowPro Master Plumbers", "24/7 Emergency Drain Clearing and Tankless Water Heaters", "plumbing", "fp", "#0e1824", "#0284c7", "#0369a1", "#152538", "Inter", "Inter", "Call Emergency Dispatch", "Plumbing Services", "services", [("24/7 Emergency Leak Repair", "Rapid Response", "Slab leak detection and burst pipe repairs dispatched in under 45m."), ("Hydro-Jetting & Drain Snaking", "Rooter", "High-pressure 4000 PSI water blasting eliminating stubborn grease & roots."), ("Tankless Water Heater Installation", "Energy Efficient", "Endless instant hot water with Navien and Rinnai gas units."), ("Trenchless Sewer Line Replacement", "No-Dig", "Cured-in-place pipe lining restoring cracked sewers without digging yards.")]),
    ("site_crypto_zenith_vault", "Zenith Institutional Vault", "Multi-Signature MPC Custody and On-Chain Staking", "crypto_custody", "zv", "#070b13", "#10b981", "#059669", "#111b2b", "Space Grotesk", "Inter", "Open Custody Account", "Security Architecture", "security", [("Threshold Multi-Party Computation (MPC)", "Hardware Isolation", "Eliminating single points of failure with distributed private key shares."), ("Segregated Institutional Cold Storage", "$500M Insured", "Bank-grade underground bunker vaults protected against physical & cyber coercion."), ("Native Proof-of-Stake Delegations", "High Yield", "Zero-slashing verified staking validators across Ethereum, Solana, and Cosmos."), ("Programmatic Automated Treasury API", "REST / Webhooks", "Whitelisted address routing with multi-tier managerial approval policies.")]),
    ("site_jewelry_aurelia_fine_gems", "Aurelia Ethical Fine Jewelry", "Lab-Grown Diamonds and Bespoke Recycled Gold Rings", "jewelry", "au", "#161317", "#e0b0ff", "#c084fc", "#241f26", "Cinzel", "Inter", "Design Custom Ring", "Fine Collections", "collections", [("The Solitaire Engagement Ring", "Certified VVS1", "Hand-set lab-grown oval diamond in 18k recycled yellow gold."), ("Pavé Diamond Tennis Bracelet", "4.5 Carats", "Seamless continuous sparkle featuring lab diamonds set in platinum."), ("Eternity Wedding Bands", "Custom Fit", "Shared-prong brilliant cut diamonds calibrated for daily comfort."), ("Bespoke Bridal Commission", "One-of-a-Kind", "Collaborate directly with master goldsmiths from sketch to 3D wax model.")]),
    ("site_martial_arts_ronin_bjj", "Ronin Martial Arts Academy", "Brazilian Jiu-Jitsu, Muay Thai, and Submission Grappling", "martial_arts", "ro", "#121214", "#dc2626", "#b91c1c", "#1f1f24", "Barlow Condensed", "Inter", "Claim Free Trial Class", "Academy Programs", "programs", [("Adult Brazilian Jiu-Jitsu (Gi)", "All Levels", "Fundamental positional control, escapes, guard passing, and submissions."), ("No-Gi Submission Grappling", "Advanced", "Wrestling takedowns, leg locks, and rapid transitional pressure."), ("Authentic Muay Thai Striking", "Cardio & Technique", "Dutch kickboxing combinations, heavy bag circuits, and clinch sparring."), ("Youth Champions Martial Arts", "Ages 5–14", "Bully prevention, discipline, self-defense, and balance fundamentals.")]),
    ("site_bookstore_the_inkwell_shelf", "The Inkwell Rare Books", "First Edition Classics, Antiquarian Maps, and Literary Cafe", "bookstore", "iw", "#1c1613", "#d97706", "#b45309", "#2b221d", "Cinzel", "Inter", "Browse Catalog", "Rare Volumes", "volumes", [("F. Scott Fitzgerald First Editions", "1925 Scribner", "Original cloth bindings in remarkably preserved collector condition."), ("Hand-Illuminated Medieval Folios", "15th Century", "Vellum manuscripts painted with gold leaf and lapis lazuli pigments."), ("18th Century Cartography & Atlases", "Antique Maps", "Copperplate engraved hand-colored navigational charts of the Americas."), ("Signed Literary Modernism", "Rare Author Inscriptions", "Authenticated signatures from Hemingway, Woolf, Joyce, and Baldwin.")]),
    ("site_landscaping_terra_verve", "TerraVerve Landscapes", "Drought-Resilient Outdoor Living and Architectural Hardscapes", "landscaping", "tv", "#101d16", "#22c55e", "#16a34a", "#1b2e23", "Plus Jakarta Sans", "Inter", "Request Site Design", "Landscape Disciplines", "disciplines", [("Architectural Paver Patios & Firepits", "Hardscapes", "Permeable bluestone paving with integrated natural gas fire features."), ("Native Xeriscape Plantings", "Water-Wise", "Drought-tolerant ornamental grasses, lavender, and drip irrigation."), ("Custom Outdoor Kitchens & Pergolas", "Outdoor Living", "Built-in stainless grills, pizza ovens, and cedar timber shade structures."), ("Low-Voltage LED Landscape Lighting", "Illumination", "Subtle warm-wash illumination highlighting specimen trees and pathways.")]),
    ("site_auto_detailing_apex_ceramic", "Apex Ceramic Studio", "Multi-Stage Paint Correction and Self-Healing PPF Film", "detailing", "ap", "#0f0f12", "#ef4444", "#dc2626", "#1c1c21", "Barlow Condensed", "Inter", "Reserve Detail Slot", "Protection Packages", "packages", [("Two-Stage Paint Correction", "Mirror Finish", "Compounding and jeweling polish removing 90%+ of swirl marks and scratches."), ("9H Ceramic Nano-Coating", "5yr Warranty", "Ultra-hydrophobic ceramic glass coating repelling water, dirt, and UV rays."), ("Full Front Paint Protection Film (PPF)", "Self-Healing", "Optically clear polyurethane shield protecting bumper, hood, and mirrors."), ("Concourse Interior Restoration", "Deep Detail", "Steam cleaning, leather ceramic protection, and ozone odor elimination.")]),
    ("site_insurance_shield_harbor", "Shield Harbor Marine Insurance", "Commercial Hull, Superyacht, and Cargo Risk Protection", "insurance", "sh", "#0a1626", "#38bdf8", "#0284c7", "#12253d", "Merriweather", "Inter", "Request Marine Quote", "Coverage Policies", "policies", [("Luxury Yacht Hull & Machinery", "Agreed Value", "Comprehensive worldwide navigation coverage including tender and crew liability."), ("Commercial Cargo in Transit", "Ocean & Air", "All-risk cargo protection covering warehouse-to-warehouse international freight."), ("Marina & Shipyard Operator Liability", "Commercial", "Pollution indemnity, ship repairer legal liability, and storm surge damage."), ("Crew Healthcare & P&I Coverage", "Protection & Indemnity", "Medical evacuation and maritime employer liability for international crews.")]),
    ("site_pottery_earth_and_kiln", "Earth & Kiln Studio", "Handmade Functional Stoneware and Pottery Classes", "pottery", "ek", "#191512", "#f59e0b", "#d97706", "#27211d", "Cinzel", "Inter", "Book Potter's Wheel Class", "Studio Offerings", "offerings", [("Beginner Wheel Throwing Workshop", "3hr Intensive", "Hands-on guidance centering clay, opening, and pulling cylinder forms."), ("Handmade Stoneware Tableware", "Ceramic Shop", "Microwave and dishwasher-safe speckled clay dinner plates and mugs."), ("Wood-Fired Anagama Kiln Residencies", "Master Class", "48-hour continuous wood firings creating natural ash glaze patinas."), ("Monthly Open Studio Membership", "24/7 Access", "Dedicated shelf space, studio glazes, and unlimited high-fire kiln firings.")]),
    ("site_moving_smooth_move_logistics", "SmoothMove Elite Movers", "White-Glove Residential Moving and Climate-Controlled Storage", "moving", "sm", "#0d1824", "#0ea5e9", "#0284c7", "#142538", "DM Sans", "Inter", "Get Instant Moving Estimate", "Moving Services", "services", [("White-Glove Luxury Moving", "Full Service", "Full packing with custom wooden crating for fine art, mirrors, and pianos."), ("Interstate Long-Distance Moving", "Coast-to-Coast", "Guaranteed direct delivery dates without multi-client truck sharing."), ("Climate-Controlled Vault Storage", "Secure Storage", "Private wooden vault containers inside 24/7 guarded, humidity-regulated hubs."), ("Office & Commercial Relocation", "Business Moving", "Weekend technology disconnect, rolling server racks, and desk reassembly.")]),
    ("site_apparel_terra_wear", "TerraWear Sustainable Activewear", "Performance Sportswear from Regenerated Ocean Plastics", "apparel", "tw", "#101814", "#10b981", "#059669", "#182620", "Outfit", "Inter", "Shop Sustainable Drop", "Core Performance Gear", "collection", [("Aero-Weave Running Shorts", "$68", "Lightweight four-way stretch recycled poly with anti-chafing compression liner."), ("Thermal Meridian Training Hoodie", "$118", "Brushed organic bamboo fleece providing thermoregulation and odor resistance."), ("High-Impact Seamless Leggings", "$88", "Squat-proof compression knit crafted from retrieved deep-ocean fishing nets."), ("Weatherproof Summit Shell Jacket", "$198", "Breathable 3-layer waterproof membrane made with 100% recycled nylon.")]),
    ("site_museum_metropolitan_modern", "Metropolitan Digital Art Hall", "Immersive Audio-Visual Exhibits and Interactive Holography", "museum", "mm", "#080711", "#d946ef", "#c026d3", "#131024", "Space Grotesk", "Inter", "Reserve Timed Entry", "Current Exhibitions", "exhibitions", [("Infinite Horizons: Light in Void", "Gallery 01", "Laser light refractions creating floating geometric optical illusions."), ("Synthetic Dreams & Artificial Mind", "Gallery 02", "Autonomous generative video environments reacting to visitor heartbeats."), ("Resonance: Spatial Sound Labyrinth", "Gallery 03", "128-speaker ambisonic acoustic chambers exploring vibrational meditation."), ("The Quantum Canvas Experience", "Gallery 04", "Interactive touchscreens allowing visitors to paint with fluid particle physics.")]),
    ("site_pest_control_eco_guard", "EcoGuard Botanical Defense", "Non-Toxic Pest Exclusion and Organic Perimeter Defense", "pest_control", "eg", "#0f1c14", "#4ade80", "#22c55e", "#192e21", "Plus Jakarta Sans", "Inter", "Schedule Inspection", "Pest Solutions", "solutions", [("Botanical Barrier Home Perimeter", "Child & Pet Safe", "Organic essential oil barrier keeping ants, spiders, and roaches out."), ("Structural Rodent Proofing", "Permanent", "Sealing foundational entry points with heavy gauge steel mesh & copper wire."), ("Eco-Friendly Termite Interception", "Monitoring", "Subterranean baiting stations eliminating colonies without pumping chemical poisons."), ("Mosquito & Tick Yard Misting", "Seasonal", "Garlic and thyme oil micro-fogging drastically cutting biting insect counts.")]),
    ("site_charter_blue_horizon_sailing", "Blue Horizon Yacht Charters", "Private Crewed Catamarans and Virgin Island Sailing", "sailing", "bh", "#081729", "#00d2d3", "#00b4b5", "#10233b", "Cinzel", "Inter", "Book Yacht Charter", "Charter Fleet", "fleet", [("Lagoon 52 Luxury Catamaran", "Up to 8 Guests", "Air-conditioned staterooms, onboard chef, tender boat, and paddleboards."), ("Sunseeker 65 Sport Yacht", "Day Charters", "High-speed cruising with flybridge sunbeds and hydraulic swim platform."), ("Bavaria 46 Monohull Cruiser", "Bareboat", "Pure sailing performance equipped with twin helms and Raymarine radar."), ("All-Inclusive VIP Island Package", "Weekly Charter", "Custom gourmet dining, open bar, provisioning, and professional captain.")]),
    ("site_tutoring_quant_masters", "QuantMasters Academy", "Olympiad Math, Physics, and Competitive Algorithmic Coding", "tutoring", "qm", "#091224", "#6366f1", "#4f46e5", "#121e38", "Space Grotesk", "Inter", "Take Diagnostic Assessment", "Academy Tracks", "curriculum", [("Mathematical Olympiad Prep", "AMC 10/12 & AIME", "Number theory, combinatorics, and synthetic Euclidean geometry proofs."), ("AP & Competitive Physics", "Mechanics & E&M", "Calculus-based physics mastery with experimental problem-solving labs."), ("USACO Algorithmic Coding", "Silver to Platinum", "Dynamic programming, graph algorithms, and segment trees in C++ and Python."), ("Ivy League STEM Admissions Mentorship", "Advisory", "Guiding high schoolers in independent peer-reviewed STEM research publications.")]),
    ("site_coffee_roasters_elevation_roast", "Elevation Roastery", "High-Altitude Volcanic Specialty Coffee and Tasting Flights", "coffee", "er", "#191310", "#ea580c", "#c2410c", "#291f1a", "Barlow Condensed", "Inter", "Shop Whole Bean", "Single-Origin Lots", "coffees", [("Ethiopia Yirgacheffe Natural", "$22 / 12oz", "Heirloom varietal with jasmine floral aroma, bergamot, and sweet blueberry."), ("Colombia Huila Pink Bourbon", "$24 / 12oz", "Anaerobic honey process yielding crisp guava, passionfruit, and panela sugar."), ("Guatemala Antigua Washed", "$20 / 12oz", "Volcanic soil cultivation with dark chocolate, candied almond, and orange peel."), ("Nitro Cold Brew Keg Service", "Commercial", "Creamy draft nitro cold brew delivered weekly to modern tech offices.")]),
    ("site_security_sentinel_patrol", "Sentinel Protective Services", "Autonomous Drone Surveillance and Executive Close Protection", "security", "sp", "#0a111a", "#eab308", "#ca8a04", "#132130", "Inter", "Inter", "Request Security Assessment", "Protection Tiers", "tiers", [("Autonomous Thermal Drone Patrols", "Perimeter", "Automated scheduled drone flyovers with AI optical intrusion alerts."), ("Executive Close Protection Details", "Armed Escort", "Former military special forces bodyguards for dignitaries and executives."), ("Access Control & CCTV Integration", "Smart Systems", "Biometric facial scanning, turnstile control, and cloud-monitored video."), ("Rapid Armed Response Vehicles", "24/7 Mobile", "Guaranteed under-10-minute on-site dispatch during triggered alarm events.")]),
    ("site_tattoo_sacred_ink_collective", "Sacred Ink Tattoo Studio", "Fine-Line Micro Realism and Custom Botanical Blackwork", "tattoo", "si", "#111114", "#d4d4d8", "#a1a1aa", "#1c1c21", "Cinzel", "Inter", "Submit Tattoo Inquiry", "Resident Artists", "artists", [("Master Kai: Micro Realism", "Portraits & Animals", "Photorealistic wildlife and classical sculpture tattoos rendered with fine needles."), ("Elena S: Botanical Fine-Line", "Florals & Flora", "Delicate anatomical botanical illustrations with soft charcoal stippling."), ("Marcus Cole: Japanese Neo-Trad", "Dragons & Waves", "Bold dynamic waves, irezumi mythology, and sweeping sleeve compositions."), ("Sterile Single-Use Studio Standards", "Hospital Grade", "Hospital-grade autoclaves, 100% vegan organic inks, and medical aftercare.")]),
    ("site_cinema_the_starlight_indie", "The Starlight Picturehouse", "35mm Analog Screenings, Cult Cinema, and Cocktail Bar", "cinema", "sl", "#140c11", "#f43f5e", "#e11d48", "#24151e", "Cinzel", "Inter", "Reserve Cinema Seats", "Now Showing", "films", [("2001: A Space Odyssey (70mm)", "Kubrick Classic", "Original 70mm roadshow print with restored six-track magnetic audio."), ("Blade Runner: The Final Cut", "Sci-Fi Cult", "Neon-drenched cyberpunk masterpiece presented with custom bourbon cocktails."), ("Chungking Express (35mm)", "Wong Kar-wai", "Vibrant 1994 Hong Kong romance film screened on original 35mm stock."), ("Midnight Shadow Horror Club", "Double Feature", "Late-night analog screenings of 1970s Italian Giallo and psychological horror.")]),
    ("site_bakery_gluten_free_crumbles", "Crumbles Dedicated Bakery", "100% Certified Gluten-Free Breads and Celebration Cakes", "gf_bakery", "cb", "#191510", "#d97706", "#b45309", "#27211a", "Outfit", "Inter", "Order Custom Cake", "Daily Gluten-Free Menu", "menu", [("Artisan Artisan Sourdough Loaf", "$11.00", "Certified celiac safe sourdough with crunchy blistered crust and soft crumb."), ("Salted Caramel Celebration Cake", "$55.00", "Fluffy vanilla sponge layered with house-made salted caramel and buttercream."), ("Cinnamon Pecan Sticky Rolls", "$5.50", "Warm brioche-style rolls baked with maple glaze and toasted Georgia pecans."), ("Savory Cheddar Chive Scones", "$4.75", "Flaky aged sharp cheddar scones brushed with melted garlic herb butter.")]),
    ("site_event_space_the_foundry_loft", "The Foundry Urban Loft", "Historic 1920s Brick Warehouse Wedding and Gala Venue", "venue", "fo", "#141414", "#d4af37", "#b89628", "#222222", "Cinzel", "Inter", "Schedule Venue Tour", "Event Spaces", "spaces", [("The Main Grand Brick Atrium", "Up to 350 Guests", "Original 30ft timber ceilings, exposed brick arches, and iron chandeliers."), ("The Open-Air Rooftop Terrace", "Up to 150 Guests", "Panoramic city skyline views with fire pits and built-in copper bar."), ("Bridal Dressing Suite", "Private Lounge", "Full-length lighted mirrors, velvet furnishings, and private champagne bar."), ("Chef's Commercial Prep Kitchen", "Catering Ready", "Industrial stainless steel prep stations and walk-in refrigeration for caterers.")]),
    ("site_medtech_pulse_biometrics", "Pulse Biometrics Systems", "Wearable Continuous Biomarker and Glucose Telemetry", "medtech", "pb", "#06101c", "#06b6d4", "#0891b2", "#0f1e30", "Space Grotesk", "Inter", "Request Clinical Trial", "Diagnostic Hardware", "hardware", [("Non-Invasive Micro-Needle Sensor", "Clinical Grade", "Continuous interstitial glucose and lactate tracking with 14-day wear time."), ("Sub-Second Bluetooth Sync", "Mobile App", "Real-time biometric telemetry stream sent directly to patient and physician apps."), ("AI Metabolic Trend Analysis", "Predictive", "Algorithms identifying hypoglycemic dips and cardiovascular spikes hours early."), ("HIPAA Compliant Cloud Dashboard", "EHR Integrated", "Direct HL7 FHIR sync into Epic, Cerner, and hospital electronic health systems.")])
]


ADDITIONAL_CONTACTS = {
    "site_photography_elena_voss": {
        "address": "420 Gallery Row, Studio 3B, New York, NY 10011",
        "phone": "+1 (212) 555-0145",
        "email": "studio@elenavossphoto.com",
        "hours": "Tue–Sat: 10am–6pm by Appointment"
    },
    "site_spa_serene_lotus_wellness": {
        "address": "770 Onsen Spring Way, Calistoga, CA 94515",
        "phone": "+1 (707) 555-0182",
        "email": "sanctuary@serenelotusspa.com",
        "hours": "Daily: 8am–9pm (Reservations Required)"
    },
    "site_solar_helios_clean_energy": {
        "address": "1500 Sunburst Boulevard, Phoenix, AZ 85004",
        "phone": "+1 (602) 555-0193",
        "email": "solutions@helioscleanenergy.com",
        "hours": "Mon–Fri: 7am–6pm | Sat: 8am–2pm"
    },
    "site_cybersecurity_aegis_shield": {
        "address": "600 Cyber Defense Parkway, Reston, VA 20190",
        "phone": "+1 (703) 555-0128",
        "email": "soc@aegiszerotrust.com",
        "hours": "24/7 Global Threat Operations Center"
    },
    "site_barbershop_iron_shears": {
        "address": "88 Vintage Mill Lane, Nashville, TN 37203",
        "phone": "+1 (615) 555-0164",
        "email": "chair@ironshearsparlour.com",
        "hours": "Tue–Fri: 9am–7pm | Sat: 8am–5pm"
    },
    "site_optometry_clarity_eye_studio": {
        "address": "320 Beacon Optical Ave, Boston, MA 02116",
        "phone": "+1 (617) 555-0176",
        "email": "care@clarityeyestudio.com",
        "hours": "Mon–Fri: 8:30am–5:30pm | Sat: 9am–1pm"
    },
    "site_catering_savory_roots": {
        "address": "512 Farmstead Road, Sonoma, CA 95476",
        "phone": "+1 (707) 555-0139",
        "email": "events@savoryrootscatering.com",
        "hours": "Mon–Fri: 9am–5pm (Tastings by Appt)"
    },
    "site_florist_botanica_atelier": {
        "address": "190 Petal Lane, Charleston, SC 29401",
        "phone": "+1 (843) 555-0152",
        "email": "blooms@botanicaatelier.com",
        "hours": "Tue–Sat: 9am–6pm"
    },
    "site_cleaning_spark_clean_co": {
        "address": "820 Sanitation Way, Minneapolis, MN 55403",
        "phone": "+1 (612) 555-0187",
        "email": "dispatch@sparkcleanfacilities.com",
        "hours": "24/7 Facility Response & Operations"
    },
    "site_logistics_vanguard_freight": {
        "address": "1400 Intermodal Blvd, Newark, NJ 07114",
        "phone": "+1 (973) 555-0124",
        "email": "customs@vanguardfreight.com",
        "hours": "24/7 Intermodal Fleet Dispatch"
    },
    "site_hotel_azure_cove_resort": {
        "address": "1000 Oceanfront Palisades, Big Sur, CA 93920",
        "phone": "+1 (831) 555-0144",
        "email": "concierge@azurecoveresort.com",
        "hours": "Daily: 24-Hour Concierge & Guest Reception"
    },
    "site_gaming_nova_strike_studios": {
        "address": "880 Cyberway Boulevard, Suite 500, Austin, TX 78701",
        "phone": "+1 (512) 555-0189",
        "email": "community@novastrikestudios.com",
        "hours": "Mon–Fri: 10am–7pm CST"
    },
    "site_mental_health_mindful_pathways": {
        "address": "452 Peaceful Oaks Drive, Boulder, CO 80302",
        "phone": "+1 (303) 555-0177",
        "email": "intake@mindfulpathwaystherapy.com",
        "hours": "Mon–Thu: 8am–7pm | Fri: 9am–3pm"
    },
    "site_recruiting_talent_forge": {
        "address": "500 Howard Street, Floor 14, San Francisco, CA 94105",
        "phone": "+1 (415) 555-0192",
        "email": "partners@talentforgesearch.com",
        "hours": "Mon–Fri: 8:30am–5:30pm PST"
    },
    "site_print_shop_press_and_paper": {
        "address": "72 Kraft Mill Road, Beacon, NY 12508",
        "phone": "+1 (845) 555-0163",
        "email": "orders@pressandpaperstudio.com",
        "hours": "Tue–Sat: 9am–5pm EST"
    },
    "site_winery_valle_di_pietra": {
        "address": "2100 Oak Knoll Trail, Napa, CA 94558",
        "phone": "+1 (707) 555-0131",
        "email": "tasting@valledipietraestate.com",
        "hours": "Thu–Sun: 10am–5pm (Reservations Only)"
    },
    "site_roofer_summit_shield_roofing": {
        "address": "1240 Industrial Parkway, Denver, CO 80216",
        "phone": "+1 (720) 555-0185",
        "email": "service@summitshieldroofing.com",
        "hours": "24/7 Emergency Storm Dispatch"
    },
    "site_dentistry_pearl_dental_spa": {
        "address": "880 Biscayne Bay Blvd, Miami, FL 33132",
        "phone": "+1 (305) 555-0148",
        "email": "appointments@pearldentalspa.com",
        "hours": "Mon–Fri: 7:30am–6pm | Sat: 8am–1pm"
    },
    "site_plumbing_flow_pro_services": {
        "address": "615 Pipeline Road, Chicago, IL 60607",
        "phone": "+1 (312) 555-0129",
        "email": "dispatch@flowproplumbers.com",
        "hours": "24/7 Rapid Emergency Response"
    },
    "site_crypto_zenith_vault": {
        "address": "40 Wall Street, 48th Floor, New York, NY 10005",
        "phone": "+1 (212) 555-0160",
        "email": "institutional@zenithvault.com",
        "hours": "Mon–Fri: 9am–6pm EST (Vault 24/7)"
    },
    "site_jewelry_aurelia_fine_gems": {
        "address": "724 5th Avenue, Suite 900, New York, NY 10019",
        "phone": "+1 (212) 555-0174",
        "email": "concierge@aureliafinegems.com",
        "hours": "Tue–Sat: 10am–6pm by Private Appointment"
    },
    "site_martial_arts_ronin_bjj": {
        "address": "310 Combat Way, San Diego, CA 92101",
        "phone": "+1 (619) 555-0155",
        "email": "oss@roninbjjacademy.com",
        "hours": "Mon–Fri: 6am–9pm | Sat: 8am–2pm"
    },
    "site_bookstore_the_inkwell_shelf": {
        "address": "45 Folio Square, Boston, MA 02116",
        "phone": "+1 (617) 555-0138",
        "email": "curator@theinkwellshelf.com",
        "hours": "Mon–Sat: 10am–8pm | Sun: 11am–6pm"
    },
    "site_landscaping_terra_verve": {
        "address": "840 Evergreen Terrace, Seattle, WA 98103",
        "phone": "+1 (206) 555-0196",
        "email": "design@terravervelandscapes.com",
        "hours": "Mon–Fri: 7am–5pm | Sat: 8am–12pm"
    },
    "site_auto_detailing_apex_ceramic": {
        "address": "1550 Speedcraft Lane, Scottsdale, AZ 85260",
        "phone": "+1 (480) 555-0167",
        "email": "booking@apexceramicstudio.com",
        "hours": "Mon–Sat: 8am–6pm"
    },
    "site_insurance_shield_harbor": {
        "address": "300 Harborview Quay, Annapolis, MD 21401",
        "phone": "+1 (410) 555-0122",
        "email": "underwriting@shieldharbormarine.com",
        "hours": "Mon–Fri: 8am–5pm EST (Claims 24/7)"
    },
    "site_pottery_earth_and_kiln": {
        "address": "180 Kiln Fire Alley, Asheville, NC 28801",
        "phone": "+1 (828) 555-0149",
        "email": "studio@earthandkiln.com",
        "hours": "Wed–Sun: 10am–6pm"
    },
    "site_moving_smooth_move_logistics": {
        "address": "920 Transport Blvd, Atlanta, GA 30318",
        "phone": "+1 (404) 555-0171",
        "email": "quotes@smoothmovemovers.com",
        "hours": "Mon–Sat: 7am–7pm | Sun: 8am–4pm"
    },
    "site_apparel_terra_wear": {
        "address": "60 Eco Strand Way, Santa Monica, CA 90401",
        "phone": "+1 (310) 555-0183",
        "email": "support@terrawearactive.com",
        "hours": "Daily: 10am–7pm PST"
    },
    "site_museum_metropolitan_modern": {
        "address": "250 Innovation Plaza, Cambridge, MA 02142",
        "phone": "+1 (617) 555-0115",
        "email": "tickets@metropolitanmodernart.org",
        "hours": "Tue–Sun: 10am–9pm | Closed Mondays"
    },
    "site_pest_control_eco_guard": {
        "address": "410 Green Shield Court, Raleigh, NC 27601",
        "phone": "+1 (919) 555-0134",
        "email": "dispatch@ecoguarddefense.com",
        "hours": "Mon–Fri: 7:30am–6pm | Sat: 8am–2pm"
    },
    "site_charter_blue_horizon_sailing": {
        "address": "12 Marina Cay Dock, Charlotte Amalie, VI 00802",
        "phone": "+1 (340) 555-0158",
        "email": "captain@bluehorizonsailing.com",
        "hours": "Daily: 8am–7pm AST"
    },
    "site_tutoring_quant_masters": {
        "address": "700 University Avenue, Palo Alto, CA 94301",
        "phone": "+1 (650) 555-0127",
        "email": "admissions@quantmastersacademy.com",
        "hours": "Mon–Sun: 9am–9pm PST"
    },
    "site_coffee_roasters_elevation_roast": {
        "address": "330 Bean Mill Road, Portland, OR 97214",
        "phone": "+1 (503) 555-0191",
        "email": "beans@elevationroastery.com",
        "hours": "Daily: 6:30am–4:30pm"
    },
    "site_security_sentinel_patrol": {
        "address": "1100 Defense Highway, McLean, VA 22102",
        "phone": "+1 (703) 555-0166",
        "email": "operations@sentinelprotectiveservices.com",
        "hours": "24/7 Monitoring & Tactical Response"
    },
    "site_tattoo_sacred_ink_collective": {
        "address": "82 Needlecraft Alley, Brooklyn, NY 11211",
        "phone": "+1 (718) 555-0142",
        "email": "booking@sacredinktattoo.com",
        "hours": "Tue–Sun: 12pm–8pm"
    },
    "site_cinema_the_starlight_indie": {
        "address": "640 Cinema Parkway, Los Angeles, CA 90028",
        "phone": "+1 (323) 555-0179",
        "email": "boxoffice@starlightpicturehouse.com",
        "hours": "Daily: 1pm–11:30pm"
    },
    "site_bakery_gluten_free_crumbles": {
        "address": "220 Celiac Safe Boulevard, Minneapolis, MN 55401",
        "phone": "+1 (612) 555-0137",
        "email": "bakery@crumblesdedicatedbakery.com",
        "hours": "Tue–Sat: 7am–3pm | Sun: 8am–1pm"
    },
    "site_event_space_the_foundry_loft": {
        "address": "1920 Brick Foundry Way, Detroit, MI 48226",
        "phone": "+1 (313) 555-0188",
        "email": "events@thefoundryurbanloft.com",
        "hours": "By Appointment (Events: Thu–Sun)"
    },
    "site_medtech_pulse_biometrics": {
        "address": "950 BioTech Parkway, San Diego, CA 92121",
        "phone": "+1 (858) 555-0153",
        "email": "clinical@pulsebiometrics.com",
        "hours": "Mon–Fri: 8am–5pm PST"
    }
}

# Convert ADDITIONAL_DOMAINS_DATA into full domain dicts
for entry in ADDITIONAL_DOMAINS_DATA:
    d_id, d_name, d_tagline, d_type, d_prefix, d_prim, d_acc, d_acc_hov, d_surf, d_head, d_body, d_cta, d_sec_name, d_sec_id, d_items = entry
    DOMAINS.append({
        "id": d_id,
        "name": d_name,
        "tagline": d_tagline,
        "type": d_type,
        "prefix": d_prefix,
        "primary": d_prim,
        "accent": d_acc,
        "accent_hover": d_acc_hov,
        "surface": d_surf,
        "heading_font": d_head,
        "body_font": d_body,
        "cta": d_cta,
        "hero_sub": f"Dedicated to {d_tagline.lower()}, delivering highest-caliber standards, transparent pricing, and world-class client service.",
        "section_name": d_sec_name,
        "section_id": d_sec_id,
        "items": [{"title": title, "tag": tag, "desc": desc} for title, tag, desc in d_items],
        "contact": ADDITIONAL_CONTACTS.get(d_id, {
            "address": f"100 Grand Avenue, Suite 400, Metropolitan City, NY 10001",
            "phone": "+1 (800) 555-0199",
            "email": f"contact@{d_id.replace('site_', '').replace('_', '')}.com",
            "hours": "Mon–Fri: 8am–6pm | Sat: 9am–2pm"
        })
    })



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
    "site_bakery_golden_crumb": "grid",
    "site_law_vance_holloway": "editorial",
    "site_travel_wanderlust_expeditions": "timeline",
    "site_vet_paws_claws_hospital": "grid",
    "site_podcast_the_future_syntax": "split_hero",
    "site_coworking_the_hive_collective": "tabs",
    "site_brewery_hop_craft_brewing": "editorial",
    "site_interior_lumina_living": "bento",
    "site_music_neon_sound_fest": "timeline",
    "site_accounting_apex_advisory": "split_hero",
    "site_photography_elena_voss": "editorial",
    "site_spa_serene_lotus_wellness": "tabs",
    "site_solar_helios_clean_energy": "timeline",
    "site_cybersecurity_aegis_shield": "bento",
    "site_barbershop_iron_shears": "grid",
    "site_optometry_clarity_eye_studio": "split_hero",
    "site_catering_savory_roots": "editorial",
    "site_florist_botanica_atelier": "grid",
    "site_cleaning_spark_clean_co": "timeline",
    "site_logistics_vanguard_freight": "bento",
    "site_hotel_azure_cove_resort": "tabs",
    "site_gaming_nova_strike_studios": "split_hero",
    "site_mental_health_mindful_pathways": "editorial",
    "site_recruiting_talent_forge": "tabs",
    "site_print_shop_press_and_paper": "editorial",
    "site_winery_valle_di_pietra": "timeline",
    "site_roofer_summit_shield_roofing": "grid",
    "site_dentistry_pearl_dental_spa": "tabs",
    "site_plumbing_flow_pro_services": "split_hero",
    "site_crypto_zenith_vault": "bento",
    "site_jewelry_aurelia_fine_gems": "editorial",
    "site_martial_arts_ronin_bjj": "timeline",
    "site_bookstore_the_inkwell_shelf": "editorial",
    "site_landscaping_terra_verve": "grid",
    "site_auto_detailing_apex_ceramic": "split_hero",
    "site_insurance_shield_harbor": "bento",
    "site_pottery_earth_and_kiln": "timeline",
    "site_moving_smooth_move_logistics": "tabs",
    "site_apparel_terra_wear": "bento",
    "site_museum_metropolitan_modern": "editorial",
    "site_pest_control_eco_guard": "grid",
    "site_charter_blue_horizon_sailing": "tabs",
    "site_tutoring_quant_masters": "timeline",
    "site_coffee_roasters_elevation_roast": "grid",
    "site_security_sentinel_patrol": "bento",
    "site_tattoo_sacred_ink_collective": "editorial",
    "site_cinema_the_starlight_indie": "split_hero",
    "site_bakery_gluten_free_crumbles": "tabs",
    "site_event_space_the_foundry_loft": "split_hero",
    "site_medtech_pulse_biometrics": "bento"
}

DOMAIN_DESCRIPTIONS = {
    "site_bakery_golden_crumb": "Handcrafted sourdough loaves, French viennoiserie, and seasonal pastries baked fresh daily with stone-ground heritage flours.",
    "site_law_vance_holloway": "Trial-tested intellectual property litigation, federal patent defense, and strategic counsel for high-growth technology enterprises.",
    "site_travel_wanderlust_expeditions": "Immersive small-group wildlife expeditions and luxury eco-lodges guided by expert field biologists across seven continents.",
    "site_vet_paws_claws_hospital": "Advanced veterinary surgical care, preventive medicine, and 24/7 emergency treatments for beloved companion animals.",
    "site_podcast_the_future_syntax": "Deep technical conversations with language creators, systems architects, and compiler engineers shaping tomorrow's software.",
    "site_coworking_the_hive_collective": "Flexible private offices, ergonomic hot desks, and tech-enabled collaboration suites tailored for agile teams and founders.",
    "site_brewery_hop_craft_brewing": "Small-batch hazy IPAs, barrel-aged wild sours, and crisp Bavarian lagers brewed on-site with Pacific Northwest hops.",
    "site_interior_lumina_living": "Bespoke architectural interiors, custom millwork, and sustainable residential spatial design for discerning homeowners.",
    "site_music_neon_sound_fest": "Three days of boundary-pushing electronic music, immersive spatial light installations, and world-class live producers.",
    "site_accounting_apex_advisory": "Strategic fractional CFO leadership, R&D tax credit monetization, and institutional audit preparation for venture-backed startups.",
    "site_photography_elena_voss": "High-fashion editorial documentation, haute couture runway collections, and intimate medium-format monochrome portraiture.",
    "site_spa_serene_lotus_wellness": "Holistic geothermal soaking pools, botanical herbal aromatherapy, and traditional Japanese hot spring thermal therapies.",
    "site_solar_helios_clean_energy": "Tier-1 monocrystalline rooftop solar installations, residential battery storage, and smart micro-grid energy management.",
    "site_cybersecurity_aegis_shield": "Kernel-level endpoint protection, automated ransomware neutralization, and 24/7 managed detection and response telemetry.",
    "site_barbershop_iron_shears": "Master straight-razor hot lather shaves, precision scissor cuts, and luxury beard conditioning in a classic heritage parlour.",
    "site_optometry_clarity_eye_studio": "Handcrafted Japanese titanium frames, precision digital wavefront diagnostics, and bespoke anti-reflective prescription lenses.",
    "site_catering_savory_roots": "Farm-to-table seasonal menus, artisanal canap\u00e9s, and full-service event dining crafted with organic heirloom ingredients.",
    "site_florist_botanica_atelier": "Architectural botanical arrangements, sculptural Ikebana installations, and bespoke event florals sourced from local growers.",
    "site_cleaning_spark_clean_co": "Eco-certified commercial office sanitation, HEPA air purification, and rope-access exterior architectural window washing.",
    "site_logistics_vanguard_freight": "Time-critical international air charters, intermodal temperature-controlled rail, and automated customs clearance logistics.",
    "site_hotel_azure_cove_resort": "Private oceanfront villas, personal infinity plunge pools, and tailored culinary experiences along pristine coastal waters.",
    "site_gaming_nova_strike_studios": "Adrenaline-fueled cyberpunk action RPGs and narrative simulations developed with cutting-edge procedural rendering.",
    "site_mental_health_mindful_pathways": "Evidence-based cognitive behavioral therapy, trauma-informed EMDR, and mindfulness-based stress reduction practices.",
    "site_recruiting_talent_forge": "Retained executive search and specialized engineering placements for fast-growing frontier technology companies.",
    "site_print_shop_press_and_paper": "Traditional letterpress impression printing, metallic hot foil stamping, and hand-gilded paper goods on heavy cotton stock.",
    "site_winery_valle_di_pietra": "Estate-grown biodynamic hillside vintages fermented with native yeasts and aged in French oak barrels.",
    "site_roofer_summit_shield_roofing": "Standing-seam architectural metal roofs, impact-resistant shingles, and commercial flat roof thermoplastic membranes.",
    "site_dentistry_pearl_dental_spa": "Minimally invasive porcelain veneers, discreet clear aligner orthodontics, and restorative ceramic implantology.",
    "site_plumbing_flow_pro_services": "Rapid-response emergency drain clearing, trenchless sewer replacement, and high-efficiency tankless water heating systems.",
    "site_crypto_zenith_vault": "Institutional multi-party computation custody, offline deep bunker cold storage, and programmatic treasury orchestration.",
    "site_jewelry_aurelia_fine_gems": "Certified lab-grown diamond solitaires, conflict-free gemstones, and bespoke heirloom jewelry cast in recycled 18k gold.",
    "site_martial_arts_ronin_bjj": "Authentic Brazilian Jiu-Jitsu, submission grappling, and Dutch-style Muay Thai striking taught by world-class champions.",
    "site_bookstore_the_inkwell_shelf": "First edition antiquarian literature, rare hand-illuminated folios, and historical cartography curated for serious collectors.",
    "site_landscaping_terra_verve": "Drought-tolerant native plant architecture, bluestone paver patios, and integrated outdoor living environments.",
    "site_auto_detailing_apex_ceramic": "Multi-stage rotary paint correction, 9H nano-ceramic coatings, and self-healing clear paint protection film installations.",
    "site_insurance_shield_harbor": "Comprehensive commercial marine hull insurance, worldwide superyacht coverage, and international cargo transit protection.",
    "site_pottery_earth_and_kiln": "Hand-thrown functional stoneware ceramics, atmospheric wood-fired kilns, and hands-on wheel throwing workshops.",
    "site_moving_smooth_move_logistics": "White-glove residential relocations, custom fine-art crating, and humidity-controlled private vault storage.",
    "site_apparel_terra_wear": "High-performance technical activewear crafted from regenerated ocean polymers and certified organic bamboo fibers.",
    "site_museum_metropolitan_modern": "Immersive digital light exhibits, interactive responsive holography, and multi-channel spatial audio environments.",
    "site_pest_control_eco_guard": "Non-toxic botanical perimeter exclusion, organic pest prevention, and structural rodent defense for health-conscious homes.",
    "site_charter_blue_horizon_sailing": "Crewed luxury catamaran charters, secluded Caribbean island itineraries, and private gourmet onboard culinary service.",
    "site_tutoring_quant_masters": "Rigorous Olympiad mathematics, university-level physics labs, and competitive algorithmic problem solving mentorship.",
    "site_coffee_roasters_elevation_roast": "High-altitude single-origin microlots roasted to order with precision thermodynamic profiling and cupping scores.",
    "site_security_sentinel_patrol": "Autonomous thermal drone patrol systems, biometric perimeter access, and executive close protection details.",
    "site_tattoo_sacred_ink_collective": "Fine-line micro-realism, botanical blackwork, and custom Neo-Japanese illustrative tattoo compositions.",
    "site_cinema_the_starlight_indie": "Archival 35mm and 70mm analog film screenings, cult cinematic retrospectives, and handcrafted craft cocktails.",
    "site_bakery_gluten_free_crumbles": "Certified gluten-free artisan sourdough, tiered celebration cakes, and morning pastries prepared in a dedicated facility.",
    "site_event_space_the_foundry_loft": "Restored 1920s timber and brick warehouse event space featuring panoramic skyline views for weddings and galas.",
    "site_medtech_pulse_biometrics": "Wearable continuous metabolic telemetry, clinical-grade interstitial sensors, and encrypted EHR telemetry streams."
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
      <div className="{p}-hero__atmosphere" aria-hidden="true" />
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

.{p}-hero__atmosphere {{
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
          <div className="{p}-hero__backdrop" aria-hidden="true" />
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

.{p}-hero__backdrop {{
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
    output_path = Path("site_trajectories_batch4.jsonl")
    data_output_path = Path("data/site_trajectories_batch4.jsonl")
    print("=" * 70)
    print("      GENERATING BATCH 4: 50 GOLD-STANDARD SITE TRAJECTORIES        ")
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
