# AZE LLM — assistant local

AZE LLM utilise trois processus locaux indépendants :

```text
Navigateur
    │
    ▼
Vite + React (développement)  http://127.0.0.1:5173
    │  HTTP + flux NDJSON
    ▼
FastAPI                       http://127.0.0.1:8000
    │  API OpenAI + clé privée
    ▼
llama-server                  http://127.0.0.1:8080
    │
    ▼
Qwen 2.5 1.5B Q4             models/*.gguf
```

Streamlit n’est plus utilisé. La clé de `llama-server` reste exclusivement
dans les processus Python et n’est jamais envoyée au navigateur.

## Prérequis

- Python 3.11 ou plus récent ;
- Node.js 20 ou plus récent ;
- `ffmpeg` pour les fichiers audio et vidéo.

Sur Ubuntu :

```bash
sudo apt update
sudo apt install -y python3-full python3-venv ffmpeg nodejs npm
```

## Installation

```bash
cd /home/evan/Dev/V6LLM

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt

cd frontend
npm install
cd ..
```

Installer ensuite le moteur et le modèle, une seule fois :

```bash
.venv/bin/python -m backend.install_llama_server
.venv/bin/python -m backend.download_model
```

## Lancement en développement

Terminal 1 — moteur :

```bash
cd /home/evan/Dev/V6LLM
.venv/bin/python -m backend.start_server
```

Terminal 2 — API :

```bash
cd /home/evan/Dev/V6LLM
.venv/bin/python -m backend.start_api
```

Terminal 3 — interface :

```bash
cd /home/evan/Dev/V6LLM/frontend
npm run dev
```

Ouvrir <http://127.0.0.1:5173>.

## Lancement avec l’interface compilée

Construire l’interface une fois :

```bash
cd /home/evan/Dev/V6LLM/frontend
npm run build
```

Lancer ensuite `llama-server` et FastAPI dans deux terminaux :

```bash
cd /home/evan/Dev/V6LLM
.venv/bin/python -m backend.start_server
```

```bash
cd /home/evan/Dev/V6LLM
.venv/bin/python -m backend.start_api
```

FastAPI sert alors directement l’interface compilée sur
<http://127.0.0.1:8000>. Vite n’a pas besoin de rester actif.

## API

| Route | Usage |
|---|---|
| `GET /api/health` | état de `llama-server` |
| `POST /api/chat` | génération en flux NDJSON |
| `POST /api/upload` | extraction texte, PDF, Word, audio ou vidéo |
| `GET /docs` | documentation interactive FastAPI |

## Configuration

| Variable | Valeur par défaut |
|---|---|
| `AZE_LLM_SERVER_URL` | `http://127.0.0.1:8080` |
| `AZE_LLM_SERVER_HOST` | `127.0.0.1` |
| `AZE_LLM_SERVER_PORT` | `8080` |
| `AZE_LLM_MODEL_ALIAS` | `qwen-local` |
| `AZE_LLM_API_KEY` | `aze-local-v6llm` |
| `AZE_LLM_CONTEXT_SIZE` | `2048` |
| `AZE_LLM_THREADS` | `2` |
| `AZE_API_HOST` | `127.0.0.1` |
| `AZE_API_PORT` | `8000` |
| `LLAMA_SERVER_BIN` | détection automatique |

`AZE_LLM_API_KEY` et `AZE_LLM_MODEL_ALIAS` doivent avoir les mêmes valeurs
pour FastAPI et `llama-server`.

## Organisation

```text
backend/
    api.py                    API FastAPI et streaming
    start_api.py              lancement de FastAPI
    config.py                 configuration du moteur
    install_llama_server.py   installation du binaire officiel
    download_model.py         téléchargement explicite de Qwen
    start_server.py           lancement sécurisé de llama-server
frontend/
    src/                      application React
    vite.config.js            proxy local vers FastAPI
    package.json              dépendances et scripts Vite
modules/
    loader_*.py               lecture texte, audio et vidéo
```
