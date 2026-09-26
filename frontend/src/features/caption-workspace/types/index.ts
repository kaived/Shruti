import { z } from 'zod';
import {
  CueKindSchema,
  CueSchema,
  IssueSchema,
  IssueSeveritySchema,
  LanguageSchema,
  QCReportSchema,
  ResultsSchema,
} from '../validation';

export type Language = z.infer<typeof LanguageSchema>;
export type CueKind = z.infer<typeof CueKindSchema>;
export type Cue = z.infer<typeof CueSchema>;
export type IssueSeverity = z.infer<typeof IssueSeveritySchema>;
export type Issue = z.infer<typeof IssueSchema>;
export type QCReport = z.infer<typeof QCReportSchema>;
export type Results = z.infer<typeof ResultsSchema>;

export interface CaptionWorkspacePageProps {
  jobId: string;
  accessToken?: string;
  filename: string;
  initialResults: Results;
  onNewVideo: () => void;
}

export interface FriendlyIssueInfo {
  title: string;
  explanation: string;
}

export type ReviewFilterType = 'needs_review' | 'reviewed' | 'all';
export type ActiveTabType = 'review' | 'captions';

export interface LanguageOption {
  code: Language;
  label: string;
  full: string;
}

export interface DeletedCueRecord {
  cue: Cue;
  index: number;
  lang: Language;
}
