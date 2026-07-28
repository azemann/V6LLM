import subprocess
import tempfile
import os
from .loader_audio import transcribe_audio

def transcribe_video_audio(video_path):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
        audio_path = audio_file.name
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-acodec",
                "libmp3lame",
                audio_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            return "❌ Erreur d'extraction audio."
        return transcribe_audio(audio_path)
    finally:
        os.unlink(audio_path)
