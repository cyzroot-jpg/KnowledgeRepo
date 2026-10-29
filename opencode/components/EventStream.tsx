import type { Phase, ScenarioEvent } from "../types";
import { getModule } from "../modules";

interface Props {
  phases: Phase[];
  currentIndex: number;
  eventCursor: number;
  techView: boolean;
  selectedEventKey: string | null;
  awaiting: boolean;
  onSelectEvent: (event: ScenarioEvent, key: string) => void;
  onSelectNode: (id: string) => void;
  onApprove: () => void;
  onDeny: () => void;
  onSeek: (index: number) => void;
}

function durabilityLabel(durability: ScenarioEvent["durability"]): string {
  if (durability === "durable") return "durable";
  if (durability === "ephemeral") return "ephemeral";
  return "internal";
}

export default function EventStream({
  phases,
  currentIndex,
  eventCursor,
  techView,
  selectedEventKey,
  awaiting,
  onSelectEvent,
  onSelectNode,
  onApprove,
  onDeny,
  onSeek,
}: Props) {
  const current = phases[currentIndex];

  return (
    <section className="stream" aria-label="事件流面板">
      <div className="stream-head">
        <div className="phase-nav" role="tablist" aria-label="阶段导航">
          {phases.map((phase, index) => (
            <button
              type="button"
              key={phase.id}
              role="tab"
              aria-selected={index === currentIndex}
              className="phase-dot"
              data-state={
                index === currentIndex ? "current" : index < currentIndex ? "done" : "todo"
              }
              onClick={() => onSeek(index)}
              title={phase.title}
            >
              {index + 1}
            </button>
          ))}
        </div>
        <h2 className="stream-title">{current?.title ?? "演示结束"}</h2>
        <p className="stream-desc">{current?.description ?? "所有阶段已播放完毕。"}</p>
      </div>

      <div className="stream-list">
        {phases.map((phase, index) => {
          if (index > currentIndex) return null;
          const visible = index === currentIndex ? eventCursor : phase.events.length;
          return (
            <div className="stream-group" key={phase.id}>
              <div className="stream-group-head">
                <span className="stream-group-index">{index + 1}</span>
                <span className="stream-group-title">{phase.title.replace(/^阶段 \d+ · /, "")}</span>
              </div>
              {phase.events.length === 0 ? (
                <p className="stream-empty">本阶段没有事件（模块内部工作）</p>
              ) : null}
              {phase.events.slice(0, visible).map((event, eventIndex) => {
                const key = `${phase.id}-${eventIndex}`;
                const module = getModule(event.node);
                const selected = selectedEventKey === key;
                return (
                  <button
                    type="button"
                    key={key}
                    className="event-row"
                    data-selected={selected}
                    data-durability={event.durability}
                    onClick={() => onSelectEvent(event, key)}
                  >
                    <span className="event-row-top">
                      {techView ? (
                        <code className="event-type">{event.type}</code>
                      ) : (
                        <span className="event-summary">{event.summary}</span>
                      )}
                      {techView ? (
                        <span className="tag" data-durability={event.durability}>
                          {durabilityLabel(event.durability)}
                        </span>
                      ) : null}
                    </span>
                    <span className="event-row-bottom">
                      <span className="event-module" data-layer={module?.layer ?? "session"}>
                        {module?.name ?? event.node}
                      </span>
                      {techView && event.seq !== undefined ? (
                        <span className="event-seq">#{event.seq}</span>
                      ) : null}
                      {!techView ? (
                        <span className="event-hint">{event.summary}</span>
                      ) : null}
                    </span>
                    {selected ? (
                      <span className="event-detail">
                        <span className="event-detail-text">{event.summary}</span>
                        <span
                          className="event-detail-link"
                          role="link"
                          tabIndex={0}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectNode(event.node);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.stopPropagation();
                              onSelectNode(event.node);
                            }
                          }}
                        >
                          查看模块 {module?.name ?? event.node} →
                        </span>
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          );
        })}

        {awaiting ? (
          <div className="approval">
            <p className="approval-title">permission.asked · 这个工具需要你批准</p>
            <div className="approval-actions">
              <button type="button" className="btn btn-approve" onClick={onApprove}>
                允许
              </button>
              <button type="button" className="btn btn-deny" onClick={onDeny}>
                拒绝
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
