# Home Assistant MQTT integration verified via owner's 2026-11-04 screenshots

Screenshots show Home Assistant MQTT integration "В сети" (online): 12 devices, 101 entities/objects currently shown. Working broker connection: core-mosquitto:1883, HA integration MQTT protocol 5, its own homeassistant username, MQTT discovery prefix homeassistant; birth/will use homeassistant/status, configured online/offline. MQTT discovery subscription QoS = 0.

Existing 12 devices and 101 entities predate monitoring; do not confuse them with the 12 planned Keenetic traffic entities. Owner confirmed an independent Keenetic MQTT account and successful MQTT QoS1 PUBACK from a Termius test. MQTT v5 HA broker connection and v3.1.1 publisher can coexist.

No HA MQTT integration reconfiguration needed. Do NOT replace Home Assistant's own broker identity with keenetic_monitor, change discovery prefix, restart broker or modify existing retained topics.

Next: publish retained HA MQTT discovery configurations (12 sensors: RX/TX cumulative and bit/s on apclii0, br0, br1) using local router credential only. Verify entities appear under device Keenetic VPN Monitoring and distinguish 12 new ones from pre-existing 101. Then test two consecutive traffic readings and periodic scheduling independently of Xray watchdog and legacy crons.

Verified thus far: MQTT transport accepts QoS1 publication. Discovery not yet published, new HA sensors not yet seen, automatic monitoring not installed. TLS not used on owner-approved protected LAN.
