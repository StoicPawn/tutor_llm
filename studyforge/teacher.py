from __future__ import annotations
from .config import settings
from .inference import chat
from .retrieval import retrieve
from .student import mastery_for

MODE_GUIDES = {
    "Breve": "Micro-lezione di 5-8 minuti: intuizione, concetti essenziali, un esempio e punti da ricordare.",
    "Approfondita": "Lezione approfondita: prerequisiti, spiegazione progressiva, connessioni, esempi, errori comuni, riepilogo e autoverifica.",
    "Ripasso": "Ripasso ad alta densità: mappa concettuale, definizioni, relazioni, flashcard e richiamo attivo.",
}

EPISTEMIC_GUIDES = {
    "Grounded": "Usa esclusivamente il materiale fornito. Se manca evidenza, dichiaralo e fermati.",
    "Tutor": "Il materiale è la fonte primaria. Puoi aggiungere conoscenza generale solo per spiegare prerequisiti, analogie o passaggi didattici; marca ogni aggiunta come [CONOSCENZA GENERALE].",
    "Expert": "Il materiale è la fonte primaria. Puoi integrare conoscenza generale per costruire una visione esperta e indicare lacune della biblioteca; marca le integrazioni come [CONOSCENZA GENERALE] e le lacune come [LACUNA BIBLIOTECA].",
}


def _context(workspace_id: int, topic: str, document_ids, k=None):
    sources = retrieve(workspace_id, topic, document_ids, k or settings.top_k)
    if not sources:
        raise ValueError("Nessun contenuto indicizzato disponibile nel workspace.")
    blocks, compact = [], []
    for i, s in enumerate(sources, 1):
        loc = f"p. {s['page']}" if s['page'] else f"chunk {s['chunk_index']}"
        blocks.append(f"[FONTE {i}: {s['document_name']}, {loc}]\n{s['text']}")
        compact.append({"n": i, "document": s['document_name'], "page": s['page'], "chunk": s['chunk_index'], "score": round(s['score'], 4)})
    return sources, blocks, compact


def build_lesson(workspace_id: int, topic: str, mode: str, document_ids=None, epistemic_mode: str = "Grounded"):
    _, blocks, compact = _context(workspace_id, topic, document_ids)
    mastery = mastery_for(workspace_id, topic)
    level = "principiante" if mastery < .35 else "intermedio" if mastery < .70 else "avanzato"
    epistemic = EPISTEMIC_GUIDES.get(epistemic_mode, EPISTEMIC_GUIDES["Grounded"])
    prompt = f'''Sei un docente rigoroso e adattivo. Lingua: italiano.
POLITICA EPISTEMICA: {epistemic}
Ogni affermazione derivata dai documenti deve avere [FONTE N]. Non attribuire mai a una fonte ciò che non dice.
ARGOMENTO: {topic}\nMODALITÀ DIDATTICA: {mode}\nPADRONANZA STIMATA: {mastery:.0%} ({level}).
Adatta difficoltà e prerequisiti a questa stima. {MODE_GUIDES.get(mode, MODE_GUIDES['Approfondita'])}
MATERIALE:\n{chr(10).join(blocks)}
Struttura in Markdown. Chiudi con: Punti chiave, Verifica rapida, Fonti usate.'''
    content = chat([
        {"role": "system", "content": "Sei Tutor LLM: accuratezza, comprensione profonda, active recall e provenance rigorosa."},
        {"role": "user", "content": prompt},
    ], temperature=.12)
    return content, compact


def build_quiz(workspace_id: int, topic: str, document_ids=None, n: int = 8, epistemic_mode: str = "Grounded") -> str:
    _, blocks, _ = _context(workspace_id, topic, document_ids, min(settings.top_k, 10))
    policy = EPISTEMIC_GUIDES.get(epistemic_mode, EPISTEMIC_GUIDES["Grounded"])
    material = "\n\n".join(blocks)
    prompt = f'''Crea un quiz di {n} domande in italiano. {policy}
Mescola risposta aperta, scelta multipla e una domanda di ragionamento. Soluzioni in fondo, separate, con breve spiegazione e [FONTE N] quando deriva dal materiale.
Tema: {topic}\nMATERIALE:\n{material}'''
    return chat([{"role": "user", "content": prompt}], temperature=.08)


def answer_question(workspace_id: int, question: str, document_ids=None, epistemic_mode: str = "Grounded") -> tuple[str, list[dict]]:
    _, blocks, compact = _context(workspace_id, question, document_ids)
    policy = EPISTEMIC_GUIDES.get(epistemic_mode, EPISTEMIC_GUIDES["Grounded"])
    answer = chat([
        {"role": "system", "content": f"Rispondi in italiano. {policy} Cita [FONTE N] per ogni informazione tratta dai documenti."},
        {"role": "user", "content": f"DOMANDA: {question}\n\nFONTI:\n" + '\n\n'.join(blocks)},
    ], temperature=.05)
    return answer, compact


def summarize(workspace_id: int, request: str, document_ids=None, epistemic_mode: str = "Grounded") -> tuple[str, list[dict]]:
    _, blocks, compact = _context(workspace_id, request, document_ids, min(settings.top_k + 4, 16))
    policy = EPISTEMIC_GUIDES.get(epistemic_mode, EPISTEMIC_GUIDES["Grounded"])
    material = "\n\n".join(blocks)
    prompt = f'''Produci un riassunto didattico in italiano per: {request}.
{policy}
Distingui concetti centrali, relazioni, formule/definizioni se presenti, errori da evitare e 5 punti di richiamo attivo. Cita [FONTE N].
MATERIALE:\n{material}'''
    content = chat([{"role": "user", "content": prompt}], temperature=.07)
    return content, compact


def deepen(workspace_id: int, topic: str, document_ids=None, epistemic_mode: str = "Tutor") -> tuple[str, list[dict]]:
    _, blocks, compact = _context(workspace_id, topic, document_ids, min(settings.top_k + 4, 16))
    policy = EPISTEMIC_GUIDES.get(epistemic_mode, EPISTEMIC_GUIDES["Tutor"])
    material = "\n\n".join(blocks)
    prompt = f'''Approfondisci il tema "{topic}" fino al livello massimo sostenibile.
{policy}
Costruisci una catena: intuizione → formalizzazione → prerequisiti → collegamenti → casi limite → almeno due esempi → domande aperte per verificare comprensione. Cita [FONTE N].
MATERIALE:\n{material}'''
    content = chat([{"role": "user", "content": prompt}], temperature=.1)
    return content, compact


def build_exercises(workspace_id: int, topic: str, document_ids=None, difficulty: str = "Adattiva", n: int = 6, epistemic_mode: str = "Tutor") -> tuple[str, list[dict]]:
    _, blocks, compact = _context(workspace_id, topic, document_ids, min(settings.top_k + 2, 12))
    mastery = mastery_for(workspace_id, topic)
    policy = EPISTEMIC_GUIDES.get(epistemic_mode, EPISTEMIC_GUIDES["Tutor"])
    material = "\n\n".join(blocks)
    prompt = f'''Genera {n} esercizi sul tema "{topic}". Difficoltà richiesta: {difficulty}; mastery stimata: {mastery:.0%}.
{policy}
Gli esercizi devono crescere da comprensione a trasferimento e ragionamento. Non mostrare subito le soluzioni: crea prima la sezione ESERCIZI, poi una sezione SOLUZIONI separata e facilmente occultabile. Per ogni soluzione spiega il ragionamento e cita [FONTE N] quando pertinente.
MATERIALE:\n{material}'''
    content = chat([{"role": "user", "content": prompt}], temperature=.12)
    return content, compact


def build_reasoning(workspace_id: int, topic: str, document_ids=None, epistemic_mode: str = "Tutor") -> tuple[str, list[dict]]:
    _, blocks, compact = _context(workspace_id, topic, document_ids, min(settings.top_k + 3, 14))
    policy = EPISTEMIC_GUIDES.get(epistemic_mode, EPISTEMIC_GUIDES["Tutor"])
    material = "\n\n".join(blocks)
    prompt = f'''Crea una sessione socratica di ragionamento su "{topic}".
{policy}
Proponi 4 problemi concettuali che richiedano collegamenti tra idee, non semplice memoria. Per ciascuno fornisci: domanda, indizio 1, indizio 2, soluzione ragionata e cosa diagnostica sull'apprendimento. Cita [FONTE N].
MATERIALE:\n{material}'''
    content = chat([{"role": "user", "content": prompt}], temperature=.1)
    return content, compact
