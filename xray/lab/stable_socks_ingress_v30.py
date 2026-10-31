#!/usr/bin/env python3
"""Disposable CI-only stable TCP SOCKS ingress lab, never deploy to router.

Only new TCP connections switch backend. Active TCP tunnels drain on the old
process. UDP, TPROXY, kernel fail-closed, DNS and watchdog are NOT tested.
"""
from dataclasses import dataclass
import contextlib
from pathlib import Path
import socket
import threading


class HandoffRejected(RuntimeError):
    pass


def proc_start_ticks(pid):
    """Linux /proc/<pid>/stat field 22, resilient to spaces in comm."""
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


@dataclass(frozen=True)
class Backend:
    port: int
    pid: int
    start_ticks: int

    def __post_init__(self):
        if not 1 <= self.port <= 65535 or self.pid <= 0 or self.start_ticks <= 0:
            raise ValueError("invalid backend identity")

    def live(self):
        try:
            return proc_start_ticks(self.pid) == self.start_ticks
        except (OSError, ValueError, IndexError):
            return False


class StableSocksTcpIngress:
    """Test-only loopback TCP relay with generation and PID/start-ticks CAS.

    A dead candidate fails closed for new connections; it never falls back to
    provider/direct. Explicit rollback to old is required.
    """

    def __init__(self, old: Backend, candidate: Backend):
        if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
            raise HandoffRejected("router/Entware detected: CI lab only")
        if old == candidate or old.port == candidate.port or not old.live():
            raise HandoffRejected("invalid distinct backends or old process is dead")
        self.backends = {"old": old, "candidate": candidate}
        self.selector = "old"
        self.generation = 1
        self.mutex = threading.RLock()
        self.stop_flag = threading.Event()
        self.sockets = set()
        self.handlers = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(16)
        self.server.settimeout(0.2)
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def activate(self, expected_generation, old, candidate, *, candidate_ready):
        with self.mutex:
            if self.generation != expected_generation:
                raise HandoffRejected("stale generation")
            if self.selector != "old" or self.backends != {"old": old, "candidate": candidate}:
                raise HandoffRejected("identity or state changed")
            if not old.live() or not candidate.live() or not candidate_ready:
                raise HandoffRejected("candidate readiness/identity failed")
            self.selector = "candidate"
            self.generation += 1
            return self.generation

    def rollback(self, expected_generation, old, candidate):
        with self.mutex:
            if self.generation != expected_generation:
                raise HandoffRejected("stale rollback generation")
            if self.selector != "candidate" or self.backends != {"old": old, "candidate": candidate}:
                raise HandoffRejected("rollback identity or state changed")
            self.selector = "old" if old.live() else "blocked"
            self.generation += 1
            return self.selector

    def _accept_loop(self):
        while not self.stop_flag.is_set():
            try:
                client, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self.mutex:
                backend = self.backends.get(self.selector)
                allowed = backend is not None and backend.live()
            if not allowed:
                client.close()
                continue
            h = threading.Thread(target=self._forward, args=(client, backend.port), daemon=True)
            with self.mutex:
                self.handlers.append(h)
            h.start()

    def _forward(self, client, port):
        upstream = None
        try:
            upstream = socket.create_connection(("127.0.0.1", port), timeout=3)
            upstream.settimeout(None)
            with self.mutex:
                self.sockets.update((client, upstream))
            a = threading.Thread(target=self._pump, args=(client, upstream), daemon=True)
            b = threading.Thread(target=self._pump, args=(upstream, client), daemon=True)
            a.start()
            b.start()
            a.join()
            b.join()
        except OSError:
            pass  # Never retry on direct route or other backend.
        finally:
            client.close()
            if upstream is not None:
                upstream.close()
            with self.mutex:
                self.sockets.discard(client)
                if upstream is not None:
                    self.sockets.discard(upstream)

    @staticmethod
    def _pump(source, destination):
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                destination.sendall(data)
        except OSError:
            pass
        finally:
            with contextlib.suppress(OSError):
                destination.shutdown(socket.SHUT_WR)

    def close(self):
        self.stop_flag.set()
        self.server.close()
        with self.mutex:
            for sock in list(self.sockets):
                with contextlib.suppress(OSError):
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
        if self.thread.is_alive():
            self.thread.join(timeout=3)
        for h in self.handlers:
            h.join(timeout=3)
