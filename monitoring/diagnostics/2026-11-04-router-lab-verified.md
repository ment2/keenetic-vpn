# 2026-11-04: Keenetic isolated VPN-monitoring lab verified

Repo: ment2/keenetic-vpn, branch feature/vpn-monitoring-home-assistant-20261104.

Router task evidence:
- 579edb1f-8cc0-49d0-9030-43a68184048a: traffic counters module syntax OK.
- 8981dbd8-176a-4753-8aa9-012e8109594a: MQTT publisher syntax OK.
- 0da14a1c-bdb5-417f-bbea-d0fcfd1028e8: one-shot collector syntax OK.
- 6b1397bb-4224-4724-b86d-5805c693af53: Home Assistant discovery module syntax OK.
- 04db1a61-f421-4ced-9576-d63a20c92b21: real apclii0 baseline, then a subsequent OK delta after 3 seconds; 12 planned HA discovery configs; **MQTT not sent**.
- Test staging tasks 4162edb8-ee5f-4286-83cd-dd90230fb9ad, 21d9a074-b1f9-4e46-9ff3-96590a84c79f, 91753483-7f37-4443-a750-3aa60e355be1, 28a2516f-51a1-45a1-85d7-b74fd02da58e all done exit 0.
- ead5c3b8-3dc8-4aaa-b157-33492ae23cf7: 28/28 offline tests passed on router (0.262s), including MQTT publish failure baseline retention.

Changes: traffic_one_shot.py advances snapshot only after valid QoS1 PUBACK when sending. No remote reading of MQTT credential. No broker publishing, discovery or scheduling occurred in this phase. Lab files reside under /opt/tmp/vpn-monitoring-lab. Do not misinterpret general interface counters as per-VLESS traffic or sum overlapping bridges.

Next owner-local Termius step: publish 12 retained HA discovery configs and two non-retained interval measurements using router-resident password. Assistant remote tools must not read the credential; prior attempted remote credential read was blocked by system controls. Validate HA integration actually creates new Keenetic device/sensors before enabling 60-second background schedule. Do not change existing Xray, firewall, routes, watchdog, or production cron.
