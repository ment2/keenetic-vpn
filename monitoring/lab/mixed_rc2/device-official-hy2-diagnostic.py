"""Owner-authorized official-client comparison; private USB temporary resources only."""
import sys,json,base64,hashlib,runpy,stat,contextlib,io,fcntl,time,subprocess as sp,socket,os,tempfile,re,ipaddress,shutil
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,unquote
B=Path("/opt/bin");D=Path("/opt/var/lib/vpn-monitor");A=Path("/opt/etc/xray/config.json");X=Path("/opt/sbin/xray")
def sha(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def uq(p):
 d=dict(p);assert len(d)==len(p);return d
def stop(p):
 if p.poll() is None:
  p.terminate()
  try:p.wait(2)
  except sp.TimeoutExpired:p.kill();p.wait(2)
def owned(pid,port):
 try:
  endpoint="0100007F:%04X"%port
  with Path("/proc/net/tcp").open() as f:
   next(f,None)
   ids={p[9] for l in f for p in [l.split()] if len(p)>9 and p[1].upper()==endpoint and p[3]=="0A"}
  if len(ids)!=1:return False
  inode=next(iter(ids))
  for fd in Path("/proc/%d/fd"%pid).iterdir():
   try:
    if os.readlink(fd)=="socket:[%s]"%inode:return True
   except OSError:continue
 except (OSError,ValueError):pass
 return False
def udp_owned(pid,ips):
 try:
  ids=set()
  for f in Path("/proc/%d/fd"%pid).iterdir():
   try:
    a=os.readlink(f)
    if a.startswith("socket:["):ids.add(a[8:-1])
   except OSError:pass
  lines=Path("/proc/net/udp").read_text().splitlines()[1:]
  local={int(x[1].split(":")[1],16) for name in ("udp","udp6") if Path("/proc/net/"+name).is_file() for l in Path("/proc/net/"+name).read_text().splitlines()[1:] for x in [l.split()] if len(x)>9 and x[9] in ids}
  return local
 except (OSError,ValueError):return set()
START=time.monotonic()
DIGEST="df667889840c3976e73abd29880d4a672bb62a88b73bfb7b6c6b4d5406a6907c"
URL="https://github.com/HyNetworks/hysteria/releases/download/app/v2.7.0/hysteria-linux-mipsle-sf"
def memory():
 return int(next(x.split()[1] for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")))
def request(port,kind):
 url={"internet":"https://www.gstatic.com/generate_204","openai":"https://api.openai.com/v1/models","exit_ip":"https://api.ipify.org/?format=json"}[kind]
 args=[str(B/"curl"),"-q","--noproxy","","--proxy","socks5h://127.0.0.1:%d"%port,"--connect-timeout","5","--max-time","8","-s"]
 args+=["--fail","--max-filesize","1024"] if kind=="exit_ip" else ["-o","/dev/null","-w","%{http_code}"]
 return args+[url]
def classify(kind,out,rc):
 if rc:return {"curl_rc":rc}
 if kind!="exit_ip":
  return {"http":out.decode() if re.fullmatch(rb"[0-9]{3}",out) else "INVALID"}
 try:
  ip=ipaddress.ip_address(json.loads(out)["ip"])
  return {"ip":str(ip)} if ip.is_global else {"ip":"NONPUBLIC"}
 except (ValueError,TypeError,KeyError):return {"ip":"INVALID"}
def main(root):
 p=json.loads(Path("/opt/etc/vpn-monitor/dynamic-source-pins.json").read_text())
 assert set(p)==set("xray-update-v23.py setup_xray.py xray_server_check.py xray_openai_probe.py".split()) and p["xray-update-v23.py"]=="b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b5b0be26984041"
 for n,h in p.items():
  f=B/n;st=f.lstat();assert stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&18 and sha(f)==h
 paths=[A,A.with_name("config.pending.json"),D/"full-subscription.json",D/"rc2-probes.json",X];snap=lambda:[sha(p) if p.is_file() else None for p in paths]
 assert sha(X)=="680db07db2b5d53080bfecb8752bc830c6a890367aa3bc57d42d4660506591f2"
 env={k:v for k,v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy","no_proxy")}
 env["GOMEMLIMIT"]="32MiB";env["GOMAXPROCS"]="2"
 exe=root/"hy"
 if memory()<81920:print("SKIP_MEMORY_BEFORE_DOWNLOAD");return
 d=sp.run([str(B/"curl"),"-q","--fail","--silent","--location","--proto","=https","--proto-redir","=https","--connect-timeout","8","--max-time","35","--max-filesize","21299415","--output",str(exe),URL],stdout=sp.DEVNULL,stderr=sp.DEVNULL,timeout=38,env=env)
 print("DOWNLOAD_RC",d.returncode,flush=True)
 if d.returncode:return
 assert exe.stat().st_size==21299415 and sha(exe)==DIGEST
 exe.chmod(0o700);print("BINARY_SHA256_OK",flush=True)
 ver=sp.run([str(exe),"version"],capture_output=True,timeout=8,env=env)
 print("NATIVE_VERSION",ver.returncode,"EXPECTED_VERSION",b"2.7.0" in ver.stdout+ver.stderr,flush=True)
 if ver.returncode or b"2.7.0" not in ver.stdout+ver.stderr:return
 raw=[];orig=Path.read_bytes
 def cap(p):
  b=orig(p)
  if p.name=="subscription":raw.append(b)
  return b
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  sys.path.insert(0,str(B));m=runpy.run_path(str(B/"xray-update-v23.py"),run_name="audit");Path.read_bytes=cap
  try:m["subscription"]()
  finally:Path.read_bytes=orig
 assert len(raw)==1;b=raw[0].strip();d=(b if b"vless://" in b else base64.b64decode(b"".join(b.split()),validate=True)).decode("utf-8-sig");hy=[l.strip() for l in d.splitlines() if l.strip().startswith(("hy2://","hysteria2://"))];assert len(hy)==2
 with (D/"dynamic-probe.lock").open("rb") as lock,Path("/opt/tmp/xray-update.lock").open("rb") as ul:
  try:fcntl.flock(lock,6);fcntl.flock(ul,5)
  except BlockingIOError:print("LOCK_BUSY");return
  old=snap()
  for i,l in enumerate(hy,1):
   t=time.localtime();gap=((3-t.tm_min)%15)*60-t.tm_sec
   print("RESOURCE",i,"MEM_KIB",memory(),"SECONDS_TO_RC2",gap,flush=True)
   if memory()<81920 or gap<58 or t.tm_min>=58 or time.monotonic()-START>112:print("SKIP_RESOURCE_SLOT",i);break
   u=urlsplit(l);q=uq(parse_qsl(u.query,True,True,max_num_fields=32));assert set(q)<={"sni","insecure","obfs","obfs-password","fm"} and q.get("insecure","0")=="0" and q["obfs"]=="salamander" and q["obfs-password"]
   m=json.loads(q["fm"],object_pairs_hook=uq);mask={"udp":[{"type":"salamander","settings":{"password":q["obfs-password"]}}]};v=m["quicParams"]
   assert set(m)=={"udp","quicParams"} and m["udp"]==mask["udp"] and set(v)<={"congestion","keepAlivePeriod","maxIdleTimeout"} and v["congestion"]=="bbr" and u.port==443
   quic={}
   for k,lo,hi in [("keepAlivePeriod",2,60),("maxIdleTimeout",4,120)]:
    if k in v:
     assert type(v[k]) is int and (v[k]==0 or lo<=v[k]<=hi)
     if v[k]:quic[k]=str(v[k])+"s"
   ips=sorted({x[4][0] for x in socket.getaddrinfo(u.hostname,443,socket.AF_INET,socket.SOCK_DGRAM)});assert ips and all(ipaddress.ip_address(x).is_global for x in ips);print("DNS",i,ips,flush=True)
   devices=set()
   for ip in ips:
    route=sp.run(["ip","route","get",ip],capture_output=True,timeout=5);match=re.search(rb"dev ([A-Za-z0-9_.-]+)",route.stdout);assert route.returncode==0 and match;devices.add(match.group(1).decode());print("ROUTE",i,ip,"DEVICE",match.group(1).decode(),flush=True)
   assert len(devices)==1;device=next(iter(devices))
   with socket.socket() as sk:sk.bind(("127.0.0.1",0));port=sk.getsockname()[1]
   cfg={"server":u.hostname+":443","auth":unquote(u.netloc.rsplit("@",1)[0]),"tls":{"sni":q.get("sni") or u.hostname,"insecure":False},"obfs":{"type":"salamander","salamander":{"password":q["obfs-password"]}},"quic":quic,"socks5":{"listen":"127.0.0.1:%d"%port,"disableUDP":True},"lazy":False}
   with tempfile.TemporaryDirectory(dir=root) as td:
    f=Path(td)/"probe.json"
    with os.fdopen(os.open(f,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"w") as w:json.dump(cfg,w)
    with tempfile.TemporaryFile(dir=root) as logs,tempfile.TemporaryFile(dir=root) as packets,tempfile.TemporaryFile(dir=root) as caplog:
     witness=set();x=None;c=None;r=None;ready=False
     try:
      c=sp.Popen([shutil.which("tcpdump"),"-p","-n","-l","-i",device,"-s","96","-c","512","udp and port 443 and ("+" or ".join("host "+a for a in ips)+")"],stdout=packets,stderr=caplog)
      time.sleep(.5);assert c.poll() is None
      x=sp.Popen([str(exe),"client","--disable-update-check","-c",str(f)],stdout=logs,stderr=logs,env=env)
      end=time.monotonic()+12
      while time.monotonic()<end and x.poll() is None:
       witness.update(udp_owned(x.pid,ips))
       if owned(x.pid,port):ready=True;break
       time.sleep(.1)
      print("CLIENT",i,"READY",ready,"EXIT",x.poll(),"MEM_KIB",memory(),flush=True)
      for kind in ("internet","openai","exit_ip"):
       if not ready or x.poll() is not None or not owned(x.pid,port) or memory()<40960:
        print("PROBE",i,kind,"NOT_RUN_NO_OWNED_LISTENER_OR_MEMORY",flush=True);continue
       start=time.monotonic();r=sp.Popen(request(port,kind),stdout=sp.PIPE,stderr=sp.DEVNULL,env=env)
       try:
        end=time.monotonic()+9
        while r.poll() is None and time.monotonic()<end:
         witness.update(udp_owned(x.pid,ips));time.sleep(.1)
        out,_=r.communicate(timeout=1)
        print("PROBE",i,kind,classify(kind,out,r.returncode) if owned(x.pid,port) and x.poll() is None else "OWNER_LOST","MS",round((time.monotonic()-start)*1000),flush=True)
       finally:stop(r);r=None
     except Exception as e:print("PHASE_ERROR",i,type(e).__name__,flush=True)
     finally:
      if r is not None:stop(r)
      if x is not None:stop(x)
      if c is not None:
       if c.poll() is None:c.send_signal(2)
       try:c.wait(2)
       except sp.TimeoutExpired:stop(c)
     logs.seek(0);s=logs.read(131072).decode(errors="replace").lower();print("LOG",i,{k:s.count(k) for k in ("timeout","no recent network activity","certificate","x509","handshake","authentication","connection refused","network is unreachable","failed","connected to server","socks5 server listening","permission denied","invalid","fatal")})
     packets.seek(0);ls=packets.read(131072).decode(errors="replace").splitlines();caplog.seek(0);cs=caplog.read(8192).decode(errors="replace");drop=re.search(r"(\d+) packets dropped by kernel",cs)
     outp=[l for l in ls if any(" > "+a+".443:" in l for a in ips)];inp=[l for l in ls if any(a+".443 > " in l for a in ips)]
     matched_out=sum(any(re.search(r"\."+str(p)+r" > ",l) for p in witness) for l in outp);matched_in=sum(any(re.search(r"\."+str(p)+r":",l) for p in witness) for l in inp)
     print("PACKETS",i,"OUT",len(outp),"IN",len(inp),"OWNED_PORT_OUT",matched_out,"OWNED_PORT_IN",matched_in,"KERNEL_DROPS",int(drop.group(1)) if drop else None,flush=True)
   assert sha(A)==old[0]
  print("UNCHANGED",snap()==old)
try:
 with tempfile.TemporaryDirectory(prefix="rc2-official-hy2-",dir="/opt/tmp") as d:main(Path(d))
 print("TEMP_RESOURCES_REMOVED")
except Exception as e:print("ERR",type(e).__name__);sys.exit(1)
