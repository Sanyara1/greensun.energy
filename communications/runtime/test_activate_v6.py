from unittest.mock import patch
from test_stage_v6 import StageTests
import activate_v6 as a
import factory as f
class ActivationTests(StageTests):
 def setup_install(self):
  self.run_stage();self.code=self.home.parent/'code';self.code.mkdir();(self.code/'factory.py').write_text('old-runtime')
  self.cp=self.home.parent/'runtime.env';self.raw=b'GSUN_PUBLISH_ENABLED=no\nGSUN_GENERATE_ENABLED=no\n';self.cp.write_bytes(self.raw)
  return f.sealed_hash(f.read(self.work/'candidate.json'))
 def test_installs_exact_candidate_preserves_ledger(self):
  expected=self.setup_install();ledger=(self.home/'deliveries.sqlite').read_bytes()
  with patch.object(a,'EXPECTED',expected):backup=a.install(self.home,self.work,self.code,self.cp,self.raw)
  self.assertTrue(backup.exists());self.assertEqual((backup/'factory.py').read_text(),'old-runtime')
  self.assertEqual((self.home/'deliveries.sqlite').read_bytes(),ledger)
  self.assertEqual(f.read(self.home/'plans/2026-11.json')['approval']['hash'],expected)
  self.assertIn(b'GSUN_PUBLISH_ENABLED=yes',self.cp.read_bytes())
  self.assertFalse((self.home/'PAUSE').exists())
 def test_hash_mismatch_leaves_live_unchanged(self):
  self.setup_install()
  with self.assertRaisesRegex(f.Stop,'STOP_REVIEWED_HASH_CHANGED'):a.install(self.home,self.work,self.code,self.cp,self.raw)
  self.unchanged();self.assertEqual(self.cp.read_bytes(),self.raw)
 def test_failure_after_pause_does_not_enable(self):
  expected=self.setup_install()
  original=a.atomic
  def fail(path,raw):
   if path==self.code/'factory.py':raise OSError('disk test')
   return original(path,raw)
  with patch.object(a,'EXPECTED',expected),patch.object(a,'atomic',fail):
   with self.assertRaises(OSError):a.install(self.home,self.work,self.code,self.cp,self.raw)
  self.assertTrue((self.home/'PAUSE').exists());self.assertEqual(self.cp.read_bytes(),self.raw)
  self.assertIsNone(f.read(self.home/'plans/2026-11.json')['approval'])
