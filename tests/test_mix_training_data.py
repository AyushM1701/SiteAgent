"""
tests/test_mix_training_data.py - Verification for Item 15 Curriculum Mixing Script.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import pytest

from scripts.mix_training_data import (
    DEFAULT_MOTION_PATH,
    DEFAULT_REPLAY_PATH,
    detect_archetype,
    load_jsonl,
    mix_datasets,
    validate_trajectory_cleanliness,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_archetype_detection():
    assert detect_archetype("Build a split-screen two-column hero for SaaS") == "split_hero"
    assert detect_archetype("Editorial asymmetric monograph and magazine layout") == "editorial_asymmetric"
    assert detect_archetype("Immersive full-bleed hero visual section") == "immersive_visual"
    assert detect_archetype("Feature bento grid with metrics") == "bento_grid"
    assert detect_archetype("Acoustic device product showcase stage") == "product_stage"


def test_trajectory_cleanliness_check():
    clean_rec = {
        "messages": [
            {"role": "user", "content": "Build section"},
            {"role": "assistant", "content": "<tool_call name=\"write_site\"><file path=\"App.tsx\">code</file></tool_call>"},
        ]
    }
    is_clean, violations = validate_trajectory_cleanliness(clean_rec)
    assert is_clean
    assert len(violations) == 0

    dirty_rec = {
        "messages": [
            {"role": "user", "content": "Build section"},
            {"role": "assistant", "content": "<think>Forbidden reasoning</think><tool_call name=\"write_site\"><file path=\"App.tsx\">code</file></tool_call>"},
        ]
    }
    is_clean_dirty, violations_dirty = validate_trajectory_cleanliness(dirty_rec)
    assert not is_clean_dirty
    assert any("forbidden <think>/<thought>" in v for v in violations_dirty)


def test_mix_datasets_ratio():
    assert DEFAULT_MOTION_PATH.is_file(), f"Missing motion dataset: {DEFAULT_MOTION_PATH}"
    motion_recs = load_jsonl(DEFAULT_MOTION_PATH)
    assert len(motion_recs) == 36

    dummy_replays = [
        {
            "task_id": f"core_replay_{i}",
            "category": "core_component",
            "messages": [
                {"role": "user", "content": f"Build component {i}"},
                {"role": "assistant", "content": f"<tool_call name=\"write_site\"><file path=\"Comp_{i}.tsx\">code</file></tool_call>"},
            ],
        }
        for i in range(200)
    ]

    combined, stats = mix_datasets(
        motion_records=motion_recs,
        replay_records=dummy_replays,
        motion_ratio=0.15,
        seed=123,
    )

    assert stats["motion_records"] == 36
    assert abs(stats["actual_motion_ratio"] - 0.15) < 0.02
    assert stats["total_records"] == len(combined)
    assert len(stats["archetype_distribution"]) > 0


def test_cli_dry_run_execution():
    cmd = [sys.executable, str(ROOT_DIR / "scripts" / "mix_training_data.py"), "--dry-run"]
    proc = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    assert proc.returncode == 0, f"Command failed: {proc.stderr}"
    assert "CURRICULUM MIXING SUMMARY" in proc.stdout
    assert "Motion Trajectories:      36" in proc.stdout
