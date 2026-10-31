# Keenetic Xray v30: separate INSTALL-ONLY consent (2026-10-31)

**Restricted scope**: `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. This document is not deployment, cutover, or rollback approval.

## Exact source pinned

- Source: `xray/staging/v30_first_cutover_canary.py`.
- Destination **after separate owner consent**: `/opt/bin/v30_first_cutover_canary.py`.
- Git blob SHA1: `08b172af082df1284be35f39592942c0942a377b`.
- SHA256 (UTF-8 file bytes, trailing LF): `93f187cadbe985e65e67f619f9f3d7c1c8f120cdb9a506b22419a75cdeabdb4d`.
- Size: 21,363 bytes. Python source: 514 code/text lines plus final LF (split produces 515 entries).
- Source viewer: https://github.com/ment2/keenetic-vpn/blob/feature/xray-v30-stable-tcp-ingress-lab-20261031/xray/staging/v30_first_cutover_canary.py
- Independently verified: Python source fetched with GitHub repository file tool and SHA256 computed over exact source bytes. GitHub Actions [41198879628](https://github.com/ment2/keenetic-vpn/actions/runs/41198879628) **SUCCESS**, `sha256sum -c -` printed `xray/staging/v30_first_cutover_canary.py: OK`; 240/240 offline/model tests passed. A preceding workflow-only quoting error was corrected; it did not modify the source itself.
- Head of branch at verification: `72c4b975c1ad42bee3bad04c7185a04712c28abf`. This may advance due to documentation. The file blob SHA and SHA256 are the installation pins, **not the mutable branch name**.

## Exact consent boundary

**Not yet approved:** Any `write_file` / `exec` against the router. User requested to see exact full contents/path and checksum before deciding.

**Proposed NEXT action, only after explicitly approving the entire source file and this destination**:
1. Use one exact UTF-8 write to `/opt/bin/v30_first_cutover_canary.py` with the pinned source bytes; verify resulting job by ID, never repeat a queued write. A plugin may create a backup; no other path should be touched.
2. Verify on router with `sha256sum /opt/bin/v30_first_cutover_canary.py`; require exact above SHA256. Before any execution, verify source has not changed.
3. If the writer creates mode `0600`, separate approved `chmod 0700 /opt/bin/v30_first_cutover_canary.py` may be used. Python can read mode `0600` as root; chmod is optional for `python3 path`.
4. Execute **ONLY** this non-mutating CLI mode after install and checks, using the latest expected identity (if stale, fail closed):
```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --plan --expected-old-pid 13546 --expected-old-ticks 100216734 --expected-config-sha 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7
```
Expected output includes `READ_ONLY_PRECHECK_OK`, `GUARD_NOT_ARMED; NO_CHANGE; NO_APPROVAL`. If Xray PID/start-ticks, config, watchdog/S98 identities, backup checksum or kernel policy differ, **STOP** and inspect rather than overriding guards.

**Explicitly prohibited by this approval:** `--trial`, `--rollback`, `--guardian`, signals, service stops/restarts, production config, iptables, route, cron, kill-switch, Cloudflare deployments, GitHub merge/deploy and all changes to `main` or snapshot.

## Why the canary is not production-ready merely because source tests pass

- Model/CI checks include detached synthetic guardian, PID/start_ticks checks and mocked rollback, **not real signal delivery or router reboot recovery**.
- The proposed guardian is single-instance. A crash between candidate process launch and PID journal update could leave an untracked live candidate, safely block restoration, but **not autonomously recover service**.
- SIGSTOP of watcher shell PIDs may not fence existing child/grandchild processes; exact process group ancestry requires a harmless on-router drill before any trial.
- TPROXY TCP/UDP end-to-end, provider/VLESS, DNS/IPv6 leakage, Telegram paths and no-direct fallback for candidate are not proven by a successful `--plan`.
- The source contains `--trial` and `--rollback` executable paths; installing the file gives those functions local availability, **not permission to invoke them**. Actual initial migration may disconnect existing flows.

**Current disposition: AWAITING EXPLICIT INSTALL-ONLY APPROVAL. Live Keenetic Xray and production network unchanged.**
