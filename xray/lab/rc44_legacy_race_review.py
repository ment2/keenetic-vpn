"""RC44 read-only source-based legacy S98/cron/killswitch race analysis.

No physical process scanning or kernel policy authority. Source snapshots only.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PATHS={
 "wifi":"xray/production/opt/bin/xray-wifi-rules.sh",
 "s98":"xray/production/opt/etc/init.d/S98xray-wifi",
 "ks":"xray/production/opt/bin/xray-ks-home.sh",
 "kswatch":"xray/production/opt/bin/xray-ks-home-watch.sh",
 "wd":"xray/production/opt/bin/xray-watchdog.sh",
 "hourly":"xray/production/opt/bin/xray-safe-hourly.sh",
 "cron":"xray/production/opt/bin/xray-fc-cron-guard.sh",
}
def source_review(root=ROOT):
 x={k:(Path(root)/p).read_text() for k,p in PATHS.items()}
 expected={
  "wifi":('-F "$CHAIN"','-A "$CHAIN" -d "$net" -j RETURN','-j TPROXY --on-port 12345'),
  "s98":('while true', 'grep -q TPROXY','sleep 60','"$SCRIPT"'),
  "ks":("sed -n '2p'",'-I FORWARD 1 -j "$CHAIN"'),
  "kswatch":('xray-ks-home.sh','sleep 15'),
  "wd":('S97xray','"$SERVICE" restart','sleep 30'),
  "hourly":('xray-update-v23.py','run -test -config','$PENDING','STAGED_ONLY:'),
  "cron":('xray-fc-guard-enabled','xray-fc-recover.sh')
 }
 for k,parts in expected.items():
  for p in parts:
   if p not in x[k]:raise RuntimeError("RC44_SOURCE_DRIFT_"+k)
 return {
  "s98_repair_loop_period_seconds":60,
  "ks_watch_period_seconds":15,
  "watchdog_period_seconds":30,
  "wifi_flushes_before_tproxy":x["wifi"].index('-F "$CHAIN"')<x["wifi"].index('-j TPROXY --on-port 12345'),
  "wifi_mangle_write_has_shared_lock":False,
  "ks_forward_uses_first_rule_only":True,
  "ks_forward_deduplicates_all_prior_occurrences":False,
  "hourly_spawns_short_lived_xray_binary_for_config_test":True,
  "hourly_staged_only_not_live_apply":True,
  "root_descendants_quiesced_proven":False,
  "production_changed":False,
  "production_authorized":False,
 }
def duplicate_forward_counterexample(initial):
 """The versioned ks-home.sh checks ONLY FIRST rule, then -I without -C."""
 state=list(initial)
 if not state or state[0]!="-A FORWARD -j XRAY_KS_HOME":
  state.insert(0,"-A FORWARD -j XRAY_KS_HOME")
 return tuple(state)
def wifi_repair_race_fixture():
 """Synthetic two actors; real physical interleaving remains UNOBSERVED."""
 prior=tuple("-A XRAY_WIFI -d "+p+" -j RETURN" for p in
   ("0.0.0.0/8","10.0.0.0/8","100.64.0.0/10","127.0.0.0/8",
    "169.254.0.0/16","172.16.0.0/12","192.168.0.0/16",
    "224.0.0.0/4","240.0.0.0/4"))
 repaired=prior+("-A XRAY_WIFI -p tcp -j TPROXY","-A XRAY_WIFI -p udp -j TPROXY")
 # S98 invokes original script and runs -F followed by all nine RETURN,
 # but one TPROXY append fails. Repair doesn't persist across this race.
 after_other_actor=prior
 return {"before_tproxy":len(prior),"after_operator_repair":len(repaired),
         "after_uncoordinated_s98_failed_rebuild":len(after_other_actor),
         "preserves_operator_repair":False,
         "simulated_only":True,"production_authorized":False}
