#!/usr/bin/env python3
"""
data_pipeline/gate_step2.py

Executes Step 2: Rigorous multi-gate filtering across all trajectories produced in Step 1.
Applies:
1. AntiDuplicationGate: extract_prose_ngrams, banned clichés, cross-domain n-grams, __ambient check.
2. PromptFidelityGate: verify_prompt_fidelity (named entities, quantities, fields).
3. VisualJudge & Motion Polish: evaluate_motion_polish, prefers-reduced-motion, visual threshold >= 3/5.

Logs all rejections with explicit reasons and outputs surviving trajectories to:
data/step2_gated_survivors.jsonl
data/step2_rejections.json
"""

import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))
sys.path.insert(0, str(BASE_DIR / "server"))
sys.path.insert(0, str(BASE_DIR / "data_pipeline"))

from anti_duplication_gate import AntiDuplicationGate, is_full_site_trajectory, extract_prose_ngrams
from prompt_fidelity_gate import verify_prompt_fidelity
import visual_judge

INPUT_FILES = [
    BASE_DIR / "data" / "site_trajectories_batch4.jsonl",
    BASE_DIR / "data" / "site_trajectories_batch5.jsonl",
    BASE_DIR / "data" / "site_star_trajectories.jsonl",
]

SURVIVORS_FILE = BASE_DIR / "data" / "step2_gated_survivors.jsonl"
REJECTIONS_FILE = BASE_DIR / "data" / "step2_rejections.json"
REJECTIONS_LOG = BASE_DIR / "data" / "step2_rejections.log"


def extract_files_from_trajectory(trajectory: dict) -> dict:
    """Extracts written files dict from assistant messages in trajectory."""
    files = {}
    for m in trajectory.get("messages", []):
        if m.get("role") == "assistant":
            content = m.get("content", "")
            matches = re.findall(r'<file path="([^"]+)">\s*(.*?)\s*</file>', content, re.DOTALL)
            for path, code in matches:
                files[path] = code
    return files


def run_gating():
    print("=" * 80)
    print("   STEP 2: RIGOROUS THREE-GATE SELECTIVITY & DUPLICATION AUDIT")
    print("=" * 80)

    # 1. Initialize Anti-Duplication Gate
    gate = AntiDuplicationGate(
        max_cross_domain_occurrences=2,
        min_ngram_size=7,
        min_css_declarations=4,
        strict_banned_phrases=True,
    )

    all_candidates = []
    for fpath in INPUT_FILES:
        if not fpath.exists():
            print(f"[Warning] Input file not found: {fpath}")
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    data["_source_file"] = fpath.name
                    all_candidates.append(data)
                except Exception as e:
                    print(f"[Error] Parsing JSON in {fpath.name}:{idx}: {e}")

    # Also load the raw STaR cases to capture the full prompt evaluations
    star_workspace = BASE_DIR / ".site_star_workspace"
    if star_workspace.exists():
        # Check for any rejected STaR cases in case directories
        for case_dir in sorted(star_workspace.glob("case_*")):
            # Check if this case was recorded
            pass

    total_candidates = len(all_candidates)
    print(f"Total Candidate Trajectories Ingested: {total_candidates}")

    survivors = []
    rejections = []

    counts_by_gate = {
        "anti_duplication": 0,
        "prompt_fidelity": 0,
        "visual_judge_and_motion": 0,
    }

    for idx, traj in enumerate(all_candidates, 1):
        task_id = traj.get("task_id", f"candidate_{idx:03d}")
        source_file = traj.get("_source_file", "unknown")
        arch = traj.get("layout_archetype", "unknown")

        # ── Gate 1: Anti-Duplication Gate ──────────────────────────────────────
        valid_dup, dup_violations = gate.check_trajectory(traj)
        if not valid_dup:
            counts_by_gate["anti_duplication"] += 1
            reason = dup_violations[0] if dup_violations else "Cross-domain n-gram duplication"
            rejections.append({
                "task_id": task_id,
                "source_file": source_file,
                "gate": "anti_duplication",
                "reason": reason,
                "layout_archetype": arch,
            })
            print(f"[{idx:03d}/{total_candidates}] [REJECT - DUP] {task_id}: {reason[:80]}")
            continue

        # ── Gate 2: Prompt-Fidelity Gate ───────────────────────────────────────
        files = extract_files_from_trajectory(traj)
        prompt_text = traj.get("prompt", "")
        if not prompt_text:
            for m in traj.get("messages", []):
                if m.get("role") == "user":
                    prompt_text = m.get("content", "")
                    break

        if prompt_text and files:
            valid_fid, fid_reasons, fid_metrics = verify_prompt_fidelity(prompt_text, files)
            if not valid_fid:
                counts_by_gate["prompt_fidelity"] += 1
                reason = fid_reasons[0] if fid_reasons else "Prompt fidelity entities/sections dropped"
                rejections.append({
                    "task_id": task_id,
                    "source_file": source_file,
                    "gate": "prompt_fidelity",
                    "reason": reason,
                    "layout_archetype": arch,
                })
                print(f"[{idx:03d}/{total_candidates}] [REJECT - FIDELITY] {task_id}: {reason[:80]}")
                continue

        # ── Gate 3: Visual Judge & Motion Polish Evaluator ─────────────────────
        if files:
            polish_res = visual_judge.evaluate_motion_polish(files, layout_archetype=arch)
            polish_score = polish_res.get("score", 5)
            polish_issues = polish_res.get("issues", [])

            # Check if trajectory contains code visual issues or missing reduced-motion
            if polish_score < 3:
                counts_by_gate["visual_judge_and_motion"] += 1
                reason = f"Motion polish score {polish_score}/5 below threshold 3/5: {', '.join(polish_issues)}"
                rejections.append({
                    "task_id": task_id,
                    "source_file": source_file,
                    "gate": "visual_judge_and_motion",
                    "reason": reason,
                    "layout_archetype": arch,
                })
                print(f"[{idx:03d}/{total_candidates}] [REJECT - MOTION/POLISH] {task_id}: {reason[:80]}")
                continue

            vis_ok, vis_res = visual_judge.filter_trajectory_visual(traj, threshold=3, exempt_single_components=True)
            if not vis_ok:
                counts_by_gate["visual_judge_and_motion"] += 1
                reason = f"Visual heuristic score {vis_res.get('score', 0)}/5 below 3/5: {vis_res.get('issues', [''])[0]}"
                rejections.append({
                    "task_id": task_id,
                    "source_file": source_file,
                    "gate": "visual_judge_and_motion",
                    "reason": reason,
                    "layout_archetype": arch,
                })
                print(f"[{idx:03d}/{total_candidates}] [REJECT - VISUAL] {task_id}: {reason[:80]}")
                continue

        # Passed all 3 gates! Register with anti-duplication gate to prevent intra-batch drift
        gate.register_trajectory(traj)
        survivors.append(traj)
        print(f"[{idx:03d}/{total_candidates}] [PASSED ALL 3 GATES] {task_id} (arch: {arch})")

    # ── Write Outputs ─────────────────────────────────────────────────────────
    with open(SURVIVORS_FILE, "w", encoding="utf-8") as f:
        for t in survivors:
            t_copy = dict(t)
            t_copy.pop("_source_file", None)
            f.write(json.dumps(t_copy) + "\n")

    with open(REJECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(rejections, f, indent=2)

    with open(REJECTIONS_LOG, "w", encoding="utf-8") as f:
        f.write(f"STEP 2 REJECTION AUDIT LOG\n")
        f.write(f"Total Candidates: {total_candidates}\n")
        f.write(f"Survivors: {len(survivors)}\n")
        f.write(f"Rejections: {len(rejections)}\n")
        f.write(f"Rejections by gate: {counts_by_gate}\n\n")
        for r in rejections:
            f.write(f"[{r['gate'].upper()}] {r['task_id']} ({r['layout_archetype']}) in {r['source_file']}: {r['reason']}\n")

    print("\n" + "=" * 80)
    print("                    STEP 2 GATING SUMMARY REPORT                       ")
    print("=" * 80)
    print(f"  • Total Candidates Ingested:        {total_candidates}")
    print(f"  • Survived All 3 Gates:              {len(survivors)} ({len(survivors)/total_candidates*100:.1f}%)")
    print(f"  • Total Rejections:                  {len(rejections)} ({len(rejections)/total_candidates*100:.1f}%)")
    print(f"    - Anti-Duplication Gate Rejects:   {counts_by_gate['anti_duplication']}")
    print(f"    - Prompt-Fidelity Gate Rejects:    {counts_by_gate['prompt_fidelity']}")
    print(f"    - Visual & Motion Polish Rejects:  {counts_by_gate['visual_judge_and_motion']}")
    print(f"  • Survivors Output Saved To:         {SURVIVORS_FILE}")
    print(f"  • Rejection Log Saved To:            {REJECTIONS_FILE} & {REJECTIONS_LOG}")
    print("=" * 80)


if __name__ == "__main__":
    run_gating()
