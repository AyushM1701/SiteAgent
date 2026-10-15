"""Separate acceptance evidence from browser and repair claims."""
def generation_scorecards(result, repair, final_validation, final_passed, provenance):
    first = {}
    retries = 0
    for entry in result.get('turn_logs', []):
        section = entry.get('section')
        if not section or entry.get('action') == 'section_blocked':
            continue
        if section in first:
            retries += 1
        else:
            first[section] = entry.get('action') == 'write_site_ok'
    required = len(result.get('sections_planned', []))
    accepted = sum(first.values())
    normalized = result.get('normalized_files', [])
    deterministic = sorted(set(normalized + list(getattr(repair, 'deterministic_files', []) or [])))
    after = getattr(repair, 'validation_after_deterministic', None)
    attempts = getattr(repair, 'repair_attempts', 0) if repair else 0
    return {'provenance':provenance, 'stages':[
        {'id':'native','label':'Model native','status':'failed' if accepted < required else 'unverified',
         'first_attempt_sections':accepted,'required_sections':required,'normalized_files':normalized,
         'note':'First-attempt section acceptance; raw full-site browser validation is not captured.'},
        {'id':'deterministic_repair','label':'Deterministic repair','status':('passed' if after.passed else 'failed') if deterministic and after else 'not_applied' if not deterministic else 'unverified',
         'files':deterministic,'validation':after.to_dict() if after else None},
        {'id':'model_repair','label':'Model repair','status':('passed' if final_passed else 'failed') if retries or attempts else 'not_applied',
         'section_retries':retries,'project_attempts':attempts},
        {'id':'final','label':'Final site','status':'passed' if final_passed else 'failed','validation':final_validation.to_dict()},
    ]}
