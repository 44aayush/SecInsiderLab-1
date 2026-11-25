# Build the Lab 4 BPF object (CLAUDE.md 5.3). Debian's clang needs the multiarch include dir.
ARCH := $(shell uname -m)
CLANG ?= clang
CFLAGS := -O2 -g -target bpf -Wall -Werror -I/usr/include/$(ARCH)-linux-gnu

all: lab4_xdp.bpf.o

lab4_xdp.bpf.o: lab4_xdp.bpf.c lab4_common.h
	$(CLANG) $(CFLAGS) -c $< -o $@

clean:
	rm -f lab4_xdp.bpf.o

.PHONY: all clean
