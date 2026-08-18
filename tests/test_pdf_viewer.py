import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import fitz
import studyforge.db as db
import studyforge.pdf_viewer as pv
from studyforge.workspaces import ensure_default_workspace, create_workspace

class PdfViewerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.old_db=db.settings
        db.settings=SimpleNamespace(db_path=str(root/'studyforge.db'))
        ensure_default_workspace(); self.wid=create_workspace('Math'); self.other=create_workspace('Other')
        pdf=root/'book.pdf'
        doc=fitz.open(); page=doc.new_page(width=400,height=600); page.insert_text((50,80),'Tutor LLM PDF viewer test'); doc.save(pdf); doc.close()
        self.did=db.add_document(self.wid,'book.pdf',str(pdf))
        db.add_pages(self.did,[{'page':1,'text':'Tutor LLM PDF viewer test','blocks':[{'bbox':[50,60,230,90],'text':'Tutor LLM PDF viewer test'}],'width':400,'height':600,'ocr_used':False}])
    def tearDown(self):
        db.settings=self.old_db; self.tmp.cleanup()
    def test_render_and_geometry(self):
        r=pv.render_pdf_page(self.wid,self.did,1,2.0)
        self.assertEqual(r['page_count'],1); self.assertEqual(r['render_width'],800); self.assertTrue(r['png'].startswith(b'\x89PNG'))
        bb=pv.normalize_render_bbox([100,120,460,180],800,1200,400,600)
        self.assertEqual(bb,[50.0,60.0,230.0,90.0])
        selected=pv.blocks_in_bbox(self.wid,self.did,1,bb)
        self.assertIn('Tutor LLM',selected['text'])
    def test_workspace_isolation(self):
        with self.assertRaises(ValueError): pv.render_pdf_page(self.other,self.did,1)

if __name__=='__main__': unittest.main()
