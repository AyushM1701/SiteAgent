from server.event_bus import EventBus


def test_written_log_has_a_real_path():
    event = EventBus().publish('audit', {'type': 'log', 'text': 'Written: src/components/Hero.tsx (721 chars)'})
    assert event['data']['path'] == 'src/components/Hero.tsx'


def test_blocked_result_is_not_a_success_event():
    result = {'status': 'blocked', 'validation': {'contract_status': 'blocked'}}
    event = EventBus().publish('audit', {'type': 'result', 'data': result})
    assert event['type'] == 'task.failed'
    assert event['data']['result'] == result


def test_blocked_validation_retains_requirements_and_unverified_gates(tmp_path):
    from server.app import _validate_blocked_site
    brief = {'motion_plan': [{'type': 'parallax'}], 'requirement_manifest': {
        'interaction_constraints': [{'kind': 'cart'}, {'kind': 'flat_view_toggle'}],
        'three_d_constraints': [{'engine': 'css'}],
    }}
    result = _validate_blocked_site(tmp_path, brief, ['shop missing'])
    assert result.typecheck_status == 'unverified'
    assert result.build_status == 'unverified'
    assert result.contract_status == 'blocked'
    assert result.motion_plan == brief['motion_plan']
    assert result.motion_runtime_status == 'unverified'
    assert result.three_d_runtime_status == 'unverified'
    assert not result.three_d_passed
    assert result.interactions_required == 2
    assert result.interaction_status == 'unverified'
    assert not result.passed


def test_blocked_validation_reports_real_compiler_results(monkeypatch, tmp_path):
    import agent.project_validator as validator
    from server.app import _validate_blocked_site
    (tmp_path / 'package.json').write_text('{}')
    (tmp_path / 'tsconfig.json').write_text('{}')
    monkeypatch.setattr(validator, 'run_project_typecheck', lambda path: (True, []))
    monkeypatch.setattr(validator, 'run_project_build', lambda path: (True, []))
    result = _validate_blocked_site(tmp_path, {}, ['shop missing'])
    assert result.typecheck_status == result.build_status == 'passed'
    assert result.contract_status == 'blocked'
    assert not result.passed


def test_blocked_validation_uses_enriched_saved_manifest(tmp_path):
    import json
    from server.app import _validate_blocked_site
    (tmp_path/'content_brief.json').write_text(json.dumps({'requirement_manifest':{
        'interaction_constraints':[{'type':'cart_state'}], 'three_d_constraints':[{'engine':'css'}]}}))
    result=_validate_blocked_site(tmp_path,{},['hero missing'])
    assert result.interactions_required == 1
    assert result.three_d_runtime_status == 'unverified'
    assert not result.three_d_passed


def test_validation_exception_cannot_report_requested_three_d_as_passed(tmp_path, monkeypatch):
    import json
    import agent.project_validator as validator
    from server.app import _validate_workspace
    (tmp_path/'content_brief.json').write_text(json.dumps({'requirement_manifest':{
        'three_d_constraints':[{'engine':'css'}],'interaction_constraints':[{'type':'cart_state'}]}}))
    def broken(**kwargs): raise RuntimeError('browser infrastructure unavailable')
    monkeypatch.setattr(validator,'validate_project',broken)
    result=_validate_workspace(tmp_path)
    assert not result.three_d_passed and not result.passed
    assert result.three_d_runtime_status=='unverified'
    assert result.interactions_required==1


def test_exception_is_cached_as_a_failed_partial_result(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import server.app as app
    workspace=tmp_path/'session'
    (workspace/'src').mkdir(parents=True)
    (workspace/'src/Hero.tsx').write_text('export default function Hero(){return <section>Saved</section>}')
    session=SimpleNamespace(workspace_dir=workspace,history=[],build_state={},save=lambda:None)
    monkeypatch.setattr(app.session_manager,'get_session',lambda sid:session)
    captured=[]
    monkeypatch.setattr(app,'_store_task_result',lambda tid,result:captured.append(result))
    result=app._store_task_failure({'task_id':'broken','session_id':'site','prompt':'Build a site'},RuntimeError('diagnostic log disappeared'))
    assert result['status']=='failed' and not result['final_passed']
    assert result['generation_complete'] is False
    assert result['files']['src/Hero.tsx'].endswith('</section>}')
    assert captured==[result]
    assert session.history[-1]['validation']['runtime_status']=='unverified'
