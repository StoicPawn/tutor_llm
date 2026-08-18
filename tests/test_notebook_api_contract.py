import unittest
from studyforge.api import app


class NotebookApiContractTests(unittest.TestCase):
    def test_notebook_routes_exist(self):
        routes={(r.path,tuple(sorted(r.methods or []))) for r in app.routes}
        paths={p for p,_ in routes}
        expected={
            '/workspaces/{workspace_id}/notebooks',
            '/notebooks',
            '/workspaces/{workspace_id}/notebooks/{notebook_id}',
            '/notebooks/{notebook_id}/pages',
            '/notebooks/{notebook_id}/pages/{page_id}',
        }
        self.assertTrue(expected.issubset(paths), expected-paths)

if __name__=='__main__': unittest.main()
