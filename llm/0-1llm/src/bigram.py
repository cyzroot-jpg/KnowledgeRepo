"""第 3 章：Bigram 基线模型。

Bigram 只看前一个 token 来预测下一个 token。
它非常简单，但能帮我们验证「数据 -> 损失 -> 反向传播 -> 生成」整条链路。
"""

import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from .data import build_datasets, get_batch, read_text
from .tokenizer import CharTokenizer
from .utils import COURSE_ROOT, pick_device, set_seed


class BigramLM(nn.Module):
    def __init__(self, vocab_size: int):
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, vocab_size)

    def forward(
        self,
        idx: torch.Tensor,
        targets: torch.Tensor | None = None,
    ):
        logits = self.token_embedding(idx)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
            )
        return logits, loss


@torch.no_grad()
def sample(
    model: BigramLM,
    idx: torch.Tensor,
    max_new_tokens: int,
    temperature: float = 1.0,
) -> torch.Tensor:
    model.eval()
    for _ in range(max_new_tokens):
        logits, _ = model(idx[:, -1:])
        logits = logits[:, -1, :] / temperature
        probs = F.softmax(logits, dim=-1)
        next_id = torch.multinomial(probs, num_samples=1)
        idx = torch.cat([idx, next_id], dim=1)
    return idx


def main() -> None:
    parser = argparse.ArgumentParser(description="训练一个 Bigram 语言模型")
    parser.add_argument(
        "--data",
        type=Path,
        default=COURSE_ROOT / "data" / "tiny_corpus.txt",
    )
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--eval-interval", type=int, default=100)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--prompt", default="小禾")
    parser.add_argument("--max-new-tokens", type=int, default=120)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    device = pick_device(args.device)

    text = read_text(args.data)
    tokenizer = CharTokenizer.from_text(text)
    train_ds, val_ds = build_datasets(text, tokenizer, block_size=1)

    model = BigramLM(tokenizer.vocab_size).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    uniform_loss = torch.log(torch.tensor(float(tokenizer.vocab_size))).item()
    print(
        f"设备: {device} | 词表: {tokenizer.vocab_size} | "
        f"训练 token: {len(train_ds) + 1}"
    )
    print(f"随机猜测的交叉熵约为 ln(V) = {uniform_loss:.3f}")

    for step in range(1, args.steps + 1):
        x, y = get_batch(train_ds, args.batch_size, device)
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss.backward()
        optimizer.step()

        if step == 1 or step % args.eval_interval == 0:
            with torch.no_grad():
                vx, vy = get_batch(val_ds, args.batch_size, device)
                _, val_loss = model(vx, vy)
            print(
                f"step {step:4d} | train {loss.item():.3f} | "
                f"val {val_loss.item():.3f}"
            )

    start = tokenizer.encode(args.prompt) or [0]
    idx = torch.tensor([start], device=device)
    out = sample(model, idx, args.max_new_tokens, args.temperature)

    print("\n生成结果：")
    print(tokenizer.decode(out[0].tolist()))


if __name__ == "__main__":
    main()