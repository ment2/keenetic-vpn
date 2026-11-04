import unittest
from dataclasses import fields
from xray.lab.rc39_ha_backup_receipt_gate import OffsiteReceipt, review


class HomeAssistantReceiptTests(unittest.TestCase):
    def test_no_backup_receipt_does_not_authorize(self):
        r=review()
        self.assertEqual(r["decision"],"OFFSITE_RECEIPT_INCOMPLETE")
        self.assertFalse(r["production_cutover_authorized"])
        self.assertFalse(r["physical_recovery_proven_by_gate"])
    def test_network_connectivity_alone_is_insufficient(self):
        r=review(OffsiteReceipt(ssh_authenticated=True))
        self.assertIn("MISSING_ENCRYPTION_AT_REST_VERIFIED",r["missing"])
        self.assertIn("MISSING_PHYSICAL_RESTORE_TEST_COMPLETED",r["missing"])
    def test_wrong_remote_digest_denied(self):
        evidence={f.name:True for f in fields(OffsiteReceipt) if f.type is bool}
        evidence.update(source_archive_sha256="a"*64, remote_archive_sha256="b"*64)
        r=review(OffsiteReceipt(**evidence))
        self.assertIn("ARCHIVE_SHA256_NOT_END_TO_END_VERIFIED",r["missing"])
    def test_same_hash_does_not_claim_physical_proof(self):
        r=review(OffsiteReceipt(
            source_archive_sha256="a"*64,remote_archive_sha256="a"*64,
            host_key_verified_out_of_band=True,ssh_authenticated=True,
            isolated_storage_from_router_usb=True,remote_file_owner_only=True,
            encryption_at_rest_verified=True,backup_contents_manifest_verified=True,
            physical_restore_test_completed=True,local_operator_recovery_available=True))
        self.assertEqual(r["decision"],"CLAIMED_RECEIPT_REQUIRES_INDEPENDENT_AUDIT")
        self.assertFalse(r["physical_recovery_proven_by_gate"])
        self.assertFalse(r["production_cutover_authorized"])
    def test_not_an_authority_to_issue_commands(self):
        self.assertEqual(review()["router_commands"],[])
        self.assertEqual(review()["bytes_transferred_by_gate"],0)
    def test_reject_untyped(self):
        with self.assertRaises(TypeError):review({"ssh_authenticated":True})


if __name__=="__main__":unittest.main()
