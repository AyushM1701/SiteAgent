#!/usr/bin/env python3
"""
generate_star.py - Self-Taught Reasoner (STaR) & Rejection Sampling Pipeline
Supports both:
1. Component-level STaR (Vitest pass/fail rejection sampling)
2. Site-level STaR with Visual Quality Gating (imports visual_judge to filter by visual quality)
"""

import argparse
import json
import os
os.environ["NO_AUTO_LOAD_MODEL"] = "1"
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
AGENT_DIR = BASE_DIR / "agent"
DATA_PIPELINE_DIR = BASE_DIR / "data_pipeline"
TRAINING_DIR = BASE_DIR / "training"

SERVER_DIR = BASE_DIR / "server"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(DATA_PIPELINE_DIR))
sys.path.insert(0, str(TRAINING_DIR))
sys.path.insert(0, str(SERVER_DIR))

# Mandatory imports per specification
from agent import (
    AgentModelRunner,
    run_agent_on_example,
    run_site_agent_on_example,
)
from app import _scaffold_site_vite_runner
from agent_protocol import (
    SITE_AGENT_SYSTEM_PROMPT,
    AGENT_SYSTEM_PROMPT,
    DEFAULT_MAX_SEQ_LENGTH,
)
from site_brief import generate_content_brief, brief_to_xml
from prompt_fidelity_gate import verify_prompt_fidelity
from anti_duplication_gate import AntiDuplicationGate
import visual_judge


# Real prompt matrix covering at minimum one prompt per archetype per domain tier:
# Trust-heavy: legal, finance, real-estate, healthcare
# Expressive: restaurant, travel, nonprofit, education
REAL_SITE_STAR_PROMPTS = [
    # Trust-heavy domain tier: legal, finance, real-estate, healthcare
    "Build a prestigious corporate litigation law firm website for 'Vanguard Legal Partners' featuring practice areas in a balanced multi-column grid, attorney profiles, landmark case results, and consultation booking. Layout archetype: grid.",
    "Build a private wealth management advisory website for 'Apex Wealth Advisors' featuring our client journey roadmap timeline with sequential milestones, investment process, portfolio tiers, and consultation scheduling. Layout archetype: timeline.",
    "Build a modern diagnostic clinic website for 'Beacon Health Diagnostics' featuring interactive tabbed clinical departments with tab switcher, physician schedules, diagnostic test catalog, and patient portal access. Layout archetype: tabs.",
    "Build an architectural luxury real estate website for 'Aura Premier Properties' featuring a split-hero 50/50 hero with interactive property visualizer on the right, curated portfolio listings, architect profiles, and private inquiries. Layout archetype: split_hero.",
    "Build an editorial legal journal and boutique litigation website for 'Blackstone & Sterling' featuring typography-first jurisprudence commentary, narrative editorial articles, landmark appellate archives, and senior counsel. Layout archetype: editorial.",
    "Build a quantitative asset management website for 'Stratum Capital Management' featuring a bento grid architecture with heterogeneous risk metrics, live fund performance analytics cards, portfolio strategy breakdown, and institutional contact. Layout archetype: bento.",

    # Expressive domain tier: restaurant, travel, nonprofit, education
    "Build an artisanal French culinary bistro website for 'L'Etoile French Bistro' featuring a seasonal dinner menu card grid with signature dishes, chef's tasting options, cellar pairings, and reservation booking. Layout archetype: grid.",
    "Build an arctic expedition travel website for 'Nordic Horizons Expeditions' featuring an expedition itinerary timeline with day-by-day route milestones, polar voyage schedule, gear checklist, and voyage reservations. Layout archetype: timeline.",
    "Build an academy of visual arts website for 'Atelier School of Visual Arts' featuring interactive tabbed curriculum tracks to switch between UI/UX, Typography, and Motion, tuition pricing toggle, faculty roster, and admissions. Layout archetype: tabs.",
    "Build a craft coffee roastery and cafe website for 'Roast & Revel Roasters' featuring a split-hero 50/50 hero with interactive coffee brew visualizer on the right, single-origin bean subscription, and cafe locator. Layout archetype: split_hero.",
    "Build a luxury travel magazine and retreat website for 'Terra Incognita Journeys' featuring editorial narrative travelogues, typography-dominant photo essays, curated sanctuary retreats, and bespoke expedition inquiries. Layout archetype: editorial.",
    "Build a marine conservation foundation website for 'TideGuard Ocean Sanctuary' featuring a bento grid architecture with marine telemetry metrics, reef restoration impact cards, interactive ocean sanctuary map, and recurring donation tiers. Layout archetype: bento.",
]


# ==============================================================================
# 1. Site-Level STaR Pipeline with Visual Judge Filtering
# ==============================================================================

def run_site_star_pipeline(
    prompts: Optional[List[str]] = None,
    output_file: str = "data/site_star_trajectories.jsonl",
    visual_threshold: int = 3,
    model_path: str = "models/qwen3-siteagent-motion-r16",
    max_turns: int = 8,
    is_mock: Optional[bool] = None,
) -> int:
    """
    Runs multi-turn site synthesis rollouts and filters trajectories by both
    compilation/build success and Playwright visual quality score (>= visual_threshold).
    Trapped or low-visual-quality outputs are discarded via rejection sampling.
    """
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not prompts:
        prompts = list(REAL_SITE_STAR_PROMPTS)

    mock_mode = bool(is_mock)
    if not mock_mode and not Path(model_path).exists():
        raise FileNotFoundError(f"STaR model not found: {model_path}; mock mode must be explicit")
    runner = AgentModelRunner(model_path=model_path, is_mock=mock_mode)
    workspace_root = BASE_DIR / ".site_star_workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    accepted_count = 0
    anti_dup_gate = AntiDuplicationGate(
        max_cross_domain_occurrences=2,
        min_ngram_size=7,
        min_css_declarations=4,
        strict_banned_phrases=True,
    )
    print("=" * 75)
    print("   SITE-LEVEL STaR REJECTION SAMPLING (WITH VISUAL JUDGE GATING)")
    print(f"   Visual Score Threshold: {visual_threshold}/5 | Model: {model_path} (mock={mock_mode})")
    print(f"   Prompts to process: {len(prompts)} across trust-heavy & expressive archetypes")
    print("=" * 75)

    with open(out_path, "w", encoding="utf-8") as f_out:
        for idx, prompt in enumerate(prompts):
            print(f"\n[Site STaR #{idx+1}/{len(prompts)}] Prompt: {prompt[:65]}...")
            brief = generate_content_brief(prompt)
            xml_brief = brief_to_xml(brief)
            sections = brief.get("sections", ["header", "hero", "features", "footer"])
            project_name = brief.get("business_name", f"SiteStar_{idx}").replace(" ", "_")

            case_dir = workspace_root / f"site_{idx:03d}"

            result = run_site_agent_on_example(
                orig_idx=idx,
                prompt=prompt,
                project_name=project_name,
                brief_xml=xml_brief,
                sections=sections,
                runner=runner,
                workspace_root=workspace_root,
                max_turns=max_turns,
                style_spec=brief.get("style_spec"),
                custom_section_instructions=brief.get("custom_section_instructions"),
            )

            if not result.get("final_passed"):
                print(f"  [REJECTED]: Compile or completion checks failed for {project_name}.")
                continue

            written_files = result.get("files", {})

            from agent.dependency_manager import ensure_runtime_packages
            dependency_errors = ensure_runtime_packages(written_files, BASE_DIR)
            if dependency_errors:
                print(f"  [REJECTED]: Dependency installation failed: {dependency_errors}")
                continue

            # Evaluate Prompt-Fidelity Gate: ensure named entities and counts are preserved
            fidelity_ok, f_reasons, f_metrics = verify_prompt_fidelity(prompt, written_files, brief=brief)
            print(f"  [Prompt Fidelity]: Passed = {fidelity_ok} (Score {f_metrics.get('fidelity_score', 1.0)}) | Issues: {f_reasons}")
            if not fidelity_ok:
                print(f"  [REJECTED]: Prompt fidelity failed for {project_name}: {', '.join(f_reasons)}")
                continue

            _scaffold_site_vite_runner(case_dir, project_name, written_files, brief=brief)

            from agent.project_validator import validate_project
            validation = validate_project(case_dir)
            if not validation.passed:
                print(f"  [REJECTED]: Full project validation failed: {validation.errors[:5]}")
                continue

            # Evaluate visual quality and code-level motion & polish
            screenshot_path = case_dir / "screenshot.webp"
            ss = visual_judge.take_screenshot(project_dir=case_dir, output_path=screenshot_path)
            base_v_score = 0
            issues = []
            if not ss or not ss.exists():
                print("  [REJECTED]: Screenshot unavailable; visual quality is unverified.")
                continue
            v_res = visual_judge._score_screenshot_heuristic(ss)
            base_v_score = v_res.get("score", 0)
            issues.extend(v_res.get("issues", []))

            # Code-level motion & polish quality gate
            layout_arch = brief.get("layout_archetype", "grid")
            polish_res = visual_judge.evaluate_motion_polish(written_files, layout_archetype=layout_arch)
            polish_score = polish_res.get("score", 5)
            polish_issues = polish_res.get("issues", [])
            for p_iss in polish_issues:
                if p_iss not in issues:
                    issues.append(p_iss)

            # Composite visual score: penalize if motion is missing for archetype
            if polish_score <= 2:
                visual_score = min(base_v_score, 2)
            elif polish_score == 3 and not polish_res.get("has_reduced_motion", True):
                visual_score = min(base_v_score, 3)
            else:
                visual_score = base_v_score

            print(f"  [Visual Judge]: Score = {visual_score}/5 (Visual: {base_v_score}, Polish: {polish_score}, Threshold = {visual_threshold}) | Issues: {issues}")

            if visual_score < visual_threshold or polish_score < visual_threshold:
                print(f"  [REJECTED]: Visual/motion quality ({visual_score}/5, polish: {polish_score}/5) below threshold {visual_threshold}: {issues}")
                continue

            # Trajectory candidate with full rehydrated code (not compacted stubs)
            raw_messages = result.get("trajectory") or result.get("turn_logs", [])
            hydrated_messages = []
            for msg in raw_messages:
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    for fpath, fcontent in written_files.items():
                        stub_pattern = re.compile(
                            rf'<file path="{re.escape(fpath)}">\s*/\* Section file accepted and saved to disk\. \*/\s*</file>',
                            re.DOTALL,
                        )
                        if stub_pattern.search(content):
                            content = stub_pattern.sub(f'<file path="{fpath}">\n{fcontent}\n</file>', content)
                    hydrated_messages.append({"role": "assistant", "content": content})
                else:
                    hydrated_messages.append(msg)

            trajectory = {
                "task_id": f"site_star_{project_name}_{int(time.time())}",
                "source": "site_star_visual_rejection",
                "provenance": "synthetic_mock" if mock_mode else "real_model",
                "is_mock": mock_mode,
                "prompt": prompt,
                "sections": sections,
                "layout_archetype": brief.get("layout_archetype", "grid"),
                "visual_score": visual_score,
                "polish_score": polish_score,
                "messages": hydrated_messages,
            }

            # Evaluate Anti-Duplication Gate
            dup_ok, dup_violations = anti_dup_gate.check_trajectory(trajectory)
            if not dup_ok:
                print(f"  [REJECTED]: Anti-duplication gate failed for {project_name}: {dup_violations[0]}")
                continue

            anti_dup_gate.register_trajectory(trajectory)
            f_out.write(json.dumps(trajectory) + "\n")
            f_out.flush()
            accepted_count += 1
            print(f"  [ACCEPTED]: Trajectory accepted (Visual {visual_score}/5, Fidelity OK, Gate OK).")

    print(f"\nSite STaR completed. Accepted {accepted_count}/{len(prompts)} trajectories saved to {out_path}.")
    return accepted_count


# ==============================================================================
# 2. Component-Level STaR Pipeline (Vitest Pass/Fail)
# ==============================================================================

def run_component_star_pipeline(
    model_path: str = "models/qwen3-siteagent-motion-r16",
    num_tasks: int = 150,
    output_file: str = "data/star_trajectories.jsonl",
    visual_threshold: int = 3,
    fidelity_check: bool = True,
):
    """Component-level STaR generation using curate_dataset.py task bank with fidelity and visual gating."""
    from curate_dataset import run_star_pipeline as _comp_star
    return _comp_star(
        model_path=model_path,
        num_tasks=num_tasks,
        output_file=output_file,
        visual_threshold=visual_threshold,
        fidelity_check=fidelity_check,
    )

# Canonical export alias
run_star_pipeline = run_component_star_pipeline


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="STaR Trajectory Generation with Visual Quality Gating")
    parser.add_argument("--mode", choices=["site", "component"], default="site", help="STaR mode")
    parser.add_argument("--visual-threshold", type=int, default=3, help="Minimum visual quality score (1-5)")
    parser.add_argument("--model", default="models/qwen3-siteagent-motion-r16", help="Model path")
    parser.add_argument("--tasks", type=int, default=5, help="Number of tasks")
    parser.add_argument("--out", default=None, help="Output JSONL path")
    parser.add_argument("--mock", action="store_true", help="Run with mock agent engine")
    parser.add_argument("--max-turns", type=int, default=8, help="Max turns per site rollout")
    args = parser.parse_args()

    if args.mode == "site":
        out = args.out or "data/site_star_trajectories.jsonl"
        run_site_star_pipeline(
            visual_threshold=args.visual_threshold,
            model_path=args.model,
            output_file=out,
            max_turns=args.max_turns,
            is_mock=True if args.mock else None,
        )
    else:
        out = args.out or "data/star_trajectories.jsonl"
        run_component_star_pipeline(
            model_path=args.model,
            num_tasks=args.tasks,
            output_file=out,
        )


if __name__ == "__main__":
    main()
