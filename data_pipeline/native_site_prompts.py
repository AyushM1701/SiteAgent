"""Deterministic, diverse website briefs for native-section training data.

Each family is one kind of business. Families listed in HOLDOUT_FAMILIES never
appear in training rows; they supply the validation split and the evaluation
prompts, so measured improvements are not memorised prompts.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

CITIES = ["Bristol", "Leeds", "Lisbon", "Austin", "Melbourne", "Toronto", "Dublin", "Glasgow", "Portland", "Copenhagen",
          "Edinburgh", "Manchester", "Brighton", "Denver", "Wellington", "Vancouver", "Cork", "Bath", "Oslo", "Kyoto",
          "Pune", "Bengaluru", "Cape Town", "Seattle", "Montreal", "Utrecht", "Ghent", "Porto", "Valencia", "Hobart"]
STYLES = ["warm and inviting", "minimal and calm", "bold and confident", "editorial with lots of white space",
          "dark and moody", "playful but tidy", "premium and understated", "bright and friendly", "earthy and natural",
          "clean and modern"]
TONES = ["sage and sand tones", "deep navy and brass", "terracotta and cream", "charcoal with a lime accent",
         "soft blush and ink", "forest green and oat", "black and white with one red accent", "ocean blue and white",
         "warm cream and espresso", "plum and gold"]
MOTION = ["gentle scroll reveals", "an animated hero headline", "subtle hover states", "scroll reveals and a calm hero",
          "a subtle WebGL gradient behind the hero", ""]


@dataclass(frozen=True)
class Family:
    id: str
    desc: list[str]
    names: list[str]
    sections: list[str]
    shop: list[tuple[str, str]] | None = None   # products with prices -> cart
    menu: list[str] | None = None               # menu categories
    tiers: list[str] | None = None              # pricing tiers
    items: list[str] | None = None              # explicit work/service names


FAMILIES = [
    Family("bakery", ["an artisan bakery", "a neighbourhood bakery and cafe", "a sourdough bakery"],
           ["Crumb & Co", "Rise Bakehouse", "The Flour Room", "Hearth Loaves", "Golden Crust"],
           ["menu", "our story", "the bakers", "visit us", "FAQ", "shop", "how we bake"],
           shop=[("Sourdough loaf", "£6"), ("Cardamom bun", "£3.50"), ("Rye loaf", "£5"), ("Box of cookies", "£12")],
           menu=["Breads", "Pastries", "Coffee"]),
    Family("coffee", ["a specialty coffee roastery", "a coffee bar", "a small-batch roaster"],
           ["Ember Roasters", "North Bean", "Slow Pour", "Copper Cup", "Daybreak Coffee"],
           ["shop", "our beans", "brewing guides", "subscriptions", "visit us", "FAQ", "wholesale", "menu", "newsletter"],
           shop=[("House espresso 250g", "£11"), ("Ethiopia Guji 250g", "£14"), ("Decaf 250g", "£12"), ("Pour-over kit", "£38")]),
    Family("restaurant", ["a modern Indian restaurant", "a neighbourhood bistro", "a family-run trattoria", "a seafood restaurant"],
           ["Saffron Table", "Little Fig", "Osteria Lume", "Salt & Tide", "The Copper Pan"],
           ["menu", "about", "private dining", "gallery", "contact", "FAQ", "our chef"],
           menu=["Starters", "Mains", "Desserts", "Drinks"]),
    Family("bar", ["a cocktail bar", "a natural wine bar", "a craft beer taproom"],
           ["The Velvet Room", "Wild Pour", "Hop Yard", "Night Owl", "Juniper & Ash"],
           ["drinks menu", "events", "about", "gallery", "visit us", "FAQ", "reviews"],
           menu=["Cocktails", "Wine", "Beer", "Snacks"]),
    Family("yoga", ["a small yoga studio", "a hot yoga studio", "a community yoga space"],
           ["Larkspur Yoga", "Still Point", "Lotus House", "Breathe Studio", "Open Sky Yoga"],
           ["classes", "teachers", "pricing", "timetable", "FAQ", "contact", "workshops", "testimonials", "join"],
           tiers=["Drop-in", "10-class pass", "Monthly unlimited"]),
    Family("gym", ["a strength and conditioning gym", "a boutique fitness studio", "a boxing gym"],
           ["Iron Works", "Pulse Fitness", "Fight Club Gym", "Forge Strength", "Peak Performance"],
           ["programs", "coaches", "pricing", "results", "FAQ", "contact", "facilities", "testimonials", "join"],
           tiers=["Starter", "Committed", "Unlimited"]),
    Family("dentist", ["a family dental practice", "a cosmetic dentistry clinic"],
           ["Brightside Dental", "Smile Studio", "Riverside Dental", "Pearl Dental Care", "Haven Dentistry"],
           ["treatments", "our team", "new patients", "pricing", "FAQ", "contact", "testimonials"],
           tiers=["Check-up", "Hygiene visit", "Whitening"]),
    Family("physio", ["a sports physiotherapy clinic", "a physiotherapy and rehab practice"],
           ["Motion Physio", "Align Clinic", "Restore Physio", "Kinetic Health", "Balance Rehab"],
           ["treatments", "our team", "how it works", "pricing", "FAQ", "contact", "testimonials"]),
    Family("salon", ["a hair salon", "a barber shop", "a nail studio"],
           ["Atelier Hair", "Fade & Co", "Polish Bar", "Mane Street", "The Barber Room"],
           ["services", "stylists", "pricing", "gallery", "FAQ", "contact", "reviews"],
           tiers=["Cut", "Cut & colour", "Full treatment"]),
    Family("spa", ["a day spa", "a wellness retreat", "a massage studio"],
           ["Haven Spa", "Quiet Waters", "Cedar Retreat", "Lumen Wellness", "Stillwater Spa"],
           ["treatments", "packages", "about", "gallery", "FAQ", "contact", "testimonials", "newsletter"]),
    Family("law", ["an employment law firm", "a family law practice", "a small business law firm"],
           ["Hartley & Shaw", "Clearwater Legal", "Mercer Law", "Kingsley Solicitors", "Fairway Legal"],
           ["practice areas", "our lawyers", "how we work", "FAQ", "contact", "case studies", "testimonials"]),
    Family("accounting", ["an accounting firm for freelancers", "a bookkeeping service", "a tax advisory practice"],
           ["Ledger Lane", "Clear Books", "Northside Accounts", "Tally & Co", "Sum Partners"],
           ["services", "pricing", "how it works", "team", "FAQ", "contact", "testimonials"],
           tiers=["Sole trader", "Small company", "Growing business"]),
    Family("agency", ["a branding agency", "a digital product studio", "a marketing agency"],
           ["Northwind Studio", "Fieldwork", "Bright Signal", "Parallel", "Common Thread"],
           ["work", "services", "process", "team", "contact", "clients", "testimonials"],
           items=["Rebrand for a coffee chain", "E-commerce launch", "Museum wayfinding", "Fintech app"]),
    Family("architecture", ["an architecture studio", "an interior design studio", "a landscape architecture practice"],
           ["Aster & Kiln", "Form Studio", "Lineworks", "Atelier North", "Ridge Architects"],
           ["projects", "studio", "process", "awards", "contact", "services"],
           items=["Harbour House", "The Mill Conversion", "Garden Pavilion", "Library Extension"]),
    Family("photography", ["a wedding photographer", "a portrait photographer", "a product photography studio"],
           ["Maya Chen Photography", "Silver Frame", "Golden Hour Studio", "Lens & Light", "Field Notes Photo"],
           ["portfolio", "packages", "about", "testimonials", "FAQ", "contact"],
           tiers=["Elopement", "Half day", "Full day"]),
    Family("saas_analytics", ["a B2B analytics platform", "a product analytics tool", "a dashboard tool for logistics teams"],
           ["Northwind Analytics", "Metricly", "Signal Board", "Tracewise", "Clearview"],
           ["features", "how it works", "pricing", "integrations", "FAQ", "customers", "contact", "product tour", "testimonials", "sign up"],
           tiers=["Starter", "Team", "Enterprise"]),
    Family("devtools", ["a developer tool for API testing", "a CI pipeline service", "an error monitoring tool"],
           ["Hyperforge", "Stackwise", "Pipeline", "Faultline", "Testbed"],
           ["features", "docs", "pricing", "changelog", "FAQ", "contact", "demo", "waitlist"],
           tiers=["Free", "Pro", "Team"]),
    Family("fintech", ["a budgeting app", "a business banking app", "an invoicing tool"],
           ["Mercury Pay", "Penny", "Invoicely", "Ledgerline", "Coinwise"],
           ["features", "security", "pricing", "how it works", "FAQ", "download", "app preview", "testimonials", "waitlist"],
           tiers=["Personal", "Plus", "Business"]),
    Family("ceramics", ["a handmade ceramics studio", "a pottery shop"],
           ["Aster Objects", "Kiln & Clay", "Earthenware Co", "Slip Studio", "Mud & Fire"],
           ["shop", "the studio", "workshops", "care guide", "FAQ", "contact"],
           shop=[("Stoneware mug", "€28"), ("Serving bowl", "€64"), ("Bud vase", "€32"), ("Dinner plate", "€36")]),
    Family("candles", ["a candle and home fragrance shop", "a small-batch candle maker"],
           ["Wick & Wane", "Ember Home", "Slow Flame", "Hearth Candle Co", "Lumen Goods"],
           ["shop", "scents", "our story", "FAQ", "contact", "newsletter", "reviews"],
           shop=[("Fig candle", "$32"), ("Cedar candle", "$32"), ("Reed diffuser", "$44"), ("Gift set", "$70")]),
    Family("plants", ["an indoor plant shop", "a garden centre"],
           ["Greenhouse Co", "Leaf & Root", "The Plant Room", "Fern House", "Wild Botanics"],
           ["shop", "plant care", "workshops", "about", "FAQ", "contact", "newsletter"],
           shop=[("Monstera", "£35"), ("Snake plant", "£22"), ("Pothos", "£14"), ("Terracotta pot", "£12")]),
    Family("skincare", ["a natural skincare brand", "a clean beauty shop"],
           ["Bare Botanics", "Glow Lab", "Petal & Oak", "Pure Form", "Dew Skincare"],
           ["shop", "ingredients", "our story", "reviews", "FAQ", "contact", "newsletter"],
           shop=[("Face oil", "$38"), ("Cleansing balm", "$29"), ("Night cream", "$45"), ("Lip balm", "$9")]),
    Family("bookshop", ["an independent bookshop", "a children's bookshop"],
           ["Paper Lantern Books", "The Margin", "Chapter One", "Inkwell Books", "Story Corner"],
           ["new arrivals", "events", "book club", "visit us", "FAQ", "about", "newsletter", "reviews"]),
    Family("bikes", ["a bicycle shop and repair workshop", "an e-bike shop"],
           ["Spoke & Chain", "Velo Works", "Freewheel", "Cadence Cycles", "Gear Up Bikes"],
           ["shop", "repairs", "pricing", "about", "FAQ", "contact"],
           shop=[("City bike", "€650"), ("Gravel bike", "€1,290"), ("Service", "€60"), ("Helmet", "€55")]),
    Family("music_school", ["a music school", "a piano teacher", "a guitar academy"],
           ["Bright Notes", "Keys Academy", "Six Strings School", "Harmony House", "Tempo Music"],
           ["lessons", "teachers", "pricing", "FAQ", "contact", "recitals", "testimonials"],
           tiers=["Trial lesson", "Monthly", "Term"]),
    Family("tutoring", ["a maths tutoring service", "a language school", "an exam coaching centre"],
           ["Bright Minds", "Lingo Hub", "Top Marks Tutoring", "Clever Fox", "Study Den"],
           ["courses", "tutors", "pricing", "how it works", "FAQ", "contact", "testimonials"],
           tiers=["Single session", "Package of 10", "Intensive"]),
    Family("nonprofit", ["a food bank charity", "an animal rescue", "a community garden project"],
           ["Common Table", "Second Chance Rescue", "Green Patch", "Open Door Trust", "Kind Hands"],
           ["our work", "impact", "volunteer", "donate", "FAQ", "contact"]),
    Family("museum", ["a local history museum", "a contemporary art gallery"],
           ["The Harbour Museum", "Gallery North", "Old Mill Gallery", "Lightbox Art", "The Archive"],
           ["exhibitions", "visit", "events", "about", "FAQ", "contact", "newsletter", "donate"]),
    Family("hotel", ["a boutique hotel", "a seaside B&B", "a mountain lodge"],
           ["The Linden", "Sea Glass Inn", "Pine Ridge Lodge", "Harbour House Hotel", "Juniper Rooms"],
           ["rooms", "amenities", "location", "gallery", "FAQ", "contact", "reviews"],
           tiers=["Classic room", "Deluxe room", "Suite"]),
    Family("travel", ["a walking tour company", "a sailing holiday operator", "a cycling tour company"],
           ["Trailhead Tours", "Blue Water Sailing", "Pedal Routes", "Wild Paths", "Coastline Walks"],
           ["tours", "how it works", "pricing", "guides", "FAQ", "contact", "testimonials"],
           tiers=["Day tour", "Weekend", "Week-long"]),
    Family("plumbing", ["a plumbing and heating company", "an electrician", "a home repair service"],
           ["Flow Plumbing", "Spark Electric", "Fixwell", "Hometown Heating", "Reliable Repairs"],
           ["services", "pricing", "areas we cover", "about", "FAQ", "contact", "reviews"],
           tiers=["Call-out", "Boiler service", "Installation"]),
    Family("cleaning", ["a home cleaning service", "an office cleaning company"],
           ["Sparkle & Co", "Fresh Start Cleaning", "Tidy Homes", "Clean Slate", "Bright Spaces"],
           ["services", "pricing", "how it works", "FAQ", "contact", "reviews"],
           tiers=["One-off clean", "Weekly", "Deep clean"]),
    Family("landscaping", ["a landscaping company", "a garden design studio"],
           ["Green Thumb Gardens", "Terrace & Stone", "Wildflower Design", "Oak Landscapes", "Hedgerow Co"],
           ["services", "projects", "process", "about", "FAQ", "contact"],
           items=["Courtyard garden", "Rooftop terrace", "Meadow planting", "Family garden"]),
    Family("realestate", ["an estate agency", "a property management company"],
           ["Keystone Homes", "Harbour Lettings", "Northgate Property", "Brick & Beam", "Oakwood Estates"],
           ["services", "how it works", "team", "FAQ", "contact", "areas"]),
    Family("portfolio_designer", ["a brand designer's portfolio", "a product designer's portfolio", "an illustrator's portfolio"],
           ["Maya Chen", "Leo Hart", "Priya Nair", "Sam Okafor", "Ines Duarte"],
           ["work", "about", "services", "contact", "process"],
           items=["Packaging for a tea brand", "Banking app redesign", "Festival identity", "Children's book"]),
    Family("portfolio_dev", ["a freelance web developer's portfolio", "a mobile developer's portfolio"],
           ["Alex Rivera", "Noor Khan", "Tom Becker", "Aiko Tanaka", "Ravi Menon"],
           ["projects", "skills", "about", "contact", "process"],
           items=["Booking platform", "Open-source CLI", "Shop rebuild", "Data dashboard"]),
    Family("musician", ["a jazz trio", "a singer-songwriter", "a wedding band"],
           ["The Blue Notes", "Ella Morgan", "Velvet Groove", "June & the Moons", "Brass Tacks"],
           ["music", "shows", "about", "bookings", "FAQ", "contact"]),
    Family("conference", ["a design conference", "a developer meetup", "a food festival"],
           ["Frontier Conf", "Build Week", "Taste of the Harbour", "Signal Summit", "Open Source Days"],
           ["speakers", "schedule", "tickets", "venue", "FAQ", "contact", "newsletter"],
           tiers=["Day pass", "Full pass", "Team pack"]),
    Family("vet", ["a veterinary clinic", "a dog grooming salon", "a pet boarding service"],
           ["Paws & Claws", "Riverside Vets", "The Groom Room", "Happy Tails", "Whisker Lodge"],
           ["services", "our team", "pricing", "FAQ", "contact", "new clients", "reviews"],
           tiers=["Consultation", "Vaccination", "Annual plan"]),
    Family("wedding", ["a wedding planner", "a florist", "a wedding venue"],
           ["Ever After Events", "Petal & Stem", "The Old Barn", "Bloom Studio", "Vow & Co"],
           ["services", "gallery", "packages", "about", "FAQ", "contact", "testimonials"]),
]

HOLDOUT_FAMILIES = {"physio", "candles", "museum", "cleaning", "musician", "devtools"}


def _join(items: list[str]) -> str:
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else items[0]


def build_prompt(family: Family, rng: random.Random) -> dict:
    name = rng.choice(family.names)
    desc = rng.choice(family.desc)
    city = rng.choice(CITIES)
    sections = rng.sample(family.sections, k=min(len(family.sections), rng.randint(4, 6)))
    style = rng.choice(STYLES)
    tone = rng.choice(TONES)
    motion = rng.choice(MOTION)
    domain = "".join(ch for ch in name.lower() if ch.isalnum())[:18] or "studio"
    email = rng.choice(["hello", "info", "studio", "team", "bookings"]) + f"@{domain}." + rng.choice(["com", "co.uk", "co", "studio"])
    extras = []
    display = list(sections)
    menu_key = next((s for s in sections if "menu" in s), None)
    if family.menu and menu_key and rng.random() < 0.85:
        cats = rng.sample(family.menu, k=min(3, len(family.menu)))
        display = [f"{s} ({', '.join(cats)})" if s == menu_key else s for s in display]
    if family.shop and "shop" in sections:
        products = rng.sample(family.shop, k=3)
        extras.append("Products: " + ", ".join(f"{n} {p}" for n, p in products) + ".")
        if rng.random() < 0.6:
            extras.append("Add to cart with a cart count; no online checkout, orders are confirmed by email.")
    if family.items and rng.random() < 0.6:
        key = next((s for s in sections if s in {"work", "projects", "portfolio"}), None)
        if key:
            picks = rng.sample(family.items, k=3)
            display = [f"{s} ({', '.join(picks)})" if s == key else s for s in display]
    if family.tiers and "pricing" in sections and rng.random() < 0.5:
        extras.append("Pricing tiers: " + ", ".join(family.tiers) + ".")
    if rng.random() < 0.25:
        options = ["Do not show prices.", "No booking system yet.", "Do not mention opening hours."]
        if not any(s in {"testimonials", "reviews"} for s in sections):
            options.append("Do not show testimonials.")
        if "pricing" in sections or family.shop:
            options.remove("Do not show prices.")
        extras.append(rng.choice(options))
    template = rng.randrange(4)
    look = f"{style.capitalize()} feel, {tone}" + (f", {motion}" if motion else "") + "."
    if template == 0:
        text = f"{name} — {desc} in {city}. Sections: {', '.join(display)}. {' '.join(extras)} {look} Email {email}."
    elif template == 1:
        text = f"Build a website for {name}, {desc} based in {city}. Include: {', '.join(display)}. {' '.join(extras)} {look} Contact email: {email}."
    elif template == 2:
        text = f"Create a site for {name} ({desc}, {city}). Sections: {', '.join(display)}. {' '.join(extras)} {look} Reach them at {email}."
    else:
        text = f"{desc[0].upper() + desc[1:]} called \"{name}\" in {city}. Sections: {', '.join(display)}. {' '.join(extras)} Visual direction: {style}, {tone}. Email {email}."
    return {"family_id": family.id, "prompt": " ".join(text.split()), "requested_sections": sections}


def section_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def prompt_bank(per_family: int = 5, seed: int = 20261016) -> list[dict]:
    """`per_family` briefs for every family, deterministically, with unique ids."""
    rng = random.Random(seed)
    rows, seen = [], set()
    for family in FAMILIES:
        made = 0
        tries = 0
        while made < per_family and tries < per_family * 20:
            tries += 1
            row = build_prompt(family, rng)
            if row["prompt"] in seen:
                continue
            seen.add(row["prompt"])
            row["id"] = f"{family.id}_{made:02d}"
            row["holdout"] = family.id in HOLDOUT_FAMILIES
            rows.append(row)
            made += 1
    return rows


# Extra sections that force the section kinds the first dataset saw least
# (articles, preview, cart, menu, team, products).
_RARE_SECTIONS = {
    "saas_analytics": ["product tour", "dashboard preview", "blog"], "devtools": ["demo", "changelog", "blog"],
    "fintech": ["app preview", "news"], "bakery": ["cart", "journal", "menu"], "coffee": ["cart", "journal"],
    "restaurant": ["menu", "events", "journal"], "bar": ["events", "news"], "ceramics": ["cart", "journal"],
    "candles": ["cart", "journal"], "plants": ["cart", "blog"], "skincare": ["cart", "journal"],
    "bookshop": ["events", "staff picks", "blog"], "bikes": ["cart", "news"], "museum": ["events", "news"],
    "conference": ["schedule", "news"], "nonprofit": ["news", "team"], "agency": ["journal", "team"],
    "architecture": ["journal", "team"], "yoga": ["team", "journal"], "gym": ["team", "blog"],
    "musician": ["news", "events"], "hotel": ["journal", "team"], "travel": ["journal", "team"],
    "photography": ["journal"], "portfolio_dev": ["blog"], "portfolio_designer": ["journal"],
    "law": ["team", "news"], "accounting": ["team", "blog"], "dentist": ["team", "blog"], "vet": ["team", "news"],
}


def rare_kind_bank(per_family: int = 2, seed: int = 61017) -> list[dict]:
    """Briefs whose section lists always include a rare section kind."""
    rng = random.Random(seed)
    rows = []
    for family in FAMILIES:
        extras = _RARE_SECTIONS.get(family.id)
        if not extras:
            continue
        for n in range(per_family):
            base = build_prompt(family, rng)
            pinned = [e for e in extras if any(w in e for w in ("preview", "demo", "tour", "cart"))][:1]
            others = [e for e in extras if e not in pinned]
            add = pinned + rng.sample(others, k=min(2 - len(pinned), len(others)))
            sections = list(dict.fromkeys(base["requested_sections"] + add))
            prompt = base["prompt"]
            for marker in ("Sections: ", "Include: "):
                if marker in prompt:
                    head, tail = prompt.split(marker, 1)
                    listed, rest = tail.split(". ", 1)
                    prompt = f"{head}{marker}{listed}, {', '.join(add)}. {rest}"
                    break
            else:
                continue
            rows.append({"family_id": family.id, "prompt": prompt, "requested_sections": sections,
                         "id": f"rare_{family.id}_{n:02d}", "holdout": family.id in HOLDOUT_FAMILIES})
    return rows
