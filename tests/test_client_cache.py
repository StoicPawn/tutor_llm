import tempfile, unittest
from pathlib import Path
from studyforge.client_cache import ClientCacheStore, ClientSyncEngine

class FakeClient:
    def __init__(self): self.objects={}; self.cursor=0
    def sync_pull(self,workspace_id,since=0,limit=500): return {'workspace_id':workspace_id,'cursor':self.cursor,'changes':[]}
    def sync_push(self,workspace_id,entity_type,client_uuid,base_revision,payload,deleted=False,server_id=None):
        current=self.objects.get(client_uuid)
        expected=current['revision'] if current else 0
        if base_revision!=expected: return {'status':'conflict','server':current,'expected_revision':expected}
        obj={'workspace_id':workspace_id,'entity_type':entity_type,'client_uuid':client_uuid,'server_id':server_id or 10,'revision':expected+1,'deleted':deleted,'payload':payload}
        self.objects[client_uuid]=obj; self.cursor+=1; return {'status':'applied','object':obj}
    def workspace_manifest(self,workspace_id): return {'workspace_id':workspace_id,'revision':f'r{self.cursor}'}
    def download_document(self,workspace_id,document_id,destination):
        p=Path(destination); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'%PDF-test'); return p

class ClientCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.store=ClientCacheStore(Path(self.tmp.name)/'cache.db'); self.client=FakeClient(); self.engine=ClientSyncEngine(self.client,self.store)
    def tearDown(self): self.tmp.cleanup()
    def test_offline_edit_pushes_and_becomes_clean(self):
        cid=self.store.edit_local(1,'note',{'title':'offline','content':'x'})
        self.assertEqual(len(self.store.dirty(1)),1)
        result=self.engine.sync(1)
        self.assertEqual(result['pushed'],1); self.assertEqual(result['conflicts'],0)
        obj=[x for x in self.store.objects(1) if x['client_uuid']==cid][0]
        self.assertFalse(obj['dirty']); self.assertEqual(obj['revision'],1)
    def test_conflict_is_preserved_for_user_resolution(self):
        cid=self.store.edit_local(1,'note',{'title':'a'},client_uuid='11111111-1111-4111-8111-111111111111')
        self.client.objects[cid]={'entity_type':'note','client_uuid':cid,'server_id':7,'revision':2,'deleted':False,'payload':{'title':'server'}}
        result=self.engine.sync(1); self.assertEqual(result['conflicts'],1)
        obj=self.store.objects(1)[0]; self.assertTrue(obj['dirty']); self.assertIsNotNone(obj['conflict'])
    def test_document_can_be_cached_offline(self):
        path=self.engine.cache_document(1,3,'book.pdf',Path(self.tmp.name)/'docs')
        self.assertTrue(path.exists()); self.assertEqual(self.store.document_status(1,3)['status'],'available')

if __name__=='__main__': unittest.main()
