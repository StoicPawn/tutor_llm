from __future__ import annotations
import json, re
from datetime import datetime, timezone
from .db import connect, iter_chunks
from .ollama_client import chat

SCHEMA = '''
CREATE TABLE IF NOT EXISTS knowledge_nodes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 name TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 node_type TEXT NOT NULL DEFAULT 'concept',
 importance REAL NOT NULL DEFAULT .5,
 evidence_json TEXT NOT NULL DEFAULT '[]',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(workspace_id,name),
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS knowledge_edges (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 source_id INTEGER NOT NULL,
 target_id INTEGER NOT NULL,
 relation TEXT NOT NULL,
 strength REAL NOT NULL DEFAULT .5,
 evidence_json TEXT NOT NULL DEFAULT '[]',
 UNIQUE(workspace_id,source_id,target_id,relation),
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
 FOREIGN KEY(source_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
 FOREIGN KEY(target_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_workspace ON knowledge_nodes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_edges_workspace ON knowledge_edges(workspace_id);
'''


def _ensure():
    with connect() as con:
        con.executescript(SCHEMA)


def _json_object(text: str) -> dict:
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I | re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.S)
        if not m:
            raise ValueError('Il modello non ha restituito un knowledge graph JSON valido.')
        return json.loads(m.group(0))


def _sample(workspace_id: int, document_ids: list[int] | None, max_chars: int = 48000) -> str:
    rows = list(iter_chunks(workspace_id, document_ids))
    if not rows:
        raise ValueError('Nessun contenuto disponibile nel workspace.')
    step = max(1, len(rows) // 32)
    chosen = rows[::step][:36]
    out, used = [], 0
    for r in chosen:
        loc = f"p.{r['page']}" if r['page'] else f"chunk {r['chunk_index']}"
        block = f"[{r['document_name']} {loc}]\n{r['text']}\n"
        if used + len(block) > max_chars:
            break
        out.append(block); used += len(block)
    return '\n'.join(out)


def rebuild_graph(workspace_id: int, document_ids: list[int] | None = None, max_nodes: int = 40) -> dict:
    _ensure()
    material = _sample(workspace_id, document_ids)
    prompt = f'''Costruisci un knowledge graph didattico dal materiale seguente.
Restituisci SOLO JSON valido con questa struttura:
{{"nodes":[{{"name":"...","description":"...","type":"concept|definition|theorem|method|skill","importance":0.0,"evidence":["fonte breve"]}}],
"edges":[{{"source":"nome nodo","target":"nome nodo","relation":"prerequisite|explains|part_of|contrasts|applies_to|generalizes","strength":0.0,"evidence":["fonte breve"]}}]}}.
Regole: massimo {max_nodes} nodi; usa solo concetti sostenuti dal materiale; nomi brevi e univoci; le relazioni devono essere utili allo studio.
MATERIALE:\n{material}'''
    data = _json_object(chat([
        {'role':'system','content':'Sei un knowledge engineer didattico rigoroso. Produci solo JSON valido.'},
        {'role':'user','content':prompt},
    ], temperature=.05))
    nodes = data.get('nodes', [])[:max_nodes]
    edges = data.get('edges', [])
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        con.execute('DELETE FROM knowledge_edges WHERE workspace_id=?', (workspace_id,))
        con.execute('DELETE FROM knowledge_nodes WHERE workspace_id=?', (workspace_id,))
        ids: dict[str, int] = {}
        for n in nodes:
            name = str(n.get('name','')).strip()[:180]
            if not name or name in ids:
                continue
            cur = con.execute('''INSERT INTO knowledge_nodes(workspace_id,name,description,node_type,importance,evidence_json,created_at,updated_at)
                                 VALUES(?,?,?,?,?,?,?,?)''',
                              (workspace_id, name, str(n.get('description',''))[:1400], str(n.get('type','concept'))[:40],
                               max(0., min(1., float(n.get('importance', .5)))), json.dumps(n.get('evidence', []), ensure_ascii=False), now, now))
            ids[name] = int(cur.lastrowid)
        count_edges = 0
        for e in edges:
            s, t = str(e.get('source','')).strip(), str(e.get('target','')).strip()
            if s not in ids or t not in ids or s == t:
                continue
            con.execute('''INSERT OR IGNORE INTO knowledge_edges(workspace_id,source_id,target_id,relation,strength,evidence_json)
                           VALUES(?,?,?,?,?,?)''',
                        (workspace_id, ids[s], ids[t], str(e.get('relation','related'))[:40],
                         max(0., min(1., float(e.get('strength', .5)))), json.dumps(e.get('evidence', []), ensure_ascii=False)))
            count_edges += 1
    return {'nodes': len(ids), 'edges': count_edges}


def graph(workspace_id: int) -> dict:
    _ensure()
    with connect() as con:
        nodes = [dict(r) for r in con.execute('SELECT * FROM knowledge_nodes WHERE workspace_id=? ORDER BY importance DESC,name', (workspace_id,)).fetchall()]
        edges = [dict(r) for r in con.execute('''SELECT e.*, s.name source, t.name target FROM knowledge_edges e
                                                  JOIN knowledge_nodes s ON s.id=e.source_id JOIN knowledge_nodes t ON t.id=e.target_id
                                                  WHERE e.workspace_id=? ORDER BY e.strength DESC''', (workspace_id,)).fetchall()]
    return {'nodes': nodes, 'edges': edges}


def prerequisites(workspace_id: int, concept: str) -> list[str]:
    _ensure()
    with connect() as con:
        rows = con.execute('''SELECT s.name FROM knowledge_edges e
                              JOIN knowledge_nodes s ON s.id=e.source_id
                              JOIN knowledge_nodes t ON t.id=e.target_id
                              WHERE e.workspace_id=? AND t.name=? AND e.relation='prerequisite'
                              ORDER BY e.strength DESC''', (workspace_id, concept)).fetchall()
    return [r['name'] for r in rows]
