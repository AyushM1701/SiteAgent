#!/usr/bin/env python3
"""
scripts/benchmark_full_sites.py - Run and Score the Dedicated Full-Website Benchmark.

Enforces Issue #25 of the SiteAgent Implementation Plan:
1. Evaluates 30-50 full-site prompts across 12 domains:
   - SaaS, portfolio, ecommerce, editorial, restaurant, healthcare,
     finance, agency, architecture, dashboard, 3D product, WebGL experience.
2. Scores every site across all 16 required dimensions:
   - prompt fidelity, required section completion, TypeScript, production build,
     runtime, interactions, responsive design, accessibility, visual structure,
     content quality, design diversity, dependencies, assets, 3D runtime/performance,
     repair attempts, time-to-preview.
3. Outputs structured report to runs/full_website_benchmark_report.json.
4. Produces promotion-ready metrics consumed by training/methodology.py.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.site_benchmark_scorer import (
    SiteBenchmarkScore,
    SiteBenchmarkScorer,
    aggregate_site_benchmark_scores,
    REQUIRED_SCORING_DIMENSIONS,
)
from evaluation.diversity_evaluator import DIVERSITY_DIMENSIONS

DEFAULT_BENCHMARK_PATH = ROOT / "data" / "eval" / "full_website_benchmark.jsonl"
DEFAULT_OUTPUT_REPORT = ROOT / "runs" / "full_website_benchmark_report.json"
DEFAULT_MOCK_OUTPUT_REPORT = ROOT / "runs" / "mock_full_website_benchmark_report.json"


def build_outcome_scorecards(
    *, mock: bool, generation_result: Optional[Dict[str, Any]] = None,
    repair_result: Any = None, final_score: Optional[SiteBenchmarkScore] = None,
) -> Dict[str, Dict[str, Any]]:
    """Keep model output, deterministic fixes, model repair, and final site distinct."""
    if mock:
        return {"mock_harness": {"status": "evaluated", "passed": bool(final_score and final_score.passed)},
                "model_native": {"status": "not_evaluated", "passed": None},
                "deterministic_repair": {"status": "not_evaluated", "passed": None},
                "model_repair": {"status": "not_evaluated", "passed": None},
                "final_rendered_site": {"status": "not_evaluated", "passed": None}}
    generation_result = generation_result or {}
    native_validation = generation_result.get("validation")
    deterministic_validation = getattr(repair_result, "validation_after_deterministic", None)
    deterministic_files = list(getattr(repair_result, "deterministic_files", []) or [])
    repair_attempts = int(getattr(repair_result, "repair_attempts", 0) or 0)
    final_validation = getattr(repair_result, "validation", None)
    native = bool(generation_result.get("generation_quality") == "native"
                  and generation_result.get("final_passed") and native_validation and native_validation.passed)
    return {
        "model_native": {"status": "evaluated", "passed": native,
                         "generation_quality": generation_result.get("generation_quality"),
                         "validation_passed": bool(native_validation and native_validation.passed)},
        "deterministic_repair": {
            "status": "evaluated" if deterministic_files else "not_run",
            "passed": bool(deterministic_validation and deterministic_validation.passed) if deterministic_files else None,
            "files_changed": deterministic_files,
        },
        "model_repair": {
            "status": "evaluated" if repair_attempts else "not_run",
            "passed": bool(final_validation and final_validation.passed) if repair_attempts else None,
            "attempts": repair_attempts,
        },
        "final_rendered_site": {
            "status": "evaluated", "passed": bool(final_score and final_score.passed),
            "validation_passed": bool(final_validation and final_validation.passed),
            "composite_score": round(final_score.composite_score, 4) if final_score else None,
        },
    }


def generate_mock_site_files(prompt_spec: Dict[str, Any]) -> Dict[str, str]:
    """Generates clean, realistic mock site files with domain-specific archetypes for diversity testing."""
    name = prompt_spec.get("name", "SiteApp")
    title = prompt_spec.get("title", f"{name} Application")
    sections = prompt_spec.get("required_sections", ["navbar", "hero", "features", "footer"])
    domain = prompt_spec.get("domain", "saas").lower()
    palette = prompt_spec.get("palette", {})
    domain_kws = prompt_spec.get("domain_keywords", ["platform", "speed", "cloud"])
    has_3d = prompt_spec.get("has_3d", False) or prompt_spec.get("has_webgl", False)

    # 1. Domain-Driven Archetypes for Anti-Template-Collapse Verification
    if domain in ("editorial", "architecture", "restaurant"):
        bg_color = palette.get("background", "#fcfbf7")
        surface_color = palette.get("surface", "#ffffff")
        primary_color = palette.get("primary", "#1c1917")
        accent_color = palette.get("accent", "#b45309")
        text_main = "#1c1917"
        text_muted = "#78716c"
        heading_font = "'Playfair Display', Georgia, serif"
        body_font = "'Source Serif Pro', Georgia, serif"
        base_radius = "0px"
        cta_radius = "0px"
        cta_class = "btn-sharp rounded-none"
        bg_treatment = "background-color: var(--color-bg);"
        hero_class = "hero font-serif text-left editorial hero__editorial"
        grid_class = "bento-grid"
        grid_css = "display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;"
    elif domain in ("dashboard", "finance"):
        bg_color = palette.get("background", "#0b0f19")
        surface_color = palette.get("surface", "#111827")
        primary_color = palette.get("primary", "#10b981")
        accent_color = palette.get("accent", "#38bdf8")
        text_main = "#f9fafb"
        text_muted = "#9ca3af"
        heading_font = "'Plus Jakarta Sans', sans-serif"
        body_font = "'JetBrains Mono', monospace"
        base_radius = "6px"
        cta_radius = "6px"
        cta_class = "btn-subtle rounded-md"
        bg_treatment = "background-image: radial-gradient(circle, rgba(16, 185, 129, 0.1) 1px, transparent 1px); background-size: 20px 20px;"
        hero_class = "hero grid-cols-2 hero__split"
        grid_class = "tabs tablist"
        grid_css = "display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;"
    elif domain in ("3d_product", "webgl_experience", "agency"):
        bg_color = palette.get("background", "#090a0f")
        surface_color = palette.get("surface", "#13141f")
        primary_color = palette.get("primary", "#a855f7")
        accent_color = palette.get("accent", "#06b6d4")
        text_main = "#f8fafc"
        text_muted = "#94a3b8"
        heading_font = "'Space Grotesk', sans-serif"
        body_font = "'Inter', sans-serif"
        base_radius = "16px"
        cta_radius = "9999px"
        cta_class = "btn-pill rounded-full"
        bg_treatment = "background: linear-gradient(135deg, #090a0f, #1a1b26); /* aurora glow */"
        hero_class = "hero full-bleed bg-cover canvas-3d-hero"
        grid_class = "carousel slider"
        grid_css = "display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 2rem;"
    elif domain == "portfolio":
        bg_color = palette.get("background", "#ffffff")
        surface_color = palette.get("surface", "#f4f4f5")
        primary_color = palette.get("primary", "#18181b")
        accent_color = palette.get("accent", "#6366f1")
        text_main = "#09090b"
        text_muted = "#71717a"
        heading_font = "'Space Grotesk', sans-serif"
        body_font = "'Inter', sans-serif"
        base_radius = "12px"
        cta_radius = "9999px"
        cta_class = "btn-pill rounded-full"
        bg_treatment = "background-color: var(--color-bg);"
        hero_class = "hero full-bleed bg-cover"
        grid_class = "carousel slider"
        grid_css = "display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem;"
    elif domain == "ecommerce":
        bg_color = palette.get("background", "#ffffff")
        surface_color = palette.get("surface", "#fafaf9")
        primary_color = palette.get("primary", "#0284c7")
        accent_color = palette.get("accent", "#f59e0b")
        text_main = "#1e293b"
        text_muted = "#64748b"
        heading_font = "'Plus Jakarta Sans', sans-serif"
        body_font = "'Inter', sans-serif"
        base_radius = "12px"
        cta_radius = "12px"
        cta_class = "btn-curved rounded-xl"
        bg_treatment = "background-color: var(--color-bg);"
        hero_class = "hero grid-cols-2 hero__split"
        grid_class = "bento-grid"
        grid_css = "display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem;"
    else:  # saas, healthcare, etc.
        bg_color = palette.get("background", "#0f172a")
        surface_color = palette.get("surface", "#1e293b")
        primary_color = palette.get("primary", "#38bdf8")
        accent_color = palette.get("accent", "#10b981")
        text_main = "#f8fafc"
        text_muted = "#94a3b8"
        heading_font = "'Inter', sans-serif"
        body_font = "'Inter', sans-serif"
        base_radius = "8px"
        cta_radius = "8px"
        cta_class = "btn-rounded rounded"
        bg_treatment = "background-image: radial-gradient(circle, rgba(56, 189, 248, 0.12) 1px, transparent 1px); background-size: 24px 24px;"
        hero_class = "hero grid-cols-2 hero__split"
        grid_class = "feature-grid grid-cols-4"
        grid_css = "display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem;"

    files: Dict[str, str] = {}

    # 1. package.json
    files["package.json"] = json.dumps({
        "name": name.lower(),
        "private": True,
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview",
            "typecheck": "tsc --noEmit"
        },
        "dependencies": {
            "react": "^19.0.0",
            "react-dom": "^19.0.0",
            "lucide-react": "^0.475.0"
        },
        "devDependencies": {
            "@types/react": "^19.0.10",
            "@types/react-dom": "^19.0.4",
            "@vitejs/plugin-react": "^4.3.4",
            "typescript": "^5.7.3",
            "vite": "^6.0.0"
        }
    }, indent=2)

    # 2. tsconfig.json
    files["tsconfig.json"] = json.dumps({
        "compilerOptions": {
            "target": "ES2022",
            "lib": ["ES2022", "DOM"],
            "jsx": "react-jsx",
            "module": "ESNext",
            "moduleResolution": "bundler",
            "esModuleInterop": True,
            "skipLibCheck": True,
            "noEmit": True
        },
        "include": ["**/*.ts", "**/*.tsx", "src/vite-env.d.ts"]
    }, indent=2)

    # 3. vite-env.d.ts
    files["src/vite-env.d.ts"] = '/// <reference types="vite/client" />\ndeclare module "*.css";\n'

    # 4. Global CSS
    files["src/index.css"] = f"""
:root {{
  --color-bg: {bg_color};
  --color-surface: {surface_color};
  --color-primary: {primary_color};
  --color-accent: {accent_color};
  --text-main: {text_main};
  --text-muted: {text_muted};
  --font-heading: {heading_font};
  --font-body: {body_font};
  --radius-base: {base_radius};
  --radius-buttons: {cta_radius};
}}

* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body {{
  {bg_treatment}
  color: var(--text-main);
  font-family: var(--font-body);
  line-height: 1.5;
}}

h1, h2, h3, h4, h5, h6 {{
  font-family: var(--font-heading);
}}

.btn {{
  border-radius: var(--radius-buttons);
  padding: 0.5rem 1.25rem;
  font-weight: 500;
  cursor: pointer;
}}

:focus-visible {{
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}}

@media (max-width: 768px) {{
  body {{
    font-size: 14px;
  }}
}}
"""

    # 5. Component sections
    component_imports: List[str] = []
    component_elements: List[str] = []

    for sec in sections:
        pascal_sec = "".join(w.capitalize() for w in re.split(r"[-_]", sec))
        component_imports.append(f'import {pascal_sec} from "./components/{pascal_sec}";')
        component_elements.append(f"      <{pascal_sec} />")

        extra_3d_code = ""
        if has_3d and ("hero" in sec.lower() or "canvas" in sec.lower() or "view" in sec.lower()):
            extra_3d_code = """
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const [isPlaying, setIsPlaying] = React.useState(true);

  React.useEffect(() => {
    let animId: number;
    const canvas = canvasRef.current;
    if (canvas) {
      const gl = canvas.getContext('webgl');
      const renderLoop = () => {
        if (isPlaying) {
          // simulation loop
        }
        animId = requestAnimationFrame(renderLoop);
      };
      animId = requestAnimationFrame(renderLoop);
    }
    return () => {
      cancelAnimationFrame(animId);
    };
  }, [isPlaying]);
"""

        is_hero_sec = "hero" in sec.lower()
        is_feature_sec = "feature" in sec.lower()
        active_sec_class = hero_class if is_hero_sec else (grid_class if is_feature_sec else f"{sec}-container")

        files[f"src/components/{pascal_sec}.css"] = f"""
.{sec}-container {{
  padding: clamp(2rem, 5vw, 4rem) 1.5rem;
  background-color: var(--color-surface);
  margin: 1rem auto;
  max-width: 1200px;
  border-radius: var(--radius-base);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
}}

.{sec}-title {{
  color: var(--color-primary);
  margin-bottom: 1rem;
  font-size: clamp(1.5rem, 3vw, 2.25rem);
}}

.{sec}-content {{
  {grid_css}
}}

.{sec}-card {{
  padding: 1.5rem;
  border: 1px solid rgba(125, 125, 125, 0.2);
  border-radius: var(--radius-base);
}}

@media (max-width: 768px) {{
  .{sec}-container {{
    padding: 1.5rem 1rem;
  }}
}}
"""

        # Domain specific interactive controls
        if domain in ("dashboard", "finance"):
            state_decl = "const [activeTab, setActiveTab] = useState(0);"
            btn_controls = f"""<button onClick={{() => setActiveTab(0)}} className="btn {cta_class}">Overview</button><button onClick={{() => setActiveTab(1)}} className="btn {cta_class}">Analytics</button>"""
        elif domain == "ecommerce":
            state_decl = "const [quantity, setQuantity] = useState(1);"
            btn_controls = f"""<button onClick={{() => setQuantity(q => Math.max(1, q - 1))}} className="btn {cta_class}">-</button><span style={{{{ margin: "0 0.5rem" }}}}>Qty: {{quantity}}</span><button onClick={{() => setQuantity(q => q + 1)}} className="btn {cta_class}">+</button>"""
        elif domain == "portfolio":
            state_decl = 'const [filter, setFilter] = useState("all");'
            btn_controls = f"""<button onClick={{() => setFilter("all")}} className="btn {cta_class}">Featured</button><button onClick={{() => setFilter("recent")}} className="btn {cta_class}">Recent</button>"""
        elif domain in ("editorial", "restaurant"):
            state_decl = 'const [mode, setMode] = useState("digest");'
            btn_controls = f"""<button onClick={{() => setMode("digest")}} className="btn {cta_class}">Curated</button><button onClick={{() => setMode("archive")}} className="btn {cta_class}">Archive</button>"""
        else:
            state_decl = "const [annual, setAnnual] = useState(true);"
            btn_controls = f"""<button onClick={{() => setAnnual(!annual)}} className="btn {cta_class}">Billing: {{annual ? "Annual (-20%)" : "Monthly"}}</button>"""

        files[f"src/components/{pascal_sec}.tsx"] = f"""import React, {{ useState }} from "react";
import "./{pascal_sec}.css";

export default function {pascal_sec}() {{
  {state_decl}
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
{extra_3d_code}
  return (
    <section className="{sec}-container {active_sec_class}" id="{sec}" aria-label="{title} {sec}">
      <h2 className="{sec}-title">{title} - {pascal_sec}</h2>
      <p style={{{{ color: "var(--text-muted)", marginBottom: "1rem" }}}}>
        Delivering high-reliability {" ".join(domain_kws[:3])} with dedicated enterprise performance for {name}.
      </p>

      {f'<div style={{{{ marginBottom: "1rem" }}}}><canvas ref={{canvasRef}} width="300" height="200" style={{{{ border: "1px solid var(--color-primary)" }}}} /><button className="btn {cta_class}" onClick={{() => setIsPlaying(!isPlaying)}}>Toggle Motion</button></div>' if extra_3d_code else ''}

      <div style={{{{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap", alignItems: "center" }}}}>
        {btn_controls}
      </div>

      <div className="{sec}-content">
        <div className="{sec}-card">
          <h3>Core Capability</h3>
          <p>Real-time telemetry and cloud operational control engineered for scale.</p>
        </div>
        <div className="{sec}-card">
          <h3>Reliable Architecture</h3>
          <p>Built with verifiable security and high availability SLA standards.</p>
        </div>
      </div>
    </section>
  );
}}
"""

    # 6. src/App.tsx with domain navigation patterns
    if domain == "dashboard":
        nav_header = f"""      <aside className="sidebar-dock" aria-label="Main sidebar navigation" style={{{{ width: "240px", padding: "1.5rem", borderRight: "1px solid rgba(125,125,125,0.2)" }}}}>
        <h1 style={{{{ fontSize: "1.25rem", color: "var(--color-primary)", marginBottom: "1rem" }}}}>{name}</h1>
        <nav><a href="#overview">Dashboard</a> | <a href="#analytics">Analytics</a></nav>
      </aside>"""
        layout_style = 'style={{ minHeight: "100vh", display: "flex", flexDirection: "row" }}'
    elif domain in ("3d_product", "agency"):
        nav_header = f"""      <header style={{{{ padding: "1rem" }}}}>
        <nav className="floating rounded-full island" aria-label="Floating navigation" style={{{{ padding: "0.75rem 1.5rem", margin: "0 auto", maxWidth: "700px", display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid rgba(125,125,125,0.2)" }}}}>
          <h1 style={{{{ fontSize: "1.25rem", color: "var(--color-primary)" }}}}>{name}</h1>
          <button className="btn {cta_class}">Launch</button>
        </nav>
      </header>"""
        layout_style = 'style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}'
    elif domain in ("editorial", "restaurant"):
        nav_header = f"""      <header className="masthead edition" aria-label="Editorial masthead navigation" style={{{{ padding: "1.5rem 2rem", borderBottom: "2px solid var(--color-primary)", textAlign: "center" }}}}>
        <h1 style={{{{ fontSize: "2rem", letterSpacing: "0.05em", color: "var(--color-primary)" }}}}>{name.upper()}</h1>
        <p style={{{{ fontSize: "0.85rem", color: "var(--text-muted)" }}}}>Daily Architectural & Editorial Review</p>
      </header>"""
        layout_style = 'style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}'
    elif domain == "portfolio":
        nav_header = f"""      <header>
        <nav className="minimal hamburger menu" aria-label="Minimal portfolio menu" style={{{{ padding: "1rem 2rem", display: "flex", justifyContent: "space-between" }}}}>
          <h1 style={{{{ fontSize: "1.25rem", color: "var(--color-primary)" }}}}>{name}</h1>
          <button aria-label="Menu" className="btn {cta_class}">Menu</button>
        </nav>
      </header>"""
        layout_style = 'style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}'
    else:
        nav_header = f"""      <header>
        <nav className="w-full border-b sticky-topbar" aria-label="Main navigation" style={{{{ padding: "1rem 2rem", borderBottom: "1px solid rgba(125,125,125,0.2)", display: "flex", justifyContent: "space-between" }}}}>
          <h1 style={{{{ fontSize: "1.25rem", color: "var(--color-primary)" }}}}>{name}</h1>
          <button className="btn {cta_class}">Get Started</button>
        </nav>
      </header>"""
        layout_style = 'style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}'

    files["src/App.tsx"] = f"""import React from "react";
import "./index.css";
{chr(10).join(component_imports)}

export default function App() {{
  return (
    <div className="site-wrapper" {layout_style}>
{nav_header}
      <main style={{{{ flex: 1 }}}}>
{chr(10).join(component_elements)}
      </main>
      <footer>
        <div style={{{{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", borderTop: "1px solid rgba(125,125,125,0.2)" }}}}>
          <p>&copy; 2026 {name}. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}}
"""

    # 7. main.tsx
    files["main.tsx"] = """import React from "react";
import ReactDOM from "react-dom/client";
import App from "./src/App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""

    # 8. index.html
    files["index.html"] = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/main.tsx"></script>
  </body>
</html>
"""

    return files


def run_full_site_benchmark(
    model_path: Optional[str] = None,
    benchmark_file: Path = DEFAULT_BENCHMARK_PATH,
    output_report_path: Path = DEFAULT_OUTPUT_REPORT,
    mock: bool = False,
    domain_filter: Optional[str] = None,
    subset: Optional[int] = None,
    live_browser_check: bool = False,
    keep_workspace: bool = False,
    workspace_base: Optional[Path] = None,
) -> Dict[str, Any]:
    """Runs the full-site benchmark and produces comprehensive scoring across all 16 metrics."""
    if mock and output_report_path == DEFAULT_OUTPUT_REPORT:
        output_report_path = DEFAULT_MOCK_OUTPUT_REPORT
    if not benchmark_file.exists():
        raise FileNotFoundError(f"Full-site benchmark file not found: {benchmark_file}")

    prompts: List[Dict[str, Any]] = []
    with open(benchmark_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                prompts.append(json.loads(line_str))

    # Apply domain filter
    if domain_filter:
        prompts = [p for p in prompts if p.get("domain", "").lower() == domain_filter.lower()]

    # Apply subset limit
    if subset and subset < len(prompts):
        prompts = prompts[:subset]

    print("=" * 75)
    print(f"SiteAgent Full-Website Benchmark Evaluation (Issue #25)")
    print("=" * 75)
    print(f"Prompts to evaluate: {len(prompts)}")
    print(f"Benchmark source:    {benchmark_file}")
    print(f"Mode:                {'MOCK HARNESS' if mock else f'MODEL ({model_path})'}")
    print(f"Dimensions:          16 mandatory criteria")
    print("-" * 75)

    if workspace_base is None:
        workspace_base = (ROOT / ".eval_site_benchmark_workspace").resolve()
        if ROOT.resolve() not in workspace_base.parents:
            raise ValueError("Benchmark workspace escaped the repository")
        if workspace_base.exists():
            shutil.rmtree(workspace_base)
    else:
        workspace_base = Path(workspace_base).resolve()
        if workspace_base.exists():
            raise FileExistsError(f"Explicit benchmark workspace already exists: {workspace_base}")
    workspace_base.mkdir(parents=True, exist_ok=True)

    scores: List[SiteBenchmarkScore] = []
    scorer = SiteBenchmarkScorer(workspace_root=workspace_base)

    # Initialize model runner if running live
    runner = None
    if not mock:
        from agent.agent import AgentModelRunner, run_site_agent_on_example
        from agent.site_brief import generate_content_brief, brief_to_xml
        runner = AgentModelRunner(model_path=model_path or "base-model")

    for idx, prompt_spec in enumerate(prompts):
        task_id = prompt_spec.get("task_id", f"task_{idx:03d}")
        domain = prompt_spec.get("domain", "general")
        name = prompt_spec.get("name", f"Site{idx:03d}")
        prompt = prompt_spec.get("prompt", "")

        site_workspace = workspace_base / task_id
        site_workspace.mkdir(parents=True, exist_ok=True)

        print(f"[{idx+1}/{len(prompts)}] Running {task_id} ({domain} - {name})...", end=" ", flush=True)
        start_time = time.time()
        turn_logs: List[Dict[str, Any]] = []
        files: Dict[str, str] = {}

        if mock:
            # Generate clean mock files
            files = generate_mock_site_files(prompt_spec)
            for path_str, content in files.items():
                dest = site_workspace / path_str
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
            elapsed = time.time() - start_time
            turn_logs = [{"action": "mock_generate", "completed": True}]
        else:
            brief = generate_content_brief(prompt)
            sections = brief.get("sections", prompt_spec.get("required_sections", ["navbar", "hero", "footer"]))
            brief_xml = brief_to_xml(brief) if brief else ""
            res = run_site_agent_on_example(
                orig_idx=idx,
                prompt=prompt,
                project_name=name,
                brief_xml=brief_xml,
                sections=sections,
                runner=runner,
                workspace_root=site_workspace,
                max_turns=max(12, len(sections) * 2),
                business_type=brief.get("business_type", "general"),
                custom_section_instructions=brief.get("custom_section_instructions"),
            )
            files = res.get("files", {})
            turn_logs = res.get("turn_logs", [])
            site_workspace = site_workspace / f"site_{idx:03d}"
            from agent.agent import resolve_project_path
            for rel_path, content in files.items():
                if rel_path.startswith("src/components/") and rel_path.endswith((".tsx", ".css")):
                    dest = resolve_project_path(site_workspace, rel_path)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.is_file() or dest.read_text(encoding="utf-8") != content:
                        dest.write_text(content, encoding="utf-8")
            from agent.dependency_manager import ensure_runtime_packages
            dependency_errors = ensure_runtime_packages(files, ROOT)
            if dependency_errors:
                turn_logs.append({"action": "dependency_failure", "errors": dependency_errors})
            os.environ.setdefault("NO_AUTO_LOAD_MODEL", "1")
            from server.app import _scaffold_site_vite_runner, verify_and_repair_project
            _scaffold_site_vite_runner(site_workspace, name, files, brief=brief)
            (site_workspace / "content_brief.json").write_text(
                json.dumps({"original_prompt": prompt, "sections": sections,
                            "required_interactions": prompt_spec.get("required_interactions", []),
                            "motion_plan": [item.to_dict() if hasattr(item, "to_dict") else item for item in brief.get("motion_plan", [])],
                            "requirement_manifest": brief.get("requirement_manifest", {})}, default=str),
                encoding="utf-8",
            )
            repair_result = verify_and_repair_project(
                workspace=site_workspace,
                runner=runner,
                original_prompt=prompt,
                brief=brief,
                max_attempts=2,
                files_dict=files,
                project_name=name,
                sections=sections,
                run_visual_check=False,
            )
            turn_logs.append({
                "action": "project_repair",
                "repair_attempts": repair_result.repair_attempts,
                "passed": repair_result.validation.passed,
                "errors": repair_result.validation.errors,
            })
            # Project repair may change files after initial section generation.
            # Score the final workspace, not the pre-repair model response.
            for source in (site_workspace / "src" / "components").glob("*"):
                if source.is_file() and source.suffix in (".tsx", ".css", ".jsx"):
                    files[source.relative_to(site_workspace).as_posix()] = source.read_text(encoding="utf-8")
            elapsed = time.time() - start_time

        # Score site across all 16 dimensions
        site_score = scorer.evaluate_site(
            prompt_spec=prompt_spec,
            files=files,
            workspace_dir=site_workspace,
            turn_logs=turn_logs,
            elapsed_seconds=elapsed,
            live_browser_check=live_browser_check or not mock,
        )
        site_score.details["turn_logs"] = turn_logs
        if not mock:
            site_score.details["generation_metrics"] = res.get("generation_metrics", [])
            site_score.details["project_validation"] = repair_result.validation.to_dict()
            site_score.details["three_d_static_status"] = repair_result.validation.three_d_static_status
            site_score.details["three_d_runtime_status"] = repair_result.validation.three_d_runtime_status
            evidence_path = site_workspace / "three_d_runtime_evidence.json"
            if evidence_path.is_file():
                site_score.details["three_d_runtime_evidence"] = json.loads(evidence_path.read_text(encoding="utf-8"))
            if not repair_result.validation.passed:
                site_score.passed = False
                site_score.errors.append("Project validation failed after repair.")
        site_score.details["outcome_scorecards"] = build_outcome_scorecards(
            mock=mock,
            generation_result=res if not mock else None,
            repair_result=repair_result if not mock else None,
            final_score=site_score,
        )
        if keep_workspace:
            site_score.details["workspace_dir"] = str(site_workspace.resolve())
        scores.append(site_score)

        # Retain completed cases if a later generation or browser run fails.
        progress_path = output_report_path.with_suffix(".progress.json")
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = progress_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({
            "status": "running", "evaluation_mode": "mock_harness" if mock else "live_model",
            "model": model_path if not mock else "mock-runner",
            "benchmark": str(benchmark_file.resolve()),
            "completed_sites": len(scores), "total_sites": len(prompts),
            "site_results": [score.to_dict() for score in scores],
        }, indent=2), encoding="utf-8")
        temporary.replace(progress_path)

        status_str = "PASS" if site_score.passed else "FAIL"
        print(f"{status_str} (Score: {site_score.composite_score:.2f}, Elapsed: {elapsed:.1f}s)")

    # Aggregate scores
    from training.provenance import generate_provenance_record
    prov_meta = generate_provenance_record(
        mock=mock,
        model_path=model_path if not mock else None,
        adapter_path=model_path if not mock and "models" in (model_path or "") else None,
        dataset_path=str(benchmark_file),
    )
    summary = aggregate_site_benchmark_scores(scores)
    summary.update(prov_meta)
    summary["model"] = model_path if not mock else "mock-runner"
    summary["is_mock"] = mock
    summary["evaluation_mode"] = "mock_harness" if mock else "live_model"
    summary["visual_quality_evidence"] = "static_and_pixel_guardrails_only; human review required for promotion"
    stages = ("mock_harness", "model_native", "deterministic_repair", "model_repair", "final_rendered_site") if mock else (
        "model_native", "deterministic_repair", "model_repair", "final_rendered_site"
    )
    summary["outcome_scorecards_summary"] = {}
    for stage in stages:
        evaluated = [s.details["outcome_scorecards"][stage] for s in scores
                     if s.details["outcome_scorecards"][stage]["status"] == "evaluated"]
        summary["outcome_scorecards_summary"][stage] = {
            "evaluated_sites": len(evaluated),
            "passed_sites": sum(card["passed"] is True for card in evaluated),
            "pass_rate": round(sum(card["passed"] is True for card in evaluated) / len(evaluated), 4)
                         if evaluated else None,
        }
    summary["evaluated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    summary["site_results"] = [s.to_dict() for s in scores]
    if keep_workspace:
        summary["workspace_dir"] = str(workspace_base)

    # Save output report
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    if scores:
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress["status"] = "complete"
        progress["report"] = str(output_report_path.resolve())
        temporary.write_text(json.dumps(progress, indent=2), encoding="utf-8")
        temporary.replace(progress_path)

    # Print summary table
    print("\n" + "=" * 75)
    print("FULL-WEBSITE BENCHMARK SUMMARY")
    print("=" * 75)
    print(f"Total Sites Evaluated:   {summary['total_sites']}")
    print(f"Overall Site Pass Rate: {summary['overall_pass_rate']:.1%}")
    print(f"Mean Composite Score:   {summary['composite_score_mean']:.3f}")
    print(f"Provenance:             {summary.get('provenance')} / {summary['evaluation_mode']}")
    for stage, card in summary["outcome_scorecards_summary"].items():
        print(f"  {stage}: {card['passed_sites']}/{card['evaluated_sites']} passed")
    print("-" * 75)
    print("16-METRIC BREAKDOWN:")
    for dim in REQUIRED_SCORING_DIMENSIONS:
        mean_v = summary["metric_means"].get(dim, 0.0)
        print(f"  - {dim:<30}: {mean_v:.3f}")
    print("-" * 75)
    print("DOMAIN BREAKDOWN (12 Domains):")
    print(f"  {'Domain':<20} | {'Sites':<5} | {'Pass Rate':<10} | {'Composite':<10} | {'Build Rate':<10}")
    print("  " + "-" * 65)
    for dom, d_data in summary["domain_breakdown"].items():
        print(
            f"  {dom:<20} | {d_data['count']:<5} | {d_data['pass_rate']:<10.1%} | "
            f"{d_data['composite_score']:<10.3f} | {d_data['production_build_rate']:<10.1%}"
        )
    print("=" * 75)
    print(f"Full report exported to: {output_report_path}")

    # Anti-Template-Collapse & Diversity Evaluation Breakdown (Issue #27)
    div_eval = summary.get("diversity_evaluation", {})
    if div_eval:
        print("\n" + "=" * 75)
        print("ANTI-TEMPLATE-COLLAPSE & DIVERSITY EVALUATION (Issue #27)")
        print("=" * 75)
        print(f"Total Sites Evaluated:        {div_eval.get('total_sites', 0)}")
        print(f"Overall Site Diversity Score: {div_eval.get('overall_diversity_score', 0.0):.3f}")
        pass_status = "PASS (Diverse)" if div_eval.get("is_diverse") else "FAIL (Template Collapse Detected)"
        print(f"Diversity Gate Status:        {pass_status}")
        flags = div_eval.get("collapse_flags", [])
        print(f"Active Collapse Flags:        {len(flags)}")
        print("-" * 75)
        print("10-DIMENSION DIVERSITY BREAKDOWN:")
        print(f"  {'Dimension':<28} | {'Entropy':<8} | {'Simpson':<8} | {'Dominant Pattern':<22} | {'Ratio':<6}")
        print("  " + "-" * 78)
        dom_patterns = div_eval.get("dominant_patterns", {})
        entropies = div_eval.get("dimension_entropies", {})
        simpsons = div_eval.get("dimension_simpson_indices", {})
        for dim in DIVERSITY_DIMENSIONS:
            ent = entropies.get(dim, 0.0)
            simp = simpsons.get(dim, 0.0)
            pat_info = dom_patterns.get(dim, {})
            pat = pat_info.get("pattern", "unknown")[:22]
            pct = pat_info.get("percentage", 0.0)
            print(f"  {dim:<28} | {ent:<8.3f} | {simp:<8.3f} | {pat:<22} | {pct:>5.1f}%")
        print("-" * 75)
        print("COLLAPSE FLAGS (>80% Dominance):")
        if flags:
            for f_msg in flags:
                print(f"  [!] {f_msg}")
        else:
            print("  [PASS] None detected - generated site batch satisfies anti-template-collapse standards.")
        print("=" * 75)

    # Separate 3D vs Normal DOM Site Evaluation (Issue #28)
    dom_summary = summary.get("dom_sites_summary", {})
    t3d_summary = summary.get("three_d_sites_summary", {})
    if t3d_summary.get("total_sites", 0) > 0:
        print("\n" + "=" * 75)
        print("FIRST-CLASS 3D CAPABILITY EVALUATION (Issue #28)")
        print("=" * 75)
        print(f"Normal DOM Sites Evaluated:   {dom_summary.get('total_sites', 0)}")
        print(f"  DOM Pass Rate:              {dom_summary.get('pass_rate', 0.0):.1%}")
        print(f"  DOM Composite Score:        {dom_summary.get('composite_score_mean', 0.0):.3f}")
        print("-" * 75)
        print(f"3D Sites Evaluated:           {t3d_summary.get('total_sites', 0)}")
        print(f"  3D Pass Rate:               {t3d_summary.get('pass_rate', 0.0):.1%}")
        print(f"  3D Composite Score:         {t3d_summary.get('composite_score_mean', 0.0):.3f}")
        print(f"  3D Performance Pass Rate:   {t3d_summary.get('three_d_performance_pass_rate', 0.0):.1%}")
        print("  6-Rule Performance Checks:")
        breakdown = t3d_summary.get("performance_checks_breakdown", {})
        for chk, rate in breakdown.items():
            print(f"    - {chk:<35}: {rate:.1%}")
        print("=" * 75)

    # Cleanup temporary workspace
    if workspace_base.exists() and not keep_workspace:
        try:
            shutil.rmtree(workspace_base)
        except Exception:
            pass

    return summary


def main():
    parser = argparse.ArgumentParser(description="Dedicated Full-Website Benchmark Runner (Issue #25)")
    parser.add_argument("--model", type=str, default="base-model", help="Path to model directory")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH, help="Path to benchmark JSONL")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_REPORT, help="Path to export report JSON")
    parser.add_argument("--mock", action="store_true", help="Run harness with mock site generator (fast CI/test)")
    parser.add_argument("--domain", type=str, default=None, help="Filter by specific domain (e.g. SaaS, portfolio)")
    parser.add_argument("--subset", type=int, default=None, help="Limit number of prompts")
    parser.add_argument("--live-browser", action="store_true", help="Run live headless Chromium browser check")
    parser.add_argument("--keep-workspace", action="store_true", help="Preserve generated files for diagnostics")
    parser.add_argument("--workspace-dir", type=Path, default=None,
                        help="Use a new, empty workspace directory for this evaluation")

    args = parser.parse_args()
    output_path = DEFAULT_MOCK_OUTPUT_REPORT if args.mock and args.output == DEFAULT_OUTPUT_REPORT else args.output

    try:
        summary = run_full_site_benchmark(
            model_path=args.model,
            benchmark_file=args.benchmark,
            output_report_path=output_path,
            mock=args.mock,
            domain_filter=args.domain,
            subset=args.subset,
            live_browser_check=args.live_browser,
            keep_workspace=args.keep_workspace,
            workspace_base=args.workspace_dir,
        )
        sys.exit(0 if summary.get("overall_pass_rate", 0.0) >= 0.70 else 1)
    except Exception as exc:
        print(f"Benchmark error: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()
