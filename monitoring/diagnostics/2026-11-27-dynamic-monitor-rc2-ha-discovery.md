# RC2 HA discovery acceptance supplement — 2026-11-27

The Home Assistant registry independently confirmed `sensor.keenetic_dynamic_vpn_rc2`, platform MQTT, not disabled. Both shadow MQTT publishes returned PUBACK. No live measurements were fabricated; test state was explicitly unavailable and non-retained. The new retained discovery is monitor-only. Old schedules/dashboard remain unchanged.

Authenticated live HA state, expiry, supported dashboard edit/render and repeated scheduled cycles remain unverified. HA add-on has no SUPERVISOR_TOKEN and core API returned HTTP 401. Cutover remains NO-GO. This supplement avoids overwriting the runbook after a GitHub update conflict.

Code CI: run 46015411857, 162/162 SUCCESS. See 2026-11-27-dynamic-monitor-rc2-runbook.md.
