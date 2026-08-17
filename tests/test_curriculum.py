import unittest
from studyforge.curriculum import _json_object
class CurriculumTests(unittest.TestCase):
 def test_json_fence(self):
  self.assertEqual(_json_object('```json\n{"nodes": []}\n```')['nodes'],[])
 def test_json_surrounded(self):
  self.assertEqual(_json_object('output: {"nodes":[{"title":"A"}]} end')['nodes'][0]['title'],'A')
if __name__=='__main__': unittest.main()
