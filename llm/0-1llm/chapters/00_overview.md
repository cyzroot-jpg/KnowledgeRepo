# 第 00 章：全貌与环境

> 本章目标：知道我们要造什么、它在数学上做什么、代码放在哪里，并把环境跑通。

---

## 1. 一句话理解 LLM

语言模型做的事情只有一件：

> 给定前面的 token，预测下一个 token 的概率分布。

用数学写出来：

```text
p(x_1, x_2, ..., x_T) = ∏ p(x_t | x_1, ..., x_{t-1})
```

训练时，我们把一整段文本同时喂进去，让每个位置都预测它的下一个字符：

```text
输入:  从 前 有 座 山
目标:  前 有 座 山 ，
```

模型输出每个位置上的「下一个 token 分数」，再和真实的下一个 token 算交叉熵。损失变小，模型就学到了文本里的统计规律。

GPT、Llama、Qwen 这些模型，主体都是这个目标，只是：

- 分词从字符换成 BPE
- 层数、宽度、数据量放大几个数量级
- 加入了更多工程优化

所以，**把最小的版本完整写一遍，是理解大模型最有效的路径**。

---

## 2. 我们要走的完整链路

```text
原始文本
   │
   ▼
[1] 分词器 encode            "小禾" -> [12, 87]
   │
   ▼
[2] 数据集切窗口             x = [12, 87, ...], y = [87, ...]
   │
   ▼
[3] Embedding 查表           id -> 向量 [B, T, C]
   │
   ▼
[4] N 层 Transformer         Attention + MLP + 残差 + LayerNorm
   │
   ▼
[5] LM Head                  hidden -> 词表分数 [B, T, V]
   │
   ▼
[6] 交叉熵损失               和真实下一个 token 比较
   │
   ▼
[7] 反向传播 + AdamW         更新参数
   │
   ▼
[8] 自回归生成               一次一个 token，拼回输入
```

对应到代码：

| 步骤 | 文件 | 关键函数/类 |
| :--- | :--- | :--- |
| 分词 | [`src/tokenizer.py`](../src/tokenizer.py) | `CharTokenizer` |
| 数据 | [`src/data.py`](../src/data.py) | `TokenDataset`, `get_batch` |
| 模型 | [`src/model.py`](../src/model.py) | `CausalSelfAttention`, `Block`, `GPT` |
| 训练 | [`src/train.py`](../src/train.py) | `run_training`, `estimate_loss` |
| 生成 | [`src/generate.py`](../src/generate.py) | `generate`, `top_k_filter` |
| 基线 | [`src/bigram.py`](../src/bigram.py) | `BigramLM` |

---

## 3. 先看清三个形状

整个课程里，最重要的三个张量是：

```text
输入 id       [B, T]
主干 hidden   [B, T, C]
输出 logits   [B, T, V]
```

默认配置：

```text
B = 16        batch size
T = 64        上下文长度
C = 64        隐藏维度
H = 2         注意力头数
Dh = 32       每个头的维度
V = 326       字符词表大小
```

为什么主干一直是 `[B, T, C]`？

因为每个 token 在每一层都有一个 `C` 维向量表示。Attention 和 MLP 都只是「读这个向量、算一个新向量、加回去」，不改变形状。这种设计叫 **residual stream（残差流）**，是 Transformer 能堆很深的关键。

---

## 4. 环境准备

在仓库根目录执行：

```bash
cd llm/0-1llm
```

创建虚拟环境并安装 PyTorch：

```bat
:: Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

确认安装成功：

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

输出类似：

```text
2.14.1+cpu False
```

`False` 表示没有可用 GPU，不影响课程。

> **Windows 常见问题**：如果报 `OSError: [WinError 126] ... c10.dll`，安装 Microsoft Visual C++ Redistributable：
> <https://aka.ms/vs/17/release/vc_redist.x64.exe>
>
> 中文乱码时先执行 `chcp 65001`。

---

## 5. 第一次运行：观察形状

```bash
python -m src.inspect_shapes
```

这个脚本会：

1. 造一个随机的小 GPT
2. 打印一次前向传播中每个张量的形状
3. 用最原始的矩阵乘法**手工复算第一层注意力**
4. 把手工结果和模型实现对比
5. 统计参数量

核心输出：

```text
输入 idx            : (2, 10)  = [B, T]
token embedding     : (2, 10, 32)
位置 embedding      : (10, 32)
注意力权重（每层）  : (2, 4, 10, 10)  = [B, n_head, T, T]
输出 logits         : (2, 10, 64)  = [B, T, vocab_size]
...
手工结果和模型一致？ True
总参数量            : 28,032
```

如果 `手工结果和模型一致？` 是 `True`，说明注意力实现和教科书公式一致。这个脚本也是你以后调试模型时的模板。

---

## 6. 跑测试

```bash
python -m unittest discover -s tests -v
```

你应该看到 9 个测试全部通过：

```text
Ran 9 tests in 0.049s

OK
```

这些测试覆盖：

- 分词器编码/解码、未知字符、保存加载
- GPT 前向形状、损失可反传
- 注意力是否真的因果（不能看未来）
- 序列长度超过 `block_size` 时是否报错
- 生成长度、前缀保留、上下文裁剪

**先让测试全绿，再开始改代码。** 这是后面所有实验的安全网。

---

## 7. 训练循环的心智模型

训练一个 step 只做四件事：

```python
optimizer.zero_grad()        # 1. 清空上一步梯度
logits, loss = model(x, y)   # 2. 前向：算预测和损失
loss.backward()              # 3. 反向：算每个参数的梯度
optimizer.step()             # 4. 更新参数
```

你会在第 06 章看到它的完整版本，包括：

- 学习率 warmup + 余弦退火
- 梯度裁剪
- 训练/验证损失评估
- 保存最优 checkpoint

现在只需要记住：**LLM 训练没有魔法，就是这四步重复很多次。**

---

## 8. 本章练习

1. 打开 [`src/inspect_shapes.py`](../src/inspect_shapes.py)，把 `n_layer` 从 2 改成 3，猜一猜：
   - 注意力权重的列表长度会变成多少？
   - 参数量会增加多少？
   运行验证你的猜测。

2. 把 `n_head` 从 4 改成 8，`n_embd` 保持 32：
   - `head_dim` 变成多少？
   - 注意力的计算量会变吗？参数量会变吗？

3. 把 `block_size` 改成 20，输入长度改成 25，观察报错信息。

4. 用自己的话解释：为什么输入是 `[B, T]`，模型却能输出 `[B, T, V]`？每个位置在预测什么？

---

## 9. 自检清单

- [ ] 我能用一句话说出 LLM 的训练目标
- [ ] 我知道 `B/T/C/V` 分别代表什么
- [ ] 我跑通了 `inspect_shapes`
- [ ] 9 个单元测试全部通过
- [ ] 我知道一次训练 step 的四个基本动作

下一章：把文本变成数字。

[第 01 章：分词器 →](./01_tokenizer.md)