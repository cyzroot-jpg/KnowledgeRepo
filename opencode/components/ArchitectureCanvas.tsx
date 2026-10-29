import { useEffect, useMemo, useRef, useState } from "react";
import type { Packet } from "../types";
import {
  EDGES,
  LAYOUT,
  MODULES,
  buildEdgePath,
  edgeLabelPosition,
  getModule,
} from "../modules";

interface Props {
  activeNodes: string[];
  doneNodes: string[];
  activeEdgeIds: string[];
  packets: Packet[];
  selectedNode: string | null;
  focusNode: string | null;
  onSelectNode: (id: string) => void;
  followCamera: boolean;
  reducedMotion: boolean;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export default function ArchitectureCanvas({
  activeNodes,
  doneNodes,
  activeEdgeIds,
  packets,
  selectedNode,
  focusNode,
  onSelectNode,
  followCamera,
  reducedMotion,
}: Props) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const update = (): void => {
      const width = el.clientWidth;
      if (width <= 0) return;
      setScale(clamp(width / LAYOUT.width, LAYOUT.minScale, 1));
    };
    update();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const activeKey = activeNodes.join(",");

  // 跟随镜头：把当前活跃节点滚到可视区域中央
  useEffect(() => {
    if (!followCamera) return;
    const container = scrollRef.current;
    const firstId = activeNodes[0];
    if (!container || !firstId) return;
    const node = getModule(firstId);
    if (!node) return;
    const left = clamp(
      node.x * scale - container.clientWidth / 2,
      0,
      Math.max(0, container.scrollWidth - container.clientWidth),
    );
    const top = clamp(
      node.y * scale - container.clientHeight / 2,
      0,
      Math.max(0, container.scrollHeight - container.clientHeight),
    );
    container.scrollTo({
      left,
      top,
      behavior: reducedMotion ? "auto" : "smooth",
    });
    // activeKey 代表当前活跃节点集合，避免数组引用变化导致重复执行
  }, [activeKey, followCamera, reducedMotion, scale]);

  const activeEdgeSet = useMemo(() => new Set(activeEdgeIds), [activeEdgeIds]);
  const activeNodeSet = useMemo(() => new Set(activeNodes), [activeNodes]);
  const doneSet = useMemo(() => new Set(doneNodes), [doneNodes]);
  const packetLabel = useMemo(() => {
    const map = new Map<string, string>();
    for (const p of packets) {
      map.set(`${p.from}->${p.to}`, p.label ?? "");
      map.set(`${p.to}->${p.from}`, p.label ?? "");
    }
    return map;
  }, [packets]);

  const paths = useMemo(
    () => EDGES.map((edge) => ({ edge, d: buildEdgePath(edge) })),
    [],
  );

  return (
    <div className="canvas" ref={wrapRef}>
      <div
        className="canvas-scroll"
        ref={scrollRef}
        style={{ height: LAYOUT.height * scale }}
      >
        <div
          className="canvas-stage"
          style={{
            width: LAYOUT.width,
            height: LAYOUT.height,
            transform: `scale(${scale})`,
          }}
        >
          <svg
            className="canvas-edges"
            width={LAYOUT.width}
            height={LAYOUT.height}
            viewBox={`0 0 ${LAYOUT.width} ${LAYOUT.height}`}
            aria-hidden="true"
          >
            <defs>
              <marker
                id="arrow-active"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
              </marker>
            </defs>
            {paths.map(({ edge, d }) => {
              const active = activeEdgeSet.has(edge.id);
              const label = packetLabel.get(edge.id) || edge.transport || "";
              const pos = edgeLabelPosition(edge);
              return (
                <g
                  key={edge.id}
                  className={active ? "edge is-active" : "edge"}
                  data-layer={getModule(edge.from)?.layer ?? "session"}
                >
                  <path id={`edge-path-${edge.id}`} d={d} markerEnd={active ? "url(#arrow-active)" : undefined} />
                  {active && !reducedMotion ? (
                    <circle className="packet" r={5}>
                      <animateMotion
                        dur="1.9s"
                        repeatCount="indefinite"
                        path={d}
                        rotate="auto"
                        calcMode="linear"
                      />
                    </circle>
                  ) : null}
                  {active && label ? (
                    <text className="edge-label" x={pos.x} y={pos.y}>
                      {label}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </svg>

          {MODULES.map((node) => {
            const state = activeNodeSet.has(node.id)
              ? "active"
              : doneSet.has(node.id)
                ? "done"
                : "idle";
            return (
              <button
                type="button"
                key={node.id}
                className="node"
                data-layer={node.layer}
                data-state={state}
                data-selected={selectedNode === node.id}
                data-focus={focusNode === node.id}
                style={{
                  left: node.x - LAYOUT.nodeW / 2,
                  top: node.y - LAYOUT.nodeH / 2,
                  width: LAYOUT.nodeW,
                  height: LAYOUT.nodeH,
                }}
                onClick={() => onSelectNode(node.id)}
                title={node.role}
              >
                <span className="node-head">
                  <span className="node-code">{node.short}</span>
                  <span className="node-name">{node.name}</span>
                  {state === "done" ? <span className="node-check">✓</span> : null}
                </span>
                <span className="node-role">{node.role}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
