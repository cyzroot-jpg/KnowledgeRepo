import { useEffect, useState } from "react";
import type { OutputItem } from "../types";
import type { PlaybackStatus } from "../hooks/usePlayback";

interface Props {
  outputs: OutputItem[];
  status: PlaybackStatus;
  speed: number;
  reducedMotion: boolean;
}

const STATUS_TEXT: Record<string, string> = {
  running: "执行中",
  success: "成功",
  failed: "失败",
};

function TypedText({
  text,
  animate,
  speed,
}: {
  text: string;
  animate: boolean;
  speed: number;
}): JSX.Element {
  const [count, setCount] = useState<number>(animate ? 0 : text.length);

  useEffect(() => {
    if (!animate) {
      setCount(text.length);
      return;
    }
    setCount(0);
    let index = 0;
    const step = Math.max(1, Math.round(text.length / 90));
    const timer = window.setInterval(() => {
      index = Math.min(text.length, index + step);
      setCount(index);
      if (index >= text.length) window.clearInterval(timer);
    }, Math.max(12, 26 / Math.max(0.25, speed)));
    return () => window.clearInterval(timer);
  }, [text, animate, speed]);

  return (
    <span className="typed">
      {text.slice(0, count)}
      {count < text.length ? <span className="caret" /> : null}
    </span>
  );
}

export default function OutputPanel({ outputs, status, speed, reducedMotion }: Props) {
  const lastIndex = outputs.length - 1;

  return (
    <section className="output" aria-label="输出面板">
      <header className="output-head">
        <h2>输出</h2>
        <span className="output-status" data-status={status}>
          {status === "idle"
            ? "未开始"
            : status === "playing"
              ? "执行中"
              : status === "paused"
                ? "已暂停"
                : status === "awaiting"
                  ? "等待审批"
                  : "会话 idle"}
        </span>
      </header>

      <div className="output-body">
        {outputs.length === 0 ? (
          <p className="output-empty">运行演示后，助手回复与工具调用会在这里逐字出现。</p>
        ) : null}

        {outputs.map((item, index) => {
          const animate = !reducedMotion && status === "playing" && index === lastIndex;
          if (item.kind === "user") {
            return (
              <div className="bubble bubble-user" key={`${item.phaseId}-${index}`}>
                <span className="bubble-role">用户</span>
                <p>{item.text ?? ""}</p>
              </div>
            );
          }
          if (item.kind === "assistant") {
            return (
              <div className="bubble bubble-assistant" key={`${item.phaseId}-${index}`}>
                <span className="bubble-role">助手</span>
                <p>
                  <TypedText text={item.text ?? ""} animate={animate} speed={speed} />
                </p>
              </div>
            );
          }
          const tool = item.tool;
          const statusText = tool ? STATUS_TEXT[tool.status] ?? tool.status : "";
          return (
            <div className="tool-card" key={`${item.phaseId}-${index}`} data-status={tool?.status}>
              <div className="tool-head">
                <span className="tool-name">{tool?.name ?? "tool"}</span>
                <span className="tool-status" data-status={tool?.status}>
                  {statusText}
                </span>
              </div>
              <code className="tool-input">{tool?.input ?? ""}</code>
            </div>
          );
        })}

        {status === "done" ? (
          <div className="idle-badge">
            <span className="idle-dot" />
            会话进入 idle · 所有事件已投影到客户端
          </div>
        ) : null}
      </div>
    </section>
  );
}
