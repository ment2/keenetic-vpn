/* RC9, inside disposable full-system QEMU guest.
 * Verify actual IP_TRANSPARENT TCP and UDP setsockopt using Linux socket API,
 * with exactly matching pre-exec UID/GID/capability profile used by Xray.
 */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/prctl.h>
#include <arpa/inet.h>
#include <linux/capability.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#define IP_TRANSPARENT 19
static unsigned long long eff(void){
 FILE *f=fopen("/proc/self/status","r");char l[240];unsigned long long n=0;
 if(!f)return 0;
 while(fgets(l,sizeof(l),f))
   if(sscanf(l,"CapEff:\t%llx",&n)==1)break;
 fclose(f);return n;
}
int main(int argc,char **argv){
 if(argc!=2)return 21;
 int raw=!strcmp(argv[1],"raw");
 unsigned long long actual=eff();
 unsigned long long wanted=raw ? 1ULL<<CAP_NET_RAW : 0ULL;
 if(geteuid()!=65534 || getegid()!=65534 || actual!=wanted){
   dprintf(1,"RC9_SOCKET: BAD_EXACT_CAPS actual=0x%llx expected=0x%llx uid=%d\n",
           actual,wanted,geteuid());return 22;
 }
 int one=1;int pass=0;
 const int types[]={SOCK_STREAM,SOCK_DGRAM};
 for(int n=0;n<2;n++){
    int fd=socket(AF_INET,types[n],0);
    if(fd<0)return 23;
    int rc=setsockopt(fd,SOL_IP,IP_TRANSPARENT,&one,sizeof(one));
    if(raw && rc==0)pass++;
    if(!raw && rc<0 && (errno==EPERM || errno==EACCES))pass++;
    close(fd);
 }
 if(pass!=2){
   dprintf(1,"RC9_SOCKET: TPROXY_CAPABILITY_MISMATCH profile=%s matched=%d\n",argv[1],pass);
   return 24;
 }
 dprintf(1,"RC9_SOCKET: REAL_IP_TRANSPARENT_TCP_UDP_%s_PASS uid=65534 caps=0x%llx\n",
         raw?"CAP_NET_RAW_ONLY":"DENIED_WITHOUT_CAPS",actual);
 dprintf(1,"RC9_SOCKET: NO_KERNEL49_OR_PHYSICAL_TPROXY_CLAIM\n");
 return 0;
}
