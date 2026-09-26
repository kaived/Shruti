import json
import logging
import os
import re

from core.contracts import Cue
from groq import APIError, Groq

log = logging.getLogger(__name__)
BENGALI = re.compile(r"[ঀ-৿]")


class GroqLLMTranslator:
    """Strict Bengali-to-English/Hindi cue translation with source lineage."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client=None,
        model: str | None = None,
        batch_size: int = 40,
    ):
        if batch_size <= 0:
            raise ValueError("Translation batch size must be positive")
        self.client = client or Groq(
            api_key=api_key or os.getenv("GROQ_API_KEY"), max_retries=6
        )
        self.model = model or os.getenv(
            "SHRUTI_TRANSLATION_MODEL", "openai/gpt-oss-120b"
        )
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
        payload = json.loads(response.choices[0].message.content or "{}")
        items = payload.get("translations") if isinstance(payload, dict) else None
        expected = {cue.id: cue.text.strip() for cue in cues}
        translations: dict[str, str] = {}
        # Keep every valid item; anything invalid, duplicated or untranslated is left
        # missing so the caller can retry just those cues.
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            cue_id, text = item.get("id"), item.get("text")
            if (
                cue_id not in expected
                or cue_id in translations
                or not isinstance(text, str)
            ):
                continue
            clean_text = text.strip()
            if not clean_text:
                continue
            # Identical output is only a copy when the source is Bengali; an already
            # English (code-switched) cue legitimately translates to itself.
            if clean_text == expected[cue_id] and BENGALI.search(clean_text):
                continue
            translations[cue_id] = clean_text
        return translations

    def _translate_with_retry(self, cues: list[Cue], language: str) -> dict[str, str]:
        """Retry missing cues in progressively smaller groups; never fail the whole job."""
        translations: dict[str, str] = {}
        pending = list(cues)
        for group_size in (len(cues), max(1, len(cues) // 4), 1):
            if not pending:
                break
            for start in range(0, len(pending), group_size):
                group = pending[start : start + group_size]
                try:
                    translations.update(self._translate_batch(group, language))
                except (APIError, json.JSONDecodeError):
                    log.warning(
                        "Translation request for %s %s cues failed",
                        len(group),
                        language,
                    )
            pending = [cue for cue in pending if cue.id not in translations]
        if pending:
            log.error(
                "No %s translation for %s cues; QC will flag them",
                language,
                len(pending),
            )
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
                self._translate_with_retry(
                    cues[start : start + self.batch_size], language
                )
            )

        return [
            Cue(
                id=f"{cue.id}-{language}",
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                language=language,
                text=translated.get(cue.id, cue.text),
                kind=cue.kind,
                speaker_ids=cue.speaker_ids,
                source_word_ids=cue.source_word_ids,
                source_cue_ids=[cue.id],
            )
            for cue in cues
        ]
