// RC41 DISPOSABLE TEST-ONLY instrumentation of the actual, pinned Xray v26.2.6
// app/proxyman/inbound/udpWorker. This file is copied into a fresh upstream
// checkout on GitHub Actions. It is NOT a production patch or a public API.
// It cannot read a pre-existing, uninstrumented process's private map.
package inbound

import (
 "context"
 "fmt"
 stdnet "net"
 "os"
 "strings"
 "sync/atomic"
 "testing"
 "time"

 xnet "github.com/xtls/xray-core/common/net"
 "github.com/xtls/xray-core/features/routing"
 "github.com/xtls/xray-core/transport/internet"
 "github.com/xtls/xray-core/transport/internet/stat"
 "golang.org/x/sys/unix"
)

type rc41EchoInbound struct { started atomic.Int64 }
func (*rc41EchoInbound) Network() []xnet.Network {return []xnet.Network{xnet.Network_UDP}}
func (e *rc41EchoInbound) Process(_ context.Context,n xnet.Network,c stat.Connection,_ routing.Dispatcher) error {
 if n!=xnet.Network_UDP{return fmt.Errorf("RC41 network %v",n)}
 e.started.Add(1)
 inner,ok:=c.(*udpConn)
 if !ok{return fmt.Errorf("RC41 expected real udpConn")}
 for {
  packets,err:=inner.ReadMultiBuffer()
  if err!=nil{return err}
  for _,p:=range packets{
   n,writeErr:=c.Write(p.Bytes())
   if n!=len(p.Bytes())&&writeErr==nil{writeErr=fmt.Errorf("partial UDP echo")}
   p.Release()
   if writeErr!=nil{return writeErr}
  }
 }
}
type rc41PrivateRow struct{
 src string
 dest string
 lastActivity int64
 closed bool
}
func rc41Snapshot(w *udpWorker) []rc41PrivateRow{
 w.RLock()
 defer w.RUnlock()
 out:=make([]rc41PrivateRow,0,len(w.activeConn))
 for id,c:=range w.activeConn{
  out=append(out,rc41PrivateRow{
   src:id.src.String(),dest:id.dest.String(),
   lastActivity:atomic.LoadInt64(&c.lastActivityTime),
   closed:c.done.Done(),
  })
 }
 return out
}
func rc41Cookie(t *testing.T,s *stdnet.UDPConn)uint64{
 t.Helper()
 raw,err:=s.SyscallConn()
 if err!=nil{t.Fatal(err)}
 var cookie uint64
 var inner error
 if err:=raw.Control(func(fd uintptr){cookie,inner=unix.GetsockoptUint64(int(fd),unix.SOL_SOCKET,unix.SO_COOKIE)});err!=nil{t.Fatal(err)}
 if inner!=nil||cookie==0{t.Fatalf("RC41 real socket cookie unavailable: %v %d",inner,cookie)}
 return cookie
}
func rc41Identity(t *testing.T)(string,string){
 t.Helper()
 boot,err:=os.ReadFile("/proc/sys/kernel/random/boot_id")
 if err!=nil{t.Fatal(err)}
 stat,err:=os.ReadFile("/proc/self/stat")
 if err!=nil{t.Fatal(err)}
 last:=strings.LastIndex(string(stat),") ")
 if last<0{t.Fatal("RC41 missing stat comm delimiter")}
 f:=strings.Fields(string(stat)[last+2:])
 if len(f)<20||f[19]==""{t.Fatal("RC41 missing start_ticks")}
 bootID:=strings.TrimSpace(string(boot))
 if len(bootID)!=36{t.Fatal("RC41 missing boot_id")}
 return bootID,f[19]
}
func rc41Client(t *testing.T)*stdnet.UDPConn{
 t.Helper()
 c,err:=stdnet.ListenUDP("udp4",&stdnet.UDPAddr{IP:stdnet.ParseIP("127.0.0.1")})
 if err!=nil{t.Fatal(err)}
 return c
}
func rc41Echo(t *testing.T,c *stdnet.UDPConn,target *stdnet.UDPAddr,label string){
 t.Helper()
 data:=[]byte("RC41-INPROCESS-UDP-"+label)
 if _,err:=c.WriteToUDP(data,target);err!=nil{t.Fatal(err)}
 if err:=c.SetReadDeadline(time.Now().Add(3*time.Second));err!=nil{t.Fatal(err)}
 buf:=make([]byte,512)
 n,from,err:=c.ReadFromUDP(buf)
 if err!=nil{t.Fatal(err)}
 if string(buf[:n])!=string(data)||from.Port!=target.Port{
  t.Fatalf("RC41 real echo mismatch payload=%q from=%v",buf[:n],from)
 }
 t.Logf("RC41_REAL_XRAY_PACKET_ECHO %s bytes=%d",label,n)
}
func TestRC41LiveIngressPrivateInventoryAndStaleCapture(t *testing.T){
 boot,ticks:=rc41Identity(t)
 echo:=new(rc41EchoInbound)
 w:=&udpWorker{
  address:xnet.LocalHostIP,port:0,
  stream:&internet.MemoryStreamConfig{},
  proxy:echo,ctx:context.WithValue(context.Background(),"cone",false),
  tag:"rc41-disposable-local-udp",
  activeConn:make(map[connID]*udpConn),
 }
 if err:=w.Start();err!=nil{t.Fatal(err)}
 defer w.Close()
 host,ok:=w.hub.Addr().(*stdnet.UDPAddr)
 if !ok{t.Fatal("RC41 actual worker hub not UDP socket")}
 a:=rc41Client(t);defer a.Close()
 b:=rc41Client(t);defer b.Close()
 cookieA,cookieB:=rc41Cookie(t,a),rc41Cookie(t,b)
 if cookieA==cookieB{
  t.Fatal("RC41 distinct Linux UDP sockets share SO_COOKIE")
 }
 srcA:=a.LocalAddr().(*stdnet.UDPAddr)
 srcB:=b.LocalAddr().(*stdnet.UDPAddr)
 rc41Echo(t,a,host,"A_INITIAL")
 deadline:=time.Now().Add(2*time.Second)
 var saved []rc41PrivateRow
 for time.Now().Before(deadline){
  saved=rc41Snapshot(w)
  if len(saved)==1{break}
  time.Sleep(10*time.Millisecond)
 }
 if len(saved)!=1||saved[0].src!=xnet.UDPDestination(xnet.IPAddress(srcA.IP),xnet.Port(srcA.Port)).String()||
  saved[0].closed {
  t.Fatalf("RC41 private activeConn is not owned by real Xray UDP ingress: %+v",saved)
 }
 if echo.started.Load()!=1{t.Fatalf("RC41 expected one real proxy.Process: %d",echo.started.Load())}
 // The second real Linux socket already exists; it has sent no packet and
 // cannot be discovered as a pre-existing Xray worker association.
 t.Logf("RC41_REAL_INPROCESS_UDP_INVENTORY_A boot=%s pid=%d ppid=%d ticks=%s a=%d cookie=%d b=%d cookie=%d",
   boot,os.Getpid(),os.Getppid(),ticks,srcA.Port,cookieA,srcB.Port,cookieB)
 // An idle connection is retained in the same real Xray activeConn map.
 time.Sleep(4*time.Second)
 idle:=rc41Snapshot(w)
 if len(idle)!=1||idle[0].src!=saved[0].src{
  t.Fatalf("RC41 idle private UDP association disappeared: %+v",idle)
 }
 rc41Echo(t,a,host,"A_AFTER_IDLE")
 if echo.started.Load()!=1{t.Fatal("RC41 old source spawned a second proxy.Process")}
 // Kernel ingress is NOT frozen. Even a complete consistent private map
 // captured under RWMutex is immediately stale when another real packet
 // arrives. We do not mislabel this lock as an atomic kernel freeze.
 frozenView:=rc41Snapshot(w)
 if len(frozenView)!=1{t.Fatal("RC41 pre-commit private view not one")}
 rc41Echo(t,b,host,"B_NEW_AFTER_SNAPSHOT")
 after:=rc41Snapshot(w)
 if len(after)!=2||echo.started.Load()!=2{
  t.Fatalf("RC41 kernel ingress was not frozen: map=%+v process=%d",after,echo.started.Load())
 }
 boot2,ticks2:=rc41Identity(t)
 if boot2!=boot||ticks2!=ticks{t.Fatal("RC41 process boot-id/start-ticks changed")}
 t.Log("RC41_REAL_XRAY_SOURCE_PRIVATE_ACTIVE_CONN_A_IDLE_REUSED_B_CREATED")
 t.Log("RC41_REAL_LINUX_CLIENT_UDP_SOCKET_COOKIES_WITNESSED")
 t.Log("RC41_PRIVATE_SNAPSHOT_RWLOCK_IS_NOT_KERNEL_INGRESS_FREEZE")
 t.Log("RC41_UNINSTRUMENTED_LEGACY_PROCESS_NOT_INSPECTED_OR_MODIFIED")
 t.Log("RC41_HARD_NO_GO_PRODUCTION_NO_ATOMIC_OWNER_COMMIT_OR_PHYSICAL_FENCING")
}
func TestRC41PinnedWorkerPrivateCleanupAfter120s(t *testing.T){
 w:=&udpWorker{address:xnet.LocalHostIP,port:12345,activeConn:make(map[connID]*udpConn)}
 id:=connID{src:xnet.UDPDestination(xnet.LocalHostIP,30404),
            dest:xnet.UDPDestination(xnet.LocalHostIP,19301)}
 c,existed:=w.getConnection(id)
 if existed||len(rc41Snapshot(w))!=1{t.Fatal("RC41 test worker missing original destination keyed row")}
 // Advance only the worker's lastActivityTime, NOT Linux kernel time and
 // not any actual production/legacy Xray process.
 atomic.StoreInt64(&c.lastActivityTime,time.Now().Unix()-121)
 if err:=w.clean();err!=nil{t.Fatal(err)}
 if len(rc41Snapshot(w))!=0{t.Fatal("RC41 pinned Xray inactivity cleanup missed stale entry")}
 t.Log("RC41_PRIVATE_XRAY_WORKER_120S_CLEANER_TEST_ONLY")
}
