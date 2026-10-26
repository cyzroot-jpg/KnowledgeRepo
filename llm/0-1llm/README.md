# 🧠 从 0 构建一个 LLM（手把手课程）

> 用一套可以真正跑起来的最小代码，从「文本」一路走到「会生成文字的 GPT」。
> 不调用任何模型库，只依赖 PyTorch 的自动求导和基础张量运算。

---

## 你会做出什么

完成本课程后，你会亲手实现并训练出一个**字符级、decoder-only 的小型 GPT**：

- 自己写分词器，把中文文本变成 token id
- 自己构造「预测下一个 token」的数据集和 batch
- 先训练一个 Bigram 基线，确认整条链路是通的
- 从零实现缩放点积注意力、因果掩码、多头注意力
- 从零实现 LayerNorm、GELU、残差连接和 Transformer Block
- 写完整的训练循环：AdamW、warmup、余弦退火、梯度裁剪、验证集、checkpoint
- 实现 greedy、temperature、top-k、top-p 生成
- 用单元测试验证形状、因果性和生成逻辑

这个模型只有 **12.5 万参数**，在 CPU 上几分钟就能训练完。它不会变成 ChatGPT，但它和 GPT 系列在结构上是同一类东西：**用上下文预测下一个 token**。

---

## 适合谁

- 学过一点 Python，想真正弄懂 LLM 内部发生了什么
- 看过很多「Transformer 图解」，但没有从头写过一遍
- 想改模型、做实验，却不知道 nanoGPT 每一行在干什么
- 不要求 GPU；有 CPU 就能完成全部必修内容

前置知识：

- Python 基础（函数、类、列表）
- 会一点点 PyTorch 更好，但不会也可以跟着写
- 线性代数的直觉：矩阵乘法、向量点积
- 不需要微积分推导，反向传播交给 PyTorch

---

## 学习路线

| 章节 | 主题 | 你会得到 | 建议时间 |
| :---: | :--- | :--- | :---: |
| [00](./chapters/00_overview.md) | 全貌与环境 | 理解 LLM 的训练目标、跑通环境 | 30 分钟 |
| [01](./chapters/01_tokenizer.md) | 分词器 | `CharTokenizer`：文本 ⇄ id | 45 分钟 |
| [02](./chapters/02_data.md) | 数据与 batch | 下一 token 预测、滑窗数据集 | 45 分钟 |
| [03](./chapters/03_bigram.md) | Bigram 基线 | 第一条可训练的基线模型 | 45 分钟 |
| [04](./chapters/04_attention.md) | 注意力机制 | 因果多头自注意力 | 90 分钟 |
| [05](./chapters/05_transformer.md) | Transformer Block | 完整 GPT、参数统计 | 90 分钟 |
| [06](./chapters/06_training.md) | 训练 | 训练循环、学习率、checkpoint | 60 分钟 |
| [07](./chapters/07_generation.md) | 生成 | 采样策略、文本生成 | 45 分钟 |
| [08](./chapters/08_modern.md) | 现代改进 | RMSNorm、RoPE、SwiGLU、GQA… | 60 分钟 |
| [09](./chapters/09_next_steps.md) | 从玩具到真实 | 放大路线、下一步学习 | 30 分钟 |

> 建议顺序执行。每一章都有「运行命令 → 观察结果 → 改代码 → 练习」四步，不要只读不跑。

---

## 环境准备

要求：**Python 3.10+**、**PyTorch 2.0+**。

进入课程目录：

```bash
cd llm/0-1llm
```

### Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果 `import torch` 报 `WinError 126` 或找不到 `c10.dll`，说明系统缺少 **Microsoft Visual C++ Redistributable**，安装后再试：

<https://aka.ms/vs/17/release/vc_redist.x64.exe>

---

## 5 分钟快速验证

在 `llm/0-1llm` 目录下依次执行：

```bash
# 1. 查看一次前向传播里每个张量的形状，并手工复算注意力
python -m src.inspect_shapes

# 2. 跑单元测试
python -m unittest discover -s tests -v
```

正常情况下你会看到：

```text
q, k, v 形状        : (2, 4, 10, 8)  = [B, n_head, T, head_dim]
scores 形状         : (2, 4, 10, 10)  = [B, n_head, T, T]
注意力输出形状      : (2, 10, 32)  = [B, T, C]
手工结果和模型一致？ True
总参数量            : 28,032
```

以及 `Ran 9 tests ... OK`。

> Windows 终端如果中文乱码，先执行 `chcp 65001`，或设置 `set PYTHONIOENCODING=utf-8`。

---

## 完整跑一遍

```bash
# 1. 训练 Bigram 基线
python -m src.bigram --steps 500

# 2. 先验证训练循环：让模型记住同一个 batch
python -m src.train --overfit --max-steps 300

# 3. 正式训练迷你 GPT（建议先跑 600 步观察）
python -m src.train --max-steps 600

# 4. 用保存下来的最优 checkpoint 生成
python -m src.generate --prompt "小禾" --max-new-tokens 150 --temperature 0.8 --top-k 40
```

参考结果（CPU）：

```text
过拟合单 batch：loss 5.80 -> 0.21
正式训练：step 200 时验证损失约 3.77，之后开始过拟合
生成：小禾的光的石头，很安腰。她把灯放在桂花。...
```

生成质量不高是正常的：语料只有两千多字，模型只有 12 万参数。我们的目标是**把原理和工程链路跑通**，不是刷榜。

---

## 项目结构

```text
0-1llm/
├── README.md                 # 本文件
├── requirements.txt
├── data/
│   └── tiny_corpus.txt       # 课程自带的微型中文语料
├── chapters/                 # 00-09 章教程
├── src/
│   ├── config.py             # 模型/训练超参数
│   ├── utils.py              # 设备选择、随机种子
│   ├── tokenizer.py          # 字符级分词器
│   ├── data.py               # 数据集与 get_batch
│   ├── bigram.py             # 第 3 章基线
│   ├── model.py              # 注意力 / Block / GPT
│   ├── train.py              # 训练循环
│   ├── generate.py           # 采样与生成
│   └── inspect_shapes.py     # 形状追踪 + 注意力手算验证
└── tests/
    └── test_model.py         # 9 个单元测试
```

训练产生的 `checkpoints/`、虚拟环境 `.venv/` 和 `__pycache__/` 已在 `.gitignore` 中忽略。

---

## 课程约定

### 张量形状

| 记号 | 含义 | 例子 |
| :---: | :--- | :--- |
| `B` | batch size | 16 |
| `T` | 序列长度（上下文 token 数） | 64 |
| `C` | 隐藏维度 `n_embd` | 64 |
| `H` | 注意力头数 `n_head` | 2 |
| `Dh` | 每个头的维度 `C / H` | 32 |
| `V` | 词表大小 `vocab_size` | 326 |

最重要的三个形状：

```text
输入 id          [B, T]
主干 hidden      [B, T, C]
输出 logits      [B, T, V]
```

注意力内部会临时出现 `[B, H, T, T]` 的分数矩阵，这是 Transformer 计算量最大的地方。

### 代码原则

1. **先能跑，再抠细节。** 每章先运行，再读代码。
2. **打印形状。** 不确定时就把 `x.shape` 打出来，绝大多数 bug 都是形状或维度顺序错了。
3. **一次只改一个变量。** 改学习率、改层数、改 mask，观察损失和输出怎么变。
4. **不引入未使用的依赖。** 核心代码只依赖 PyTorch 标准功能。

---

## 配套材料

- 仓库里的 [`llm/mini_llm_step.py`](../mini_llm_step.py) 是一个**纯 NumPy、可单步执行**的前向演示，不训练，适合配合第 4、5 章逐行观察数据流。
- [`llm/0-1llm/0-1llm.md`](./0-1llm.md) 记录了计时与 `synchronize()` 的补充笔记。
- 第 08、09 章列出了从当前玩具代码升级到真实训练的路线。

---

## 常见问题

**Q：为什么不用 Hugging Face / nanoGPT？**
A：课程目标是从零理解。先自己写一遍 300 行的 GPT，再去看 nanoGPT 会非常轻松。

**Q：为什么用字符级分词，不用 BPE？**
A：字符级没有额外依赖，词表小，最容易看清「文本 → id → 向量」的全过程。BPE 是工程优化，第 08、09 章会讲怎么替换。

**Q：CPU 能跑吗？**
A：可以。默认配置就是为 CPU 设计的。GPU 会自动启用，速度更快。

**Q：损失降到多少才算成功？**
A：对这份小语料，验证损失降到 3~4 就已经在学东西了。继续训练训练损失会接近 0，但验证损失会上升，这是过拟合，第 06 章会专门讨论。

**Q：生成结果不通顺，是不是代码有 bug？**
A：不一定是。先跑 `python -m src.train --overfit --max-steps 300`，如果 loss 能降到接近 0，说明模型和训练循环是通的；生成质量取决于数据量、模型大小和训练步数。

---

## 学完之后

你会具备继续做这些事的基础：

- 把字符级分词换成 BPE / SentencePiece
- 把语料换成莎士比亚、TinyStories 或你自己的领域文本
- 实现 KV Cache，加速自回归生成
- 加入混合精度、梯度累积、分布式训练
- 阅读并改造 nanoGPT、llama.cpp 等真实项目

从 [第 00 章](./chapters/00_overview.md) 开始吧。