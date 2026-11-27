"""Owner-authorized bounded Hysteria2 handshake diagnostic; no production writes."""
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
def main():
 p=json.loads(Path("/opt/etc/vpn-monitor/dynamic-source-pins.json").read_text())
 assert set(p)==set("xray-update-v23.py setup_xray.py xray_server_check.py xray_openai_probe.py".split()) and p["xray-update-v23.py"]=="b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b5b0be26984041"
 for n,h in p.items():
  f=B/n;st=f.lstat();assert stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&18 and sha(f)==h
 paths=[A,A.with_name("config.pending.json"),D/"full-subscription.json",D/"rc2-probes.json",X];snap=lambda:[sha(p) if p.is_file() else None for p in paths];old=snap()
 assert old[-1]=="680db07db2b5d53080bfecb8752bc830c6a890367aa3bc57d42d4660506591f2"
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
  try:fcntl.flock(lock,6)
  except BlockingIOError:print("MONITOR_LOCK_BUSY");return
  try:fcntl.flock(ul,5)
  except BlockingIOError:print("UPDATER_LOCK_BUSY");return
  for i,l in enumerate(hy,1):
   t=time.localtime();mem=int(next(x.split()[1] for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")))
   gap=((3-t.tm_min)%15)*60-t.tm_sec
   print("RESOURCE",i,"MEM_KIB",mem,"MINUTE",t.tm_min,"SECONDS_TO_RC2",gap,flush=True)
   if mem<81920 or gap<55 or t.tm_min>=58:print("SKIP_RESOURCE_SLOT",i);break
   u=urlsplit(l);q=uq(parse_qsl(u.query,True,True,max_num_fields=32));assert set(q)<={"sni","insecure","obfs","obfs-password","fm"} and q.get("insecure","0")=="0" and q["obfs"]=="salamander" and q["obfs-password"]
   m=json.loads(q["fm"],object_pairs_hook=uq);mask={"udp":[{"type":"salamander","settings":{"password":q["obfs-password"]}}]};v=m["quicParams"]
   assert set(m)=={"udp","quicParams"} and m["udp"]==mask["udp"] and set(v)<={"congestion","keepAlivePeriod","maxIdleTimeout"} and v["congestion"]=="bbr" and u.port==443
   for k,lo,hi in [("keepAlivePeriod",2,60),("maxIdleTimeout",4,120)]:
    if k in v:assert type(v[k]) is int and (v[k]==0 or lo<=v[k]<=hi)
   ips=sorted({x[4][0] for x in socket.getaddrinfo(u.hostname,443,socket.AF_INET,socket.SOCK_DGRAM)});assert ips and all(ipaddress.ip_address(x).is_global for x in ips);print("DNS",i,ips,flush=True)
   devices=set()
   for ip in ips:
    route=sp.run(["ip","route","get",ip],capture_output=True,timeout=5); match=re.search(rb"dev ([A-Za-z0-9_.-]+)",route.stdout);assert route.returncode==0 and match;devices.add(match.group(1).decode());print("ROUTE",i,ip,"DEVICE",match.group(1).decode(),flush=True)
   assert len(devices)==1;device=next(iter(devices))
   with socket.socket() as sk:sk.bind(("127.0.0.1",0));port=sk.getsockname()[1]
   o={"tag":"probe","protocol":"hysteria","settings":{"version":2,"address":u.hostname,"port":443},"streamSettings":{"network":"hysteria","security":"tls","tlsSettings":{"serverName":q.get("sni") or u.hostname,"alpn":["h3"]},"hysteriaSettings":dict(v,version=2,auth=unquote(u.netloc.rsplit("@",1)[0])),"finalmask":mask}}
   cfg={"log":{"loglevel":"debug"},"inbounds":[{"listen":"127.0.0.1","port":port,"protocol":"socks","tag":"in","settings":{"auth":"noauth","udp":False}}],"outbounds":[{"protocol":"blackhole","tag":"blocked"},o],"routing":{"domainStrategy":"AsIs","rules":[{"type":"field","inboundTag":["in"],"outboundTag":"probe"}]}}
   with tempfile.TemporaryDirectory() as td:
    f=Path(td)/"probe.json"
    with os.fdopen(os.open(f,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"w") as w:json.dump(cfg,w)
    with tempfile.TemporaryFile() as logs,tempfile.TemporaryFile() as packets,tempfile.TemporaryFile() as caplog:
     witness=set();phase="CAPTURE_START";x=None;c=None;r=None
     try:
      c=sp.Popen([shutil.which("tcpdump"),"-n","-l","-i",device,"-s","96","-c","512","udp and port 443 and ("+" or ".join("host "+a for a in ips)+")"],stdout=packets,stderr=caplog)
      time.sleep(.5)
      print("CAPTURE_START",i,c.poll(),flush=True)
      phase="XRAY_CONFIG_TEST"
      test=sp.run([str(X),"run","-test","-config",str(f)],stdout=logs,stderr=logs,timeout=12)
      print("CONFIG_TEST",i,test.returncode,flush=True)
      if test.returncode:raise RuntimeError("config test")
      phase="XRAY_START"
      x=sp.Popen([str(X),"run","-config",str(f)],stdout=logs,stderr=logs)
      end=time.monotonic()+6
      while time.monotonic()<end and not owned(x.pid,port):
       if x.poll() is not None:break
       time.sleep(.1)
      own=owned(x.pid,port)
      print("XRAY_START",i,x.poll(),"OWNED",own,flush=True)
      if x.poll() is not None or not own:raise RuntimeError("listener")
      phase="CURL"
      env={k:v for k,v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy","no_proxy")}
      r=sp.Popen([str(B/"curl"),"-q","--noproxy","","--proxy","socks5h://127.0.0.1:%d"%port,"--connect-timeout","10","--max-time","12","-s","-o","/dev/null","-w","%{http_code}","https://www.gstatic.com/generate_204"],stdout=sp.PIPE,stderr=sp.DEVNULL,env=env)
      end=time.monotonic()+14
      while r.poll() is None and time.monotonic()<end:
       witness.update(udp_owned(x.pid,ips));time.sleep(.1)
      out,_=r.communicate(timeout=1)
      print("CURL",i,r.returncode,out.decode() if re.fullmatch(rb"[0-9]{3}",out) else "INVALID","LISTENER_AFTER",owned(x.pid,port),"OWNED_UDP_PORT_COUNT",len(witness),flush=True)
     except Exception as e:
      print("PHASE_ERROR",i,phase,type(e).__name__,flush=True)
     finally:
      if r is not None:stop(r)
      if x is not None:stop(x)
      if c is not None:
       if c.poll() is None:c.send_signal(2)
       try:c.wait(2)
       except sp.TimeoutExpired:stop(c)
     logs.seek(0);s=logs.read(131072).decode(errors="replace").lower();print("LOG",i,{k:s.count(k) for k in ("timeout","no recent network activity","timeout: no recent network activity","certificate","x509","handshake","authentication","authentication failed","connection refused","network is unreachable","failed","quic","no such host","failed to dial","failed to connect","failed to open","drop packet","invalid packet","tls","crypto error","failed to start","failed to load","invalid config","unknown","permission denied","address already in use","failed to listen","no such file","handshake did not complete","unsupported config format","failed to read config","failed to parse","failed to build","config format","failed to decode")})
     packets.seek(0);ls=packets.read(131072).decode(errors="replace").splitlines();caplog.seek(0);cs=caplog.read(8192).decode(errors="replace");drop=re.search(r"(\d+) packets dropped by kernel",cs)
     outp=[l for l in ls if any(" > "+a+".443:" in l for a in ips)];inp=[l for l in ls if any(a+".443 > " in l for a in ips)]
     matched_out=sum(any(re.search(r"\."+str(p)+r" > ",l) for p in witness) for l in outp);matched_in=sum(any(re.search(r"\."+str(p)+r":",l) for p in witness) for l in inp)
     print("PACKETS",i,"OUT",len(outp),"IN",len(inp),"OWNED_PORT_OUT",matched_out,"OWNED_PORT_IN",matched_in,"LINES",len(ls),"KERNEL_DROPS",int(drop.group(1)) if drop else None,flush=True)
   assert sha(A)==old[0]
 print("UNCHANGED",snap()==old)
try:main()
except Exception as e:print("ERR",type(e).__name__);sys.exit(1)
