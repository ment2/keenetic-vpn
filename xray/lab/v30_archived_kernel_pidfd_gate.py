#!/usr/bin/env python3
"""Offline archived-kernel compatibility contract; NO live router reads.

Historical read-only Keenetic job ea140581-a4db-42f5-ac4d-46c8c6c462ba
reported '4.9-ndm-5'. This source is evidence of an earlier state, not
a fresh current host query. pidfd_send_signal requires Linux >=5.1;
pidfd_open requires Linux >=5.3. Linux 4.9 has neither syscall, so the
staged v30_supervisor_core.py must fail closed on this archived kernel.
"""
import argparse
import json
import re

ARCHIVED_KERNEL = "4.9-ndm-5"
ARCHIVED_JOB = "ea140581-a4db-42f5-ac4d-46c8c6c462ba"
MIN_PIDFD_SEND = (5,1)
MIN_PIDFD_OPEN = (5,3)


def parse_release(name):
    if not isinstance(name,str):
        raise ValueError("no valid kernel release")
    m=re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?(?:[-+._][A-Za-z0-9._+-]*)?$",name)
    if not m:
        raise ValueError("bad kernel release")
    return int(m.group(1)),int(m.group(2)),int(m.group(3) or 0)


def capability_report(release, *, provenance="historical_archive"):
    major,minor,patch=parse_release(release)
    pair=(major,minor)
    send=pair>=MIN_PIDFD_SEND
    open_=pair>=MIN_PIDFD_OPEN
    usable=send and open_
    return {
        "kernel":release,
        "kernel_version":[major,minor,patch],
        "pidfd_send_signal_min":"5.1",
        "pidfd_open_min":"5.3",
        "pidfd_send_signal_kernel_capable":send,
        "pidfd_open_kernel_capable":open_,
        "staged_supervisor_pidfd_compatible":usable,
        "evidence_provenance":provenance,
        "evidence_is_fresh":False,
        "release_gate":"OFFLINE_KERNEL_INCOMPATIBLE" if not usable else "VERIFY_LIVE_KERNEL_AND_PYTHON",
        "production_signal_authorized":False,
        "production_commands":[],
        "engineering_next":"kernel_4_9_parent_owned_supervisor_design_or_no_go" if not usable else "fresh_readonly_kernel_probe",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archived-only",action="store_true")
    a=p.parse_args()
    if not a.archived_only:
        p.error("only archived read-only evidence; no router calls")
    r=capability_report(ARCHIVED_KERNEL)
    r["archived_job_id"]=ARCHIVED_JOB
    print(json.dumps(r,sort_keys=True))


if __name__=="__main__":
    main()
