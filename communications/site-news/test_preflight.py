"""Read-only audit boundary tests; no live VPS calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import preflight_site as audit


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base/'site'
        self.root.mkdir()
        (self.root/'index.html').write_bytes(b'live-home')

    def tearDown(self):
        self.temp.cleanup()

    def test_audit_does_not_change_site(self):
        before = audit.tree(self.root)
        with patch.object(audit.subprocess,'check_output',return_value=b'nginx snapshot'), patch.object(audit,'fetch',return_value=b'live-home'):
            audit.inspect(self.root,self.base/'private')
        self.assertEqual(before,audit.tree(self.root))
        state=json.loads((self.base/'private/preflight.json').read_text())
        self.assertFalse(state['publication_authorized'])
        self.assertFalse(state['backup_created'])
        self.assertEqual((self.base/'private').stat().st_mode & 0o777,0o700)
        self.assertEqual((self.base/'private/nginx-T.txt').stat().st_mode & 0o777,0o600)

    def test_no_output_inside_web_root(self):
        with self.assertRaises(ValueError):
            audit.inspect(self.root,self.root/'audit')
        self.assertFalse((self.root/'audit').exists())

    def test_reject_wrong_origin_or_symlink(self):
        with patch.object(audit.subprocess,'check_output',return_value=b'nginx snapshot'), patch.object(audit,'fetch',return_value=b'other-vhost'):
            with self.assertRaises(ValueError):
                audit.inspect(self.root,self.base/'private')
        self.assertFalse((self.base/'private').exists())
        (self.root/'unexpected').symlink_to(self.root/'index.html')
        with self.assertRaises(ValueError):
            audit.tree(self.root)


if __name__=='__main__':
    unittest.main()
