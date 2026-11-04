import tempfile
import unittest
from pathlib import Path
from monitoring.traffic_counters import Sample, interval, read_snapshot

class TrafficTests(unittest.TestCase):
    def s(self,rx,tx,t=10_000_000_000,boot="a",iface="apclii0"):
        return Sample(iface,boot,t,rx,tx)
    def test_deltas_and_rates(self):
        r=interval(self.s(100,200),self.s(1300,700,15_000_000_000))
        self.assertEqual((r["rx_delta_bytes"],r["tx_delta_bytes"]),(1200,500))
        self.assertEqual(r["rx_bits_per_sec"],1920)
        self.assertFalse(r["vpn_specific"])
    def test_zero_traffic(self):
        self.assertEqual(interval(self.s(100,100),self.s(100,100,11_000_000_000))["tx_delta_bytes"],0)
    def test_boot_change(self):
        self.assertEqual(interval(self.s(10,10),self.s(20,20,20_000_000_000,boot="new"))["status"],"reset")
    def test_counter_reset(self):
        self.assertEqual(interval(self.s(100,100),self.s(1,300,20_000_000_000))["status"],"reset")
    def test_gap(self):
        self.assertEqual(interval(self.s(100,100),self.s(300,300,611_000_000_000))["status"],"gap")
    def test_nonpositive_elapsed(self):
        self.assertEqual(interval(self.s(100,100),self.s(300,300))["status"],"reset")
    def test_mismatch(self):
        with self.assertRaises(ValueError): interval(self.s(1,2),self.s(2,3,20_000_000_000,iface="br0"))
    def test_read_sysfs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); stats=p/"apclii0"/"statistics"; stats.mkdir(parents=True)
            (stats/"rx_bytes").write_text("123");(stats/"tx_bytes").write_text("321")
            (p/"boot_id").write_text("boot-test")
            x=read_snapshot("apclii0",p,p/"boot_id")
            self.assertEqual((x.rx_bytes,x.tx_bytes,x.boot_id),(123,321,"boot-test"))
    def test_path_traversal(self):
        with self.assertRaises(ValueError): read_snapshot("../proc")
    def test_negative_counter(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); stats=p/"apclii0"/"statistics";stats.mkdir(parents=True)
            (stats/"rx_bytes").write_text("-1");(stats/"tx_bytes").write_text("7")
            (p/"boot_id").write_text("boot")
            with self.assertRaises(ValueError):read_snapshot("apclii0",p,p/"boot_id")
if __name__=="__main__":unittest.main()
