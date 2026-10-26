# 第 04 章：注意力机制——让每个 token 看见上下文

> 本章目标：从零实现缩放点积注意力、因果掩码和多头注意力，并能手算一个 4×4 的注意力矩阵。

---

## 1. 问题：Bigram 看不到上下文

Bigram 只看前一个 token。要理解下面这句话，显然不够：

```text
小禾把灯放在窗台上，因为____太黑了。
```

要填「屋里」还是「山上」，必须看更前面的内容。

注意力机制解决的就是：

> 当前位置应该从历史中**哪些位置**、以**多大权重**读取信息？

---

## 2. Q、K、V 的直觉

每个 token 的向量会生成三个角色：

| 名称 | 含义 | 类比 |
| :--- | :--- | :--- |
| **Q (Query)** | 我想找什么 | 搜索关键词 |
| **K (Key)** | 我能提供什么 | 文档标题/标签 |
| **V (Value)** | 我实际携带的内容 | 文档正文 |

计算流程：

1. 用当前 token 的 Q，和所有历史 token 的 K 做点积 → 相似度分数
2. 分数经过缩放和 softmax → 注意力权重
3. 用权重对所有 V 加权求和 → 当前位置的新表示

用公式写：

```text
Attention(Q, K, V) = softmax(Q Kᵀ / √d_k) V
```

---

## 3. 为什么除以 √d_k？

假设 Q 和 K 的每个分量都是均值 0、方差 1 的独立随机变量。点积有 `d_k` 项：

```text
q · k = q_1 k_1 + ... + q_{d_k} k_{d_k}
```

方差约为 `d_k`。`d_k = 32` 时，分数可能到 ±5 甚至更大。softmax 会把这些分数放大成非常尖锐的分布，导致：

- 几乎所有概率集中在一个 token
- 梯度接近 0，训练变慢

除以 `√d_k` 把方差拉回 1 左右，softmax 处于更平滑的工作区间。

---

## 4. 因果掩码：不能偷看未来

训练时我们一次性把整段文本喂进去。位置 5 的 Q 会看到位置 6、7 的 K——如果不处理，模型就作弊了。

做法：在 softmax 之前，把「未来位置」的分数设成 `-∞`：

```text
scores =
[[ 0.8,  -∞,   -∞,   -∞ ],
 [ 0.2,  0.5,  -∞,   -∞ ],
 [ 0.1,  0.9,  0.3,  -∞ ],
 [ 0.4,  0.2,  0.7,  0.6 ]]
```

softmax 后：

```text
weights =
[[1.00, 0.00, 0.00, 0.00],
 [0.43, 0.57, 0.00, 0.00],
 [0.28, 0.58, 0.14, 0.00],
 [0.24, 0.17, 0.33, 0.26]]
```

每一行和为 1，上三角全为 0。这就是**下三角因果矩阵**。

> 为什么用 `-∞` 而不是 `0`？因为 softmax 的指数是 `exp(score)`。设为 0 会得到 `exp(0)=1`，仍然有权重；设为 `-∞` 才能得到 `exp(-∞)=0`。

---

## 5. 多头注意力

如果只做一次注意力，模型只能学一种「关注方式」。多头让模型并行学习多种关系：

```text
C = 64, H = 4
每个头只看 C/H = 16 维
```

每个头有独立的 Q/K/V 投影，分别计算注意力，最后把结果拼回 `C` 维，再过一个输出投影。

```text
x [B,T,C]
  ├─ head 0: [B,T,16] -> attention -> [B,T,16]
  ├─ head 1: [B,T,16] -> attention -> [B,T,16]
  ├─ head 2: ...
  └─ head 3: ...
       拼接 -> [B,T,64] -> c_proj -> [B,T,64]
```

不同头可能关注不同现象：前一个词、句首、标点、重复模式等。注意：这是**可解释性的经验观察**，不是硬性保证。

---

## 6. 代码逐段拆解

打开 [`src/model.py`](../src/model.py) 的 `CausalSelfAttention`。

### 6.1 一次算出 Q、K、V

```python
self.c_attn = nn.Linear(config.n_embd, 3 * config.n_embd, bias=config.bias)
```

```python
q, k, v = self.c_attn(x).split(self.n_embd, dim=2)
```

把三个矩阵拼成一个大矩阵做一次矩阵乘法，比分别做三次更高效。输出 `[B, T, 3C]`，切成三份 `[B, T, C]`。

### 6.2 拆头

```python
q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
```

形状变化：

```text
[B, T, C] -> [B, T, H, Dh] -> [B, H, T, Dh]
```

把 `H` 挪到前面，方便对最后两维 `[T, Dh]` 做批量矩阵乘法。

### 6.3 分数

```python
scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
```

```text
q:      [B, H, T, Dh]
kᵀ:     [B, H, Dh, T]
scores: [B, H, T, T]
```

`scores[b, h, i, j]` 表示：第 `b` 个样本、第 `h` 个头里，位置 `i` 对位置 `j` 的关注分数。

### 6.4 掩码

```python
mask = self.causal_mask[:, :, :T, :T]
scores = scores.masked_fill(mask == 0, float("-inf"))
```

`causal_mask` 是 `[1, 1, block_size, block_size]` 的下三角矩阵，注册为 buffer，会跟着模型移动到 GPU。

### 6.5 softmax 与加权

```python
weights = F.softmax(scores, dim=-1)
y = weights @ v
```

```text
weights: [B, H, T, T]
v:       [B, H, T, Dh]
y:       [B, H, T, Dh]
```

### 6.6 拼头 + 输出投影

```python
y = y.transpose(1, 2).contiguous().view(B, T, C)
y = self.resid_dropout(self.c_proj(y))
```

```text
[B, H, T, Dh] -> [B, T, H, Dh] -> [B, T, C]
```

注意 `.contiguous()`：`transpose` 后张量在内存里不连续，`view` 需要连续内存；用 `reshape` 也可以。

---

## 7. 完整形状表

| 步骤 | 张量 | 形状 |
| :--- | :--- | :--- |
| 输入 | `x` | `[B, T, C]` |
| QKV 投影 | `qkv` | `[B, T, 3C]` |
| 拆分 | `q, k, v` | `[B, T, C]` |
| 拆头 | `q, k, v` | `[B, H, T, Dh]` |
| 分数 | `scores` | `[B, H, T, T]` |
| 掩码后 softmax | `weights` | `[B, H, T, T]` |
| 加权求和 | `y` | `[B, H, T, Dh]` |
| 拼头 | `y` | `[B, T, C]` |
| 输出投影 | `y` | `[B, T, C]` |

**输入和输出形状完全一样。** 这是残差连接能成立的前提。

---

## 8. 运行并手算验证

```bash
python -m src.inspect_shapes
```

它会打印未训练模型的注意力权重（接近均匀），例如：

```text
tensor([[1.0000, 0.0000, 0.0000, 0.0000, ...],
        [0.5000, 0.5000, 0.0000, 0.0000, ...],
        [0.3330, 0.3330, 0.3330, 0.0000, ...],
        ...])
```

这是**未训练**的模型，所以每个头对历史 token 几乎等权。训练后权重会变得有结构。

然后脚本会用最原始的矩阵乘法重新算一遍：

```text
q, k, v 形状        : (2, 4, 10, 8)  = [B, n_head, T, head_dim]
scores 形状         : (2, 4, 10, 10)  = [B, n_head, T, T]
注意力输出形状      : (2, 10, 32)  = [B, T, C]
手工结果和模型一致？ True
```

如果这一行是 `True`，说明你对注意力的理解和代码实现一致。

---

## 9. 计算量：为什么长上下文很贵

注意力分数矩阵大小是：

```text
B × H × T × T
```

计算量也随 `T²` 增长。`T` 翻倍，注意力的计算和显存大约变成 4 倍。

这就是为什么：

- 长上下文模型需要 FlashAttention、稀疏注意力、KV Cache 等优化
- 上下文长度是模型服务成本的核心变量之一

第 08、09 章会继续讨论。

---

## 10. 本章练习

### 练习 1：去掉缩放

把 `scores / math.sqrt(self.head_dim)` 改成 `scores`，训练几百步，观察：

- 损失是否更容易震荡？
- 注意力权重是否变得非常尖锐？

### 练习 2：反向掩码（经典 bug）

把 `masked_fill(mask == 0, -inf)` 改成 `masked_fill(mask == 1, -inf)`，运行测试。哪个测试会失败？为什么？

### 练习 3：用 PyTorch 内置实现

把手工 QKᵀ + softmax 替换成：

```python
y = F.scaled_dot_product_attention(
    q, k, v,
    dropout_p=self.dropout if self.training else 0.0,
    is_causal=True,
)
```

和原实现比较输出是否一致。再查一下它底层可能调用哪些 kernel（FlashAttention、memory-efficient、math）。

### 练习 4：单头 vs 多头

固定 `C = 64`，分别用 `H = 1` 和 `H = 4` 训练，比较：

- 参数量
- 训练速度
- 生成文本的差异

思考：多头增加了什么？是参数量，还是表达方式？

### 练习 5：可视化注意力

用 `return_attn=True` 取出一层的注意力矩阵，选一个头，把它打印成热力图（可以用 matplotlib，也可以直接用字符画）。观察哪些位置关注句首、标点或前一个词。

---

## 11. 自检清单

- [ ] 我能写出 `Attention(Q,K,V) = softmax(QKᵀ/√d_k)V`
- [ ] 我知道为什么要除以 `√d_k`
- [ ] 我能解释因果掩码为什么用 `-∞`
- [ ] 我清楚 `[B,T,C] -> [B,H,T,Dh]` 的形状变换
- [ ] 我知道注意力的计算量随 `T²` 增长
- [ ] `inspect_shapes` 的手算对比返回 `True`

下一章：把注意力、MLP、残差和 LayerNorm 组装成完整的 Transformer Block。

[第 05 章：Transformer Block →](./05_transformer.md)