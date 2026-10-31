"""RC14 dual-provenance: immutable RC10 bytes vs separately attested PIDFD descendant."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"xray/staging/v30-rc14-pidfd-source-provenance.json"
def git_blob(path):
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
class RC14Provenance(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(P.read_text())
    def test_immutable_old_manifest_and_historical_archive(self):
        h=self.p["original_rc10"]
        self.assertEqual(git_blob(h["manifest_path"]),h["manifest_git_blob_sha"])
        m=json.loads((ROOT/h["manifest_path"]).read_text())
        self.assertEqual(m["source_blobs"][h["old_file_path"]],h["original_git_blob_sha"])
        self.assertEqual(git_blob(h["archive_copy_path"]),h["original_git_blob_sha"])
        self.assertEqual(
            json.loads((ROOT/h["manifest_path"]).read_text())["source_blobs"][h["original_workflow_path"]],
            h["original_workflow_blob_sha"])
        self.assertEqual(git_blob(h["archive_workflow_path"]),h["original_workflow_blob_sha"])
        self.assertFalse(h["manifest_edited"])
    def test_new_pidfd_revision_pinned_without_relabeling_old_evidence(self):
        c=self.p["current_pidfd_revision"]
        self.assertNotEqual(c["script_git_blob_sha"],self.p["original_rc10"]["original_git_blob_sha"])
        for p,k in (("script_path","script_git_blob_sha"),("pidfd_guard_path","pidfd_guard_git_blob_sha"),("native_workflow_path","native_workflow_git_blob_sha")):
            self.assertEqual(git_blob(c[p]),c[k],p)
        self.assertEqual(c["proven_successful_native_ci_id"],41229534586)
    def test_release_is_unconditionally_hard_no_go(self):
        self.assertEqual(self.p["decision"],"HARD_NO_GO_PRODUCTION")
        self.assertFalse(any(self.p["certification"][k] for k in (
            "production_authorized","kernel49_native_mips_packet_path_proven",
            "physical_legacy_root_cgroup_fencing_proven",
            "physical_non_usb_boot_rescue_proven","physical_vendor_ndm5_no_leak_proven")))
        self.assertEqual(self.p["router_jobs"],0)
        self.assertEqual(self.p["production_commands"],[])
if __name__=="__main__":
    unittest.main()
