# RC2 mobile layout — 2026-11-27

User visual feedback: original vertically spaced per-server diagnostic paragraphs are hard to scan on iPhone. New canonical rc2_card.yaml provides a five-column compact overview, short Russian status labels, pool membership markers and grouped server details with IPs, geography, short measurement times, HTTP durations and stale-data warnings. Existing graphs remain unchanged. No probe logic changed.

CI 46019283668 SUCCESS, 166/166, commit 85f2a6ae56f8f425d2ac33c17371a9521885987f. Template includes an explicit ten-row matrix regression test.

Apply only the existing rc2-shadow card through the authenticated Lovelace API, after exact old-card comparison and private backup. Application job 21333817-0bfe-4591-9195-35d039964a12 was queued; do not resubmit. Verify result and visual rendering before declaring acceptance. No router, cron, Xray, updater, firewall, routing or kill-switch change.