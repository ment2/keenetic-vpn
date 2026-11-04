import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from monitoring.traffic_counters import Sample
from monitoring.traffic_one_shot import event_from_sample, save_snapshot_atomic, previous_sample, collect_once

class TrafficOneShotTests(unittest.TestCase):
    def sample(self, rx=100, tx=200, clock=1000000000, boot='boot'):
        return Sample('apclii0', boot, clock, rx, tx)
    def test_first_sample_baseline(self):
        e=event_from_sample(self.sample(),None,'2026-11-04T09:00:00Z')
        self.assertEqual(e['interval']['status'],'baseline')
        self.assertFalse(e['vpn_specific'])
    def test_subsequent_delta(self):
        e=event_from_sample(self.sample(500,400,2000000000),self.sample(),'2026-11-04T09:00:00Z')
        self.assertEqual(e['interval']['rx_delta_bytes'],400)
        self.assertEqual(e['interval']['tx_delta_bytes'],200)
    def test_state_save_load_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'state'/'apclii0.json'
            save_snapshot_atomic(p,self.sample())
            self.assertEqual(previous_sample(p,'apclii0'),self.sample())
            self.assertEqual(p.stat().st_mode & 0o077, 0)
    def test_no_publish_without_optin(self):
        with tempfile.TemporaryDirectory() as temp, patch('monitoring.traffic_one_shot.read_snapshot',return_value=self.sample()), patch('monitoring.traffic_one_shot.load_password') as cred:
            results=collect_once(['apclii0'],temp,publish=False)
            self.assertEqual(results,[('apclii0','baseline')])
            cred.assert_not_called()
    def test_publish_pins_topic_and_payload(self):
        with tempfile.TemporaryDirectory() as temp, patch('monitoring.traffic_one_shot.read_snapshot',return_value=self.sample()), patch('monitoring.traffic_one_shot.load_password',return_value='test-secret'), patch('monitoring.traffic_one_shot.publish_once') as mqtt:
            result=collect_once(['apclii0'],temp,publish=True)
            self.assertEqual(result,[('apclii0','baseline')])
            self.assertEqual(mqtt.call_args.kwargs['topic'],'keenetic/vpn-monitor/v1/traffic/apclii0')
            self.assertEqual(mqtt.call_args.kwargs['payload']['interval']['status'],'baseline')
if __name__=='__main__':unittest.main()
