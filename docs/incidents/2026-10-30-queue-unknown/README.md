# Keenetic Mobile v5: unknown job blocked queue (2026-10-30)

## Incident and evidence
- Cloudflare Worker: `keenetic-control-bridge.wlad124650.workers.dev`; Durable Object is authoritative for job state.
- A local read-only scan of `/opt/telegram-ai/keenetic-agent-ledger/` found 123 records with local `done`, none with local `running` or `unknown`. Local ledger cannot prove the server queue is clear.
- Authenticated read-only `GET /v1/audit` showed job `da2d6c64-d60d-4cc5-bd67-66b8b3a16908` queued then claimed; eight later jobs queued.
- `get_router_task_result` confirmed the first job (`read_file`) as `unknown`, with the other eight `queued` (seven `read_file`, one `exec`).
- Initial recovery script checked `unknown` but failed at interactive `input()` inside `python3 - <<'PY'`: `EOFError`. **No reconcile was sent by that attempt.** Fix: read confirmation from `/dev/tty`.
- Operator subsequently ran corrected recovery script. Final read-only GET response: `HTTP_STATUS:200`, job status `failed`, `exit_code:-1`, output `Task expired or permission revoked before execution.` Thus the unknown state was cleared. **The result of POST itself was not supplied**, but the subsequent status change was verified.
- No evidence yet that eight queued jobs have all completed. Poll their existing IDs; never enqueue them again.

## Job IDs pending at diagnosis (do not resubmit)
- `d43456d4-bc38-4395-a4f8-d3eac829f1e0` read_file
- `6879a9e5-e0d9-4f44-ad62-d5ab11966664` read_file
- `73ed5129-8ae3-45d6-b78c-2c626f6944d5` read_file
- `0954bd27-036f-4ff8-8421-0db17c519a56` read_file
- `e3d2d5c7-6482-40ff-aeb0-7e9310b6eed7` read_file
- `afd9efa1-a40d-4441-bc67-c82442ef736c` read_file
- `2a5427da-9d58-48f4-9806-72013d411886` read_file
- `73553c5a-5253-455b-a760-5a8c6ea21e59` exec (inspect intended command before permitting processing)

## Safe response procedure
1. Scan local agent ledger read-only using `scan_local_jobs.py` (only local evidence).
2. Read `GET /v1/audit` with `CONTROL_ADMIN_TOKEN`; extract candidate job IDs.
3. Confirm each with `GET /v1/jobs/{id}` or `get_router_task_result` (no new jobs).
4. Verify agent is **not currently executing** the unknown job; a status of `unknown` alone does not prove execution stopped.
5. With operator approval only, run `reconcile_unknown.py` (prompts for admin and policy tokens and YES, checks status first, posts one reconcile, verifies status). This changes server queue state, not router config.
6. Poll the existing eight IDs and check results before claiming queue recovery. In particular the pending `exec` may run automatically once the queue resumes.

## Boundaries
- No secrets are stored in these files; enter tokens interactively and never paste them into chat or commit them.
- Never manually call `/v1/agent/next`, resend jobs, restart Xray, or modify cron/firewall/routes to recover this queue.
- The `reconcile_unknown.py` script is a runbook and must not be executed automatically. Endpoint request contract is based on the working conversation command, not a fresh independent production schema audit.