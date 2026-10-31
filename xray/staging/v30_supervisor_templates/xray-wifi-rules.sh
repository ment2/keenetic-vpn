#!/opt/bin/sh
# STAGED ONLY. A direct call must NOT bypass the shared supervisor mutex.
set -eu
exec /opt/bin/python3 /opt/bin/v30_supervisor_service.py wifi-repair
