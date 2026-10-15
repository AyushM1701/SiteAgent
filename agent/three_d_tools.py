"""
agent/three_d_tools.py — First-Class 3D Diagnostic and Asset Tools (Issue #28).

Provides:
1. get_webgl_errors: Inspects WebGL context creation, shader compilation, context loss handlers, and runtime logs.
2. get_scene_metadata: Analyzes camera, lights, materials, particle counts, canvas DPR, frameloop, and useFrame allocations.
3. get_asset_manifest: Scans for 3D models (GLTF/GLB), textures, HDR environments, loader hooks, and Suspense fallbacks.
4. run_three_d_tool: Unified dispatcher for all 4 required 3D agent tools:
   - install_package
   - get_webgl_errors
   - get_scene_metadata
   - get_asset_manifest
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# Curated recipes give the planner an authored starting point instead of making
# the small model invent a complete scene lifecycle each time.
THREE_D_SCENE_RECIPES: Dict[str, Dict[str, Any]] = {
    "product_turntable": {"narrative": "product rotation", "mobile_fallback": "static product image"},
    "gradient_glass_orb": {"narrative": "material and light", "mobile_fallback": "CSS radial gradient"},
    "particle_field": {"narrative": "ambient depth", "mobile_fallback": "static gradient"},
    "architectural_wireframe": {"narrative": "structure and geometry", "mobile_fallback": "SVG outline"},
    "depth_card_constellation": {"narrative": "layered information", "mobile_fallback": "stacked cards"},
    "point_cloud_logo": {"narrative": "brand mark", "mobile_fallback": "brand SVG"},
    "shader_background": {"narrative": "ambient atmosphere", "mobile_fallback": "CSS gradient"},
    "data_terrain": {"narrative": "data landscape", "mobile_fallback": "static chart"},
}


def get_three_d_scene_recipes() -> Dict[str, Dict[str, Any]]:
    """Return immutable-friendly metadata for the planner and UI."""
    return {name: {**recipe, "constraints": {
        "max_dpr": 1.5,
        "request_animation_frame": True,
        "resize_observer_cleanup": True,
        "prefers_reduced_motion": True,
        "explicit_canvas_dimensions": True,
        "non_blocking_assets": True,
    }} for name, recipe in THREE_D_SCENE_RECIPES.items()}


def _extract_files_dict(workspace_dir_or_files: Union[Path, str, Dict[str, str]]) -> Dict[str, str]:
    """Normalizes input workspace directory or dictionary into {relative_path: content}."""
    if isinstance(workspace_dir_or_files, dict):
        return dict(workspace_dir_or_files)

    path_obj = Path(workspace_dir_or_files).resolve()
    files: Dict[str, str] = {}
    if path_obj.exists() and path_obj.is_dir():
        for p in path_obj.rglob("*"):
            if p.is_file() and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"]):
                rel = p.relative_to(path_obj).as_posix()
                try:
                    files[rel] = p.read_text(encoding="utf-8")
                except Exception:
                    pass
    elif path_obj.exists() and path_obj.is_file():
        files[path_obj.name] = path_obj.read_text(encoding="utf-8")
    return files


# ── 1. get_webgl_errors ───────────────────────────────────────────────────────

def get_webgl_errors(
    workspace_dir_or_files: Union[Path, str, Dict[str, str]],
    runtime_logs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Analyzes project files and runtime diagnostic logs for WebGL errors and failure modes.

    Validates:
    - WebGL context availability check and fallback UI
    - Shader compilation / syntax sanity
    - Unhandled context loss events (webglcontextlost)
    - Runtime WebGL error signatures in logs
    """
    files = _extract_files_dict(workspace_dir_or_files)
    combined = "\n".join(files.values())

    errors: List[str] = []
    warnings: List[str] = []

    # Check for runtime error signatures in logs
    if runtime_logs:
        for entry in runtime_logs:
            text = str(entry.get("text", entry.get("message", "")))
            if any(err in text for err in ["INVALID_OPERATION", "INVALID_VALUE", "OUT_OF_MEMORY"]):
                errors.append(f"Runtime WebGL error: {text.strip()}")
            elif "THREE.WebGLRenderer: Error compiling shader" in text:
                errors.append(f"Shader compilation error: {text.strip()}")
            elif "CONTEXT_LOST_WEBGL" in text or "webglcontextlost" in text:
                warnings.append(f"WebGL context loss event: {text.strip()}")

    # Check for WebGL presence
    has_canvas = ("<canvas" in combined.lower()) or ("<Canvas" in combined)
    has_three = ("@react-three/fiber" in combined) or ("three" in combined.lower()) or ("webgl" in combined.lower())
    has_shader = ("vertexshader" in combined.lower()) or ("fragmentshader" in combined.lower()) or ("shadermaterial" in combined.lower())

    if not has_canvas and not has_three and not has_shader:
        return {
            "has_errors": False,
            "errors": [],
            "warnings": ["No 3D canvas or WebGL components detected in project files."],
            "webgl_status": "inactive",
            "context_loss_handled": False,
            "has_fallback_ui": False,
            "details": {"has_canvas": False, "has_three": False},
        }

    # Context loss handling
    context_loss_handled = (
        ("webglcontextlost" in combined)
        or ("onContextLost" in combined)
        or ("onContextRestored" in combined)
        or ("WEBGL_lose_context" in combined)
    )
    if not context_loss_handled:
        warnings.append("No WebGL context loss listener (webglcontextlost/onContextLost) detected.")

    # Fallback UI check: WebGL availability probe or Suspense fallback
    has_probe = bool(re.search(r"getContext\(['\"](?:webgl|experimental-webgl|webgl2)['\"]\)", combined))
    has_fallback_element = (
        ("fallback" in combined.lower() and ("div" in combined.lower() or "span" in combined.lower()))
        or ("CSSFallback" in combined)
        or ("webglFailed" in combined)
        or ("webglAvailable" in combined)
    )
    has_fallback_ui = has_probe or has_fallback_element
    if not has_fallback_ui:
        warnings.append("No WebGL capability probe or CSS fallback UI found for non-WebGL devices.")

    # Raw Shader Material checks
    shader_match = re.findall(r"vertexShader\s*[:=]\s*[`'\"]([\s\S]*?)[`'\"]", combined)
    for s_code in shader_match:
        if "void main()" not in s_code:
            errors.append("Invalid vertexShader: missing 'void main()'.")

    frag_match = re.findall(r"fragmentShader\s*[:=]\s*[`'\"]([\s\S]*?)[`'\"]", combined)
    for f_code in frag_match:
        if "void main()" not in f_code:
            errors.append("Invalid fragmentShader: missing 'void main()'.")

    status = "error" if errors else ("warning" if warnings else "healthy")

    return {
        "has_errors": len(errors) > 0,
        "errors": errors,
        "warnings": warnings,
        "webgl_status": status,
        "context_loss_handled": context_loss_handled,
        "has_fallback_ui": has_fallback_ui,
        "details": {
            "has_canvas": has_canvas,
            "has_three": has_three,
            "has_probe": has_probe,
            "shader_count": len(shader_match) + len(frag_match),
        },
    }


# ── 2. get_scene_metadata ─────────────────────────────────────────────────────

def get_scene_metadata(workspace_dir_or_files: Union[Path, str, Dict[str, str]]) -> Dict[str, Any]:
    """
    Inspects 3D scene architecture, camera, lighting, DPR, particle systems, and useFrame allocations.
    """
    files = _extract_files_dict(workspace_dir_or_files)
    combined = "\n".join(files.values())

    # Camera metadata
    camera_info: Dict[str, Any] = {
        "type": "PerspectiveCamera",
        "fov": 50,
        "position": [0, 0, 5],
        "responsive": False,
    }
    fov_m = re.search(r"fov\s*:\s*(\d+)", combined)
    if fov_m:
        camera_info["fov"] = int(fov_m.group(1))

    pos_m = re.search(r"position\s*:\s*\[([0-9.,\s\-]+)\]", combined)
    if pos_m:
        try:
            parts = [float(p.strip()) for p in pos_m.group(1).split(",") if p.strip()]
            camera_info["position"] = parts
        except Exception:
            pass

    if "OrthographicCamera" in combined or "orthographic" in combined:
        camera_info["type"] = "OrthographicCamera"

    if (
        "viewport.width" in combined
        or ("useThree" in combined and ("width" in combined or "aspect" in combined))
        or "isMobile" in combined
    ):
        camera_info["responsive"] = True

    # Lights metadata
    ambient_count = len(re.findall(r"<ambientLight\b", combined))
    directional_count = len(re.findall(r"<directionalLight\b", combined))
    point_count = len(re.findall(r"<pointLight\b", combined))
    spot_count = len(re.findall(r"<spotLight\b", combined))
    hemi_count = len(re.findall(r"<hemisphereLight\b", combined))
    total_lights = ambient_count + directional_count + point_count + spot_count + hemi_count

    # Shadow check
    shadow_lights_count = len(re.findall(r"<(?:directionalLight|pointLight|spotLight)[^>]*\bcastShadow(?:\s*=\s*\{?\s*(?:true|1)\s*\}?)?", combined))
    has_shadows = bool(re.search(r"\bshadows\b|\bcastShadow\b", combined))

    # Canvas DPR & frameloop
    dpr_bounded = True
    dpr_val = [1, 1.5]
    dpr_match = re.search(r"dpr\s*=\s*\{([^}]+)\}", combined)
    if dpr_match:
        dpr_raw = dpr_match.group(1).strip()
        if "[" in dpr_raw and "]" in dpr_raw:
            nums = re.findall(r"[0-9.]+", dpr_raw)
            if nums:
                dpr_val = [float(x) for x in nums]
                if max(dpr_val) > 2.0:
                    dpr_bounded = False
        else:
            try:
                num = float(dpr_raw)
                dpr_val = [num]
                if num > 2.0:
                    dpr_bounded = False
            except Exception:
                if "devicePixelRatio" in dpr_raw and "min" not in dpr_raw.lower():
                    dpr_bounded = False

    frameloop = "always"
    frameloop_m = re.search(r'frameloop\s*=\s*["\']([^"\']+)["\']', combined)
    if frameloop_m:
        frameloop = frameloop_m.group(1)

    # useFrame & allocation leaks
    use_frame_calls = len(re.findall(r"\buseFrame\s*\(", combined))
    has_invalidate = "invalidate()" in combined or "invalidate" in combined

    # Check for allocations inside useFrame callbacks
    use_frame_leaks: List[str] = []
    for m in re.finditer(r"useFrame\s*\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>\s*\{([\s\S]*?)\}\s*\)", combined):
        body = m.group(1)
        if "new THREE.Vector3" in body:
            use_frame_leaks.append("new THREE.Vector3() allocated inside useFrame")
        if "new THREE.Color" in body:
            use_frame_leaks.append("new THREE.Color() allocated inside useFrame")
        if "new THREE.Matrix" in body:
            use_frame_leaks.append("new THREE.Matrix4() allocated inside useFrame")
        if re.search(r"\bnew\s+THREE\.[A-Za-z0-9]+\b", body):
            alloc_type = re.search(r"\bnew\s+(THREE\.[A-Za-z0-9]+)\b", body).group(1)
            if alloc_type not in ["THREE.Vector3", "THREE.Color", "THREE.Matrix4"]:
                use_frame_leaks.append(f"{alloc_type} allocated inside useFrame")

    # Particle systems
    has_particles = bool(re.search(r"<points\b", combined, re.IGNORECASE) or "THREE.Points" in combined)
    particle_count = 0
    bounded_particles = True
    p_count_m = re.search(r"(?:count|particles|pointsCount)\s*[:=]\s*\{?(\d+)\}?", combined)
    if p_count_m:
        particle_count = int(p_count_m.group(1))
        if particle_count > 5000:
            bounded_particles = False

    # Post-processing
    has_composer = ("<EffectComposer" in combined) or ("EffectComposer" in combined)
    post_passes: List[str] = []
    for p_name in ["Bloom", "DepthOfField", "ChromaticAberration", "Noise", "Vignette", "Glitch", "SSAO", "SSR"]:
        if f"<{p_name}" in combined or p_name in combined:
            post_passes.append(p_name)
    bounded_post = len(post_passes) <= 3

    performance_flags: List[str] = []
    if total_lights > 2:
        performance_flags.append(f"Excessive light count: {total_lights} lights (budget is <= 2)")
    if shadow_lights_count > 1:
        performance_flags.append(f"Too many shadow-casting lights: {shadow_lights_count}")
    if not dpr_bounded:
        performance_flags.append(f"Unbounded DPR detected: {dpr_val}")
    if use_frame_leaks:
        performance_flags.extend(use_frame_leaks)
    if not bounded_particles:
        performance_flags.append(f"Particle count exceeds safe bounds: {particle_count} > 5000")
    if not bounded_post:
        performance_flags.append(f"Too many heavy post-processing passes: {len(post_passes)}")

    return {
        "camera": camera_info,
        "lights": {
            "ambient": ambient_count,
            "directional": directional_count,
            "point": point_count,
            "spot": spot_count,
            "hemisphere": hemi_count,
            "total": total_lights,
            "shadow_casting": shadow_lights_count,
            "within_budget": total_lights <= 2 and shadow_lights_count <= 1,
        },
        "canvas": {
            "frameloop": frameloop,
            "dpr": dpr_val,
            "dpr_bounded": dpr_bounded,
            "has_shadows": has_shadows,
        },
        "animations": {
            "use_frame_count": use_frame_calls,
            "has_invalidate": has_invalidate,
            "use_frame_leaks": use_frame_leaks,
        },
        "particle_systems": {
            "has_particles": has_particles,
            "count": particle_count,
            "bounded": bounded_particles,
        },
        "post_processing": {
            "has_composer": has_composer,
            "passes": post_passes,
            "bounded": bounded_post,
        },
        "performance_flags": performance_flags,
    }


# ── 3. get_asset_manifest ─────────────────────────────────────────────────────

def get_asset_manifest(workspace_dir_or_files: Union[Path, str, Dict[str, str]]) -> Dict[str, Any]:
    """
    Scans for 3D model files, environment/texture assets, loader hooks, and Suspense fallback boundaries.
    """
    files = _extract_files_dict(workspace_dir_or_files)
    combined = "\n".join(files.values())

    models: List[Dict[str, Any]] = []
    textures: List[Dict[str, Any]] = []

    # 1. On-disk file assets
    for rel_path in files.keys():
        low = rel_path.lower()
        if low.endswith((".gltf", ".glb", ".obj", ".fbx")):
            models.append({"path": rel_path, "type": Path(rel_path).suffix.lstrip(".")})
        elif low.endswith((".hdr", ".exr", ".png", ".jpg", ".jpeg", ".webp")):
            if any(t_dir in low for t_dir in ["textures", "assets", "public", "models", "env"]):
                textures.append({"path": rel_path, "type": Path(rel_path).suffix.lstrip(".")})

    # 2. In-code loader references
    code_asset_refs: List[str] = []
    preload_hooks: List[str] = []

    # useGLTF, useTexture, useEnvironment calls
    for match in re.finditer(r'useGLTF\s*\(\s*["\']([^"\']+)["\']', combined):
        ref = match.group(1)
        code_asset_refs.append(ref)
        if not any(m["path"] == ref for m in models):
            models.append({"path": ref, "type": "gltf", "referenced_in_code": True})

    for match in re.finditer(r'useGLTF\.preload\s*\(\s*["\']([^"\']+)["\']', combined):
        preload_hooks.append(f"useGLTF.preload({match.group(1)})")

    for match in re.finditer(r'useTexture\s*\(\s*["\']([^"\']+)["\']', combined):
        ref = match.group(1)
        code_asset_refs.append(ref)
        if not any(t["path"] == ref for t in textures):
            textures.append({"path": ref, "type": "texture", "referenced_in_code": True})

    for match in re.finditer(r'useTexture\.preload\s*\(\s*["\']([^"\']+)["\']', combined):
        preload_hooks.append(f"useTexture.preload({match.group(1)})")

    for match in re.finditer(r'useEnvironment\s*\(\s*\{[^}]*files:\s*["\']([^"\']+)["\']', combined):
        ref = match.group(1)
        code_asset_refs.append(ref)
        textures.append({"path": ref, "type": "hdr", "referenced_in_code": True})

    # Suspense check
    has_suspense = (
        ("<Suspense" in combined)
        and ("fallback" in combined)
    )

    return {
        "models": models,
        "textures": textures,
        "code_asset_references": list(set(code_asset_refs)),
        "preload_hooks": preload_hooks,
        "has_suspense_boundaries": has_suspense,
        "total_assets_count": len(models) + len(textures),
    }


# ── 4. Unified Dispatcher ─────────────────────────────────────────────────────

def run_three_d_tool(
    action_name: str,
    workspace_dir_or_files: Union[Path, str, Dict[str, str]],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Unified entry point for all 4 agent 3D tools:
    - install_package
    - get_webgl_errors
    - get_scene_metadata
    - get_asset_manifest
    """
    payload = payload or {}

    if action_name == "install_package":
        pkg = payload.get("package") or payload.get("name")
        version = payload.get("version")
        is_dev = bool(payload.get("is_dev") or payload.get("dev", False))
        if not pkg:
            return {"success": False, "error": "Package name required for install_package"}

        # If workspace_dir is a Path/directory, execute DependencyManager
        if isinstance(workspace_dir_or_files, (Path, str)):
            ws_path = Path(workspace_dir_or_files).resolve()
            if ws_path.is_dir():
                try:
                    from agent.dependency_manager import DependencyManager
                    dm = DependencyManager(ws_path)
                    res = dm.install_package(pkg, version=version, is_dev=is_dev)
                    return res
                except Exception as e:
                    return {"success": False, "error": str(e)}
        # A dict of source files has no workspace on which installation can be
        # performed. Keep the legacy acknowledgement but make the unexecuted
        # state impossible to mistake for a real install.
        return {"success": True, "executed": False, "verified": False, "package": pkg, "version": version, "mock": True,
                "warning": "Package installation was not executed: provide a workspace directory."}

    elif action_name == "get_webgl_errors":
        logs = payload.get("runtime_logs")
        return get_webgl_errors(workspace_dir_or_files, runtime_logs=logs)

    elif action_name == "get_scene_metadata":
        return get_scene_metadata(workspace_dir_or_files)

    elif action_name == "get_asset_manifest":
        return get_asset_manifest(workspace_dir_or_files)

    else:
        raise ValueError(f"Unknown 3D tool action: '{action_name}'")
