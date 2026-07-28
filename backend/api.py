import json
import os
from pathlib import Path
import tempfile

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import API_KEY, MODEL_ALIAS
from modules.loader_audio import transcribe_audio
from modules.loader_text import load_text_file
from modules.loader_video import transcribe_video_audio


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = PROJECT_ROOT / "frontend" / "dist"
LLAMA_SERVER_URL = os.getenv(
    "AZE_LLM_SERVER_URL",
    "http://127.0.0.1:8080",
).rstrip("/")
DEFAULT_SYSTEM_PROMPT = (
    "Tu es un assistant utile. Réponds clairement et en français, "
    "sauf si l'utilisateur demande une autre langue."
)
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".mp3",
    ".wav",
    ".mp4",
    ".mov",
}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

app = FastAPI(title="AZE LLM API", version="1.0.0")


class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = Field(default=0.4, ge=0, le=1)
    max_tokens: int = Field(default=256, ge=64, le=512)
    document_content: str | None = Field(default=None, max_length=100_000)


def auth_headers():
    return {"Authorization": f"Bearer {API_KEY}"}


def bounded_messages(request: ChatRequest, max_chars: int = 6_000):
    messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    used_chars = len(DEFAULT_SYSTEM_PROMPT)

    if request.document_content:
        document = request.document_content[:4_000]
        messages.append(
            {
                "role": "system",
                "content": (
                    "Voici le contenu du fichier fourni par l'utilisateur :\n"
                    f"{document}"
                ),
            }
        )
        used_chars += len(document)

    allowed_roles = {"user", "assistant"}
    recent_messages = [
        {"role": message.role, "content": message.content}
        for message in request.messages
        if message.role in allowed_roles
    ]
    kept_messages = []
    for message in reversed(recent_messages):
        content = message["content"]
        if used_chars + len(content) > max_chars:
            if not kept_messages and message["role"] == "user":
                remaining = max(1, max_chars - used_chars)
                kept_messages.append(
                    {"role": "user", "content": content[-remaining:]}
                )
            break
        kept_messages.append(message)
        used_chars += len(content)

    messages.extend(reversed(kept_messages))
    return messages


@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(
                f"{LLAMA_SERVER_URL}/health",
                headers=auth_headers(),
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        return {
            "ready": False,
            "detail": str(error),
            "model": MODEL_ALIAS,
        }

    return {
        "ready": payload.get("status") == "ok",
        "detail": payload.get("status", "état inconnu"),
        "model": MODEL_ALIAS,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.messages or request.messages[-1].role != "user":
        raise HTTPException(
            status_code=422,
            detail="La conversation doit se terminer par un message utilisateur.",
        )

    payload = {
        "model": MODEL_ALIAS,
        "messages": bounded_messages(request),
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "stream": True,
    }

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600, connect=5)) as client:
                async with client.stream(
                    "POST",
                    f"{LLAMA_SERVER_URL}/v1/chat/completions",
                    headers={
                        **auth_headers(),
                        "Accept": "text/event-stream",
                    },
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        detail = (await response.aread()).decode(
                            "utf-8",
                            errors="replace",
                        )
                        yield json.dumps(
                            {
                                "error": (
                                    f"llama-server a répondu "
                                    f"{response.status_code}: {detail[:300]}"
                                )
                            },
                            ensure_ascii=False,
                        ) + "\n"
                        return

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line.removeprefix("data:").strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        if "error" in chunk:
                            yield json.dumps(
                                {"error": str(chunk["error"])},
                                ensure_ascii=False,
                            ) + "\n"
                            return
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        content = choices[0].get("delta", {}).get("content")
                        if content:
                            yield json.dumps(
                                {"content": content},
                                ensure_ascii=False,
                            ) + "\n"
        except httpx.HTTPError:
            yield json.dumps(
                {
                    "error": (
                        "Le moteur local ne répond pas. Démarre llama-server "
                        "avec `.venv/bin/python -m backend.start_server`."
                    )
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )


def extract_file(path: str, extension: str):
    if extension in {".txt", ".md", ".pdf", ".docx"}:
        return load_text_file(path)
    if extension in {".mp3", ".wav"}:
        return transcribe_audio(path)
    return transcribe_video_audio(path)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    filename = Path(file.filename or "fichier").name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Format de fichier non supporté.")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    file.file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Le fichier dépasse la limite de 100 Mo.",
        )

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = temporary_file.name
        extracted = extract_file(temporary_path, extension)
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Impossible de traiter le fichier : {error}",
        ) from error
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)

    return {
        "filename": filename,
        "content": extracted[:100_000],
        "truncated": len(extracted) > 100_000,
    }


if WEB_DIST.exists():
    assets_dir = WEB_DIST / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    async def serve_index():
        return (WEB_DIST / "index.html").read_text(encoding="utf-8")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Route API inconnue.")
        return HTMLResponse(
            (WEB_DIST / "index.html").read_text(encoding="utf-8")
        )
