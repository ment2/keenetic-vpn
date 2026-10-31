"""RC34: disposable MIPS Linux4.9 guest conntrack module closure.

This intentionally fails if the archived QEMU kernel lacks the required
conntrack modules. No host modprobe; all bytes load only in disposable guest.
"""
from pathlib import Path
import argparse
from xray.lab import rc13_mips49_module_dependency_pack as base
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",type=Path,required=True)
 p.add_argument("--dest",type=Path,required=True)
 a=p.parse_args()
 base.REQUIRED=base.REQUIRED+("pcnet32","xt_tcpudp","nf_conntrack","nf_conntrack_ipv4")
 print("RC34_GUEST_CONNTRACK_MODULE_ORDER",",".join(base.build(a.root,a.dest)))
if __name__=="__main__":main()
