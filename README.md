# Tutor LLM

Tutor LLM è una piattaforma **local-first e API-first** per studiare qualsiasi materia partendo principalmente dai materiali caricati dall'utente. Ogni materia vive in un **workspace isolato**: libri, documenti, retrieval, curriculum, mastery, note e sessioni non contaminano gli altri workspace.

Esempi: `Matematica`, `Sistemi Operativi`, `Filosofia`, `Machine Learning`.

## Visione

Il prodotto non è un semplice chatbot sui PDF. Il modello operativo è:

```text
Workspace
├── Library
├── Knowledge / Curriculum
├── Student mastery
├── Tutor activities
├── Notes / annotations
└── Study Sessions
```

Il materiale dell'utente è l'autorità primaria. Il modello fornisce capacità didattica, ragionamento e conoscenza generale secondo una politica epistemica esplicita.

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
- riassunti trasversali
- approfondimenti
- esercizi graduati
- quiz
- sessioni di ragionamento socratico
- curriculum adattivo con prerequisiti
- mastery distinta per workspace e concetto
- note personali, anche collegate a documento e pagina
- Study Session persistenti con documento/pagina/testo selezionato/concetto corrente
- API FastAPI per client futuri web, desktop e iPadOS
- export dataset e LoRA/SFT opzionale per adattare il comportamento didattico

## Architettura

- **LLM locale:** Ollama + `qwen3:4b`
- **Embedding:** Ollama + `embeddinggemma`
- **Storage:** SQLite
- **RAG:** chunking + embeddings + cosine retrieval
- **PDF:** PyMuPDF
- **OCR:** Tesseract
- **Word:** python-docx
- **Web client attuale:** Streamlit
- **API:** FastAPI

La logica importante vive nel package `studyforge/`; Streamlit è soltanto un client. Questo permette di costruire un'app iPad nativa senza duplicare il motore.

## Struttura

```text
studyforge/
├── api.py           # API per client esterni
├── config.py
├── curriculum.py
├── db.py
├── ingest.py
├── notes.py
├── ollama_client.py
├── pipeline.py
├── retrieval.py
├── sessions.py
├── student.py
├── teacher.py
└── workspaces.py
```

## Installazione Linux / Ubuntu

Installa Tesseract e Python:

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng python3-venv
```

Installa e avvia Ollama, quindi:

```bash
ollama pull qwen3:4b
ollama pull embeddinggemma
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Client web

```bash
streamlit run app.py
```

### API

```bash
uvicorn studyforge.api:app --host 0.0.0.0 --port 8000
```

La documentazione OpenAPI sarà disponibile su `/docs`.

## Study Session e futura app iPad

Una Study Session conserva il contesto operativo corrente:

```text
workspace
├── current_document_id
├── current_page
├── selected_text
├── current_concept
├── learning_goal
└── state_json
```

Questo permette a un client iPad di visualizzare un PDF, selezionare un passaggio e chiedere al tutor una spiegazione sapendo esattamente quale pagina e quale testo l'utente sta osservando. Le note possono essere legate a documento e pagina e in futuro ospitare handwriting/Apple Pencil senza trasformare automaticamente gli appunti dell'utente in fonti autorevoli.

## Perché RAG + training, non fine-tuning sui libri

I libri sono conoscenza variabile, sostituibile e verificabile: devono restare nel retrieval. Il training opzionale serve invece a migliorare *come* il tutor insegna: struttura, stile pedagogico e preferenze apprese dal feedback.

## Migrazione dalla v0.3

I database esistenti vengono migrati automaticamente. Documenti, lezioni, curriculum e mastery preesistenti vengono associati al workspace `General`; da quel momento i nuovi dati sono isolati per workspace.

## Test

```bash
python -m compileall -q studyforge app.py tests
python -m unittest discover -s tests -v
```

GitHub Actions esegue compilazione e test a ogni push. La suite include verifiche esplicite contro la contaminazione di documenti e mastery tra workspace.

## Training personale opzionale

```bash
python training/export_dataset.py
pip install -r requirements-train.txt
python training/train_lora.py
```

## Configurazione

```bash
export CHAT_MODEL=qwen3:4b
export EMBEDDING_MODEL=embeddinggemma
export OLLAMA_URL=http://localhost:11434
export OCR_LANG=ita+eng
export TOP_K=8
```

## Roadmap

- [x] ingestione multi-formato e OCR
- [x] RAG locale con provenance
- [x] workspace isolati
- [x] mastery per workspace
- [x] curriculum adattivo
- [x] Grounded / Tutor / Expert
- [x] riassunti, approfondimenti, esercizi, quiz e ragionamento
- [x] note collegate a pagine
- [x] Study Session page-aware
- [x] API-first
- [ ] parsing strutturale indice/capitoli/sezioni
- [ ] bounding box del testo PDF per selezioni precise nell'app
- [ ] OCR layout-aware per formule, tabelle e figure
- [ ] grading automatico delle risposte aperte con rubriche
- [ ] spaced repetition e scheduler adattivo
- [ ] knowledge graph persistente e navigabile
- [ ] analisi automatica della copertura della biblioteca rispetto a un obiettivo expert
- [ ] flashcard/Anki
- [ ] client iPadOS con PDF, Apple Pencil e split view Tutor/Notes
- [ ] sincronizzazione opzionale LAN/server privato mantenendo il core locale-first

## Privacy

I documenti e il database locale sono esclusi da Git. Il flusso può funzionare interamente sulla macchina dell'utente tramite Ollama. I client futuri potranno collegarsi al core locale via API senza richiedere servizi cloud.
