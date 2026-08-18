from __future__ import annotations
import json, re
from .config import settings
from .inference import chat
from .retrieval import retrieve
from .student import record_result


def _parse_json(text: str) -> dict:
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I | re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.S)
        if not match:
            raise ValueError('Il grader non ha restituito JSON valido.')
        return json.loads(match.group(0))


def grade_answer(
    workspace_id: int,
    topic: str,
    question: str,
    user_answer: str,
    document_ids: list[int] | None = None,
    *,
    event_type: str = 'graded_answer',
) -> dict:
    sources = retrieve(workspace_id, f"{topic}\n{question}", document_ids, min(settings.top_k, 10))
    if not sources:
        raise ValueError('Nessuna fonte disponibile per valutare la risposta.')
    blocks = []
    compact = []
    for i, source in enumerate(sources, 1):
        loc = f"p. {source['page']}" if source['page'] else f"chunk {source['chunk_index']}"
        blocks.append(f"[FONTE {i}: {source['document_name']}, {loc}]\n{source['text']}")
        compact.append({
            'n': i,
            'document': source['document_name'],
            'page': source['page'],
            'chunk': source['chunk_index'],
            'score': round(source['score'], 4),
        })
    material = '\n\n'.join(blocks)
    prompt = f'''Valuta rigorosamente la risposta dello studente usando il materiale fornito.
TEMA: {topic}
DOMANDA: {question}
RISPOSTA STUDENTE: {user_answer}

MATERIALE AUTOREVOLE:
{material}

Restituisci SOLO JSON valido con questa struttura:
{{
  "score": 0.0,
  "correct": ["..."],
  "missing": ["..."],
  "errors": ["..."],
  "feedback": "...",
  "next_question": "..."
}}
Score tra 0 e 1. Non penalizzare formulazioni diverse se concettualmente corrette. Ogni errore fattuale deve essere verificabile nel materiale.'''
    data = _parse_json(chat([
        {'role': 'system', 'content': 'Sei un correttore didattico severo ma calibrato. Produci soltanto JSON.'},
        {'role': 'user', 'content': prompt},
    ], temperature=.02))
    score = max(0.0, min(1.0, float(data.get('score', 0.0))))
    mastery = record_result(workspace_id, topic, score, event_type)
    return {
        'score': score,
        'mastery': mastery,
        'correct': list(data.get('correct', [])),
        'missing': list(data.get('missing', [])),
        'errors': list(data.get('errors', [])),
        'feedback': str(data.get('feedback', '')),
        'next_question': str(data.get('next_question', '')),
        'sources': compact,
    }
