"""Execute a reviewed generation candidate through SFT and live gates, without promotion."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from training.preflight import read_jsonl, sha256
from training.native_generation_gate import require_native_completion
from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
from scripts.prepare_generation_mix import build


def require_broad_reviewed_sources(extra):
    rows=read_jsonl(extra)
    errors=validate_reviewed_site_rows(rows,[])
    expected={'editorial','arts','hospitality','education','civic','events','dashboard','healthcare','nonprofit'}
    if {row.get('domain') for row in rows}!=expected:
        errors.append('All nine newly requested source-review domains must be admitted before this candidate run')
    if errors:raise ValueError('; '.join(errors))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-extra',type=Path,required=True)
    parser.add_argument('--dataset-output',type=Path,required=True)
    parser.add_argument('--model-output',type=Path,required=True)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--native-gate',type=Path,default=ROOT/'runs/native_base_contract_v9/report.json')
    args=parser.parse_args()
    # Resolve paths before subprocesses, which may choose a different working directory.
    extra=args.reviewed_extra.resolve();mix=args.dataset_output.resolve();model=args.model_output.resolve();run_dir=args.run_dir.resolve()
    require_broad_reviewed_sources(extra)
    native=require_native_completion(args.native_gate,expected_model_dir=ROOT/'base-model')
    for path in (mix,model,run_dir):
        if path.exists():raise ValueError(f'Use a new isolated destination: {path}')
    run_dir.mkdir(parents=True)
    state={'status':'preparing','initialization':'verified base-model, no historical adapter',
           'native_gate':native,'reviewed_extra_sha256':sha256(extra),'phases':[],
           'promotion_status':'not_promoted; later live and two-person blinded gates mandatory',
           'second_blinded_reviewer':'Yash (named by user)'}
    def save():
        (run_dir/'workflow_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    def execute(name,arguments):
        command=[sys.executable,*arguments]
        phase={'name':name,'command':command,'status':'running','log':str(run_dir/f'{name}.log')}
        state['phases'].append(phase);state['status']=name;save()
        print(f'{name}: running; log {phase["log"]}',flush=True)
        with Path(phase['log']).open('w',encoding='utf-8') as handle:
            result=subprocess.run(command,cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT)
        phase['returncode']=result.returncode;phase['status']='passed' if result.returncode==0 else 'failed';save()
        if result.returncode:
            raise ValueError(f'{name} failed; inspect {phase["log"]}. Candidate remains unpromoted.')
    save()
    try:
        inputs=[ROOT/'data/reviewed_full_sites'/name for name in ('diverse_v1.jsonl','forma_scroll_v2.jsonl','flattened_v2.jsonl','contract_repairs_v1.jsonl')]+[extra]
        state['dataset_manifest']=build(mix,inputs);save()
        common=['--data',str(mix/'train.jsonl'),'--validation-data',str(mix/'validation.jsonl'),'--max-seq-length','8192']
        execute('preflight',['training/train_sft.py',*common,'--preflight-only'])
        execute('sft',['training/train_sft.py',*common,'--output',str(model),'--checkpoint-dir',str(run_dir/'checkpoints'),
            '--native-gate-report',str(args.native_gate.resolve()),'--epochs','1','--rank','16','--learning-rate','0.00002'])
        execute('candidate_native',['scripts/native_site_gate.py','--model',str(model),'--output',str(run_dir/'native')])
        require_native_completion(run_dir/'native/report.json',expected_model_dir=model)
        state['adapter_sha256']=sha256(model/'adapter_model.safetensors');save()
        # Held-out prompts are used for evaluation only after the development gate passes.
        for role,path in [('candidate',model),('baseline',ROOT/'base-model')]:
            execute(f'{role}_heldout',['scripts/benchmark_full_sites.py','--model',str(path),
                '--benchmark',str(ROOT/'data/eval/visual_holdout_v1.jsonl'),'--output',str(run_dir/f'{role}_heldout.json'),
                '--workspace-dir',str(run_dir/f'{role}_workspace'),'--live-browser','--keep-workspace'])
        state['status']='live_reports_ready_requires_blinded_capture_package_and_two_humans';save()
        print('Live reports saved. Prepare real blinded A/B captures; no automatic promotion.',flush=True)
    except BaseException as error:
        state['status']='failed';state['error']=f'{type(error).__name__}: {error}';save();raise


if __name__=='__main__':
    main()
