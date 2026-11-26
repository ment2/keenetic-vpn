import ctypes as C
import ctypes.util
import os

lib = C.CDLL(ctypes.util.find_library('crypto') or 'libcrypto.so.3')
def bind(name, result, *args):
    f = getattr(lib, name); f.restype = result; f.argtypes = args; return f
P=C.c_void_p; I=C.c_int
new=bind('EVP_CIPHER_CTX_new',P)
free=bind('EVP_CIPHER_CTX_free',None,P)
cipher=bind('EVP_aes_256_gcm',P)
init=bind('EVP_CipherInit_ex',I,P,P,P,P,P,I)
update=bind('EVP_CipherUpdate',I,P,P,C.POINTER(I),P,I)
final=bind('EVP_CipherFinal_ex',I,P,P,C.POINTER(I))
ctrl=bind('EVP_CIPHER_CTX_ctrl',I,P,I,I,P)
def check(v):
    if v != 1: raise ValueError('cryptographic operation failed')
def transform(key, nonce, data, tag=None):
    if len(key)!=32 or len(nonce)!=12 or len(data)>64*1024*1024: raise ValueError('invalid input')
    enc=tag is None
    if not enc and len(tag)!=16: raise ValueError('invalid tag')
    ctx=new()
    if not ctx: raise MemoryError()
    try:
        check(init(ctx,cipher(),None,key,nonce,int(enc)))
        out=C.create_string_buffer(len(data)+16); n=I(); m=I()
        check(update(ctx,out,C.byref(n),data,len(data)))
        if not enc: check(ctrl(ctx,0x11,16,tag))
        check(final(ctx,C.byref(out,n.value),C.byref(m)))
        result=out.raw[:n.value+m.value]
        if enc:
            t=C.create_string_buffer(16); check(ctrl(ctx,0x10,16,t)); return result+t.raw
        return result
    finally: free(ctx)
def seal(key,data):
    nonce=os.urandom(12); return nonce+transform(key,nonce,data)
def open_sealed(key,blob):
    if len(blob)<28: raise ValueError('truncated')
    return transform(key,blob[:12],blob[12:-16],blob[-16:])
