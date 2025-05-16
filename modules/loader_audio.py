import subprocess

def transcribe_audio(audio_path):
    result = subprocess.run(["whisper", audio_path, "--model", "base", "--language", "fr"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else "❌ Erreur transcription audio."
