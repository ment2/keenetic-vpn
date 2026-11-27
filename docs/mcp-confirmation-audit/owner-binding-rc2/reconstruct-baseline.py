#!/usr/bin/env python3
"""Reconstruct exact archived Keenetic v5 core modules; ONLY a synthetic legacy catalog stub.
This script is for a disposable test tree, never production deployment.
"""
import argparse, hashlib, pathlib, re, zipfile
p=argparse.ArgumentParser();p.add_argument('ha_rc6_archive');p.add_argument('out');a=p.parse_args()
root=pathlib.Path(a.out);root.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(a.ha_rc6_archive) as z: raw=z.read('release-worker.mjs')
assert hashlib.sha256(raw).hexdigest()=='2972f8fa590b4f8ce15e9221abc34ca527cd703fd002bbf07fda657a530ba9b8'
(root/'ha').mkdir();(root/'ha'/'pristine.mjs').write_bytes(raw);(root/'ha'/'rc5.mjs').write_bytes(raw)
s=raw.decode();k=root/'keenetic'/'worker';(k/'src').mkdir(parents=True);(k/'reference').mkdir()
def mod(name):return s.split('const '+name+'=(()=>{\n',1)[1].split('\nreturn {',1)[0].rstrip('\n')
def put(n,v,sha):
 b=v.encode();h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();assert h==sha,(n,h);(k/n).write_bytes(b);print(n,h,hashlib.sha256(b).hexdigest())
v=mod('__ha_module_3_6').split('// Only a Worker service binding',1)[1];v="import {verifyReadinessProof} from './readiness-proof.mjs';\nimport {response,body,taskFromBody,digest,seal,open,redact,UUID,contentHash} from './security.mjs';\n// Only a Worker service binding"+v;put('src/coordinator.mjs',v.replace('class QueueCoordinator {','export class QueueCoordinator {',1),'a1931c19e31112b15d2cd827142eab7ac31ee4cd')
v=mod('__ha_module_0_2');v=v[v.index('const operations=['):].replace('const __ha_default = {async fetch','export default {async fetch',1);v="import {extensionTools} from '../mobile-tools.mjs';\nimport legacy from '../reference/worker-v4.js';\nimport {response,authorized,body,UUID,redact} from './security.mjs';\nexport {QueueCoordinator} from './coordinator.mjs';\n"+v;put('src/worker.mjs',v,'7d31e40f47ee87cfa93010d59ba38fea15c58497')
v=mod('__ha_module_2_5');v=re.sub(r'^(const (?:UUID|response)=|(?:async )?function (?:authorized|body|redact|contentHash|digest|seal|open|taskFromBody)\()',r'export \1',v,flags=re.M)+'\n';put('src/security.mjs',v,'e0efa84e301a1607e34a249180d7b7a973c54df5')
v=mod('__ha_module_3_7');v=re.sub(r'^(function readinessMessage\(|async function verifyReadinessProof\()',r'export \1',v,flags=re.M)+'\n';put('src/readiness-proof.mjs',v,'1658f077c82bf8ce37e2211192a8d63f47689c78')
v=mod('__ha_module_0_3').replace('const extensionTools=','export const extensionTools=',1).replace('function validateExtension(','export function validateExtension(',1)+'\n';put('mobile-tools.mjs',v,'79007655aef7da084de7c305ec4d705f242737b0')
(k/'reference'/'worker-v4.js').write_text(mod('__ha_module_1_4').replace('const __ha_default =','export default',1)+'\n');print('reference/worker-v4.js = catalog-only synthetic fixture; NOT production source')
import shutil
shutil.copytree(k,root/'keenetic'/'base'/'worker')
