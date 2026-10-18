"""Native section authoring: the model writes each section's TSX and CSS itself.

The design kit plans the site (sections, kinds, theme, photos) and the model has
already written each section's copy as JSON (kit content step). In native mode the
model then writes the section *code* too, against the site's design system
(src/App.css tokens and layout classes). The prompt built here is shared by the
training-data builder and the live generator, so training and inference match.

If the model's files are unusable (missing, wrong paths, broken syntax), callers
fall back to the kit renderer for that section and report it as a fallback.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parents[2]

NATIVE_SYSTEM_PROMPT = """You are SiteAgent, a front-end engineer who writes production website sections.
Write ONE section as a React 19 + TypeScript component and its CSS file.

The site has a shared design system in src/App.css. Use it instead of hard-coded values:
- Tokens: --k-bg, --k-surface, --k-surface-2, --k-ink, --k-muted, --k-line, --k-line-strong, --k-accent,
  --k-accent-hover, --k-accent-ink, --k-accent-soft, --k-accent-text, --k-font-display, --k-font-body,
  --k-radius, --k-radius-btn, --k-space-1 ... --k-space-12, --k-density, --k-gutter, --k-max, --k-ease, --k-ease-out.
- Layout and type classes: k-section, k-section--tint, k-container, k-head, k-head--split, k-h2, k-h3,
  k-display, k-lede, k-muted, k-text, k-link, k-actions, k-btn, k-btn--primary, k-btn--ghost, k-media,
  k-art, k-stagger, k-tilt.
- Scroll reveal: elements with data-motion="scroll-reveal" become visible when the useReveal hook adds is-visible.

Rules:
- Put all copy in a `const DATA: any = {...}` object, copied exactly from the content JSON you are given.
  Do not invent facts, prices, people, links or claims.
- Export the component by name and as the default export. Import only from 'react', 'react-dom' and the section's own CSS file.
- Semantic, accessible markup: one <section id="..."> (or <header>/<footer> for site chrome) with aria-labelledby,
  real buttons and links, alt text, visible focus states, keyboard support for interactive widgets.
- Scope every CSS rule under the section's own class (e.g. `.k-faq ...`). Respect prefers-reduced-motion.
- Output exactly two blocks and nothing else:
<file path="src/components/Name.tsx">...</file>
<file path="src/components/Name.css">...</file>"""

_FILE_RE = re.compile(r'<file\s+path="([^"]+)"\s*>\n?(.*?)\n?</file>', re.S)


def native_spec(site: Any, slug: str) -> dict:
    """The design decisions the kit renderer would use for this section."""
    kind = site.kinds[slug]
    theme = site.theme
    return {
        "component": site.component(slug),
        "id": slug,
        "kind": kind,
        "position": site.section_index(slug) + 1,
        "sections": len(site.sections),
        "tinted_background": bool(site.tints.get(slug)),
        "scroll_reveal": slug == site.reveal_section,
        "theme_mode": theme.mode,
        "lively_motion": bool(getattr(theme, "lively", False)),
        "section_rules": bool(getattr(theme, "rule", False)),
        "store": bool(site.is_store),
    }


def native_messages(site: Any, slug: str, content: Optional[dict] = None) -> list[dict]:
    """Chat messages asking the model to write `slug`'s TSX and CSS."""
    spec = native_spec(site, slug)
    content = site.final_content(slug) if content is None else content
    name = spec["component"]
    lines = [
        f"Site: {site.brand} — {site.business_label()}" + (f", {site.location}" if site.location else "") + ".",
        f"Section: {name} (id \"{slug}\", kind \"{spec['kind']}\"), section {spec['position']} of {spec['sections']}.",
        "Design: " + ", ".join([
            f"theme {spec['theme_mode']}",
            "tinted background" if spec["tinted_background"] else "plain background",
            "scroll reveal on" if spec["scroll_reveal"] else "scroll reveal off",
            "lively motion" if spec["lively_motion"] else "calm motion",
            "rules between sections" if spec["section_rules"] else "no section rules",
            "store with cart" if spec["store"] else "no store",
        ]) + ".",
        "Content JSON:",
        json.dumps(content, ensure_ascii=False, indent=2),
        f"Files: src/components/{name}.tsx and src/components/{name}.css",
    ]
    return [{"role": "system", "content": NATIVE_SYSTEM_PROMPT}, {"role": "user", "content": "\n".join(lines)}]


def native_target(files: list[tuple[str, str]]) -> str:
    """The assistant reply for a section's files, in the protocol parse_native_files reads."""
    return "\n".join(f'<file path="{path}">\n{source.rstrip()}\n</file>' for path, source in files)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


_DATA_RE = re.compile(r"const DATA(?:\s*:\s*[\w<>\[\], ]+)?\s*=\s*(\{.*?\})(?:\s+as\s+const)?;\s*\n", re.S)


def _js_object_to_json(source: str) -> str:
    """Rewrite a plain JS object literal (bare keys, single quotes, trailing commas)
    as JSON, so copy written in either syntax is compared on its text, not its quoting."""
    out, i, n = [], 0, len(source)
    while i < n:
        ch = source[i]
        if ch in "\"'`":
            quote, j, buf = ch, i + 1, []
            while j < n and source[j] != quote:
                if source[j] == "\\" and j + 1 < n:
                    buf.append(source[j:j + 2])
                    j += 2
                    continue
                buf.append(source[j])
                j += 1
            text = "".join(buf)
            if quote != '"':
                text = text.replace("\\'", "'").replace("\\`", "`").replace('"', '\\"')
            out.append('"' + text + '"')
            i = j + 1
            continue
        key = re.match(r"([A-Za-z_$][\w$]*)\s*:", source[i:])
        if key and (not out or out[-1].rstrip()[-1:] in "{,"):
            out.append(f'"{key.group(1)}":')
            i += key.end()
            continue
        if ch == "," and re.match(r",\s*[}\]]", source[i:]):
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def missing_copy(tsx: str, content: dict) -> list[str]:
    """Approved copy the component changed, dropped or added to (empty when faithful).

    The model may arrange the markup however it likes, but its DATA object must hold
    exactly the approved content: no rewritten, missing or invented copy. JSON or a
    plain JS object literal are both accepted."""
    match = _DATA_RE.search(tsx or "")
    if not match:
        return ["no `const DATA = {...};` object"]
    try:
        data = json.loads(match.group(1))
    except ValueError:
        try:
            data = json.loads(_js_object_to_json(match.group(1)))
        except ValueError:
            return ["DATA is not a plain object literal"]
    if data == content:
        return []
    expected, written = set(_strings(content)), set(_strings(data))
    differences = sorted(expected - written) + [f"(added) {t}" for t in sorted(written - expected)]
    return differences or ["DATA structure differs from the approved content"]


_MARKERS = (
    r'data-motion="[^"]+"', r'\bid="[^"{]+"', r'\baria-[a-z]+=', r'\brole="[^"]+"',
    r'\bsrc=\{', r'\bhref=\{', r'\bonClick=\{', r'\bonKeyDown=\{', r'\bonSubmit=\{', r'\btabIndex=\{',
)


def structural_gaps(tsx: str, reference_tsx: str) -> list[str]:
    """Behaviour the reference (kit) rendering has that the model's component lacks:
    reveal markers, ids, ARIA attributes, roles, image sources, links and handlers.
    Markup may differ freely; these behaviours may not go missing."""
    gaps = []
    for pattern in _MARKERS:
        wanted = {m: n for m, n in __import__("collections").Counter(re.findall(pattern, reference_tsx)).items()}
        have = __import__("collections").Counter(re.findall(pattern, tsx))
        gaps += [marker for marker, count in wanted.items() if have.get(marker, 0) < min(count, 1)]
    return sorted(set(gaps))


def parse_native_files(text: str, component: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Extract the section's TSX and CSS from a model reply; report anything unusable."""
    found = {path.strip(): source for path, source in _FILE_RE.findall(text or "")}
    tsx_path = f"src/components/{component}.tsx"
    css_path = f"src/components/{component}.css"
    problems = []
    tsx, css = found.get(tsx_path, ""), found.get(css_path, "")
    if not tsx.strip():
        problems.append(f"missing {tsx_path}")
    if not css.strip():
        problems.append(f"missing {css_path}")
    if tsx and not re.search(rf"export\s+(?:default\s+)?function\s+{re.escape(component)}\b|export\s+default\s+{re.escape(component)}\b", tsx):
        problems.append(f"{tsx_path} does not export {component}")
    if tsx and re.search(r"""from\s+['"](?!react['"]|react-dom['"]|\./)""", tsx):
        problems.append(f"{tsx_path} imports a package other than react/react-dom")
    if tsx:
        repeated = sorted(i for i, n in __import__("collections").Counter(re.findall(r'\bid="([^"{]+)"', tsx)).items() if n > 1)
        if repeated:
            problems.append(f"{tsx_path} repeats element id(s) {', '.join(repeated)} (WCAG 4.1.1)")
    extra = sorted(set(found) - {tsx_path, css_path})
    if extra:
        problems.append("unexpected files: " + ", ".join(extra))
    if problems:
        return [], problems
    return [(tsx_path, tsx.rstrip() + "\n"), (css_path, css.strip() + "\n")], []


def typecheck_sections(files: dict[str, list[tuple[str, str]]]) -> dict[str, list[str]]:
    """Typecheck each sample's TSX in one tsc run; returns errors per sample id."""
    work = Path(tempfile.mkdtemp(prefix="native_tsc_"))
    try:
        (work / "src").mkdir()
        (work / "src" / "globals.d.ts").write_text("declare module '*.css';\n", encoding="utf-8")
        owner = {}
        for sample_id, pairs in files.items():
            folder = work / "src" / sample_id
            folder.mkdir(parents=True)
            for path, source in pairs:
                target = folder / Path(path).name
                target.write_text(source, encoding="utf-8")
                if target.suffix == ".tsx":
                    owner[target.relative_to(work).as_posix()] = sample_id
        tsconfig = {"compilerOptions": {"jsx": "react-jsx", "module": "ESNext", "moduleResolution": "bundler",
                                        "target": "ES2020", "lib": ["ES2020", "DOM", "DOM.Iterable"], "strict": False,
                                        "skipLibCheck": True, "noEmit": True, "allowSyntheticDefaultImports": True,
                                        "typeRoots": [str(BASE_DIR / "node_modules" / "@types")],
                                        "baseUrl": ".", "paths": {"react": [str(BASE_DIR / "node_modules/@types/react")],
                                                                  "react-dom": [str(BASE_DIR / "node_modules/@types/react-dom")],
                                                                  "react/*": [str(BASE_DIR / "node_modules/@types/react/*")],
                                                                  "react-dom/*": [str(BASE_DIR / "node_modules/@types/react-dom/*")]}},
                    "include": ["src"]}
        (work / "tsconfig.json").write_text(json.dumps(tsconfig), encoding="utf-8")
        run = subprocess.run(["node", str(BASE_DIR / "node_modules/typescript/bin/tsc"), "-p", "."], cwd=work,
                             capture_output=True, text=True, timeout=300)
        errors: dict[str, list[str]] = defaultdict(list)
        for line in (run.stdout + run.stderr).splitlines():
            m = re.match(r"(src/[^(]+)\(\d+,\d+\): error (TS\d+: .*)", line.replace("\\", "/"))
            if m and m.group(1) in owner:
                errors[owner[m.group(1)]].append(m.group(2)[:200])
        return errors
    finally:
        shutil.rmtree(work, ignore_errors=True)
