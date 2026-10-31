"""RC36 upstream source blob-hash and private UDP-worker inventory gates.

No invocation of root commands, production, router, or network.
"""
import hashlib
import tempfile
from pathlib import Path
import unittest
from xray.lab.rc36_pinned_xray_udp_source_audit import (
 BLOBS,SourceDrift,PINNED_COMMIT,read_verified_sources,
)
def blob(raw):
 return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\\0"+raw).hexdigest()

class SourcePin(unittest.TestCase):
 def test_commit_and_git_blob_format(self):
  self.assertEqual(PINNED_COMMIT,"12ee51e4bb1d02ece4ef4b7114efa2bcdc130995")
  self.assertEqual(len(BLOBS),5)
  self.assertTrue(all(len(v)==40 and int(v,16)>=0 for v in BLOBS.values()))
 def test_valid_five_temp_sources_with_exact_expected_blob(self):
  with tempfile.TemporaryDirectory() as tmp:
   expected={}
   for rel in BLOBS:
    raw=("source/"+rel+"\\n").encode()
    p=Path(tmp)/rel;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(raw);expected[rel]=blob(raw)
   data=read_verified_sources(Path(tmp),expected)
   self.assertEqual(set(data),set(BLOBS))
 def test_single_byte_drift_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   expected={}
   for rel in BLOBS:
    raw=("source/"+rel+"\\n").encode()
    p=Path(tmp)/rel;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(raw);expected[rel]=blob(raw)
   first=next(iter(BLOBS))
   with (Path(tmp)/first).open("ab") as f:f.write(b"# drift")
   with self.assertRaisesRegex(SourceDrift,"GIT_BLOB_SHA_MISMATCH"):
    read_verified_sources(Path(tmp),expected)
 def test_missing_fifth_blob_and_extra_manifest_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(SourceDrift,"PINNED_SOURCE_ABSENT"):
    read_verified_sources(Path(tmp))
   with self.assertRaisesRegex(SourceDrift,"PINNED_SOURCE_FILE_SET_DRIFT"):
    read_verified_sources(Path(tmp),dict(list(BLOBS.items())[:4]))
 def test_raw_sha1_cannot_impersonate_git_blob(self):
  raw=b"abc";self.assertNotEqual(hashlib.sha1(raw).hexdigest(),blob(raw))

if __name__=="__main__":unittest.main()
