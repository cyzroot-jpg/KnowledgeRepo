# 第 09 章：从玩具到真实——下一步怎么走

> 本章目标：清楚知道当前代码的边界，拿到一条可执行的放大路线，并知道接下来该学什么、做什么项目。

---

## 1. 你已经拥有了什么

先诚实盘点。你现在有一个：

- 字符级 tokenizer
- 滑动窗口数据集
- Bigram 基线
- 因果多头自注意力
- Pre-Norm Transformer Block
- 完整 GPT
- 可运行的训练循环
- greedy / temperature / top-k / top-p 生成
- 9 个单元测试
- checkpoint 保存与恢复

这已经覆盖了 LLM 的**核心原理**。剩下的是工程规模和数据问题。

---

## 2. 当前代码的边界

| 限制 | 现状 | 影响 | 对应章节 |
| :--- | :--- | :--- | :--- |
| 分词 | 字符级 | 序列长、词表利用率低 | 01 / 08 |
| 数据 | 2216 字 | 严重过拟合 | 02 / 06 |
| 模型 | 2 层 / 64 维 / 125K 参数 | 只能学局部模式 | 05 |
| 位置编码 | 可学习绝对位置 | 不能外推长上下文 | 05 / 08 |
| 注意力 | 手写 MHA | 长序列慢、占显存 | 04 / 08 |
| 生成 | 无 KV Cache | 每步重算前缀 | 07 |
| 精度 | fp32 | 慢、占显存 | 08 |
| 并行 | 单进程 | 无法多卡 | 08 |
| 对齐 | 无 SFT / RLHF | 不会听指令 | 09 |
| 评估 | 只有验证损失 | 不知道真实能力 | 09 |

这些不是「缺陷」，而是**课程刻意保留的最小实现**。每一条都是下一步的入口。

---

## 3. 第一件事：换数据

模型不变，只换语料：

```bash
python -m src.train --data /path/to/your_corpus.txt --max-steps 2000
```

建议：

- 用 UTF-8 纯文本
- 至少几十万字符起步
- 先清洗：去重、去广告、去乱码、统一标点
- 训练集/验证集按**文档**切分，不要按字符切分（避免同一篇文章同时出现在两边）

可以尝试的公开数据：

- **TinyStories**：简单英文短故事，适合小模型
- **莎士比亚全集**：经典字符级基准
- **维基百科中文**：规模大，需要清洗
- **你自己的领域文档**：笔记、代码、小说、客服记录

> 注意数据许可。公开数据集也有各自的使用条款，商用前要确认。

换数据后，词表会自动重建。旧 checkpoint 不能继续用，因为 id 映射变了。

---

## 4. 第二件事：换 BPE 分词

字符级分词在中文里还行，但在英文/代码上序列会非常长。工业标准是 BPE。

推荐用 Hugging Face `tokenizers` 训练一个 BPE：

```python
from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import ByteLevel

tokenizer = Tokenizer(BPE(unk_token="<unk>"))
tokenizer.pre_tokenizer = ByteLevel()

trainer = BpeTrainer(
    vocab_size=8000,
    special_tokens=["<unk>", "<s>", "</s>"],
)
tokenizer.train(files=["data/corpus.txt"], trainer=trainer)
tokenizer.save("tokenizer.json")
```

然后写一个适配层，保持和 `CharTokenizer` 相同的接口：

```python
class BPETokenizer:
    @property
    def vocab_size(self): ...
    def encode(self, text) -> list[int]: ...
    def decode(self, ids) -> str: ...
    def save(self, path): ...
    @classmethod
    def load(cls, path): ...
```

这样 `train.py` 和 `generate.py` 几乎不用改。注意 checkpoint 里要保存 BPE 的完整配置，而不只是词表列表。

---

## 5. 第三件事：放大模型

先估算参数量：

```text
参数 ≈ 12 · n_layer · C² + V · C + T · C
```

参考规模（非常粗略）：

| 规模 | 参数量 | 数据量 | 硬件 | 能做什么 |
| :--- | ---: | ---: | :--- | :--- |
| 玩具 | 0.1M | 2K token | CPU | 学原理 |
| 小 | 10M | 10M token | 单卡 GPU | 简单故事/诗歌 |
| 中 | 100M | 1B token | 多卡 | 领域助手雏形 |
| 大 | 1B | 20B token | 多卡集群 | 通用对话 |
| 超大 | 7B+ | 1T+ token | 大规模集群 | 接近产品级 |

放大时优先顺序通常是：

1. **数据量和质量**（收益最大）
2. **模型宽度/深度**（受显存限制）
3. **训练步数**（受计算预算限制）

不要一上来就堆 7B。先用 10M 模型把数据管线、评估、部署跑通。

修改配置的位置：

- [`src/config.py`](../src/config.py) 的 `MODEL_PRESETS`
- [`src/train.py`](../src/train.py) 的 `TrainConfig`

例如加一个 `medium` 预设：

```python
"medium": {
    "block_size": 256,
    "n_layer": 6,
    "n_head": 8,
    "n_embd": 384,
    "dropout": 0.1,
},
```

---

## 6. 第四件事：训练工程

当模型变大，单卡跑不动时，按顺序加：

### 6.1 混合精度

```python
with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
    logits, loss = model(x, y)
```

### 6.2 梯度累积

```python
loss = loss / accum_steps
loss.backward()
if (step + 1) % accum_steps == 0:
    optimizer.step()
    optimizer.zero_grad()
```

### 6.3 梯度检查点

用计算换显存：

```python
from torch.utils.checkpoint import checkpoint
x = checkpoint(block, x, use_reentrant=False)
```

### 6.4 DDP / FSDP

多卡数据并行，或者参数分片。先用单机多卡 DDP，再考虑 FSDP/ZeRO。

### 6.5 日志与恢复

需要记录：

- 训练/验证损失
- 学习率
- 梯度范数
- 吞吐（token/s）
- 显存占用
- 样本生成

并支持从 checkpoint 恢复：

```python
torch.save({
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),
    "step": step,
    "config": config,
    "vocab": tokenizer.vocab,
}, path)
```

本课程的 `save_checkpoint` 只保存了模型，没有保存 optimizer。真正长跑训练必须补上，否则恢复后动量状态丢失。

---

## 7. 第五件事：评估

只看验证损失是不够的。至少需要三层评估：

### 7.1 语言建模指标

- 验证交叉熵
- 困惑度（perplexity）
- 不同领域/长度上的分层损失

### 7.2 生成质量

- 人工看 20~50 条样本
- 重复率、长度分布、停转率
- 与基线模型对比

### 7.3 下游任务

- 问答准确率
- 代码通过率
- 分类/抽取 F1
- 指令遵循率

真实项目里，**评估集的设计往往比模型结构更重要**。先想清楚「什么叫好」，再开始训练。

---

## 8. 第六件事：指令微调（SFT）

本课程训练的是**基座模型**：它只会续写，不会听指令。

SFT（Supervised Fine-Tuning）用「指令 → 回答」数据继续训练：

```text
<user> 用一句话解释什么是注意力机制。
<assistant> 注意力机制让每个 token 根据相关性从上下文中读取信息。
```

关键细节：

1. **只对回答部分计算损失**，prompt 部分 mask 掉
2. 使用统一的 chat template
3. 数据质量远比数量重要
4. 需要单独的 SFT 评估集

```python
loss = F.cross_entropy(
    logits[:, :-1].reshape(-1, V),
    labels[:, 1:].reshape(-1),
    ignore_index=-100,   # prompt 部分设为 -100
)
```

再往后还有偏好优化（DPO、PPO/RLHF）、拒绝采样、蒸馏等。先把 SFT 做扎实。

---

## 9. 第七件事：推理与部署

训练完只是开始。上线要考虑：

- **KV Cache**：必须实现，否则长文本生成极慢
- **批处理**：同时服务多个请求
- **量化**：int8/int4 降低显存
- **分页 KV Cache**：vLLM 的 PagedAttention
- **流式输出**：边生成边返回
- **超时/限流/监控**

学习路径：

1. 先在本课程代码里实现简单 KV Cache
2. 用 `torch.compile` 或 SDPA 优化
3. 再研究 vLLM / llama.cpp 的架构
4. 最后考虑量化与多卡部署

---

## 10. 一个 4 周行动计划

### 第 1 周：打牢原理

- 完成第 00~04 章
- 能独立解释 Q/K/V、因果掩码、多头
- 手算一个 4×4 注意力矩阵

### 第 2 周：完整训练

- 完成第 05~07 章
- 跑通 overfit 测试
- 训练 2000 步，保存并生成
- 写出你对损失曲线的观察

### 第 3 周：升级一次

从下面选一个：

- 换 BPE
- 换更大语料
- 加 KV Cache
- 换 RMSNorm + SwiGLU + SDPA

要求：用测试和损失曲线证明改动有效或无效。

### 第 4 周：做一个小项目

- 选一个领域语料（诗歌、代码、客服）
- 训练 10M 级模型
- 设计评估集
- 写一份实验报告：数据、配置、损失、样本、失败案例

---

## 11. 项目想法

1. **中文古诗生成器**：收集唐宋诗，字符级或 BPE，观察平仄和押韵
2. **代码补全模型**：用开源代码训练，评估补全通过率
3. **领域问答助手**：SFT + RAG，做一个能回答你笔记问题的机器人
4. **注意力可视化工具**：把每层每个头的注意力画成热力图
5. **KV Cache 性能实验**：对比有无缓存、不同序列长度下的 token/s
6. **小型推理引擎**：实现 batching + KV Cache + 流式输出

每个项目都能把课程里的某一块真正吃透。

---

## 12. 推荐阅读

**入门与直觉**

- Jay Alammar, *The Illustrated Transformer*
- Andrej Karpathy, *Let's build GPT: from scratch, in code, spelled out*（视频）
- Andrej Karpathy, [nanoGPT](https://github.com/karpathy/nanoGPT)

**论文**

- *Attention Is All You Need* — <https://arxiv.org/abs/1706.03762>
- *Language Models are Unsupervised Multitask Learners*（GPT-2）
- *Language Models are Few-Shot Learners*（GPT-3）— <https://arxiv.org/abs/2005.14165>
- *Training Compute-Optimal Large Language Models*（Chinchilla）— <https://arxiv.org/abs/2203.15556>
- *FlashAttention* — <https://arxiv.org/abs/2205.14135>
- *RoFormer: Enhanced Transformer with Rotary Position Embedding* — <https://arxiv.org/abs/2104.09864>
- *GQA: Training Generalized Multi-Query Transformer Models* — <https://arxiv.org/abs/2305.13245>
- *Root Mean Square Layer Normalization* — <https://arxiv.org/abs/1910.07467>
- *GLU Variants Improve Transformer*（SwiGLU）— <https://arxiv.org/abs/2002.05202>
- *Llama 2: Open Foundation and Fine-Tuned Chat Models* — <https://arxiv.org/abs/2307.09288>
- *TinyStories: How Small Can Language Models Be and Still Speak Coherent English?* — <https://arxiv.org/abs/2305.07759>

**工程**

- [vLLM](https://github.com/vllm-project/vllm)：高吞吐推理引擎
- [llama.cpp](https://github.com/ggerganov/llama.cpp)：本地推理与量化
- [Megatron-LM](https://github.com/NVIDIA/Megatron-LM)：大规模训练
- [Hugging Face Transformers](https://github.com/huggingface/transformers)：工业级实现参考

---

## 13. 最后的自检

如果你能不看代码回答下面这些问题，说明你已经真正入门：

- [ ] 为什么语言模型可以并行训练、却必须串行生成？
- [ ] 注意力里为什么要除以 `√d_k`？
- [ ] 因果掩码为什么在 softmax 之前加？
- [ ] Pre-Norm 相比 Post-Norm 解决了什么问题？
- [ ] 权重绑定省了多少参数？
- [ ] 为什么验证损失会先降后升？
- [ ] top-k 和 top-p 的本质区别是什么？
- [ ] KV Cache 缓存了什么？为什么能加速？
- [ ] GQA 为什么能缩小 KV Cache？
- [ ] 从 125K 参数放大到 7B，哪些东西会变，哪些不会变？

---

## 结语

你不是「调用了一个 LLM」，你是**亲手实现并训练了一个**。

它很小，生成结果也不完美。但你已经走过了完整链路：

```text
文本 → token → embedding → attention → transformer → logits
     → loss → backward → 参数更新 → 采样 → 文本
```

剩下的事情，主要是把这条链路：

- 换成更好的分词
- 喂更多、更干净的数据
- 放大模型和算力
- 加工程优化和评估
- 做指令对齐和部署

**原理已经在你手里了。** 接下来就是选一个方向，继续做下去。

祝你好运。

---

[返回课程首页](../README.md)