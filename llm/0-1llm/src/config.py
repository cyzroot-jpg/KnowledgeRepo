"""模型结构与训练流程的超参数。"""

from dataclasses import dataclass


@dataclass
class GPTConfig:
    """GPT 模型的结构超参数。"""

    vocab_size: int
    block_size: int = 64
    n_layer: int = 2
    n_head: int = 2
    n_embd: int = 64
    dropout: float = 0.0
    bias: bool = True


@dataclass
class TrainConfig:
    """训练流程的超参数。"""

    batch_size: int = 16
    max_steps: int = 2000
    eval_interval: int = 200
    eval_iters: int = 50
    log_interval: int = 20
    learning_rate: float = 1e-3
    min_lr: float = 1e-4
    warmup_steps: int = 100
    weight_decay: float = 0.01
    grad_clip: float = 1.0
    seed: int = 42


MODEL_PRESETS = {
    "tiny": {
        "block_size": 64,
        "n_layer": 2,
        "n_head": 2,
        "n_embd": 64,
        "dropout": 0.0,
    },
    "small": {
        "block_size": 128,
        "n_layer": 4,
        "n_head": 4,
        "n_embd": 128,
        "dropout": 0.1,
    },
}


def build_gpt_config(vocab_size: int, preset: str = "tiny") -> GPTConfig:
    """根据词表大小和预设组合出一个完整配置。"""

    if preset not in MODEL_PRESETS:
        raise ValueError(f"未知预设 {preset!r}，可选：{sorted(MODEL_PRESETS)}")
    return GPTConfig(vocab_size=vocab_size, **MODEL_PRESETS[preset])