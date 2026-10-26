# 第 08 章：现代改进——从 GPT-2 到 Llama

> 本章目标：认识当前主流 LLM 相对本课程玩具模型的改进，知道每一项解决什么问题、怎么替换，以及升级顺序。

---

## 1. 本课程实现的是「GPT-2 风格」

你写出的结构：

```text
LayerNorm + 可学习位置编码 + GELU MLP + 多头注意力 + 权重绑定
```

这是 GPT-2 那一代的做法。现代开源模型（Llama、Qwen、Mistral 等）大多换成了：

| 组件 | GPT-2 风格（本课程） | 现代常见做法 |
| :--- | :--- | :--- |
| 归一化 | LayerNorm | **RMSNorm** |
| 位置编码 | 可学习绝对位置 | **RoPE** |
| 前馈网络 | GELU MLP | **SwiGLU** |
| 注意力 | 多头（MHA） | **GQA / MQA** |
| 注意力计算 | 手写 QKᵀ + softmax | **FlashAttention / SDPA** |
| 偏置 | Linear 带 bias | **多数去掉 bias** |
| 精度 | fp32 | **bf16 / fp16 + 混合精度** |
| 并行 | 单卡 | **DDP / FSDP / 张量并行** |

好消息：**骨架完全没变。** 仍然是「Embedding → N 层 Block → LM Head」，仍然是下一 token 预测。改的是零件。

---

## 2. RMSNorm：更便宜的归一化

LayerNorm：

```text
x̂ = (x - mean(x)) / √(var(x) + ε)
y = γ ⊙ x̂ + β
```

RMSNorm 去掉了减均值和 β：

```text
y = γ ⊙ x / √(mean(x²) + ε)
```

```python
class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x):
        x = x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return self.weight * x
```

优点：

- 少一次均值计算和一次减法
- 少一组 bias 参数
- 实践中效果与 LayerNorm 相当，甚至更稳

代价：不再保证输出均值为 0。现代模型通常认为这没关系。

---

## 3. RoPE：旋转位置编码

可学习位置编码有两个问题：

1. 训练时 `block_size=64`，推理不能超过 64
2. 模型学的是绝对位置，不是「相隔几个 token」

RoPE 的做法：**把 Q 和 K 的每一对维度看成二维向量，按位置旋转一个角度。**

```text
位置 m 的 Q 旋转 m·θ
位置 n 的 K 旋转 n·θ
两者点积后，结果只依赖 (m - n)
```

所以注意力分数天然携带**相对位置**信息。

关键性质：

- 不需要位置 embedding 参数
- 相对位置外推更自然
- 可以通过调整 `base` 或插值扩展到更长上下文

概念代码（不要求现在实现）：

```python
# 对第 i 对维度，频率 θ_i = base^(-2i/d)
# 位置 pos 的旋转角 = pos * θ_i
# 把 (x[2i], x[2i+1]) 旋转这个角度
```

Llama 系列使用 RoPE 的变体（如 NTK-aware、YaRN）来扩展上下文长度。你不需要背公式，但要理解：**RoPE 让「距离」进入注意力分数，而不是加在输入 embedding 上。**

---

## 4. SwiGLU：带门控的前馈网络

本课程的 MLP：

```text
x -> Linear(C, 4C) -> GELU -> Linear(4C, C)
```

SwiGLU：

```text
x -> 两条分支
     分支 1: Linear(C, H) -> SiLU
     分支 2: Linear(C, H)
     两者逐元素相乘 -> Linear(H, C)
```

```python
class SwiGLU(nn.Module):
    def __init__(self, dim, hidden):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden, bias=False)
        self.w2 = nn.Linear(dim, hidden, bias=False)
        self.w3 = nn.Linear(hidden, dim, bias=False)

    def forward(self, x):
        return self.w3(F.silu(self.w1(x)) * self.w2(x))
```

`SiLU(x) = x * sigmoid(x)`，也叫 Swish。门控让网络可以学习「什么时候让信息通过」。

因为多了一条分支，隐藏维度通常从 `4C` 降到约 `(8/3)C`，保持总参数量接近。

Llama、PaLM 等模型都用 SwiGLU。

---

## 5. GQA：减少 KV Cache

标准多头注意力（MHA）：每个头都有自己的 K、V。

```text
H 个 Query 头 -> H 组 K/V
```

推理时 KV Cache 大小正比于 `H`。头越多，缓存越大。

**MQA（Multi-Query Attention）**：所有 Query 头共享一组 K/V。

**GQA（Grouped-Query Attention）**：折中方案，把 Query 头分组，每组共享一组 K/V。

```text
H = 32 个 Query 头
G = 8 组 K/V
每 4 个 Query 头共享一组 K/V
```

效果：

- KV Cache 缩小到 `G/H`
- 生成速度更快
- 质量通常接近 MHA

Llama 2 70B、Llama 3、Mistral 等广泛使用 GQA。

实现上，Q 仍然是 `H` 个头，K/V 只有 `G` 个头；计算时把 K/V 重复到对应的 Query 组。第 07 章练习的 KV Cache 是理解 GQA 的前置。

---

## 6. FlashAttention：让注意力更快

标准注意力会把 `[T, T]` 的分数矩阵完整写进显存（HBM），再读回来做 softmax。`T=4096` 时，一个头就是 16M 个元素。

FlashAttention 的核心：

- 把 Q/K/V 分块，块内计算
- 用**在线 softmax**（online softmax）避免保存完整分数矩阵
- 中间结果留在 SRAM，不写回 HBM（或大幅减少读写）

它不是近似算法，**数学结果和标准注意力一致**，只是改变了计算顺序和内存访问。

PyTorch 2.0+ 提供了统一入口：

```python
y = F.scaled_dot_product_attention(
    q, k, v,
    dropout_p=dropout if self.training else 0.0,
    is_causal=True,
)
```

底层会自动选择 FlashAttention、memory-efficient 或 math 实现。

在本课程的小模型上，手写版本更利于理解；在生产环境，直接用 SDPA。

---

## 7. 混合精度训练

默认 fp32 训练又慢又占显存。混合精度：

```python
with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
    logits, loss = model(x, y)
```

常见做法：

- 前向/反向用 bf16 或 fp16
- 参数更新、LayerNorm、softmax 保持 fp32
- fp16 需要 `GradScaler` 防止梯度下溢；bf16 一般不需要

```python
scaler = torch.cuda.amp.GradScaler()
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

注意：CPU 上 bf16 支持因硬件而异；本课程默认 fp32 最稳。

---

## 8. 梯度累积与分布式

### 梯度累积

显存放不下大 batch 时：

```python
for i in range(accum_steps):
    x, y = get_batch(...)
    _, loss = model(x, y)
    (loss / accum_steps).backward()

optimizer.step()
optimizer.zero_grad()
```

等价于把 batch size 放大 `accum_steps` 倍，但显存只占一个 micro-batch。

### DDP（DistributedDataParallel）

每张卡一个模型副本，处理不同数据，反向时用 all-reduce 同步梯度：

```text
GPU0: grad_0 ─┐
GPU1: grad_1 ─┼─> 平均 -> 每张卡都得到同一个梯度
GPU2: grad_2 ─┤
GPU3: grad_3 ─┘
```

更省显存的方案还有 FSDP / ZeRO（切分参数、梯度、优化器状态），以及张量并行（按矩阵维度切分）。

这些都属于「把同一份代码放大」，不改变模型原理。

---

## 9. 缩放定律：小模型和大模型的关系

经验规律（简化版）：

```text
损失随参数量、数据量、计算量按幂律下降
```

Chinchilla 的一个重要结论：在固定计算预算下，**参数量和数据量应该同步增长**，大约每个参数配 20 个训练 token（这只是粗略经验，不是硬规则）。

这解释了两件事：

1. 为什么「小模型 + 海量数据」可能优于「大模型 + 小数据」
2. 为什么数据质量和数量往往比模型结构更影响最终效果

本课程用 125K 参数 + 2K token，显然远远不在这个比例上，所以只能学到局部模式。

---

## 10. 升级路线（建议顺序）

不要一次性全改，否则出问题无法定位。推荐：

1. **换成 SDPA**：改动最小，先用测试确认输出一致
2. **加 dropout / 调 weight decay**：改善小数据过拟合
3. **把 LayerNorm 换成 RMSNorm**：改动小，验证损失
4. **把 GELU MLP 换成 SwiGLU**：注意调整隐藏维度
5. **把绝对位置换成 RoPE**：需要改注意力，测试相对位置性质
6. **把 MHA 换成 GQA**：需要改 KV 头和缓存
7. **加混合精度**：GPU 上收益明显
8. **加梯度累积 / DDP**：最后再做分布式

每一步都跑一遍：

```bash
python -m unittest discover -s tests -v
python -m src.train --overfit --max-steps 300
python -m src.train --max-steps 600
```

**先保证正确，再追求更快。**

---

## 11. 本章练习

### 练习 1：实现 RMSNorm

把 `LayerNorm` 换成上面的 `RMSNorm`，训练 600 步。比较：

- 参数量变化（少了 bias）
- 训练速度
- 验证损失

### 练习 2：实现 SwiGLU

把 `MLP` 换成 `SwiGLU`，隐藏维度取 `int(8/3 * C)` 再向上取整到 8 的倍数。比较参数量和损失。

### 练习 3：用 SDPA 替换手写注意力

要求：

- `return_attn=True` 时仍返回权重（SDPA 默认不返回，需要保留一个调试分支）
- 训练/推理输出和原实现一致（`torch.allclose`）
- 在 GPU 上测一下速度差

### 练习 4：给 RoPE 做一个性质测试

写一个测试：位置 `m, n` 的 Q/K 点积，只依赖 `m - n`，与绝对位置无关。可以先实现一个最小版本，再接入模型。

### 练习 5：估算 KV Cache

假设 `B=1, H=32, T=4096, Dh=128, n_layer=32, fp16`，计算 KV Cache 的显存占用。再算 GQA `G=8` 时是多少。

提示：每个 token 每层要存 K 和 V，每个元素 2 字节。

---

## 12. 自检清单

- [ ] 我知道 RMSNorm 和 LayerNorm 的差别
- [ ] 我能解释 RoPE 为什么携带相对位置
- [ ] 我知道 SwiGLU 的门控结构
- [ ] 我能解释 GQA 如何缩小 KV Cache
- [ ] 我知道 FlashAttention 不是近似算法
- [ ] 我理解梯度累积和 DDP 各自解决什么问题
- [ ] 我有一个按顺序升级模型的计划

下一章：从玩具模型走向真实项目。

[第 09 章：下一步 →](./09_next_steps.md)