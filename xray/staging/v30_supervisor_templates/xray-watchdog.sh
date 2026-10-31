#!/opt/bin/sh
# STAGED ONLY. Per-cycle watchdog obtains common flock inside the broker.
set -eu
exec /opt/bin/python3 /opt/bin/v30_supervisor_service.py watchdog-loop
