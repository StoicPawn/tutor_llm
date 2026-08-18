import os, tempfile, unittest
from datetime import datetime, timezone
from types import SimpleNamespace
import studyforge.db as db

class PageContextTests(unittest.TestCase):
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

    def test_page_lookup_respects_workspace(self):
        d=db.add_document(self.w1,'book.pdf','/tmp/book.pdf')
        db.add_pages(d,[{'page':1,'text':'theorem','blocks':[{'bbox':[0,0,10,10],'text':'theorem'}],'width':100,'height':200,'ocr_used':False}])
        self.assertEqual(db.get_document_page(self.w1,d,1)['text'],'theorem')
        self.assertIsNone(db.get_document_page(self.w2,d,1))

if __name__=='__main__': unittest.main()
