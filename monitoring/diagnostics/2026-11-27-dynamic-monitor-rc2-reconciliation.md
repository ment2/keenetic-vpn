# RC2 reconciliation — 2026-11-27

## Canonical implementation
The branch contained two incompatible representations using the same RC2 MQTT
topic. Retained the previously physically tested `rc2_*.py` implementation
and its `rc2_card.yaml` / `rc2_history_cards.yaml` templates. Restored the
eight overlapping RC1 files to the exact blobs from RC1 commit 7c65ea95.
RC1 and RC2 must not run simultaneously. The canonical RC2 payload uses
named objects, not RC1 positional rows. No router source was changed in this
reconciliation.

## CI
- Intermediate combined tree: run 46016084241, 172/172 SUCCESS; superseded
  because it contained the conflicting parallel implementation.
- Reconciled tree: run 46016326666, 162/162 SUCCESS.
- Final code/test commit ba34060e8f59050f61af399ea608213a193f1ec0:
  run 46016462712, job 140564759281, 163/163 SUCCESS.
  Added maximum-length ten-node hostname/Unicode geography and probe-budget
  regression. The 24-node representative payload test and 32 KiB cap
  remain. Larger worst-case payloads fail closed; no arbitrary node count
  or broker capacity is claimed.

## Physical evidence and remaining gates
The preceding RC2 runbook records the isolated physical ten-node cycle:
82.59 s, six Internet HTTP 204, five OpenAI HTTP 401, six exit-IP and
geography results; main Xray identity/config unchanged. Single-node probe
9.16 s. Previous shadow discovery and explicitly unavailable non-retained
state received PUBACK; HA registry confirmed the new sensor.

Current read-only preflight: five active VPN nodes, pending absent,
Linux 4.9 little-endian, Python 3.13.9, readable proc TCP data, protected
monitor directory, adequate storage. Source pins unchanged. Private RC2
stage and backup manifest are present; original OpenAI cron line remains,
no RC2 cron line observed. Previously recorded full-cycle duration is not
a guarantee of every future scheduled cycle. Probe budget 600 s;
ten nodes × 55 s <= 600 s; history separately bounded between calls.

HA add-on has neither SUPERVISOR_TOKEN nor HA_TOKEN exposed. Requests to
both supervisor/core/api and homeassistant:8123/api returned HTTP 401.
Browser integration also requires its originating connected browser context.
Do not scrape tokens, modify authorization or directly edit cached
.storage to bypass the gate.

Next: use an authorized HA UI/API session to validate the actual entity
state, expiry, full real aggregate MQTT payload and mobile view; verify
staged source and backup hashes before cutover. Then follow existing RC2
runbook for monitor-only schedule and two complete scheduled cycles,
preserving old history and traffic collector. No production Xray/updater,
firewall, routes, kill-switch, cron or dashboard changes made in this turn.
Physical cutover remains NO-GO. See prior RC2 runbook and HA discovery
supplement for the already completed physical tests.
