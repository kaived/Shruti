import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export type ModalMaxWidth = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  badge?: {
    icon?: React.ReactNode;
    text: string;
  };
  maxWidth?: ModalMaxWidth;
  footer?: React.ReactNode;
  children: React.ReactNode;
  showCloseButton?: boolean;
  className?: string;
}

const MAX_WIDTH_MAP: Record<ModalMaxWidth, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '3xl': 'max-w-3xl',
  '4xl': 'max-w-4xl',
};

export function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  badge,
  maxWidth = '2xl',
  footer,
  children,
  showCloseButton = true,
  className = '',
}: ModalProps) {
  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Lock background scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className={`relative w-full ${MAX_WIDTH_MAP[maxWidth]} max-h-[88vh] flex flex-col bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        {(title || badge || showCloseButton) && (
          <div className="shrink-0 flex items-start justify-between px-6 sm:px-8 py-5 border-b border-slate-200 bg-gradient-to-b from-slate-50 to-white">
            <div className="flex-1 pr-4">
              {badge && (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-100/60 rounded-md mb-2">
                  {badge.icon && <span className="shrink-0">{badge.icon}</span>}
                  <span>{badge.text}</span>
                </div>
              )}
              {title && (
                <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                  {title}
                </h2>
              )}
              {subtitle && (
                <p className="text-xs sm:text-sm text-slate-500 mt-1 leading-relaxed">
                  {subtitle}
                </p>
              )}
            </div>
            {showCloseButton && (
              <button
                type="button"
                className="flex items-center justify-center w-8 h-8 rounded-lg border border-slate-200 bg-white text-slate-400 hover:text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors shrink-0 cursor-pointer"
                onClick={onClose}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}

        {/* Scrollable Content Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 sm:px-8 py-5">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="shrink-0 flex items-center justify-between px-6 sm:px-8 py-3.5 bg-slate-100/90 border-t border-slate-200 gap-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
