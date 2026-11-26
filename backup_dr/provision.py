"""One-time RSA-OAEP-SHA256 wrapping; private material stays local.
Public PEM and wrapped ciphertext may traverse authenticated admin transport.
Never print, log or transfer the master or RSA private key in plaintext.
"""
import ctypes as C, ctypes.util, hashlib, hmac, os, pathlib, stat
L=C.CDLL(ctypes.util.find_library('crypto') or 'libcrypto.so.3')
P=C.c_void_p; I=C.c_int; Z=C.c_size_t

def bind(n,r,*a):
    f=getattr(L,n); f.restype=r; f.argtypes=a; return f

def ok(v):
    if v!=1: raise ValueError('key operation failed')

def ptr(v):
    if not v: raise ValueError('key allocation failed')
    return v
ctx_new=bind('EVP_PKEY_CTX_new_id',P,I,P)
ctx_for=bind('EVP_PKEY_CTX_new',P,P,P)
ctx_free=bind('EVP_PKEY_CTX_free',None,P)
key_free=bind('EVP_PKEY_free',None,P)
kg_init=bind('EVP_PKEY_keygen_init',I,P)
kg_bits=bind('EVP_PKEY_CTX_set_rsa_keygen_bits',I,P,I)
kg=bind('EVP_PKEY_keygen',I,P,C.POINTER(P))
bio_mem=bind('BIO_s_mem',P)
bio_new=bind('BIO_new',P,P)
bio_buf=bind('BIO_new_mem_buf',P,P,I)
bio_free=bind('BIO_free',I,P)
bio_pending=bind('BIO_ctrl_pending',Z,P)
bio_read=bind('BIO_read',I,P,P,I)
write_pub=bind('PEM_write_bio_PUBKEY',I,P,P)
write_priv=bind('PEM_write_bio_PrivateKey',I,P,P,P,P,I,P,P)
read_pub=bind('PEM_read_bio_PUBKEY',P,P,P,P,P)
read_priv=bind('PEM_read_bio_PrivateKey',P,P,P,P,P)
sha256=bind('EVP_sha256',P)
padding=bind('EVP_PKEY_CTX_set_rsa_padding',I,P,I)
oaep=bind('EVP_PKEY_CTX_set_rsa_oaep_md',I,P,P)
mgf=bind('EVP_PKEY_CTX_set_rsa_mgf1_md',I,P,P)
enc_init=bind('EVP_PKEY_encrypt_init',I,P)
dec_init=bind('EVP_PKEY_decrypt_init',I,P)
enc=bind('EVP_PKEY_encrypt',I,P,P,C.POINTER(Z),P,Z)
dec=bind('EVP_PKEY_decrypt',I,P,P,C.POINTER(Z),P,Z)

def pem(key,private):
    b=ptr(bio_new(bio_mem()))
    try:
        ok(write_priv(b,key,None,None,0,None,None) if private else write_pub(b,key))
        n=bio_pending(b); out=C.create_string_buffer(n)
        if bio_read(b,out,n)!=n: raise ValueError('PEM read')
        return out.raw
    finally: bio_free(b)

def generate():
    c=ptr(ctx_new(6,None)); key=P()
    try:
        ok(kg_init(c)); ok(kg_bits(c,3072)); ok(kg(c,C.byref(key)))
        return pem(key,True),pem(key,False)
    finally:
        if key: key_free(key)
        ctx_free(c)

def transform(material,data,encrypt):
    b=ptr(bio_buf(material,len(material))); key=None; c=None
    try:
        key=ptr((read_pub if encrypt else read_priv)(b,None,None,None))
        c=ptr(ctx_for(key,None)); ok((enc_init if encrypt else dec_init)(c))
        ok(padding(c,4)); ok(oaep(c,sha256())); ok(mgf(c,sha256()))
        f=enc if encrypt else dec; n=Z(); ok(f(c,None,C.byref(n),data,len(data)))
        if n.value>8192: raise ValueError('unexpected RSA size')
        out=C.create_string_buffer(n.value); ok(f(c,out,C.byref(n),data,len(data)))
        return out.raw[:n.value]
    finally:
        if c: ctx_free(c)
        if key: key_free(key)
        bio_free(b)

def wrap(public,master):
    if len(master)!=32: raise ValueError('master size')
    return transform(public,master,True)

def unwrap(private,ciphertext):
    master=transform(private,ciphertext,False)
    if len(master)!=32: raise ValueError('master size')
    return master

def write_secret(path,data):
    path=pathlib.Path(path); parent=path.parent
    if parent.is_symlink() or parent.stat().st_mode & 0o077: raise ValueError('insecure key directory')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def confirmation(master,challenge):
    if len(master)!=32 or len(challenge)!=32: raise ValueError('confirmation input')
    return hmac.digest(master,b'keenetic-dr-provision-v1:'+challenge,'sha256').hex()
