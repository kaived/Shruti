import os

from ai.acoustics import WaveAcousticAnalyzer
from ai.aligner import MonotonicAligner
from ai.shots import SceneCutDetector
from ai.transcriber import GroqWhisperTranscriber
from ai.translator import GroqLLMTranslator
from core.config import Settings
from providers.base import Providers, ProviderUnavailable


def create_providers(settings: Settings) -> Providers:
    """Instantiate and return the verified AI model provider suite."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ProviderUnavailable("GROQ_API_KEY is required for Groq ASR and translation.")

    return Providers(
        transcriber=GroqWhisperTranscriber(api_key=groq_key),
        aligner=MonotonicAligner(),
        acoustics=WaveAcousticAnalyzer(),
        shots=SceneCutDetector(),
        translator=GroqLLMTranslator(api_key=groq_key),
    )
