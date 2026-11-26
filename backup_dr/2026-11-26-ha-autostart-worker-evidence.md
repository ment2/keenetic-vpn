# HA watchdog cutover: autostart and Worker release evidence

Baseline: ment2/keenetic-vpn commit 77282a99680d21192b5d08c59d183fdbf2b07037. Four reviewed runtime modules staged; six hashes and candidate import previously passed. No activation or new backup service.

## Owner UI evidence

Owner screenshots IMG_0110.png and IMG_0111.png and IMG_0112.png in this conversation: Advanced SSH & Web Terminal v24.2.1 is running; Start on boot and add-on Watchdog toggles are on. Original init_commands has `python3 /data/ha-admin-agent/ha_monitor.py start` followed by an exporter command. The subsequent unsaved UI shows the exporter first and a truncated new watchdog command second. The Save button is enabled. Full new command and final persisted setting are not confirmed; preserve original order and exporter. Owner was instructed not to save or restart pending gate. Add-on boot/watchdog flags now evidenced by the owner UI, not the previously denied Supervisor CLI.

## Worker evidence

Active deployment was verified in the preceding turn: version 54 a2f3bdb8-0fa5-4ea4-a248-2a3760a91ad3 at 100%, deployed 2026-11-26T19:08:01.996554Z. Earlier metadata confirms version 53 be38dd8c-7777-45c9-9b92-8cb407c79d1d and 54 share script ETag dfc03e0e7ee6b83982cab88e3fcbad2f8905c259ce360cb4d72cbf3ceb14bb83. ETag continuity is not independently verified byte equivalence to a local bundle. Do not retry the denied source retrieval or reconstruct the protected live source.

New documentary evidence: ment2/keenetic-control commit 5725ce0fa4a74d29ccf7f6d3ebf28e44930985ca, docs/homeassistant/2026-11-26-ha-oauth-accepted.md, explicitly identifies production v53, deployment b33f2c6c-aa75-49a5-a4af-cfa9858a2f90 and the four OAuth consent/redirect/CSP/audit fixes between v49 and v53. It reports 25/25 offline tests and real OAuth acceptance. No explicit version-bound duplicate-result attestation appears in the record. The saved 2026-11-26-ha-oauth-bundle-tests.tap has 24/24 PASS, including original single claim/authorize/result flow and uncertain execution quarantine; the inspected test source lists those cases but no named same-result duplicate/lease-conflict case. These are historical documented results, not a new execution or live verification of v54 idempotency. Code/commit searches did not locate an additional attestation. Historical result-handler review and live receipt-recovery observations remain supporting but insufficient evidence of the exact current deployed contract.

## Decision

Boot/watchdog evidence gate closed. Source-attestation gate remains open. Production cutover remains NO-GO under the prior agreed gate. No production job/result replay, restart, source deployment, privilege change, queue reset, or setting save performed in this turn. No further owner terminal commands needed now. Next useful action is an authorized release-side attestation binding the same-result ACK, conflict rejection, and exact-lease late-result behavior to the current version/ETag, or a separately approved reviewed release and isolated acceptance. Do not treat repeated metadata queries as fresh attestation. Backup DR real sender/receiver and actual restore remain unimplemented in production; prior Keenetic package transfer restriction remains in force.
