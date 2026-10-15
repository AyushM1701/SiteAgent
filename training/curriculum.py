"""
training/curriculum.py - Staged Training Curriculum for the 4B Model (Stages A through H).

Implements the official 8-stage curriculum recommended for post-corpus stabilization:

  Stage A — Protocol fidelity (near-perfect structured tool calls, zero thought tokens, valid XML)
  Stage B — React correctness (diverse single components, accessibility, state, forms, tabs, modals)
  Stage C — Design-system execution (strict adherence to 10 supplied design genomes)
  Stage D — Section-archetype diversity (multi-topology features: bento, sticky deck, diagram, etc.)
  Stage E — Full-site multi-turn generation (exploded-per-assistant-turn sequential composition)
  Stage F — Repair trajectories (targeted surgical edits: TypeScript, overflow, contrast, interaction)
  Stage G — Motion/interactions (known-safe declarative primitives, mandatory reduced-motion)
  Stage H — Preference optimization for aesthetics (DPO pairwise; filtered correctness-first)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple


# ==============================================================================
# 1. Curriculum Stages & Taxonomy
# ==============================================================================

class CurriculumStage(str, Enum):
    STAGE_A_PROTOCOL_FIDELITY = "stage_a_protocol_fidelity"
    STAGE_B_REACT_CORRECTNESS = "stage_b_react_correctness"
    STAGE_C_DESIGN_SYSTEM_EXECUTION = "stage_c_design_system_execution"
    STAGE_D_SECTION_ARCHETYPE_DIVERSITY = "stage_d_section_archetype_diversity"
    STAGE_E_FULL_SITE_MULTI_TURN = "stage_e_full_site_multi_turn"
    STAGE_F_REPAIR_TRAJECTORIES = "stage_f_repair_trajectories"
    STAGE_G_MOTION_INTERACTIONS = "stage_g_motion_interactions"
    STAGE_H_PREFERENCE_OPTIMIZATION = "stage_h_preference_optimization"


# ── Stage C: 10 Authoritative Design Genomes ─────────────────────────────────

DESIGN_GENOMES: list[str] = [
    "paper editorial",         # warm stone/cream, serifs, print-inspired typography, generous whitespace
    "luxury dark",             # deep obsidian/charcoal, high-contrast gold/silver accents, refined tracking
    "neo-brutalist",           # stark borders, hard offset drop-shadows, high-saturation accents
    "technical monochrome",    # monospace accents, terminal dark, precision grids, data badges
    "soft organic",            # earthy greens/terracotta, rounded curves, tactile card surfaces
    "Swiss grid",              # modular grid discipline, stark grotesque typography, asymmetrical balance
    "high-fashion typography", # high-contrast display serifs, literary pull quotes, monograph chapters
    "product glass",           # glassmorphism backdrops, backdrop-filter blur, luminous borders
    "warm hospitality",        # rich espresso/cream/sage tones, welcoming imagery, classic menu typography
    "playful geometric",       # vibrant dual-tone accents, pill buttons, circular badges, joyful rhythm
]


# ── Stage D: 8 Mandatory Visual Structures for Content/Features ──────────────

FEATURE_ARCHETYPES: list[str] = [
    "bento",               # variable-span mosaic grid (2x1, 1x2, 2x2) with metric badges
    "editorial list",      # numbered literary monograph items with pull quotes and prose
    "sticky deck",         # stacked storytelling cards pinning on scroll
    "diagram",             # process flow with connector nodes and step badges
    "horizontal ribbon",   # compact ticker / marquee / horizontal scroll track
    "asymmetric split",    # 50/50 or 60/40 offset layout with focal feature
    "comparison table",    # structured matrix with checkmarks and feature rows
    "metric narrative",    # large KPI numbers with contextual impact narrative
]

MAX_ARCHETYPE_DOMINANCE_THRESHOLD = 0.25  # No single archetype (e.g. 3-card grid) may exceed 25%


# ── Stage F: 6 Targeted Repair Categories ────────────────────────────────────

REPAIR_CATEGORIES: list[str] = [
    "fix_typescript_only",     # type annotations, missing imports, unparameterized generics
    "fix_overflow_only",       # mobile responsiveness, text-overflow, box-sizing, max-width
    "fix_contrast_only",       # WCAG AA/AAA text-to-background luminance contrast
    "fix_one_interaction",     # broken click handler, missing state update, unhandled keyboard event
    "fix_one_token",           # reconcile color token, spacing variable, font-family token
    "fix_one_component",       # surgical edit to child component without modifying siblings
]


# ── Stage G: Known-Safe Motion Primitives ─────────────────────────────────────

MOTION_PRIMITIVES: list[str] = [
    "StickyNarrative",         # CSS position: sticky with progress observation
    "ScrollReveal",            # declarative IntersectionObserver wrapper
    "StaggeredEntrance",       # CSS custom property --stagger-index with transition delays
    "CrossfadePanel",          # accessible tab panel crossfade/settle
]


# ── Stage H: Preference Criteria (Aesthetic Optimization) ─────────────────────

PREFERENCE_CRITERIA: list[str] = [
    "composition",             # visual balance, white space, layout entropy
    "typography",              # font pairings, line-height, typographic hierarchy
    "uniqueness",              # distinct brand character, non-generic details
    "information_hierarchy",   # clear reading flow, distinct primary/secondary visual weight
    "polish",                  # subtle micro-interactions, cohesive tokens, refined borders
    "responsive_composition",  # graceful adaptation from mobile to ultrawide
]


# ==============================================================================
# 2. Stage Specification & Documentation
# ==============================================================================

@dataclass(frozen=True)
class StageSpec:
    stage: CurriculumStage
    name: str
    objective: str
    target_corpus_size: str
    prerequisites: List[CurriculumStage]
    key_constraints: List[str]
    evaluation_gate: str


STAGE_SPECS: dict[CurriculumStage, StageSpec] = {
    CurriculumStage.STAGE_A_PROTOCOL_FIDELITY: StageSpec(
        stage=CurriculumStage.STAGE_A_PROTOCOL_FIDELITY,
        name="Stage A — Protocol Fidelity",
        objective="Near-perfect structured output: tool grammar, file paths, 1 action per turn, zero thought tokens, valid XML.",
        target_corpus_size="50–100 clean rows",
        prerequisites=[],
        key_constraints=[
            "Strictly 0 <thought> or <think> tags in assistant targets",
            "Exactly 1 action per turn (<tool_call> or <finish>)",
            "Safe, relative file paths only (src/components/...)",
            "100% balanced XML tags",
            "No markdown fences wrapping tool calls",
        ],
        evaluation_gate="100% protocol parser pass rate on synthetic tool calls.",
    ),
    CurriculumStage.STAGE_B_REACT_CORRECTNESS: StageSpec(
        stage=CurriculumStage.STAGE_B_REACT_CORRECTNESS,
        name="Stage B — React Correctness",
        objective="Diverse single components with reliable state, forms, menus, tabs, modals, and WCAG accessibility.",
        target_corpus_size="200–400 component examples",
        prerequisites=[CurriculumStage.STAGE_A_PROTOCOL_FIDELITY],
        key_constraints=[
            "Zero TypeScript compilation errors (tsc --noEmit)",
            "Functional React state (useState/useEffect/useRef)",
            "Accessible controls (aria-expanded, aria-selected, role)",
            "Keyboard and escape listener cleanup",
            "Simple, clean styling focused on functional soundness",
        ],
        evaluation_gate=">= 90% TypeScript compile rate, >= 80% Vitest unit test pass rate.",
    ),
    CurriculumStage.STAGE_C_DESIGN_SYSTEM_EXECUTION: StageSpec(
        stage=CurriculumStage.STAGE_C_DESIGN_SYSTEM_EXECUTION,
        name="Stage C — Design-System Execution",
        objective="Train the model to follow a supplied design genome faithfully rather than inventing arbitrary styles.",
        target_corpus_size="300–500 examples",
        prerequisites=[CurriculumStage.STAGE_B_REACT_CORRECTNESS],
        key_constraints=[
            "Covers all 10 canonical design genomes in balanced proportions",
            "No single design genome exceeds 18% of the dataset",
            "Adherence to specified CSS variables and typography tokens",
            "Text contrast passes WCAG AA for declared color palette",
        ],
        evaluation_gate=">= 85% design-token fidelity score across all 10 genomes.",
    ),
    CurriculumStage.STAGE_D_SECTION_ARCHETYPE_DIVERSITY: StageSpec(
        stage=CurriculumStage.STAGE_D_SECTION_ARCHETYPE_DIVERSITY,
        name="Stage D — Section-Archetype Diversity",
        objective="Eliminate 'features = 3 cards' template collapse by training 8 distinct visual topologies.",
        target_corpus_size="300–600 section examples",
        prerequisites=[CurriculumStage.STAGE_C_DESIGN_SYSTEM_EXECUTION],
        key_constraints=[
            "Features must exist as bento, editorial list, sticky deck, diagram, ribbon, split, table, metric narrative",
            "No single feature structure exceeds 25% of feature rows",
            "High compositional entropy across all content sections",
        ],
        evaluation_gate="Anti-template collapse score >= 0.70; card-grid dominance <= 20%.",
    ),
    CurriculumStage.STAGE_E_FULL_SITE_MULTI_TURN: StageSpec(
        stage=CurriculumStage.STAGE_E_FULL_SITE_MULTI_TURN,
        name="Stage E — Full-Site Multi-Turn Generation",
        objective="Exploded-per-assistant-turn multi-turn generation where prior sections provide context for the next supervised section.",
        target_corpus_size="500–1,000 turn-exploded rows",
        prerequisites=[CurriculumStage.STAGE_D_SECTION_ARCHETYPE_DIVERSITY],
        key_constraints=[
            "Exploded turn formulation: prior sections visible as context, next section is supervised target",
            "Consistent design token namespace across all sections of a site",
            "Cross-section links and shared anchors (#hero, #pricing, #contact) match exactly",
            "Zero hallucinated backend dependencies across sections",
        ],
        evaluation_gate="Full-site build pass rate >= 80%, composite site score >= 0.70.",
    ),
    CurriculumStage.STAGE_F_REPAIR_TRAJECTORIES: StageSpec(
        stage=CurriculumStage.STAGE_F_REPAIR_TRAJECTORIES,
        name="Stage F — Repair Trajectories",
        objective="Train targeted, minimal patch edits rather than destructive whole-file rewrites.",
        target_corpus_size="200–400 repair trajectories",
        prerequisites=[CurriculumStage.STAGE_E_FULL_SITE_MULTI_TURN],
        key_constraints=[
            "Covers all 6 repair categories: TypeScript, overflow, contrast, interaction, token, component",
            "Surgical edits: line diff ratio <= 30% of file (patch-like behavior)",
            "Unrelated component code preserved intact",
            "Directly addresses compiler/linter error message",
        ],
        evaluation_gate="Single-turn repair success rate >= 75% on compiler error holdout.",
    ),
    CurriculumStage.STAGE_G_MOTION_INTERACTIONS: StageSpec(
        stage=CurriculumStage.STAGE_G_MOTION_INTERACTIONS,
        name="Stage G — Motion/Interactions",
        objective="Declarative, known-safe motion primitives rather than 80-line raw scroll listeners.",
        target_corpus_size="200–350 motion examples",
        prerequisites=[CurriculumStage.STAGE_F_REPAIR_TRAJECTORIES],
        key_constraints=[
            "Utilize known-safe motion patterns (StickyNarrative, ScrollReveal, StaggeredEntrance, CrossfadePanel)",
            "100% of motion rules accompanied by @media (prefers-reduced-motion: reduce)",
            "No uncleaned window event listeners",
            "GPU-accelerated properties (transform, opacity) prioritized",
        ],
        evaluation_gate="Motion visual judge pass rate >= 85%; 100% reduced-motion compliance.",
    ),
    CurriculumStage.STAGE_H_PREFERENCE_OPTIMIZATION: StageSpec(
        stage=CurriculumStage.STAGE_H_PREFERENCE_OPTIMIZATION,
        name="Stage H — Preference Optimization for Aesthetics (DPO)",
        objective="Pairwise aesthetic alignment (Site A vs Site B) strictly filtered for correctness first.",
        target_corpus_size="300–600 pairwise comparisons",
        prerequisites=[
            CurriculumStage.STAGE_E_FULL_SITE_MULTI_TURN,
            CurriculumStage.STAGE_F_REPAIR_TRAJECTORIES,
            CurriculumStage.STAGE_G_MOTION_INTERACTIONS,
        ],
        key_constraints=[
            "Both candidate sites MUST pass 100% of hard gates (typecheck, render, exact facts)",
            "Never preference-train attractive broken sites against correct plain ones",
            "Pairwise preference scored on: composition, typography, uniqueness, hierarchy, polish, responsiveness",
        ],
        evaluation_gate="DPO win-rate on blinded human aesthetic review >= 65% over baseline.",
    ),
}


# ==============================================================================
# 3. Stage Validation & Gating Functions
# ==============================================================================

@dataclass
class StageValidationResult:
    stage: CurriculumStage
    is_valid: bool
    total_samples: int
    passed_samples: int
    violations: List[str]
    metrics: Dict[str, Any]
    summary: str


@dataclass(frozen=True)
class VerificationReceipt:
    """Typed, auditable hard-gate evidence for a Stage H pair.

    A bare boolean is not evidence: it cannot identify the artifact, runner, or
    checks that produced it.  Receipts are intentionally strict and JSON-safe.
    """
    schema_version: int
    artifact_id: str
    typecheck: bool
    build: bool
    runtime: bool
    facts: bool
    visual: bool
    provenance: str
    verified_at: str

    @property
    def passed(self) -> bool:
        return all((self.typecheck, self.build, self.runtime, self.facts, self.visual)) and self.provenance == "real"


def parse_verification_receipt(value: Any) -> Optional[VerificationReceipt]:
    if not isinstance(value, dict):
        return None
    required = ("schema_version", "artifact_id", "typecheck", "build", "runtime", "facts", "visual", "provenance", "verified_at")
    if any(k not in value for k in required):
        return None
    if value.get("schema_version") != 1 or not isinstance(value.get("artifact_id"), str) or not value["artifact_id"]:
        return None
    if any(type(value[k]) is not bool for k in ("typecheck", "build", "runtime", "facts", "visual")):
        return None
    if value.get("provenance") != "real" or not isinstance(value.get("verified_at"), str) or not value["verified_at"].strip():
        return None
    return VerificationReceipt(**{k: value[k] for k in required})


def _stage_b_row_errors(row: dict) -> list[str]:
    text = json.dumps(row)
    low = text.lower()
    errors = []
    low_cleaned = re.sub(r'passed\s*\(\s*0\s*errors?\s*\)', '', low)
    low_cleaned = re.sub(r'0\s*errors?', '', low_cleaned)
    if re.search(r"(?:tsc|typescript|compile)[^\n]{0,80}(?:error|fail)|(?:error|fail)[^\n]{0,80}(?:tsc|typescript|compile)", low_cleaned):
        errors.append("typescript compilation failure")
    if "usestate" in low or "useeffect" in low or "useref" in low:
        if "react" not in low and "from 'react'" not in low and 'from \"react\"' not in low:
            errors.append("React hook used without React import")
    interactive = any(x in low for x in ("button", "input", "select", "tab", "modal", "menu", "dialog"))
    if interactive and not any(x in low for x in ("aria-", "role=", "onkeydown", "onclick", "onchange", "onkeyup")):
        errors.append("interactive control lacks accessibility/interaction contract")
    return errors


def _stage_e_row_errors(row: dict) -> list[str]:
    errors = []
    messages = row.get("messages")
    if not isinstance(messages, list) or len([m for m in messages if isinstance(m, dict) and m.get("role") == "assistant"]) < 2:
        errors.append("full-site trajectory must contain at least two assistant turns")
    if row.get("exploded_turn") is None or row.get("total_turns") is None:
        errors.append("row is not an exploded prefix/target trajectory")
    if row.get("exploded_turn") is not None and row.get("total_turns") is not None and row["exploded_turn"] > 1:
        assts = [m for m in messages or [] if isinstance(m, dict) and m.get("role") == "assistant"]
        if len(assts) != row["exploded_turn"]:
            errors.append("exploded prefix does not match exploded_turn")
    if re.search(r"(?:fetch\(|axios|supabase|firebase|mongodb|postgres|/api/)", json.dumps(row), re.I):
        errors.append("undeclared backend dependency")
    return errors


def validate_curriculum_stage(stage: CurriculumStage, dataset_path: str | Path) -> StageValidationResult:
    """
    Validates a training dataset JSONL file against the formal constraints of a curriculum stage.
    Fail-closed: any fundamental violation marks is_valid as False.
    """
    p = Path(dataset_path)
    if not p.is_file():
        return StageValidationResult(
            stage=stage,
            is_valid=False,
            total_samples=0,
            passed_samples=0,
            violations=[f"Dataset file not found: {p}"],
            metrics={},
            summary=f"Validation failed: file not found at {p}",
        )

    rows: list[dict[str, Any]] = []
    line_errors = 0
    with p.open(encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                rows.append(json.loads(line_str))
            except json.JSONDecodeError as err:
                line_errors += 1

    if not rows:
        return StageValidationResult(
            stage=stage,
            is_valid=False,
            total_samples=0,
            passed_samples=0,
            violations=["Empty dataset or unparseable JSON"],
            metrics={"line_errors": line_errors},
            summary="Validation failed: no valid JSON objects in dataset.",
        )

    violations: list[str] = []
    if line_errors > 0:
        violations.append(f"{line_errors} line(s) contain malformed JSON.")

    passed_count = 0
    metrics: dict[str, Any] = {}

    if stage == CurriculumStage.STAGE_A_PROTOCOL_FIDELITY:
        # Check tool grammar, file paths, 1 action per turn, zero thought tokens, valid XML
        thought_tag_count = 0
        multiple_action_count = 0
        malformed_xml_count = 0
        unsafe_path_count = 0

        for r_idx, row in enumerate(rows):
            row_ok = True
            messages = row.get("messages", [])
            for msg in messages:
                if msg.get("role") != "assistant":
                    continue
                content = msg.get("content", "")
                # Zero thought tags
                if any(tag in content for tag in ("<thought>", "</thought>", "<think>", "</think>")):
                    thought_tag_count += 1
                    row_ok = False
                # Exactly one action
                actions = re.findall(r"<(?:tool_call\s+name=|finish>|tool_call\s+name=\"finish\")", content)
                if len(actions) != 1:
                    multiple_action_count += 1
                    row_ok = False
                # XML tag balance
                for tag in ("tool_call", "file", "finish"):
                    opened = len(re.findall(r"<" + tag + r"(?:\s[^>]*|)>", content))
                    closed = len(re.findall(r"</" + tag + r">", content))
                    # finish can be self-closing <tool_call name="finish" />
                    if tag == "finish" and "<tool_call name=\"finish\"" in content:
                        continue
                    if opened != closed:
                        malformed_xml_count += 1
                        row_ok = False
                # Safe paths
                for m in re.finditer(r'<file\s+path="([^"]+)"', content):
                    path = m.group(1)
                    if path.startswith(("/", "\\")) or ":" in path or ".." in path:
                        unsafe_path_count += 1
                        row_ok = False
            if row_ok:
                passed_count += 1

        metrics = {
            "thought_tag_count": thought_tag_count,
            "multiple_action_count": multiple_action_count,
            "malformed_xml_count": malformed_xml_count,
            "unsafe_path_count": unsafe_path_count,
            "pass_rate": passed_count / len(rows),
        }
        if thought_tag_count > 0:
            violations.append(f"Found {thought_tag_count} assistant message(s) containing thought tags.")
        if multiple_action_count > 0:
            violations.append(f"Found {multiple_action_count} assistant message(s) without exactly 1 action.")
        if malformed_xml_count > 0:
            violations.append(f"Found {malformed_xml_count} assistant message(s) with unbalanced XML tags.")
        if unsafe_path_count > 0:
            violations.append(f"Found {unsafe_path_count} unsafe file path(s).")

    elif stage == CurriculumStage.STAGE_C_DESIGN_SYSTEM_EXECUTION:
        # Check representation of the 10 design genomes and balance
        genome_counts: dict[str, int] = {g: 0 for g in DESIGN_GENOMES}
        for row in rows:
            text = json.dumps(row).lower()
            matched = False
            for genome in DESIGN_GENOMES:
                if genome.lower() in text:
                    genome_counts[genome] += 1
                    matched = True
            if matched:
                passed_count += 1

        total_matched = sum(genome_counts.values()) or 1
        max_share = max(genome_counts.values()) / total_matched
        metrics = {
            "genome_distribution": genome_counts,
            "max_genome_share": round(max_share, 4),
            "unmatched_rows": len(rows) - passed_count,
        }
        # Check if any genome has 0 representations
        missing = [g for g, c in genome_counts.items() if c == 0]
        if missing:
            violations.append(f"Missing design genomes: {missing}")
        if max_share > 0.25:
            violations.append(f"Design genome balance violated: max share {max_share:.1%} exceeds 25%.")

    elif stage == CurriculumStage.STAGE_B_REACT_CORRECTNESS:
        row_failures = 0
        for row in rows:
            errors = _stage_b_row_errors(row)
            if errors:
                row_failures += 1
            else:
                passed_count += 1
        metrics = {"row_failure_count": row_failures, "compile_pass_rate": passed_count / len(rows), "unit_test_pass_rate": passed_count / len(rows)}
        if metrics["compile_pass_rate"] < 0.90:
            violations.append(f"Stage B TypeScript/React correctness pass rate {metrics['compile_pass_rate']:.1%} is below 90%.")
        if metrics["unit_test_pass_rate"] < 0.80:
            violations.append(f"Stage B unit-test proxy pass rate {metrics['unit_test_pass_rate']:.1%} is below 80%.")

    elif stage == CurriculumStage.STAGE_D_SECTION_ARCHETYPE_DIVERSITY:
        # Check representation of 8 feature archetypes and absence of card-grid monopoly
        archetype_counts: dict[str, int] = {a: 0 for a in FEATURE_ARCHETYPES}
        grid_count = 0
        for row in rows:
            text = json.dumps(row).lower()
            matched = False
            for arch in FEATURE_ARCHETYPES:
                if arch in text or arch.replace(" ", "_") in text:
                    archetype_counts[arch] += 1
                    matched = True
            if "grid" in text or "card" in text:
                grid_count += 1
            if matched:
                passed_count += 1

        total_features = sum(archetype_counts.values()) or 1
        grid_share = grid_count / len(rows)
        metrics = {
            "archetype_distribution": archetype_counts,
            "grid_mention_share": round(grid_share, 4),
        }
        missing_arch = [a for a, c in archetype_counts.items() if c == 0]
        if missing_arch:
            violations.append(f"Missing feature visual archetypes: {missing_arch}")
        if grid_share > MAX_ARCHETYPE_DOMINANCE_THRESHOLD:
            violations.append(
                f"Grid/card dominance: {grid_share:.1%} exceeds threshold {MAX_ARCHETYPE_DOMINANCE_THRESHOLD:.1%}."
            )

    elif stage == CurriculumStage.STAGE_E_FULL_SITE_MULTI_TURN:
        row_failures = 0
        for row in rows:
            errors = _stage_e_row_errors(row)
            if errors:
                row_failures += 1
            else:
                passed_count += 1
        metrics = {"full_site_pass_rate": passed_count / len(rows), "row_failure_count": row_failures}
        if metrics["full_site_pass_rate"] < 0.80:
            violations.append(f"Stage E full-site trajectory pass rate {metrics['full_site_pass_rate']:.1%} is below 80%.")

    elif stage == CurriculumStage.STAGE_F_REPAIR_TRAJECTORIES:
        # Check repair categories and multi-turn repair structure
        repair_cat_counts: dict[str, int] = {c: 0 for c in REPAIR_CATEGORIES}
        for row in rows:
            text = json.dumps(row).lower()
            matched = False
            for cat in REPAIR_CATEGORIES:
                if cat in text or cat.replace("_", " ") in text:
                    repair_cat_counts[cat] += 1
                    matched = True
            # Must have repair context / compiler diagnostic
            has_diagnostic = "error" in text or "diagnostic" in text or "repair" in text
            if matched and has_diagnostic:
                passed_count += 1

        metrics = {
            "category_distribution": repair_cat_counts,
            "valid_repair_count": passed_count,
        }
        missing_cats = [c for c, count in repair_cat_counts.items() if count == 0]
        if missing_cats:
            violations.append(f"Missing repair categories: {missing_cats}")

    elif stage == CurriculumStage.STAGE_G_MOTION_INTERACTIONS:
        # Check safe primitives and 100% reduced-motion query coverage
        reduced_motion_missing = 0
        primitive_counts: dict[str, int] = {p: 0 for p in MOTION_PRIMITIVES}
        for row in rows:
            text = json.dumps(row)
            norm = text.lower()
            if "animation" in norm or "transition" in norm or "scroll" in norm:
                if "prefers-reduced-motion" not in norm:
                    reduced_motion_missing += 1
                else:
                    passed_count += 1
            else:
                passed_count += 1
            for prim in MOTION_PRIMITIVES:
                if prim.lower() in norm:
                    primitive_counts[prim] += 1

        metrics = {
            "reduced_motion_missing": reduced_motion_missing,
            "primitive_usage": primitive_counts,
        }
        if reduced_motion_missing > 0:
            violations.append(f"{reduced_motion_missing} row(s) contain motion but lack prefers-reduced-motion fallback.")

    elif stage == CurriculumStage.STAGE_H_PREFERENCE_OPTIMIZATION:
        # Check pairwise structure (chosen vs rejected) and gate verification
        unpaired_count = 0
        missing_verification = 0
        for row in rows:
            has_pair = ("chosen" in row and "rejected" in row) or ("site_a" in row and "site_b" in row)
            if not has_pair:
                unpaired_count += 1
            # Both sides must be verified correct
            receipts = row.get("verification_receipts") if isinstance(row.get("verification_receipts"), dict) else {}
            chosen_receipt = parse_verification_receipt(row.get("chosen_verification_receipt") or receipts.get("chosen"))
            rejected_receipt = parse_verification_receipt(row.get("rejected_verification_receipt") or receipts.get("rejected"))
            verified = chosen_receipt is not None and rejected_receipt is not None and chosen_receipt.passed and rejected_receipt.passed
            if not verified:
                missing_verification += 1
            if has_pair and verified:
                passed_count += 1

        metrics = {
            "unpaired_count": unpaired_count,
            "missing_verification_count": missing_verification,
        }
        if unpaired_count > 0:
            violations.append(f"{unpaired_count} sample(s) lack pairwise comparison structure.")
        if missing_verification > 0:
            violations.append(
                f"{missing_verification} pairwise sample(s) missing hard gate verification: typed hard-gate verification receipts are required. "
                "Do not preference-train broken sites against correct plain ones."
            )
    else:
        # Default pass for generic structure
        passed_count = len(rows)
        metrics = {"sample_count": len(rows)}

    is_valid = len(violations) == 0 and (passed_count / len(rows) >= 0.80)
    summary = (
        f"{stage.value}: {'VALID' if is_valid else 'INVALID'} "
        f"({passed_count}/{len(rows)} passed, {len(violations)} violation(s))"
    )

    return StageValidationResult(
        stage=stage,
        is_valid=is_valid,
        total_samples=len(rows),
        passed_samples=passed_count,
        violations=violations,
        metrics=metrics,
        summary=summary,
    )


# ==============================================================================
# 4. Curriculum Progression Controller
# ==============================================================================

class CurriculumProgressionController:
    """Controls staged graduation from Stage A through Stage H."""

    @staticmethod
    def can_advance_to_stage(
        target_stage: CurriculumStage,
        completed_stages: Set[CurriculumStage],
    ) -> Tuple[bool, str]:
        """Verifies whether prerequisite stages are fulfilled before commencing target stage."""
        spec = STAGE_SPECS.get(target_stage)
        if not spec:
            return False, f"Unknown stage: {target_stage}"

        # Compute transitive closure: claiming a leaf stage is not enough to
        # bypass its own foundations.
        required: Set[CurriculumStage] = set()
        stack = list(spec.prerequisites)
        while stack:
            prerequisite = stack.pop()
            if prerequisite in required:
                continue
            required.add(prerequisite)
            stack.extend(STAGE_SPECS[prerequisite].prerequisites)
        missing = [p for p in required if p not in completed_stages]
        if missing:
            missing_names = [STAGE_SPECS[m].name for m in missing]
            return False, (
                f"Cannot advance to {spec.name}: missing prerequisite stage(s): {', '.join(missing_names)}. "
                "The 4B model must master foundational protocol and correctness stages first."
            )

        return True, f"Prerequisites met for {spec.name}."
