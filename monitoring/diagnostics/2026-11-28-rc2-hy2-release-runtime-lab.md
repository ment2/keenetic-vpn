# RC2 Hysteria2: release interoperability and MIPS Go runtime regression

Date: 2026-11-28 MSK. Baseline report `ff6a6eee95a2b8b25bfbb24ae9de6e1d6de1c9d0`. Branch `feature/rc2-hysteria2-monitor-candidate-20261127`. Scope: public upstream research, disposable synthetic-only CI. No router jobs or production changes in this iteration. No real subscription, provider endpoint, user credentials or external destination traffic in the test environments.

## Upstream root cause

- Xray issues [5882](https://github.com/XTLS/Xray-core/issues/5882), [5926](https://github.com/XTLS/Xray-core/issues/5926), [6270](https://github.com/XTLS/Xray-core/issues/6270): reported 26.3.27 MIPS/Keenetic startup crash in runtime.futexwakeup with return -89. Issue 5926 closed as duplicate of 5882; 6270 likewise referred to the Go runtime issue. A reported working older configuration is not evidence that all providers work.
- Go [77730](https://github.com/golang/go/issues/77730) and [77731](https://github.com/golang/go/issues/77731): MIPS ENOSYS is 89, not 38; unsupported futex_time64 on older kernels fails to fall back correctly. Backport [9fe1db7e7e4b51b594f32d4ef34b2ddfabe14a68](https://github.com/golang/go/commit/9fe1db7e7e4b51b594f32d4ef34b2ddfabe14a68) changes _ENOSYS from 0x26 to 0x59 for MIPS and MIPS64. Included in Go 1.26.2. This startup fault is independent of provider credentials or QUIC traffic.
- Official Xray 26.2.6 AMD64 release built with Go 1.25.7 and apernet/quic-go v0.57.2-0.20260111184307-eec823306178. Official 26.3.27 AMD64/MIPS32LE uses Go 1.26.1; apernet/quic-go v0.59.1-0.20260217092621-db4786c77a22 on AMD64. Modern release moves QUIC parameters into finalmask.quicParams; legacy fields are not a reliable configuration contract in the new version. See [release comparison](https://github.com/XTLS/Xray-core/compare/v26.2.6...v26.3.27). No production parser changes.

## Laboratory A: release interoperability and native runtime reproduction

Source commit `c5cf82e6b765ea4d76ca557572efa8874454d4ae`; workflow `.github/workflows/rc2-release-runtime-lab.yml`; CI [46072485533](https://github.com/ment2/keenetic-vpn/actions/runs/46072485533), all three jobs SUCCESS. Public artifacts checked against pinned SHA256 before execution. Both AMD64 releases tested against the same pinned Hysteria2 2.7.1 synthetic localhost service in private loopback-only namespaces, with separate HTTP witness and verified TLS, using version-appropriate synthetic fixture schema. No real provider or subscription.

| Job | Positive | Negative |
|---|---|---|
| 140752456605, 26.2.6 legacy | plain and Salamander: all four owned observations | wrong auth, TLS name, mask, absent mask: no HTTP witness |
| 140752456758, 26.3.27 modern | plain and Salamander: all four owned observations | wrong auth, TLS name, mask, absent mask: no HTTP witness |

Job `140752456329`: pinned full-system Debian MIPS Malta Linux 4.9.228 (4.9.0-13-4kc-malta), no NIC, no network backend. Minimal Go fixtures with identical source and forced GOMAXPROCS=4; official Xray 26.3.27 MIPS32LE only invoked with version argument. Serial evidence:

```
FUTEX_LEGACY rc=0 errno=0
FUTEX_TIME64 rc=-1 errno=89
futexwakeup ... returned -89
SIGSEGV: segmentation violation
RUNTIME_RESULT go1.26.1 rc=2
GO_RUNTIME_WITNESS go1.26.2 count=3200
RUNTIME_RESULT go1.26.2 rc=0
futexwakeup ... returned -89
SIGSEGV: segmentation violation
RUNTIME_RESULT xray26.3.27 rc=2
COMPARISON old=2 fixed=0 release=2
GUEST_EXIT 0
```

The CI passes because the experiment records the expected runtime fault and verifies the corrected Go probe. It does NOT mean the official MIPS32LE Xray 26.3.27 passed startup. A prior exact Entware 26.2.6-1 binary reported Go 1.26.1 and passed synthetic Hysteria2 on Linux 4.9; that earlier guest used one CPU and the test conditions/build provenance differ. Do not infer the cause of that distinction without further evidence.

Regression CI [46072485387](https://github.com/ment2/keenetic-vpn/actions/runs/46072485387): 59 candidate + 276 legacy tests, real MQTT and both loopback architectures SUCCESS.

## Laboratory B: modern source with fixed Go in full-system MIPS Linux 4.9

Source commit `020d5613c3877f9fd8465546b3f434a9e5307a9f`, workflow `.github/workflows/rc2-modern-fixed-go-mips49.yml`, CI [46072720408](https://github.com/ment2/keenetic-vpn/actions/runs/46072720408), job `140753223851` SUCCESS. Exact upstream Xray v26.3.27 source revision `d2758a023cd7f4174a5a5fa4ff66e487d4342ba0`, Go 1.26.2, linux/mipsle, softfloat, CGO disabled. CI-only reconstructed executable SHA256 `64842c05a61ba0583b4fe4bdc0f8c258ecf3a7fc272884b70b66338309619abd`. This is a laboratory build, not a production release or installation candidate. A pinned synthetic Hysteria2 2.7.0 server and HTTP witness ran in the same full-system MIPS guest without NIC or network backend, using verified synthetic TLS and Salamander. Serial evidence:

```
KERNEL 4.9.0-13-4kc-malta ARCH mips
GUEST_HTTP_WITNESS
MODERN_FIXED_GO_MIPS49_SYNTHETIC_HTTP204_PASS
GUEST_CHILDREN_REAPED
GUEST_EXIT 0
```

Separate regression CI [46072720323](https://github.com/ment2/keenetic-vpn/actions/runs/46072720323): all four jobs SUCCESS.

## Decision and remaining limitations

Both versions interoperate with synthetic Hysteria2 peers under the tested conditions. The official 26.3.27 MIPS startup regression is reproduced independently of the network; the corrected Go runtime and modern source can pass an isolated old-kernel laboratory. These findings do not establish that the real Lithuanian provider requires the newer Xray or that the new build would resolve its timeout. The kernel is Debian Malta 4.9, not the physical vendor NDM kernel. No real profile protocol/entry/port has been independently confirmed from the phone; the egress IP and app core version alone are insufficient to establish profile identity. Earlier physical capture for 26.2.6 recorded outgoing UDP but no incoming packets; no new real-path evidence in this iteration. No changes to production, VPN, updater, firewall, routes, or installed binaries. No repeat or rerouting of the previously blocked physical client launch. Physical admission and independent no-leak verification remain HARD NO-GO. A provider-side confirmation of the actual profile and supported core versions is the next appropriate independent source of evidence. No secrets or raw phone logs committed.
