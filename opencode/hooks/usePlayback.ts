import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { OutputItem, Scenario } from "../types";

export type PlaybackStatus = "idle" | "playing" | "paused" | "awaiting" | "done";

/** 每个事件出现的间隔（会被倍速缩放） */
const EVENT_DELAY = 700;
const EPHEMERAL_DELAY = 460;
const OUTPUT_DELAY = 420;
/** 阶段之间的停顿，对应验收要求的 600–900ms */
const PHASE_GAP = 820;

export interface Playback {
  status: PlaybackStatus;
  phaseIndex: number;
  eventCursor: number;
  outputs: OutputItem[];
  approval: "allowed" | "denied" | null;
  /** 因为拒绝权限而中断 */
  denied: boolean;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  stepForward: () => void;
  stepBack: () => void;
  replay: () => void;
  seek: (index: number) => void;
  resolveApproval: (result: "allowed" | "denied") => void;
}

function outputsBefore(scenario: Scenario, index: number): OutputItem[] {
  const list: OutputItem[] = [];
  for (let i = 0; i < index && i < scenario.phases.length; i += 1) {
    const phase = scenario.phases[i];
    if (phase.output) {
      list.push({ ...phase.output, phaseId: phase.id });
    }
  }
  return list;
}

/**
 * 演示播放控制：阶段 -> 事件 -> 输出 -> 下一阶段。
 * 所有定时器都由 effect 统一管理，暂停 / 重播 / 卸载时会正确清理。
 */
export function usePlayback(scenario: Scenario, speed: number): Playback {
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [eventCursor, setEventCursor] = useState(0);
  const [applied, setApplied] = useState<string[]>([]);
  const [outputs, setOutputs] = useState<OutputItem[]>([]);
  const [status, setStatus] = useState<PlaybackStatus>("idle");
  const [approval, setApproval] = useState<"allowed" | "denied" | null>(null);
  const [denied, setDenied] = useState(false);

  // 命令文本变化时同步已经产生的输出（流程本身不变）
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;

  const totalPhases = scenario.phases.length;
  const delay = useCallback((base: number) => base / Math.max(0.25, speed), [speed]);

  useEffect(() => {
    if (status !== "playing") return;
    const phase = scenarioRef.current.phases[phaseIndex];
    if (!phase) {
      setStatus("done");
      return;
    }

    if (eventCursor < phase.events.length) {
      const event = phase.events[eventCursor];
      const wait = delay(event.durability === "ephemeral" ? EPHEMERAL_DELAY : EVENT_DELAY);
      const timer = window.setTimeout(() => {
        setEventCursor((c) => c + 1);
        if (event.gate) setStatus("awaiting");
      }, wait);
      return () => window.clearTimeout(timer);
    }

    if (phase.output && !applied.includes(phase.id)) {
      const timer = window.setTimeout(() => {
        setOutputs((prev) => [...prev, { ...phase.output!, phaseId: phase.id }]);
        setApplied((prev) => [...prev, phase.id]);
      }, delay(OUTPUT_DELAY));
      return () => window.clearTimeout(timer);
    }

    const timer = window.setTimeout(() => {
      if (phaseIndex >= scenarioRef.current.phases.length - 1) {
        setStatus("done");
      } else {
        setPhaseIndex((i) => i + 1);
        setEventCursor(0);
      }
    }, delay(PHASE_GAP));
    return () => window.clearTimeout(timer);
  }, [status, phaseIndex, eventCursor, applied, delay]);

  const play = useCallback(() => {
    setStatus((prev) => {
      if (prev === "done") return prev;
      return "playing";
    });
  }, []);

  const pause = useCallback(() => {
    setStatus((prev) => (prev === "playing" ? "paused" : prev));
  }, []);

  const toggle = useCallback(() => {
    setStatus((prev) => {
      if (prev === "playing") return "paused";
      if (prev === "done") return prev;
      return "playing";
    });
  }, []);

  const stepForward = useCallback(() => {
    const scenarioNow = scenarioRef.current;
    const phase = scenarioNow.phases[phaseIndex];
    if (!phase) {
      setStatus("done");
      return;
    }
    if (eventCursor < phase.events.length) {
      const event = phase.events[eventCursor];
      setEventCursor(eventCursor + 1);
      setStatus(event.gate ? "awaiting" : "paused");
      return;
    }
    if (phase.output && !applied.includes(phase.id)) {
      setOutputs((prev) => [...prev, { ...phase.output!, phaseId: phase.id }]);
      setApplied((prev) => [...prev, phase.id]);
      setStatus("paused");
      return;
    }
    if (phaseIndex >= scenarioNow.phases.length - 1) {
      setStatus("done");
      return;
    }
    setPhaseIndex(phaseIndex + 1);
    setEventCursor(0);
    setStatus("paused");
  }, [phaseIndex, eventCursor, applied]);

  const seek = useCallback(
    (index: number) => {
      const scenarioNow = scenarioRef.current;
      const target = Math.min(Math.max(index, 0), scenarioNow.phases.length - 1);
      setPhaseIndex(target);
      setEventCursor(0);
      setApplied(scenarioNow.phases.slice(0, target).map((p) => p.id));
      setOutputs(outputsBefore(scenarioNow, target));
      setApproval(null);
      setDenied(false);
      setStatus("paused");
    },
    [],
  );

  const stepBack = useCallback(() => {
    if (eventCursor > 0) {
      const scenarioNow = scenarioRef.current;
      setEventCursor(0);
      setApplied(scenarioNow.phases.slice(0, phaseIndex).map((p) => p.id));
      setOutputs(outputsBefore(scenarioNow, phaseIndex));
      setStatus("paused");
      return;
    }
    seek(phaseIndex - 1);
  }, [eventCursor, phaseIndex, seek]);

  const replay = useCallback(() => {
    setPhaseIndex(0);
    setEventCursor(0);
    setApplied([]);
    setOutputs([]);
    setApproval(null);
    setDenied(false);
    setStatus("playing");
  }, []);

  const resolveApproval = useCallback(
    (result: "allowed" | "denied") => {
      setApproval(result);
      if (result === "allowed") {
        setStatus("playing");
        return;
      }
      const scenarioNow = scenarioRef.current;
      const phase = scenarioNow.phases[phaseIndex];
      const items: OutputItem[] = [];
      if (phase) {
        setEventCursor(phase.events.length);
        if (phase.output && !applied.includes(phase.id)) {
          const out = phase.output;
          items.push({
            ...out,
            phaseId: phase.id,
            tool: out.tool ? { ...out.tool, status: "failed" } : undefined,
          });
          setApplied((prev) => [...prev, phase.id]);
        }
      }
      items.push({
        phaseId: "denied",
        kind: "assistant",
        text: "工具调用被拒绝，Runner 结束本次执行，会话回到 idle。",
      });
      setOutputs((prev) => [...prev, ...items]);
      setDenied(true);
      setStatus("done");
    },
    [phaseIndex, applied],
  );

  // 脚本被替换（例如改了命令文案）时，保证索引不会越界
  useEffect(() => {
    if (phaseIndex > totalPhases - 1) {
      setPhaseIndex(Math.max(0, totalPhases - 1));
      setEventCursor(0);
    }
  }, [phaseIndex, totalPhases]);

  return useMemo(
    () => ({
      status,
      phaseIndex,
      eventCursor,
      outputs,
      approval,
      denied,
      play,
      pause,
      toggle,
      stepForward,
      stepBack,
      replay,
      seek,
      resolveApproval,
    }),
    [
      status,
      phaseIndex,
      eventCursor,
      outputs,
      approval,
      denied,
      play,
      pause,
      toggle,
      stepForward,
      stepBack,
      replay,
      seek,
      resolveApproval,
    ],
  );
}
