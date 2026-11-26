"""Offline RSA envelope for a 32-byte random backup master.
The recovery private key is generated and retained by the owner offline.
No device credentials are collected or exported by this module.
"""
import base64, hashlib, hmac, json
from provision import wrap, unwrap

def fingerprint(public): return hashlib.sha256(public).hexdigest()

def master_id(master):
    if len(master)!=32: raise ValueError('invalid master')
    return hmac.digest(master,b'keenetic-dr/escrow-id/v1','sha256').hex()

def envelope(public, master, pinned_fingerprint):
    if not hmac.compare_digest(fingerprint(public),pinned_fingerprint): raise ValueError('escrow public key mismatch')
    return json.dumps({'version':1,'algorithm':'RSA-OAEP-SHA256','recipient':pinned_fingerprint,'master_id':master_id(master),'wrapped':base64.b64encode(wrap(public,master)).decode('ascii')},sort_keys=True).encode('ascii')

def recover(private, raw, expected_recipient, expected_master_id):
    if len(raw)>4096: raise ValueError('envelope limit')
    e=json.loads(raw)
    if not isinstance(e,dict) or set(e)!={'version','algorithm','recipient','master_id','wrapped'} or e['version']!=1 or e['algorithm']!='RSA-OAEP-SHA256': raise ValueError('invalid envelope')
    if not hmac.compare_digest(e['recipient'],expected_recipient) or not hmac.compare_digest(e['master_id'],expected_master_id): raise ValueError('wrong escrow identity')
    master=unwrap(private,base64.b64decode(e['wrapped'],validate=True))
    if not hmac.compare_digest(master_id(master),expected_master_id): raise ValueError('recovered master mismatch')
    return master
