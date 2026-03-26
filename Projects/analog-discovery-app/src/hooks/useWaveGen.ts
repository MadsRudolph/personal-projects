import { useState, useCallback, useRef } from 'react';

const API = 'http://127.0.0.1:8765';

export type Waveform = 'sine' | 'square' | 'triangle' | 'sawtooth';

export interface WaveGenSettings {
  enabled: boolean;
  waveform: Waveform;
  frequency: number;
  amplitude: number;
  offset: number;
  dutyCycle: number;
  sweepEnabled: boolean;
  sweepStart: number;
  sweepStop: number;
  sweepTime: number;
  amEnabled: boolean;
  amFrequency: number;
  amDepth: number;
  fmEnabled: boolean;
  fmFrequency: number;
  fmDeviation: number;
  dcOutput: boolean;
  dcVoltage: number;
}

const defaults: WaveGenSettings = {
  enabled: false,
  waveform: 'sine',
  frequency: 1000,
  amplitude: 1.0,
  offset: 0,
  dutyCycle: 50,
  sweepEnabled: false,
  sweepStart: 100,
  sweepStop: 10000,
  sweepTime: 1,
  amEnabled: false,
  amFrequency: 100,
  amDepth: 50,
  fmEnabled: false,
  fmFrequency: 100,
  fmDeviation: 1000,
  dcOutput: false,
  dcVoltage: 0,
};

function camelToSnake(key: string): string {
  return key.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase());
}

async function apiPost(path: string, body?: Record<string, unknown>) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function useWaveGen() {
  const [settings, setSettings] = useState<WaveGenSettings>(defaults);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const update = useCallback((partial: Partial<WaveGenSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...partial };
      const body: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(next)) {
        if (k === 'enabled') continue;
        body[camelToSnake(k)] = v;
      }
      apiPost('/wavegen/configure', body).catch((e) =>
        console.error('WaveGen configure failed:', e),
      );
      return next;
    });
  }, []);

  const toggleOutput = useCallback(async () => {
    const wasEnabled = settingsRef.current.enabled;
    try {
      await apiPost(wasEnabled ? '/wavegen/disable' : '/wavegen/enable');
      setSettings((prev) => ({ ...prev, enabled: !wasEnabled }));
    } catch (e) {
      console.error('WaveGen toggle failed:', e);
    }
  }, []);

  return { settings, update, toggleOutput };
}
