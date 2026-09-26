import { z } from 'zod';

export const LanguageSchema = z.enum(['bn', 'en', 'hi']);
export const CueKindSchema = z.enum(['speech', 'sound']);
export const IssueSeveritySchema = z.enum(['critical', 'high', 'medium']);
export const JobStateSchema = z.enum([
  'uploading',
  'uploaded',
  'queued',
  'running',
  'completed',
  'partial',
  'failed',
  'blocked',
]);
export const QCStatusSchema = z.enum(['not_run', 'incomplete', 'review_required', 'automated_checks_passed']);

export const CapabilitiesSchema = z.object({
  inference_configured: z.boolean(),
  max_upload_bytes: z.number().int().positive(),
  max_duration_seconds: z.number().positive(),
  upload_key_required: z.boolean(),
  caption_profile: z.string(),
  release_approval_available: z.literal(false),
});

export const AccessSchema = z.object({
  id: z.string().min(1),
  access_token: z.string().min(1),
  filename: z.string().min(1),
});

const MediaStreamSchema = z
  .object({
    index: z.number().int().nullable().optional(),
    codec_type: z.string().nullable().optional(),
    codec_name: z.string().nullable().optional(),
    start_time: z.string().nullable().optional(),
    sample_rate: z.string().nullable().optional(),
    avg_frame_rate: z.string().nullable().optional(),
  })
  .passthrough();

export const JobMediaSchema = z
  .object({
    duration_ms: z.number().int().nonnegative().optional(),
    run_id: z.string().optional(),
    format_start_seconds: z.string().nullable().optional(),
    audio_sample_rate: z.number().int().positive().optional(),
    audio_channels: z.number().int().positive().optional(),
    audio_stream_selection: z.string().optional(),
    timestamp_origin: z.string().optional(),
    streams: z.array(MediaStreamSchema).optional(),
  })
  .passthrough();

export const JobSchema = z.object({
  id: z.string().min(1),
  filename: z.string().min(1),
  state: JobStateSchema,
  stage: z.string(),
  qc_state: QCStatusSchema,
  message: z.string().nullable(),
  error_code: z.string().nullable(),
  attempts: z.number().int().nonnegative(),
  created_at: z.string(),
  updated_at: z.string(),
  media: JobMediaSchema.default({}),
  stage_metrics: z.record(z.string(), z.unknown()).default({}),
});

export const CueSchema = z.object({
  id: z.string().min(1),
  language: LanguageSchema,
  text: z.string(),
  kind: CueKindSchema,
  start_ms: z.number().int().nonnegative(),
  end_ms: z.number().int().positive(),
  speaker_ids: z.array(z.string()).default([]),
  source_word_ids: z.array(z.string()).default([]),
  source_cue_ids: z.array(z.string()).default([]),
  original_text: z.string().optional(),
  is_edited: z.boolean().optional(),
  needs_translation_update: z.boolean().optional(),
});

export const IssueSchema = z.object({
  id: z.string().min(1),
  code: z.string().min(1),
  severity: IssueSeveritySchema,
  language: z.string(),
  start_ms: z.number().int().nonnegative(),
  end_ms: z.number().int().nonnegative(),
  reason: z.string(),
  evidence: z.record(z.string(), z.unknown()).default({}),
  cue_ids: z.array(z.string()).default([]),
  review_state: z.enum(['open', 'resolved']).default('open'),
});

export const CaptionProfileSchema = z.object({
  version: z.string(),
  official: z.boolean(),
  character_counting: z.literal('unicode_code_points'),
  max_cps: z.object({
    bn: z.number().positive(),
    en: z.number().positive(),
    hi: z.number().positive(),
  }),
  max_line_length: z.number().int().positive(),
  max_lines: z.number().int().positive(),
  min_duration_ms: z.number().int().positive(),
  max_duration_ms: z.number().int().positive(),
  min_speech_support: z.number().min(0).max(1),
});

export const QCReportSchema = z.object({
  status: z.enum(['incomplete', 'review_required', 'automated_checks_passed']),
  release_ready: z.literal(false),
  profile: CaptionProfileSchema,
  issues: z.array(IssueSchema).default([]),
  checks: z.record(z.string(), z.string()).default({}),
  limitations: z.array(z.string()).default([]),
});

export const ArtifactNameSchema = z.enum([
  'bengali.vtt',
  'english.srt',
  'hindi.srt',
  'english.vtt',
  'hindi.vtt',
  'qc_report.json',
  'manifest.json',
]);

export const ResultsSchema = z.object({
  tracks: z.object({
    bn: z.array(CueSchema),
    en: z.array(CueSchema),
    hi: z.array(CueSchema),
  }),
  qc: QCReportSchema,
  downloads: z.array(ArtifactNameSchema).default([]),
});

export const RetryResponseSchema = z.object({
  id: z.string().min(1),
  message: z.string(),
});

export const HealthSchema = z.object({
  status: z.literal('ok'),
  service: z.literal('shruti'),
});

export const ReadinessSchema = z.object({
  database: z.boolean(),
  queue: z.boolean(),
  media_tools: z.boolean(),
});

export type Access = z.infer<typeof AccessSchema>;
export type ArtifactName = z.infer<typeof ArtifactNameSchema>;
export type Capabilities = z.infer<typeof CapabilitiesSchema>;
export type Cue = z.infer<typeof CueSchema>;
export type CueKind = z.infer<typeof CueKindSchema>;
export type Health = z.infer<typeof HealthSchema>;
export type Issue = z.infer<typeof IssueSchema>;
export type IssueSeverity = z.infer<typeof IssueSeveritySchema>;
export type Job = z.infer<typeof JobSchema>;
export type JobState = z.infer<typeof JobStateSchema>;
export type Language = z.infer<typeof LanguageSchema>;
export type QCReport = z.infer<typeof QCReportSchema>;
export type Readiness = z.infer<typeof ReadinessSchema>;
export type Results = z.infer<typeof ResultsSchema>;
export type RetryResponse = z.infer<typeof RetryResponseSchema>;
