"""第 4、5 章：打印形状，并手工复算第一层注意力。"""

import math

import torch

from .config import GPTConfig
from .model import GPT, count_parameters


def main() -> None:
    torch.manual_seed(0)

    config = GPTConfig(
        vocab_size=64,
        block_size=16,
        n_layer=2,
        n_head=4,
        n_embd=32,
        dropout=0.0,
    )
    model = GPT(config).eval()
    model = model.to("cpu")

    B, T = 2, 10
    idx = torch.randint(0, config.vocab_size, (B, T))
    targets = torch.randint(0, config.vocab_size, (B, T))

    with torch.no_grad():
        logits, loss, attns = model(idx, targets=targets, return_attn=True)

    print("=" * 64)
    print("一次前向传播的张量形状")
    print("=" * 64)
    print(f"输入 idx            : {tuple(idx.shape)}  = [B, T]")
    print(f"token embedding     : {tuple(idx.shape + (config.n_embd,))}")
    print(f"位置 embedding      : {(T, config.n_embd)}")
    print(f"注意力权重（每层）  : {tuple(attns[0].shape)}  = [B, n_head, T, T]")
    print(f"输出 logits         : {tuple(logits.shape)}  = [B, T, vocab_size]")
    print(f"loss                : {loss.item():.4f}")

    print("\n第一层注意力权重（batch 0, head 0，保留 3 位小数）：")
    print(attns[0][0, 0].round(decimals=3))

    upper = torch.triu(
        torch.ones(T, T, dtype=torch.bool),
        diagonal=1,
    )
    print(
        "\n上三角（未来位置）的最大权重：",
        attns[0][..., upper].abs().max().item(),
    )
    print(
        "每一行的权重和（应为 1）：",
        attns[0][0, 0].sum(dim=-1).tolist(),
    )

    print("\n" + "=" * 64)
    print("手工复算第一层注意力，和模型实现对比")
    print("=" * 64)

    block = model.transformer.h[0]
    positions = torch.arange(T)
    x = model.transformer.wte(idx) + model.transformer.wpe(positions)
    x = model.transformer.drop(x)
    x_norm = block.ln_1(x)

    C = config.n_embd
    H = config.n_head
    Dh = C // H

    q, k, v = block.attn.c_attn(x_norm).split(C, dim=-1)
    q = q.view(B, T, H, Dh).transpose(1, 2)
    k = k.view(B, T, H, Dh).transpose(1, 2)
    v = v.view(B, T, H, Dh).transpose(1, 2)

    scores = q @ k.transpose(-2, -1) / math.sqrt(Dh)
    mask = torch.tril(torch.ones(T, T, dtype=torch.bool))
    scores = scores.masked_fill(~mask, float("-inf"))
    weights = scores.softmax(dim=-1)

    y = weights @ v
    y = y.transpose(1, 2).contiguous().view(B, T, C)
    manual = block.attn.c_proj(y)
    actual = block.attn(x_norm)

    print(f"q, k, v 形状        : {tuple(q.shape)}  = [B, n_head, T, head_dim]")
    print(f"scores 形状         : {tuple(scores.shape)}  = [B, n_head, T, T]")
    print(f"注意力输出形状      : {tuple(y.shape)}  = [B, T, C]")
    print(f"手工结果和模型一致？ {torch.allclose(manual, actual, atol=1e-6)}")

    print("\n" + "=" * 64)
    print("参数统计")
    print("=" * 64)
    print(f"总参数量            : {count_parameters(model):,}")
    print(
        "其中 token embedding 与 lm_head 共享同一份参数，只计算一次。"
    )


if __name__ == "__main__":
    main()