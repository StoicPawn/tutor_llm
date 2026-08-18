import unittest
from studyforge.api import app

class ApiContractTests(unittest.TestCase):
    def test_learning_routes_are_exposed(self):
        paths={r.path for r in app.routes}
        expected={
            '/documents/selection/map',
            '/documents/structure/rebuild',
            '/flashcards/generate',
            '/workspaces/{workspace_id}/review-queue',
            '/workspaces/{workspace_id}/next-activity',
            '/workspaces/{workspace_id}/documents/{document_id}/pages/{page}',
            '/exercises/sessions/{session_id}/answer',
            '/admin/devices',
            '/admin/devices/{device_id}',
            '/device/me',
            '/sync/workspaces/{workspace_id}/manifest',
            '/sync/workspaces/{workspace_id}/changes',
            '/sync/push',
            '/sync/resolve',
            '/notes/{note_id}',
            '/workspaces/{workspace_id}/notes/{note_id}',
        }
        self.assertTrue(expected.issubset(paths), expected-paths)

if __name__=='__main__': unittest.main()
