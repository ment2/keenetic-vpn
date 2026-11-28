#!/usr/bin/env bash
# Disposable isolated acceptance only. Never installs packages or deploys a Worker.
set -euo pipefail
[[ $# == 3 ]] || { echo 'Usage: native-preflight.sh RC3_EXTRACTED_DIR BUILD_DIR ORIGINAL_LEGACY_FILE'; exit 2; }
ROOT=$(realpath "$1"); BUILD=$(realpath "$2"); LEGACY=$(realpath "$3")
check_sha(){ printf '%s  %s\n' "$1" "$2" | sha256sum -c --status || { echo "HASH_MISMATCH: $(basename "$2")"; exit 3; }; }
(cd "$ROOT"; sha256sum -c SHA256SUMS --status)
check_sha 9920663ac095b9f382d5d2db06f1a9422fc72369d3ef895dbc8ba1463413374b "$ROOT/package-lock.json"
K="$BUILD/keenetic/worker"; H="$BUILD/ha"
check_sha 667c25d33ec7848beaf6128d869b8fbd73a3624e3897b22dd9107fc76126e831 "$K/src/worker.mjs"
check_sha bce342a8dc1712813ca736b1f9d7ee85467ebf926876209b07ff8d183aa8970e "$K/src/coordinator.mjs"
check_sha 32a202bde7ee08b1806eac8d8809e605cee497e7d2aba8d72548150c3e1f8645 "$H/rc5.mjs"
[[ $(git hash-object "$LEGACY") == 64e9ae80553852a4ee77c290db13da2e8fa7fc1a ]] || { echo 'ORIGINAL_KEENETIC_LEGACY_BLOB_REQUIRED'; exit 4; }
for pair in 'src/security.mjs e0efa84e301a1607e34a249180d7b7a973c54df5' 'src/readiness-proof.mjs 1658f077c82bf8ce37e2211192a8d63f47689c78' 'mobile-tools.mjs 79007655aef7da084de7c305ec4d705f242737b0'; do read -r p sha <<< "$pair"; [[ $(git hash-object "$K/$p") == "$sha" ]] || { echo "CORE_BLOB_MISMATCH: $p"; exit 3; }; done
# These modules must be exact copies of the RC3 or archived RC2 helper source.
for dir in "$K/src" "$H"; do cmp -s "$ROOT/owner-audit.mjs" "$dir/owner-audit.mjs" || { echo 'OWNER_AUDIT_SIDECAR_MISMATCH'; exit 3; }; cmp -s "$ROOT/owner-binding-rc2/pending-consent.mjs" "$dir/pending-consent.mjs" || { echo 'PENDING_CONSENT_SIDECAR_MISMATCH'; exit 3; }; done
for dir in "$K/src" "$H"; do [[ $(git hash-object "$dir/operation-consent.mjs") == be50254ce19a9680b9928195d464caf4f2e228da && $(git hash-object "$dir/confirmation-contract.mjs") == 3621c9234053bb4369b063654eb4ccb497e88147 ]] || { echo 'CONSENT_SIDECAR_MISMATCH'; exit 3; }; done
# Native package check happens before making a disposable copy. No network request.
(cd "$ROOT"; node -e "for(const [n,v] of [['miniflare','5.20261123.1-beta'],['workerd','1.20261123.1']]){if(JSON.parse(require('node:fs').readFileSync('node_modules/'+n+'/package.json')).version!==v)process.exit(1)}" && node --input-type=module -e "import {Miniflare,convertV4MiniflareOptions} from 'miniflare'; if(typeof Miniflare!=='function'||typeof convertV4MiniflareOptions!=='function')process.exit(1)") || { echo 'BLOCKED_NATIVE_RUNTIME_NOT_INSTALLED'; exit 5; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
cp -a "$K" "$TMP/keenetic"; cp -a "$H" "$TMP/ha"; cp "$LEGACY" "$TMP/keenetic/reference/worker-v4.js"
# The RC3 native harness creates isolated SQLite DOs with synthetic bindings and denies outbound calls.
node "$ROOT/owner-audit-integration.test.mjs" native "$TMP/keenetic/src/worker.mjs" "$TMP/ha/rc5.mjs" "$ROOT"
