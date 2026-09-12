#!/usr/bin/env python3
"""
slm.py - Unified CLI for the React Agentic SLM Project
Provides a streamlined entry point for training, evaluation, generation, and dataset management.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SCRIPT_PATHS = {
    "train": BASE_DIR / "training" / "train_sft.py",
    "train-dpo": BASE_DIR / "training" / "train_dpo.py",
    "evaluate": BASE_DIR / "training" / "evaluate.py",
    "serve": BASE_DIR / "server" / "app.py",
    "agent": BASE_DIR / "agent" / "agent.py",
    "build_dataset": BASE_DIR / "data_pipeline" / "build_dataset.py",
    "curate_dataset": BASE_DIR / "data_pipeline" / "curate_dataset.py",
    "generate_trajectories": BASE_DIR / "data_pipeline" / "generate_trajectories.py",
    "star": BASE_DIR / "generate_star.py",
}


def run_script(script_path: Path, args: list):
    if not script_path.exists():
        print(f"Error: {script_path} not found.")
        sys.exit(1)

    cmd = [sys.executable, str(script_path)] + args
    try:
        subprocess.run(cmd, check=True, cwd=BASE_DIR)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="Unified CLI for the React Agent SLM Pipeline",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 1. Pipeline (End-to-End One-Command: Merge -> Validate -> Train)
    parser_pipe = subparsers.add_parser(
        "pipeline",
        help="One-command end-to-end pipeline: merge -> validate -> train SFT"
    )
    parser_pipe.add_argument(
        "--data", default=str(BASE_DIR / "data" / "training_data.jsonl"),
        help="Target training data path"
    )
    parser_pipe.add_argument(
        "--skip-validate", action="store_true",
        help="Skip the live Vitest/TSC validation step"
    )

    # 2. Train SFT
    subparsers.add_parser("train", help="Fine-tune the model with QLoRA SFT")

    # 3. Train DPO
    subparsers.add_parser("train-dpo", help="Direct Preference Optimization (DPO) fine-tuning")

    # 4. Evaluate
    subparsers.add_parser("evaluate", help="Run the test suite on the model")

    # 5. Generate
    parser_generate = subparsers.add_parser("generate", help="Generate or mine trajectories")
    parser_generate.add_argument(
        "mode",
        choices=["site", "teacher", "star", "typescript-instruct", "curate-sources", "stack"],
        help="Generation mode (site trajectories, teacher LLM, STaR, typescript-instruct, curate-sources, or stack)"
    )

    # 6. Dataset
    parser_dataset = subparsers.add_parser("dataset", help="Dataset tools")
    parser_dataset.add_argument(
        "action",
        choices=["merge", "validate", "build-star", "build-expanded", "merge-trajectories"],
        help="Dataset action"
    )

    # 7. Serve (Web UI)
    subparsers.add_parser("serve", help="Run the Flask Web UI workbench on localhost:5000")

    # 8. Agent
    subparsers.add_parser("agent", help="Run the autonomous agent loop manually")

    # If no args, print help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args, unknown_args = parser.parse_known_args()

    if args.command == "pipeline":
        data_path = Path(args.data)
        print("=" * 70)
        print("   REACTAGENT SLM: FULL AUTOMATED TRAINING PIPELINE           ")
        print("=" * 70)

        # Step 1: Merge all trajectory sources into master training dataset
        print("\n[Step 1/3] Merging all trajectory datasets into:", data_path)
        run_script(SCRIPT_PATHS["build_dataset"], ["merge", "--out", str(data_path)])

        # Step 2: Validate trajectories
        if not args.skip_validate:
            print("\n[Step 2/3] Validating trajectories with live tsc + Vitest...")
            run_script(SCRIPT_PATHS["build_dataset"], ["validate", str(data_path), "--verify-only"])
        else:
            print("\n[Step 2/3] Skipping validation as requested.")

        # Step 3: Train model
        print("\n[Step 3/3] Launching QLoRA SFT training...")
        train_args = ["--data", str(data_path)] + unknown_args
        run_script(SCRIPT_PATHS["train"], train_args)

    elif args.command == "train":
        run_script(SCRIPT_PATHS["train"], unknown_args)

    elif args.command == "train-dpo":
        run_script(SCRIPT_PATHS["train-dpo"], unknown_args)

    elif args.command == "evaluate":
        run_script(SCRIPT_PATHS["evaluate"], unknown_args)

    elif args.command == "generate":
        if args.mode == "site":
            run_script(SCRIPT_PATHS["generate_trajectories"], unknown_args)
        elif args.mode == "teacher":
            run_script(SCRIPT_PATHS["curate_dataset"], ["teacher"] + unknown_args)
        elif args.mode == "star":
            run_script(SCRIPT_PATHS["star"], unknown_args)
        elif args.mode == "typescript-instruct":
            run_script(SCRIPT_PATHS["curate_dataset"], ["typescript-instruct"] + unknown_args)
        elif args.mode == "curate-sources":
            run_script(SCRIPT_PATHS["curate_dataset"], ["curate-sources"] + unknown_args)
        elif args.mode == "stack":
            run_script(SCRIPT_PATHS["curate_dataset"], ["stack"] + unknown_args)

    elif args.command == "dataset":
        action = "merge" if args.action == "merge-trajectories" else args.action
        run_script(SCRIPT_PATHS["build_dataset"], [action] + unknown_args)

    elif args.command == "serve":
        run_script(SCRIPT_PATHS["serve"], unknown_args)

    elif args.command == "agent":
        run_script(SCRIPT_PATHS["agent"], unknown_args)


if __name__ == "__main__":
    main()
