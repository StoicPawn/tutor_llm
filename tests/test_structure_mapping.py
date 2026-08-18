import os,tempfile,unittest
from types import SimpleNamespace
import studyforge.db as db
from studyforge.workspaces import create_workspace, ensure_default_workspace
from studyforge.structure import rebuild_structure, list_sections
from studyforge.source_map import map_selection, store_chunk_spans

class StructureMappingTests(unittest.TestCase):
    def setUp(self):
        fd,self.path=tempfile.mkstemp(suffix='.db'); os.close(fd); os.unlink(self.path)
        self.old=db.settings; db.settings=SimpleNamespace(db_path=self.path)
        ensure_default_workspace(); self.wid=create_workspace('Math')
        self.did=db.add_document(self.wid,'book.pdf','/tmp/book.pdf')
        db.add_pages(self.did,[
            {'page':1,'text':'CAPITOLO 1 Limiti\n1.1 Definizione\nIl limite descrive il comportamento locale.',
             'blocks':[{'bbox':[0,0,100,20],'text':'CAPITOLO 1 Limiti'},{'bbox':[0,30,100,50],'text':'1.1 Definizione'},{'bbox':[0,60,300,90],'text':'Il limite descrive il comportamento locale.'}], 'width':400,'height':600,'ocr_used':False},
            {'page':2,'text':'1.2 Continuità\nLa continuità richiede limite uguale al valore della funzione.', 'blocks':[], 'width':400,'height':600,'ocr_used':False}
        ])
        chunks=[{'page':1,'chunk_index':0,'text':'Il limite descrive il comportamento locale.','char_start':34,'char_end':78}]
        db.add_chunks(self.did,chunks,[[1.0,0.0]]); store_chunk_spans(self.did,chunks)
    def tearDown(self):
        db.settings=self.old
        try: os.unlink(self.path)
        except OSError: pass
    def test_structure_detects_headings_and_valid_ranges(self):
        rows=rebuild_structure(self.wid,self.did)
        self.assertTrue(any('Limiti' in r['title'] for r in rows))
        self.assertGreaterEqual(len(list_sections(self.wid,self.did)),2)
        self.assertTrue(all(int(r['end_page']) >= int(r['start_page']) for r in rows))
    def test_selection_maps_to_chunk_bbox_and_span(self):
        m=map_selection(self.wid,self.did,1,'Il limite descrive il comportamento locale.',[0,55,320,100])
        self.assertEqual(m['matches'][0]['chunk_index'],0)
        self.assertIsNotNone(m['matches'][0]['char_start'])
        self.assertTrue(m['blocks'])
        self.assertEqual(m['citation'],'book.pdf, p. 1')

if __name__=='__main__': unittest.main()
