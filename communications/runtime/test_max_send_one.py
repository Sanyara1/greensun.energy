import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sqlite3
import max_send_one as m

class Fake:
    def __init__(self, failure=False, rights=True):
        self.sent = 0
        self.failure = failure
        self.rights = rights
    def upload(self, content):
        return 'test-token'
    def api(self, route, method='GET', body=None):
        if route == '/me': return {'user_id': m.BOT, 'is_bot': True}
        if route.endswith('/members/me'): return {'is_admin': True, 'permissions': ['write'] if self.rights else []}
        if route.startswith('/chats/'): return {'chat_id': m.CHANNEL, 'type': 'channel'}
        self.sent += 1
        assert body['notify'] is True
        if self.failure: raise TimeoutError()
        return {'message': {'body': {'mid': 'test-id'}, 'recipient': {'chat_id': m.CHANNEL}}}

class Tests(unittest.TestCase):
    def test_sent_blocks_duplicate(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.time, 'sleep'):
            c = Fake()
            m.deliver(Path(d), {}, {'text_ru': 'test'}, b'image', c)
            with self.assertRaises(m.Stop): m.deliver(Path(d), {}, {'text_ru': 'test'}, b'image', c)
            self.assertEqual(c.sent, 1)
    def test_timeout_blocks_retry(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.time, 'sleep'):
            c = Fake(failure=True)
            with self.assertRaises(TimeoutError): m.deliver(Path(d), {}, {'text_ru': 'test'}, b'image', c)
            with self.assertRaises(m.Stop): m.deliver(Path(d), {}, {'text_ru': 'test'}, b'image', c)
            self.assertEqual(c.sent, 1)
            with sqlite3.connect(Path(d)/'max-deliveries.sqlite') as db:
                self.assertEqual(db.execute('SELECT status FROM deliveries').fetchone()[0], 'unknown')
    def test_no_permission_no_send(self):
        with tempfile.TemporaryDirectory() as d:
            c = Fake(rights=False)
            with self.assertRaises(m.Stop): m.deliver(Path(d), {}, {'text_ru': 'test'}, b'image', c)
            self.assertEqual(c.sent, 0)

if __name__ == '__main__': unittest.main()
