"""课程代码的单元测试。

运行：
    python -m unittest discover -s tests -v
"""

import tempfile
import unittest
from pathlib import Path

import torch

from src.config import GPTConfig
from src.generate import generate
from src.model import GPT
from src.tokenizer import CharTokenizer


class TestTokenizer(unittest.TestCase):
    def test_roundtrip(self):
        tokenizer = CharTokenizer.from_text("小禾与灯。\n")
        text = "小禾与灯"
        self.assertEqual(tokenizer.decode(tokenizer.encode(text)), text)

    def test_unknown_character(self):
        tokenizer = CharTokenizer.from_text("abc")
        with self.assertRaisesRegex(ValueError, "不在词表"):
            tokenizer.encode("z")

    def test_save_and_load(self):
        tokenizer = CharTokenizer.from_text("abcdef")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tokenizer.json"
            tokenizer.save(path)
            loaded = CharTokenizer.load(path)
        self.assertEqual(loaded.vocab, tokenizer.vocab)
        self.assertEqual(loaded.encode("cab"), tokenizer.encode("cab"))


class TestGPT(unittest.TestCase):
    def build_model(self):
        config = GPTConfig(
            vocab_size=17,
            block_size=8,
            n_layer=2,
            n_head=2,
            n_embd=16,
            dropout=0.0,
        )
        return GPT(config).eval()

    def test_forward_shapes_and_loss(self):
        model = self.build_model()
        idx = torch.randint(0, 17, (3, 8))
        targets = torch.randint(0, 17, (3, 8))
        logits, loss = model(idx, targets)
        self.assertEqual(tuple(logits.shape), (3, 8, 17))
        self.assertEqual(loss.ndim, 0)
        self.assertTrue(torch.isfinite(loss))

    def test_attention_is_causal(self):
        model = self.build_model()
        idx = torch.randint(0, 17, (2, 6))
        with torch.no_grad():
            _, _, attns = model(idx, return_attn=True)

        weights = attns[0]
        self.assertEqual(len(attns), 2)
        self.assertEqual(tuple(weights.shape), (2, 2, 6, 6))

        T = weights.size(-1)
        future = torch.triu(
            torch.ones(T, T, dtype=torch.bool),
            diagonal=1,
        )
        self.assertEqual(weights[..., future].abs().max().item(), 0.0)
        self.assertTrue(
            torch.allclose(
                weights.sum(dim=-1),
                torch.ones_like(weights.sum(dim=-1)),
                atol=1e-5,
            )
        )

    def test_backward_reaches_parameters(self):
        model = self.build_model()
        idx = torch.randint(0, 17, (2, 8))
        targets = torch.randint(0, 17, (2, 8))
        _, loss = model(idx, targets)
        loss.backward()
        self.assertIsNotNone(model.lm_head.weight.grad)
        self.assertIsNotNone(model.transformer.h[0].attn.c_attn.weight.grad)

    def test_rejects_sequence_longer_than_block_size(self):
        model = self.build_model()
        idx = torch.randint(0, 17, (1, 9))
        with self.assertRaisesRegex(ValueError, "block_size"):
            model(idx)


class TestGenerate(unittest.TestCase):
    def build_model(self):
        config = GPTConfig(
            vocab_size=17,
            block_size=8,
            n_layer=2,
            n_head=2,
            n_embd=16,
            dropout=0.0,
        )
        return GPT(config).eval()

    def test_greedy_generation_length_and_prefix(self):
        model = self.build_model()
        idx = torch.randint(0, 17, (2, 5))
        out = generate(model, idx, max_new_tokens=4, greedy=True)
        self.assertEqual(tuple(out.shape), (2, 9))
        self.assertTrue(torch.equal(out[:, :5], idx))

    def test_generation_crops_to_context_window(self):
        model = self.build_model()
        idx = torch.randint(0, 17, (1, 12))
        out = generate(
            model,
            idx,
            max_new_tokens=3,
            temperature=0.9,
            top_k=10,
        )
        self.assertEqual(tuple(out.shape), (1, 15))


if __name__ == "__main__":
    unittest.main()