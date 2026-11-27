# RC2 Lithuanian endpoint attribution — 2026-11-27

Verdict: CONFIRMED endpoint identity; monitoring coverage gap, not Geo RC1 exclusion or VLESS conversion loss.

Predecessor 81f77748214c862b965013fbbdf8a405e1f266ea. Approved rc2_hysteria2_ip_audit_command.txt SHA256 a6d32756d0328166af655f741e7c2f44c4b37ddc42ed21a6f469bed4266f753a verified against local file. Submitted once, Keenetic Mobile job 5b150ed7-7b44-4286-81e7-5a348ba26bc9, created 19:29:34 UTC, DONE exit 0.

Sanitized result: NONEMPTY 12 HYSTERIA2 2; HYSTERIA2_ENDPOINT 1 140.225.199.183 443 TARGET False; HYSTERIA2_ENDPOINT 2 lt1.nerpvpn.net 443 TARGET False (literal hostname comparison); CONFIGS_UNCHANGED True.

Independent DNS via HA, read-only owner grant, job 5f3912d4-473a-48b3-ae38-d8d0d70f94c4, created 19:30:31 UTC, DONE exit 0: HOST lt1.nerpvpn.net IPS ['212.24.109.100'] TARGET True. Confirms the requested IP is the resolved endpoint of the second Hysteria2 entry in the current subscription, using HA resolver at observation time. Does not independently establish its egress IP or tunnel reachability, and does not prove phone traffic path.

Root cause: provider has 12 entries (10 VLESS, 2 Hysteria2); subscription() selects only lowercase vless:// and RC2 consumes that subset. Lithuanian Hysteria2 entry is consequently absent from RC2 and Xray VLESS pool. All ten VLESS entries previously matched the snapshot; four active. No hardcoded 10 limit observed. No production modification, restart, forced probe, credential export or job resubmission. Future monitoring expansion to include Hysteria2 should be developed and tested separately, with actual protocol-specific probes and without changing active VPN pool absent separate approval.
