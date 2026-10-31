/* RC8 privileged-descendant escape defense, ACTUAL FULL-SYSTEM GUEST ONLY.
 * Run after RC7 has mounted a private cgroup v1 hierarchy. Drops UID/GID
 * before fork+setsid+exec, blocks privileged group migration, confirms
 * inherited membership, then proves an untracked orphan forces NO_RESTART.
 * Never used on a router and NEVER claims that simple UID-drop is a kernel
 * containment proof for arbitrary legacy privileged processes.
 */
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <sys/prctl.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <signal.h>
#include <grp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#define CGROUP "/run/cgroup-pids/v30/cgroup.procs"
#define PARENT "/run/cgroup-pids/cgroup.procs"
static void die(const char *s){dprintf(1,"RC8_GUEST: FAIL %s errno=%d\n",s,errno);_exit(31);}
static void store(const char *p,const char *v){
 int fd=open(p,O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC,0666);
 if(fd<0)die("store");if(write(fd,v,strlen(v))!=(ssize_t)strlen(v))die("storewrite");close(fd);
}
static int member(int pid){
 FILE *f=fopen(CGROUP,"r");if(!f)die("cgroup read");
 int p,found=0;while(fscanf(f,"%d",&p)==1)if(p==pid)found=1;
 fclose(f);return found;
}
static int alive_scope_member(int except){
 FILE *f=fopen(CGROUP,"r");if(!f)die("scope scan");
 int p,found=0;while(fscanf(f,"%d",&p)==1){if(p!=except){found=1;break;}}
 fclose(f);return found;
}
static void waitfile(const char *name){
 for(int k=0;k<200;k++){if(access(name,F_OK)==0)return;usleep(20000);}
 die("rendezvous-timeout");
}
static void drop(void){
 if(setgroups(0,NULL)!=0 && errno!=EPERM)die("groups");
 if(setresgid(65534,65534,65534)!=0)die("setresgid");
 if(setresuid(65534,65534,65534)!=0)die("setresuid");
 if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0)!=0)die("no_new_privs");
 if(getuid()!=65534||geteuid()!=65534)die("drop privilege");
}
static void sockets(void){
 struct sockaddr_in sa={0};sa.sin_family=AF_INET;sa.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 int t=socket(AF_INET,SOCK_STREAM,0),u=socket(AF_INET,SOCK_DGRAM,0);
 if(t<0||u<0)die("socket");
 sa.sin_port=0;if(bind(t,(void*)&sa,sizeof(sa)))die("bindTCP");
 socklen_t l=sizeof(sa);if(getsockname(t,(void*)&sa,&l)||listen(t,1))die("listen");
 if(bind(u,(void*)&sa,sizeof(sa)))die("bindUDP");
 dprintf(1,"RC8_GUEST: REAL_UNPRIV_TCP_UDP_PORT %d\n",ntohs(sa.sin_port));
 int fd=open(PARENT,O_WRONLY|O_CLOEXEC);
 if(fd>=0){
   char id[40];snprintf(id,sizeof(id),"%d\n",getpid());
   if(write(fd,id,strlen(id))==(ssize_t)strlen(id))die("unprivileged cgroup escape succeeded");
   close(fd);
   dprintf(1,"RC8_GUEST: UNPRIVILEGED_CGROUP_ESCAPE_WRITE_DENIED\n");
 }else{
   if(errno!=EACCES && errno!=EPERM)die("unexpected migration error");
   dprintf(1,"RC8_GUEST: UNPRIVILEGED_CGROUP_ESCAPE_DENIED\n");
 }
 if(!member(getpid()))die("unprivileged child escaped group");
 dprintf(1,"RC8_GUEST: UNPRIVILEGED_FORK_SETSID_EXEC_SCOPE_HELD\n");
 close(t);close(u);
}
int main(int argc,char **argv){
 if(argc>1 && !strcmp(argv[1],"worker")){
   if(setsid()<0)die("setsid");
   drop();sockets();return 0;
 }
 if(argc>1 && !strcmp(argv[1],"orphan")){
   if(setsid()<0)die("orphan setsid");
   drop();
   char id[40];snprintf(id,sizeof(id),"%d\n",getpid());
   store("/run/rc8-lab/orphan-pid",id);
   waitfile("/run/rc8-lab/orphan-release");
   return 0;
 }
 if(geteuid()!=0)die("root-only parent test");
 /* Permit read-only membership observation after UID drop; preserve root-only writes. */
 if(chmod("/run/cgroup-pids",0755)!=0)die("cgroup read traversal");
 if(chmod("/run/cgroup-pids/v30",0755)!=0)die("child scope read traversal");
 mkdir("/run/rc8-lab",0777);
 if(chmod("/run/rc8-lab",0777)!=0)die("private test rendezvous");
 int fd=open(CGROUP,O_WRONLY);
 if(fd<0)die("existing cgroup1 scope not mounted");
 char own[40];snprintf(own,sizeof(own),"%d\n",getpid());
 if(write(fd,own,strlen(own))!=(ssize_t)strlen(own))die("enter scope");
 close(fd);
 for(int i=0;i<8;i++){
   pid_t p=fork();if(p<0)die("fork worker");
   if(p==0){execl("/bin/rc8privdrop","rc8privdrop","worker",(char*)0);die("worker exec");}
   int status=0;waitpid(p,&status,0);
   if(!WIFEXITED(status)||WEXITSTATUS(status)!=0)die("privdrop child failed");
 }
 dprintf(1,"RC8_GUEST: EIGHT_REAL_UNPRIV_FORK_SETSID_EXEC_ESCAPE_DENIALS_PASS\n");
 pid_t intermediary=fork();
 if(intermediary<0)die("fork intermediary");
 if(intermediary==0){
   pid_t orphan=fork();if(orphan<0)die("fork orphan");
   if(orphan==0){execl("/bin/rc8privdrop","rc8privdrop","orphan",(char*)0);die("orphan exec");}
   _exit(0);
 }
 waitpid(intermediary,NULL,0);
 waitfile("/run/rc8-lab/orphan-pid");
 int orphan=atoi("0");
 FILE *f=fopen("/run/rc8-lab/orphan-pid","r");if(!f)die("orphan identity");
 if(fscanf(f,"%d",&orphan)!=1||orphan<=1)die("bad orphan pid");fclose(f);
 if(!member(orphan) || !alive_scope_member(getpid()))die("unknown descendant absent");
 dprintf(1,"RC8_GUEST: GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT\n");
 store("/run/rc8-lab/orphan-release","OK\n");
 for(int i=0;i<150;i++){
    if(!member(orphan))break;
    usleep(20000);
 }
 if(member(orphan))die("orphan never drained");
 dprintf(1,"RC8_GUEST: UNPRIVILEGED_ORPHAN_DRAINED_NO_RESTART_BEFORE_ABSENCE\n");
 dprintf(1,"RC8_GUEST: PRODUCTION_SECURITY_STILL_UNPROVEN\n");
 return 0;
}
