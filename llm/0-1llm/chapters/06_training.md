# 第 06 章：训练——让损失真正下降

> 本章目标：理解训练循环的每个组件，先过拟合一个 batch 验证代码正确，再正式训练并学会阅读损失曲线。

---

## 1. 损失函数：交叉熵

模型在每个位置输出 `V` 个 logits。经过 softmax 得到概率，再和真实的下一个 token 算交叉熵：

```text
loss = -log( p(正确 token) )
```

如果模型给正确 token 的概率是：

| p(正确) | loss |
| :---: | :---: |
| 1.0 | 0 |
| 0.5 | 0.69 |
| 0.1 | 2.30 |
| 1/V | ln(V) |

代码：

```python
loss = F.cross_entropy(
    logits.reshape(-1, logits.size(-1)),  # [B*T, V]
    targets.reshape(-1),                  # [B*T]
)
```

PyTorch 会自动做 log_softmax + 负对数似然，不需要你先手动 softmax。

### 困惑度（Perplexity）

```text
ppl = exp(loss)
```

可以粗略理解为「模型在多少个 token 之间犹豫」。`ppl = 43` 大致相当于在 43 个候选里猜。它是交叉熵的单调变换，排序完全一致。

---

## 2. 训练循环的四个动作

```python
optimizer.zero_grad(set_to_none=True)   # 1. 清空上一步梯度
logits, loss = model(x, y)              # 2. 前向：算预测和损失
loss.backward()                         # 3. 反向：算梯度
optimizer.step()                        # 4. 更新参数
```

完整的 [`src/train.py`](../src/train.py) 还多了：

- 学习率调度
- 梯度裁剪
- 训练/验证评估
- 保存最优 checkpoint

---

## 3. 优化器：AdamW 和参数分组

```python
optimizer = torch.optim.AdamW(
    groups,
    lr=cfg.learning_rate,
    betas=(0.9, 0.95),
)
```

### 为什么要分组？

不是所有参数都适合做 weight decay：

- 矩阵权重（`Linear`、`Embedding`）：适合 decay，抑制过大权重
- bias、LayerNorm 的 `γ/β`：通常不做 decay

```python
for param in model.parameters():
    if param.dim() >= 2:
        decay.append(param)
    else:
        no_decay.append(param)
```

### AdamW vs Adam

Adam 把 weight decay 混进梯度里；AdamW 把 decay 单独拿出来，按 `param -= lr * wd * param` 更新。现代 Transformer 训练基本都用 AdamW。

`betas=(0.9, 0.95)` 是 GPT 系列的常见设置。第二个 beta 比默认 0.999 小，对梯度变化的响应更快。

---

## 4. 学习率：Warmup + 余弦退火

Transformer 对学习率很敏感。一开始参数随机，梯度方向不稳定；先用小学习率「热身」，再逐渐升高，最后慢慢降下来。

```python
def get_lr(step, cfg):
    if step < cfg.warmup_steps:
        return cfg.learning_rate * (step + 1) / cfg.warmup_steps
    if step >= cfg.max_steps:
        return cfg.min_lr
    progress = (step - cfg.warmup_steps) / (cfg.max_steps - cfg.warmup_steps)
    coeff = 0.5 * (1.0 + math.cos(math.pi * progress))
    return cfg.min_lr + coeff * (cfg.learning_rate - cfg.min_lr)
```

默认：

```text
learning_rate = 1e-3
min_lr        = 1e-4
warmup_steps  = 100
max_steps     = 2000
```

曲线形状：

```text
lr
1e-3 |        ________
     |      /          \
     |    /              \___
1e-4 |  /                    \___
     +------------------------------> step
       100                    2000
```

每个 step 把当前 lr 写入 optimizer：

```python
for group in optimizer.param_groups:
    group["lr"] = lr
```

---

## 5. 梯度裁剪

偶尔会出现一个特别大的梯度，把参数一下子推飞。裁剪把梯度范数限制在阈值内：

```python
torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
```

默认 `grad_clip = 1.0`。它不改变梯度方向，只缩小长度。

---

## 6. 评估：训练集和验证集

```python
@torch.no_grad()
def estimate_loss(...):
    model.eval()
    ...
    model.train()
```

两个细节：

1. `model.eval()`：关闭 dropout，使用推理行为。
2. `torch.no_grad()`：不建计算图，省内存、更快。

每个评估点随机抽 `eval_iters=50` 个 batch，取平均。随机采样会带来噪声，50 次平均后已经足够稳定。

---

## 7. 先过拟合一个 batch

这是最重要的调试步骤。**如果模型连一个固定 batch 都记不住，后面所有训练都没有意义。**

```bash
python -m src.train --overfit --max-steps 300
```

参考输出：

```text
过拟合单个 batch：损失应该一路下降到接近 0。
step    1/300 | lr 2.00e-05 | loss 5.8030
step   40/300 | lr 4.10e-04 | loss 4.9950
step  100/300 | lr 1.00e-03 | loss 3.1096
step  200/300 | lr 5.50e-04 | loss 0.6729
step  300/300 | lr 1.00e-04 | loss 0.2139
```

损失从 5.80 降到 0.21，说明：

- 数据构造正确
- 模型前向正确
- 损失和反向传播正确
- 优化器在工作

此时生成结果基本是在复读训练样本，这正是「过拟合」的定义。

---

## 8. 正式训练

建议先跑 600 步，观察曲线：

```bash
python -m src.train --max-steps 600
```

参考输出：

```text
设备: cpu | 预设: tiny | 词表: 326 | block_size: 64
层数: 2 | 头数: 2 | d_model: 64 | 参数量: 125,056
step   200 | train 2.4608 | val 3.7745 | ppl 43.58
  -> 保存最优 checkpoint（val 3.7745）
step   400 | train 1.2771 | val 4.2190 | ppl 67.97
step   600 | train 0.9080 | val 4.3493 | ppl 77.42
训练结束，最优验证损失 3.7745
```

观察到了什么？

- **训练损失持续下降**：模型在记住训练集
- **验证损失先降后升**：从第 200 步左右开始过拟合
- **checkpoint 保存的是验证损失最低的那一步**，而不是最后一步

继续跑到 2000 步会更明显：

```text
step  200 | train 2.4424 | val 3.7715
step 1000 | train 0.1214 | val 5.6691
step 2000 | train 0.0605 | val 6.1945
```

训练损失接近 0，验证损失却越来越高。这不是代码 bug，而是**数据太少、模型相对太大**。

### 这份语料上的正确预期

| 指标 | 合理范围 | 说明 |
| :--- | :---: | :--- |
| 训练损失 | 0.1 ~ 3.8 | 能降到很低 |
| 验证损失 | 3.5 ~ 4.5 | 第 200 步左右最好 |
| 困惑度 | 30 ~ 90 | 对应验证损失 |
| 生成文本 | 局部通顺、整体混乱 | 语料只有 2216 字 |

---

## 9. Checkpoint 里有什么？

```python
torch.save({
    "model": model.state_dict(),
    "config": asdict(config),
    "vocab": tokenizer.vocab,
    "step": step,
    "val_loss": val_loss,
}, path)
```

保存了四样东西：

1. 模型参数
2. 模型结构超参数（重建网络用）
3. 词表（把 id 变回文字）
4. 训练进度和验证损失

所以生成脚本只需要一个 `ckpt.pt`，不需要你再手动指定层数、宽度或词表。

---

## 10. 调试清单

训练不顺利时，按顺序排查：

### 损失不动，停在 ln(V) 附近

- 学习率是不是太小？先用 `--overfit` 排除数据和模型问题
- 损失是不是没连到参数？检查 `loss.backward()` 后梯度是否为 `None`
- 数据 `x` 和 `y` 是不是完全一样？检查 `TokenDataset`

### 损失变成 NaN

- 学习率太大
- softmax 前有 `+inf` / `NaN`
- 掩码写反，导致某一行全是 `-inf`，softmax 分母为 0
- 梯度爆炸（加梯度裁剪）

### 训练损失下降，验证损失上升

- 数据太少
- 模型太大
- 训练太久
- 解决：更多数据、dropout、weight decay、early stopping

### 生成结果是乱码

- 先确认 checkpoint 和词表是否匹配
- 再跑 `--overfit`，确认模型能记住东西
- 如果 overfit 正常，那只是模型能力/数据量的问题

### 训练太慢

- 减小 `block_size`
- 减小 `batch_size`
- 减小 `n_layer` / `n_embd`
- 用 GPU（`--device cuda`）

---

## 11. 本章练习

### 练习 1：观察学习率

在 `run_training` 里每 10 步打印一次 lr，画出前 200 步的曲线。确认 warmup 和退火符合预期。

### 练习 2：关闭 warmup

把 `warmup_steps` 改成 1，训练 300 步。损失是否更早震荡或发散？

### 练习 3：对比 weight decay

分别用 `weight_decay=0.0` 和 `0.1` 训练 600 步，比较验证损失。小语料上哪个更好？

### 练习 4：实现 early stopping

当验证损失连续 `N` 次没有改善时自动停止训练。提示：在 `run_training` 里维护 `best_val` 和 `patience`。

### 练习 5：保存每个评估点的 checkpoint

把最优 checkpoint 改成按 step 命名，例如 `ckpt_step200.pt`。比较不同 step 的生成效果。

---

## 12. 自检清单

- [ ] 我能写出训练循环的四个动作
- [ ] 我知道 `ln(V)` 是随机猜测基线
- [ ] 我理解 warmup 和余弦退火的作用
- [ ] 我会用 `--overfit` 做冒烟测试
- [ ] 我能解释训练损失下降、验证损失上升意味着什么
- [ ] 我知道 checkpoint 里保存了哪些信息

下一章：用训练好的模型生成文本。

[第 07 章：生成 →](./07_generation.md)