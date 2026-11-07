#!/usr/bin/env python3
"""RC43: read-only current-state report using exact previously installed canary.

This file is feature-branch staging only, never auto-installed/executed.
No process signals, firewall/routes changes, config writes or production calls.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

CANARY_PATH=Path("/opt/bin/v30_first_cutover_canary.py")
CANARY_SHA256="8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203"
CANARY_GIT_BLOB="495cd51581f472a9cb0a257ff7cd9f0d611dcab7"
PENDING=(
 "CURRENT_OFFSITE_ENCRYPTED_BACKUP_AND_RESTORE_TEST",
 "WATCHDOG_AND_S97_S98_S99_CRON_DESCENDANTS_QUIESCED",
 "LOCAL_PHONE_SSH_RECOVERY_RECONFIRMED",
 "REAL_SOCKS_TPROXY_TCP_UDP_AND_OPENAI_DNS_IPV6_CHECKS",
 "CANDIDATE_API_START_AND_ROLLBACK_REHEARSAL",
 "PERMANENT_PROMOTION_SEPARATELY_REVIEWED",
)
class Blocked(RuntimeError): pass
def digest(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
def import_verified(path=CANARY_PATH):
 p=Path(path)
 if p.is_symlink() or not p.is_file():raise Blocked("CANARY_MISSING_OR_SYMLINK")
 if digest(p)!=CANARY_SHA256:raise Blocked("CANARY_SHA_DRIFT")
 spec=importlib.util.spec_from_file_location("rc43_verified_canary",p)
 if spec is None or spec.loader is None:raise Blocked("CANARY_IMPORT_UNAVAILABLE")
 module=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 return module
def inspect(module,getuid=os.geteuid,boot_path=Path("/proc/sys/kernel/random/boot_id")):
 if getuid()!=0:raise Blocked("ROOT_REQUIRED_FOR_READONLY_PLAN")
 owners=module.owned_xray_pids()
 if not isinstance(owners,list) or len(owners)!=1:
  raise Blocked("OLD_XRAY_OWNER_NOT_EXCLUSIVE")
 pid=owners[0]
 ticks=module.ticks(pid)
 if not isinstance(ticks,int) or ticks<1:raise Blocked("OLD_XRAY_TICKS_INVALID")
 sha=module.checksum(module.ACTIVE)
 # Existing --plan code path: backup hashes, original config and binary,
 # listener ownership, firewall read-only checks, watcher/script hashes.
 watchdog,wifi=module.preflight(pid,ticks,sha)
 if len(watchdog)!=2 or len(wifi)!=2 or watchdog[0]==wifi[0]:
  raise Blocked("WATCHER_IDENTITY_AMBIGUOUS")
 boot=Path(boot_path).read_text(encoding="ascii").strip()
 if len(boot)!=36:raise Blocked("BOOT_ID_UNAVAILABLE")
 if module.STATE.exists() or module.READY.exists():
  raise Blocked("PREVIOUS_GUARDIAN_JOURNAL_PRESENT")
 return {
  "state":"CURRENT_LEGACY_READONLY_PREFLIGHT_OK",
  "boot_id":boot,
  "old_pid":pid,"old_start_ticks":ticks,"active_config_sha256":sha,
  "watchdog_pid_start_ticks":list(watchdog),
  "wifi_pid_start_ticks":list(wifi),
  "first_migration":"MAINTENANCE_OUTAGE_SESSION_RESET_ALLOWED",
  "legacy_private_activeconn_snapshot_required":False,
  "currently_unverified_prerequisites":list(PENDING),
  "canary_or_cutover_executed":False,"production_modified":False,
  "cutover_authorized":False,
 }
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--installed-canary",type=Path,default=CANARY_PATH)
 args=p.parse_args()
 try:
  result=inspect(import_verified(args.installed_canary))
 except (OSError,ValueError,Blocked,RuntimeError) as e:
  reason=str(e) if isinstance(e,Blocked) else "READONLY_PLAN_FAILED"
  print(json.dumps({"state":"BLOCKED","reason_code":reason,
                    "production_modified":False,"cutover_authorized":False}))
  return 2
 print(json.dumps(result,sort_keys=True))
 return 0
if __name__=="__main__":raise SystemExit(main())
