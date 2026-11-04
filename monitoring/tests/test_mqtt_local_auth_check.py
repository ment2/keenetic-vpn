import unittest
from monitoring.mqtt_local_auth_check import connect_packet, mqtt_string, remaining_length

class TestMQTTLocalAuth(unittest.TestCase):
    def test_string_encoding(self):
        self.assertEqual(mqtt_string("MQTT"),b"\x00\x04MQTT")
    def test_remaining_length(self):
        self.assertEqual(remaining_length(127),b"\x7f")
        self.assertEqual(remaining_length(128),b"\x80\x01")
        self.assertEqual(remaining_length(16384),b"\x80\x80\x01")
    def test_connect_packet(self):
        packet=connect_packet("keenetic_monitor","private")
        self.assertEqual(packet[0],0x10)
        self.assertIn(b"\x00\x04MQTT\x04\xc2",packet)
        self.assertIn(mqtt_string("keenetic_monitor"),packet)
        self.assertIn(mqtt_string("private"),packet)
    def test_long_field_rejected(self):
        with self.assertRaises(ValueError):mqtt_string("x"*65536)
if __name__=="__main__":unittest.main()
