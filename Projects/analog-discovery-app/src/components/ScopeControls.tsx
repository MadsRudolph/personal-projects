import type { CSSProperties } from 'react';

const TIME_STEPS = [
  1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6, 200e-6, 500e-6,
  1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3,
];

const VOLT_STEPS = [
  0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5,
];

function formatTime(s: number): string {
  if (s >= 0.001) return `${(s * 1000).toFixed(0)}ms`;
  return `${(s * 1e6).toFixed(0)}\u00b5s`;
}

function formatVolts(v: number): string {
  if (v >= 1) return `${v}V`;
  return `${(v * 1000).toFixed(0)}mV`;
}

function cycleStep(steps: number[], current: number, dir: 1 | -1): number {
  let closest = 0;
  let minDist = Infinity;
  for (let i = 0; i < steps.length; i++) {
    const d = Math.abs(steps[i] - current);
    if (d < minDist) {
      minDist = d;
      closest = i;
    }
  }
  const next = closest + dir;
  if (next < 0 || next >= steps.length) return steps[closest];
  return steps[next];
}

const btnStyle: CSSProperties = {
  background: 'var(--bg-tertiary)',
  border: '1px solid var(--border)',
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  padding: '2px 6px',
  borderRadius: 3,
  cursor: 'pointer',
  lineHeight: '18px',
};

const valStyle: CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  minWidth: 52,
  textAlign: 'center',
};

const groupStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 2,
};

const labelStyle: CSSProperties = {
  fontSize: 10,
  color: 'var(--text-secondary)',
  fontFamily: 'var(--font-sans)',
  marginRight: 2,
};

interface ScopeControlsProps {
  timePerDiv: number;
  ch1Range: number;
  ch2Range: number;
  ch1Enabled: boolean;
  ch2Enabled: boolean;
  triggerMode: 'auto' | 'normal' | 'single';
  triggerEdge: 'rising' | 'falling';
  onUpdate: (updates: Record<string, unknown>) => void;
}

export default function ScopeControls({
  timePerDiv,
  ch1Range,
  ch2Range,
  ch1Enabled,
  ch2Enabled,
  triggerMode,
  triggerEdge,
  onUpdate,
}: ScopeControlsProps) {
  const ch1VDiv = ch1Range / 8;
  const ch2VDiv = ch2Range / 8;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {/* Time/div */}
      <div style={groupStyle}>
        <span style={labelStyle}>T/div</span>
        <button style={btnStyle} onClick={() => onUpdate({ timePerDiv: cycleStep(TIME_STEPS, timePerDiv, -1) })}>-</button>
        <span style={{ ...valStyle, color: 'var(--text-primary)' }}>{formatTime(timePerDiv)}</span>
        <button style={btnStyle} onClick={() => onUpdate({ timePerDiv: cycleStep(TIME_STEPS, timePerDiv, 1) })}>+</button>
      </div>

      {/* CH1 V/div */}
      <div style={groupStyle}>
        <button
          style={{
            ...btnStyle,
            color: 'var(--ch1)',
            background: ch1Enabled ? 'rgba(0, 229, 255, 0.15)' : 'var(--bg-tertiary)',
            borderColor: ch1Enabled ? 'var(--ch1)' : 'var(--border)',
          }}
          onClick={() => onUpdate({ ch1Enabled: !ch1Enabled })}
        >
          CH1
        </button>
        {ch1Enabled && (
          <>
            <button style={btnStyle} onClick={() => onUpdate({ ch1Range: cycleStep(VOLT_STEPS, ch1VDiv, -1) * 8 })}>-</button>
            <span style={{ ...valStyle, color: 'var(--ch1)' }}>{formatVolts(ch1VDiv)}/d</span>
            <button style={btnStyle} onClick={() => onUpdate({ ch1Range: cycleStep(VOLT_STEPS, ch1VDiv, 1) * 8 })}>+</button>
          </>
        )}
      </div>

      {/* CH2 V/div */}
      <div style={groupStyle}>
        <button
          style={{
            ...btnStyle,
            color: 'var(--ch2)',
            background: ch2Enabled ? 'rgba(255, 0, 229, 0.15)' : 'var(--bg-tertiary)',
            borderColor: ch2Enabled ? 'var(--ch2)' : 'var(--border)',
          }}
          onClick={() => onUpdate({ ch2Enabled: !ch2Enabled })}
        >
          CH2
        </button>
        {ch2Enabled && (
          <>
            <button style={btnStyle} onClick={() => onUpdate({ ch2Range: cycleStep(VOLT_STEPS, ch2VDiv, -1) * 8 })}>-</button>
            <span style={{ ...valStyle, color: 'var(--ch2)' }}>{formatVolts(ch2VDiv)}/d</span>
            <button style={btnStyle} onClick={() => onUpdate({ ch2Range: cycleStep(VOLT_STEPS, ch2VDiv, 1) * 8 })}>+</button>
          </>
        )}
      </div>

      {/* Trigger mode */}
      <div style={groupStyle}>
        <span style={labelStyle}>Trig</span>
        {(['auto', 'normal', 'single'] as const).map((m) => (
          <button
            key={m}
            style={{
              ...btnStyle,
              background: triggerMode === m ? 'var(--trigger)' : 'var(--bg-tertiary)',
              color: triggerMode === m ? '#fff' : 'var(--text-secondary)',
              borderColor: triggerMode === m ? 'var(--trigger)' : 'var(--border)',
            }}
            onClick={() => onUpdate({ triggerMode: m })}
          >
            {m[0].toUpperCase()}
          </button>
        ))}
      </div>

      {/* Trigger edge */}
      <button
        style={{
          ...btnStyle,
          color: 'var(--trigger)',
          fontSize: 13,
          padding: '2px 8px',
        }}
        onClick={() => onUpdate({ triggerEdge: triggerEdge === 'rising' ? 'falling' : 'rising' })}
      >
        {triggerEdge === 'rising' ? '\u2191' : '\u2193'}
      </button>
    </div>
  );
}
