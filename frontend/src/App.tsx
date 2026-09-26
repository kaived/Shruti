import { useEffect, useState } from 'react';
import { HomePage } from './features/home';
import { AccessSchema } from './features/upload-screen';
import type { Access } from './features/upload-screen';
import { Footer, Navbar } from './layouts';
import { z } from 'zod';

function getSavedJobs(): Access[] {
  try {
    const parsed = z.array(AccessSchema).safeParse(
      JSON.parse(sessionStorage.getItem('shruti-jobs') || '[]')
    );
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

export default function App() {
  const [jobs, setJobs] = useState<Access[]>(getSavedJobs);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(() => getSavedJobs()[0]?.id ?? null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  // Sync jobs to sessionStorage
  useEffect(() => {
    sessionStorage.setItem('shruti-jobs', JSON.stringify(jobs));
  }, [jobs]);

  const handleSelectJob = (id: string) => {
    setSelectedJobId(id);
  };

  const handleNewVideo = () => {
    setSelectedJobId(null);
  };

  const handleSelectFile = (file: File) => {
    setSelectedJobId(null);
    setPendingFile(file);
  };

  return (
    <div className="app-layout">
      {/* Top Application Navigation Bar */}
      <Navbar
        jobs={jobs}
        selectedJobId={selectedJobId}
        onSelectJob={handleSelectJob}
        onNewVideo={handleNewVideo}
        onSelectFile={handleSelectFile}
      />

      {/* Main Home Screen Feature: Upload -> Processing -> Caption Workspace */}
      <main className="app-main-content">
        <HomePage
          jobs={jobs}
          setJobs={setJobs}
          selectedJobId={selectedJobId}
          setSelectedJobId={setSelectedJobId}
          onNewVideo={handleNewVideo}
          pendingFile={pendingFile}
          onClearPendingFile={() => setPendingFile(null)}
        />
      </main>

      {/* Production & QC Compliance Footer */}
      <Footer />
    </div>
  );
}
