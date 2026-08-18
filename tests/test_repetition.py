import os, tempfile, unittest
from datetime import datetime, timezone
from unittest.mock import patch

class RepetitionTests(unittest.TestCase):
    def test_review_items_are_workspace_isolated(self):
        fd,path=tempfile.mkstemp(suffix='.db'); os.close(fd)
        try:
            with patch('studyforge.config.settings.db_path', path):
                from studyforge.db import connect
                from studyforge.repetition import schedule_concept, upcoming_reviews
                now=datetime.now(timezone.utc).isoformat()
                with connect() as con:
                    w1=int(con.execute('INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)',('Math','','',now)).lastrowid)
                    w2=int(con.execute('INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)',('OS','','',now)).lastrowid)
                schedule_concept(w1,'derivatives'); schedule_concept(w2,'processes')
                self.assertEqual([r['concept'] for r in upcoming_reviews(w1)], ['derivatives'])
                self.assertEqual([r['concept'] for r in upcoming_reviews(w2)], ['processes'])
        finally:
            try: os.unlink(path)
            except OSError: pass

if __name__=='__main__': unittest.main()
