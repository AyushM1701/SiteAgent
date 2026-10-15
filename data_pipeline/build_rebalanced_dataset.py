#!/usr/bin/env python3
"""
data_pipeline/build_rebalanced_dataset.py

Builds 12 production-grade, hand-authored full-site trajectories specifically targeting
empty cells in the Archetype x Domain matrix, prioritizing structural trust-tier features.
"""

import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_PATH = BASE_DIR / "data" / "site_trajectories_rebalanced.jsonl"

SYSTEM_PROMPT = """You are an expert autonomous React, TypeScript, and CSS coding agent specialising in full-page website composition.
Your objective is to build a complete, visually rich, multi-section website from a structured content brief, one section at a time.

You interact with an automated build environment using structured XML tags:

1. <thought>
Explain your plan for the current section, describe styling decisions, and acknowledge the content brief.
</thought>

2. <tool_call name="write_site">
<file path="src/components/Header.tsx">
// Complete React + TypeScript component for this section
</file>
<file path="src/components/Header.css">
/* Required CSS — NEVER leave empty. Every section MUST have visual styles. */
</file>
</tool_call>
Writes ONE section (one .tsx file + one .css file) per turn. The environment will confirm what was written and instruct you on the next section.

3. <finish>
Brief summary of all sections produced.
</finish>
Call this ONLY after the environment confirms all required sections are complete.

OPERATING GUIDELINES:
- Every turn: output <thought> first, then ONE <tool_call name="write_site"> with exactly one .tsx and one .css <file> pair.
- CSS is MANDATORY. Every section must have real visual rules (colors, typography, spacing, layout). Empty or placeholder CSS is a hard failure.
- Use modern CSS: flexbox/grid for layout, CSS custom properties for design tokens, responsive units (rem/%, vw).
- Write production-quality TypeScript. Keep all types inline — no third-party imports except react and react-dom.
- Reconcile prompt and brief: Honor the content brief data (business name, tagline, tiers) while incorporating any specific interactive capabilities requested in the user prompt (e.g. dark/light mode toggle in Header, active category tabs in Features, annual/monthly billing toggle in Pricing, and next/prev carousel pagination in Testimonials).
- Real Interactive State: For interactive sections (pricing toggles, tab filtering, carousels, mobile menus), write functional React state (`useState`, `useEffect`) rather than static unclickable elements.
- Clean Iconography: Use clean inline SVGs or standard FontAwesome icon classes (e.g. `fa-solid fa-check`, `fa-solid fa-bolt`, `fa-solid fa-star`, `fa-brands fa-github`).
- Do NOT output markdown code fences (```) around your <tool_call> tags.
- Do NOT combine multiple sections into one turn — one section per tool_call only."""


def make_traj(task_id: str, brief_xml: str, sections: list) -> dict:
    first_sec = sections[0]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Build a complete website for the following brief.\n\n{brief_xml}\n\n"
                f"You will build the site ONE SECTION AT A TIME. Start with the first section now.\n\n"
                f"FIRST SECTION REQUIRED: Write the {first_sec['name']} section: {first_sec['instruction']} "
                f"Files: {first_sec['tsx_path']} + {first_sec['css_path']}"
            )
        }
    ]

    for i, s in enumerate(sections):
        # Assistant write_site turn
        assistant_content = (
            f"<thought>\n{s['thought']}\n</thought>\n"
            f'<tool_call name="write_site">\n'
            f'<file path="{s["tsx_path"]}">\n{s["tsx"].strip()}\n</file>\n'
            f'<file path="{s["css_path"]}">\n{s["css"].strip()}\n</file>\n'
            f"</tool_call>"
        )
        messages.append({"role": "assistant", "content": assistant_content})

        is_last = (i == len(sections) - 1)
        if not is_last:
            nxt = sections[i + 1]
            obs = (
                f'<observation status="ok">\n'
                f"[Files accepted]:\n"
                f"  ✓ {s['tsx_path']}\n"
                f"  ✓ {s['css_path']}\n\n"
                f"[NEXT SECTION REQUIRED]: Write the {nxt['name']} section: {nxt['instruction']} "
                f"Files: {nxt['tsx_path']} + {nxt['css_path']}\n"
                f'Write ONE <tool_call name="write_site"> with exactly one .tsx file and one .css file for this section.\n'
                f"</observation>"
            )
            messages.append({"role": "user", "content": obs})
        else:
            files_list = "\n".join(f"  ✓ {sec['tsx_path']}\n  ✓ {sec['css_path']}" for sec in sections)
            obs = (
                f'<observation status="complete">\n'
                f"[SITE BUILD COMPLETE]: All required sections have been written successfully.\n"
                f"[Files written in this session]:\n{files_list}\n"
                f"Output a <finish> tag with a brief summary of the site you built.\n"
                f"</observation>"
            )
            messages.append({"role": "user", "content": obs})
            finish_msg = (
                f"<thought>\nAll sections for {task_id} have been completed with dedicated structural trust-tier components and responsive layouts.\n</thought>\n"
                f"<finish>\nSuccessfully built the complete website for {task_id}.\n</finish>"
            )
            messages.append({"role": "assistant", "content": finish_msg})

    return {"task_id": task_id, "messages": messages}


def main():
    from rebalanced_fintech import get_fintech_trajectories
    from rebalanced_legal import get_legal_trajectories
    from rebalanced_realestate import get_realestate_trajectories
    from rebalanced_healthcare import get_healthcare_trajectories

    fintech = get_fintech_trajectories()
    legal = get_legal_trajectories()
    realestate = get_realestate_trajectories()
    healthcare = get_healthcare_trajectories()

    all_trajs = fintech + legal + realestate + healthcare
    print(f"[build_rebalanced_dataset] Loaded trajectories:")
    print(f"  Fintech:     {len(fintech)}")
    print(f"  Legal:       {len(legal)}")
    print(f"  Real Estate: {len(realestate)}")
    print(f"  Healthcare:  {len(healthcare)}")
    print(f"  TOTAL:       {len(all_trajs)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for t in all_trajs:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"[build_rebalanced_dataset] Successfully wrote {len(all_trajs)} trajectories to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

