"""Bounded browser check of saved-project hydration; never submits generation."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / 'runs/workbench_ui_audit_20261005/session_result.json').read_text())
OUT = ROOT / 'runs/workbench_ui_audit_20261005/fix_hydration'
OUT.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    results = []
    for width in (1440, 390):
        context = browser.new_context(viewport={'width': width, 'height': 1000})
        page = context.new_page()
        errors, mutations = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: mutations.append(request.url) if request.method != 'GET' else None)
        page.route('**/api/projects', lambda route: route.fulfill(json={'projects': [FIXTURE]}))
        page.route('**/api/projects/' + FIXTURE['session_id'], lambda route: route.fulfill(json=FIXTURE))
        # Isolate hydration from model/server and preview lifecycle.
        page.route('**/preview/**', lambda route: route.fulfill(content_type='text/html', body='<h1>Isolated preview fixture</h1>'))
        page.add_init_script('window.WebSocket = class {static OPEN=1; readyState=0; close(){} send(){}};')
        page.goto('http://127.0.0.1:5000', wait_until='domcontentloaded', timeout=30000)
        if width < 768:
            page.locator('#topbar-sidebar-toggle').click()
        page.locator('aside').get_by_text('Aster_Objects', exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('3 / 4 sections complete', timeout=10000)
        expect(page.get_by_text('What do you want to build?', exact=True)).to_have_count(0)
        expect(page.locator('body')).to_contain_text('Orbit Mug')
        page.locator('#topbar-workspace-toggle').click()
        expect(page.locator('summary')).to_contain_text('1 validation errors')
        page.locator('summary').click()
        expect(page.locator('body')).to_contain_text('[Generation blocked] shop: structural_violation')
        assert page.locator('iframe[title="Live Preview"]').get_attribute('sandbox') == 'allow-scripts allow-forms allow-popups'
        assert not errors, errors
        assert not mutations, mutations
        page.screenshot(path=str(OUT / f'hydrated_{width}.png'), full_page=True)
        results.append({'width': width, 'chat_restored': True, 'blocked_result_restored': True,
                        'validation_errors': 1, 'sandbox_preserved': True, 'page_errors': errors, 'mutating_requests': mutations})
        context.close()
    browser.close()
    (OUT / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results))
