"""Create single-pair full-site turns from scored sites, verifying identical rendered pixels."""

from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
from scripts.build_diverse_curriculum import envelope
from scripts.capture_visual_review import capture
from scripts.native_site_gate import assemble
from scripts.prepare_diverse_review_queue import SilentHandler, interactions
from training.preflight import encode_row, sha256
from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows

SITES = {
    'forma_scroll_v2': ('forma_scroll_v2', ('Hero', 'Collection', 'Contact'),
                        ROOT / 'data/reviewed_full_sites/forma_scroll_v2.jsonl', 'portfolio'),
    'paperkite': ('paperkite', ('Hero', 'Shop', 'About'),
                  ROOT / 'data/reviewed_full_sites/diverse_v1.jsonl', 'ecommerce'),
    'quiethours': ('quiethours', ('Hero', 'Guide', 'Journal'),
                   ROOT / 'data/reviewed_full_sites/diverse_v1.jsonl', 'unfamiliar'),
}
BRIEFS = {
    'forma_scroll_v2': ('An editorial object-design portfolio with warm stone, clay, a large serif '
                        '"Less object. More presence." headline, dimensional CSS sculpture, three work studies, '
                        'working category filters, scroll-linked parallax and staggered reveals, and a fictional '
                        'contact footer without fabricated details. Support reduced motion and responsive layout.'),
    'paperkite': ('An illustrated demo print shop with original CSS poster artwork, Sunroom $24, Blue Hour $28, '
                  'Soft Landing $24, a working additive bag with visible count and total, and an Empty bag action. '
                  'State that no orders, payments, or shipping are processed. Make navigation and mobile layout work.'),
    'quiethours': ('A calm soundwalk journal with CSS moon and layered hills, scroll parallax and guide reveals, '
                   'a labelled 400-character journal form with nonempty validation, Save and Clear actions, and '
                   'an in-memory-only note disclosure. No tracking or microphone. Support reduced motion and mobile.'),
}
OUTPUT = ROOT / 'runs/flattened_reviewed_sites'
BANK = ROOT / 'data/reviewed_full_sites/evidence/flattened_v1'
TARGET = ROOT / 'data/reviewed_full_sites/flattened_v1.jsonl'


@contextmanager
def serving(directory: Path):
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SilentHandler, directory=str(directory)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def flatten(site: str, sections: tuple[str, ...]) -> tuple[str, str]:
    source = ROOT / 'data/diverse_reference/source' / site
    hooks = {'useState', 'useEffect', 'useRef'}
    used = {hook for section in sections for hook in hooks
            if re.search(r'\b' + hook + r'\b', (source / f'{section}.tsx').read_text(encoding='utf-8'))}
    react_import = 'import React' + (',{' + ','.join(sorted(used)) + '}' if used else '') + " from 'react';"
    parts = [react_import, "import './Main.css';"]
    for section in sections:
        text = (source / f'{section}.tsx').read_text(encoding='utf-8')
        lines = [line for line in text.splitlines()
                 if not line.startswith('import ') and not line.startswith('export default ')]
        parts.append('\n'.join(lines))
    wrapper = ("export function Main(){return <><a className=\"reference-skip\" href=\"#reference-main\">"
               "Skip to content</a><main id=\"reference-main\">"
               + ''.join(f'<{section}/>' for section in sections)
               + '</main></>;}\nexport default Main;')
    parts.append(wrapper)
    original_main_css = (ROOT / 'runs/diverse_reference_review' / site / 'src/components/Main.css').read_text(encoding='utf-8')
    css = '\n'.join([original_main_css] + [(source / f'{section}.css').read_text(encoding='utf-8') for section in sections])
    return '\n\n'.join(parts) + '\n', css


def pixel_equivalence(original_url: str, flattened_url: str, folder: Path) -> dict:
    results = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for mode, width in (('desktop', 1280), ('mobile', 390)):
                images = []
                dom = []
                for label, url in (('original', original_url), ('flattened', flattened_url)):
                    page = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                    page.goto(url, wait_until='networkidle')
                    page.wait_for_timeout(600)
                    dom.append(page.locator('#reference-main').evaluate('(element) => element.outerHTML'))
                    filename = folder / f'{mode}_{label}.png'
                    page.screenshot(path=str(filename), full_page=True)
                    images.append(Image.open(filename).convert('RGBA'))
                    page.close()
                difference = ImageChops.difference(images[0], images[1])
                same_pixels = images[0].size == images[1].size and difference.getbbox() is None
                results[mode] = {'dom_identical': dom[0] == dom[1], 'pixels_identical': same_pixels,
                                 'original_screenshot': str(folder / f'{mode}_original.png'),
                                 'flattened_screenshot': str(folder / f'{mode}_flattened.png')}
        finally:
            browser.close()
    return results


def forma_interactions(url: str) -> list[dict]:
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for mode, width, reduced in (('desktop', 1280, False), ('mobile', 390, False),
                                         ('reduced_motion', 390, True)):
                page = browser.new_page(viewport={'width': width, 'height': 900},
                                        reduced_motion='reduce' if reduced else 'no-preference')
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url, wait_until='networkidle')
                page.get_by_role('button', name='Studies', exact=True).click()
                one = page.locator('.forma-grid article').count() == 1
                page.get_by_role('button', name='All', exact=True).click()
                all_items = page.locator('.forma-grid article').count() == 3
                no_overflow = not page.evaluate('document.documentElement.scrollWidth > innerWidth + 2')
                results.append({'mode': mode, 'checks': {'filter_one': one, 'filter_all': all_items,
                                                        'no_overflow': no_overflow, 'no_runtime_errors': not errors},
                                'errors': errors, 'passed': one and all_items and no_overflow and not errors})
                page.close()
        finally:
            browser.close()
    return results


def main() -> None:
    if TARGET.exists():
        raise ValueError(f'Immutable flattened dataset already exists: {TARGET}')
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    encoder = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    native = AutoTokenizer.from_pretrained(ROOT / 'base-model', local_files_only=True)
    rows = []
    for site, (source_name, sections, reviewed_path, domain) in SITES.items():
        reviewed = [json.loads(line) for line in reviewed_path.read_text(encoding='utf-8').splitlines()]
        approved = next(row for row in reviewed if row['task_id'] == (
            'diverse_forma_scroll_v2_hero' if site == 'forma_scroll_v2' else f'diverse_{site}_hero'))
        tsx, css = flatten(source_name, sections)
        output = OUTPUT / site
        output.mkdir(parents=True, exist_ok=False)
        compilation = assemble(output, {'src/components/Main.tsx': tsx,
                                        'src/components/Main.css': css})
        if not all(check['passed'] for check in compilation.values()):
            raise ValueError(f'{site}: flattened site does not compile: {compilation}')
        original_dist = ROOT / 'runs/diverse_reference_review' / site / 'dist'
        with serving(original_dist) as original_url, serving(output / 'dist') as flat_url:
            pixels = pixel_equivalence(original_url, flat_url, output)
            checks = forma_interactions(flat_url) if site == 'forma_scroll_v2' else interactions(flat_url, site)
            captures = capture(flat_url, output / 'captures')['captures']
        if not all(item['dom_identical'] and item['pixels_identical'] for item in pixels.values()):
            raise ValueError(f'{site}: source refactor changed rendered DOM or pixels: {pixels}')
        if not all(item['passed'] for item in checks):
            raise ValueError(f'{site}: flattened interactions failed: {checks}')
        if any(capture['browser_errors'] for capture in captures.values()):
            raise ValueError(f'{site}: browser capture logged runtime errors')
        source_bank = BANK / site / 'source'
        source_bank.mkdir(parents=True, exist_ok=False)
        for extension, content in (('tsx', tsx), ('css', css)):
            (source_bank / f'Main.{extension}').write_text(content, encoding='utf-8')
        browser_evidence = {}
        for mode, capture_info in captures.items():
            item = dict(capture_info)
            for kind in ('screenshot', 'scroll_video'):
                artifact = Path(item[kind])
                archived = BANK / site / 'captures' / artifact.name
                archived.parent.mkdir(parents=True, exist_ok=True)
                archived.write_bytes(artifact.read_bytes())
                item[kind] = str(archived)
                item[kind + '_sha256'] = sha256(archived)
            browser_evidence[mode] = item
        verification = {'site': site, 'source_sha256': {f'Main.{ext}': sha256(source_bank / f'Main.{ext}')
                                                        for ext in ('tsx', 'css')},
                        'compilation': compilation, 'pixel_equivalence': pixels, 'interactions': checks,
                        'review_form_sha256': approved['visual_review']['review_form_sha256'],
                        'original_reviewed_task_id': approved['task_id'], 'passed': True}
        (BANK / site / 'verification.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')
        (output / 'verification.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')
        row = {'task_id': f'flattened_{site}_main', 'family_id': approved['family_id'],
               'domain': domain, 'source': str(source_bank.relative_to(ROOT)),
               'license': approved['license'],
               'source_files': verification['source_sha256'],
               'validation': {'typecheck': True, 'build': True, 'runtime': True, 'interaction': True},
               'browser_evidence': browser_evidence,
               'visual_review': {**approved['visual_review'],
                                 'score_application': 'Pixel-identical source refactor of the scored site'},
               'admission_status': 'reviewed_visual_equivalent', 'category': 'full_site',
               'provenance': {'author': 'Codex', 'origin': 'single-pair refactor of human-scored source',
                              'not_native_model_result': True, 'pixel_equivalence_report': str(BANK / site / 'verification.json')},
               'messages': [{'role': 'system', 'content': approved['messages'][0]['content']},
                            {'role': 'user', 'content': 'Build the complete ' + site.replace('_', ' ') +
                             ' website as one self-contained React Main component and paired Main.css. '
                             'Include all sections, navigation, visual composition, and working interactions. '
                             'Return exactly src/components/Main.tsx and Main.css with named and default Main exports. '
                             + BRIEFS[site]},
                            {'role': 'assistant', 'content': envelope('Main', tsx, css)}]}
        row['native_encoded_tokens'] = len(encode_row(row, encoder, 8192, chat_tokenizer=native)['input_ids'])
        rows.append(row)
        print(json.dumps({'site': site, 'pixel_equivalence': pixels, 'max_tokens': row['native_encoded_tokens']}), flush=True)
    errors = validate_reviewed_site_rows(rows, [])
    if errors:
        raise ValueError('\n'.join(errors))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    print(json.dumps({'rows': len(rows), 'max_tokens': max(row['native_encoded_tokens'] for row in rows),
                      'dataset_sha256': sha256(TARGET), 'path': str(TARGET)}, indent=2))


if __name__ == '__main__':
    main()
