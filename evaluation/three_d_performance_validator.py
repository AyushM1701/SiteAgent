"""
evaluation/three_d_performance_validator.py — 3D Runtime & Performance Validator (Issue #28).

Validates the 6 mandatory 3D performance checks:
1. no WebGL errors: checks context availability, shader syntax, and runtime diagnostic logs.
2. reasonable DPR: checks Canvas DPR is clamped (<= 2.0 or bounded array [1, 1.5]/[1, 2]).
3. bounded particle count: checks particle systems do not exceed safe 5,000 threshold without instancing.
4. no expensive unnecessary shadows: ensures <= 2 shadow-casting lights and shadow maps <= 2048.
5. no leaking useFrame allocations: checks for 'new THREE.*' or array allocations inside useFrame loops.
6. no unbounded post-processing: checks for excessive or stacked unmetered post-processing passes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

THREE_D_PERFORMANCE_CHECK_NAMES = [
    "no_webgl_errors",
    "reasonable_dpr",
    "bounded_particle_count",
    "no_expensive_unnecessary_shadows",
    "no_leaking_use_frame_allocations",
    "no_unbounded_post_processing",
]


def is_three_d_requested(brief: str) -> bool:
    return bool(re.search(r"\b(?:3d|webgl|three\.js|react three fiber|r3f|three-dimensional)\b", brief, re.I))


def validate_scene_contract(files: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Require an actual drawable scene; a canvas alone is never 3D evidence."""
    source = "\n".join(files.values())
    r3f_canvas = bool(re.search(r"<Canvas\b", source))
    drawable = bool(re.search(r"<(?:mesh|points|line|lineSegments|primitive|instancedMesh|skinnedMesh|sprite)\b", source))
    raw_scene = bool(re.search(r"new\s+(?:THREE\.)?Scene\s*\(", source))
    raw_renderer = bool(re.search(r"new\s+(?:THREE\.)?WebGLRenderer\s*\(", source))
    raw_drawable = bool(re.search(r"new\s+(?:THREE\.)?(?:Mesh|Points|Line|InstancedMesh)\s*\(", source))
    css_scene = bool(re.search(r"\bperspective\s*:", source, re.I)) and bool(
        re.search(r"preserve-3d", source, re.I)
    ) and bool(re.search(r"(?:rotate[XY]|translateZ)\s*\(", source, re.I))
    kind = "r3f" if r3f_canvas and drawable else "three_js" if raw_scene and raw_renderer and raw_drawable else "css_3d" if css_scene else None
    passed = kind is not None
    return passed, ("Drawable scene contract found." if passed else
                    "No drawable 3D scene found; an empty canvas or import is insufficient."), {
        "kind": kind, "r3f_canvas": r3f_canvas, "drawable": drawable,
        "raw_scene": raw_scene, "raw_renderer": raw_renderer, "css_scene": css_scene,
    }


def validate_no_webgl_errors(
    files: Dict[str, str],
    runtime_logs: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Check 1: Validate no WebGL errors, shader compilation failures, or unhandled context loss."""
    combined = "\n".join(files.values())
    errors: List[str] = []

    # Check runtime logs
    if runtime_logs:
        for log in runtime_logs:
            text = str(log.get("text", log.get("message", "")))
            if any(sig in text for sig in ["INVALID_OPERATION", "INVALID_VALUE", "OUT_OF_MEMORY"]):
                errors.append(f"Runtime WebGL error: {text}")
            elif "Error compiling shader" in text:
                errors.append(f"Shader error: {text}")
            elif "CONTEXT_LOST_WEBGL" in text:
                errors.append(f"Unhandled context lost: {text}")

    # Check raw shaders in source
    for match in re.finditer(r"(?:vertexShader|fragmentShader)\s*:\s*[`'\"]([\s\S]*?)[`'\"]", combined):
        code = match.group(1)
        if "void main()" not in code:
            errors.append("Invalid shader material: missing 'void main()'.")

    passed = len(errors) == 0
    reason = "No WebGL errors detected." if passed else f"WebGL errors found: {'; '.join(errors)}"
    return passed, reason, {"errors": errors}


def validate_reasonable_dpr(files: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Check 2: Validate Canvas DPR is bounded to prevent high-DPI GPU lag."""
    combined = "\n".join(files.values())
    dpr_matches = re.findall(r"dpr\s*=\s*\{([^}]+)\}", combined)

    if not dpr_matches:
        # Default R3F DPR is [1, 2] which is reasonable and safe
        return True, "Default or unspecified DPR is safe [1, 2].", {"dpr": "[1, 2]"}

    for raw in dpr_matches:
        raw_clean = raw.strip()
        # Check array notation [min, max]
        if "[" in raw_clean and "]" in raw_clean:
            nums = re.findall(r"[0-9.]+", raw_clean)
            if nums:
                max_dpr = max(float(x) for x in nums)
                if max_dpr > 2.0:
                    return False, f"DPR max ({max_dpr}) exceeds safe upper bound 2.0: {raw_clean}", {"dpr": raw_clean}
        else:
            # Check raw scalar
            try:
                val = float(raw_clean)
                if val > 2.0:
                    return False, f"Fixed DPR ({val}) exceeds safe upper bound 2.0.", {"dpr": raw_clean}
            except ValueError:
                if "devicePixelRatio" in raw_clean and "min" not in raw_clean.lower():
                    return False, f"Raw unmetered window.devicePixelRatio used without Math.min clamp: {raw_clean}", {"dpr": raw_clean}

    return True, "DPR configuration is safely bounded.", {"dpr": dpr_matches[0]}


def validate_bounded_particle_count(files: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Check 3: Validate particle counts are bounded (<= 5,000 without instancing)."""
    combined = "\n".join(files.values())
    has_particles = bool(re.search(r"<points\b", combined, re.IGNORECASE) or "THREE.Points" in combined)
    if not has_particles:
        return True, "No heavy particle systems present.", {"count": 0}

    # Search for count definitions
    counts = re.findall(r"(?:count|particles|pointsCount)\s*[:=]\s*\{?(\d+)\}?", combined)
    for c_str in counts:
        c = int(c_str)
        if c > 5000:
            return False, f"Particle count ({c}) exceeds safe 5,000 threshold without instancing.", {"count": c}

    # Search for Float32Array allocations
    arrays = re.findall(r"new\s+Float32Array\s*\(\s*(\d+)\s*\)", combined)
    for a_str in arrays:
        num = int(a_str)
        if num > 15000:  # 5000 vertices * 3 coords = 15000
            return False, f"Float32Array buffer size ({num}) exceeds safe particle budget.", {"buffer_size": num}

    return True, "Particle systems are properly bounded.", {"count": int(counts[0]) if counts else 0}


def validate_no_expensive_unnecessary_shadows(files: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Check 4: Validate maximum 1-2 shadow casting lights and reasonable shadow maps."""
    combined = "\n".join(files.values())

    # Count shadow-casting lights
    shadow_lights = re.findall(r"<(?:directionalLight|pointLight|spotLight)[^>]*\bcastShadow(?:\s*=\s*\{?\s*(?:true|1)\s*\}?)?", combined)
    if len(shadow_lights) > 2:
        return False, f"Too many shadow-casting lights ({len(shadow_lights)} > 2); causes severe overdraw.", {"shadow_lights": len(shadow_lights)}

    # Check for excessive shadow map resolution (> 2048)
    resolutions = re.findall(r"(?:shadow-mapSize-(?:width|height)|mapSize)\s*=\s*\{?(\d+)\}?", combined)
    for r_str in resolutions:
        r = int(r_str)
        if r > 2048:
            return False, f"Shadow map resolution ({r}) exceeds 2048px; high GPU memory footprint.", {"resolution": r}

    return True, "Shadow configuration is performant and within budget.", {"shadow_lights": len(shadow_lights)}


def validate_no_leaking_use_frame_allocations(files: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Check 5: Validate no object/vector allocations inside useFrame animation loop."""
    combined = "\n".join(files.values())
    leaking_allocations: List[str] = []

    # Find all useFrame callbacks
    for m in re.finditer(r"useFrame\s*\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>\s*\{([\s\S]*?)\}\s*\)", combined):
        body = m.group(1)
        # Search for object creations
        alloc_matches = re.findall(r"\bnew\s+(THREE\.[A-Za-z0-9]+|Array|Float32Array|Vector3|Color)\b", body)
        for alloc in alloc_matches:
            leaking_allocations.append(alloc)

    if leaking_allocations:
        return (
            False,
            f"Object allocations detected inside useFrame loop: {', '.join(set(leaking_allocations))}. Causes GC frame drops.",
            {"allocations": leaking_allocations},
        )

    return True, "useFrame hooks are clean without per-frame allocations.", {"allocations": []}


def validate_no_unbounded_post_processing(files: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Check 6: Validate post-processing passes are bounded and not excessively stacked."""
    combined = "\n".join(files.values())
    has_composer = ("<EffectComposer" in combined) or ("EffectComposer" in combined)
    if not has_composer:
        return True, "No post-processing overhead detected.", {"passes_count": 0}

    # Count passes
    known_passes = [
        "Bloom", "DepthOfField", "ChromaticAberration", "Noise",
        "Vignette", "Glitch", "SSAO", "SSR", "GodRays", "TiltShift"
    ]
    detected_passes = [p for p in known_passes if f"<{p}" in combined or p in combined]

    if len(detected_passes) > 3:
        return (
            False,
            f"Too many heavy post-processing passes stacked ({len(detected_passes)} > 3): {', '.join(detected_passes)}.",
            {"passes": detected_passes, "count": len(detected_passes)},
        )

    return True, "Post-processing pipeline is bounded and performant.", {"passes": detected_passes, "count": len(detected_passes)}


def validate_three_d_performance(
    files: Dict[str, str],
    runtime_logs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Runs all 6 performance checks and returns comprehensive report."""
    results: Dict[str, Dict[str, Any]] = {}
    failed_checks: List[str] = []

    check_functions = [
        ("no_webgl_errors", lambda: validate_no_webgl_errors(files, runtime_logs)),
        ("reasonable_dpr", lambda: validate_reasonable_dpr(files)),
        ("bounded_particle_count", lambda: validate_bounded_particle_count(files)),
        ("no_expensive_unnecessary_shadows", lambda: validate_no_expensive_unnecessary_shadows(files)),
        ("no_leaking_use_frame_allocations", lambda: validate_no_leaking_use_frame_allocations(files)),
        ("no_unbounded_post_processing", lambda: validate_no_unbounded_post_processing(files)),
    ]

    for name, fn in check_functions:
        passed, reason, details = fn()
        results[name] = {
            "passed": passed,
            "reason": reason,
            "details": details,
        }
        if not passed:
            failed_checks.append(name)

    scene_passed, scene_reason, scene_details = validate_scene_contract(files)
    if not scene_passed:
        failed_checks.append("scene_contract")
    all_passed = len(failed_checks) == 0
    passed_count = sum(result["passed"] for result in results.values())
    score = round(passed_count / len(check_functions), 4) if scene_passed else 0.0

    return {
        "all_passed": all_passed,
        "passed_count": passed_count,
        "total_checks": len(check_functions),
        "score": score,
        "checks": results,
        "scene_contract": {"passed": scene_passed, "reason": scene_reason, "details": scene_details},
        "failed_checks": failed_checks,
    }
