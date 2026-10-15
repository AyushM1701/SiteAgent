import pytest


def test_methodology_override_cannot_bypass_native_quality_gate(monkeypatch, tmp_path):
    from agent import base_model_fingerprint
    from training import native_generation_gate
    from training.train_sft import train
    monkeypatch.setattr(base_model_fingerprint, 'verify_base_model_architecture',
                        lambda *a, **k: {'is_authentic_qwen3': True})

    def reject(*a, **k):
        raise ValueError('native completion is mandatory')

    monkeypatch.setattr(native_generation_gate, 'require_native_completion', reject)
    with pytest.raises(ValueError, match='native completion is mandatory'):
        train(dataset_path=str(tmp_path / 'missing.jsonl'), max_seq_length=8192,
              override_methodology_gate=True, output_path=str(tmp_path / 'candidate'),
              checkpoint_dir=str(tmp_path / 'checkpoints'))
