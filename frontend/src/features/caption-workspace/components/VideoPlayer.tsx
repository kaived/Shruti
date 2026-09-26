import React from 'react';
import { getJobMediaUrl } from '../../../shared/api-client';
import type { Cue, Language } from '../types';
import { formatTime } from '../utils/time';

interface VideoPlayerProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  jobId: string;
  isPlaying: boolean;
  currentTimeMs: number;
  durationMs: number;
  playbackRate: number;
  showCaptionsOverlay: boolean;
  activeCue: Cue | undefined;
  language: Language;
  onTogglePlay: () => void;
  onTimeUpdate: () => void;
  onChangePlaybackRate: (rate: number) => void;
  onToggleCaptionsOverlay: () => void;
}

const PLAYBACK_RATES = [0.5, 0.75, 1, 1.25, 1.5, 2];

export function VideoPlayer({
  videoRef,
  jobId,
  isPlaying,
  currentTimeMs,
  durationMs,
  playbackRate,
  showCaptionsOverlay,
  activeCue,
  language,
  onTogglePlay,
  onTimeUpdate,
  onChangePlaybackRate,
  onToggleCaptionsOverlay,
}: VideoPlayerProps) {
  return (
    <div className="player-column-wrapper">
      <div className="video-player-container">
        <video
          ref={videoRef}
          src={getJobMediaUrl(jobId)}
          className="main-video-element"
          onTimeUpdate={onTimeUpdate}
          onClick={onTogglePlay}
        />

        {showCaptionsOverlay && activeCue && (
          <div className="custom-subtitle-overlay" lang={language}>
            <div className="subtitle-bubble">
              {activeCue.speaker_ids.length > 0 && activeCue.kind === 'speech' && (
                <span className="subtitle-speaker">{activeCue.speaker_ids.join(', ')}: </span>
              )}
              <span className="subtitle-text">{activeCue.text}</span>
            </div>
          </div>
        )}
      </div>

      <div className="player-control-bar">
        <div className="controls-left">
          <button
            type="button"
            className="btn-player-action play-pause"
            onClick={onTogglePlay}
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            )}
          </button>

          <span className="time-display">
            {formatTime(currentTimeMs)} / {formatTime(durationMs || 1)}
          </span>
        </div>

        <div className="controls-right">
          <div className="rate-selector">
            {PLAYBACK_RATES.map((rate) => (
              <button
                key={rate}
                type="button"
                className={`rate-btn ${playbackRate === rate ? 'active' : ''}`}
                onClick={() => onChangePlaybackRate(rate)}
              >
                {rate}x
              </button>
            ))}
          </div>

          <button
            type="button"
            className={`btn-player-action cc-toggle ${showCaptionsOverlay ? 'active' : ''}`}
            onClick={onToggleCaptionsOverlay}
            title="Toggle subtitles overlay"
          >
            CC
          </button>
        </div>
      </div>
    </div>
  );
}
