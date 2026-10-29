export type LayerId = "client" | "server" | "session" | "execution" | "context" | "ai";

export interface LayerMeta {
  id: LayerId;
  name: string;
  color: string;
}

/** 架构图中的一个模块节点 */
export interface ModuleNode {
  id: string;
  /** 模块名 */
  name: string;
  /** 卡片上的短代号 */
  short: string;
  /** 一句话职责 */
  role: string;
  layer: LayerId;
  /** 虚拟画布中的中心坐标 */
  x: number;
  y: number;
  /** 技术视图下展示的关键文件 */
  files?: string[];
}

export type EdgeRoute = "down" | "up" | "side" | "auto";

/** 模块之间的连线（也是“连接机制”的载体） */
export interface Edge {
  id: string;
  from: string;
  to: string;
  route: EdgeRoute;
  /** 连接机制，例如 HTTP、事件总线、SSE、工具调用 */
  transport?: string;
}

export type Durability = "durable" | "ephemeral" | "none";

export interface ScenarioEvent {
  type: string;
  durability: Durability;
  /** 一句话解释（中文） */
  summary: string;
  /** 产生该事件的模块 id */
  node: string;
  seq?: number;
  /** 该事件需要等待用户决策（例如权限审批） */
  gate?: boolean;
}

export interface ToolOutput {
  name: string;
  input: string;
  status: "running" | "success" | "failed";
}

export interface OutputItem {
  phaseId: string;
  kind: "user" | "assistant" | "tool";
  text?: string;
  tool?: ToolOutput;
}

export interface PhaseDetail {
  /** 本阶段该模块接收什么 */
  input: string;
  /** 本阶段该模块输出什么 */
  output: string;
  /** 额外展示的技术细节（等宽字体块） */
  note?: string;
  files?: string[];
}

export interface Packet {
  from: string;
  to: string;
  label?: string;
}

export interface Phase {
  id: string;
  title: string;
  description: string;
  activeNodes: string[];
  completedNodes?: string[];
  packets: Packet[];
  events: ScenarioEvent[];
  output?: Omit<OutputItem, "phaseId">;
  details?: Record<string, PhaseDetail>;
}

export interface Scenario {
  command: string;
  phases: Phase[];
}
