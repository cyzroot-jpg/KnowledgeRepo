import type { Scenario } from "./types";

/** 点击即可填入输入框的示例命令 */
export const SAMPLE_COMMANDS: readonly string[] = [
  "修复登录页点击没反应",
  "给项目补一个 README",
  "解释这个报错并给出修复方案",
];

export const DEFAULT_COMMAND = SAMPLE_COMMANDS[0];

/**
 * 演示脚本：整个流程被拆成 9 个阶段。
 * 文案中的 {cmd} 会在运行时替换成用户实际输入的命令。
 */
export const baseScenario: Scenario = {
  command: DEFAULT_COMMAND,
  phases: [
    {
      id: "p1-submit",
      title: "阶段 1 · 提交命令",
      description:
        "用户输入被封装成一条 prompt，由 Client SDK 通过 HTTP 发给服务端。这一步还没有任何事件产生，服务端也还没开始工作。",
      activeNodes: ["composer", "clientSdk", "httpHandler"],
      packets: [
        { from: "composer", to: "clientSdk", label: "user prompt" },
        { from: "clientSdk", to: "httpHandler", label: "POST /session/:id/prompt" },
      ],
      events: [],
      details: {
        composer: {
          input: "用户在输入框里敲下的文本：{cmd}",
          output: "一条 user prompt，同时在消息列表中乐观插入一个气泡",
          note: "optimistic message: { status: 'pending' }",
          files: ["packages/client/src/components/Composer.tsx"],
        },
        clientSdk: {
          input: "user prompt + sessionId",
          output: "HTTP 请求；同时保持 SSE 订阅处于打开状态",
          files: ["packages/sdk/src/client.ts"],
        },
        httpHandler: {
          input: "HTTP 请求体（prompt、clientId、可选 attachments）",
          output: "调用 Session.prompt()，立即返回 202",
          files: ["packages/server/src/http/prompt.ts"],
        },
      },
    },
    {
      id: "p2-enqueue",
      title: "阶段 2 · 进入输入队列",
      description:
        "prompt 不直接变成消息，而是先写入 session_inbox。这样输入就变成可靠、可取消、可幂等的一条记录。",
      activeNodes: ["session", "inbox", "eventBus", "projector", "sqlite"],
      packets: [
        { from: "httpHandler", to: "session" },
        { from: "session", to: "inbox" },
        { from: "inbox", to: "eventBus" },
        { from: "eventBus", to: "projector" },
        { from: "projector", to: "sqlite" },
      ],
      events: [
        {
          type: "session.inbox.enqueued",
          durability: "durable",
          summary: "输入被写入 session_inbox，还没有成为可见消息",
          node: "inbox",
          seq: 1,
        },
      ],
      details: {
        session: {
          input: "prompt 文本",
          output: "交给 Inbox 入队，不直接开始执行",
          files: ["packages/core/src/session/session.ts"],
        },
        inbox: {
          input: "一条 prompt",
          output: "session_inbox 中的一行（状态 enqueued）",
          note: "INSERT INTO session_inbox (session_id, payload, state) VALUES (?, ?, 'enqueued')",
          files: ["packages/core/src/session/inbox.ts"],
        },
        eventBus: {
          input: "inbox 变更",
          output: "广播 durable 事件 session.inbox.enqueued",
          files: ["packages/core/src/session/event-bus.ts"],
        },
        projector: {
          input: "durable 事件",
          output: "在同一个事务里更新读模型",
          files: ["packages/core/src/session/projector.ts"],
        },
        sqlite: {
          input: "事件 + 读模型变更",
          output: "事件落盘，可被重放恢复",
          files: ["packages/core/src/store/sqlite.ts"],
        },
      },
    },
    {
      id: "p3-wake",
      title: "阶段 3 · 唤醒执行",
      description:
        "Session 唤醒自己的执行 fiber。同一个 Session 同一时刻只允许一条 fiber，跨 Session 则可以并发。",
      activeNodes: ["session", "execution", "runCoordinator"],
      packets: [
        { from: "session", to: "execution" },
        { from: "execution", to: "runCoordinator" },
      ],
      events: [
        {
          type: "session.execution.started",
          durability: "durable",
          summary: "开启一个 busy period，并写入可恢复的 claim",
          node: "execution",
          seq: 2,
        },
      ],
      details: {
        execution: {
          input: "Session.wake() 调用",
          output: "一条执行 fiber（含恢复 claim）",
          note: "claim: { sessionId, runId, leaseUntil }  // 崩溃后可被接管",
          files: ["packages/core/src/execution/fiber.ts"],
        },
        runCoordinator: {
          input: "fiber 的执行请求",
          output: "同 Session 排队串行，不同 Session 并行放行",
          files: ["packages/core/src/execution/coordinator.ts"],
        },
      },
    },
    {
      id: "p4-deliver",
      title: "阶段 4 · 投递输入",
      description:
        "Runner 从 Inbox 提升这条输入：inbox 行被消费的同时，插入一条真正的 user message，界面上才出现用户气泡。",
      activeNodes: ["runner", "inbox", "eventBus", "projector", "sqlite"],
      packets: [
        { from: "runCoordinator", to: "runner" },
        { from: "runner", to: "inbox" },
        { from: "inbox", to: "eventBus" },
        { from: "eventBus", to: "projector" },
        { from: "projector", to: "sqlite" },
      ],
      events: [
        {
          type: "session.inbox.delivered",
          durability: "durable",
          summary: "inbox 行被消费，同时插入一条 user message",
          node: "inbox",
          seq: 3,
        },
      ],
      output: { kind: "user", text: "{cmd}" },
      details: {
        runner: {
          input: "被唤醒的执行权",
          output: "向 Inbox 请求提升下一条输入",
          files: ["packages/core/src/execution/runner.ts"],
        },
        inbox: {
          input: "提升请求",
          output: "inbox 行标记 delivered + 一条 user message",
          files: ["packages/core/src/session/inbox.ts"],
        },
      },
    },
    {
      id: "p5-context",
      title: "阶段 5 · 装配上下文",
      description:
        "Runner 请 Context Builder 组装一次模型调用需要的全部材料：Agent 与权限、系统提示、历史、工具快照、模型。",
      activeNodes: [
        "contextBuilder",
        "agent",
        "instructions",
        "modelResolver",
        "history",
        "toolRegistry",
      ],
      packets: [
        { from: "runner", to: "contextBuilder" },
        { from: "contextBuilder", to: "agent" },
        { from: "contextBuilder", to: "instructions" },
        { from: "contextBuilder", to: "modelResolver" },
        { from: "contextBuilder", to: "history" },
        { from: "contextBuilder", to: "toolRegistry" },
      ],
      events: [],
      details: {
        contextBuilder: {
          input: "Runner 的一次装配请求",
          output: "system / messages / tools 三段快照",
          note:
            "system   = agent 系统提示 + instruction baseline\n" +
            "messages = 最近一次压缩之后的历史\n" +
            "tools    = 当前权限允许的工具快照",
          files: ["packages/core/src/context/builder.ts"],
        },
        agent: {
          input: "agent 名称或默认 agent",
          output: "agent 定义 + 合并后的权限表",
          files: ["packages/core/src/agent/registry.ts"],
        },
        instructions: {
          input: "agent 定义 + 工作区约定",
          output: "系统提示字符串（含 AGENTS.md、技能、MCP 说明）",
          files: ["packages/core/src/agent/instructions.ts"],
        },
        modelResolver: {
          input: "agent 指定的模型与 variant",
          output: "可调用的模型端点与参数",
          files: ["packages/core/src/model/resolver.ts"],
        },
        history: {
          input: "session id",
          output: "压缩点之后的历史消息",
          files: ["packages/core/src/context/compaction.ts"],
        },
        toolRegistry: {
          input: "权限表",
          output: "可被模型调用的工具列表（JSON Schema）",
          files: ["packages/core/src/tools/registry.ts"],
        },
      },
    },
    {
      id: "p6-first-call",
      title: "阶段 6 · 第一次调用模型",
      description:
        "Step 拿着上下文发起一次 LLM 调用。provider 的原始流被 Stream Normalizer 归一化成统一的 LLMEvent，再逐步变成事件。",
      activeNodes: [
        "runner",
        "step",
        "llmClient",
        "route",
        "provider",
        "streamNormalizer",
      ],
      packets: [
        { from: "runner", to: "step" },
        { from: "step", to: "llmClient" },
        { from: "llmClient", to: "route" },
        { from: "route", to: "provider" },
        { from: "provider", to: "streamNormalizer" },
        { from: "streamNormalizer", to: "step" },
      ],
      events: [
        {
          type: "session.step.started",
          durability: "durable",
          summary: "开始第 1 个 Step",
          node: "step",
          seq: 4,
        },
        {
          type: "session.text.started",
          durability: "durable",
          summary: "模型开始输出文本",
          node: "step",
          seq: 5,
        },
        {
          type: "session.text.delta",
          durability: "ephemeral",
          summary: "逐字流式增量（不落盘，只推送）",
          node: "step",
          seq: 6,
        },
        {
          type: "session.text.delta",
          durability: "ephemeral",
          summary: "继续推送增量",
          node: "step",
          seq: 7,
        },
        {
          type: "session.text.ended",
          durability: "durable",
          summary: "第一段文本结束，形成一条 assistant message",
          node: "step",
          seq: 8,
        },
      ],
      output: {
        kind: "assistant",
        text: "我先看一下登录页的实现，确认点击没有反应的原因。",
      },
      details: {
        step: {
          input: "上下文快照",
          output: "text.delta 流 + 持久化后的 assistant message",
          files: ["packages/core/src/execution/step.ts"],
        },
        llmClient: {
          input: "统一的请求对象",
          output: "按 provider 路由后的请求",
          files: ["packages/core/src/llm/client.ts"],
        },
        route: {
          input: "统一请求",
          output: "provider 私有协议请求体",
          files: ["packages/core/src/llm/routes/index.ts"],
        },
        provider: {
          input: "协议请求",
          output: "HTTP/SSE 原始流",
          files: ["packages/core/src/llm/transport.ts"],
        },
        streamNormalizer: {
          input: "provider 原始事件",
          output: "统一的 LLMEvent 序列",
          files: ["packages/core/src/llm/normalizer.ts"],
        },
      },
    },
    {
      id: "p7-tools",
      title: "阶段 7 · 工具调用与审批",
      description:
        "模型请求调用 read 工具。工具先经过权限检查：allow 直接执行，ask 需要用户批准，deny 直接拒绝。",
      activeNodes: ["step", "toolRegistry", "permission", "builtinTools"],
      packets: [
        { from: "step", to: "toolRegistry" },
        { from: "toolRegistry", to: "permission" },
        { from: "permission", to: "builtinTools" },
      ],
      events: [
        {
          type: "session.tool.input.started",
          durability: "durable",
          summary: "模型开始输出工具入参",
          node: "step",
          seq: 9,
        },
        {
          type: "session.tool.input.delta",
          durability: "ephemeral",
          summary: "工具入参的流式增量",
          node: "step",
          seq: 10,
        },
        {
          type: "session.tool.input.ended",
          durability: "durable",
          summary: "工具入参解析完成",
          node: "step",
          seq: 11,
        },
        {
          type: "session.tool.called",
          durability: "durable",
          summary: "工具调用被登记，等待执行",
          node: "toolRegistry",
          seq: 12,
        },
        {
          type: "permission.asked",
          durability: "ephemeral",
          summary: "该工具需要用户批准，执行在此暂停",
          node: "permission",
          seq: 13,
          gate: true,
        },
        {
          type: "session.tool.success",
          durability: "durable",
          summary: "工具返回结果，写回事件流",
          node: "builtinTools",
          seq: 14,
        },
      ],
      output: {
        kind: "tool",
        tool: { name: "read", input: "src/pages/Login.tsx", status: "success" },
      },
      details: {
        toolRegistry: {
          input: "工具名 + 入参",
          output: "找到工具实现并检查权限",
          files: ["packages/core/src/tools/registry.ts"],
        },
        permission: {
          input: "工具调用意图",
          output: "allow / ask / deny 决策；ask 时挂起等待用户",
          note: "policy: read -> allow | edit -> ask | shell -> ask",
          files: ["packages/core/src/tools/permission.ts"],
        },
        builtinTools: {
          input: "已授权的工具调用",
          output: "执行结果 + 文件快照",
          files: ["packages/core/src/tools/builtin/index.ts"],
        },
      },
    },
    {
      id: "p8-next-step",
      title: "阶段 8 · 进入下一步",
      description:
        "工具结果不会被塞回内存里的对话数组。Runner 重新从 SQLite 读历史，再发起一次完全独立的 LLM 调用。",
      activeNodes: ["runner", "history", "contextBuilder", "step", "llmClient"],
      packets: [
        { from: "step", to: "runner" },
        { from: "sqlite", to: "runner" },
        { from: "runner", to: "history" },
        { from: "history", to: "contextBuilder" },
        { from: "contextBuilder", to: "step" },
        { from: "step", to: "llmClient" },
      ],
      events: [
        {
          type: "session.step.started",
          durability: "durable",
          summary: "开始第 2 个 Step（全新的一次调用）",
          node: "step",
          seq: 15,
        },
        {
          type: "session.text.started",
          durability: "durable",
          summary: "模型基于工具结果继续输出",
          node: "step",
          seq: 16,
        },
        {
          type: "session.text.delta",
          durability: "ephemeral",
          summary: "逐字流式增量",
          node: "step",
          seq: 17,
        },
        {
          type: "session.text.delta",
          durability: "ephemeral",
          summary: "继续推送增量",
          node: "step",
          seq: 18,
        },
        {
          type: "session.text.ended",
          durability: "durable",
          summary: "第二段文本结束",
          node: "step",
          seq: 19,
        },
      ],
      output: {
        kind: "assistant",
        text: '找到问题了：第 42 行的 onClick 绑定了未定义的 handleClick，而且 button 缺 type="button"，在表单里会被当成提交。',
      },
      details: {
        runner: {
          input: "上一步的工具结果事件",
          output: "决定再走一个 Step",
          files: ["packages/core/src/execution/runner.ts"],
        },
        history: {
          input: "重新读取 SQLite",
          output: "含工具结果的最新历史（必要时触发压缩）",
          files: ["packages/core/src/context/compaction.ts"],
        },
        sqlite: {
          input: "SELECT 历史事件",
          output: "重放后的消息列表",
          files: ["packages/core/src/store/sqlite.ts"],
        },
      },
    },
    {
      id: "p9-finish",
      title: "阶段 9 · 完成并渲染",
      description:
        "Runner 没有更多事情要做，释放 claim 并标记执行成功。客户端消费同一套事件，投影出最终界面，会话回到 idle。",
      activeNodes: ["eventBus", "eventFeed", "clientStore", "composer"],
      packets: [
        { from: "step", to: "eventBus" },
        { from: "eventBus", to: "eventFeed" },
        { from: "eventFeed", to: "clientStore" },
        { from: "clientStore", to: "composer" },
      ],
      events: [
        {
          type: "session.step.ended",
          durability: "durable",
          summary: "Step 结束，带上 finish reason 与 usage",
          node: "step",
          seq: 20,
        },
        {
          type: "session.execution.succeeded",
          durability: "durable",
          summary: "busy period 结束，释放 claim",
          node: "execution",
          seq: 21,
        },
      ],
      output: {
        kind: "assistant",
        text: "已修改：把 handleClick 改成组件内的 arrow function，并给 button 补上 type=\"button\"。现在点击可以正常触发登录校验了。",
      },
      details: {
        eventBus: {
          input: "Step / Execution 产生的 durable 事件",
          output: "广播给所有订阅者（含 SSE）",
          files: ["packages/core/src/session/event-bus.ts"],
        },
        eventFeed: {
          input: "事件订阅",
          output: "SSE 推送给客户端",
          files: ["packages/server/src/http/events.ts"],
        },
        clientStore: {
          input: "SSE 事件",
          output: "消息树与工具状态（本地投影）",
          files: ["packages/client/src/store/projection.ts"],
        },
        composer: {
          input: "投影后的消息树",
          output: "最终渲染的回答，会话进入 idle",
          files: ["packages/client/src/components/Composer.tsx"],
        },
      },
    },
  ],
};

function fillCommand(value: unknown, command: string): unknown {
  if (typeof value === "string") {
    return value.split("{cmd}").join(command);
  }
  if (Array.isArray(value)) {
    return value.map((item) => fillCommand(item, command));
  }
  if (value && typeof value === "object") {
    const source = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(source)) {
      out[key] = fillCommand(source[key], command);
    }
    return out;
  }
  return value;
}

/** 用用户实际输入的命令替换脚本里的 {cmd} 占位符 */
export function withCommand(scenario: Scenario, command: string): Scenario {
  const text = command.trim().length > 0 ? command.trim() : DEFAULT_COMMAND;
  return fillCommand(scenario, text) as Scenario;
}
