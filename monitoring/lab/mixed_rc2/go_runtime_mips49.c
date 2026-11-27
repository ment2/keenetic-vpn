#define _GNU_SOURCE
#include <errno.h>
#include <linux/futex.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
static int child(const char *label,const char *path,int version){
 pid_t p=fork();if(p==0){if(setenv("GOMAXPROCS","4",1))_exit(126);if(version)execl(path,path,"version",(char*)0);else execl(path,path,(char*)0);_exit(127);}
 int s=0;if(p<0||waitpid(p,&s,0)!=p)return -1;
 int rc=WIFEXITED(s)?WEXITSTATUS(s):128+WTERMSIG(s);printf("RUNTIME_RESULT %s rc=%d\n",label,rc);return rc;
}
static int run(void){
 struct utsname u;if(uname(&u))return 1;printf("KERNEL %s ARCH %s\n",u.release,u.machine);
 if(mount("proc","/proc","proc",0,0))return 2;
 if(mount("devtmpfs","/dev","devtmpfs",0,0)){mknod("/dev/urandom",S_IFCHR|0666,makedev(1,9));mknod("/dev/random",S_IFCHR|0666,makedev(1,8));mknod("/dev/null",S_IFCHR|0666,makedev(1,3));}
 int word=0;errno=0;long a=syscall(SYS_futex,&word,FUTEX_WAKE_PRIVATE,1,0,0,0);printf("FUTEX_LEGACY rc=%ld errno=%d\n",a,errno);
 #ifdef SYS_futex_time64
 errno=0;long b=syscall(SYS_futex_time64,&word,FUTEX_WAKE_PRIVATE,1,0,0,0);printf("FUTEX_TIME64 rc=%ld errno=%d\n",b,errno);
 #endif
 int old=child("go1.26.1","/old",0);int fixed=child("go1.26.2","/fixed",0);int x=child("xray26.3.27","/xray",1);
 printf("COMPARISON old=%d fixed=%d release=%d\n",old,fixed,x);
 return (old<0||fixed!=0||x<0)?3:0;
}
int main(void){setvbuf(stdout,NULL,_IONBF,0);int rc=run();printf("GUEST_EXIT %d\n",rc);sync();reboot(RB_POWER_OFF);for(;;)pause();}
