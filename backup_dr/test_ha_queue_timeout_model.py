"""SQLite model of the observed Worker claim/expiry predicates, not live DO tests."""
import sqlite3
import unittest

CLAIM = "SELECT id,exec_timeout FROM jobs WHERE state='queued' AND revision=? ORDER BY created,id LIMIT 1"
EXPIRY = "UPDATE jobs SET state='failed' WHERE state='queued' AND created<=?"

def claim(db, now, cap=45):
    db.execute(EXPIRY, (now-3600000,))
    row = db.execute(CLAIM, (3,)).fetchone()
    return row[0] if row and row[1]<=cap else None

class QueueTimeoutModel(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE jobs(id TEXT, state TEXT, revision INTEGER, created INTEGER, exec_timeout INTEGER)')
        self.db.executemany('INSERT INTO jobs VALUES(?,?,?,?,?)', [('listener','queued',3,1000,145),('diagnostic','queued',3,331000,20)])
    def tearDown(self): self.db.close()
    def test_head_blocks_short_job(self): self.assertIsNone(claim(self.db,400000))
    def test_expiry_releases_next(self):
        self.assertEqual(claim(self.db,3601000),'diagnostic')
        self.assertEqual(self.db.execute("SELECT state FROM jobs WHERE id='listener'").fetchone()[0],'failed')
    def test_ha_ingress_guard(self):
        def accepted(timeout): return isinstance(timeout,int) and not isinstance(timeout,bool) and 1<=timeout<=45
        self.assertTrue(accepted(45)); self.assertFalse(accepted(145)); self.assertFalse(accepted(0))

if __name__=='__main__': unittest.main()