from __future__ import annotations
import json
from pathlib import Path
from studyforge.db import rated_lessons

out = Path("training/feedback_sft.jsonl")
rows = rated_lessons()
with out.open("w", encoding="utf-8") as f:
    for r in rows:
        if int(r["rating"]) < 4:
            continue
        record = {
            "messages": [
                {"role": "system", "content": "Sei StudyForge, un tutor rigoroso, chiaro e orientato alla comprensione."},
                {"role": "user", "content": f"Crea una lezione {r['mode'].lower()} sul tema: {r['topic']}"},
                {"role": "assistant", "content": r["content"]},
            ],
            "metadata": {"rating": r["rating"], "feedback": r["feedback"] or ""},
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
print(f"Esportati {sum(1 for r in rows if int(r['rating']) >= 4)} esempi in {out}")
