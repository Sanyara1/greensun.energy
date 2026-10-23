import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import factory as f
import revise as r

class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.revision=json.loads((Path(__file__).parent.parent/'editorial/november-2026-v2.json').read_text())
        self.revision['month']='2099-11'
        for i,p in enumerate(self.revision['posts'],1): p['id']=f'2099-11-{i:02d}'
        ids=sorted({fid for p in self.revision['posts'] for fid in p['fact_ids']})
        facts=[{'id':fid,'public':True,'verified':True,'status':'service','text':'Fixture only',
                'source_url':'https://greensun.energy/','checked_at':'2026-10-24T00:00:00+03:00',
                'valid_until':'2100-01-01T00:00:00+03:00'} for fid in ids]
        f.write(self.home/'facts.json',facts);f.write(self.home/'media.json',{})
        posts=copy.deepcopy(self.revision['posts'])
        for p,t in zip(posts,f.slots('2099-11')):p['scheduled_at']=t;p['text_ru']='Original';p['text_en']='Original'
        self.path=self.home/'plans/2099-11.json'
        self.plan={'month':'2099-11','channel_id':f.CHANNEL,'timezone':'Europe/Moscow','posts':posts,
                   'fact_hashes':{x['id']:f.digest(x) for x in facts},'media_hashes':{},'approval':None,
                   'review':{'pass':True,'posts_hash':f.digest(posts)}}
        f.write(self.path,self.plan)
    def test_success_archives_and_requires_owner(self):
        reviewer=Mock(return_value={'pass':True,'issues':[]})
        r.revise(self.home,self.revision,reviewer)
        updated=f.read(self.path)
        self.assertIsNone(updated['approval']);self.assertEqual(updated['posts'][0]['text_ru'],self.revision['posts'][0]['text_ru'])
        archive=self.home/'revisions'/self.revision['revision_id']/('original-'+f.digest(self.plan)+'.json')
        self.assertEqual(f.read(archive),self.plan)
        r.revise(self.home,self.revision,reviewer);self.assertEqual(reviewer.call_count,1)
    def test_rejection_does_not_replace(self):
        with self.assertRaisesRegex(f.Stop,'EDITOR_REVIEW_REQUIRED'):
            r.revise(self.home,self.revision,lambda *a:{'pass':False,'issues':['unsupported claim']})
        self.assertEqual(f.read(self.path),self.plan)
    def test_timeout_preserves_original(self):
        with self.assertRaisesRegex(f.Stop,'REMOTE_TIMEOUT'):
            r.revise(self.home,self.revision,Mock(side_effect=f.Stop('REMOTE_TIMEOUT')))
        self.assertEqual(f.read(self.path),self.plan)
    def test_concurrent_approval_blocks_replacement(self):
        def review(*a):
            plan=f.read(self.path);plan['approval']={'hash':f.sealed_hash(plan)};f.write(self.path,plan)
            return {'pass':True,'issues':[]}
        with self.assertRaisesRegex(f.Stop,'STOP_PLAN_CHANGED'):
            r.revise(self.home,self.revision,review)
        self.assertIsNotNone(f.read(self.path)['approval'])
    def test_changed_sources_block(self):
        def review(*a):
            facts=f.read(self.home/'facts.json');facts[0]['text']='changed';f.write(self.home/'facts.json',facts)
            return {'pass':True,'issues':[]}
        with self.assertRaisesRegex(f.Stop,'STOP_SOURCES_CHANGED'):
            r.revise(self.home,self.revision,review)
        self.assertEqual(f.read(self.path),self.plan)
    def test_already_approved_not_reviewed(self):
        self.plan['approval']={'hash':f.sealed_hash(self.plan)};f.write(self.path,self.plan)
        reviewer=Mock()
        with self.assertRaisesRegex(f.Stop,'STOP_ALREADY_APPROVED'):
            r.revise(self.home,self.revision,reviewer)
        reviewer.assert_not_called()
    def test_inconsistent_positive_verdict_blocked(self):
        with self.assertRaisesRegex(f.Stop,'EDITOR_REVIEW_REQUIRED'):
            r.revise(self.home,self.revision,lambda *a:{'pass':True,'issues':['still unresolved']})
        self.assertEqual(f.read(self.path),self.plan)


class ChunkReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        self.plan={'posts':[{'id':str(i),'text_ru':'RU','text_en':'EN','fact_ids':['f'],'image_brief':'omit'} for i in range(13)]}
        self.facts=[{'id':'f','text':'Evidence'}]
        self.config={'LLM_MODEL':'model','LLM_URL':'endpoint'}
        self.ok={'pass':True,'issues':[]}
    def run_review(self):
        return r.review_with_cloudflare(self.plan,self.facts,self.config,self.path)
    def test_resume_and_compact_payload(self):
        from unittest.mock import patch
        with patch.object(r,'review_call',side_effect=[self.ok,f.Stop('REVIEW_OUTPUT_TRUNCATED')]) as call:
            with self.assertRaisesRegex(f.Stop,'TRUNCATED'): self.run_review()
            self.assertNotIn('image_brief',call.call_args_list[0].args[1]['posts'][0])
        with patch.object(r,'review_call',return_value=self.ok) as call:
            self.assertTrue(self.run_review()['pass']); self.assertEqual(call.call_count,7)
            self.assertEqual(len(call.call_args.args[1]['posts']),13)
        with patch.object(r,'review_call') as call:
            self.assertTrue(self.run_review()['pass']);call.assert_not_called()
    def test_changed_evidence_invalidates_cache(self):
        from unittest.mock import patch
        with patch.object(r,'review_call',return_value=self.ok):self.run_review()
        self.facts[0]['text']='Changed'
        with patch.object(r,'review_call',return_value=self.ok) as call:
            self.run_review();self.assertEqual(call.call_count,8)
    def test_failed_stage_retained(self):
        from unittest.mock import patch
        failed={'pass':False,'issues':[{'post_id':'0','reason':'unsupported'}]}
        with patch.object(r,'review_call',side_effect=[failed]+[self.ok]*7):
            self.assertFalse(self.run_review()['pass'])
        with patch.object(r,'review_call') as call:
            self.assertFalse(self.run_review()['pass']);call.assert_not_called()
    def test_invalid_issue_not_cached(self):
        from unittest.mock import patch
        with patch.object(r,'review_call',return_value={'pass':False,'issues':['bad']}):
            with self.assertRaisesRegex(f.Stop,'ISSUE_INVALID'):self.run_review()
        self.assertEqual(list(self.path.iterdir()),[])

if __name__=='__main__': unittest.main()
