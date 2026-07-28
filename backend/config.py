from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / MODEL_NAME
MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/"
    f"resolve/main/{MODEL_NAME}"
)

MODEL_ALIAS = os.getenv("AZE_LLM_MODEL_ALIAS", "qwen-local")
API_KEY = os.getenv("AZE_LLM_API_KEY", "aze-local-v6llm")
SERVER_HOST = os.getenv("AZE_LLM_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("AZE_LLM_SERVER_PORT", "8080"))
CONTEXT_SIZE = int(os.getenv("AZE_LLM_CONTEXT_SIZE", "2048"))
THREADS = int(os.getenv("AZE_LLM_THREADS", "2"))
LLAMA_INSTALL_DIR = PROJECT_ROOT / "bin" / "llama.cpp"
