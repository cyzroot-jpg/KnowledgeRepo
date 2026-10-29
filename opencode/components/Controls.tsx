import type { PlaybackStatus } from "../hooks/usePlayback";

interface Props {
  status: PlaybackStatus;
  speed: number;
  techView: boolean;
  followCamera: boolean;
  onTogglePlay: () => void;
  onStep: () => void;
  onReplay: () => void;
  onSpeedChange: (speed: number) => void;
  onTechViewChange: (value: boolean) => void;
  onFollowCameraChange: (value: boolean) => void;
}

const SPEEDS: number[] = [0.5, 1, 2];

export default function Controls({
  status,
  speed,
  techView,
  followCamera,
  onTogglePlay,
  onStep,
  onReplay,
  onSpeedChange,
  onTechViewChange,
  onFollowCameraChange,
}: Props) {
  const playing = status === "playing";
  const finished = status === "done";

  return (
    <div className="controls" role="group" aria-label="播放控制">
      <div className="controls-cluster">
        <button
          type="button"
          className="btn btn-primary"
          onClick={onTogglePlay}
          disabled={finished || status === "awaiting"}
        >
          {playing ? "暂停" : "播放"}
        </button>
        <button type="button" className="btn" onClick={onStep} disabled={finished}>
          单步前进
        </button>
        <button type="button" className="btn" onClick={onReplay}>
          重播
        </button>
      </div>

      <div className="controls-cluster" role="group" aria-label="播放速度">
        <span className="controls-label">速度</span>
        {SPEEDS.map((value) => (
          <button
            type="button"
            key={value}
            className="btn btn-small"
            data-active={speed === value}
            onClick={() => onSpeedChange(value)}
          >
            {value}x
          </button>
        ))}
      </div>

      <div className="controls-cluster">
        <label className="switch" data-active={techView}>
          <input
            type="checkbox"
            checked={techView}
            onChange={(e) => onTechViewChange(e.target.checked)}
          />
          <span className="switch-track" aria-hidden="true">
            <span className="switch-thumb" />
          </span>
          <span className="switch-text">{techView ? "显示技术细节" : "产品视图"}</span>
        </label>
        <label className="switch" data-active={followCamera}>
          <input
            type="checkbox"
            checked={followCamera}
            onChange={(e) => onFollowCameraChange(e.target.checked)}
          />
          <span className="switch-track" aria-hidden="true">
            <span className="switch-thumb" />
          </span>
          <span className="switch-text">跟随镜头</span>
        </label>
      </div>

      <div className="controls-hint">
        键盘：空格 播放/暂停 · ← 后退一阶段 · → 单步前进
      </div>
    </div>
  );
}
