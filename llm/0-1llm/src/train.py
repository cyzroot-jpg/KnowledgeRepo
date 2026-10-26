"""第 6 章：训练循环、学习率调度、评估和 checkpoint。"""

import argparse
import math
from dataclasses import asdict
from pathlib import Path

import torch

from .config import MODEL_PRESETS, TrainConfig, build_gpt_config
from .data import build_datasets, get_batch, read_text
from .generate import generate
from .model import GPT, count_parameters
from .tokenizer import CharTokenizer
from .utils import COURSE_ROOT, pick_device, set_seed


def configure_optimizer(model: GPT, cfg: TrainConfig) -> torch.optim.Optimizer:
    """矩阵/向量参数做 weight decay，bias 和 LayerNorm 不做。"""

    decay = []
    no_decay = []
    for param in model.parameters():
        if not param.requires_grad:
            continue
        if param.dim() >= 2:
            decay.append(param)
        else:
            no_decay.append(param)

    groups = [
        {"params": decay, "weight_decay": cfg.weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]
    return torch.optim.AdamW(
        groups,
        lr=cfg.learning_rate,
        betas=(0.9, 0.95),
    )


def get_lr(step: int, cfg: TrainConfig) -> float:
    """线性 warmup + 余弦退火。"""

    if step < cfg.warmup_steps:
        return cfg.learning_rate * (step + 1) / max(1, cfg.warmup_steps)
    if step >= cfg.max_steps:
        return cfg.min_lr

    progress = (step - cfg.warmup_steps) / max(1, cfg.max_steps - cfg.warmup_steps)
    coeff = 0.5 * (1.0 + math.cos(math.pi * progress))
    return cfg.min_lr + coeff * (cfg.learning_rate - cfg.min_lr)


@torch.no_grad()
def estimate_loss(
    model: GPT,
    train_ds,
    val_ds,
    cfg: TrainConfig,
    device: torch.device,
    generator: torch.Generator,
) -> dict[str, float]:
    model.eval()
    result = {}
    for split, dataset in (("train", train_ds), ("val", val_ds)):
        losses = torch.zeros(cfg.eval_iters)
        for i in range(cfg.eval_iters):
            x, y = get_batch(
                dataset,
                cfg.batch_size,
                device,
                generator,
            )
            _, loss = model(x, y)
            losses[i] = loss.item()
        result[split] = losses.mean().item()
    model.train()
    return result


def save_checkpoint(
    path: Path,
    model: GPT,
    config,
    tokenizer: CharTokenizer,
    step: int,
    val_loss: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model": model.state_dict(),
            "config": asdict(config),
            "vocab": tokenizer.vocab,
            "step": step,
            "val_loss": val_loss,
        },
        path,
    )


def run_training(
    model: GPT,
    train_ds,
    val_ds,
    cfg: TrainConfig,
    tokenizer: CharTokenizer,
    device: torch.device,
    out_dir: Path,
    generator: torch.Generator,
) -> None:
    optimizer = configure_optimizer(model, cfg)
    best_val = float("inf")

    for step in range(1, cfg.max_steps + 1):
        lr = get_lr(step, cfg)
        for group in optimizer.param_groups:
            group["lr"] = lr

        x, y = get_batch(
            train_ds,
            cfg.batch_size,
            device,
            generator,
        )
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(x, y)

        loss.backward()
        if cfg.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        optimizer.step()

        if step == 1 or step % cfg.log_interval == 0:
            print(f"step {step:5d}/{cfg.max_steps} | lr {lr:.2e} | train {loss.item():.4f}")

        if step % cfg.eval_interval == 0 or step == cfg.max_steps:
            losses = estimate_loss(
                model,
                train_ds,
                val_ds,
                cfg,
                device,
                generator,
            )
            perplexity = math.exp(losses["val"])
            print(
                f"step {step:5d} | train {losses['train']:.4f} | "
                f"val {losses['val']:.4f} | ppl {perplexity:.2f}"
            )

            if losses["val"] < best_val:
                best_val = losses["val"]
                save_checkpoint(
                    out_dir / "ckpt.pt",
                    model,
                    model.config,
                    tokenizer,
                    step,
                    losses["val"],
                )
                print(f"  -> 保存最优 checkpoint（val {best_val:.4f}）")

    print(f"训练结束，最优验证损失 {best_val:.4f}")


def run_overfit(
    model: GPT,
    train_ds,
    cfg: TrainConfig,
    tokenizer: CharTokenizer,
    device: torch.device,
    generator: torch.Generator,
) -> None:
    """用同一个 batch 反复训练，验证模型和训练循环没有问题。"""

    x, y = get_batch(train_ds, cfg.batch_size, device, generator)
    optimizer = configure_optimizer(model, cfg)

    print("过拟合单个 batch：损失应该一路下降到接近 0。")
    for step in range(1, cfg.max_steps + 1):
        lr = get_lr(step, cfg)
        for group in optimizer.param_groups:
            group["lr"] = lr

        optimizer.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss.backward()
        if cfg.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        optimizer.step()

        if step == 1 or step % cfg.log_interval == 0:
            print(f"step {step:4d}/{cfg.max_steps} | lr {lr:.2e} | loss {loss.item():.4f}")

    prompt_ids = tokenizer.encode("小禾")
    idx = torch.tensor([prompt_ids], device=device)
    out = generate(
        model,
        idx,
        max_new_tokens=80,
        temperature=0.8,
        top_k=40,
    )
    print("\n过拟合后的输出（基本是训练样本的复读）：")
    print(tokenizer.decode(out[0].tolist()))


def sample_text(
    model: GPT,
    tokenizer: CharTokenizer,
    prompt: str,
    device: torch.device,
    max_new_tokens: int,
) -> str:
    prompt_ids = tokenizer.encode(prompt)
    if not prompt_ids:
        prompt_ids = [0]
    idx = torch.tensor([prompt_ids], device=device)
    out = generate(
        model,
        idx,
        max_new_tokens=max_new_tokens,
        temperature=0.8,
        top_k=40,
    )
    return tokenizer.decode(out[0].tolist())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="训练一个迷你 GPT")
    parser.add_argument(
        "--data",
        type=Path,
        default=COURSE_ROOT / "data" / "tiny_corpus.txt",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(MODEL_PRESETS),
        default="tiny",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=COURSE_ROOT / "checkpoints",
    )
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overfit", action="store_true")
    parser.add_argument("--prompt", default="小禾")
    parser.add_argument("--max-new-tokens", type=int, default=150)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = pick_device(args.device)

    text = read_text(args.data)
    tokenizer = CharTokenizer.from_text(text)
    config = build_gpt_config(tokenizer.vocab_size, args.preset)
    train_ds, val_ds = build_datasets(text, tokenizer, config.block_size)

    train_cfg = TrainConfig(seed=args.seed)
    if args.max_steps is not None:
        train_cfg.max_steps = args.max_steps
    elif args.overfit:
        train_cfg.max_steps = 300
    if args.batch_size is not None:
        train_cfg.batch_size = args.batch_size
    if args.lr is not None:
        train_cfg.learning_rate = args.lr

    model = GPT(config).to(device)
    generator = torch.Generator().manual_seed(train_cfg.seed)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.save(args.out_dir / "tokenizer.json")

    print(
        f"设备: {device} | 预设: {args.preset} | "
        f"词表: {config.vocab_size} | block_size: {config.block_size}"
    )
    print(
        f"层数: {config.n_layer} | 头数: {config.n_head} | "
        f"d_model: {config.n_embd} | 参数量: {count_parameters(model):,}"
    )
    print(
        f"训练 token: {len(train_ds) + config.block_size} | "
        f"验证 token: {len(val_ds) + config.block_size}"
    )

    if args.overfit:
        run_overfit(
            model,
            train_ds,
            train_cfg,
            tokenizer,
            device,
            generator,
        )
        return

    run_training(
        model,
        train_ds,
        val_ds,
        train_cfg,
        tokenizer,
        device,
        args.out_dir,
        generator,
    )

    checkpoint_path = args.out_dir / "ckpt.pt"
    if checkpoint_path.exists():
        checkpoint = torch.load(
            checkpoint_path,
            map_location=device,
            weights_only=False,
        )
        model.load_state_dict(checkpoint["model"])

    print("\n生成示例：")
    print(
        sample_text(
            model,
            tokenizer,
            args.prompt,
            device,
            args.max_new_tokens,
        )
    )


if __name__ == "__main__":
    main()