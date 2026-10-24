import copy
import json
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
import factory as f


class FakeTelegram:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail
    def verify(self):
        pass
    def send(self, chat, text, photo=None):
        self.sent.append((chat, text, photo))
        if self.fail:
            raise TimeoutError()
        return {'message_id': len(self.sent)}


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.facts = [{'id': 'a', 'public': True, 'verified': True,
                       'status': 'service', 'source_url': 'https://gsun.ai/',
                       'text': 'Солнечные станции', 'checked_at': '2026-10-23T12:00:00+03:00',
                       'valid_until': '2100-01-01T00:00:00+03:00'}]
        self.plan = {'month': '2099-11', 'channel_id': f.CHANNEL, 'timezone': 'Europe/Moscow',
                     'fact_hashes': {'a': f.digest(self.facts[0])}, 'media_hashes': {},
                     'posts': [{'id': f'2099-11-{i+1:02d}', 'scheduled_at': t,
                                'text_ru': 'Солнечные станции', 'text_en': 'Solar stations',
                                'fact_ids': ['a'], 'media_id': None}
                               for i, t in enumerate(f.slots('2099-11'))]}
        self.plan['review'] = {'pass': True, 'posts_hash': f.digest(self.plan['posts'])}
        self.plan['approval'] = {'hash': f.sealed_hash(self.plan)}
        self.save()
        self.now = f.instant(self.plan['posts'][0]['scheduled_at'])
        self.env = patch.dict(os.environ, {'GSUN_PUBLISH_ENABLED': 'yes', 'OWNER_CHAT_ID': '1234'})
        self.env.start()
        self.addCleanup(self.env.stop)
    def save(self):
        f.write(self.home / 'facts.json', self.facts)
        f.write(self.home / 'media.json', {})
        f.write(self.home / 'plans/2099-11.json', self.plan)
    def test_calendar(self):
        for s in f.slots('2026-11'):
            d = f.instant(s)
            self.assertIn(d.weekday(), (0, 2, 4))
            self.assertEqual(d.hour, 11)
            self.assertEqual(d.utcoffset().total_seconds(), 10800)
    def test_unapproved_never_sent(self):
        self.plan['approval'] = None; self.save()
        c = FakeTelegram()
        self.assertEqual(f.tick(self.home, True, c, self.now), [])
        self.assertEqual(c.sent, [])
    def test_post_only_once(self):
        c = FakeTelegram()
        f.tick(self.home, True, c, self.now)
        f.tick(self.home, True, c, self.now)
        self.assertEqual(len(c.sent), 1)
    def test_unknown_no_retry(self):
        c = FakeTelegram(fail=True)
        result = f.tick(self.home, True, c, self.now)
        self.assertEqual(result[0]['status'], 'sending_or_unknown')
        f.tick(self.home, True, c, self.now)
        self.assertEqual(len(c.sent), 1)
    def test_modified_approval_blocks(self):
        self.plan['posts'][0]['text_ru'] = 'Different'
        self.save()
        with self.assertRaisesRegex(f.Stop, 'APPROVED_PLAN_CHANGED'):
            f.tick(self.home, True, FakeTelegram(), self.now)
    def test_source_change_blocks(self):
        self.facts[0]['text'] = 'Different'
        self.save()
        with self.assertRaisesRegex(f.Stop, 'FACT_CHANGED'):
            f.tick(self.home, True, FakeTelegram(), self.now)
    def test_expired_source_blocks(self):
        self.facts[0]['valid_until'] = '2099-01-01T00:00:00+03:00'; self.save()
        with self.assertRaisesRegex(f.Stop, 'FACT_EXPIRED'):
            f.tick(self.home, True, FakeTelegram(), self.now)
    def test_reminders_deduplicated(self):
        c = FakeTelegram()
        for hours in (24, 1):
            f.tick(self.home, True, c, self.now - timedelta(hours=hours))
            f.tick(self.home, True, c, self.now - timedelta(hours=hours))
        self.assertEqual(len(c.sent), 2)
        self.assertTrue(all(x[0] == '1234' for x in c.sent))
    def test_no_false_missed_after_sent(self):
        c = FakeTelegram()
        f.tick(self.home, True, c, self.now)
        f.tick(self.home, True, c, self.now + timedelta(hours=2))
        self.assertEqual(len(c.sent), 1)
    def test_late_post_not_published(self):
        c = FakeTelegram()
        f.tick(self.home, True, c, self.now + timedelta(hours=2))
        self.assertEqual(c.sent[0][0], '1234')
    def test_dry_run_does_not_consume_delivery(self):
        f.tick(self.home, False, now=self.now)
        self.assertFalse((self.home / 'deliveries.sqlite').exists())
        c = FakeTelegram(); f.tick(self.home, True, c, self.now)
        self.assertEqual(len(c.sent), 1)
    def test_pause(self):
        (self.home / 'PAUSE').touch()
        with self.assertRaisesRegex(f.Stop, 'PAUSED'):
            f.tick(self.home, True, FakeTelegram(), self.now)
    def test_media_escape(self):
        with self.assertRaisesRegex(f.Stop, 'MEDIA_PATH_INVALID'):
            f.media_path(self.home, {'path': '../facts.json'})
    def test_review_stale(self):
        self.plan['posts'][0]['text_ru'] = 'Changed'
        with self.assertRaisesRegex(f.Stop, 'REVIEW_STALE'):
            f.validate(self.plan, self.home, self.facts, {})
    def test_model_pipeline_and_no_overwrite(self):
        facts = [dict(self.facts[0], id=x) for x in ('a', 'b', 'c')]
        f.write(self.home / 'facts.json', facts)
        raw = {'posts': [{k: v for k, v in p.items() if k not in ('id', 'scheduled_at')}
                         for p in self.plan['posts']]}
        (self.home / 'plans/2099-11.json').unlink()
        with patch.object(f, 'llm', side_effect=[{'posts': [post]} for post in raw['posts']] + [{'pass': True, 'issues': []}]) as model:
            path = f.generate('2099-11', self.home)
            self.assertEqual(model.call_count, len(raw['posts']) + 1)
        self.assertIsNone(f.read(path)['approval'])
        with self.assertRaisesRegex(f.Stop, 'PLAN_EXISTS'):
            f.generate('2099-11', self.home)
    def test_resume_after_failure_and_input_change_guard(self):
        facts = [dict(self.facts[0], id=x) for x in ('a', 'b', 'c')]
        f.write(self.home / 'facts.json', facts)
        (self.home / 'plans/2099-11.json').unlink()
        raw = {k: v for k, v in self.plan['posts'][0].items() if k not in ('id', 'scheduled_at')}
        with patch.object(f, 'llm', side_effect=[{'posts': [raw]}, f.Stop('REMOTE_TIMEOUT')]):
            with self.assertRaisesRegex(f.Stop, 'REMOTE_TIMEOUT'):
                f.generate('2099-11', self.home)
        self.assertFalse((self.home / 'plans/2099-11.json').exists())
        self.assertEqual(len(f.read(self.home / 'generation/2099-11.json')['posts']), 1)
        facts[0]['text'] = 'changed'
        f.write(self.home / 'facts.json', facts)
        with patch.object(f, 'llm') as model:
            with self.assertRaisesRegex(f.Stop, 'CHECKPOINT_INPUT_CHANGED'):
                f.generate('2099-11', self.home)
            model.assert_not_called()
        facts[0]['text'] = self.facts[0]['text']
        f.write(self.home / 'facts.json', facts)
        count = len(self.plan['posts'])
        with patch.object(f, 'llm', side_effect=[{'posts': [raw]}] * (count-1) + [{'pass': True}] ) as model:
            result = f.generate('2099-11', self.home)
            self.assertEqual(model.call_count, count)
        self.assertEqual(len(f.read(result)['posts']), count)
        self.assertIsNone(f.read(result)['approval'])

    def test_cloudflare_low_reasoning_and_truncation(self):
        with patch.dict(os.environ, {'LLM_URL': 'https://api.cloudflare.com/client/v4/accounts/test/ai/v1/chat/completions', 'LLM_MODEL': 'test'}):
            with patch.object(f, 'request_json', return_value={'choices': [{'finish_reason':'stop','message': {'content':'{"posts":[]}'}}]}) as call:
                self.assertEqual(f.llm([]), {'posts':[]})
                payload = call.call_args.args[1]
                self.assertEqual(payload['reasoning_effort'], 'low')
                self.assertEqual(payload['max_completion_tokens'], 4800)
                self.assertEqual(call.call_args.kwargs['timeout'], 120)
                f.llm([], reviewer=True)
                self.assertEqual(call.call_args.kwargs['timeout'], 240)
            with patch.object(f, 'request_json', return_value={'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}):
                with self.assertRaisesRegex(f.Stop, 'MODEL_OUTPUT_TRUNCATED'):
                    f.llm([])

    def test_early_sent_and_unknown_suppress_reminders_and_dry_run(self):
        import sqlite3
        for status in ('sent', 'sending_or_unknown'):
            with self.subTest(status=status):
                with sqlite3.connect(self.home/'deliveries.sqlite') as db:
                    db.execute('CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY,status TEXT,result TEXT)')
                    db.execute('DELETE FROM deliveries')
                    db.execute('INSERT INTO deliveries VALUES (?,?,?)',
                               ('post:'+self.plan['posts'][0]['id']+':'+str(f.CHANNEL),status,'{}'))
                before=(self.home/'deliveries.sqlite').read_bytes()
                c=FakeTelegram()
                for hours in (24,1,0,-2):
                    at=self.now-timedelta(hours=hours)
                    f.tick(self.home,False,now=at)
                    f.tick(self.home,True,c,at)
                self.assertEqual(c.sent,[])
                with sqlite3.connect(self.home/'deliveries.sqlite') as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM deliveries').fetchone()[0],1)
                self.assertEqual((self.home/'deliveries.sqlite').read_bytes(),before)

    def test_live_requires_enable(self):
        with patch.dict(os.environ, {'GSUN_PUBLISH_ENABLED': 'no'}):
            with self.assertRaisesRegex(f.Stop, 'LIVE_DISABLED'):
                f.tick(self.home, True, FakeTelegram(), self.now)


if __name__ == '__main__':
    unittest.main()
