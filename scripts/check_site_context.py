"""Measure the real initial site request without loading a model or generating code."""
import json
from pathlib import Path
import sys
import uuid
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'agent'))
from agent import run_site_agent_on_example
from agent_protocol import format_chatml
from site_brief import generate_content_brief, brief_to_xml


class Captured(BaseException):
    pass


class CaptureRunner:
    history = None
    def generate_turn(self, **kwargs):
        self.history = kwargs['history']
        raise Captured()


def main():
    prompt = json.loads((ROOT/'sessions/1789582016_b4b7d5.json').read_text(encoding='utf8'))['prompt']
    brief = generate_content_brief(prompt, provider='heuristic', resolve_images=False)
    runner = CaptureRunner()
    workspace = ROOT/'experiments'/'context-checks'/uuid.uuid4().hex
    try:
        run_site_agent_on_example(0,prompt,'NexaFlow',brief_to_xml(brief),brief['sections'],runner,workspace,
                                  brief=brief,style_spec=brief.get('style_spec'),
                                  custom_section_instructions=brief.get('custom_section_instructions'))
    except Captured:
        pass
    tokenizer = Tokenizer.from_file(str(ROOT/'base-model/tokenizer.json'))
    count = len(tokenizer.encode(format_chatml(runner.history,add_generation_prompt=True)).ids)
    result = {'initial_prompt_tokens':count,'context_limit':8192,'requested_output_tokens':4096,
              'fits':count+4096<=8192,'sections':brief['sections'],
              'scope':'Exact initial request only; later history must also fit after compaction.'}
    (ROOT/'experiments'/'site-context-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
    return 0 if result['fits'] else 1


if __name__=='__main__':
    raise SystemExit(main())
