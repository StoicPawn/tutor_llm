from __future__ import annotations
from .config import settings
from .ollama_client import chat
from .retrieval import retrieve
from .student import mastery_for

MODE_GUIDES = {
    "Breve": "Micro-lezione di 5-8 minuti: intuizione, concetti essenziali, un esempio e punti da ricordare.",
    "Approfondita": "Lezione approfondita: prerequisiti, spiegazione progressiva, connessioni, esempi, errori comuni, riepilogo e autoverifica.",
    "Ripasso": "Ripasso ad alta densità: mappa concettuale, definizioni, relazioni, flashcard e richiamo attivo.",
}

def _context(topic, document_ids, k=None):
    sources = retrieve(topic, document_ids, k or settings.top_k)
    if not sources: raise ValueError("Nessun contenuto indicizzato disponibile.")
    blocks=[]; compact=[]
    for i,s in enumerate(sources,1):
        loc=f"p. {s['page']}" if s['page'] else f"chunk {s['chunk_index']}"
        blocks.append(f"[FONTE {i}: {s['document_name']}, {loc}]\n{s['text']}")
        compact.append({"n":i,"document":s['document_name'],"page":s['page'],"chunk":s['chunk_index'],"score":round(s['score'],4)})
    return sources, blocks, compact

def build_lesson(topic: str, mode: str, document_ids=None):
    _, blocks, compact = _context(topic, document_ids)
    mastery = mastery_for(topic)
    level = "principiante" if mastery < .35 else "intermedio" if mastery < .70 else "avanzato"
    prompt=f'''Sei un docente rigoroso. Insegna ESCLUSIVAMENTE dal materiale. Ogni affermazione sostanziale deve avere [FONTE N].
Se manca evidenza, dichiaralo. Non fingere che una fonte dica qualcosa che non dice. Lingua: italiano.
ARGOMENTO: {topic}\nMODALITÀ: {mode}\nPADRONANZA STIMATA: {mastery:.0%} ({level}).
Adatta difficoltà e prerequisiti a questa stima. {MODE_GUIDES.get(mode, MODE_GUIDES['Approfondita'])}
MATERIALE:\n{chr(10).join(blocks)}
Struttura in Markdown. Chiudi con: Punti chiave, Verifica rapida, Fonti usate.'''
    content=chat([{"role":"system","content":"Sei StudyForge, tutor locale orientato a comprensione, accuratezza e active recall."},{"role":"user","content":prompt}],temperature=.12)
    return content,compact

def build_quiz(topic: str, document_ids=None, n: int=8) -> str:
    _, blocks, _ = _context(topic, document_ids, min(settings.top_k,10))
    material='\n\n'.join(blocks)
    return chat([{"role":"user","content":f'''Crea un quiz di {n} domande in italiano basato soltanto sul materiale. Mescola risposta aperta e scelta multipla. Soluzioni in fondo, separate, con breve spiegazione e [FONTE N]. Tema: {topic}\n{material}'''}],temperature=.08)

def answer_question(question: str, document_ids=None) -> tuple[str,list[dict]]:
    _,blocks,compact=_context(question,document_ids)
    answer=chat([{"role":"system","content":"Rispondi solo dalle fonti fornite, in italiano. Cita [FONTE N]. Se non basta, dillo."},{"role":"user","content":f"DOMANDA: {question}\n\nFONTI:\n"+'\n\n'.join(blocks)}],temperature=.05)
    return answer,compact
