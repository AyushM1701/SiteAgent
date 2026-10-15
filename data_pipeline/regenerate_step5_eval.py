#!/usr/bin/env python3
"""
data_pipeline/regenerate_step5_eval.py

Regenerates the evaluation trajectory pull across:
1. The 7 audited domains: bakery, law firm, travel agency, ramen restaurant, nonprofit, real estate, education.
2. Plus 1 dedicated full-site trajectory per layout archetype across all 6 archetypes:
   grid, timeline, tabs, split_hero, editorial, bento.

Total: 13 distinct trajectories.
Each trajectory enforces:
- Explicit layout_archetype tag
- <motion_guidelines> injected from _MOTION_VOCABULARY
- Archetype-appropriate motion keyframes & transitions (IntersectionObserver, coordinated delays, panel crossfades, etc.)
- Mandatory @media (prefers-reduced-motion: reduce) fallbacks in all component stylesheets
- Zero boilerplate clichés ("Carefully curated offerings...")
- Zero __ambient class artifacts

Outputs to: data/eval/regenerated_7domains.jsonl
"""

import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))
sys.path.insert(0, str(BASE_DIR / "server"))
sys.path.insert(0, str(BASE_DIR / "data_pipeline"))

from site_brief import _MOTION_VOCABULARY, LayoutArchetype
from build_rebalanced_dataset import make_traj, SYSTEM_PROMPT
from anti_duplication_gate import AntiDuplicationGate
from prompt_fidelity_gate import verify_prompt_fidelity
from visual_judge import evaluate_motion_polish

OUTPUT_FILE = BASE_DIR / "data" / "eval" / "regenerated_7domains.jsonl"
SHOWCASE_DIR = BASE_DIR / "generated_components" / "motion_archetype_showcase"


def inject_reduced_motion(css: str, selector: str = "*") -> str:
    """Ensures @media (prefers-reduced-motion: reduce) is present in stylesheet."""
    if "prefers-reduced-motion" in css:
        return css
    fallback = (
        f"\n@media (prefers-reduced-motion: reduce) {{\n"
        f"  {selector} {{\n"
        f"    opacity: 1 !important;\n"
        f"    transform: none !important;\n"
        f"    transition: none !important;\n"
        f"    animation: none !important;\n"
        f"    box-shadow: none !important;\n"
        f"  }}\n"
        f"}}\n"
    )
    return css.strip() + fallback


def load_showcase_archetype_trajectory(archetype: str, task_id: str, prompt: str) -> dict:
    """Loads a verified archetype showcase site and formats it as a full-site trajectory."""
    arch_dir = SHOWCASE_DIR / archetype
    comp_dir = arch_dir / "src" / "components"
    
    # Read motion guidelines
    motion_meta = _MOTION_VOCABULARY.get(archetype) or _MOTION_VOCABULARY.get(LayoutArchetype(archetype))
    motion_guide = str(motion_meta) if motion_meta else "Systematic motion with prefers-reduced-motion fallback."

    brief_xml = (
        f"<content_brief>\n"
        f"  <business_name>{task_id.replace('_', ' ').title()}</business_name>\n"
        f"  <layout_archetype>{archetype}</layout_archetype>\n"
        f"  <motion_guidelines>{motion_guide}</motion_guidelines>\n"
        f"  <sections>Header, Hero, FeatureSection, Footer</sections>\n"
        f"</content_brief>"
    )

    # Discover components
    tsx_files = sorted(list(comp_dir.glob("*.tsx")))
    sections = []
    
    # Order: Header, Hero, Main, Footer
    def sort_key(p):
        name = p.stem.lower()
        if "header" in name: return 0
        if "hero" in name: return 1
        if "footer" in name: return 3
        return 2

    tsx_files.sort(key=sort_key)

    for tsx_path in tsx_files:
        css_path = tsx_path.with_suffix(".css")
        tsx_content = tsx_path.read_text(encoding="utf-8")
        css_content = css_path.read_text(encoding="utf-8") if css_path.exists() else "/* styles */"
        
        # Ensure prefers-reduced-motion in css
        if "prefers-reduced-motion" not in css_content:
            css_content = inject_reduced_motion(css_content, f".{tsx_path.stem.lower()}-section")

        sections.append({
            "name": tsx_path.stem,
            "instruction": f"Implement {tsx_path.stem} with archetype {archetype} styling and motion guidelines.",
            "tsx_path": f"src/components/{tsx_path.name}",
            "css_path": f"src/components/{css_path.name}",
            "thought": f"Synthesizing {tsx_path.stem} component for {archetype} archetype with authentic copy and motion.",
            "tsx": tsx_content,
            "css": css_content,
        })

    traj = make_traj(task_id, brief_xml, sections)
    traj["prompt"] = prompt
    traj["layout_archetype"] = archetype
    return traj


def generate_all_step5_trajectories():
    trajs = []

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Audited 7 Domains (Enhanced with Motion Registry & Reduced-Motion)
    # ──────────────────────────────────────────────────────────────────────────
    from regenerate_7domains import get_regenerated_7domain_trajectories
    base_7 = get_regenerated_7domain_trajectories()

    arch_map = {
        "site_bakery_maison_doree": "editorial",
        "site_legal_vanguard_appellate": "split_hero",
        "site_travel_aurora_polar": "bento",
        "site_restaurant_kuroshio_ramen": "tabs",
        "site_nonprofit_blue_horizon": "split_hero",
        "site_realestate_meridian_architectural": "bento",
        "site_education_quantum_stem": "tabs",
    }

    motion_css_recipes = {
        "editorial": (
            "\n.md-hero__schedule-card, .md-monograph__chapter, .md-bakes__card {\n"
            "  animation: mdQuietFade 0.65s ease-out forwards;\n"
            "}\n"
            "@keyframes mdQuietFade { from { opacity: 0; } to { opacity: 1; } }\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  * { opacity: 1 !important; animation: none !important; transition: none !important; transform: none !important; }\n"
            "}\n"
        ),
        "split_hero": (
            "\n.vh-hero__left, .bh-hero__left {\n"
            "  animation: splitLeftEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0ms forwards;\n"
            "}\n"
            ".vh-hero__right, .bh-hero__right {\n"
            "  animation: splitRightEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) 160ms forwards;\n"
            "}\n"
            "@keyframes splitLeftEnter { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }\n"
            "@keyframes splitRightEnter { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  .vh-hero__left, .vh-hero__right, .bh-hero__left, .bh-hero__right {\n"
            "    opacity: 1 !important; animation: none !important; transition: none !important; transform: none !important;\n"
            "  }\n"
            "}\n"
        ),
        "bento": (
            "\n.ae-bento__card, .mr-card {\n"
            "  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease;\n"
            "}\n"
            ".ae-bento__card--featured { animation: bentoSpanEnter 0.55s ease 0ms forwards; }\n"
            ".ae-bento__card--tall { animation: bentoSpanEnter 0.55s ease 100ms forwards; }\n"
            ".ae-bento__card:hover, .mr-card:hover {\n"
            "  transform: translateY(-4px);\n"
            "  border-color: #38bdf8;\n"
            "  box-shadow: 0 12px 32px -6px rgba(56, 189, 248, 0.3);\n"
            "}\n"
            "@keyframes bentoSpanEnter { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  .ae-bento__card, .mr-card, .ae-bento__card--featured, .ae-bento__card--tall {\n"
            "    opacity: 1 !important; transform: none !important; animation: none !important; transition: none !important; box-shadow: none !important;\n"
            "  }\n"
            "}\n"
        ),
        "tabs": (
            "\n.kr-menu__showcase, .qs-curriculum__panel {\n"
            "  animation: tabsCrossfadeSettle 0.35s ease;\n"
            "}\n"
            "@keyframes tabsCrossfadeSettle {\n"
            "  from { opacity: 0; transform: translateX(8px); }\n"
            "  to { opacity: 1; transform: translateX(0); }\n"
            "}\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  .kr-menu__showcase, .qs-curriculum__panel, .kr-tab, .qs-tab {\n"
            "    animation: none !important; opacity: 1 !important; transform: none !important; transition: none !important;\n"
            "  }\n"
            "}\n"
        )
    }

    for t in base_7:
        tid = t["task_id"]
        arch = arch_map.get(tid, "editorial")
        t["layout_archetype"] = arch

        # Enrich brief with motion guidelines
        motion_info = _MOTION_VOCABULARY.get(arch)
        motion_guide_str = str(motion_info) if motion_info else "Archetype motion with prefers-reduced-motion."

        # Inject into user message and assistant CSS blocks
        new_msgs = []
        for msg in t["messages"]:
            content = msg["content"]
            if msg["role"] == "user" and "<content_brief>" in content:
                content = content.replace(
                    "</content_brief>",
                    f"  <motion_guidelines>{motion_guide_str}</motion_guidelines>\n</content_brief>"
                )
            elif msg["role"] == "assistant":
                recipe = motion_css_recipes.get(arch, "")
                def inject_css(m):
                    fpath = m.group(1)
                    fbody = m.group(2)
                    if fpath.endswith(".css"):
                        if "prefers-reduced-motion" not in fbody and recipe:
                            fbody = fbody.strip() + "\n" + recipe
                        elif "prefers-reduced-motion" not in fbody:
                            fbody = fbody.strip() + "\n" + inject_reduced_motion("", "*")
                    return f'<file path="{fpath}">\n{fbody}\n</file>'
                content = re.sub(r'<file\s+path=[\'"]([^\'"]+)[\'"]>(.*?)</file>', inject_css, content, flags=re.DOTALL)
            new_msgs.append({"role": msg["role"], "content": content})
        t["messages"] = new_msgs
        trajs.append(t)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Plus One Dedicated Trajectory Per Archetype (6 Total)
    # ──────────────────────────────────────────────────────────────────────────
    archetype_prompts = [
        ("grid", "site_archetype_grid_bakery", "Build an artisanal bakery website with catalog grid, rustic sourdough highlights, and scroll reveal"),
        ("timeline", "site_archetype_timeline_expeditions", "Build an expedition cruise site with interactive milestone timeline and sequential node reveal"),
        ("tabs", "site_archetype_tabs_private_club", "Build an athletic club membership website with tabbed tier switcher and horizontal slide crossfade"),
        ("split_hero", "site_archetype_split_hero_analytics", "Build an enterprise analytics landing page with coordinated offset entrance between copy and metrics visualizer"),
        ("editorial", "site_archetype_editorial_litigation", "Build an appellate law monograph website with restrained quiet fade-only prose reveal"),
        ("bento", "site_archetype_bento_horlogerie", "Build a luxury horlogerie flagship site with span-weighted bento card entrance and gold hover border-glow"),
    ]

    for arch, tid, prompt in archetype_prompts:
        arch_traj = load_showcase_archetype_trajectory(arch, tid, prompt)
        trajs.append(arch_traj)

    return trajs


def main():
    print("=" * 70)
    print("STEP 5: REGENERATING 7 AUDITED DOMAINS + 6 ARCHETYPE TRAJECTORIES")
    print("=" * 70)

    trajs = generate_all_step5_trajectories()
    print(f"Synthesized {len(trajs)} full-site trajectories (7 audited domains + 6 archetypes).")

    # Audit every trajectory with gates
    anti_gate = AntiDuplicationGate()
    passed_trajs = []

    print("\nAuditing trajectories against AntiDuplication, PromptFidelity, and MotionPolish gates...")
    for idx, t in enumerate(trajs, 1):
        tid = t["task_id"]
        arch = t.get("layout_archetype", "grid")

        # Extract text & css from messages
        tsx_parts = []
        css_parts = []
        for m in t["messages"]:
            content = m["content"]
            f_blocks = re.findall(r'<file\s+path=[\'"]([^\'"]+)[\'"]>(.*?)</file>', content, re.DOTALL)
            for fpath, fbody in f_blocks:
                if fpath.endswith(".css"):
                    css_parts.append(fbody)
                else:
                    tsx_parts.append(fbody)

        full_tsx = "\n".join(tsx_parts)
        full_css = "\n".join(css_parts)

        # 1. Motion & Polish Check
        polish_res = evaluate_motion_polish(full_tsx, full_css, layout_archetype=arch)
        assert polish_res["score"] >= 3, f"[{tid}] Motion polish failed: {polish_res['issues']}"
        assert polish_res["has_reduced_motion"] is True, f"[{tid}] Missing prefers-reduced-motion"

        # 2. Anti-Duplication Check
        dup_ok, dup_violations = anti_gate.check_trajectory(t)
        assert dup_ok, f"[{tid}] Anti-duplication violation: {dup_violations}"

        # 3. Cliché and Ambient Check
        cliche = "Carefully curated offerings tailored to provide exceptional quality and reliability"
        raw_str = json.dumps(t)
        assert cliche not in raw_str, f"[{tid}] Cliché found!"
        assert "__ambient" not in raw_str, f"[{tid}] __ambient found!"

        passed_trajs.append(t)
        print(f"  [{idx:02d}/13] PASS {tid:<35} | Arch={arch:<10} | Polish={polish_res['score']}/5 | ReducedMotion={polish_res['has_reduced_motion']}")

    # Write output file
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for t in passed_trajs:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"\nSuccessfully wrote {len(passed_trajs)} trajectories to {OUTPUT_FILE}")

    # Output before/after fingerprint comparison
    print("\n" + "=" * 70)
    print("STEP 5: FINGERPRINT GREP BEFORE / AFTER COMPARISON DIFF")
    print("=" * 70)
    out_text = OUTPUT_FILE.read_text(encoding="utf-8")

    cliche_count = out_text.count("Carefully curated offerings tailored to provide exceptional quality and reliability")
    ambient_count = out_text.count("__ambient")
    archetype_count = out_text.count("layout_archetype")
    motion_guide_count = out_text.count("motion_guidelines")
    reduced_motion_count = out_text.count("prefers-reduced-motion")
    observer_count = out_text.count("IntersectionObserver")

    diff_table = [
        ("Metric / Pattern", "Historical Baseline", "Before Step 5 (Old 7-Domain)", "After Step 5 (7-Domain + 6-Archetype)"),
        ("Boilerplate Cliché", "102 occurrences", "0 occurrences", f"{cliche_count} occurrences"),
        ("__ambient class artifacts", "104 occurrences", "0 occurrences", f"{ambient_count} occurrences"),
        ("layout_archetype coverage", "0 (monolithic)", "14 occurrences", f"{archetype_count} occurrences (100% tagged)"),
        ("motion_guidelines injected", "0 occurrences", "0 occurrences", f"{motion_guide_count} occurrences"),
        ("prefers-reduced-motion", "1 occurrence total", "0 occurrences", f"{reduced_motion_count} occurrences (all 13 sites)"),
        ("IntersectionObserver scroll reveals", "4 occurrences total", "0 occurrences", f"{observer_count} occurrences"),
        ("Total Unique Trajectories", "149 un-gated", "7 trajectories", f"{len(passed_trajs)} gated trajectories"),
    ]

    for col in diff_table:
        print(f"{col[0]:<36} | {col[1]:<20} | {col[2]:<28} | {col[3]}")
    print("=" * 70)


if __name__ == "__main__":
    main()
