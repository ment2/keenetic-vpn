import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from monitoring import full_subscription_snapshot as s

def convert(line, n):
    return {"tag":"vpn%02d"%n, "protocol":"vless", "settings":{"vnext":[{"address":line+".invalid","port":443,"users":[{"id":"fixture"}]}]}, "streamSettings":{"network":"tcp"}}, "unused label"

class FullSubscriptionTests(unittest.TestCase):
    def test_ten_unfiltered(self):
        c=s.build_config(["example"+str(i) for i in range(10)],convert)
        self.assertEqual(len(c["outbounds"]),10)
        self.assertEqual(c["outbounds"][-1]["tag"],"vpn10")
    def test_parse_failure_not_partial(self):
        def bad(line,n):
            if n==2:
                raise RuntimeError("private parser exception")
            return convert(line,n)
        with self.assertRaises(RuntimeError):
            s.build_config(["a","b","c"],bad)
    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            s.build_config(["a","a"],convert)
    def test_empty_and_oversize(self):
        for lines in ([],["a"]*25):
            with self.assertRaises(ValueError):
                s.build_config(lines,convert)
    def test_bad_tag(self):
        def bad(line,n):
            ob,label=convert(line,n)
            ob["tag"]="other"
            return ob,label
        with self.assertRaises(ValueError):
            s.build_config(["a"],bad)
    def test_live_output_rejected_before_io(self):
        with self.assertRaises(ValueError):
            s.refresh(base="/nonexistent",expected={},output="/opt/etc/xray/config.json")
    def test_missing_digests(self):
        with self.assertRaises(ValueError):
            s.verify_sources("/nonexistent",{})
    def test_digest_and_mode_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            import os
            expected={}
            for name in s.SOURCE_NAMES:
                p=Path(tmp)/name
                p.write_bytes(b"fixture")
                p.chmod(0o600)
                expected[name]=hashlib.sha256(b"fixture").hexdigest()
            # CI is non-root; model the required owner without weakening the runtime check.
            original=Path.lstat
            from types import SimpleNamespace
            def owned(p):
                st=original(p)
                return SimpleNamespace(st_mode=st.st_mode,st_uid=0)
            with patch.object(Path,"lstat",owned):
                s.verify_sources(tmp,expected)
                (Path(tmp)/s.SOURCE_NAMES[0]).write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    s.verify_sources(tmp,expected)
