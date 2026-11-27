# Geo-independent v23 — crash and packet acceptance, 2026-11-27

Status: production HARD NO-GO. Candidate unchanged. No production config,
updater, pins, wrapper, firewall, routing, kill-switch or cron edits.

## Baseline and staging
Prior report d2bbd98a7b05a24afadfe5b60d099ecf7673349f reviewed.
Staged candidate SHA256 9e22a9b68a2e0fd5b1e66499778662419bc56cd8af491f229401269be2456ecd
reconfirmed. The installed ip command lacks JSON output (exit 255).
tcpdump and iptables-save/ip6tables-save available; unshare absent.

## Journal model, disposable filesystem
CI 46023107769 SUCCESS 197/197, commit 606dac515c2ec4ac3ee21c3b042622b983d474b8.
Seven new tests execute real SIGKILL after durable prepared journal,
first rename, second rename, commit and during recovery. Old generation
restored after uncommitted crash; committed pair retained; interrupted
recovery can resume; unknown generation and corrupt backup reject before
writing. Model uses synthetic files only, fsync and atomic replace.
No power-loss proof, no concurrent uncooperative writer proof, no live
cron journal fencing. Existing wrapper cannot be assumed journal-aware.

## Real kernel packet reference
CI 46023248399 SUCCESS, commit 207ecbb51cef3d2b1625725242c4708684b6bc7f.
Three isolated Linux namespaces, veth only, no external WAN. Real IPv4
netfilter FORWARD and OUTPUT reference drops to synthetic destination.
TCP, UDP, DNS UDP and DNS TCP tested from client and router: 8/8 positive
receipts; 0/8 negative receipts; DROP counters FORWARD=4 and OUTPUT=4.
This is NOT the actual Keenetic chain, IPv6 or TPROXY death path proof.
Live read-only inventory confirms XRAY_KS_HOME has 2 rules including 1
DROP/REJECT, XRAY_WIFI has 11 rules. No physical outage or changes.
Existing RC22 disposable MIPS TCP/UDP death lab and RC45 no-leak report
reviewed for context; neither supplies missing current production proof.

## Coherent full-generation trial and route witness
First bounded attempt fc9485a6-665e-41b0-9313-86df39f7e71f exited 1 with
no output; no probes or validation can be credited. Exact cause unknown.
Live preflight at 18:16:09 MSK: cron updater and old OpenAI both */15;
VLESS collector still running. No RC2 cron line observed.
Added reusable acceptance harness (commit 07be97f9de1a0adc284bf4103921c823498df96c)
with quiet-window and transport budget gates, existing exclusive lock,
four separate route tables/rules snapshots, multiset/order distinction,
redacted shape changes, process/file/IPv4+IPv6 firewall witnesses. Does
not print private routes or export candidate outside a temporary directory.
CI 46023450359 SUCCESS 197/197 (ordinary suite; no claim that CI executed
the hardware harness). Staged harness write verified SHA256
1feb056cb6258d05f5c8f8709493410e3102819551af44828d7c67709a03a12e.
Execution job 53cd0ce1-9b60-4457-a948-ec875e796387 queued; do not resend.
Previous aggregate route mismatch still unexplained; its original per-table
data were not retained. No inferred cause or physical no-leak success.

## Remaining release gates
Resolve result of existing job. Full coherent subscription, real Xray -test,
and unchanged route witnesses must be positively observed. If preflight
aborts, use a newly justified quiet window, not a bypass of the 180-second
transport cap. Resolve any route differences using per-table structure and
independent read-only events. Establish actual independent IPv4/IPv6
TCP/UDP/DNS fail-closed and kill-switch witnesses in disposable equivalent
or separately approved controlled physical trial. Integrate and verify
journal-aware gating before claiming crash-safe updater/pin installation.
Physical install and rollback remain separate approval gates.
