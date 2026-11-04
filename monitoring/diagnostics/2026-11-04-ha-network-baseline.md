# VPN Monitoring: Home Assistant first read-only network baseline
Date: 2026-11-04
Status: observed user-run probe; no mutations

## Host
- Home Assistant OS 18.4; Core 2026.10.4, Supervisor 2026.10.5 (from UI).
- Terminal returned `uname -m`: `aarch64`. Do not assume x86 mini-PC.
- `df -h /config` resolved to `/dev/sda8` mounted on `/addon_configs`, 116.7G capacity, 14.2G used, 97.7G available, 13% used. This describes the terminal-visible mount, not proven capacity of every HA data volume.
- WLAN interface wlan0: 192.168.0.169/24. Default route via 192.168.0.1, metric 600. Local networks: docker0 172.30.232.0/23 and hassio 172.30.32.0/23.
- Default gateway 192.168.0.1: ping 3/3 successful, 0% packet loss; min/avg/max 4.390/5.062/6.370 ms.
- TCP connect to 192.168.0.1:10808 via `nc -z -w 3` failed. IMPORTANT: 192.168.0.1 is the Home Assistant gateway, not confirmed Keenetic address; SOCKS5 historically listens on 127.0.0.1:10808 on Keenetic, so failure is not a VPN outage finding.

## Next read-only discovery
- Identify default gateway vendor/host and Keenetic management LAN IP via known router UI, DHCP device list or existing Keenetic diagnostic connector. Confirm whether 192.168.0.169 and Keenetic share a routed subnet.
- From Home Assistant terminal: `ip neigh show 192.168.0.1; ip -4 addr show dev wlan0; ha network info` (avoid disclosing secrets). Optionally read-only ping of *verified* Keenetic LAN address. Do not scan arbitrary hosts or expose router services.
- Once topology verified, test bounded telemetry path with dedicated access control; do not expose existing loopback SOCKS listener or change VPN ingress.

## Guardrails
No router jobs, no production Xray changes, no firewall/routes/cron/watchdog changes, no HA configuration mutations, and no DNS or port forwarding. Separate implementation approvals required. Monitoring must remain independent of unproven seamless cutover gates.
