"""设备选择、随机种子等通用小工具。"""

import random
from pathlib import Path

import torch

COURSE_ROOT = Path(__file__).resolve().parent.parent


def pick_device(name: str = "auto") -> torch.device:
    """auto 时依次尝试 CUDA、MPS、CPU。"""

    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)