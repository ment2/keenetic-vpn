# OpenAI monitoring: follow-up while lock-busy fix CI awaits runner

Date: 2026-11-04. Branch feature/vpn-monitoring-home-assistant-20261104.

- Existing lock-busy patch commits aeeeec2b866fd5d0b795829e63a56ba2cc2fbb8b and unit test a7da64a2f6a3bec2f6b8ea8555edabd3341ac196. Workflow 41878954667 is queued (runner=null; 0 steps), run 41878870917 also queued at last read. Older CI 41873235903 SUCCESS, but does not include lock-busy fix.
- Read-only Keenetic task e06ef3d1-bcbf-47ab-9a57-0fb4e040c062 done, exit_code=0, with NOW epoch 1793814216 (~17:43 UTC): 14 history rows total, last seven from 17:30 UTC, one successful cycle and one historical BlockingIOError, log age 767s. No new cycle expected until 17:45 UTC, so this does not prove schedule malfunction.
- Existing cron was verified single */15 invocation, /opt/sbin/crond one process.
- No extra exec/write jobs were issued after this diagnostic, no duplicate submission, no Xray changes and no cron edits.
- Await workflow success before updating /opt/tmp/vpn-monitoring-lab/monitoring/openai_health_collector_loop.py, then verify next unattended cycle and benign skip behavior. The patch changes only behavior when lock is busy; current collector already executes real cycles correctly.
