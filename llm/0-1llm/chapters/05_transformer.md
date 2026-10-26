# 第 05 章：Transformer Block——把零件组装成 GPT

> 本章目标：实现 LayerNorm、GELU、残差连接、Pre-Norm Block，并组装出完整的 decoder-only GPT。

---

## 1. 一个 Block 的组成

一个 Transformer Block 只有两个子层：

```text
x ──► LayerNorm ──► Attention ──► + ──► LayerNorm ──► MLP ──► + ──► 输出
 │                                  ▲                          ▲
 └────────────── 残差 ──────────────┘────────── 残差 ─────────┘
```

代码（[`src/model.py`](../src/model.py)）：

```python
class Block(nn.Module):
    def forward(self, x):
        x = x + self.attn(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x
```

就这两行。GPT 就是把这样的 Block 重复 `n_layer` 次。

---

## 2. LayerNorm：让每个 token 的向量稳定

对每个 token 的 `C` 维向量，独立做归一化：

```text
μ = mean(x)
σ² = var(x)
x̂ = (x - μ) / √(σ² + ε)
y = γ ⊙ x̂ + β
```

其中 `γ`、`β` 是可学习的 `C` 维参数。

代码：

```python
class LayerNorm(nn.Module):
    def __init__(self, ndim, bias=True):
        self.weight = nn.Parameter(torch.ones(ndim))
        self.bias = nn.Parameter(torch.zeros(ndim)) if bias else None

    def forward(self, x):
        return F.layer_norm(
            x, (self.weight.shape[0],),
            self.weight, self.bias, eps=1e-5,
        )
```

### 为什么不用 BatchNorm？

BatchNorm 在 batch 维度上统计均值和方差，依赖 batch 里其他样本。语言模型：

- 序列长度可变
- 推理时 batch size 可能为 1
- 自回归生成时一个 token 一个 token 来

LayerNorm 只在单个 token 的 `C` 维上统计，和 batch、序列长度都无关，天然适合。

### Pre-Norm vs Post-Norm

原论文用的是 Post-Norm：

```text
x = LayerNorm(x + Attention(x))
```

GPT-2 之后更常见 Pre-Norm：

```text
x = x + Attention(LayerNorm(x))
```

区别：

- **Post-Norm**：残差后再归一化，训练深层网络时需要小心 warmup
- **Pre-Norm**：归一化在分支里，残差主干保持干净，梯度更容易传回去，深层更稳定

本课程用 Pre-Norm。

---

## 3. GELU 与 MLP

MLP 是逐 token 的两层前馈网络：

```python
class MLP(nn.Module):
    def forward(self, x):
        x = self.c_fc(x)       # C -> 4C
        x = self.gelu(x)
        x = self.c_proj(x)     # 4C -> C
        return self.dropout(x)
```

为什么中间要放大 4 倍？

- 给模型更多非线性表达能力
- `C -> 4C -> C` 是 Transformer 的经典比例
- 现代模型常用 SwiGLU，比例会调整（第 08 章）

GELU 的定义（近似形式）：

```text
GELU(x) ≈ 0.5x(1 + tanh(√(2/π)(x + 0.044715x³)))
```

相比 ReLU，GELU 在 0 附近是平滑的，不是硬折线。`nn.GELU()` 默认使用精确的 erf 形式，行为足够接近。

注意：**Attention 负责 token 之间交换信息，MLP 负责每个 token 内部变换。** 两者缺一不可。

---

## 4. 残差连接：深层网络的高速公路

```python
x = x + self.attn(self.ln_1(x))
```

如果没有 `x +`，每层都会完全覆盖上一层的表示。堆到几十层时：

- 梯度容易消失
- 前面层的信息难以保留
- 训练非常不稳定

残差让每层只学「增量」：

```text
输出 = 输入 + 修改量
```

梯度反传时，有一条直接的加法路径回到前面。这是 ResNet 和 Transformer 能堆深的核心技巧。

---

## 5. 位置编码：告诉模型谁在前谁在后

注意力本身是**置换不变**的：把 token 顺序打乱，QKᵀ 的结果只是跟着重排，模型不知道谁先谁后。

所以需要位置信息。本课程用最简单的**可学习位置编码**：

```python
self.wpe = nn.Embedding(block_size, n_embd)
```

```python
positions = torch.arange(0, T, device=idx.device)
x = self.transformer.wte(idx) + self.transformer.wpe(positions)
```

- `wte`：token embedding，`[V, C]`
- `wpe`：position embedding，`[block_size, C]`
- 两者相加，形状都是 `[B, T, C]`

可学习位置编码的局限：

- 只能处理训练时见过的最大长度
- 不能自然外推到更长序列
- 位置是绝对编号，不直接建模「相对距离」

现代模型多用 RoPE（旋转位置编码），第 08 章会讲。

---

## 6. 完整 GPT

```python
class GPT(nn.Module):
    def __init__(self, config):
        self.transformer = nn.ModuleDict({
            "wte": nn.Embedding(vocab_size, n_embd),
            "wpe": nn.Embedding(block_size, n_embd),
            "drop": nn.Dropout(dropout),
            "h": nn.ModuleList([Block(config) for _ in range(n_layer)]),
            "ln_f": LayerNorm(n_embd),
        })
        self.lm_head = nn.Linear(n_embd, vocab_size, bias=False)
```

前向：

```python
positions = torch.arange(0, T)
x = wte(idx) + wpe(positions)
x = drop(x)

for block in h:
    x = block(x)

x = ln_f(x)
logits = lm_head(x)
```

形状：

```text
idx      [B, T]
wte(idx) [B, T, C]
+ wpe    [B, T, C]
...
logits   [B, T, V]
```

---

## 7. 权重绑定（Weight Tying）

输入 embedding 是 `[V, C]`，输出 LM Head 需要 `[C, V]`。两者形状互为转置，含义也相关：

- 输入：token id → 向量
- 输出：向量 → 每个 token 的分数

GPT-2 让它们共享同一个参数矩阵：

```python
self.transformer.wte.weight = self.lm_head.weight
```

好处：

- 减少参数量（省掉 `V × C`）
- 输入和输出的语义空间被强制一致
- 小模型上通常有正则化效果

注意 `count_parameters` 会正确去重，因为 `named_parameters` 默认不会重复统计共享参数。

---

## 8. 初始化：小模型也要认真对待

```python
nn.init.normal_(module.weight, mean=0.0, std=0.02)
```

残差分支的投影层再用更小的标准差：

```python
nn.init.normal_(
    param,
    mean=0.0,
    std=0.02 / math.sqrt(2 * n_layer),
)
```

原因：残差是累加的。如果每个分支输出方差都一样，堆 `n_layer` 层后主干方差会随层数增长。缩小 `c_proj` 的初始化，可以让深层残差流保持稳定。这是 GPT-2 论文里的做法。

---

## 9. 参数都花在哪了？

对 `n_layer` 层、宽度 `C`、词表 `V`、上下文 `T`：

```text
每层 Attention:
  c_attn: 3C² + 3C
  c_proj: C² + C
  LayerNorm ×2: 4C

每层 MLP:
  c_fc:   4C² + 4C
  c_proj: 4C² + C
  LayerNorm ×2: 4C

每层合计约 12C² + 13C

全部:
  12 · n_layer · C²
+ V · C            (token embedding，与 lm_head 共享)
+ T · C            (位置 embedding)
+ 2C               (最终 LayerNorm)
```

代入本课程配置：

```text
C = 64, V = 326, T = 64, n_layer = 2

12 × 2 × 64²      = 98,304
326 × 64          = 20,864
64 × 64           = 4,096
2 × 64            = 128
                  ---------
总计              = 125,056
```

运行训练脚本会打印同样的数字：

```text
层数: 2 | 头数: 2 | d_model: 64 | 参数量: 125,056
```

可以看到：**大部分参数在 MLP 和 Attention 的矩阵里，embedding 只占一小部分。** 真实大模型也是这个规律，只是 `C` 和层数大了几个数量级。

---

## 10. 运行验证

```bash
python -m src.inspect_shapes
python -m unittest discover -s tests -v
```

重点看：

```text
手工结果和模型一致？ True
总参数量            : 28,032
```

测试里还会验证：

- `logits` 形状是 `[B, T, V]`
- 损失可以反向传播到 `c_attn` 和 `lm_head`
- 注意力权重是下三角
- 输入长度超过 `block_size` 会报错

---

## 11. 本章练习

### 练习 1：去掉残差

把 Block 改成：

```python
x = self.attn(self.ln_1(x))
x = self.mlp(self.ln_2(x))
```

训练 300 步，观察损失。再改回来，对比训练稳定性。

### 练习 2：改成 Post-Norm

尝试：

```python
x = self.ln_1(x + self.attn(x))
x = self.ln_2(x + self.mlp(x))
```

注意：这样最后一层输出可能没有归一化，需要调整 `ln_f`。观察训练是否更容易发散。

### 练习 3：取消权重绑定

把 `self.lm_head` 改成独立的 `nn.Linear(C, V)`，不共享 `wte`。参数量增加多少？小语料上损失有变化吗？

### 练习 4：调整 MLP 倍率

把 `4 * n_embd` 改成 `2 * n_embd` 或 `8 * n_embd`，重新计算参数量，训练并比较。注意：倍率越大，参数量和计算量增长越快。

### 练习 5：用公式预测参数量

不看代码，用上面的公式计算：如果 `C=128, n_layer=4, V=500, T=128`，总参数量是多少？然后用 `count_parameters` 验证。

---

## 12. 自检清单

- [ ] 我能说出 Block 的两个子层和两个残差
- [ ] 我理解 Pre-Norm 和 Post-Norm 的区别
- [ ] 我知道 Attention 和 MLP 各自负责什么
- [ ] 我能解释为什么需要位置编码
- [ ] 我理解权重绑定的作用和代价
- [ ] 我能用公式估算参数量

下一章：把这个模型真正训练起来。

[第 06 章：训练 →](./06_training.md)