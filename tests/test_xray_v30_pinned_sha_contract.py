"""Immutable source/backup SHA256 regression contract for Xray v30 canary.

Runs only on GitHub runner with frozen, non-sensitive production snapshot.
Never reads a live router and never attempts --plan, --trial or --rollback.
"""
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from xray.staging import v30_first_cutover_canary as canary


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "xray" / "production" / "MANIFEST.sha256"
HEX = re.compile(r"^[0-9a-f]{64}$")
SOURCE_PINS = {
    "S97_SHA": "opt/etc/init.d/S97xray",
    "WIFI_SHA": "opt/etc/init.d/S98xray-wifi",
    "S99_SHA": "opt/etc/init.d/S99xray-watchdog",
    "WD_SHA": "opt/bin/xray-watchdog.sh",
    "WIFI_RULES_SHA": "opt/bin/xray-wifi-rules.sh",
}
ALL_PINS = (
    "BACKUP_MANIFEST_SHA", "BIN_SHA", "BASE_SHA", "S97_SHA", "S98_SHA",
    "S99_SHA", "WD_SHA", "WIFI_RULES_SHA",
)
LIVE_WD_BACKUP_SHA_20261031 = (
    "dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08"
)


def attr_for_pin(label):
    # The runtime diagnostic calls the S98 source pin "S98_SHA" even though
    # the existing module-level variable is named WIFI_SHA.
    return "WIFI_SHA" if label == "S98_SHA" else label


def parse_frozen_manifest():
    entries = {}
    for row in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        if not row or row.startswith("#"):
            continue
        values = row.split()
        if len(values) != 3 or not HEX.fullmatch(values[0]):
            raise ValueError("invalid frozen manifest row")
        if values[1] in entries:
            raise ValueError("duplicate snapshot entry")
        entries[values[1]] = values[0]
    return entries


class XrayV30PinnedHashSafetyTests(unittest.TestCase):
    def test_all_embedded_sha256_values_have_64_lowercase_hex(self):
        found = canary.validate_pinned_hashes()
        self.assertEqual(set(found), set(ALL_PINS))
        for name, value in found.items():
            with self.subTest(name=name):
                self.assertRegex(value, HEX)

    def test_every_live_source_pin_matches_frozen_snapshot(self):
        entries = parse_frozen_manifest()
        for name, file_path in SOURCE_PINS.items():
            with self.subTest(name=name, path=file_path):
                self.assertIn(file_path, entries)
                self.assertEqual(getattr(canary, name), entries[file_path])

    def test_watchdog_hash_matches_actual_readonly_router_and_backup(self):
        self.assertEqual(canary.WD_SHA, LIVE_WD_BACKUP_SHA_20261031)
        self.assertEqual(len(canary.WD_SHA), 64)

    def test_frozen_manifest_watchdog_bytes_match_its_sha(self):
        from hashlib import sha256
        p = ROOT / "xray" / "production" / "opt" / "bin" / "xray-watchdog.sh"
        self.assertEqual(sha256(p.read_bytes()).hexdigest(),
                         LIVE_WD_BACKUP_SHA_20261031)

    def test_reject_missing_character_for_all_pins(self):
        for name in ALL_PINS:
            with self.subTest(name=name):
                value = getattr(canary, attr_for_pin(name))
                with patch.object(canary, attr_for_pin(name), value[1:]):
                    with self.assertRaisesRegex(canary.GateError, name):
                        canary.validate_pinned_hashes()

    def test_reject_extra_character_for_all_pins(self):
        for name in ALL_PINS:
            with self.subTest(name=name):
                with patch.object(canary, attr_for_pin(name), getattr(canary, attr_for_pin(name)) + "f"):
                    with self.assertRaisesRegex(canary.GateError, name):
                        canary.validate_pinned_hashes()

    def test_reject_uppercase_for_all_pins(self):
        for name in ALL_PINS:
            with self.subTest(name=name):
                with patch.object(canary, attr_for_pin(name), "A" * 64):
                    with self.assertRaisesRegex(canary.GateError, name):
                        canary.validate_pinned_hashes()

    def test_reject_nonhex_for_all_pins(self):
        for name in ALL_PINS:
            with self.subTest(name=name):
                with patch.object(canary, attr_for_pin(name), "g" * 64):
                    with self.assertRaisesRegex(canary.GateError, name):
                        canary.validate_pinned_hashes()

    def test_reject_nonstring_for_all_pins(self):
        for name in ALL_PINS:
            with self.subTest(name=name):
                with patch.object(canary, attr_for_pin(name), None):
                    with self.assertRaisesRegex(canary.GateError, name):
                        canary.validate_pinned_hashes()

    def test_manifest_missing_pin_is_not_silently_ignored(self):
        entries = parse_frozen_manifest()
        for k in SOURCE_PINS.values():
            self.assertIn(k, entries)
        self.assertGreaterEqual(len(entries), 60)

    def test_root_only_backup_pin_matches_verified_router_measurement(self):
        self.assertEqual(canary.BACKUP_MANIFEST_SHA,
                         "f27c336f66f1bbb9ef22a82f7e8aa84f80f9bee808b3a87abf6a5372e79d5c62")

    def test_static_failure_refuses_to_read_router_backup(self):
        # A corrupt hash pin must be rejected even if a backup is otherwise
        # correctly signed. This unit test does not connect to the router.
        with patch.object(canary, "WD_SHA", "dddcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08"):
            with patch.object(canary, "checksum", side_effect=AssertionError("router read not allowed")):
                with self.assertRaisesRegex(canary.GateError, "WD_SHA"):
                    canary.verify_backup()

    def test_correct_pin_never_alters_running_router(self):
        from inspect import getsource
        validate = getsource(canary.validate_pinned_hashes)
        self.assertNotIn("os.kill(", validate)
        self.assertNotIn("subprocess.", validate)
        self.assertNotIn("STATE_DIR.mkdir", validate)
        self.assertNotIn("ACTIVE.write", validate)


if __name__ == "__main__":
    unittest.main()
