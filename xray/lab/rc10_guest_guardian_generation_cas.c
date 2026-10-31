/* RC10 disposable full-system Linux 4.9 guardian CAS journal contract.
 * 3 rounds of 8 actual simultaneous child processes with their own
 * independent flock FD. Exactly one owner can advance each generation;
 * incomplete PREPARED writes do not advance and are not auto-replayed.
 * All files are private guest /run, no router process or filesystem touch.
 */
#define _GNU_SOURCE
#include <sys/file.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <signal.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#define LEDGER "/run/rc10-generation"
#define LOCK "/run/rc10-generation.lock"
static void fail(const char *why){dprintf(1,"RC10_CAS: FAIL %s errno=%d\n",why,errno);_exit(91);}
static int state(void){
 int fd=open(LEDGER,O_RDONLY|O_CLOEXEC);if(fd<0)fail("open state");
 char b[32]={0};ssize_t n=read(fd,b,sizeof(b)-1);close(fd);
 if(n<=0)fail("read state");
 char *end=NULL;long v=strtol(b,&end,10);
 if(end==b||v<0||v>100)fail("corrupt state");
 return (int)v;
}
static void durable(int v,int pid){
 char path[120],data[40];snprintf(path,sizeof(path),"/run/rc10-prepared.%d",pid);
 int fd=open(path,O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC,0600);
 if(fd<0)fail("prepare");
 snprintf(data,sizeof(data),"%d\n",v);
 if(write(fd,data,strlen(data))!=(ssize_t)strlen(data))fail("write prepared");
 if(fsync(fd))fail("file fsync");
 if(close(fd))fail("file close");
 if(rename(path,LEDGER))fail("rename committed");
 fd=open("/run",O_RDONLY|O_DIRECTORY|O_CLOEXEC);
 if(fd<0||fsync(fd))fail("directory fsync");
 close(fd);
}
static void wave(int expect,int next){
 int go[2];if(pipe(go))fail("pipe");
 pid_t p[8];int wins=0,stale=0;
 for(int i=0;i<8;i++){
   p[i]=fork();if(p[i]<0)fail("fork");
   if(p[i]==0){
     close(go[1]);
     char x;if(read(go[0],&x,1)!=1)_exit(80);close(go[0]);
     int fd=open(LOCK,O_CREAT|O_RDWR|O_CLOEXEC,0600);
     if(fd<0||flock(fd,LOCK_EX))_exit(81);
     int old=state();
     if(old!=expect){flock(fd,LOCK_UN);close(fd);_exit(20);}
     durable(next,getpid());flock(fd,LOCK_UN);close(fd);_exit(0);
   }
 }
 close(go[0]);for(int i=0;i<8;i++)if(write(go[1],"G",1)!=1)fail("barrier");
 close(go[1]);
 for(int i=0;i<8;i++){
   int st=0;if(waitpid(p[i],&st,0)!=p[i]||!WIFEXITED(st))fail("wait");
   if(WEXITSTATUS(st)==0)wins++;
   else if(WEXITSTATUS(st)==20)stale++;
   else fail("guardian unexpected failure");
 }
 if(wins!=1 || stale!=7 || state()!=next)fail("CAS not exactly once");
 dprintf(1,"RC10_CAS: REAL_LINUX49_EIGHT_GUARDIANS_ONE_COMMIT_GENERATION_%d\n",next);
}
static void interrupted(void){
 pid_t p=fork();if(p<0)fail("fork crash");
 if(p==0){
   int fd=open(LOCK,O_CREAT|O_RDWR|O_CLOEXEC,0600);
   if(fd<0||flock(fd,LOCK_EX))_exit(88);
   int prep=open("/run/rc10-interrupted-prepared",O_CREAT|O_EXCL|O_WRONLY,0600);
   if(prep<0)_exit(88);
   if(write(prep,"3\n",2)!=2||fsync(prep))_exit(88);
   close(prep);
   dprintf(1,"RC10_CAS: INJECT_GUARDIAN_CRASH_AFTER_PREPARED_BEFORE_COMMIT\n");
   fflush(stdout);
   kill(getpid(),SIGKILL);
   _exit(99);
 }
 int st=0;waitpid(p,&st,0);
 if(!WIFSIGNALED(st)||WTERMSIG(st)!=SIGKILL||state()!=2)fail("crashed guardian changed committed generation");
 dprintf(1,"RC10_CAS: CRASH_DID_NOT_ADVANCE_GENERATION_OR_REPLAY_PREPARED\n");
}
int main(void){
 int fd=open(LEDGER,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
 if(fd<0)fail("initial state");
 if(write(fd,"0\n",2)!=2||fsync(fd))fail("fsync init");
 close(fd);
 wave(0,1);
 wave(1,2);
 interrupted();
 wave(2,3);
 dprintf(1,"RC10_CAS: REAL_LINUX49_8X3_GENERATION_FLOCK_PREPARED_CRASH_RECOVERY_PASS\n");
 dprintf(1,"RC10_CAS: LIMITATION guest-only CAS, not whole physical legacy S97 S98 watchdog\n");
 return 0;
}
