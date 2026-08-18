from __future__ import annotations
from .repetition import due_reviews
from .flashcards import list_flashcards
from .student import mastery_for


def review_queue(workspace_id:int, limit:int=20)->list[dict]:
    due=[dict(r) for r in due_reviews(workspace_id,limit*2)]
    cards=list_flashcards(workspace_id,200)
    by_concept={}
    for c in cards:
        by_concept.setdefault(c['concept'].strip().lower(),[]).append(c)
    out=[]
    for r in due:
        concept=r['concept']
        card_list=by_concept.get(concept.strip().lower(),[])
        out.append({
            'type':'flashcard' if card_list else 'concept_review',
            'concept':concept,
            'mastery':mastery_for(workspace_id,concept),
            'due_at':r['due_at'],
            'interval_days':r['interval_days'],
            'flashcard':card_list[0] if card_list else None,
        })
        if len(out)>=limit: break
    return out
