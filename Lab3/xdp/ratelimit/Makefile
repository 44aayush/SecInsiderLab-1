# Build the XDP rate limiter:  make
# Needs clang and libbpf-dev (for <bpf/bpf_helpers.h>).
ARCH_INC := /usr/include/$(shell uname -m)-linux-gnu

xdp_ratelimit.bpf.o: xdp_ratelimit.bpf.c
	clang -O2 -g -target bpf -mcpu=v3 -I$(ARCH_INC) -c $< -o $@

clean:
	rm -f xdp_ratelimit.bpf.o

.PHONY: clean
