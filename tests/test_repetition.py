import os, tempfile, unittest
from datetime import datetime, timezone
from types import SimpleNamespace
import studyforge.db as db
from studyforge.repetition import schedule_concept, upcoming_reviews

class RepetitionTests(unittest.TestCase):
    def setUp(self):
        fd,self.path=tempfile.mkstemp(suffix='.db'); os.close(fd); os.unlink(self.path)
        self.old_settings=db.settings; db.settings=SimpleNamespace(db_path=self.path)
        now=datetime.now(timezone.utc).isoformat()
        with db.connect() as con:
            self.w1=int(con.execute('INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)',('Math','','',now)).lastrowid)
            self.w2=int(con.execute('INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)',('OS','','',now)).lastrowid)

    def tearDown(self):
        db.settings=self.old_settings
        try: os.unlink(self.path)
        except OSError: pass

    def test_review_items_are_workspace_isolated(self):
        schedule_concept(self.w1,'derivatives'); schedule_concept(self.w2,'processes')
        self.assertEqual([r['concept'] for r in upcoming_reviews(self.w1)],['derivatives'])
        self.assertEqual([r['concept'] for r in upcoming_reviews(self.w2)],['processes'])

if __name__=='__main__': unittest.main()
