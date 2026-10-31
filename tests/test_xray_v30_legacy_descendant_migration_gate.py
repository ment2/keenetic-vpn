"""Synthetic legacy process ancestry gates. No live /proc, signals or router."""
from dataclasses import fields, replace
import unittest
from xray.lab import v30_legacy_descendant_migration_gate as gate

P = gate.Process


class V30MigrationGateTests(unittest.TestCase):
    def test_default_all_release_gates_no_go(self):
        result=gate.evaluate([], [])
        self.assertEqual(result["decision"],"NO_PRODUCTION_CUTOVER")
        self.assertIs(result["production_cutover_authorized"],False)
        self.assertEqual(result["router_commands"],[])
        self.assertIn("MISSING_PIDFD_KERNEL_SUPPORTED",result["reason_codes"])
        self.assertIn("INCOMPLETE_PROCESS_INVENTORY",result["reason_codes"])

    def test_every_missing_evidence_is_blocker(self):
        ready=gate.Evidence(**{f.name:True for f in fields(gate.Evidence)})
        for field in fields(gate.Evidence):
            with self.subTest(field=field.name):
                e=replace(ready,**{field.name:False})
                reasons=gate.evaluate([],[],evidence=e,inventory_complete=True)["reason_codes"]
                self.assertIn("MISSING_"+field.name.upper(),reasons)

    def test_stopped_watchdog_can_have_active_child_killall(self):
        procs=[
            P(32713,1,100,"T","/opt/bin/xray-watchdog.sh"),
            P(32714,32713,101,"S","/opt/etc/init.d/S97xray restart"),
            P(32715,32714,102,"R","killall xray"),
        ]
        reasons=gate.process_hazards(procs,[(32713,100)])
        self.assertIn("LIVE_LEGACY_DESCENDANTS",reasons)
        self.assertIn("UNFENCED_EXECUTOR_PRESENT",reasons)
        self.assertIn("LEGACY_ROOTS_STILL_RUNNING",reasons)

    def test_stopped_s98_leaves_rules_child(self):
        procs=[P(24097,1,200,"T","/opt/etc/init.d/S98xray-wifi"),
               P(24098,24097,201,"R","/opt/bin/xray-wifi-rules.sh"),
               P(24099,24098,202,"D","iptables -t mangle -F XRAY_WIFI")]
        reasons=gate.process_hazards(procs,[(24097,200)])
        self.assertIn("LIVE_LEGACY_DESCENDANTS",reasons)
        self.assertIn("UNFENCED_EXECUTOR_PRESENT",reasons)

    def test_orphaned_reparented_writer_cannot_be_ignored(self):
        procs=[P(24097,1,200,"Z","/opt/etc/init.d/S98xray-wifi"),
               P(25000,1,201,"R","/opt/bin/xray-wifi-rules.sh")]
        reasons=gate.process_hazards(procs,[(24097,200)])
        self.assertIn("ORPHANED_LEGACY_PROCESS",reasons)

    def test_cron_restart_bypasses_stopped_known_roots(self):
        procs=[P(32713,1,100,"Z","/opt/bin/xray-watchdog.sh"),
               P(33333,1,450,"R","/opt/etc/init.d/S97xray restart")]
        reasons=gate.process_hazards(procs,[(32713,100)])
        self.assertIn("LEGACY_ENTRYPOINT_PRESENT",reasons)

    def test_pid_reuse_rejected(self):
        with self.assertRaises(ValueError):
            gate.process_hazards([P(32713,1,333,"S","watchdog")],[(32713,100)])

    def test_duplicate_pid_and_invalid_start_ticks_rejected(self):
        for procs in ([P(55,1,1,"S","x"),P(55,1,2,"S","y")],
                      [P(55,1,0,"S","x")],
                      [P(1,0,1,"S","init")]):
            with self.subTest(procs=procs):
                with self.assertRaises(ValueError):
                    gate.process_hazards(procs,[])

    def test_incomplete_process_snapshot_never_authorizes(self):
        complete=gate.Evidence(**{f.name:True for f in fields(gate.Evidence)})
        result=gate.evaluate([],[],evidence=complete,inventory_complete=False)
        self.assertIn("INCOMPLETE_PROCESS_INVENTORY",result["reason_codes"])
        self.assertFalse(result["production_cutover_authorized"])

    def test_green_synthetic_snapshot_still_not_prod_approval(self):
        ready=gate.Evidence(**{f.name:True for f in fields(gate.Evidence)})
        result=gate.evaluate([],[],evidence=ready,inventory_complete=True)
        self.assertEqual(result["decision"],"OFFLINE_CONTRACT_ONLY")
        self.assertFalse(result["production_cutover_authorized"])
        self.assertEqual(result["router_commands"],[])

    def test_unknown_process_status_is_rejected(self):
        with self.assertRaises(ValueError):
            gate.process_hazards([P(55,1,99,"?","x")],[])

    def test_no_live_router_or_signals(self):
        import inspect
        s=inspect.getsource(gate)
        for bad in ("os.kill(", "subprocess.", "os.read(", "Path('/proc')",
                    "iptables -F XRAY_WIFI"):
            self.assertNotIn(bad,s)


if __name__=="__main__":
    unittest.main()
