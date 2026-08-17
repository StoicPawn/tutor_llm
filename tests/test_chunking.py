import unittest
from studyforge.ingest import chunk_pages

class ChunkingTest(unittest.TestCase):
    def test_chunks_keep_page(self):
        text = ("Concetto importante. " * 250).strip()
        chunks = chunk_pages([{"page": 7, "text": text}])
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c["page"] == 7 for c in chunks))
        self.assertEqual([c["chunk_index"] for c in chunks], list(range(len(chunks))))

if __name__ == "__main__":
    unittest.main()
