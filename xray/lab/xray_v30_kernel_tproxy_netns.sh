#!/usr/bin/env bash
# DISPOSABLE GITHUB ACTIONS ONLY. Real IPv4 kernel TPROXY TCP/UDP smoke, no router.
set -euo pipefail
if [[ "${1:-}" != "--run" || "${GITHUB_ACTIONS:-}" != "true" || -z "${RUNNER_TEMP:-}" || -z "${XRAY_MIPS_BINARY:-}" ]]; then
  echo "REFUSE: requires --run, GITHUB_ACTIONS=true and pinned Xray binary" >&2
  exit 2
fi
if [[ -e /opt/etc/xray/config.json || -e /opt/etc/init.d/S97xray ]]; then
  echo "REFUSE: production Entware detected" >&2
  exit 2
fi
set -x
tmp="$(mktemp -d "${RUNNER_TEMP}/v30-tproxy.XXXXXX")"
xray_pid="" ; server_pid=""
cleanup() {
  set +e
  if [[ -n "$xray_pid" ]] && [[ -f "/proc/$xray_pid/cmdline" ]] &&
     tr '\0' ' ' <"/proc/$xray_pid/cmdline" | grep -q 'qemu-mipsel'; then
    sudo kill "$xray_pid" 2>/dev/null
  fi
  if [[ -n "$server_pid" ]] && [[ -f "/proc/$server_pid/cmdline" ]] &&
     tr '\0' ' ' <"/proc/$server_pid/cmdline" | grep -q 'xray_v30_kernel_tproxy_echo'; then
    sudo kill "$server_pid" 2>/dev/null
  fi
  sudo ip netns del xv30c 2>/dev/null
  sudo ip netns del xv30g 2>/dev/null
  sudo ip netns del xv30s 2>/dev/null
  rm -rf "$tmp"
}
trap cleanup EXIT
for ns in xv30c xv30g xv30s; do
  sudo ip netns add "$ns"
  sudo ip -n "$ns" link set lo up
done
sudo ip link add cv30 type veth peer name gv30a
sudo ip link set cv30 netns xv30c
sudo ip link set gv30a netns xv30g
sudo ip link add gv30b type veth peer name sv30
sudo ip link set gv30b netns xv30g
sudo ip link set sv30 netns xv30s
sudo ip -n xv30c addr add 10.199.71.2/24 dev cv30
sudo ip -n xv30g addr add 10.199.71.1/24 dev gv30a
sudo ip -n xv30g addr add 10.199.72.1/24 dev gv30b
sudo ip -n xv30s addr add 10.199.72.2/24 dev sv30
for pair in "xv30c cv30" "xv30g gv30a" "xv30g gv30b" "xv30s sv30"; do
  read -r ns link <<< "$pair"
  sudo ip -n "$ns" link set "$link" up
done
sudo ip -n xv30c route add 10.199.72.0/24 via 10.199.71.1
sudo ip -n xv30s route add 10.199.71.0/24 via 10.199.72.1
# No Internet default route in any lab namespace.
sudo ip netns exec xv30g sysctl -qw net.ipv4.ip_forward=1
sudo ip netns exec xv30g iptables -P FORWARD DROP
sudo ip -n xv30g rule add fwmark 0x40000000/0x40000000 table 100 priority 20000
sudo ip -n xv30g route add local 0.0.0.0/0 dev lo table 100
sudo ip netns exec xv30g iptables -t mangle -N XRAY_V30_LAB
for proto in tcp udp; do
  sudo ip netns exec xv30g iptables -t mangle -A PREROUTING -i gv30a -d 10.199.72.2 -p "$proto" --dport 19090 -j XRAY_V30_LAB
  sudo ip netns exec xv30g iptables -t mangle -A XRAY_V30_LAB -p "$proto" -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
done
cat > "$tmp/config.json" <<'JSON'
{
  "log": {"loglevel":"warning"},
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
sudo ip netns exec xv30g qemu-mipsel "$XRAY_MIPS_BINARY" run -test -config "$tmp/config.json"
sudo ip netns exec xv30s bash -c 'echo "$$" > "$1"; exec python3 -u -m xray.lab.xray_v30_kernel_tproxy_echo server' _ "$tmp/server.pid" >"$tmp/server.log" 2>&1 &
sudo ip netns exec xv30g bash -c 'echo "$$" > "$1"; exec qemu-mipsel "$2" run -config "$3"' _ "$tmp/xray.pid" "$XRAY_MIPS_BINARY" "$tmp/config.json" >"$tmp/xray.log" 2>&1 &
for _ in $(seq 1 30); do
  if [[ -s "$tmp/server.pid" && -s "$tmp/xray.pid" ]] &&
     sudo ip netns exec xv30g ss -lnt | grep -q ':12345'; then
    break
  fi
  sleep 1
done
[[ -s "$tmp/server.pid" && -s "$tmp/xray.pid" ]]
server_pid="$(cat "$tmp/server.pid")" ; xray_pid="$(cat "$tmp/xray.pid")"
sudo ip netns exec xv30c python3 -m xray.lab.xray_v30_kernel_tproxy_echo client
# Kill ONLY this disposable test instance and assert the namespace's
# FORWARD=DROP prevents fallback to original test destination.
sudo kill "$xray_pid"
for _ in $(seq 1 30); do
  if ! sudo kill -0 "$xray_pid" 2>/dev/null; then break; fi
  sleep 0.1
done
sudo ip netns exec xv30c python3 -m xray.lab.xray_v30_kernel_tproxy_echo blocked
echo "KERNEL_TPROXY: PASS disposable namespaces, no production kernel change"
