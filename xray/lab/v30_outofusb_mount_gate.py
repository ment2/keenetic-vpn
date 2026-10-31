#!/usr/bin/env python3
"""Offline proof contract for a rescue mount independent of USB Entware.

Never assumes /tmp, /opt or a directory on the same filesystem is a
durable fallback. This is a *verifier for supplied evidence*, not a router
mount operation, and cannot prove boot persistence without a live test.
"""
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Mount:
    mount_id: int
    parent_id: int
    device: str
    mountpoint: str
    fstype: str
    source: str
    options: str


def parse_mountinfo(source):
    items = []
    for line in source.splitlines():
        if not line.strip():
            continue
        before, sep, after = line.partition(" - ")
        if not sep:
            raise ValueError("invalid mountinfo line")
        a, b = before.split(), after.split()
        if len(a) < 6 or len(b) < 3:
            raise ValueError("truncated mountinfo")
        items.append(Mount(int(a[0]),int(a[1]),a[2],a[4],b[0],b[1],
                           ",".join(a[5:])))
    if len({x.mount_id for x in items}) != len(items):
        raise ValueError("duplicate mount ID")
    return items


def covering(path, mounts):
    matching = [m for m in mounts if path == m.mountpoint or
                path.startswith(m.mountpoint.rstrip("/") + "/")]
    if not matching:
        raise ValueError("no covering mount")
    return max(matching, key=lambda m:len(m.mountpoint))


def assess(mountinfo, *, entware="/opt", rescue="/mnt/keenetic-rescue",
           observed_after_cold_boot=False, root_owned_0700=False,
           independent_restore_after_usb_loss=False,
           sha256_archive_verified=False, guardian_exec_without_usb=False):
    reasons=[]
    try:
        if not rescue.startswith("/") or not entware.startswith("/"):
            raise ValueError("nonabsolute mount path")
        mounts=parse_mountinfo(mountinfo)
        active=covering(entware,mounts)
        safe=covering(rescue,mounts)
        if active.mount_id == safe.mount_id:
            reasons.append("SAME_MOUNT_ID")
        if active.device == safe.device:
            reasons.append("SAME_KERNEL_DEVICE")
        if safe.mountpoint != rescue:
            reasons.append("RESCUE_NOT_EXPLICIT_MOUNT_ROOT")
        if safe.fstype in ("tmpfs","ramfs","overlay"):
            reasons.append("RESCUE_NOT_PERSISTENT_FS")
        if safe.source == active.source:
            reasons.append("SAME_BLOCK_SOURCE")
        if entware.startswith(rescue.rstrip("/")+"/") or rescue.startswith(entware.rstrip("/")+"/"):
            reasons.append("MOUNT_PATH_OVERLAP")
    except (ValueError, IndexError, TypeError):
        reasons.append("MOUNTINFO_UNTRUSTWORTHY")
    inputs={
        "observed_after_cold_boot":observed_after_cold_boot,
        "root_owned_0700":root_owned_0700,
        "independent_restore_after_usb_loss":independent_restore_after_usb_loss,
        "sha256_archive_verified":sha256_archive_verified,
        "guardian_exec_without_usb":guardian_exec_without_usb,
    }
    reasons.extend("NO_"+name.upper() for name, yes in inputs.items() if yes is not True)
    return {
        "status":"INSUFFICIENT_EVIDENCE" if reasons else "OFFLINE_MOUNT_EVIDENCE_ONLY",
        "reasons":sorted(set(reasons)),
        "physical_router_reboot_proven":False,
        "production_rescue_authorized":False,
        "production_commands":[],
    }


if __name__=="__main__":
    print(json.dumps(assess(""),sort_keys=True))
