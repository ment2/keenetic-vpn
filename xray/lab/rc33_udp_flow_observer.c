/* RC33 disposable AF_PACKET observer for pre-existing UDP 5-tuples.
 * Captures packets on isolated MIPS guest eth1 before PREROUTING xt_TPROXY.
 * This is ONLY a bounded witness; it cannot establish complete ownership for
 * flows silent during the observation window. Fail closed on every mismatch.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <net/if.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#define MAXFLOWS 16
struct flow {unsigned src,dst;unsigned short sport,dport;};
static struct flow flows[MAXFLOWS];
static void fail(const char*m){dprintf(1,"RC33_OBSERVER_HARD_NO_GO_%s errno=%d\n",m,errno);exit(3);}
int main(int argc,char**argv){
 if(argc!=3)fail("ARGS");
 char *end=0;long required=strtol(argv[1],&end,10);
 if(!end||*end||required<2||required>MAXFLOWS)fail("FLOW_BOUND");
 if(strcmp(argv[2],"eth1"))fail("UNTRUSTED_INGRESS_INTERFACE");
 int ix=if_nametoindex("eth1");if(ix<=0)fail("NO_INTERFACE");
 int fd=socket(AF_PACKET,SOCK_RAW,htons(ETH_P_IP));if(fd<0)fail("AF_PACKET");
 struct sockaddr_ll bind_addr={0};bind_addr.sll_family=AF_PACKET;
 bind_addr.sll_protocol=htons(ETH_P_IP);bind_addr.sll_ifindex=ix;
 if(bind(fd,(struct sockaddr*)&bind_addr,sizeof(bind_addr)))fail("BIND");
 struct timeval tv={.tv_sec=1,.tv_usec=0};
 if(setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv)))fail("TIMEOUT");
 setvbuf(stdout,NULL,_IONBF,0);
 puts("RC33_OBSERVER_PACKET_SOCKET_READY_ETH1");
 unsigned count=0;int attempts=0;
 while(count<(unsigned)required && attempts++<40){
  unsigned char frame[2048];
  ssize_t n=recv(fd,frame,sizeof(frame),0);
  if(n<0){if(errno==EAGAIN||errno==EINTR)continue;fail("RECV");}
  if(n<(ssize_t)(sizeof(struct ethhdr)+sizeof(struct iphdr)))continue;
  struct ethhdr *eth=(struct ethhdr*)frame;
  if(ntohs(eth->h_proto)!=ETH_P_IP)continue;
  struct iphdr *ip=(struct iphdr*)(frame+sizeof(struct ethhdr));
  unsigned header=ip->ihl*4;
  if(ip->version!=4||header<20||(size_t)n<sizeof(struct ethhdr)+header+sizeof(struct udphdr))continue;
  if(ip->protocol!=IPPROTO_UDP || ntohl(ip->saddr)!=0x0a4d0001 || ntohl(ip->daddr)!=0x0a4d0003)continue;
  struct udphdr *u=(struct udphdr*)(frame+sizeof(struct ethhdr)+header);
  unsigned short sport=ntohs(u->source),dport=ntohs(u->dest);
  if(dport!=19301 || sport<1024)continue;
  int duplicate=0;
  for(unsigned i=0;i<count;i++)if(flows[i].src==ip->saddr && flows[i].dst==ip->daddr && flows[i].sport==sport && flows[i].dport==dport)duplicate=1;
  if(duplicate)continue;
  flows[count++]=(struct flow){ip->saddr,ip->daddr,sport,dport};
  printf("RC33_OBSERVER_DISCOVERED_UDP_FIVE_TUPLE proto=udp iface=eth1 sport=%hu total=%u\n",sport,count);
 }
 close(fd);
 if(count!=(unsigned)required)fail("INCOMPLETE_OLD_FLOW_INVENTORY");
 /* Durable *lab* snapshot with bounded table, boot ID + generation witness.
  * Not an atomic kernel flow freeze nor production fsync journal. */
 FILE *boot=fopen("/proc/sys/kernel/random/boot_id","r");
 if(!boot)fail("BOOT_ID_READ");
 char bootid[80]={0};
 if(!fgets(bootid,sizeof(bootid),boot))fail("BOOT_ID_EMPTY");
 fclose(boot);
 bootid[strcspn(bootid,"\r\n")]=0;
 if(strlen(bootid)!=36)fail("BOOT_ID_INVALID");
 FILE *f=fopen("/lab/rc33-udp-flows.tmp","w");if(!f)fail("OPEN_MAP");
 if(fprintf(f,"boot=%s generation=1 interface=eth1 count=%u\n",bootid,count)<0)fail("WRITE_HEADER");
 for(unsigned i=0;i<count;i++) {
  struct in_addr src={.s_addr=flows[i].src},dst={.s_addr=flows[i].dst};
  char srcip[INET_ADDRSTRLEN],dstip[INET_ADDRSTRLEN];
  if(!inet_ntop(AF_INET,&src,srcip,sizeof(srcip))||!inet_ntop(AF_INET,&dst,dstip,sizeof(dstip)))fail("INET_NTOP");
  if(fprintf(f,"%s %hu %s %hu\n",srcip,flows[i].sport,dstip,flows[i].dport)<0)fail("WRITE_FLOW");
 }
 if(fflush(f)||fsync(fileno(f))||fclose(f))fail("FSYNC");
 if(rename("/lab/rc33-udp-flows.tmp","/lab/rc33-udp-flows.txt"))fail("RENAME");
 printf("RC33_OBSERVER_FROZEN_BOOT_GENERATION_ONE_OLD_UDP_COUNT_%u\n",count);
 return 0;
}
