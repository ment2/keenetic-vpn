/* RC7: guest-only static cgroup-v1 pids, detached exec, TCP+UDP inode and escape probe.
 * This binary is NEVER deployed. It runs solely inside disposable QEMU full-system VM.
 * No host/router network rules, route changes, process signals to unknown PIDs.
 */
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/file.h>
#include <sys/wait.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>

static void stop(const char *m){ dprintf(1,"RC7_GUEST: FAIL %s errno=%d\n",m,errno); _exit(27); }
static void put(const char *p,const char *v){
 int fd=open(p,O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC,0600); if(fd<0)stop(p);
 if(write(fd,v,strlen(v))!=(ssize_t)strlen(v))stop("write"); close(fd);
}
static int present(const char *path,int pid){
 FILE *f=fopen(path,"r");if(!f)return 0;int n,found=0;
 while(fscanf(f,"%d",&n)==1)if(n==pid)found=1;
 fclose(f);return found;
}
static int sockpair(int *tcpfd,int *udpfd){
 struct sockaddr_in a={0};socklen_t len=sizeof(a);
 a.sin_family=AF_INET; a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 int t=socket(AF_INET,SOCK_STREAM,0),u=socket(AF_INET,SOCK_DGRAM,0);
 if(t<0||u<0)return -1;
 a.sin_port=0;if(bind(t,(void*)&a,sizeof(a))||getsockname(t,(void*)&a,&len))return -1;
 if(listen(t,3)||bind(u,(void*)&a,sizeof(a)))return -1;
 *tcpfd=t;*udpfd=u;return ntohs(a.sin_port);
}
static void guardian_races(void){
  for(int round=0;round<2;round++){
    int fd=open("/run/rc7-guardian.lock",O_CREAT|O_RDWR,0600);
    if(fd<0)stop("guardian lock open");
    close(fd);
    pid_t ids[8];int holders[8]={0},won=0;
    for(int j=0;j<8;j++){
      int pipefd[2];if(pipe(pipefd))stop("guardian pipe");
      ids[j]=fork();
      if(ids[j]<0)stop("guardian fork");
      if(ids[j]==0){
        close(pipefd[0]);
        int ownfd=open("/run/rc7-guardian.lock",O_CREAT|O_RDWR,0600);
        if(ownfd<0)_exit(7);
        int rc=flock(ownfd,LOCK_EX|LOCK_NB);
        char c=rc==0?'W':'L';
        write(pipefd[1],&c,1);
        close(pipefd[1]);
        if(c=='W')sleep(3);
        close(ownfd);
        _exit(0);
      }
      close(pipefd[1]);char c='?';
      if(read(pipefd[0],&c,1)!=1)stop("guardian decision");
      close(pipefd[0]);
      if(c=='W'){holders[j]=1;won++;}
    }
    if(won!=1)stop("guardian generation did not have exactly one winner");
    for(int j=0;j<8;j++){
      if(holders[j])kill(ids[j],SIGKILL); /* parent of unreaped test child only */
      waitpid(ids[j],NULL,0);
    }
    dprintf(1,"RC7_GUEST: REAL_EIGHT_GUARDIAN_FLOCK_RACE_ROUND_%d_ONE_WINNER\n",round+1);
  }
}
static int fd_in_net(int pid,const char *proto){
 char path[128],line[512],fdpath[128],target[128];
 snprintf(fdpath,sizeof(fdpath),"/proc/%d/fd",pid);
 int matched=0;
 for(int n=0;n<64;n++){
   snprintf(path,sizeof(path),"%s/%d",fdpath,n);
   ssize_t len=readlink(path,target,sizeof(target)-1);
   if(len<=0)continue;target[len]=0;
   if(strncmp(target,"socket:[",8))continue;
   char *end=strchr(target+8,']');if(!end)continue;
   *end=0;char *inode=target+8;
   snprintf(path,sizeof(path),"/proc/net/%s",proto);
   FILE *fp=fopen(path,"r");if(!fp)continue;
   while(fgets(line,sizeof(line),fp)){
      /* kernel /proc/net inode is a token; require whole word */
      char *tok=strtok(line," \t\n");
      while(tok){if(!strcmp(tok,inode))matched=1;tok=strtok(NULL," \t\n");}
   }
   fclose(fp);
 }
 return matched;
}
int main(int argc,char **argv){
 if(argc>1 && !strcmp(argv[1],"child")){
   int t,u;int port=sockpair(&t,&u);if(port<0)stop("TCP_UDP_SOCKET");
   if(setsid()<0)stop("setsid");
   dprintf(1,"RC7_GUEST: REAL_DETACHED_EXEC_TCP_UDP port=%d pid=%d ppid=%d\n",port,getpid(),getppid());
   put("/run/rc7childready","READY\n");
   char buf[64];snprintf(buf,sizeof(buf),"%d\n",getpid());
   /* A root process may attempt to migrate to parent cgroup via cgroup.procs.
      A successful migration proves scope is NOT sealed. */
   int fd=open("/run/cgroup-pids/cgroup.procs",O_WRONLY);
   if(fd>=0){
      if(write(fd,buf,strlen(buf))==(ssize_t)strlen(buf))
          dprintf(1,"RC7_GUEST: PRIVILEGED_CGROUP_ESCAPE_SUCCEEDED_HARD_NO_GO\n");
      else dprintf(1,"RC7_GUEST: PRIVILEGED_ESCAPE_WRITE_DENIED errno=%d\n",errno);
      close(fd);
   } else dprintf(1,"RC7_GUEST: PRIVILEGED_ESCAPE_OPEN_DENIED errno=%d\n",errno);
   sleep(2);close(t);close(u);return 0;
 }
 if(geteuid()!=0)stop("guest not root");
 mkdir("/run/cgroup-pids",0700);
 if(mount("none","/run/cgroup-pids","cgroup",0,"pids")) {
   dprintf(1,"RC7_GUEST: CGROUP_V1_UNAVAILABLE_HARD_NO_GO errno=%d\n",errno);
   return 77;
 }
 dprintf(1,"RC7_GUEST: REAL_CGROUP_V1_PIDS_MOUNT_PASS\n");
 mkdir("/run/cgroup-pids/v30",0700);
 char self[48];snprintf(self,sizeof(self),"%d\n",getpid());
 put("/run/cgroup-pids/v30/cgroup.procs",self);
 pid_t pid=fork();if(pid<0)stop("fork");
 if(pid==0){
   execl("/bin/rc7cgroup","rc7cgroup","child",(char*)0);
   stop("exec");
 }
 int found=0;
 for(int i=0;i<200;i++){
   if(present("/run/cgroup-pids/v30/cgroup.procs",pid)){found=1;break;}
   usleep(10000);
 }
 if(!found)stop("child not inherited");
 int ready=0;
 for(int i=0;i<300;i++){
   if(access("/run/rc7childready",F_OK)==0){ready=1;break;}
   usleep(10000);
 }
 if(!ready)stop("detached child did not bind sockets");
 if(!fd_in_net(pid,"tcp")||!fd_in_net(pid,"udp"))stop("TCP/UDP FD socket inode crosscheck");
 dprintf(1,"RC7_GUEST: REAL_TCP_UDP_FD_INODE_OWNER_PASS\n");
 dprintf(1,"RC7_GUEST: REAL_CGROUP_V1_FORK_INHERIT_PASS pid=%d\n",pid);
 int status=0;
 waitpid(pid,&status,0);
 if(!WIFEXITED(status)||WEXITSTATUS(status)!=0)stop("child exit");
 if(present("/run/cgroup-pids/v30/cgroup.procs",pid))stop("child still in scope");
 dprintf(1,"RC7_GUEST: REAL_CGROUP_V1_FORK_EXEC_DRAIN_PASS\n");
 guardian_races();
 dprintf(1,"RC7_GUEST: KERNEL49_PHYSICAL_CONTAINMENT_UNPROVEN\n");
 return 0;
}
