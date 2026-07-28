import sys

import requests

from backend.config import MODEL_DIR, MODEL_PATH, MODEL_URL


def download_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists():
        size_gib = MODEL_PATH.stat().st_size / (1024**3)
        print(f"Qwen est déjà présent : {MODEL_PATH} ({size_gib:.1f} Gio)")
        return MODEL_PATH

    partial_path = MODEL_PATH.with_suffix(MODEL_PATH.suffix + ".part")
    print("Téléchargement explicite de Qwen 2.5 1.5B Q4…")
    try:
        with requests.get(MODEL_URL, stream=True, timeout=(10, 120)) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            with partial_path.open("wb") as model_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    model_file.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = downloaded * 100 // total
                        print(
                            f"\rProgression : {percent:3d}%"
                            f" ({downloaded / 1024**2:.0f} Mio)",
                            end="",
                            flush=True,
                        )
        if total:
            print()
        partial_path.replace(MODEL_PATH)
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise

    print(f"Modèle prêt : {MODEL_PATH}")
    return MODEL_PATH


if __name__ == "__main__":
    try:
        download_model()
    except Exception as error:
        print(f"Échec du téléchargement : {error}", file=sys.stderr)
        raise SystemExit(1) from error
