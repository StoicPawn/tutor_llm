# Tutor LLM

Tutor LLM è una piattaforma **local-first e API-first** per studiare qualsiasi materia partendo principalmente dai materiali caricati dall'utente. Ogni materia vive in un **workspace isolato**: libri, documenti, retrieval, curriculum, mastery, knowledge graph, note, ripassi e sessioni non contaminano gli altri workspace.

Esempi: `Matematica`, `Sistemi Operativi`, `Filosofia`, `Machine Learning`.

## Visione

Il prodotto non è un semplice chatbot sui PDF. Il modello operativo è:

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
- **sessioni di esercizi interattivi una domanda alla volta**, con correzione automatica
- curriculum adattivo con prerequisiti
- mastery distinta per workspace e concetto
- **spaced repetition** con scheduler adattivo e ripassi dovuti
- **knowledge graph persistente** con concetti e relazioni didattiche
- analisi Expert della copertura della biblioteca rispetto a un obiettivo
- note personali, anche collegate a documento e pagina
- Study Session persistenti con documento/pagina/testo selezionato/concetto corrente
- **PDF page-aware**: testo pagina, dimensioni e bounding box dei blocchi nativi
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
├── api.py
├── assessment.py
├── config.py
├── coverage.py
├── curriculum.py
├── db.py
├── ingest.py
├── interactive.py
├── knowledge.py
├── notes.py
├── ollama_client.py
├── pipeline.py
├── repetition.py
├── retrieval.py
├── sessions.py
├── student.py
├── teacher.py
└── workspaces.py
```

## Installazione Linux / Ubuntu

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng python3-venv
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

La documentazione OpenAPI è disponibile su `/docs`.

## PDF page-aware e futura app iPad

Per i PDF nativi Tutor LLM conserva ora, oltre al testo usato dal RAG, anche:

```text
document
└── page
    ├── text
    ├── width / height
    ├── OCR flag
    └── blocks[]
        ├── bbox [x0,y0,x1,y1]
        └── text
```

Questo è il contratto necessario per una futura app iPad in cui l'utente scorre il PDF, seleziona visivamente un passaggio e lo invia al tutor. Le pagine OCR restano esplicitamente marcate perché le coordinate native non sono considerate affidabili finché non verrà introdotto OCR layout-aware.

Una Study Session conserva inoltre:

```text
workspace
├── current_document_id
├── current_page
├── selected_text
├── current_concept
├── learning_goal
└── state_json
```

Le note restano artefatti personali separati dalle fonti autorevoli e potranno ospitare handwriting/Apple Pencil.

## Motore di apprendimento

La mastery non è trattata come un voto assoluto. È memoria operativa dello studio e viene aggiornata tramite evidenze: feedback, quiz, correzioni e sessioni interattive.

Le sessioni interattive generano esercizi progressivi, mostrano una domanda per volta, valutano la risposta sulle fonti, distinguono elementi corretti/mancanti/errori e aggiornano sia mastery sia scheduler di ripasso.

Lo scheduler usa una variante semplice del principio SM-2, corretta modestamente per la mastery: un buon risultato allunga progressivamente l'intervallo, un risultato debole riporta il concetto a breve termine. La mastery non può eliminare completamente il retrieval practice.

## Knowledge graph

Ogni workspace può costruire una mappa persistente con nodi (`concept`, `definition`, `theorem`, `method`, `skill`) e relazioni come `prerequisite`, `explains`, `part_of`, `contrasts`, `applies_to`, `generalizes`. Il graph è ricostruito dai materiali del workspace e rimane separato dagli altri mondi di studio.

## Perché RAG + training, non fine-tuning sui libri

I libri sono conoscenza variabile, sostituibile e verificabile: devono restare nel retrieval. Il training opzionale serve invece a migliorare *come* il tutor insegna: struttura, stile pedagogico e preferenze apprese dal feedback.

## Migrazione dalla v0.3

I database esistenti vengono migrati automaticamente. I dati preesistenti vengono associati al workspace `General`; da quel momento i nuovi dati sono isolati per workspace.

## Test

```bash
python -m compileall -q studyforge app.py tests
python -m unittest discover -s tests -v
```

GitHub Actions esegue compilazione e test a ogni push. La suite comprende verifiche di isolamento workspace anche per pagine e scheduler di ripasso.

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
- [x] grading automatico delle risposte aperte
- [x] esercizi interattivi domanda-per-domanda
- [x] spaced repetition e scheduler adattivo
- [x] knowledge graph persistente
- [x] analisi Expert della copertura della biblioteca
- [x] note collegate a pagine
- [x] Study Session page-aware
- [x] bounding box dei blocchi testuali PDF nativi
- [x] API-first
- [ ] parsing strutturale indice/capitoli/sezioni
- [ ] mapping preciso selezione PDF → span/chunk/citazione
- [ ] OCR layout-aware per formule, tabelle e figure
- [ ] flashcard/Anki e review queue unificata
- [ ] planner Next Best Activity che combini curriculum, mastery, graph e scadenze
- [ ] client iPadOS con PDF, Apple Pencil e split view Tutor/Notes
- [ ] sincronizzazione opzionale LAN/server privato mantenendo il core local-first

## Privacy

I documenti e il database locale sono esclusi da Git. Il flusso può funzionare interamente sulla macchina dell'utente tramite Ollama. I client futuri potranno collegarsi al core locale via API senza richiedere servizi cloud.
