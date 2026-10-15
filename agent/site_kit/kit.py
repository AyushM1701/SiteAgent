"""KitSite: one art direction, one site context, model-written content per section."""
from __future__ import annotations

import hashlib
import html
import io
import json
import re
from typing import Any, Optional

from .base_css import build_base_css, derived_colors
from .content import (COUNTS, DEFAULT_MAX_TOKENS, MAX_TOKENS, MODEL_KINDS, Integrity, SectionContext, build_messages,
                      is_usable, nav_label, normalise, parse_json_object, pascal, section_kind)
from .imagery import ImagePlanner
from .render import render_section, scope_class
from .themes import THEMES, Theme, _rgb, apply_requested_palette, select_theme

try:
    from agent.site_brief import (_descriptive_business_name, _explicitly_excluded, _is_negated, _mentions,
                                  detect_business_type, extract_business_name, extract_supplied_products)
except ImportError:  # pragma: no cover - script context with agent/ on sys.path
    from site_brief import (_descriptive_business_name, _explicitly_excluded, _is_negated, _mentions,  # type: ignore
                            detect_business_type, extract_business_name, extract_supplied_products)

_LOCATION_REJECT = {
    "react", "typescript", "javascript", "tailwind", "css", "html", "english", "spanish", "french", "hindi", "dark",
    "light", "the", "a", "an", "our", "my", "your", "vite", "next", "figma", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october", "november", "december", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday", "sections", "style", "minimal", "modern",
}
_STORE_RE = r"\b(?:cart|add to cart|online store|online shop|e-?commerce|shopping bag|basket)\b"
_REVEAL_KINDS = ("features", "products", "articles", "story", "work")
_TINT_KINDS = {"contact", "cart", "quotes"}
_CLOSING_KINDS = {"contact", "cta"}


def extract_location(prompt: str, brand: str = "") -> str:
    for m in re.finditer(r"\b(?:based\s+in|located\s+in|in|from)\s+((?:[A-Z][\w'’-]+)(?:[ -](?:[A-Z][\w'’-]+)){0,2})", prompt):
        candidate = m.group(1).strip().rstrip(".")
        first = candidate.split()[0].lower()
        if first in _LOCATION_REJECT or candidate.lower() == brand.lower() or candidate.lower() in brand.lower():
            continue
        if re.search(r"\b(?:sections?|include|projects?|products?)\b", candidate, re.I):
            continue
        return candidate
    return ""


def business_label_from_prompt(prompt: str, brand: str, business_type: str) -> str:
    text = prompt.strip()
    patterns = [
        rf"^\s*[\"“']?{re.escape(brand)}[\"”']?\s*(?:[—–:]|\s-\s|,|\s+is)\s*(?:a|an|the)?\s*([^.;\n]+)",
        rf"\b{re.escape(brand)}\s*,\s*(?:a|an|the)\s+([^.;\n]+)",
        r"\bfor\s+(?:a|an|my|our)\s+([^.;\n]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            label = m.group(1)
            label = re.split(r"\s+(?:in|from|based|located|near|with|that|which|who|called|named)\s+|,", label)[0]
            label = re.sub(r"^(?:a|an|the)\s+", "", label.strip(), flags=re.I)
            words = label.split()
            if 1 <= len(words) <= 6 and not re.search(r"\b(?:website|site|page|landing)\b", label, re.I):
                return label
            if words and len(words) > 6:
                return " ".join(words[:5])
    m = re.match(rf"^\s*{re.escape(brand)}\s+([a-z][\w-]*(?:\s+[a-z][\w-]*){{0,3}})", text)
    if m:
        return m.group(1)
    return {"saas": "software company", "restaurant": "restaurant", "portfolio": "portfolio", "ecommerce": "shop",
            "fitness": "gym", "coffee": "cafe", "healthcare": "clinic", "education": "school", "agency": "studio",
            "architecture": "architecture studio", "realestate": "property business", "nonprofit": "nonprofit",
            "event": "event", "blog": "publication", "editorial": "publication", "fintech": "finance company"}.get(business_type, "business")


class KitSite:
    def __init__(self, prompt: str, brief: Optional[dict] = None, sections: Optional[list[str]] = None,
                 theme_id: Optional[str] = None):
        self.prompt = prompt or ""
        self.brief = brief or {}
        lower = self.prompt.lower()
        self.business_type = self.brief.get("business_type") or detect_business_type(self.prompt)
        brand = (self.brief.get("business_name") or "").strip()
        if not brand or brand == "My Business":
            brand = extract_business_name(self.prompt)
        if brand == "My Business":
            brand = _descriptive_business_name(self.prompt) or "Studio"
        self.brand = brand
        self.label_text = business_label_from_prompt(self.prompt, self.brand, self.business_type)
        contact = self.brief.get("contact") if isinstance(self.brief.get("contact"), dict) else {}
        email_m = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", self.prompt)
        self.email = (contact or {}).get("email") or (email_m.group(0).rstrip(".") if email_m else "")
        if self.email and self.email.lower() not in lower:
            self.email = email_m.group(0).rstrip(".") if email_m else ""
        self.location = extract_location(self.prompt, self.brand)
        self.products = [p for p in (self.brief.get("products") or extract_supplied_products(self.prompt))
                         if isinstance(p, dict) and p.get("name")]
        theme = select_theme(self.prompt, self.business_type, theme_id)
        self.theme: Theme = apply_requested_palette(theme, self.brief)
        self.sections = self._order_sections(list(sections or self.brief.get("sections") or []))
        self.kinds = {slug: ("header" if i == 0 else "footer" if slug == self.sections[-1] else section_kind(slug))
                      for i, slug in enumerate(self.sections)}
        self.kinds = {slug: (section_kind(slug) if section_kind(slug) in {"header", "footer", "hero"} else kind)
                      for slug, kind in self.kinds.items()}
        self.is_store = ("cart" in self.kinds.values()) or (
            _mentions(lower, _STORE_RE) and not _explicitly_excluded(lower, _STORE_RE))
        self.checkout_available = _mentions(lower, r"\bcheckout\b")
        self.images = ImagePlanner(self.prompt)
        self.integrity = Integrity(self.prompt, extra_facts=[p.get("price", "") for p in self.products])
        self._forbidden = self._forbidden_topics(lower)
        self.labels = {slug: nav_label(slug) for slug in self.sections}
        self.reveal_section = next((s for s in self.sections if self.kinds[s] in _REVEAL_KINDS), "")
        self.tints = self._tints()
        self.contents: dict[str, dict] = {}
        self.voice: list[str] = []
        self.hero_style = ""
        self.shader = bool(re.search(r"\b(?:3d|3-d|three[- ]d|shader|webgl|fluid|mesh gradient)\b", lower))
        self._allocate_images()

    # ── Planning ────────────────────────────────────────────────────────────
    def _order_sections(self, raw: list[str]) -> list[str]:
        seen: list[str] = []
        for slug in raw:
            slug = re.sub(r"[^a-z0-9-]+", "-", str(slug).lower()).strip("-")
            if not slug:
                continue
            if slug in {"nav", "navbar", "navigation", "masthead", "top-bar"}:
                slug = "header"
            if slug not in seen:
                seen.append(slug)
        middle = [s for s in seen if section_kind(s) not in {"header", "footer", "hero"}]
        closing = [s for s in middle if section_kind(s) in _CLOSING_KINDS]
        middle = [s for s in middle if s not in closing] + closing
        hero = next((s for s in seen if section_kind(s) == "hero"), "hero")
        return ["header", hero] + middle + ["footer"]

    def _tints(self) -> dict[str, bool]:
        tints: dict[str, bool] = {}
        toggle = False
        previous = ""
        for slug in self.sections:
            kind = self.kinds[slug]
            if kind in {"header", "footer", "hero"}:
                tints[slug] = False
                previous = ""
                continue
            if kind == "cta":
                tints[slug] = False
                previous = slug
                continue
            want = kind in _TINT_KINDS or toggle
            toggle = not toggle
            if want and previous and tints.get(previous):
                if kind in _TINT_KINDS and self.kinds[previous] not in _TINT_KINDS:
                    tints[previous] = False
                else:
                    want = False
            tints[slug] = want
            previous = slug
        return tints

    def _forbidden_topics(self, lower: str) -> list[str]:
        topics = {
            r"\breserv\w*|\bbook(?:ing|ings)?\b|book a table": r"\b(?:reserv\w*|book(?:ing|ings)?|book a table)\b",
            r"\bpric\w*": r"\b(?:pric\w*|cost|costs|fee|fees|per month|/mo)\b",
            r"\bcheckout\b": r"\b(?:checkout|check out|buy online|order online)\b",
            r"\bdeliver\w*": r"\bdeliver\w*\b",
        }
        return [deny for probe, deny in topics.items() if _explicitly_excluded(lower, probe)]

    def _allocate_images(self) -> None:
        """Hero first, then single-image sections, then grids, so no section that
        is designed around one photo is starved by a catalogue."""
        self.section_images: dict[str, list] = {}
        singles = {"story", "split", "menu", "steps", "articles"}
        self.section_images[self.sections[1]] = self.images.take(1)
        middle = self.sections[2:-1]
        for slug in middle:
            if self.kinds[slug] in singles:
                self.section_images[slug] = self.images.take(1)
        for slug in middle:
            kind = self.kinds[slug]
            if kind == "work":
                self.section_images[slug] = self.images.take(max(len(self.supplied_items(slug)), 4))
            elif kind == "products":
                self.section_images[slug] = self.images.take(max(len(self.products) or len(self.supplied_items(slug)), 4))

    # ── Public helpers ──────────────────────────────────────────────────────
    def component(self, slug: str) -> str:
        if self.kinds.get(slug) == "header":
            return "Header"
        if self.kinds.get(slug) == "footer":
            return "Footer"
        return pascal(slug)

    def section_index(self, slug: str) -> int:
        return self.sections.index(slug) if slug in self.sections else 0

    def business_label(self) -> str:
        return self.label_text

    def supplied_items(self, slug: str) -> list[str]:
        plans = self.brief.get("section_plans") or {}
        items = list((plans.get(slug) or {}).get("parsed_items") or [])
        if not items and self.kinds.get(slug) == "work":
            items = [p.get("name") for p in (self.brief.get("projects") or []) if isinstance(p, dict) and p.get("name")]
        return [str(i).strip() for i in items if str(i).strip()][:12]

    def needs_model(self, slug: str) -> bool:
        return self.kinds.get(slug) in MODEL_KINDS

    def max_tokens(self, slug: str) -> int:
        return MAX_TOKENS.get(self.kinds.get(slug, ""), DEFAULT_MAX_TOKENS)

    def _ctx(self, slug: str) -> SectionContext:
        quotes = [q for q in (self.brief.get("testimonials") or []) if isinstance(q, dict) and q.get("quote")]
        return SectionContext(
            slug=slug, kind=self.kinds[slug], label=self.labels[slug], brand=self.brand,
            business_label=self.label_text, business_type=self.business_type, location=self.location,
            email=self.email, supplied_items=self.supplied_items(slug),
            products=self.products if self.kinds[slug] == "products" else [],
            is_store=self.is_store, checkout_available=self.checkout_available,
            quotes=[{"quote": q.get("quote"), "author": q.get("author", "")} for q in quotes],
        )

    def messages(self, slug: str) -> list[dict]:
        kind = self.kinds[slug]
        supplied = self.supplied_items(slug)
        ask = COUNTS.get(kind, (0, 0, 3))[2]
        return build_messages(self._ctx(slug), self.prompt, len(supplied) or ask, self.voice)

    def is_usable(self, slug: str, text: str) -> bool:
        return is_usable(self.kinds[slug], parse_json_object(text), self.integrity)

    # ── Accepting content ───────────────────────────────────────────────────
    def _href_for(self, slug: str) -> str:
        return f"#{slug}"

    def _contact_href(self) -> str:
        contact = next((s for s in self.sections if self.kinds[s] == "contact"), "")
        if contact:
            return f"#{contact}"
        if self.email:
            return f"mailto:{self.email}"
        return "#site-footer"

    def _content_sections(self) -> list[str]:
        return [s for s in self.sections[2:-1]]

    def _links(self) -> list[dict]:
        return [{"id": s, "href": f"#{s}", "label": self.labels[s]} for s in self._content_sections()]

    def _img(self, photo, width: int, height: int) -> Optional[dict]:
        if not photo:
            return None
        return {"src": photo.url(width), "alt": photo.alt, "w": width, "h": height}

    def _mark(self) -> str:
        m = re.search(r"[A-Za-z0-9]", self.brand)
        return m.group(0).upper() if m else "•"

    def _apply_forbidden(self, value: Any) -> Any:
        if not self._forbidden:
            return value
        if isinstance(value, str):
            from .content import split_sentences
            kept = [s for s in split_sentences(value)
                    if not any(re.search(p, s, re.I) and not _is_negated(s.lower(), *re.search(p, s, re.I).span())
                               for p in self._forbidden)]
            return " ".join(kept)
        if isinstance(value, list):
            return [self._apply_forbidden(v) for v in value]
        if isinstance(value, dict):
            return {k: self._apply_forbidden(v) for k, v in value.items()}
        return value

    def accept(self, slug: str, text: str) -> tuple[dict, list[str]]:
        kind = self.kinds[slug]
        notes: list[str] = []
        if kind == "header":
            content = self._header_content()
        elif kind == "footer":
            content = self._footer_content()
        else:
            data = parse_json_object(text or "")
            if text and data is None:
                notes.append("model output was not valid JSON; used fallback copy")
            elif not text:
                notes.append("no model output; used fallback copy")
            if data is not None:
                data = self._apply_forbidden(data)
            ctx = self._ctx(slug)
            content, norm_notes = normalise(ctx, data, self.integrity)
            notes.extend(norm_notes)
            if data is not None and not is_usable(kind, data, self.integrity):
                notes.append("model output unusable; used fallback copy")
            content["eyebrow"] = self.labels[slug] if content.get("title", "").lower() != self.labels[slug].lower() else ""
            content = self._decorate(slug, kind, content)
        self.contents[slug] = content
        headline = content.get("headline") or content.get("title")
        if headline and kind not in {"header", "footer"}:
            self.voice.append(headline)
        return content, notes

    def _header_content(self) -> dict:
        links = self._links()
        contact_href = self._contact_href()
        cta_label = "Get in touch"
        if self.is_store and any(self.kinds[s] == "products" for s in self.sections):
            shop = next(s for s in self.sections if self.kinds[s] == "products")
            cta = {"href": f"#{shop}", "label": "Shop now"}
        else:
            cta = {"href": contact_href, "label": cta_label}
        nav = [l for l in links if l["href"] != cta["href"]][:6] or links[:6]
        currency = ""
        if self.products:
            m = re.match(r"\s*([$€£₹¥])", self.products[0].get("price", ""))
            currency = m.group(1) if m else ""
        note = ("Checkout is handled by email for now: send us your list and we'll confirm availability and payment."
                if not self.checkout_available else
                "Ready to order? Send us your list and we'll confirm the details.")
        if self.email:
            note = note.replace("send us your list", f"email {self.email} with your list")
        return {"brand": self.brand, "links": nav, "cta": cta, "store": self.is_store, "email": self.email,
                "currency": currency, "checkoutNote": note}

    def _footer_content(self) -> dict:
        hero = self.contents.get(self.sections[1], {})
        tagline = hero.get("tagline") or (self.label_text[:1].upper() + self.label_text[1:] if self.label_text else "")
        contact_section = next((s for s in self.sections if self.kinds[s] == "contact"), "")
        privacy = ("This site does not use analytics or advertising cookies. Fonts load from Google Fonts and photos "
                   "from Unsplash, which receive your IP address to deliver them. If you write to us, your message is "
                   "used only to reply.")
        return {"brand": self.brand, "tagline": tagline, "links": self._links(), "email": self.email,
                "location": self.location, "contactHref": f"#{contact_section}" if contact_section else "",
                "cta": {"href": self._contact_href(), "label": "Get in touch"}, "privacy": privacy}

    def _decorate(self, slug: str, kind: str, content: dict) -> dict:
        photos = self.section_images.get(slug, [])
        content = dict(content)
        content["mark"] = self._mark()
        if kind == "hero":
            first = next((s for s in self._content_sections() if self.kinds[s] not in _CLOSING_KINDS), "")
            contact_href = self._contact_href()
            content["primary"] = {"href": f"#{first}" if first else contact_href, "label": content.pop("primary_cta")}
            content["secondary"] = {"href": contact_href, "label": content.pop("secondary_cta")}
            if content["secondary"]["href"] == content["primary"]["href"] and first:
                content["secondary"]["href"] = "#site-footer"
            content["fact"] = f"Based in {self.location}" if self.location else ""
            style = self._hero_style(bool(photos))
            self.hero_style = style
            content["style"] = style
            width, height = {"fullbleed": (2000, 1300), "typographic": (2000, 860)}.get(style, (1200, 1500))
            content["img"] = self._img(photos[0], width, height) if photos else None
            content["shader"] = style == "product" or self.shader
            if content["shader"]:
                c = self.theme.colors
                accent2 = derived_colors(self.theme)["accent2"]
                content["shader_colors"] = [[round(v, 4) for v in _rgb(x)] for x in (c["bg"], c["accent"], accent2)]
                content["shader_mix"] = ["0.50", "0.42"] if self.theme.mode == "dark" else ["0.22", "0.16"]
            content["window"] = {"title": f"{self.brand} overview", "labels": ["Overview", "Activity", "Reports"],
                                 "bars": [38, 52, 46, 64, 58, 72, 66, 84, 78, 90]}
        elif kind in {"story", "split", "menu", "steps"}:
            content["img"] = self._img(photos[0], 1000, 1250) if photos else None
            if kind == "menu":
                content["empty"] = f"Ask {self.brand} for today's menu."
        elif kind == "work":
            for i, item in enumerate(content.get("items", [])):
                item["img"] = self._img(photos[i], 1000, 800) if i < len(photos) else None
        elif kind == "products":
            for i, item in enumerate(content.get("items", [])):
                item["img"] = self._img(photos[i], 900, 1125) if i < len(photos) else None
                subject = f"Question about {item['name']}"
                item["ask"] = (f"mailto:{self.email}?subject=" + re.sub(r" ", "%20", subject)) if self.email else self._contact_href()
        elif kind == "articles":
            for i, item in enumerate(content.get("items", [])):
                item["img"] = self._img(photos[i], 1200, 750) if i < len(photos) else None
        elif kind == "pricing":
            tiers = content.get("tiers", [])
            content["featured"] = 1 if len(tiers) >= 3 else -1
            content["quoteHref"] = self._contact_href()
        elif kind == "quotes":
            content["feedbackHref"] = (f"mailto:{self.email}?subject=Feedback%20for%20" + re.sub(r"\s", "%20", self.brand)
                                       if self.email else self._contact_href())
        elif kind == "contact":
            content["email"] = self.email
            content["location"] = self.location
            content["note"] = ("Sending opens your email app with the message ready to go." if self.email
                               else "This form isn't connected to a mailbox yet, so nothing is sent from here.")
            content["doneNote"] = ("Your email app should now open with the message ready to send." if self.email
                                   else "Thanks. This form isn't connected yet, so please reach us another way for now.")
        elif kind == "cta":
            content["href"] = self._contact_href() if self._contact_href() != f"#{slug}" else "#site-footer"
        elif kind == "preview":
            content["bars"] = [42, 58, 50, 66, 61, 74, 69, 82]
        elif kind == "cart":
            content["email"] = self.email
            content["brand"] = self.brand
            m = re.match(r"\s*([$€£₹¥])", (self.products[0].get("price", "") if self.products else ""))
            content["currency"] = m.group(1) if m else ""
            content["note"] = ("Online checkout isn't available yet. " +
                               (f"Email {self.email} with your list and we'll confirm availability and payment."
                                if self.email else "Send us your list and we'll confirm availability and payment.")
                               ) if not self.checkout_available else "Review your items, then send us your order."
        return content

    def _hero_style(self, has_photo: bool) -> str:
        theme = self.theme
        if theme.id == "signal":
            return "product"
        styles = list(theme.hero_styles)
        if not has_photo:
            return "typographic" if "typographic" in styles or theme.rule else "split"
        if "typographic" in styles and re.search(r"\b(?:minimal|minimalist|white space|typographic|editorial)\b", self.prompt, re.I):
            return "typographic"
        styles = [s for s in styles if s != "product"] or ["split"]
        digest = int(hashlib.sha256(self.prompt.encode("utf-8")).hexdigest(), 16)
        return styles[digest % len(styles)]

    # ── Rendering ───────────────────────────────────────────────────────────
    def render(self, slug: str) -> list[tuple[str, str]]:
        if slug not in self.contents:
            self.accept(slug, "")
        if self.kinds[slug] in {"header", "footer"}:
            # Links and taglines depend on the final site; refresh them.
            self.contents[slug] = self._header_content() if self.kinds[slug] == "header" else self._footer_content()
        tsx, css = render_section(self, slug, self.kinds[slug], self.contents[slug])
        name = self.component(slug)
        return [(f"src/components/{name}.tsx", tsx), (f"src/components/{name}.css", css.strip() + "\n")]

    def base_css(self) -> str:
        return build_base_css(self.theme)

    def font_href(self) -> str:
        return f"https://fonts.googleapis.com/css2?{self.theme.font_query}&display=swap"

    def _description(self) -> str:
        hero = self.contents.get(self.sections[1], {})
        text = hero.get("lede") or f"{self.brand}, {self.label_text}."
        return text if len(text) <= 160 else text[:157].rsplit(" ", 1)[0] + "…"

    def _hero_photo_url(self) -> str:
        photos = self.section_images.get(self.sections[1], [])
        return photos[0].url(1200) if photos else ""

    def head_tags(self) -> str:
        esc = lambda v: html.escape(str(v), quote=True)
        desc = self._description()
        og_image = self._hero_photo_url() or "/og-image.png"
        hero_img = (self.contents.get(self.sections[1]) or {}).get("img")
        lines = [
            f'<meta name="description" content="{esc(desc)}" />',
            f'<meta name="theme-color" content="{esc(self.theme.colors["bg"])}" />',
            '<meta property="og:type" content="website" />',
            f'<meta property="og:title" content="{esc(self.brand)}" />',
            f'<meta property="og:description" content="{esc(desc)}" />',
            f'<meta property="og:image" content="{esc(og_image)}" />',
            '<meta name="twitter:card" content="summary_large_image" />',
            '<link rel="icon" href="/favicon.svg" type="image/svg+xml" />',
            '<link rel="apple-touch-icon" href="/apple-touch-icon.png" />',
        ]
        if hero_img:
            lines.append(f'<link rel="preload" as="image" href="{esc(hero_img["src"])}" fetchpriority="high" />')
        return "\n    ".join(lines)

    def public_files(self) -> list[tuple[str, Any]]:
        c = self.theme.colors
        mark = html.escape(self._mark())
        display = self.theme.display_font
        favicon = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" '
                   f'fill="{c["accent"]}"/><text x="32" y="44" text-anchor="middle" font-family="Georgia, serif" '
                   f'font-size="36" font-weight="700" fill="{c["accent_ink"]}">{mark}</text></svg>\n')
        files: list[tuple[str, Any]] = [("favicon.svg", favicon), ("404.html", self._page_404())]
        touch = self._png_icon(180, 180)
        if touch:
            files.append(("apple-touch-icon.png", touch))
        if not self._hero_photo_url():
            og = self._png_icon(1200, 630, text=self.brand)
            if og:
                files.append(("og-image.png", og))
        return files

    def _png_icon(self, width: int, height: int, text: str = "") -> Optional[bytes]:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:  # pragma: no cover
            return None
        c = self.theme.colors
        bg = tuple(round(v * 255) for v in _rgb(c["accent"]))
        fg = tuple(round(v * 255) for v in _rgb(c["accent_ink"]))
        image = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(image)
        label = text or self._mark()
        size = int(height * (0.16 if text else 0.56))
        try:
            font = ImageFont.load_default(size=size)
        except TypeError:  # pragma: no cover - old Pillow
            font = ImageFont.load_default()
        box = draw.textbbox((0, 0), label, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        draw.text(((width - tw) / 2 - box[0], (height - th) / 2 - box[1]), label, fill=fg, font=font)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _page_404(self) -> str:
        c = self.theme.colors
        brand = html.escape(self.brand)
        from .base_css import font_stack
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex" />
    <title>Page not found · {brand}</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="{html.escape(self.font_href())}" rel="stylesheet" />
    <style>
      :root {{ color-scheme: {self.theme.mode}; }}
      body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px; background-color: {c['bg']}; color: {c['ink']}; font-family: {font_stack(self.theme.body_font)}; }}
      main {{ max-width: 560px; }}
      p.brand {{ font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; font-size: 0.8125rem; color: {c['muted']}; }}
      h1 {{ font-family: {font_stack(self.theme.display_font)}; font-weight: {self.theme.display_weight}; font-size: clamp(2.4rem, 7vw, 4rem); line-height: 1.04; margin: 12px 0 16px; text-transform: {self.theme.heading_case}; }}
      a {{ display: inline-flex; align-items: center; min-height: 48px; padding: 0 22px; border-radius: {self.theme.button_radius}; background-color: {c['accent']}; color: {c['accent_ink']}; font-weight: 600; text-decoration: none; }}
      a:focus-visible {{ outline: 2px solid {c['ink']}; outline-offset: 3px; }}
    </style>
  </head>
  <body>
    <main>
      <p class="brand">{brand}</p>
      <h1>This page doesn't exist</h1>
      <p>The link may be old or mistyped. Everything else is still here.</p>
      <p><a href="/">Back to the home page</a></p>
    </main>
  </body>
</html>
"""

    def theme_summary(self) -> dict:
        return {"id": self.theme.id, "name": self.theme.name, "mode": self.theme.mode,
                "display_font": self.theme.display_font, "body_font": self.theme.body_font,
                "colors": dict(self.theme.colors), "hero_style": self.hero_style,
                "sections": {s: self.kinds[s] for s in self.sections}}

    def edit_summary(self) -> str:
        """Compact description of the design system for edit turns."""
        classes = ", ".join(f"{self.component(s)} (.{scope_class(s) if self.kinds[s] not in {'header', 'footer'} else 'k-' + self.kinds[s]})"
                            for s in self.sections)
        return (f"DESIGN KIT: theme '{self.theme.name}' ({self.theme.mode}); fonts {self.theme.display_font} / "
                f"{self.theme.body_font}. Tokens in src/App.css: --k-bg, --k-surface, --k-surface-2, --k-ink, --k-muted, "
                f"--k-line, --k-accent, --k-accent-ink, --k-accent-soft, --k-font-display, --k-font-body, --k-radius, "
                f"--k-radius-btn, --k-space-1..12. Primitives: .k-container, .k-section, .k-h2, .k-h3, .k-lede, .k-btn "
                f"(--primary/--ghost). Sections: {classes}. Keep edits inside these classes and tokens.")
