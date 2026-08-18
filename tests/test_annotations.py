import os,tempfile,unittest
from types import SimpleNamespace
import studyforge.db as db
import studyforge.annotations as annotations
from studyforge.workspaces import ensure_default_workspace, create_workspace

class AnnotationTests(unittest.TestCase):
    def setUp(self):
        fd,self.path=tempfile.mkstemp(suffix='.db'); os.close(fd); os.unlink(self.path)
        self.old_db=db.settings; self.old_ann=annotations.connect
        db.settings=SimpleNamespace(db_path=self.path)
        annotations.connect=db.connect
        ensure_default_workspace(); self.w1=create_workspace('Math'); self.w2=create_workspace('OS')
        self.d1=db.add_document(self.w1,'math.pdf','/tmp/math.pdf'); self.d2=db.add_document(self.w2,'os.pdf','/tmp/os.pdf')
    def tearDown(self):
        db.settings=self.old_db; annotations.connect=self.old_ann
        try: os.unlink(self.path)
        except OSError: pass
    def test_annotation_isolation(self):
        aid=annotations.create_annotation(self.w1,self.d1,2,'highlight',bbox=[1,2,30,40],text='limite')
        self.assertEqual(len(annotations.list_annotations(self.w1,self.d1,2)),1)
        self.assertEqual(annotations.list_annotations(self.w2,self.d2,2),[])
        self.assertEqual(annotations.list_annotations(self.w1,self.d1,2)[0]['id'],aid)
    def test_ink_roundtrip(self):
        payload={'strokes':[{'tool':'pen','width':2.5,'points':[[1,2,0.5],[3,4,0.7]]}]}
        annotations.create_annotation(self.w1,self.d1,1,'ink',payload=payload)
        row=annotations.list_annotations(self.w1,self.d1,1)[0]
        self.assertEqual(row['kind'],'ink'); self.assertEqual(row['payload']['strokes'][0]['tool'],'pen')
    def test_reject_cross_workspace_document(self):
        with self.assertRaises(ValueError): annotations.create_annotation(self.w1,self.d2,1,'bookmark')

if __name__=='__main__': unittest.main()
