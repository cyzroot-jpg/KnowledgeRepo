"""第 2 章：把文本变成训练用的 (输入, 目标) 批次。"""

from pathlib import Path

import torch
from torch.utils.data import Dataset

from .tokenizer import CharTokenizer


def read_text(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"语料文件为空：{path}")
    return text


def split_text(text: str, val_ratio: float = 0.1) -> tuple[str, str]:
    """按字符切分训练集和验证集，验证集取末尾一部分。"""

    if not 0.0 < val_ratio < 1.0:
        raise ValueError("val_ratio 必须在 (0, 1) 之间")
    cut = int(len(text) * (1.0 - val_ratio))
    return text[:cut], text[cut:]


class TokenDataset(Dataset):
    """一个滑动窗口数据集。

    第 i 个样本是 ids[i : i+block_size+1]：
        x = 前 block_size 个 token
        y = 后 block_size 个 token（即 x 整体右移一位）
    """

    def __init__(self, ids: list[int] | tuple[int, ...] | torch.Tensor, block_size: int):
        self.ids = torch.as_tensor(ids, dtype=torch.long)
        self.block_size = block_size
        if self.block_size < 1:
            raise ValueError("block_size 必须 >= 1")
        if len(self.ids) <= self.block_size:
            raise ValueError(
                f"token 数 {len(self.ids)} 必须大于 block_size {self.block_size}"
            )

    def __len__(self) -> int:
        return len(self.ids) - self.block_size

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        chunk = self.ids[index : index + self.block_size + 1]
        return chunk[:-1], chunk[1:]


def build_datasets(
    text: str,
    tokenizer: CharTokenizer,
    block_size: int,
    val_ratio: float = 0.1,
) -> tuple[TokenDataset, TokenDataset]:
    train_text, val_text = split_text(text, val_ratio)
    train_ds = TokenDataset(tokenizer.encode(train_text), block_size)
    val_ds = TokenDataset(tokenizer.encode(val_text), block_size)
    return train_ds, val_ds


def get_batch(
    dataset: TokenDataset,
    batch_size: int,
    device: str | torch.device = "cpu",
    generator: torch.Generator | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """随机抽 batch_size 个窗口，堆成 [B, T] 的两个张量。"""

    if batch_size < 1:
        raise ValueError("batch_size 必须 >= 1")
    indices = torch.randint(
        0,
        len(dataset),
        (batch_size,),
        generator=generator,
    )
    pairs = [dataset[int(i)] for i in indices]
    x = torch.stack([pair[0] for pair in pairs])
    y = torch.stack([pair[1] for pair in pairs])
    return x.to(device), y.to(device)