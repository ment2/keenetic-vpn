# HA watchdog production staging — 2026-11-26

Baseline handoff: 6f0812a34972a721587bfd9b26c888c83a6142e9. Owner reported old monitor NOT_RUNNING/BLOCKED, TICK_FAILED_MANUAL_REVIEW:URLError, pending journal absent, polls 107. Underlying URLError cause not established. Owner started original monitor locally. Existing job 3726f867-7e9e-4bed-ba35-5dfec2703289 completed exit 0; all four staging targets absent and baseline monitor/tick hashes matched. No queue reset or reexecution of this job.

Four runtime modules from reviewed commit 0a159b61356103d7748efd056c4b63e1b80d1934 staged via HA MCP under distinct filenames in /data/ha-admin-agent. Each completed exit 0 FILE_WRITE_SHA256_VERIFIED:

| File | Job |
|---|---|
| ha_receipt_retry.py | f0d50bc4-eb8f-4af7-b7cd-a993816ab48f |
| ha_monitor_receipt_candidate.py | e2957258-6455-4752-b182-6ffdc3b98a75 |
| ha_receipt_watchdog.py | 81a9eb08-b837-405f-a14a-f49f683f583e |
| ha_monitor_watchdog_candidate.py | da789b8f-0d4a-45e3-957e-9320321854a6 |

Verification job b767bf8a-8ee5-4a27-b316-d2654b5e1d63, remote timeout 15 s, completed exit 0: RUNTIME_AND_BASELINE_SHA256_PASS 6; CANDIDATE_IMPORT_PASS; original MONITOR_PROCESS RUNNING, STATUS RUNNING, DETAIL HA_AGENT_JOB_ACKNOWLEDGED, POLLS 5. All six files regular, root-owned mode 0600, SHA-256 matched exact manifest/baseline. PENDING_JOURNAL True observed inside the verification job itself; this does not certify idle journal absence. All four staging write receipts also appear in audit revision 4. No fixture stub installed, no existing monitor or bridge overwritten, no activation or change to init_commands. Actual staging writes are the only changes to the production agent directory.

Status: STAGED / NOT ACTIVE. Existing recovery v2 remains installed. Prior physical isolated watchdog acceptance 18/18 and full budget 43.018 s remain valid. No additional feature development. Activation gate remains: live Worker version 54 duplicate-result semantics not attested; prior source read explicitly blocked, no workaround; SSH add-on boot/watchdog flags not readable by current agent. Use approved non-sensitive release attestation and authorized add-on metadata/UI, not alternate extraction. Switch only from independent local maintenance context, not a job whose own result depends on stopping the monitor. Confirm no active/UNKNOWN jobs, no pending journal, both locks free and no descendants after cooperative stop. Preserve old startup wiring in trial. Rollback: stop candidate, confirm same conditions, restart unchanged original; never erase uncertain journal. No real backup enabled; prior Keenetic package-write restriction and final inventory/key escrow remain. No Keenetic commands or transfer attempted in this stage.
