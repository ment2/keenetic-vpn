# 2026-11-04 MQTT credential verification gate

User confirmed MQTT_CREDENTIALS_READY after manually creating local router file /opt/etc/vpn-monitor/mqtt-password (expected mode 0600).

Assistant attempted to execute a read-in-place MQTT authentication check remotely through Keenetic Mobile; host safety systems BLOCKED the tool call before execution. No credential was retrieved, no broker authentication was verified, no MQTT message was published, and no change was made by the blocked call.

Policy: Do NOT retry or reroute remote password-file reads via other connectors/tools. The operator may run a local password test in Termius and report only the resulting status string. Keep broker password and MQTT credentials out of GitHub and ChatGPT.

Next after local confirmation: isolated probe publishing a non-sensitive payload and scheduled interface counter collection using separately approved, least-privileged execution; Xray/cron/watchdog/firewall/routes untouched pending distinct approval.
