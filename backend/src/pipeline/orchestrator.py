import hashlib
import json
import logging
import time
from pathlib import Path

from pydantic import TypeAdapter

from captions.exporters import srt, webvtt
from captions.segmentation import segment
from core.config import Settings
from core.contracts import AudioEvidence, CaptionProfile, Cue, ShotAnalysis, Transcript
from core.database import Database, Job
from media.audio import MediaError, prepare_media
from providers.base import ProviderUnavailable, load_providers
from qc.evaluation import evaluate

log = logging.getLogger(__name__)
PIPELINE_VERSION = "0.2.0"


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def value_fingerprint(value) -> str:
    def serializable(item):
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")
        raise TypeError(f"Cannot fingerprint {type(item)!r}")

    encoded = json.dumps(
        value,
        default=serializable,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def run_pipeline(job_id: str, settings: Settings | None = None) -> None:
    settings = settings or Settings()
    db = Database(settings)
    if not db.claim(job_id):
        return
    root = settings.data_dir / "jobs" / job_id
    metrics: dict = {}
    started = time.monotonic()
    try:
        db.update_job(job_id, stage="configuration")
        # Detect missing inference setup before performing expensive media extraction.
        providers = load_providers(settings)
        with db.sessions() as session:
            job = session.get(Job, job_id)
            checksum = job.sha256
            attempt = job.attempts
        profile = CaptionProfile()
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "media": checksum,
                    "pipeline": PIPELINE_VERSION,
                    "provider_factory": settings.provider_factory,
                    "provider_revision": settings.provider_revision,
                    "profile": profile.model_dump(),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[:24]
        run_dir = root / "runs" / fingerprint
        run_dir.mkdir(parents=True, exist_ok=True)

        def checkpoint(stage, schema, operation, *, dependency=None, is_complete=lambda _: True):
            db.update_job(job_id, stage=stage)
            tick = time.monotonic()
            path = run_dir / f"{stage}.json"
            meta_path = run_dir / f"{stage}.meta.json"
            adapter = TypeAdapter(schema)
            dependency_hash = value_fingerprint(dependency)
            cached = False
            result = None
            if path.exists() and meta_path.exists():
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                if metadata.get("dependency") == dependency_hash:
                    candidate = adapter.validate_json(path.read_bytes())
                    if is_complete(candidate) or metadata.get("attempt") == attempt:
                        result, cached = candidate, True
            if not cached:
                result = adapter.validate_python(operation())
                write_json(path, adapter.dump_python(result, mode="json"))
                write_json(
                    meta_path,
                    {
                        "dependency": dependency_hash,
                        "complete": bool(is_complete(result)),
                        "attempt": attempt,
                    },
                )
            metrics[stage] = {"seconds": round(time.monotonic() - tick, 3), "cached": cached}
            db.update_job(job_id, stage_metrics=dict(metrics))
            return result

        db.update_job(job_id, stage="media")
        media_path, audio_path = root / "media.json", root / "audio.wav"
        tick = time.monotonic()
        media_cached = media_path.exists() and audio_path.exists()
        if media_cached:
            media = json.loads(media_path.read_text(encoding="utf-8"))
        else:
            media = prepare_media(root / "source", audio_path, settings)
            write_json(media_path, media)
        metrics["media"] = {"seconds": round(time.monotonic() - tick, 3), "cached": media_cached}
        db.update_job(job_id, media={**media, "run_id": fingerprint}, stage_metrics=dict(metrics))
        duration_ms = media["duration_ms"]
        raw = checkpoint(
            "transcription",
            Transcript,
            lambda: providers.transcriber.transcribe(audio_path),
            dependency={"media_sha256": checksum},
            is_complete=lambda value: value.recognition_complete,
        )
        aligned = checkpoint(
            "alignment",
            Transcript,
            lambda: providers.aligner.align(audio_path, raw),
            dependency=raw,
            is_complete=lambda value: value.alignment_complete,
        )
        if [(w.id, w.text, w.speaker_id) for w in raw.words] != [
            (w.id, w.text, w.speaker_id) for w in aligned.words
        ]:
            raise ValueError("Alignment must preserve recognized words and speaker references")
        if (
            raw.recognition_complete != aligned.recognition_complete
            or raw.diarization_complete != aligned.diarization_complete
        ):
            raise ValueError("Alignment cannot change recognition or diarization completion")
        evidence = checkpoint(
            "acoustics",
            AudioEvidence,
            lambda: providers.acoustics.analyze(audio_path, duration_ms),
            dependency={"duration_ms": duration_ms},
            is_complete=lambda value: value.complete,
        )
        shots = checkpoint(
            "shots",
            ShotAnalysis,
            lambda: providers.shots.detect(root / "source", duration_ms),
            dependency={"duration_ms": duration_ms},
            is_complete=lambda value: value.complete,
        )
        if any(t < 0 or t > duration_ms for t in shots.cuts_ms):
            raise ValueError("Shot boundaries must be within the media timeline")
        bn = checkpoint(
            "bengali_cues",
            list[Cue],
            lambda: segment(aligned, evidence, shots, profile),
            dependency={"transcript": aligned, "audio": evidence, "shots": shots},
        )
        speech_cues = [c for c in bn if c.kind == "speech"]
        tracks = {"bn": bn}
        for language in ("en", "hi"):
            tracks[language] = checkpoint(
                f"translation_{language}",
                list[Cue],
                lambda language=language: providers.translator.translate(speech_cues, language),
                dependency=speech_cues,
            )
        db.update_job(job_id, stage="quality_control")
        report = evaluate(tracks, aligned, evidence, shots, duration_ms, profile)
        names = {
            s.id: s.display_name
            for s in aligned.speakers
            if s.name_status == "confirmed" and s.display_name
        }
        db.update_job(job_id, stage="export")
        (run_dir / "bengali.vtt").write_text(webvtt(bn, names, profile), encoding="utf-8")
        for language, filename in (("en", "english"), ("hi", "hindi")):
            (run_dir / f"{filename}.srt").write_text(
                srt(tracks[language], names, profile), encoding="utf-8"
            )
            (run_dir / f"{filename}.vtt").write_text(
                webvtt(tracks[language], names, profile), encoding="utf-8"
            )
        write_json(run_dir / "qc_report.json", report.model_dump(mode="json"))
        write_json(
            run_dir / "tracks.json",
            {
                language: [c.model_dump(mode="json") for c in cues]
                for language, cues in tracks.items()
            },
        )
        write_json(
            run_dir / "manifest.json",
            {
                "job_id": job_id,
                "input_sha256": checksum,
                "pipeline_version": PIPELINE_VERSION,
                "provider_revision": settings.provider_revision,
                "profile": profile.model_dump(),
                "qc_status": report.status,
                "release_ready": False,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "stages": metrics,
                "reviewed": False,
                "output_kind": "original_automated_draft",
            },
        )
        db.update_job(
            job_id,
            state="partial" if report.status == "incomplete" else "completed",
            stage="finished",
            qc_state=report.status,
            error_code=None,
            message=None,
            stage_metrics={**metrics, "total_seconds": round(time.monotonic() - started, 3)},
        )
    except ProviderUnavailable as exc:
        db.update_job(
            job_id,
            state="blocked",
            stage="configuration",
            qc_state="incomplete",
            error_code="PROVIDER_NOT_CONFIGURED",
            message=str(exc),
        )
    except MediaError as exc:
        db.update_job(
            job_id, state="failed", qc_state="incomplete", error_code=exc.code, message=str(exc)
        )
    except Exception:
        log.exception("Pipeline failed for job %s", job_id)
        db.update_job(
            job_id,
            state="failed",
            qc_state="incomplete",
            error_code="PIPELINE_FAILED",
            message="Processing failed. Check worker logs; successful checkpoints are retained.",
        )
        raise
    finally:
        db.engine.dispose()
