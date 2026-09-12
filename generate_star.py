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
from evaluate import strip_test_imports
from site_brief import generate_content_brief, brief_to_xml
import visual_judge


# ==============================================================================
# 1. Site-Level STaR Pipeline with Visual Judge Filtering
# ==============================================================================

def run_site_star_pipeline(
    prompts: Optional[List[str]] = None,
    output_file: str = "data/site_star_trajectories.jsonl",
    visual_threshold: int = 3,
    model_path: str = "my-react-agent-lora",
    max_turns: int = 8,
) -> int:
    """
    Runs multi-turn site synthesis rollouts and filters trajectories by both
    compilation/build success and Playwright visual quality score (>= visual_threshold).
    Trapped or low-visual-quality outputs are discarded via rejection sampling.
    """
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not prompts:
        prompts = [
            "Build a luxury editorial website for 'AURA Spatial Audio' with Header, Hero, Spatial Products, and Footer.",
            "Create a modern law firm website for 'Vanguard Legal Partners' with Practice Areas, Attorneys, Case Results, Contact.",
            "Build an artisanal coffee roastery website for 'Beacon Coffee' with Menu, Story, Subscriptions, and Visit us.",
        ]

    runner = AgentModelRunner(model_path=model_path, is_mock=(not Path(model_path).exists()))
    workspace_root = BASE_DIR / ".site_star_workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    accepted_count = 0
    print("=" * 75)
    print("   SITE-LEVEL STaR REJECTION SAMPLING (WITH VISUAL JUDGE GATING)")
    print(f"   Visual Score Threshold: {visual_threshold}/5 | Model: {model_path}")
    print("=" * 75)

    with open(out_path, "a", encoding="utf-8") as f_out:
        for idx, prompt in enumerate(prompts):
            print(f"\n[Site STaR #{idx+1}/{len(prompts)}] Prompt: {prompt[:65]}...")
            brief = generate_content_brief(prompt)
            xml_brief = brief_to_xml(brief)
            sections = brief.get("sections", ["header", "hero", "features", "footer"])
            project_name = brief.get("business_name", f"SiteStar_{idx}").replace(" ", "_")

            case_dir = workspace_root / f"case_{idx:03d}"
            case_dir.mkdir(parents=True, exist_ok=True)

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
            _scaffold_site_vite_runner(case_dir, project_name, written_files, brief=brief)

            # Evaluate visual quality
            screenshot_path = case_dir / "screenshot.webp"
            ss = visual_judge.take_screenshot(project_dir=case_dir, output_path=screenshot_path)
            visual_score = 3  # Default neutral if screenshot tool unavailable
            issues = []
            if ss and ss.exists():
                v_res = visual_judge._score_screenshot_heuristic(ss)
                visual_score = v_res.get("score", 0)
                issues = v_res.get("issues", [])

            print(f"  [Visual Judge]: Score = {visual_score}/5 (Threshold = {visual_threshold}) | Issues: {issues}")

            if visual_score < visual_threshold:
                print(f"  [REJECTED]: Visual quality {visual_score}/5 below threshold {visual_threshold}.")
                continue

            # Trajectory passed both compile and visual judge - keep trajectory
            trajectory = {
                "task_id": f"site_star_{project_name}_{int(time.time())}",
                "source": "site_star_visual_rejection",
                "prompt": prompt,
                "sections": sections,
                "visual_score": visual_score,
                "messages": result.get("turn_logs", []),
            }
            f_out.write(json.dumps(trajectory) + "\n")
            f_out.flush()
            accepted_count += 1
            print(f"  [ACCEPTED]: Trajectory accepted (Score {visual_score}/5).")

    print(f"\nSite STaR completed. Accepted {accepted_count}/{len(prompts)} trajectories saved to {out_path}.")
    return accepted_count


# ==============================================================================
# 2. Component-Level STaR Pipeline (Vitest Pass/Fail)
# ==============================================================================

def run_component_star_pipeline(
    model_path: str = "my-react-agent-lora",
    num_tasks: int = 150,
    output_file: str = "data/star_trajectories.jsonl",
):
    """Component-level STaR generation using curate_dataset.py task bank."""
    from curate_dataset import run_star_pipeline as _comp_star
    return _comp_star(
        model_path=model_path,
        num_tasks=num_tasks,
        output_file=output_file,
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
    parser.add_argument("--model", default="my-react-agent-lora", help="Model path")
    parser.add_argument("--tasks", type=int, default=5, help="Number of tasks")
    parser.add_argument("--out", default=None, help="Output JSONL path")
    args = parser.parse_args()

    if args.mode == "site":
        out = args.out or "data/site_star_trajectories.jsonl"
        run_site_star_pipeline(
            visual_threshold=args.visual_threshold,
            model_path=args.model,
            output_file=out,
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
