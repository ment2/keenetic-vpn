"""RC40: distinguishability theorem for missing private Xray UDP owner inventory.

Pure data-only model. This can falsify release rules based solely on the
kernel conntrack+packet snapshot, but CANNOT attest any live router process,
enforce a kernel fence, copy a real session or authorize production.
"""
from dataclasses import dataclass
from typing import FrozenSet, Tuple

@dataclass(frozen=True)
class UdpFiveTuple:
    ingress: str
    source_ip: str
    source_port: int
    dest_ip: str
    dest_port: int

@dataclass(frozen=True)
class ExternalWitness:
    boot_id: str
    generation: int
    old_pid: int
    old_start_ticks: int
    candidate_pid: int
    candidate_start_ticks: int
    conntrack_entries: FrozenSet[UdpFiveTuple]
    recent_packets: FrozenSet[UdpFiveTuple]
    rules_sha256: str

@dataclass(frozen=True)
class World:
    visible: ExternalWitness
    xray_private_active_conns: FrozenSet[UdpFiveTuple]

@dataclass(frozen=True)
class CommitAuthority:
    complete_xray_private_snapshot_attested: bool=False
    simultaneous_immutable_kernel_snapshot_attested: bool=False
    actual_ingress_freeze_before_capture: bool=False
    kernel_commit_receipt: bool=False
    durable_fsync_generation_cas: bool=False
    stable_boot_pid_start_ticks_and_socket_cookies: bool=False
    mandatory_independent_root_descendant_fence: bool=False
    original_rules_exact_rollback_ack: bool=False
    independent_usb_free_rescue_verified: bool=False
    physical_vendor_kernel_acceptance: bool=False

def non_identifiability_witness(a: World, b: World) -> dict:
    """A complete owner map cannot be inferred from an equal public snapshot
    if two possible internal maps disagree. Synthetic proof, NOT live probe.
    """
    if a.visible != b.visible:
        return {"witness":"DIFFERENT_EXTERNAL_SNAPSHOTS",
                "demonstrates_incomplete_inventory":False,
                "production_authorized":False}
    if a.xray_private_active_conns == b.xray_private_active_conns:
        return {"witness":"PRIVATE_STATES_IDENTICAL",
                "demonstrates_incomplete_inventory":False,
                "production_authorized":False}
    return {"witness":"SAME_KERNEL_PACKET_SNAPSHOT_DIFFERENT_XRAY_PRIVATE_OWNER",
            "demonstrates_incomplete_inventory":True,
            "production_authorized":False}

def release_decision(observed: ExternalWitness, *, owner_snapshot=None,
                     authority: CommitAuthority=None) -> dict:
    """Never substitute an opaque current UDP process for session enumerability.
    Even complete synthetic booleans are not a real independent signed receipt.
    """
    authority=authority or CommitAuthority()
    reasons=[]
    if owner_snapshot is None:
        reasons.append("NO_COMPLETE_VERIFIED_XRAY_INTERNAL_UDP_OWNER_MAP")
    else:
        missing=observed.conntrack_entries.difference(owner_snapshot)
        if missing:
            reasons.append("KERNEL_UDP_TUPLES_WITHOUT_XRAY_OWNER")
        # An expired conntrack entry may still exist in legacy private map;
        # a public-only snapshot is NOT a complete owner authority.
        if owner_snapshot.difference(observed.conntrack_entries):
            reasons.append("PRIVATE_UDP_OWNER_HIDDEN_FROM_KERNEL_CONNTRACK")
        if not authority.complete_xray_private_snapshot_attested:
            reasons.append("CLAIMED_PRIVATE_OWNER_SNAPSHOT_NOT_INDEPENDENTLY_ATTESTED")
    for k,val in vars(authority).items():
        if val is not True:
            reasons.append("MISSING_INDEPENDENT_RELEASE_WITNESS:"+k)
    reasons += [
        "LEGACY_UNINSTRUMENTED_XRAY_26_2_6_PRIVATE_MAP_NOT_EXPORTABLE_BY_PINNED_GRPC",
        "ACTUAL_KERNEL_FREEZE_COMMIT_NOT_PROVEN",
        "ROOT_CGROUP_V1_ESCAPE_AND_SEVEN_PRIVILEGED_DESCENDANTS_NOT_FENCED",
        "PHYSICAL_USB_FREE_RECOVERY_NOT_VERIFIED",
        "SYNTHETIC_RECEIPTS_ARE_NOT_PHYSICAL_ACCEPTANCE",
    ]
    return {
        "decision":"HARD_NO_GO_PRODUCTION",
        "reasons":tuple(sorted(set(reasons))),
        "complete_live_owner_inventory_proven":False,
        "atomic_kernel_commit_proven":False,
        "physical_root_fencing_proven":False,
        "production_authorized":False,
        "router_actions":(),
    }
