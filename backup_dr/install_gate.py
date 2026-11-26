"""Offline readiness check. Does not install, write secrets or start anything."""
import argparse, hashlib, json, pathlib, sys
from groups import validate, preflight
from group_runtime import TOTAL_BUDGET

def verify_bundle(root):
    root=pathlib.Path(root).resolve()
    record=json.loads((root/'bundle-manifest.json').read_text())
    if record.get('version')!=1 or not record.get('files'): raise ValueError('bad bundle manifest')
    for name,digest in record['files'].items():
        p=root/name
        if p.parent!=root or p.is_symlink() or not p.is_file(): raise ValueError('bad bundle path')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest: raise ValueError('bundle digest mismatch')
    return len(record['files'])

def check_plan(policy, config=None, source_root=None):
    quotas={g:v['quota_bytes'] for g,v in policy['groups'].items()}
    if not quotas or any(type(q) is not int or q<=0 for q in quotas.values()) or sum(quotas.values())>min(TOTAL_BUDGET,policy['total_archive_budget_bytes']): raise ValueError('bad policy quotas')
    result={'configured_budget':sum(quotas.values()),'required_groups':sorted(quotas),'allowlist_verified':False,'installation_authorized':False}
    if config is not None:
        config=validate(config)
        if set(config)!=set(quotas): raise ValueError('incomplete group plan')
        if source_root is None: raise ValueError('source root required')
        result['preflight']=preflight(source_root,config)
        result['allowlist_verified']=all(r['ready'] for r in result['preflight'].values())
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--bundle',required=True); ap.add_argument('--config'); ap.add_argument('--source-root'); a=ap.parse_args()
    root=pathlib.Path(a.bundle); n=verify_bundle(root); policy=json.loads((root/'group-policy-v3.3.json').read_text()); plan=check_plan(policy,json.loads(pathlib.Path(a.config).read_text()) if a.config else None,a.source_root); print(json.dumps({'bundle_files_verified':n,**plan},sort_keys=True)); return 0
if __name__=='__main__': sys.exit(main())
