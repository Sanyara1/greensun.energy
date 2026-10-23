import unittest
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer
from unittest.mock import patch
import factory as f
import bridge
from test_factory import FactoryTests

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=FactoryTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home=self.fixture.home
    def test_snapshot_no_secret_and_no_publish(self):
        with patch.object(f.Telegram,'send',side_effect=AssertionError('no send')):
            s=bridge.snapshot(self.home,'2099-11')
        self.assertTrue(s['approved']);self.assertEqual(len(s['posts']),len(self.fixture.plan['posts']))
        self.assertEqual(len(s['posts'][0]['reminders']),2)
        self.assertNotIn('OWNER_CHAT_ID',str(s))
    def test_changed_plan_cannot_approve(self):
        with self.assertRaises(f.Stop):bridge.action(self.home,'2099-11',{'action':'approve','hash':'0'*64})
    def test_pause_resume(self):
        bridge.action(self.home,'2099-11',{'action':'pause'});self.assertTrue((self.home/'PAUSE').exists())
        bridge.action(self.home,'2099-11',{'action':'resume'});self.assertFalse((self.home/'PAUSE').exists())
    def test_no_paths_or_arbitrary_actions(self):
        with self.assertRaises(f.Stop):bridge.snapshot(self.home,'../../secret')
        with self.assertRaises(f.Stop):bridge.action(self.home,'2099-11',{'action':'send'})
    def test_http_auth(self):
        server=HTTPServer(('127.0.0.1',0),bridge.handler(self.home,'x'*32))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url='http://127.0.0.1:'+str(server.server_port)+'/plan?month=2099-11'
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(url)
            self.assertEqual(e.exception.code,401)
            req=urllib.request.Request(url,headers={'Authorization':'Bearer '+'x'*32})
            with urllib.request.urlopen(req) as r:self.assertEqual(r.status,200)
        finally:server.shutdown();server.server_close();thread.join()
