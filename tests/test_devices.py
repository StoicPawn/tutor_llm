import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import studyforge.db as db
import studyforge.devices as devices
import studyforge.sync as sync
from studyforge.workspaces import ensure_default_workspace, create_workspace


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.old_db=db.settings
        fake=SimpleNamespace(db_path=str(root/'studyforge.db'),upload_dir=str(root/'uploads'))
        db.settings=fake
        ensure_default_workspace(); self.wid=create_workspace('Math')

    def tearDown(self):
        db.settings=self.old_db; self.tmp.cleanup()

    def test_device_token_is_revocable(self):
        created=devices.create_device('iPad','ipados')
        self.assertTrue(created['token'].startswith('tllm_'))
        authenticated=devices.authenticate_device(created['token'],touch=False)
        self.assertEqual(authenticated['name'],'iPad')
        self.assertTrue(devices.revoke_device(created['id']))
        self.assertIsNone(devices.authenticate_device(created['token'],touch=False))

    def test_raw_token_is_not_stored(self):
        created=devices.create_device('Laptop','macos')
        with db.connect() as con:
            row=con.execute('SELECT token_hash,token_prefix FROM client_devices WHERE id=?',(created['id'],)).fetchone()
        self.assertNotEqual(row['token_hash'],created['token'])
        self.assertEqual(row['token_prefix'],created['token_prefix'])

    def test_workspace_manifest_changes(self):
        first=sync.workspace_manifest(self.wid)
        with db.connect() as con:
            con.execute('INSERT INTO notes(workspace_id,title,content,kind,created_at) VALUES(?,?,?,?,?)',(self.wid,'n','x','text','2026-01-01T00:00:00+00:00'))
        second=sync.workspace_manifest(self.wid)
        self.assertNotEqual(first['revision'],second['revision'])
        self.assertEqual(second['entities']['notes']['count'],1)

if __name__=='__main__': unittest.main()
