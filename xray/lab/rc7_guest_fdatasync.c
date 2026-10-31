/* RC7 disposable QEMU full-system POSIX durability primitive.
 * Actual fdatasync(file) + fsync(parent directory) on guest ext4.
 * Only callable with two absolute paths below /mnt/active/.
 * No production path, no /opt path, never installed on Keenetic.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
static void bad(const char *reason){
 dprintf(2,"RC7_FSYNC: FAIL %s errno=%d\n",reason,errno);_exit(80);
}
int main(int argc,char**argv){
 if(argc!=3)bad("usage");
 if(strncmp(argv[1],"/mnt/active/",12)!=0 ||
    strcmp(argv[2],"/mnt/active")!=0 ||
    strstr(argv[1],"/../") ||strstr(argv[1],"//"))bad("disposable paths only");
 int fd=open(argv[1],O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
 if(fd<0)bad("file open");
 if(fdatasync(fd)!=0)bad("fdatasync");
 if(close(fd)!=0)bad("file close");
 int parent=open(argv[2],O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);
 if(parent<0)bad("parent open");
 if(fsync(parent)!=0)bad("directory fsync");
 if(close(parent)!=0)bad("directory close");
 dprintf(1,"RC7_FSYNC: FILE_FDATASYNC_AND_DIRECTORY_FSYNC_PASS\n");
 return 0;
}
