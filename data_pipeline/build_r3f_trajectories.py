"""Hand-authored R3F / Three.js training trajectory builder.

Design rules:
- Measured scene budgets (bounded DPR, minimal lights, lazy loading, offscreen pause)
- Reduced-motion and WebGL-unavailable fallbacks
- On-demand rendering (frameloop=demand + invalidate)
- Training trajectories for performance diagnosis and camera rigs

These are hand-authored DRAFT records. Each needs browser render verification
before promotion to the training mix via build_quality_v2.py.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.agent_protocol import SITE_AGENT_SYSTEM_PROMPT as SYS


# ─────────────────────────────────────────────────────────────────────────────
# Record 1: Floating Orb hero
# Teaches: Canvas setup, on-demand rendering, reduced-motion, WebGL fallback
# ─────────────────────────────────────────────────────────────────────────────
R1_USER = (
    "Write a React TypeScript component FloatingOrb.tsx + FloatingOrb.css:\n"
    "a hero section with a Three.js / React Three Fiber floating 3D orb.\n\n"
    "Requirements:\n"
    "- Canvas with frameloop=\"demand\" for on-demand rendering\n"
    "- DPR bounded to [1, 1.5] for laptop GPU safety\n"
    "- One ambient + one directional light only (2 max)\n"
    "- Animate rotation with useFrame; call invalidate() to self-sustain\n"
    "- prefers-reduced-motion: pause animation, show a static orb\n"
    "- WebGL unavailable: show CSS gradient circle fallback (no crash)\n"
    "- Skip link above canvas for screen readers\n"
    "- Warm ivory/copper MeshStandardMaterial, charcoal background, fullscreen height\n"
    "- Named export FloatingOrb"
)

R1_ASSISTANT = (
    "<thought>\n"
    "Key patterns to get right:\n"
    "1. frameloop=demand stops GPU overdraw when idle; invalidate() inside useFrame sustains animation.\n"
    "2. Detect prefers-reduced-motion in a React useEffect (not inside useFrame) to avoid stale closures.\n"
    "3. Probe WebGL availability before mounting Canvas — show CSS fallback on failure.\n"
    "4. Keep geometry segments to 32 and lights to 2; SphereGeometry at 128 costs 16x more vertices with no visible benefit at this scale.\n"
    "5. Export as named export, not default, so tree-shaking and fast refresh work correctly.\n"
    "</thought>\n"
    "<tool_call name=\"write_site\">\n"
    "<file path=\"src/components/FloatingOrb.tsx\">\n"
    "import React, { useRef, useEffect, Suspense, useState } from 'react';\n"
    "import { Canvas, useFrame, useThree } from '@react-three/fiber';\n"
    "import * as THREE from 'three';\n"
    "import './FloatingOrb.css';\n\n"
    "function OrbMesh({ paused }: { paused: boolean }) {\n"
    "  const meshRef = useRef<THREE.Mesh>(null);\n"
    "  const { invalidate } = useThree();\n"
    "  useFrame((_state, delta) => {\n"
    "    if (paused || !meshRef.current) return;\n"
    "    meshRef.current.rotation.x += delta * 0.18;\n"
    "    meshRef.current.rotation.y += delta * 0.28;\n"
    "    invalidate();\n"
    "  });\n"
    "  return (\n"
    "    <mesh ref={meshRef}>\n"
    "      <sphereGeometry args={[1.6, 32, 32]} />\n"
    "      <meshStandardMaterial color=\"#c4a882\" roughness={0.35} metalness={0.55} />\n"
    "    </mesh>\n"
    "  );\n"
    "}\n\n"
    "function CSSFallback() {\n"
    "  return (\n"
    "    <div className=\"fo-fallback\" aria-hidden=\"true\">\n"
    "      <div className=\"fo-orb\" />\n"
    "    </div>\n"
    "  );\n"
    "}\n\n"
    "export function FloatingOrb() {\n"
    "  const [prefersReduced, setPrefersReduced] = useState(false);\n"
    "  const [webglFailed, setWebglFailed] = useState(false);\n\n"
    "  useEffect(() => {\n"
    "    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');\n"
    "    setPrefersReduced(mq.matches);\n"
    "    const h = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);\n"
    "    mq.addEventListener('change', h);\n"
    "    return () => mq.removeEventListener('change', h);\n"
    "  }, []);\n\n"
    "  useEffect(() => {\n"
    "    try {\n"
    "      const c = document.createElement('canvas');\n"
    "      if (!c.getContext('webgl') && !c.getContext('experimental-webgl')) setWebglFailed(true);\n"
    "    } catch { setWebglFailed(true); }\n"
    "  }, []);\n\n"
    "  return (\n"
    "    <section className=\"fo-hero\" aria-label=\"Floating orb hero\">\n"
    "      <a className=\"fo-skip\" href=\"#fo-content\">Skip 3D animation</a>\n"
    "      {webglFailed ? <CSSFallback /> : (\n"
    "        <Canvas className=\"fo-canvas\" frameloop=\"demand\" dpr={[1, 1.5]}\n"
    "          camera={{ position: [0, 0, 5], fov: 50 }} aria-hidden=\"true\">\n"
    "          <ambientLight intensity={0.55} />\n"
    "          <directionalLight position={[4, 6, 3]} intensity={1.1} castShadow={false} />\n"
    "          <Suspense fallback={null}><OrbMesh paused={prefersReduced} /></Suspense>\n"
    "        </Canvas>\n"
    "      )}\n"
    "      <div id=\"fo-content\" className=\"fo-content\">\n"
    "        <h1 className=\"fo-headline\">Form in<br /><span className=\"fo-accent\">motion.</span></h1>\n"
    "        <p className=\"fo-sub\">A spatial product story built with depth and purposeful motion.</p>\n"
    "      </div>\n"
    "    </section>\n"
    "  );\n"
    "}\n"
    "</file>\n"
    "<file path=\"src/components/FloatingOrb.css\">\n"
    ".fo-hero{position:relative;width:100%;height:100svh;min-height:600px;background:#141618;overflow:hidden;display:flex;align-items:center;justify-content:center}\n"
    ".fo-skip{position:absolute;left:16px;top:-100px;z-index:20;background:#f0ebe3;color:#141618;padding:10px 16px;font-size:.875rem;font-weight:600;border-radius:6px;text-decoration:none}\n"
    ".fo-skip:focus{top:16px}\n"
    ".fo-canvas{position:absolute !important;inset:0;width:100% !important;height:100% !important}\n"
    ".fo-fallback{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none}\n"
    ".fo-orb{width:300px;height:300px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#e8d5b7 0%,#c4a882 40%,#92613f 75%,#2a1f14 100%);box-shadow:0 0 80px rgba(196,168,130,.2)}\n"
    ".fo-content{position:relative;z-index:10;text-align:center;pointer-events:none}\n"
    ".fo-headline{font-family:'Inter',system-ui,sans-serif;font-size:clamp(48px,7vw,96px);font-weight:600;line-height:1;letter-spacing:-.05em;color:#f0ebe3;margin:0 0 20px}\n"
    ".fo-accent{color:#c4a882}\n"
    ".fo-sub{font-size:clamp(14px,1.5vw,18px);color:rgba(240,235,227,.6);max-width:360px;margin:0 auto;line-height:1.7}\n"
    "@media(prefers-reduced-motion:reduce){.fo-canvas{opacity:0;pointer-events:none}}\n"
    "@media(max-width:640px){.fo-headline{font-size:44px}.fo-orb{width:220px;height:220px}}\n"
    "</file>\n"
    "</tool_call>"
)

# ─────────────────────────────────────────────────────────────────────────────
# Record 2: Performance diagnosis and fix
# Teaches: identifying DPR abuse, always-on frameloop, excess lights, vertex waste
# ─────────────────────────────────────────────────────────────────────────────
R2_USER = (
    "The following R3F scene is lagging on a laptop GPU.\n"
    "Diagnose every performance issue and fix them. Keep the same visual result: a slowly rotating blue sphere.\n\n"
    "// BEFORE\n"
    "import { Canvas, useFrame } from '@react-three/fiber';\n"
    "import { useRef } from 'react';\n"
    "function Sphere() {\n"
    "  const ref = useRef();\n"
    "  useFrame(() => { if (ref.current) ref.current.rotation.y += 0.01; });\n"
    "  return <mesh ref={ref}><sphereGeometry args={[1, 128, 128]} /><meshStandardMaterial color='royalblue' /></mesh>;\n"
    "}\n"
    "export default function LaggyScene() {\n"
    "  return (\n"
    "    <Canvas dpr={[1, 3]}>\n"
    "      <ambientLight intensity={1} /><pointLight position={[0,5,0]} intensity={2} />\n"
    "      <pointLight position={[5,0,0]} intensity={2} /><pointLight position={[-5,0,0]} intensity={2} />\n"
    "      <directionalLight position={[0,10,10]} intensity={2} /><spotLight position={[0,10,0]} intensity={3} />\n"
    "      <Sphere />\n"
    "    </Canvas>\n"
    "  );\n"
    "}"
)

R2_ASSISTANT = (
    "<thought>\n"
    "Five distinct performance bugs:\n"
    "1. dpr max=3: renders a 4K canvas on a laptop GPU. Fix: cap to [1, 1.5].\n"
    "2. frameloop defaults to 'always': GPU redraws at 60fps even when idle. Fix: frameloop=demand + invalidate().\n"
    "3. 5 lights (ambient + 4 point/spot/directional): massive specular overdraw. Fix: 2 lights max.\n"
    "4. sphereGeometry 128x128 = 16,384 vertices. At this scale 32x32 is visually identical. Fix: 32x32 (97% fewer vertices).\n"
    "5. castShadow not disabled: shadow maps computed by default. Fix: castShadow={false} on all lights.\n"
    "Bonus: useFrame delta-based rotation makes animation frame-rate independent.\n"
    "</thought>\n"
    "<tool_call name=\"write_site\">\n"
    "<file path=\"src/components/FixedScene.tsx\">\n"
    "// AFTER — five performance issues fixed, comments explain each change\n"
    "import { Canvas, useFrame, useThree } from '@react-three/fiber';\n"
    "import { useRef } from 'react';\n"
    "import * as THREE from 'three';\n"
    "import './FixedScene.css';\n\n"
    "function Sphere() {\n"
    "  const ref = useRef<THREE.Mesh>(null);\n"
    "  const { invalidate } = useThree(); // fix 2: demand rendering\n"
    "  useFrame((_s, delta) => {\n"
    "    if (!ref.current) return;\n"
    "    ref.current.rotation.y += delta * 0.6; // delta-based: frame-rate independent\n"
    "    invalidate();\n"
    "  });\n"
    "  return (\n"
    "    <mesh ref={ref}>\n"
    "      <sphereGeometry args={[1, 32, 32]} />{/* fix 4: 32x32 not 128x128 */}\n"
    "      <meshStandardMaterial color=\"#4a7ab5\" roughness={0.4} metalness={0.2} />\n"
    "    </mesh>\n"
    "  );\n"
    "}\n\n"
    "export default function FixedScene() {\n"
    "  return (\n"
    "    <div className=\"fs-wrap\">\n"
    "      <Canvas\n"
    "        frameloop=\"demand\"{/* fix 2 */}\n"
    "        dpr={[1, 1.5]}{/* fix 1: no 4K canvas */}\n"
    "        camera={{ position: [0, 0, 4], fov: 50 }}\n"
    "        aria-hidden=\"true\"\n"
    "      >\n"
    "        <color attach=\"background\" args={['#1a1c20']} />\n"
    "        <ambientLight intensity={0.6} />{/* fix 3+5: 2 lights, no shadows */}\n"
    "        <directionalLight position={[4, 6, 3]} intensity={1.2} castShadow={false} />\n"
    "        <Sphere />\n"
    "      </Canvas>\n"
    "    </div>\n"
    "  );\n"
    "}\n"
    "</file>\n"
    "<file path=\"src/components/FixedScene.css\">\n"
    ".fs-wrap{width:100%;height:480px;border-radius:16px;overflow:hidden;background:#1a1c20}\n"
    "@media(prefers-reduced-motion:reduce){.fs-wrap canvas{animation:none !important}}\n"
    "</file>\n"
    "</tool_call>"
)

# ─────────────────────────────────────────────────────────────────────────────
# Record 3: Scroll-driven camera rig
# Teaches: ScrollControls, useScroll, lerp, mobile fallback, reduced-motion
# ─────────────────────────────────────────────────────────────────────────────
R3_USER = (
    "Write a React TypeScript component ScrollCameraHero.tsx + ScrollCameraHero.css\n"
    "that moves the camera along a path as the user scrolls.\n\n"
    "Requirements:\n"
    "- Use @react-three/drei ScrollControls + useScroll\n"
    "- Camera lerps (factor 0.06) from [0, 0, 8] to [0, 2, 3] as scroll goes 0→1\n"
    "- Three simple box meshes at different Z depths as landmarks\n"
    "- Mobile (< 768px): disable scroll controls, use static centered view\n"
    "- frameloop=demand, dpr [1, 1.5], max 2 lights\n"
    "- prefers-reduced-motion: freeze camera at midpoint, no scroll movement\n"
    "- Named export ScrollCameraHero"
)

R3_ASSISTANT = (
    "<thought>\n"
    "Scroll-driven camera: ScrollControls wraps the scene; useScroll gives offset 0-1.\n"
    "lerp camera position inside useFrame using THREE.MathUtils.lerp or Vector3.lerp.\n"
    "On mobile: render without ScrollControls (static scene, no scroll hijacking).\n"
    "prefers-reduced-motion: read in React, pass as prop, freeze camera at t=0.5 (midpoint).\n"
    "frameloop=demand still works with ScrollControls because drei calls invalidate on scroll offset changes.\n"
    "</thought>\n"
    "<tool_call name=\"write_site\">\n"
    "<file path=\"src/components/ScrollCameraHero.tsx\">\n"
    "import React, { useRef, useEffect, useState } from 'react';\n"
    "import { Canvas, useFrame, useThree } from '@react-three/fiber';\n"
    "import { ScrollControls, useScroll } from '@react-three/drei';\n"
    "import * as THREE from 'three';\n"
    "import './ScrollCameraHero.css';\n\n"
    "const START = new THREE.Vector3(0, 0, 8);\n"
    "const END = new THREE.Vector3(0, 2, 3);\n\n"
    "function CameraRig({ paused }: { paused: boolean }) {\n"
    "  const { camera, invalidate } = useThree();\n"
    "  const scroll = useScroll();\n"
    "  const target = useRef(START.clone());\n"
    "  useFrame(() => {\n"
    "    const t = paused ? 0.5 : scroll.offset;\n"
    "    target.current.lerpVectors(START, END, t);\n"
    "    camera.position.lerp(target.current, 0.06);\n"
    "    camera.lookAt(0, 0, 0);\n"
    "    invalidate();\n"
    "  });\n"
    "  return null;\n"
    "}\n\n"
    "function Landmarks() {\n"
    "  return (\n"
    "    <>\n"
    "      <mesh position={[-2, 0, 0]}>\n"
    "        <boxGeometry args={[0.8, 0.8, 0.8]} />\n"
    "        <meshStandardMaterial color=\"#6366f1\" roughness={0.4} metalness={0.3} />\n"
    "      </mesh>\n"
    "      <mesh position={[0, 0.4, -3]}>\n"
    "        <boxGeometry args={[1, 1, 1]} />\n"
    "        <meshStandardMaterial color=\"#22d3ee\" roughness={0.3} metalness={0.5} />\n"
    "      </mesh>\n"
    "      <mesh position={[2.5, -0.3, -6]}>\n"
    "        <boxGeometry args={[0.6, 1.2, 0.6]} />\n"
    "        <meshStandardMaterial color=\"#f59e0b\" roughness={0.5} metalness={0.2} />\n"
    "      </mesh>\n"
    "    </>\n"
    "  );\n"
    "}\n\n"
    "function Lights() {\n"
    "  return (\n"
    "    <>\n"
    "      <ambientLight intensity={0.5} />\n"
    "      <directionalLight position={[5, 8, 4]} intensity={1.1} castShadow={false} />\n"
    "    </>\n"
    "  );\n"
    "}\n\n"
    "export function ScrollCameraHero() {\n"
    "  const [isMobile, setIsMobile] = useState(false);\n"
    "  const [prefersReduced, setPrefersReduced] = useState(false);\n\n"
    "  useEffect(() => {\n"
    "    const mq = window.matchMedia('(max-width: 767px)');\n"
    "    const rm = window.matchMedia('(prefers-reduced-motion: reduce)');\n"
    "    setIsMobile(mq.matches);\n"
    "    setPrefersReduced(rm.matches);\n"
    "    const onMQ = (e: MediaQueryListEvent) => setIsMobile(e.matches);\n"
    "    const onRM = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);\n"
    "    mq.addEventListener('change', onMQ);\n"
    "    rm.addEventListener('change', onRM);\n"
    "    return () => { mq.removeEventListener('change', onMQ); rm.removeEventListener('change', onRM); };\n"
    "  }, []);\n\n"
    "  return (\n"
    "    <div className=\"sch-root\">\n"
    "      <a className=\"sch-skip\" href=\"#sch-after\">Skip scroll animation</a>\n"
    "      <Canvas frameloop=\"demand\" dpr={[1, 1.5]}\n"
    "        camera={{ position: [0, 0, 8], fov: 55 }} aria-hidden=\"true\">\n"
    "        <color attach=\"background\" args={['#0f1117']} />\n"
    "        <Lights />\n"
    "        {isMobile || prefersReduced ? (\n"
    "          <Landmarks />\n"
    "        ) : (\n"
    "          <ScrollControls pages={3} damping={0.25}>\n"
    "            <CameraRig paused={prefersReduced} />\n"
    "            <Landmarks />\n"
    "          </ScrollControls>\n"
    "        )}\n"
    "      </Canvas>\n"
    "      <p id=\"sch-after\" className=\"sch-hint\">Scroll to move through the scene</p>\n"
    "    </div>\n"
    "  );\n"
    "}\n"
    "</file>\n"
    "<file path=\"src/components/ScrollCameraHero.css\">\n"
    ".sch-root{position:relative;width:100%;height:100svh;min-height:500px}\n"
    ".sch-root canvas{position:absolute !important;inset:0;width:100% !important;height:100% !important}\n"
    ".sch-skip{position:absolute;left:16px;top:-80px;z-index:20;background:#f0f0f0;color:#0f1117;padding:8px 14px;font-size:.8rem;font-weight:600;border-radius:6px;text-decoration:none}\n"
    ".sch-skip:focus{top:16px}\n"
    ".sch-hint{position:absolute;bottom:28px;left:50%;transform:translateX(-50%);color:rgba(255,255,255,.4);font-size:.8rem;letter-spacing:.1em;pointer-events:none;margin:0}\n"
    "@media(max-width:767px){.sch-hint{display:none}}\n"
    "@media(prefers-reduced-motion:reduce){.sch-hint{display:none}}\n"
    "</file>\n"
    "</tool_call>"
)

records = [
    {
        "task_id": "r3f_floating_orb_v1",
        "family_id": "r3f_scenes",
        "source": "hand_authored",
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": R1_USER},
            {"role": "assistant", "content": R1_ASSISTANT},
        ],
    },
    {
        "task_id": "r3f_performance_fix_v1",
        "family_id": "r3f_scenes",
        "source": "hand_authored",
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": R2_USER},
            {"role": "assistant", "content": R2_ASSISTANT},
        ],
    },
    {
        "task_id": "r3f_scroll_camera_v1",
        "family_id": "r3f_scenes",
        "source": "hand_authored",
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": R3_USER},
            {"role": "assistant", "content": R3_ASSISTANT},
        ],
    },
]


def build():
    out_dir = ROOT / "data" / "r3f_trajectories"
    out_dir.mkdir(parents=True, exist_ok=True)
    draft = out_dir / "r3f_draft.jsonl"
    draft.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )
    report = {
        "records": len(records),
        "task_ids": [r["task_id"] for r in records],
        "families": list({r["family_id"] for r in records}),
        "path": str(draft),
        "status": "DRAFT — requires browser render + reduced-motion + WebGL-fallback verification before promotion",
        "teaches": [
            "on-demand rendering (frameloop=demand + invalidate)",
            "DPR budgeting for laptop GPU",
            "performance diagnosis: lights/vertices/shadow",
            "prefers-reduced-motion in React",
            "WebGL availability probe + CSS fallback",
            "scroll-driven camera with useScroll + lerp",
            "mobile fallback (disable ScrollControls)",
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    build()
