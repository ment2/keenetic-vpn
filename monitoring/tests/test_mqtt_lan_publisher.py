import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from monitoring.mqtt_lan_publisher import _field, _remaining, publish_once, load_password

class FakeSocket:
    def __init__(self): self.messages=[]; self.parts=[b"\x20\x02\x00\x00", b"\x40\x02\x00\x01"]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def settimeout(self,x): pass
    def sendall(self,data):self.messages.append(data)
    def recv(self,n):
        if not self.parts:return b""
        part=self.parts[0][:n];self.parts[0]=self.parts[0][n:]
        if not self.parts[0]:self.parts.pop(0)
        return part

class TestPublish(unittest.TestCase):
    def test_field(self):self.assertEqual(_field("a"),b"\x00\x01a")
    def test_remaining(self):self.assertEqual(_remaining(128),b"\x80\x01")
    def test_publish_qos1_and_no_retained(self):
        sock=FakeSocket()
        with patch("monitoring.mqtt_lan_publisher.socket.create_connection",return_value=sock):
            publish_once(host="192.168.0.169",port=1883,username="x",password="y",topic="keenetic/vpn-monitor/v1/traffic/apclii0",payload={"rx":30})
        self.assertEqual(sock.messages[1][0],0x32)
        self.assertEqual(sock.messages[-1],b"\xe0\x00")
    def test_bad_topic(self):
        with self.assertRaises(ValueError): publish_once(host="x",port=1883,username="x",password="y",topic="homeassistant/#",payload={})
    def test_credentials_permissions(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"password";p.write_text("password\n");os.chmod(p,0o600)
            self.assertEqual(load_password(p),"password")
            os.chmod(p,0o644)
            with self.assertRaises(PermissionError):load_password(p)
    def test_max_payload(self):
        with self.assertRaises(ValueError):
            publish_once(host="x",port=1883,username="x",password="y",topic="keenetic/vpn-monitor/v1/x",payload={"x":"z"*5000})
if __name__=="__main__":unittest.main()
