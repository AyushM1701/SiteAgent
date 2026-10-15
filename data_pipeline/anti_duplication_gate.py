"""
anti_duplication_gate.py - Corpus-Level Anti-Duplication & Cross-Domain Overlap Gate

Computes phrase-level and CSS-value-level n-gram overlap across trajectories from different domains
(not just full-message hash dedup). Rejects or downsamples batches/trajectories where a cliché phrase
(e.g., "Carefully curated offerings tailored to provide exceptional quality and reliability")
or an identical multi-declaration CSS block appears across 3+ unrelated domains.

Exempts single-component tasks (e.g., shadcn/ui primitives, typescript_instruct) from the full-site
cross-domain ratio, as those are single-component tasks and not full-site compositions.
"""

import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple


# Cliché phrases that must never propagate across multiple domains
BANNED_TEMPLATE_CLICHES = [
    "carefully curated offerings tailored to provide exceptional quality and reliability",
    "carefully curated offerings tailored to provide",
    "offerings tailored to provide exceptional quality and reliability",
]

# Protocol and structural phrases to exclude from phrase n-gram deduplication
PROTOCOL_IGNORE_PHRASES = {
    "you are an expert autonomous react",
    "explain your plan for the current section",
    "tool call name write site",
    "build a complete website for the following",
    "first section required write the header",
    "files src components header tsx",
    "files src components hero tsx",
    "files src components footer tsx",
    "all rights reserved",
    "site build complete all required sections",
    "operating guidelines every turn output",
    "react typescript and css coding agent",
    "write one section one tsx file",
    "write one tool call name write site",
    "header hero core offerings and footer",
    "core offerings and footer are complete",
    "sections of the website are written and verified",
    "strictly comply with the active design tokens",
    "all 4 sections of the",
    "successfully built the complete",
    "website with full responsive layouts",
    "it needs to reflect the brand identity",
    "deep background with crisp contrast",
    "implement a scroll listener to trigger",
    "trigger glassmorphism and subtle border illumination",
    "subtle border illumination on scroll",
    "start by crafting the header for",
    "now implementing the section",
    "using a responsive card grid with",
    "hero accepted now implementing",
    "section accepted now completing the final",
    "final section footer it will display",
}

GENERIC_LAYOUT_PROPS = {
    "display", "align-items", "justify-content", "flex-direction", "gap",
    "flex", "grid-template-columns", "grid-column", "grid-row",
    "width", "height", "max-width", "min-height", "margin", "padding",
    "position", "top", "left", "right", "bottom", "z-index", "overflow",
    "box-sizing", "text-align",
}

def is_distinctive_css_block(norm: str, min_declarations: int = 4) -> bool:
    """
    Determines if a normalized CSS block represents a distinctive visual styling pattern
    (e.g., custom card surfaces, branded borders, shadows, and color themes) rather than
    a generic flexbox/grid layout, alignment container, or micro-indicator dot/bar.
    """
    decls = [d.strip() for d in norm.split(";") if d.strip() and ":" in d]
    if len(decls) < min_declarations:
        return False

    # Filter out micro-indicators (e.g. width: 6px-25px, height: 2px-25px)
    has_micro_dimension = any(
        re.search(r"^(?:width|height):\s*(?:[1-9]|[12][0-9])px$", d) for d in decls
    )
    if has_micro_dimension and len(decls) <= 5:
        return False

    visual_props = [
        d.split(":")[0].strip().lower() for d in decls
        if any(v in d.split(":")[0].lower() for v in ["background", "border", "shadow", "radius", "color", "font-family", "backdrop"])
    ]
    # Must have at least 3 visual styling properties and min_declarations total properties
    return len(visual_props) >= 3 and len(decls) >= min_declarations

# Standard common CSS declarations to allow universally (resets, universal flex/grid idioms)
COMMON_CSS_ALLOWLIST = {
    "box-sizing:border-box",
    "margin:0",
    "padding:0",
    "width:100%",
    "height:100%",
    "display:flex",
    "display:none",
    "display:block",
    "display:grid",
    "align-items:center;display:flex",
    "display:flex;justify-content:center",
    "align-items:center;display:flex;justify-content:center",
    "background:transparent;border:none",
    "cursor:pointer",
    "position:relative",
    "position:absolute",
    "animation:none !important;transform:none !important;transition:none !important",
    "animation:none !important;opacity:1 !important;transform:none !important;transition:none !important",
    "transform:none !important;transition:none !important",
    "opacity:1 !important;transform:none !important;transition:none !important",
    "animation:none !important;transition:none !important",
}


def is_full_site_trajectory(trajectory: Dict[str, Any]) -> bool:
    """
    Identifies whether a trajectory represents a full-site multi-section composition
    or a single-component task (e.g. shadcn UI primitives, typescript-instruct).
    Single-component tasks are exempt from full-site cross-domain checks.
    """
    task_id = trajectory.get("task_id", "")
    if not task_id:
        return False

    # Check task_id prefixes
    if task_id.startswith("site_"):
        return True

    # Check for presence of write_site tool calls or multi-section files
    messages = trajectory.get("messages", [])
    has_site_call = False
    for m in messages:
        c = m.get("content", "")
        if 'name="write_site"' in c or "src/components/Header.tsx" in c:
            has_site_call = True
            break

    # Single-component task indicators (e.g. shadcn, radix, standalone primitives)
    if any(k in task_id.lower() for k in ["shadcn", "primitive", "task_", "episode_task_"]):
        if not has_site_call:
            return False

    return has_site_call


def extract_domain(trajectory: Dict[str, Any]) -> str:
    """
    Extracts canonical business domain from brief XML, business_type, or task_id.
    """
    messages = trajectory.get("messages", [])
    for m in messages:
        c = m.get("content", "")
        btype_m = re.search(r"<business_type>(.*?)</business_type>", c)
        if btype_m:
            return btype_m.group(1).strip().lower()

    task_id = trajectory.get("task_id", "")
    parts = task_id.split("_")
    if len(parts) >= 2 and parts[0] == "site":
        return parts[1].lower()

    return "general"


def extract_prose_ngrams(trajectory: Dict[str, Any], n: int = 7, include_thoughts: bool = False) -> Set[str]:
    """
    Extracts normalized word n-grams from human-facing component copy
    (JSX text nodes, subtitles, quotes, card descriptions, and titles).
    Optionally includes thoughts with meta-planning filtering.
    """
    ngrams: Set[str] = set()
    messages = trajectory.get("messages", [])

    for m in messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content", "")
        prose_chunks = []

        # 1. JSX text nodes (e.g. <p>...</p>, <h2>...</h2>, <h3>...</h3>, <span>...</span>)
        jsx_texts = re.findall(r">([^<>{}\n]{15,200})<", content)
        prose_chunks.extend(jsx_texts)

        # 2. TSX object literals with description, subtitle, quote, tagline
        desc_matches = re.findall(r'["\'](?:desc|description|quote|subtitle|tagline)["\']\s*:\s*["\']([^"\']{15,200})["\']', content)
        prose_chunks.extend(desc_matches)

        # 3. Optional thought prose (excluding agent turn-orchestration boilerplate)
        if include_thoughts:
            thoughts = re.findall(r"<thought>\s*(.*?)\s*</thought>", content, flags=re.DOTALL)
            for th in thoughts:
                for sent in re.split(r"[.!?]\s+", th):
                    sent_l = sent.lower()
                    if any(k in sent_l for k in [
                        "accepted", "finalizing", "strictly comply", "written and verified",
                        "now implementing", "now building", "start by crafting", "completing the final section",
                        "design tokens", "active design tokens", "tool_call", "write_site"
                    ]):
                        continue
                    prose_chunks.append(sent)

        for chunk in prose_chunks:
            # Normalize text
            clean = re.sub(r"[^a-zA-Z0-9\s]", " ", chunk).lower()
            words = [w for w in clean.split() if len(w) >= 3]
            if len(words) < n:
                continue

            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i + n])
                if any(ig in ngram for ig in PROTOCOL_IGNORE_PHRASES):
                    continue
                ngrams.add(ngram)

    return ngrams


def normalize_css_block(block_body: str) -> str:
    """
    Normalizes a CSS rule body into a canonical, alphabetically sorted declaration string.
    """
    # Strip comments
    clean = re.sub(r"/\*.*?\*/", "", block_body, flags=re.DOTALL)
    decls = []
    for line in clean.split(";"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        prop, val = line.split(":", 1)
        prop = prop.strip().lower()
        val = re.sub(r"\s+", " ", val.strip().lower())
        # Strip vendor prefixes for canonical matching
        prop = re.sub(r"^-(?:webkit|moz|ms|o)-", "", prop)
        decls.append(f"{prop}:{val}")

    decls.sort()
    return ";".join(decls)


def extract_css_blocks(trajectory: Dict[str, Any], min_declarations: int = 4) -> Set[str]:
    """
    Extracts non-trivial normalized CSS declaration blocks from written CSS files.
    """
    blocks: Set[str] = set()
    messages = trajectory.get("messages", [])

    for m in messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content", "")
        css_files = re.findall(r'<file path="[^"]*\.css">\s*(.*?)\s*</file>', content, flags=re.DOTALL)

        for css in css_files:
            rule_bodies = re.findall(r'\{([^}]+)\}', css)
            for body in rule_bodies:
                norm = normalize_css_block(body)
                # Ensure it is a distinctive styling block rather than generic layout/utility
                if is_distinctive_css_block(norm, min_declarations=min_declarations) and norm not in COMMON_CSS_ALLOWLIST:
                    blocks.add(norm)

    return blocks


class AntiDuplicationGate:
    """
    Corpus-level anti-duplication gate.
    Monitors cross-domain phrase and CSS block overlap, rejecting or downsampling
    trajectories that replicate identical phrases or CSS rules across 3+ unrelated domains.
    """

    def __init__(
        self,
        max_cross_domain_occurrences: int = 2,
        min_ngram_size: int = 7,
        min_css_declarations: int = 3,
        strict_banned_phrases: bool = True,
    ):
        self.max_cross_domain = max_cross_domain_occurrences
        self.min_ngram_size = min_ngram_size
        self.min_css_declarations = min_css_declarations
        self.strict_banned_phrases = strict_banned_phrases

        # phrase -> set of domain names where observed
        self.phrase_domain_index: Dict[str, Set[str]] = defaultdict(set)
        # phrase -> list of task_ids where observed
        self.phrase_task_index: Dict[str, List[str]] = defaultdict(list)

        # css_block -> set of domain names where observed
        self.css_domain_index: Dict[str, Set[str]] = defaultdict(set)
        # css_block -> list of task_ids where observed
        self.css_task_index: Dict[str, List[str]] = defaultdict(list)

        # Domain tracking
        self.domain_trajectory_count: Dict[str, int] = defaultdict(int)
        self.full_site_count = 0
        self.single_component_count = 0
        self.total_checked = 0
        self.total_rejected = 0

    def check_trajectory(self, trajectory: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Checks a trajectory against the anti-duplication gate.
        Returns:
            (is_valid: bool, violations: List[str])
        """
        task_id = trajectory.get("task_id", "unknown")
        is_site = is_full_site_trajectory(trajectory)

        # Single component tasks are exempted from cross-domain full-site duplication gate
        if not is_site:
            return True, []

        domain = extract_domain(trajectory)
        violations: List[str] = []

        # 1. Check for banned template cliché phrases (e.g. "Carefully curated offerings...")
        if self.strict_banned_phrases:
            raw_text = json.dumps(trajectory).lower()
            for cliche in BANNED_TEMPLATE_CLICHES:
                if cliche in raw_text:
                    violations.append(
                        f"Contains banned template cliché phrase: '{cliche}'"
                    )

        # 2. Check phrase n-grams across unrelated domains
        ngrams = extract_prose_ngrams(trajectory, n=self.min_ngram_size)
        for ng in ngrams:
            existing_domains = self.phrase_domain_index.get(ng, set())
            unrelated_domains = existing_domains - {domain}
            if len(unrelated_domains) >= self.max_cross_domain:
                violations.append(
                    f"Phrase '{ng}' appears across {len(unrelated_domains)} unrelated domains: {list(unrelated_domains)[:4]}"
                )
                break  # Record highest-severity match

        # 3. Check CSS block declarations across unrelated domains
        css_blocks = extract_css_blocks(trajectory, min_declarations=self.min_css_declarations)
        for block in css_blocks:
            existing_css_domains = self.css_domain_index.get(block, set())
            unrelated_css_domains = existing_css_domains - {domain}
            if len(unrelated_css_domains) >= self.max_cross_domain:
                sample_decl = block[:80] + "..." if len(block) > 80 else block
                violations.append(
                    f"CSS block '{sample_decl}' appears across {len(unrelated_css_domains)} unrelated domains: {list(unrelated_css_domains)[:4]}"
                )
                break

        is_valid = len(violations) == 0
        return is_valid, violations

    def register_trajectory(self, trajectory: Dict[str, Any]):
        """
        Indexes a trajectory's phrases and CSS blocks under its domain.
        """
        task_id = trajectory.get("task_id", "unknown")
        is_site = is_full_site_trajectory(trajectory)

        self.total_checked += 1
        if not is_site:
            self.single_component_count += 1
            return

        self.full_site_count += 1
        domain = extract_domain(trajectory)
        self.domain_trajectory_count[domain] += 1

        # Index prose n-grams
        ngrams = extract_prose_ngrams(trajectory, n=self.min_ngram_size)
        for ng in ngrams:
            self.phrase_domain_index[ng].add(domain)
            if len(self.phrase_task_index[ng]) < 5:
                self.phrase_task_index[ng].append(task_id)

        # Index CSS blocks
        css_blocks = extract_css_blocks(trajectory, min_declarations=self.min_css_declarations)
        for block in css_blocks:
            self.css_domain_index[block].add(domain)
            if len(self.css_task_index[block]) < 5:
                self.css_task_index[block].append(task_id)

    def filter_trajectories(
        self,
        trajectories: List[Dict[str, Any]],
        mode: str = "reject",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Processes a sequence of trajectories through the gate, rejecting or downsampling
        violating items.
        """
        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        rejection_details: List[Dict[str, Any]] = []

        for traj in trajectories:
            task_id = traj.get("task_id", "unknown")
            is_valid, violations = self.check_trajectory(traj)

            if is_valid:
                self.register_trajectory(traj)
                accepted.append(traj)
            else:
                self.total_rejected += 1
                rejected.append(traj)
                rejection_details.append({
                    "task_id": task_id,
                    "domain": extract_domain(traj),
                    "violations": violations,
                })

        report = {
            "total_input": len(trajectories),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "full_site_count": self.full_site_count,
            "single_component_count": self.single_component_count,
            "rejections": rejection_details,
        }

        return accepted, report

    def audit_corpus(self, trajectories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Audits an entire corpus or merged JSONL file and computes cross-domain overlap metrics.
        Returns a structured report verifying that baseline duplication has been eliminated.
        """
        full_site_trajs: List[Dict[str, Any]] = []
        single_comp_trajs: List[Dict[str, Any]] = []

        target_cliche = BANNED_TEMPLATE_CLICHES[0]
        cliche_occurrences = 0

        # Dedicated temporary gate to measure cross-domain spread across the entire corpus
        temp_gate = AntiDuplicationGate(
            max_cross_domain_occurrences=self.max_cross_domain,
            min_ngram_size=self.min_ngram_size,
            min_css_declarations=self.min_css_declarations,
            strict_banned_phrases=False,
        )

        for traj in trajectories:
            if is_full_site_trajectory(traj):
                full_site_trajs.append(traj)
                # Check baseline phrase
                if target_cliche in json.dumps(traj).lower():
                    cliche_occurrences += 1
                temp_gate.register_trajectory(traj)
            else:
                single_comp_trajs.append(traj)

        # Count phrases appearing across 3+ unrelated domains
        cross_domain_phrases = {
            phrase: list(doms)
            for phrase, doms in temp_gate.phrase_domain_index.items()
            if len(doms) >= 3
        }

        # Count CSS blocks appearing across 3+ unrelated domains
        cross_domain_css = {
            block: list(doms)
            for block, doms in temp_gate.css_domain_index.items()
            if len(doms) >= 3
        }

        full_site_total = len(full_site_trajs)
        cliche_ratio_str = f"{cliche_occurrences}/{full_site_total}" if full_site_total > 0 else "0/0"
        baseline_beaten = cliche_occurrences < 102  # Baseline was 102 of 149

        return {
            "total_trajectories": len(trajectories),
            "full_site_trajectories": full_site_total,
            "single_component_tasks": len(single_comp_trajs),
            "target_cliche_occurrences": cliche_occurrences,
            "target_cliche_ratio": cliche_ratio_str,
            "baseline_beaten": baseline_beaten,
            "cross_domain_phrase_violations_count": len(cross_domain_phrases),
            "cross_domain_css_violations_count": len(cross_domain_css),
            "status": "PASS" if baseline_beaten and cliche_occurrences == 0 else "WARN",
        }
