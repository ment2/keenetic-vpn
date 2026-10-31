#!/bin/sh
# LAB-ONLY watchdog: shared-lock health request only.
set -eu
: "${XRAY_V30_DISPOSABLE_ROOT:?No lab root; production invocation denied}"
exec python3 -m xray.lab.v30_kernel49_cooperative_lab --client "$XRAY_V30_DISPOSABLE_ROOT" watchdog CHECK_HEALTH
