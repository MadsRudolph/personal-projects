export function exportCSV(data: {
  ch1: number[] | null;
  ch2: number[] | null;
  sample_rate: number;
}) {
  const lines = ['time_s,ch1_v,ch2_v'];
  const len = Math.max(data.ch1?.length ?? 0, data.ch2?.length ?? 0);
  for (let i = 0; i < len; i++) {
    const t = i / data.sample_rate;
    const ch1 = data.ch1?.[i]?.toFixed(6) ?? '';
    const ch2 = data.ch2?.[i]?.toFixed(6) ?? '';
    lines.push(`${t.toExponential(6)},${ch1},${ch2}`);
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `scope_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function exportPNG(canvas: HTMLCanvasElement) {
  const url = canvas.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = url;
  a.download = `scope_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`;
  a.click();
}
