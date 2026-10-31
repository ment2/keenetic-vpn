/* RC9 - disposable QEMU full-system guest ONLY.
 * Retains ONLY CAP_NET_RAW across transition to UID/GID 65534,
 * raises it ambient for exec, sets NO_NEW_PRIVS and PDEATHSIG after setuid.
 * No SYS_ADMIN, NET_ADMIN or filesystem rights. Parent owns every PID.
 */
#define _GNU_SOURCE
#include <linux/capability.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <grp.h>
#include <unistd.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#ifndef PR_CAP_AMBIENT
#define PR_CAP_AMBIENT 47
#define PR_CAP_AMBIENT_RAISE 2
#endif
static void error(const char *m){dprintf(2,"RC9_CAP: FAIL %s errno=%d\n",m,errno);_exit(70);}
int main(int argc,char **argv){
 if(argc!=3 || strcmp(argv[1],"raw")&&strcmp(argv[1],"none"))error("usage: raw/none socket/xray");
 if(strcmp(argv[2],"socket")&&strcmp(argv[2],"xray"))error("bad target");
 if(geteuid()!=0)error("privileged disposable test setup required");
 int raw=!strcmp(argv[1],"raw");
 if(prctl(PR_SET_KEEPCAPS,1,0,0,0))error("keep caps");
 if(setgroups(0,NULL))error("drop groups");
 if(setresgid(65534,65534,65534))error("drop gid");
 if(setresuid(65534,65534,65534))error("drop uid");
 struct __user_cap_header_struct h={.version=_LINUX_CAPABILITY_VERSION_3,.pid=0};
 struct __user_cap_data_struct caps[2]={{0},{0}};
 if(raw){
   const int n=CAP_NET_RAW/32, bit=CAP_NET_RAW%32;
   caps[n].effective=caps[n].permitted=caps[n].inheritable=1U<<bit;
 }
 if(syscall(SYS_capset,&h,caps))error("set exact capability set");
 if(raw && prctl(PR_CAP_AMBIENT,PR_CAP_AMBIENT_RAISE,CAP_NET_RAW,0,0))
   error("ambient raw for exec");
 if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0))error("no new privileges");
 /* Changing UID/GID clears previous PDEATHSIG on some kernels; reset now. */
 if(prctl(PR_SET_PDEATHSIG,SIGKILL,0,0,0))error("parent death sig");
 if(getppid()==1)error("parent already dead");
 dprintf(1,"RC9_CAP: BEFORE_EXEC target=%s raw=%d uid=%d gid=%d no_new_privs=1\n",
         argv[2],raw,geteuid(),getegid());
 fflush(stdout);
 if(!strcmp(argv[2],"socket")){
   execl("/bin/rc9socket","rc9socket",raw?"raw":"none",(char *)0);
 }else{
   execl("/bin/xray","xray","run","-config","/etc/xray.json",(char *)0);
 }
 error("exec target");
}
