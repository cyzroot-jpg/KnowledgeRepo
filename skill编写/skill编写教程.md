# skill编写教程

## 1. skill的格式

> skill的后缀名固定为md

`skill的核心就是：文件夹 + 一个SKILL.md文件`

```bash
SKILL.md文件中包含：
    - 元数据（至少需要有名称和描述）
    - 告诉AI如何完成某一特定任务的指令
```

## 2. skill本质
skill的本质就是一个md文件
> skill_名
   |_SKILL.md


## 3. SKILL.md模板

```md
---
name: skill的名字
description: skill的功能描述
---

# 名称

## 使用场景
具体的使用场景描述

## 功能1

- 使用什么`工具`完成什么任务

## 功能2
详细的描述
```

```json
最小必填字段：
name: skill的名字
description: skill的功能描述

可选字段：
license: 许可证
metadata:
    author: example-org
    version: "x.x.x"
```

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 是 | Skill 名称，最长 64 字符，只能使用小写字母、数字和 `-`，且不能以 `-` 开头或结尾 |
| `description` | 是 | 功能与使用场景说明，最长 1024 字符，不能为空 |
| `license` | 否 | 许可证名称或指向随 Skill 附带的许可证文件 |
| `compatibility` | 否 | 环境与依赖说明（产品、系统包、网络权限等），最长 500 字符 |
| `metadata` | 否 | 自定义键值对，用于扩展元数据（如作者、版本号） |
| `allowed-tools` | 否 | 允许使用的工具列表（空格分隔，实验性功能） |

```json
更复杂的skill的目录结构

skill_name/
|_SKILL.md
|_scripts/ # 可选： 可执行代码
|_references/  # 可选：文档资料
|_assets/  # 可选： 模板、资源

```

## 4. Skill如何工作
skill用渐进式加载来高校管理上下文：
- 发现： 启动时，AI只加载每个技能的名称和描述，只保留最基本的识别信息
- 激活： 当任务匹配某个技能的`描述`时，AI才把完整的SKILL.md指令读入上下文
- 执行： AI按照指令执行，按需加载参考文件或运行代码


| 对比项 | 普通 Prompt | Skills 机制 |
|--------|-------------|-------------|
| 每次都要重新描述 | 是 | 否（只描述一次） |
| 上下文长度占用 | 每次全量塞入 | 渐进式加载（只在触发时才读完整内容） |
| 一致性 | 依赖每次 prompt 质量 | 高（固定 SOP + 模板） |
| 复用性 | 手动复制粘贴 | 自动匹配 / slash 命令 / 项目共享 |
| 维护方式 | 改一次 prompt 就要重新发 | 修改 SKILL.md 文件，全局/项目生效 |

