import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import studyforge.db as db
from studyforge.workspaces import ensure_default_workspace, create_workspace
from studyforge.notebooks import create_notebook, get_notebook, add_page, update_page


class NotebookApiCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.old = db.settings
        db.settings = SimpleNamespace(db_path=str(root / 'studyforge.db'), upload_dir=str(root / 'uploads'))
        ensure_default_workspace()
        self.workspace_id = create_workspace('Notebook API')
        self.document_id = db.add_document(self.workspace_id, 'book.pdf', str(root / 'book.pdf'))

    def tearDown(self):
        db.settings = self.old
        self.tmp.cleanup()

    def test_legacy_rest_positional_notebook_create_is_supported(self):
        notebook_id = create_notebook(self.workspace_id, 'Appunti', self.document_id, 7, 'Limiti')
        notebook = get_notebook(self.workspace_id, notebook_id)
        self.assertEqual(notebook['linked_document_id'], self.document_id)
        self.assertEqual(notebook['linked_page'], 7)
        self.assertEqual(notebook['linked_concept'], 'Limiti')

    def test_rest_page_add_and_partial_update_shapes_are_supported(self):
        notebook_id = create_notebook(self.workspace_id, 'Q', document_id=self.document_id)
        page = add_page(self.workspace_id, notebook_id, 'grid', 'Pagina iPad', [{'kind': 'text', 'text': 'x'}])
        self.assertEqual(page['background'], 'grid')
        self.assertEqual(page['layers'][0]['text'], 'x')

        updated = update_page(self.workspace_id, notebook_id, page['id'], title='Nuovo titolo')
        self.assertEqual(updated['title'], 'Nuovo titolo')
        self.assertEqual(updated['layers'][0]['text'], 'x')


if __name__ == '__main__':
    unittest.main()
