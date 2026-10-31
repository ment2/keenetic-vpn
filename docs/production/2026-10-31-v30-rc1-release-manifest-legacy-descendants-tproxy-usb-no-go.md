# Keenetic Xray v30 RC1 release bundle: exact pins, legacy migration NO-GO, kernel TPROXY and USB fault matrix

Date: **2026-10-31**. Repository **`ment2/keenetic-vpn`**, only branch **`feature/xray-v30-stable-tcp-ingress-lab-20261031`**. This report is NOT approval to deploy or execute a trial on Keenetic.

## Verified latest CI

- [Offline source contracts run **41209378306**](https://github.com/ment2/keenetic-vpn/actions/runs/41209378306), **SUCCESS, 345/345 tests** on head `6f547cf548dd669a4fff6d61036e8e3ba8d4483e`. Checks exact versioned staged/archived hashes, shell sources, no-production contract, legacy process/cron/descendant blockers, real frozen five-file partial restore, USB backup loss and corruption, boot-like replay via fresh Python interpreter.
- [Native kernel TPROXY run **41209311676**](https://github.com/ment2/keenetic-vpn/actions/runs/41209311676), **SUCCESS** on `e1f8e9d27a42e237b618104afa26cdad0180e99e`. Three separate isolated Linux namespace runs (first full harness plus two repeat attempts) with real **native x86_64** Xray 26.2.6: IPv4 TCP+UDP transparent proxy through `mangle PREROUTING` + `fwmark 0x40000000/0x40000000` + table 100; after killing only disposable test Xray, TCP and UDP are blocked by isolated fail-closed policy. **NOT** MIPS32LE TPROXY.
- Previous [real MIPS32LE QEMU run **41207498806**](https://github.com/ment2/keenetic-vpn/actions/runs/41207498806) **SUCCESS**: two actual Xray 26.2.6 MIPS32LE processes; SOCKS5 TCP and UDP ASSOCIATE restored by independent secondary guardian after controller/primary guardian crashes, including mid-rollback. This is loopback SOCKS, not transparent routing.

## Versioned manifest and exact candidate hashes

Manifest: `xray/staging/v30-release-manifest-v1.json`, commit `cbead0f1b61148599343d5eb7041256016228c6c`. Source integrity validator `xray/lab/v30_release_manifest_contract.py` verifies all nine staged SHA256 plus Git blob SHA1 and byte sizes, and exactly five archived original SHA256 values against `xray/production/MANIFEST.sha256` with frozen mode `100755`. Every missing gate or mismatched file blocks validation.

| Component | Candidate SHA256 | Frozen original SHA256 |
| --- | --- | --- |
| `S97xray` | `de4b130dc31be1129eee52acea95a90120b08454a19b83fbec680a34d782e228` | `87ea1dc13a9be95d57c0595d7a7f13b03fe97bd56ab1f144a3c94d57cc588d5d` |
| `S98xray-wifi` | `7caad6f2a56fd56ec9aa3d4082b2fca10cd866173d082a505fc74c0d114b604a` | `6742e5e7f2a2bd41b85e9975371e7c46e66f0cfc6f5f843bf2c5dc1434c53601` |
| `S99xray-watchdog` | `bb80fd8858057e88a58a200f4a4e60c56df28c34cff7331c809a2a17d363ccaa` | `e8423e15ed2cf4d3662e5725d27d6e58bd08bbdd807b47fcabe30391ac4c738b` |
| `xray-watchdog.sh` | `8b0dd73ba30d81657d8851eff5bc2447627cd3357589fc3ab5022c1a4dea03d3` | `dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08` |
| `xray-wifi-rules.sh` | `b7d31628129490e5b521de5a519b2e51b823879f35956022dd1e310d09b136cb` | `ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef` |
| `v30_supervisor_core.py` | `2af080991a194af1372b3fa90b70bd40a2af979109866ac373df220c46d44379` | N/A (new) |
| `v30_supervisor_service.py` | `0a4232d166f63bf648c7e3d72bb393db2f356584e6e851e855e2caaf1c65acfc` | N/A (new) |
| `v30_cooperative_canary.py` | `472a7222d1006fc9de290b7d9e6705a24ddb3f8a4de357f1805f7536cee9f1c1` | N/A (new) |
| `v30_first_cutover_canary.py` **old installed pin** | `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203` | N/A (must stay unchanged) |

This is an **RC1 source manifest, not a production deployment bundle**. It records `STAGING_ONLY_NOT_FOR_DEPLOY`, `deployment_authorized=false`, `production_trial_authorized=false`, default `deny`, and eight required live-release gates. Source SHA256 values were computed from exact fetched UTF-8 GitHub bytes and independently checked in CI using `hashlib` and Git's blob SHA1 format, including the separately known old-canary SHA.

## Legacy migration/descendant release gate

New `xray/lab/v30_legacy_descendant_migration_gate.py` and `tests/test_xray_v30_legacy_descendant_migration_gate.py` model exact PID/start-ticks identity, full parent/child trees, reparented legacy writers, cron-initiated `S97xray restart`, stopped-parent/live-child `killall xray`, and S98 `xray-wifi-rules.sh` `iptables` descendants. All produce **NO_PRODUCTION_CUTOVER** until separately proven drained under a cooperative shared lock and all entrypoints migrated. Synthetic positive inventory is explicitly `OFFLINE_CONTRACT_ONLY` with `production_cutover_authorized=false`; no router commands embedded.

**A stopped watchdog or S98 parent does NOT fence existing descendants.** Neither a broad goal approval nor green offline test substitutes for real root process inventory, safe staged migration, pidfd kernel checks, and precise service replacement approval.

## Simulated reboot and USB failure

New `xray/lab/v30_reboot_usb_fault_matrix.py` uses copies of actual frozen and staged five scripts. It kills a staged installer after 2/5 source replacements. If the archived backup folder vanishes (simulated USB unmount), independent recovery **fails closed and changes zero additional active bytes**. If the backup returns with a corrupted `S97xray` file, SHA validation also **blocks without writes**. After restoring identical verified backup bytes, a **fresh Python interpreter** replays the fsynced transaction and restores 5/5 archived SHA256 values and protected modes.

This proves **process-restart replay with durable simulated files**, NOT the router reboot/power-loss or Entware USB physical-removal recovery. With a genuinely unavailable USB installation, automation may be unavailable; an out-of-USB persistent rescue mechanism would be necessary for production release.

## Evidence and practical blockers

1. **Kernel pidfd unknown.** Earlier single authorized `router_status` job `4861e527-fa5c-43da-a84d-a7f5672448b8` returned ONLINE and Python 3.13.9, but prior one read `/proc/sys/kernel/osrelease` job `6e65e44d-3f82-4ba9-89a5-f5ac64e47d3b` failed `operation_failed`. No duplicate or substitute router jobs in this turn, no blocked tool workaround. The staged pidfd signal helper explicitly fails closed if pidfd is unsupported.
2. **Original live sources unfenced.** Legacy S97 currently uses global `killall xray`; legacy S98 may mutate routes/iptables from spawned descendants. New broker `flock` cannot retroactively fence these live independent writers. Need exact reviewed two-phase, service/cron/child-tree migration with independent recovery.
3. **Installed canary incompatible.** It pins old S97/S98/S99/watchdog hashes and uses a different transaction lock. The new staging-only `v30_cooperative_canary.py` deliberately has no `--trial`, only offline plan, until real integration is implemented and proven.
4. **Transparent routing disparity.** Native x86_64 namespace TPROXY TCP+UDP passed three runs, while MIPS32LE QEMU tests verify SOCKS TCP/UDP. Linux QEMU user-mode and real Keenetic MIPS kernel TPROXY are NOT interchangeable. Real TPROXY MIPS, real VPN/VLESS, IPv6/DNS leak, fail-closed physical host kernel remain unproven.
5. **Physical USB/reboot.** Only Linux process and disposable backup simulations passed, not a hardware reboot or storage removal recovery. No production release until a reliable out-of-band rescue path and persistence are established.
6. **Explicit scope.** User requested feature-only work and separate exact-file review before production staging; no merge/deploy, no live trial or stop/start on Keenetic.

## Final verified disposition

- **PASS:** manifest 9/9 exact staged hashes + frozen 5/5 archive, independent guardian failover on real MIPS QEMU TCP/UDP SOCKS, native x86 kernel TPROXY TCP/UDP three runs including fail-closed, interrupted five-file update, lost/corrupt USB-backup refusal, fresh-process SHA256 restore, legacy process-tree NO-GO gate, total 345/345 unit tests.
- **NO-GO PRODUCTION:** no verified Keenetic pidfd, no proof all actual legacy descendants/cron fenced, no deployed common-lock release, no physical USB/reboot or MIPS native kernel TPROXY proof.
- **No Keenetic job created in this turn**; no changes to Xray, config, cron, kernel firewall, routes, kill-switch, Cloudflare, main/snapshot branches. No merge/deploy.

**Next action:** continue isolated runbook and generation of exact, independently reviewable preinstall/rollback package. Only after a verified supported read-only pidfd and current live process/cron inventory plus full recovery proof can any production change be separately proposed.
