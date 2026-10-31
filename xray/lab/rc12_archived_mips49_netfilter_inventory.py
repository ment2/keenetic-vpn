"""RC12 archived MIPS32LE Linux4.9 kernel image/module inventory, NO network actions.

Never loads a module, runs a VM, touches a router or claims packet-path evidence.
The exact archived package and guest kernel bytes are SHA256-checked before review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

DEB_SHA = "9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b"
KERNEL_SHA = "20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f"
RELEASE = "4.9.0-13-4kc-malta"
COMPONENTS = {
    "xt_TPROXY": "CONFIG_NETFILTER_XT_TARGET_TPROXY",
    "xt_socket": "CONFIG_NETFILTER_XT_MATCH_SOCKET",
    "iptable_mangle": "CONFIG_IP_NF_MANGLE",
    "ip_tables": "CONFIG_IP_NF_IPTABLES",
    "x_tables": "CONFIG_NETFILTER_XTABLES",
}
SUPPORTING = ("nf_defrag_ipv4", "nf_defrag_ipv6", "nf_conntrack", "nf_socket_ipv4")

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def metadata(path):
    """modinfo and readelf read foreign architecture objects; never execute them."""
    def probe(cmd):
        try:
            p = subprocess.run(cmd, text=True, capture_output=True, timeout=12, check=False)
            return p.stdout if p.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""
    vermagic = probe(["modinfo", "-F", "vermagic", str(path)]).strip()
    elf = probe(["readelf", "-h", str(path)])
    is_mips = bool(re.search(r"Machine:\s+MIPS", elf))
    is_le32 = bool(re.search(r"Class:\s+ELF32", elf) and
                   re.search(r"Data:.*little endian", elf))
    return {
        "sha256": digest(path),
        "vermagic": vermagic,
        "kernel_vermagic_match": vermagic.startswith(RELEASE + " "),
        "elf32_mips_little_endian": is_mips and is_le32,
    }

def classify(config_value, module_found, module_metadata=None):
    if config_value == "y":
        return "KCONFIG_BUILTIN_ONLY_RUNTIME_UNVERIFIED"
    if module_found and module_metadata and module_metadata.get("kernel_vermagic_match") and module_metadata.get("elf32_mips_little_endian"):
        return "MATCHING_MIPS_MODULE_BYTES_ONLY_NOT_LOADED"
    if module_found:
        return "MODULE_PRESENT_BUT_VERMAGIC_OR_ARCH_UNVERIFIED"
    if config_value == "m":
        return "CONFIG_MODULE_BUT_BYTES_MISSING"
    if config_value == "n":
        return "CONFIG_DISABLED"
    return "CONFIG_AND_MODULE_UNVERIFIED"

def review(deb, root):
    deb, root = Path(deb), Path(root)
    if digest(deb) != DEB_SHA:
        raise ValueError("ARCHIVED_DEBIAN_MIPS_PACKAGE_SHA256_MISMATCH")
    kernel = root / "boot" / ("vmlinux-" + RELEASE)
    if not kernel.is_file() or digest(kernel) != KERNEL_SHA:
        raise ValueError("ARCHIVED_MIPS_KERNEL_ELF_SHA256_MISMATCH")
    candidates = sorted((root / "boot").glob("config-*"))
    config = {}
    for path in candidates:
        if RELEASE not in path.name:
            continue
        for line in path.read_text(errors="replace").splitlines():
            m = re.fullmatch(r"(CONFIG_[A-Z0-9_]+)=(y|m|n)", line)
            if m:
                config[m.group(1)] = m.group(2)
    modules = sorted((root / "lib" / "modules").rglob("*.ko*"))
    by_name = {path.name.split(".ko", 1)[0]:path for path in modules
               if ".ko" in path.name}
    records = {}
    for name, flag in COMPONENTS.items():
        module = by_name.get(name)
        details = metadata(module) if module else None
        config_value = config.get(flag, "?")
        records[name] = {
            "kconfig_flag": flag,
            "kconfig_value": config_value,
            "module_relative_path": str(module.relative_to(root)) if module else None,
            "metadata": details,
            "assessment": classify(config_value, module is not None, details),
        }
    support = {name: str(by_name[name].relative_to(root)) if name in by_name else None
               for name in SUPPORTING}
    fully_accounted = all(
        rec["assessment"] in ("KCONFIG_BUILTIN_ONLY_RUNTIME_UNVERIFIED",
                              "MATCHING_MIPS_MODULE_BYTES_ONLY_NOT_LOADED")
        for rec in records.values()
    )
    return {
        "schema": 1,
        "mode": "ARCHIVED_DEBIAN_MIPS32LE_KERNEL_MODULE_BYTES_READ_ONLY",
        "archive_exact_sha256": DEB_SHA,
        "guest_kernel_exact_sha256": KERNEL_SHA,
        "guest_kernel_release": RELEASE,
        "config_file_present": bool(config),
        "module_object_count": len(modules),
        "required": records,
        "supporting_module_paths": support,
        "required_component_bytes_accounted_for": fully_accounted,
        "inventory_status": ("ARCHIVED_COMPONENTS_ACCOUNTED_FOR_BUT_NOT_LOADED"
                             if fully_accounted else "ARCHIVED_COMPONENTS_MISSING_OR_UNVERIFIED"),
        "actual_mips49_tcp_tproxy_packets_verified": False,
        "actual_mips49_udp_tproxy_packets_verified": False,
        "actual_mips49_ipv6_dns_no_leak_verified": False,
        "physical_vendor_ndm5_kernel_compatible": False,
        "legacy_root_cgroup_escape_fenced": False,
        "physical_usb_independent_rescue_verified": False,
        "release_decision": "HARD_NO_GO_PRODUCTION",
        "deployment_authorized": False,
        "router_commands": [],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--deb", type=Path, required=True)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    evidence = review(a.deb, a.root)
    a.out.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print("RC12: ARCHIVED_MIPS49_NETFILTER_MODULES_READ_ONLY " + evidence["inventory_status"])
    for name, rec in evidence["required"].items():
        print("RC12: " + name + "=" + rec["assessment"] + " config=" + rec["kconfig_value"])
    print("RC12: HARD_NO_GO_REAL_MIPS_PACKET_PATH_AND_PHYSICAL_HARDWARE_UNPROVEN")

if __name__ == "__main__":
    main()
