import { useState } from 'react';
import { CaptionWorkspace, useJobResultsQuery } from '../../caption-workspace';
import { ProcessingScreen, useJobStatusQuery, useRetryJobMutation } from '../../processing-screen';
import { UploadScreen, useCapabilitiesQuery, useUploadVideoMutation } from '../../upload-screen';
import { WorkflowBar } from '../components/WorkflowBar';
import type { HomePageProps, ScreenView } from '../types';

export function HomePage({
  jobs,
  setJobs,
  selectedJobId,
  setSelectedJobId,
  onNewVideo,
  pendingFile,
  onClearPendingFile,
}: HomePageProps) {
  const [localErrorMessage, setLocalErrorMessage] = useState('');
  const [uploadProgress, setUploadProgress] = useState<number | undefined>(undefined);

  // Active video selection
  const activeAccess = jobs.find((item) => item.id === selectedJobId);

  // 1. TanStack Query: Backend capabilities & max file sizes
  const { data: capabilities } = useCapabilitiesQuery();

  // 2. TanStack Query: Real-time job status polling (every 1.8s while active)
  const { data: currentJob, error: jobStatusError } = useJobStatusQuery(
    selectedJobId,
    activeAccess?.access_token
  );

  // 3. Terminal state check for results ready
  const isResultsReady = Boolean(
    currentJob && ['completed', 'partial'].includes(currentJob.state)
  );

  // 4. TanStack Query: Job output results & QC report
  const { data: currentResults, error: resultsError } = useJobResultsQuery(
    selectedJobId,
    activeAccess?.access_token,
    isResultsReady
  );

  // 5. TanStack Mutations: Upload and Retry
  const uploadMutation = useUploadVideoMutation();
  const retryMutation = useRetryJobMutation();

  // Determine current active workflow view
  const isWorkspaceReady = Boolean(
    activeAccess && currentResults && ['completed', 'partial'].includes(currentJob?.state || '')
  );
  const isProcessing = Boolean(activeAccess && !isWorkspaceReady);

  let currentView: ScreenView = 'upload';
  if (isWorkspaceReady) {
    currentView = 'workspace';
  } else if (isProcessing) {
    currentView = 'processing';
  }

  // Combined error message
  const activeError =
    localErrorMessage ||
    (uploadMutation.error ? uploadMutation.error.message : '') ||
    (jobStatusError ? jobStatusError.message : '') ||
    (resultsError ? resultsError.message : '') ||
    (retryMutation.error ? retryMutation.error.message : '');

  // Handle Video Upload via TanStack Mutation
  const handleStartUpload = async (file: File, uploadKey?: string) => {
    const maxBytes = capabilities?.max_upload_bytes ?? 500 * 1024 * 1024;
    if (file.size > maxBytes) {
      setLocalErrorMessage(
        `Video exceeds the maximum upload limit of ${Math.round(maxBytes / (1024 * 1024))} MB.`
      );
      return;
    }

    setLocalErrorMessage('');
    setUploadProgress(0);

    try {
      const access = await uploadMutation.mutateAsync({
        file,
        onProgress: (percent) => setUploadProgress(percent),
        uploadKey,
      });

      const newAccess = { ...access, filename: file.name };
      setJobs((current) => [newAccess, ...current.filter((j) => j.id !== newAccess.id)].slice(0, 15));
      setSelectedJobId(access.id);
      setUploadProgress(undefined);
    } catch {
      setUploadProgress(undefined);
    }
  };

  // Handle Retry Job via TanStack Mutation
  const handleRetryJob = async () => {
    if (!activeAccess) return;
    setLocalErrorMessage('');
    try {
      await retryMutation.mutateAsync({
        jobId: activeAccess.id,
        accessToken: activeAccess.access_token,
      });
    } catch {
      // Handled by retryMutation.error
    }
  };

  const handleCancelProcessing = () => {
    // Keep the video in "My videos" so it can be reopened later; removal is explicit (✕ in the menu).
    onNewVideo();
    setLocalErrorMessage('');
    uploadMutation.reset();
    onClearPendingFile?.();
  };

  const handleNewVideoFromWorkspace = () => {
    onNewVideo();
    setLocalErrorMessage('');
    uploadMutation.reset();
    onClearPendingFile?.();
  };

  return (
    <div className="home-feature-container">
      {/* Step Indicator Header Bar */}
      <WorkflowBar currentView={currentView} filename={activeAccess?.filename} />

      {/* Screen 1: Upload Screen */}
      {!selectedJobId && (
        <UploadScreen
          capabilities={capabilities || null}
          onStartUpload={handleStartUpload}
          isUploading={uploadMutation.isPending}
          uploadProgress={uploadProgress}
          errorMessage={activeError}
          initialFile={pendingFile}
        />
      )}

      {/* Screen 2: Processing Screen */}
      {activeAccess && !isWorkspaceReady && (
        <ProcessingScreen
          job={currentJob || null}
          filename={activeAccess.filename}
          uploadProgress={uploadProgress}
          onRetry={handleRetryJob}
          onCancel={handleCancelProcessing}
          isRetrying={retryMutation.isPending}
        />
      )}

      {/* Screen 3: Caption Workspace (Main Workstation) */}
      {activeAccess && currentResults && isWorkspaceReady && (
        <CaptionWorkspace
          key={activeAccess.id}
          jobId={activeAccess.id}
          accessToken={activeAccess.access_token}
          filename={activeAccess.filename}
          initialResults={currentResults}
          onNewVideo={handleNewVideoFromWorkspace}
        />
      )}
    </div>
  );
}
