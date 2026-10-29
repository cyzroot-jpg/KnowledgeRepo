import type { Phase, ScenarioEvent } from "../types";
import { LAYER_MAP, getModule } from "../modules";

interface Props {
  moduleId: string | null;
  phase: Phase | undefined;
  techView: boolean;
  onClose: () => void;
}

export default function ModuleDrawer({ moduleId, phase, techView, onClose }: Props) {
  if (!moduleId) return null;
  const node = getModule(moduleId);
  if (!node) return null;

  const layer = LAYER_MAP[node.layer];
  const detail = phase?.details?.[node.id];
  const relatedEvents: ScenarioEvent[] = (phase?.events ?? []).filter(
    (event) => event.node === node.id,
  );
  const isActive = phase?.activeNodes.includes(node.id) ?? false;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="drawer" aria-label={`${node.name} 详情`}>
        <header className="drawer-head">
          <div>
            <span className="drawer-code" data-layer={node.layer}>
              {node.short}
            </span>
            <h3>{node.name}</h3>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            关闭
          </button>
        </header>

        <p className="drawer-layer" style={{ color: layer.color }}>
          {layer.name} · {isActive ? "本阶段活跃" : "本阶段未参与"}
        </p>
        <p className="drawer-role">{node.role}</p>

        <section className="drawer-section">
          <h4>本阶段输入</h4>
          <p>{detail?.input ?? "本阶段不从该模块读取输入。"}</p>
        </section>

        <section className="drawer-section">
          <h4>本阶段输出</h4>
          <p>{detail?.output ?? "本阶段该模块没有对外输出。"}</p>
        </section>

        {detail?.note ? (
          <section className="drawer-section">
            <h4>技术细节</h4>
            <pre className="drawer-note">{detail.note}</pre>
          </section>
        ) : null}

        <section className="drawer-section">
          <h4>关联事件</h4>
          {relatedEvents.length === 0 ? (
            <p className="drawer-muted">本阶段没有由该模块产生的事件。</p>
          ) : (
            <ul className="drawer-events">
              {relatedEvents.map((event) => (
                <li key={event.type + String(event.seq ?? "")}>
                  {techView ? <code className="event-type">{event.type}</code> : null}
                  <span>{event.summary}</span>
                  <span className="tag" data-durability={event.durability}>
                    {event.durability}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {techView && node.files && node.files.length > 0 ? (
          <section className="drawer-section">
            <h4>关键文件</h4>
            <ul className="drawer-files">
              {node.files.map((file) => (
                <li key={file}>
                  <code>{file}</code>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </aside>
    </>
  );
}
