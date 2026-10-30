# Production Xray inventory (read-only snapshot, 2026-10-30)

Source: Keenetic Mobile owner-admin read-only shell inspection. **This is a metadata snapshot, not a deployable copy.** Do not place live credentials or the raw active Xray config into Git.

## Environment
- Router: Keenetic Ultra KN-1810 / Entware
- Xray binary: 26.2.6 (linux/mipsle)
- Python: 3.13.9
- Active Xray PID at snapshot: 13546
- Invocation: `/opt/sbin/xray run -config /opt/etc/xray/config.json`
- Free disk: 3.53 GB
- Related running scripts seen: `/opt/etc/init.d/S98xray-wifi`, `/opt/bin/xray-ks-home-watch.sh`, `/opt/bin/xray-watchdog`

## Exact production SHA256
| Production path | SHA256 |
|---|---|
| `/opt/etc/xray/config.json` | `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7` |
| `/opt/bin/update_xray_subscription.py` | `8ec3010e7dbf40009e3649d5af720e17e7fe5a458905cc9836ff4e749cd94e3a` |
| `/opt/bin/xray-update-v23.py` | `00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf` |
| `/opt/bin/xray-update-v23.1.py` | `d1ad8c8eec80b398241db92c303fa8da27dd24a1e3a38468529f9e82c6da4126` |
| `/opt/bin/xray_server_check.py` | `6d8c38107517dca8b6ecfaa0551f71d20897539b9a969ab95cf3d23dc4580c68` |
| `/opt/bin/setup_xray.py` | `d949aedac4dda40ae75ceed32b14eaf1c74fccbc36916262eb7098ce6b40f265` |
| `/opt/bin/xray-watchdog.sh` | `dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08` |
| `/opt/bin/xray-safe-hourly.sh` | `890c242609c1146f5ba6087a1f973fc4a707c82491c0892b96bd60aac261deb5` |
| `/opt/bin/xray_openai_probe.py` | `1ca2484d5ec6ed4794ea980b07a3921eebd975b2875868b2430baa441a06e4b7` |
| `/opt/etc/init.d/S97xray` | `87ea1dc13a9be95d57c0595d7a7f13b03fe97bd56ab1f144a3c94d57cc588d5d` |
| `/opt/etc/init.d/S99xray-watchdog` | `e8423e15ed2cf4d3662e5725d27d6e58bd08bbdd807b47fcabe30391ac4c738b` |

## Follow-up
- Additional inventory job `aff33140-4c03-4120-94a3-118171453537` was queued. Retrieve its result; **do not resubmit**.
- Compare production source hashes against archive GitHub file content hashes; exact equality has **not yet been established**.
- Read only non-secret source files to capture production-only scripts and differences; preserve their contents exactly.
- For live config, retain only metadata, validated redacted templates, and checksum. Never commit private upstream credentials.
- No production changes were made.
