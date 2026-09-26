import JSZip from 'jszip';
import type { Cue, Language, Results } from '../types';
import { formatSrtTimestamp, formatVttTimestamp } from './time';

export function generateVttString(cues: Cue[]): string {
  let out = 'WEBVTT\n\n';
  cues.forEach((c, idx) => {
    const s = formatVttTimestamp(c.start_ms);
    const e = formatVttTimestamp(c.end_ms);
    const prefix = c.speaker_ids.length > 0 ? `<v ${c.speaker_ids.join(', ')}>` : '';
    out += `${idx + 1}\n${s} --> ${e}\n${prefix}${c.text}\n\n`;
  });
  return out;
}

export function generateSrtString(cues: Cue[]): string {
  let out = '';
  cues.forEach((c, idx) => {
    const s = formatSrtTimestamp(c.start_ms);
    const e = formatSrtTimestamp(c.end_ms);
    out += `${idx + 1}\n${s} --> ${e}\n${c.text}\n\n`;
  });
  return out;
}

export function downloadTextFile(filename: string, content: string, mimeType = 'text/plain'): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function downloadEverythingZip(
  jobId: string,
  filename: string,
  tracks: Record<Language, Cue[]>,
  qc: Results['qc'],
  unreviewedCount: number
): Promise<void> {
  const zip = new JSZip();
  zip.file('bengali.vtt', generateVttString(tracks.bn || []));
  zip.file('english.srt', generateSrtString(tracks.en || []));
  zip.file('hindi.srt', generateSrtString(tracks.hi || []));
  zip.file('qc_report.json', JSON.stringify(qc, null, 2));

  const manifest = {
    job_id: jobId,
    filename,
    generated_at: new Date().toISOString(),
    unresolved_issues_count: unreviewedCount,
    review_completed: unreviewedCount === 0,
    languages: ['bn', 'en', 'hi'],
  };
  zip.file('manifest.json', JSON.stringify(manifest, null, 2));

  const blob = await zip.generateAsync({ type: 'blob' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `shruti_captions_${jobId.slice(0, 8)}.zip`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
