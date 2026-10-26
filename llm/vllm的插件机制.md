# VLLM插件机制
VLLM的插件机制，就是一套，装了就能自动自动接上的扩展办法

## 1. 什么是插件
比如手机是（VLLM）出厂后就这么点功能和软件，为了想要更多的功能就需要自己下载其他的软件（这个软件就是插件）。

VLLM也是一样的。它想支持很多的模型，和很多的硬件，但他不可能写死在代码里面，于是就规定，别人可以写插件包装上去。

## 2. 为什么需要插件机制
因为VLLM要面对两件事永远在变：
模型的东西              例子
模型                    其他的模型
硬件                    其他的硬件平台

如果每来一个就需要该VLLM源码，就会导致源码会乱，就要不停的更新。因此，VLLM就规定，“我不认识你，但你按照我的规矩登记一下，启动时，我就会找到你”

## 3. 这套机制靠的两个东西
1. entry_points（登记信息）
你的插件包在打包时，写一句话：“VLLM启动时，请调用我的init函数”。安装后，这句话会被记在环境里（entry_points.txt）。

2. importlib.metadata（查登记册）
VLLM启动时，会翻查登记册：把所有登记过的插件找出来，挨个调用他们的函数。

总的来说就是：装包时登记-->启动时翻册-->调用注册

## vLLM的几个插件类别
组名（类别）                管什么
vllm.platform_plugins       硬件平台
vllm.gengral_plugins        通用扩展：模型、补丁
vllm.stat_logger_plugins    统计日志

## 完整的流程
1. 你写插件包，并在里面声明：启动时调用init()
2. pip install 你的插件，环境里就有了登记信息
3. 你运行vllm server ，vllm启动--> 翻登记册-->发现你的插件--> 调用init()-->你的模型被注册进VLLM
4. 之后vLLM加载模型时，就认识你的模型了。

## 一个具体的例子
VLLM出场：不认识xxxx模型
你装插件后，init()里面写：register_model("Qwen3DenseForCausalLM", 我的类)

VLLM启动：调用init()-->注册表里面多了这个条

你vllm server一个xxxxx模型：vllm查注册表-->找到-->用你的代码跑

## 真实解释
第一步：如果想放进去一个新的模型，就要构建一个包的的结构，结构如下：
xxx-model
    |_ __init__.py # 放一个注册函数
    |_ model
        |_ __init__.py
        |_ model.py # 模型的组网文件

第二步：创建好上面的内容后，然后创建pyproject.tom配置信息，然后通过使用python -m build来生成whl包。

第三步：安装这个whl包，安装完之后，启动vllm server的时候会自动加载我们的模型。
> 注意：注册名/架构名要和模型 config.json 的 architectures[0] 对上，否则加载不到。
## entry_points
| 对比维度 | `console_scripts` | `vllm.general_plugins` |
|---|---|---|
| 谁定义的 | Python 打包标准（所有遵循该标准的安装器都认） | vLLM 自己定义的（由 vLLM 识别和消费） |
| 谁消费 | `pip` 等安装器，在安装时生成命令行入口 | vLLM，在运行时读取入口点并调用注册函数 |
| 拿来干什么 | 生成一个命令行可执行文件 | 调用函数，为 vLLM 注册插件或扩展功能 |
| 结果 | 环境里多一个命令，例如 `mygreet` | vLLM 获得相应的插件注册信息，例如模型注册 |
| 不安装 vLLM 会怎样 | 照样可以使用该命令（前提是相关包及依赖已安装） | 普通 Python 安装器不会消费它；没有 vLLM 来读取，就不会触发相应的注册逻辑 |



## VLLM里面的注册
ModelRegistry.register_model("Qwen3DenseForCausalLM", "tecovllm_models.models.qwen3_dense:Qwen3DenseForCausalLM")

1. ModelRegistry 是什么
它是 vLLM 内部的一张对照表（本质是个字典）：
架构名(architectures[0])  →  模型类
"Qwen3DenseForCausalLM"   →  你的 Qwen3DenseForCausalLM
"LlamaForCausalLM"        →  vLLM 自带的 Llama 实现
...
vLLM 加载任何模型前，都会拿 config.json 里的 architectures[0] 去这张表查："该用哪个类？"

2. 两个参数的含义
ModelRegistry.register_model(
    "Qwen3DenseForCausalLM",                                    # ① 键：架构名
    "tecovllm_models.models.qwen3_dense:Qwen3DenseForCausalLM", # ② 值：类的位置
)
基本正确——核心就是往字典里塞一条 self.models[model_arch] = model。没有复杂操作。


## VLLM是如何进行读取插件的
