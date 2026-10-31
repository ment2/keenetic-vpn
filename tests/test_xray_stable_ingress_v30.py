"""CI-only stable loopback TCP ingress contracts (no Xray or router)."""
import os
import socket
import threading
import unittest
from unittest.mock import patch

from xray.lab.stable_socks_ingress_v30 import (
    Backend, HandoffRejected, StableSocksTcpIngress, proc_start_ticks,
)


class Echo:
    def __init__(self, prefix):
        self.prefix = prefix
        self.stop = threading.Event()
        self.s = socket.socket()
        self.s.bind(("127.0.0.1", 0))
        self.s.listen(10)
        self.s.settimeout(.1)
        self.port = self.s.getsockname()[1]
        self.thread = threading.Thread(target=self.accept, daemon=True)
        self.thread.start()

    def accept(self):
        while not self.stop.is_set():
            try:
                client, _ = self.s.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self.handle, args=(client,), daemon=True).start()

    def handle(self, c):
        with c:
            c.settimeout(.5)
            while not self.stop.is_set():
                try:
                    data = c.recv(4096)
                    if not data:
                        return
                    c.sendall(self.prefix + data)
                except socket.timeout:
                    continue
                except OSError:
                    return

    def close(self):
        self.stop.set()
        self.s.close()
        self.thread.join(timeout=2)


def talk(c, b):
    c.sendall(b)
    return c.recv(4096)


class StableIngressContracts(unittest.TestCase):
    def setUp(self):
        self.a, self.b = Echo(b"A:"), Echo(b"B:")
        pid, ticks = os.getpid(), proc_start_ticks(os.getpid())
        self.old, self.new = Backend(self.a.port, pid, ticks), Backend(self.b.port, pid, ticks)
        self.ingress = StableSocksTcpIngress(self.old, self.new).start()
        self.addCleanup(self.ingress.close)
        self.addCleanup(self.b.close)
        self.addCleanup(self.a.close)

    def activate(self):
        return self.ingress.activate(1, self.old, self.new, candidate_ready=True)

    def test_pid_start_ticks(self):
        self.assertTrue(self.old.live())
        self.assertFalse(Backend(self.old.port, self.old.pid, self.old.start_ticks + 1).live())

    def test_stable_port_existing_flow_and_rollback(self):
        port = self.ingress.port
        with socket.create_connection(("127.0.0.1", port), timeout=3) as old:
            self.assertEqual(talk(old, b"one"), b"A:one")
            self.assertEqual(self.activate(), 2)
            with socket.create_connection(("127.0.0.1", port), timeout=3) as new:
                self.assertEqual(talk(new, b"two"), b"B:two")
            self.assertEqual(talk(old, b"three"), b"A:three")
            self.assertEqual(self.ingress.rollback(2, self.old, self.new), "old")
            with socket.create_connection(("127.0.0.1", port), timeout=3) as again:
                self.assertEqual(talk(again, b"four"), b"A:four")
            self.assertEqual(self.ingress.port, port)

    def test_reject_not_ready(self):
        with self.assertRaises(HandoffRejected):
            self.ingress.activate(1, self.old, self.new, candidate_ready=False)
        self.assertEqual(self.ingress.selector, "old")

    def test_reject_stale_generation(self):
        with self.assertRaises(HandoffRejected):
            self.ingress.activate(0, self.old, self.new, candidate_ready=True)

    def test_reject_changed_candidate_identity(self):
        wrong = Backend(self.new.port, self.new.pid, self.new.start_ticks + 1)
        with self.assertRaises(HandoffRejected):
            self.ingress.activate(1, self.old, wrong, candidate_ready=True)

    def test_double_activate_rejected(self):
        self.activate()
        with self.assertRaises(HandoffRejected):
            self.activate()

    def test_stale_rollback_rejected(self):
        self.activate()
        with self.assertRaises(HandoffRejected):
            self.ingress.rollback(1, self.old, self.new)
        self.assertEqual(self.ingress.selector, "candidate")

    def test_rollback_to_dead_old_blocks(self):
        self.activate()
        live = Backend.live
        with patch.object(Backend, "live", lambda b: False if b.port == self.old.port else live(b)):
            self.assertEqual(self.ingress.rollback(2, self.old, self.new), "blocked")
        with socket.create_connection(("127.0.0.1", self.ingress.port), timeout=2) as s:
            s.settimeout(2)
            self.assertEqual(s.recv(10), b"")

    def test_dead_candidate_never_routes_direct_or_implicitly_old(self):
        self.activate()
        live = Backend.live
        with patch.object(Backend, "live", lambda b: False if b.port == self.new.port else live(b)):
            with socket.create_connection(("127.0.0.1", self.ingress.port), timeout=2) as s:
                s.settimeout(2)
                self.assertEqual(s.recv(10), b"")
        self.assertEqual(self.ingress.selector, "candidate")

    def test_loopback_binding(self):
        self.assertEqual(self.ingress.server.getsockname()[0], "127.0.0.1")

    def test_identical_backends_forbidden(self):
        with self.assertRaises(HandoffRejected):
            StableSocksTcpIngress(self.old, self.old)


if __name__ == "__main__":
    unittest.main()
