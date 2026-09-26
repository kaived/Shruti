import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '../shared/ui';

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
                        Production-grade Bengali closed captioning & multi-lingual subtitling engine. Acoustic-evidence verification protects against unflagged hallucinations
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
                            <strong>Alignment & Shots:</strong> stable-ts forced word alignment & PySceneDetect shot cuts
                        </li>
                        <li>
                            <strong>Speaker Tracking:</strong> pyannote diarization with stable speaker IDs; rename speakers in the studio
                        </li>
                        <li>
                            <strong>Translation:</strong> Groq GPT-OSS 120B (Bengali → English & Hindi, inline English kept)
                        </li>
                        <li>
                            <strong>Quality Control:</strong> Silero VAD + PANNs hallucination & silence audit, reading rate & shot-crossing checks
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

                    <Button
                        variant="secondary"
                        size="md"
                        className="!bg-white/10 !border-white/20 !text-slate-200 hover:!bg-white/20 !shadow-none self-start"
                        onClick={() => setShowShortcuts(!showShortcuts)}
                        iconRight={
                            showShortcuts ? (
                                <ChevronUp size={14} className="text-slate-400 shrink-0 ml-1.5" />
                            ) : (
                                <ChevronDown size={14} className="text-slate-400 shrink-0 ml-1.5" />
                            )
                        }
                    >
                        ⌨ Keyboard Shortcuts
                    </Button>

                    {showShortcuts && (
                        <div className="shortcuts-popup-card">
                            <div className="shortcut-row">
                                <kbd>Space</kbd>
                                <span>Play / Pause</span>
                            </div>
                            <div className="shortcut-row">
                                <kbd>J</kbd> / <kbd>L</kbd>
                                <span>Go back / forward 2 seconds</span>
                            </div>
                            <div className="shortcut-row">
                                <kbd>1</kbd> / <kbd>2</kbd> / <kbd>3</kbd>
                                <span>Show Bengali / English / Hindi</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="footer-bottom-bar">
                <div className="footer-copyright">
                    © {new Date().getFullYear()} Shruti Caption Studio. Provisional
                    thresholds calibrated for production compliance.
                </div>
            </div>
        </footer>
    );
}
