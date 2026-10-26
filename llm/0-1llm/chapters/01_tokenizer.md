# 第 01 章：分词器——把文本变成数字

> 本章目标：理解为什么需要 token、字符级分词器怎么工作，并亲手完成「文本 ⇄ id」的双向转换。

---

## 1. 神经网络只认识数字

模型内部全是浮点矩阵乘法，它没法直接处理 `"小禾"` 这样的字符串。第一步必须把文本映射成整数序列：

```text
"从前有座山"  ->  [12, 87, 3, 201, 45]
```

这个整数叫 **token id**，映射规则叫 **分词器（tokenizer）**。

分词器有两个方向：

```text
encode: 文本 -> id 列表     训练和推理的输入
decode: id 列表 -> 文本     把模型输出变回人话
```

注意：**分词器本身不是模型，不参与训练。** 它的词表一旦确定就固定下来，模型只认识这些 id。

---

## 2. 字符级、词级还是 BPE？

| 方式 | 例子 | 词表大小 | 优点 | 缺点 |
| :--- | :--- | :---: | :--- | :--- |
| 字符级 | `小` `禾` `，` | 几百~几千 | 简单、无 OOV、中文友好 | 序列长，一个汉字一个 token |
| 词级 | `小禾` `桂花树` | 几万~几十万 | 序列短 | 未登录词无法处理 |
| BPE / SentencePiece | `小` `禾` `桂花` | 3 万~15 万 | 平衡长度与词表，工业标准 | 实现复杂，需要训练词表 |

本课程用**字符级分词**，原因很实际：

1. 不需要额外依赖，不需要预训练词表
2. 中文一个字一个 token，直观
3. 词表只有 326，模型很小，CPU 能跑
4. 你可以清楚看到每个 id 对应哪个字符

代价是序列会变长。等你看懂全部流程后，第 08、09 章会讲怎么换成 BPE。

---

## 3. 代码走读：`CharTokenizer`

打开 [`src/tokenizer.py`](../src/tokenizer.py)，核心只有三件事。

### 3.1 建词表

```python
@classmethod
def from_text(cls, text: str) -> "CharTokenizer":
    if not text:
        raise ValueError("文本不能为空")
    return cls(sorted(set(text)))
```

`set(text)` 去重，`sorted(...)` 排序。

**为什么要排序？** 因为 `set` 的遍历顺序在不同 Python 进程里不保证一致。如果不排序，同一份语料两次训练可能得到不同的 id，checkpoint 就对不上了。排序给了一个**确定性的、可复现的**映射。

注意排序是按 Unicode 码点，不是拼音。所以 `"小禾与灯"` 的词表是：

```python
['与', '小', '灯', '禾']
```

### 3.2 两个字典

```python
self.stoi = {ch: i for i, ch in enumerate(self.vocab)}
self.itos = {i: ch for i, ch in enumerate(self.vocab)}
```

- `stoi`：string to int，编码用
- `itos`：int to string，解码用

这就是查表，时间复杂度 O(1)。

### 3.3 编码与解码

```python
def encode(self, text: str) -> list[int]:
    ids = []
    for ch in text:
        if ch not in self.stoi:
            raise ValueError(f"字符 {ch!r} 不在词表中...")
        ids.append(self.stoi[ch])
    return ids

def decode(self, ids) -> str:
    return "".join(self.itos[int(token_id)] for token_id in ids)
```

对未知字符，我们选择**直接报错**，而不是悄悄跳过。原因是：训练时出现未知字符，说明词表和语料不匹配，应该尽早暴露，而不是让模型在错误的 id 上学习。

工业界更常见的做法是：

- 加一个 `<unk>` token 表示未知
- 用 byte-level BPE，保证任何字节都能编码，从根上避免 OOV

---

## 4. 动手试一下

在 `llm/0-1llm` 目录下启动 Python：

```bash
python
```

```python
>>> from src.tokenizer import CharTokenizer
>>> tok = CharTokenizer.from_text("小禾与灯")
>>> tok.vocab
['与', '小', '灯', '禾']
>>> tok.encode("小禾灯")
[1, 3, 2]
>>> tok.decode([1, 3, 2])
'小禾灯'
```

再看真实语料：

```python
>>> from src.data import read_text
>>> text = read_text("data/tiny_corpus.txt")
>>> tok = CharTokenizer.from_text(text)
>>> len(text)
2216
>>> tok.vocab_size
326
>>> ids = tok.encode("从前有座山")
>>> ids
[...]
>>> tok.decode(ids)
'从前有座山'
```

结论：

- 语料有 **2216 个字符**
- 词表有 **326 个不同字符**
- 平均每个字符就是一个 token

这也意味着，`block_size=64` 时，模型一次最多看到 64 个汉字，大约两三个短句。

---

## 5. 保存和加载词表

词表是 checkpoint 的一部分。如果训练时用一套 id，推理时用另一套，生成的文本会完全错乱。

`CharTokenizer` 提供了 JSON 保存：

```python
tok.save("checkpoints/tokenizer.json")
tok2 = CharTokenizer.load("checkpoints/tokenizer.json")
assert tok2.vocab == tok.vocab
```

训练脚本会自动保存 `tokenizer.json`，同时把词表写进模型 checkpoint（见 [`src/train.py`](../src/train.py) 的 `save_checkpoint`）。生成脚本直接从 checkpoint 里恢复词表，不依赖外部文件。

---

## 6. 字符级分词的局限

1. **序列长**：一句 20 字的话就是 20 个 token；BPE 可能只要 8~12 个。
2. **词表利用率低**：很多汉字频率极低，但每个都占一个 embedding 行。
3. **语义单元太细**：模型要自己学会把「桂」「花」「树」组合成概念。
4. **多语言爆炸**：中英日韩混在一起，词表会迅速变大。

但对我们这个 12 万参数的小模型来说，这些都不是问题。**先理解机制，再优化工程。**

---

## 7. 本章练习

### 练习 1：加一个 `<unk>`

修改 `CharTokenizer`，让未知字符映射到 `<unk>`，而不是报错。思考：

- `<unk>` 应该放在词表的哪个位置？
- 解码时遇到 `<unk>` 应该输出什么？
- 训练语料里如果从来没有 `<unk>`，模型能学会它的 embedding 吗？

### 练习 2：统计字符频率

写一个函数，统计语料中每个字符出现的次数，按频率从高到低打印前 20 个。

问题：如果按频率重排词表，会改变 id 的数值，但**模型效果会变吗**？（提示：embedding 是可学习的，id 本身没有大小含义。）

### 练习 3：手写一个极简 BPE

给定文本 `"low lower lowest"`：

1. 把每个词拆成字符，并在词尾加 `</w>`
2. 统计相邻字符对的出现次数
3. 合并出现次数最多的一对，加入词表
4. 重复 3~5 次

观察词表如何从字符逐渐长成子词。这个练习会帮你理解 GPT-2 分词器在做什么。

### 练习 4：序列长度对比

用 `len(tok.encode(text))` 统计一段中文文本的 token 数。再估算一下：如果换成词表 5 万的 BPE，sequence length 大概会缩短多少倍？这对训练速度意味着什么？

---

## 8. 自检清单

- [ ] 我知道 token id 是什么，以及 `encode` / `decode` 的方向
- [ ] 我理解为什么词表要 `sorted` 保证确定性
- [ ] 我能解释字符级分词和 BPE 的取舍
- [ ] 我知道 OOV 是什么，以及字符级分词为什么基本没有 OOV
- [ ] 我跑过 `CharTokenizer` 的编码解码示例

下一章：把 id 变成训练样本。

[第 02 章：数据与 batch →](./02_data.md)