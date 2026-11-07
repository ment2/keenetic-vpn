#!/usr/bin/env bash
set -euo pipefail
test "$GITHUB_ACTIONS" = true
test "$1" = --inside
W="$2";cd "$3"
test "$(ip -o link show | wc -l)" -eq 1
test -z "$(ip -4 route show default)"
ip link set lo up
unshare --net -- sleep 60 & other=$!
server=
trap 'test -z "$server" || kill "$server" 2>/dev/null || :;kill "$other" 2>/dev/null || :;wait "$other" 2>/dev/null || :' EXIT
ip link add v44r type veth peer name v44c
ip addr add 10.44.0.1/24 dev v44r
ip link set v44r up
ip link set v44c netns "$other"
nsenter -t "$other" -n -- ip link set lo up
nsenter -t "$other" -n -- ip addr add 10.44.0.2/24 dev v44c
nsenter -t "$other" -n -- ip link set v44c up
nsenter -t "$other" -n -- ip route add 198.18.44.10/32 via 10.44.0.1 dev v44c
test -z "$(ip -4 route show default)"
test -z "$(nsenter -t "$other" -n -- ip -4 route show default)"
if test "$(cat /proc/sys/net/ipv4/ip_forward)" != 0;then
  sysctl -q -w net.ipv4.ip_forward=0
fi
test "$(cat /proc/sys/net/ipv4/ip_forward)" = 0
iptables -P FORWARD DROP
ip6tables -P FORWARD DROP
ip rule add fwmark 0x40000000/0x40000000 lookup 100 priority 20000
ip route add local default dev lo table 100
iptables -t mangle -N XRAY_WIFI
for net in 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 169.254.0.0/16 172.16.0.0/12 192.168.0.0/16 224.0.0.0/4 240.0.0.0/4;do
 iptables -t mangle -A XRAY_WIFI -d "$net" -j RETURN
done
for proto in tcp udp;do
 iptables -t mangle -I PREROUTING 1 -s 10.44.0.2/32 -i v44r -p "$proto" -j XRAY_WIFI
done
iptables -t mangle -S XRAY_WIFI >"$W/nine.rules"
python3 - <<'PY'
from xray.lab.rc44_tproxy_repair_gate import current_chain_lines,sha_lines
import os
from pathlib import Path
assert Path(os.environ["RC44_NINE"]).read_text().splitlines()==list(current_chain_lines())
print("RC44_REAL_KERNEL_NINE_RETURN_BASELINE_SHA",sha_lines(current_chain_lines()))
PY
iptables-save -t mangle >"$W/before.rules"
python3 -u xray/lab/rc44_tproxy_packet_witness.py serve >"$W/sink.log" 2>&1 & server=$!
for n in $(seq 1 70);do
 if grep -Fq 'RC44_REAL_TRANSPARENT_LISTENER udp' "$W/sink.log";then break;fi
 sleep .05
done
grep -Fq 'RC44_REAL_TRANSPARENT_LISTENER tcp' "$W/sink.log"
grep -Fq 'RC44_REAL_TRANSPARENT_LISTENER udp' "$W/sink.log"
nsenter -t "$other" -n -- python3 -u xray/lab/rc44_tproxy_packet_witness.py pre >"$W/pre.log" 2>&1
grep -Fq RC44_CLIENT_PRE_TCP_BLOCKED "$W/pre.log"
! grep -Fq RC44_REAL_TPROXY_TCP_PACKET "$W/sink.log"
! grep -Fq RC44_REAL_TPROXY_UDP_PACKET "$W/sink.log"
echo RC44_PRE_REPAIR_REAL_TCP_UDP_FAIL_CLOSED
cat >"$W/repair.rules" <<'EOS'
*mangle
-A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
-A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
COMMIT
EOS
iptables-restore --noflush <"$W/repair.rules"
iptables -t mangle -S XRAY_WIFI >"$W/repaired.rules"
test "$(grep -c -- '-j TPROXY' "$W/repaired.rules")" = 2
test "$(grep -c -- '-j RETURN' "$W/repaired.rules")" = 9
nsenter -t "$other" -n -- python3 -u xray/lab/rc44_tproxy_packet_witness.py repair >"$W/client-repair.log" 2>&1
grep -Fq RC44_CLIENT_REPAIR_TCP_EXACT_ECHO "$W/client-repair.log"
for n in $(seq 1 60);do
 if grep -Fq 'RC44_REAL_TPROXY_TCP_PACKET RC44-REPAIR-TCP' "$W/sink.log" && grep -Fq 'RC44_REAL_TPROXY_UDP_PACKET RC44-REPAIR-UDP' "$W/sink.log";then break;fi
 sleep .04
done
grep -Fq 'RC44_REAL_TPROXY_TCP_PACKET RC44-REPAIR-TCP' "$W/sink.log"
grep -Fq 'RC44_REAL_TPROXY_UDP_PACKET RC44-REPAIR-UDP' "$W/sink.log"
iptables -t mangle -vxnL XRAY_WIFI >"$W/counters.txt"
cat "$W/counters.txt"
awk '($3=="TPROXY" && ($4=="tcp" || $4=="6") && $1+0>0){t=1} ($3=="TPROXY" && ($4=="udp" || $4=="17") && $1+0>0){u=1} END{exit (t&&u)?0:1}' "$W/counters.txt"
echo RC44_REAL_NATIVE_KERNEL_TPROXY_TCP_UDP_PACKET_COUNTER_SOCKET_SUCCESS
iptables -t mangle -D XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
iptables -t mangle -D XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
iptables-save -t mangle >"$W/restored.rules"
# iptables-save emits generation timestamps in # comments. Compare every
# actual rule, chain declaration, policy and COMMIT line in exact order.
# Built-in chain packet/byte counters have changed because we sent real packets.
grep -v "^#" "$W/before.rules" | sed -E "s/\\[[0-9]+:[0-9]+\\]/[COUNTERS]/g" >"$W/before.rulelines"
grep -v "^#" "$W/restored.rules" | sed -E "s/\\[[0-9]+:[0-9]+\\]/[COUNTERS]/g" >"$W/restored.rulelines"
cmp "$W/before.rulelines" "$W/restored.rulelines"
nsenter -t "$other" -n -- python3 -u xray/lab/rc44_tproxy_packet_witness.py rollback >"$W/client-rollback.log" 2>&1
grep -Fq RC44_CLIENT_ROLLBACK_TCP_BLOCKED "$W/client-rollback.log"
sleep .25
! grep -Fq RC44-ROLLBACK-UDP "$W/sink.log"
! grep -Fq RC44-ROLLBACK-TCP "$W/sink.log"
test "$(cat /proc/sys/net/ipv4/ip_forward)" = 0
test -z "$(ip -4 route show default)"
iptables -S FORWARD | grep -Fxq -- '-P FORWARD DROP'
ip6tables -S FORWARD | grep -Fxq -- '-P FORWARD DROP'
echo RC44_EXACT_ORIGINAL_KERNEL_MANGLE_RESTORED_AND_FAIL_CLOSED
echo RC44_HARD_NO_GO_NATIVE_LINUX_IS_NOT_PHYSICAL_KENETIC
