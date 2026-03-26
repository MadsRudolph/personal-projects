import { useState } from 'react';
import type { WaveGenSettings, Waveform } from '../hooks/useWaveGen';
import Knob from './Knob';

interface WaveGenDrawerProps {
  settings: WaveGenSettings;
  onUpdate: (partial: Partial<WaveGenSettings>) => void;
  onToggle: () => void;
  connected: boolean;
}

const waveforms: { type: Waveform; icon: string; label: string }[] = [
  { type: 'sine', icon: '∿', label: 'Sine' },
  { type: 'square', icon: '⊓', label: 'Square' },
  { type: 'triangle', icon: '△', label: 'Triangle' },
  { type: 'sawtooth', icon: '⩘', label: 'Saw' },
];

function Section({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: '8px 0',
        borderBottom: '1px solid var(--border)',
      }}
    >
      {children}
    </div>
  );
}

function Checkbox({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (v: boolean) => void;
}) {
  return (
    <label
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 11,
        color: 'var(--text-secondary)',
        fontFamily: 'var(--font-sans)',
        cursor: 'pointer',
      }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{ accentColor: 'var(--accent)' }}
      />
      {label}
    </label>
  );
}

export default function WaveGenDrawer({
  settings,
  onUpdate,
  onToggle,
  connected,
}: WaveGenDrawerProps) {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        position: 'absolute',
        right: 0,
        top: 0,
        bottom: 0,
        width: open ? 280 : 40,
        transition: 'width 0.25s ease',
        display: 'flex',
        flexDirection: 'row',
        zIndex: 10,
      }}
    >
      {/* Toggle tab */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          position: 'absolute',
          left: -28,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 28,
          height: 80,
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          borderRight: 'none',
          borderRadius: '6px 0 0 6px',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          writingMode: 'vertical-rl',
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          letterSpacing: '0.1em',
          padding: 0,
        }}
      >
        AWG
      </button>

      {/* Drawer body */}
      <div
        style={{
          flex: 1,
          background: 'var(--bg-secondary)',
          borderLeft: '1px solid var(--border)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {open && (
          <div
            style={{
              width: 280,
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              overflowY: 'auto',
              flex: 1,
            }}
          >
            {/* Header */}
            <Section>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    fontFamily: 'var(--font-sans)',
                    color: 'var(--text-primary)',
                  }}
                >
                  Wave Gen
                </span>
                <button
                  onClick={onToggle}
                  disabled={!connected}
                  style={{
                    padding: '4px 12px',
                    borderRadius: 4,
                    border: 'none',
                    fontSize: 10,
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 600,
                    cursor: connected ? 'pointer' : 'not-allowed',
                    background: settings.enabled
                      ? 'var(--danger)'
                      : 'var(--success)',
                    color: '#fff',
                    opacity: connected ? 1 : 0.5,
                  }}
                >
                  {settings.enabled ? 'OUTPUT ON' : 'OUTPUT OFF'}
                </button>
              </div>
            </Section>

            {/* Waveform selector */}
            <Section>
              <div style={{ display: 'flex', gap: 4 }}>
                {waveforms.map((w) => (
                  <button
                    key={w.type}
                    onClick={() => onUpdate({ waveform: w.type })}
                    title={w.label}
                    style={{
                      flex: 1,
                      padding: '6px 0',
                      borderRadius: 4,
                      border:
                        settings.waveform === w.type
                          ? '1px solid var(--accent)'
                          : '1px solid var(--border)',
                      background:
                        settings.waveform === w.type
                          ? 'rgba(99, 102, 241, 0.15)'
                          : 'var(--bg-tertiary)',
                      color:
                        settings.waveform === w.type
                          ? 'var(--accent)'
                          : 'var(--text-secondary)',
                      fontSize: 18,
                      cursor: 'pointer',
                      fontFamily: 'sans-serif',
                      lineHeight: 1,
                    }}
                  >
                    {w.icon}
                  </button>
                ))}
              </div>
            </Section>

            {/* Main knobs: Freq, Amp, Offset */}
            <Section>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-around',
                  gap: 4,
                }}
              >
                <Knob
                  label="Freq"
                  unit="Hz"
                  value={settings.frequency}
                  min={1}
                  max={25e6}
                  logarithmic
                  onChange={(v) => onUpdate({ frequency: v })}
                />
                <Knob
                  label="Amp"
                  unit="V"
                  value={settings.amplitude}
                  min={0.001}
                  max={5}
                  logarithmic
                  onChange={(v) => onUpdate({ amplitude: v })}
                />
                <Knob
                  label="Offset"
                  unit="V"
                  value={settings.offset}
                  min={-5}
                  max={5}
                  onChange={(v) => onUpdate({ offset: v })}
                />
              </div>
            </Section>

            {/* Duty cycle (square only) */}
            {settings.waveform === 'square' && (
              <Section>
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <Knob
                    label="Duty"
                    unit="%"
                    value={settings.dutyCycle}
                    min={1}
                    max={99}
                    onChange={(v) => onUpdate({ dutyCycle: Math.round(v) })}
                  />
                </div>
              </Section>
            )}

            {/* Sweep */}
            <Section>
              <Checkbox
                checked={settings.sweepEnabled}
                label="Sweep"
                onChange={(v) => onUpdate({ sweepEnabled: v })}
              />
              {settings.sweepEnabled && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-around',
                    marginTop: 8,
                    gap: 4,
                  }}
                >
                  <Knob
                    label="Start"
                    unit="Hz"
                    value={settings.sweepStart}
                    min={1}
                    max={25e6}
                    logarithmic
                    onChange={(v) => onUpdate({ sweepStart: v })}
                  />
                  <Knob
                    label="Stop"
                    unit="Hz"
                    value={settings.sweepStop}
                    min={1}
                    max={25e6}
                    logarithmic
                    onChange={(v) => onUpdate({ sweepStop: v })}
                  />
                  <Knob
                    label="Time"
                    unit="s"
                    value={settings.sweepTime}
                    min={0.001}
                    max={100}
                    logarithmic
                    onChange={(v) => onUpdate({ sweepTime: v })}
                  />
                </div>
              )}
            </Section>

            {/* AM */}
            <Section>
              <Checkbox
                checked={settings.amEnabled}
                label="AM Modulation"
                onChange={(v) => onUpdate({ amEnabled: v })}
              />
              {settings.amEnabled && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-around',
                    marginTop: 8,
                    gap: 4,
                  }}
                >
                  <Knob
                    label="AM Freq"
                    unit="Hz"
                    value={settings.amFrequency}
                    min={1}
                    max={1e6}
                    logarithmic
                    onChange={(v) => onUpdate({ amFrequency: v })}
                  />
                  <Knob
                    label="Depth"
                    unit="%"
                    value={settings.amDepth}
                    min={0}
                    max={100}
                    onChange={(v) => onUpdate({ amDepth: v })}
                  />
                </div>
              )}
            </Section>

            {/* FM */}
            <Section>
              <Checkbox
                checked={settings.fmEnabled}
                label="FM Modulation"
                onChange={(v) => onUpdate({ fmEnabled: v })}
              />
              {settings.fmEnabled && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-around',
                    marginTop: 8,
                    gap: 4,
                  }}
                >
                  <Knob
                    label="FM Freq"
                    unit="Hz"
                    value={settings.fmFrequency}
                    min={1}
                    max={1e6}
                    logarithmic
                    onChange={(v) => onUpdate({ fmFrequency: v })}
                  />
                  <Knob
                    label="Dev"
                    unit="Hz"
                    value={settings.fmDeviation}
                    min={1}
                    max={1e6}
                    logarithmic
                    onChange={(v) => onUpdate({ fmDeviation: v })}
                  />
                </div>
              )}
            </Section>

            {/* DC Output */}
            <Section>
              <Checkbox
                checked={settings.dcOutput}
                label="DC Output"
                onChange={(v) => onUpdate({ dcOutput: v })}
              />
              {settings.dcOutput && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    marginTop: 8,
                  }}
                >
                  <Knob
                    label="DC"
                    unit="V"
                    value={settings.dcVoltage}
                    min={-5}
                    max={5}
                    onChange={(v) => onUpdate({ dcVoltage: v })}
                  />
                </div>
              )}
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}
