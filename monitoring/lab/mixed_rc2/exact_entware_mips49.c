#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <net/if.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/time.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
#define C(x) do { if(!(x)){printf("FAIL line %d errno %d\n",__LINE__,errno);return 1;} }while(0)
static pid_t children[3];
static struct sockaddr_in addr(int port){struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);a.sin_port=htons(port);return a;}
static int connect_local(int port){int s=socket(AF_INET,SOCK_STREAM,0);if(s<0)return -1;struct timeval t={5,0};setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&t,sizeof(t));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,&t,sizeof(t));struct sockaddr_in a=addr(port);if(connect(s,(void*)&a,sizeof(a))){close(s);return -1;}return s;}
static int exact(int s,void *b,size_t n){size_t off=0;while(off<n){ssize_t z=read(s,(char*)b+off,n-off);if(z<=0)return -1;off+=(size_t)z;}return 0;}
static pid_t start(const char *mode,const char *cfg){pid_t p=fork();if(!p){if(!strcmp(mode,"client")){if(setenv("SSL_CERT_FILE","/ca.pem",1))_exit(126);execl("/xray","xray","run","-config",cfg,(char*)NULL);}else execl("/hy","hy",mode,"-c",cfg,(char*)NULL);_exit(127);}return p;}
static int sink(void){int s=socket(AF_INET,SOCK_STREAM,0);C(s>=0);struct sockaddr_in a=addr(18080);C(!bind(s,(void*)&a,sizeof(a)));C(!listen(s,2));pid_t p=fork();C(p>=0);if(!p){alarm(40);int fd=accept(s,NULL,NULL);if(fd<0)_exit(2);char b[1024];ssize_t n=read(fd,b,sizeof(b)-1);if(n<=0)_exit(3);b[n]=0;if(!strstr(b,"GET /witness "))_exit(4);const char *r="HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n";if(write(fd,r,strlen(r))!=(ssize_t)strlen(r))_exit(5);close(fd);puts("GUEST_HTTP_WITNESS");_exit(0);}children[0]=p;close(s);return 0;}
static int run(void){struct utsname u;C(!uname(&u));printf("KERNEL %s ARCH %s\n",u.release,u.machine);C(!strncmp(u.release,"4.9.",4));C(!mount("proc","/proc","proc",0,NULL));if(mount("devtmpfs","/dev","devtmpfs",0,NULL)){mknod("/dev/urandom",S_IFCHR|0666,makedev(1,9));mknod("/dev/random",S_IFCHR|0666,makedev(1,8));mknod("/dev/null",S_IFCHR|0666,makedev(1,3));}
 int fd=socket(AF_INET,SOCK_DGRAM,0);C(fd>=0);struct ifreq ifr={0};strcpy(ifr.ifr_name,"lo");C(!ioctl(fd,SIOCGIFFLAGS,&ifr));ifr.ifr_flags|=IFF_UP;C(!ioctl(fd,SIOCSIFFLAGS,&ifr));close(fd);
 C(!sink());children[1]=start("server","/server.json");C(children[1]>0);sleep(2);children[2]=start("client","/client.json");C(children[2]>0);int s=-1;for(int i=0;i<150&&s<0;i++){s=connect_local(11080);if(s<0)usleep(100000);}C(s>=0);unsigned char greeting[]={5,1,0},b[32];C(write(s,greeting,sizeof(greeting))==sizeof(greeting));C(!exact(s,b,2)&&b[0]==5&&b[1]==0);unsigned char req[]={5,1,0,1,127,0,0,1,0x46,0xa0};C(write(s,req,sizeof(req))==sizeof(req));C(!exact(s,b,4)&&b[0]==5&&b[1]==0);size_t n=0;if(b[3]==1)n=4;else if(b[3]==4)n=16;else if(b[3]==3){C(!exact(s,b,1));n=b[0];}else C(0);C(n<=sizeof(b)-2);C(!exact(s,b,n+2));const char *http="GET /witness HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n";C(write(s,http,strlen(http))==(ssize_t)strlen(http));char resp[13]={0};C(!exact(s,resp,12)&&!memcmp(resp,"HTTP/1.1 204",12));close(s);int st;C(waitpid(children[0],&st,0)==children[0]&&WIFEXITED(st)&&WEXITSTATUS(st)==0);children[0]=0;puts("EXACT_ENTWARE_XRAY_MIPS49_SALAMANDER_TLS_HTTP204_PASS");return 0;}
int main(void){setvbuf(stdout,NULL,_IONBF,0);signal(SIGPIPE,SIG_IGN);int rc=run();for(int i=0;i<3;i++)if(children[i]>0){kill(children[i],SIGKILL);waitpid(children[i],NULL,0);}puts("GUEST_CHILDREN_REAPED");printf("GUEST_EXIT %d\n",rc);sync();reboot(RB_POWER_OFF);for(;;)pause();}
