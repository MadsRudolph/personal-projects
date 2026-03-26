import type { CSSProperties } from 'react';
import type { ScopeData } from '../hooks/useScopeState';

interface MeasurementsProps {
  data: ScopeData | null;
  ch1Enabled: boolean;
  ch2Enabled: boolean;
}

const container: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 16,
  background: 'var(--bg-secondary)',
  borderRadius: 6,
  padding: '5px 12px',
  border: '1px solid var(--border)',
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  flexShrink: 0,
  minHeight: 28,
};

const dimStyle: CSSProperties = {
  color: 'var(--text-dim)',
  fontSize: 11,
};

function formatV(v: number): string {
  if (Math.abs(v) >= 1) return `${v.toFixed(2)}V`;
  return `${(v * 1000).toFixed(1)}mV`;
}

function formatFreq(f: number): string {
  if (f >= 1e6) return `${(f / 1e6).toFixed(2)}MHz`;
  if (f >= 1e3) return `${(f / 1e3).toFixed(2)}kHz`;
  return `${f.toFixed(1)}Hz`;
}

export default function Measurements({ data, ch1Enabled, ch2Enabled }: MeasurementsProps) {
  if (!data) {
    return (
      <div style={container}>
        <span style={dimStyle}>No data</span>
      </div>
    );
  }

  const m = data.measurements;

  return (
    <div style={container}>
      {ch1Enabled && m?.ch1 && (
        <div style={{ display: 'flex', gap: 12 }}>
          <span style={{ color: 'var(--ch1)', fontWeight: 600 }}>CH1</span>
          <span style={{ color: 'var(--ch1)' }}>Vpp {formatV(m.ch1.vpp)}</span>
          <span style={{ color: 'var(--ch1)' }}>f {formatFreq(m.ch1.frequency)}</span>
          <span style={{ color: 'var(--ch1)' }}>{'\u00b5'} {formatV(m.ch1.mean)}</span>
        </div>
      )}
      {ch2Enabled && m?.ch2 && (
        <div style={{ display: 'flex', gap: 12 }}>
          <span style={{ color: 'var(--ch2)', fontWeight: 600 }}>CH2</span>
          <span style={{ color: 'var(--ch2)' }}>Vpp {formatV(m.ch2.vpp)}</span>
          <span style={{ color: 'var(--ch2)' }}>f {formatFreq(m.ch2.frequency)}</span>
        </div>
      )}
      {!ch1Enabled && !ch2Enabled && <span style={dimStyle}>No channels enabled</span>}
    </div>
  );
}
