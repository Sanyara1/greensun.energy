import sqlite3
import unittest
import crosspost_factory_test as m

class Fake:
    def __init__(self, fail=None): self.fail, self.calls = fail, []
    def send(self, platform):
        self.calls.append(platform)
        if platform == self.fail: raise TimeoutError()
        return '123'

class Tests(unittest.TestCase):
    def test_success_no_duplicates(self):
        with sqlite3.connect(':memory:') as db:
            api = Fake()
            self.assertTrue(m.deliver(db, api))
            self.assertTrue(m.deliver(db, api))
            self.assertEqual(api.calls, ['telegram', 'max'])
    def test_partial_failure_does_not_resend(self):
        with sqlite3.connect(':memory:') as db:
            api = Fake('telegram')
            self.assertFalse(m.deliver(db, api))
            self.assertFalse(m.deliver(db, api))
            self.assertEqual(api.calls, ['telegram', 'max'])
            self.assertEqual(db.execute("SELECT status FROM sends WHERE platform='telegram'").fetchone()[0], 'unknown')
    def test_reservation_visible_before_send(self):
        with sqlite3.connect(':memory:') as db:
            class Check:
                def send(self, platform):
                    assert db.execute('SELECT status FROM sends WHERE platform=?', (platform,)).fetchone()[0] == 'unknown'
                    assert not db.in_transaction
                    return '123'
            self.assertTrue(m.deliver(db, Check()))

if __name__ == '__main__': unittest.main()
