"""Verify the requested Forma motion revision without changing reviewed v1 evidence."""
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_diverse_review_queue import SilentHandler, interactions
from scripts.native_site_gate import assemble
from scripts.capture_visual_review import capture
from training.preflight import sha256


def main():
 source=ROOT/'data/diverse_reference/source/forma_scroll_v2'
 output=ROOT/'runs/diverse_reference_review/forma_scroll_v2';output.mkdir(exist_ok=True)
 files={f'src/components/{p.name}':p.read_text(encoding='utf-8') for p in source.iterdir() if p.is_file()}
 original=ROOT/'runs/diverse_reference_review/forma/src/components'
 for name in ('Main.tsx','Main.css'):files[f'src/components/{name}']=(original/name).read_text(encoding='utf-8')
 compilation=assemble(output,files)
 if not all(c['passed'] for c in compilation.values()):raise ValueError(compilation)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(SilentHandler,directory=str(output/'dist')))
 thread=Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}'
 try:
  behavior=interactions(url,'forma')
  from playwright.sync_api import sync_playwright
  timeline=[]
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True)
   for reduced in (False,True):
    page=browser.new_page(viewport={'width':1280,'height':700},reduced_motion='reduce' if reduced else 'no-preference')
    page.goto(url,wait_until='networkidle')
    before=page.locator('.forma-grid article').first.evaluate('(e)=>getComputedStyle(e).opacity')
    initial=page.locator('.forma-stage').evaluate('(e)=>getComputedStyle(e).transform')
    page.locator('.forma-grid article').first.scroll_into_view_if_needed();page.wait_for_timeout(1000)
    after=page.locator('.forma-grid article').first.evaluate('(e)=>getComputedStyle(e).opacity')
    final=page.locator('.forma-stage').evaluate('(e)=>getComputedStyle(e).transform')
    passed=(float(before)==1 and float(after)==1 and initial==final) if reduced else (float(before)==0 and float(after)==1 and initial!=final)
    timeline.append({'reduced_motion':reduced,'opacity_before':before,'opacity_after':after,'stage_before':initial,'stage_after':final,'passed':passed})
    page.close()
   browser.close()
  evidence=capture(url,output/'captures')
 finally:server.shutdown();server.server_close();thread.join(timeout=5)
 report={'source_files':{p.name:sha256(p) for p in source.iterdir() if p.is_file()},'compilation':compilation,'interactions':behavior,'motion_timeline':timeline,'browser_evidence':evidence,'passed':all(c['passed'] for c in behavior+timeline),'human_visual_review':None,'admission_status':'new_revision_awaiting_review'}
 (output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({'passed':report['passed'],'motion_timeline':timeline,'output':str(output)},indent=2))


if __name__=='__main__':main()
