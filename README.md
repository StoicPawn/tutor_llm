# StudyForge Local

Un tutor di studio **locale-first**: carica PDF (anche scansioni), immagini, Word, TXT/Markdown; indicizza il contenuto; crea lezioni brevi o approfondite, ripassi e quiz citando i passaggi del materiale usato.

## Architettura

- **LLM locale:** Ollama + `qwen3:4b`
- **Embedding locale:** Ollama + `embeddinggemma`
- **RAG:** chunking + embedding + ricerca cosine in SQLite
- **PDF nativi:** PyMuPDF
- **PDF scansioni / immagini:** Tesseract OCR
- **Word:** python-docx
- **UI:** Streamlit
- **Apprendimento:** feedback sulle lezioni → dataset SFT → LoRA opzionale

### Perché RAG + training, non fine-tuning sui libri

I documenti sono conoscenza variabile e devono rimanere verificabili e sostituibili. Vengono quindi recuperati al momento della domanda. Il fine-tuning opzionale serve invece a migliorare stile didattico, struttura delle spiegazioni e preferenze apprese dal feedback.

## Installazione Linux / Ubuntu

1. Installa Ollama dal sito ufficiale e avvialo.
2. Installa Tesseract e le lingue OCR:

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng python3-venv
```

3. Scarica i modelli locali:

```bash
ollama pull qwen3:4b
ollama pull embeddinggemma
```

4. Installa StudyForge:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. Avvia:

```bash
streamlit run app.py
```

Apri l'indirizzo locale mostrato da Streamlit (di norma `http://localhost:8501`).

## Uso

1. **Carica** uno o più documenti.
2. Se un PDF non contiene testo sufficiente, StudyForge esegue OCR pagina per pagina.
3. Scegli nella sidebar quali libri usare.
4. Scrivi un argomento e scegli **Breve**, **Approfondita** o **Ripasso**.
5. La lezione usa riferimenti `[FONTE N]` ai passaggi recuperati.
6. Valuta la lezione e scrivi cosa migliorare.
7. Genera quiz separati per richiamo attivo.

## Training personale (opzionale)

Quando hai accumulato lezioni valutate positivamente:

```bash
python training/export_dataset.py
pip install -r requirements-train.txt
python training/train_lora.py
```

Il training LoRA richiede tipicamente una macchina con GPU adeguata. Non è necessario per usare StudyForge: il sistema funziona subito tramite RAG.

## Configurazione

Variabili d'ambiente principali:

```bash
export CHAT_MODEL=qwen3:4b
export EMBEDDING_MODEL=embeddinggemma
export OLLAMA_URL=http://localhost:11434
export OCR_LANG=ita+eng
export TOP_K=8
```

## Roadmap

- [x] PDF testuali
- [x] PDF scansionati via OCR
- [x] Immagini
- [x] DOCX / TXT / Markdown
- [x] RAG locale con citazioni
- [x] Lezione breve / approfondita / ripasso
- [x] Quiz
- [x] Feedback persistente
- [x] Export dataset per training
- [x] LoRA/SFT opzionale
- [ ] parsing strutturale di capitoli e indice
- [ ] OCR layout-aware per tabelle/formule
- [ ] sessioni di studio con spaced repetition
- [ ] profilo dello studente e stima della padronanza per concetto
- [ ] generazione automatica di un corso completo da più libri
- [ ] esportazione lezioni/flashcard in Markdown/Anki

## Privacy

Il flusso applicativo è progettato per funzionare in locale. I documenti vengono salvati sotto `data/uploads/` e l'indice in `data/studyforge.db`; entrambi sono esclusi da Git.

## Tutor adattivo (v0.2)

StudyForge mantiene una stima locale e trasparente della padronanza per argomento. Le valutazioni delle lezioni e i risultati dei quiz aggiornano gradualmente la stima; la lezione successiva usa tale valore per regolare prerequisiti e profondità. Non è un voto psicometrico: è una memoria operativa dello studio.

Sono inoltre disponibili una modalità **Domande** grounded sui documenti, gestione della libreria e cronologia dei progressi.

## v0.3 — Percorsi adattivi

StudyForge può trasformare i documenti selezionati in un syllabus ordinato. Il planner campiona l'intero corpus, propone concetti supportati dalle fonti, registra i prerequisiti e sceglie la prossima lezione usando sia la padronanza stimata sia l'importanza del concetto. I nodi passano tra `todo`, `learning` e `done`; un prerequisito è considerato superato anche quando la padronanza stimata raggiunge il 68%.

### Flusso

1. Indicizza uno o più documenti.
2. Apri **Percorso**, descrivi l'obiettivo e genera il syllabus.
3. Usa **Studia la prossima lezione**: StudyForge seleziona un nodo i cui prerequisiti sono soddisfatti.
4. Valuta lezioni e quiz: il profilo dello studente influenza le scelte successive.

Il syllabus è una struttura di navigazione didattica, non una fonte: le lezioni continuano a essere generate via RAG dai documenti indicizzati e devono citare le evidenze recuperate.
