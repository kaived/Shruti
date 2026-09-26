from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Interval(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_ms <= self.start_ms:
            raise ValueError("Interval must have positive duration")
        return self


class Word(Interval):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    speaker_id: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class Speaker(BaseModel):
    id: str
    display_name: str | None = None
    name_status: Literal["unknown", "suggested", "confirmed"] = "unknown"
    name_evidence: list[Interval] = []


class Transcript(BaseModel):
    provider: str
    model_version: str
    words: list[Word]
    speakers: list[Speaker]
    recognition_complete: bool = False
    diarization_complete: bool = False
    alignment_complete: bool = False

    @model_validator(mode="after")
    def references(self):
        ids = [w.id for w in self.words]
        speakers = [s.id for s in self.speakers]
        if len(set(ids)) != len(ids) or len(set(speakers)) != len(speakers):
            raise ValueError("Duplicate word/speaker IDs")
        if any(w.speaker_id and w.speaker_id not in speakers for w in self.words):
            raise ValueError("Unknown speaker reference")
        if ids and any(
            a.start_ms > b.start_ms for a, b in zip(self.words, self.words[1:], strict=False)
        ):
            raise ValueError("Words must be ordered on the global timeline")
        return self


class SoundEvent(Interval):
    id: str
    label_bn: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)


class AudioEvidence(BaseModel):
    provider: str
    model_version: str
    complete: bool
    evaluated_duration_ms: int = Field(ge=0)
    independent_of_asr: bool
    speech: list[Interval]
    music: list[Interval] = []
    sounds: list[SoundEvent] = []


class ShotAnalysis(BaseModel):
    provider: str
    model_version: str
    complete: bool
    cuts_ms: list[int] = []


class Cue(Interval):
    id: str
    language: Literal["bn", "en", "hi"]
    text: str = Field(min_length=1)
    kind: Literal["speech", "sound"] = "speech"
    speaker_ids: list[str] = []
    source_word_ids: list[str] = []
    source_cue_ids: list[str] = []


class CaptionProfile(BaseModel):
    version: str = "provisional-1"
    official: bool = False
    character_counting: Literal["unicode_code_points"] = "unicode_code_points"
    max_cps: dict[str, float] = {"bn": 17, "en": 20, "hi": 17}
    max_line_length: int = 42
    max_lines: int = 2
    min_duration_ms: int = 800
    max_duration_ms: int = 7000
    min_speech_support: float = 0.35


class Issue(BaseModel):
    id: str
    code: str
    severity: Literal["critical", "high", "medium"]
    language: str
    start_ms: int
    end_ms: int
    cue_ids: list[str] = []
    reason: str
    evidence: dict = {}
    review_state: Literal["open", "resolved"] = "open"


class QCReport(BaseModel):
    status: Literal["incomplete", "review_required", "automated_checks_passed"]
    release_ready: Literal[False] = False
    profile: CaptionProfile
    checks: dict[str, str]
    issues: list[Issue]
    limitations: list[str]
