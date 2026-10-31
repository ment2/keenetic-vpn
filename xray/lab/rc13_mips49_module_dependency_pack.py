"""Build *disposable* initramfs module load order from SHA-pinned archive bytes.

HOST ONLY. Uses modinfo as a metadata reader, never insmod or modprobe here.
The resulting module binaries are copied to a QEMU-only initramfs.
"""
import argparse
from pathlib import Path
import shutil
import subprocess

REQUIRED = ("x_tables", "ip_tables", "iptable_mangle", "xt_socket", "xt_TPROXY")
def build(root, dest):
    root, dest = Path(root), Path(dest)
    options = sorted((root / "lib" / "modules").rglob("*.ko"))
    by_name = {p.name[:-3]:p for p in options}
    if not all(x in by_name for x in REQUIRED):
        raise ValueError("REQUIRED_MIPS_MODULE_BYTES_MISSING")
    order = []
    seen = set()
    visiting = set()
    def visit(name):
        if name in seen:
            return
        if name in visiting:
            raise ValueError("CYCLIC_MODULE_DEPENDENCY:" + name)
        if name not in by_name:
            raise ValueError("REQUIRED_DEPENDENCY_BYTES_MISSING:" + name)
        visiting.add(name)
        out = subprocess.run(
            ["modinfo", "-F", "depends", str(by_name[name])],
            capture_output=True, text=True, check=True, timeout=15).stdout.strip()
        for item in out.replace("-", "_").split(","):
            if item.strip():
                visit(item.strip())
        visiting.remove(name)
        seen.add(name)
        order.append((name, by_name[name]))
    for item in REQUIRED:
        visit(item)
    dest.mkdir(parents=True, exist_ok=False)
    lines=[]
    for i, (name, path) in enumerate(order):
        out = f"{i:03d}.ko"
        shutil.copyfile(path, dest / out)
        lines.append(out + " " + name)
    (dest / "order.txt").write_text("\n".join(lines) + "\n")
    return tuple(name for name, _ in order)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--dest", type=Path, required=True)
    x=p.parse_args()
    order=build(x.root,x.dest)
    print("RC13: MIPS_MODULE_DEPENDENCY_ORDER=" + ",".join(order))
    print("RC13: MODULE_BYTES_COPIED_FOR_DISPOSABLE_QEMU_ONLY")
if __name__=="__main__":
    main()
