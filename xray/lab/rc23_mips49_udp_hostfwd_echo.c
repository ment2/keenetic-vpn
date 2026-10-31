/* RC23 disposable MIPS32LE udp hostfwd return proof, no Xray, no TPROXY.
 * Only a full byte-equal UDP reply received on the host counts as success.
 */
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/select.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define PORT 19301
static const char TCP[]="RC23-TCP-HOSTFWD-BASELINE";
static const char UDP[]="RC23-UDP-HOSTFWD-BASELINE";
static void die(const char *m){fprintf(stderr,"RC23_GUEST: HARD_NO_GO_%s errno=%d\n",m,errno);exit(2);}
int main(void){
 setvbuf(stdout,NULL,_IONBF,0);
 int ts=socket(AF_INET,SOCK_STREAM,0),us=socket(AF_INET,SOCK_DGRAM,0);
 if(ts<0||us<0)die("SOCKET");
 int yes=1;setsockopt(ts,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));
 struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons(PORT);a.sin_addr.s_addr=htonl(INADDR_ANY);
 if(bind(ts,(void*)&a,sizeof(a))||bind(us,(void*)&a,sizeof(a))||listen(ts,8))die("BIND_LISTEN");
 puts("RC23_GUEST: TCP_UDP_SOCKET_READY");
 int tcp_ok=0,udp_rx=0,udp_tx=0;
 for(int i=0;i<80;i++){
  fd_set fds;FD_ZERO(&fds);FD_SET(ts,&fds);FD_SET(us,&fds);
  struct timeval tv={1,0};int r=select((ts>us?ts:us)+1,&fds,NULL,NULL,&tv);
  if(r<0)die("SELECT");if(!r)continue;
  if(FD_ISSET(ts,&fds)){
   int cs=accept(ts,NULL,NULL);if(cs<0)die("ACCEPT");
   char buf[128];ssize_t n=recv(cs,buf,sizeof(buf),0);
   if(n!=(ssize_t)strlen(TCP)||memcmp(buf,TCP,(size_t)n))die("TCP_BYTES");
   if(send(cs,buf,(size_t)n,0)!=n)die("TCP_SEND");
   close(cs);tcp_ok=1;puts("RC23_GUEST: TCP_ECHO_BYTES_EQUAL");
  }
  if(FD_ISSET(us,&fds)){
   struct sockaddr_in peer={0},local={0};socklen_t len=sizeof(peer),llen=sizeof(local);
   char buf[128];ssize_t n=recvfrom(us,buf,sizeof(buf),0,(void*)&peer,&len);
   if(n!=(ssize_t)strlen(UDP)||memcmp(buf,UDP,(size_t)n))die("UDP_PAYLOAD");
   if(getsockname(us,(void*)&local,&llen))die("GETSOCKNAME");
   char ip[INET_ADDRSTRLEN]={0};
   if(!inet_ntop(AF_INET,&peer.sin_addr,ip,sizeof(ip)))die("INET_NTOP");
   fprintf(stdout,"RC23_GUEST: UDP_RX_EXACT seq=%d peer=%s:%u listener=%u bytes=%ld\n",
           ++udp_rx,ip,ntohs(peer.sin_port),ntohs(local.sin_port),(long)n);
   ssize_t sent=sendto(us,buf,(size_t)n,0,(void*)&peer,len);
   if(sent!=n)die("UDP_SENDTO");
   ++udp_tx;fprintf(stdout,"RC23_GUEST: UDP_SENDTO_EXACT seq=%d bytes=%ld\n",udp_tx,(long)sent);
  }
 }
 fprintf(stdout,"RC23_GUEST: FINISH tcp=%d udp_rx=%d udp_tx=%d\n",tcp_ok,udp_rx,udp_tx);
 if(!tcp_ok||udp_rx<1||udp_tx<1)die("PACKET_INGRESS_OR_SEND_MISSING");
 puts("RC23_GUEST: UDP_SENDTO_WITNESSED_NOT_HOST_RETURN");
 return 0;
}
