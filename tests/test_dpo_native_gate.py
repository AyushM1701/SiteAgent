import pytest


def test_dpo_checks_initial_adapter_native_gate_before_gpu(monkeypatch):
    import torch
    from training import native_generation_gate
    from training.train_dpo import train_dpo
    calls = []

    def reject(report, expected_model_dir=None):
        calls.append(expected_model_dir)
        raise ValueError('native completion must pass')

    monkeypatch.setattr(native_generation_gate, 'require_native_completion', reject)
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    with pytest.raises(ValueError, match='native completion must pass'):
        train_dpo(model_path='candidate')
    assert calls == ['candidate']


def test_dpo_preserves_existing_candidate(monkeypatch, tmp_path):
    from training import native_generation_gate
    from training.train_dpo import train_dpo
    monkeypatch.setattr(native_generation_gate, 'require_native_completion', lambda *a, **k: {})
    weights = tmp_path / 'adapter_model.safetensors'
    weights.write_bytes(b'existing candidate')
    with pytest.raises(ValueError, match='new isolated candidate'):
        train_dpo(model_path='candidate', output_dir=str(tmp_path))
    assert weights.read_bytes() == b'existing candidate'
