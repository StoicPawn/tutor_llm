import os
import tempfile
import unittest
from types import SimpleNamespace

import studyforge.db as db
from studyforge.workspaces import create_workspace, ensure_default_workspace
from studyforge.student import record_result, mastery_for


class WorkspaceIsolationTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.unlink(self.path)
        self.old_settings = db.settings
        db.settings = SimpleNamespace(db_path=self.path)
        self.general = ensure_default_workspace()
        self.math = create_workspace('Matematica')
        self.os = create_workspace('Sistemi Operativi')

    def tearDown(self):
        db.settings = self.old_settings
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_documents_and_chunks_are_isolated(self):
        d1 = db.add_document(self.math, 'analisi.pdf', '/tmp/analisi.pdf')
        d2 = db.add_document(self.os, 'os.pdf', '/tmp/os.pdf')
        db.add_chunks(d1, [{'page': 1, 'chunk_index': 0, 'text': 'limiti'}], [[1.0, 0.0]])
        db.add_chunks(d2, [{'page': 1, 'chunk_index': 0, 'text': 'processi'}], [[0.0, 1.0]])
        self.assertEqual([r['document_name'] for r in db.iter_chunks(self.math)], ['analisi.pdf'])
        self.assertEqual([r['document_name'] for r in db.iter_chunks(self.os)], ['os.pdf'])

    def test_mastery_is_isolated(self):
        record_result(self.math, 'memoria', 1.0, 'test')
        self.assertGreater(mastery_for(self.math, 'memoria'), mastery_for(self.os, 'memoria'))


if __name__ == '__main__':
    unittest.main()
