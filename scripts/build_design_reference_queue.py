"""Verify nine original complete websites and capture a pending human review queue."""
from contextlib import contextmanager
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline.reference_sites_v2 import SITES, source_files
from scripts.native_site_gate import assemble
from scripts.capture_visual_review import capture
from scripts.prepare_diverse_review_queue import SilentHandler
from training.preflight import sha256

OUTPUT = ROOT / 'runs/design_reference_v2'
SOURCE = ROOT / 'data/design_reference_v2/source'


@contextmanager
def serve(folder):
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SilentHandler, directory=str(folder)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown(); server.server_close(); worker.join(timeout=5)


def browser_checks(url, site_id, spec):
    from playwright.sync_api import sync_playwright
    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for mode, width, reduced in [('desktop',1280,False),('mobile',390,False),('reduced_motion',390,True)]:
                page = browser.new_page(viewport={'width':width,'height':900}, reduced_motion='reduce' if reduced else 'no-preference')
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                page.goto(url, wait_until='networkidle')
                results = {'main_visible': page.get_by_role('main').is_visible(),
                           'one_h1': page.locator('h1').count()==1,
                           'no_overflow': page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')}
                for index, operation in enumerate(spec['checks']):
                    action, *args = operation
                    if action == 'click': page.get_by_role(args[0],name=args[1],exact=True).click()
                    elif action == 'click_selector': page.locator(args[0]).filter(has_text=args[1]).click()
                    elif action == 'select': page.get_by_label(args[0],exact=True).select_option(label=args[1])
                    elif action == 'fill': page.get_by_label(args[0],exact=True).fill(args[1])
                    elif action == 'check': page.get_by_role('checkbox',name=args[0],exact=True).check()
                    elif action == 'count': results[f'interaction_{index}'] = page.locator(args[0]).count()==args[1]
                    elif action == 'text': results[f'interaction_{index}'] = page.locator(args[0]).inner_text()==args[1]
                    elif action == 'contains': results[f'interaction_{index}'] = args[1] in page.locator(args[0]).inner_text()
                    elif action == 'visible': results[f'interaction_{index}'] = page.locator(args[0]).is_visible()
                    elif action == 'attribute': results[f'interaction_{index}'] = page.locator(args[0]).get_attribute(args[1])==args[2]
                    else: raise ValueError(f'Unknown operation {action}')
                results['nav_targets_exist'] = page.locator('nav a').evaluate_all("links=>links.every(a=>a.hash&&document.querySelector(a.hash))")
                results['no_orphan_labels'] = page.locator('label[for]').evaluate_all("labels=>labels.every(l=>document.getElementById(l.htmlFor))")
                page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(100)
                art = page.locator('[data-art]')
                if art.count():
                    before = art.first.evaluate('(el)=>getComputedStyle(el).transform')
                    page.evaluate('window.scrollTo(0,500)');page.wait_for_timeout(150)
                    after = art.first.evaluate('(el)=>getComputedStyle(el).transform')
                    results['parallax_or_reduced_motion'] = before==after if reduced else before!=after
                # Visit each reveal, including nodes inserted by filter interactions.
                for reveal in page.locator('[data-reveal]').all():
                    reveal.scroll_into_view_if_needed();page.wait_for_timeout(750)
                results['reveal_visible'] = page.locator('[data-reveal]').evaluate_all('els=>els.every(el=>Number(getComputedStyle(el).opacity)>.99)')
                if site_id == 'prism':
                    cube = page.locator('[data-cube]')
                    before = cube.evaluate('(el)=>getComputedStyle(el).transform');page.wait_for_timeout(400)
                    after = cube.evaluate('(el)=>getComputedStyle(el).transform')
                    results['css_3d_motion_or_reduced_motion'] = before==after if reduced else before!=after
                    results['css_3d_faces'] = page.locator('[data-face]').count()==6
                    page.get_by_role('checkbox',name='Show flat composition').check()
                    results['flat_fallback'] = cube.evaluate('(el)=>getComputedStyle(el).transform')=='none' and page.locator('[data-face="0"]').is_visible()
                results['no_browser_errors'] = not errors
                checks.append({'mode':mode,'checks':results,'errors':errors,'passed':all(results.values())})
                page.close()
        finally:
            browser.close()
    return checks


def repair_probe(target, files):
    """Inject a real TS type error without altering the approved fixed design."""
    directory = target / 'repair_probe'
    bad = dict(files)
    bad['src/components/Main.tsx'] += '\nconst injectedDiagnostic: number = "invalid";\n'
    failed = assemble(directory, bad)
    if failed['typescript']['passed']:
        raise ValueError('Fault injection did not produce a compiler diagnostic')
    diagnostic = failed['typescript']['output']
    (directory / 'before.tsx.txt').write_text(bad['src/components/Main.tsx'], encoding='utf-8')
    fixed = assemble(directory, files)
    if not all(result['passed'] for result in fixed.values()):
        raise ValueError('Fixed reference failed repair compilation')
    result = {'origin':'authored fault injection; actual compiler output', 'compiler':diagnostic,
              'before_tsx':bad['src/components/Main.tsx'], 'after_typecheck':True,'after_build':True}
    (directory / 'diagnostics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def verified_entry(site_id, spec, source, target, fingerprints):
    """Recover a queue entry only from intact verification and repair artifacts."""
    try:
        report = json.loads((target/'verification.json').read_text(encoding='utf-8'))
        diagnostic = json.loads((target/'repair_probe/diagnostics.json').read_text(encoding='utf-8'))
        if report['source_files'] != fingerprints or report['passed'] is not True:
            return None
        if not all(result['passed'] for result in report['compilation'].values()):
            return None
        if {check['mode'] for check in report['browser_checks']} != {'desktop','mobile','reduced_motion'} or not all(check['passed'] and all(check['checks'].values()) for check in report['browser_checks']):
            return None
        if not diagnostic['compiler'] or not diagnostic['after_typecheck'] or not diagnostic['after_build']:
            return None
        if diagnostic['before_tsx'] != (source/'Main.tsx').read_text(encoding='utf-8')+'\nconst injectedDiagnostic: number = "invalid";\n':
            return None
        if set(report['captures']) != {'desktop','mobile','reduced_motion'}:
            return None
        for capture_record in report['captures'].values():
            if capture_record['browser_errors']:
                return None
            for artifact in ('screenshot','scroll_video'):
                path = Path(capture_record[artifact])
                if not path.is_file() or sha256(path) != capture_record[artifact+'_sha256']:
                    return None
        return {'site_id':site_id,'family_id':f'original_design_v2_{site_id}', 'domain':spec['domain'],
            'description':spec['brief'],'source':str(source.resolve()),'source_files':fingerprints,
            'license':'MIT (repository LICENSE)', 'author':'Codex; original reference, not local model output',
            'validation':{'typecheck':True,'build':True,'runtime':True,'interaction':True},
            'browser_evidence':report['captures'],'visual_review':None,'admission_status':'awaiting_human_review'}
    except (OSError, KeyError, ValueError):
        return None


def save_queue(queue):
    (OUTPUT / 'queue.json').write_text(json.dumps(queue,indent=2),encoding='utf-8')


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    queue = []
    for site_id, spec in SITES.items():
        target = OUTPUT / site_id
        source = SOURCE / site_id
        source.mkdir(parents=True,exist_ok=True)
        files = source_files(site_id,spec)
        for filename, code in files.items():
            path = source / Path(filename).name
            if path.exists() and path.read_text(encoding='utf-8') != code:
                if (ROOT / 'data/reviewed_full_sites/evidence/design_v2' / site_id).exists():
                    raise ValueError(f'Reviewed source cannot change: {path}; use a new version')
                archive = target / 'unreviewed_source_revisions'
                archive.mkdir(parents=True,exist_ok=True)
                (archive / f'{sha256(path)}_{path.name}').write_bytes(path.read_bytes())
            path.write_text(code,encoding='utf-8')
        fingerprints = {p.name:sha256(p) for p in source.iterdir() if p.is_file()}
        reused = verified_entry(site_id, spec, source, target, fingerprints)
        if reused:
            queue.append(reused)
            print(f'{site_id}: reusing unchanged verified source and capture bytes; human review pending',flush=True)
            continue
        compilation = assemble(target,files)
        (target / 'compilation.json').write_text(json.dumps(compilation,indent=2),encoding='utf-8')
        if not all(result['passed'] for result in compilation.values()):
            raise ValueError(f'{site_id}: compilation failed; see compilation.json')
        with serve(target / 'dist') as url:
            checks = browser_checks(url,site_id,spec)
            evidence = capture(url,target / 'captures')
        fingerprints = {p.name:sha256(p) for p in source.iterdir() if p.is_file()}
        for capture_record in evidence['captures'].values():
            for artifact in ('screenshot','scroll_video'):
                capture_record[artifact+'_sha256'] = sha256(Path(capture_record[artifact]))
        passed = all(check['passed'] for check in checks) and all(not item['browser_errors'] for item in evidence['captures'].values())
        verification = {'source_files':fingerprints,'compilation':compilation,'browser_checks':checks,
                        'captures':evidence['captures'],'passed':passed,'visual_review':'pending_human',
                        'three_d_kind':'explicit_css_composition' if site_id=='prism' else 'not_requested',
                        'webgl_runtime':'not_requested; no WebGL claim'}
        (target / 'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
        if not passed:
            raise ValueError(f'{site_id}: browser verification failed; see verification.json')
        repair_probe(target,files)
        queue.append({'site_id':site_id,'family_id':f'original_design_v2_{site_id}', 'domain':spec['domain'],
            'description':spec['brief'],'source':str(source.resolve()),'source_files':fingerprints,
            'license':'MIT (repository LICENSE)', 'author':'Codex; original reference, not local model output',
            'validation':{'typecheck':True,'build':True,'runtime':True,'interaction':True},
            'browser_evidence':evidence['captures'],'visual_review':None,'admission_status':'awaiting_human_review'})
        save_queue(queue)
        print(f'{site_id}: compilation, three-mode browser checks, captures and compiler repair passed; human review pending',flush=True)
    save_queue(queue)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
