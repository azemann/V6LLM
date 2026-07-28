import platform
import sys
import tarfile
import tempfile
from pathlib import Path

import requests

from backend.config import LLAMA_INSTALL_DIR


RELEASES_URL = (
    "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=10"
)


def install_llama_server():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError(
            "L'installateur automatique attend Linux x86_64."
        )

    print("Recherche de la dernière version officielle de llama.cpp…")
    releases_response = requests.get(
        RELEASES_URL,
        headers={"Accept": "application/vnd.github+json"},
        timeout=30,
    )
    releases_response.raise_for_status()

    selected_release = None
    selected_asset = None
    for release in releases_response.json():
        expected_name = (
            f"llama-{release['tag_name']}-bin-ubuntu-x64.tar.gz"
        )
        asset = next(
            (
                candidate
                for candidate in release.get("assets", [])
                if candidate["name"] == expected_name
            ),
            None,
        )
        if asset:
            selected_release = release
            selected_asset = asset
            break

    if not selected_release or not selected_asset:
        raise RuntimeError(
            "Aucune release récente ne contient le binaire Ubuntu x64."
        )

    tag = selected_release["tag_name"]
    archive_name = selected_asset["name"]
    archive_url = selected_asset["browser_download_url"]
    destination = LLAMA_INSTALL_DIR / tag
    existing_binary = next(destination.rglob("llama-server"), None)
    if existing_binary and existing_binary.is_file():
        print(f"llama-server est déjà installé : {existing_binary}")
        return existing_binary

    destination.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement de llama.cpp {tag}…")
    with tempfile.TemporaryDirectory() as temporary_dir:
        archive_path = Path(temporary_dir) / archive_name
        with requests.get(
            archive_url,
            stream=True,
            timeout=(10, 120),
        ) as response:
            response.raise_for_status()
            with archive_path.open("wb") as archive_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        archive_file.write(chunk)

        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(destination, filter="data")

    binary = next(destination.rglob("llama-server"), None)
    if not binary:
        raise RuntimeError("Le binaire llama-server est absent de l'archive.")
    binary.chmod(binary.stat().st_mode | 0o111)
    print(f"llama-server installé : {binary}")
    return binary


if __name__ == "__main__":
    try:
        install_llama_server()
    except Exception as error:
        print(f"Échec de l'installation : {error}", file=sys.stderr)
        raise SystemExit(1) from error
