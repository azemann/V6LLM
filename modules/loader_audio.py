from functools import lru_cache
from pathlib import Path
import os

WHISPER_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "whisper"

@lru_cache(maxsize=1)
def get_whisper_model():
    from faster_whisper import WhisperModel

    WHISPER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    return WhisperModel(
        "tiny",
        device="cpu",
        compute_type="int8",
        cpu_threads=max(1, min(2, os.cpu_count() or 1)),
        num_workers=1,
        download_root=str(WHISPER_MODEL_DIR),
    )

def transcribe_audio(audio_path):
    segments, _ = get_whisper_model().transcribe(
        audio_path,
        language="fr",
        beam_size=1,
        vad_filter=True,
    )
    transcript = " ".join(segment.text.strip() for segment in segments).strip()
    return transcript or "❌ Aucun dialogue détecté."
