# Home Assistant network discovery (second read-only pass)

Date: 2026-11-04. Project: Keenetic VPN Monitoring. User-provided output from Advanced SSH & Web Terminal.

## Confirmed
- `ip neigh show 192.168.0.1`: MAC `60:a4:b7:b4:bf:54`, neighbour state `DELAY`. MAC alone does not establish the gateway model or ownership.
- `wlan0` UP with `192.168.0.169/24`.
- `ha network info`: SSID `ASUS-Mnt2`, WPA-PSK, signal `93` (units not assumed), wlan0 connected and primary; DNS/gateway `192.168.0.1`; host_internet=true; supervisor_internet=true.
- Ethernet `end0` disabled and disconnected, no IPv4 address.
- HA docker `172.30.32.0/23`, gateway `172.30.32.1`, DNS `172.30.32.3`.
- wlan0 has IPv6 link-local but no IPv6 gateway shown.

## Limitations
- Gateway 192.168.0.1 is not verified as Keenetic. Prior 192.168.0.1:10808 failure does not imply broken Xray; Xray SOCKS5 historically binds 127.0.0.1:10808.
- No VPN node measurements yet. HA internet access doesn't prove access to Keenetic.

## Next step
Verify Keenetic LAN address through its own UI or read-only Keenetic diagnostics, then test only the verified address. No broad scanning, SOCKS exposure or changes to firewall/routes/Xray/cron/watchdog.

Status: observations only; no router/HA modifications.