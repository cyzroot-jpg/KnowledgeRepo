import { useCallback, useEffect, useMemo, useState } from "react";
import ArchitectureCanvas from "./components/ArchitectureCanvas";
import Controls from "./components/Controls";
import EventStream from "./components/EventStream";
import ModuleDrawer from "./components/ModuleDrawer";
import OutputPanel from "./components/OutputPanel";
import { usePlayback } from "./hooks/usePlayback";
import { useReducedMotion } from "./hooks/useReducedMotion";
import { LAYERS, findEdge } from "./modules";
import { DEFAULT_COMMAND, SAMPLE_COMMANDS, baseScenario, withCommand } from "./scenario";
import type { ScenarioEvent } from "./types";

export default function App() {
  const [command, setCommand] = useState<string>(DEFAULT_COMMAND);
  const [speed, setSpeed] = useState<number>(1);
  const [techView, setTechView] = useState<boolean>(true);
  const [followCamera, setFollowCamera] = useState<boolean>(true);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<{
    event: ScenarioEvent;
    key: string;
  } | null>(null);

  const reducedMotion = useReducedMotion();
  const scenario = useMemo(() => withCommand(baseScenario, command), [command]);
  const playback = usePlayback(scenario, speed);

  const phaseIndex = Math.min(playback.phaseIndex, scenario.phases.length - 1);
  const currentPhase = scenario.phases[phaseIndex];

  const activeNodes = useMemo(
    () => currentPhase?.activeNodes ?? [],
    [currentPhase],
  );

  const doneNodes = useMemo(() => {
    const set = new Set<string>();
    for (let i = 0; i < phaseIndex; i += 1) {
      for (const id of scenario.phases[i].activeNodes ?? []) set.add(id);
    }
    for (const id of currentPhase?.completedNodes ?? []) set.add(id);
    return Array.from(set);
  }, [scenario, phaseIndex, currentPhase]);

  const activeEdgeIds = useMemo(() => {
    const packets = currentPhase?.packets ?? [];
    const ids: string[] = [];
    for (const packet of packets) {
      const edge = findEdge(packet.from, packet.to);
      if (edge && !ids.includes(edge.id)) ids.push(edge.id);
    }
    return ids;
  }, [currentPhase]);

  const run = useCallback(() => {
    setSelectedEvent(null);
    playback.replay();
  }, [playback]);

  // 键盘：空格播放/暂停，方向键单步
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }
      if (event.code === "Space") {
        event.preventDefault();
        playback.toggle();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        playback.stepForward();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        playback.stepBack();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [playback]);

  const onSelectEvent = useCallback((event: ScenarioEvent, key: string) => {
    setSelectedEvent((prev) => (prev && prev.key === key ? null : { event, key }));
  }, []);

  const focusNode = selectedEvent?.event.node ?? null;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>AI Agent 运行时架构演示器</h1>
          <p className="app-sub">
            从「用户输入命令」到「最终输出」，逐阶段演示事件是如何在模块之间流动的。
          </p>
        </div>
        <div className="legend">
          {LAYERS.map((layer) => (
            <span className="legend-item" key={layer.id}>
              <i style={{ background: layer.color }} />
              {layer.name}
            </span>
          ))}
        </div>
      </header>

      <section className="composer" aria-label="命令输入">
        <div className="composer-row">
          <input
            className="composer-input"
            value={command}
            placeholder="输入一条命令，例如：修复登录页点击没反应"
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") run();
            }}
          />
          <button type="button" className="btn btn-primary btn-run" onClick={run}>
            运行演示
          </button>
        </div>
        <div className="composer-chips">
          {SAMPLE_COMMANDS.map((sample) => (
            <button
              type="button"
              key={sample}
              className="chip"
              data-active={command === sample}
              onClick={() => setCommand(sample)}
            >
              {sample}
            </button>
          ))}
        </div>
        <p className="composer-note">
          当前输入会被当作 <code>user prompt</code> 处理：
          <span className="composer-preview">{command.trim() || "（空）"}</span>
        </p>
      </section>

      <Controls
        status={playback.status}
        speed={speed}
        techView={techView}
        followCamera={followCamera}
        onTogglePlay={playback.toggle}
        onStep={playback.stepForward}
        onReplay={run}
        onSpeedChange={setSpeed}
        onTechViewChange={setTechView}
        onFollowCameraChange={setFollowCamera}
      />

      <main className="stage-grid">
        <section className="panel canvas-panel" aria-label="架构图舞台">
          <ArchitectureCanvas
            activeNodes={activeNodes}
            doneNodes={doneNodes}
            activeEdgeIds={activeEdgeIds}
            packets={currentPhase?.packets ?? []}
            selectedNode={selectedNode}
            focusNode={focusNode}
            onSelectNode={setSelectedNode}
            followCamera={followCamera}
            reducedMotion={reducedMotion}
          />
        </section>

        <EventStream
          phases={scenario.phases}
          currentIndex={phaseIndex}
          eventCursor={playback.eventCursor}
          techView={techView}
          selectedEventKey={selectedEvent?.key ?? null}
          awaiting={playback.status === "awaiting"}
          onSelectEvent={onSelectEvent}
          onSelectNode={setSelectedNode}
          onApprove={() => playback.resolveApproval("allowed")}
          onDeny={() => playback.resolveApproval("denied")}
          onSeek={playback.seek}
        />
      </main>

      <OutputPanel
        outputs={playback.outputs}
        status={playback.status}
        speed={speed}
        reducedMotion={reducedMotion}
      />

      <ModuleDrawer
        moduleId={selectedNode}
        phase={currentPhase}
        techView={techView}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}
