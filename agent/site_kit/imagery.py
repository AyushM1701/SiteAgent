"""Verified, subject-matched photography.

Every photo id below was downloaded and visually checked on 2026-10-16. When no
topic matches the prompt, renderers show a designed art panel instead — never an
unrelated photo and never a placeholder host.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional

_UNSPLASH = "https://images.unsplash.com/photo-{id}?auto=format&fit=crop&w={w}&q=80"

# topic -> [(id, descriptive alt)]
PHOTOS: dict[str, list[tuple[str, str]]] = {
    "coffee": [
        ("1495474472287-4d71bcdd2085", "A cup of coffee on a wooden table"),
        ("1509042239860-f550ce710b93", "Latte art in a ceramic cup"),
        ("1447933601403-0c6688de566e", "Freshly roasted coffee beans"),
        ("1511920170033-f8396924c348", "Coffee being poured into a cup"),
        ("1501339847302-ac426a4a7cbb", "A warm, sunlit cafe interior"),
    ],
    "cafe_street": [("1559925393-8be0ec4767c8", "A cafe front on a quiet street")],
    "restaurant": [
        ("1414235077428-338989a2e8c0", "A plated dish in a restaurant"),
        ("1517248135467-4c7edcad34c4", "A restaurant dining room set for service"),
        ("1555396273-367ea4eb4db5", "Restaurant tables in warm evening light"),
        ("1504674900247-0877df9cc836", "A colourful plate of food"),
        ("1577219491135-ce391730fb2c", "A chef plating food in a kitchen"),
    ],
    "healthy_food": [
        ("1546069901-ba9599a7e63c", "A bowl of fresh salad and grains"),
        ("1540189549336-e6e99c3679fe", "A fresh vegetable salad"),
        ("1512621776951-a57141f2eefd", "A colourful vegetable bowl"),
    ],
    "indian_food": [
        ("1585937421612-70a008356fbe", "A bowl of Indian curry"),
        ("1631452180519-c014fe946bc7", "A spread of Indian dishes"),
        ("1596797038530-2c107229654b", "Spiced Indian dishes in small bowls"),
        ("1601050690597-df0568f70950", "Freshly made samosas"),
        ("1565557623262-b51c2513a641", "A rich Indian curry with rice"),
        ("1588166524941-3bf61a9c41db", "A fragrant plate of biryani"),
    ],
    "bakery": [
        ("1509440159596-0249088772ff", "Loaves of crusty bread"),
        ("1517433670267-08bbd4be890f", "Pastries on a bakery counter"),
        ("1555507036-ab1f4038808a", "Fresh croissants on a tray"),
        ("1558961363-fa8fdf82db35", "Freshly baked cookies"),
        ("1486427944299-d1955d23e34d", "A cake on a stand"),
    ],
    "ceramics": [
        ("1565193566173-7a0ee3dbe261", "Hands shaping clay on a pottery wheel"),
        ("1610701596007-11502861dcfa", "Handmade ceramic vessels on a shelf"),
        ("1578749556568-bc2c40e68b61", "Glazed ceramic bowls and cups"),
        ("1493106641515-6b5631de4bb9", "A potter working at the studio bench"),
    ],
    "yoga": [
        ("1544367567-0f2fcb009e0b", "A person holding a yoga pose"),
        ("1506126613408-eca07ce68773", "Meditation in soft morning light"),
        ("1545205597-3d9d02c29597", "A calm yoga studio"),
        ("1599901860904-17e6ed7083a0", "A yoga class stretching together"),
    ],
    "spa": [("1540555700478-4be289fbecef", "A calm spa treatment room")],
    "fitness": [
        ("1534438327276-14e5300c3a48", "A strength training gym floor"),
        ("1517836357463-d25dfeac3438", "An athlete training with weights"),
        ("1571019613454-1cb2f99b2d8b", "A person training in a gym"),
        ("1583454110551-21f2fa2afe61", "Dumbbells on a gym rack"),
    ],
    "fashion": [
        ("1445205170230-053b83016050", "Clothing on a rail in a boutique"),
        ("1490481651871-ab68de25d43d", "Folded garments in soft light"),
        ("1441986300917-64674bd600d8", "A bright clothing boutique"),
        ("1483985988355-763728e1935b", "Shopping bags held by a customer"),
    ],
    "florist": [
        ("1487070183336-b863922373d4", "A bouquet of fresh flowers"),
        ("1561181286-d3fee7d55364", "A florist arranging flowers"),
        ("1490750967868-88aa4486c946", "Pink flowers in bloom"),
        ("1455659817273-f96807779a8a", "A vase of mixed flowers"),
    ],
    "interior": [
        ("1600210492486-724fe5c67fb0", "A bright, modern living room"),
        ("1586023492125-27b2c045efd7", "A calm interior with a sofa"),
        ("1618221195710-dd6b41faaea6", "A styled interior with natural light"),
        ("1600607687939-ce8a6c25118c", "A minimal kitchen interior"),
    ],
    "architecture": [
        ("1600585154340-be6161a56a0c", "A modern house exterior"),
        ("1487958449943-2429e8be8625", "A contemporary building facade"),
        ("1511818966892-d7d671e672a2", "Architectural lines against the sky"),
        ("1494526585095-c41746248156", "A modern home with large windows"),
    ],
    "photography": [
        ("1452587925148-ce544e77e70d", "A camera on a desk"),
        ("1516035069371-29a1b244cc32", "A photographer holding a camera"),
        ("1502920917128-1aa500764cbd", "A camera lens in close up"),
    ],
    "design": [
        ("1561070791-2526d30994b5", "Design sketches and colour swatches"),
        ("1558655146-9f40138edfeb", "A designer working at a desk"),
        ("1542744094-3a31f272c490", "Brand design work laid out on a table"),
    ],
    "tech": [
        ("1551288049-bebda4e38f71", "An analytics dashboard on a screen"),
        ("1460925895917-afdab827c52f", "Charts on a laptop screen"),
        ("1558494949-ef010cbdcc31", "Server racks in a data centre"),
        ("1518770660439-4636190af475", "Electronic circuitry in close up"),
        ("1550751827-4bd374c3f58b", "Glowing technology hardware"),
        ("1531297484001-80022131f5a1", "A laptop on a dark desk"),
    ],
    "office": [
        ("1497366216548-37526070297c", "A sunlit modern office"),
        ("1497366811353-6870744d04b2", "A contemporary workspace"),
        ("1521737711867-e3b97375f902", "A team at work around a table"),
        ("1551434678-e076c223a692", "Colleagues collaborating"),
        ("1522071820081-009f0129c71c", "A team planning together"),
    ],
    "books": [
        ("1481627834876-b7833e8f5570", "Shelves of books in a library"),
        ("1495446815901-a7297e633e8d", "Stacks of books"),
    ],
    "travel": [
        ("1507525428034-b723cf961d3e", "A quiet tropical beach"),
        ("1501785888041-af3ef285b470", "A lake surrounded by mountains"),
        ("1469474968028-56623f02e42e", "Sunlight over a mountain valley"),
        ("1506744038136-46273834b3fb", "A scenic landscape at golden hour"),
    ],
    "real_estate": [
        ("1564013799919-ab600027ffc6", "A family home with a garden"),
        ("1570129477492-45c003edd2be", "A modern suburban house"),
        ("1512917774080-9991f1c4c750", "A luxury home with a pool"),
    ],
    "wine": [
        ("1510812431401-41d2bd2722f3", "Red wine being poured"),
        ("1506377247377-2a5b3b417ebb", "Vineyard rows at sunset"),
        ("1474722883778-792e7990302f", "Wine glasses on a table"),
    ],
    "music": [
        ("1511379938547-c1f69419868d", "A musician playing guitar"),
        ("1493225457124-a3eb161ffa5f", "A live concert crowd"),
        ("1514525253161-7a46d19cd819", "Stage lights at a concert"),
    ],
    "education": [
        ("1503676260728-1c00da094a0b", "Students learning together"),
        ("1524178232363-1fb2b075b655", "A bright classroom"),
    ],
    "medical": [
        ("1576091160399-112ba8d25d1d", "A doctor in a consultation"),
        ("1538108149393-fbbd81895907", "A clean clinic corridor"),
        ("1588776814546-1ffcf47267a5", "A medical professional at work"),
    ],
    "dental": [
        ("1629909613654-28e377c37b09", "A modern dental treatment room"),
        ("1606811971618-4486d14f3f99", "A dentist with a patient"),
    ],
    "plants": [
        ("1485955900006-10f4d324d411", "Potted houseplants by a window"),
        ("1459411552884-841db9b3cc2a", "Green plants in pots"),
        ("1416879595882-3373a0480b5b", "Hands planting seedlings"),
    ],
    "jewelry": [
        ("1515562141207-7a88fb7ce338", "Fine jewellery on display"),
        ("1599643478518-a784e5dc4c8f", "A gold necklace in close up"),
    ],
    "stationery": [
        ("1455390582262-044cdead277a", "A notebook and pen on a desk"),
        ("1517842645767-c639042777db", "An open notebook with handwriting"),
        ("1531346878377-a5be20888e57", "Stationery laid out on a table"),
    ],
    "skincare": [
        ("1598440947619-2c35fc9aa908", "Skincare bottles on a shelf"),
        ("1570172619644-dfd03ed5d881", "A skincare routine in soft light"),
    ],
    "pets": [
        ("1548199973-03cce0bbc87b", "Two dogs playing on grass"),
        ("1450778869180-41d0601e046e", "A happy dog outdoors"),
    ],
    "event": [
        ("1540575467063-178a50c2df87", "An audience at a conference"),
        ("1505373877841-8d25f7d46678", "A speaker on stage at an event"),
        ("1511578314322-379afb476865", "Guests at an evening event"),
    ],
    "law": [
        ("1589829545856-d10d557cf95f", "Scales of justice on a desk"),
        ("1505664194779-8beaceb93744", "Law books on a shelf"),
        ("1450101499163-c8848c66ca85", "Signing a document at a desk"),
    ],
    "finance": [
        ("1554224155-6726b3ff858f", "Financial documents and a calculator"),
        ("1486406146926-c627a92ad1ab", "Office towers in a financial district"),
        ("1611974789855-9c2a0a7236a3", "Market charts on a screen"),
    ],
    "nature": [
        ("1441974231531-c6227db76b6e", "Sunlight through a forest"),
        ("1470071459604-3b5ec3a7fe05", "Misty hills at dawn"),
    ],
    "craft": [("1452860606245-08befc0ff44b", "Craft tools on a workbench")],
    "cars": [
        ("1492144534655-ae79c964c9d7", "A classic car on the road"),
        ("1503376780353-7e6692767b70", "A sports car in close up"),
    ],
}

# Ordered: more specific subjects first; tech near the end; office/nature last.
_TOPIC_PATTERNS: list[tuple[str, str]] = [
    ("ceramics", r"ceramic|pottery|potter|\bclay\b|kiln|glaze"),
    ("indian_food", r"\bindian\b|curry|biryani|tandoor|masala|dosa|samosa"),
    ("bakery", r"bakery|bakehouse|bread|pastr|patisserie|croissant|cake|cookie|donut|doughnut"),
    ("coffee", r"coffee|espresso|roaster|roastery|\bcafe\b|café|latte"),
    ("wine", r"\bwine|winery|vineyard|sommelier"),
    ("healthy_food", r"salad|vegan|healthy food|smoothie|juice bar|plant-based"),
    ("restaurant", r"restaurant|bistro|dining|kitchen|eatery|ramen|sushi|tapas|\bchef\b|cuisine|\bmenu\b"),
    ("yoga", r"\byoga|pilates|meditation|mindfulness"),
    ("spa", r"\bspa\b|massage|wellness|retreat"),
    ("fitness", r"\bgym\b|fitness|strength|crossfit|workout|boxing|athlet|personal train"),
    ("dental", r"dental|dentist|orthodont"),
    ("medical", r"medical|clinic|doctor|health ?care|physio|hospital|therap"),
    ("florist", r"florist|flower|bouquet|floral"),
    ("plants", r"\bplants?\b|nursery|garden|seedling|botanical"),
    ("jewelry", r"jewel|necklace|\brings?\b|bracelet"),
    ("skincare", r"skincare|skin care|cosmetic|beauty|serum"),
    ("fashion", r"fashion|clothing|apparel|boutique|garment|tailor|wardrobe"),
    ("stationery", r"stationery|notebook|\bpaper goods|pencil|\bpens?\b|planner"),
    ("books", r"\bbooks?\b|bookshop|bookstore|library|publisher|author"),
    ("photography", r"photographer|photo studio"),
    ("architecture", r"architect|architecture"),
    ("interior", r"interior|furniture|home decor|living room"),
    ("real_estate", r"real estate|realty|property|properties|\bhomes\b|apartment|villa"),
    ("travel", r"travel|\btours?\b|resort|beach|island|holiday|vacation|adventure"),
    ("event", r"conference|festival|\bevents?\b|summit|meetup|wedding"),
    ("music", r"music|band|concert|record label|musician|\bdj\b"),
    ("education", r"school|academy|course|classes for|tutor|education|learning|camp"),
    ("law", r"\blaw\b|lawyer|legal|attorney|solicitor"),
    ("finance", r"finance|financial|accounting|accountant|\btax\b|invest|wealth|insurance"),
    ("pets", r"\bpets?\b|\bdogs?\b|\bcats?\b|grooming|veterinar"),
    ("cars", r"\bcars?\b|automotive|garage|mechanic|motor"),
    ("craft", r"\bcraft|woodwork|workshop|maker"),
    ("design", r"brand design|designer|design studio|branding|graphic design|portfolio"),
    ("tech", r"saas|software|platform|analytics|\bdata\b|\bai\b|developer|\bapi\b|cloud|startup|logistics|\bapp\b"),
    ("office", r"consult|agency|business services|b2b|office"),
    ("nature", r"nature|forest|outdoor|hiking|eco|sustainab"),
]

_GENERIC_TOPICS = {"tech", "office", "nature"}

_NO_PHOTOS_RE = re.compile(r"\b(?:no|without|avoid)\s+(?:stock\s+)?(?:photos?|photography|images?|imagery|pictures?)\b", re.I)


@dataclass(frozen=True)
class Photo:
    id: str
    alt: str
    topic: str

    def url(self, width: int = 1200) -> str:
        return _UNSPLASH.format(id=self.id, w=width)


def detect_topics(prompt: str) -> list[str]:
    try:
        from agent.site_brief import _is_negated
    except ImportError:  # pragma: no cover
        from site_brief import _is_negated  # type: ignore
    lower = prompt.lower()
    topics: list[str] = []
    for topic, pattern in _TOPIC_PATTERNS:
        if any(not _is_negated(lower, m.start(), m.end()) for m in re.finditer(pattern, lower)):
            topics.append(topic)
    return topics


class ImagePlanner:
    """Hands out unused photos for the prompt's first two topics."""

    def __init__(self, prompt: str, topics: Optional[list[str]] = None):
        self.enabled = not _NO_PHOTOS_RE.search(prompt or "")
        found = topics if topics is not None else detect_topics(prompt or "")
        # Generic topics only pair with each other; a ceramics site never borrows office stock.
        if found and found[0] not in _GENERIC_TOPICS:
            found = [found[0]] + [t for t in found[1:] if t not in _GENERIC_TOPICS]
        self.topics = found[:2]
        seed = int(hashlib.sha256((prompt or "").encode("utf-8")).hexdigest(), 16)
        pool: list[Photo] = []
        for index, topic in enumerate(self.topics):
            rows = [Photo(pid, alt, topic) for pid, alt in PHOTOS.get(topic, [])]
            if index == 0 and rows:
                shift = seed % len(rows)
                rows = rows[shift:] + rows[:shift]
            pool.extend(rows)
        self._pool = pool if self.enabled else []
        self._used: set[str] = set()

    @property
    def available(self) -> int:
        return len([p for p in self._pool if p.id not in self._used])

    def take(self, n: int) -> list[Photo]:
        """Unused photos first; never repeats while any remain."""
        fresh = [p for p in self._pool if p.id not in self._used][:n]
        for photo in fresh:
            self._used.add(photo.id)
        return fresh
