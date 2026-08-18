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
python -c "import secrets; print(secrets.token_urlsafe(48))"
# paste the generated value into API_TOKEN in .env
docker compose --env-file .env -f docker-compose.server.yml up -d --build
docker compose --env-file .env -f docker-compose.server.yml exec ollama ollama pull qwen3:4b
docker compose --env-file .env -f docker-compose.server.yml exec ollama ollama pull embeddinggemma
```

`API_TOKEN` is mandatory in server mode. Every operational API request must send:

```text
Authorization: Bearer <API_TOKEN>
```

The health endpoint and OpenAPI documentation remain public for diagnostics; workspace content, documents, tutor operations, notes and study state require authentication.

The Compose profile intentionally publishes Tutor LLM only on `127.0.0.1:8000` and does not publish Ollama at all. Remote access should be provided by a private VPN/tunnel or an authenticated TLS reverse proxy. Do not expose the raw Tutor API or Ollama directly to the public Internet.

A practical personal deployment is to use a private network/tunnel to proxy the server's localhost Tutor endpoint to authenticated devices. The Tutor API token remains a second application-level protection even inside that private network.

### GPU

The base Compose file is CPU-compatible. GPU-specific overrides will be maintained separately because NVIDIA, AMD and Apple hardware require different runtimes. Tutor Core itself does not depend on a particular accelerator.

## Inference provider boundary

Tutor Core calls `studyforge.inference`, not a model implementation directly. The first provider is Ollama. This boundary allows future backends (for example an iPad-native runtime or another private inference server) without changing RAG, curriculum, mastery or study logic.

```text
Tutor Core -> InferenceProvider -> Ollama today
                              -> other private runtimes later
```

`DEPLOY_MODE` describes where Tutor Core is deployed; `INFERENCE_PROVIDER` describes how it obtains generation/embedding inference. They are deliberately separate concepts.

## Backup, restore and migration

GitHub contains source code and deployment definitions, not user data or model weights. Tutor LLM backups contain the SQLite state plus uploaded documents, but intentionally exclude model weights.

Create a backup:

```bash
make backup
```

Restore onto another local installation, with Tutor services stopped:

```bash
make restore ARCHIVE=/path/to/tutor-llm-backup-....zip
```

This is also the migration path from a personal PC to a private server:

```text
Local PC -> export backup -> install Tutor Server -> restore backup -> download models
```

The destination can download Qwen/embedding weights again, while preserving workspaces, documents, chunks/embeddings, notes, mastery, curricula, knowledge graph, reviews and other database state.

Before any destructive restore, create a fresh backup of the destination. Restore is designed to run while Tutor LLM services are stopped so the SQLite database and uploaded files cannot change during replacement.
