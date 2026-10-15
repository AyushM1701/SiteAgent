import pytest
from agent.agent_protocol import get_default_tokenizer, set_default_tokenizer


@pytest.fixture(autouse=True)
def isolate_default_tokenizer():
    """Ensure the global _DEFAULT_TOKENIZER does not leak across test boundaries."""
    orig = get_default_tokenizer()
    yield
    set_default_tokenizer(orig)
