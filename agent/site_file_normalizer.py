"""Small deterministic repairs for complete generated site file pairs."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, List, Tuple

from agent.tailwind_support import is_tailwind_utility


def _repair_common_interaction_patterns(content: str, section_name: str, original_prompt: str) -> str:
    """Repair a few complete but inert controls emitted by the local site model."""
    section = section_name.lower()
    prompt = original_prompt.lower()
    # A null-initialized selection state needs a type when later assigned a
    # typed string identifier. Qwen frequently omits this generic in galleries.
    for match in list(re.finditer(
        r'\b(?:React\.)?useState\(null\)', content
    )):
        prefix = content[:match.start()]
        binding = re.search(r'\[\s*\w+\s*,\s*(set\w+)\s*\]\s*=\s*$', prefix)
        if not binding:
            continue
        setter = binding.group(1)
        assignments = re.findall(rf'\b{re.escape(setter)}\(\s*(\w+)\s*\)', content)
        if any(re.search(rf'\b{re.escape(arg)}\s*:\s*string\b', content) for arg in assignments):
            content = content[:match.start()] + match.group(0).replace('useState(', 'useState<string | null>(') + content[match.end():]
            break
    content = re.sub(r'\.tags\.map\(\s*\(tag\)\s*=>', '.tags.map((tag: string) =>', content)
    if re.search(r'gallery|case[-_]?stud|projects', section) and "querySelector('.lightbox')?.classList.add('active')" in content:
        content = content.replace(
            "document.querySelector('.lightbox')?.classList.add('active');",
            "const selected = projects.find(project => project.id === id); "
            "if (selected) window.dispatchEvent(new CustomEvent('site-open-lightbox', { detail: selected }));",
        )
    if "lightbox" in section and "site-open-lightbox" not in content:
        signature = re.search(
            r'(export\s+default\s+function\s+\w+)\(\s*\{\s*project\s*\}\s*:\s*\{\s*project\s*:\s*any\s*\}\s*\)\s*\{',
            content,
        )
        if signature:
            listener = (
                "\n  const [project, setProject] = React.useState<any>(null);\n"
                "  React.useEffect(() => {\n"
                "    const open = (event: Event) => setProject((event as CustomEvent).detail);\n"
                "    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') setProject(null); };\n"
                "    window.addEventListener('site-open-lightbox', open);\n"
                "    window.addEventListener('keydown', close);\n"
                "    return () => { window.removeEventListener('site-open-lightbox', open); window.removeEventListener('keydown', close); };\n"
                "  }, []);"
            )
            content = content[:signature.start()] + signature.group(1) + "() {" + listener + content[signature.end():]
            content = content.replace("setActive(false)", "setProject(null)")
            returns = list(re.finditer(r'\breturn\s*\(', content))
            if returns:
                last_return = returns[-1]
                content = content[:last_return.start()] + "if (!project) return null;\n  " + content[last_return.start():]
    if section == "features" and "interactive metrics explorer" in prompt:
        if "activeTab" in content and "features.map((feature) =>" in content and ".filter((feature) =>" not in content:
            content = content.replace(
                "features.map((feature) =>",
                "features.filter((feature) => activeTab.toLowerCase() === 'all' || "
                "feature.id === activeTab.toLowerCase()).map((feature) =>",
                1,
            )
    if section == "pricing" and re.search(r"monthly\s*(?:vs|/|and)\s*annual", prompt):
        if "billingType" in content and "tier.price" in content:
            content = content.replace(
                ">${tier.price}</p>",
                ">{billingType === 'annual' ? "
                "`$${Math.round(Number(tier.price.replace(/[^0-9.]/g, '')) * 12 * 0.85)}/year` "
                ": `${tier.price}/month`}</p>",
                1,
            )
        content = re.sub(
            r'<button\b(?![^>]*\bonClick\b)[^>]*>\s*Get Started\s*</button>',
            '', content, flags=re.I,
        )
    if section in {"header", "navbar"} and "setIsMenuOpen" in content:
        content = re.sub(
            r'<button(\s+onClick=\{\(\) => setIsMenuOpen\([^>]*?)(>)',
            lambda match: (
                '<button aria-label="Toggle navigation" aria-controls="mobile-navigation" '
                'aria-expanded={isMenuOpen}' + match.group(1) + match.group(2)
            ),
            content,
            count=1,
        ) if 'aria-controls="mobile-navigation"' not in content else content
        if 'aria-controls="mobile-navigation"' in content and 'id="mobile-navigation"' not in content:
            content = re.sub(
                r'<div(?=\s+className=\{`[^`]*\b(?:isMenuOpen|menuOpen))',
                '<div id="mobile-navigation"',
                content,
                count=1,
            )
        if (re.search(r'const\s*\[isDark,\s*setIsDark\]\s*=\s*useState\(true\);', content)
                and content.count("isDark") <= 3):
            content = re.sub(r'<button\b.*?\bsetIsDark\(.*?>.*?</button>', '', content, count=1, flags=re.S)
            content = re.sub(r'\s*const\s*\[isDark,\s*setIsDark\]\s*=\s*useState\(true\);', '', content, count=1)
        elif "setIsDark" in content and 'aria-label="Toggle color theme"' not in content:
            content = re.sub(
                r'<button(\s+onClick=\{\(\) => setIsDark\([^>]*?)(>)',
                lambda match: '<button aria-label="Toggle color theme"' + match.group(1) + match.group(2),
                content,
                count=1,
            )
    return content


def is_substantive_fallback_rewrite(before: str, after: str) -> bool:
    """Reject a fallback rewrite that only clears its status marker or formatting."""
    if not re.search(r'data-fallback\s*=\s*["\']true["\']', before):
        return True
    marker = r'data-fallback\s*=\s*["\'](?:true|false)["\']'
    old_body = re.sub(r'\s+', '', re.sub(marker, '', before))
    new_body = re.sub(r'\s+', '', re.sub(marker, '', after))
    return SequenceMatcher(None, old_body, new_body).ratio() < 0.95


def normalize_site_section_files(
    files: List[Tuple[str, str]],
    section_name: str,
    original_prompt: str = "",
    known_sections: Iterable[str] = (),
) -> List[Tuple[str, str]]:
    """Wire file pairs and anchors, and repair narrowly recognized inert controls."""
    css_paths = {path for path, _ in files if path.endswith(".css")}
    known = {section.lower() for section in known_sections}
    root_class = ""
    for path, source in files:
        if path.endswith((".tsx", ".jsx")):
            root = re.search(r'<(?:section|header|footer)\b[^>]*\bclassName=["\']([^"\']+)', source, re.I)
            if root:
                root_class = next((token for token in root.group(1).split() if not is_tailwind_utility(token)), "")
                if root_class:
                    break
    normalized: List[Tuple[str, str]] = []
    for path, content in files:
        if path.endswith(".css"):
            # Some model outputs paste a Tailwind class list into a CSS rule.
            # That is not a declaration and makes the stylesheet fail parsing.
            lines = []
            inside_rule = False
            for line in content.splitlines(keepends=True):
                stripped = line.strip()
                tokens = stripped.split()
                pasted_utilities = (
                    inside_rule
                    and len(tokens) >= 2
                    and ";" not in stripped
                    and "{" not in stripped
                    and "}" not in stripped
                    and all(is_tailwind_utility(token) for token in tokens)
                )
                if not pasted_utilities:
                    lines.append(line)
                if "{" in line:
                    inside_rule = True
                if "}" in line:
                    inside_rule = False
            content = "".join(lines)
            if root_class:
                content = re.sub(
                    r'(?m)^(\s*)\.section__inner\s*\{',
                    rf'\1.{root_class} .section__inner {{',
                    content,
                )
        if path.endswith((".tsx", ".jsx")):
            content = _repair_common_interaction_patterns(content, section_name, original_prompt)
            if section_name.lower() == "hero" and "products" in known:
                content = re.sub(
                    r'<button\b(?![^>]*\bonClick\b)([^>]*)>\s*(Shop Now|View Catalog|Browse Products)\s*</button>',
                    lambda match: f'<a href="#products"{match.group(1)}>{match.group(2)}</a>',
                    content,
                    flags=re.I | re.S,
                )
            content = content.replace('href="#"', 'href="#site-main"').replace("href='#'", "href='#site-main'")
            if section_name.lower() == "footer":
                # Generated footer placeholders often point unrelated labels
                # at the page top. Keep genuine "back to top" links intact.
                content = re.sub(
                    r'<a\b[^>]*\bhref=["\']#site-main["\'][^>]*>\s*'
                    r'(Careers|FAQ|Privacy(?: Policy)?|Terms(?: of Service)?)\s*</a>',
                    lambda match: f'<span>{match.group(1)}</span>',
                    content,
                    flags=re.I,
                )
            def local_section_link(match: re.Match[str]) -> str:
                quote, route = match.group(1), match.group(2)
                target = route.strip("/").lower()
                if not target:
                    return f'href={quote}#site-main{quote}'
                if target in known:
                    return f'href={quote}#{target}{quote}'
                return match.group(0)
            content = re.sub(r'href=(\'|\")(/[^\'"?#]*)\1', local_section_link, content)
            if "contact" not in known and "footer" in known:
                content = content.replace('href="#contact"', 'href="#footer"').replace("href='#contact'", "href='#footer'")
            if original_prompt:
                allowed_emails = {email.lower() for email in re.findall(
                    r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', original_prompt
                )}
                if section_name.lower() in {"contact", "checkout", "booking", "newsletter", "donate"}:
                    # A local form must not report a message, booking or order as
                    # completed when the component has no submission integration.
                    if not re.search(r"\b(?:fetch|axios\.|sendEmail|submitOrder)\s*\(", content):
                        content = re.sub(
                            r"\balert\(\s*(['\"])(?:(?!\1).)*\b(?:sent|submitted|placed|confirmed|subscribed)(?:(?!\1).)*\1\s*\)",
                            "alert('Demo only: this form is not connected to a service.')",
                            content,
                            flags=re.I,
                        )
                allowed_phones = {
                    re.sub(r'\D', '', phone) for phone in re.findall(
                        r'(?:\+?\d{1,3}[\s.-]*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}', original_prompt
                    )
                }

                def scrub_contact_paragraph(match: re.Match[str]) -> str:
                    body = match.group(2)
                    emails = {email.lower() for email in re.findall(
                        r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', body
                    )}
                    phones = {
                        re.sub(r'\D', '', phone) for phone in re.findall(
                            r'(?:\+?\d{1,3}[\s.-]*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}', body
                        )
                    }
                    if emails - allowed_emails or phones - allowed_phones:
                        return f'<p{match.group(1)}>Contact details are available upon request.</p>'
                    return match.group(0)

                content = re.sub(r'<p([^>]*)>([^<]*)</p>', scrub_contact_paragraph, content, flags=re.S)
            repaired_lines = []
            for line in content.splitlines(keepends=True):
                if ("</button>" in line and re.search(r'\{\s*\w+\s*\?\s*<', line)
                        and line.count("{") == line.count("}") + 1):
                    line = line.replace("</button>", "}</button>", 1)
                repaired_lines.append(line)
            content = "".join(repaired_lines)
            has_link_definition = (
                re.search(r'\bimport\b[^;\n]*\bLink\b[^;\n]*\bfrom\b', content)
                or re.search(r'\b(?:function|class|const|let)\s+Link\b', content)
            )
            if re.search(r'<Link\b', content) and not has_link_definition:
                def replace_undeclared_link(match: re.Match[str]) -> str:
                    tag = match.group(0).replace("<Link", "<a", 1).replace("</Link", "</a", 1)
                    return re.sub(r'\bto(?=\s*=)', "href", tag)

                content = re.sub(r'</?Link\b[^>]*>', replace_undeclared_link, content)
                content = content.replace('href="#"', 'href="#site-main"').replace("href='#'", "href='#site-main'")
            react_hooks = ("useState", "useEffect", "useRef", "useMemo", "useCallback", "useId")
            react_imports = " ".join(re.findall(r"import\s+[^;\n]+\s+from\s+['\"]react['\"]", content))
            missing_hooks = [hook for hook in react_hooks
                             if re.search(rf"(?<![\w.]){hook}\s*\(", content)
                             and not re.search(rf"\b{hook}\b", react_imports)]
            if missing_hooks:
                content = f"import {{ {', '.join(missing_hooks)} }} from 'react';\n" + content
            css_path = str(Path(path).with_suffix(".css")).replace("\\", "/")
            if css_path in css_paths:
                css_name = Path(css_path).name
                if not re.search(rf"\bimport\s*['\"]\./{re.escape(css_name)}['\"]", content):
                    content = f"import './{css_name}';\n" + content
            if section_name:
                section_id = re.sub(r"[^a-z0-9-]", "-", section_name.lower().replace("_", "-"))
                root_tag = re.search(r"<(section|header|footer)\b[^>]*>", content, re.I)
                if root_tag and not re.search(r"\bid\s*=", root_tag.group(0)):
                    replacement = root_tag.group(0).replace("<" + root_tag.group(1),
                                                               "<" + root_tag.group(1) + f' id="{section_id}"', 1)
                    content = content[:root_tag.start()] + replacement + content[root_tag.end():]
        normalized.append((path, content))
    return normalized


def remove_unresolved_section_links(files: dict[str, str]) -> dict[str, str]:
    """Render links to absent in-page targets as text, preserving their content."""
    source_files = {path: source for path, source in files.items() if path.endswith((".tsx", ".jsx", ".html"))}
    ids = {"site-main"}
    for source in source_files.values():
        ids.update(re.findall(r'\bid\s*=\s*["\']([A-Za-z][\w-]*)["\']', source))

    changed: dict[str, str] = {}
    anchor_pattern = re.compile(
        r'<a\b(?P<attrs>[^>]*\bhref\s*=\s*["\']#(?P<target>[A-Za-z][\w-]*)["\'][^>]*)>'
        r'(?P<body>.*?)</a>', re.S | re.I,
    )
    for path, source in source_files.items():
        if not path.endswith((".tsx", ".jsx")):
            continue

        def strip_dead_link(match: re.Match[str]) -> str:
            attrs = match.group("attrs")
            if match.group("target") in ids or re.search(r'\bonClick\s*=', attrs):
                return match.group(0)
            # A home/top link may use the familiar route name even when the
            # declared landing section is hero. Preserve its navigation intent.
            if (match.group("target") == "home" and "hero" in ids
                    and re.fullmatch(r'\s*(?:Home|Back to home)\s*', match.group("body"), re.I)):
                return re.sub(r'(\bhref\s*=\s*["\'])#home(["\'])',
                              r'\1#hero\2', match.group(0), count=1)
            attrs = re.sub(r'\s*href\s*=\s*["\']#[A-Za-z][\w-]*["\']', '', attrs, count=1)
            return f'<span{attrs}>{match.group("body")}</span>'

        repaired = anchor_pattern.sub(strip_dead_link, source)
        if repaired != source:
            changed[path] = repaired
    return changed
