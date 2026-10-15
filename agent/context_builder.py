"""
agent/context_builder.py - Prioritized Context Selection & Token Budget Engine

Implements the blueprint's 8-tier context priority hierarchy:
1. Selected element (preview inspection / 3D selection)
2. Explicitly mentioned files (@mentions)
3. Semantic code search (symbol export, JSX tags, classNames, IDs)
4. Recently changed files (last checkpoint / turn)
5. Dependency-related files (imports, companion CSS, parent modules)
6. Project metadata (dependencies, component outline, design tokens)
7. Build/runtime diagnostics (TypeScript errors, lint warnings, console errors)
8. Recent conversation (turn summaries)

Enforces strict token budgeting with dynamic surplus reallocation so that
unused diagnostic or history tokens expand code context without exceeding
the model's context window. Never dumps the entire repository.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ── Token Budget Model ────────────────────────────────────────────────────────

@dataclasses.dataclass
class TokenBudget:
    """Configurable token slices for context construction."""
    total: Optional[int] = None
    system_contracts: Optional[int] = None
    current_instruction: Optional[int] = None
    project_metadata: Optional[int] = None
    selected_files: Optional[int] = None
    related_files: Optional[int] = None
    recent_conversation: Optional[int] = None
    build_diagnostics: Optional[int] = None
    reserve: Optional[int] = None

    def __post_init__(self):
        from agent.config import ModelRuntimeConfig
        if self.total is None:
            self.total = ModelRuntimeConfig.get_max_seq_length()
        scale = self.total / 8192.0
        if self.system_contracts is None:
            self.system_contracts = int(round(1000 * scale))
        if self.current_instruction is None:
            self.current_instruction = int(round(300 * scale))
        if self.project_metadata is None:
            self.project_metadata = int(round(300 * scale))
        if self.selected_files is None:
            self.selected_files = int(round(3000 * scale))
        if self.related_files is None:
            self.related_files = int(round(1600 * scale))
        if self.recent_conversation is None:
            self.recent_conversation = int(round(900 * scale))
        if self.build_diagnostics is None:
            self.build_diagnostics = int(round(700 * scale))
        if self.reserve is None:
            self.reserve = self.total - (
                self.system_contracts
                + self.current_instruction
                + self.project_metadata
                + self.selected_files
                + self.related_files
                + self.recent_conversation
                + self.build_diagnostics
            )

    @property
    def max_context_input(self) -> int:
        """Total allowed tokens for the user prompt and context, excluding system contracts and reserve."""
        return (self.total or 8192) - (self.system_contracts or 1000) - (self.reserve or 392)


@dataclasses.dataclass
class TokenUsage:
    """Actual tokens allocated to each context slice."""
    system_contracts: int = 0
    current_instruction: int = 0
    project_metadata: int = 0
    selected_files: int = 0
    related_files: int = 0
    recent_conversation: int = 0
    build_diagnostics: int = 0
    reserve: int = 0
    total: int = 0

    def to_dict(self) -> Dict[str, int]:
        return dataclasses.asdict(self)

    def summary(self) -> str:
        return (
            f"system={self.system_contracts}, "
            f"instruction={self.current_instruction}, "
            f"metadata={self.project_metadata}, "
            f"selected={self.selected_files}, "
            f"related={self.related_files}, "
            f"history={self.recent_conversation}, "
            f"diagnostics={self.build_diagnostics}, "
            f"reserve={self.reserve} (total={self.total})"
        )


@dataclasses.dataclass
class BuiltContext:
    """Result of context assembly."""
    prompt_text: str
    selected_files: List[Tuple[str, str]]
    related_files: List[Tuple[str, str]]
    diagnostics_text: str
    metadata_text: str
    history_text: str
    token_usage: TokenUsage
    budget: TokenBudget
    motion_text: str = ""



# ── Fast Token Estimator ──────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """
    Estimates token count with character and word heuristics calibrated
    for mixed TypeScript/JSX/CSS code and natural language instructions.
    Average ratio for code/markdown is ~3.8 characters per token.
    """
    if not text:
        return 0
    # Blend character count and whitespace word count
    char_estimate = len(text) / 3.8
    words = len(text.split())
    word_estimate = words * 1.3
    # Use average with safe ceiling
    estimated = int(math.ceil((char_estimate * 0.7) + (word_estimate * 0.3)))
    return max(1, estimated)


# ── Stop Words for Code Search ────────────────────────────────────────────────

_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "its", "itself", "let", "make", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", "some",
    "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "with", "would", "you", "your", "yours",
    "update", "change", "modify", "edit", "please", "code", "file", "component"
}


def extract_search_terms(query: str) -> List[str]:
    """Extracts distinctive identifier tokens, camelCase parts, and keywords from query."""
    raw_tokens = re.findall(r'[A-Za-z0-9_-]+', query)
    terms: Set[str] = set()

    for token in raw_tokens:
        clean = token.lower().strip("-_")
        if not clean or clean in _STOP_WORDS or len(clean) < 2:
            continue
        terms.add(clean)

        # Split camelCase (e.g. HeroSection -> hero, section)
        camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', token)
        if len(camel_parts) > 1:
            for cp in camel_parts:
                cp_clean = cp.lower()
                if cp_clean and cp_clean not in _STOP_WORDS and len(cp_clean) >= 3:
                    terms.add(cp_clean)

    return sorted(terms)


# ── Semantic Code Search ──────────────────────────────────────────────────────

def search_codebase(
    query: str,
    files: Dict[str, str],
) -> List[Tuple[str, float]]:
    """
    Ranks files based on semantic code match to query terms.
    Scoring weights:
    - Filename or stem exact match: +10.0
    - Component export (`export function ...`, `export const ...`): +8.0
    - JSX tag definition or usage (`<Hero`, `<Pricing`): +6.0
    - Class name or ID attribute match: +4.0
    - Term frequency occurrences in content: +1.0 per term (capped at +5.0)
    """
    terms = extract_search_terms(query)
    if not terms or not files:
        return []

    scores: List[Tuple[str, float]] = []

    for path, content in files.items():
        # Ignore external/generated files
        if any(ignore in path.lower() for ignore in ["node_modules", "dist", "preview.js"]):
            continue

        score = 0.0
        path_lower = path.lower()
        stem_lower = Path(path).stem.lower()
        content_lower = content.lower()

        for term in terms:
            # 1. Filename / stem match
            if term == stem_lower:
                score += 12.0
            elif term in stem_lower:
                score += 8.0
            elif term in path_lower:
                score += 5.0

            # 2. Exported component match
            if re.search(rf'export\s+(?:default\s+)?(?:function|const|class)\s+{re.escape(term)}\b', content, re.I):
                score += 9.0

            # 3. JSX tag match
            if re.search(rf'<{re.escape(term)}\b', content, re.I):
                score += 6.0

            # 4. Class name or CSS selector match
            if re.search(rf'class(?:Name)?=[\'"][^\'"]*\b{re.escape(term)}\b', content, re.I):
                score += 4.5
            elif path.endswith(".css") and re.search(rf'\.{re.escape(term)}\b', content, re.I):
                score += 4.5

            # 5. Term frequency in content
            count = content_lower.count(term)
            if count > 0:
                score += min(5.0, count * 0.8)

        if score > 0.0:
            scores.append((path, round(score, 2)))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


# ── Dependency Extractor ──────────────────────────────────────────────────────

def extract_dependencies(
    file_path: str,
    content: str,
    all_files: Dict[str, str],
) -> List[str]:
    """
    Extracts related files imported by or companion to `file_path`:
    1. Companion CSS / SCSS / module styles (`Hero.module.css`, `Hero.css`)
    2. Relative imports (`./components/Header`, `../Navbar`)
    3. Parent module that imports this file (e.g. `App.tsx` importing `file_path`)
    """
    related: List[str] = []
    parent_dir = Path(file_path).parent
    stem = Path(file_path).stem

    # 1. Companion CSS files
    for candidate in [f"{stem}.module.css", f"{stem}.css", f"{parent_dir}/{stem}.module.css", f"{parent_dir}/{stem}.css"]:
        clean_candidate = candidate.replace("\\", "/").lstrip("./")
        for f in all_files.keys():
            if f.lower() == clean_candidate.lower() or Path(f).name.lower() in (f"{stem}.module.css".lower(), f"{stem}.css".lower()):
                if f not in related and f != file_path:
                    related.append(f)

    # 2. Relative imports inside content
    import_matches = re.findall(r'(?:import|from)\s+[\'"](\.[^\'"]+)[\'"]', content)
    for imp in import_matches:
        # Normalize relative path
        resolved = (parent_dir / imp).resolve()
        # Find matching file in workspace with extensions
        for ext in ["", ".tsx", ".ts", ".jsx", ".js", ".css", ".module.css"]:
            for f in all_files.keys():
                candidate_p = Path(f)
                if imp.endswith(ext) and candidate_p.name.lower() == Path(imp).name.lower():
                    if f not in related and f != file_path:
                        related.append(f)
                elif candidate_p.stem.lower() == Path(imp).stem.lower():
                    if f not in related and f != file_path:
                        related.append(f)

    # 3. Parent importer: check if App.tsx or main.tsx imports this component
    for top_file in ["App.tsx", "src/App.tsx", "main.tsx", "src/main.tsx"]:
        if top_file in all_files and top_file != file_path and top_file not in related:
            top_content = all_files[top_file]
            if re.search(rf'\b{re.escape(stem)}\b', top_content):
                related.append(top_file)

    return related


# ── Bounded File Excerpter ────────────────────────────────────────────────────

def bounded_excerpt(
    path: str,
    content: str,
    max_tokens: int,
    focus_terms: Optional[List[str]] = None,
    is_primary: bool = True,
) -> str:
    """
    Intelligently bounds file content to fit max_tokens:
    - Fits within budget: returns full content unchanged.
    - If `not is_primary` (related file): extracts interfaces, exported component declarations,
      props, and signatures, collapsing implementation bodies to save tokens.
    - If `is_primary` (selected target file): extracts imports, surrounding context of
      matching focus terms/symbols, and bounded window with clear ellipsis markers.
    """
    token_est = estimate_tokens(content)
    if token_est <= max_tokens:
        return content

    lines = content.splitlines()
    if not lines:
        return ""

    if not is_primary:
        # Related file skeletonizer: keep imports, types, interfaces, exported signatures
        skeleton_lines: List[str] = []
        in_interface_or_type = False
        in_export_func = False

        for line in lines:
            stripped = line.strip()
            # Preserve imports
            if stripped.startswith("import ") or stripped.startswith("from "):
                skeleton_lines.append(line)
                continue

            # Preserve types and interfaces
            if re.match(r'^(?:export\s+)?(?:interface|type)\s+', stripped):
                in_interface_or_type = True
                skeleton_lines.append(line)
                continue

            if in_interface_or_type:
                skeleton_lines.append(line)
                if stripped.startswith("}"):
                    in_interface_or_type = False
                continue

            # If inside component/function body, skip lines until top-level closing brace
            if in_export_func:
                if stripped.startswith("}") and (line.startswith("}") or line.startswith("};")):
                    skeleton_lines.append(line.rstrip())
                    in_export_func = False
                continue

            # Preserve top-level component/function export signatures
            if re.match(r'^(?:export\s+)?(?:default\s+)?(?:function|const)\s+([A-Za-z0-9_]+)', stripped):
                skeleton_lines.append(line)
                skeleton_lines.append("  // [... component JSX & implementation omitted for token budget ...]")
                in_export_func = True
                continue

        skeleton_text = "\n".join(skeleton_lines)
        if estimate_tokens(skeleton_text) <= max_tokens:
            return skeleton_text


    # Window-based extraction with priority on focus terms
    target_line_indices: Set[int] = set()
    if focus_terms:
        for idx, line in enumerate(lines):
            line_low = line.lower()
            if any(term in line_low for term in focus_terms):
                for context_offset in range(-5, 6):
                    c_idx = idx + context_offset
                    if 0 <= c_idx < len(lines):
                        target_line_indices.add(c_idx)

    # Always keep top imports (first 25 lines)
    top_n = min(25, len(lines))
    for i in range(top_n):
        target_line_indices.add(i)

    # Always keep bottom return/export lines (last 10 lines)
    for i in range(max(0, len(lines) - 10), len(lines)):
        target_line_indices.add(i)

    sorted_indices = sorted(target_line_indices)
    excerpt_lines: List[str] = []
    last_idx = -1

    for idx in sorted_indices:
        if last_idx != -1 and idx > last_idx + 1:
            omitted = idx - last_idx - 1
            excerpt_lines.append(f"    // ... [{omitted} lines omitted for token budget] ...")
        excerpt_lines.append(lines[idx])
        last_idx = idx

        # Check token budget during accumulation
        if estimate_tokens("\n".join(excerpt_lines)) >= (max_tokens - 40):
            excerpt_lines.append("    // ... [remaining content truncated for token budget] ...")
            break

    return "\n".join(excerpt_lines)


# ── ContextBuilder Class ──────────────────────────────────────────────────────

class ContextBuilder:
    """
    Dedicated ContextBuilder that assembles generation and edit turn prompts
    under a strict token budget with prioritized context selection.
    """

    def __init__(self, budget: Optional[TokenBudget] = None):
        self._custom_budget = budget

    @property
    def budget(self) -> TokenBudget:
        if self._custom_budget is not None:
            return self._custom_budget
        from agent.config import ModelRuntimeConfig
        return ModelRuntimeConfig.get_token_budget()

    @budget.setter
    def budget(self, value: Optional[TokenBudget]) -> None:
        self._custom_budget = value

    def resolve_context_files(
        self,
        all_files: Dict[str, str],
        instruction: str,
        preview_selection: Optional[Dict[str, Any]] = None,
        recent_files: Optional[List[str]] = None,
        session_title: str = "New Session",
    ) -> Dict[str, Any]:
        """
        Resolves candidate files according to priorities:
        Priority 1: Selected element (preview inspection / 3D node)
        Priority 2: Explicit @mentions
        Priority 3: Semantic code search
        Priority 4: Recently changed files
        Priority 5: Dependency-related files
        """
        if not all_files:
            return {
                "selected": [],
                "related": [],
                "priority_notes": ["No workspace files present."],
            }

        selected_paths: Set[str] = set()
        priority_notes: List[str] = []

        # ── Priority 1: Selected Element ─────────────────────────────────────
        if preview_selection:
            comp_name = preview_selection.get("component")
            selector = preview_selection.get("selector")
            tag = preview_selection.get("tag")
            three_node = preview_selection.get("three_node")

            target_hint = comp_name or selector or three_node
            if target_hint:
                clean_hint = re.sub(r'^[.#]', '', str(target_hint)).lower()
                for path in all_files.keys():
                    stem = Path(path).stem.lower()
                    if clean_hint in stem or stem in clean_hint:
                        selected_paths.add(path)
                        priority_notes.append(f"Priority 1: Selected element '{target_hint}' matched '{path}'")

        # ── Priority 2: Explicit @mentions ───────────────────────────────────
        mentions = re.findall(r'@([A-Za-z0-9_.-]+)', instruction)
        for m in mentions:
            m_clean = m.lower()
            for path in all_files.keys():
                path_lower = path.lower()
                stem = Path(path).stem.lower()
                name = Path(path).name.lower()
                if m_clean in (path_lower, stem, name) or stem == m_clean:
                    selected_paths.add(path)
                    priority_notes.append(f"Priority 2: Mention '@{m}' matched '{path}'")

        # ── Targeted Image Swap / Animation Intent Heuristic ─────────────────
        inst_low = instruction.lower()
        if not selected_paths and any(k in inst_low for k in ["image", "photo", "picture", "pic"]):
            if any(k in inst_low for k in ["hero", "banner", "warmer", "warm"]):
                for path, content in all_files.items():
                    if "hero.css" in path.lower() or "hero.tsx" in path.lower():
                        selected_paths.add(path)
                        priority_notes.append(f"Priority 2b: Hero image swap intent matched '{path}'")
                        break

            if not selected_paths and any(k in inst_low for k in ["product", "item", "card", "listing", "dish", "second", "2nd"]):
                for path in all_files.keys():
                    stem = Path(path).stem.lower()
                    if stem in ("features", "products", "menu", "listings", "catalog", "shop") and path.endswith(".tsx"):
                        selected_paths.add(path)
                        priority_notes.append(f"Priority 2b: Product image swap intent matched '{path}'")
                        break

        # ── Priority 3: Semantic Code Search ─────────────────────────────────
        if len(selected_paths) < 2:
            search_matches = search_codebase(instruction, all_files)
            for path, score in search_matches:
                if path not in selected_paths and score >= 5.0:
                    selected_paths.add(path)
                    priority_notes.append(f"Priority 3: Semantic search matched '{path}' (score: {score})")
                    if len(selected_paths) >= 3:
                        break

        # ── Priority 4: Recently Changed Files ───────────────────────────────
        if recent_files and len(selected_paths) < 2:
            for rf in recent_files:
                clean_rf = rf.replace("\\", "/").lstrip("./")
                for path in all_files.keys():
                    if path.lower() == clean_rf.lower() or Path(path).name.lower() == Path(rf).name.lower():
                        if path not in selected_paths:
                            selected_paths.add(path)
                            priority_notes.append(f"Priority 4: Recently changed file matched '{path}'")
                            break

        # ── Fallback if still empty ──────────────────────────────────────────
        if not selected_paths:
            comp_files = [p for p in all_files.keys() if "components" in p.lower() and p.endswith(".tsx")]
            if comp_files:
                selected_paths.add(comp_files[0])
                priority_notes.append(f"Fallback: Primary component '{comp_files[0]}'")
            elif f"{session_title}.tsx" in all_files:
                selected_paths.add(f"{session_title}.tsx")
                priority_notes.append(f"Fallback: Title component '{session_title}.tsx'")
            elif "Component.tsx" in all_files:
                selected_paths.add("Component.tsx")
                priority_notes.append("Fallback: 'Component.tsx'")
            elif "App.tsx" in all_files:
                selected_paths.add("App.tsx")
                priority_notes.append("Fallback: 'App.tsx'")
            else:
                code_candidates = [
                    p for p in all_files.keys()
                    if p.endswith((".tsx", ".ts", ".css"))
                    and not any(k in p for k in ("node_modules", "vite.config", "preview.js"))
                ]
                if code_candidates:
                    selected_paths.add(code_candidates[0])
                    priority_notes.append(f"Fallback: Code file '{code_candidates[0]}'")

        # ── Priority 5: Dependency-Related Files ─────────────────────────────
        related_paths: Set[str] = set()
        for sel_path in list(selected_paths):
            content = all_files.get(sel_path, "")
            deps = extract_dependencies(sel_path, content, all_files)
            for d in deps:
                if d not in selected_paths:
                    related_paths.add(d)
                    priority_notes.append(f"Priority 5: Dependency '{d}' related to '{sel_path}'")

        # Exclude selected from related
        related_paths.difference_update(selected_paths)

        return {
            "selected": [(p, all_files[p]) for p in sorted(selected_paths) if p in all_files],
            "related": [(p, all_files[p]) for p in sorted(related_paths) if p in all_files],
            "priority_notes": priority_notes,
        }

    def format_project_metadata(
        self,
        session: Any,
        all_files: Dict[str, str],
        max_tokens: int,
    ) -> str:
        """Formats compact project metadata without dumping full file content."""
        lines = ["<project_metadata>"]
        lines.append(f"Title: {getattr(session, 'title', 'Site Project')}")
        lines.append(f"Mode: {getattr(session, 'mode', 'site')}")
        lines.append("Framework: React + TypeScript + Vite")

        # Parse package.json dependencies if present
        deps: List[str] = []
        pkg_content = all_files.get("package.json")
        if pkg_content:
            try:
                pkg_data = json.loads(pkg_content)
                deps = list(pkg_data.get("dependencies", {}).keys())
                dev_deps = list(pkg_data.get("devDependencies", {}).keys())
                if deps:
                    lines.append(f"Installed Dependencies: {', '.join(deps)}")
                if dev_deps:
                    lines.append(f"Dev Dependencies: {', '.join(dev_deps)}")
            except Exception:
                pass

        # Workspace structure summary (file names only)
        code_files = [
            p for p in sorted(all_files.keys())
            if not any(k in p for k in ("node_modules", "package-lock.json", "preview.js"))
        ]
        if code_files:
            lines.append(f"Workspace Files ({len(code_files)}): {', '.join(code_files[:15])}")
            if len(code_files) > 15:
                lines.append(f"... and {len(code_files) - 15} more files")

        # Design tokens
        tokens = getattr(session, "style_tokens", None)
        if tokens:
            lines.append(f"Design Tokens: {tokens[:250]}...")

        # 3D Project Capability Metadata (Issue #28)
        uses_3d = getattr(session, "uses_3d", False) or getattr(session, "uses3D", False)
        three_lib = getattr(session, "three_library", None) or getattr(session, "threeLibrary", None)
        if not uses_3d:
            if "@react-three/fiber" in deps or "three" in deps:
                uses_3d = True
            elif any("@react-three" in content or "from 'three'" in content or 'from "three"' in content for content in all_files.values()):
                uses_3d = True

        if uses_3d:
            three_lib = three_lib or "@react-three/fiber"
            lines.append("3D Metadata:")
            lines.append(json.dumps({
                "uses3D": True,
                "threeLibrary": three_lib,
            }, indent=2))

        lines.append("</project_metadata>")
        text = "\n".join(lines)
        return bounded_excerpt("metadata", text, max_tokens, is_primary=True)

    def format_diagnostics(
        self,
        build_state: Optional[Dict[str, Any]],
        max_tokens: int,
    ) -> str:
        """Formats compiler errors, lint warnings, and runtime issues within budget."""
        if not build_state:
            return ""

        errors = build_state.get("errors") or []
        warnings = build_state.get("warnings") or []
        runtime_errors = build_state.get("runtime_errors") or []

        if not errors and not warnings and not runtime_errors:
            return ""

        lines = ["<diagnostics>"]
        lines.append("RECENT COMPILER & RUNTIME VALIDATION FEEDBACK:")

        if errors:
            lines.append(f"TypeScript / Build Errors ({len(errors)}):")
            for err in errors[:5]:
                lines.append(f"  • {err}")

        if runtime_errors:
            lines.append(f"Browser Runtime Errors ({len(runtime_errors)}):")
            for r_err in runtime_errors[:3]:
                lines.append(f"  • {r_err}")

        if warnings:
            lines.append(f"Lint / Style Warnings ({len(warnings)}):")
            for warn in warnings[:3]:
                lines.append(f"  • {warn}")

        lines.append("Fix these compiler/runtime diagnostics in your updated code.")
        lines.append("</diagnostics>")

        text = "\n".join(lines)
        return bounded_excerpt("diagnostics", text, max_tokens, is_primary=True)

    def format_recent_conversation(
        self,
        history: Optional[List[Dict[str, Any]]],
        max_tokens: int,
    ) -> str:
        """Formats compact history log from newest to oldest within token slice."""
        if not history:
            return ""

        lines = ["<recent_conversation>"]
        lines.append("PRIOR TURNS IN THIS SESSION:")

        accumulated_lines: List[str] = []
        for h in reversed(history[-6:]):  # inspect up to last 6 turns
            role = str(h.get("role", "turn")).capitalize()
            summary = h.get("summary") or h.get("content", "")[:120]
            summary_clean = summary.replace("\n", " ").strip()
            item_line = f"- [{role}]: {summary_clean}"

            test_text = "\n".join(lines + [item_line] + accumulated_lines + ["</recent_conversation>"])
            if estimate_tokens(test_text) > max_tokens:
                break
            accumulated_lines.insert(0, item_line)

        if not accumulated_lines:
            return ""

        lines.extend(accumulated_lines)
        lines.append("</recent_conversation>")
        return "\n".join(lines)

    def build_context(
        self,
        session: Any,
        new_instruction: str,
        target_files: Optional[List[Tuple[str, str]]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        preview_selection: Optional[Dict[str, Any]] = None,
        current_section_motion: Optional[List[Any]] = None,
    ) -> BuiltContext:
        """
        Builds the complete generation context respecting priorities and token budget:
        - Allocates fixed slices
        - Calculates surplus from unused fixed allocations
        - Distributes surplus to code slices (selected + related files)
        - Formats excerpts and never sends the whole repository
        - Gives current-section motion requirements top priority so compaction never drops them
        """
        budget = self.budget
        all_files = session.get_current_files() if hasattr(session, "get_current_files") else {}

        # Merge preview_selection from session if not passed directly
        if not preview_selection and hasattr(session, "preview_selection"):
            preview_selection = session.preview_selection

        # Resolve recent files from session history/checkpoints
        recent_files: List[str] = []
        if hasattr(session, "checkpoints") and session.checkpoints:
            recent_files = session.checkpoints[-1].get("files_touched") or []
        elif hasattr(session, "history") and session.history:
            recent_files = session.history[-1].get("files_touched") or []

        # 1. Resolve selected vs related files if target_files not explicitly provided
        if target_files is None:
            resolved_info = self.resolve_context_files(
                all_files=all_files,
                instruction=new_instruction,
                preview_selection=preview_selection,
                recent_files=recent_files,
                session_title=getattr(session, "title", "Site"),
            )
            selected_files = resolved_info["selected"]
            related_files = resolved_info["related"]
        else:
            selected_files = list(target_files)
            # Find related files for the provided targets
            rel_set: Set[str] = set()
            sel_paths = {p for p, _ in selected_files}
            for sel_path, content in selected_files:
                for dep in extract_dependencies(sel_path, content, all_files):
                    if dep not in sel_paths:
                        rel_set.add(dep)
            related_files = [(p, all_files[p]) for p in sorted(rel_set) if p in all_files]

        # 2. Format fixed slices
        # User Instruction
        instruction_text = (
            f"<instruction>\n"
            f"USER INSTRUCTION FOR THIS EDIT:\n{new_instruction}\n\n"
            f"Modify the target files to satisfy the instruction. "
            f"Emit complete updated file contents using <tool_call name=\"write_site\">\n"
            f"<file path=\"...\">\n...content...\n</file>\n</tool_call>.\n"
            f"</instruction>"
        )
        used_instruction = estimate_tokens(instruction_text)

        # Current Section Motion Requirements (Top Priority - Never dropped)
        motion_text = ""
        resolved_motion: List[Any] = []
        if current_section_motion:
            resolved_motion = list(current_section_motion)
        else:
            try:
                from agent.motion_patterns import extract_motion_requirements
                resolved_motion = extract_motion_requirements(new_instruction)
            except Exception:
                pass

        if resolved_motion:
            try:
                from agent.motion_patterns import get_motion_implementation_guidelines
                m_lines = ["<current_section_motion>"]
                m_lines.append("MANDATORY MOTION REQUIREMENTS FOR THIS SECTION (HIGH PRIORITY - DO NOT OMIT):")
                for spec in resolved_motion:
                    m_type = spec.type.value if hasattr(spec.type, "value") else str(getattr(spec, "type", spec))
                    intensity = getattr(spec, "intensity", "subtle")
                    target = getattr(spec, "target_section", "general")
                    m_lines.append(f"- Pattern: {m_type} (Target: {target}, Intensity: {intensity})")
                    guide = get_motion_implementation_guidelines(spec) if hasattr(spec, "type") else ""
                    if guide:
                        m_lines.append(guide)
                m_lines.append("</current_section_motion>")
                motion_text = "\n".join(m_lines)
            except Exception:
                pass

        # Selected element block (Priority 1)
        selected_element_text = ""
        if preview_selection:
            elem_lines = ["<selected_element>"]
            if preview_selection.get("component"):
                elem_lines.append(f"Component: {preview_selection['component']}")
            if preview_selection.get("selector"):
                elem_lines.append(f"Selector: {preview_selection['selector']}")
            if preview_selection.get("tag"):
                elem_lines.append(f"Tag: {preview_selection['tag']}")
            if preview_selection.get("text"):
                elem_lines.append(f"Element Text: {str(preview_selection['text'])[:120]}")
            if preview_selection.get("three_node"):
                elem_lines.append(f"Three.js 3D Node: {preview_selection['three_node']}")
            elem_lines.append("</selected_element>")
            selected_element_text = "\n".join(elem_lines)

        # Project Metadata (Priority 6)
        metadata_text = self.format_project_metadata(session, all_files, budget.project_metadata)
        used_metadata = estimate_tokens(metadata_text)

        # Build / Runtime Diagnostics (Priority 7)
        diag_state = diagnostics or getattr(session, "build_state", None)
        diagnostics_text = self.format_diagnostics(diag_state, budget.build_diagnostics)
        used_diagnostics = estimate_tokens(diagnostics_text)

        # Recent Conversation (Priority 8)
        history_list = getattr(session, "history", None)
        history_text = self.format_recent_conversation(history_list, budget.recent_conversation)
        used_history = estimate_tokens(history_text)

        # 3. Dynamic Surplus Reallocation
        # Calculate surplus from unused fixed allocations
        surplus = max(0, budget.current_instruction - used_instruction)
        surplus += max(0, budget.project_metadata - used_metadata)
        surplus += max(0, budget.build_diagnostics - used_diagnostics)
        surplus += max(0, budget.recent_conversation - used_history)

        # Reallocate surplus: 65% to selected files, 35% to related files
        selected_budget = budget.selected_files + int(surplus * 0.65)
        related_budget = budget.related_files + int(surplus * 0.35)

        # Extract focus terms from instruction for smart windowing
        focus_terms = extract_search_terms(new_instruction)

        # 4. Format Selected Target Files (Priority 1, 2, 3, 4)
        selected_sections: List[str] = []
        if selected_files:
            tokens_per_selected = max(300, selected_budget // len(selected_files))
            for path, content in selected_files:
                excerpt = bounded_excerpt(
                    path=path,
                    content=content,
                    max_tokens=tokens_per_selected,
                    focus_terms=focus_terms,
                    is_primary=True,
                )
                selected_sections.append(f'<file path="{path}">\n{excerpt}\n</file>')

        selected_files_text = "\n\n".join(selected_sections)
        used_selected = estimate_tokens(selected_files_text)

        # 5. Format Related Files (Priority 5)
        related_sections: List[str] = []
        if related_files:
            tokens_per_related = max(150, related_budget // len(related_files))
            for path, content in related_files:
                excerpt = bounded_excerpt(
                    path=path,
                    content=content,
                    max_tokens=tokens_per_related,
                    focus_terms=focus_terms,
                    is_primary=False,
                )
                related_sections.append(f'<related_file path="{path}">\n{excerpt}\n</related_file>')

        related_files_text = "\n\n".join(related_sections)
        used_related = estimate_tokens(related_files_text)

        # Assemble complete context prompt (motion_text placed adjacent to instruction with top priority)
        prompt_parts = []
        if metadata_text:
            prompt_parts.append(metadata_text)
        if selected_element_text:
            prompt_parts.append(selected_element_text)
        if diagnostics_text:
            prompt_parts.append(diagnostics_text)
        if history_text:
            prompt_parts.append(history_text)

        if selected_files_text:
            prompt_parts.append(f"CURRENT TARGET FILE CONTENTS TO MODIFY:\n{selected_files_text}")

        if related_files_text:
            prompt_parts.append(f"REFERENCE & RELATED FILES (READ-ONLY):\n{related_files_text}")

        if motion_text:
            prompt_parts.append(motion_text)

        prompt_parts.append(instruction_text)
        prompt_text = "\n\n".join(prompt_parts)

        # Validate final prompt using real Qwen3 tokenizer and enforce context limits
        from agent.config import ModelRuntimeConfig
        real_prompt_tokens = ModelRuntimeConfig.count_tokens(prompt_text)

        # Enforce that prompt strictly fits within total budget less system contracts and reserve
        max_prompt_allowance = max(100, budget.total - budget.system_contracts - budget.reserve)
        if real_prompt_tokens > max_prompt_allowance:
            # Prune lowest-priority sections iteratively if real token count exceeds estimate
            # Motion requirements and instruction_text are NEVER dropped
            if related_files_text:
                related_files_text = ""
                used_related = 0
                prompt_parts = [p for p in [metadata_text, selected_element_text, diagnostics_text, history_text] if p]
                if selected_files_text:
                    prompt_parts.append(f"CURRENT TARGET FILE CONTENTS TO MODIFY:\n{selected_files_text}")
                if motion_text:
                    prompt_parts.append(motion_text)
                prompt_parts.append(instruction_text)
                prompt_text = "\n\n".join(prompt_parts)
                real_prompt_tokens = ModelRuntimeConfig.count_tokens(prompt_text)

            if real_prompt_tokens > max_prompt_allowance and history_text:
                history_text = ""
                used_history = 0
                prompt_parts = [p for p in [metadata_text, selected_element_text, diagnostics_text] if p]
                if selected_files_text:
                    prompt_parts.append(f"CURRENT TARGET FILE CONTENTS TO MODIFY:\n{selected_files_text}")
                if motion_text:
                    prompt_parts.append(motion_text)
                prompt_parts.append(instruction_text)
                prompt_text = "\n\n".join(prompt_parts)
                real_prompt_tokens = ModelRuntimeConfig.count_tokens(prompt_text)

            if real_prompt_tokens > max_prompt_allowance and diagnostics_text:
                diagnostics_text = ""
                used_diagnostics = 0
                prompt_parts = [p for p in [metadata_text, selected_element_text] if p]
                if selected_files_text:
                    prompt_parts.append(f"CURRENT TARGET FILE CONTENTS TO MODIFY:\n{selected_files_text}")
                if motion_text:
                    prompt_parts.append(motion_text)
                prompt_parts.append(instruction_text)
                prompt_text = "\n\n".join(prompt_parts)
                real_prompt_tokens = ModelRuntimeConfig.count_tokens(prompt_text)

            if real_prompt_tokens > max_prompt_allowance and selected_files_text:
                protected_tokens = ModelRuntimeConfig.count_tokens(instruction_text) + (ModelRuntimeConfig.count_tokens(motion_text) if motion_text else 0) + 50
                avail_tokens = max(200, max_prompt_allowance - protected_tokens)
                selected_sections = []
                tokens_per_sel = max(150, avail_tokens // max(1, len(selected_files)))
                for path, content in selected_files:
                    exc = bounded_excerpt(path, content, max_tokens=tokens_per_sel, focus_terms=focus_terms, is_primary=True)
                    selected_sections.append(f'<file path="{path}">\n{exc}\n</file>')
                selected_files_text = "\n\n".join(selected_sections)
                used_selected = ModelRuntimeConfig.count_tokens(selected_files_text)
                prompt_parts = [f"CURRENT TARGET FILE CONTENTS TO MODIFY:\n{selected_files_text}"]
                if motion_text:
                    prompt_parts.append(motion_text)
                prompt_parts.append(instruction_text)
                prompt_text = "\n\n".join(prompt_parts)
                real_prompt_tokens = ModelRuntimeConfig.count_tokens(prompt_text)

        # Compute final token usage using real tokenizer validation
        total_used = min(budget.total, real_prompt_tokens + budget.system_contracts)
        usage = TokenUsage(
            system_contracts=budget.system_contracts,
            current_instruction=used_instruction,
            project_metadata=used_metadata,
            selected_files=used_selected,
            related_files=used_related,
            recent_conversation=used_history,
            build_diagnostics=used_diagnostics,
            reserve=budget.reserve,
            total=total_used,
        )

        return BuiltContext(
            prompt_text=prompt_text,
            selected_files=selected_files,
            related_files=related_files,
            diagnostics_text=diagnostics_text,
            metadata_text=metadata_text,
            history_text=history_text,
            token_usage=usage,
            budget=budget,
            motion_text=motion_text,
        )



# Global singleton builder instance
context_builder = ContextBuilder()
