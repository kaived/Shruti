import logging
from pathlib import Path

from core.contracts import ShotAnalysis

log = logging.getLogger(__name__)


class SceneCutDetector:
    """Detect camera cuts with PySceneDetect and expose decode failures."""

    def detect(self, video: Path, duration_ms: int) -> ShotAnalysis:
        try:
            from scenedetect import ContentDetector, detect

            scene_list = detect(str(video), ContentDetector(threshold=27.0))
            cuts_ms = sorted(
                {
                    round(scene[0].get_seconds() * 1000)
                    for scene in scene_list
                    if 0 < round(scene[0].get_seconds() * 1000) < duration_ms
                }
            )
        except Exception:
            log.exception("Shot detection failed for %s", video)
            return ShotAnalysis(
                provider="pyscenedetect",
                model_version="0.7.1",
                complete=False,
                cuts_ms=[],
            )

        return ShotAnalysis(
            provider="pyscenedetect",
            model_version="0.7.1",
            complete=True,
            cuts_ms=cuts_ms,
        )
