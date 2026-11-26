# HA queue recovery: verified incident and reusable command

On 2026-11-26 an HA exec with timeout 145 seconds blocked FIFO; agent supports 45 seconds. Local monitor was RUNNING, HA_AGENT_IDLE, pending journal absent. User synchronized the HA-only policy secret and updated the local admin token to match the current Worker. Reapplying identical policy succeeded: revision 3 -> 4, both queued jobs ca8cb67a-b25d-4566-b3ec-712acbdade18 and da504b6d-3080-4935-a45f-44b1a2bd0a14 failed before execution, existing scopes retained. Subsequent HA job 11c1c981-1e31-4e06-9df6-a929739b9b55 completed; detached fixture startup job 663bf294-1fff-45c9-a0ba-9e4224a08add returned LISTENER_RC 0; Keenetic sender 8c954c7d-3443-4502-be36-90bc09b4c479 returned KEENETIC_HTTP_RECEIPT_PASS. HA-side disk restore log not yet inspected in this checkpoint.

## Local command (HA add-on terminal, not via MCP)

`python3 /data/ha-admin-agent/recover_ha_queue.py --reset-queued`

Type RESET followed by the revision printed by the script. This cancels ALL queued HA jobs, not just one; use only when the owner intends to cancel all waiting jobs and no active execution is expected. Default without flags is read-only. Optional --expect-revision N pins a known revision. Script checks policy, visible unresolved audit claims and local pending journal; these are not an atomic server-side queue lock. Do not use during other active admin operations. POST once only; verify policy and job states after any error; never automatically retry. No restart, no clearing journals, no key changes. Local root-owned private credential files are read, never logged. GET 401 indicates admin key mismatch; POST 401 after successful GET suggests policy key mismatch or auth routing; verify deployment and HA-only keys, do not rotate agent token. Keep HA exec timeout <=45s; launch bounded detached processes and verify readiness separately. Long-term fix is server-side timeout admission validation and scoped queued-job cancellation, not repeated policy resets.

New script has mocked offline tests; the live incident used the equivalent manual POST. Do not invoke a real reset just to test the wrapper.
