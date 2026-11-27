package main
import("fmt";"runtime";"sync";"time")
func main(){
 runtime.GOMAXPROCS(4)
 var mu sync.Mutex
 var wg sync.WaitGroup
 n:=0
 for i:=0;i<32;i++ { wg.Add(1);go func(){ defer wg.Done();for j:=0;j<100;j++ {mu.Lock();n++;mu.Unlock();runtime.Gosched()}}() }
 wg.Wait()
 if n!=3200 {panic("counter mismatch")}
 <-time.After(5*time.Millisecond)
 fmt.Printf("GO_RUNTIME_WITNESS %s count=%d\n",runtime.Version(),n)
}
