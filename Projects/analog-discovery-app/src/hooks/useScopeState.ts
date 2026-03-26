import { useState, useCallback } from 'react';

const API = 'http://127.0.0.1:8765';

export interface ChannelMeasurements {
  vpp: number;
  mean: number;
  max: number;
  min: number;
  frequency: number;
}

export interface ScopeData {
  ch1: number[];
  ch2: number[];
  measurements: {
    ch1: ChannelMeasurements;
    ch2: ChannelMeasurements;
  };
  sample_rate: number;
  buffer_size: number;
}

export type MathMode = 'off' | 'add' | 'subtract';

export interface ScopeState {
  ch1Enabled: boolean;
  ch2Enabled: boolean;
  ch1Range: number;
  ch2Range: number;
  timePerDiv: number;
  triggerLevel: number;
  triggerSource: 'ch1' | 'ch2';
  triggerEdge: 'rising' | 'falling';
  triggerMode: 'auto' | 'normal' | 'single';
  running: boolean;
  connected: boolean;
  scopeData: ScopeData | null;
  mathMode: MathMode;
  cursorsVisible: boolean;
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

export function useScopeState() {
  const [state, setState] = useState<ScopeState>({
    ch1Enabled: true,
    ch2Enabled: true,
    ch1Range: 8, // 1V/div * 8
    ch2Range: 8,
    timePerDiv: 0.001, // 1ms
    triggerLevel: 0,
    triggerSource: 'ch1',
    triggerEdge: 'rising',
    triggerMode: 'auto',
    running: false,
    connected: false,
    scopeData: null,
    mathMode: 'off',
    cursorsVisible: false,
  });

  const setScopeData = useCallback((data: ScopeData) => {
    setState((prev) => ({ ...prev, scopeData: data }));
  }, []);

  const setMathMode = useCallback((mathMode: MathMode) => {
    setState((prev) => ({ ...prev, mathMode }));
  }, []);

  const setCursorsVisible = useCallback((cursorsVisible: boolean) => {
    setState((prev) => ({ ...prev, cursorsVisible }));
  }, []);

  const connect = useCallback(async () => {
    try {
      await apiPost('/connect');
      setState((prev) => ({ ...prev, connected: true }));
    } catch (e) {
      console.error('Connect failed:', e);
    }
  }, []);

  const disconnect = useCallback(async () => {
    try {
      await apiPost('/disconnect');
      setState((prev) => ({ ...prev, connected: false, running: false, scopeData: null }));
    } catch (e) {
      console.error('Disconnect failed:', e);
    }
  }, []);

  const updateSettings = useCallback(
    async (updates: Partial<Pick<ScopeState, 'ch1Enabled' | 'ch2Enabled' | 'ch1Range' | 'ch2Range' | 'timePerDiv' | 'triggerLevel' | 'triggerSource' | 'triggerEdge' | 'triggerMode'>>) => {
      setState((prev) => {
        const next = { ...prev, ...updates };
        const config = {
          ch1_enabled: next.ch1Enabled,
          ch2_enabled: next.ch2Enabled,
          ch1_range: next.ch1Range,
          ch2_range: next.ch2Range,
          time_per_div: next.timePerDiv,
          trigger_level: next.triggerLevel,
          trigger_source: next.triggerSource,
          trigger_edge: next.triggerEdge,
          trigger_mode: next.triggerMode,
        };
        apiPost('/scope/configure', config).catch((e) => console.error('Configure failed:', e));
        return next;
      });
    },
    [],
  );

  const startScope = useCallback(async () => {
    try {
      await apiPost('/scope/start');
      setState((prev) => ({ ...prev, running: true }));
    } catch (e) {
      console.error('Start failed:', e);
    }
  }, []);

  const stopScope = useCallback(async () => {
    try {
      await apiPost('/scope/stop');
      setState((prev) => ({ ...prev, running: false }));
    } catch (e) {
      console.error('Stop failed:', e);
    }
  }, []);

  const autoscale = useCallback(async () => {
    try {
      const result = await apiPost('/scope/autoscale');
      if (result) {
        setState((prev) => ({
          ...prev,
          ...(result.ch1_range != null && { ch1Range: result.ch1_range }),
          ...(result.ch2_range != null && { ch2Range: result.ch2_range }),
          ...(result.time_per_div != null && { timePerDiv: result.time_per_div }),
          ...(result.trigger_level != null && { triggerLevel: result.trigger_level }),
        }));
      }
    } catch (e) {
      console.error('Autoscale failed:', e);
    }
  }, []);

  return {
    ...state,
    setScopeData,
    setMathMode,
    setCursorsVisible,
    connect,
    disconnect,
    updateSettings,
    startScope,
    stopScope,
    autoscale,
  };
}
