import { useEffect, useRef, useState } from 'react';
import { CaptionsList } from '../components/CaptionsList';
import { QcReportModal } from '../components/QcReportModal';
import { RenameSpeakerModal } from '../components/RenameSpeakerModal';
import { ReviewPanel } from '../components/ReviewPanel';
import { TimelineTrack } from '../components/TimelineTrack';
import { VideoPlayer } from '../components/VideoPlayer';
import { WorkspaceHeader } from '../components/WorkspaceHeader';
import type {
  ActiveTabType,
  CaptionWorkspacePageProps,
  Cue,
  DeletedCueRecord,
  Issue,
  Language,
  LanguageOption,
  ReviewFilterType,
} from '../types';

const LANGUAGES: LanguageOption[] = [
  { code: 'bn', label: 'বাংলা · CC', full: 'Bengali Closed Captions' },
  { code: 'en', label: 'English', full: 'English Subtitles' },
  { code: 'hi', label: 'हिन्दी', full: 'Hindi Subtitles' },
];

export function CaptionWorkspacePage({
  jobId,
  filename,
  initialResults,
  onNewVideo,
}: CaptionWorkspacePageProps) {
  // Main Data States
  const [tracks, setTracks] = useState<Record<Language, Cue[]>>(initialResults.tracks);
  const [issues, setIssues] = useState<Issue[]>(initialResults.qc.issues);
  const [language, setLanguage] = useState<Language>('bn');

  // Video & Playback States
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [durationMs, setDurationMs] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showCaptionsOverlay, setShowCaptionsOverlay] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);

  // Active Workspace Navigation & Filters
  const [activeTab, setActiveTab] = useState<ActiveTabType>('review');
  const [reviewFilter, setReviewFilter] = useState<ReviewFilterType>('needs_review');
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);

  // Editing States
  const [editingCueId, setEditingCueId] = useState<string | null>(null);
  const [editCueText, setEditCueText] = useState('');
  const [editCueStart, setEditCueStart] = useState(0);
  const [editCueEnd, setEditCueEnd] = useState(0);
  const [editCueSpeaker, setEditCueSpeaker] = useState('');

  // Undo Stack for Deleted Cues
  const [deletedCueStack, setDeletedCueStack] = useState<DeletedCueRecord[]>([]);

  // Speaker Renaming Modal
  const [renameSpeakerModalOpen, setRenameSpeakerModalOpen] = useState(false);
  const [targetSpeakerId, setTargetSpeakerId] = useState('');
  const [newSpeakerName, setNewSpeakerName] = useState('');

  // QC Report Inspection Modal
  const [qcModalOpen, setQcModalOpen] = useState(false);

  // Sync Video Duration
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const handleLoadedMetadata = () => {
      setDurationMs(v.duration * 1000);
    };
    v.addEventListener('loadedmetadata', handleLoadedMetadata);
    return () => v.removeEventListener('loadedmetadata', handleLoadedMetadata);
  }, []);

  // Sync Current Caption
  const currentCues = tracks[language] || [];
  const activeCue = currentCues.find((c) => c.start_ms <= currentTimeMs && currentTimeMs < c.end_ms);

  // Auto-scroll caption list
  const activeCueRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (autoScroll && activeCueRef.current && activeTab === 'captions') {
      activeCueRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [activeCue?.id, autoScroll, activeTab]);

  // Video Control Handlers
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      void videoRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const seekTo = (ms: number, autoPlay = false) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(0, ms / 1000);
    setCurrentTimeMs(ms);
    if (autoPlay) {
      void videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const changePlaybackRate = (rate: number) => {
    setPlaybackRate(rate);
    if (videoRef.current) {
      videoRef.current.playbackRate = rate;
    }
  };

  const replaySection = (startMs: number, endMs: number) => {
    seekTo(startMs, true);
    const checkEnd = () => {
      if (videoRef.current && videoRef.current.currentTime * 1000 >= endMs) {
        videoRef.current.pause();
        setIsPlaying(false);
        videoRef.current.removeEventListener('timeupdate', checkEnd);
      }
    };
    videoRef.current?.addEventListener('timeupdate', checkEnd);
  };

  // Review Queue Filtering & Navigation
  const filteredIssues = issues.filter((issue) => {
    if (reviewFilter === 'needs_review') return issue.review_state !== 'resolved';
    if (reviewFilter === 'reviewed') return issue.review_state === 'resolved';
    return true;
  });

  const unreviewedCount = issues.filter((i) => i.review_state !== 'resolved').length;

  const currentIssueIndex = selectedIssueId
    ? filteredIssues.findIndex((i) => i.id === selectedIssueId)
    : -1;

  const nextIssue = () => {
    if (filteredIssues.length === 0) return;
    const nextIdx = (currentIssueIndex + 1) % filteredIssues.length;
    const item = filteredIssues[nextIdx];
    setSelectedIssueId(item.id);
    seekTo(item.start_ms);
  };

  const prevIssue = () => {
    if (filteredIssues.length === 0) return;
    const prevIdx = (currentIssueIndex - 1 + filteredIssues.length) % filteredIssues.length;
    const item = filteredIssues[prevIdx];
    setSelectedIssueId(item.id);
    seekTo(item.start_ms);
  };

  const toggleIssueResolved = (issueId: string) => {
    setIssues((current) =>
      current.map((iss) =>
        iss.id === issueId
          ? { ...iss, review_state: iss.review_state === 'resolved' ? 'open' : 'resolved' }
          : iss
      )
    );
  };

  // Inline Editing Handlers
  const startEditingCue = (cue: Cue) => {
    setEditingCueId(cue.id);
    setEditCueText(cue.text);
    setEditCueStart(cue.start_ms);
    setEditCueEnd(cue.end_ms);
    setEditCueSpeaker(cue.speaker_ids[0] || '');
  };

  const saveEditedCue = () => {
    if (!editingCueId) return;
    setTracks((prev) => {
      const updatedList = (prev[language] || []).map((cue) => {
        if (cue.id === editingCueId) {
          return {
            ...cue,
            text: editCueText,
            start_ms: Math.max(0, editCueStart),
            end_ms: Math.max(editCueStart + 100, editCueEnd),
            speaker_ids: editCueSpeaker ? [editCueSpeaker] : [],
            is_edited: true,
            original_text: cue.original_text || cue.text,
            needs_translation_update: language === 'bn' ? true : cue.needs_translation_update,
          };
        }
        return cue;
      });
      return { ...prev, [language]: updatedList };
    });
    setEditingCueId(null);
  };

  const cancelEditingCue = () => {
    setEditingCueId(null);
  };

  const deleteCue = (cueId: string) => {
    const list = tracks[language] || [];
    const index = list.findIndex((c) => c.id === cueId);
    if (index === -1) return;
    const deleted = list[index];

    setDeletedCueStack((prev) => [{ cue: deleted, index, lang: language }, ...prev]);
    setTracks((prev) => ({
      ...prev,
      [language]: list.filter((c) => c.id !== cueId),
    }));
  };

  const undoDeleteCue = () => {
    if (deletedCueStack.length === 0) return;
    const [lastDeleted, ...rest] = deletedCueStack;
    setDeletedCueStack(rest);

    setTracks((prev: Record<Language, Cue[]>) => {
      const list = [...(prev[lastDeleted.lang] || [])];
      list.splice(lastDeleted.index, 0, lastDeleted.cue);
      return { ...prev, [lastDeleted.lang]: list };
    });
  };

  // Speaker Renaming Handler
  const openRenameSpeaker = (speakerId: string) => {
    setTargetSpeakerId(speakerId);
    setNewSpeakerName(speakerId);
    setRenameSpeakerModalOpen(true);
  };

  const applyRenameSpeaker = () => {
    if (!targetSpeakerId || !newSpeakerName.trim()) return;
    const replacement = newSpeakerName.trim();

    setTracks((prev) => {
      const updated: Record<Language, Cue[]> = { bn: [], en: [], hi: [] };
      for (const lang of ['bn', 'en', 'hi'] as Language[]) {
        updated[lang] = (prev[lang] || []).map((cue) => {
          if (cue.speaker_ids.includes(targetSpeakerId)) {
            return {
              ...cue,
              speaker_ids: cue.speaker_ids.map((s) => (s === targetSpeakerId ? replacement : s)),
              is_edited: true,
            };
          }
          return cue;
        });
      }
      return updated;
    });

    setRenameSpeakerModalOpen(false);
  };

  // Distinct Speakers list for datalist dropdown
  const allSpeakers = Array.from(
    new Set(
      Object.values(tracks)
        .flat()
        .flatMap((c) => c.speaker_ids)
        .filter(Boolean)
    )
  );

  return (
    <div className="caption-workspace-shell">
      <WorkspaceHeader
        jobId={jobId}
        filename={filename}
        unreviewedCount={unreviewedCount}
        hasDeletedCues={deletedCueStack.length > 0}
        tracks={tracks}
        qc={initialResults.qc}
        onNewVideo={onNewVideo}
        onUndoDelete={undoDeleteCue}
        onOpenQcModal={() => setQcModalOpen(true)}
      />

      <div className="workspace-grid">
        <section className="player-column">
          <VideoPlayer
            videoRef={videoRef}
            jobId={jobId}
            isPlaying={isPlaying}
            currentTimeMs={currentTimeMs}
            durationMs={durationMs}
            playbackRate={playbackRate}
            showCaptionsOverlay={showCaptionsOverlay}
            activeCue={activeCue}
            language={language}
            onTogglePlay={togglePlay}
            onTimeUpdate={() => setCurrentTimeMs((videoRef.current?.currentTime || 0) * 1000)}
            onChangePlaybackRate={changePlaybackRate}
            onToggleCaptionsOverlay={() => setShowCaptionsOverlay(!showCaptionsOverlay)}
          />

          <TimelineTrack
            currentTimeMs={currentTimeMs}
            durationMs={durationMs}
            issues={issues}
            selectedIssueId={selectedIssueId}
            onSeek={(ms) => seekTo(ms)}
            onSelectIssue={(issueId) => {
              setSelectedIssueId(issueId);
              setActiveTab('review');
            }}
          />
        </section>

        <section className="side-column">
          <div className="panel-tab-bar">
            <div className="tab-group-left">
              <button
                type="button"
                className={`panel-tab ${activeTab === 'review' ? 'active' : ''}`}
                onClick={() => setActiveTab('review')}
              >
                <span>Review queue</span>
                {unreviewedCount > 0 && <span className="tab-counter">{unreviewedCount}</span>}
              </button>
              <button
                type="button"
                className={`panel-tab ${activeTab === 'captions' ? 'active' : ''}`}
                onClick={() => setActiveTab('captions')}
              >
                <span>Captions list</span>
                <span className="tab-counter-subtle">{currentCues.length}</span>
              </button>
            </div>

            <div className="language-selector">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  className={`lang-btn ${language === lang.code ? 'active' : ''}`}
                  onClick={() => setLanguage(lang.code)}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          </div>

          {activeTab === 'review' && (
            <ReviewPanel
              issues={issues}
              filteredIssues={filteredIssues}
              reviewFilter={reviewFilter}
              selectedIssueId={selectedIssueId}
              cues={tracks[language] || []}
              onFilterChange={setReviewFilter}
              onSelectIssue={(issueId) => {
                setSelectedIssueId(issueId);
                const iss = issues.find((i) => i.id === issueId);
                if (iss) seekTo(iss.start_ms);
              }}
              onPrevIssue={prevIssue}
              onNextIssue={nextIssue}
              onToggleIssueResolved={toggleIssueResolved}
              onReplaySection={replaySection}
              onEditCue={(targetCue) => {
                setActiveTab('captions');
                startEditingCue(targetCue);
                seekTo(targetCue.start_ms);
              }}
            />
          )}

          {activeTab === 'captions' && (
            <CaptionsList
              cues={currentCues}
              activeCue={activeCue}
              activeCueRef={activeCueRef}
              language={language}
              trackHeading={LANGUAGES.find((l) => l.code === language)?.full || 'Captions'}
              autoScroll={autoScroll}
              editingCueId={editingCueId}
              editCueText={editCueText}
              editCueStart={editCueStart}
              editCueEnd={editCueEnd}
              editCueSpeaker={editCueSpeaker}
              availableSpeakers={allSpeakers}
              onToggleAutoScroll={setAutoScroll}
              onSeek={(ms) => seekTo(ms)}
              onStartEdit={startEditingCue}
              onSaveEdit={saveEditedCue}
              onCancelEdit={cancelEditingCue}
              onDeleteCue={deleteCue}
              onOpenRenameSpeaker={openRenameSpeaker}
              setEditCueText={setEditCueText}
              setEditCueStart={setEditCueStart}
              setEditCueEnd={setEditCueEnd}
              setEditCueSpeaker={setEditCueSpeaker}
            />
          )}
        </section>
      </div>

      <RenameSpeakerModal
        isOpen={renameSpeakerModalOpen}
        targetSpeakerId={targetSpeakerId}
        newSpeakerName={newSpeakerName}
        onNewSpeakerNameChange={setNewSpeakerName}
        onClose={() => setRenameSpeakerModalOpen(false)}
        onApply={applyRenameSpeaker}
      />

      <QcReportModal
        isOpen={qcModalOpen}
        qc={initialResults.qc}
        onClose={() => setQcModalOpen(false)}
      />
    </div>
  );
}
