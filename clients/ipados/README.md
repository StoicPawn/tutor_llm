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
- lista workspace e documenti
- viewer PDF nativo con PDFKit
- split view adatta a iPad
- Tutor contestuale al documento/pagina corrente
- canvas PencilKit
- cache nativa SwiftData per stato sync e artefatti personali
- download dei PDF in Application Support per lettura offline
- dirty queue per modifiche create senza rete
- pull/push del change feed Tutor LLM v0.11+
- rilevazione conflitti senza last-write-wins distruttivo
- cursor e manifest persistenti per workspace
- indicatori UI per PDF offline, sincronizzazione e conflitti

## Modello offline

Il server resta source of truth per inferenza, RAG, curriculum, mastery e knowledge graph. Il client può però conservare localmente PDF e artefatti personali.

```text
Tutor Server
    ⇅ sync
SwiftData cache iPad
    ├── cursor / manifest
    ├── note / annotation / notebook_page
    ├── dirty queue
    ├── conflitti
    └── riferimenti ai PDF offline

Application Support
    └── copie PDF disponibili offline

Keychain
    └── token dispositivo
```

Il ciclo client è conservativo:

```text
pull → applica modifiche remote non dirty → push dirty queue → conserva conflitti → aggiorna cursor
```

Se il server non è raggiungibile, i PDF già scaricati restano leggibili e le modifiche personali possono restare accodate fino alla connessione successiva.

## Stato PencilKit

Il canvas PencilKit è già nativo e funzionante. Il backend supporta `notebook_page` con layer ink vettoriali; resta da completare la conversione bidirezionale `PKDrawing ↔ layer ink Tutor LLM` e la scelta/creazione del quaderno server a cui associare il foglio corrente.

## Selezione PDF

Il prossimo passaggio del reader è collegare le selezioni native PDFKit al contratto già disponibile sul server:

- `/documents/render-selection`
- `/study/context-action`

per azioni immediate come **Spiegami**, **Perché?**, **Approfondisci**, **Esempio**, **Esercizio** e **Prerequisiti**.

## CI

`.github/workflows/ipados.yml` gira su macOS, installa XcodeGen, genera il progetto e prova una build per iOS Simulator con code signing disabilitato.

## Principio architetturale

Il client iPad non contiene Llama e non replica Tutor Core. PDFKit/PencilKit, cache locale e networking vivono sul dispositivo; inferenza, RAG, mastery, curriculum e knowledge graph restano sul Tutor Server.
