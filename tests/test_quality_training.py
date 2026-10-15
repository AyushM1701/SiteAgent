from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.prepare_quality_training import make_windows, group_families
from agent.site_quality import prepare_site_quality, wants_dimensional_visual


def sample(task_id="one", prompt="Build the first section"):
    return {"task_id": task_id, "messages": [
        {"role": "system", "content": "Write complete code"},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "<tool_call>First implementation</tool_call>"},
        {"role": "user", "content": "<observation>Fix the button</observation>"},
        {"role": "assistant", "content": "<tool_call>Corrected implementation</tool_call>"},
    ]}


def test_windows_preserve_targets_and_feedback():
    row = sample()
    windows, rejected = make_windows(row, len, 2000)
    assert not rejected and len(windows) == 2
    assert [w["messages"][-1]["content"] for w in windows] == [row["messages"][2]["content"], row["messages"][4]["content"]]
    assert "Fix the button" in windows[1]["messages"][1]["content"]
    assert "First implementation" in windows[1]["messages"][1]["content"]
    assert all(sum(m["role"] == "assistant" for m in w["messages"]) == 1 for w in windows)


def test_oversize_target_is_rejected_not_truncated():
    windows, rejected = make_windows(sample(), len, 5)
    assert not windows and len(rejected) == 2


def test_related_trajectories_stay_in_one_family():
    rows = [sample("one"), sample("two")]
    assert len(set(group_families(rows))) == 1


def test_3d_assets_installed_only_when_requested(tmp_path):
    assert wants_dimensional_visual("a premium 3-d product site")
    instructions, files = prepare_site_quality("a 3D product site", tmp_path)
    assert set(files) == {"src/visuals/PremiumScene.tsx", "src/visuals/PremiumScene.css"}
    assert "../visuals/PremiumScene" in instructions
    assert all((tmp_path / name).read_text(encoding="utf-8") == content for name, content in files.items())
    _, ordinary_files = prepare_site_quality("a bakery site", tmp_path / "ordinary")
    assert not ordinary_files


def test_missing_screenshot_never_passes_visual_review(tmp_path, monkeypatch):
    from agent import visual_judge
    monkeypatch.setattr(visual_judge, "take_screenshot", lambda *args, **kwargs: None)
    result = visual_judge.score_visual(tmp_path)
    assert result["pass"] is False
    assert result["score"] == 0
