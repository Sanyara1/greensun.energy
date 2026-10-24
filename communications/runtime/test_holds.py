from datetime import timedelta
from test_factory import FactoryTests,FakeTelegram
import factory as f
class HoldsTests(FactoryTests):
 def held(self):
  self.plan['publication_holds']={self.plan['posts'][0]['id']:'reserve'}
  self.plan['minimum_publisher_features']=['publication_holds','sent_before_reminders']
  self.plan['approval']={'hash':f.sealed_hash(self.plan)};self.save()
 def test_held_never_sent_or_reminded(self):
  self.held();c=FakeTelegram()
  for delta in [-24,-1,0,1]:
   events=f.tick(self.home,True,c,self.now+timedelta(hours=delta))
   self.assertFalse(any(self.plan['posts'][0]['id'] in e['id'] for e in events))
  self.assertEqual(c.sent,[])
 def test_hold_change_breaks_approval(self):
  self.held();self.plan['publication_holds']={};self.save()
  with self.assertRaisesRegex(f.Stop,'APPROVED_PLAN_CHANGED'):f.tick(self.home,True,FakeTelegram(),self.now)
 def test_unknown_feature(self):
  self.plan['minimum_publisher_features']=['unknown'];self.save()
  with self.assertRaisesRegex(f.Stop,'PUBLISHER_FEATURE_UNSUPPORTED'):f.validate(self.plan,self.home,self.facts,{})
