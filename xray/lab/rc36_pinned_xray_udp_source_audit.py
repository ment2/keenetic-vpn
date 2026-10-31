"""RC36 pinned Xray 26.2.6 source authority audit, never physical or runtime introspection.

Runs only against exactly hashed upstream source files. A pass proves API
surface does not export full udpWorker.activeConn snapshots in these three
services; it does NOT prove no external instrumentation is possible.
"""
import argparse
import hashlib
from pathlib import Path
import re

PINNED_COMMIT="12ee51e4bb1d02ece4ef4b7114efa2bcdc130995"
BLOBS={
 "app/proxyman/inbound/worker.go":"ef454d21195e2df878cd129f907dfaa65f7cdff0",
 "app/proxyman/command/command.proto":"71f8f0dcf0e9ae83204550aa9e02eba8384cb6b0",
 "app/stats/command/command.proto":"9c3f9131d087a6cd5c831a5ff708d93351b865f2",
 "app/router/command/command.proto":"22ae95b9844039f7460d1a5db5bfc54aa251487e",
 "proxy/dokodemo/dokodemo.go":"e56363db0a8dd0b059b0bf705067d6c65ed0b6aa",
}
class SourceDrift(RuntimeError):pass
def rpc_surface(proto):
    return frozenset(re.findall(r"\brpc\s+(\w+)\s*\(",proto))
def review(sources):
    worker=sources["app/proxyman/inbound/worker.go"]
    handlers=sources["app/proxyman/command/command.proto"]
    stats=sources["app/stats/command/command.proto"]
    routing=sources["app/router/command/command.proto"]
    dokodemo=sources["proxy/dokodemo/dokodemo.go"]
    expected=[
        r"activeConn\s+map\[connID\]\*udpConn",
        r"type connID struct",
        r"src\s+net.Destination",
        r"dest\s+net.Destination",
        r"if\s+!w.cone\s*\{",
        r"nowSec-atomic.LoadInt64\(&conn.lastActivityTime\)\s*>\s*2\*60",
        r"conn, found := w.activeConn\[id\]",
        r"w.activeConn\[id\] = conn",
        r"func \(w \*udpWorker\) removeConn\(id connID\)",
    ]
    for expr in expected:
        if not re.search(expr,worker):
            raise SourceDrift("MISSING_INTERNAL_SESSION_WITNESS:"+expr)
    if "processing connection from:" not in dokodemo:
        raise SourceDrift("MISSING_XRAY_PROXY_PROCESS_LOG_EVENT")
    api={
        "HandlerService":rpc_surface(handlers),
        "RoutingService":rpc_surface(routing),
        "StatsService":rpc_surface(stats)
    }
    if not all(api.values()):
        raise SourceDrift("MISSING_PINNED_GRPC_SERVICE")
    # This is *not* a claim about every extension/API in the universe; only
    # these source-pinned services configured by our MIPS candidate.
    for service,operations in api.items():
        for operation in operations:
            if re.search(r"(?i)(udp.*(session|conn|flow)|(session|conn|flow).*udp|freeze|snapshot|drain)",operation):
                raise SourceDrift("POSSIBLE_NEW_OWNER_API_REQUIRES_REVIEW:"+service+"."+operation)
    return {
        "pinned_commit":PINNED_COMMIT,
        "services":{k:tuple(sorted(v)) for k,v in api.items()},
        "internal_map":"private udpWorker.activeConn keyed by source and conditional destination",
        "inactive_older_than_seconds":120,
        "current_public_apis_complete_udp_owner_snapshot":False,
        "atomic_packet_freeze_or_durable_session_cas_proven":False,
        "verified_root_legacy_fencing":False,
        "production_authorized":False,
        "decision":"HARD_NO_GO_PRODUCTION",
    }

def read_verified_sources(root, expected=BLOBS):
    """Verify exact Git blob SHA1, NOT ordinary raw-file SHA1.

    Git's blob ID hashes b"blob <length>\\0" + bytes. Missing, modified,
    or unexpected sources must never produce a source-authority claim.
    """
    if set(expected)!=set(BLOBS):
        raise SourceDrift("PINNED_SOURCE_FILE_SET_DRIFT")
    sources={}
    for rel,sha in expected.items():
        path=Path(root)/rel
        if not path.is_file():
            raise SourceDrift("PINNED_SOURCE_ABSENT:"+rel)
        raw=path.read_bytes()
        git_blob=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+bytes([0])+raw).hexdigest()
        if git_blob!=sha:
            raise SourceDrift("GIT_BLOB_SHA_MISMATCH:"+rel)
        sources[rel]=raw.decode("utf-8")
    return sources

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args()
    sources={}
    sources=read_verified_sources(a.root)
    out=review(sources)
    print("RC36_SOURCE_PINNED_XRAY_26_2_6_UDP_ACTIVE_CONN_PRIVATE_MAP_CONFIRMED")
    print("RC36_SOURCE_GRPC_NO_COMPLETE_UDP_SESSION_OWNER_SNAPSHOT_IN_THREE_SERVICES")
    print("RC36_SOURCE_INTERNAL_UDP_120S_INACTIVITY_INDEPENDENT_OF_KERNEL_CONNTRACK")
    print("RC36_SOURCE_HARD_NO_GO_ATOMIC_FREEZE_ROOT_FENCING_NOT_IMPLEMENTED")
    print("RC36_SOURCE_SERVICE_OPERATIONS",out["services"])
if __name__=="__main__":main()
