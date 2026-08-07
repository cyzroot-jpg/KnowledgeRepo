# opencode

# 1. opencode的目录结构

项目级配置目录：
```json
your-project/                      # 你的业务项目根目录
├── .opencode/                     # 🗂️ 项目级配置目录
│   ├── memory-bank/               # 🧠 记忆库 (跨会话保持上下文)
│   │   ├── projectbrief.md        # 项目需求与目标
│   │   ├── productContext.md      # 产品背景与解决的问题
│   │   ├── activeContext.md       # 当前工作焦点与最近变更
│   │   ├── systemPatterns.md      # 系统架构与设计模式
│   │   ├── techContext.md         # 技术栈与开发环境
│   │   └── progress.md            # 项目进度与已知问题
│   ├── skills/                    # 🛠️ 自定义技能
│   ├── agents/                    # 🤖 自定义 Agent 定义
│   ├── commands/                  # ⌨️ 自定义斜杠命令 (/xxx)
│   └── specs/                     # 📋 项目规范文档
│
├── AGENTS.md                      # 项目专属 AI 指令 (优先级高)
└── opencode.json                  # 项目 MCP 服务配置
```
> .opencode 目录是 OpenCode 项目级配置的核心目录。你可以把它理解为你项目的“专属控制台”，用来存放只在这个项目里生效的各类个性化设置。


# 2. skills配置方式

opencode的skills发现机制：

> 对于项目本地路径，OpenCode 会从当前工作目录向上遍历，直到到达 git 工作树根目录。 在此过程中，它会加载 .opencode/ 中所有匹配的 skills/*/SKILL.md，以及匹配的 .claude/skills/*/SKILL.md 或 .agents/skills/*/SKILL.md。

> 全局定义也会从 ~/.config/opencode/skills/*/SKILL.md、~/.claude/skills/*/SKILL.md 和 ~/.agents/skills/*/SKILL.md 中加载。


# 3. opencode.json的位置

> 在项目目录中创建或更新 opencode.json 文件


# 遇到的问题

## 1. 会话容易中断

> 原因：
```bash
日志内容：

timestamp=2026-08-06T14:25:35.271Z level=INFO run=f5964e56 message="project copy refresh started" projectID=global
timestamp=2026-08-06T14:25:35.274Z level=INFO run=f5964e56 message="project copy refresh done" projectID=global updated=[] removed=[]
timestamp=2026-08-06T14:31:52.171Z level=ERROR run=f5964e56 message="Failed to fetch models.dev" cause=Cause([Fail(TimeoutError)])
timestamp=2026-08-06T15:26:32.506Z level=INFO run=f5964e56 message="booting location services" directory=/root/node_modules/opencode-linux-loong64/bin/projects/waic workspaceID=undefined

```

前景：
```bash
OpenCode 使用 AI SDK 和 Models.dev 支持 75+ LLM 提供商，并支持运行本地模型。

AI SDK	Vercel 出品的 TypeScript 工具包，用统一 API 调用各种 AI 模型，构建 AI 应用

Models.dev	开源的 AI 模型信息数据库，一站式查询所有模型的规格、定价和能力,静态配置/元数据（价格、尺寸、能力标志）。

OpenCode 与 Models.dev 的集成加载机制
1. 传统方案的痛点（背景）
传统的 AI 编程工具（如旧版 Cursor 或 Continue）通常采用硬编码方式维护模型参数（如上下文窗口大小、是否支持JSON模式等）。

缺点：每当厂商发布新模型，工具必须发布新版本进行适配，导致用户无法即时使用最新模型，维护成本高且响应滞后。

2. OpenCode 的核心机制：动态加载
OpenCode 不再硬编码，而是将 Models.dev 作为“模型配置中心”，在运行时动态拉取数据。

① 运行时拉取

时机：在 IDE/工具启动时，或用户在设置中切换模型时。

动作：实时请求 models.dev 的公开 JSON API（https://models.dev/api.json），获取最新的全量模型数据库。

② 动态调整行为（字段映射）
OpenCode 读取 JSON 中的特定字段，并据此自动调整底层逻辑，无需人工干预：

contextWindow（上下文长度）：自动计算 Prompt 预留空间，防止超出 Token 限制。

supportsTools（工具调用）：决定是否向该模型发送 function calling 格式的函数定义。

supportsImages / supportsAudio（多模态）：决定是否允许用户向对话框上传图片或音频文件。

pricing（定价信息）：在 UI 界面实时计算并显示本次对话的预估消耗费用。

3. 该设计的巧妙之处（优势）
优势一：零等待更新（社区驱动）

当 Anthropic 发布 Claude 4 或 OpenAI 发布新模型时，无需等待 OpenCode 官方发布新版本。

只要 Models.dev 的 GitHub 仓库有社区成员提交 PR（Pull Request）并合并，几分钟内所有 OpenCode 用户即可无缝使用新模型，且参数准确无误。

优势二：标准化映射（统一标识）

OpenCode 内部使用统一的标准化 Model ID（如 claude-3-7-sonnet-20250219），该 ID 与 Models.dev 的记录保持严格一致。

加载模型时，OpenCode 仅将底层 Provider（如 OpenAI SDK、Anthropic SDK）的调用参数，动态映射为 models.dev 中的标准值，保证了代码的高内聚和低耦合。

补充说明（架构边界）：

需要注意的是，Models.dev 仅提供“静态元数据”（配置信息）。实际的推理请求（文本生成）依然由 OpenCode 直接发往各大厂商的原生 API（或本地 Ollama），不经过 Models.dev 服务器。

```

> 解决方法：
```bash
在启动opencode的时候禁止拉取模型

OPENCODE_DISABLE_MODELS_FETCH=1 opencode

```