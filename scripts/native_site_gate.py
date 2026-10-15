"""Live native-only smoke gate: three small sites, no source repair or fallback.

This development gate is not a held-out promotion evaluation or a human review.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import socket
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PIPELINE_SOURCES = ('agent/agent.py', 'agent/agent_protocol.py', 'agent/site_prompt.py',
                    'agent/style_ingest.py', 'scripts/native_site_gate.py')

CASES = [
    ('portfolio', 'Claylight', 'A ceramic artist portfolio. Warm ivory and dark terracotta. '
     'Hero introduces Claylight handmade vessels. Work lists Ash Bowl and Fold Vase. '
     'Contact says Commission enquiries welcome; no invented address.', ['hero', 'work', 'contact']),
    ('store', 'Threadleaf', 'A demo stationery store. Pale sage and dark forest green. '
     'Hero introduces Threadleaf. Products lists Notebook at illustrative $12 and Pencil at illustrative $3. '
     'Each product has Add to cart, which updates a visible Cart item count starting at 0. '
     'Cart says Demo only; no checkout or payment.', ['hero', 'products', 'cart']),
    ('unfamiliar', 'Moss Atlas', 'An educational bryophyte observation guide. Cream and dark moss green. '
     'Hero introduces Moss Atlas. Field notes explains observing moss on bark and stone without collecting it. '
     'Checklist has a labelled checkbox Record the habitat which toggles visibly.', ['hero', 'notes', 'checklist']),
]


def assemble(path, files):
    for name, source in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding='utf-8')
    (path / 'package.json').write_text('{"type":"module"}', encoding='utf-8')
    (path / 'index.html').write_text('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Native probe</title><div id="root"></div><script type="module" src="/src/main.tsx"></script></html>', encoding='utf-8')
    (path / 'src/main.tsx').write_text("import React from 'react';import{createRoot}from'react-dom/client';import Main from './components/Main';createRoot(document.getElementById('root')!).render(<Main/>);", encoding='utf-8')
    (path / 'src/globals.d.ts').write_text("declare module '*.css';", encoding='utf-8')
    (path / 'vite.config.mjs').write_text("import{defineConfig}from'vite';import react from'@vitejs/plugin-react';export default defineConfig({plugins:[react()]});", encoding='utf-8')
    commands = {
        'typescript': ['node', str(ROOT / 'node_modules/typescript/bin/tsc'), '--noEmit', '--jsx', 'react-jsx', '--module', 'ESNext', '--moduleResolution', 'bundler', '--target', 'ES2020', '--lib', 'ES2020,DOM', '--skipLibCheck', '--allowSyntheticDefaultImports', 'src/main.tsx', 'src/globals.d.ts'],
        'build': ['node', str(ROOT / 'node_modules/vite/bin/vite.js'), 'build'],
    }
    results = {}
    for name, command in commands.items():
        result = subprocess.run(command, cwd=path, capture_output=True, text=True, timeout=90)
        results[name] = {'passed': result.returncode == 0, 'output': result.stdout + result.stderr}
    return results


def verify_interactions(page, domain):
    """Test requested state, not merely any text change after one click."""
    if domain == 'store':
        def count():
            text = page.locator('#cart').inner_text() if page.locator('#cart').count() else ''
            patterns = (r'cart(?:\s+item)?(?:\s+count)?\s*[:(]?\s*(\d+)',
                        r'items?(?:\s+count)?\s*[:(]?\s*(\d+)', r'(\d+)\s+items?\b')
            match = next((match for pattern in patterns if (match := re.search(pattern,text,re.I))),None)
            return int(match.group(1)) if match else None
        buttons = page.get_by_role('button',name=re.compile(r'add\b.*\bto cart',re.I))
        counts = [count()]
        if buttons.count() != 2 or counts[0] != 0:
            return {'passed':False,'counts':counts,'reason':'Two add controls and visible initial cart count 0 required'}
        for index in (0,1,0):
            buttons.nth(index).click();page.wait_for_timeout(50);counts.append(count())
        return {'passed':counts==[0,1,2,3],'counts':counts}
    if domain == 'unfamiliar':
        boxes = page.get_by_role('checkbox',name='Record the habitat',exact=True)
        if boxes.count()!=1:
            return {'passed':False,'reason':'One checkbox with exact requested accessible name required'}
        states=[boxes.first.is_checked()]
        boxes.first.click();states.append(boxes.first.is_checked())
        boxes.first.click();states.append(boxes.first.is_checked())
        return {'passed':states[0]!=states[1] and states[0]==states[2],'states':states}
    return {'passed':True,'status':'not_requested'}


def browser_check(path, domain, ids):
    from playwright.sync_api import sync_playwright
    required_copy = {
        'portfolio': ('Claylight', 'Ash Bowl', 'Fold Vase', 'Commission enquiries welcome'),
        'store': ('Threadleaf', 'Notebook', '$12', 'Pencil', '$3', 'Demo only'),
        'unfamiliar': ('Moss Atlas', 'bark', 'stone', 'without collecting', 'Record the habitat'),
    }
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', str(path / 'dist')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f'http://127.0.0.1:{port}'
    results = []
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(url, timeout=1).close()
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for label, width, reduced in [('desktop', 1280, False), ('mobile', 390, False), ('reduced_motion', 390, True)]:
                    page = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='reduce' if reduced else 'no-preference')
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(url, wait_until='networkidle')
                    visible = all(page.locator(f'#{section}').count() == 1 and page.locator(f'#{section}').is_visible() for section in ids)
                    navigation = all(page.locator(f'nav a[href="#{section}"]').count() >= 1 for section in ids)
                    body_text = page.locator('body').inner_text().casefold()
                    content = all(fragment.casefold() in body_text for fragment in required_copy[domain])
                    overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 2')
                    behavior = verify_interactions(page,domain)
                    interaction = behavior['passed']
                    page.screenshot(path=str(path / f'{label}.png'), full_page=True)
                    results.append({'viewport': label, 'sections_visible': visible,
                                    'interaction_evidence':behavior,
                                    'navigation_passed': navigation, 'content_passed': content,
                                    'horizontal_overflow': overflow, 'interaction_passed': interaction,
                                    'browser_errors': errors,
                                    'passed': visible and navigation and content and not overflow and interaction and not errors})
                    page.close()
            finally:
                browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--tokens', type=int, default=2400)
    parser.add_argument('--seconds', type=float, default=240)
    parser.add_argument('--domain', choices=[c[0] for c in CASES], help='Diagnostic subset; cannot pass the full training gate')
    args = parser.parse_args()
    import torch
    torch.manual_seed(42)
    from agent.site_prompt import section_output_contract
    from agent.agent import AgentModelRunner, SITE_AGENT_SYSTEM_PROMPT, parse_agent_output
    from agent.agent_protocol import site_envelope_errors
    from agent.style_ingest import check_css_selector_coverage, check_css_syntactic_completeness
    from training.preflight import sha256
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    pipeline_sources = {name: sha256(ROOT / name) for name in PIPELINE_SOURCES}
    runner = AgentModelRunner(args.model, max_seq_length=8192)
    model_dir = Path(args.model).resolve()
    identity_files = sorted(model_dir.glob('*.safetensors')) + [model_dir / 'tokenizer_config.json']
    identity_files += [p for p in (model_dir / 'config.json', model_dir / 'adapter_config.json') if p.exists()]
    adapter_file = model_dir / 'adapter_model.safetensors'
    report = {'provenance': 'live_model_native_development_gate', 'model': str(model_dir),
        'adapter_sha256': sha256(adapter_file) if adapter_file.exists() else None,
        'model_files': {p.name: sha256(p) for p in identity_files},
        'pipeline_sources': pipeline_sources, 'seed': 42,
        'repair_count': 0, 'fallback_count': 0, 'cases': [], 'passed': False}
    for index, (domain, title, brief, ids) in enumerate(CASES):
        if args.domain and domain != args.domain:
            continue
        torch.manual_seed(42 + index)
        path = output / domain
        path.mkdir()
        runner.generation_log_dir = path / 'turns'
        prompt = (f'Build a small complete single-page website: {brief} '
            f'Use one self-contained component Main in src/components/Main.tsx plus Main.css. '
            f'Include exactly three visible sections with ids {", ".join(ids)} and a navigation link to each. '
            'Export named and default Main. Use ONLY scoped plain CSS: define every class you use. '
            'No fonts, images, external URLs, SVG, libraries, or Tailwind. Keep content short and accurate. '
            'Responsive layout, readable dark text on light backgrounds, focus indicators. '
            'Keep all source under 1500 tokens total. Close both files and the tool call.\n'
            + section_output_contract('Main'))
        response = runner.generate_turn(index, [{'role': 'system', 'content': SITE_AGENT_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], 'Main', max_new_tokens=args.tokens, max_time_seconds=args.seconds, temperature=.25)
        (path / 'response.txt').write_text(response, encoding='utf-8')
        action = parse_agent_output(response).action
        pairs = getattr(action, 'files', [])
        files = dict(pairs)
        expected = {'src/components/Main.tsx', 'src/components/Main.css'}
        errors = site_envelope_errors(response)
        if set(files) != expected or len(pairs) != 2:
            errors.append('Expected exactly Main.tsx and Main.css')
        tsx, css = files.get('src/components/Main.tsx', ''), files.get('src/components/Main.css', '')
        if not tsx.strip() or not css.strip():
            errors.append('Empty source or CSS')
        if not re.search(r'''import\s*["']\./Main\.css["']''', tsx):
            errors.append('Paired CSS is not imported by Main.tsx')
        coverage, missing = check_css_selector_coverage(tsx, css)
        if not coverage:
            errors.append(f'Missing CSS: {missing}')
        syntax, css_errors = check_css_syntactic_completeness(css)
        errors.extend(css_errors)
        item = {'domain': domain, 'title': title, 'errors': errors, 'stop_reason': runner.last_generation_diagnostics['stop_reason'], 'generated_tokens': runner.last_generation_tokens, 'passed': False}
        if set(files) == expected:
            try:
                item['compilation'] = assemble(path, files)
                if item['compilation']['build']['passed']:
                    item['browser'] = browser_check(path, domain, ids)
                item['passed'] = not errors and all(c['passed'] for c in item['compilation'].values()) and bool(item.get('browser')) and all(c['passed'] for c in item['browser'])
            except Exception as exc:
                errors.append(f'{type(exc).__name__}: {exc}')
        report['cases'].append(item)
        item['artifacts'] = {file.relative_to(path).as_posix(): sha256(file)
            for file in path.rglob('*') if file.is_file() and (file.suffix in ('.png', '.tsx', '.css') or file.name == 'response.txt')}
        report['passed'] = len(report['cases']) == len(CASES) and all(c['passed'] for c in report['cases'])
        (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(item), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
