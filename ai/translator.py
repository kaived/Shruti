import json
import os

# pyrefly: ignore [missing-import]
from groq import Groq

from core.contracts import Cue


class GroqLLMTranslator:
    """Strict Bengali-to-English/Hindi cue translation with source lineage."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client=None,
        model: str = "llama-3.3-70b-versatile",
        batch_size: int = 40,
    ):
        if batch_size <= 0:
            raise ValueError("Translation batch size must be positive")
        self.client = client or Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.model = model
        self.batch_size = batch_size

    def _translate_batch(self, cues: list[Cue], language: str) -> dict[str, str]:
        lang_name = {"en": "English", "hi": "Hindi"}[language]
        input_payload = [{"id": cue.id, "text": cue.text} for cue in cues]
        system_prompt = (
            f"Translate Bengali film and TV subtitle cues into natural {lang_name}. "
            "Translate only the supplied dialogue: do not add explanations, missing dialogue, "
            "speaker names, sound labels, or facts. Preserve negation, names, numbers, relationships, "
            "register, and inline English. Return exactly one non-empty translation for every input id. "
            "Return only a JSON object with this shape: "
            '{"translations":[{"id":"cue_id","text":"translated_text"}]}'
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(input_payload, ensure_ascii=False),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw_text = response.choices[0].message.content
        if not raw_text:
            raise RuntimeError(f"Groq returned an empty {language} translation")
        payload = json.loads(raw_text)
        items = payload.get("translations") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise RuntimeError(f"Groq returned an invalid {language} translation payload")

        expected = {cue.id: cue.text.strip() for cue in cues}
        translations: dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict):
                raise RuntimeError(f"Groq returned an invalid {language} translation item")
            cue_id, text = item.get("id"), item.get("text")
            if cue_id not in expected or not isinstance(text, str) or not text.strip():
                raise RuntimeError(f"Groq returned an invalid {language} translation item")
            if cue_id in translations:
                raise RuntimeError(f"Groq returned duplicate translation id {cue_id}")
            clean_text = text.strip()
            if clean_text == expected[cue_id]:
                raise RuntimeError(f"Groq copied untranslated source cue {cue_id}")
            translations[cue_id] = clean_text

        missing = expected.keys() - translations.keys()
        if missing:
            raise RuntimeError(f"Groq omitted {language} translations for: {sorted(missing)}")
        return translations

    def translate(self, cues: list[Cue], language: str) -> list[Cue]:
        if language not in {"en", "hi"}:
            raise ValueError(f"Unsupported translation language: {language}")
        if not cues:
            return []
        if len({cue.id for cue in cues}) != len(cues):
            raise ValueError("Translation input cue IDs must be unique")

        translated: dict[str, str] = {}
        for start in range(0, len(cues), self.batch_size):
            translated.update(
                self._translate_batch(cues[start : start + self.batch_size], language)
            )

        return [
            Cue(
                id=f"{cue.id}-{language}",
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                language=language,
                text=translated[cue.id],
                kind=cue.kind,
                speaker_ids=cue.speaker_ids,
                source_word_ids=cue.source_word_ids,
                source_cue_ids=[cue.id],
            )
            for cue in cues
        ]
