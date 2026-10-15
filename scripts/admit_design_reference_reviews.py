"""Admit original complete-site and compiler-repair examples using actual human CSVs."""
import argparse
import copy
import csv
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.human_visual_review import RUBRIC_AXES
from scripts.build_design_review_gallery import source_fingerprint
from training.preflight import sha256, encode_row


def validate_score(score,item,verification_path):
    if not str(score.get('reviewer_id','')).strip():
        raise ValueError('A named human reviewer is required')
    values={axis:float(score[axis]) for axis in RUBRIC_AXES}
    if not all(1<=value<=5 for value in values.values()):
        raise ValueError('Human scores must be between 1 and 5')
    if score.get('source_fingerprint')!=source_fingerprint(item) or score.get('verification_sha256')!=sha256(verification_path):
        raise ValueError('Review is not bound to the current source and browser evidence')
    approved=str(score.get('approved','')).strip().lower()=='yes'
    if approved and (min(values.values())<3 or sum(values.values())/len(values)<4):
        raise ValueError('Approved references require every axis >=3 and mean >=4')
    return approved,values


def immutable_copy(source,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and sha256(dest)!=sha256(source):
        raise ValueError(f'Existing reviewed evidence has different bytes: {dest}')
    if not dest.exists():shutil.copy2(source,dest)


def validate_review_ids(scores, items):
    ids = [score['site_id'] for score in scores]
    if not ids or len(set(ids)) != len(ids) or not set(ids).issubset(items):
        raise ValueError('Review CSV must contain a nonempty unique subset of queued references')


def admit(scores_file,output):
    folder=ROOT/'runs/design_reference_v2'
    queue=json.loads((folder/'queue.json').read_text(encoding='utf-8'))
    items={item['site_id']:item for item in queue}
    with scores_file.open(encoding='utf-8-sig',newline='') as handle:
        scores=list(csv.DictReader(handle))
    validate_review_ids(scores, items)
    bank=ROOT/'data/reviewed_full_sites/evidence/design_v2'
    form=bank/f'human_scores_{sha256(scores_file)[:16]}.csv'
    reviewed=[]
    for score in scores:
        item=items[score['site_id']]
        site=item['site_id'];verification_path=folder/site/'verification.json'
        approved,values=validate_score(score,item,verification_path)
        if not approved:continue
        verification=json.loads(verification_path.read_text(encoding='utf-8'))
        if verification.get('passed') is not True or item['source_files']!=verification['source_files']:
            raise ValueError(f'{site}: browser/source evidence is not verified')
        for filename,fingerprint in item['source_files'].items():
            if sha256(Path(item['source'])/filename)!=fingerprint:
                raise ValueError(f'{site}: source changed after capture')
        reviewed.append((score,item,values))
    if not reviewed:raise ValueError('No approved references; nothing admitted')
    if output.exists():raise ValueError('Output already exists; choose a new reviewed version')
    immutable_copy(scores_file,form)
    from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
    from transformers import AutoTokenizer
    from tokenizers import Tokenizer
    native=AutoTokenizer.from_pretrained(ROOT/'base-model',local_files_only=True)
    encoder=Tokenizer.from_file(str(ROOT/'base-model/tokenizer.json'))
    rows=[]
    for score,item,values in reviewed:
        site=item['site_id'];target=bank/site
        source=Path(item['source'])
        for filename in item['source_files']:immutable_copy(source/filename,target/'source'/filename)
        immutable_copy(folder/site/'verification.json',target/'verification.json')
        diagnostics_path=folder/site/'repair_probe/diagnostics.json'
        immutable_copy(diagnostics_path,target/'repair_diagnostics.json')
        captures=copy.deepcopy(item['browser_evidence'])
        for mode,capture in captures.items():
            for artifact in ('screenshot','scroll_video'):
                original=Path(capture[artifact]);dest=target/'captures'/f'{mode}_{artifact}{original.suffix}'
                if sha256(original)!=capture[artifact+'_sha256']:raise ValueError('Capture changed after review')
                immutable_copy(original,dest);capture[artifact]=str(dest.resolve())
        meta={**copy.deepcopy(item),'source':str((target/'source').resolve()),'browser_evidence':captures,
              'visual_review':{'review_type':'human_visual','reviewer_id':score['reviewer_id'].strip(),
                  'rubric_scores':values,'notes':score.get('notes',''),'review_form':str(form.resolve()),'review_form_sha256':sha256(form)},
              'verification_report':str((target/'verification.json').resolve()),'verification_sha256':sha256(target/'verification.json'),
              'admission_status':'reviewed'}
        tsx=(target/'source/Main.tsx').read_text(encoding='utf-8');css=(target/'source/Main.css').read_text(encoding='utf-8')
        envelope=f'<tool_call name="write_site">\n<file path="src/components/Main.tsx">\n{tsx}</file>\n<file path="src/components/Main.css">\n{css}</file>\n</tool_call>'
        request=(item['description']+' Return the complete self-contained Main.tsx and Main.css. '
                 'Import React and the paired CSS, export named and default Main. This is a standalone full site: '
                 'the stylesheet may include the document reset; scope the design under its root class.')
        complete={**copy.deepcopy(meta),'task_id':f'design_v2_{site}_complete','category':'full_site',
                  'messages':[{'role':'system','content':SITE_AGENT_SYSTEM_PROMPT},{'role':'user','content':request},{'role':'assistant','content':envelope}]}
        diagnostics=json.loads((target/'repair_diagnostics.json').read_text(encoding='utf-8'))
        repair={**copy.deepcopy(meta),'task_id':f'design_v2_{site}_repair','category':'repair','repair_diagnostics':diagnostics,
                'messages':[{'role':'system','content':SITE_AGENT_SYSTEM_PROMPT},{'role':'user','content':
                 f'Repair this complete site without changing appearance or behavior. Return Main.tsx and the unchanged paired Main.css.\nCurrent TSX:\n{diagnostics["before_tsx"]}\nCurrent CSS:\n{css}\nObserved compiler diagnostic:\n{diagnostics["compiler"]}'},
                 {'role':'assistant','content':envelope}]}
        for row in (complete,repair):
            row['native_encoded_tokens']=len(encode_row(row,encoder,8192,chat_tokenizer=native)['input_ids'])
            rows.append(row)
    from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
    errors=validate_reviewed_site_rows(rows,[])
    if errors:raise ValueError('; '.join(errors))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
    return {'admitted_sites':len(reviewed),'rows':len(rows),'domains':sorted({row['domain'] for row in rows}),
            'output':str(output.resolve()),'sha256':sha256(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--human-scores',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(admit(args.human_scores,args.output),indent=2))
