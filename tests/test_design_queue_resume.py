import json
import pytest
from scripts import build_design_reference_queue as builder
from scripts.admit_design_reference_reviews import validate_review_ids


def test_resume_persists_all_reused_sites_even_when_queue_lost_entries(tmp_path, monkeypatch):
    output = tmp_path/'runs'; output.mkdir()
    (output/'queue.json').write_text('[{"site_id":"first"}]')
    monkeypatch.setattr(builder, 'OUTPUT', output)
    monkeypatch.setattr(builder, 'SOURCE', tmp_path/'source')
    monkeypatch.setattr(builder, 'SITES', {'first':{}, 'second':{}, 'third':{}})
    monkeypatch.setattr(builder, 'source_files', lambda *args: {'Main.tsx':'fixture'})
    monkeypatch.setattr(builder, 'verified_entry', lambda site, *args: {'site_id':site})
    monkeypatch.setattr(builder, 'assemble', lambda *args: pytest.fail('Intact evidence must be reused'))
    assert builder.main() == 0
    assert [item['site_id'] for item in json.loads((output/'queue.json').read_text())] == ['first','second','third']


def test_partial_review_submission_preserves_unique_known_sites():
    validate_review_ids([{'site_id':'first'}], {'first':{},'second':{}})
    for scores in ([], [{'site_id':'unknown'}], [{'site_id':'first'},{'site_id':'first'}]):
        with pytest.raises(ValueError,match='unique subset'):
            validate_review_ids(scores, {'first':{},'second':{}})
