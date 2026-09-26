"""Real inference integration boundary. No canned transcripts or implicit mock provider."""

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol

from core.config import Settings
from core.contracts import AudioEvidence, Cue, ShotAnalysis, Transcript


class ProviderUnavailable(RuntimeError):
    pass


class Transcriber(Protocol):
    def transcribe(self, audio: Path) -> Transcript: ...


class Aligner(Protocol):
    def align(self, audio: Path, transcript: Transcript) -> Transcript: ...


class Diarizer(Protocol):
    def diarize(self, audio: Path, transcript: Transcript) -> Transcript: ...


class AcousticAnalyzer(Protocol):
    def analyze(self, audio: Path, duration_ms: int) -> AudioEvidence: ...


class ShotDetector(Protocol):
    def detect(self, video: Path, duration_ms: int) -> ShotAnalysis: ...


class Translator(Protocol):
    def translate(self, cues: list[Cue], language: str) -> list[Cue]: ...


@dataclass
class Providers:
    transcriber: Transcriber
    aligner: Aligner
    acoustics: AcousticAnalyzer
    shots: ShotDetector
    translator: Translator
    diarizer: Diarizer | None = None
    normalizer: Any = None  # optional code-switch respelling: normalize(Transcript) -> Transcript


def load_providers(settings: Settings) -> Providers:
    if not settings.provider_factory or settings.provider_revision == "unconfigured":
        raise ProviderUnavailable(
            "Connect real ASR/diarization, alignment, acoustic evidence, shot detection and "
            "translation adapters. Set SHRUTI_PROVIDER_FACTORY and SHRUTI_PROVIDER_REVISION."
        )
    module, separator, name = settings.provider_factory.partition(":")
    if not separator:
        raise ProviderUnavailable("Provider factory must use the trusted module:function format.")
    providers = getattr(import_module(module), name)(settings)
    if not isinstance(providers, Providers):
        raise ProviderUnavailable("Provider factory must return a Providers instance.")
    return providers
