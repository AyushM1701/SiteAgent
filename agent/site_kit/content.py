"""Section kinds, model prompts, JSON parsing, integrity filters and fallbacks.

The model writes a small JSON object of copy for one section. Everything here
turns that (possibly broken) output into honest, length-bounded content, and
supplies deterministic copy when the model output is unusable.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from agent.design_leaks import is_design_direction
except ImportError:  # pragma: no cover - script context
    from design_leaks import is_design_direction  # type: ignore

# ── Section kinds ───────────────────────────────────────────────────────────

KIND_PATTERNS: list[tuple[str, str]] = [
    ("header", r"^(?:header|nav|navbar|navigation|masthead|top-bar)$"),
    ("footer", r"\bfooter\b"),
    ("hero", r"\b(?:hero|banner)\b|^cover$"),
    ("cart", r"\b(?:cart|checkout|basket|bag)\b"),
    ("menu", r"\bmenus?\b"),
    ("faq", r"\b(?:faqs?|questions)\b"),
    ("pricing", r"\b(?:pricing|prices|plans|packages|rates|tiers|memberships?)\b"),
    ("quotes", r"\b(?:testimonials?|reviews?|quotes|kind-words|press)\b"),
    ("team", r"\b(?:team|people|instructors|staff|trainers|coaches|doctors|founders|speakers)\b"),
    ("contact", r"\b(?:contact|booking|bookings|reserv\w*|enquir\w*|inquir\w*|visit|hours|location|find-us)\b"),
    ("cta", r"\b(?:newsletter|cta|subscribe|signup|sign-up|join|waitlist|donate)\b"),
    ("preview", r"\b(?:preview|demo|product-tour|dashboard)\b"),
    ("products", r"\b(?:products?|shop|store|collections?|catalog|catalogue|goods|pieces)\b"),
    ("work", r"\b(?:gallery|work|projects?|portfolio|case-stud\w*|lookbook|showcase|properties)\b"),
    ("articles", r"\b(?:blog|journal|notes|stories|news|posts|events|schedule|articles|archives?)\b"),
    ("steps", r"\b(?:process|how-it-works|steps|care|guide|method|journey|timeline|itinerary)\b"),
    ("story", r"\b(?:about|story|chef|founder|studio|mission|philosophy|history|approach|values|heritage|impact)\b"),
    ("features", r"\b(?:features|services|benefits|offerings|amenities|classes|programs|programmes|courses|why|"
                 r"treatments|expertise|stats|skills|capabilities|architecture|specialties)\b"),
]

MODEL_KINDS = {"hero", "features", "steps", "story", "work", "products", "menu", "faq", "articles", "pricing",
               "quotes", "team", "contact", "cta", "preview", "split", "cart"}

MAX_TOKENS = {"hero": 260, "contact": 200, "cta": 160, "cart": 140, "quotes": 160, "menu": 700, "faq": 650,
              "pricing": 560, "story": 520, "split": 480}
DEFAULT_MAX_TOKENS = 480

# kind -> (min, max, ask)
COUNTS = {"features": (3, 6, 3), "work": (3, 6, 4), "products": (3, 8, 4), "steps": (3, 5, 4), "faq": (3, 6, 4),
          "articles": (3, 4, 3), "pricing": (2, 4, 3), "team": (2, 6, 3)}

SHAPES = {
    "hero": '{"headline": "5-9 words", "lede": "18-32 words", "primary_cta": "2-4 words", "secondary_cta": "2-4 words", "tagline": "2-6 words"}',
    "features": '{"title": "...", "intro": "one sentence", "items": [{"title": "2-5 words", "text": "one or two sentences"}]}',
    "steps": '{"title": "...", "intro": "one sentence", "steps": [{"title": "2-5 words", "text": "one or two sentences"}]}',
    "story": '{"title": "...", "paragraphs": ["2-3 sentences", "2-3 sentences"], "highlights": ["2-6 words", "2-6 words", "2-6 words"]}',
    "work": '{"title": "...", "intro": "one sentence", "items": [{"title": "2-6 words", "caption": "one sentence"}]}',
    "products": '{"title": "...", "intro": "one sentence", "items": [{"name": "2-5 words", "description": "one sentence"}]}',
    "menu": '{"title": "...", "intro": "one sentence", "categories": [{"name": "1-3 words", "items": [{"name": "dish name", "description": "under 12 words"}]}]}',
    "faq": '{"title": "...", "intro": "one sentence", "items": [{"q": "question", "a": "1-2 sentence answer"}]}',
    "articles": '{"title": "...", "intro": "one sentence", "items": [{"title": "4-9 words", "excerpt": "one sentence", "tag": "1-2 words"}]}',
    "pricing": '{"title": "...", "intro": "one sentence", "tiers": [{"name": "1-3 words", "description": "one sentence", "features": ["2-5 words", "2-5 words", "2-5 words"]}]}',
    "quotes": '{"title": "...", "intro": "one sentence", "invite": "one sentence inviting feedback"}',
    "team": '{"title": "...", "intro": "one sentence", "members": [{"role": "2-4 words", "text": "one sentence"}]}',
    "contact": '{"title": "...", "text": "1-2 sentences", "button": "2-3 words"}',
    "cta": '{"title": "...", "text": "one sentence", "button": "2-3 words"}',
    "preview": '{"title": "...", "intro": "one sentence", "labels": ["1-2 words", "1-2 words", "1-2 words"], "points": [{"title": "2-5 words", "text": "one sentence"}]}',
    "split": '{"title": "...", "intro": "one sentence", "paragraphs": ["2-3 sentences"], "bullets": ["2-6 words", "2-6 words", "2-6 words"]}',
    "cart": '{"title": "2-4 words", "text": "one sentence"}',
}

SYSTEM_PROMPT = (
    "You write the words for one section of a website. A design system already handles layout, colours, "
    "fonts and images, so you only write copy. Reply with a single JSON object and nothing else. Write like a "
    "skilled brand copywriter for this specific business: concrete, warm, plain verbs, sentence case, no hype, "
    "no clichés like elevate/unlock/seamless/world-class. Never describe the design, colours, fonts, layout, "
    "sections or these instructions. Never mention that something is a demo, placeholder or illustrative. Use "
    "only facts from the request. Do not invent prices, phone numbers, addresses, opening hours, statistics, "
    "awards, client names, people's names or reviews. Describe qualities and experiences instead."
)

_ACRONYMS = {"faq": "FAQ", "cta": "Get in touch", "ai": "AI", "api": "API", "ux": "UX", "ui": "UI", "seo": "SEO"}


def section_kind(slug: str) -> str:
    s = slug.lower()
    for kind, pattern in KIND_PATTERNS:
        if re.search(pattern, s):
            return kind
    return "split"


def nav_label(slug: str) -> str:
    if slug.lower() in _ACRONYMS:
        return _ACRONYMS[slug.lower()]
    words = [w for w in re.split(r"[-_\s]+", slug) if w]
    if not words:
        return "Section"
    words = [_ACRONYMS.get(w.lower(), w.lower()) if w.lower() in {"faq", "ai", "api", "ux", "ui", "seo"} else w.lower()
             for w in words]
    label = " ".join(words)
    return label[:1].upper() + label[1:]


def pascal(slug: str) -> str:
    name = "".join(w[:1].upper() + w[1:] for w in re.split(r"[^A-Za-z0-9]+", slug) if w)
    if not name or not name[0].isalpha():
        name = "Sec" + name
    return name


# ── JSON parsing ────────────────────────────────────────────────────────────

def _close_truncated(text: str) -> Optional[str]:
    """Trim a dangling field from truncated JSON and close open brackets."""
    stack: list[str] = []
    in_string = False
    escape = False
    last_safe = 0
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            last_safe = i + 1
        elif ch == ",":
            last_safe = i
    candidate = text[:last_safe] if in_string or not text.rstrip().endswith(("}", "]", '"')) else text
    candidate = candidate.rstrip().rstrip(",").rstrip()
    stack = []
    in_string = False
    escape = False
    for ch in candidate:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            stack.pop()
    if in_string:
        return None
    candidate = re.sub(r",\s*$", "", candidate)
    candidate = re.sub(r'(?:,\s*)?"[^"]*"\s*:\s*$', "", candidate)
    closing = "".join("}" if ch == "{" else "]" for ch in reversed(stack))
    return candidate + closing


def parse_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    text = re.sub(r"<think>[\s\S]*$", "", text) if "<think>" in text and "</think>" not in text else text
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    if start < 0:
        return None
    body = text[start:]
    decoder = json.JSONDecoder()
    attempts = [body]
    repaired = (body.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'"))
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    attempts.append(repaired)
    closed = _close_truncated(repaired)
    if closed:
        attempts.append(re.sub(r",\s*([}\]])", r"\1", closed))
    for attempt in attempts:
        try:
            value, _ = decoder.raw_decode(attempt)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            return value
    return None


# ── Integrity ───────────────────────────────────────────────────────────────

# Design words (palette, typography, fonts, layout…) are judged per sentence by
# is_design_direction, so business copy that uses them survives.
META_RE = re.compile(
    r"\b(?:hex(?:\s+code)?|#[0-9a-f]{3,6}\b|css|this\s+section|placeholders?|lorem|ipsum|illustrative|demo\s+data|"
    r"sample\s+(?:copy|text|data)|this\s+(?:website|site|page)|the\s+user|as\s+requested|(?:not\s+)?invented|"
    r"fabricat\w*|user[- ]supplied|supplied\s+by|json|tbd|coming\s+soon|mock-?up|wireframe|"
    r"no\s+online\s+(?:checkout|reservations?|booking)\b(?=[.!]?$))", re.I)

_STYLE_WORDS = re.compile(
    r"\b(?:style|styled|look|looks|aesthetic|vibe|feel|palette|colou?rs?|tones?|fonts?|typography|serif|sans|minimal|"
    r"minimalist|layout|photography|imagery|images|white\s+space|whitespace|editorial|textures?|gradients?|dark|light|"
    r"warm|cool|muted|pastel|neon|bold|clean|airy|moody|playful|ivory|cream|terracotta|sage|navy|charcoal|black|white|"
    r"gold|beige|olive|burgundy|cobalt|lavender|espresso|forest|green|blue|red|pink|orange|purple|grey|gray|brown|"
    r"technical|luxurious|cozy|cosy|colourful|colorful|motion|animations?)\b", re.I)

_STOPWORDS = set("""a an the and or but of for to in on at by with from into over under about our your their its his
her we you they it is are was were be been being this that these those as so very more most just also only not no
do does did have has had will would can could should may might must than then there here what which who whom whose
when where why how all any each every some such own same other lots lot""".split())

_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CURRENCY_RE = re.compile(r"(?:[$€£₹¥]\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:usd|eur|gbp|inr|rs\.?|rupees|dollars|euros|pounds)\b)", re.I)
_COUNT_RE = re.compile(
    r"\b(\d[\d,.]*)\s?(?:%|\+|percent\b|k\b|x\b|customers\b|clients\b|users\b|years\b|awards?\b|members\b|students\b|"
    r"countries\b|cities\b|projects\b|reviews\b|stars\b|people\b|families\b|guests\b|teams\b|companies\b|brands\b|"
    r"downloads\b|orders\b|locations\b|stores\b|employees\b|partners\b|hours\b|minutes\b|times\b)", re.I)
_TITLE_ORG_RE = re.compile(r"\b(?:CEO|CTO|CPO|COO|VP|Director|Head|Founder|Co-founder|President|Manager)\s+(?:of|at)\s+[A-Z][a-z]")
_CLAIM_RE = re.compile(
    r"\b(?:award[- ]winning|best\s+in|#\s?1\b|number\s+one|voted\b|featured\s+in|as\s+seen\s+(?:in|on)|trusted\s+by\s+\d|"
    r"rated\s+\d|five[- ]star|5[- ]star|michelin|certified\s+by|industry[- ]leading|world[- ]class|leading\s+provider|"
    # Vague track-record claims the request never made ("clients across multiple industries").
    r"(?:clients|brands|companies|customers|businesses)\s+(?:across|in|from)\s+(?:multiple|many|various|several|diverse|numerous|all)\b|"
    r"(?:multiple|many|numerous|countless|dozens\s+of|hundreds\s+of|leading|top|major|global)\s+(?:clients|brands|companies|customers|businesses))",
    re.I)
_HOURS_RE = re.compile(
    r"\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b|\b(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)(?:day)?s?\s*(?:-|–|to|through)\s*"
    r"(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)|\bopen\s+(?:daily|every\s+day|seven\s+days|24/7)\b|\b24/7\b", re.I)
_COUNT_LEAK_RE = re.compile(r"\(\d+ (?:cards?|items?|tiers?)\)|\b\d+ cards\b", re.I)
_CLICHE_RE = re.compile(r"\b(?:elevate|elevates|elevating|unlock|unlocks|seamless(?:ly)?|world-class|cutting-edge|"
                        r"game-chang\w+|revolutioni[sz]\w*|synerg\w+|next-level|best-in-class)\b", re.I)


def _sentence_case(text: str) -> str:
    """Capitalise the first letter of each sentence the model left lowercase."""
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z'-]{2,}", text.lower()) if w not in _STOPWORDS]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“(])", text)
    return [p.strip() for p in parts if p.strip()]


class Integrity:
    """Sentence-level filters built from the user's request."""

    def __init__(self, prompt: str, extra_facts: Optional[list[str]] = None):
        self.prompt = prompt or ""
        lower = self.prompt.lower()
        self.prompt_lower = lower
        self.prompt_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", self.prompt))
        for fact in extra_facts or []:
            self.prompt_numbers.update(re.findall(r"\d+(?:[.,]\d+)?", str(fact)))
        self.prompt_emails = {e.lower() for e in _EMAIL_RE.findall(self.prompt)}
        self.has_hours = bool(re.search(r"\b(?:am|pm|hours|open|opening|closed|daily)\b", lower))
        self.style_clauses: list[set[str]] = []
        for clause in re.split(r"[.;\n]|,(?=\s)", self.prompt):
            if _STYLE_WORDS.search(clause):
                words = set(_words(clause))
                if words:
                    self.style_clauses.append(words)
        self.prompt_clause_texts = [c.strip().lower().rstrip(".") for c in re.split(r"[.;\n]", self.prompt) if c.strip()]

    def _numbers_ok(self, matches: list[str]) -> bool:
        for match in matches:
            digits = re.findall(r"\d+(?:[.,]\d+)?", match)
            if any(d not in self.prompt_numbers and d.replace(",", "") not in self.prompt_numbers for d in digits):
                return False
        return True

    def sentence_ok(self, sentence: str) -> bool:
        s = sentence.strip()
        if not s:
            return False
        lower = s.lower()
        if (META_RE.search(s) or is_design_direction(s) or _COUNT_LEAK_RE.search(s) or _TITLE_ORG_RE.search(s)
                or _CLAIM_RE.search(s)):
            return False
        # Verbatim restatement of a prompt clause that is an instruction or style direction.
        bare = lower.rstrip(".!? ")
        if bare in self.prompt_clause_texts and (_STYLE_WORDS.search(bare) or re.search(r"\b(?:no|not|do not|don't|never|without)\b", bare)):
            return False
        words = _words(s)
        if words:
            for clause in self.style_clauses:
                shared = len(set(words) & clause)
                if (shared >= 3 and shared / len(set(words)) >= 0.45) or (2 <= len(set(words)) <= 3 and set(words) <= clause):
                    return False
        if any(e.lower() not in self.prompt_emails for e in _EMAIL_RE.findall(s)):
            return False
        phones = _PHONE_RE.findall(s)
        if phones and not self._numbers_ok(phones):
            return False
        if not self._numbers_ok(_CURRENCY_RE.findall(s)):
            return False
        if not self._numbers_ok([m.group(0) for m in _COUNT_RE.finditer(s)]):
            return False
        if not self.has_hours and _HOURS_RE.search(s):
            return False
        return True

    def clean_text(self, text: Any) -> str:
        sentences = [s for s in split_sentences(str(text or "")) if self.sentence_ok(s)]
        cleaned = _sentence_case(" ".join(sentences))
        return _CLICHE_RE.sub(lambda m: {"elevate": "lift", "elevates": "lifts", "unlock": "open",
                                          "unlocks": "opens"}.get(m.group(0).lower(), m.group(0)), cleaned).strip()

    def clean_short(self, text: Any, max_words: int) -> str:
        """Titles, labels and button text: one phrase, same filters, word cap."""
        value = re.sub(r"\s+", " ", str(text or "")).strip().strip('"“”')
        if not value or not self.sentence_ok(value):
            return ""
        words = value.split()
        if len(words) > max_words:
            value = " ".join(words[:max_words]).rstrip(",;:—–-")
        return _sentence_case(value)


# ── Context, normalisation and fallback ─────────────────────────────────────

@dataclass
class SectionContext:
    slug: str
    kind: str
    label: str
    brand: str
    business_label: str
    business_type: str
    location: str = ""
    email: str = ""
    supplied_items: list = field(default_factory=list)
    products: list = field(default_factory=list)  # [{"name","price"}]
    is_store: bool = False
    checkout_available: bool = False
    quotes: list = field(default_factory=list)


def _cap_words(text: str, max_words: int) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    trimmed = " ".join(words[:max_words]).rstrip(",;:—–-")
    return trimmed if trimmed.endswith((".", "!", "?")) else trimmed + "."


def _cap_sentences(text: str, max_sentences: int, max_words: int) -> str:
    sentences = split_sentences(text)[:max_sentences]
    return _cap_words(" ".join(sentences), max_words)


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _match_supplied(names: list[str], rows: list[dict], key: str) -> list[Optional[dict]]:
    """Attach model rows to user-supplied names: exact, word overlap, then next unused."""
    used: set[int] = set()
    result: list[Optional[dict]] = [None] * len(names)
    def norm(v: Any) -> str:
        return re.sub(r"[^a-z0-9 ]", "", str(v or "").lower()).strip()
    for i, name in enumerate(names):
        for j, row in enumerate(rows):
            if j not in used and norm(row.get(key)) == norm(name):
                result[i] = row
                used.add(j)
                break
    for i, name in enumerate(names):
        if result[i] is not None:
            continue
        best, best_score = None, 0
        for j, row in enumerate(rows):
            if j in used:
                continue
            score = len(set(norm(name).split()) & set(norm(row.get(key)).split()))
            if score > best_score:
                best, best_score = j, score
        if best is not None:
            result[i] = rows[best]
            used.add(best)
    unused = [row for j, row in enumerate(rows) if j not in used]
    for i in range(len(names)):
        if result[i] is None and unused:
            result[i] = unused.pop(0)
    return result


def _business_noun(ctx: SectionContext) -> str:
    return ctx.business_label or "studio"


def fallback(ctx: SectionContext) -> dict:
    """Deterministic, honest copy: brand, business, location and supplied items only."""
    b, noun, where = ctx.brand, _business_noun(ctx), (f" in {ctx.location}" if ctx.location else "")
    items = list(ctx.supplied_items)
    kind = ctx.kind
    label = ctx.label
    if kind == "hero":
        return {"headline": f"{b}, a {noun}{where}" if len(f"{b}, a {noun}{where}".split()) <= 10 else b,
                "lede": f"{b} is a {noun}{where}. Take a look around, see what we make and get in touch when you are ready.",
                "primary_cta": "Take a look", "secondary_cta": "Get in touch", "tagline": noun[:1].upper() + noun[1:]}
    if kind in {"features", "team"}:
        names = items or ["What we do", "How we work", "Who it is for"]
        key = "members" if kind == "team" else "items"
        rows = [{"title": n, "role": n, "text": f"Ask us about {n.lower()}." if items else
                 {"What we do": f"The work at the heart of {b}.", "How we work": "Carefully, and in plain language.",
                  "Who it is for": "People who care about the details."}[n]} for n in names]
        return {"title": label, "intro": f"An overview of {label.lower()} at {b}.", key: rows}
    if kind == "steps":
        names = items or ["Get in touch", "Talk it through", "Make a plan", "Follow through"]
        texts = ["Tell us what you need.", "We listen and ask questions.", "Together we agree the next steps.",
                 "We keep you posted along the way."]
        return {"title": label, "intro": f"How {label.lower()} works at {b}.",
                "steps": [{"title": n, "text": texts[i % len(texts)] if not items else f"Details on {n.lower()} are available on request."}
                          for i, n in enumerate(names)]}
    if kind in {"story", "split"}:
        return {"title": label, "intro": f"About {b}.",
                "paragraphs": [f"{b} is a {noun}{where}.", "Write to us and we will happily tell you more."],
                "highlights": [], "bullets": items[:4]}
    if kind == "work":
        names = items or []
        return {"title": label, "intro": f"Selected {label.lower()} from {b}.",
                "items": [{"title": n, "caption": ""} for n in names]}
    if kind == "products":
        names = [p["name"] for p in ctx.products] or items
        return {"title": label, "intro": f"A selection from {b}.",
                "items": [{"name": n, "description": ""} for n in names]}
    if kind == "menu":
        return {"title": label, "intro": f"Ask {b} for today's menu.", "categories": []}
    if kind == "faq":
        questions = [("How do I get in touch?", f"Write to {ctx.email} and we will reply personally." if ctx.email
                      else "Use the contact details on this page and we will reply personally."),
                     (f"Where is {b}?", f"We are in {ctx.location}." if ctx.location else "Ask us and we will tell you how to find us."),
                     ("Can I ask a question first?", "Of course. Ask anything before you decide.")]
        return {"title": "Questions", "intro": "Answers to common questions.",
                "items": [{"q": q, "a": a} for q, a in questions]}
    if kind == "articles":
        names = items or []
        return {"title": label, "intro": f"{label} from {b}.",
                "items": [{"title": n, "excerpt": "", "tag": ""} for n in names]}
    if kind == "pricing":
        names = items or ["Starter", "Regular", "Full"]
        return {"title": label, "intro": "Ask us for current pricing.",
                "tiers": [{"name": n, "description": "", "features": []} for n in names]}
    if kind == "quotes":
        return {"title": "Kind words", "intro": f"Worked with {b}?", "invite": "We'd love to hear how it went."}
    if kind == "contact":
        return {"title": "Get in touch",
                "text": (f"Questions, ideas or plans: write to {ctx.email} and we'll reply personally." if ctx.email
                         else "Questions, ideas or plans: send a note and we'll reply personally."),
                "button": "Send message"}
    if kind == "cta":
        return {"title": f"Stay in touch with {b}", "text": "Write to us any time.", "button": "Write to us"}
    if kind == "preview":
        return {"title": f"Inside {b}", "intro": f"A look at how {b} works.", "labels": ["Overview", "Activity", "Reports"],
                "points": [{"title": "One clear view", "text": "The essentials in one place."},
                           {"title": "Less busywork", "text": "Routine steps take fewer clicks."},
                           {"title": "Shared context", "text": "Everyone sees the same picture."}]}
    if kind == "cart":
        return {"title": "Your cart", "text": "Items you add appear here."}
    return {"title": label}


def normalise(ctx: SectionContext, data: Optional[dict], integrity: Integrity) -> tuple[dict, list[str]]:
    """Clean, cap and complete model content; fill gaps from the fallback."""
    notes: list[str] = []
    fb = fallback(ctx)
    data = data if isinstance(data, dict) else {}
    kind = ctx.kind
    clean, short = integrity.clean_text, integrity.clean_short

    def pick_short(key: str, max_words: int, default: str = "") -> str:
        value = short(data.get(key), max_words)
        if not value and data.get(key):
            notes.append(f"{key} filtered")
        return value or default

    def pick_text(key: str, max_sentences: int, max_words: int, default: str = "") -> str:
        value = _cap_sentences(clean(data.get(key)), max_sentences, max_words)
        return value or default

    out: dict = {}
    if kind == "hero":
        out["headline"] = pick_short("headline", 10, fb["headline"]).rstrip(".")
        out["lede"] = pick_text("lede", 2, 36, fb["lede"])
        out["primary_cta"] = pick_short("primary_cta", 4, fb["primary_cta"]).rstrip(".")
        out["secondary_cta"] = pick_short("secondary_cta", 4, fb["secondary_cta"]).rstrip(".")
        out["tagline"] = pick_short("tagline", 6, fb["tagline"]).rstrip(".")
        return out, notes

    out["title"] = pick_short("title", 8, fb.get("title", ctx.label)).rstrip(".")
    if kind in {"cart"}:
        out["text"] = pick_text("text", 1, 24, fb["text"])
        return out, notes
    if kind in {"contact", "cta"}:
        out["text"] = pick_text("text", 2, 40, fb["text"])
        out["button"] = pick_short("button", 3, fb["button"]).rstrip(".")
        return out, notes
    if kind == "quotes":
        out["intro"] = pick_text("intro", 1, 24, fb["intro"])
        out["invite"] = pick_text("invite", 1, 24, fb["invite"])
        out["quotes"] = list(ctx.quotes)
        return out, notes

    out["intro"] = pick_text("intro", 1, 30, fb.get("intro", ""))
    if kind in {"story", "split"}:
        paragraphs = [_cap_sentences(clean(p), 3, 70) for p in _as_list(data.get("paragraphs"))]
        paragraphs = [p for p in paragraphs if p][: (2 if kind == "story" else 2)]
        out["paragraphs"] = paragraphs or fb["paragraphs"]
        bullet_key = "highlights" if kind == "story" else "bullets"
        bullets = [short(b, 7) for b in _as_list(data.get(bullet_key)) + _as_list(data.get("highlights" if kind == "split" else "bullets"))]
        bullets = list(dict.fromkeys(b.rstrip(".") for b in bullets if b))[:4]
        if ctx.supplied_items:
            bullets = list(dict.fromkeys(list(ctx.supplied_items) + bullets))[:6]
        out["bullets"] = bullets or fb.get("bullets", [])
        return out, notes

    lo, hi, _ = COUNTS.get(kind, (0, 8, 3))
    supplied = list(ctx.supplied_items)

    def rows_from(key: str, name_key: str, text_keys: dict[str, tuple[int, int]], fb_key: str) -> list[dict]:
        raw = [r for r in _as_list(data.get(key)) if isinstance(r, dict)]
        cleaned_rows = []
        for r in raw:
            row = {name_key: short(r.get(name_key), 9).rstrip(".")}
            for tk, (sent, words) in text_keys.items():
                row[tk] = _cap_sentences(clean(r.get(tk)), sent, words)
            cleaned_rows.append(row)
        if supplied:
            matched = _match_supplied(supplied, raw, name_key)
            rows = []
            for name, src in zip(supplied, matched):
                row = {name_key: name}
                for tk, (sent, words) in text_keys.items():
                    row[tk] = _cap_sentences(clean((src or {}).get(tk)), sent, words)
                rows.append(row)
            return rows
        rows = [r for r in cleaned_rows if r.get(name_key)]
        seen: set[str] = set()
        unique = []
        for r in rows:
            k = r[name_key].lower()
            if k not in seen:
                seen.add(k)
                unique.append(r)
        rows = unique[:hi]
        if len(rows) < lo:
            for extra in fb.get(fb_key, []):
                if len(rows) >= lo:
                    break
                if extra.get(name_key, "").lower() not in seen:
                    rows.append({name_key: extra.get(name_key, ""), **{tk: extra.get(tk, "") for tk in text_keys}})
        return rows

    if kind == "features":
        out["items"] = rows_from("items", "title", {"text": (2, 34)}, "items")
    elif kind == "team":
        rows = rows_from("members", "role", {"text": (1, 26)}, "members")
        out["members"] = [{"name": r["role"] if supplied else "", "role": r["role"] if not supplied else "", "text": r["text"]}
                          for r in rows]
        if supplied:
            matched = _match_supplied(supplied, [r for r in _as_list(data.get("members")) if isinstance(r, dict)], "role")
            for member, src in zip(out["members"], matched):
                member["role"] = short((src or {}).get("role"), 4).rstrip(".")
    elif kind == "steps":
        out["steps"] = rows_from("steps", "title", {"text": (2, 34)}, "steps")
    elif kind == "work":
        out["items"] = rows_from("items", "title", {"caption": (1, 24)}, "items")
    elif kind == "articles":
        rows = rows_from("items", "title", {"excerpt": (1, 26)}, "items")
        raw = [r for r in _as_list(data.get("items")) if isinstance(r, dict)]
        for row in rows:
            src = next((r for r in raw if str(r.get("title", "")).strip().lower() == row["title"].lower()), {})
            row["tag"] = short(src.get("tag"), 2).rstrip(".")
        out["items"] = rows
    elif kind == "products":
        supplied_products = list(ctx.products)
        if supplied_products:
            supplied = [p["name"] for p in supplied_products]
        rows = rows_from("items", "name", {"description": (1, 22)}, "items")
        prices = {p["name"].lower(): p["price"] for p in supplied_products}
        for row in rows:
            price = prices.get(row["name"].lower())
            if price:
                row["price"] = price
        out["items"] = rows
    elif kind == "faq":
        raw = [r for r in _as_list(data.get("items")) if isinstance(r, dict)]
        rows = []
        for r in raw:
            q = short(r.get("q") or r.get("question"), 16)
            a = _cap_sentences(clean(r.get("a") or r.get("answer")), 2, 45)
            if q and a and q.lower() not in {x["q"].lower() for x in rows}:
                rows.append({"q": q if q.endswith("?") else q.rstrip(".") + "?", "a": a})
        rows = rows[:hi]
        for extra in fb["items"]:
            if len(rows) >= lo:
                break
            if extra["q"].lower() not in {x["q"].lower() for x in rows}:
                rows.append(extra)
        out["items"] = rows
    elif kind == "pricing":
        raw = [r for r in _as_list(data.get("tiers")) if isinstance(r, dict)]
        names = supplied or [short(r.get("name"), 3).rstrip(".") for r in raw if short(r.get("name"), 3)]
        names = list(dict.fromkeys(n for n in names if n))[:hi] or [t["name"] for t in fb["tiers"]]
        matched = _match_supplied(names, raw, "name")
        tiers = []
        for name, src in zip(names, matched):
            src = src or {}
            features = [short(f, 6).rstrip(".") for f in _as_list(src.get("features"))]
            tiers.append({"name": name, "description": _cap_sentences(clean(src.get("description")), 1, 22),
                          "features": [f for f in features if f][:4], "price": ""})
        while len(tiers) < lo:
            tiers.append({"name": fb["tiers"][len(tiers)]["name"], "description": "", "features": [], "price": ""})
        out["tiers"] = tiers
    elif kind == "menu":
        categories = []
        for cat in _as_list(data.get("categories"))[:5]:
            if not isinstance(cat, dict):
                continue
            name = short(cat.get("name"), 3).rstrip(".")
            dishes = []
            for dish in _as_list(cat.get("items"))[:8]:
                if not isinstance(dish, dict):
                    continue
                dname = short(dish.get("name"), 6).rstrip(".")
                if dname:
                    dishes.append({"name": dname, "description": _cap_sentences(clean(dish.get("description")), 1, 16), "price": ""})
            if name and dishes:
                categories.append({"name": name, "items": dishes})
        if supplied:
            # Supplied menu items are the categories, in the user's order; the
            # model's dishes attach by name and no dish is invented for the rest.
            matched = _match_supplied(supplied, categories, "name") if categories else [None] * len(supplied)
            categories = [{"name": name, "items": list((src or {}).get("items") or [])}
                          for name, src in zip(supplied, matched)]
        out["categories"] = categories
    elif kind == "preview":
        labels = [short(l, 2).rstrip(".") for l in _as_list(data.get("labels"))]
        out["labels"] = [l for l in labels if l][:3] or fb["labels"]
        while len(out["labels"]) < 3:
            out["labels"].append(fb["labels"][len(out["labels"])])
        points = []
        for p in _as_list(data.get("points"))[:3]:
            if isinstance(p, dict) and short(p.get("title"), 6):
                points.append({"title": short(p.get("title"), 6).rstrip("."), "text": _cap_sentences(clean(p.get("text")), 1, 22)})
        out["points"] = points if len(points) >= 2 else fb["points"]
    return out, notes


# ── Prompting ───────────────────────────────────────────────────────────────

def build_messages(ctx: SectionContext, prompt: str, item_count: int, voice: list[str],
                   cta_targets: Optional[tuple[str, str]] = None) -> list[dict]:
    lines = [
        f"Request: {prompt.strip()}",
        f"Business name: {ctx.brand}",
        f"Business: {ctx.business_label or ctx.business_type}",
        f"Section: {ctx.label}",
    ]
    if ctx.kind == "products" and ctx.products:
        lines.append("Use exactly these items from the request, in this order: " + ", ".join(p["name"] for p in ctx.products) + ".")
    elif ctx.kind == "menu" and ctx.supplied_items:
        lines.append("Use exactly these menu categories from the request, in this order, with 2-4 dishes each: "
                     + ", ".join(ctx.supplied_items) + ".")
    elif ctx.supplied_items:
        lines.append("Use exactly these items from the request, in this order: " + ", ".join(ctx.supplied_items) + ".")
    elif ctx.kind in COUNTS:
        lines.append(f"Write {item_count} items.")
    if ctx.kind == "hero" and cta_targets:
        lines.append(f"Button labels must match where they go: primary_cta opens the {cta_targets[0]} section; "
                     f"secondary_cta opens the {cta_targets[1]} section.")
    if voice:
        lines.append("Headlines already on the page (keep the same voice, don't repeat them): " + " | ".join(voice[:3]))
    lines.append(f"Reply with JSON in this shape: {SHAPES.get(ctx.kind, SHAPES['split'])}")
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "\n".join(lines)}]


def is_usable(kind: str, data: Optional[dict], integrity: Integrity) -> bool:
    if not isinstance(data, dict):
        return False
    key = "headline" if kind == "hero" else "title"
    return bool(integrity.clean_short(data.get(key), 12))
