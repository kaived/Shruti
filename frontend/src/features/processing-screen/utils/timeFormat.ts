export function formatElapsed(sec: number): string {
  const mins = Math.floor(sec / 60);
  const s = sec % 60;
  return `${mins}m ${s.toString().padStart(2, '0')}s`;
}
