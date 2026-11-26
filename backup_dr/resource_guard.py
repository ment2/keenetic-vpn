"""Conservative candidate limits for the observed 256 MiB MIPS router."""
SOURCE_MAX=4*1024**2
CIPHER_MAX=8*1024**2+28
AVAILABLE_MIN=64*1024**2

def check_memory(meminfo='/proc/meminfo',minimum=AVAILABLE_MIN):
    with open(meminfo) as f:
        for line in f:
            if line.startswith('MemAvailable:'):
                available=int(line.split()[1])*1024
                if available<minimum: raise MemoryError('insufficient available router memory')
                return available
    raise MemoryError('MemAvailable unavailable')
