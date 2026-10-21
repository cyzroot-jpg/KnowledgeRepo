# vLLM 基础模型添加教程笔记

> 本笔记整理自 [vLLM 官方文档 - Basic Model](https://docs.vllm.ai/en/stable/contributing/model/basic/)，旨在梳理向 vLLM 添加新模型的核心步骤与要点。

---

## 一、导入模型代码

从源仓库克隆 PyTorch 模型代码，例如 vLLM 的 OPT 模型就是从 HuggingFace 的 `modeling_opt.py` 改编而来。

> ⚠️ **注意**：务必审阅并遵守原始代码的版权和许可条款。

---

## 二、使代码与 vLLM 兼容

### 2.1 初始化要求

所有 vLLM 模块的构造函数必须包含 `prefix` 参数：

- **作用一（运行时支持）**：vLLM 的注意力算子通过全名在模型状态中注册，每个注意力算子必须有唯一的前缀作为层名，避免冲突。
- **作用二（非均匀量化支持）**：量化检查点可以选择性地量化某些层，而保持其他层为全精度。通过提供 `prefix`，vLLM 可以将当前层前缀与量化配置匹配，决定该层是否以量化模式初始化。

### 2.2 计算要求

1. **添加 `embed_input_ids` 方法**：在模型模块内添加该方法，根据 `input_ids` 返回文本嵌入。这等价于直接调用文本嵌入层，但为复合多模态模型提供了统一接口。
2. **重写 `forward` 方法**：
   - 移除不必要的代码（如训练专用代码）。
   - 将 `input_ids` 和 `positions` 改为**展平张量**（flattened tensors），仅包含单个 batch size 维度，不含 max-sequence length 维度。

> ⚠️ **注意**：vLLM 目前仅支持基础的多头注意力机制及其带旋转位置嵌入的变体。如果模型采用不同的注意力机制，需要在 vLLM 中实现新的注意力层。

> 💡 **建议**：vLLM 已支持大量模型，推荐找到与目标模型相似的实现进行参考和改编。可参考 `vllm/model_executor/models` 目录下的示例。

---

## 三、（可选）实现张量并行与量化支持

当模型过大无法放入单张 GPU 时，可使用张量并行。需将模型的线性层和嵌入层替换为张量并行版本。

### 3.1 嵌入层与输出层替换

| 原始层 | 替换为 |
|--------|--------|
| `torch.nn.Embedding` | `VocabParallelEmbedding` |
| 输出 LM head | `ParallelLMHead` |

### 3.2 线性层并行选项

| 类名 | 说明 | 典型用途 |
|------|------|----------|
| `ReplicatedLinear` | 复制输入和权重到多 GPU，无内存节省 | — |
| `RowParallelLinear` | 输入沿 hidden 维度切分，权重沿行（输入维度）切分，矩阵乘法后执行 all-reduce | 第二个 FFN 层、注意力层的输出线性变换 |
| `ColumnParallelLinear` | 输入复制，权重沿列（输出维度）切分，结果沿列切分 | 第一个 FFN 层、原始 Transformer 中分离的 QKV 变换 |
| `MergedColumnParallelLinear` | 合并多个 `ColumnParallelLinear` 算子 | 带加权激活函数（如 SiLU）的第一个 FFN 层 |
| `QKVParallelLinear` | 多头/分组查询注意力的 QKV 投影并行层 | 当 KV 头数小于 world size 时，正确处理 KV 头的复制 |

> 📌 所有上述线性层都接收 `linear_method` 参数，vLLM 会根据不同的量化方案自动设置该参数以支持权重量化。

---

## 四、实现权重加载逻辑

在 `*ForCausalLM` 类中实现 `load_weights` 方法，从 HuggingFace 检查点文件加载权重并分配到模型对应层。

对于 `MergedColumnParallelLinear` 和 `QKVParallelLinear` 层，如果原始模型有分离的权重矩阵，需要分别加载不同部分。

---

## 五、注册模型

参考 [模型注册页面](https://docs.vllm.ai/en/stable/contributing/model/registration/) 的指引，将新模型注册到 vLLM 中。

---

## 六、常见问题

### 6.1 支持交错滑动窗口的模型

1. 确保模型的 `config.json` 包含 `layer_types`。
2. 在建模代码中，解析每层的滑动窗口值，传递给注意力层的 `per_layer_sliding_window` 参数。

### 6.2 支持使用 Mamba 的模型

分三种场景：

| 场景 | 说明 | 参考实现 | 协议 |
|------|------|----------|------|
| **场景 1** | 仅使用 Mamba 层（Mamba-1 或 Mamba-2），无注意力层 | `MambaForCausalLM`（Mamba-1）或 `Mamba2ForCausalLM`（Mamba-2） | 继承 `IsAttentionFree` |
| **场景 2** | Mamba 层 + 注意力层混合 | `JambaForCausalLM`（Mamba-1+注意力）或 `NemotronHForCausalLM`（Mamba-2+注意力） | 继承 `IsHybrid` |
| **场景 3** | Mamba-like 机制（如 Linear Attention、ShortConv）+ 注意力层 | `Lfm2ForCausalLM` | 同场景 2 |

**场景 1 额外要求**：
- 实现 `get_mamba_state_dtype_from_config` 和 `get_mamba_state_shape_from_config` 类方法
- Mamba 层使用 `MambaMixer`（Mamba-1）或 `MambaMixer2`（Mamba-2）
- 添加到 `MODELS_CONFIG_MAP`

**场景 2 额外要求**：
- 无需添加到 `MODELS_CONFIG_MAP`（运行时默认值从协议推断）

**场景 3 额外要求（自定义 Mamba-like 层）**：
- 继承 `MambaBase`，实现 `get_state_dtype`、`get_state_shape`、`mamba_type`、`get_attn_backend`
- 实现 "attention meta-data" 类
- 更新 `MambaAttentionBackendEnum`
- 支持 torch compile 和 CUDA graphs 需将调用包装为自定义 op 并注册
- 新自定义 op 需添加到 `_attention_ops` 列表

---

## 七、关键参考文件

| 用途 | 路径 |
|------|------|
| 模型示例 | `vllm/model_executor/models/` |
| Llama 实现参考 | `vllm/model_executor/models/llama.py` |
| 模型注册配置 | `vllm/model_executor/models/config.py` |
| Mamba 后端注册 | `vllm/v1/attention/backends/registry.py` |
| 编译配置 | `vllm/config/compilation.py` |




> ----
1. 注册
```bash
tecovllm_models/             # TecoVLLM的插件机制
├── __init__.py              # 模型注册入口
├── layers/                  # 公共模块（如 RMSNorm、RoPE 等）
│   └── ...
└── models/                  # 模型组网
    ├── __init__.py
    └── ...
```
```bash

模型组网文件中需实现 embed_input_ids、forward、compute_logits、load_weights 等接口
需要做的改动：
```
```bash
1. 构造函数__init__ —— 增加 prefix 参数
```
```python
原：
                                                            
def __init__(self, config):                                                         
    super().__init__(config)                                                            
    self.self_attn = LlamaAttention(config)                                                         

```

```python
VLLM风格：

def __init__(self, config, prefix: str = ""):  # 1. 新增 prefix 参数
    super().__init__(config)
    # 2. 实例化任何子模块（尤其是Attention层）时，把 prefix 传进去
    self.self_attn = LlamaAttention(config, prefix=f"{prefix}.self_attn") 

```
> 你要改的地方：模型主类（*ForCausalLM）、每一层DecoderLayer、以及层内部的Attention类，它们的 __init__ 都要加上 prefix 并往下传。

```bash
2. 新增 embed_input_ids 方法
```
```python

在模型主类（*ForCausalLM）中新增一个函数：

def embed_input_ids(self, input_ids: torch.Tensor) -> torch.Tensor:
    # 直接调用你的词嵌入层（通常是 model.embed_tokens 或 model.embed_word）
    return self.model.embed_tokens(input_ids)

```
> 你要改的地方：找到 self.model.embed_tokens 或类似的Embedding层对象，把这行代码贴进去。

```bash

3. forward 函数签名 —— 接收扁平张量
```
```python

原代码（HF风格）：

def forward(self, input_ids, attention_mask, position_ids, ...):
    # input_ids 形状是 [batch, seq_len]

```
```python

vLLM风格：

def forward(self, input_ids, positions, kv_caches, attn_metadata, ...):
    # 注意：input_ids 和 positions 现在形状是 [num_tokens] (一维)

```
> 1. 函数参数里的 position_ids 改名为 positions。
> 2. 删除 attention_mask 参数（vLLM不需要，由 attn_metadata 接管）。
> 3. 内部接收的 input_ids 不再有第1维（seq_len），直接当一维张量处理。

```bash
4. forward 函数内部 —— 删除维度重整 + 删除训练逻辑
```
```python

原代码内部：
# 隐藏层通常需要 view 或 reshape
hidden_states = hidden_states.view(bs, seq_len, -1) 
# 有 if self.training 分支
# 有 return loss

```
```python

改为：
# 1. 删掉所有的 .view(batch, seq_len) 操作，保持 [num_tokens, hidden_dim]
# 2. 删掉 if self.training 条件判断及 dropout 训练分支
# 3. 删掉计算 loss 的代码（只需要返回 logits）
# 4. 删掉 attention_mask 的运算逻辑

```
> 你要改的地方：把整个 forward 函数里涉及 batch_size、seq_len 维度变换的代码全部移除。只保留纯粹的矩阵乘法、激活函数和残差连接。

```bash
5. 替换底层 Attention 实现（最核心）
```
```python

原代码： 使用 torch.nn.MultiheadAttention 或 HuggingFace 自带的 LlamaAttention。

```
```python

改为： 导入并使用 vLLM 自带的 Attention 层。
from vllm.attention import Attention

# 在 __init__ 中：
self.attn = Attention(
    num_heads=config.num_attention_heads,
    head_size=config.hidden_size // config.num_attention_heads,
    num_kv_heads=config.num_key_value_heads,  # GQA支持
    prefix=prefix  # 必须传
)

# 在 forward 中，调用方式改为：
attn_output, _ = self.attn(
    hidden_states,  # [num_tokens, hidden_dim]
    kv_cache=kv_caches,  # 由vLLM外部传入
    attn_metadata=attn_metadata,  # 由vLLM外部传入
)

```
> 你要改的地方：
> 1. 删掉原有的 self.attn 初始化代码。
> 2. 将 forward 中调用旧注意力计算（如 torch.bmm 或 scaled_dot_product_attention）的代码，替换成上述 self.attn(...) 调用。
> 3. 如果模型特殊（如Alibi位置编码），需在 Attention 初始化时指定 position_embedding 类型。





```c++

from vllm import ModelRegistry

def init():
    ModelRegistry.register_model(
        model_arch="Qwen3DenseForCausalLM", model_cls="tecovllm_models.models.qwen3_dense:Qwen3DenseForCausalLM"
    )
    ModelRegistry.register_model(
        model_arch="HunYuanDenseV1ForCausalLM", model_cls="tecovllm_models.models.hunyuan_v1_dense:HunYuanDenseV1ForCausalLM"
    )

```

