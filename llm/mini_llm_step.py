"""
mini_llm_step.py —— 可「单步执行」的迷你 LLM（纯 numpy，无训练）

和 mini_llm.py 的区别：
    每一步都会停下来，等你按回车才继续，方便你一步一步观察
    每个变量的 shape 和数值、以及这一步在干什么。

运行：
    python3 mini_llm_step.py

操作：
    [回车] 执行下一步
    [a]    自动播放到底
    [q]    退出
"""

import sys
import numpy as np

np.set_printoptions(precision=3, suppress=True, linewidth=200)
rng = np.random.default_rng(42)

INTERACTIVE = sys.stdin.isatty()   # 非交互环境自动全速播放
auto = not INTERACTIVE
_step = 0


# ----------------------------------------------------------------------
# 单步控制：打印说明 -> 等回车
# ----------------------------------------------------------------------
def banner(title, desc=""):
    global _step, auto
    _step += 1
    print("\n" + "═" * 70)
    print(f"▶ 步骤 {_step}  |  {title}")
    print("═" * 70)
    if desc:
        for line in desc.strip("\n").split("\n"):
            print("   " + line)
    if not auto:
        try:
            ans = input("\n   [回车]下一步   [a]自动播放   [q]退出 > ").strip().lower()
        except EOFError:
            ans = ""
        if ans == "q":
            print("   已退出。")
            sys.exit(0)
        if ans == "a":
            auto = True
            print("   >>> 自动播放模式 <<<")


def show(label, arr):
    """打印一个张量的形状，并预览数值。"""
    print(f"\n   {label}")
    print(f"       shape = {arr.shape}")
    flat = np.asarray(arr)
    with np.printoptions(precision=3, suppress=True, linewidth=100):
        print(f"       value =\n{np.array2string(flat, prefix='               ')}")


# ----------------------------------------------------------------------
# 基础运算
# ----------------------------------------------------------------------
def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)


def layer_norm(x, g, b, eps=1e-5):
    mean = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return g * (x - mean) / np.sqrt(var + eps) + b


def gelu(x):
    return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x ** 3)))


# ----------------------------------------------------------------------
# 配置 & 权重
# ----------------------------------------------------------------------
D_MODEL = 8
N_HEADS = 2
HEAD_DIM = D_MODEL // N_HEADS
N_LAYERS = 2
MAX_SEQ = 16

corpus = "hello world"
vocab = sorted(set(corpus))
VOCAB_SIZE = len(vocab)
stoi = {ch: i for i, ch in enumerate(vocab)}
itos = {i: ch for ch, i in stoi.items()}


def randn(*shape, scale=0.1):
    return rng.normal(0, scale, size=shape)


W_E = randn(VOCAB_SIZE, D_MODEL)
W_P = randn(MAX_SEQ, D_MODEL)
layers = []
for _ in range(N_LAYERS):
    layers.append({
        "ln1_g": np.ones(D_MODEL), "ln1_b": np.zeros(D_MODEL),
        "Wq": randn(D_MODEL, D_MODEL), "bq": np.zeros(D_MODEL),
        "Wk": randn(D_MODEL, D_MODEL), "bk": np.zeros(D_MODEL),
        "Wv": randn(D_MODEL, D_MODEL), "bv": np.zeros(D_MODEL),
        "Wo": randn(D_MODEL, D_MODEL), "bo": np.zeros(D_MODEL),
        "ln2_g": np.ones(D_MODEL), "ln2_b": np.zeros(D_MODEL),
        "W1": randn(D_MODEL, 4 * D_MODEL), "b1": np.zeros(4 * D_MODEL),
        "W2": randn(4 * D_MODEL, D_MODEL), "b2": np.zeros(D_MODEL),
    })
ln_f_g = np.ones(D_MODEL)
ln_f_b = np.zeros(D_MODEL)
W_lm = randn(D_MODEL, VOCAB_SIZE)
b_lm = np.zeros(VOCAB_SIZE)


# ======================================================================
# 开始
# ======================================================================
print("#" * 70)
print("#  迷你 LLM 单步演示：每一小步都会停下，观察输入输出 shape 和数值")
print("#" * 70)

banner("总览：我们要走的路", f"""
文本 -> 分词 -> Embedding -> N 层(Attention+MLP) -> LM Head -> 下一个 token
配置：T=11 个 token, d_model={D_MODEL}, n_heads={N_HEADS}, n_layers={N_LAYERS}
主干张量 H 的形状全程都是 [T, d_model] = [11, {D_MODEL}]
""")

# ----------------------------------------------------------------------
banner("分词：文本 -> 整数 id", """
计算机只认识数字。先把每个字符映射成一个整数。
""")
text = "hello world"
ids = [stoi[c] for c in text]
print(f"\n   词表 vocab = {vocab}")
print(f"   '{text}' -> ids = {ids}")
ids_arr = np.array(ids)
show("ids (序列长度 T)", ids_arr)

T = len(ids)
banner(f"Embedding 查表：id -> 向量", f"""
用每个 id 去 W_E 里查一行，得到 d_model={D_MODEL} 维向量。
""")
H = W_E[ids]
print(f"\n   W_E 是 Embedding 表，形状 {W_E.shape} = [词表, d_model]")
show("H = W_E[ids]", H)

banner("加上位置编码", """
再给每个位置加一个可学的向量，否则模型分不清词的先后顺序。
""")
H = H + W_P[np.arange(T)]
show("H = H + W_P[0:T]", H)
print("\n   >>> H 是主干张量(residual stream)，接下来每层都读它、改它。")

# ----------------------------------------------------------------------
for li in range(N_LAYERS):
    p = layers[li]
    H_in = H.copy()
    banner(f"进入第 {li} 层：记录本层输入", f"""
第 {li} 层的输入就是上一层的输出 H。
""")
    show(f"H (第 {li} 层输入)", H)

    banner(f"第 {li} 层 - LayerNorm①", """
归一化，让数值均值 0、方差 1，训练/推理更稳定。
""")
    x = layer_norm(H, p["ln1_g"], p["ln1_b"])
    show("x = LayerNorm(H)", x)

    banner(f"第 {li} 层 - 计算 Q、K、V", """
每个 token 生成三个向量：
  Q(Query)=我想找什么   K(Key)=我能提供什么   V(Value)=我携带的内容
""")
    q = x @ p["Wq"] + p["bq"]
    k = x @ p["Wk"] + p["bk"]
    v = x @ p["Wv"] + p["bv"]
    show("Q = x·Wq + bq", q)
    show("K = x·Wk + bk", k)
    show("V = x·Wv + bv", v)
    print(f"\n   >>> 真实的 KV Cache 缓存的就是这里的 K、V（每层都存）。")

    banner(f"第 {li} 层 - 拆成 {N_HEADS} 个头", f"""
把 d_model={D_MODEL} 切成 {N_HEADS} 个头、每头 {HEAD_DIM} 维，
让模型从多个“视角”同时看上下文。
""")
    qh = q.reshape(T, N_HEADS, HEAD_DIM).transpose(1, 0, 2)
    kh = k.reshape(T, N_HEADS, HEAD_DIM).transpose(1, 0, 2)
    vh = v.reshape(T, N_HEADS, HEAD_DIM).transpose(1, 0, 2)
    show("Q -> [n_heads, T, head_dim]", qh)

    banner(f"第 {li} 层 - 计算注意力分数 scores", """
每个 token 的 Q 和所有 token 的 K 做点积，得到“相似度”。
""")
    scores = qh @ kh.transpose(0, 2, 1) / np.sqrt(HEAD_DIM)
    show("scores = Q·Kᵀ / √head_dim", scores)
    print("\n   >>> scores[i][j] = 第 i 个 token 对第 j 个 token 的原始关注分。")

    banner(f"第 {li} 层 - 加因果掩码", """
防止“偷看未来”：把上三角(未来位置)的分数设成 -1e9，
这样 softmax 后它们的权重就变成 0。
""")
    mask = np.triu(np.ones((T, T)), k=1).astype(bool)
    scores = np.where(mask, -1e9, scores)
    show("scores（上三角已屏蔽）", scores)

    banner(f"第 {li} 层 - softmax 得到注意力权重 attn", """
把分数变成概率，每一行加起来=1。
因为掩码，上三角是 0，所以是“下三角矩阵”。
""")
    attn = softmax(scores, axis=-1)
    show("attn = softmax(scores)", attn)
    print("\n   >>> attn[h][i][j] = 第 h 个头里，token i 花在 token j 上的注意力。")

    banner(f"第 {li} 层 - 用权重对 V 加权求和", """
按注意力权重，把各个 token 的 V 混合起来，得到这个 token 的新表示。
""")
    out = attn @ vh
    show("out = attn·V", out)

    banner(f"第 {li} 层 - 拼回多头 + 输出投影", """
把各头的结果拼回 [T, d_model]，再过一次线性层 Wo 融合。
""")
    out = out.transpose(1, 0, 2).reshape(T, D_MODEL)
    show("多头拼回", out)
    out = out @ p["Wo"] + p["bo"]
    show("Attention 最终输出 = out·Wo", out)

    banner(f"第 {li} 层 - 残差①：H = H + Attention", """
把 Attention 的结果“加”回主干。
正因如此主干 shape 不变，信息能顺畅传递。
""")
    H = H + out
    show("H = H + Attention", H)

    banner(f"第 {li} 层 - LayerNorm②", "MLP 之前再归一化一次。")
    x = layer_norm(H, p["ln2_g"], p["ln2_b"])
    show("x = LayerNorm(H)", x)

    banner(f"第 {li} 层 - MLP 升维", "先变宽（8->32），给模型更多表达能力。")
    m = x @ p["W1"] + p["b1"]
    show("h = x·W1", m)

    banner(f"第 {li} 层 - MLP 激活(GELU)", "加入非线性，让模型能表达复杂函数。")
    m = gelu(m)
    show("h = gelu(h)", m)

    banner(f"第 {li} 层 - MLP 降维", "再变回 8 维。")
    m = m @ p["W2"] + p["b2"]
    show("h = h·W2", m)

    banner(f"第 {li} 层 - 残差②：H = H + MLP", "MLP 结果再加回主干。")
    H = H + m
    show("H = H + MLP", H)
    print(f"\n   >>> 第 {li} 层输出 shape = {H.shape}，和第 {li} 层输入 {H_in.shape} 完全一样！")

# ----------------------------------------------------------------------
banner("所有层跑完 - 最终 LayerNorm", "输出前最后归一化一次。")
H_norm = layer_norm(H, ln_f_g, ln_f_b)
show("H_norm", H_norm)

banner("只取最后一个位置", """
我们预测的是“下一个 token”，所以只关心最后一个位置的向量。
前面位置的输出已经作为 K/V 被用了，不需要送进 LM Head。
""")
last = H_norm[-1]
show("last = H_norm[-1]", last)

banner("LM Head：hidden -> 词表分数 logits", """
把 d_model 维向量投影到“词表大小”的维度，
每个数就是对应词的原始分数。
""")
logits = last @ W_lm + b_lm
show("logits = last·W_lm", logits)

banner("softmax -> 下一个 token 的概率", "分数转成概率。")
probs = softmax(logits)
show("probs", probs)
print("\n   每个词作为下一个 token 的概率：")
for ch, pr in zip(vocab, probs):
    print(f"     {ch!r:>5} : {pr:6.3f}  {'#' * int(pr * 50)}")

banner("采样：选出下一个 token", "这里用最简单的 greedy：选概率最大的。")
next_id = int(np.argmax(probs))
print(f"\n   下一个 token id = {next_id}  ->  字符 {itos[next_id]!r}")
print(f"   新文本 = '{text}' + '{itos[next_id]}'")

banner("生成循环：一次一个 token", f"""
真实生成时：把这个新 token 拼回输入，重复【整段流程】，再生成下一个。
为避免重复计算，真实引擎用 KV Cache 存下每层的 K、V。
本模型没训练，所以输出是随机的 —— 我们只看数据怎么流。
""")

print("\n" + "#" * 70)
print("#  演示结束！共走了", _step, "步。")
print("#" * 70)