# Build the XDP per-source-IP rate limiter.
#   make          -> xdp_ratelimit.bpf.o  xdp_ratelimit.skel.h  xdp_ratelimit_user
#   make clean
CLANG   ?= clang
BPFTOOL ?= bpftool
CC      ?= gcc
ARCH    := $(shell uname -m | sed 's/x86_64/x86/;s/aarch64/arm64/')

BPF_CFLAGS := -O2 -g -target bpf -mcpu=v3 -D__TARGET_ARCH_$(ARCH) -Wall -Wno-missing-declarations
USER_CFLAGS := -O2 -g -Wall
USER_LIBS := -lbpf -lelf -lz

all: xdp_ratelimit_user

# Kernel type definitions from the running kernel's BTF (CO-RE style header).
vmlinux.h:
	$(BPFTOOL) btf dump file /sys/kernel/btf/vmlinux format c > $@

xdp_ratelimit.bpf.o: xdp_ratelimit.bpf.c xdp_ratelimit.h vmlinux.h
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

# Skeleton: embeds the BPF object and gives typed access to maps/progs.
xdp_ratelimit.skel.h: xdp_ratelimit.bpf.o
	$(BPFTOOL) gen skeleton $< > $@

xdp_ratelimit_user: xdp_ratelimit_user.c xdp_ratelimit.skel.h xdp_ratelimit.h
	$(CC) $(USER_CFLAGS) $< -o $@ $(USER_LIBS)

# Disassembly with interleaved source - handy to see what the verifier sees.
dump: xdp_ratelimit.bpf.o
	llvm-objdump -S --no-show-raw-insn $<

clean:
	rm -f xdp_ratelimit.bpf.o xdp_ratelimit.skel.h xdp_ratelimit_user

distclean: clean
	rm -f vmlinux.h

.PHONY: all dump clean distclean
