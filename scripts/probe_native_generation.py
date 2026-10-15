"""Small live diagnostic. Saves raw native output; never repairs or promotes it."""
import argparse
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--tokens', type=int, default=1200)
    parser.add_argument('--seconds', type=float, default=180)
    args = parser.parse_args()
    from agent.agent import AgentModelRunner, SITE_AGENT_SYSTEM_PROMPT, parse_agent_output
    from training.preflight import sha256
    runner = AgentModelRunner(args.model, max_seq_length=8192)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    runner.generation_log_dir = output / 'turns'
    prompt = ('Build only Hero for a ceramic artist portfolio named Claylight. '
        'Use a warm ivory background and terracotta type, a heading Claylight, '
        'one sentence about handmade vessels, and a View work anchor to #work. '
        'Return exactly src/components/Hero.tsx and src/components/Hero.css in one '
        'write_site call. Import ./Hero.css. Export named Hero and default Hero. '
        'Use compact, complete plain CSS; no images or libraries. Keep this simple section under 600 tokens.')
    history = [{'role': 'system', 'content': SITE_AGENT_SYSTEM_PROMPT},
               {'role': 'user', 'content': prompt}]
    response = runner.generate_turn(0, history, 'Hero', max_new_tokens=args.tokens,
        max_time_seconds=args.seconds, temperature=.25)
    turn = parse_agent_output(response)
    files = getattr(turn.action, 'files', [])
    paths = [p for p, _ in files]
    report = dict(runner.last_generation_diagnostics)
    weights = Path(args.model) / 'adapter_model.safetensors'
    report.update(adapter_sha256=sha256(weights) if weights.is_file() else None,
        parsed_action=type(turn.action).__name__, paths=paths,
        envelope_complete='</tool_call>' in response,
        css_missing='src/components/Hero.css' not in paths,
        css_import_missing=not re.search(r'''import\s*["']\./Hero\.css["']''', dict(files).get('src/components/Hero.tsx', '')),
        section_mismatch=bool(paths) and any(Path(p).stem != 'Hero' for p in paths),
        native_pair_complete=set(paths) == {'src/components/Hero.tsx', 'src/components/Hero.css'}
            and '</tool_call>' in response)
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (output / 'response.txt').write_text(response, encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('prompt', 'raw_output')}, indent=2))


if __name__ == '__main__':
    main()
