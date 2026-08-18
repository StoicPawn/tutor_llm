import tempfile, unittest, uuid
from pathlib import Path
from types import SimpleNamespace
import studyforge.db as db
import studyforge.offline_sync as sync
from studyforge.workspaces import ensure_default_workspace, create_workspace

class OfflineSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.old=db.settings; db.settings=SimpleNamespace(db_path=str(root/'db.sqlite'),upload_dir=str(root/'uploads'))
        ensure_default_workspace(); self.wid=create_workspace('Math')
    def tearDown(self):
        db.settings=self.old; self.tmp.cleanup()
    def test_push_pull_and_conflict(self):
        cid=str(uuid.uuid4())
        a=sync.push_change(self.wid,'note',cid,0,{'title':'A','content':'one'})
        self.assertEqual(a['status'],'applied'); self.assertEqual(a['object']['revision'],1)
        feed=sync.pull_changes(self.wid,0); self.assertEqual(len(feed['changes']),1)
        b=sync.push_change(self.wid,'note',cid,1,{'title':'A','content':'two'})
        self.assertEqual(b['object']['revision'],2)
        conflict=sync.push_change(self.wid,'note',cid,1,{'title':'A','content':'stale'})
        self.assertEqual(conflict['status'],'conflict'); self.assertEqual(conflict['expected_revision'],2)
    def test_tombstone_is_synced(self):
        cid=str(uuid.uuid4()); sync.push_change(self.wid,'annotation',cid,0,{'text':'x'})
        deleted=sync.push_change(self.wid,'annotation',cid,1,{},True)
        self.assertTrue(deleted['object']['deleted'])
        feed=sync.pull_changes(self.wid,1); self.assertEqual(feed['changes'][-1]['operation'],'delete')

if __name__=='__main__': unittest.main()
