import { useCallback, useRef, useEffect } from 'react';

interface KnobProps {
  value: number;
  min: number;
  max: number;
  label: string;
  unit: string;
  onChange: (value: number) => void;
  logarithmic?: boolean;
  color?: string;
}

function formatValue(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e6) return (v / 1e6).toFixed(2) + ' M';
  if (abs >= 1e3) return (v / 1e3).toFixed(2) + ' k';
  if (abs >= 1) return v.toFixed(abs >= 100 ? 0 : abs >= 10 ? 1 : 2);
  if (abs >= 0.001) return (v * 1e3).toFixed(1) + ' m';
  return v.toFixed(3);
}

export default function Knob({
  value,
  min,
  max,
  label,
  unit,
  onChange,
  logarithmic = false,
  color = 'var(--accent)',
}: KnobProps) {
  const knobRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ startY: number; startNorm: number } | null>(null);

  const toNorm = useCallback(
    (v: number) => {
      if (logarithmic && min > 0) {
        return (Math.log(v / min)) / (Math.log(max / min));
      }
      return (v - min) / (max - min);
    },
    [min, max, logarithmic],
  );

  const fromNorm = useCallback(
    (n: number) => {
      const clamped = Math.max(0, Math.min(1, n));
      if (logarithmic && min > 0) {
        return min * Math.pow(max / min, clamped);
      }
      return min + (max - min) * clamped;
    },
    [min, max, logarithmic],
  );

  const norm = toNorm(value);
  const angleDeg = -135 + norm * 270;

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragState.current = { startY: e.clientY, startNorm: toNorm(value) };

      const handleMouseMove = (me: MouseEvent) => {
        if (!dragState.current) return;
        const dy = dragState.current.startY - me.clientY;
        const sensitivity = me.shiftKey ? 0.001 : 0.005;
        const newNorm = dragState.current.startNorm + dy * sensitivity;
        onChange(fromNorm(newNorm));
      };

      const handleMouseUp = () => {
        dragState.current = null;
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    },
    [value, toNorm, fromNorm, onChange],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      dragState.current = null;
    };
  }, []);

  const gradientStop = norm * 100;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        userSelect: 'none',
      }}
    >
      <span
        style={{
          fontSize: 9,
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-sans)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        {label}
      </span>
      <div
        ref={knobRef}
        onMouseDown={handleMouseDown}
        style={{
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: `conic-gradient(from 202.5deg, ${color} 0deg, ${color} ${gradientStop * 2.7}deg, var(--bg-tertiary) ${gradientStop * 2.7}deg, var(--bg-tertiary) 270deg, transparent 270deg)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'ns-resize',
          position: 'relative',
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              width: 2,
              height: 12,
              background: color,
              borderRadius: 1,
              transformOrigin: '50% 100%',
              transform: `translate(-50%, -100%) rotate(${angleDeg}deg)`,
            }}
          />
        </div>
      </div>
      <span
        style={{
          fontSize: 10,
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-mono)',
          whiteSpace: 'nowrap',
        }}
      >
        {formatValue(value)}{unit}
      </span>
    </div>
  );
}
