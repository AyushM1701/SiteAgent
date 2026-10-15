"""Two deterministic held-out section probes with real DOM interaction tests.

These narrow probes are not the full premium-site or 153-task benchmark.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'agent'))
from agent import AgentModelRunner
from agent_protocol import SITE_AGENT_SYSTEM_PROMPT, WriteSiteAction, parse_agent_output
from evaluate import run_command

CASES = {
    'FeatureTabs': (
        'Build only an accessible feature-tabs section for Orbit Notes, a fictional premium team notebook. '
        'Use restrained indigo on off-white, large editorial typography and responsive CSS. '
        'Tabs are Collect, Connect and Publish, initially Collect. Use roles tablist/tab/tabpanel, '
        'aria-selected, aria-controls, aria-labelledby and roving tabIndex. Right/Left arrows and Home/End '
        'must move selection and focus. Each selected panel contains exactly its corresponding sentence: '
        'Collect: Capture your first idea. Connect: Bring related thoughts together. Publish: Share a finished story. '
        'Inactive panels must be hidden or unmounted.',
        '''it('tabs change content, selection and keyboard focus',async()=>{
 const user=userEvent.setup();render(<Component/>);
 const collect=screen.getByRole('tab',{name:'Collect',exact:true});
 const connect=screen.getByRole('tab',{name:'Connect',exact:true});
 expect(collect).toHaveAttribute('aria-selected','true');
 await user.click(connect);
 expect(connect).toHaveAttribute('aria-selected','true');
 expect(screen.getByRole('tabpanel')).toHaveTextContent('Bring related thoughts together.');
 await user.keyboard('{ArrowRight}');
 expect(screen.getByRole('tab',{name:'Publish',exact:true})).toHaveFocus();
 expect(screen.getByRole('tabpanel')).toHaveTextContent('Share a finished story.');
 await user.keyboard('{Home}');expect(collect).toHaveFocus();
 expect(collect).toHaveAttribute('aria-selected','true');
 expect(collect).toHaveAttribute('tabindex','0');expect(connect).toHaveAttribute('tabindex','-1');
 expect(screen.getByRole('tabpanel')).toHaveTextContent('Capture your first idea.');
});'''),
    'Pricing': (
        'Build only the pricing section for Orbit Notes, a fictional premium team notebook. '
        'Use restrained indigo, off-white, large editorial typography and responsive CSS. '
        'Explicitly label prices illustrative. Include an accessible role=switch named Annual billing, '
        'initially off. Monthly price is $12 / month and the billing line is Billed monthly. '
        'When switched on show $9 / month and $108 billed yearly. Toggle must change both price and '
        'billing line and aria-checked together; pressing Space must toggle it. Include a CTA to #workspace '
        'but do not perform purchases or claim a working checkout.',
        '''it('billing changes both amounts and supports keyboard reversal',async()=>{
 const user=userEvent.setup();render(<Component/>);
 const toggle=screen.getByRole('switch',{name:'Annual billing',exact:true});
 expect(toggle).not.toBeChecked();expect(document.body).toHaveTextContent('$12');
 expect(document.body).toHaveTextContent('Billed monthly');
 await user.click(toggle);expect(toggle).toBeChecked();
 expect(document.body).toHaveTextContent('$9');expect(document.body).toHaveTextContent('$108 billed yearly');
 await user.keyboard(' ');expect(toggle).not.toBeChecked();
 expect(document.body).toHaveTextContent('$12');expect(document.body).toHaveTextContent('Billed monthly');
});'''),
}


def evaluate(model, output):
    output.mkdir(parents=True, exist_ok=True)
    runner = AgentModelRunner(str(model), max_seq_length=8192)
    results=[]
    for index,(name,(brief,test)) in enumerate(CASES.items()):
        destination=output/name
        destination.mkdir(exist_ok=True)
        prompt=brief+f' Write exactly src/components/{name}.tsx and src/components/{name}.css. Export default function {name}. Return complete closed file tags without markdown fences.'
        started=time.monotonic()
        response=runner.generate_turn(index,[{'role':'system','content':SITE_AGENT_SYSTEM_PROMPT},{'role':'user','content':prompt}],name,max_new_tokens=2048,temperature=0)
        (destination/'response.txt').write_text(response,encoding='utf-8')
        action=parse_agent_output(response).action
        files=dict(action.files) if isinstance(action,WriteSiteAction) else {}
        expected={f'src/components/{name}.tsx',f'src/components/{name}.css'}
        for path,code in files.items():
            if path in expected:
                target=destination/path;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(code,encoding='utf-8')
        row={'section':name,'prompt':prompt,'elapsed_seconds':round(time.monotonic()-started,2),
             'expected_files':expected==set(files),'closed_file_tags':response.count('</file>')==2,
             'typecheck':False,'interaction_tests':False}
        if expected<=set(files):
            test_file=destination/'generated.test.tsx'
            test_file.write_text("import React from 'react';import {it,expect} from 'vitest';import {render,screen} from '@testing-library/react';import userEvent from '@testing-library/user-event';import Component from './src/components/"+name+"';\n"+test,encoding='utf-8')
            compile_result=run_command(['npx','tsc','--noEmit','--jsx','react-jsx','--target','ES2022','--module','ESNext','--moduleResolution','bundler','--esModuleInterop','--skipLibCheck',str(destination/'src/components'/f'{name}.tsx'),'css.d.ts'],cwd=ROOT)
            row['typecheck']=compile_result.returncode==0
            (destination/'typecheck.txt').write_text(compile_result.stdout+compile_result.stderr,encoding='utf-8')
            result=run_command(['npx','vitest','run',str(test_file),'--config','vitest.config.ts'],cwd=ROOT)
            row['interaction_tests']=result.returncode==0
            (destination/'tests.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        results.append(row)
        report={'model':str(model),'adapter_sha256':hashlib.sha256((model/'adapter_model.safetensors').read_bytes()).hexdigest(),'max_new_tokens':2048,'temperature':0,'cases':results,'scope':'One-shot section tests only; no visual score or full-site claim.'}
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(row),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    evaluate(args.model,args.output)
