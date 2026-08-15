# python

## 1. OpenAI

```bash
你的 Python 程序
       │
       ↓
  openai Python库
       │
       ↓
 HTTP API 请求
       │
       ↓
 OpenAI API
       │
       ↓
     模型


```

```bash

openai
│
├── OpenAI
│
├── responses
│   └── create()
│
├── chat
│   └── completions
│       └── create()
│
├── embeddings
│   └── create()
│
├── files
│
├── models
│
├── fine_tuning
│
└── ...


```



```bash
1. 安装
pip install openai

2. 导入
from openai import OpenAI

3. 使用

```python

client = OpenAI(
    api_key="xxx",
    base_url="https://api.openai.com/v1",
    timeout=60.0,
    max_retries=2
)

参数	        作用
api_key	        API Key
base_url	    API 服务地址
timeout	        请求超时时间
max_retries	    自动重试次数



response = client.responses.create(
    model="gpt-5",
    input="什么是 RAG？"
)

print(response.output_text)

-----------------------------------------------
response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[
        {
            "role": "user",
            "content": "什么是 RAG？"
        }
    ]
)

print(response.choices[0].message.content)
```

## 2. python的init方法

```python
self 不是 Python 强制规定“所有 __init__ 都必须叫 self”，而是实例方法的第一个参数需要接收“当前对象本身”。

在Python类中规定，函数的第一个参数是实例对象本身，并且约定俗成，把其名字写为self。其作用相当于java中的this，表示当前类的对象，可以调用当前类中的属性和方法。

普通函数第一个参数没有要求 和 类的实例方法的默认的第一个参数是self
```


## 3. response的结构：

```json

ChatCompletion                         ← 对象类型
│
├── id: str
│   └── "20260815113436306dc400ce7d4bf9"
│
├── choices: list[Choice]
│   │
│   └── Choice                         ← 对象类型
│       │
│       ├── finish_reason: str | None
│       │   └── "tool_calls"
│       │
│       ├── index: int
│       │   └── 0
│       │
│       ├── logprobs: ... | None
│       │   └── None
│       │
│       └── message: ChatCompletionMessage
│           │
│           ├── content: str | None
│           │   └── "你好！我来帮你查看当前目录中的文件。"
│           │
│           ├── refusal: str | None
│           │   └── None
│           │
│           ├── role: Literal["assistant"]
│           │   └── "assistant"
│           │
│           ├── annotations: list[...] | None
│           │   └── None
│           │
│           ├── audio: ... | None
│           │   └── None
│           │
│           ├── function_call: ... | None
│           │   └── None
│           │
│           ├── tool_calls: list[
│           │       ChatCompletionMessageFunctionToolCall
│           │   ] | None
│           │   │
│           │   └── ChatCompletionMessageFunctionToolCall
│           │       │
│           │       ├── id: str
│           │       │   └── "call_-7349550098499494940"
│           │       │
│           │       ├── type: str
│           │       │   └── "function"
│           │       │
│           │       ├── index: int
│           │       │   └── 0
│           │       │
│           │       └── function: Function
│           │           │
│           │           ├── name: str
│           │           │   └── "list_dir"
│           │           │
│           │           └── arguments: str
│           │               └── "{}"
│           │
│           └── reasoning_content: str | None
│               └── "用户想要查看当前目录中的文件……"
│
├── created: int
│   └── 1786764877
│
├── model: str
│   └── "glm-4.7-flash"
│
├── object: str
│   └── "chat.completion"
│
├── service_tier: str | None
│   └── None
│
├── system_fingerprint: str | None
│   └── None
│
├── usage: CompletionUsage | None
│   │
│   ├── prompt_tokens: int
│   │   └── 278
│   │
│   ├── completion_tokens: int
│   │   └── 60
│   │
│   ├── total_tokens: int
│   │   └── 338
│   │
│   ├── completion_tokens_details: CompletionTokensDetails | None
│   │   │
│   │   ├── accepted_prediction_tokens: int | None
│   │   ├── audio_tokens: int | None
│   │   ├── reasoning_tokens: int | None
│   │   │   └── 44
│   │   └── rejected_prediction_tokens: int | None
│   │
│   └── prompt_tokens_details: PromptTokensDetails | None
│       │
│       ├── audio_tokens: int | None
│       └── cached_tokens: int | None
│           └── 276
│
└── request_id: str | None
    └── "20260815113436306dc400ce7d4bf9"

```

## 4. __init__.py

```bash

__init__.py 是 Python 包（Package）的初始化文件。你可以把它理解成：

告诉 Python：“这个目录是一个 Python 包”，并且可以在导入这个包时执行一些初始化代码。

1. __init__.py 里面可以什么都不写

2. 它的一个重要作用就是让这个目录明确成为一个 Python package。

3. Python 3.3 以后支持 Namespace Package，所以某些情况下没有 __init__.py 也可以导入。

4. __init__.py 最重要的用途之一：统一导出

比如你现在有：

tools/
├── __init__.py
├── file_tools.py
└── shell_tools.py

file_tools.py：

def read_file(path):
    print(f"读取文件：{path}")

shell_tools.py：

def run_shell(command):
    print(f"执行命令：{command}")

你可以在：

tools/__init__.py

里面写：

from .file_tools import read_file
from .shell_tools import run_shell

那么外部就可以直接：

from tools import read_file, run_shell

而不需要：

from tools.file_tools import read_file
from tools.shell_tools import run_shell


5. __init__.py 还能在导入时执行代码v

例如：
# tools/__init__.py
print("tools package 被加载了")


6. . 是什么意思
你以后会经常看到：

from .file_tools import read_file

这里的：

.

表示：

当前 package

所以：

from .file_tools import read_file

就是：

从当前 tools 包里的 file_tools.py
导入 read_file

而：

from ..xxx import xxx

就是：

从上一级 package 导入
```