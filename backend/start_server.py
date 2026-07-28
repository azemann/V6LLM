import os
from pathlib import Path
import shutil
import sys

from backend.config import (
    API_KEY,
    CONTEXT_SIZE,
    LLAMA_INSTALL_DIR,
    MODEL_ALIAS,
    MODEL_PATH,
    SERVER_HOST,
    SERVER_PORT,
    THREADS,
)


def find_llama_server():
    configured_binary = os.getenv("LLAMA_SERVER_BIN")
    if configured_binary:
        candidate = Path(configured_binary).expanduser().resolve()
        if candidate.is_file():
            return candidate

    system_binary = shutil.which("llama-server")
    if system_binary:
        return Path(system_binary)

    local_binaries = sorted(
        LLAMA_INSTALL_DIR.rglob("llama-server"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if local_binaries:
        return local_binaries[0]
    return None


def main():
    binary = find_llama_server()
    if not binary:
        print(
            "llama-server n'est pas installé.\n"
            "Exécute : .venv/bin/python -m backend.install_llama_server",
            file=sys.stderr,
        )
        return 1
    if not MODEL_PATH.exists():
        print(
            f"Le modèle est absent : {MODEL_PATH}\n"
            "Exécute : .venv/bin/python -m backend.download_model",
            file=sys.stderr,
        )
        return 1

    command = [
        str(binary),
        "--model",
        str(MODEL_PATH),
        "--alias",
        MODEL_ALIAS,
        "--api-key",
        API_KEY,
        "--host",
        SERVER_HOST,
        "--port",
        str(SERVER_PORT),
        "--ctx-size",
        str(CONTEXT_SIZE),
        "--threads",
        str(THREADS),
        "--threads-batch",
        str(THREADS),
        "--batch-size",
        "64",
        "--ubatch-size",
        "64",
        "--parallel",
        "1",
        "--n-gpu-layers",
        "0",
    ]
    print(
        f"Démarrage de llama-server sur "
        f"http://{SERVER_HOST}:{SERVER_PORT}"
    )
    os.execv(str(binary), command)


if __name__ == "__main__":
    raise SystemExit(main())
