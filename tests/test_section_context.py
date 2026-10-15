import pytest
from copy import deepcopy
from types import SimpleNamespace
from agent.agent import run_site_agent_on_example


def test_next_section_keeps_brief_but_discards_previous_raw_output(tmp_path, monkeypatch):
    histories = []
    def generate(**kwargs):
        histories.append(deepcopy(kwargs['history']))
        name = 'Hero' if len(histories) == 1 else 'Footer'
        slug = name.lower()
        return f'''<tool_call name="write_site">
<file path="src/components/{name}.tsx">
import React from 'react';
import './{name}.css';
export function {name}() {{return <section id="{slug}" className="{slug}"><p>Unique raw {name} content</p></section>;}}
export default {name};
</file>
<file path="src/components/{name}.css">.{slug}{{padding:2rem;color:#111;background:#fff}}</file>
</tool_call>'''
    monkeypatch.setattr('agent.agent.run_command', lambda *a, **kw: SimpleNamespace(returncode=0, stdout='', stderr=''))
    result = run_site_agent_on_example(0, 'Build a pottery portfolio', 'Pottery', '', ['hero', 'footer'], SimpleNamespace(generate_turn=generate), workspace_root=tmp_path, max_turns=2)
    assert result['sections_completed'] == 2
    second = '\n'.join(item['content'] for item in histories[1])
    assert 'pottery portfolio' in second
    assert 'Accepted sections: hero' in second
    assert 'src/components/Hero.tsx' in second
    assert 'Unique raw Hero content' not in second
    assert 'CURRENT SECTION REQUIRED:' in second
    assert 'Footer.tsx' in second


def test_deterministic_source_normalization_is_not_native_credit(tmp_path, monkeypatch):
    output='''<tool_call name="write_site">
<file path="src/components/Hero.tsx">import React from 'react';import './Hero.css';export function Hero(){return <section id="hero" className="hero">Pottery</section>;}export default Hero;</file>
<file path="src/components/Hero.css">.hero{font: size 14px;color:#111;background:#fff}</file>
</tool_call>'''
    monkeypatch.setattr('agent.agent.run_command',lambda *a,**kw:SimpleNamespace(returncode=0,stdout='',stderr=''))
    result=run_site_agent_on_example(0,'Build a pottery hero','Pottery','',['hero'],SimpleNamespace(generate_turn=lambda **kw:output),workspace_root=tmp_path,max_turns=1)
    assert result['sections_completed']==1
    assert 'src/components/Hero.css' in result['normalized_files']
    assert result['generation_quality']=='repaired'


@pytest.fixture(autouse=True)
def _freeform_site_strategy(monkeypatch):
    """These tests exercise the legacy code-writing loop, not the design kit."""
    monkeypatch.setenv("SITE_STRATEGY", "freeform")
