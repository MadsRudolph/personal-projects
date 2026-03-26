import { useRef, useEffect, useCallback } from 'react';
import type { ScopeData } from '../hooks/useScopeState';

interface ScopeViewProps {
  data: ScopeData | null;
  ch1Enabled: boolean;
  ch2Enabled: boolean;
  ch1Range: number;
  ch2Range: number;
  timePerDiv: number;
  triggerLevel: number;
}

const GRID_COLS = 10;
const GRID_ROWS = 8;
const MINOR_DIVS = 5;

export default function ScopeView({
  data,
  ch1Enabled,
  ch2Enabled,
  ch1Range,
  ch2Range,
  triggerLevel,
}: ScopeViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);
  const sizeRef = useRef({ w: 0, h: 0 });

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = sizeRef.current.w;
    const h = sizeRef.current.h;

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Background
    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, w, h);

    const cellW = w / GRID_COLS;
    const cellH = h / GRID_ROWS;

    // Minor grid
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    const minorCellW = cellW / MINOR_DIVS;
    const minorCellH = cellH / MINOR_DIVS;
    for (let i = 0; i <= GRID_COLS * MINOR_DIVS; i++) {
      const x = Math.round(i * minorCellW) + 0.5;
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let i = 0; i <= GRID_ROWS * MINOR_DIVS; i++) {
      const y = Math.round(i * minorCellH) + 0.5;
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();

    // Major grid
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i <= GRID_COLS; i++) {
      const x = Math.round(i * cellW) + 0.5;
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let i = 0; i <= GRID_ROWS; i++) {
      const y = Math.round(i * cellH) + 0.5;
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();

    // Center crosshair
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    const cx = Math.round(w / 2) + 0.5;
    const cy = Math.round(h / 2) + 0.5;
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, h);
    ctx.moveTo(0, cy);
    ctx.lineTo(w, cy);
    ctx.stroke();

    // Trigger level line
    const ch1VoltsPerPixel = ch1Range / h;
    const triggerY = h / 2 - triggerLevel / ch1VoltsPerPixel;
    if (triggerY >= 0 && triggerY <= h) {
      ctx.strokeStyle = '#ff6600';
      ctx.lineWidth = 1;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(0, triggerY);
      ctx.lineTo(w, triggerY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw traces
    const drawTrace = (samples: number[], range: number, color: string) => {
      if (samples.length < 2) return;
      const voltsPerPixel = range / h;
      const step = (samples.length - 1) / (w - 1);

      // Glow pass
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.25;
      ctx.lineWidth = 5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      for (let px = 0; px < w; px++) {
        const idx = px * step;
        const i0 = Math.floor(idx);
        const i1 = Math.min(i0 + 1, samples.length - 1);
        const t = idx - i0;
        const v = samples[i0] * (1 - t) + samples[i1] * t;
        const y = h / 2 - v / voltsPerPixel;
        if (px === 0) ctx.moveTo(px, y);
        else ctx.lineTo(px, y);
      }
      ctx.stroke();

      // Crisp pass
      ctx.globalAlpha = 1;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let px = 0; px < w; px++) {
        const idx = px * step;
        const i0 = Math.floor(idx);
        const i1 = Math.min(i0 + 1, samples.length - 1);
        const t = idx - i0;
        const v = samples[i0] * (1 - t) + samples[i1] * t;
        const y = h / 2 - v / voltsPerPixel;
        if (px === 0) ctx.moveTo(px, y);
        else ctx.lineTo(px, y);
      }
      ctx.stroke();
    };

    if (data) {
      if (ch1Enabled && data.ch1) drawTrace(data.ch1, ch1Range, '#00e5ff');
      if (ch2Enabled && data.ch2) drawTrace(data.ch2, ch2Range, '#ff00e5');
    }
  }, [data, ch1Enabled, ch2Enabled, ch1Range, ch2Range, triggerLevel]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        sizeRef.current = {
          w: entry.contentRect.width,
          h: entry.contentRect.height,
        };
        cancelAnimationFrame(animRef.current);
        animRef.current = requestAnimationFrame(draw);
      }
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, [draw]);

  useEffect(() => {
    cancelAnimationFrame(animRef.current);
    animRef.current = requestAnimationFrame(draw);
  }, [draw]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'absolute',
        inset: 0,
        borderRadius: 6,
        overflow: 'hidden',
        border: '1px solid var(--border)',
      }}
    >
      <canvas ref={canvasRef} style={{ display: 'block' }} />
    </div>
  );
}
