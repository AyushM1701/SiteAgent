import json
from agent import project_validator as validator


def test_compiler_failure_does_not_erase_requested_browser_gates(tmp_path, monkeypatch):
    (tmp_path/'content_brief.json').write_text(json.dumps({
        'original_prompt':'Create CSS 3D pottery with parallax and a cart',
        'requirement_manifest':{'interaction_constraints':[{'kind':'cart'},{'kind':'flat_view_toggle'}]},
    }))
    monkeypatch.setattr(validator,'run_project_typecheck',lambda path:(False,['[TypeScript Error] broken listener']))
    result=validator.validate_project(tmp_path)
    assert result.interactions_required == 2
    assert result.interactions_tested == 0
    assert result.interaction_status == 'unverified'
    assert result.runtime_unverified
    assert result.three_d_runtime_status == 'runtime_unverified'
    assert result.motion_runtime_status == 'runtime_unverified'
    assert not result.passed


def test_plural_text_reveals_cannot_bypass_browser_motion_verification(tmp_path):
    errors=validator._check_motion_browser(None,None,'',tmp_path,json.dumps({'original_prompt':'Add scrolling text reveals'}))
    assert errors and 'typed motion plan' in errors[0]
