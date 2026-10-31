/* RC11 disposable QEMU MIPS32LE Malta full-system Linux 4.9 /init.
 * Every child is owned by this init or its direct owner; no router access,
 * no killall, no outside network, no production package management.
 * This test proves MIPS guest kernel + real Xray socket permissions, NOT
 * an end-to-end MIPS iptables TPROXY packet flow or Keenetic hardware.
 */
#define _GNU_SOURCE
#include <sys/utsname.h>
#include <sys/types.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>

static void line(const char *msg){dprintf(1,"%s\n",msg);fsync(1);}
static void fail(const char *msg){dprintf(1,"RC11_MIPS49: HARD_NO_GO %s errno=%d\n",msg,errno);sync();reboot(RB_POWER_OFF);_exit(92);}
static int run(const char *name,const char *a,const char *b){
 pid_t p=fork();if(p<0)fail("fork");
 if(!p){execl(name,name,a,b,(char *)NULL);_exit(127);}
 int st=0;if(waitpid(p,&st,0)!=p)fail("wait owned child");
 if(!WIFEXITED(st))return -1;
 return WEXITSTATUS(st);
}
static int live_tcp(void){
 FILE *f=fopen("/proc/net/tcp","r");if(!f)return 0;
 char buf[300];int result=0;
 while(fgets(buf,sizeof(buf),f))if(strstr(buf,":3039 ") && strstr(buf," 0A ")){result=1;break;}
 fclose(f);return result;
}
static int proc_state(pid_t p,unsigned long long *ticks,char *state){
 char path[60],linebuf[4096];snprintf(path,sizeof(path),"/proc/%ld/stat",(long)p);
 FILE *f=fopen(path,"r");if(!f)return -1;
 if(!fgets(linebuf,sizeof(linebuf),f)){fclose(f);return -1;}fclose(f);
 char *s=strrchr(linebuf,')');if(!s)return -1;
 s+=2;char *save=NULL;int column=3;
 for(char *t=strtok_r(s," ",&save);t;t=strtok_r(NULL," ",&save),column++){
   if(column==3)*state=t[0];
   if(column==22){*ticks=strtoull(t,NULL,10);return *ticks?0:-1;}
 }
 return -1;
}
static int check_caps(pid_t p){
 char name[60],linebuf[220];snprintf(name,sizeof(name),"/proc/%ld/status",(long)p);
 FILE *f=fopen(name,"r");if(!f)return 0;
 int uid=-1, caps=0;
 while(fgets(linebuf,sizeof(linebuf),f)){
  if(!strncmp(linebuf,"Uid:",4))sscanf(linebuf,"Uid: %d",&uid);
  if(!strncmp(linebuf,"CapEff:",7)){
    unsigned long long value=0;
    if(sscanf(linebuf,"CapEff: %llx",&value)==1 && value==0x2000ULL)caps=1;
  }
 }
 fclose(f);return uid==65534 && caps;
}
static void no_net(const char *s){
 dprintf(1,"RC11_MIPS49: %s; NO_MIPS_IPTABLES_TPROXY_PACKET_TOPOLOGY; HARD_NO_GO\n",s);
}
int main(void){
 setvbuf(stdout,NULL,_IONBF,0);
 mkdir("/proc",0555);mkdir("/sys",0555);mkdir("/run",0755);mkdir("/tmp",01777);
 mkdir("/etc",0755);
 if(mount("proc","/proc","proc",0,NULL))fail("mount proc");
 if(mount("sysfs","/sys","sysfs",0,NULL))fail("mount sysfs");
 struct utsname u={0};if(uname(&u))fail("uname");
 if(strncmp(u.release,"4.9.",4)||(!strstr(u.machine,"mips")&&!strstr(u.machine,"MIPS")))
   fail("not a real MIPS32LE Linux49 guest");
 dprintf(1,"RC11_MIPS49: REAL_FULLSYSTEM_KERNEL_BOOT uname=%s arch=%s\n",u.release,u.machine);
 if(run("/bin/rc9capwrap","none","socket"))fail("no-cap socket denial not established");
 line("RC11_MIPS49: IN_GUEST_UNPRIVILEGED_TRANSPARENT_SOCKETS_DENIED");
 if(run("/bin/rc9capwrap","raw","socket"))fail("raw-only MIPS TCP UDP IP_TRANSPARENT");
 line("RC11_MIPS49: IN_GUEST_ONLY_CAP_NET_RAW_TCP_UDP_IP_TRANSPARENT_PASS");
 if(run("/bin/rc7cgroup",NULL,NULL))fail("real MIPS kernel49 cgroup v1 and privileged descendant escape test");
 line("RC11_MIPS49: PRIVILEGED_ESCAPE_NATIVELY_OBSERVED_IN_MIPS_CGROUP_V1_HARD_NO_GO");
 if(run("/bin/rc8privdrop",NULL,NULL))fail("MIPS guest unprivileged detached child containment test");
 line("RC11_MIPS49: EIGHT_UNPRIVILEGED_DESCENDANTS_AND_UNKNOWN_ORPHAN_NO_RESTART_PASS");
 if(run("/bin/rc10cas",NULL,NULL))fail("three waves guardian CAS");
 line("RC11_MIPS49: REAL_8X3_FLOCK_CAS_PREPARED_CRASH_RECONCILE_PASS");
 pid_t x=fork();if(x<0)fail("fork xray");
 if(!x){execl("/bin/rc9capwrap","rc9capwrap","raw","xray",(char *)NULL);_exit(127);}
 unsigned long long original=0;
 int ready=0;
 for(int i=0;i<350;i++){
   char state=0;unsigned long long t=0;
   if(proc_state(x,&t,&state)==0 && t){
      if(!original)original=t;
      if(original!=t)fail("xray PID/start ticks changed");
   }
   if(live_tcp() && check_caps(x)){ready=1;break;}
   int st=0;
   if(waitpid(x,&st,WNOHANG)==x)fail("xray died before TPROXY listener ready");
   usleep(100000);
 }
 if(!ready)fail("real MIPS Xray restricted inbound did not start");
 line("RC11_MIPS49: REAL_MIPS_XRAY_26_2_6_UID65534_CAP_NET_RAW_ONLY_INBOUND_PASS");
 if(kill(x,SIGTERM))fail("signal owned unreaped direct child");
 int st=0;if(waitpid(x,&st,0)!=x)fail("wait owned Xray");
 if(live_tcp())fail("Xray listener survived child exit");
 line("RC11_MIPS49: PARENT_OWNED_MIPS_XRAY_NO_STALE_PID_SIGNAL_LISTENER_DRAIN_PASS");
 no_net("REAL_MIPS49_FULL_TPROXY_PACKETS_NOT_TESTED");
 line("RC11_MIPS49: PHYSICAL_KEENETIC_NDM5_PRODUCTION_HARD_NO_GO");
 sync();
 reboot(RB_POWER_OFF);
 _exit(0);
}
