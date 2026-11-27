# Geo-independent v23 — shared lock migration, 27 November 2026

Status: HARD NO-GO for production. No Keenetic tasks, writes, service
signals, permission changes, cron changes or firewall/route changes in
this phase. No repeated physical candidate or packet trials.

## Basis
Opened /Keenetic/Xray/2026-11-27-v23-native-gate-evidence.zip from the
available downloaded archive. All 20 SHA256SUMS entries match and COMMIT
is 57a422dc2060715b08c9d078d26d36e4dc729eb5. Prior CI 46026859953
232/232, physical 10/10 92.7 s Xray -test PASS and IPv4/IPv6 reference
labs retained. Actual /opt/tmp is 0777 without sticky bit; legacy
root processes remain independently callable. Prior audit source is
monitoring/diagnostics/2026-11-27-v23-native-gate-preflight.md.

## Implementation
xray/candidates/geo-independent-v23/lock_migration.py is fixture-only.
No native CLI or production migration capability. It uses a protected
control lock for serializing cooperative actor admission and migration.
The existing DATA lock inode is preserved across same-filesystem move
from opt/tmp/xray-update.lock to opt/etc/xray/locks/xray-update.lock.
The control lock is not a second authority for data work. Kernel
renameat2(RENAME_NOREPLACE) refuses existing destination, with no unsafe
fallback. Its native MIPS/Linux 4.9 libc/filesystem availability must
be tested separately. Both parent directories are fsynced. Data lock
is never created, copied, truncated, hardlinked or unlinked by migration.
Exact identity checked before and after each move. Unknown, replaced,
duplicate or absent path fails closed. Crash between prepared and
committed reverts to the original path and inode; committed stays
protected; rollback is durable and resumable. Restore to unsafe old
path is a laboratory scenario, not recommended native rollback.
A simulated boot change blocks actor admission until explicit fixture
reacceptance; an unresolved actor receipt blocks even then. Never
automatically recreate a missing lock. Actual USB power failure, device
number change after reboot and durable boot ordering remain unproven.

Eight synthetic actor descriptors (cron/manual updater/watchdog/S97/S98/
legacy VLESS/legacy OpenAI/RC2 probe) must match expected fixture hashes.
A fixture drained assertion is NOT a native process inventory or fencing
witness. A durable actor-running receipt fences ambiguous completion.
Integration with existing release_gate.Gate uses the protected control
lock first, and Gate acquires the same moved data inode once; an optional
expected inode is enforced at acquisition. Wrapper-owned S97 is part
of the outer operation, not a nested flock. Generic actor admission
requires known committed release pair when a source journal exists.
Both receipt paths block other cooperating actors and recovery. Source
pair rollback must finish before lock-path rollback. This is a tested
fixture contract, not installed watchdog/S97/S98/RC2 code.

## Evidence and limits
Initial CI 46027471055 SUCCESS 249/249 (17 new tests). Integration CI
46027688871 failed one test because two imports produce distinct Blocked
exception classes; actual prepared-state refusal occurred before callback.
Corrected test asserts correct class and no callback/receipt. Final
source/test commit c688ff4f4ab88bb3cc85d6e3637f71367c114d5e.
Final CI 46027796975 SUCCESS 255/255 (23 new tests relative to 232).
Tests use real flock, previously opened FD contending with relocated
path, real SIGKILL before and after rename/commit and rollback, simulated
boot, no-replace destination, missing lock, unknown actor and persistent
receipt. Integrated source transaction, cron, monitor and actor gates
tested with synthetic files/commands, not native services.

Critical negative witness: an unmodified old actor CAN recreate an
independent inode at the abandoned world-writable pathname and obtain
flock even while the migrated gate holds the original inode. The
cooperating gate detects both paths and refuses future operations or
leaves receipt at final readback; it cannot undo the already executed
ungated action. This proves migration is NOT safe until every native
legacy entrypoint and descendant is fenced. No claim of arbitrary
privileged writer confinement. A hardlink alias is not used (prior
release gate requires st_nlink=1; alias in writable parent is unsafe).
An old FD already opened before move cannot bypass the data lock but
can still run ungated after release if its actor is not drained.

## Native bootstrap change request (not executed)
1. Reconcile actual installed sources and call graph: cron, manual
   xray-safe-v23.sh, safe-hourly, S97, S98/rules writer, watchdog and
   old monitor collectors, init/boot order, all descendants and
   rc.unslung paths. Verify exact source hashes, process boot/PID/
   start-ticks/argv/ancestry and no unknown active writers. No stale
   PID-file authority or killall. Inventory alone is not fencing.
2. Develop native gate-aware entrypoints and demonstrate their actual
   negative controls in disposable equivalents. All top-level operations
   enter one protected control admission and one data lock; delegated
   S97 invoked by wrapper/watchdog must use a verified ownership handoff
   rather than recursively acquire lock or trust arbitrary environment
   marker. S97 legacy killall must not affect probe children. S98
   long-lived watcher must acquire gate per bounded rule mutation,
   not hold forever or bypass during a transaction. Watchdog check and
   any repair must be separately guarded; old VLESS/OpenAI probe fleets
   and RC2 refresh/probe mutually excluded; publish-only monitor
   keeps its monitor lock and must not advertise stale freshness.
3. Separately approve short maintenance bootstrap with independent
   recovery path. Protect persistent control/state directory (0700).
   Gate-aware wrappers and boot guards must be in place while old
   updater/pins remain unchanged, and old scheduler/entrypoints fenced
   before any data-lock move. Prove no pending/in-flight old invocation
   or child, no unsynchronized new ones, and fresh boot/source/cron
   CAS. Do not rely solely on advisory flock for arbitrary root actors.
   Preserve old scheduler/config/script bytes privately; no blanket
   permission change of /opt/tmp, no lock unlink.
4. Verify native renameat2 NOREPLACE and fsync on disposable files on
   the same actual EXT4 mount, secure parents, persistent mount identity,
   exact old inode and absent destination. Test actual adapter in
   native disposable directories first. Acquire control then old data
   lock, durable prepared journal, move same inode, fsync both parents,
   verify single authoritative protected path, commit. If old path
   reappears, block; do not delete foreign file or select a winner.
   Validate actual boot recovery and old-pair scheduled cycles through
   the new gate before authorizing any source-pair update. Reboot after
   receipt requires manual reconciliation; no automatic receipt clear.
5. Install new builder/pin only in separately accepted transaction
   under same protected gate. Actual no-leak TCP/UDP/DNS IPv4/IPv6 and
   physical runtime rollback remain separate maintenance gates. Do not
   stop production merely to force negative proof without authorization.
6. Prefer rollback of updater/pins while RETAINING protected lock and
   gated actors. Only if separately necessary, revert lock location
   using durable rollback while all actors still fenced and no receipt/
   release journal; verify same inode and exact old pair, then separately
   authorize restoration of old cron. Returning to 0777 old directory
   reintroduces known weakness. No automatic fallback to legacy path.
