from types import SimpleNamespace
from agent.generation_scorecards import generation_scorecards
from agent.project_validator import ValidationResult


def test_repaired_result_never_turns_failed_native_output_into_a_pass():
    validation=ValidationResult()
    result={'sections_planned':['hero'],'turn_logs':[
        {'section':'hero','action':'write_site_structural_violation'},
        {'section':'hero','action':'write_site_ok'}],'normalized_files':['src/Hero.css']}
    repair=SimpleNamespace(deterministic_files=[],validation_after_deterministic=validation,repair_attempts=2)
    cards=generation_scorecards(result,repair,validation,False,{'mode':'live'})
    native,deterministic,model,final=cards['stages']
    assert native['status']=='failed' and native['first_attempt_sections']==0
    assert model['section_retries']==1 and model['project_attempts']==2
    assert deterministic['status']=='failed' and final['status']=='failed'
