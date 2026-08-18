from __future__ import annotations
import json, re
from .db import iter_chunks
from .inference import chat


def _parse_json(text: str) -> dict:
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I | re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.S)
        if not m:
            raise ValueError('Analisi copertura non valida.')
        return json.loads(m.group(0))


def _sample(workspace_id: int, document_ids: list[int] | None, max_chars: int = 50000) -> str:
    rows = list(iter_chunks(workspace_id, document_ids))
    if not rows:
        raise ValueError('Il workspace non contiene materiale indicizzato.')
    step = max(1, len(rows) // 30)
    chosen = rows[::step][:36]
    blocks, used = [], 0
    for row in chosen:
        loc = f"p.{row['page']}" if row['page'] else f"sez.{row['chunk_index']}"
        block = f"[{row['document_name']} {loc}]\n{row['text']}\n"
        if used + len(block) > max_chars:
            break
        blocks.append(block); used += len(block)
    return '\n'.join(blocks)


def analyze_coverage(workspace_id: int, goal: str, document_ids: list[int] | None = None) -> dict:
    material = _sample(workspace_id, document_ids)
    prompt = f'''Agisci come progettista di curriculum esperto. L'obiettivo dello studente è:
{goal}

Valuta quanto il materiale caricato copre realmente le competenze necessarie per raggiungere l'obiettivo. Non fingere che la biblioteca sia sufficiente.
Restituisci SOLO JSON valido:
{{
  "coverage": 0.0,
  "level_supported": "...",
  "strong": [{{"topic":"...","evidence":"..."}}],
  "partial": [{{"topic":"...","reason":"..."}}],
  "missing": [{{"topic":"...","why_needed":"..."}}],
  "recommended_next": ["..."],
  "library_assessment": "..."
}}
Coverage tra 0 e 1. Se l'obiettivo richiede conoscenze avanzate non presenti, elencale in missing. Non inventare titoli di libri specifici: descrivi invece che tipo di materiale servirebbe.

CAMPIONE DELLA BIBLIOTECA:
{material}'''
    data = _parse_json(chat([
        {'role': 'system', 'content': 'Sei un curriculum architect rigoroso. Distingui copertura reale da conoscenza esterna. Produci solo JSON.'},
        {'role': 'user', 'content': prompt},
    ], temperature=.03))
    coverage = max(0.0, min(1.0, float(data.get('coverage', 0.0))))
    return {
        'coverage': coverage,
        'level_supported': str(data.get('level_supported', '')),
        'strong': list(data.get('strong', [])),
        'partial': list(data.get('partial', [])),
        'missing': list(data.get('missing', [])),
        'recommended_next': list(data.get('recommended_next', [])),
        'library_assessment': str(data.get('library_assessment', '')),
    }
