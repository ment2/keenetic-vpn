/* RC13 Linux4.9 MIPS32LE Malta /init: load pinned archived modules INSIDE QEMU.
 * NO external network, no iptables mutation, no routes, no user process.
 * Module load is kernel evidence, not proof of any TPROXY packet forwarding.
 */
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/mount.h>
#include <sys/syscall.h>
#include <sys/reboot.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/wait.h>

static void logline(const char *msg){dprintf(1,"RC13_GUEST: %s\n",msg);}
static void fail(const char *msg){
 dprintf(1,"RC13_GUEST: HARD_NO_GO_MODULE_RUNTIME %s errno=%d\n",msg,errno);
 sync();reboot(RB_POWER_OFF);_exit(99);
}
static void insmod_pinned(const char *shortname, const char *name){
 char path[100];snprintf(path,sizeof(path),"/mod/%s",shortname);
 FILE *f=fopen(path,"rb");if(!f)fail("missing module");
 if(fseek(f,0,SEEK_END))fail("seek module");
 long n=ftell(f);if(n<1||n>8000000L)fail("module length");
 if(fseek(f,0,SEEK_SET))fail("seek module start");
 char *b=malloc((size_t)n);if(!b)fail("malloc module");
 if(fread(b,1,(size_t)n,f)!=(size_t)n)fail("read module");
 fclose(f);
 if(syscall(SYS_init_module,b,(unsigned long)n,"")!=0){
   dprintf(1,"RC13_GUEST: MODULE_LOAD_FAILED module=%s errno=%d\n",name,errno);
   free(b);fail("init_module syscall");
 }
 free(b);
 dprintf(1,"RC13_GUEST: MODULE_LOAD_OK %s\n",name);
}
static int has_module(const char *name){
 FILE *f=fopen("/proc/modules","r");if(!f)return 0;
 char buf[1024],got[256];int ok=0;
 while(fgets(buf,sizeof(buf),f)){
   if(sscanf(buf,"%255s",got)==1 && !strcmp(got,name)){ok=1;break;}
 }
 fclose(f);return ok;
}
static void run_guest(const char *name,const char *binary,char *const args[]){
 pid_t pid=fork();if(pid<0)fail("fork");
 if(pid==0){execv(binary,args);dprintf(2,"RC18_GUEST: EXECV_FAILED %s errno=%d\n",name,errno);_exit(127);}
 int status=0;
 if(waitpid(pid,&status,0)!=pid||!WIFEXITED(status)||WEXITSTATUS(status)!=0)
   {dprintf(1,"RC18_GUEST: COMMAND_FAILURE %s status=%d\n",name,status);fail("guest userland");}
 dprintf(1,"RC18_GUEST: EXEC_SUCCESS %s\n",name);
}
int main(void){
 setvbuf(stdout,NULL,_IONBF,0);
 mkdir("/proc",0555);mkdir("/sys",0555);
 if(mount("proc","/proc","proc",0,NULL))fail("mount proc");
 if(mount("sysfs","/sys","sysfs",0,NULL))fail("mount sys");
 FILE *f=fopen("/mod/order.txt","r");if(!f)fail("open module order");
 char filename[100],name[100];
 int n=0;
 while(fscanf(f,"%99s %99s",filename,name)==2){
   insmod_pinned(filename,name);n++;
 }
 fclose(f);
 if(n<5)fail("not enough kernel modules");
 const char *required[]={"x_tables","ip_tables","iptable_mangle","xt_socket","xt_TPROXY"};
 for(unsigned i=0;i<sizeof(required)/sizeof(required[0]);i++){
   if(!has_module(required[i])){
     dprintf(1,"RC13_GUEST: REQUIRED_MODULE_NOT_REGISTERED %s\n",required[i]);
     fail("proc modules failed");
   }
 }
 logline("REAL_MIPS49_NETFILTER_XTABLES_TPROXY_MODULES_LOADED");
 char *const ip_args[]={"/bin/ip","-V",NULL};
 char *const table_args[]={"/sbin/iptables","-V",NULL};
 char *const read_args[]={"/sbin/iptables","-t","mangle","-L","-n",NULL};
 run_guest("MIPS_IPROUTE2_VERSION","/bin/ip",ip_args);
 run_guest("MIPS_IPTABLES_VERSION","/sbin/iptables",table_args);
 run_guest("MIPS_IPTABLES_MANGLE_READONLY","/sbin/iptables",read_args);
 logline("MIPS49_USERLAND_EXECUTABLE_LIBC_XTABLES_CLOSURE_SUCCESS");
 logline("NO_GUEST_NIC_IPTABLES_RULES_FWMARK_OR_POLICY_ROUTE");
 logline("HARD_NO_GO_TCP_UDP_PACKET_PATH_NOT_EXECUTED");
 logline("HARD_NO_GO_PRIVILEGED_LEGACY_CGROUP_ESCAPE_AND_PHYSICAL_RESCUE");
 sync();reboot(RB_POWER_OFF);_exit(0);
}
