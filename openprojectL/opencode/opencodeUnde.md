# opencode的理解

## 1. 输入处理架构

```bash
思想：
用户消息到达后，不直接交给模型执行，而是先可靠保存起来，然后在异步执行
Admission（受理）和Execution（执行）分离
用户消息 ---> Admission（受理阶段）---> 保存到session_input数据库 ---> Execution执行阶段 ---> LLM推理

"我先告诉系统：我收到了你的消息，并且永久记录下来。至于什么时候处理，后面再说。"


传统方式：
收到消息 ----> 直接执行
如果，LLM执行到一半服务器挂了，消息就会丢失，需要重新发送
```

```bash
1. prompt: Effect.uninterruptible(...)

整个受理过程不可被打断
用户发送消息 ---> 准备写数据库 ---> 突然取消任务

如果允许中断：
收到消息 ---> 数据库写一半 ---> 程序停止 ---> 数据损坏

因此：
Admission阶段：必须保证要么成功写入，要么完全失败。类似数据库事务。


2. SessionInput.admit(db, events, {...})
这个就是把用户输入写入inbox
类似发邮件：用户 ---> 邮箱服务器 inbox ---> 你打开邮件阅读

session_input表就是inbox


3.events.publish(PromptAdmitted)
这个是事件溯源
系统不仅保存当前状态，还保存发生过什么事情


4.execution.wake(sessionID)
通知执行器
这个session有新消息了，可以干活了


5.admittedSeq 是什么？
事件序号
seq=100

用户登录


seq=101

用户发送:
你好


seq=102

AI开始回答


seq=103

AI结束

admittedSeq=101
这条输入在整个事件流中的唯一位置。

之所以需要这个：是因为系统可能会失败，例如用户输入你好 ---> 写入数据库 ---> 得到admittedseq=101 ---> 准备执行服务器突然挂了 ---> 重启以后可以重新执行

```

**幂等重试**
```bash
分布式系统的概念：
例如：
用户发送： 帮我总结论文 ---> 系统执行 ---> 第一次：

收到消息

开始生成

服务器挂

系统重试。

如果没有幂等：

可能：

执行两次:

回答1
回答2

产生重复。

所以系统规定：

只有完全一样的请求才能重试。

条件：

messageID
+
session
+
prompt
+
delivery

必须全部一致。

例如：

第一次：

session:

A


messageID:

001


prompt:

介绍RAG


delivery:

web

失败。

重试：

一样：

session:

A


messageID:

001


prompt:

介绍RAG


delivery:

web

允许。

```