"""Synthetic tests for non-disclosing snapshot credential detection."""
import unittest
from tools.check_snapshot_secrets import inspect_text


class SnapshotSecretsTests(unittest.TestCase):
    def test_no_false_positive_for_environment_variable(self):
        self.assertEqual(inspect_text('token = os.environ["MEMORY_WRITE_TOKEN"]'), [])

    def test_no_false_positive_for_url_without_secret(self):
        self.assertEqual(inspect_text("https://cloudflare.example/workers"), [])

    def test_block_private_key_header(self):
        self.assertIn("private_key_block", inspect_text("-----BEGIN PRIVATE KEY-----"))

    def test_block_embedded_vless_uuid(self):
        sample = "vless://" + "01234567-89ab-cdef-0123-456789abcdef" + "@example.invalid:443"
        self.assertIn("vless_with_uuid", inspect_text(sample))

    def test_block_high_confidence_api_token(self):
        sample = "sk-" + "a" * 35
        self.assertIn("openai_token", inspect_text(sample))

    def test_masking_is_responsibility_of_caller(self):
        self.assertEqual(inspect_text("normal shell script without credentials"), [])


if __name__ == "__main__":
    unittest.main()
