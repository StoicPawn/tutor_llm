# Deployment modes

Tutor LLM supports two first-class deployment profiles. They share the same Tutor Core, database model, workspaces and API contract.

## 1. Local PC

Use this when one computer is both the study device and the AI engine.

```text
Desktop UI / browser
        |
    Tutor Core
     /      \
 SQLite    Ollama
            |-- chat model
            `-- embedding model
```

All documents, embeddings, notes, mastery and models remain on that computer. After the initial installation and model downloads, normal study can work without Internet.

Current developer setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen3:4b
ollama pull embeddinggemma
make run
```

Configuration starts from `deploy/.env.local.example`.

The product goal is a native installer that performs runtime/dependency checks and model downloads automatically; Git and Python commands are not intended to be required for normal end users.

## 2. Private Tutor Server

Use this when one machine is the persistent AI study server and laptops/tablets/phones are clients.

```text
 iPad / PC / phone
        |
 private encrypted access
        |
   Tutor LLM API
       /      \
   storage   Ollama
              |-- chat model
              `-- embedding model
```

The server is the source of truth for documents, embeddings, workspaces, notes, student mastery, review schedule and knowledge graph. Clients do not need a local LLM.

### Docker Compose

```bash
cd deploy
cp .env.server.example .env
docker compose -f docker-compose.server.yml up -d --build
docker compose -f docker-compose.server.yml exec ollama ollama pull qwen3:4b
docker compose -f docker-compose.server.yml exec ollama ollama pull embeddinggemma
```

The Compose profile intentionally publishes Tutor LLM only on `127.0.0.1:8000` and does not publish Ollama at all. Remote access should be provided by a private VPN/tunnel or an authenticated TLS reverse proxy. Do not expose the raw Tutor API or Ollama directly to the public Internet.

A practical personal deployment is to use Tailscale Serve (or an equivalent private network solution) to proxy the server's localhost Tutor endpoint to authenticated devices in the private network.

### GPU

The base Compose file is CPU-compatible. GPU-specific overrides will be maintained separately because NVIDIA, AMD and Apple hardware require different runtimes. Tutor Core itself does not depend on a particular accelerator.

## Inference provider boundary

Tutor Core calls `studyforge.inference`, not a model implementation directly. The first provider is Ollama. This boundary allows future backends (for example an iPad-native runtime or another private inference server) without changing RAG, curriculum, mastery or study logic.

```text
Tutor Core -> InferenceProvider -> Ollama today
                              -> other private runtimes later
```

`DEPLOY_MODE` describes where Tutor Core is deployed; `INFERENCE_PROVIDER` describes how it obtains generation/embedding inference. They are deliberately separate concepts.

## Data and migration

GitHub contains source code and installation/deployment definitions, not user data or model weights. A future backup/export feature must move the user state (database + documents + related assets) independently from application installation. Model weights can normally be downloaded again on the destination machine.
