"""Write a fixed, never-trained set of website briefs for blinded visual review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data/eval/visual_holdout_v1.jsonl"

# Each case specifies a different information architecture and a real interaction.
# These prompts are evaluation inputs, never SFT targets.
CASES = [
    ("ecommerce", "Aster & Kiln ceramics", "collection-led storefront with glaze stories, product detail, care guide and studio notes", "Filter by vessel type and add an item to a shared cart; show honest checkout-unavailable messaging", "warm editorial photography, clay textures, restrained hover motion"),
    ("ecommerce", "Northline cycling parts", "technical catalog with compatibility finder, comparison table, product specifications and repair journal", "Filter parts by bike standard and keep the selection when navigating to a product", "precision typography, annotated diagrams, quiet dark accents"),
    ("ecommerce", "Morrow Seed Library", "seasonal seed shop with growing calendar, seed details, regional advice and basket", "Filter by growing zone and season; update basket count across the header and listing", "botanical illustration, paper grain, gentle scroll reveals"),
    ("portfolio", "Mina Okafor, set designer", "case-study portfolio with production credits, process sketches, biography and inquiry", "Open each project case study and return to the same gallery position", "theatrical editorial layout, large imagery, deliberate text reveals"),
    ("portfolio", "Luis Park, data journalist", "story-led portfolio with featured investigations, methods, talks and contact", "Switch project topics without losing article links", "newspaper hierarchy, expressive charts, modest motion"),
    ("portfolio", "Tess Armand, furniture maker", "material-first portfolio with object index, workshop process, commissions and availability", "Filter works by material and open accessible detail dialogs", "quiet gallery art direction, tactile closeups, subtle parallax"),
    ("editorial", "Tide Atlas coastal journal", "issue cover, long-form features, regional archive, contributors and newsletter explanation", "Filter stories by coastline and make all article links resolve", "magazine typography, strong image crops, slow reading rhythm"),
    ("editorial", "Signal & Soil climate publication", "data-led lead story, explainers, field reports, author pages and issue archive", "Switch topic tabs and preserve readable charts on mobile", "clear public-interest visual language, animated chart introductions"),
    ("editorial", "Sunday Table food stories", "recipe feature, seasonal index, chef interviews and pantry notes", "Filter recipes by ingredient and show matching results", "sunlit still-life photography, generous whitespace, restrained micro-interactions"),
    ("arts", "Glasshouse contemporary dance", "season program, production pages, dancer biographies and visit information", "Filter performances by date and open ticket information without claiming purchase", "expressive type, dramatic stage imagery, choreographed scroll reveals"),
    ("arts", "Lumen printmaking collective", "exhibition index, artist profiles, workshop calendar and membership", "Switch exhibition views and reveal practical booking details", "ink texture, asymmetrical grid, accessible image captions"),
    ("arts", "Night Archive sound museum", "listening exhibits, collection map, oral histories and accessibility information", "Select an exhibit and update its transcript panel", "immersive dark gallery, waveform motifs, reduced-motion-safe transitions"),
    ("civic", "Eastbank public library", "services dashboard, branch hours, event calendar, research help and accessibility", "Filter events by branch and show current selection in the result count", "trustworthy civic design, clear hierarchy, high contrast"),
    ("civic", "River Ward mobility plan", "project timeline, proposal map, meeting schedule, documents and feedback steps", "Switch proposal phases and keep document links valid", "map-led public information, plain language, no decorative obstruction"),
    ("civic", "Oakfield community garden", "plot availability, volunteer tasks, seasonal notices and visitor guidance", "Filter tasks by date and show a usable inquiry form", "neighborhood warmth, real schedules, modest scroll motion"),
    ("events", "Common Ground design festival", "schedule-first festival site with speakers, venues, session detail and travel", "Filter sessions by day and discipline; save selections locally", "energetic identity, poster typography, smooth timeline transitions"),
    ("events", "Dawn Chorus city run", "route details, wave schedule, accessibility, volunteer roles and FAQs", "Choose distance and update route, start time and preparation advice", "outdoor photography, clear wayfinding, reduced-motion-aware counters"),
    ("events", "Afterglow film week", "film lineup, venue guide, director conversations and passes information", "Filter screenings by venue and date without dead links", "cinematic stills, bold type, controlled reveal timing"),
    ("education", "Open Bench woodworking school", "course pathways, class detail, instructor profiles, workshop safety and enrollment inquiry", "Filter classes by skill level and reveal prerequisites", "workshop documentary imagery, instructional clarity, tactile accents"),
    ("education", "Bright Current ocean science", "age-based learning paths, field activities, educator resources and glossary", "Switch learner age and update activity recommendations", "scientific illustration, playful but accurate diagrams, gentle motion"),
    ("hospitality", "Casa Nube mountain inn", "rooms, seasonal experiences, dining, location and booking inquiry", "Switch room type and update amenities and price explanation", "calm landscape photography, refined typography, subtle parallax"),
    ("hospitality", "Sable House city hotel", "room index, neighborhood guide, meeting spaces, dining and accessibility", "Filter rooms by capacity and make inquiry actions functional", "architectural photography, clean luxury, low-motion fallback"),
    ("healthcare", "Harbor Pediatric Therapy", "services, care team, first-visit process, insurance guidance and contact", "Switch service categories and show clear appointment-request steps", "reassuring color, excellent readability, no invented clinical claims"),
    ("healthcare", "Northfield Community Clinic", "care programs, locations, hours, patient resources and urgent guidance", "Filter locations and update hours and contact details", "accessible civic-health design, plain language, restrained transitions"),
    ("dashboard", "Transit reliability desk", "operations overview, route health, incident timeline and service metrics", "Filter routes and time periods; update all visible metric cards coherently", "dense but legible information design, purposeful chart motion"),
    ("dashboard", "Studio inventory console", "stock overview, material table, reorder alerts and supplier activity", "Filter materials and keep summary totals synchronized", "practical professional interface, strong focus states, no fake live data"),
    ("unfamiliar", "A taxonomy of imaginary weather", "exploratory atlas of invented weather phenomena with field notes, index and specimen pages", "Filter phenomena by altitude and intensity and keep the legend accurate", "scientific-fiction art direction, layered atmospheric motion, readable fallback"),
    ("unfamiliar", "The Museum of Lost Instructions", "exhibition-like archive of obsolete how-to manuals with collections, object notes and visit page", "Search by era and open object details with keyboard support", "archival paper and technical drawings, unusual but usable navigation"),
    ("nonprofit", "City Canopy tree trust", "impact map, planting programs, volunteer calendar, transparent funding and stories", "Filter volunteer opportunities by neighborhood and date", "optimistic environmental identity, documentary images, subtle growth motion"),
    ("nonprofit", "Open Door legal aid", "eligibility guide, service paths, appointment information, language support and resources", "Choose a service path and show relevant next steps without collecting sensitive data", "calm high-trust interface, clear accessibility, minimal animation"),
]


def main() -> None:
    rows = []
    for index, (domain, subject, structure, interaction, art_direction) in enumerate(CASES, 1):
        rows.append({
            "task_id": f"visual_holdout_{index:02d}",
            "family_id": f"visual_holdout_{index:02d}",
            "domain": domain,
            "subject": subject,
            "prompt": (f"Build a complete responsive website for {subject}. Create a {structure}. "
                       f"Required interaction: {interaction}. Art direction: {art_direction}. "
                       "Make it usable at 390px, keyboard accessible, and readable with reduced motion. "
                       "Use specific honest content; do not invent testimonials, payment completion, or live data."),
            "source": "original project-authored evaluation brief",
            "license": "project-owned evaluation use",
        })
    if len(rows) != 30 or len({row["domain"] for row in rows}) != 12:
        raise AssertionError("Visual holdout must have 30 sites across 12 domains")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(json.dumps({"path": str(OUTPUT), "rows": len(rows), "domains": 12, "sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
