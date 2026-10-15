"""
data_pipeline/build_three_d_curriculum.py — 3D Training Curriculum Builder (Issue #28).

Covers all 13 canonical 3D generation curriculum topics:
1. Canvas
2. React Three Fiber
3. Drei
4. Suspense
5. GLTF loading
6. lighting
7. materials
8. shader basics
9. animation cleanup
10. responsive camera
11. device pixel ratio
12. reduced motion
13. fallback UI
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]

# Canonical 13 required topics per Issue #28
THREE_D_CURRICULUM_TOPICS: List[str] = [
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

# ─────────────────────────────────────────────────────────────────────────────
# 13 Structured Curriculum Lessons
# ─────────────────────────────────────────────────────────────────────────────

CURRICULUM_LESSONS: List[Dict[str, Any]] = [
    {
        "topic": "Canvas",
        "task_id": "three_d_canvas_setup",
        "title": "Configuring the R3F Canvas Container",
        "description": "Teaches proper Canvas setup, frameloop configuration, and full-bleed layout.",
        "user_prompt": "Create a Hero canvas with on-demand frameloop and correct container dimensions.",
        "key_concepts": ["frameloop='demand'", "gl={{ antialias: true }}", "fullscreen sizing", "tabIndex"],
        "component_code": (
            "import React from 'react';\n"
            "import { Canvas } from '@react-three/fiber';\n"
            "export function CanvasHero() {\n"
            "  return (\n"
            "    <div style={{ width: '100%', height: '100svh', position: 'relative' }}>\n"
            "      <Canvas frameloop='demand' dpr={[1, 1.5]} camera={{ position: [0, 0, 5], fov: 50 }}>\n"
            "        <ambientLight intensity={0.6} />\n"
            "        <mesh><boxGeometry /><meshStandardMaterial color='#6366f1' /></mesh>\n"
            "      </Canvas>\n"
            "    </div>\n"
            "  );\n"
            "}"
        ),
    },
    {
        "topic": "React Three Fiber",
        "task_id": "three_d_r3f_core",
        "title": "Declarative Scene Graph with R3F",
        "description": "Teaches scene graph hierarchies, meshes, groups, and useFrame updates.",
        "user_prompt": "Build an interactive 3D hierarchy with parent group rotation and child orbiting meshes.",
        "key_concepts": ["<group>", "<mesh>", "useFrame", "useThree", "invalidate"],
        "component_code": (
            "import React, { useRef } from 'react';\n"
            "import { useFrame, useThree } from '@react-three/fiber';\n"
            "import * as THREE from 'three';\n"
            "export function OrbitingGroup() {\n"
            "  const groupRef = useRef<THREE.Group>(null);\n"
            "  const { invalidate } = useThree();\n"
            "  useFrame((_state, delta) => {\n"
            "    if (groupRef.current) {\n"
            "      groupRef.current.rotation.y += delta * 0.4;\n"
            "      invalidate();\n"
            "    }\n"
            "  });\n"
            "  return (\n"
            "    <group ref={groupRef}>\n"
            "      <mesh position={[2, 0, 0]}><sphereGeometry args={[0.5, 32, 32]} /><meshStandardMaterial color='#22d3ee' /></mesh>\n"
            "    </group>\n"
            "  );\n"
            "}"
        ),
    },
    {
        "topic": "Drei",
        "task_id": "three_d_drei_helpers",
        "title": "Leveraging Drei Helpers",
        "description": "Teaches using OrbitControls, Float, Center, and Html overlays.",
        "user_prompt": "Create an interactive product showcase using Drei Float and OrbitControls with bounded rotation.",
        "key_concepts": ["Float", "OrbitControls", "enableZoom=false", "maxPolarAngle", "Center"],
        "component_code": (
            "import React from 'react';\n"
            "import { Float, OrbitControls, Center } from '@react-three/drei';\n"
            "export function FloatScene() {\n"
            "  return (\n"
            "    <>\n"
            "      <OrbitControls enableZoom={false} maxPolarAngle={Math.PI / 2} minPolarAngle={Math.PI / 4} />\n"
            "      <Center>\n"
            "        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>\n"
            "          <mesh><torusKnotGeometry args={[1, 0.3, 64, 16]} /><meshStandardMaterial color='#f59e0b' /></mesh>\n"
            "        </Float>\n"
            "      </Center>\n"
            "    </>\n"
            "  );\n"
            "}"
        ),
    },
    {
        "topic": "Suspense",
        "task_id": "three_d_suspense_boundaries",
        "title": "Asynchronous Scene Loading with React Suspense",
        "description": "Teaches wrapping async loaders in Suspense with DOM or HTML fallbacks.",
        "user_prompt": "Wrap complex 3D assets with Suspense and an accessible loading fallback indicator.",
        "key_concepts": ["<Suspense fallback={...}>", "Html center", "aria-busy", "smooth entrance"],
        "component_code": (
            "import React, { Suspense } from 'react';\n"
            "import { Html } from '@react-three/drei';\n"
            "function Loader() {\n"
            "  return <Html center><div className='p-2 bg-black/70 text-white rounded text-xs' role='status'>Loading 3D asset…</div></Html>;\n"
            "}\n"
            "export function SuspendedAsset({ children }: { children: React.ReactNode }) {\n"
            "  return <Suspense fallback={<Loader />}>{children}</Suspense>;\n"
            "}"
        ),
    },
    {
        "topic": "GLTF loading",
        "task_id": "three_d_gltf_loading",
        "title": "Loading and Preloading GLTF/GLB Models",
        "description": "Teaches useGLTF, preloading models, extracting nodes/materials, and clean unmounting.",
        "user_prompt": "Load a GLTF model using useGLTF with useGLTF.preload and render its cloned scene safely.",
        "key_concepts": ["useGLTF", "useGLTF.preload", "primitive object={scene.clone()}", "clean disposal"],
        "component_code": (
            "import React, { useMemo } from 'react';\n"
            "import { useGLTF } from '@react-three/drei';\n"
            "const MODEL_URL = '/models/sculpture.glb';\n"
            "export function Model() {\n"
            "  const { scene } = useGLTF(MODEL_URL);\n"
            "  const clone = useMemo(() => scene.clone(), [scene]);\n"
            "  return <primitive object={clone} scale={1.5} />;\n"
            "}\n"
            "useGLTF.preload(MODEL_URL);\n"
        ),
    },
    {
        "topic": "lighting",
        "task_id": "three_d_lighting_budget",
        "title": "Performant Studio Lighting and Shadows",
        "description": "Teaches balancing scene visibility with low draw calls and bounded lights (<= 2).",
        "user_prompt": "Set up balanced lighting with 1 ambientLight and 1 directionalLight without unnecessary shadow maps.",
        "key_concepts": ["ambientLight intensity={0.5}", "directionalLight castShadow={false}", "light budget <= 2"],
        "component_code": (
            "import React from 'react';\n"
            "export function StudioLighting() {\n"
            "  return (\n"
            "    <>\n"
            "      <ambientLight intensity={0.5} />\n"
            "      <directionalLight position={[5, 8, 4]} intensity={1.1} castShadow={false} />\n"
            "    </>\n"
            "  );\n"
            "}"
        ),
    },
    {
        "topic": "materials",
        "task_id": "three_d_materials_config",
        "title": "PBR Materials and Color Management",
        "description": "Teaches MeshStandardMaterial, roughness, metalness, and tone mapping.",
        "user_prompt": "Configure physically-based materials with metallic reflections and roughness contrast.",
        "key_concepts": ["meshStandardMaterial", "roughness", "metalness", "envMapIntensity", "color tokens"],
        "component_code": (
            "import React from 'react';\n"
            "export function PremiumMaterials() {\n"
            "  return (\n"
            "    <mesh>\n"
            "      <sphereGeometry args={[1, 32, 32]} />\n"
            "      <meshStandardMaterial color='#c4a882' roughness={0.25} metalness={0.8} />\n"
            "    </mesh>\n"
            "  );\n"
            "}"
        ),
    },
    {
        "topic": "shader basics",
        "task_id": "three_d_shader_basics",
        "title": "Custom Vertex and Fragment Shaders",
        "description": "Teaches custom GLSL shaders with uniforms, varying, time progression, and main() syntax.",
        "user_prompt": "Implement a custom wave shader using shaderMaterial with time and color uniforms.",
        "key_concepts": ["shaderMaterial", "uniforms: { uTime }", "vertexShader", "fragmentShader", "void main()"],
        "component_code": (
            "import React, { useRef } from 'react';\n"
            "import { shaderMaterial } from '@react-three/drei';\n"
            "import { extend, useFrame } from '@react-three/fiber';\n"
            "import * as THREE from 'three';\n"
            "const WaveMaterial = shaderMaterial(\n"
            "  { uTime: 0, uColor: new THREE.Color('#38bdf8') },\n"
            "  `varying vec2 vUv; void main() { vUv = uv; vec3 p = position; p.z += sin(p.x * 4.0 + uTime) * 0.2; gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }`,\n"
            "  `uniform vec3 uColor; varying vec2 vUv; void main() { gl_FragColor = vec4(uColor * (0.8 + 0.2 * vUv.y), 1.0); }`\n"
            ");\n"
            "extend({ WaveMaterial });\n"
        ),
    },
    {
        "topic": "animation cleanup",
        "task_id": "three_d_animation_cleanup",
        "title": "Animation Cleanup and Memory Leak Prevention",
        "description": "Teaches avoiding allocations inside useFrame, cancelling animation loops, and disposing geometries.",
        "user_prompt": "Ensure zero memory allocations inside useFrame and clean up on component unmount.",
        "key_concepts": ["pre-allocated refs", "no new inside useFrame", "geometry.dispose()", "cancelAnimationFrame"],
        "component_code": (
            "import React, { useRef, useEffect } from 'react';\n"
            "import { useFrame, useThree } from '@react-three/fiber';\n"
            "import * as THREE from 'three';\n"
            "const TEMP_VEC = new THREE.Vector3();\n"
            "export function CleanAnimation() {\n"
            "  const meshRef = useRef<THREE.Mesh>(null);\n"
            "  const { invalidate } = useThree();\n"
            "  useFrame((state, delta) => {\n"
            "    if (!meshRef.current) return;\n"
            "    TEMP_VEC.set(Math.sin(state.clock.elapsedTime), 0, 0);\n"
            "    meshRef.current.position.copy(TEMP_VEC);\n"
            "    invalidate();\n"
            "  });\n"
            "  return <mesh ref={meshRef}><boxGeometry args={[1, 1, 1]} /><meshBasicMaterial color='#10b981' /></mesh>;\n"
            "}"
        ),
    },
    {
        "topic": "responsive camera",
        "task_id": "three_d_responsive_camera",
        "title": "Viewport-Aware Responsive Camera Adjustments",
        "description": "Teaches dynamic FOV, viewport width adaptations, and mobile camera framing.",
        "user_prompt": "Adjust camera FOV and position dynamically based on viewport width to prevent mobile clipping.",
        "key_concepts": ["useThree((s) => s.viewport)", "aspect ratio", "mobile fov adjustment", "camera.updateProjectionMatrix"],
        "component_code": (
            "import React, { useEffect } from 'react';\n"
            "import { useThree } from '@react-three/fiber';\n"
            "export function ResponsiveCameraRig() {\n"
            "  const { camera, size } = useThree();\n"
            "  useEffect(() => {\n"
            "    const isNarrow = size.width < 768;\n"
            "    if ('fov' in camera) {\n"
            "      camera.fov = isNarrow ? 70 : 50;\n"
            "      camera.position.z = isNarrow ? 7 : 5;\n"
            "      camera.updateProjectionMatrix();\n"
            "    }\n"
            "  }, [size.width, camera]);\n"
            "  return null;\n"
            "}"
        ),
    },
    {
        "topic": "device pixel ratio",
        "task_id": "three_d_dpr_budget",
        "title": "Device Pixel Ratio (DPR) Clamping for High-DPI Displays",
        "description": "Teaches bounding DPR to [1, 1.5] or [1, 2] to prevent 4K GPU overdraw on laptops/phones.",
        "user_prompt": "Set Canvas DPR to a safe bounded array [1, 1.5] to prevent high-DPI GPU lag.",
        "key_concepts": ["dpr={[1, 1.5]}", "Math.min(window.devicePixelRatio, 2)", "GPU fillrate protection"],
        "component_code": (
            "import React from 'react';\n"
            "import { Canvas } from '@react-three/fiber';\n"
            "export function SafeDprCanvas({ children }: { children: React.ReactNode }) {\n"
            "  return (\n"
            "    <Canvas dpr={[1, 1.5]} frameloop='demand'>\n"
            "      {children}\n"
            "    </Canvas>\n"
            "  );\n"
            "}"
        ),
    },
    {
        "topic": "reduced motion",
        "task_id": "three_d_reduced_motion",
        "title": "Accessible prefers-reduced-motion Handling",
        "description": "Teaches querying prefers-reduced-motion media query and freezing or halting 3D rotations.",
        "user_prompt": "Pause 3D rotation and provide static camera framing when prefers-reduced-motion is active.",
        "key_concepts": ["matchMedia('(prefers-reduced-motion: reduce)')", "pause useFrame", "accessibility compliance"],
        "component_code": (
            "import React, { useState, useEffect } from 'react';\n"
            "export function usePrefersReducedMotion() {\n"
            "  const [reduced, setReduced] = useState(false);\n"
            "  useEffect(() => {\n"
            "    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');\n"
            "    setReduced(mq.matches);\n"
            "    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);\n"
            "    mq.addEventListener('change', handler);\n"
            "    return () => mq.removeEventListener('change', handler);\n"
            "  }, []);\n"
            "  return reduced;\n"
            "}"
        ),
    },
    {
        "topic": "fallback UI",
        "task_id": "three_d_fallback_ui",
        "title": "Graceful CSS and 2D Canvas Fallbacks for WebGL Failure",
        "description": "Teaches probing WebGL context support and rendering CSS gradient or image fallback when unsupported.",
        "user_prompt": "Probe WebGL support before mounting Canvas and display a CSS fallback UI if unavailable.",
        "key_concepts": ["canvas.getContext('webgl')", "CSS gradient orb", "no blank screen crash", "graceful degradation"],
        "component_code": (
            "import React, { useState, useEffect } from 'react';\n"
            "export function WebGLGate({ children, fallback }: { children: React.ReactNode; fallback: React.ReactNode }) {\n"
            "  const [supported, setSupported] = useState<boolean | null>(null);\n"
            "  useEffect(() => {\n"
            "    try {\n"
            "      const c = document.createElement('canvas');\n"
            "      const gl = c.getContext('webgl') || c.getContext('experimental-webgl');\n"
            "      setSupported(Boolean(gl));\n"
            "    } catch {\n"
            "      setSupported(false);\n"
            "    }\n"
            "  }, []);\n"
            "  if (supported === false) return <>{fallback}</>;\n"
            "  if (supported === null) return null;\n"
            "  return <>{children}</>;\n"
            "}"
        ),
    },
]


def verify_curriculum_coverage(lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verifies that all 13 canonical topics are covered in the curriculum."""
    covered_topics: Set[str] = {lesson["topic"] for lesson in lessons}
    missing = [t for t in THREE_D_CURRICULUM_TOPICS if t not in covered_topics]
    return {
        "all_covered": len(missing) == 0,
        "total_required": len(THREE_D_CURRICULUM_TOPICS),
        "total_covered": len(covered_topics),
        "missing_topics": missing,
        "covered_topics": sorted(list(covered_topics)),
    }


def build_three_d_curriculum() -> Dict[str, Any]:
    """Builds and exports the 3D curriculum JSONL and index metadata."""
    out_dir = ROOT / "data" / "r3f_trajectories"
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = out_dir / "three_d_curriculum.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for lesson in CURRICULUM_LESSONS:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")

    verification = verify_curriculum_coverage(CURRICULUM_LESSONS)

    index_data = {
        "version": "1.0.0",
        "total_lessons": len(CURRICULUM_LESSONS),
        "topics": THREE_D_CURRICULUM_TOPICS,
        "verification": verification,
        "lessons_summary": [
            {"topic": l["topic"], "task_id": l["task_id"], "title": l["title"]}
            for l in CURRICULUM_LESSONS
        ],
    }

    index_path = out_dir / "three_d_curriculum_index.json"
    index_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

    return {
        "jsonl_path": str(jsonl_path),
        "index_path": str(index_path),
        "verification": verification,
    }


if __name__ == "__main__":
    report = build_three_d_curriculum()
    print("3D Curriculum built successfully:")
    print(json.dumps(report, indent=2))
