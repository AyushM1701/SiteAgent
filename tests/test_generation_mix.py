from scripts.prepare_generation_mix import classify_target, scope_section_row


def site(symbol='Hero'):
    return f'<tool_call name="write_site"><file path="src/components/{symbol}.tsx">import React from "react";import "./{symbol}.css";export function {symbol}(){{return <section className="root">Content</section>}}export default {symbol};</file><file path="src/components/{symbol}.css">.root{{padding:2rem}}</file></tool_call>'


def row(target, request='Build a complete website'):
    return {'task_id': 't', 'family_id': 'f', 'messages': [
        {'role': 'user', 'content': request}, {'role': 'assistant', 'content': target}]}


def test_finish_requires_actual_prior_generation_and_acceptance():
    item = row('<finish>Everything is done</finish>')
    assert classify_target(item)[0] == 'excluded'
    item['messages'].insert(1, {'role': 'tool', 'content': '{"status":"accepted","project_complete":true}'})
    assert classify_target(item)[0] == 'excluded'


def test_section_scope_preserves_brief_and_target():
    original = row(site())
    scoped = scope_section_row(original, ['Hero', 'Contact'])
    assert original['messages'][0]['content'] == 'Build a complete website'
    assert scoped['messages'][-1]['content'] == original['messages'][-1]['content']
    assert 'Contact' in scoped['messages'][0]['content']
    assert classify_target(scoped)[0] == 'section'


def test_isolated_component_and_unscoped_section_are_not_complete_sites():
    assert classify_target(row('<tool_call name="write_component"><tsx>x</tsx></tool_call>'))[0] == 'excluded'
    assert classify_target(row(site()))[0] == 'excluded'


def test_full_main_and_diagnostic_repair_are_distinct():
    assert classify_target(row(site('Main')))[0] == 'complete_site'
    item = row(site('Main'), 'Repair the Main component')
    item['category'] = 'repair'
    assert classify_target(item)[0] == 'excluded'
    item['repair_diagnostics'] = {'compiler': 'TS2322: invalid property', 'after_typecheck': True}
    assert classify_target(item)[0] == 'repair'
