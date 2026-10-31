#!/usr/bin/env bash
# DISPOSABLE GITHUB ACTIONS ONLY. Real IPv4 kernel TPROXY TCP/UDP smoke, no router.
set -euo pipefail
if [[ ( "${1:-}" != "--run" && "${1:-}" != "--native-run" ) || "${GITHUB_ACTIONS:-}" != "true" || -z "${RUNNER_TEMP:-}" ]]; then
  echo "REFUSE: requires --run/--native-run, GITHUB_ACTIONS=true and pinned Xray binary" >&2
  exit 2
fi
if [[ "${1:-}" == "--native-run" ]]; then
  [[ -n "${XRAY_NATIVE_BINARY:-}" ]] || exit 2
  xray_cmd=("$XRAY_NATIVE_BINARY")
else
  [[ -n "${XRAY_MIPS_BINARY:-}" ]] || exit 2
  xray_cmd=(qemu-mipsel "$XRAY_MIPS_BINARY")
fi
if [[ -e /opt/etc/xray/config.json || -e /opt/etc/init.d/S97xray ]]; then
  echo "REFUSE: production Entware detected" >&2
  exit 2
fi
set -x
tmp="$(mktemp -d "${RUNNER_TEMP}/v30-rc10-tproxy.XXXXXX")"
chmod 755 "$tmp"  # allow only read access to non-root Xray config, disposable path
xray_pid="" ; server_pid=""
cleanup() {
  status=$?
  set +e
  if [[ "$status" -ne 0 ]]; then
    echo 'NETNS_DIAG: FAILURE before cleanup (synthetic fixtures only)'
    sudo ip netns exec xv10g iptables -t mangle -vnL PREROUTING
    sudo ip netns exec xv10g iptables -t mangle -vnL XRAY_RC10_LAB
    sudo ip netns exec xv10g iptables -vnL FORWARD
    sudo ip netns exec xv10g ip rule show
    sudo ip netns exec xv10g ip route show table 100
    sudo ip netns exec xv10g ss -lntup
    cat "$tmp/xray.log" "$tmp/server.log" 2>/dev/null
  fi
  if [[ -n "$xray_pid" ]] && [[ -f "/proc/$xray_pid/cmdline" ]] &&
     tr '\0' ' ' <"/proc/$xray_pid/cmdline" | grep -Eq 'qemu-mipsel|/xray( |$)'; then
    sudo kill "$xray_pid" 2>/dev/null
  fi
  if [[ -n "$server_pid" ]] && [[ -f "/proc/$server_pid/cmdline" ]] &&
     tr '\0' ' ' <"/proc/$server_pid/cmdline" | grep -q 'xray_v30_kernel_tproxy_echo'; then
    sudo kill "$server_pid" 2>/dev/null
  fi
  sudo ip netns del xv10c 2>/dev/null
  sudo ip netns del xv10g 2>/dev/null
  sudo ip netns del xv10s 2>/dev/null
  rm -rf "$tmp"
}
trap cleanup EXIT
for ns in xv10c xv10g xv10s; do
  sudo ip netns add "$ns"
  sudo ip -n "$ns" link set lo up
done
sudo ip link add cv30 type veth peer name gv30a
sudo ip link set cv30 netns xv10c
sudo ip link set gv30a netns xv10g
sudo ip link add gv30b type veth peer name sv30
sudo ip link set gv30b netns xv10g
sudo ip link set sv30 netns xv10s
sudo ip -n xv10c addr add 10.199.71.2/24 dev cv30
sudo ip -n xv10g addr add 10.199.71.1/24 dev gv30a
sudo ip -n xv10g addr add 10.199.72.1/24 dev gv30b
sudo ip -n xv10s addr add 10.199.72.2/24 dev sv30
for pair in "xv10c cv30" "xv10g gv30a" "xv10g gv30b" "xv10s sv30"; do
  read -r ns link <<< "$pair"
  sudo ip -n "$ns" link set "$link" up
done
sudo ip -n xv10c route add 10.199.72.0/24 via 10.199.71.1
sudo ip -n xv10s route add 10.199.71.0/24 via 10.199.72.1
# No Internet default route in any lab namespace.
sudo ip netns exec xv10g sysctl -qw net.ipv4.ip_forward=1
# Independent native host kernel control: IP_TRANSPARENT must work here.
sudo ip netns exec xv10g python3 -c 'import socket; s=socket.socket(); s.setsockopt(socket.SOL_IP,19,1); print("KERNEL_TPROXY: native IP_TRANSPARENT setsockopt supported",flush=True); s.close()'
sudo ip netns exec xv10g iptables -P FORWARD DROP
sudo ip -n xv10g rule add fwmark 0x40000000/0x40000000 table 100 priority 20000
sudo ip -n xv10g route add local 0.0.0.0/0 dev lo table 100
sudo ip netns exec xv10g iptables -t mangle -N XRAY_RC10_LAB
for proto in tcp udp; do
  sudo ip netns exec xv10g iptables -t mangle -A PREROUTING -i gv30a -d 10.199.72.2 -p "$proto" --dport 19090 -j XRAY_RC10_LAB
  sudo ip netns exec xv10g iptables -t mangle -A XRAY_RC10_LAB -p "$proto" -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
done
cat > "$tmp/config.json" <<'JSON'
{
  "log": {"loglevel":"debug"},
  "inbounds": [{
    "tag":"lab-tproxy", "listen":"0.0.0.0", "port":12345,
    "protocol":"dokodemo-door",
    "settings":{"network":"tcp,udp","followRedirect":true},
    "streamSettings":{"sockopt":{"tproxy":"tproxy"}}
  }],
  "outbounds":[
    {"tag":"lab-only-destination","protocol":"freedom","settings":{}},
    {"tag":"blocked","protocol":"blackhole","settings":{}}
  ],
  "routing":{"rules":[
    {"type":"field","inboundTag":["lab-tproxy"],"outboundTag":"lab-only-destination"},
    {"type":"field","port":"0-65535","outboundTag":"blocked"}
  ]}
}
JSON
# The test server is the *only* routable destination and is also the
# Xray's original destination; no Internet path exists.
sudo ip netns exec xv10g "${xray_cmd[@]}" run -test -config "$tmp/config.json"
sudo ip netns exec xv10s bash -c 'echo "$$" > "$1"; exec python3 -u -m xray.lab.xray_v30_kernel_tproxy_echo server' _ "$tmp/server.pid" >"$tmp/server.log" 2>&1 &
sudo ip netns exec xv10g bash -c 'echo "$" > "$1"; shift; exec "$@"' _ "$tmp/xray.pid" \
  setpriv --reuid=65534 --regid=65534 --clear-groups \
    --inh-caps +net_raw --ambient-caps +net_raw --bounding-set -all,+net_raw \
    --no-new-privs "${xray_cmd[@]}" run -config "$tmp/config.json" >"$tmp/xray.log" 2>&1 &
for _ in $(seq 1 30); do
  if [[ -s "$tmp/server.pid" && -s "$tmp/xray.pid" ]] &&
     sudo ip netns exec xv10g ss -lnt | grep -q ':12345'; then
    break
  fi
  sleep 1
done
[[ -s "$tmp/server.pid" && -s "$tmp/xray.pid" ]]
server_pid="$(cat "$tmp/server.pid")" ; xray_pid="$(cat "$tmp/xray.pid")"
# Exact process identity/privilege assertions before and after packets.
test "$(awk '/^Uid:/ {print $2}' "/proc/$xray_pid/status")" = 65534
test "$(awk '/^CapEff:/ {print $2}' "/proc/$xray_pid/status")" = 0000000000002000
test "$(awk '/^NoNewPrivs:/ {print $2}' "/proc/$xray_pid/status")" = 1
START_TICKS="$(awk '{print $22}' "/proc/$xray_pid/stat")"
test -n "$START_TICKS"
echo "RC10_TPROXY: REAL_XRAY_UID65534_ONLY_CAP_NET_RAW_STARTTICKS_VERIFIED"
sudo ip netns exec xv10c python3 -m xray.lab.xray_v30_kernel_tproxy_echo client
# Kill ONLY this disposable test instance and assert the namespace's
# FORWARD=DROP prevents fallback to original test destination.
sudo kill "$xray_pid"
for _ in $(seq 1 30); do
  if ! sudo kill -0 "$xray_pid" 2>/dev/null; then break; fi
  sleep 0.1
done
sudo ip netns exec xv10c python3 -m xray.lab.xray_v30_kernel_tproxy_echo blocked
if [ -e "/proc/$xray_pid/stat" ]; then
  AFTER_TICKS="$(awk '{print $22}' "/proc/$xray_pid/stat" 2>/dev/null)"
  [ "$AFTER_TICKS" = "$START_TICKS" ] || { echo "RC10_TPROXY: FAIL PID reuse ambiguity"; exit 1; }
fi
echo "RC10_TPROXY: REAL_TCP_UDP_PACKET_INTERCEPTION_WITH_CAP_NET_RAW_AND_DEAD_CHILD_BLOCKED_PASS"
echo "KERNEL_TPROXY: PASS disposable namespaces, no production kernel change"
