/* RC19 disposable guest-only TCP/UDP echo server, exact byte comparison. */
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/select.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#ifndef PORT
#define PORT 19191
#endif
static const char tcp[]="RC19-TCP-PAYLOAD-20261031";
static const char udp[]="RC19-UDP-PAYLOAD-20261031";
static void fail(const char *what){fprintf(stderr,"RC19_GUEST_SERVER_FAIL: %s errno=%d\n",what,errno);exit(2);}
int main(void){
 int ts=socket(AF_INET,SOCK_STREAM,0), us=socket(AF_INET,SOCK_DGRAM,0);
 if(ts<0||us<0)fail("socket");
 struct sockaddr_in addr={0};addr.sin_family=AF_INET;addr.sin_port=htons(PORT);addr.sin_addr.s_addr=htonl(INADDR_ANY);
 int yes=1;setsockopt(ts,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));
 if(bind(ts,(void*)&addr,sizeof(addr))||bind(us,(void*)&addr,sizeof(addr))||listen(ts,4))fail("bind/listen");
 puts("RC19_GUEST: ECHO_SERVER_READY");fflush(stdout);
 int got_tcp=0,got_udp=0;
 for(int rounds=0;rounds<150&&(!got_tcp||!got_udp);rounds++){
  fd_set fds;FD_ZERO(&fds);FD_SET(ts,&fds);FD_SET(us,&fds);
  struct timeval tv={1,0};int r=select((ts>us?ts:us)+1,&fds,NULL,NULL,&tv);
  if(r<0)fail("select");if(!r)continue;
  if(FD_ISSET(ts,&fds)){
   int cs=accept(ts,NULL,NULL);if(cs<0)fail("accept");
   char buf[128]={0};ssize_t n=recv(cs,buf,sizeof(buf),0);
   if(n!=(ssize_t)strlen(tcp)||memcmp(buf,tcp,(size_t)n))fail("tcp payload mismatch");
   if(send(cs,buf,(size_t)n,0)!=n)fail("tcp send");
   close(cs);got_tcp=1;printf("RC19_GUEST: REAL_TCP_BYTES=%ld\n",(long)n);fflush(stdout);
  }
  if(FD_ISSET(us,&fds)){
   struct sockaddr_in peer; socklen_t len=sizeof(peer);char buf[128]={0};
   ssize_t n=recvfrom(us,buf,sizeof(buf),0,(void*)&peer,&len);
   if(n!=(ssize_t)strlen(udp)||memcmp(buf,udp,(size_t)n))fail("udp payload mismatch");
   if(sendto(us,buf,(size_t)n,0,(void*)&peer,len)!=n)fail("udp send");
   got_udp=1;printf("RC19_GUEST: REAL_UDP_BYTES=%ld\n",(long)n);fflush(stdout);
  }
 }
 if(!got_tcp||!got_udp)fail("packet timeout");
 puts("RC19_GUEST: REAL_TCP_UDP_ECHO_BYTES_PASS");fflush(stdout);
 return 0;
}
