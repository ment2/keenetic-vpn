#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <net/if.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/reboot.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
#include <poll.h>
#include <grp.h>
#include <signal.h>
#if defined(__mips__) && __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define ARCH AUDIT_ARCH_MIPSEL
#elif defined(__x86_64__)
#define ARCH AUDIT_ARCH_X86_64
#else
#error unreviewed ABI
#endif
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"FAIL line %d errno %d\n",__LINE__,errno); return 1; } } while(0)
static struct sockaddr_in addr(unsigned port){struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons(port);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);return a;}
static int sink(unsigned *port){int fd=socket(AF_INET,SOCK_DGRAM,0);struct sockaddr_in a=addr(0);socklen_t n=sizeof(a);if(fd<0||bind(fd,(void*)&a,sizeof(a))||getsockname(fd,(void*)&a,&n))return -1;*port=ntohs(a.sin_port);return fd;}
static int filter(void){
 struct sock_filter ins[]={
 BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,ARCH,1,0),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL),
 BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_read,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_write,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_exit,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_exit_group,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
 BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM)};
 struct sock_fprog p={.len=sizeof(ins)/sizeof(ins[0]),.filter=ins};return prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&p,0,0);
}
struct proof{unsigned long long inode;unsigned port;int filter_errno;};
static int proc_owner(pid_t pid, int fd,struct proof p){char path[128],link[128],want[128],line[1024];snprintf(path,sizeof(path),"/proc/%d/fd/%d",pid,fd);ssize_t n=readlink(path,link,sizeof(link)-1);CHECK(n>0);link[n]=0;snprintf(want,sizeof(want),"socket:[%llu]",p.inode);CHECK(!strcmp(link,want));FILE *f=fopen("/proc/net/udp","r");CHECK(f);int seen=0;while(fgets(line,sizeof(line),f)){unsigned local,remote;unsigned long long inode;char la[9],ra[9];if(sscanf(line," %*u: %8[0-9A-Fa-f]:%x %8[0-9A-Fa-f]:%x %*s %*s %*s %*s %*s %*s %llu",la,&local,ra,&remote,&inode)==5&&local==p.port&&inode==p.inode)seen++;}fclose(f);CHECK(seen==1);snprintf(path,sizeof(path),"/proc/%d/status",pid);f=fopen(path,"r");CHECK(f);int uid=0,caps=0,nnp=0;while(fgets(line,sizeof(line),f)){unsigned u;unsigned long long c;if(sscanf(line,"Uid: %u",&u)==1)uid=(u==65534);if(sscanf(line,"CapEff: %llx",&c)==1)caps=(c==0);if(sscanf(line,"NoNewPrivs: %u",&u)==1)nnp=(u==1);}fclose(f);CHECK(uid&&caps);printf("OWNER pid=%d inode=%llu port=%u uid=65534 capeff=0 nnp_proc=%d\n",pid,p.inode,p.port,nnp);return 0;}
static int recv_exact(int fd,const char *s,int timeout){struct pollfd p={fd,POLLIN,0};int n=poll(&p,1,timeout);if(!s)return n==0?0:1;if(n!=1)return 1;char b[128];ssize_t z=recv(fd,b,sizeof(b),0);return z==(ssize_t)strlen(s)&&!memcmp(b,s,z)?0:1;}
static int trial(int gated){unsigned pa,pb;int a=sink(&pa),b=sink(&pb);CHECK(a>=0&&b>=0);int udp=socket(AF_INET,SOCK_DGRAM,0);CHECK(udp>=0);struct sockaddr_in aa=addr(pa),bb=addr(pb),local;socklen_t ln=sizeof(local);CHECK(!connect(udp,(void*)&aa,sizeof(aa)));CHECK(!getsockname(udp,(void*)&local,&ln));struct stat st;CHECK(!fstat(udp,&st));int go[2],report[2];CHECK(!pipe(go)&&!pipe(report));pid_t child=fork();CHECK(child>=0);if(!child){close(a);close(b);close(go[1]);close(report[0]);if(setgroups(0,NULL)||setgid(65534)||setuid(65534)||prctl(PR_SET_DUMPABLE,1)||prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0))_exit(20);struct proof p={(unsigned long long)st.st_ino,ntohs(local.sin_port),0};if(gated&&filter())p.filter_errno=errno;if(write(report[1],&p,sizeof(p))!=sizeof(p))_exit(21);char c;if(read(go[0],&c,1)!=1)_exit(22);if(p.filter_errno)_exit(23);if(write(udp,"allowed-marker",14)!=14)_exit(24);if(!gated){if(sendto(udp,"forbidden-marker",16,0,(void*)&bb,sizeof(bb))!=16)_exit(25);}else{if(sendto(udp,"forbidden-marker",16,0,(void*)&bb,sizeof(bb))!=-1||errno!=EPERM)_exit(26);if(connect(udp,(void*)&bb,sizeof(bb))!=-1||errno!=EPERM)_exit(27);if(socket(AF_INET,SOCK_STREAM,0)!=-1||errno!=EPERM)_exit(28);if(write(udp,"allowed-again",13)!=13)_exit(29);}if(read(go[0],&c,1)!=1)_exit(30);_exit(0);}close(go[0]);close(report[1]);close(udp);struct proof p;CHECK(read(report[0],&p,sizeof(p))==sizeof(p));if(p.filter_errno){fprintf(stderr,"SECCOMP_UNAVAILABLE errno=%d\n",p.filter_errno);if(write(go[1],"x",1)!=1)kill(child,SIGKILL);waitpid(child,NULL,0);return 1;}CHECK(!proc_owner(child,udp,p));CHECK(write(go[1],"x",1)==1);CHECK(!recv_exact(a,"allowed-marker",3000));if(gated){CHECK(!recv_exact(a,"allowed-again",3000));CHECK(!recv_exact(b,NULL,300));puts("GATED_POSITIVE_ALLOWED_AND_NEGATIVE_FORBIDDEN_NO_BYTES");}else{CHECK(!recv_exact(b,"forbidden-marker",3000));puts("UID_NNP_ONLY_NEGATIVE_DIRECT_UDP_BYTES_RECEIVED");}CHECK(write(go[1],"x",1)==1);int status;CHECK(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);char path[80];snprintf(path,sizeof(path),"/proc/%d/fd/%d",child,udp);CHECK(access(path,F_OK)==-1&&errno==ENOENT);close(a);close(b);close(go[1]);close(report[0]);puts("CHILD_REAPED");return 0;}
static int run(int guest){struct utsname u;CHECK(!uname(&u));printf("KERNEL %s ARCH %s\n",u.release,u.machine);if(guest){CHECK(!strncmp(u.release,"4.9.",4));CHECK(!mount("proc","/proc","proc",0,NULL));int fd=socket(AF_INET,SOCK_DGRAM,0);CHECK(fd>=0);struct ifreq ifr={0};strcpy(ifr.ifr_name,"lo");CHECK(!ioctl(fd,SIOCGIFFLAGS,&ifr));ifr.ifr_flags|=IFF_UP;CHECK(!ioctl(fd,SIOCSIFFLAGS,&ifr));close(fd);}CHECK(!trial(0));CHECK(!trial(1));puts("RC2_CONTAINMENT_LAB_PASS_SYNTHETIC_CONNECTED_UDP_ONLY");puts("XRAY_NATIVE_SOCKET_FACTORY_NOT_CONTAINED_HARD_NO_GO");return 0;}
int main(int argc,char **argv){(void)argv;setvbuf(stdout,NULL,_IONBF,0);int guest=argc==1&&getpid()==1;int rc=run(guest);if(guest){printf("GUEST_EXIT %d\n",rc);sync();reboot(RB_POWER_OFF);for(;;)pause();}return rc;}
