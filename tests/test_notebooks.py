import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import studyforge.db as db
import studyforge.notebooks as notebooks
from studyforge.workspaces import ensure_default_workspace, create_workspace


class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        fake=SimpleNamespace(db_path=str(root/'studyforge.db'),upload_dir=str(root/'uploads'))
        self.old_db=db.settings; self.old_nb=notebooks.connect.__globals__['settings'] if 'settings' in notebooks.connect.__globals__ else None
        db.settings=fake
        ensure_default_workspace(); self.w1=create_workspace('Math'); self.w2=create_workspace('OS')

    def tearDown(self):
        db.settings=self.old_db; self.tmp.cleanup()

    def test_notebook_roundtrip_and_isolation(self):
        nid=notebooks.create_notebook(self.w1,'Analisi',concept='Limiti')
        book=notebooks.get_notebook(self.w1,nid)
        self.assertEqual(book['title'],'Analisi'); self.assertEqual(len(book['pages']),1)
        page=book['pages'][0]
        layers=[
            {'kind':'text','text':'epsilon-delta','x':10,'y':20},
            {'kind':'ink','strokes':[{'tool':'pen','points':[[1,2,.5],[3,4,.8]]}]},
        ]
        saved=notebooks.save_page(self.w1,nid,page['id'],layers=layers,background='grid')
        self.assertEqual(saved['background'],'grid'); self.assertEqual(saved['layers'][1]['kind'],'ink')
        self.assertIsNone(notebooks.get_notebook(self.w2,nid))
        with self.assertRaises(ValueError): notebooks.save_page(self.w2,nid,page['id'],layers=[])

    def test_add_page(self):
        nid=notebooks.create_notebook(self.w1,'Quaderno')
        p=notebooks.add_page(self.w1,nid,title='Seconda',background='dot')
        self.assertEqual(p['position'],2); self.assertEqual(p['background'],'dot')

if __name__=='__main__': unittest.main()
