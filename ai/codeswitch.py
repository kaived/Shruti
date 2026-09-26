"""Restore code-switched English words that Whisper wrote in Bengali script.

Whisper with language="bn" transliterates spoken English ("meeting" -> "মিটিং").
An LLM identifies those words and returns their Latin spelling. It may only respell
an existing word: word count, IDs, timing and speakers are unchanged, the raw ASR
text is kept in ``raw_text``, and any invalid response leaves the word untouched.
"""

import json
import logging
import os
import re

from core.contracts import Transcript
from groq import APIError, Groq

log = logging.getLogger(__name__)
LATIN = re.compile(r"[A-Za-z]")
BENGALI = re.compile(r"[ঀ-৿]")
# Native words an LLM tends to misread as English (সেটার -> "set-এর"). Never respelled.
NATIVE = {
    "সেটা", "সেটার", "সেটাই", "সেটাকে", "এটা", "এটার", "এটাই", "ওটা", "ওটার",
    "সেই", "কেন", "কি", "কী", "না", "তো", "হ্যাঁ", "আমি", "তুমি", "আপনি",
}  # fmt: skip

PROMPT = (
    "You receive numbered words from an automatic Bengali transcript of spoken dialogue. "
    "Speakers often switch to English inline, e.g. 'ওর office-এ একটা meeting আছে', but the "
    "recognizer wrote those English words in Bengali script (মিটিং, অফিসে). Identify ONLY words "
    "that are English words spoken as English and give their standard English spelling. Keep an "
    "attached Bengali case suffix in Bengali script after a hyphen (অফিসে -> office-এ, "
    "মিটিংয়ে -> meeting-এ). Never change native Bengali words, names, numbers or words of "
    "Sanskrit/Persian origin that are ordinary Bengali (e.g. টেবিল stays only if unsure). "
    "Bengali pronouns and demonstratives (সেটা, সেটার, এটা, ওটা) are never English. "
    "Never merge, split, add or remove words. If unsure, leave the word out. Return only JSON: "
    '{"replacements":[{"i":<word number>,"text":"<english spelling>"}]}'
)


class GroqCodeSwitchNormalizer:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        client=None,
        model: str | None = None,
        batch_size: int = 60,
    ):
        self.client = client or Groq(
            api_key=api_key or os.getenv("GROQ_API_KEY"), max_retries=6
        )
        self.model = model or os.getenv(
            "SHRUTI_TRANSLATION_MODEL", "openai/gpt-oss-120b"
        )
        self.batch_size = batch_size

    def _batch(self, words: list[tuple[int, str]]) -> dict[int, str]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        [{"i": index, "w": text} for index, text in words],
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        allowed = dict(words)
        result: dict[int, str] = {}
        for item in (
            payload.get("replacements", []) if isinstance(payload, dict) else []
        ):
            if not isinstance(item, dict):
                continue
            index, text = item.get("i"), item.get("text")
            if index not in allowed or not isinstance(text, str):
                continue
            text = text.strip()
            # One token, must contain Latin letters, source must have been Bengali script.
            if not text or " " in text or not LATIN.search(text):
                continue
            if allowed[index].strip("।.?!, ") in NATIVE:
                continue
            if (
                not BENGALI.search(allowed[index])
                or len(text) > 3 * len(allowed[index]) + 4
            ):
                continue
            # Keep the recognizer's sentence punctuation; cue segmentation relies on it.
            source = allowed[index].rstrip()
            tail = source[len(source.rstrip("।.?!,")) :]
            result[index] = text.rstrip("।.?!,") + tail
        return result

    def _batch_with_retry(self, batch: list[tuple[int, str]]) -> dict[int, str]:
        """JSON mode occasionally rejects a generation (HTTP 400): retry, then split in half."""
        for _ in range(2):
            try:
                return self._batch(batch)
            except (APIError, json.JSONDecodeError):
                log.warning(
                    "Code-switch batch of %s words failed; retrying", len(batch)
                )
        if len(batch) <= 10:
            log.error("Code-switch left %s words as recognized", len(batch))
            return {}
        middle = len(batch) // 2
        return {
            **self._batch_with_retry(batch[:middle]),
            **self._batch_with_retry(batch[middle:]),
        }

    def normalize(self, transcript: Transcript) -> Transcript:
        indexed = list(enumerate(word.text for word in transcript.words))
        replacements: dict[int, str] = {}
        for start in range(0, len(indexed), self.batch_size):
            batch = indexed[start : start + self.batch_size]
            replacements.update(self._batch_with_retry(batch))
        words = [
            word.model_copy(update={"text": replacements[index], "raw_text": word.text})
            if index in replacements
            else word
            for index, word in enumerate(transcript.words)
        ]
        return transcript.model_copy(
            update={
                "words": words,
                "provider": f"{transcript.provider}+codeswitch/{self.model}",
            }
        )
