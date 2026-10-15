from data_pipeline.build_quality_v2 import screen


def row(code, question='Build a header'):
    return {'messages': [{'role': 'user', 'content': question}, {'role': 'assistant', 'content':
        '<tool_call name="write_site">'
        '<file path="src/components/Header.tsx">'+code+'</file>'
        '<file path="src/components/Header.css">.header {color: red}</file></tool_call>'}]}


def test_code_duplicate_survives_prompt_paraphrase():
    assert screen(row('export default function Header(){return <header/>}'))[1] == screen(
        row('export default function Header(){return <header/>}', 'Make a header'))[1]


def test_bad_supervised_history_is_not_hidden_by_good_final_turn():
    bad = row('export default function Header(){return <a href="#">Home</a>}')
    good = row('export default function Header(){return <a href="#home">Home</a>}')
    bad['messages'] += good['messages']
    assert any('placeholder' in reason for reason in screen(bad)[0])
    assert not screen(good)[0]
