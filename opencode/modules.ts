import type { Edge, EdgeRoute, LayerId, LayerMeta, ModuleNode } from "./types";

/** 虚拟画布尺寸：所有节点坐标都在这个坐标系里定义，渲染时整体等比缩放 */
export const LAYOUT = {
  width: 1120,
  height: 845,
  nodeW: 150,
  nodeH: 78,
  minScale: 0.62,
};

export const LAYERS: LayerMeta[] = [
  { id: "client", name: "客户端", color: "#22d3ee" },
  { id: "server", name: "服务端接入", color: "#60a5fa" },
  { id: "session", name: "会话核心", color: "#a78bfa" },
  { id: "execution", name: "执行编排", color: "#fbbf24" },
  { id: "context", name: "上下文与能力", color: "#34d399" },
  { id: "ai", name: "AI 与工具", color: "#fb923c" },
];

export const LAYER_MAP: Record<LayerId, LayerMeta> = LAYERS.reduce((acc, layer) => {
  acc[layer.id] = layer;
  return acc;
}, {} as Record<LayerId, LayerMeta>);

const colX = (c: number): number => 80 + c * 160;
const rowY = (r: number): number => 62 + r * 118;

interface NodeSeed {
  id: string;
  name: string;
  short: string;
  role: string;
  layer: LayerId;
  col: number;
  row: number;
  files?: string[];
}

const SEEDS: NodeSeed[] = [
  // 第 1 层：客户端
  {
    id: "composer",
    name: "Composer",
    short: "CMP",
    role: "收集用户输入，乐观显示消息",
    layer: "client",
    col: 1,
    row: 0,
    files: ["packages/client/src/components/Composer.tsx"],
  },
  {
    id: "clientSdk",
    name: "Client SDK",
    short: "SDK",
    role: "发送命令并订阅事件流",
    layer: "client",
    col: 3,
    row: 0,
    files: ["packages/sdk/src/client.ts"],
  },
  {
    id: "clientStore",
    name: "Client Data Store",
    short: "CDS",
    role: "把 SSE 事件投影成消息树",
    layer: "client",
    col: 5,
    row: 0,
    files: ["packages/client/src/store/projection.ts"],
  },

  // 第 2 层：服务端接入
  {
    id: "httpHandler",
    name: "HTTP Handler",
    short: "HTTP",
    role: "接收 POST /session/:id/prompt",
    layer: "server",
    col: 3,
    row: 1,
    files: ["packages/server/src/http/prompt.ts"],
  },
  {
    id: "eventFeed",
    name: "Event Feed",
    short: "FEED",
    role: "把事件以 SSE 推送给客户端",
    layer: "server",
    col: 5,
    row: 1,
    files: ["packages/server/src/http/events.ts"],
  },

  // 第 3 层：会话核心
  {
    id: "session",
    name: "Session",
    short: "SES",
    role: "会话门面：prompt / compact / interrupt",
    layer: "session",
    col: 1,
    row: 2,
    files: ["packages/core/src/session/session.ts"],
  },
  {
    id: "inbox",
    name: "Inbox",
    short: "INB",
    role: "输入队列：入队、投递、steer",
    layer: "session",
    col: 2,
    row: 2,
    files: ["packages/core/src/session/inbox.ts"],
  },
  {
    id: "eventBus",
    name: "Event Bus",
    short: "BUS",
    role: "发布 durable / ephemeral 事件",
    layer: "session",
    col: 3,
    row: 2,
    files: ["packages/core/src/session/event-bus.ts"],
  },
  {
    id: "projector",
    name: "Projector",
    short: "PRJ",
    role: "事务内把事件投影成读模型",
    layer: "session",
    col: 4,
    row: 2,
    files: ["packages/core/src/session/projector.ts"],
  },
  {
    id: "sqlite",
    name: "SQLite",
    short: "DB",
    role: "持久化事件、消息、inbox 行",
    layer: "session",
    col: 5,
    row: 2,
    files: ["packages/core/src/store/sqlite.ts"],
  },

  // 第 4 层：执行编排
  {
    id: "execution",
    name: "Execution",
    short: "EXE",
    role: "每 Session 一条 fiber：wake / claim",
    layer: "execution",
    col: 1,
    row: 3,
    files: ["packages/core/src/execution/fiber.ts"],
  },
  {
    id: "runCoordinator",
    name: "Run Coordinator",
    short: "RCO",
    role: "同 Session 串行，跨 Session 并发",
    layer: "execution",
    col: 2,
    row: 3,
    files: ["packages/core/src/execution/coordinator.ts"],
  },
  {
    id: "runner",
    name: "Runner",
    short: "RUN",
    role: "决定下一步，驱动多 Step",
    layer: "execution",
    col: 3,
    row: 3,
    files: ["packages/core/src/execution/runner.ts"],
  },
  {
    id: "step",
    name: "Step",
    short: "STP",
    role: "一次 LLM 调用：流式输出与工具",
    layer: "execution",
    col: 4,
    row: 3,
    files: ["packages/core/src/execution/step.ts"],
  },

  // 第 5 层：上下文与能力
  {
    id: "agent",
    name: "Agent",
    short: "AGT",
    role: "选择 Agent 并合并权限",
    layer: "context",
    col: 1,
    row: 4,
    files: ["packages/core/src/agent/registry.ts"],
  },
  {
    id: "instructions",
    name: "Instructions",
    short: "INS",
    role: "拼系统提示、AGENTS.md、技能",
    layer: "context",
    col: 2,
    row: 4,
    files: ["packages/core/src/agent/instructions.ts"],
  },
  {
    id: "contextBuilder",
    name: "Context Builder",
    short: "CTX",
    role: "装配历史、模型、工具快照",
    layer: "context",
    col: 3,
    row: 4,
    files: ["packages/core/src/context/builder.ts"],
  },
  {
    id: "modelResolver",
    name: "Model Resolver",
    short: "MDL",
    role: "解析模型与 variant",
    layer: "context",
    col: 4,
    row: 4,
    files: ["packages/core/src/model/resolver.ts"],
  },
  {
    id: "history",
    name: "History / Compaction",
    short: "HST",
    role: "读取历史，必要时压缩上下文",
    layer: "context",
    col: 5,
    row: 4,
    files: ["packages/core/src/context/compaction.ts"],
  },

  // 第 6 层：AI 与工具
  {
    id: "llmClient",
    name: "LLM Client",
    short: "LLM",
    role: "统一请求入口",
    layer: "ai",
    col: 2,
    row: 5,
    files: ["packages/core/src/llm/client.ts"],
  },
  {
    id: "route",
    name: "Route / Protocol",
    short: "RTE",
    role: "适配不同 provider 协议",
    layer: "ai",
    col: 3,
    row: 5,
    files: ["packages/core/src/llm/routes/index.ts"],
  },
  {
    id: "provider",
    name: "Provider Transport",
    short: "PVD",
    role: "HTTP/SSE 或 WebSocket 传输",
    layer: "ai",
    col: 4,
    row: 5,
    files: ["packages/core/src/llm/transport.ts"],
  },
  {
    id: "streamNormalizer",
    name: "Stream Normalizer",
    short: "NRM",
    role: "把 provider 事件归一化为 LLMEvent",
    layer: "ai",
    col: 5,
    row: 5,
    files: ["packages/core/src/llm/normalizer.ts"],
  },
  {
    id: "toolRegistry",
    name: "Tool Registry",
    short: "TRG",
    role: "注册、过滤、执行工具",
    layer: "ai",
    col: 1,
    row: 6,
    files: ["packages/core/src/tools/registry.ts"],
  },
  {
    id: "permission",
    name: "Permission",
    short: "PRM",
    role: "allow / ask / deny，ask 时等待",
    layer: "ai",
    col: 2,
    row: 6,
    files: ["packages/core/src/tools/permission.ts"],
  },
  {
    id: "builtinTools",
    name: "Built-in Tools",
    short: "BIT",
    role: "read / edit / shell / subagent",
    layer: "ai",
    col: 3,
    row: 6,
    files: ["packages/core/src/tools/builtin/index.ts"],
  },
  {
    id: "snapshot",
    name: "Snapshot",
    short: "SNP",
    role: "记录文件快照，支持 diff 回滚",
    layer: "ai",
    col: 4,
    row: 6,
    files: ["packages/core/src/tools/snapshot.ts"],
  },
];

export const MODULES: ModuleNode[] = SEEDS.map(({ col, row, ...rest }) => ({
  ...rest,
  x: colX(col),
  y: rowY(row),
}));

export const MODULE_MAP: Record<string, ModuleNode> = MODULES.reduce<Record<string, ModuleNode>>(
  (acc, m) => {
    acc[m.id] = m;
    return acc;
  },
  {},
);

export function getModule(id: string): ModuleNode | undefined {
  return MODULE_MAP[id];
}

interface EdgeSeed {
  from: string;
  to: string;
  route?: EdgeRoute;
  transport?: string;
}

const EDGE_SEEDS: EdgeSeed[] = [
  { from: "composer", to: "clientSdk", route: "side", transport: "本地调用" },
  { from: "clientSdk", to: "httpHandler", route: "down", transport: "HTTP POST /session/:id/prompt" },
  { from: "httpHandler", to: "session", route: "down", transport: "Session.prompt()" },
  { from: "session", to: "inbox", route: "side", transport: "入队" },
  { from: "inbox", to: "eventBus", route: "side", transport: "durable event" },
  { from: "eventBus", to: "projector", route: "side", transport: "事件投影（同一事务）" },
  { from: "projector", to: "sqlite", route: "side", transport: "SQL 写入" },
  { from: "session", to: "execution", route: "down", transport: "wake()" },
  { from: "execution", to: "runCoordinator", route: "side", transport: "claim" },
  { from: "runCoordinator", to: "runner", route: "side", transport: "串行调度" },
  { from: "runner", to: "inbox", route: "up", transport: "提升输入（steer / queue）" },
  { from: "runner", to: "contextBuilder", route: "down", transport: "装配上下文" },
  { from: "contextBuilder", to: "agent", route: "side", transport: "读取 agent 定义" },
  { from: "contextBuilder", to: "instructions", route: "side", transport: "读取指令" },
  { from: "contextBuilder", to: "modelResolver", route: "side", transport: "解析模型" },
  { from: "contextBuilder", to: "history", route: "side", transport: "读取历史" },
  { from: "contextBuilder", to: "toolRegistry", route: "down", transport: "工具快照" },
  { from: "runner", to: "step", route: "side", transport: "发起一步" },
  { from: "step", to: "llmClient", route: "down", transport: "统一请求" },
  { from: "llmClient", to: "route", route: "side", transport: "协议适配" },
  { from: "route", to: "provider", route: "side", transport: "HTTP / SSE" },
  { from: "provider", to: "streamNormalizer", route: "side", transport: "provider 原始流" },
  { from: "streamNormalizer", to: "step", route: "up", transport: "LLMEvent 归一化流" },
  { from: "step", to: "eventBus", route: "up", transport: "durable / ephemeral 事件" },
  { from: "step", to: "toolRegistry", route: "down", transport: "工具调用" },
  { from: "toolRegistry", to: "permission", route: "side", transport: "权限检查" },
  { from: "permission", to: "builtinTools", route: "side", transport: "执行工具" },
  { from: "builtinTools", to: "snapshot", route: "side", transport: "写快照" },
  { from: "eventBus", to: "eventFeed", route: "up", transport: "事件订阅" },
  { from: "eventFeed", to: "clientStore", route: "up", transport: "SSE 推送" },
  { from: "clientStore", to: "composer", route: "side", transport: "UI 投影" },
  { from: "sqlite", to: "runner", route: "down", transport: "重新读取历史" },
];

export const EDGES: Edge[] = EDGE_SEEDS.map((seed) => ({
  id: `${seed.from}->${seed.to}`,
  from: seed.from,
  to: seed.to,
  route: seed.route ?? "auto",
  transport: seed.transport,
}));

export function edgeKey(from: string, to: string): string {
  return `${from}->${to}`;
}

/** 按两个端点找连线（忽略方向），用于把演示脚本里的 packet 映射到连线 */
export function findEdge(from: string, to: string): Edge | undefined {
  return (
    EDGES.find((e) => e.from === from && e.to === to) ??
    EDGES.find((e) => e.from === to && e.to === from)
  );
}

const HW = LAYOUT.nodeW / 2;
const HH = LAYOUT.nodeH / 2;

function resolveRoute(a: ModuleNode, b: ModuleNode, route: EdgeRoute): "down" | "up" | "side" {
  if (route !== "auto") return route;
  const dy = b.y - a.y;
  if (Math.abs(dy) < 24) return "side";
  return dy > 0 ? "down" : "up";
}

/** 生成一条连线的 SVG path */
export function buildEdgePath(edge: Edge): string {
  const a = getModule(edge.from);
  const b = getModule(edge.to);
  if (!a || !b) return "";

  const kind = resolveRoute(a, b, edge.route);

  if (kind === "down") {
    const y1 = a.y + HH;
    const y2 = b.y - HH;
    const bend = Math.max(40, (y2 - y1) * 0.42);
    return `M ${a.x} ${y1} C ${a.x} ${y1 + bend}, ${b.x} ${y2 - bend}, ${b.x} ${y2}`;
  }

  if (kind === "up") {
    const y1 = a.y - HH;
    const y2 = b.y + HH;
    const bend = Math.max(40, (y1 - y2) * 0.42);
    return `M ${a.x} ${y1} C ${a.x} ${y1 - bend}, ${b.x} ${y2 + bend}, ${b.x} ${y2}`;
  }

  // 同一行：从侧边出发，必要时向下绕行，避免压住中间的卡片
  const dir = b.x >= a.x ? 1 : -1;
  const spans = Math.max(1, Math.round(Math.abs(b.x - a.x) / 160));
  const dip = dir > 0 ? (spans === 1 ? 0 : 70) : 74 + 22 * (spans - 1);
  const x1 = a.x + dir * HW;
  const x2 = b.x - dir * HW;
  const c1 = x1 + dir * 56;
  const c2 = x2 - dir * 56;
  return `M ${x1} ${a.y} C ${c1} ${a.y + dip}, ${c2} ${b.y + dip}, ${x2} ${b.y}`;
}

/** 连线上标注文字的位置（path 中点近似） */
export function edgeLabelPosition(edge: Edge): { x: number; y: number } {
  const a = getModule(edge.from);
  const b = getModule(edge.to);
  if (!a || !b) return { x: 0, y: 0 };
  const kind = resolveRoute(a, b, edge.route);
  if (kind === "side") {
    const spans = Math.max(1, Math.round(Math.abs(b.x - a.x) / 160));
    const dip = b.x >= a.x ? (spans === 1 ? 0 : 70) : 74 + 22 * (spans - 1);
    return { x: (a.x + b.x) / 2, y: a.y + dip * 0.72 + 6 };
  }
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}
