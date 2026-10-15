"""Build a local human review form with real captures and empty score inputs."""
import html
import json
import argparse
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.human_visual_review import RUBRIC_AXES


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--queue',default='queue.json',help='Queue JSON in runs/diverse_reference_review')
 parser.add_argument('--output',default='review.html',help='Output HTML filename in the same folder')
 args=parser.parse_args()
 folder=ROOT/'runs/diverse_reference_review'
 queue=json.loads((folder/args.queue).read_text(encoding='utf-8'))
 sections=[]
 for item in queue:
  site=item['site_id']
  # Vite's absolute asset URLs are served from this review portal's root.
  assets=folder/site/'dist/assets'
  (folder/'assets').mkdir(exist_ok=True)
  for asset in assets.iterdir():shutil.copy2(asset,folder/'assets'/asset.name)
  fields=''.join(f'<label>{axis.replace("_"," ").title()}<select name="{axis}" required><option value="">Choose a score</option>'+''.join(f'<option>{n}</option>' for n in range(1,6))+'</select></label>' for axis in RUBRIC_AXES)
  modes=''.join(f'<button type="button" data-mode="{mode}">{mode.replace("_"," ").title()}</button>' for mode in ('desktop','mobile','reduced_motion'))
  sections.append(f'''<section data-site="{site}"><div class="heading"><div><p>{html.escape(item['domain'].upper())}</p><h2>{site}</h2></div><a href="{site}/dist/" target="_blank">Open interactive reference ↗</a></div><p>{html.escape(item['description'])}</p><div class="modes" role="group" aria-label="Capture viewport">{modes}</div><div class="evidence"><a class="image-link" href="{site}/captures/desktop_screenshot.png" target="_blank"><img src="{site}/captures/desktop_screenshot.png" alt="{site} full-page capture"></a><div><h3>Scroll recording</h3><video controls preload="metadata" src="{site}/captures/desktop_scroll_video.webm"></video><p>Inspect the full screenshot, motion recording and interactive reference. Scores begin empty.</p></div></div><div class="scores">{fields}</div><label>Notes<textarea name="notes" rows="3" placeholder="What works, and what should change?"></textarea></label><label class="approval"><input type="checkbox" name="approved"> I reviewed this site and approve it for the training reference pool.</label></section>''')
 page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Human review · Website references</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f1e9;color:#26372e;font:15px/1.6 system-ui}main{max-width:1120px;margin:auto;padding:50px 24px}h1{font:clamp(36px,5vw,65px)/1.05 Georgia;letter-spacing:-2px}h2{font:38px Georgia;margin:5px 0}h3{font:24px Georgia}a{color:#315849}header>p{max-width:740px}section{padding:35px;margin:40px 0;background:#fffdf7;border:1px solid #c7cebf;border-radius:14px}.heading{display:flex;justify-content:space-between;align-items:center;gap:20px}.heading p{font:11px monospace;letter-spacing:2px}.modes{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap}button{padding:11px 18px;border:1px solid #617866;background:#edf0e8;color:#26372e;border-radius:7px;cursor:pointer}.modes button[aria-pressed=true]{background:#26372e;color:#fffdf7}.evidence{display:grid;grid-template-columns:1fr 1fr;gap:30px}.image-link{height:450px;overflow:auto;display:block;border:1px solid #c7cebf}.image-link img{display:block;width:100%;height:auto}video{width:100%;max-height:350px;background:#ddd}.scores{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:30px 0}label{display:block;font-size:13px;font-weight:600}input[type=text],textarea,select{display:block;width:100%;margin-top:6px;padding:12px;font:14px system-ui;border:1px solid #9ba993;border-radius:5px;background:#fff}input[type=text]{max-width:400px}.approval{margin-top:20px}.approval input{margin-right:8px}.export{background:#26372e;color:#fffdf7;font-size:16px;padding:16px 25px}:focus-visible{outline:3px solid #a76632;outline-offset:3px}details{padding:16px;border:1px solid #c7cebf;border-radius:8px}@media(max-width:700px){main{padding:30px 15px}section{padding:20px}.heading{display:block}.evidence{grid-template-columns:1fr}.scores{grid-template-columns:1fr 1fr}.image-link{height:420px}}
</style><main><header><p>WEBSITE REFERENCE REVIEW</p><h1>Help define the<br>quality we train toward.</h1><p>These references passed browser checks. Your visual scores decide whether they enter the reviewed training pool. Promotion will require a later blinded A/B review with two independent people.</p><details><summary>Scoring guide</summary><p>Use 1 for poor, 2 for substantial issues, 3 for usable with clear weaknesses, 4 for polished with minor issues, and 5 for excellent. Consider hierarchy and readability; typography; content specificity; purposeful artwork; motion timing and reduced-motion behavior; and mobile composition. Admission requires each score at least 3 and an average of at least 4.</p></details></header><form id="review"><label>Your reviewer name or ID<input type="text" name="reviewer_id" required autocomplete="name"></label>'''+''.join(sections)+'''<button class="export" type="submit">Download my review CSV</button><p id="status" role="status"></p></form></main><script>
document.querySelectorAll('section').forEach(section=>{section.querySelectorAll('[data-mode]').forEach(button=>{button.setAttribute('aria-pressed',button.dataset.mode==='desktop');button.onclick=()=>{section.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',b===button));const prefix=section.dataset.site+'/captures/'+button.dataset.mode;section.querySelector('img').src=prefix+'_screenshot.png';section.querySelector('.image-link').href=prefix+'_screenshot.png';section.querySelector('video').src=prefix+'_scroll_video.webm';};});});
document.querySelector('form').onsubmit=event=>{event.preventDefault();const form=event.currentTarget;const axes=['layout','hierarchy','typography','content_specificity','imagery_assets','motion_timing','mobile_composition'];const fields=['site_id','reviewer_id',...axes,'notes','approved'];const quote=value=>'"'+String(value).replaceAll('"','""')+'"';const lines=[fields.map(quote).join(',')];form.querySelectorAll('section').forEach(section=>{const values=[section.dataset.site,form.elements.reviewer_id.value.trim(),...axes.map(axis=>section.querySelector('[name="'+axis+'"]').value),section.querySelector('[name=notes]').value,section.querySelector('[name=approved]').checked?'yes':'no'];lines.push(values.map(quote).join(','));});const url=URL.createObjectURL(new Blob([lines.join('\\r\\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='human_scores.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.querySelector('#status').textContent='Review downloaded. Attach the CSV to this task so the scores can be verified and imported.';};
</script></html>'''
 (folder/args.output).write_text(page,encoding='utf-8')
 print(folder/args.output)


if __name__=='__main__':main()
