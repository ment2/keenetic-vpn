"""Bounded HTTP transport candidate; no production defaults or embedded keys."""
import hashlib, hmac, http.server, os, pathlib, tempfile, urllib.request
from crypto import seal, open_sealed
LIMIT = 64 * 1024 * 1024 + 28

def keys(master):
    if len(master) != 32: raise ValueError('key length')
    return tuple(hmac.digest(master, b'keenetic-backup-v1/'+x, 'sha256') for x in (b'encryption', b'receipt'))

def receipt(key, digest):
    return hmac.digest(key, b'accepted:'+digest.encode('ascii'), 'sha256').hex()

def store(root, blob, budget=None, reserve=0):
    root = pathlib.Path(root)
    digest = hashlib.sha256(blob).hexdigest()
    target = root / (digest+'.gcm')
    if target.is_symlink(): raise ValueError('storage conflict')
    if target.exists():
        if not target.is_file() or target.stat().st_size!=len(blob) or target.read_bytes()!=blob: raise ValueError('storage conflict')
        dfd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
        return digest
    if budget is not None:
        from quota import check
        check(root,len(blob),budget,reserve)
    fd, tmp = tempfile.mkstemp(dir=root, prefix='.pending-')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(blob); f.flush(); os.fsync(f.fileno())
        try: os.link(tmp,target)
        except FileExistsError:
            if target.read_bytes() != blob: raise ValueError('storage conflict')
        dfd = os.open(root,os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally: os.unlink(tmp)
    return digest

def receiver(root, master, allowed_ip, bind, *, verify_manifest=True, budget=2*1024**3, reserve=5*1024**3, routes=None):
    # Routes are trusted local configuration, not request-supplied paths.
    if routes is None:
        routes={'/v1/backup':(root,master,budget,None)}
    prepared={path:(directory,*keys(key),quota,expected) for path,(directory,key,quota,expected) in routes.items()}
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def setup(self):
            super().setup(); self.connection.settimeout(15)
        def do_POST(self):
            route=prepared.get(self.path)
            if self.client_address[0] != allowed_ip or route is None:
                self.send_error(403); return
            directory,enc,ack,quota,expected=route
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[])) != 1:
                self.send_error(400); return
            try:
                n=int(self.headers['Content-Length'])
                if not 28 <= n <= LIMIT: raise ValueError('size')
                blob=self.rfile.read(n)
                if len(blob)!=n: raise ValueError('short body')
                plaintext=open_sealed(enc,blob)
                if verify_manifest or expected is not None:
                    from manifest import verify
                    verify(plaintext,expected=expected)
                digest=store(directory,blob,quota,reserve)
            except (ValueError,OSError,EOFError,TypeError,KeyError,AttributeError, __import__('tarfile').TarError):
                self.send_error(400); return
            result=receipt(ack,digest).encode('ascii')
            self.send_response(200); self.send_header('Content-Length',str(len(result))); self.end_headers(); self.wfile.write(result)
    return http.server.HTTPServer(bind,Handler)

def upload(url, master, blob):
    _, ack=keys(master)
    digest=hashlib.sha256(blob).hexdigest()
    req=urllib.request.Request(url,blob,{'Content-Type':'application/octet-stream'},method='POST')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=60) as response:
        got=response.read(65)
    if not hmac.compare_digest(got,receipt(ack,digest).encode('ascii')): raise ValueError('bad receipt')
    return digest

def encrypt_archive(master,data): return seal(keys(master)[0],data)
