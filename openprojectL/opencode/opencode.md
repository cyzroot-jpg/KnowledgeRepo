# opencode开源项目学习

## 1. 核心设计思想
```bash
① 分层严格单向依赖（架构价值观）
schema → protocol → server
                ↑
              core  ←（依赖 schema/llm/plugin）
client（零Effect Promise版 / /effect 版）→ sdk-next（嵌入式 host）→ tui/cli/app/opencode
- schema = 浏览器安全的 wire/storage 契约（纯 Effect Schema，无运行时行为）
- protocol = 定义 HttpApi 契约 + 中间件放置（不 import core/server）
- server = 组装具体实现（提供中间件 key）
- core = 领域引擎本体，绝不 import packages/opencode
- 客户端由契约代码生成，禁止手改 generated

② V1/V2 双轨演进（正处深度重构期）
- V1 = 旧架构（Hono + Bus + SyncEvent + 单进程 SessionPrompt.loop），保留在 core/src/v1、opencode/src/session 作兼容
- V2 = 目标架构：SessionV2 事件溯源引擎 + EventV2 持久事件日志 + 插件 hooks + HttpApi 生成客户端
- 学习时注意：很多地方同时存在两套实现

③ 事件溯源 + 可重放（EventV2 / SessionV2）
- 持久事件日志（event + event_sequence 表），事务内写事件 + 投影 + 序列号分配 + post-commit 发布，全部原子
- Session 是"事件 → 投影"的只读读模型；State.Transformable 可重放状态变换
- "受理（admit）"与"执行（execute）"分离：输入先进持久收件箱，到安全 Provider 轮次边界才晋升为模型可见消息
- 崩溃后继续恢复、集群化执行被显式推迟——这是边界清晰的工程取舍

④ 统一运行时抽象：Effect + AppNode
- 服务 = Context.Service + Layer，按 Location（目录）作用域实例化（InstanceState + ScopedCache）
- AppNodeBuilder/LayerNode 把一组服务组装成"每个目录一份"的运行时
- 依赖注入替代全局单例，插件通过 Layer 注入

⑤ 工具（Tool）系统
- 不透明类型 Tool.make({description, input, output, execute, toModelOutput?})，单一执行器
- 执行管道：解析→解码→调用→编码→投影→边界化输出→持久结算
- 输出边界化：超限文本进受管文件 + 有界预览，绝不发布有损成功
- 失效拒绝：注册被替换后拒绝旧调用；命名即注册键，Location 注册优先于进程级

⑥ 上下文工程（Context Epoch / System Context）
- System Context 拆成多个独立观测的 Context Source（稳定 key + codec + loader + 纯渲染器）
- Context Epoch：一次不可变的 provider 缓存基线；只在实际变化的边界发时序系统消息
- 自动压缩：超预算时滚动摘要 + 保留近期转写，绝不跨压缩边界拆分 provider 原生消息

⑦ 权限双轨
- permissions（交互式 ask/allow/deny + 保存的批准）+ experimental.policies（allow/deny 通配，最后一个匹配胜出，文档反向读取）
- bash 无沙箱，默认 ask，靠 external_directory 强校验 + 宿主用户权限模型

⑧ 插件即边界
- 插件 hook 收不可变输入 + 返回 Immer draft 可变输出 + cancel；按固定 order 确定性触发
- provider/config/auth/model-discovery 都变成插件 transforms，服务热重载（reload() 重跑 transforms）
- 插件无权改 policy

⑨ 客户端-服务器同构
- 网络版与嵌入式版共用同一 HttpApi 契约，只换 HttpClient transport
- @opencode-ai/client（根=零Effect Promise fetch；/effect=富 Effect 客户端）；sdk-next = 进程内执行 Server 的 HttpRouter，无网络 I/O

⑩ "Everything is hotreloadable" + 明确推迟清单
细粒度事件驱动重配；同时把 provider 超时策略、post-crash 恢复、集群化等明确列为"将来切片"。

```

## 2. 核心思想分解学习

**0. 先破除一个误区：Agent 不是一个"循环"，而是一份"配置"**

```bash
在 opencode 里，"Agent" 是一个数据对象（core/src/agent.ts），不是运行主体：

AgentV2.Service（@opencode/v2/Agent）
├── 状态：Map<ID, Info> + default ID
├── Info = { model, request(system prompt), permissions, steps, mode, color, description }
├── 操作：get / default / resolve / select / all
└── 关键点：Agent 只描述"用什么模型、什么系统提示、什么权限、最多跑几步"，不执行任何东西

真正的"循环"是 SessionRunner（core/src/session/runner/），真正的"状态机"是 SessionV2.Service（core/src/session.ts）。理解这层分离是读懂这个项目的钥匙：
```

| 概念 | 是什么 | 代码位置 |
|------|--------|----------|
| Agent | 配置/选择（数据） | `core/src/agent.ts` |
| Session | 会话编排/API 门面（对外） | `core/src/session.ts` |
| SessionRunner | 一次 provider turn 的执行（内层循环） | `core/src/session/runner/llm.ts` |
| SessionExecution | 每 Session 串行化 + 唤醒/中断（外层循环） | `core/src/session/execution/local.ts` |
| SessionRunCoordinator | 进程级并发协调器 | `core/src/session/run-coordinator.ts` |
| ToolRegistry | 工具注册/物化/结算 | `core/src/tool/registry.ts` |
| SystemContext | 特权上下文（初始化/对账/替换） | `core/src/system-context/index.ts` |
| EventV2 | 事件溯源（持久/投影/重放） | `core/src/event.ts` |

**1. 一次完整 Agent Turn 的旅程（核心）**
```bash
以用户发一条消息 sessions.prompt(...) 为起点，完整走一遍代码：

① 受理（Admission）—— core/src/session.ts:360 → session/input.ts:41
prompt: Effect.uninterruptible(...)        // 受理过程不可中断
  ├─ SessionInput.admit(db, events, {...}) // 关键：写入持久 inbox
  │    └─ events.publish(PromptAdmitted)   // 事件溯源：PromptAdmitted 事件
  ├─ if (resume !== false) execution.wake(sessionID)  // 建议性唤醒
  └─ return admitted                        // 返回 Admitted{admittedSeq, id, ...}

设计要点：输入先落 session_input 表（收件箱），此刻模型还看不到它。admit 与 execute 彻底分离——这就是整个项目最核心的"受理/执行分离"思想。admittedSeq 是持久化的事件序列号，用于后续幂等重试（同一 messageID + session + prompt + delivery 才允许重试，否则 PromptConflictError）。

② 唤醒与协调 —— session/execution/local.ts + run-coordinator.ts

execution.wake() 调用 SessionRunCoordinator.wake()：
wake: Effect.sync(() => {
  const entry = active.get(key)
  if (entry !== undefined) { entry.pendingWake = true; return }  // 合并唤醒（容量1）
  const next = makeEntry(); active.set(key, next); start(key, next, false)
})

设计要点：
每个 Session 一个协调器条目，同一 Session 的执行严格串行，不同 Session 并发（Map<Key, Entry>）
wake 是"咨询性"的：活跃执行中再次 wake 只置 pendingWake=true，绝不并发跑第二个 drain；run（显式 resume）会 join 现有执行
interrupt 只针对本进程拥有的执行链；空闲/缺失是 no-op
Drain 是进程本地的执行跨度，没有持久身份——崩溃后继续恢复被明确推迟（run-coordinator.ts:51-64 的 settle 逻辑处理续跑）

③ Provider Turn 内层循环 —— session/runner/llm.ts（全项目的心脏）
run() 外层循环（queue 交付）→ runTurn() 内层循环（steer 交付 + 工具续跑）：
run: while (shouldRun) {
  let needsContinuation = true, step = 1
  while (needsContinuation) {
    const result = yield* runTurn(sessionID, promotion, step)
    needsContinuation = result.needsContinuation
    step = result.step + 1
    ...
    if (!needsContinuation) needsContinuation = hasPending(db, sessionID, "steer")
  }
  shouldRun = hasPending(db, sessionID, "queue")   // queue 交付：空闲边界才晋升
}

runTurnAttempt 的关键步骤（llm.ts:173-348）：
 1. 位置校验：Session 的 location 必须与当前 runner 的 location 一致，否则中断（llm.ts:180）

 2. 选择 Agent：agents.select(session.agent) —— 会话存的是 agent ID，运行时解析

 3. 初始化 Context Epoch：SessionContextEpoch.initialize(db, loadSystemContext(agent), session.id)，加载 System Context（系统提示 + 技能引导 + 引用引导，concurrency: "unbounded" 并发加载）

 4. 晋升输入：promoteSteers / promoteNextQueued，在安全边界把收件箱输入变成用户消息（llm.ts:187-196）。晋升会重置 agent 的 provider 轮次配额（currentStep = 1）

 5. 解析模型：models.resolve(session) → 从 Catalog 解析 provider/模型/凭据/variant（runner/model.ts）

 6. 加载历史：SessionHistory.entriesForRunner —— 应用压缩与 Epoch 截断后的投影历史

 7. 构建请求：LLM.request({model, providerOptions, system, messages, tools, toolChoice})，system 由 agent 的 system prompt + Epoch baseline 组成

 8. 压缩检查：compaction.compactIfNeeded(...) 超预算就触发 TurnTransitionError（自动压缩后重建请求重跑）

 9. 快照：snapshots.capture() 记录 turn 前的文件状态（用于 diff 和 revert）

10. llm.stream(request) —— 每个 provider turn 只有这一次流式请求，一个信号量（Semaphore.makeUnsafe(1)）串行化所有事件发布

④ 流式事件的四种命运（llm.ts:232-275）
const providerStream = llm.stream(request).pipe(
  Stream.runForEach((event) => {
    if (overflowFailure || publisher.hasProviderError()) return  // 溢出或已失败则停
    if (LLMEvent.is.providerError(event)) { ... 判断是否 context overflow ... }
    yield* publish(event)                          // ① 发布持久事件（text/reasoning/tool...）
    if (event.type !== "tool-call" || event.providerExecuted) return  // ② hosted 工具跳过本地
    needsContinuation = true
    const assistantMessageID = publisher.assistantMessageID(event.id)  // ③ 绑定持久 assistant 消息 ID
    toolMaterialization.settle({ sessionID, agent, assistantMessageID, call: event })  // ④ 本地结算
      .pipe(FiberSet.run(toolFibers))   // 急切启动，但不阻塞当前流
  }),
)

设计要点：
工具调用在流中急切启动（eager），但通过 FiberSet 放进后台 fiber，流关闭后才 FiberSet.join 等待所有工具结算
每个工具调用都先记录持久事件（publisher.assistantMessageID），副作用发生前就已持久化调用中断/失败时的严谨清理链：failInterruptedTools → 未结算工具标记 Tool execution interrupted → 绝不静默重放副作用（llm.ts:119-139, 295-315）
三个层级的错误语义（tool/AGENTS.md）：ToolFailure（预期、模型可见）vs 中断（取消，不是工具结果）vs 缺陷（runtime 运维失败）——禁止大范围 catch-cause，中断和缺陷必须穿透

⑤ 结算与续跑（llm.ts:316-345）
流成功 + 工具都结算后，发布 Step.Ended（含 end snapshot、文件 diff、tokens、finish 原因）
needsContinuation = !hasProviderError() && needsContinuation —— 只有工具被调用过才续跑
续跑：回到第 3 步 runTurn，重载历史再起一次 provider turn，绝不把工具循环留在内存里
若 agent 配了 steps 上限，最后一轮 toolChoice: "none" + 注入 MAX_STEPS_PROMPT，工具直接禁用

```

**2. 事件溯源：持久事件的"唯一真相"**
```bash
EventV2.Service（core/src/event.ts）是所有 agent 行为的记账本，也是理解一切异步的钥匙：

commitDurableEvent（event.ts:216-364）—— 一个事务里原子完成：
  1. 读 EventSequenceTable 拿当前 seq（aggregate 级单调递增）
  2. 校验 owner / 幂等（同 id + seq + 数据才算重放命中）
  3. 顺序执行 projectors（投影器！）
  4. 执行 commit hook（如晋升收件箱行）
  5. 写 EventSequenceTable（新 seq）
  6. 写 EventTable（事件本体，versionedType 带版本号）
  7. 事务提交后发布到 PubSub 唤醒 durable 尾部

关键机制：
- Durable vs Live：带 durable: { aggregate, version } 的事件持久化可重放；Text.Delta/Reasoning.Delta/Tool.Input.Delta 是 live-only（只给连接的渲染器，不推进持久游标）——见 schema/src/session-event.ts

- 可重放：events.durable({aggregateID, after}) = 先回放历史 + 再订阅 live（event.ts:585-604），SSE 流由此而来

- 投影：SessionProjector（session/projector.ts）把事件转成读模型——session_message 表、session_input 收件箱状态、session 表汇总（cost/tokens 累加）

- 事件清单：session.next.* 系列（PromptAdmitted/Prompted/Text/Reasoning/Tool/Step/Compaction...）都在 schema/src/session-event.ts 定义，Event.inventory 统一登记

```

**3. 系统上下文：特权上下文的代数结构**
```bash
core/src/system-context/index.ts 把"系统提示"这个模糊概念拆成了严格的代数：

Source<A> = { key, codec, load, baseline, update, removed? }
  ↓ make() 关闭 A 的类型，变成不透明 SystemContext
  ↓ combine() 组合多个 source，拒绝重复 key
  ↓ initialize() 首次观测 → { baseline文本, snapshot }   // 不可变基线 + 模型隐藏的结构化快照
  ↓ reconcile() 对账 → Unchanged | Updated(文本+新快照) | 需 Replace
  ↓ replace()   压缩后 → ReplacementReady | ReplacementBlocked

- Context Epoch：一次不可变的 provider 缓存基线（含日期、AGENTS.md、技能列表等），只有实际变化的边界才发时序系统消息（ContextUpdated 事件），不是每次轮询都推

- 快照（Snapshot）：模型隐藏的 JSON 比较状态，让"对账"可以精确知道哪个 source 变了、是否需要发更新消息

- 不可用上下文（Unavailable）：stale-while-revalidate 语义，与"成功加载为空"区分（后者可能触发 removal 文本）

- 原子性：Mid-Conversation System Message 持久化与快照推进在同一事务——session/context-epoch.ts

```

**4. 工具系统：不透明值 + 结算边界**
```bash
core/src/tool/tool.ts 定义不透明 Tool.make：

Tool.make({ description, input, output, structured?, toStructuredOutput?, execute, toModelOutput? })
  └─ runtimes WeakMap 持有私有 runtime（definition / settle / permission）

- 双层注册：进程级 ApplicationTools（opencode.tools.register）+ 每 Location 的 ToolRegistry，Location 覆盖进程级，最新注册胜出，scope 关闭只移除自己的

- 物化（Materialization）：registry.materialize(permissions) 输出快照——definitions（给模型的广告）+ settle（执行入口）。模型看到的是广告，执行的是同一份注册，且校验 identity 防止 stale

- 结算管道（registry.ts:50-82）：解析 → 解码输入 → 执行 → 编码输出 → toModelOutput 投影 → 输出边界化（超限文本进受管文件 + 有界预览）→ 返回

- 权限：注册表不做授权！叶子工具自行构造 PermissionV2 请求（tool/AGENTS.md：受信工具自己决定权限请求）。注册表只在 materialize 时做"整体禁用"的可见性过滤

- 内置工具：read/bash/edit/write/apply_patch/glob/grep/webfetch/websearch/todowrite/question/skill 等，每个配 .txt 提示词（opencode/src/tool/）

```

**5. Agent 与 Session 的边界（V1/V2 桥接）**
```bash
opencode/src/event-v2-bridge.ts 是两者之间的胶水：把 core 的 EventV2 事件转发到旧的 GlobalBus（兼容 V1 的 TUI/App/CLI），并自动附加当前 Instance 的 location。这解释了为什么 packages/opencode 仍在——它是兼容层，不是架构核心。

```

## 3. 按核心设计思想拆解项目
```json
学习主线（理解 agent 的 7 大支柱，全部对应代码）
├─ 1. 受理/执行分离        → session/input.ts, session.ts:prompt
├─ 2. 事件溯源             → event.ts, session/projector.ts, schema/session-event.ts
├─ 3. 安全边界+轮次         → session/runner/llm.ts, session/history.ts
├─ 4. 上下文代数            → system-context/index.ts, session/context-epoch.ts
├─ 5. 工具结算             → tool/tool.ts, tool/registry.ts, tool-output-store.ts
├─ 6. 模型解析             → session/runner/model.ts, llm/(llm.ts, route/, protocols/)
├─ 7. 进程级协调           → session/execution/local.ts, session/run-coordinator.ts
│
横切机制
├─ 位置作用域（Location）   → location.ts, location-service-map.ts, effect/app-node.ts
├─ Effect DI/Layer         → 几乎所有 service（Context.Service + Layer + node）
├─ 事件发布/SSE            → protocol/groups/event.ts, opencode/src/server/event.ts
├─ 权限                    → permission.ts, policy.ts
└─ 压缩/快照               → session/compaction.ts, snapshot.ts

```