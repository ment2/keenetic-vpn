# Keenetic ↔ Home Assistant connectivity, 2026-11-04

Read-only diagnostics from existing Keenetic Mobile.

## Confirmed topology
- Keenetic hostname: Keenetic-6059; apclii0 192.168.0.135/24; default route via 192.168.0.1; br0 192.168.1.1/24; br1 10.1.30.1/24.
- Home Assistant: wlan0 192.168.0.169/24, default gateway 192.168.0.1, Wi-Fi ASUS-Mnt2.
- 192.168.0.1 is shared upstream gateway, not Keenetic's own LAN address; earlier probing it at port 10808 was not an Xray test.

## Observed agent jobs (all done, exit 0)
- diagnostic 89c45849-1da9-4043-9bea-8e91b506360f: Keenetic ONLINE, Python 3.13.9, load (0.21,0.22,0.3), free disk 3.48 GB.
- IP/routes eda8a6f7-b2c8-4715-99db-fe13ddbde9ce: above topology.
- ICMP 22d0365c-db0b-4bce-b3a0-ed7792d64d0b: 3/3 ping to 192.168.0.169, 0% loss; min/avg/max 3.102/20.972/41.303 ms. BusyBox nc -z was unsupported and produced misleading failure; disregard.
- HTTP 2250e99b-6050-41ae-8ede-6e3defed76d7: GET http://192.168.0.169:8123/ returned HTTP 200. Confirms HTTP network reachability only, not HA authentication or MQTT.
- owner_admin and diagnostic/exec/read_file/write_file scopes enabled at Keenetic connector.

## Next
Inspect HA Mosquitto availability and configure restricted local MQTT publishing only with separate approval, stable per-node identity, bounded read-only probes and retention. Avoid Xray/TPROXY/SOCKS, routing, firewall, cron, watchdog and production changes. No HA config or production changes carried out in these checks.
