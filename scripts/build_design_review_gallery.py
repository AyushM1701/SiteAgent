"""Create a review form tied to exact source and browser evidence fingerprints."""
import hashlib
import html
import json
from pathlib import Path
import sys
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.human_visual_review import RUBRIC_AXES
from training.preflight import sha256


def source_fingerprint(item):
    return hashlib.sha256(json.dumps(item['source_files'],sort_keys=True).encode()).hexdigest()


def build(folder, exclude=(), filename='review.html'):
    queue = json.loads((folder/'queue.json').read_text(encoding='utf-8'))
    queue = [item for item in queue if item['site_id'] not in exclude]
    sections = []
    assets = folder/'assets';assets.mkdir(exist_ok=True)
    for item in queue:
        site = item['site_id']
        for asset in (folder/site/'dist/assets').iterdir():
            shutil.copy2(asset,assets/asset.name)
        fields = ''.join(f'<label>{axis.replace("_"," ").title()}<select name="{axis}" required><option value="">Choose</option>'+''.join(f'<option value="{score}">{score}</option>' for score in range(1,6))+'</select></label>' for axis in RUBRIC_AXES)
        modes = ''.join(f'<button type="button" data-mode="{mode}">{mode.replace("_"," ")}</button>' for mode in ('desktop','mobile','reduced_motion'))
        fingerprint = source_fingerprint(item)
        verification_hash = sha256(folder/site/'verification.json')
        sections.append(f'''<section data-site="{site}" data-source="{fingerprint}" data-verification="{verification_hash}"><p>{html.escape(item['domain'].upper())}</p><h2>{html.escape(site)}</h2><p>{html.escape(item['description'])}</p><a href="{site}/dist/" target="_blank" rel="noopener">Open interactive site ↗</a><div data-modes>{modes}</div><div data-evidence><a data-image href="{site}/captures/desktop_screenshot.png" target="_blank"><img src="{site}/captures/desktop_screenshot.png" alt="{site} desktop full-page capture" loading="lazy"/></a><video controls preload="none" src="{site}/captures/desktop_scroll_video.webm" aria-label="{site} scroll capture"></video></div><fieldset><legend>Visual quality scores, 1 to 5</legend><div data-scores>{fields}</div><label>Notes<textarea name="notes" rows="2"></textarea></label><label><input type="checkbox" name="approved"/> I approve these exact reference files for training</label></fieldset></section>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Website design reference review</title><style>body{margin:0;background:#f4f1e8;color:#26382d;font:16px/1.65 Arial}main{max-width:1200px;margin:auto;padding:50px 5vw}h1{font:clamp(40px,6vw,70px)/1.05 Georgia;letter-spacing:-2px}h2{font:34px Georgia}header{max-width:800px}section{margin:45px 0;padding:30px;border:1px solid #aab6a7;background:#fffdf7}button,select,input,textarea{font:inherit}button{padding:10px 16px;background:#26382d;color:#fffdf7;border:1px solid;border-radius:4px;cursor:pointer}button[aria-pressed=true]{background:#e5c993;color:#26382d}label{display:block;margin:15px 0}input[type=text],textarea{display:block;width:100%;box-sizing:border-box;padding:10px}select{display:block;padding:9px;width:100%}[data-modes]{display:flex;gap:10px;flex-wrap:wrap;margin:25px 0}[data-evidence]{display:grid;grid-template-columns:1fr 1fr;gap:20px}[data-image]{display:block;height:500px;overflow:auto;border:1px solid #c2c9ba}img,video{width:100%}fieldset{border:0;padding:0;margin-top:25px}[data-scores]{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}a{color:inherit;text-underline-offset:4px}:focus-visible{outline:3px solid #bf520f;outline-offset:4px}@media(max-width:700px){main{padding:30px 5vw}section{padding:20px}[data-evidence]{grid-template-columns:1fr}[data-scores]{grid-template-columns:1fr 1fr}}</style><main><header><p>ORIGINAL DESIGN REFERENCE REVIEW</p><h1>Help choose what<br/>the model learns.</h1><p>These authored references passed compiler and browser checks. They are not local-model outputs. Your visual scores decide admission to training. The later model promotion review is a separate blinded A/B comparison with you and Yash.</p><p>Score 1: poor; 2: substantial issues; 3: usable with clear weaknesses; 4: polished with minor issues; 5: excellent. Approval requires every axis at least 3 and an average of at least 4. Inspect mobile and reduced-motion captures as well as the interactive site.</p></header><form id="review"><label>Your reviewer name or ID<input name="reviewer_id" type="text" required/></label>'''+''.join(sections)+'''<button type="submit">Download human scores CSV</button><p role="status" id="status"></p></form></main><script>
const axes=['layout','hierarchy','typography','content_specificity','imagery_assets','motion_timing','mobile_composition'];
document.querySelectorAll('section').forEach(section=>section.querySelectorAll('[data-mode]').forEach(button=>{button.setAttribute('aria-pressed',button.dataset.mode==='desktop');button.onclick=()=>{section.querySelectorAll('[data-mode]').forEach(other=>other.setAttribute('aria-pressed',other===button));const base=section.dataset.site+'/captures/'+button.dataset.mode;section.querySelector('img').src=base+'_screenshot.png';section.querySelector('[data-image]').href=base+'_screenshot.png';section.querySelector('video').src=base+'_scroll_video.webm';};}));
document.querySelector('form').onsubmit=event=>{event.preventDefault();const form=event.currentTarget;const fields=['site_id','reviewer_id',...axes,'notes','approved','source_fingerprint','verification_sha256'];const quote=value=>'"'+String(value).replaceAll('"','""')+'"';const lines=[fields.map(quote).join(',')];form.querySelectorAll('section').forEach(section=>{const values=[section.dataset.site,form.elements.reviewer_id.value.trim(),...axes.map(axis=>section.querySelector('[name="'+axis+'"]').value),section.querySelector('[name=notes]').value,section.querySelector('[name=approved]').checked?'yes':'no',section.dataset.source,section.dataset.verification];lines.push(values.map(quote).join(','));});const blob=new Blob([lines.join(String.fromCharCode(13,10))],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='design_reference_human_scores.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.querySelector('#status').textContent='Attach the downloaded CSV to this chat. No examples have been admitted yet.';};
</script></html>'''
    (folder/filename).write_text(page,encoding='utf-8')
    return folder/filename


if __name__=='__main__':
    print(build(ROOT/'runs/design_reference_v2'))
