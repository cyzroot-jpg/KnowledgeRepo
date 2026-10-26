"""第 1 章：字符级分词器。"""

import json
from pathlib import Path
from typing import Iterable, Sequence


class CharTokenizer:
    """把每个字符映射成一个整数 id。

    vocab 的顺序固定为 sorted(set(text))，这样同一份语料每次得到的 id 都一样。
    """

    def __init__(self, vocab: Sequence[str]):
        # 未知字符
        self.unk_token = "<|UNK|>"
        self.vocab = list(vocab)
        # 将未知字符添加到词表中
        self.vocab = self.unk_token + self.vocab
        self.stoi = {ch: i for i, ch in enumerate(self.vocab)}
        self.itos = {i: ch for i, ch in enumerate(self.vocab)}

    @classmethod
    # 开始分词
    def from_text(cls, text: str) -> "CharTokenizer":
        if not text:
            raise ValueError("文本不能为空")
        return cls(sorted(set(text)))

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    def encode(self, text: str) -> list[int]:
        ids = []
        for ch in text:
            # if ch not in self.stoi:
            #     raise ValueError(f"字符 {ch!r} 不在词表中，请扩充语料或使用 BPE 分词器")
            ids.append(self.stoi[ch])
        return ids

    def decode(self, ids: Iterable[int]) -> str:
        chars = []
        for token_id in ids:
            token_id = int(token_id)
            if token_id not in self.itos:
                raise ValueError(f"token id {token_id} 不在词表中")
            chars.append(self.itos[token_id])
        return "".join(chars)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"type": "char", "vocab": self.vocab}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "CharTokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("type") != "char":
            raise ValueError("这不是一个字符级分词器文件")
        return cls(payload["vocab"])