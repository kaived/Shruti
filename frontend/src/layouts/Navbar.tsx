import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Film, HelpCircle, Plus } from 'lucide-react';
import type { Access } from '../features/upload-screen';
import { HowItWorksModal } from '../features/home';
import { Button } from '../shared/ui';

interface NavbarProps {
  jobs?: Access[];
  selectedJobId?: string | null;
  onSelectJob?: (id: string) => void;
  onRemoveJob?: (id: string) => void;
  onNewVideo?: () => void;
  onSelectFile?: (file: File) => void;
}

export function Navbar({ jobs = [], selectedJobId, onSelectJob, onNewVideo }: NavbarProps) {
  const [isHowItWorksOpen, setIsHowItWorksOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close the menu on an outside click or Escape.
  useEffect(() => {
    if (!isMenuOpen) return;
    const onPointer = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setIsMenuOpen(false);
    };
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && setIsMenuOpen(false);
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [isMenuOpen]);

  return (
    <>
      <header className="top-navbar-wrapper">
        <nav className="top-nav" aria-label="Main Navigation">
          {/* Brand Group */}
          <div className="nav-brand-group">
            <div className="nav-brand-block">
              <span className="brand-glyph" aria-hidden="true">
                শ্রু
              </span>
              <div className="brand-text-col">
                <span className="brand-title">Shruti</span>
                <span className="brand-subtitle">Caption Studio</span>
              </div>
            </div>
          </div>

          <div className="nav-actions-group flex items-center gap-2">
            {/* My videos: lets people come back to videos they uploaded earlier */}
            {jobs.length > 0 && (
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setIsMenuOpen((open) => !open)}
                  aria-haspopup="menu"
                  aria-expanded={isMenuOpen}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Film size={15} />
                  My videos ({jobs.length})
                  <ChevronDown
                    size={14}
                    aria-hidden="true"
                    className={`transition-transform duration-200 ${isMenuOpen ? 'rotate-180' : ''}`}
                  />
                </button>

                {isMenuOpen && (
                  <div
                    role="menu"
                    className="absolute right-0 z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
                  >
                    <p className="px-2 pb-2 pt-1 text-xs text-slate-500">
                      Your videos on this browser. Click one to see its progress or captions.
                    </p>
                    <ul className="max-h-72 overflow-y-auto">
                      {jobs.map((job) => (
                        <li key={job.id} className="flex items-center gap-1">
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => {
                              onSelectJob?.(job.id);
                              setIsMenuOpen(false);
                            }}
                            className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-2 text-left text-sm hover:bg-slate-50 ${
                              job.id === selectedJobId ? 'bg-slate-100 font-medium text-slate-900' : 'text-slate-700'
                            }`}
                          >
                            <Film size={14} className="shrink-0 text-slate-400" />
                            <span className="truncate">{job.filename}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                    {onNewVideo && (
                      <button
                        type="button"
                        onClick={() => {
                          onNewVideo();
                          setIsMenuOpen(false);
                        }}
                        className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-lg border-t border-slate-100 px-2 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
                      >
                        <Plus size={15} />
                        Upload a new video
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            <Button
              variant="primary"
              size="md"
              className="!px-5"
              icon={<HelpCircle size={15} strokeWidth={2.2} />}
              onClick={() => setIsHowItWorksOpen(true)}
              title="See how Shruti makes captions and subtitles"
            >
              How it works
            </Button>
          </div>
        </nav>
      </header>

      {/* How It Works Modal */}
      <HowItWorksModal isOpen={isHowItWorksOpen} onClose={() => setIsHowItWorksOpen(false)} />
    </>
  );
}
