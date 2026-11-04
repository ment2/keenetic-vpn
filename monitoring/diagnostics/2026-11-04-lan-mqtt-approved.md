# VPN monitoring: approved LAN MQTT transport (2026-11-04)

Owner explicitly authorized plain MQTT over protected home Wi-Fi for Keenetic to Home Assistant telemetry; accept limitation that MQTT username/password and message contents are not application-layer encrypted. Never forward broker port to WAN. Prefer dedicated restricted identity `keenetic_monitor`, no admin rights.

Broker host: 192.168.0.169 port 1883. The server responds to TCP and MQTT, anonymous MQTT CONNECT rejected 0x05. Owner confirmed the dedicated Home Assistant user was created; successful authenticated CONNECT is NOT YET VERIFIED because its password is intentionally unavailable to the assistant. TLS port 8883 refuses connection; TLS is no longer a blocker by owner's explicit choice.

GitHub feature branch implementation:
- monitoring/mqtt_lan_publisher.py: dependency-free MQTT 3.1.1 authenticated QoS1 publisher; checks PUBACK and bounded payload, rejects topic wildcards and enforces private credential-file permissions. No background retry, no retained publications.
- monitoring/tests/test_mqtt_lan_publisher.py: mock broker and permissions tests. CI results not yet confirmed.
- traffic_counters.py and telemetry.py prepared previously. Publishing/periodic scheduling remains uninstalled.

Next required local action: user enters MQTT secret privately on their router in Termius using non-echo prompt and mode-0600 file; never paste password in chat, GitHub or agent command payload. Need exact final setup instruction and approved live canary before writing to router or enabling scheduled operations. The presence of Home Assistant local-only account does not mean it can be used without password.

Production Xray, routes, firewall, cron and watchdog unchanged.
