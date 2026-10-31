"""RC35 disposable-only freeze/commit and generation CAS model for UDP ownership.

No actual kernel freeze, Xray internals, router calls or durable journal.
The successful outcome means only an *in-memory simulated transaction*.
"""
from dataclasses import dataclass
from threading import RLock

class UnsafeHandover(RuntimeError): pass

@dataclass(frozen=True, order=True)
class Flow:
    ingress: str
    source: str
    sport: int
    destination: str
    dport: int
    protocol: str="udp"

@dataclass(frozen=True)
class Witness:
    boot_id: str
    generation: int
    active_client_flows: frozenset[Flow]
    kernel_flows: frozenset[Flow]
    xray_owned_flows: frozenset[Flow]
    kernel_freeze_receipt: bool=False
    complete_xray_owner_inventory_receipt: bool=False
    independent_root_fence_receipt: bool=False

class HandoverModel:
    def __init__(self, boot_id: str, generation: int, old_flows: frozenset[Flow]):
        if not boot_id or generation<1:raise ValueError("invalid starting identity")
        self.boot_id=boot_id
        self.generation=generation
        self.old_flows=frozenset(old_flows)
        self.phase="OLD_OWNER"
        self._lock=RLock()
        self._preparation=None
        self.production_authorized=False

    def prepare(self, witness: Witness):
        with self._lock:
            if self.phase!="OLD_OWNER":
                raise UnsafeHandover("another freeze/commit in progress")
            if (witness.boot_id!=self.boot_id or witness.generation!=self.generation):
                raise UnsafeHandover("STALE_BOOT_OR_GENERATION_CAS")
            if (self.old_flows != witness.active_client_flows or
                self.old_flows != witness.kernel_flows or
                self.old_flows != witness.xray_owned_flows):
                raise UnsafeHandover("SILENT_OR_EXPIRED_FLOW_INCOMPLETE")
            if not (witness.kernel_freeze_receipt and
                    witness.complete_xray_owner_inventory_receipt and
                    witness.independent_root_fence_receipt):
                raise UnsafeHandover("MISSING_KERNEL_FREEZE_OR_XRAY_OWNER_OR_ROOT_FENCE")
            self.phase="FROZEN"
            self._preparation=(self.boot_id,self.generation,self.old_flows)
            return self._preparation

    def commit(self, prepared: tuple, *, exact_kernel_owner_receipt: bool,
               old_socket_bytes_preserved: bool):
        with self._lock:
            if (self.phase!="FROZEN" or prepared!=self._preparation or
                prepared!=(self.boot_id,self.generation,self.old_flows)):
                raise UnsafeHandover("INVALID_PREPARE_OR_STALE_CAS")
            if not exact_kernel_owner_receipt or not old_socket_bytes_preserved:
                raise UnsafeHandover("KERNEL_OWNER_ACK_OR_OLD_SOCKETS_MISSING")
            self.generation+=1
            self.phase="NEW_FLOWS_CANDIDATE_OLD_PINNED"
            return self.generation

    def rollback(self, *, boot_id: str, expected_generation: int,
                 original_rules_restored: bool, old_socket_bytes_preserved: bool):
        with self._lock:
            if (boot_id!=self.boot_id or expected_generation!=self.generation or
                self.phase not in ("FROZEN","NEW_FLOWS_CANDIDATE_OLD_PINNED")):
                raise UnsafeHandover("STALE_ROLLBACK_OR_NO_OWNER")
            if not original_rules_restored or not old_socket_bytes_preserved:
                raise UnsafeHandover("PHYSICAL_ROLLBACK_NOT_ACKNOWLEDGED")
            self.generation+=1
            self.phase="OLD_OWNER"
            self._preparation=None
            return self.generation
