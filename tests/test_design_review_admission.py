import pytest
from scripts.admit_design_reference_reviews import validate_score
from scripts.build_design_review_gallery import source_fingerprint
from training.preflight import sha256
from evaluation.human_visual_review import RUBRIC_AXES


def fixture(tmp_path):
    item={'source_files':{'Main.tsx':'unit-test-source-fingerprint'}}
    report=tmp_path/'verification.json';report.write_text('{"fixture":true}')
    score={'reviewer_id':'unit-test-reviewer','approved':'yes',**{axis:'4' for axis in RUBRIC_AXES},
           'source_fingerprint':source_fingerprint(item),'verification_sha256':sha256(report)}
    return score,item,report


def test_admission_requires_named_human_and_exact_reviewed_bytes(tmp_path):
    score,item,report=fixture(tmp_path)
    assert validate_score(score,item,report)[0] is True
    report.write_text('{"fixture":"changed"}')
    with pytest.raises(ValueError,match='bound'):
        validate_score(score,item,report)


def test_unnamed_or_low_quality_approval_rejected(tmp_path):
    score,item,report=fixture(tmp_path)
    score['reviewer_id']=''
    with pytest.raises(ValueError,match='named'):
        validate_score(score,item,report)
    score['reviewer_id']='unit-test-reviewer';score['layout']='2'
    with pytest.raises(ValueError,match='every axis'):
        validate_score(score,item,report)


def test_nonapproval_does_not_admit_reference(tmp_path):
    score,item,report=fixture(tmp_path);score['approved']='no'
    assert validate_score(score,item,report)[0] is False
