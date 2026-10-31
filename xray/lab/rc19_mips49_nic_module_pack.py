#!/usr/bin/env python3
"""RC19 extends RC13 module dependency closure only within this Python process."""
from pathlib import Path
import argparse
from xray.lab import rc13_mips49_module_dependency_pack as p
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--root",type=Path,required=True)
 a.add_argument("--dest",type=Path,required=True)
 x=a.parse_args()
 p.REQUIRED=p.REQUIRED+("pcnet32",)
 print("RC19_MODULE_ORDER",",".join(p.build(x.root,x.dest)))
if __name__=="__main__":main()
