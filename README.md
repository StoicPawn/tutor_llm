# Tutor LLM

Tutor LLM è una piattaforma **local-first e API-first** per studiare qualsiasi materia partendo principalmente dai materiali caricati dall'utente. Ogni materia vive in un **workspace isolato**: libri, documenti, retrieval, curriculum, mastery, knowledge graph, note, ripassi e sessioni non contaminano gli altri workspace.

Esempi: `Matematica`, `Sistemi Operativi`, `Filosofia`, `Machine Learning`.

## Visione

Tutor LLM non è un semplice chatbot sui PDF. Il modello operativo è:

```text
Workspace
├── Library
├── Knowledge graph / Curriculum
├── Student mastery
├── Adaptive reviews
├── Tutor activities
├── Notes / annotations
└── Study Sessions
```

Il materiale dell'utente è l'autorità primaria. Il modello fornisce capacità didattica, ragionamento e conoscenza generale secondo una politica epistemica esplicita.

## Due modalità ufficiali di deploy

Tutor LLM deve poter essere installato in **due modi diversi senza cambiare il prodotto**.

### 1. Local PC

Tutto gira sul computer dell'utente:

```text
UI / browser
    |
Tutor LLM Core
  /        \
SQLite    InferenceProvider
             |
           Ollama
          /      \
      Qwen    EmbeddingGemma
```

Il PC contiene documenti, database, embeddings, modelli, knowledge graph, mastery e note. Dopo l'installazione iniziale e il download dei modelli, l'uso normale può essere completamente offline.

Per sviluppo:

```bash
make install
make models
make run
```

L'obiettivo di prodotto è un installer nativo che installi/verifichi automaticamente runtime, OCR, Ollama e modelli: l'utente finale non dovrà conoscere Git o Python.

### 2. Private Tutor Server

Tutor LLM Core, dati e modelli girano su un server personale. iPad, PC, telefono e futuri client si collegano a quel server:

```text
iPad / PC / phone
        |
 accesso privato cifrato
        |
 Tutor LLM API
   /          \
storage     InferenceProvider
                 |
               Ollama
```

Il server è la **source of truth** per biblioteca, workspaces, embeddings, mastery, knowledge graph, note e cronologia. I client non devono installare Llama o mantenere copie separate dello Student Model.

È disponibile un profilo Docker Compose. La modalità server richiede un token applicativo:

```bash
cd deploy
cp .env.server.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# inserire il valore generato come API_TOKEN nel file .env
cd ..
make server-up
make server-models
```

Ogni richiesta operativa remota usa:

```text
Authorization: Bearer <API_TOKEN>
```

Per sicurezza, il Compose pubblica Tutor LLM solo su `127.0.0.1` e **non espone Ollama**. Per accesso fuori casa va usata una rete privata/tunnel o reverse proxy autenticato; non va pubblicata direttamente su Internet la porta dell'API. Il Bearer token costituisce un ulteriore livello applicativo anche all'interno della rete privata.

Dettagli: `docs/deployment.md`.

## Inference provider

Il core non deve dipendere direttamente da dove gira il modello. Il confine ufficiale è:

```text
Tutor Core -> InferenceProvider -> Ollama oggi
                              -> altri runtime privati in futuro
```

`DEPLOY_MODE=local|server` descrive dove gira Tutor Core. `INFERENCE_PROVIDER=ollama` descrive il backend di inferenza. Sono concetti separati.

Questo permette in futuro di usare un runtime iPad-native, un server GPU più potente o un altro backend senza riscrivere RAG, curriculum, mastery o UI.

## Modalità epistemiche

- **Grounded** — usa esclusivamente i materiali del workspace; se l'evidenza manca, lo dichiara.
- **Tutor** — i materiali restano la fonte primaria; eventuali integrazioni didattiche vengono marcate `[CONOSCENZA GENERALE]`.
- **Expert** — può integrare conoscenza generale e segnalare ciò che manca nella biblioteca come `[LACUNA BIBLIOTECA]` per costruire un percorso verso expertise reale.

## Funzioni attuali

- PDF testuali e PDF scansionati con OCR
- immagini, DOCX, TXT e Markdown
- RAG locale con embeddings e citazioni documento/pagina
- workspace completamente separati
- lezioni brevi, approfondite e ripasso
- domande grounded sui documenti
- riassunti trasversali e approfondimenti
- esercizi, quiz e ragionamento
- sessioni interattive domanda-per-domanda con correzione automatica
- curriculum adattivo con prerequisiti
- mastery distinta per workspace e concetto
- spaced repetition con scheduler adattivo
- knowledge graph persistente
- analisi Expert della copertura della biblioteca
- flashcard e review queue
- Next Best Activity planner
- parsing di sezioni/capitoli
- mapping selezione PDF → blocchi/chunk/citazione
- note personali collegate a documento e pagina
- Study Session persistenti con documento/pagina/testo selezionato/concetto corrente
- PDF page-aware con bounding box dei blocchi nativi
- API FastAPI per client web, desktop e futuro iPadOS
- autenticazione Bearer obbligatoria nel profilo server
- backup/restore portabile di database + documenti, con rilocalizzazione automatica dei path
- export dataset e LoRA/SFT opzionale per adattare il comportamento didattico

## Architettura

- **Tutor Core:** Python package `studyforge/`
- **Inference:** provider abstraction + Ollama
- **Chat model predefinito:** `qwen3:4b`
- **Embedding model:** `embeddinggemma`
- **Storage:** SQLite + filesystem locale/server
- **RAG:** chunking + embeddings + cosine retrieval
- **PDF:** PyMuPDF
- **OCR:** Tesseract
- **Word:** python-docx
- **Web client attuale:** Streamlit
- **API:** FastAPI

GitHub contiene **codice, configurazione e definizioni di deploy**, non i modelli LLM né i dati personali. Documenti, database e pesi dei modelli restano sulla macchina che esegue Tutor LLM Core/Ollama.

## Configurazione

Profilo locale:

```bash
export DEPLOY_MODE=local
export INFERENCE_PROVIDER=ollama
export OLLAMA_URL=http://localhost:11434
export CHAT_MODEL=qwen3:4b
export EMBEDDING_MODEL=embeddinggemma
```

Profilo server aggiunge obbligatoriamente:

```bash
export DEPLOY_MODE=server
export API_TOKEN=<segreto-lungo-casuale>
```

Template completi:

- `deploy/.env.local.example`
- `deploy/.env.server.example`

## Backup e migrazione

I pesi dei modelli non vengono inclusi nei backup: vengono riscaricati sulla macchina destinazione. La conoscenza personale invece è portabile.

Backup locale:

```bash
make backup
```

Restore locale, con Tutor LLM fermo:

```bash
make restore ARCHIVE=/path/to/backup.zip
```

Sul server Docker:

```bash
make server-backup
make server-restore ARCHIVE=nome-file.zip
```

I backup server vengono scritti in `deploy/backups/`. Questo rende supportato il percorso:

```text
PC locale -> backup -> Tutor Server -> restore -> download modelli
```

## API e futura app iPad

La logica importante vive nel package `studyforge/`; Streamlit è soltanto un client. È disponibile anche `studyforge.client.TutorClient` come client HTTP autenticato di riferimento. L'iPad implementerà lo stesso contratto API.

Per i PDF nativi Tutor LLM conserva pagina, testo, dimensioni, bounding box e mapping verso chunk. Una Study Session conserva:

```text
workspace
├── current_document_id
├── current_page
├── selected_text
├── current_concept
├── learning_goal
└── state_json
```

Questo permette una futura UI iPad con PDF, selezione del passaggio, Tutor e foglio Apple Pencil senza duplicare il motore.

## Demo workspace

Con Ollama e i modelli già installati:

```bash
make demo
```

crea localmente `Matematica Demo`, una fixture end-to-end separata dai dati reali. Vedi `docs/demo_workspace.md`.

## Test

```bash
make check
```

GitHub Actions esegue compilazione e test. La suite comprende isolamento workspace, page mapping, scheduler, backup, sicurezza server e contratto API.

## Privacy e accesso remoto

- i documenti e il database sono esclusi da Git;
- in modalità local possono restare interamente sul PC;
- in modalità server restano sul server personale;
- Ollama non deve essere esposto direttamente a Internet;
- l'API server richiede Bearer token;
- il server remoto deve essere raggiunto tramite accesso privato cifrato/autenticato;
- i modelli LLM non vengono inseriti nei backup né nella repository.

## Roadmap principale

- [x] workspace isolati
- [x] RAG + provenance
- [x] curriculum/mastery/knowledge graph
- [x] spaced repetition, flashcard e review queue
- [x] esercizi interattivi e grading
- [x] PDF page-aware e source mapping
- [x] Next Best Activity planner
- [x] API-first
- [x] profili architetturali `local` e `server`
- [x] Docker Compose server
- [x] autenticazione API server
- [x] backup/export/import della conoscenza personale
- [x] migrazione local → server con rilocalizzazione dei documenti
- [ ] installer desktop automatico per Windows/macOS/Linux
- [ ] gestione dispositivi/token multipli e revoca
- [ ] GPU-specific server profiles
- [ ] OCR layout-aware per formule, tabelle e figure
- [ ] client iPadOS con PDF, Apple Pencil e split view Tutor/Notes
- [ ] sync/cache offline controllata per client remoti
