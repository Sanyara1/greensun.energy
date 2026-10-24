import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import factory as f
import attach_cards as a
from test_revise import RevisionTests

class CardsTests(unittest.TestCase):
    def setUp(self):
        fixture=RevisionTests();fixture.setUp();self.addCleanup(fixture.tmp.cleanup)
        self.home=fixture.home;self.plan=fixture.plan
        self.plan['editorial_revision']=a.SOURCE
        self.path=self.home/'plans/2026-11.json';f.write(self.path,self.plan)
        self.data=b'fixed-image-test-fixture'
        self.manifest=[{'post_id':p['id'],'file':f"card-{i}.png",'sha256':hashlib.sha256(self.data).hexdigest(),'card_copy':'test'} for i,p in enumerate(self.plan['posts'])]
        self.ok=Mock(return_value={'pass':True,'issues':[]})
    def attach(self, reviewer=None):
        return a.attach(self.home,self.manifest,lambda x:self.data,reviewer or self.ok)
    def test_success_and_idempotence(self):
        result=self.attach()
        self.assertIsNone(result['approval']);self.assertEqual(len(f.read(self.home/'media.json')),13)
        self.assertTrue(all(p['media_id'] and 'Иллюстрация' in p['text_ru'] for p in result['posts']))
        self.assertEqual(f.read(self.home/'revisions'/a.REVISION/'original-plan.json'),self.plan)
        self.assertEqual(result['review']['posts_hash'],f.digest(result['posts']))
        self.attach();self.assertEqual(self.ok.call_count,1)
        preview=(self.home/'revisions'/a.REVISION/'preview.html').read_text()
        self.assertEqual(preview.count('<article>'),13);self.assertEqual(preview.count('data:image/png;base64,'),13)
    def test_rejection_keeps_plan_and_catalog(self):
        with self.assertRaisesRegex(f.Stop,'CARDS_REVIEW_REQUIRED'):
            self.attach(Mock(return_value={'pass':False,'issues':['bad']}))
        self.assertEqual(f.read(self.path),self.plan);self.assertEqual(f.read(self.home/'media.json'),{})
    def test_bad_hash_keeps_plan(self):
        self.manifest[0]['sha256']='0'*64
        with self.assertRaisesRegex(f.Stop,'HASH_MISMATCH'):self.attach()
        self.assertEqual(f.read(self.path),self.plan);self.ok.assert_not_called()
    def test_concurrent_approval_blocks_commit(self):
        def reviewer(*args):
            p=f.read(self.path);p['approval']={'owner':True};f.write(self.path,p)
            return {'pass':True,'issues':[]}
        with self.assertRaisesRegex(f.Stop,'STOP_PLAN_CHANGED'):self.attach(reviewer)
        self.assertEqual(f.read(self.home/'media.json'),{})
    def test_overlong_caption_stops_before_review(self):
        self.plan['posts'][0]['text_ru']='a'*1010
        self.plan['review']['posts_hash']=f.digest(self.plan['posts']);f.write(self.path,self.plan)
        with self.assertRaisesRegex(f.Stop,'CAPTION_TOO_LONG'):self.attach()
        self.ok.assert_not_called()
    def test_unapproved_source_review_stops(self):
        self.plan['review']['pass']=False;f.write(self.path,self.plan)
        with self.assertRaisesRegex(f.Stop,'EDITOR_REVIEW_REQUIRED'):self.attach()
        self.ok.assert_not_called()
    def test_catalog_addition_interruption_keeps_original_valid(self):
        write=f.write
        def interrupted(path,value):
            if Path(path)==self.path:raise OSError('simulated interruption')
            write(path,value)
        with patch.object(f,'write',side_effect=interrupted):
            with self.assertRaises(OSError):self.attach()
        f.validate(f.read(self.path),self.home,f.read(self.home/'facts.json'),f.read(self.home/'media.json'))
        self.attach()

if __name__=='__main__':unittest.main()
