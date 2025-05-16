import os
from pathlib import Path
import requests
from llama_cpp import Llama

MODEL_NAME = "mistral-7b-instruct-v0.1.Q4_K_M.gguf"
MODEL_PATH = f"models/{MODEL_NAME}"
MODEL_URL = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/" + MODEL_NAME

def download_model():
    os.makedirs("models", exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        print("🔽 Téléchargement du modèle Mistral...")
        with requests.get(MODEL_URL, stream=True) as r:
            r.raise_for_status()
            with open(MODEL_PATH, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("✅ Modèle téléchargé.")

download_model()
llm = Llama(model_path=MODEL_PATH, n_ctx=2048)

def init_chat():
    return []

def update_chat(prompt, history):
    full_prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    full_prompt += f"\nuser: {prompt}\nassistant:"

    output = llm(full_prompt, max_tokens=256, stop=["user:", "assistant:"])
    reply = output["choices"][0]["text"].strip()

    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": reply})
    return reply
