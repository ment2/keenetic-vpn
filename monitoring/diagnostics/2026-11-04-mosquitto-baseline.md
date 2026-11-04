# Mosquitto HA verified baseline, 2026-11-04

User screenshots confirm Mosquitto broker application 7.1.3 running in HA OS. Autostart, watchdog and automatic updates enabled. Displayed ports: 1883 MQTT, 1884 WebSocket, 8883 TLS MQTT, 8884 TLS WebSocket. Require client certificate is off. Fields certfile fullchain.pem and keyfile privkey.pem are populated with filenames, but validity/presence of TLS files remains unverified.

Prior read-only MQTT handshake from Keenetic at 192.168.0.169:1883 returned CONNACK 20020005, meaning anonymous connect rejected. Broker requires authorization; no publish attempted.

Official HA Mosquitto docs confirm an independent MQTT identity can be configured via Settings > People > Users (alternative add-on-local logins), keeping production credentials out of GitHub and Library. Prefer a distinct nonadmin account and narrow broker ACL if supported; inspect first. Existing smart home devices should not be disrupted or broker restarted. No credentials, changes, integrations or automated monitoring yet.
