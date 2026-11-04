# CI queue investigation — 2026-11-04

Scope: ment2/keenetic-vpn branch feature/vpn-monitoring-home-assistant-20261104.

## Verified findings
1. Workflow .github/workflows/vpn-monitoring-tests.yml runs on ubuntu-latest; previous configuration matched all monitoring/** changes (including markdown diagnostics), so every small docs/source commit spawned an independent workflow.
2. Several older workflow runs were temporarily queued with no assigned runner and empty steps, then began processing and completed successfully. GitHub Actions public status page showed Actions operational at the checked time. The evidence does not establish a sustained runner shortage or account billing suspension.
3. Run 41865295410 (SHA 322b5add...) actually started and failed one Python test out of 94. Its log shows test_missing_password_fails_closed asserted sink empty. Production-oriented code had intentionally been modified to preserve local sanitized evidence even if publishing cannot authenticate to MQTT; test was stale.
4. Subsequent SHA e352d318d17826978c53787fa17e74aeaa7f66af fixed the expectation and added MQTT outage evidence-preservation test. Run 41865332989 completed SUCCESS.
5. Added workflow-level concurrency group vpn-monitoring-${{ github.ref }} and cancel-in-progress: true, and narrowed triggers to monitoring/**/*.py plus the workflow itself, commit 0f4ba9fc82c55bbef67b15f0cc4e0be2b07b0da8. This reduces *future* spurious queue work; older non-concurrent runs may remain independently queued. No manual cancellation of older workflow runs was attempted.
6. Latest run 41866604225 was still queued at last read; do not claim its conclusion until confirmed.

## Operator guidance
- Do not continue committing report markdown under monitoring/ and causing fresh CI runs. New workflow excludes them.
- Confirm latest run 41866604225 SUCCESS before changing router. Avoid rerunning older failure: its fix is already included in a later successful commit.
- Old queued runs are safe to cancel via GitHub UI (Actions → select run → Cancel workflow) if desired, but this is optional; never cancel the newest test run by accident.
- CI source checks alone do not mean live deployment is complete. Router Xray, routing and installed collector were not changed in this investigation.
