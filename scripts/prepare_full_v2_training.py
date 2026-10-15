"""Prepare an isolated canonical-prompt pool; require reviewed rows for final input."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def normalize(row):
 from agent.agent_protocol import AGENT_SYSTEM_PROMPT
 from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
 result=copy.deepcopy(row)
 site=any('write_site' in m['content'] for m in row['messages'] if m['role']=='assistant')
 system=SITE_AGENT_SYSTEM_PROMPT if site else AGENT_SYSTEM_PROMPT
 previous=result['messages'][0]['content'] if result['messages'][0]['role']=='system' else ''
 if result['messages'][0]['role']=='system':result['messages'][0]['content']=system
 else:result['messages'].insert(0,{'role':'system','content':system})
 result['prompt_alignment']={'protocol':'site' if site else 'component','previous_system_sha256':hashlib.sha256(previous.encode()).hexdigest(),'current_system_sha256':hashlib.sha256(system.encode()).hexdigest()}
 return result


def site_contract_errors(row):
 """Conservatively exclude historical targets that contradict the new contract."""
 from agent.agent_protocol import parse_agent_output
 from agent.style_ingest import check_css_selector_coverage
 errors=[]
 for message in row['messages']:
  if message['role']!='assistant':continue
  files=dict(getattr(parse_agent_output(message['content']).action,'files',[]))
  for path,source in files.items():
   if not path.endswith('.tsx'):continue
   css_path=Path(path).with_suffix('.css').as_posix()
   css=files.get(css_path,'')
   if not css.strip():errors.append(f'{path}: missing paired stylesheet')
   if not re.search(r'''import\s*["']\./'''+re.escape(Path(css_path).name)+r'''["']''',source):
    errors.append(f'{path}: missing paired CSS import')
   # Dynamic class fragments need runtime evidence; don't mistake the static
   # prefix of foo-${value} for a literal class named foo-.
   static_source=re.sub(r'\S*\$\{[^}]*\}\S*', '', source)
   valid,missing=check_css_selector_coverage(static_source,css,allow_tailwind=True)
   if not valid:errors.append(f'{path}: stylesheet contract gaps: {missing}')
 return errors


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--draft',action='store_true',help='Prepare historical rows only for CPU preflight; not ready for training')
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--reviewed',type=Path,action='append',help='Reviewed JSONL; repeat to combine independently scored evidence sets')
 args=parser.parse_args()
 from tokenizers import Tokenizer
 from transformers import AutoTokenizer
 from training.preflight import read_jsonl,prepare_rows,check_holdout,sha256
 from data_pipeline.reviewed_site_examples import require_reviewed_training_examples
 original=ROOT/'data/full_site_training/train.jsonl';validation=ROOT/'data/quality_candidate/validation.jsonl'
 exclusions=[]
 def accepted(path,split):
  kept=[]
  for row in read_jsonl(path):
   errors=site_contract_errors(row)
   if errors:exclusions.append({'split':split,'task_id':row.get('task_id'),'reasons':errors})
   else:kept.append(normalize(row))
  return kept
 rows=accepted(original,'train');heldout=accepted(validation,'validation')
 sources={str(original.relative_to(ROOT)):sha256(original)}
 if not args.draft:
  reviewed_paths=args.reviewed or [ROOT/'data/reviewed_full_sites/diverse_v1.jsonl']
  reviewed=[row for path in reviewed_paths for row in read_jsonl(path)]
  if len({row['task_id'] for row in reviewed})!=len(reviewed):
   raise ValueError('Reviewed sources contain duplicate task IDs')
  require_reviewed_training_examples(reviewed,heldout)
  rows.extend(normalize(r) for r in reviewed)
  for path in reviewed_paths:sources[str(path)]=sha256(path)
 check_holdout(rows,heldout)
 encoder=Tokenizer.from_file(str(ROOT/'base-model/tokenizer.json'));native=AutoTokenizer.from_pretrained(ROOT/'base-model',local_files_only=True)
 encoded=prepare_rows(rows,encoder,8192,chat_tokenizer=native)
 prepare_rows(heldout,encoder,8192,chat_tokenizer=native)
 args.output.mkdir(parents=True,exist_ok=False)
 for name,data in [('train',rows),('validation',heldout)]:
  (args.output/f'{name}.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data),encoding='utf-8')
 manifest={'status':'draft_requires_human_review' if args.draft else 'reviewed_input_ready_for_training_preflight','rows':len(rows),'validation_rows':len(heldout),'families':len({r['family_id'] for r in rows}),'reviewed_rows':sum(bool(r.get('visual_review')) for r in rows),'sources':sources,'sha256':sha256(args.output/'train.jsonl'),'validation_sha256':sha256(args.output/'validation.jsonl'),'max_native_tokens':max(len(r['input_ids']) for r in encoded),'system_prompt_policy':'current runtime prompt selected by actual assistant protocol','training_started':False}
 (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 (args.output/'excluded_rows.json').write_text(json.dumps(exclusions,indent=2),encoding='utf-8')
 manifest['excluded_train_rows']=sum(r['split']=='train' for r in exclusions)
 manifest['excluded_validation_rows']=sum(r['split']=='validation' for r in exclusions)
 manifest['exclusion_policy']='Historical paired CSS import and selector contract; no target rewriting. This is not a claim that every excluded target fails rendering.'
 (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
