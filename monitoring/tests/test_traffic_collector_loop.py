import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from monitoring.traffic_collector_loop import run_loop

class TestLoop(unittest.TestCase):
    def test_reject_too_short_interval(self):
        with self.assertRaises(ValueError):run_loop(interval_seconds=1,max_cycles=1)
    def test_reject_negative_cycles(self):
        with self.assertRaises(ValueError):run_loop(max_cycles=-1)
    def test_two_cycles_no_mqtt(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("monitoring.traffic_collector_loop.collect_once",return_value=[("apclii0","ok")]) as collector, patch("monitoring.traffic_collector_loop.time.sleep",return_value=None), patch("monitoring.traffic_collector_loop.time.monotonic",side_effect=[0,60,60,120,120]) as clock:
                run_loop(interval_seconds=60,lock_file=str(Path(d)/'lock'),state_dir=d,max_cycles=2,publish=False)
            self.assertEqual(collector.call_count,2)
            self.assertFalse(collector.call_args.kwargs['publish'])
    def test_failed_cycle_continues(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("monitoring.traffic_collector_loop.collect_once",side_effect=[ConnectionError("private data"),[("br0","ok")]]) as collector, patch("monitoring.traffic_collector_loop.time.sleep",return_value=None), patch("monitoring.traffic_collector_loop.time.monotonic",side_effect=[0,60,60,120,120]):
                run_loop(interval_seconds=60,lock_file=str(Path(d)/'lock'),state_dir=d,max_cycles=2)
            self.assertEqual(collector.call_count,2)
    def test_no_implicit_publish(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("monitoring.traffic_collector_loop.collect_once",return_value=[]) as collector:
                run_loop(max_cycles=1,lock_file=str(Path(d)/'lock'),state_dir=d)
            self.assertFalse(collector.call_args.kwargs['publish'])
if __name__=="__main__": unittest.main()
