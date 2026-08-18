# Tutor LLM iPadOS Client

Client nativo SwiftUI per collegarsi a Tutor LLM in modalità server.

## Requisiti

- macOS con Xcode recente
- iOS/iPadOS 17+
- XcodeGen (`brew install xcodegen`) oppure creazione manuale di un target iPadOS con i file in `Sources/`
- Tutor LLM server raggiungibile via rete privata/VPN/tunnel autenticato
- token dispositivo `tllm_...`, non il token amministrativo del server

## Generazione progetto

```bash
cd clients/ipados
xcodegen generate
open TutorLLM.xcodeproj
```

Se usi un iPad fisico, imposta il tuo Team di firma in Xcode.

## Funzioni presenti

- configurazione URL server
- token dispositivo salvato in Keychain
- health/identity validation
- lista workspace
- lista documenti
- viewer PDF nativo con PDFKit
- split view adatta a iPad
- Tutor contestuale al documento/pagina corrente
- canvas PencilKit
- base networking compatibile con Tutor LLM API v0.11+

## Stato attuale

Questa è la prima tranche del client nativo. PDF e Tutor usano già il server reale. Il canvas PencilKit è funzionante localmente ma il suo salvataggio deve ancora essere collegato alle `notebook_page` sincronizzabili già supportate dal backend.

Il prossimo livello client comprende:

1. cache SQLite/SwiftData locale equivalente a `studyforge/client_cache.py`;
2. download `Disponibile offline` dei PDF;
3. pull/push automatico degli envelope di note, annotazioni e notebook;
4. persistenza PencilKit -> layer ink del quaderno;
5. selezione PDF nativa -> `/documents/render-selection` e azioni Spiegami/Perché/Esempio/Esercizio;
6. gestione conflitti con UI esplicita;
7. pairing device user-friendly senza copiare manualmente token.

## Principio architetturale

Il client iPad non contiene Llama e non replica Tutor Core. PDFKit/PencilKit, cache locale e networking vivono sul dispositivo; inferenza, RAG, mastery, curriculum e knowledge graph restano sul Tutor Server.
