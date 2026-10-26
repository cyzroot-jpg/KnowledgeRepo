# 第 03 章：Bigram 基线——先让整条链路跑通

> 本章目标：用一个极简模型验证「数据 → 前向 → 损失 → 反向传播 → 生成」全部打通，并建立一个可以对比的损失基线。

---

## 1. 为什么要先写一个「笨」模型？

直接上 Transformer 很容易一次性引入太多 bug：

- 分词错了
- 数据错位了
- 损失算错了
- 学习率太大了
- 注意力 mask 反了

最后损失不下降，你根本不知道是哪一层的问题。

**工程上的正确顺序是：先跑通最小可行版本，再逐步增加复杂度。**

Bigram 就是那个最小版本。

---

## 2. Bigram 在做什么？

Bigram 假设：下一个 token 只依赖**前一个** token。

```text
P(下一个 | 前一个)
```

它本质上是一张 `V × V` 的转移概率表：

```text
            下一个 token
          小   禾   与   灯  ...
前一个 小  0.1 0.6 0.2 0.1
      禾  0.2 0.1 0.5 0.2
      与  ...
      灯  ...
```

代码里不需要显式存概率，只存**分数（logits）**，再用交叉熵训练：

```python
class BigramLM(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, vocab_size)

    def forward(self, idx, targets=None):
        logits = self.token_embedding(idx)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
            )
        return logits, loss
```

`nn.Embedding(V, V)` 就是一个 `V × V` 的查找表：

- 输入 `idx` 形状 `[B, T]`
- 输出 `logits` 形状 `[B, T, V]`
- 每个位置的输出就是「以这个位置 token 为行号」的那一行

没有注意力，没有 MLP，没有位置编码。它甚至不关心中文语义，只统计「谁后面常跟谁」。

---

## 3. 交叉熵和「随机猜测」基线

词表大小 `V = 326`。如果模型对下一个 token 完全没概念，输出接近均匀分布：

```text
每个 token 概率 ≈ 1 / 326
交叉熵 = -log(1/326) = ln(326) ≈ 5.787
```

所以：

- **损失 > 5.787**：比瞎猜还差（通常是初始化太随机或学习率有问题）
- **损失 ≈ 5.787**：和瞎猜一样
- **损失 < 5.787**：开始学到东西了
- **损失继续下降**：学到了字符转移规律

我们的 Bigram 训练输出：

```text
随机猜测的交叉熵约为 ln(V) = 5.787
step    1 | train 6.337 | val 6.089
step  100 | train 5.897 | val 5.839
step  200 | train 5.134 | val 5.022
step  300 | train 4.719 | val 4.973
step  400 | train 4.587 | val 5.275
step  500 | train 3.789 | val 4.806
```

训练损失明显低于 5.787，说明整条链路是通的。验证损失先降后升，是小语料上过拟合的信号，后面会反复遇到。

---

## 4. 运行 Bigram

```bash
python -m src.bigram --steps 500
```

可调参数：

```bash
python -m src.bigram \
  --steps 1000 \
  --batch-size 64 \
  --lr 0.01 \
  --temperature 0.8 \
  --prompt "小禾"
```

### 代码在做什么

打开 [`src/bigram.py`](../src/bigram.py)，主流程：

```python
text = read_text(args.data)
tokenizer = CharTokenizer.from_text(text)
train_ds, val_ds = build_datasets(text, tokenizer, block_size=1)

model = BigramLM(tokenizer.vocab_size).to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

for step in range(1, args.steps + 1):
    x, y = get_batch(train_ds, args.batch_size, device)
    _, loss = model(x, y)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()
```

注意 `block_size=1`：每个样本的 `x` 长度是 1，`y` 是它的下一个字符。

生成时也只看最后一个 token：

```python
logits, _ = model(idx[:, -1:])
```

---

## 5. 生成结果为什么像乱码？

Bigram 只看前一个字符。它可能学会了：

```text
"小" 后面常跟 "禾"
"。" 后面常跟 "\n"
```

但它不知道「小禾」「桂花树」「小狐狸」这些多字词，也无法维持句子主题。所以生成出来会是一串局部合理、整体混乱的字符。

这正好说明：**上下文长度是语言模型能力的核心。** 下一章的注意力，就是用来让模型看到更长的上下文。

---

## 6. 和后面 GPT 的关系

| 模型 | 能看到的历史 | 参数量（本课程） | 能力 |
| :--- | :--- | :---: | :--- |
| Bigram | 1 个 token | 106,276 | 字符转移 |
| 迷你 GPT | 64 个 token | 125,056 | 短句模式、局部语法 |

Bigram 的参数量甚至不小（`326 × 326 ≈ 10.6 万`），但它**没有上下文建模能力**。参数多不等于聪明，结构决定了它能利用多少信息。

---

## 7. 本章练习

### 练习 1：用计数实现 Bigram

不用梯度下降，直接统计语料中每个字符后面跟什么：

```python
counts[prev_id][next_id] += 1
```

然后归一化成概率，写一个采样函数。和训练出来的 Bigram 比较生成结果。

问题：计数法在什么情况下会遇到「概率为 0」的问题？怎么用平滑（smoothing）解决？

### 练习 2：调整温度

用 `--temperature 0.5` 和 `--temperature 1.5` 各生成一次。

- 低温时输出更保守还是更随机？
- 高温时为什么更容易出现罕见字符？

### 练习 3：只看高频 token

统计语料中频率最高的 20 个字符。它们的 Bigram 转移是否更容易学会？低频字符对损失贡献大吗？

### 练习 4：解释验证损失上升

训练损失从 3.79 继续下降，但验证损失从 4.80 开始上升。用「模型容量 vs 数据量」解释这个现象。

---

## 8. 自检清单

- [ ] 我理解 Bigram 的「只看前一个 token」假设
- [ ] 我知道 `ln(V)` 是随机猜测的交叉熵基线
- [ ] 我能独立运行 `python -m src.bigram`
- [ ] 我明白 Bigram 参数量不小，但上下文能力很弱
- [ ] 我能解释为什么下一步需要注意力

下一章：真正的主角——因果自注意力。

[第 04 章：注意力机制 →](./04_attention.md)