import type { FriendlyIssueInfo } from '../types';

export function getFriendlyIssueInfo(code: string): FriendlyIssueInfo {
  switch (code) {
    case 'SUSPECTED_HALLUCINATION':
      return {
        title: 'Possible dialogue during music / silence',
        explanation: 'We detected text here, but found little evidence of speech in the audio.',
      };
    case 'SPEECH_WITHOUT_TEXT':
      return {
        title: 'Possible speech without a caption',
        explanation: 'Acoustic speech evidence was detected here that was not captured in the transcript.',
      };
    case 'SPEAKER_UNCERTAIN':
      return {
        title: 'We’re unsure who is speaking',
        explanation: 'Speaker attribution has low acoustic confidence or unresolved overlaps.',
      };
    case 'CPS_EXCEEDED':
      return {
        title: 'This caption may disappear too quickly',
        explanation: 'The reading speed exceeds standard viewing profile limits (17-20 CPS).',
      };
    case 'SHOT_CROSSING':
      return {
        title: 'This caption crosses a scene cut',
        explanation: 'The subtitle straddles a detected camera angle change, which can distract viewers.',
      };
    case 'LINE_LIMIT_EXCEEDED':
      return {
        title: 'Caption text exceeds line limits',
        explanation: 'Text does not fit the configured line length (max 42 chars per line).',
      };
    case 'SOURCE_UNCERTAINTY':
      return {
        title: 'Translation source requires review',
        explanation: 'The underlying Bengali source caption has open review flags.',
      };
    default:
      return {
        title: code.replace(/_/g, ' ').toLowerCase(),
        explanation: 'Please review timing and wording against playback.',
      };
  }
}
