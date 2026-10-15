"""One deterministic held-out hero probe; never substitutes for visual evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from agent import AgentModelRunner
from agent_protocol import SITE_AGENT_SYSTEM_PROMPT, parse_agent_output, WriteSiteAction
from site_quality import prepare_site_quality
from evaluate import run_command


def evaluate(model_path, output):
    output.mkdir(parents=True, exist_ok=True)
    prompt = ('Build only the Hero section for Vela, a fictional developer workspace. '
              'Headline: Give your ideas form. Use a two-column layout, a working anchor CTA '
              'to #workflow, and the supplied 3D PremiumScene component. '
              'Write src/components/Hero.tsx and Hero.css. Export default function Hero. '
              'Do not invent metrics or customers. Support 375px screens and reduced motion.')
    instructions, _ = prepare_site_quality(prompt, output)
    runner = AgentModelRunner(str(model_path), max_seq_length=8192)
    start = time.monotonic()
    response = runner.generate_turn(0, [{"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
                                      {"role": "user", "content": prompt + "\n" + instructions}],
                                    "Hero", max_new_tokens=2048, temperature=0)
    (output / "response.txt").write_text(response, encoding="utf-8")
    turn = parse_agent_output(response)
    files = dict(turn.action.files) if isinstance(turn.action, WriteSiteAction) else {}
    allowed = {"src/components/Hero.tsx", "src/components/Hero.css"}
    for name, content in files.items():
        if name in allowed:
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    code = files.get("src/components/Hero.tsx", "")
    css = files.get("src/components/Hero.css", "")
    compiled = False
    diagnostics = "No expected Hero.tsx generated"
    if code:
        result = run_command(["npx", "tsc", "--noEmit", "--jsx", "react-jsx", "--target", "ES2022",
                              "--moduleResolution", "bundler", "--esModuleInterop", "--skipLibCheck",
                              str((output / "src/components/Hero.tsx").resolve()), "css.d.ts"], cwd=ROOT)
        compiled = result.returncode == 0
        diagnostics = result.stdout + result.stderr
    weights = model_path / "adapter_model.safetensors"
    report = {"model": str(model_path), "adapter_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
              "prompt": prompt, "max_new_tokens": 2048, "temperature": 0,
              "elapsed_seconds": round(time.monotonic() - start, 2), "typecheck": compiled,
              "expected_files": allowed <= set(files), "uses_3d_primitive": "<PremiumScene" in code,
              "has_responsive_rule": "@media" in css, "diagnostics": diagnostics,
              "visual_quality": "Not measured by this probe; render and review separately."}
    report['closed_envelope'] = response.count('</file>') == 2 and response.count('</tool_call>') == 1
    report['probe_pass'] = compiled and allowed <= set(files) and report['closed_envelope']
    if compiled and allowed <= set(files):
        (output / "package.json").write_text(json.dumps({"private": True, "type": "module", "scripts": {"dev": "vite"}}), encoding="utf-8")
        (output / "index.html").write_text('<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vela probe</title></head><body><div id="root"></div><script type="module" src="/main.tsx"></script></body></html>', encoding="utf-8")
        (output / "main.tsx").write_text('import React from "react"; import {createRoot} from "react-dom/client"; import Hero from "./src/components/Hero"; createRoot(document.getElementById("root")!).render(<><Hero/><section id="workflow">Workflow destination for the hero CTA</section></>);', encoding="utf-8")
        from visual_judge import take_screenshot
        screenshot = take_screenshot(output.resolve(), output_path=(output / "probe.webp").resolve())
        report["screenshot"] = str(screenshot) if screenshot else None
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.model, args.output)
