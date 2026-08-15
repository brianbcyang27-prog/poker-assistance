import unittest
from pathlib import Path


class TestAnchorSummary(unittest.TestCase):
    def test_doc_exists(self):
        self.assertTrue(Path("docs/ANCHOR_SUMMARY.md").exists())

    def test_doc_content(self):
        text = Path("docs/ANCHOR_SUMMARY.md").read_text()
        self.assertIn("Anchored Conversation Summary", text)
        self.assertIn("Next steps", text)


if __name__ == "__main__":
    unittest.main()
