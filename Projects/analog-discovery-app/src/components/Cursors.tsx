import { useState, useCallback, useRef, type CSSProperties } from 'react';

interface CursorsProps {
  width: number;
  height: number;
  timePerDiv: number;
  ch1Range: number;
}

const GRID_COLS = 10;
const GRID_ROWS = 8;

interface CursorState {
  t1: number; // pixel x
  t2: number; // pixel x
  v1: number; // pixel y
  v2: number; // pixel y
}

const READOUT_STYLE: CSSProperties = {
  position: 'absolute',
  top: 8,
  right: 8,
  background: 'rgba(0,0,0,0.8)',
  border: '1px solid #ffcc00',
  borderRadius: 4,
  padding: '6px 10px',
  fontFamily: 'var(--font-mono, monospace)',
  fontSize: 11,
  color: '#ffcc00',
  pointerEvents: 'none',
  lineHeight: 1.6,
  whiteSpace: 'pre',
};

export default function Cursors({ width, height, timePerDiv, ch1Range }: CursorsProps) {
  const [cursors, setCursors] = useState<CursorState>(() => ({
    t1: Math.round(width * 0.3) || 100,
    t2: Math.round(width * 0.7) || 300,
    v1: Math.round(height * 0.3) || 80,
    v2: Math.round(height * 0.7) || 240,
  }));

  const dragRef = useRef<{ key: keyof CursorState; axis: 'x' | 'y' } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const onMouseDown = useCallback((key: keyof CursorState, axis: 'x' | 'y') => {
    return (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragRef.current = { key, axis };

      const onMove = (ev: MouseEvent) => {
        if (!dragRef.current || !svgRef.current) return;
        const rect = svgRef.current.getBoundingClientRect();
        const val =
          dragRef.current.axis === 'x'
            ? Math.max(0, Math.min(width, ev.clientX - rect.left))
            : Math.max(0, Math.min(height, ev.clientY - rect.top));
        setCursors((prev) => ({ ...prev, [dragRef.current!.key]: val }));
      };

      const onUp = () => {
        dragRef.current = null;
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };

      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    };
  }, [width, height]);

  // Convert pixel positions to physical units
  const totalTime = timePerDiv * GRID_COLS;
  const t1Sec = (cursors.t1 / width) * totalTime;
  const t2Sec = (cursors.t2 / width) * totalTime;
  const deltaT = Math.abs(t2Sec - t1Sec);

  const voltsPerPixel = ch1Range / height;
  const v1Volts = (height / 2 - cursors.v1) * voltsPerPixel;
  const v2Volts = (height / 2 - cursors.v2) * voltsPerPixel;
  const deltaV = Math.abs(v2Volts - v1Volts);

  const fmtTime = (s: number) => {
    if (s >= 1) return `${s.toFixed(3)} s`;
    if (s >= 1e-3) return `${(s * 1e3).toFixed(3)} ms`;
    return `${(s * 1e6).toFixed(1)} us`;
  };

  const fmtVolts = (v: number) => {
    if (Math.abs(v) >= 1) return `${v.toFixed(3)} V`;
    return `${(v * 1e3).toFixed(1)} mV`;
  };

  const freq = deltaT > 0 ? 1 / deltaT : 0;
  const fmtFreq = (f: number) => {
    if (f === 0) return '---';
    if (f >= 1e6) return `${(f / 1e6).toFixed(2)} MHz`;
    if (f >= 1e3) return `${(f / 1e3).toFixed(2)} kHz`;
    return `${f.toFixed(1)} Hz`;
  };

  const readout = [
    `T1: ${fmtTime(t1Sec)}  T2: ${fmtTime(t2Sec)}`,
    `dT: ${fmtTime(deltaT)}  1/dT: ${fmtFreq(freq)}`,
    `V1: ${fmtVolts(v1Volts)}  V2: ${fmtVolts(v2Volts)}`,
    `dV: ${fmtVolts(deltaV)}`,
  ].join('\n');

  if (width === 0 || height === 0) return null;

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      >
        {/* Time cursor 1 */}
        <line
          x1={cursors.t1}
          y1={0}
          x2={cursors.t1}
          y2={height}
          stroke="#ffcc00"
          strokeWidth={1.5}
          strokeDasharray="6,4"
          style={{ pointerEvents: 'auto', cursor: 'ew-resize' }}
          onMouseDown={onMouseDown('t1', 'x')}
        />
        {/* Time cursor 2 */}
        <line
          x1={cursors.t2}
          y1={0}
          x2={cursors.t2}
          y2={height}
          stroke="#ffcc00"
          strokeWidth={1.5}
          strokeDasharray="6,4"
          style={{ pointerEvents: 'auto', cursor: 'ew-resize' }}
          onMouseDown={onMouseDown('t2', 'x')}
        />
        {/* Voltage cursor 1 */}
        <line
          x1={0}
          y1={cursors.v1}
          x2={width}
          y2={cursors.v1}
          stroke="#ffcc00"
          strokeWidth={1.5}
          strokeDasharray="4,4"
          style={{ pointerEvents: 'auto', cursor: 'ns-resize' }}
          onMouseDown={onMouseDown('v1', 'y')}
        />
        {/* Voltage cursor 2 */}
        <line
          x1={0}
          y1={cursors.v2}
          x2={width}
          y2={cursors.v2}
          stroke="#ffcc00"
          strokeWidth={1.5}
          strokeDasharray="4,4"
          style={{ pointerEvents: 'auto', cursor: 'ns-resize' }}
          onMouseDown={onMouseDown('v2', 'y')}
        />
        {/* Labels */}
        <text x={cursors.t1 + 4} y={14} fill="#ffcc00" fontSize={10} fontFamily="monospace">
          T1
        </text>
        <text x={cursors.t2 + 4} y={14} fill="#ffcc00" fontSize={10} fontFamily="monospace">
          T2
        </text>
        <text x={4} y={cursors.v1 - 4} fill="#ffcc00" fontSize={10} fontFamily="monospace">
          V1
        </text>
        <text x={4} y={cursors.v2 - 4} fill="#ffcc00" fontSize={10} fontFamily="monospace">
          V2
        </text>
      </svg>
      <div style={READOUT_STYLE}>{readout}</div>
    </div>
  );
}
