import fcntl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from monitoring import dynamic_monitor_cycle as c

class CycleTests(unittest.TestCase):
    def test_schedule(self):
        for minute in (0,15,30,45,59):
            runner=Mock()
            self.assertEqual(c.cycle("probe",minute=minute,runner=runner),2)
            runner.assert_not_called()
    def test_probe_order(self):
        runner=Mock(return_value=0)
        pins={n:"a"*64 for n in c.SOURCE_NAMES}
        self.assertEqual(c.cycle("probe",minute=3,pins_reader=lambda:pins,idle=lambda:True,runner=runner),0)
        self.assertEqual([x.args[0] for x in runner.call_args_list],["monitoring.full_subscription_snapshot","monitoring.dynamic_snapshot"])
        self.assertEqual(runner.call_args.args[1],["probe","--full",c.DEFAULT_OUTPUT,"--publish"])
    def test_busy_updater_skip(self):
        runner=Mock(return_value=0)
        self.assertEqual(c.cycle("probe",minute=3,idle=lambda:False,runner=runner),3)
        runner.assert_not_called()
    def test_refresh_error_prevents_probe(self):
        runner=Mock(return_value=1)
        self.assertEqual(c.cycle("probe",minute=18,pins_reader=lambda:{n:"a"*64 for n in c.SOURCE_NAMES},idle=lambda:True,runner=runner),1)
        self.assertEqual(runner.call_count,1)
    def test_publish_independent(self):
        runner=Mock(return_value=0)
        self.assertEqual(c.cycle("publish",runner=runner),0)
        runner.assert_called_once_with("monitoring.dynamic_snapshot",["publish","--full",c.DEFAULT_OUTPUT,"--publish"])
    def test_real_lock_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"updater.lock"
            self.assertFalse(c.updater_idle(p))
            self.assertFalse(p.exists())
            with p.open("w") as f:
                self.assertTrue(c.updater_idle(p))
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertFalse(c.updater_idle(p))
            self.assertTrue(c.updater_idle(p))
