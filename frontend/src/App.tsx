import { useEffect, useState } from 'react';
import { HomePage } from './features/home';
import { AccessSchema } from './features/upload-screen';
import type { Access } from './features/upload-screen';
import { Footer, Navbar } from './layouts';
import { z } from 'zod';

function getSavedJobs(): Access[] {
  try {
    const parsed = z.array(AccessSchema).safeParse(
      JSON.parse(localStorage.getItem('shruti-jobs') || '[]')
    );
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

function getInitialSelectedJobId(): string | null {
  try {
    const savedId = localStorage.getItem('shruti-selected-job');
    if (!savedId || savedId === 'null') return null;
    const savedJobs = getSavedJobs();
    return savedJobs.some((j) => j.id === savedId) ? savedId : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [jobs, setJobs] = useState<Access[]>(getSavedJobs);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(getInitialSelectedJobId);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  // Sync jobs to localStorage (may be unavailable in private modes)
  useEffect(() => {
    try {
      localStorage.setItem('shruti-jobs', JSON.stringify(jobs));
    } catch {
      /* storage unavailable: jobs stay in memory */
    }
  }, [jobs]);

  // Sync selectedJobId to localStorage
  useEffect(() => {
    try {
      if (selectedJobId) {
        localStorage.setItem('shruti-selected-job', selectedJobId);
      } else {
        localStorage.removeItem('shruti-selected-job');
      }
    } catch {
      /* storage unavailable */
    }
  }, [selectedJobId]);

  const handleSelectJob = (id: string) => {
    setSelectedJobId(id);
  };

  const handleRemoveJob = (id: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== id));
    if (selectedJobId === id) {
      setSelectedJobId(null);
    }
  };

  const handleNewVideo = () => {
    // Keep earlier jobs in the navbar so users can return to them; only deselect.
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
        onRemoveJob={handleRemoveJob}
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
