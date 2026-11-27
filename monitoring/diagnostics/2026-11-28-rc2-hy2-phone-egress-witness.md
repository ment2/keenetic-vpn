# RC2 Hysteria2 — phone egress witness

Date: 2026-11-28, screenshot clock 00:35 MSK. Baseline report commit `63e6b1eade463dfb9f7b0117f6e3022b993a037c`.

## Observation

Owner reports iPhone on Asus Wi-Fi (no router VPN) with Happ Plus Lithuania profile. Prior screenshot shows Lithuania selected; current IPinfo screenshot displays `Your IP 212.24.109.100` and Lithuanian flag. This is a browser egress observation, not a packet capture or profile export. It matches the earlier DNS A record for subscription Hysteria2 endpoint `lt1.nerpvpn.net` (hy02). No full profile, credentials, subscription URL, account identifiers or screenshots are included in this report.

## Interpretation

The matching IPv4 egress strengthens evidence that the phone uses the same service/IP, but does not establish its ingress endpoint, protocol, port, authentication parameters or exact profile equivalence. Prior Keenetic capture showed outbound UDP and no inbound response for hy02; exact installed Entware binary passed synthetic Linux 4.9 interoperability. These observations cannot distinguish all provider-side or physical network-path causes. The earlier capture with the phone connected to Asus is not evidence of packet loss on Keenetic.

## Remaining acceptance gate

Request only nonsecret protocol/endpoint/port or confirmation from provider; if the profile is hidden, do not export or alter it. No further physical client launch, no bypass of prior platform block. No router, VPN, firewall, route, updater, or monitoring changes. No production admission for hy02; physical acceptance remains unverified. Keep existing RC2 and Geo policy unchanged.
