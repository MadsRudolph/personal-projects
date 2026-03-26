import type { CSSProperties } from 'react';
import type { MathMode } from '../hooks/useScopeState';
import ScopeControls from './ScopeControls';

interface TopBarProps {
  connected: boolean;
  running: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onStart: () => void;
  onStop: () => void;
  onAutoscale: () => void;
  timePerDiv: number;
  ch1Range: number;
  ch2Range: number;
  ch1Enabled: boolean;
  ch2Enabled: boolean;
  triggerMode: 'auto' | 'normal' | 'single';
  triggerEdge: 'rising' | 'falling';
  onUpdate: (updates: Record<string, unknown>) => void;
  cursorsVisible: boolean;
  onToggleCursors: () => void;
  mathMode: MathMode;
  onSetMathMode: (mode: MathMode) => void;
}

const actionBtn: CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 12,
  fontWeight: 500,
  padding: '4px 14px',
  borderRadius: 4,
  border: '1px solid transparent',
  cursor: 'pointer',
  transition: 'background 0.15s',
};

export default function TopBar({
  connected,
  running,
  onConnect,
  onDisconnect,
  onStart,
  onStop,
  onAutoscale,
  timePerDiv,
  ch1Range,
  ch2Range,
  ch1Enabled,
  ch2Enabled,
  triggerMode,
  triggerEdge,
  onUpdate,
  cursorsVisible,
  onToggleCursors,
  mathMode,
  onSetMathMode,
}: TopBarProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        background: 'var(--bg-secondary)',
        borderRadius: 6,
        padding: '6px 10px',
        border: '1px solid var(--border)',
        flexShrink: 0,
      }}
    >
      {/* Connect / Disconnect */}
      <button
        style={{
          ...actionBtn,
          background: connected ? 'var(--success)' : 'var(--accent)',
          color: '#fff',
        }}
        onClick={connected ? onDisconnect : onConnect}
      >
        {connected ? 'Disconnect' : 'Connect'}
      </button>

      {/* Run / Stop */}
      <button
        style={{
          ...actionBtn,
          background: running ? 'var(--danger)' : 'var(--success)',
          color: '#fff',
          opacity: connected ? 1 : 0.4,
          pointerEvents: connected ? 'auto' : 'none',
        }}
        onClick={running ? onStop : onStart}
        disabled={!connected}
      >
        {running ? 'Stop' : 'Run'}
      </button>

      {/* Autoscale */}
      <button
        style={{
          ...actionBtn,
          background: 'var(--bg-tertiary)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border)',
          opacity: connected ? 1 : 0.4,
          pointerEvents: connected ? 'auto' : 'none',
        }}
        onClick={onAutoscale}
        disabled={!connected}
      >
        Auto
      </button>

      {/* Separator */}
      <div
        style={{
          width: 1,
          height: 22,
          background: 'var(--border)',
          margin: '0 4px',
        }}
      />

      {/* Scope Controls */}
      <ScopeControls
        timePerDiv={timePerDiv}
        ch1Range={ch1Range}
        ch2Range={ch2Range}
        ch1Enabled={ch1Enabled}
        ch2Enabled={ch2Enabled}
        triggerMode={triggerMode}
        triggerEdge={triggerEdge}
        onUpdate={onUpdate}
      />

      {/* Separator */}
      <div style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 4px' }} />

      {/* Cursors toggle */}
      <button
        style={{
          ...actionBtn,
          background: cursorsVisible ? '#ffcc00' : 'var(--bg-tertiary)',
          color: cursorsVisible ? '#000' : 'var(--text-primary)',
          border: '1px solid var(--border)',
        }}
        onClick={onToggleCursors}
      >
        Cursors
      </button>

      {/* Math channel */}
      {(['add', 'subtract'] as const).map((mode) => (
        <button
          key={mode}
          style={{
            ...actionBtn,
            background: mathMode === mode ? '#ffcc00' : 'var(--bg-tertiary)',
            color: mathMode === mode ? '#000' : 'var(--text-primary)',
            border: '1px solid var(--border)',
          }}
          onClick={() => onSetMathMode(mathMode === mode ? 'off' : mode)}
        >
          {mode === 'add' ? 'Ch1+Ch2' : 'Ch1\u2212Ch2'}
        </button>
      ))}

    </div>
  );
}
