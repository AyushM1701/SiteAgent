from pathlib import Path

from agent.site_requirements import build_requirement_manifest
from agent.project_validator import run_contract_check
from evaluation.human_visual_review import RUBRIC_AXES, validate_human_review
from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
from scripts import blinded_visual_review
import json
import csv
from training.train_sft import check_benchmark_disjointness


def test_manifest_preserves_supplied_facts_and_cart_contract():
    prompt = "Build an ecommerce website for North Goods. Products: Lamp at $29. Include: header, hero, features, footer. Add to cart."
    brief = {"business_name": "North Goods", "sections": ["header", "hero", "features", "footer"],
             "products": [{"name": "Lamp", "price": "$29"}], "motion_plan": []}
    manifest = build_requirement_manifest(prompt, brief)
    assert {"North Goods", "Lamp", "$29"}.issubset(manifest["exact_facts"])
    assert manifest["explicit_sections"] == ["header", "hero", "features", "footer"]
    assert "cart_state" in manifest["interactions"]
    assert manifest["cross_section_contracts"][0]["consumer"] == "shared cart indicator or panel"


def test_manifest_contract_rejects_missing_user_fact(tmp_path: Path):
    (tmp_path / "App.tsx").write_text("export default function App(){return <main><h1>Shop</h1></main>}", encoding="utf-8")
    (tmp_path / "content_brief.json").write_text(
        '{"requirement_manifest":{"exact_facts":["North Goods"],"routes":[],"explicit_sections":[]}}', encoding="utf-8"
    )
    passed, errors, _ = run_contract_check(tmp_path)
    assert not passed
    assert any("North Goods" in error for error in errors)


def test_human_review_cannot_be_fabricated_with_missing_evidence():
    report = {"review_type": "blinded_pairwise_human", "candidate_adapter_sha256": "abc",
              "site_reviews": [{"task_id": "one", "domain": "portfolio", "reviewer_id": "r1",
                                "candidate_label": "A", "pairwise_winner": "A", "rubric_scores": {}, "evidence": {}}]}
    errors = validate_human_review(report, "abc")
    assert any("at least 30" in error for error in errors)
    assert any("desktop screenshot file is missing" in error for error in errors)
    assert any("typography" in error for error in errors)
    assert any("two independent reviewers" in error for error in errors)


def test_human_review_requires_real_distinct_paired_captures(tmp_path: Path):
    axes = ("layout", "hierarchy", "typography", "content_specificity", "imagery_assets", "motion_timing", "mobile_composition")
    reviews = []
    for index in range(30):
        evidence = {}
        for label in ("A", "B"):
            evidence[label] = {}
            for mode in ("desktop", "mobile", "reduced_motion"):
                screenshot = tmp_path / f"{index}-{label}-{mode}.png"
                video = tmp_path / f"{index}-{label}-{mode}.webm"
                screenshot.write_bytes(f"image {index} {label} {mode}".encode())
                video.write_bytes(f"video {index} {label} {mode}".encode())
                evidence[label][mode] = {"screenshot": str(screenshot), "scroll_video": str(video)}
        for reviewer in ("reviewer-one", "reviewer-two"):
            reviews.append({"task_id": f"site-{index}", "domain": f"domain-{index % 12}",
                            "reviewer_id": reviewer, "candidate_label": "A", "pairwise_winner": "A",
                            "rubric_scores": {label: {axis: 3 for axis in axes} for label in ("A", "B")},
                            "evidence": evidence})
    report = {"review_type": "blinded_pairwise_human", "candidate_adapter_sha256": "adapter",
              "blinding_manifest_sha256": "a" * 64, "site_reviews": reviews}
    assert validate_human_review(report, "adapter") == []
    reviews[0]["evidence"]["B"]["desktop"]["screenshot"] = reviews[0]["evidence"]["A"]["desktop"]["screenshot"]
    assert any("reused" in error or "identical" in error for error in validate_human_review(report, "adapter"))


def test_reviewed_training_rows_require_provenance_and_family_separation():
    row = {"task_id": "one", "family_id": "same", "domain": "portfolio", "messages": []}
    errors = validate_reviewed_site_rows([row], [dict(row, task_id="two")])
    assert any("share family IDs" in error for error in errors)
    assert any("source and license" in error for error in errors)
    assert any("desktop screenshot" in error for error in errors)


def test_reviewed_training_rejects_changed_scored_evidence(tmp_path: Path):
    import hashlib

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    source = tmp_path / 'source'
    source.mkdir()
    component = source / 'Main.tsx'
    component.write_text('export default function Main(){return null}', encoding='utf-8')
    form = tmp_path / 'scores.csv'
    form.write_text('human review', encoding='utf-8')
    evidence = {}
    for mode in ('desktop', 'mobile', 'reduced_motion'):
        evidence[mode] = {}
        for kind in ('screenshot', 'scroll_video'):
            artifact = tmp_path / f'{mode}_{kind}.bin'
            artifact.write_bytes(f'{mode}/{kind}'.encode())
            evidence[mode][kind] = str(artifact)
            evidence[mode][kind + '_sha256'] = digest(artifact)
    row = {'task_id': 'site', 'family_id': 'family', 'domain': 'portfolio', 'source': str(source),
           'license': 'MIT', 'source_files': {'Main.tsx': digest(component)},
           'validation': {key: True for key in ('typecheck', 'build', 'runtime', 'interaction')},
           'visual_review': {'reviewer_id': 'reviewer', 'review_form': str(form),
                             'review_form_sha256': digest(form),
                             'rubric_scores': {axis: 4 for axis in RUBRIC_AXES}},
           'browser_evidence': evidence, 'category': 'full_site'}
    assert validate_reviewed_site_rows([row], []) == []
    component.write_text('changed after review', encoding='utf-8')
    assert any('source fingerprint mismatch' in error for error in validate_reviewed_site_rows([row], []))


def test_blinded_review_package_hides_model_identity(tmp_path: Path, monkeypatch):
    holdout = tmp_path / "holdout.jsonl"
    cases = [{"task_id": f"case-{i}", "domain": f"domain-{i % 12}", "prompt": f"Build site {i}"} for i in range(30)]
    holdout.write_text("".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8")
    monkeypatch.setattr(blinded_visual_review, "HOLDOUT", holdout)
    source = tmp_path / "source"
    for case in cases:
        for role in ("candidate", "baseline"):
            root = source / case["task_id"] / role
            root.mkdir(parents=True)
            captures = {}
            for mode in ("desktop", "mobile", "reduced_motion"):
                screenshot = root / f"{mode}.png"
                video = root / f"{mode}.webm"
                screenshot.write_bytes(f"{case['task_id']} {role} {mode} screenshot".encode())
                video.write_bytes(f"{case['task_id']} {role} {mode} video".encode())
                captures[mode] = {"screenshot": str(screenshot), "scroll_video": str(video)}
            (root / "evidence.json").write_text(json.dumps({"captures": captures}), encoding="utf-8")
    package = tmp_path / "public"
    private = tmp_path / "private.json"
    blinded_visual_review.prepare(source, package, private, ["r1", "r2"])
    assert private.is_file()
    assert len(list(package.glob("case-*/A/desktop_screenshot.png"))) == 30
    assert "candidate_label" not in (package / "cases.json").read_text(encoding="utf-8")
    assert len((package / "review_form_r1.csv").read_text(encoding="utf-8-sig").splitlines()) == 31
    mapping = json.loads(private.read_text(encoding="utf-8"))["cases"]
    forms = []
    for reviewer in ("r1", "r2"):
        form = package / f"review_form_{reviewer}.csv"
        with form.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows = list(reader)
        for row in rows:
            row["pairwise_winner"] = mapping[row["task_id"]]["candidate_label"]
            for key in fields:
                if key.startswith(("A_", "B_")):
                    row[key] = "3"
        with form.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        forms.append(form)
    report = tmp_path / "review_report.json"
    blinded_visual_review.assemble(package, private, "adapter-sha", forms, report)
    assert len(json.loads(report.read_text(encoding="utf-8"))["site_reviews"]) == 60


def test_visual_holdout_is_distinct_from_training():
    root = Path(__file__).resolve().parents[1]
    holdout = root / "data/eval/visual_holdout_v1.jsonl"
    train = root / "data/full_site_training/train.jsonl"
    cases = [json.loads(line) for line in holdout.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(cases) == len({row["task_id"] for row in cases}) == 30
    assert len({row["domain"] for row in cases}) == 12
    check_benchmark_disjointness(str(train), str(holdout))
