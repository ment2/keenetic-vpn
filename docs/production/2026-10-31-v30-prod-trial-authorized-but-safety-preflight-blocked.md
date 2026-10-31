# Xray v30 production trial: owner approved outage, launch BLOCKED before any signal

Date: 2026-10-31; scope only `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

## Owner consent

Owner explicitly approved first live canary experiment with possible VPN interruption, in response to the proposal of:

```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --trial --expected-old-pid 13546 --expected-old-ticks 100216734 --expected-config-sha 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7 --accept-network-interruption
```

This is approval of risk and **not evidence the live process state is still the same or that the guard is fit for purpose**. Prior installation passed one `--plan` and was documented separately.

## Gate interrupted prior to trial

Before considering `--trial`, a non-mutating router preflight was prepared to check installed canary SHA/mode, exact legacy Xray + watcher/S98 PID/start-ticks, absence of previous guardian journal, and whether an in-flight S97 `restart` or `xray-wifi-rules.sh` child could run beyond a `SIGSTOP` of the shell PID. It would not print script contents or secrets.

The attempted Keenetic Mobile `exec_command` **did not return a job id**; the orchestration tool returned exactly:

```text
Script error:
Этот вызов инструмента был заблокирован системами безопасности OpenAI. Внимательно проверьте отправляемые данные.
```

The block was not bypassed or retried with a different command or tool. The remote system did not return `queued`, `running` or `done`. Therefore do **not** infer the preflight succeeded, or that production status was freshly measured. No `--trial` job was submitted, no trial job ID exists in this interaction, no `--rollback` or guardian invocation was submitted, and no changes to Xray/firewall/routes/cron/Cloudflare were intentionally made.

## Independent source-review risk remaining even with 253 green CI tests

- Frozen production `xray-watchdog.sh` calls `S97xray restart` when 10808 appears unavailable; `S97xray` uses global `killall xray`.
- `S98xray-wifi` invokes `xray-wifi-rules.sh`; the latter can flush and refill the live `XRAY_WIFI` iptables chain and replace the TPROXY route.
- Current installed `xray/staging/v30_first_cutover_canary.py` fences only the identified watchdog and S98 shell PIDs via `SIGSTOP` and checks their `T/t` states. It **does not fence already running child/descendant processes** or prove no in-flight S97 restart / wifi rules rewrite.
- If one of those descendants continues during cutover, it may kill the candidate (via `killall`) or alter live routing despite the stopped parent PIDs. A point-in-time preflight alone would not eliminate the race between observation and SIGSTOP. The autonomous guardian can return `blocked` without restoring service in these conditions. The owner accepted interruption, but automatic recovery cannot honestly be guaranteed.
- CI `41200967162` SUCCESS, 253 offline tests and one previous read-only `--plan` PASS do not prove descendant fencing, end-to-end TPROXY TCP/UDP, or recovery from guardian death/reboot.

## Disposition / safe continuation

**HOLD** any live `--trial` or `--rollback` until a redesigned or more rigorously tested descendant-safe first cutover is independently approved. Review process parent/child fencing and rollback in an isolated simulated environment; use a permitted first-party diagnostic pathway for live status checks rather than trying to circumvent the security block. Any revised executable changes Git SHA/byte SHA and would need a fresh exact installation and trial approval. Do not reuse the earlier approval for modified bytes.

The existing on-router canary remains at its last verified SHA256 `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203` as of the earlier successful `--plan`; it was **not freshly rehashed in this turn**.

**State:** owner consent recorded; **production trial NOT STARTED**, safety gate not cleared, no duplicate jobs.
