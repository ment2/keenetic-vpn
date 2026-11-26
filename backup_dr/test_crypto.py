import unittest
from crypto import seal,open_sealed,transform
class CryptoTests(unittest.TestCase):
    def test_roundtrip(self):
        self.assertEqual(open_sealed(bytes(32),seal(bytes(32),b'backup')),b'backup')
    def test_tamper(self):
        b=seal(bytes(32),b'backup'); self.assertRaises(ValueError,open_sealed,bytes(32),b[:-1]+bytes([b[-1]^1]))
    def test_wrong_key(self):
        self.assertRaises(ValueError,open_sealed,bytes([1])*32,seal(bytes(32),b'backup'))
    def test_nist(self):
        self.assertEqual(transform(bytes(32),bytes(12),b'').hex(),'530f8afbc74536b9a963b4f1c4cb738b')
