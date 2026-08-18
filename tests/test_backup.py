import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import studyforge.db as db
import studyforge.backup as backup
from studyforge.workspaces import ensure_default_workspace, create_workspace


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.db_path=root/'data'/'studyforge.db'
        self.uploads=root/'data'/'uploads'
        self.old_db_settings=db.settings
        self.old_backup_settings=backup.settings
        fake=SimpleNamespace(
            db_path=str(self.db_path), upload_dir=str(self.uploads), deploy_mode='local',
            chat_model='test-chat', embedding_model='test-embed'
        )
        db.settings=fake; backup.settings=fake
        ensure_default_workspace(); self.wid=create_workspace('Math')
        doc_dir=self.uploads/str(self.wid); doc_dir.mkdir(parents=True,exist_ok=True)
        doc_path=doc_dir/'book.txt'; doc_path.write_text('hello',encoding='utf-8')
        db.add_document(self.wid,'book.txt',str(doc_path))

    def tearDown(self):
        db.settings=self.old_db_settings; backup.settings=self.old_backup_settings
        self.tmp.cleanup()

    def _archive(self):
        archive=Path(self.tmp.name)/'backup.zip'
        backup.export_backup(str(archive))
        return archive

    def test_export_contains_database_and_uploads(self):
        archive=self._archive()
        manifest=backup.inspect_backup(str(archive))
        self.assertEqual(manifest['format'],'tutor-llm-backup')
        self.assertFalse(manifest['models_included'])
        import zipfile
        with zipfile.ZipFile(archive) as zf:
            names=set(zf.namelist())
        self.assertIn('studyforge.db',names)
        self.assertIn(f'uploads/{self.wid}/book.txt',names)

    def test_restore_relocates_document_paths(self):
        archive=self._archive()
        target=Path(self.tmp.name)/'server'
        fake=SimpleNamespace(
            db_path=str(target/'studyforge.db'), upload_dir=str(target/'uploads'), deploy_mode='server',
            chat_model='test-chat', embedding_model='test-embed'
        )
        backup.settings=fake
        backup.import_backup(str(archive), replace=True)
        con=sqlite3.connect(fake.db_path)
        try:
            path=con.execute("SELECT path FROM documents WHERE name='book.txt'").fetchone()[0]
        finally:
            con.close()
        expected=target/'uploads'/str(self.wid)/'book.txt'
        self.assertEqual(Path(path),expected)
        self.assertEqual(expected.read_text(encoding='utf-8'),'hello')

if __name__=='__main__': unittest.main()
