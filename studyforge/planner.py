from __future__ import annotations
from .curriculum import list_curricula, next_node, curriculum_document_ids
from .repetition import due_reviews
from .student import weakest, mastery_for
from .knowledge import prerequisites


def next_best_activity(workspace_id: int) -> dict:
    """Choose one actionable study activity from reviews, weak concepts and curriculum progress."""
    due = due_reviews(workspace_id, 20)
    if due:
        ranked = sorted(due, key=lambda r: (float(r['last_score']) if r['last_score'] is not None else 0.0, r['due_at']))
        r = ranked[0]
        return {
            'type': 'review',
            'concept': r['concept'],
            'reason': 'Il concetto è scaduto nello spaced repetition ed è prioritario per evitare decadimento.',
            'score': float(r['last_score']) if r['last_score'] is not None else None,
            'due_at': r['due_at'],
            'recommended_mode': 'interactive_exercise',
        }

    weak = weakest(workspace_id, 12)
    weak_candidates = [r for r in weak if int(r['attempts']) >= 2 and float(r['mastery']) < .55]
    if weak_candidates:
        r = weak_candidates[0]
        prereq = prerequisites(workspace_id, r['name'])
        return {
            'type': 'remediation',
            'concept': r['name'],
            'reason': 'La mastery osservata è bassa dopo più evidenze: conviene recuperare prima di avanzare.',
            'mastery': float(r['mastery']),
            'prerequisites': prereq,
            'recommended_mode': 'deep_lesson_then_exercise',
        }

    curricula = list_curricula(workspace_id)
    for c in curricula:
        node = next_node(workspace_id, int(c['id']))
        if node:
            return {
                'type': 'advance',
                'concept': node['title'],
                'description': node['description'],
                'curriculum_id': int(c['id']),
                'document_ids': curriculum_document_ids(workspace_id, int(c['id'])),
                'mastery': mastery_for(workspace_id, node['title']),
                'reason': 'Non ci sono ripassi urgenti o lacune forti: puoi avanzare nel percorso rispettando i prerequisiti.',
                'recommended_mode': 'lesson_then_recall',
            }

    if weak:
        r = weak[0]
        return {
            'type': 'practice',
            'concept': r['name'],
            'mastery': float(r['mastery']),
            'reason': 'Non esiste un percorso attivo; consolida il concetto meno padroneggiato già osservato.',
            'recommended_mode': 'interactive_exercise',
        }

    return {
        'type': 'setup',
        'concept': None,
        'reason': 'Non ci sono ancora evidenze sufficienti. Indicizza materiale e crea un percorso o avvia una prima sessione di studio.',
        'recommended_mode': 'create_curriculum',
    }
