"""Tell design directions apart from business copy that happens to use design words.

"Warm ivory palette with editorial typography." is a style instruction leaking into a
page. "Explore our palette of 200 paint colours." is a paint shop describing its stock.
Both contain "palette"; only the first is a leak. A sentence that names a design term
is treated as a leak when it is about the website itself, or when every other content
word is style vocabulary (a bare direction with nothing about the business in it).
"""
from __future__ import annotations

import re

DESIGN_TERM_RE = re.compile(
    r"\b(?:palettes?|typography|typefaces?|fonts?|font\s+pairings?|colou?r\s+schemes?|design\s+systems?|"
    r"design\s+language|layouts?|aesthetics?|art\s+direction)\b", re.I)

# The sentence talks about the page/site/code rather than the business.
SITE_META_RE = re.compile(
    r"\b(?:website|web\s+site|this\s+site|the\s+site|this\s+page|the\s+page|homepage|landing\s+page|sections?|"
    r"hero|header|footer|navbar|navigation|css|hex|tokens?|ui)\b|#[0-9a-f]{3,6}\b", re.I)

_DIRECTION_VOCAB = set("""
palette palettes typography typeface typefaces font fonts pairing pairings scheme schemes design system systems
language layout layouts aesthetic aesthetics art direction style styled styling look looks vibe feel tone tones
hue hues shade shades accent accents colour colours color colors serif sans display body heading headings
minimal minimalist editorial clean bold airy moody playful elegant modern premium sleek rich deep earthy natural
neutral vibrant bright soft subtle restrained generous refined luxurious cozy cosy warm cool muted pastel neon
monochrome contrast high-contrast dark light white space whitespace texture textures gradient gradients grain
photography imagery images visual visuals motion animation animations rounded sharp geometric organic
ivory cream terracotta sage navy charcoal black gold beige olive burgundy cobalt lavender espresso forest green
blue red pink orange purple grey gray brown teal coral mustard rust
use using keep make apply choose pick pair paired pairs set feature featuring throughout overall plenty lots
generous large small big tight loose
""".split())

_STOPWORDS = set("""a an the and or but of for to in on at by with from into over under about our your their its
is are be been this that these those as so very more most just also only not no do does it we you they
""".split())


def is_design_direction(sentence: str) -> bool:
    """True when a sentence containing a design term reads as a style instruction."""
    text = str(sentence or "")
    if not DESIGN_TERM_RE.search(text):
        return False
    if SITE_META_RE.search(text):
        return True
    words = [w for w in re.findall(r"[a-z][a-z'-]*", text.lower()) if w not in _STOPWORDS]
    return all(w in _DIRECTION_VOCAB for w in words)
