from pathlib import Path
from unittest.mock import Mock
import unittest
import factory as f
import private_preview as p
from test_attach_cards import CardsTests

class PrivatePreviewTests(unittest.TestCase):
    def setUp(self):
        fixture=CardsTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.home=fixture.home
        fixture.attach()
        self.config=self.home/'runtime.env'
        self.config.write_text('GSUN_PUBLISH_ENABLED=no\nTELEGRAM_BOT_TOKEN=fixture\nOWNER_CHAT_ID=\n')
        self.before=f.read(self.home/'plans/2026-11.json')
        self.bot=Mock()
        def call(method,params):
            if method=='getMe':return {'username':f.BOT}
            if method=='getChatAdministrators':return [{'status':'creator','user':{'id':123,'is_bot':False}}]
            if method=='getChat':return {'id':123,'type':'private','username':'owner_test'}
            raise AssertionError('Unexpected method: '+method)
        self.bot.call.side_effect=call
        self.bot.send.return_value={'message_id':42,'chat':{'id':123}}
    def run_preview(self):
        return p.send_preview(self.home,self.config,123,'owner_test',self.bot,post_id='2099-11-02')
    def test_private_delivery_is_once_and_channel_unchanged(self):
        self.run_preview();self.run_preview()
        self.assertEqual(self.bot.send.call_count,1)
        self.assertEqual(self.bot.send.call_args.args[0],123)
        self.assertEqual(f.read(self.home/'plans/2026-11.json'),self.before)
        self.assertFalse((self.home/'deliveries.sqlite').exists())
        self.assertIn('OWNER_CHAT_ID=123',self.config.read_text())
        self.assertIn('GSUN_PUBLISH_ENABLED=no',self.config.read_text())
    def test_unknown_does_not_retry(self):
        self.bot.send.side_effect=TimeoutError()
        for _ in range(2):
            with self.assertRaisesRegex(f.Stop,'PREVIEW_RESULT_UNKNOWN'):self.run_preview()
        self.assertEqual(self.bot.send.call_count,1)
    def test_wrong_recipient_not_saved_or_sent(self):
        self.bot.call.side_effect=lambda method,params: {'username':f.BOT} if method=='getMe' else ([{'status':'creator','user':{'id':123}}] if method=='getChatAdministrators' else {'id':123,'type':'private','username':'someone_else'})
        with self.assertRaisesRegex(f.Stop,'RECIPIENT_MISMATCH'):self.run_preview()
        self.bot.send.assert_not_called();self.assertNotIn('OWNER_CHAT_ID=123',self.config.read_text())
    def test_changed_owner_is_blocked(self):
        self.config.write_text(self.config.read_text().replace('OWNER_CHAT_ID=','OWNER_CHAT_ID=456'))
        with self.assertRaisesRegex(f.Stop,'EXISTING_OWNER_DIFFERS'):self.run_preview()
        self.bot.send.assert_not_called()
    def test_enabled_publication_is_blocked(self):
        self.config.write_text(self.config.read_text().replace('ENABLED=no','ENABLED=yes'))
        with self.assertRaisesRegex(f.Stop,'STOP_PUBLISH_ENABLED'):self.run_preview()
        self.bot.send.assert_not_called()

if __name__=='__main__':unittest.main()
