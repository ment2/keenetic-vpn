# Keenetic production → GitHub: verified scope and staging gaps

Assessment: 2026-10-31. Repository: `ment2/keenetic-vpn`, branch `snapshot/keenetic-production-2026-10-30`.

## Decision in one paragraph

**There is already an executable, isolated Xray 26.2.6 MIPS32LE compatibility laboratory in GitHub Actions. There is NOT yet a full router-faithful staging environment or a reproducible disaster-recovery release.** The frozen **2026-10-30** snapshot of 63 enumerated nonsecret Xray sources/backups has an independently recorded live-router SHA256 comparison from that day. The new CI verifier checks the **GitHub checkout against the frozen manifest and Git modes only**; it cannot establish that current router files have not drifted after 2026-10-30.

## What is ready and what the proof means

| Area | Status | Evidence / limit |
| --- | --- | --- |
| Historical Library archive | Archived | 60/60 Library source documents matched GitHub default branch on 2026-10-30; not synonymous with production |
| Production Xray source/archive | **2026-10-30 snapshot complete for the enumerated set** | 63/63 files and historical backups under `xray/production/opt/`; original independent live-hash comparison in `xray/production/README.md` |
| Frozen-tree integrity after GitHub changes | **CI PASS** | `tools/verify_production_snapshot.py` recalculates SHA256 on the 63 checkout files, checks for missing/extra/unmanifested files and Git modes; mutation tests deliberately corrupt/miss/add files |
| Python/shell syntax and source contracts | **CI PASS** | 17 Python files parsed; selected active shell/init files `sh -n`; 131 offline unit/contract tests including 8 snapshot integrity and 6 credential guard tests |
| Xray binary/API on target instruction set | **Compatibility lab PASS** | GitHub runner QEMU MIPS32LE, Xray 26.2.6. Two independent real Xray processes; SOCKS5 TCP and UDP ASSOCIATE, candidate termination and TCP/UDP via the old process; API `bo/ado/rmo` continuity |
| First cutover with one stable production ingress | **NOT implemented** | Existing tests choose separate SOCKS ports or use a synthetic controller; no real shared-port handoff |
| Router TPROXY, Wi-Fi routes, iptables, IPv6, DNS, kill-switch | **NOT reproduced** | Requires KeeneticOS/kernel/network fidelity; user-space QEMU is not a router kernel |
| Production watchdog/init coordination | **NOT proven** | Captured `S97xray` uses `killall xray`; unsafe with dual-process cutover; no real supervisor fencing test |
| Production rollback / zero-interruption guarantee | **NOT proven** | No approved production migration, no bounded outage measurement on router |
| Deploy/recovery from GitHub | **NOT available** | No authoritative build/package/permissions inventory plus verified sanitized runtime configuration and secret restoration process |
| Git history secret audit | **NOT proven** | Current 63 files pass a high-confidence credential scanner; full commit history and obfuscated values have not been scanned |

**GitHub Action:** `Xray snapshot offline source contracts` (run 41189579857: SUCCESS, 131/131 tests), and `Xray v30 isolated MIPS32LE compatibility` (run 41136161172: SUCCESS). Neither touches production.

## Current snapshot boundaries and missing inventory

1. **Source drift:** 63/63 is a *2026-10-30 enumerated source-set claim*, not an assertion that every executable on the router remains byte-identical on 2026-10-31. A new *read-only* current-state inventory and checksum comparison will be needed before declaring a baseline refreshed. Do not overwrite a known-good archived snapshot; create a new date/generation with clear provenance.
2. **Runtime config:** live `/opt/etc/xray/config.json` and `config.pending.json` intentionally excluded because of VPN provider credentials and identifiers. Existing known config checksum and structural notes are in `docs/production/2026-10-30-inventory.md`; do not store raw VLESS UUIDs, subscription URLs or tokens in GitHub. A synthetic/redacted schema template and offline generation validation remain to be implemented.
3. **Router environment:** Xray binary archive checksum/signature, Entware package/lock list, firmware and kernel, libraries, mounted filesystem and exact ownership/permissions are not captured as a reproducible build. Git modes 100755/100644 do not preserve 0700/0600 or user/group.
4. **Live traffic policy:** runtime `iptables` chains, route table 100, `ip rule`, TPROXY mark/PREROUTING, LAN bridge and IPv6/DNS escape coverage need sanitized read-only inventory and an isolated test strategy. Sources of `S98xray-wifi`, kill-switch and watchdog are present but do not prove current kernel state.
5. **Service ordering:** actual cron's selected lines and SHA256 are documented in `xray/production/README.md`; not all system timers/supervisor runtime state are frozen. Xray `S97xray` restarts via `killall`, so a blue-green production transition cannot be inferred safe from the lab.
6. **Adjacent service changed after snapshot:** on **2026-10-31** `/opt/telegram-ai/cloudflare_sync.py` was patched on the router to use local Xray SOCKS5 with remote DNS for Cloudflare. This file and `/opt/etc/init.d/S96cloudflare-sync` are **not included among the 63 Xray files**. MenttwoGPT source of truth is `ment2/menttwogpt`, branch `fix/cloudflare-memory-sync-socks5-20261031`, and the incident is indexed at `docs/incidents/2026-10-31-menttwogpt-memory-delivery-dependency.md`. Independent smoke success is confirmed; independent healthy 300-second supervisor cycle is still **unverified**. Do not claim GitHub and current production are byte-identical for this service until its source hash is compared.
7. **Other management components:** Agent and Cloudflare Worker belong to `ment2/keenetic-control`. Installed agent fingerprint, deployed Worker fingerprint and integration versions must be checked before a recovery release can depend on them.
8. **Private runtime state:** Telegram sessions, memory inbox, queue receipts, keys, network credentials and all backups containing secrets must stay in separately controlled encrypted storage, **never** in repository contents or GitHub Actions logs.

## Safe progression toward a usable staging and recovery kit

1. **Done: frozen source integrity and limited secret gate.** Run `python tools/verify_production_snapshot.py` in CI; fail on any modified, missing or unmanifested frozen file, or incorrect Git executable bit. This is GitHub state integrity, not live-router attestation.
2. **Next, repo-only:** build a separate `staging/` synthetic runtime specification (sanitized JSON for SOCKS/TPROXY, mock upstreams, service dependencies and firewall/route assertions). Integrate staged config regeneration, binary SHA pinning and deterministic fail-closed tests without any provider credential.
3. **Next, disposable runner:** test one stable test ingress with two real local Xray processes, old TCP session drain, failure and rollback, then add a separate UDP story and watchdog fencing. Never equate synthetic switcher with production TPROXY.
4. **After separate read-only access approval:** compare a new generation of production hashes, active listeners, port owners, supervisor scripts and sanitized cron/iptables/route metadata to the frozen baseline. Record deltas, not secrets; never replay old queued jobs or mutate Xray during inventory.
5. **After test and security gates:** document exact device/Entware dependencies, permission mapping, encrypted secret-rehydration process, verified known-good rollback images and a rehearsal on a spare device or equivalent kernel-capable system. Obtain explicit owner approval before any live cutover.
6. **Promotion still requires explicit authorization:** no GitHub branch merge, production deploy, router restart, cron/firewall/routing change, config application or kill-switch adjustment is authorized by this document.

## Commands for GitHub checkout only

```sh
python tools/verify_production_snapshot.py
python -m unittest discover -s tests -p 'test_*.py' -v
```

These commands are suitable for a disposable checkout. **Do not run historical files under `xray/production/opt/` as setup scripts**; many manage services, network state or firewall.

## Next explicit decision

The remaining work splits into two independent threads:

- **Repository-only staging** can continue immediately on the existing snapshot branch, without touching the router.
- **Current production parity** cannot be certified without separately authorized, strictly read-only checks on the current router and dependent services. After checks, compare SHA256 to a *new* dated manifest; retain this 2026-10-30 historical snapshot unchanged.

## CI addition: conservative current-source disclosure gate

`tools/check_snapshot_secrets.py` scans only the 63 frozen source files for high-confidence indicators such as an embedded private key, fully formed VLESS credential URI, GitHub/OpenAI-like token, or URL with inline password. It reports **only file path and detector type** on failure, never the matching value. Six isolated synthetic tests validate positive/negative cases. **CI 41189579857 SUCCESS: 131/131 tests; 63/63 frozen SHA256/mode checks; 63 files passed current-source secret heuristics.** This is not a full secret or Git-history audit. Before any publication/merge, separately scan all Git commit objects and review false negatives under an approved security procedure.
