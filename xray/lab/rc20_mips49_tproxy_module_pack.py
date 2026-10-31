#!/usr/bin/env python3
"""RC20 guest-only module closure with TCPUDP matcher (no host kernel changes)."""
from pathlib import Path
import argparse
from xray.lab import rc13_mips49_module_dependency_pack as base
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",type=Path,required=True)
 p.add_argument("--dest",type=Path,required=True)
 a=p.parse_args()
 base.REQUIRED=base.REQUIRED+("pcnet32","xt_tcpudp")
 print("RC20_MODULE_ORDER",",".join(base.build(a.root,a.dest)))
if __name__=="__main__":main()
