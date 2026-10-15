"""Build and verify original reference sites; keep human review explicitly pending."""
import csv
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.native_site_gate import assemble
from scripts.capture_visual_review import capture
from training.preflight import sha256
from evaluation.human_visual_review import RUBRIC_AXES

SOURCE=ROOT/'data/diverse_reference/source'
OUTPUT=ROOT/'runs/diverse_reference_review'
SITES={
 'forma':{'domain':'portfolio','sections':['Hero','Collection','Contact'],'description':'Original sculpture portfolio with CSS 3D composition and working category filters.'},
 'paperkite':{'domain':'ecommerce','sections':['Hero','Shop','About'],'description':'Original illustrated print shop with a functional local cart and explicit demo pricing.'},
 'quiethours':{'domain':'unfamiliar','sections':['Hero','Guide','Journal'],'description':'Original soundwalk journal with parallax, scroll reveals, validation and in-memory note saving.'},
}


class SilentHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass


def interactions(url,name):
 from playwright.sync_api import sync_playwright
 result=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  try:
   for mode,width,reduced in [('desktop',1280,False),('mobile',390,False),('reduced_motion',390,True)]:
    page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce' if reduced else 'no-preference')
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='networkidle')
    checks={}
    if name=='forma':
     orbit=page.locator('.forma-orbit')
     before=orbit.evaluate('(e)=>getComputedStyle(e).transform')
     page.wait_for_timeout(450)
     after=orbit.evaluate('(e)=>getComputedStyle(e).transform')
     checks['motion_contract']=(before==after) if reduced else (before!=after)
     page.get_by_role('button',name='Studies',exact=True).click()
     checks['filter_one']=page.locator('.forma-grid article').count()==1
     page.get_by_role('button',name='All',exact=True).click()
     checks['filter_all']=page.locator('.forma-grid article').count()==3
    elif name=='paperkite':
     page.get_by_role('button',name='Add Sunroom to bag').click()
     page.get_by_role('button',name='Add Blue Hour to bag').click()
     checks['cart_total']='2 prints · $52' in page.locator('#bag').inner_text()
     page.get_by_role('button',name='Empty bag',exact=True).click()
     checks['cart_reset']='0 prints · $0' in page.locator('#bag').inner_text()
    else:
     moon=page.locator('.quiet-moon')
     before=moon.evaluate('(e)=>getComputedStyle(e).transform')
     page.locator('#guide').scroll_into_view_if_needed()
     page.wait_for_timeout(750)
     after=moon.evaluate('(e)=>getComputedStyle(e).transform')
     checks['parallax_contract']=(before==after) if reduced else (before!=after)
     checks['reveal_visible']=all(float(v)>.99 for v in page.locator('.quiet-step').evaluate_all('(els)=>els.map(e=>getComputedStyle(e).opacity)'))
     page.get_by_role('button',name='Save this moment').click()
     checks['empty_validation']='Write a few words' in page.locator('#quiet-error').inner_text()
     page.get_by_label('One thing I noticed').fill('Leaves moving above a distant bicycle bell.')
     page.get_by_role('button',name='Save this moment').click()
     checks['saved_note']=page.locator('.quiet-saved p').inner_text()=='Leaves moving above a distant bicycle bell.'
     page.get_by_role('button',name='Clear note').click()
     checks['clear_note']=page.locator('.quiet-saved p').count()==0
    checks['no_overflow']=page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    checks['no_runtime_errors']=not errors
    result.append({'mode':mode,'checks':checks,'errors':errors,'passed':all(checks.values())})
    page.close()
  finally: browser.close()
 return result


def main():
 OUTPUT.mkdir(parents=True,exist_ok=True)
 queue=[]
 for name,spec in SITES.items():
  target=OUTPUT/name
  target.mkdir(exist_ok=True)
  source=SOURCE/name
  files={f'src/components/{p.name}':p.read_text(encoding='utf-8') for p in source.iterdir() if p.suffix in ('.tsx','.css')}
  files['src/components/Main.tsx']='import React from "react";import "./Main.css";'+''.join(f'import {s} from "./{s}";' for s in spec['sections'])+'export default function Main(){return <><a className="reference-skip" href="#reference-main">Skip to content</a><main id="reference-main">'+''.join(f'<{s}/>' for s in spec['sections'])+'</main></>;}'
  files['src/components/Main.css']='*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif}html{scroll-behavior:smooth}a{color:inherit}button,input,textarea{font:inherit}.reference-skip{position:absolute;top:-100px;left:15px;z-index:100;padding:15px;background:#fff;color:#111}.reference-skip:focus{top:15px}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}'
  compilation=assemble(target,files)
  if not all(v['passed'] for v in compilation.values()):
   (target/'compilation.json').write_text(json.dumps(compilation,indent=2),encoding='utf-8')
   raise RuntimeError(f'{name} failed compilation; see compilation.json')
  server=ThreadingHTTPServer(('127.0.0.1',0),partial(SilentHandler,directory=str(target/'dist')))
  thread=Thread(target=server.serve_forever,daemon=True);thread.start()
  url=f'http://127.0.0.1:{server.server_port}'
  try:
   browser=interactions(url,name)
   evidence=capture(url,target/'captures')
  finally:
   server.shutdown();server.server_close();thread.join(timeout=5)
  verification={'source_files':{p.name:sha256(p) for p in source.iterdir() if p.is_file()},'compilation':compilation,'interaction_checks':browser,'passed':all(v['passed'] for v in browser) and not any(v['browser_errors'] for v in evidence['captures'].values())}
  (target/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
  queue.append({'site_id':name,'family_id':f'original_diverse_{name}','domain':spec['domain'],'description':spec['description'],'source':str(source.relative_to(ROOT)),'license':'MIT (repository LICENSE)','author':'Codex; original authored reference, not local-model output','source_files':verification['source_files'],'validation':{'typecheck':True,'build':True,'runtime':all(not c['errors'] for c in browser),'interaction':all(c['passed'] for c in browser)},'browser_evidence':evidence['captures'],'visual_review':None,'admission_status':'awaiting_human_review' if verification['passed'] else 'validation_failed'})
  print(f'{name}: browser validation {verification["passed"]}',flush=True)
 (OUTPUT/'queue.json').write_text(json.dumps(queue,indent=2),encoding='utf-8')
 form=OUTPUT/'human_scores.csv'
 if not form.exists():
  with form.open('w',newline='',encoding='utf-8') as handle:
   writer=csv.DictWriter(handle,fieldnames=['site_id','reviewer_id',*RUBRIC_AXES,'notes','approved'])
   writer.writeheader();writer.writerows({'site_id':name} for name in SITES)
 print(f'Review queue: {OUTPUT}; admitted training rows: 0',flush=True)


if __name__=='__main__':main()
