"""第 4、5 章：因果自注意力、Transformer Block 和 GPT。"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import GPTConfig


class LayerNorm(nn.Module):
    """带可学习缩放和平移的层归一化。"""

    def __init__(self, ndim: int, bias: bool = True):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(ndim))
        self.bias = nn.Parameter(torch.zeros(ndim)) if bias else None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.layer_norm(
            x,
            (self.weight.shape[0],),
            self.weight,
            self.bias,
            eps=1e-5,
        )


class CausalSelfAttention(nn.Module):
    """多头因果自注意力。

    输入  x: [B, T, C]
    输出  y: [B, T, C]
    """

    def __init__(self, config: GPTConfig):
        super().__init__()
        if config.n_embd % config.n_head != 0:
            raise ValueError("n_embd 必须能被 n_head 整除")

        self.n_head = config.n_head
        self.n_embd = config.n_embd
        self.head_dim = config.n_embd // config.n_head

        self.c_attn = nn.Linear(
            config.n_embd,
            3 * config.n_embd,
            bias=config.bias,
        )
        self.c_proj = nn.Linear(
            config.n_embd,
            config.n_embd,
            bias=config.bias,
        )
        self.attn_dropout = nn.Dropout(config.dropout)
        self.resid_dropout = nn.Dropout(config.dropout)

        mask = torch.tril(torch.ones(config.block_size, config.block_size))
        self.register_buffer(
            "causal_mask",
            mask.view(1, 1, config.block_size, config.block_size),
            persistent=False,
        )

    def forward(
        self,
        x: torch.Tensor,
        return_attn: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        B, T, C = x.shape

        q, k, v = self.c_attn(x).split(self.n_embd, dim=2)

        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)

        mask = self.causal_mask[:, :, :T, :T]
        scores = scores.masked_fill(mask == 0, float("-inf"))

        weights = F.softmax(scores, dim=-1)
        weights = self.attn_dropout(weights)

        y = weights @ v
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        y = self.resid_dropout(self.c_proj(y))

        if return_attn:
            return y, weights
        return y


class MLP(nn.Module):
    """位置独立的两层前馈网络，中间维度放大 4 倍。"""

    def __init__(self, config: GPTConfig):
        super().__init__()
        self.c_fc = nn.Linear(
            config.n_embd,
            4 * config.n_embd,
            bias=config.bias,
        )
        self.gelu = nn.GELU()
        self.c_proj = nn.Linear(
            4 * config.n_embd,
            config.n_embd,
            bias=config.bias,
        )
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.c_fc(x)
        x = self.gelu(x)
        x = self.c_proj(x)
        return self.dropout(x)


class Block(nn.Module):
    """Pre-Norm 的 Transformer Block。"""

    def __init__(self, config: GPTConfig):
        super().__init__()
        self.ln_1 = LayerNorm(config.n_embd, bias=config.bias)
        self.attn = CausalSelfAttention(config)
        self.ln_2 = LayerNorm(config.n_embd, bias=config.bias)
        self.mlp = MLP(config)

    def forward(
        self,
        x: torch.Tensor,
        return_attn: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        if return_attn:
            attn_out, weights = self.attn(self.ln_1(x), return_attn=True)
            x = x + attn_out
            x = x + self.mlp(self.ln_2(x))
            return x, weights

        x = x + self.attn(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x


class GPT(nn.Module):
    """一个只做下一 token 预测的 decoder-only Transformer。"""

    def __init__(self, config: GPTConfig):
        super().__init__()
        if config.vocab_size < 1:
            raise ValueError("vocab_size 必须 >= 1")
        self.config = config

        self.transformer = nn.ModuleDict(
            {
                "wte": nn.Embedding(config.vocab_size, config.n_embd),
                "wpe": nn.Embedding(config.block_size, config.n_embd),
                "drop": nn.Dropout(config.dropout),
                "h": nn.ModuleList(
                    [Block(config) for _ in range(config.n_layer)]
                ),
                "ln_f": LayerNorm(config.n_embd, bias=config.bias),
            }
        )

        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)

        # 权重绑定：输入 embedding 和输出投影共享同一个矩阵。
        self.transformer.wte.weight = self.lm_head.weight

        self.apply(self._init_weights)

        # 对残差分支的投影层使用更小的初始化，深层网络更稳定。
        for name, param in self.named_parameters():
            if name.endswith("c_proj.weight"):
                nn.init.normal_(
                    param,
                    mean=0.0,
                    std=0.02 / math.sqrt(2 * config.n_layer),
                )

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self,
        idx: torch.Tensor,
        targets: torch.Tensor | None = None,
        return_attn: bool = False,
    ):
        """idx: [B, T] 的 token id。

        返回 (logits, loss)；
        当 return_attn=True 时返回 (logits, loss, 每层注意力权重)。
        """

        B, T = idx.shape
        if T > self.config.block_size:
            raise ValueError(
                f"序列长度 {T} 超过了 block_size {self.config.block_size}"
            )

        positions = torch.arange(0, T, device=idx.device)
        x = self.transformer.wte(idx) + self.transformer.wpe(positions)
        x = self.transformer.drop(x)

        attns = []
        for block in self.transformer.h:
            if return_attn:
                x, weights = block(x, return_attn=True)
                attns.append(weights)
            else:
                x = block(x)

        x = self.transformer.ln_f(x)
        logits = self.lm_head(x)

        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
            )

        if return_attn:
            return logits, loss, attns
        return logits, loss


def count_parameters(model: nn.Module) -> int:
    return sum(param.numel() for param in model.parameters())