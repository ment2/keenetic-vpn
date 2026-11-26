import unittest
from scheduler import observe, acknowledge
class TestScheduler(unittest.TestCase):
    def test_delay(self):
        s, due = observe({}, 'a', 100); self.assertFalse(due)
        self.assertFalse(observe(s,'b',3699)[1]); self.assertTrue(observe(s,'b',3700)[1])
    def test_retry(self):
        s,_=observe({},'a',0); self.assertTrue(observe(s,'a',3600)[1]); self.assertTrue(observe(s,'a',3660)[1])
    def test_ack(self):
        self.assertFalse(observe(acknowledge({},'a'),'a',9000)[1])
    def test_revert(self):
        s,_=observe({'committed':'a'},'b',0); s,due=observe(s,'a',5000); self.assertFalse(due); self.assertNotIn('since',s)
if __name__=='__main__': unittest.main()
