"""RC44 first-migration TPROXY repair release review: read-only, source-pinned.

No router, no privileged command execution, no production authorization.
A two-rule repair is only a *proposal*, gated by future physical checks.
"""
import hashlib
from dataclasses import dataclass
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"xray/production/opt/bin/xray-wifi-rules.sh"
SOURCE_SHA256="ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef"
LIVE_RC43_CHAIN_SHA256="44f3d783cae72cb3987133c3f84abac389f1f1e4d91b98bafeafd04f1a5c3891"
MARK="0x40000000/0x40000000"
EXCEPTIONS=("0.0.0.0/8","10.0.0.0/8","100.64.0.0/10",
 "127.0.0.0/8","169.254.0.0/16","172.16.0.0/12",
 "192.168.0.0/16","224.0.0.0/4","240.0.0.0/4")
def current_chain_lines():
 return ("-N XRAY_WIFI",)+tuple("-A XRAY_WIFI -d "+net+" -j RETURN" for net in EXCEPTIONS)
def sha_lines(lines):
 return hashlib.sha256(("\n".join(lines)+"\n").encode()).hexdigest()
def pinned_source_review():
 raw=SOURCE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
  raise RuntimeError("PINNED_WIFI_REPAIR_SOURCE_DRIFT")
 text=raw.decode("utf8")
 required=("-F \"$CHAIN\"","-A \"$CHAIN\" -d \"$net\" -j RETURN",
           "-j TPROXY --on-port 12345","--tproxy-mark \"$MARK\"",
           "for proto in tcp udp")
 if not all(k in text for k in required):
  raise RuntimeError("WIFI_SCRIPT_CONTROL_PATH_DRIFT")
 if "set -e" in text or "|| exit" in text:
  raise RuntimeError("WIFI_SCRIPT_ERROR_HANDLING_REQUIRES_REEVALUATION")
 return {"source_sha256":SOURCE_SHA256,"nine_return_chain_sha256":sha_lines(current_chain_lines()),
         "unhandled_tproxy_append_failure_possible":True}
def minimal_iptables_restore_batch():
 # MUST be used only in an independently controlled and approved maintenance
 # window, after the original mangle table has been snapshotted and hashed.
 # Do not run on a router from this code path.
 return "\n".join(("*mangle",
  "-A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark "+MARK,
  "-A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark "+MARK,
  "COMMIT",""))
@dataclass(frozen=True)
class LiveWitness:
 boot_id: str=""
 xray_pid: int=0
 start_ticks: int=0
 wifi_chain_sha256: str=""
 same_listener_owner: bool=False
 target_tproxy_supported: bool=False
 original_mangle_snapshot_verified: bool=False
 rollback_rehearsed_on_target: bool=False
 root_descendants_quiesced: bool=False
 ipv4_ipv6_failclosed_verified: bool=False
 local_recovery_verified: bool=False

def review(witness=LiveWitness()):
 pinned_source_review()
 reasons=[]
 if witness.wifi_chain_sha256!=LIVE_RC43_CHAIN_SHA256:
  reasons.append("CHAIN_STATE_DRIFT_OR_NINE_RETURN_BASE_NOT_CONFIRMED")
 if not (witness.boot_id and witness.xray_pid>1 and witness.start_ticks>0):
  reasons.append("CURRENT_BOOT_PID_START_TICKS_UNVERIFIED")
 for key in ("same_listener_owner","target_tproxy_supported",
             "original_mangle_snapshot_verified","rollback_rehearsed_on_target",
             "root_descendants_quiesced","ipv4_ipv6_failclosed_verified",
             "local_recovery_verified"):
  if getattr(witness,key) is not True:reasons.append("MISSING_"+key.upper())
 # The model is NEVER an authority even when all synthetic booleans true.
 reasons.append("MODEL_RECEIPTS_DO_NOT_AUTHORIZE_PHYSICAL_TPROXY_CHANGE")
 return {"decision":"HOLD_REAL_ROUTER_REPAIR","production_authorized":False,
         "live_rules_modified":False,"router_jobs_submitted":False,
         "candidate_batch_for_review_only":minimal_iptables_restore_batch(),
         "rollback_rule_selectors":(
           "-D XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark "+MARK,
           "-D XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark "+MARK),
         "reasons":tuple(reasons)}
