"""Prepare pending full-site trajectories and compiler-observed repair pairs.

No reviewed training rows are published without an explicit human score file.
"""
import argparse
import copy
import csv
import json
from pathlib import Path
import subprocess
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
from scripts.prepare_diverse_review_queue import SITES, SOURCE, OUTPUT
from training.preflight import sha256, encode_row
from evaluation.human_visual_review import RUBRIC_AXES

DETAILS={
 'forma':['Build a navigation and editorial hero with a warm stone background, clay accent, a large serif headline Less object. More presence. and three dimensional CSS blocks. Include reduced motion. Link #work and #contact.', 'Build #work with Quiet Column, The Space Between and Low Horizon sculptural CSS illustrations. Filters All, Objects and Studies must change the displayed items; expose aria-pressed and visible focus.', 'Build #contact as an honest fictional studio footer. Include a back-to-top link to #intro; do not fabricate contact details.'],
 'paperkite':['Build a playful paper-cream, blue and coral hero. Headline Put a little play on your wall. Original CSS poster artwork and a reduced-motion-aware decorative animation. Navigation links #prints and #about.', 'Build #prints with Sunroom $24, Blue Hour $28 and Soft Landing $24, all illustrative USD prices. CSS artwork, additive quantities, a visible total and working Empty bag button in #bag. Explicitly say no orders, payments or shipping are processed.', 'Build #about with a playful coral background, an honest fictional-shop description, and a link to #hello.'],
 'quiethours':['Build a calm soundwalk-journal hero with an abstract CSS landscape, a moon and layered hills. Parallax must disable under reduced motion and listeners must clean up. Links #guide and #journal. No tracking or microphone.', 'Build #guide with three invitations: Arrive, Listen in layers, Leave a small note. Reveal entries on scroll with IntersectionObserver and cleanup. Content must remain visible when reduced motion is requested.', 'Build #journal with an explicitly labelled textarea, 400-character limit, nonempty validation, Save this moment and Clear note. Show the saved text safely. Explain that notes are only kept in page memory and refreshing clears them. Link #start.'],
}
FAULTS={'forma':('Collection','setFilter(item)','setFiltre(item)'), 'paperkite':('Shop','setCart(current','setBasket(current'), 'quiethours':('Journal','setSaved(note.trim())','setSvaed(note.trim())')}


def envelope(name,tsx,css):
 return f'<tool_call name="write_site">\n<file path="src/components/{name}.tsx">\n{tsx}\n</file>\n<file path="src/components/{name}.css">\n{css}\n</file>\n</tool_call>'


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--human-scores',type=Path)
 args=parser.parse_args()
 from tokenizers import Tokenizer
 from transformers import AutoTokenizer
 encoder=Tokenizer.from_file(str(ROOT/'base-model/tokenizer.json'))
 native=AutoTokenizer.from_pretrained(ROOT/'base-model',local_files_only=True)
 queue=json.loads((OUTPUT/'queue.json').read_text(encoding='utf-8'))
 rows=[]
 for item in queue:
  name=item['site_id'];spec=SITES[name];source=SOURCE/name
  if not all(item['validation'].values()):raise ValueError(f'{name}: validation not passed')
  for file,digest in item['source_files'].items():
   if sha256(source/file)!=digest:raise ValueError(f'{name}: source changed since validation')
  meta={key:copy.deepcopy(item[key]) for key in ('family_id','domain','source','license','validation','browser_evidence','source_files')}
  meta.update(provenance={'author':'Codex','origin':'original authored reference; not a native model result'},visual_review=None,admission_status='pending_human_review')
  history=[{'role':'system','content':SITE_AGENT_SYSTEM_PROMPT}]
  for index,section in enumerate(spec['sections']):
   tsx=(source/f'{section}.tsx').read_text(encoding='utf-8');css=(source/f'{section}.css').read_text(encoding='utf-8')
   request=f'{spec["description"]} The complete site consists of {", ".join(spec["sections"])} in that order. The host supplies border-box sizing, body margin 0, Arial, and reduced-motion-aware anchor scrolling.\n{DETAILS[name][index]}\nWrite only src/components/{section}.tsx and {section}.css. Use self-contained plain CSS and React, named plus default exports, and the paired CSS import.'
   history.extend([{'role':'user','content':request},{'role':'assistant','content':envelope(section,tsx,css)}])
   row={**copy.deepcopy(meta),'task_id':f'diverse_{name}_{section.lower()}','category':'full_site','messages':copy.deepcopy(history)}
   row['native_encoded_tokens']=len(encode_row(row,encoder,8192,chat_tokenizer=native)['input_ids']);rows.append(row)
  section,good,bad=FAULTS[name]
  tsx=(source/f'{section}.tsx').read_text(encoding='utf-8');css=(source/f'{section}.css').read_text(encoding='utf-8')
  if good not in tsx:raise ValueError('Fault injection target missing')
  broken=tsx.replace(good,bad,1)
  faultdir=OUTPUT/name/'repair_probe';faultdir.mkdir(exist_ok=True)
  faultfile=faultdir/f'{section}.tsx';faultfile.write_text(broken,encoding='utf-8')
  (faultdir/f'{section}.css').write_text(css,encoding='utf-8')
  (faultdir/'globals.d.ts').write_text("declare module '*.css';",encoding='utf-8')
  command=['node',str(ROOT/'node_modules/typescript/bin/tsc'),'--noEmit','--jsx','react-jsx','--module','ESNext','--moduleResolution','bundler','--target','ES2020','--lib','ES2020,DOM','--skipLibCheck','--allowSyntheticDefaultImports',str(faultfile),str(faultdir/'globals.d.ts')]
  failure=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
  if failure.returncode==0:raise ValueError(f'{name}: injected fault was not detected')
  diagnostic=(failure.stdout+failure.stderr).replace(str(faultdir),'src/components').replace(str(ROOT),'[workspace]')
  (faultdir/'diagnostic.txt').write_text(diagnostic,encoding='utf-8')
  faultfile.write_text(tsx,encoding='utf-8')
  fixed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
  if fixed.returncode:raise ValueError(f'{name}: repair did not typecheck')
  (faultdir/'before.tsx.txt').write_text(broken,encoding='utf-8')
  repair={**copy.deepcopy(meta),'task_id':f'diverse_{name}_repair','category':'repair','repair_diagnostics':{'origin':'authored fault injection; actual compiler output','before':broken,'compiler':diagnostic,'after_typecheck':True},'messages':[{'role':'system','content':SITE_AGENT_SYSTEM_PROMPT},{'role':'user','content':f'Repair this {section} component without changing its appearance or behavior. Return the complete corrected TSX and unchanged paired CSS.\nCurrent src/components/{section}.tsx:\n{broken}\nCurrent CSS:\n{css}\nObserved compiler diagnostic:\n{diagnostic}'},{'role':'assistant','content':envelope(section,tsx,css)}]}
  repair['native_encoded_tokens']=len(encode_row(repair,encoder,8192,chat_tokenizer=native)['input_ids']);rows.append(repair)
 pending=OUTPUT/'pending_rows.jsonl'
 pending.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
 if args.human_scores:
  with args.human_scores.open(encoding='utf-8',newline='') as handle:scores=list(csv.DictReader(handle))
  approved={}
  for score in scores:
   if score['approved'].strip().lower()!='yes' or not score['reviewer_id'].strip():raise ValueError('Explicit human approval and reviewer ID required for every site')
   values={axis:float(score[axis]) for axis in RUBRIC_AXES}
   if not all(1<=v<=5 for v in values.values()) or min(values.values())<3 or sum(values.values())/len(values)<4:raise ValueError('Reviewed examples require scores 1–5, every axis >=3 and mean >=4')
   approved[score['site_id']]={'reviewer_id':score['reviewer_id'],'rubric_scores':values,'notes':score['notes'],'review_type':'human_visual','review_form_sha256':sha256(args.human_scores)}
  if set(approved)!=set(SITES):raise ValueError('Human scores must cover each source site exactly once')
  bank=ROOT/'data/reviewed_full_sites/evidence/diverse_v1'
  def immutable_copy(original,destination):
   destination.parent.mkdir(parents=True,exist_ok=True)
   if destination.exists() and sha256(destination)!=sha256(original):
    raise ValueError(f'Reviewed evidence already exists with different bytes: {destination}')
   if not destination.exists():shutil.copy2(original,destination)
  immutable_copy(args.human_scores,bank/'human_scores.csv')
  for row in rows:
   site=row['family_id'].removeprefix('original_diverse_');row['visual_review']=approved[site];row['admission_status']='reviewed'
   row['visual_review']['review_form']=str(bank/'human_scores.csv')
   for file in row['source_files']:
    immutable_copy(SOURCE/site/file,bank/site/'source'/file)
   row['source']=str((bank/site/'source').relative_to(ROOT))
   for mode,capture in row['browser_evidence'].items():
    for kind in ('screenshot','scroll_video'):
     original=Path(capture[kind]);destination=bank/site/'captures'/original.name
     immutable_copy(original,destination);capture[kind]=str(destination)
     capture[kind+'_sha256']=sha256(destination)
  from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
  errors=validate_reviewed_site_rows(rows,[])
  if errors:raise ValueError('\n'.join(errors))
  target=ROOT/'data/reviewed_full_sites/diverse_v1.jsonl'
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
  print(f'Published {len(rows)} human-reviewed rows to {target}')
 else:
  print(json.dumps({'pending_rows':len(rows),'families':3,'full_site_turns':9,'repair_pairs':3,'max_tokens':max(r['native_encoded_tokens'] for r in rows),'admitted_rows':0,'path':str(pending)},indent=2))


if __name__=='__main__':main()
