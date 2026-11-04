"""Linux interface counter deltas. Read-only and not per-VLESS statistics."""
from dataclasses import dataclass
from pathlib import Path
import re, time
IFACE = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")
@dataclass(frozen=True)
class Sample:
    iface: str
    boot_id: str
    monotonic_ns: int
    rx_bytes: int
    tx_bytes: int

def read_snapshot(iface: str, sysfs_root=Path("/sys/class/net"), boot_id_path=Path("/proc/sys/kernel/random/boot_id")) -> Sample:
    if not IFACE.fullmatch(iface): raise ValueError("bad interface name")
    stats = sysfs_root / iface / "statistics"
    rx, tx = (int((stats / (direction + "_bytes")).read_text().strip()) for direction in ("rx","tx"))
    boot = boot_id_path.read_text().strip()
    if min(rx,tx) < 0 or not boot: raise ValueError("invalid counter or boot")
    return Sample(iface,boot,time.monotonic_ns(),rx,tx)

def interval(old: Sample, new: Sample, max_interval_s=600) -> dict:
    if old.iface != new.iface: raise ValueError("interface mismatch")
    if old.boot_id != new.boot_id: return {"status":"reset","reason":"boot_changed"}
    seconds=(new.monotonic_ns-old.monotonic_ns)/1e9
    if seconds <= 0: return {"status":"reset","reason":"nonpositive_elapsed"}
    if seconds > max_interval_s: return {"status":"gap","reason":"interval_too_long","elapsed_s":seconds}
    rx=new.rx_bytes-old.rx_bytes; tx=new.tx_bytes-old.tx_bytes
    if rx<0 or tx<0: return {"status":"reset","reason":"counter_decreased"}
    return {"status":"ok","interface":new.iface,"elapsed_s":seconds,
      "rx_delta_bytes":rx,"tx_delta_bytes":tx,
      "rx_bytes_per_sec":rx/seconds,"tx_bytes_per_sec":tx/seconds,
      "rx_bits_per_sec":rx*8/seconds,"tx_bits_per_sec":tx*8/seconds,
      "source":"linux_interface_counters","vpn_specific":False}
