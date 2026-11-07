#!/usr/bin/env bash
# RC41 disposable-only pinned upstream Xray source + private UDP worker
# test binary. No production files, no remote router commands.
set -euo pipefail
test "${GITHUB_ACTIONS:-}" = true
: "${RUNNER_TEMP:?}"
W="$RUNNER_TEMP/rc41-private-worker"
test ! -e "$W"
mkdir -p "$W"
git clone --quiet --depth 1 --branch v26.2.6 --single-branch https://github.com/XTLS/Xray-core.git "$W/xray-core"
cd "$W/xray-core"
test "$(git rev-parse HEAD)" = 12ee51e4bb1d02ece4ef4b7114efa2bcdc130995
test "$(git hash-object app/proxyman/inbound/worker.go)" = ef454d21195e2df878cd129f907dfaa65f7cdff0
test "$(git hash-object app/proxyman/command/command.proto)" = 71f8f0dcf0e9ae83204550aa9e02eba8384cb6b0
test "$(git hash-object app/stats/command/command.proto)" = 9c3f9131d087a6cd5c831a5ff708d93351b865f2
test "$(git hash-object app/router/command/command.proto)" = 22ae95b9844039f7460d1a5db5bfc54aa251487e
test "$(git hash-object proxy/dokodemo/dokodemo.go)" = e56363db0a8dd0b059b0bf705067d6c65ed0b6aa
echo RC41_PINNED_UPSTREAM_XRAY_26_2_6_SHA_VERIFIED
cp "$GITHUB_WORKSPACE/xray/lab/rc41_pinned_xray_worker_instrumented_test.go" app/proxyman/inbound/rc41_private_worker_instrumented_test.go
# Go dependency resolution/compilation may access public module repos, but
# it is in an ephemeral runner. No packet test runs until network namespace.
export GOPROXY=https://proxy.golang.org,direct
export GOTOOLCHAIN=auto
export GOMAXPROCS=2
timeout --signal=TERM 500s go test -c -o "$W/rc41_inbound.test" ./app/proxyman/inbound
test -s "$W/rc41_inbound.test"
chmod 755 "$W/rc41_inbound.test"
# Runner temp parents may be inaccessible to unprivileged UID65534.
# Stage only the built, non-secret test executable under ephemeral /tmp.
E="$(mktemp -d /tmp/rc41-private-exec.XXXXXXXX)"
chmod 755 "$E"
install -m 755 "$W/rc41_inbound.test" "$E/rc41_inbound.test"
echo RC41_UPSTREAM_REAL_GO_PACKAGE_COMPILED_TEST_ONLY
# Only the following execution path carries real socket packets. Isolate
# network namespace; no route, external NIC, proxy, or physical router.
sudo unshare --net -- bash -c '
 set -euo pipefail
 test -z "$(ip -4 route show default)"
 test "$(ip -o link show | wc -l)" -eq 1
 ip link set lo up
 test -z "$(ip -4 route show default)"
 echo RC41_ISOLATED_KERNEL_LOOPBACK_NO_DEFAULT_ROUTE
 exec setpriv --reuid=65534 --regid=65534 --clear-groups \
   timeout --signal=TERM 150s "$1/rc41_inbound.test" -test.v -test.count=1 -test.run "^TestRC41"
' rc41 "$E" | tee "$W/real-private-worker.log"
grep -Fq RC41_REAL_XRAY_SOURCE_PRIVATE_ACTIVE_CONN_A_IDLE_REUSED_B_CREATED "$W/real-private-worker.log"
grep -Fq RC41_REAL_LINUX_CLIENT_UDP_SOCKET_COOKIES_WITNESSED "$W/real-private-worker.log"
grep -Fq RC41_PRIVATE_SNAPSHOT_RWLOCK_IS_NOT_KERNEL_INGRESS_FREEZE "$W/real-private-worker.log"
grep -Fq RC41_PRIVATE_XRAY_WORKER_120S_CLEANER_TEST_ONLY "$W/real-private-worker.log"
grep -Fq RC41_UNINSTRUMENTED_LEGACY_PROCESS_NOT_INSPECTED_OR_MODIFIED "$W/real-private-worker.log"
grep -Fq RC41_HARD_NO_GO_PRODUCTION_NO_ATOMIC_OWNER_COMMIT_OR_PHYSICAL_FENCING "$W/real-private-worker.log"
echo RC41_PASS_REAL_INPROCESS_XRAY_WORKER_PACKET_AND_PRIVATE_MAP_BOUNDED_ONLY
echo RC41_HARD_NO_GO_NO_EXTERNAL_LEGACY_INVENTORY_KERNEL_FREEZE_ROOT_FENCE_USB_RESCUE
