"""Reusable composition guidance and tested visual assets for small-model sites."""
from pathlib import Path
import re

ASSET_DIR = Path(__file__).with_name("visual_assets")

PROFESSIONAL_SITE_CONTRACT = """
ART DIRECTION: Build a cohesive product story, not a stack of interchangeable cards.
Use a strong type hierarchy, constrained text widths, generous spacing, one dominant
hero visual and varied section density. Preserve the user's brand, copy and sections.
Use real supplied imagery or provided visual primitives; never invent asset URLs.
Do not invent customer logos, testimonials, awards, or numerical performance claims.

BILLING & PRICING: If the user supplies billing terms (monthly/annual toggle, exact
prices, or discount percentages), preserve them exactly. Annual totals must be
mathematically correct (e.g. annual = monthly × 12 × (1 − discount)). Update all
visible amounts, billing period labels, and aria-label/aria-checked attributes when the
toggle changes. Never hard-code "20% off" unless the user specified it; label illustrative
pricing as such. Do not show three pricing tiers unless the user requested them.

INTERACTION & TABS: Tab components must respond to keyboard arrow keys (ArrowLeft/ArrowRight)
and update aria-selected on the active tab and aria-hidden on inactive panels. Show visible
focus rings on all interactive controls. Toggle switches for billing must also respond to
Enter and Space. Accordions must expand/collapse on click and keyboard activation.

MOBILE NAVIGATION: The mobile hamburger must render a visible menu on small viewports when
open (not off-screen or z-index blocked). The drawer must close on Escape and restore focus
to the trigger. Never place a sticky header inside a scrolling or overflow-hidden ancestor.
Test the layout at 375px: no element should cause horizontal overflow.
Keep wordmarks separate from display headings: use a small responsive brand label in
navigation, one primary h1 in the main content, and a bounded fluid hero type scale.
Overflow hiding is not a mobile layout fix: all links, cart and menu controls must stay
inside the visible viewport or inside a keyboard-accessible opened drawer.

FORMS: Label every input. Show inline validation errors. Disabled submit until required
fields are filled. Never claim a form was submitted without a real backend; show a local
confirmation state instead (e.g. "Message received — we'll be in touch.").

MOTION: Prefer transform/opacity, brief entrances and restrained hover feedback. Keep
content visible without JS. Honor prefers-reduced-motion; provide pause for looping art.
Looping animations need accessible pause controls.
When scroll parallax is requested, connect scroll progress to visible displacement;
hover zoom and translate3d(0,0,0) do not fulfill it. Requested scroll reveals need an
observer or scroll timeline and a visible transition, with readable content in reduced motion.
CSS 3D needs perspective, preserve-3d geometry and a visible dimensional composition.
A requested flat-view toggle must change the scene into an accessible flat composition.

RESPONSIVE: Work at 375px without horizontal overflow; preserve readable contrast and
keyboard focus. Decorative visuals must not block pointer input or obscure text.
Use var(--on-accent) for text on accent CTAs. Check both normal and hover/focus colors;
do not use the same accent token for text and its background. Preserve supplied tokens.
Every in-page href must target an existing section ID. Reduced-motion overrides must
win the CSS cascade, including document scrolling.

CSS OWNERSHIP: Scope every component rule to its section ID or unique root class.
Never define shared .section__inner, .btn or heading rules in an individual section.
Keep sticky navigation outside scrolling/overflow-hidden ancestors.

HONESTY: Do not use href="#", fake contacts (e.g. example.com, 555 numbers) or
fabricated social URLs. Placeholder destinations need honest local behavior.
Keep demo/illustrative pricing, testimonials and metrics clearly labeled as such.
""".strip()


def wants_dimensional_visual(prompt: str) -> bool:
    return bool(re.search(r"\b(?:3[ -]?d|three[ -]dimensional|dimensional|spatial)\b", prompt, re.I))


def jsx_open_tags(source: str, tag: str):
    """Yield (start, attributes) for each <tag ...> open tag, reading attribute
    values with balanced braces and quotes so `ref={(el) => ...}` does not end
    the tag at the arrow's '>' (B9b)."""
    for match in re.finditer(rf'<{tag}\b', source):
        i, depth, quote = match.end(), 0, ''
        while i < len(source):
            ch = source[i]
            if quote:
                if ch == quote and source[i - 1] != '\\':
                    quote = ''
            elif ch in '"\'`':
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth = max(0, depth - 1)
            elif ch == '>' and depth == 0:
                break
            i += 1
        yield match.start(), source[match.end():i]


def collect_site_rendering_diagnostics(files: dict[str, str], prompt: str = "") -> list[str]:
    """Return source evidence of rendering failures, never a browser pass certificate.

    Contrast checks deliberately cover only directly declared, opaque color pairs.
    Complex inheritance, selectors, alpha compositing, responsive control bounds and
    actual motion displacement still require browser validation. No files are repaired.
    """
    from agent.style_ingest import parse_css_rule_blocks, wcag_contrast_ratio

    css_files = {path: re.sub(r'/\*.*?\*/', '', source, flags=re.S)
                 for path, source in files.items() if path.endswith('.css')}
    jsx_files = {path: source for path, source in files.items()
                 if path.endswith(('.tsx', '.jsx', '.html'))}
    css = '\n'.join(css_files.values())
    jsx = '\n'.join(jsx_files.values())
    # Only document tokens are globally resolvable; component-scoped variables
    # must not be treated as a different component's colors.
    tokens = {}
    for selector, body, _ in parse_css_rule_blocks(css):
        if ':root' in selector:
            tokens.update(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', body))

    def resolve(value, local=None):
        value = value.strip()
        variables = {**tokens, **(local or {})}
        for _ in range(12):
            match = re.fullmatch(r'var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)', value)
            if not match:
                break
            replacement = variables.get(match.group(1), match.group(2))
            if replacement is None or replacement == value:
                return None
            value = replacement.strip()
        return value

    def opaque(value):
        return value and not re.search(r'rgba\(|hsla\(|(?:rgb|hsl)\([^)]*/|transparent|gradient|color-mix', value, re.I) and not re.fullmatch(r'#[0-9a-fA-F]{4}|#[0-9a-fA-F]{8}', value)

    errors = []
    nav_sources = {path: source for path, source in jsx_files.items()
                   if re.search(r'<nav\b', source) or re.search(r'(?:navbar|header)\.', path, re.I)}
    nav_heading_classes = set()
    nav_root_classes = set()
    nav_has_heading = False
    for source in nav_sources.values():
        for region in re.finditer(r'<(?P<tag>nav|header)\b[\s\S]*?</(?P=tag)>', source):
            markup = region.group(0)
            nav_has_heading = nav_has_heading or bool(re.search(r'<h[12]\b', markup))
            for match in re.finditer(r'<(?:nav|header)\b[^>]*className=["\']([^"\']+)', markup):
                nav_root_classes.update(match.group(1).split())
            for match in re.finditer(r'<h[12]\b[^>]*className=["\']([^"\']+)', markup):
                nav_heading_classes.update(match.group(1).split())
    for path, source in css_files.items():
        blocks = parse_css_rule_blocks(source)
        base_rules = {selector: dict(re.findall(r'(?<![\w-])([\w-]+)\s*:\s*([^;{}]+)', body))
                      for selector, body, _ in blocks}
        for selector, body, _ in blocks:
            declarations = dict(re.findall(r'(?<![\w-])([\w-]+)\s*:\s*([^;{}]+)', body))
            # For a simple pseudo state, unchanged properties still come from
            # the exact base selector. Avoid guessing broader selector cascade.
            base_selector = re.sub(r':(?:hover|focus|focus-visible|active)$', '', selector)
            if base_selector != selector and base_selector in base_rules:
                declarations = {**base_rules[base_selector], **declarations}
            local = dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', body))
            fg = resolve(declarations.get('color', ''), local)
            bg = resolve(declarations.get('background-color', declarations.get('background', '')), local)
            size = resolve(declarations.get('font-size', ''), local)
            numeric_size = re.fullmatch(r'(\d+(?:\.\d+)?)(px|rem)', size or '')
            pixels = float(numeric_size.group(1)) * (16 if numeric_size.group(2) == 'rem' else 1) if numeric_size else 0
            bold = re.fullmatch(r'(?:bold|[7-9]00)', declarations.get('font-weight', '').strip())
            minimum = 3.0 if pixels >= 24 or (pixels >= 18.66 and bold) else 4.5
            if opaque(fg) and opaque(bg):
                ratio = wcag_contrast_ratio(fg, bg)
                if ratio is not None and ratio < minimum:
                    errors.append(f'[{path}] [TEXT CONTRAST]: {selector} declares {ratio:.2f}:1 foreground/background contrast; check normal, hover and focus rendering.')
            nav_selector = any(re.search(rf'\.{re.escape(name)}\b', selector) for name in nav_heading_classes)
            heading_selector = re.search(r'(?:^|[\s,])h[12](?:$|[\s,:])', selector)
            nav_scope = re.search(r'(?:^|[\s,])(?:nav|header)(?:$|[\s.#:])', selector) or any(re.search(rf'\.{re.escape(name)}\b', selector) for name in nav_root_classes)
            nav_selector = nav_selector or bool(nav_has_heading and heading_selector and (nav_scope or selector.strip() in {'h1', 'h2'}))
            if nav_selector and size:
                large = re.fullmatch(r'(\d+(?:\.\d+)?)(px|rem)', size)
                if large and float(large.group(1)) * (16 if large.group(2) == 'rem' else 1) > 64:
                    errors.append(f'[{path}] [NAV TYPOGRAPHY]: {selector} applies {size} display type to navigation headings; use a responsive wordmark and verify control bounds at 375px.')
            if (re.search(r'(?:^|[\s,])(?:html|body|#root|\.site-root)(?:$|[\s,:])', selector)
                    and any(re.search(r'\b(?:hidden|clip)\b', declarations.get(prop, '')) for prop in ('overflow', 'overflow-x'))
                    and re.search(r'<(?:button|a)\b', jsx)):
                errors.append(f'[{path}] [CONTROL CLIPPING]: {selector} hides horizontal overflow around controls; document scrollWidth cannot prove mobile accessibility. Verify visible bounds and open navigation.')

        # Match whole reduced-motion blocks, then compare later ordinary html
        # scrolling declarations. !important auto remains safe against those.
        for match in re.finditer(r'@media\s*\([^)]*prefers-reduced-motion\s*:\s*reduce[^)]*\)\s*\{', source):
            depth, end = 1, match.end()
            while end < len(source) and depth:
                depth += (source[end] == '{') - (source[end] == '}')
                end += 1
            block = source[match.end():end - 1]
            if re.search(r'html\s*\{[^}]*scroll-behavior\s*:\s*auto\s*;', block) and re.search(r'html\s*\{[^}]*scroll-behavior\s*:\s*smooth', source[end:]):
                errors.append(f'[{path}] [REDUCED MOTION]: later html smooth scrolling overrides the reduce rule; place the override last or make auto important.')

    ids = set(re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', jsx))
    for path, source in jsx_files.items():
        form_ranges = [(m.start(), m.end()) for m in re.finditer(r'<form\b[\s\S]*?</form>', source, re.I)]
        for button_start, attributes in jsx_open_tags(source, 'button'):
            within_form = any(start <= button_start < end for start, end in form_ranges)
            if (not within_form and not re.search(r'\bon[A-Z]\w*\s*=|\bonclick\s*=|\{\s*\.\.\.|\bdisabled(?:\s|$|=\{true\})', attributes)):
                errors.append(f'[{path}] [INERT BUTTON]: button has no event handler or containing form; use a real section link for navigation or implement its visible action.')
        for target in re.findall(r'\bhref\s*=\s*["\']#([^"\']+)["\']', source):
            if target not in ids:
                errors.append(f'[{path}] [ANCHOR TARGET]: #{target} has no declared target; verify the rendered target and scroll result.')

    scroll_source = bool(re.search(r'addEventListener\(\s*["\']scroll["\']|\b(?:scrollY|scrollTop|useScroll)\b|animation-timeline\s*:\s*(?:scroll|view)\(', jsx + '\n' + css))
    displacement = bool(re.search(r'(?:translate[XYZ]?\(|style\.transform|setProperty\([^)]*(?:scroll|parallax))', jsx + '\n' + css))
    if re.search(r'\bparallax\b', prompt, re.I) and not (scroll_source and displacement):
        errors.append('[SCROLL PARALLAX]: requested scroll displacement has no supported scroll-to-transform source evidence; a class name or hover zoom is insufficient.')
    reveal_requested = bool(re.search(r'\breveals?\b', prompt, re.I))
    observer = bool(re.search(r'\b(?:IntersectionObserver|useInView)\b|animation-timeline\s*:\s*view\(', jsx + '\n' + css))
    reveal_transition = bool(re.search(r'(?:transition\s*:[^;]*opacity|@keyframes\b)', css))
    if reveal_requested and not (observer and reveal_transition):
        errors.append('[SCROLL REVEAL]: requested reveal lacks supported viewport trigger and transition evidence; validate its visible timeline in a browser.')
    if wants_dimensional_visual(prompt):
        composition = bool(re.search(r'perspective\s*:\s*(?!none\b|0(?:px)?\s*[;}])\S+', css)
                           and re.search(r'transform-style\s*:\s*preserve-3d', css)
                           and re.search(r'(?:rotate[XY]\(|translateZ\(\s*(?!0(?:px)?\s*\))|matrix3d\()', css))
        if not composition and not re.search(r'<canvas\b|\bCanvas\b|WebGLRenderer', jsx):
            errors.append('[3D COMPOSITION]: requested 3D has no supported perspective/geometry or canvas evidence; translate3d(0,0,0) is a flat wrapper.')
    if re.search(r'flat[ -]?(?:view|mode)', prompt, re.I):
        flat_control = re.search(r'<(?:button|input)\b[^>]*(?:onClick|onChange)\s*=', jsx)
        flat_state = re.search(r'\b(?:setFlat\w*|set\w*Flat\w*)\s*\(', jsx, re.I)
        if not (flat_control and flat_state):
            errors.append('[FLAT VIEW]: requested flat view lacks supported interactive state evidence; its label alone is insufficient. Verify scene changes in a browser.')
    return list(dict.fromkeys(errors))


def prepare_site_quality(prompt: str, directory: Path):
    files = {}
    instructions = PROFESSIONAL_SITE_CONTRACT
    if wants_dimensional_visual(prompt):
        for name in ("PremiumScene.tsx", "PremiumScene.css"):
            relative = f"src/visuals/{name}"
            content = (ASSET_DIR / name).read_text(encoding="utf-8")
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            files[relative] = content
        instructions += """
PROVIDED 3D ART: src/visuals/PremiumScene.tsx is already installed. In the Hero section,
import PremiumScene from '../visuals/PremiumScene'; render <PremiumScene /> beside the
headline. It includes CSS 3D geometry, pause/change-view controls and reduced motion.
Let the scene keep its intrinsic height: never crop it with a fixed-height wrapper or
overflow:hidden. Its controls must remain visible. Do not animate the entire hero on hover.
Do not rewrite these files or import Three.js, React Three Fiber or animation packages.
This is abstract CSS 3D art, not a product-specific 3D model or generated photograph.
"""
    return instructions, files
