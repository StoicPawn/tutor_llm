# Matematica Demo

Tutor LLM include un workspace di test riproducibile per verificare il prodotto end-to-end senza usare materiale personale.

Prerequisiti: ambiente installato, Ollama avviato, `qwen3:4b` ed `embeddinggemma` disponibili.

```bash
make demo
```

Lo script crea `Matematica Demo` e genera due PDF sintetici multipagina su limiti, continuità, derivate, integrali e teorema fondamentale del calcolo. I PDF passano dalla pipeline reale: estrazione layout, pagine e bounding box, chunking con span, embedding, parsing sezioni e isolamento workspace.

Test consigliati nell'interfaccia o via API:

1. aprire `Matematica Demo` e verificare che gli altri workspace non compaiano nelle fonti;
2. chiedere una lezione sul rapporto fra derivate e integrali;
3. ricostruire il knowledge graph;
4. generare flashcard e controllare la review queue;
5. avviare una sessione di esercizi interattiva;
6. interrogare una pagina PDF e mappare una selezione testuale/bounding-box su chunk e citazione;
7. verificare il `Next Best Activity` dopo alcuni risultati corretti e errati.

Il workspace demo vive nel database locale e non viene versionato in Git. Per rigenerarlo, elimina prima il workspace `Matematica Demo` dall'istanza locale.
