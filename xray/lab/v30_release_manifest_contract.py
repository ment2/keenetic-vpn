#!/usr/bin/env python3
"""Offline v30 release manifest validator: no router/network/process actions.

A missing, stale, mismatched or non-hermetic entry makes the release invalid.
The only supported output is an offline integrity assessment, never approval
to install production supervisor/init/canary.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "xray/staging/v30-release-manifest-v1.json"
EXPECTED = {
    "S97": "xray/staging/v30_supervisor_templates/S97xray",
    "S98": "xray/staging/v30_supervisor_templates/S98xray-wifi",
    "S99": "xray/staging/v30_supervisor_templates/S99xray-watchdog",
    "watchdog": "xray/staging/v30_supervisor_templates/xray-watchdog.sh",
    "wifi_rules": "xray/staging/v30_supervisor_templates/xray-wifi-rules.sh",
    "core": "xray/staging/v30_supervisor_core.py",
    "broker": "xray/staging/v30_supervisor_service.py",
    "canary": "xray/staging/v30_cooperative_canary.py",
    "legacy_canary": "xray/staging/v30_first_cutover_canary.py",
}
ARCHIVE = {
    "S97": "xray/production/opt/etc/init.d/S97xray",
    "S98": "xray/production/opt/etc/init.d/S98xray-wifi",
    "S99": "xray/production/opt/etc/init.d/S99xray-watchdog",
    "watchdog": "xray/production/opt/bin/xray-watchdog.sh",
    "wifi_rules": "xray/production/opt/bin/xray-wifi-rules.sh",
}
EXPECTED_GATES = (
    "pidfd_kernel_compatibility", "legacy_descendant_drain",
    "all_entrypoints_cooperative", "canary_live_integration",
    "kernel_tproxy_tcp_udp", "fail_closed_dns_ipv6",
    "reboot_usb_loss_recovery", "owner_exact_file_approval",
)


class ManifestError(RuntimeError):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") +
                        b"\0" + data).hexdigest()


def checked_file(root, relative):
    if not isinstance(relative, str) or relative.startswith("/") or (
            any(x in ("", ".", "..") for x in relative.split("/"))):
        raise ManifestError("unsafe path")
    path = root.joinpath(*relative.split("/"))
    if path.is_symlink() or not path.is_file():
        raise ManifestError("missing or symlinked release source")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()):
        raise ManifestError("release source escaped checkout")
    return path.read_bytes()


def valid_hash(value, n):
    return (isinstance(value, str) and len(value) == n and
            all(c in "0123456789abcdef" for c in value))


def verify(root=ROOT, manifest=None):
    root = Path(root).resolve()
    obj = json.loads(MANIFEST.read_text()) if manifest is None else manifest
    if obj.get("schema_version") != 1 or obj.get("release") != "v30-cooperative-supervisor-rc1":
        raise ManifestError("release schema/name drift")
    if obj.get("source_branch") != "feature/xray-v30-stable-tcp-ingress-lab-20261031":
        raise ManifestError("branch drift")
    if not valid_hash(obj.get("source_commit"), 40):
        raise ManifestError("source commit unpinned")
    if obj.get("status") != "STAGING_ONLY_NOT_FOR_DEPLOY" or (
            obj.get("deployment_authorized") is not False or
            obj.get("production_trial_authorized") is not False or
            obj.get("default_action") != "deny"):
        raise ManifestError("unexpected execution authorization")
    if obj.get("shared_lock") != "/opt/var/run/xray-v30-supervisor.lock" or (
            obj.get("required_actors") != ["S97", "S98", "watchdog", "cutover", "guardian"]):
        raise ManifestError("shared actor mutex mismatch")
    if set(obj.get("required_release_gates", ())) != set(EXPECTED_GATES):
        raise ManifestError("missing release gate")
    entries = obj.get("entries", ())
    if (not isinstance(entries, list) or len(entries) != len(EXPECTED) or
            {x.get("role") for x in entries} != set(EXPECTED)):
        raise ManifestError("incomplete or duplicate role set")
    frozen = {}
    for line in (root / "xray/production/MANIFEST.sha256").read_text().splitlines():
        parts = line.split()
        if len(parts) == 3:
            frozen[parts[1]] = (parts[0], parts[2])
    for entry in entries:
        role = entry["role"]
        if entry.get("staging_path") != EXPECTED[role]:
            raise ManifestError("entry path drift: " + role)
        data = checked_file(root, entry["staging_path"])
        if entry.get("staging_size") != len(data):
            raise ManifestError("entry byte size drift: " + role)
        if not valid_hash(entry.get("staging_sha256"), 64) or (
                entry["staging_sha256"] != sha256(data)):
            raise ManifestError("SHA256 drift: " + role)
        if not valid_hash(entry.get("staging_git_blob"), 40) or (
                entry["staging_git_blob"] != git_blob_sha(data)):
            raise ManifestError("Git blob drift: " + role)
        if role in ARCHIVE:
            if entry.get("legacy_snapshot_path") != ARCHIVE[role]:
                raise ManifestError("legacy archive path drift: " + role)
            old = checked_file(root, entry["legacy_snapshot_path"])
            if entry.get("legacy_snapshot_size") != len(old) or (
                    entry.get("legacy_snapshot_sha256") != sha256(old)) or (
                    entry.get("legacy_git_blob") != git_blob_sha(old)):
                raise ManifestError("archive digest drift: " + role)
            archive_key = "opt/" + ARCHIVE[role].split("/opt/", 1)[1]
            expected_frozen = frozen.get(archive_key)
            if expected_frozen != (sha256(old), "100755"):
                raise ManifestError("frozen snapshot manifest or mode drift: " + role)
        else:
            if any(k.startswith("legacy_") for k in entry):
                raise ManifestError("unrequested legacy path: " + role)
    legacy_canary = next(x for x in entries if x["role"] == "legacy_canary")
    if legacy_canary["staging_sha256"] != (
            "8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203"):
        raise ManifestError("previously installed canary immutable pin drift")
    return {"verified": len(entries), "status": "PASS_STAGED_INTEGRITY_ONLY",
            "production_trial_allowed": False, "deployment_allowed": False,
            "unresolved_gates": list(EXPECTED_GATES)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    if not args.verify:
        p.error("only read-only --verify supported")
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
