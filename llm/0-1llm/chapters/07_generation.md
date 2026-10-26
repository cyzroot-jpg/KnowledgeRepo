# 第 07 章：生成——把 logits 变成文字

> 本章目标：理解自回归生成循环，掌握 greedy、temperature、top-k、top-p 四种采样策略，并知道 KV Cache 为什么重要。

---

## 1. 自回归生成的基本循环

训练时我们一次性喂一整段文本；生成时没有「未来」可喂，只能一个一个来：

```text
提示词 "小禾"
  │
  ├─ 模型预测下一个 token -> 采样出 "的"
  ├─ 序列变成 "小禾的"
  ├─ 再预测下一个 -> "光"
  ├─ 序列变成 "小禾的光"
  └─ ... 重复 max_new_tokens 次
```

代码（[`src/generate.py`](../src/generate.py)）：

```python
for _ in range(max_new_tokens):
    idx_cond = idx[:, -model.config.block_size:]
    logits, _ = model(idx_cond)
    logits = logits[:, -1, :]        # 只关心最后一个位置
    next_id = sample(logits)
    idx = torch.cat([idx, next_id], dim=1)
```

三个关键点：

1. **只取最后一个位置的 logits**：前面位置的预测已经用不上了。
2. **裁剪到 `block_size`**：模型的位置编码和注意力 mask 只支持固定最大长度。
3. **把新 token 拼回去**：这是「自回归」的含义。

---

## 2. 从 logits 到 token：softmax + 采样

模型输出的是分数，不是概率：

```text
logits = [2.1, 0.3, -1.2, ...]
```

先除以温度，再 softmax：

```python
probs = F.softmax(logits / temperature, dim=-1)
```

然后按概率采样：

```python
next_id = torch.multinomial(probs, num_samples=1)
```

`multinomial` 会按照概率随机抽一个。概率高的 token 更常被选中，但低概率 token 也有机会。

---

## 3. Greedy：永远选最大

```python
next_id = torch.argmax(logits, dim=-1, keepdim=True)
```

优点：

- 完全确定，方便复现
- 适合评估、调试

缺点：

- 容易陷入重复循环
- 生成缺乏多样性

用 greedy 跑我们训练好的模型：

```bash
python -m src.generate --prompt "小禾" --max-new-tokens 40 --greedy
```

可能得到：

```text
小禾说：“原来，你？”
小狐狸看着小狐狸。”
小狐狸看着小狐狸。
小狐狸。
小狐狸看
```

模型发现「小狐狸」后面接「看着小狐狸」能降低损失，于是一直重复。这就是 greedy 的典型退化。

---

## 4. Temperature：控制随机性

```python
logits = logits / temperature
```

| 温度 | 效果 | 适用场景 |
| :---: | :--- | :--- |
| `T < 1` | 分布更尖锐，更保守 | 事实问答、代码 |
| `T = 1` | 原始分布 | 通用 |
| `T > 1` | 分布更平坦，更随机 | 创意写作 |
| `T → 0` | 接近 greedy | 确定性输出 |

注意：温度不能为 0（会除零）。要确定性输出请用 `--greedy`。

---

## 5. Top-k：只保留前 k 个候选

```python
kth_value = torch.topk(logits, k, dim=-1).values[..., -1, None]
logits = logits.masked_fill(logits < kth_value, float("-inf"))
```

例如 `k=40`：只在前 40 个最可能的 token 里采样，把长尾全部砍掉。

好处：

- 避免采到极其离谱的低概率 token
- 计算量可控

坏处：

- `k` 是固定的：分布很尖时浪费候选，分布很平时又限制太狠

---

## 6. Top-p（核采样）：动态候选集

Top-p 不固定候选数量，而是固定**累计概率**：

1. 按概率从高到低排序
2. 累加概率，直到超过 `p`
3. 只在这个最小集合里采样

例如 `p=0.9`：

```text
token A: 0.50  累计 0.50  <- 保留
token B: 0.25  累计 0.75  <- 保留
token C: 0.10  累计 0.85  <- 保留
token D: 0.05  累计 0.90  <- 保留（刚好跨过阈值）
token E: 0.03  累计 0.93  <- 丢弃
...
```

实现：

```python
sorted_logits, sorted_indices = torch.sort(logits, descending=True, dim=-1)
sorted_probs = F.softmax(sorted_logits, dim=-1)
cumulative = torch.cumsum(sorted_probs, dim=-1)

remove = (cumulative - sorted_probs) > p
sorted_logits = sorted_logits.masked_fill(remove, float("-inf"))

filtered = torch.full_like(logits, float("-inf"))
filtered.scatter(1, sorted_indices, sorted_logits)
```

`cumulative - sorted_probs` 是「当前 token 之前的累计概率」：

- 如果它已经超过 `p`，当前 token 及其后面的都可以丢掉
- 第一个跨过 `p` 的 token 会被保留

Top-p 的自适应特性让它比 top-k 更常用。常见组合：

```text
temperature = 0.8
top_k = 40
top_p = 0.9
```

本课程的 CLI 默认只用 `top_k=40`；你可以传 `--top-p 0.9` 叠加使用，或把 `--top-k 0` 设为关闭 top-k、只使用 top-p。

---

## 7. 运行生成

先确保已经训练过：

```bash
python -m src.train --max-steps 600
```

然后：

```bash
python -m src.generate \
  --prompt "小禾" \
  --max-new-tokens 150 \
  --temperature 0.8 \
  --top-k 40
```

参考输出（你的结果会因随机种子略有不同）：

```text
小禾的光的石头，很安腰。她把灯放在桂花。
小禾说：团睛里，每天来。
小禾儿，你？”
小禾的时候是从山灯放在。
...
```

再试试：

```bash
# 更保守
python -m src.generate --prompt "小禾" --temperature 0.3 --top-k 20

# 更随机
python -m src.generate --prompt "小禾" --temperature 1.2 --top-k 100

# 只用 top-p
python -m src.generate --prompt "小禾" --top-k 0 --top-p 0.9
```

### 为什么生成质量一般？

- 语料只有 2216 个字符
- 模型只有 2 层、64 维
- 训练 200 步后就开始过拟合

模型学会了局部搭配（「小禾说」「小狐狸」「桂花树」），但没有足够数据学会长程逻辑。**这是数据规模问题，不是生成代码问题。**

---

## 8. 一次生成到底算了多少？

没有 KV Cache 时，每生成一个 token，都要把整个前缀重新过一遍模型：

```text
生成第 1 个：处理 T 个 token
生成第 2 个：处理 T+1 个 token
生成第 3 个：处理 T+2 个 token
...
```

总计算量约 `O(T³)`（每步注意力 `O(T²)`）。序列越长越慢。

### KV Cache 的思路

在 Transformer 里，已经处理过的 token 的 K、V 不会改变。所以可以缓存：

```python
K_cache[layer]: [B, H, T_past, Dh]
V_cache[layer]: [B, H, T_past, Dh]
```

生成新 token 时：

1. 只计算新 token 的 Q、K、V
2. 把新的 K、V 追加到缓存
3. 用新 Q 和完整 K/V 算注意力
4. 只输出一个位置的 logits

这样每步只处理 1 个新 token，总计算量从 `O(T³)` 降到 `O(T²)`。代价是显存：缓存大小随层数、头数、序列长度线性增长。

真实推理引擎（vLLM、llama.cpp）大量工程都在优化 KV Cache 的布局、分页和共享。第 08、09 章会继续提到。

---

## 9. 本章练习

### 练习 1：实现 repetition penalty

在采样前，对已经出现过的 token 降低 logits：

```python
for token_id in set(idx[0].tolist()):
    logits[0, token_id] /= penalty
```

`penalty > 1` 会抑制重复。观察 greedy 的循环是否被打破。

### 练习 2：只用 top-p

修改 CLI，让 `--top-k 0` 表示关闭 top-k，只使用 top-p。对比 `p=0.9` 和 `p=0.95` 的生成差异。

### 练习 3：实现 KV Cache

这是本章最有价值的挑战。提示：

- 给 `CausalSelfAttention.forward` 增加 `kv_cache` 参数
- 输入只有新 token 时，缓存的 K/V 拼在前面
- 注意因果 mask 要允许新 token 看到所有历史
- 先用 `T=1` 的增量生成验证输出和完整前向一致，再优化

### 练习 4：比较采样策略

固定同一个 prompt 和 seed，分别用：

- greedy
- `temperature=0.8, top_k=40`
- `temperature=1.0, top_p=0.9`
- `temperature=0.5, top_k=10`

生成 5 次，记录重复率、通顺度和多样性。写一段你的观察。

---

## 10. 自检清单

- [ ] 我能写出自回归生成的三步循环
- [ ] 我知道 temperature 如何改变分布
- [ ] 我能解释 top-k 和 top-p 的区别
- [ ] 我知道 greedy 为什么容易重复
- [ ] 我理解 KV Cache 省了什么、多占用了什么
- [ ] 我能独立运行 `python -m src.generate`

下一章：看看真实大模型还用了哪些现代改进。

[第 08 章：现代改进 →](./08_modern.md)