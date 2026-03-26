import { useCallback, useState } from 'react';
import { useScopeState } from './hooks/useScopeState';
import { useWebSocket } from './hooks/useWebSocket';
import { useWaveGen } from './hooks/useWaveGen';
import TopBar from './components/TopBar';
import ScopeView from './components/ScopeView';
import Measurements from './components/Measurements';
import WaveGenDrawer from './components/WaveGenDrawer';
import Cursors from './components/Cursors';

export default function App() {
  const scope = useScopeState();
  const { settings: waveGenSettings, update: updateWaveGen, toggleOutput } = useWaveGen();
  const [scopeSize, setScopeSize] = useState({ w: 0, h: 0 });

  const onData = useCallback(
    (data: unknown) => {
      scope.setScopeData(data as Parameters<typeof scope.setScopeData>[0]);
    },
    [scope.setScopeData],
  );

  useWebSocket({
    url: 'ws://127.0.0.1:8765/ws/scope',
    onData,
    enabled: scope.connected && scope.running,
  });

  const handleUpdate = useCallback(
    (updates: Record<string, unknown>) => {
      scope.updateSettings(updates);
    },
    [scope.updateSettings],
  );

  const handleSizeChange = useCallback((w: number, h: number) => {
    setScopeSize({ w, h });
  }, []);

  const handleToggleCursors = useCallback(() => {
    scope.setCursorsVisible(!scope.cursorsVisible);
  }, [scope.setCursorsVisible, scope.cursorsVisible]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        padding: '36px 12px 12px 12px',
        gap: 8,
      }}
    >
      <TopBar
        connected={scope.connected}
        running={scope.running}
        onConnect={scope.connect}
        onDisconnect={scope.disconnect}
        onStart={scope.startScope}
        onStop={scope.stopScope}
        onAutoscale={scope.autoscale}
        timePerDiv={scope.timePerDiv}
        ch1Range={scope.ch1Range}
        ch2Range={scope.ch2Range}
        ch1Enabled={scope.ch1Enabled}
        ch2Enabled={scope.ch2Enabled}
        triggerMode={scope.triggerMode}
        triggerEdge={scope.triggerEdge}
        onUpdate={handleUpdate}
        cursorsVisible={scope.cursorsVisible}
        onToggleCursors={handleToggleCursors}
        mathMode={scope.mathMode}
        onSetMathMode={scope.setMathMode}
      />
      <div style={{ flex: 1, position: 'relative', display: 'flex' }}>
        <ScopeView
          data={scope.scopeData}
          ch1Enabled={scope.ch1Enabled}
          ch2Enabled={scope.ch2Enabled}
          ch1Range={scope.ch1Range}
          ch2Range={scope.ch2Range}
          timePerDiv={scope.timePerDiv}
          triggerLevel={scope.triggerLevel}
          mathMode={scope.mathMode}
          onSizeChange={handleSizeChange}
        />
        {scope.cursorsVisible && (
          <Cursors
            width={scopeSize.w}
            height={scopeSize.h}
            timePerDiv={scope.timePerDiv}
            ch1Range={scope.ch1Range}
          />
        )}
        <WaveGenDrawer
          settings={waveGenSettings}
          onUpdate={updateWaveGen}
          onToggle={toggleOutput}
          connected={scope.connected}
        />
      </div>
      <Measurements
        data={scope.scopeData}
        ch1Enabled={scope.ch1Enabled}
        ch2Enabled={scope.ch2Enabled}
      />
    </div>
  );
}
