"""
tests/test_three_d_capability.py — Comprehensive Test Suite for Issue #28:
Treat 3D Generation as a First-Class Capability.

Verifies:
1. Project metadata (uses3D: true, threeLibrary: "@react-three/fiber") in Session and ContextBuilder.
2. 4 Agent tools (install_package, get_webgl_errors, get_scene_metadata, get_asset_manifest)
   parsing and execution.
3. Training curriculum covering all 13 canonical topics.
4. 6 Performance checks (no WebGL errors, reasonable DPR, bounded particle count,
   no expensive shadows, no leaking useFrame allocations, no unbounded post-processing).
5. Acceptance criteria: 3D sites evaluated separately from normal DOM sites in benchmark aggregation.
"""

import json
import tempfile
import time
from pathlib import Path
import pytest

from agent.agent_protocol import (
    GetAssetManifestAction,
    GetSceneMetadataAction,
    GetWebglErrorsAction,
    InstallPackageAction,
    parse_agent_output,
)
from agent.context_builder import ContextBuilder
from agent.three_d_tools import (
    get_asset_manifest,
    get_scene_metadata,
    get_webgl_errors,
    run_three_d_tool,
)
from data_pipeline.build_three_d_curriculum import (
    CURRICULUM_LESSONS,
    THREE_D_CURRICULUM_TOPICS,
    build_three_d_curriculum,
    verify_curriculum_coverage,
)
from evaluation.site_benchmark_scorer import (
    SiteBenchmarkScore,
    SiteBenchmarkScorer,
    aggregate_site_benchmark_scores,
)
from evaluation.three_d_performance_validator import (
    THREE_D_PERFORMANCE_CHECK_NAMES,
    validate_bounded_particle_count,
    validate_no_expensive_unnecessary_shadows,
    validate_no_leaking_use_frame_allocations,
    validate_no_unbounded_post_processing,
    validate_no_webgl_errors,
    validate_reasonable_dpr,
    validate_three_d_performance,
)
from server.sessions import Session, SessionManager


# ─────────────────────────────────────────────────────────────────────────────
# 1. Project Metadata
# ─────────────────────────────────────────────────────────────────────────────

def test_session_3d_project_metadata():
    """Verify uses3D and threeLibrary are stored, persisted, and serialized in Session."""
    sid = f"{int(time.time())}_abc123"
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(
            session_id=sid,
            title="3D Spatial Product",
            workspace_dir=tmp_dir,
            uses_3d=True,
            three_library="@react-three/fiber",
        )
        d = session.to_dict()
        assert d["uses_3d"] is True
        assert d["uses3D"] is True
        assert d["three_library"] == "@react-three/fiber"
        assert d["threeLibrary"] == "@react-three/fiber"


def test_context_builder_formats_3d_metadata():
    """Verify ContextBuilder injects 3D project metadata block into prompt context."""
    builder = ContextBuilder()
    session = type("MockSession", (), {
        "title": "3D Hero",
        "mode": "site",
        "uses_3d": True,
        "uses3D": True,
        "three_library": "@react-three/fiber",
        "style_tokens": None,
    })()

    all_files = {
        "package.json": json.dumps({"dependencies": {"@react-three/fiber": "^8.0.0", "three": "^0.150.0"}}),
        "src/components/Hero.tsx": "import { Canvas } from '@react-three/fiber';",
    }

    metadata_text = builder.format_project_metadata(session, all_files, max_tokens=500)
    assert "<project_metadata>" in metadata_text
    assert '"uses3D": true' in metadata_text
    assert '"threeLibrary": "@react-three/fiber"' in metadata_text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Agent Tools
# ─────────────────────────────────────────────────────────────────────────────

def test_protocol_parser_parses_all_3d_tools():
    """Verify agent protocol parses JSON and XML tool calls for all 4 tools."""
    # 1. install_package
    t1 = parse_agent_output('{"action": "install_package", "arguments": {"package": "@react-three/fiber"}}')
    assert isinstance(t1.action, InstallPackageAction)
    assert t1.action.package == "@react-three/fiber"

    t1_xml = parse_agent_output('<tool_call name="install_package">three</tool_call>')
    assert isinstance(t1_xml.action, InstallPackageAction)
    assert t1_xml.action.package == "three"

    # 2. get_webgl_errors
    t2 = parse_agent_output('{"action": "get_webgl_errors"}')
    assert isinstance(t2.action, GetWebglErrorsAction)

    t2_xml = parse_agent_output('<tool_call name="get_webgl_errors" />')
    assert isinstance(t2_xml.action, GetWebglErrorsAction)

    # 3. get_scene_metadata
    t3 = parse_agent_output('{"action": "get_scene_metadata"}')
    assert isinstance(t3.action, GetSceneMetadataAction)

    t3_xml = parse_agent_output('<tool_call name="get_scene_metadata" />')
    assert isinstance(t3_xml.action, GetSceneMetadataAction)

    # 4. get_asset_manifest
    t4 = parse_agent_output('{"action": "get_asset_manifest"}')
    assert isinstance(t4.action, GetAssetManifestAction)

    t4_xml = parse_agent_output('<tool_call name="get_asset_manifest" />')
    assert isinstance(t4_xml.action, GetAssetManifestAction)


def test_tool_get_webgl_errors():
    """Verify get_webgl_errors detects fallback UI and flags missing shader main."""
    # Healthy 3D code with fallback
    files_ok = {
        "src/Scene.tsx": (
            "import { Canvas } from '@react-three/fiber';\n"
            "const gl = canvas.getContext('webgl');\n"
            "export function Scene() { return gl ? <Canvas /> : <div className='CSSFallback' />; }"
        )
    }
    res_ok = get_webgl_errors(files_ok)
    assert res_ok["has_errors"] is False
    assert res_ok["has_fallback_ui"] is True

    # Bad shader code without void main()
    files_bad = {
        "src/Shader.tsx": "const vertexShader = 'vec3 p = position;';"
    }
    res_bad = get_webgl_errors(files_bad)
    assert res_bad["has_errors"] is True
    assert any("void main()" in err for err in res_bad["errors"])


def test_tool_get_scene_metadata():
    """Verify get_scene_metadata extracts camera, lights, DPR, and useFrame allocations."""
    files = {
        "src/Hero.tsx": (
            "import { Canvas, useFrame } from '@react-three/fiber';\n"
            "export function Hero() {\n"
            "  useFrame(() => { const v = new THREE.Vector3(1, 2, 3); });\n"
            "  return (\n"
            "    <Canvas dpr={[1, 1.5]} frameloop='demand' camera={{ position: [0, 2, 6], fov: 45 }}>\n"
            "      <ambientLight intensity={0.5} />\n"
            "      <directionalLight position={[2, 4, 1]} castShadow={false} />\n"
            "    </Canvas>\n"
            "  );\n"
            "}"
        )
    }
    meta = get_scene_metadata(files)
    assert meta["camera"]["fov"] == 45
    assert meta["camera"]["position"] == [0.0, 2.0, 6.0]
    assert meta["lights"]["total"] == 2
    assert meta["lights"]["within_budget"] is True
    assert meta["canvas"]["dpr_bounded"] is True
    assert meta["canvas"]["frameloop"] == "demand"
    assert len(meta["animations"]["use_frame_leaks"]) > 0


def test_tool_get_asset_manifest():
    """Verify get_asset_manifest identifies 3D models, textures, preload hooks, and Suspense."""
    files = {
        "public/models/watch.glb": "binary-content",
        "public/textures/env.hdr": "binary-content",
        "src/Model.tsx": (
            "import { Suspense } from 'react';\n"
            "import { useGLTF, useTexture } from '@react-three/drei';\n"
            "useGLTF.preload('/models/watch.glb');\n"
            "useTexture.preload('/textures/diffuse.png');\n"
            "export function Model() {\n"
            "  return <Suspense fallback={<div>Loading...</div>}><mesh /></Suspense>;\n"
            "}"
        )
    }
    manifest = get_asset_manifest(files)
    assert manifest["has_suspense_boundaries"] is True
    assert len(manifest["models"]) >= 1
    assert any("/models/watch.glb" in p for p in manifest["preload_hooks"])
    assert any("/textures/diffuse.png" in p for p in manifest["preload_hooks"])


def test_run_three_d_tool_dispatcher():
    """Verify unified dispatcher executes all 4 tools correctly."""
    files = {"src/Scene.tsx": "<Canvas dpr={[1, 1.5]}><ambientLight /></Canvas>"}
    r1 = run_three_d_tool("install_package", files, {"package": "@react-three/fiber"})
    assert r1.get("success") is True

    r2 = run_three_d_tool("get_webgl_errors", files)
    assert "webgl_status" in r2

    r3 = run_three_d_tool("get_scene_metadata", files)
    assert "camera" in r3

    r4 = run_three_d_tool("get_asset_manifest", files)
    assert "models" in r4


# ─────────────────────────────────────────────────────────────────────────────
# 3. Training Curriculum (13 Topics)
# ─────────────────────────────────────────────────────────────────────────────

def test_curriculum_coverage_all_13_topics():
    """Verify that all 13 canonical topics are present in the curriculum."""
    assert len(THREE_D_CURRICULUM_TOPICS) == 13
    expected_topics = [
        "Canvas",
        "React Three Fiber",
        "Drei",
        "Suspense",
        "GLTF loading",
        "lighting",
        "materials",
        "shader basics",
        "animation cleanup",
        "responsive camera",
        "device pixel ratio",
        "reduced motion",
        "fallback UI",
    ]
    assert sorted(THREE_D_CURRICULUM_TOPICS) == sorted(expected_topics)

    res = verify_curriculum_coverage(CURRICULUM_LESSONS)
    assert res["all_covered"] is True
    assert res["total_covered"] == 13
    assert len(res["missing_topics"]) == 0


def test_build_three_d_curriculum_exports_valid_files():
    """Verify curriculum builder writes out JSONL and JSON index files."""
    report = build_three_d_curriculum()
    assert report["verification"]["all_covered"] is True
    jsonl_p = Path(report["jsonl_path"])
    index_p = Path(report["index_path"])

    assert jsonl_p.exists()
    assert index_p.exists()

    lines = [json.loads(line) for line in jsonl_p.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 13


# ─────────────────────────────────────────────────────────────────────────────
# 4. Performance Checks (6 Rules)
# ─────────────────────────────────────────────────────────────────────────────

def test_performance_check_1_no_webgl_errors():
    """Verify rule 1: no WebGL errors."""
    clean_files = {"src/App.tsx": "const gl = canvas.getContext('webgl');"}
    passed, _, _ = validate_no_webgl_errors(clean_files)
    assert passed is True

    error_logs = [{"text": "WebGL: INVALID_OPERATION: drawElements: buffer not bound"}]
    passed, reason, _ = validate_no_webgl_errors(clean_files, runtime_logs=error_logs)
    assert passed is False
    assert "INVALID_OPERATION" in reason


def test_performance_check_2_reasonable_dpr():
    """Verify rule 2: reasonable DPR bounded <= 2.0."""
    # Pass: bounded array
    passed, _, _ = validate_reasonable_dpr({"src/App.tsx": "<Canvas dpr={[1, 1.5]} />"})
    assert passed is True

    # Fail: DPR max 3
    passed, reason, _ = validate_reasonable_dpr({"src/App.tsx": "<Canvas dpr={[1, 3]} />"})
    assert passed is False
    assert "upper bound" in reason

    # Fail: raw unmetered devicePixelRatio
    passed, reason, _ = validate_reasonable_dpr({"src/App.tsx": "<Canvas dpr={window.devicePixelRatio} />"})
    assert passed is False
    assert "unmetered" in reason


def test_performance_check_3_bounded_particle_count():
    """Verify rule 3: bounded particle count <= 5,000."""
    # Pass: 2000 particles
    passed, _, _ = validate_bounded_particle_count({"src/App.tsx": "<points count={2000} />"})
    assert passed is True

    # Fail: 50,000 particles
    passed, reason, _ = validate_bounded_particle_count({"src/App.tsx": "<Points count={50000} />"})
    assert passed is False
    assert "5,000" in reason


def test_performance_check_4_no_expensive_unnecessary_shadows():
    """Verify rule 4: maximum 1-2 shadow casting lights and shadow map <= 2048."""
    # Pass: 1 directional light with shadow
    passed, _, _ = validate_no_expensive_unnecessary_shadows({"src/App.tsx": "<directionalLight castShadow />"})
    assert passed is True

    # Fail: 4 lights casting shadows
    bad_code = (
        "<directionalLight castShadow />\n"
        "<pointLight castShadow />\n"
        "<spotLight castShadow />\n"
        "<pointLight castShadow />"
    )
    passed, reason, _ = validate_no_expensive_unnecessary_shadows({"src/App.tsx": bad_code})
    assert passed is False
    assert "Too many shadow-casting lights" in reason


def test_performance_check_5_no_leaking_use_frame_allocations():
    """Verify rule 5: zero allocations inside useFrame animation loops."""
    # Pass: mutating ref position
    good_code = "useFrame((_, delta) => { if (ref.current) ref.current.rotation.y += delta; });"
    passed, _, _ = validate_no_leaking_use_frame_allocations({"src/App.tsx": good_code})
    assert passed is True

    # Fail: new Vector3 inside useFrame
    bad_code = "useFrame(() => { const v = new THREE.Vector3(1, 0, 0); ref.current.position.add(v); });"
    passed, reason, _ = validate_no_leaking_use_frame_allocations({"src/App.tsx": bad_code})
    assert passed is False
    assert "allocations detected" in reason


def test_performance_check_6_no_unbounded_post_processing():
    """Verify rule 6: bounded post-processing passes (<= 3)."""
    # Pass: 2 passes
    good_code = "<EffectComposer><Bloom /><Vignette /></EffectComposer>"
    passed, _, _ = validate_no_unbounded_post_processing({"src/App.tsx": good_code})
    assert passed is True

    # Fail: 5 heavy passes stacked
    bad_code = "<EffectComposer><Bloom /><SSAO /><DepthOfField /><Glitch /><Noise /></EffectComposer>"
    passed, reason, _ = validate_no_unbounded_post_processing({"src/App.tsx": bad_code})
    assert passed is False
    assert "stacked" in reason


def test_aggregate_validate_three_d_performance():
    """Verify validate_three_d_performance executes all 6 checks together."""
    files = {
        "src/App.tsx": (
            "import { Canvas, useFrame } from '@react-three/fiber';\n"
            "export function App() {\n"
            "  useFrame((_, delta) => { if (mesh.current) mesh.current.rotation.y += delta; });\n"
            "  return (\n"
            "    <Canvas dpr={[1, 1.5]} frameloop='demand'>\n"
            "      <ambientLight intensity={0.5} />\n"
            "      <directionalLight position={[5, 5, 5]} castShadow={false} />\n"
            "      <points count={1000} />\n"
            "    </Canvas>\n"
            "  );\n"
            "}"
        )
    }
    report = validate_three_d_performance(files)
    assert report["all_passed"] is True
    assert report["score"] == 1.0
    assert len(report["checks"]) == 6
    for chk in THREE_D_PERFORMANCE_CHECK_NAMES:
        assert chk in report["checks"]
        assert report["checks"][chk]["passed"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 5. Acceptance Criteria: Separate 3D vs Normal DOM Sites Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def test_separate_evaluation_in_benchmark_scorer():
    """Verify 3D sites are scored with 3D checks and aggregated separately from DOM sites."""
    scorer = SiteBenchmarkScorer()

    # Normal DOM site
    dom_spec = {"task_id": "dom_site_1", "has_3d": False, "domain": "saas", "name": "CloudApp"}
    dom_files = {
        "src/App.tsx": "export function App() { return <div><h1>CloudApp</h1></div>; }",
        "src/components/Header.tsx": "export function Header() { return <header>Nav</header>; }",
    }
    score_dom = scorer.evaluate_site(dom_spec, dom_files)
    assert score_dom.is_3d_site is False

    # 3D site with performant R3F canvas
    three_spec = {"task_id": "three_site_1", "has_3d": True, "domain": "spatial", "name": "SpatialViewer"}
    three_files = {
        "src/App.tsx": (
            "import { Canvas, useFrame } from '@react-three/fiber';\n"
            "const gl = canvas.getContext('webgl');\n"
            "export function App() {\n"
            "  useFrame((_, d) => { if (ref.current) ref.current.rotation.y += d; });\n"
            "  return (\n"
            "    <Canvas dpr={[1, 1.5]} frameloop='demand'>\n"
            "      <ambientLight />\n"
            "      <directionalLight castShadow={false} />\n"
            "    </Canvas>\n"
            "  );\n"
            "}"
        ),
    }
    score_3d = scorer.evaluate_site(three_spec, three_files)
    assert score_3d.is_3d_site is True
    assert "no_webgl_errors" in score_3d.three_d_performance_checks

    # Aggregate both
    batch = [score_dom, score_3d]
    aggregate = aggregate_site_benchmark_scores(batch)

    # Acceptance criteria verification: separate summaries
    assert "dom_sites_summary" in aggregate
    assert "three_d_sites_summary" in aggregate

    dom_sum = aggregate["dom_sites_summary"]
    t3d_sum = aggregate["three_d_sites_summary"]

    assert dom_sum["total_sites"] == 1
    assert t3d_sum["total_sites"] == 1
    assert "three_d_performance_pass_rate" in t3d_sum
    assert "performance_checks_breakdown" in t3d_sum
    assert t3d_sum["three_d_performance_pass_rate"] == 1.0
