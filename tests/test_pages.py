import os, tempfile, unittest
from datetime import datetime, timezone
from unittest.mock import patch

class PageContextTests(unittest.TestCase):
    def test_page_lookup_respects_workspace(self):
        fd,path=tempfile.mkstemp(suffix='.db'); os.close(fd)
        try:
            with patch('studyforge.config.settings.db_path', path):
                from studyforge.db import connect, add_document, add_pages, get_document_page
                now=datetime.now(timezone.utc).isoformat()
                with connect() as con:
                    w1=int(con.execute('INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)',('Math','','',now)).lastrowid)
                    w2=int(con.execute('INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)',('OS','','',now)).lastrowid)
                d=add_document(w1,'book.pdf','/tmp/book.pdf')
                add_pages(d,[{'page':1,'text':'theorem','blocks':[{'bbox':[0,0,10,10],'text':'theorem'}],'width':100,'height':200,'ocr_used':False}])
                self.assertEqual(get_document_page(w1,d,1)['text'],'theorem')
                self.assertIsNone(get_document_page(w2,d,1))
        finally:
            try: os.unlink(path)
            except OSError: pass

if __name__=='__main__': unittest.main()
