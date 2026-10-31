/* RC9 full-system guest ONLY: own one real Xray direct child, prove identity
 * before owner deliberately crashes. Child uses pre-exec PDEATHSIG from
 * rc9capwrap; independent shell observer must never signal the stale PID.
 */
#define _GNU_SOURCE
#include <sys/wait.h>
#include <sys/types.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
static void fail(const char *x){dprintf(1,"RC9_OWNER: FAIL %s errno=%d\n",x,errno);_exit(67);}
static unsigned long long ticks(pid_t p){
 char path[64],buf[4096];snprintf(path,sizeof(path),"/proc/%d/stat",p);
 FILE *f=fopen(path,"r");if(!f)return 0;
 if(!fgets(buf,sizeof(buf),f)){fclose(f);return 0;}fclose(f);
 char *s=strrchr(buf,')');if(!s)return 0;s+=2;
 int index=3;char *save=NULL;
 for(char *token=strtok_r(s," ",&save);token;token=strtok_r(NULL," ",&save),index++)
   if(index==22)return strtoull(token,NULL,10);
 return 0;
}
static int listener(void){
 FILE *f=fopen("/proc/net/tcp","r");if(!f)return 0;
 char line[512];int found=0;
 while(fgets(line,sizeof(line),f))
   if(strstr(line,":3039 ")){found=1;break;}
 fclose(f);return found;
}
int main(void){
 pid_t kid=fork();if(kid<0)fail("fork");
 if(kid==0){execl("/bin/rc9capwrap","rc9capwrap","raw","xray",(char *)0);fail("exec capwrap");}
 unsigned long long start=0;int ready=0;
 for(int i=0;i<100;i++){
    start=ticks(kid);
    if(start && listener()){ready=1;break;}
    int status=0;
    if(waitpid(kid,&status,WNOHANG)==kid)fail("real Xray died before owner crash");
    usleep(50000);
 }
 if(!ready)fail("Xray listener not ready during parent ownership");
 FILE *f=fopen("/run/rc9-owned-identity","w");if(!f)fail("journal identity");
 fprintf(f,"%d %llu %d\n",kid,start,getpid());
 if(fflush(f)||fsync(fileno(f)))fail("fsync identity");
 fclose(f);
 dprintf(1,"RC9_OWNER: PID_START_TICKS_PINNED_AND_LISTENER_CONFIRMED kid=%d ticks=%llu\n",kid,start);
 dprintf(1,"RC9_OWNER: SELF_SIGKILL_AFTER_PDEATHSIG_CHILD_SPAWN\n");
 fflush(stdout);
 kill(getpid(),SIGKILL); /* only self; never a stale child PID */
 _exit(99);
}
