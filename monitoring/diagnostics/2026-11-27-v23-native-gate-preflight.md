# Geo-independent v23 — native gate preflight, 27 November 2026

**HARD NO-GO for production installation.** No production writes, changes
to permissions, service signals, cron edits, module loads, reboots or
firewall/route modifications. Only read-only Keenetic inventory performed.

## Provenance
The corrected evidence archive at commit
4b18e57d4c57d087d80c896bb8a43c86b548f7a7 was opened and all 17 manifest
entries verified byte-for-byte, including hidden workflow files. The
older local archive is incomplete and is not the basis of this work.
Accepted builder SHA256 9e22a9b68a2e0fd5b1e66499778662419bc56cd8af491f229401269be2456ecd
unchanged. Prior physical 10/10 and Xray -test PASS (92.7 s), IPv4/IPv6
reference lab and crash tests not repeated as new physical trials.

## Native read-only evidence
Job e9dbd8d1-255b-4f73-a2c8-32f8a874d34b exit 0:
/opt real directory, ext4 rw, same device for /opt/bin, /opt/etc/xray,
/opt/etc/vpn-monitor, /opt/tmp and monitor staging; root filesystem
squashfs ro, /tmp tmpfs rw. Python 3.13.9 supports O_NOFOLLOW and dir_fd
rename. This is capability evidence, not proof of actual USB power-loss
durability. The updater, wrapper and legacy S97/S98 sources were observed:
updater 00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf,
wrapper c63c0f171cda5b5f3150731e0706784b66977b256d737856edfcce15fba223c8,
S97 87ea1dc13a9be95d57c0595d7a7f13b03fe97bd56ab1f144a3c94d57cc588d5d,
S98 6742e5e7f2a2bd41b85e9975371e7c46e66f0cfc6f5f843bf2c5dc1434c53601.
Crontab SHA256 fb3f3871bcf79a83739f14dbaa8817b262bedb1c1cd0907b4594f709cd6da6c3;
legacy updater and OpenAI collector every 15 minutes. No RC2 schedule observed.

Job eab30a02-1538-4205-bcbd-98eaf32631aa exit 0:
/opt/tmp mode 0777, root-owned, no sticky bit. Lock mode 0600, single link,
inode 1280 in preceding observation. A process with write permission to
the parent can unlink or rename the lock pathname despite file mode.
No attack was attempted or observed; inode checks alone do not eliminate
this potential split-lock race. The candidate refuses a writable parent,
including sticky world-writable parents, by conservative policy.
Persistent release journal directory absent. /opt/var/lib and rc2-stage
mode 0700. Boot ID syntactically valid.

Observed live legacy actors: watchdog PID 720/start ticks 4462, VLESS
collector PID 773/start ticks 4525, S98 PID 23941/start ticks 8326634.
These are observations, not authority to signal a process. Watchdog calls
S97, S97 uses killall xray; S98 periodically invokes rules writer.
A separate xray-safe-v23.sh references updater; other backup/migration
scripts exist. Presence alone does not establish active invocation.
Current legacy cron and these independent actors do not enforce the
new journal. Do not equate lock ownership with full privileged fencing.

## Native adapter and simulated boot
xray/candidates/geo-independent-v23/native_gate.py supplies fixed-path
read-only check mode, mountinfo parsing, source/pin/ownership checks,
protected lock parent requirement and boot continuity check. It cannot
install or execute a production wrapper from its CLI. It has not been
deployed or run on Keenetic; inventory independently demonstrates that
its strict lock-parent preflight would reject the current layout.
The boot_decision function is a proposed admission contract, not an
installed boot service. It blocks missing lock, unknown/changed boot,
unfenced legacy actors, persistent running receipt and unknown generation.
No automatic receipt clear after reboot. Prepared/rollback phase
requires actual journal/backup/CAS validation under lock before recovery.
The existing disposable transaction is reused for recovery tests.
RC2 runner constructs exact refresh + probe argv with reviewed pins,
skips probe after refresh failure, and avoids old rc2_cycle idle check
that would conflict with the held lock. It is an injected runner
contract; no native monitor schedule integration or execution claimed.
CI 46026734626 SUCCESS 231/231, 12 new tests including simulated reboot
with new lock inode and preserved journal/receipt. Actual power failure
and boot ordering remain unproven.

## Change request for next separately authorized stage
Prefer a dedicated persistent root-only lock directory under /opt/etc/xray
rather than chmod of shared /opt/tmp. No change executed. Prepare exact
native bootstrap and actor coordination plan: prove legacy updater idle
and no descendants, preserve management/recovery path, reconcile old
cron, watchdog, S97/S98 and both collectors, ensure all participating
entrypoints use the same protected lock and gate before any new builder
or pin is installed. Never have two independently authoritative lock
inodes during transition. Verify legacy lock identity and schedule,
backup exact cron and all changed files/modes, abort on unexpected
writers. The old lock must not be blindly unlinked. Full root actor
fencing cannot be guaranteed by directory permissions or advisory flock.
After a reboot, validate mount, persistent journal and lock identity,
current boot and actors; reaccept explicitly rather than automatically
launching cron on an old receipt. Rehearse bootstrap/rollback in
disposable environment, then separately authorize physical acceptance
including actual IPv4/IPv6 TCP/UDP/DNS fail-closed and recovery. No
production outage or deployment is authorized by this report.
