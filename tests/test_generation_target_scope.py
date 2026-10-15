from scripts.prepare_generation_mix import mark_final_target
from training.preflight import build_canonical_train_manifest


def test_already_selected_prefixes_are_not_reexpanded():
    messages = [{'role':'user','content':'Write first'}, {'role':'assistant','content':'<finish>First</finish>'},
                {'role':'user','content':'Write second'}, {'role':'assistant','content':'<finish>Second</finish>'}]
    short = {'task_id':'first','family_id':'family','messages':messages[:2]}
    long = {'task_id':'second','family_id':'family','messages':messages}
    prepared = build_canonical_train_manifest([mark_final_target(short),mark_final_target(long)])
    assert len(prepared) == 2
    assert [row['messages'][-1]['content'] for row in prepared] == ['<finish>First</finish>','<finish>Second</finish>']
