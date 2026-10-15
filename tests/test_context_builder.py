"""
tests/test_context_builder.py - Comprehensive Unit & Integration Tests for ContextBuilder

Tests the 8-tier context priority hierarchy, token budgeting, dynamic surplus
reallocation, and repository bounding:
1. Priority 1: Selected element (preview selection)
2. Priority 2: Explicit @mentions
3. Priority 3: Semantic code search
4. Priority 4: Recently changed files
5. Priority 5: Dependency-related files
6. Priority 6: Project metadata & package.json summary
7. Priority 7: Compiler / runtime diagnostics
8. Priority 8: Recent conversation history
9. Token budget enforcement & dynamic surplus reallocation
10. Whole-repository exclusion / bounded file excerpts
"""

import json
import tempfile
from pathlib import Path

from agent.context_builder import (
    ContextBuilder,
    TokenBudget,
    TokenUsage,
    bounded_excerpt,
    estimate_tokens,
    extract_dependencies,
    extract_search_terms,
    search_codebase,
)
from server.sessions import Session, SessionManager


# ── 1. Priority 1: Selected Element ──────────────────────────────────────────

def test_priority_1_selected_element():
    builder = ContextBuilder()
    files = {
        "src/components/Hero.tsx": "export const Hero = () => <section id='hero'>Hero</section>;",
        "src/components/Navbar.tsx": "export const Navbar = () => <nav className='navbar'>Nav</nav>;",
        "src/components/Footer.tsx": "export const Footer = () => <footer>Foot</footer>;",
    }
    preview_selection = {
        "component": "Navbar",
        "selector": ".navbar",
        "tag": "nav",
        "text": "Nav",
    }

    resolved = builder.resolve_context_files(
        all_files=files,
        instruction="Make this element sticky and transparent",
        preview_selection=preview_selection,
    )

    selected_paths = [p for p, _ in resolved["selected"]]
    assert "src/components/Navbar.tsx" in selected_paths
    assert any("Priority 1" in note for note in resolved["priority_notes"])

    # Verify formatting in built context
    session = Session(session_id="1789000000_111111", title="TestApp", preview_selection=preview_selection)
    built = builder.build_context(
        session=session,
        new_instruction="Make this element sticky",
        target_files=resolved["selected"],
    )
    assert "<selected_element>" in built.prompt_text
    assert "Component: Navbar" in built.prompt_text
    assert "Selector: .navbar" in built.prompt_text


# ── 2. Priority 2: Explicit @mentions ────────────────────────────────────────

def test_priority_2_explicit_mentions():
    builder = ContextBuilder()
    files = {
        "src/components/Pricing.tsx": "export const Pricing = () => <div>$29/mo</div>;",
        "src/components/Pricing.css": ".pricing { color: gold; }",
        "src/components/About.tsx": "export const About = () => <div>About Us</div>;",
    }

    resolved = builder.resolve_context_files(
        all_files=files,
        instruction="Update @Pricing and change billing cycle to annual",
    )

    selected_paths = [p for p, _ in resolved["selected"]]
    assert "src/components/Pricing.tsx" in selected_paths
    assert any("Priority 2" in note for note in resolved["priority_notes"])


# ── 3. Priority 3: Semantic Code Search ──────────────────────────────────────

def test_priority_3_semantic_code_search():
    builder = ContextBuilder()
    files = {
        "src/components/CartModal.tsx": (
            "import React, { useState } from 'react';\n"
            "export function CartModal() {\n"
            "  const [tax, setTax] = useState(0);\n"
            "  return <div className='checkout-dialog'><button id='checkout-btn'>Pay</button></div>;\n"
            "}"
        ),
        "src/components/Hero.tsx": "export function Hero() { return <h1>Welcome</h1>; }",
        "src/components/Footer.tsx": "export function Footer() { return <footer>Copyright 2026</footer>; }",
    }

    # Test search_codebase directly
    scored = search_codebase("add sales tax calculation to the checkout cart dialog", files)
    assert len(scored) > 0
    top_file, top_score = scored[0]
    assert top_file == "src/components/CartModal.tsx"
    assert top_score > 8.0

    # Test resolve_context_files
    resolved = builder.resolve_context_files(
        all_files=files,
        instruction="add sales tax calculation to the checkout cart dialog",
    )
    selected_paths = [p for p, _ in resolved["selected"]]
    assert "src/components/CartModal.tsx" in selected_paths


# ── 4. Priority 4: Recently Changed Files ────────────────────────────────────

def test_priority_4_recently_changed_files():
    builder = ContextBuilder()
    files = {
        "src/components/Gallery.tsx": "export const Gallery = () => <div className='grid'>Grid</div>;",
        "src/components/Hero.tsx": "export const Hero = () => <div>Hero</div>;",
        "src/components/Contact.tsx": "export const Contact = () => <div>Contact</div>;",
    }

    # With a vague instruction, recently changed file should be prioritized
    resolved = builder.resolve_context_files(
        all_files=files,
        instruction="Refine the layout spacing and borders",
        recent_files=["src/components/Gallery.tsx"],
    )

    selected_paths = [p for p, _ in resolved["selected"]]
    assert "src/components/Gallery.tsx" in selected_paths


# ── 5. Priority 5: Dependency-Related Files ──────────────────────────────────

def test_priority_5_dependency_extraction():
    files = {
        "src/components/Hero.tsx": (
            "import React from 'react';\n"
            "import { Button } from './Button';\n"
            "import './Hero.css';\n"
            "export const Hero = () => <section><Button /></section>;"
        ),
        "src/components/Button.tsx": "export const Button = () => <button>Click</button>;",
        "src/components/Hero.css": ".hero { display: flex; }",
        "App.tsx": (
            "import { Hero } from './src/components/Hero';\n"
            "export default function App() { return <Hero />; }"
        ),
    }

    deps = extract_dependencies("src/components/Hero.tsx", files["src/components/Hero.tsx"], files)
    assert "src/components/Hero.css" in deps
    assert "src/components/Button.tsx" in deps
    assert "App.tsx" in deps


# ── 6. Priority 6: Project Metadata & Package Summary ────────────────────────

def test_priority_6_project_metadata():
    builder = ContextBuilder()
    files = {
        "package.json": json.dumps({
            "name": "cosmic-experience",
            "dependencies": {
                "react": "^19.0.0",
                "three": "^0.160.0",
                "@react-three/fiber": "^8.15.0",
                "lucide-react": "^0.300.0",
            },
            "devDependencies": {
                "vite": "^6.0.0",
                "typescript": "^5.5.0",
            },
        }),
        "src/components/Scene.tsx": "export const Scene = () => <canvas />;",
        "src/components/Overlay.tsx": "export const Overlay = () => <div>HUD</div>;",
    }

    session = Session(session_id="1789000000_222222", title="CosmicApp", mode="site", style_tokens="color-primary: #8a2be2;")
    meta_text = builder.format_project_metadata(session, files, max_tokens=300)

    assert "<project_metadata>" in meta_text
    assert "CosmicApp" in meta_text
    assert "three" in meta_text
    assert "lucide-react" in meta_text
    assert "Scene.tsx" in meta_text


# ── 7. Priority 7: Compiler / Runtime Diagnostics ────────────────────────────

def test_priority_7_diagnostics_formatting():
    builder = ContextBuilder()
    build_state = {
        "typecheck_passed": False,
        "errors": [
            "src/components/Hero.tsx(14,7): error TS2304: Cannot find name 'ThreeFiberCanvas'.",
            "src/components/Hero.tsx(22,12): error TS2339: Property 'nonExistent' does not exist on type 'Props'.",
        ],
        "warnings": [
            "[CSS Lint] Selector '.unknown-class' is missing styling definition.",
        ],
        "runtime_errors": [
            "Uncaught TypeError: window.renderScene is not a function at Scene.tsx:32",
        ],
    }

    diag_text = builder.format_diagnostics(build_state, max_tokens=700)
    assert "<diagnostics>" in diag_text
    assert "TS2304" in diag_text
    assert "ThreeFiberCanvas" in diag_text
    assert "window.renderScene" in diag_text
    assert "[CSS Lint]" in diag_text


# ── 8. Priority 8: Recent Conversation History ───────────────────────────────

def test_priority_8_recent_conversation():
    builder = ContextBuilder()
    history = [
        {"role": "user", "content": "Create a 3D celestial landing page"},
        {"role": "assistant", "summary": "Synthesized 5 sections with R3F scene and stars", "files_touched": ["Scene.tsx"]},
        {"role": "user", "content": "Make the stars rotate faster on drag"},
        {"role": "assistant", "summary": "Added useFrame orbit controls acceleration", "files_touched": ["Scene.tsx"]},
    ]

    hist_text = builder.format_recent_conversation(history, max_tokens=900)
    assert "<recent_conversation>" in hist_text
    assert "Added useFrame orbit controls acceleration" in hist_text
    assert "Make the stars rotate faster on drag" in hist_text


# ── 9. Token Budget Enforcement & Dynamic Surplus Reallocation ───────────────

def test_token_budget_enforcement_and_surplus_reallocation():
    budget = TokenBudget(
        total=8192,
        system_contracts=1000,
        current_instruction=300,
        project_metadata=300,
        selected_files=3000,
        related_files=1600,
        recent_conversation=900,
        build_diagnostics=700,
        reserve=392,
    )
    builder = ContextBuilder(budget=budget)

    # Large target files that test budget limits
    large_ts = "import React from 'react';\n" + "\n".join(f"const item{i} = {i};" for i in range(1500))
    files = {
        "src/components/BigComponent.tsx": large_ts,
        "src/components/Helper.tsx": "export const Helper = () => <span>Help</span>;",
    }

    session = Session(session_id="1789000000_333333", title="BigApp")
    built = builder.build_context(
        session=session,
        new_instruction="Update BigComponent with new styling",
        target_files=[("src/components/BigComponent.tsx", large_ts)],
        diagnostics=None,  # 0 tokens used -> surplus flows to selected_files
    )

    # 1. Total tokens must never exceed total budget
    assert built.token_usage.total <= budget.total

    # 2. Surplus was reallocated: diagnostics was 0, so selected_files received a surplus boost
    assert built.token_usage.build_diagnostics == 0
    assert built.token_usage.selected_files > 0
    assert built.token_usage.reserve == 392


# ── 10. Repository Bounding & No Dump Rule ────────────────────────────────────

def test_repository_bounding_excludes_unrelated_files():
    builder = ContextBuilder()
    files = {
        "src/components/Hero.tsx": "export const Hero = () => <h1>Hero</h1>;",
        "src/components/Unrelated1.tsx": "export const Unrelated1 = () => <div>1</div>;",
        "src/components/Unrelated2.tsx": "export const Unrelated2 = () => <div>2</div>;",
        "src/components/Unrelated3.tsx": "export const Unrelated3 = () => <div>3</div>;",
        "src/components/Unrelated4.tsx": "export const Unrelated4 = () => <div>4</div>;",
        "src/components/Unrelated5.tsx": "export const Unrelated5 = () => <div>5</div>;",
    }

    session = Session(session_id="1789000000_444444", title="MultiComponentApp")
    session.workspace_dir.mkdir(parents=True, exist_ok=True)
    for p, c in files.items():
        (session.workspace_dir / p).parent.mkdir(parents=True, exist_ok=True)
        (session.workspace_dir / p).write_text(c, encoding="utf-8")

    built = builder.build_context(
        session=session,
        new_instruction="Update @Hero with a warmer color gradient",
    )

    # Hero.tsx must be in target files
    assert '<file path="src/components/Hero.tsx">' in built.prompt_text
    # Unrelated files must NOT be dumped into the prompt
    assert '<file path="src/components/Unrelated1.tsx">' not in built.prompt_text
    assert '<file path="src/components/Unrelated5.tsx">' not in built.prompt_text


# ── 11. Bounded Excerpt Skeletonizes Related Files ────────────────────────────

def test_bounded_excerpt_skeletonizes_related_files():
    code = (
        "import React from 'react';\n"
        "import { useState } from 'react';\n\n"
        "export interface CardProps {\n"
        "  title: string;\n"
        "  count: number;\n"
        "}\n\n"
        "export function Card(props: CardProps) {\n"
        "  const [v, setV] = useState(0);\n"
        "  // lots of lines\n"
        + "\n".join(f"  const line{i} = {i};" for i in range(100)) + "\n"
        "  return <div>{props.title}</div>;\n"
        "}\n"
    )

    # Skeletonize as related file with small max_tokens
    excerpt = bounded_excerpt("Card.tsx", code, max_tokens=100, is_primary=False)
    assert "import React from 'react';" in excerpt
    assert "export interface CardProps" in excerpt
    assert "title: string;" in excerpt
    assert "omitted for token budget" in excerpt


# ── 12. SessionManager Integration Test ──────────────────────────────────────

def test_session_manager_integration():
    sm = SessionManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_555555", title="Button", mode="component", workspace_dir=tmp_dir)
        (Path(tmp_dir) / "Button.tsx").write_text("export const Button = () => <button>Click</button>;", encoding="utf-8")
        (Path(tmp_dir) / "Button.module.css").write_text(".btn { border-radius: 4px; }", encoding="utf-8")

        # 1. resolve_target_files finds Button.tsx and companion CSS
        targets = sm.resolve_target_files(session, "Make the button rounded with 16px border radius")
        target_names = [p for p, _ in targets]
        assert "Button.tsx" in target_names
        assert "Button.module.css" in target_names

        # 2. build_follow_up_context formats prioritized prompt text
        context_str = sm.build_follow_up_context(session, "Make the button rounded", targets)
        assert "ORIGINAL TASK" in context_str or "USER INSTRUCTION" in context_str
        assert '<file path="Button.tsx">' in context_str

        # 3. build_follow_up_context_detailed returns token usage metrics
        detailed = sm.build_follow_up_context_detailed(session, "Make the button rounded", targets)
        assert detailed.token_usage.total > 0
        assert detailed.token_usage.total <= 8192
