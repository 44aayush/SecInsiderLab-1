# Makefile for Lab 3 Task 4 (XDP source-IP blocklist filter).
# `make`, `make objdump` and `make clean` need no root.
# attach, detach, status, block, unblock and stats are run by the USER with sudo,
# for example: sudo make attach IFACE=lo

CLANG  ?= clang
# asm/types.h lives in the multiarch include dir when gcc-multilib is absent.
ARCH_INC := -I/usr/include/$(shell uname -m)-linux-gnu
CFLAGS := -O2 -g -Wall -Werror -target bpf $(ARCH_INC)

OBJ   := xdp_filter.o
IFACE ?= lo
# Dotted IP -> four decimal bytes ("127.0.0.2" -> "127 0 0 2") for bpftool keys.
IP_BYTES = $(shell echo $(IP) | tr '.' ' ')

.PHONY: all clean objdump attach detach status block unblock stats

# Compile the BPF object.
all: $(OBJ)

$(OBJ): xdp_filter.c
	$(CLANG) $(CFLAGS) -c xdp_filter.c -o $(OBJ)

# Remove build output.
clean:
	rm -f $(OBJ)

# Non-root sanity check: show the compiled BPF instructions with source lines.
objdump: $(OBJ)
	llvm-objdump -S $(OBJ)

# (sudo) Attach in generic (skb) mode; works on any interface including lo.
attach: $(OBJ)
	ip link set dev $(IFACE) xdpgeneric obj $(OBJ) sec xdp

# (sudo) Remove the program from the interface.
detach:
	ip link set dev $(IFACE) xdpgeneric off

# (sudo) Show the link flags and the loaded program. bpftool truncates program
# names to 15 characters; "xdp_filter_prog" is exactly 15, so it matches.
status:
	ip link show dev $(IFACE)
	bpftool net show dev $(IFACE)
	bpftool prog show name xdp_filter_prog

# (sudo) Add a source IP to the blocklist: make block IP=127.0.0.2
block:
	@test -n "$(IP)" || { echo "usage: make block IP=a.b.c.d"; exit 1; }
	bpftool map update name blocklist key $(IP_BYTES) value 1 any

# (sudo) Remove a source IP from the blocklist: make unblock IP=127.0.0.2
unblock:
	@test -n "$(IP)" || { echo "usage: make unblock IP=a.b.c.d"; exit 1; }
	bpftool map delete name blocklist key $(IP_BYTES)

# (sudo) Dump the per-CPU counters (index 0 = PASS, 1 = DROP); sum the CPUs.
stats:
	bpftool map dump name stats
