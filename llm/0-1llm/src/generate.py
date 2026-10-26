"""第 7 章：自回归生成和常用采样策略。"""

import argparse
from pathlib import Path

import torch
import torch.nn.functional as F

from .config import GPTConfig
from .model import GPT
from .tokenizer import CharTokenizer
from .utils import COURSE_ROOT, pick_device, set_seed


def top_k_filter(logits: torch.Tensor, k: int) -> torch.Tensor:
    if k < 1:
        raise ValueError("top_k 必须 >= 1")
    k = min(k, logits.size(-1))
    kth_value = torch.topk(logits, k, dim=-1).values[..., -1, None]
    return logits.masked_fill(logits < kth_value, float("-inf"))


def top_p_filter(logits: torch.Tensor, p: float) -> torch.Tensor:
    if not 0.0 < p <= 1.0:
        raise ValueError("top_p 必须在 (0, 1] 之间")

    sorted_logits, sorted_indices = torch.sort(
        logits,
        descending=True,
        dim=-1,
    )
    sorted_probs = F.softmax(sorted_logits, dim=-1)
    cumulative = torch.cumsum(sorted_probs, dim=-1)

    remove = (cumulative - sorted_probs) > p
    sorted_logits = sorted_logits.masked_fill(remove, float("-inf"))

    filtered = torch.full_like(logits, float("-inf"))
    return filtered.scatter(1, sorted_indices, sorted_logits)


@torch.no_grad()
def generate(
    model: GPT,
    idx: torch.Tensor,
    max_new_tokens: int,
    temperature: float = 1.0,
    top_k: int | None = None,
    top_p: float | None = None,
    greedy: bool = False,
) -> torch.Tensor:
    """从 idx: [B, T] 开始，一次生成一个 token。"""

    if idx.size(1) == 0:
        raise ValueError("提示词不能为空")
    if not greedy and temperature <= 0:
        raise ValueError("temperature 必须 > 0")

    was_training = model.training
    model.eval()
    try:
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -model.config.block_size :]
            logits, _ = model(idx_cond)
            logits = logits[:, -1, :]

            if greedy:
                next_id = torch.argmax(logits, dim=-1, keepdim=True)
            else:
                logits = logits / temperature
                if top_k is not None:
                    logits = top_k_filter(logits, top_k)
                if top_p is not None:
                    logits = top_p_filter(logits, top_p)
                probs = F.softmax(logits, dim=-1)
                next_id = torch.multinomial(probs, num_samples=1)

            idx = torch.cat([idx, next_id], dim=1)
    finally:
        model.train(was_training)

    return idx


def load_checkpoint(
    path: str | Path,
    device: torch.device,
) -> tuple[GPT, CharTokenizer]:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    config = GPTConfig(**checkpoint["config"])
    model = GPT(config)
    model.load_state_dict(checkpoint["model"])
    model.to(device)
    model.eval()

    tokenizer = CharTokenizer(checkpoint["vocab"])
    return model, tokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description="加载 checkpoint 并生成文本")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=COURSE_ROOT / "checkpoints" / "ckpt.pt",
    )
    parser.add_argument("--prompt", default="小禾")
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=40, help="0 表示关闭 top-k")
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--greedy", action="store_true")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.checkpoint.exists():
        raise SystemExit(
            f"找不到 checkpoint：{args.checkpoint}\n"
            "请先运行：python -m src.train"
        )

    set_seed(args.seed)
    device = pick_device(args.device)
    model, tokenizer = load_checkpoint(args.checkpoint, device)

    prompt_ids = tokenizer.encode(args.prompt)
    if not prompt_ids:
        raise SystemExit("提示词不能为空")

    idx = torch.tensor([prompt_ids], device=device)
    top_k = args.top_k if args.top_k > 0 else None
    out = generate(
        model,
        idx,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_k=top_k,
        top_p=args.top_p,
        greedy=args.greedy,
    )

    print(tokenizer.decode(out[0].tolist()))


if __name__ == "__main__":
    main()