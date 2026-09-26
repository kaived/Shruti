import { useState } from 'react';

export function Footer() {
  const [showShortcuts, setShowShortcuts] = useState(false);

  return (
    <footer className="app-footer">
      <div className="footer-inner">
        {/* Brand & Project Info */}
        <div className="footer-col brand-col">
          <div className="footer-brand-title">
            <span className="brand-glyph-sm">শ্রু</span>
            <span>Shruti Caption Studio</span>
          </div>
          <p className="footer-description">
            Production-grade Bengali closed captioning & multi-lingual subtitling engine built for
            Hoichoi OTT. Acoustic-evidence verification protects against unflagged hallucinations
            over silence and music.
          </p>
          <div className="footer-meta-tags">
            <span className="footer-tag">WebVTT (বাংলা CC)</span>
            <span className="footer-tag">SRT Subtitles (EN · HI)</span>
            <span className="footer-tag">Evidence-Based QC (.json)</span>
          </div>
        </div>

        {/* Pipeline & QC Specifications */}
        <div className="footer-col specs-col">
          <h4 className="footer-heading">Pipeline Specifications</h4>
          <ul className="footer-specs-list">
            <li>
              <strong>Bengali ASR:</strong> Groq Whisper Large v3 (Word Timestamps)
            </li>
            <li>
              <strong>Alignment & Shots:</strong> Monotonic word alignment & scene cut detection
            </li>
            <li>
              <strong>Speaker Tracking:</strong> Stable speaker IDs & character renaming
            </li>
            <li>
              <strong>Translation:</strong> Groq LLaMA 3.3 70B (Bengali → English & Hindi)
            </li>
            <li>
              <strong>Quality Control:</strong> Hallucination & silence audit, reading rate & shot-crossing checks
            </li>
          </ul>
        </div>

        {/* Shortcuts & Verification Notice */}
        <div className="footer-col shortcuts-col">
          <h4 className="footer-heading">Review Studio Tools</h4>
          <p className="footer-notice">
            Synthetic fixture transcripts are restricted to tests. All captions reflect actual
            acoustic inference and review queue ranking.
          </p>

          <button
            type="button"
            className="footer-shortcuts-btn"
            onClick={() => setShowShortcuts(!showShortcuts)}
          >
            <span>⌨ Keyboard Shortcuts</span>
            <span className="shortcuts-toggle-icon">{showShortcuts ? '▲' : '▼'}</span>
          </button>

          {showShortcuts && (
            <div className="shortcuts-popup-card">
              <div className="shortcut-row">
                <kbd>Space</kbd>
                <span>Play / Pause</span>
              </div>
              <div className="shortcut-row">
                <kbd>J</kbd> / <kbd>L</kbd>
                <span>Seek -2s / +2s</span>
              </div>
              <div className="shortcut-row">
                <kbd>Ctrl</kbd> + <kbd>Z</kbd>
                <span>1-Click Undo Deleted Cue</span>
              </div>
              <div className="shortcut-row">
                <kbd>1</kbd> / <kbd>2</kbd> / <kbd>3</kbd>
                <span>Switch Language (বাংলা / EN / HI)</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="footer-bottom-bar">
        <div className="footer-copyright">
          © {new Date().getFullYear()} Shruti - Hoichoi Caption Studio. Provisional
          thresholds calibrated for production compliance.
        </div>
      </div>
    </footer>
  );
}
