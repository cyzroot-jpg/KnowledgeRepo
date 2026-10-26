# 第 02 章：数据与 batch——构造「下一 token 预测」

> 本章目标：把一维 token 序列切成 `(x, y)` 训练对，理解 `[B, T]` 的形状从哪来，以及为什么一次前向能同时监督所有位置。

---

## 1. 训练目标：给定前文，预测下一个

把语料看成一个很长的 id 序列：

```text
ids = [12, 87, 3, 201, 45, 8, 9, ...]
```

语言模型在每个位置都要回答：

```text
看到 ids[0:i+1]，下一个 id 是什么？
```

所以训练样本的构造方式极其简单：**把同一段序列右移一位，作为目标。**

以语料开头为例：

```text
x = 小 禾 与 灯 \n \n 从 前 ， 有 一 座 青 山 。 山
y = 禾 与 灯 \n \n 从 前 ， 有 一 座 青 山 。 山 下
```

- `x[0] = 小`，目标是 `y[0] = 禾`
- `x[1] = 禾`，目标是 `y[1] = 与`
- …
- `x[15] = 山`，目标是 `y[15] = 下`

一个长度为 `T` 的窗口，能提供 `T` 个预测任务。

---

## 2. 代码走读：`TokenDataset`

打开 [`src/data.py`](../src/data.py)。

```python
class TokenDataset(Dataset):
    def __init__(self, ids, block_size):
        self.ids = torch.as_tensor(ids, dtype=torch.long)
        self.block_size = block_size

    def __len__(self):
        return len(self.ids) - self.block_size

    def __getitem__(self, index):
        chunk = self.ids[index : index + self.block_size + 1]
        return chunk[:-1], chunk[1:]
```

关键点：

1. 取 `block_size + 1` 个 token。
2. 前 `block_size` 个是 `x`。
3. 后 `block_size` 个是 `y`。
4. 所以 `y` 正好是 `x` 右移一位。

`__len__` 是窗口的起始位置数量。如果语料有 1994 个 token、`block_size=64`，那么共有 `1994 - 64 = 1930` 个可能的起点。

> 注意：滑动窗口是**逐字符移动**的，相邻样本高度重叠。这没问题，训练时我们随机采样起点。

---

## 3. 训练集 / 验证集

```python
def split_text(text, val_ratio=0.1):
    cut = int(len(text) * (1.0 - val_ratio))
    return text[:cut], text[cut:]
```

把文本末尾 10% 留作验证集：

```text
2216 个字符
  ├─ 训练: 前 1994 个字符
  └─ 验证: 后 222 个字符
```

验证集不参与梯度更新，只用来判断模型是否在「背答案」。

### 一个容易忽略的细节：分词器用哪部分训练？

本课程为了简单，用**全量文本**建立字符词表：

```python
tokenizer = CharTokenizer.from_text(text)
```

严格来说，真实项目应该只用训练集训练 BPE 词表，避免验证集字符提前进入词表。字符级词表很小，泄漏影响可以忽略；但换成 BPE 时，这是一个必须处理的问题。

---

## 4. 随机取 batch

```python
def get_batch(dataset, batch_size, device="cpu", generator=None):
    indices = torch.randint(0, len(dataset), (batch_size,), generator=generator)
    pairs = [dataset[int(i)] for i in indices]
    x = torch.stack([pair[0] for pair in pairs])
    y = torch.stack([pair[1] for pair in pairs])
    return x.to(device), y.to(device)
```

输出形状：

```text
x: [B, T]
y: [B, T]
```

`B = 16`、`T = 64` 时：

```text
x: [16, 64]
y: [16, 64]
```

一次前向就得到 `16 × 64 = 1024` 个预测任务。这正是 Transformer 高效的地方：**训练时所有位置并行计算。**

---

## 5. 为什么可以并行，而生成时必须一个一个来？

训练时，虽然模型一次看到整段 `x`，但注意力有**因果掩码**：

```text
位置 0 只能看 0
位置 1 只能看 0, 1
位置 2 只能看 0, 1, 2
...
```

所以位置 5 的输出不会偷看位置 6 的 token。每个位置的预测都是合法的「只看过去」。

生成时没有真实的下一个 token 可以喂，只能：

1. 用已有序列预测下一个
2. 采样出一个 token
3. 拼到序列末尾
4. 重复

这就是第 07 章的**自回归生成**。

---

## 6. 动手观察

在 `llm/0-1llm` 目录下启动 Python：

```python
>>> from src.data import read_text, build_datasets, get_batch
>>> from src.tokenizer import CharTokenizer
>>> text = read_text("data/tiny_corpus.txt")
>>> tok = CharTokenizer.from_text(text)
>>> train_ds, val_ds = build_datasets(text, tok, block_size=16)
>>> len(train_ds)
1978
>>> x, y = train_ds[0]
>>> tok.decode(x.tolist())
'小禾与灯\n\n从前，有一座青山。山'
>>> tok.decode(y.tolist())
'禾与灯\n\n从前，有一座青山。山下'
>>> xb, yb = get_batch(train_ds, batch_size=4)
>>> xb.shape, yb.shape
(torch.Size([4, 16]), torch.Size([4, 16]))
```

再验证「右移一位」：

```python
>>> torch.equal(x[1:], y[:-1])
True
```

---

## 7. 一个 batch 里发生了什么？

假设 `B=2, T=4`，模型输入：

```text
x = [[小, 禾, 与, 灯],
     [从, 前, 有, 座]]
```

模型输出 logits `[2, 4, V]`。损失计算时把 batch 和序列维度摊平：

```text
logits.reshape(-1, V)   ->  [8, V]
targets.reshape(-1)     ->  [8]
```

然后对这 8 个预测求平均交叉熵：

```text
位置 (0,0): 预测 "小" 的下一个 -> 目标 "禾"
位置 (0,1): 预测 "禾" 的下一个 -> 目标 "与"
...
位置 (1,3): 预测 "座" 的下一个 -> 目标 "山"
```

这就是 [`src/model.py`](../src/model.py) 里这一段：

```python
loss = F.cross_entropy(
    logits.reshape(-1, logits.size(-1)),
    targets.reshape(-1),
)
```

---

## 8. 本章练习

### 练习 1：打印更多样本

取 `train_ds[100]`，打印 `x`、`y` 的文本，确认它们仍然只差一个字符。再取一个靠近末尾的样本，观察窗口如何截断。

### 练习 2：改变 `block_size`

分别用 `block_size=8`、`16`、`64` 建立数据集，打印 `len(dataset)`。

问题：

- `block_size` 越大，样本数量越多还是越少？
- 为什么不能把 `block_size` 设得比语料还长？
- 增大 `block_size` 对显存/内存有什么影响？

### 练习 3：实现 stride

当前窗口起点是 `0, 1, 2, ...`。实现一个 `stride` 参数，让起点每次移动 `stride` 步：

```python
dataset = TokenDataset(ids, block_size=64, stride=32)
```

思考：训练时用 `stride > 1` 有什么好处和坏处？

### 练习 4：检查数据泄漏

如果把验证集的前 64 个 token 也放进训练集，会发生什么？为什么验证损失会变得「好看但虚假」？

---

## 9. 自检清单

- [ ] 我能解释 `x` 和 `y` 为什么只差一位
- [ ] 我知道 `[B, T]` 里的 `B` 和 `T` 分别是什么
- [ ] 我理解训练时可以并行、生成时必须串行的原因
- [ ] 我知道验证集的作用
- [ ] 我能说出 `block_size` 的两个影响：上下文长度、样本数量

下一章：先训练一个最简单的 Bigram，把整条链路跑通。

[第 03 章：Bigram 基线 →](./03_bigram.md)