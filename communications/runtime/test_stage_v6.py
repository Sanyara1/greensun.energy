import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import os
import ast
import base64
import zlib
from unittest.mock import patch
import factory as f
import stage_v6 as s

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'editorial/v6/source-export.json'
ASSETS=Path(os.environ.get('GSUN_TEST_ASSETS',str(ROOT.parents[2]/'deliverables/GSun-November-Cards/assets')))

@unittest.skipUnless(ASSETS.is_dir(),'Set GSUN_TEST_ASSETS to original 13-card asset directory')
class StageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/'live';self.home.mkdir()
        self.work=Path(self.tmp.name)/'staged'
        self.source=f.read(SOURCE)
        for name in ('facts','media'):f.write(self.home/(name+'.json'),self.source[name])
        f.write(self.home/'plans/2026-11.json',self.source['plan'])
        for x in self.source['media'].values():
            dest=self.home/'assets'/x['path'];dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((ASSETS/Path(x['path']).name).read_bytes())
        post=self.source['plan']['posts'][1]
        with sqlite3.connect(self.home/'deliveries.sqlite') as db:
            db.execute('create table deliveries(id text primary key,status text,result text)')
            db.execute('insert into deliveries values(?,?,?)',('post:2026-11-02:'+str(f.CHANNEL),'sent',json.dumps({'post_hash':f.digest(post),'channel_id':f.CHANNEL,'message_id':4})))
        tree=ast.parse((ROOT/'releases/v6/stage-v6-final.py').read_text())
        encoded=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PAYLOAD' for t in x.targets))
        self.payload=json.loads(json.loads(zlib.decompress(base64.b64decode(encoded)))['payload.json'])
        self.config={'LLM_MODEL':'test','LLM_URL':'https://example.invalid'}
        self.before={str(p.relative_to(self.home)):p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
    def unchanged(self):
        self.assertEqual(self.before,{str(p.relative_to(self.home)):p.read_bytes() for p in self.home.rglob('*') if p.is_file() and p.name!='.lock'})
    def run_stage(self,good=True):
        return s.stage(self.home,self.work,self.payload,self.config,
            lambda p,fs:{'pass':good,'issues':[] if good else [{'post_id':'2026-11-01','reason':'test failure'}]},
            lambda a,b:{'pass':True,'issues':[]})
    def test_success_is_staging_only(self):
        self.assertTrue(self.run_stage());self.unchanged()
        plan=f.read(self.work/'candidate.json')
        self.assertEqual(plan['posts'][1],self.source['plan']['posts'][1])
        self.assertIsNone(plan['approval'])
        self.assertEqual(plan['publication_holds'],{'2026-11-13':'RESERVE_NOT_AUTHORIZED'})
    def test_rejection_removes_stale_ready(self):
        self.work.mkdir();f.write(self.work/'READY.json',{'stale':True})
        self.assertFalse(self.run_stage(False));self.assertFalse((self.work/'READY.json').exists());self.unchanged()
    def test_changed_sent_post_rejected(self):
        self.payload['posts'][1]['text_ru']='changed'
        with self.assertRaisesRegex(f.Stop,'STOP_SENT_POST_CHANGED'):self.run_stage()
        self.unchanged()
    def test_asset_corruption_rejected(self):
        key=next(iter(self.payload['assets']));self.payload['assets'][key]='eA=='
        with self.assertRaisesRegex(f.Stop,'STOP_ASSET_HASH'):self.run_stage()
        self.unchanged()
    def test_unknown_delivery_rejected(self):
        with sqlite3.connect(self.home/'deliveries.sqlite') as db:db.execute("update deliveries set status='sending_or_unknown'")
        with self.assertRaisesRegex(f.Stop,'STOP_DELIVERY_RESULT_UNKNOWN'):self.run_stage()
    def test_changed_live_plan_during_review_rejected(self):
        def review(p,fs):
            f.write(self.home/'plans/2026-11.json',{'changed':True})
            return {'pass':True,'issues':[]}
        with self.assertRaisesRegex(f.Stop,'STOP_LIVE_STATE_CHANGED'):
            s.stage(self.home,self.work,self.payload,self.config,review,lambda a,b:{'pass':True,'issues':[]})
        self.assertFalse((self.work/'READY.json').exists())

if __name__=='__main__':unittest.main()
