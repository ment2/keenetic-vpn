# RC2 VPN monitoring — cutover, 27 November 2026

Scope: monitoring only. geo-independent v23 work stopped. No Xray, updater,
watchdog, firewall, routing or kill-switch modifications performed.
All times below MSK.

## Cutover
Preflight job 70085e84-5e08-4a57-958c-ec3883d741bd confirmed six core
staging blobs and four valid source pins, old cron SHA
fb3f3871bcf79a83739f14dbaa8817b262bedb1c1cd0907b4594f709cd6da6c3,
old init SHA abea4530831916ddc92eac4742a5f9a528a3efc4188a9e13f3305cc4a3d855af.
HA was unavailable before cutover.

First attempt e43626f2-a2bc-43d3-b23c-526040243f22 failed before writing:
native /bin/sh rejects -n (exit 245); Entware /opt/bin/sh -n passed.
Baseline unchanged, verified in job bd9d5db0-91d1-4013-a8e8-1d3c8ec531e6.
Corrected cutover commit 8594be988b00f4c146d03059e6ed9f506556dbc4,
staged script SHA256 8db23ce935d196ea0dd4d8d6e69c6c37f5e5d838f0465364cbc79bfb7105deea.
Second attempt 60adaa58-d3d9-4854-87ba-04aeacd478f6 wrote private backups,
stopped old VLESS collector and installed new cron/init, but reported
rollback cron conflict because crontab added three comment lines.
Do not rerun this cutover. Reconciliation jobs 3924f495-a2ad-4778-b652-dd6b19779f5c
and 73dc07be-b09c-4b14-8137-ec0b901626da confirm exact command order,
three extra comments only, no missing expected lines, init matches
prepared after-image. Actual cron SHA256
ba1903a998c4b707551e93667d481c1d36744ce00d18af07effcda6cf29541d0.
Unrelated updater cron line preserved. Old VPN/OpenAI collectors absent;
traffic collector PID 746/start ticks 4507 unchanged at readback.
Repository script amended for comment-only normalization, commit
24e6789519fa16fd000d4ea19a4c152856d1c34a; not redeployed or rerun.

Probe cron: minutes 3,18,33,48. Publish cron: every minute.
Both use persistent rc2-stage and existing RC2 monitor locks.
Private per-mode logs overwrite each execution; no unbounded append.
If updater is busy, existing RC2 checks skip the probe; no hard 15-minute
coverage SLA claimed.

## Live panel
19:10:08 scheduled HA publication: unavailable (expired old snapshot).
One bounded initial operational seed, job 73dc07be-b09c-4b14-8137-ec0b901626da,
refreshed full subscription of ten and probed eight within 82.26 s.
19:12:08 automatic HA publication: state ok, count 10, probe_complete 8,
subscription_at 1795795821; job a2340beb-0666-4183-9004-5f7d322b29fb.
Actual Lovelace rc2-shadow compact card matched staged YAML; seven cards
present, live template rendered all ten tags, no unavailable notice;
job a3aa951c-24f0-4035-99c7-04510fd212e3 exit 0.
No physical iPhone screenshot verified in this turn. Complete normal
scheduled probe cycle not yet observed. One-time read-only follow-up
scheduled at 19:45 MSK to inspect 19:18 and 19:33 cycles and HA freshness.
No extra probe or deployment authorized by follow-up.

## Rollback
Private verified before/after copies and SHA256SUMS in
/opt/var/lib/vpn-monitor/rc2-cutover-backup-1795795689.
If necessary, compare actual cron commands and comments against after
image, restore only monitor schedule and init before-image, ensure no
new probe running, then start only original VLESS collector.
Preserve traffic collector and unrelated jobs. No physical rollback
performed; no VPN restart. Keep previous HA dashboard and history.
