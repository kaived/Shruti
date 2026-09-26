import os

from core.config import Settings
from groq import Groq
from providers.base import Providers, ProviderUnavailable

from ai.acoustics import ModelAcousticAnalyzer
from ai.aligner import StableWhisperAligner
from ai.codeswitch import GroqCodeSwitchNormalizer
from ai.diarizer import PyannoteDiarizer
from ai.shots import SceneCutDetector
from ai.transcriber import GroqWhisperTranscriber
from ai.translator import GroqLLMTranslator


def create_providers(settings: Settings) -> Providers:
    """Instantiate and return the verified AI model provider suite."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ProviderUnavailable(
            "GROQ_API_KEY is required for Groq ASR and translation."
        )

    client = Groq(api_key=groq_key, max_retries=6)
    transcriber = GroqWhisperTranscriber(client=client)
    translator = GroqLLMTranslator(client=client)
    try:
        available = {
            model.id
            for model in client.models.list().data
            if getattr(model, "active", True)
        }
    except Exception as exc:
        raise ProviderUnavailable("Could not verify accessible Groq models") from exc
    missing = {transcriber.model, translator.model} - available
    if missing:
        raise ProviderUnavailable(
            f"Groq account cannot access required models: {sorted(missing)}"
        )

    return Providers(
        transcriber=transcriber,
        aligner=StableWhisperAligner(),
        acoustics=ModelAcousticAnalyzer(),
        shots=SceneCutDetector(),
        translator=translator,
        diarizer=PyannoteDiarizer(token=os.getenv("SHRUTI_HF_TOKEN")),
        normalizer=GroqCodeSwitchNormalizer(client=client),
    )
