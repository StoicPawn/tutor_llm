import os,tempfile,unittest
from types import SimpleNamespace
import studyforge.db as db
from studyforge.workspaces import ensure_default_workspace, create_workspace
from studyforge.sessions import start_session
from studyforge.study_view import study_workspace_state, selection_context, contextual_tutor_request

class StudyViewTests(unittest.TestCase):
    def setUp(self):
        fd,self.path=tempfile.mkstemp(suffix='.db'); os.close(fd); os.unlink(self.path)
        self.old=db.settings; db.settings=SimpleNamespace(db_path=self.path)
        ensure_default_workspace(); self.wid=create_workspace('Math')
        self.did=db.add_document(self.wid,'book.pdf','/tmp/book.pdf')
        db.add_pages(self.did,[{'page':1,'text':'The derivative is the limit of the incremental ratio.','blocks':[{'bbox':[0,0,100,20],'text':'The derivative is the limit of the incremental ratio.'}],'width':200,'height':300,'ocr_used':False}])
        db.add_chunks(self.did,[{'page':1,'chunk_index':0,'text':'The derivative is the limit of the incremental ratio.'}],[[1.0,0.0]])
        self.sid=start_session(self.wid,'learn calculus')
    def tearDown(self):
        db.settings=self.old
        try: os.unlink(self.path)
        except OSError: pass
    def test_state_contains_page_and_documents(self):
        state=study_workspace_state(self.wid,self.sid,self.did,1)
        self.assertEqual(state['page']['document_name'],'book.pdf')
        self.assertEqual(state['active_document_id'],self.did)
        self.assertTrue(state['documents'])
    def test_contextual_request_keeps_provenance(self):
        selection=selection_context(self.wid,self.did,1,'derivative is the limit')
        prompt=contextual_tutor_request('why',selection,'use intuition first')
        self.assertIn('book.pdf, p. 1',prompt)
        self.assertIn('use intuition first',prompt)
        self.assertIn('PASSAGGIO SELEZIONATO',prompt)

if __name__=='__main__': unittest.main()
