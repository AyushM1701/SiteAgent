import torch
import torch.nn.functional as F
from training.memory_loss import chunked_causal_loss


def test_chunked_loss_matches_dense_causal_loss_with_masked_prompts():
    torch.manual_seed(7)
    hidden = torch.randn(2, 12, 8)
    head = torch.nn.Linear(8, 17, bias=False)
    labels = torch.randint(0, 17, (2, 12))
    labels[:, :5] = -100
    labels[1, 10:] = -100
    expected = F.cross_entropy(head(hidden[:, :-1]).reshape(-1,17), labels[:,1:].reshape(-1))
    actual = chunked_causal_loss(hidden, labels, head, chunk_size=3)
    torch.testing.assert_close(actual, expected)
