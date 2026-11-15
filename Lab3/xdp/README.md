# Lab 3, Task 4: XDP source-IP blocklist filter

`xdp_filter.c` is a small XDP program. It parses Ethernet and IPv4, and for TCP and UDP it
bounds-checks the L4 header. If the packet's source IPv4 address is in the BPF hash map `blocklist`,
it returns `XDP_DROP`; everything else (non-IPv4, truncated or malformed headers, unlisted sources) returns
`XDP_PASS`. A per-CPU array map `stats` counts the verdicts (index 0 = PASS, 1 = DROP).
Theory is in `THEORY.md`.

## Prerequisites

The toolchain from `TASKS.md` T7.0 (clang, llvm, libbpf-dev, gcc-multilib, bpftool, iproute2). The build
itself needs no root. Attaching, bpftool map access and detaching need root: **run those with `sudo`
yourself.**

## Build

```bash
cd Lab3/xdp
make              # clang -O2 -g -Wall -Werror -target bpf  ->  xdp_filter.o
make objdump      # optional: disassembly with source lines (no root)
```

## Demo (T7.3) on `lo`, generic mode

The Makefile uses `IFACE=lo` by default. Run each command in `Lab3/xdp/`.

1. Attach and check.
   ```bash
   sudo make attach
   sudo make status
   ```
   Screenshot 1: `make status` showing `xdpgeneric` on `lo` and the program `xdp_filter_prog`.

2. Baseline: both pings work.
   ```bash
   ping -c 3 127.0.0.1
   ping -c 3 -I 127.0.0.2 127.0.0.1
   ```

3. Block the source 127.0.0.2.
   ```bash
   sudo make block IP=127.0.0.2
   ```

4. Repeat both pings.
   ```bash
   ping -c 3 127.0.0.1                 # still works
   ping -c 3 -I 127.0.0.2 127.0.0.1    # now fails: 100% packet loss
   ```
   What exactly is dropped: on `lo` every packet leaves and re-enters through the same interface, so the
   XDP hook sees both directions. The echo **request** (source 127.0.0.2) is dropped by the filter, so no
   reply is ever created. The reply (source 127.0.0.1) would pass, because only 127.0.0.2 is blocked.
   Screenshot 2: the two pings, one with 0% loss and one with 100% loss.

5. Read the counters.
   ```bash
   sudo make stats
   ```
   The output has one entry per index (key 0 = PASS, key 1 = DROP) with one value per CPU. Add up the
   CPU values for each key to get the totals; DROP should be at least 3 (one per blocked echo request;
   ping retries are included).
   Screenshot 3: the `make stats` output, with your sums noted.

6. Optional TCP check (two terminals).
   ```bash
   nc -l 127.0.0.1 9000                  # terminal A (some netcat versions need: nc -l -p 9000)
   nc -s 127.0.0.2 127.0.0.1 9000        # terminal B: hangs/fails while 127.0.0.2 is blocked
   ```
   Then run `sudo make unblock IP=127.0.0.2` and repeat terminal B: the connection now works.

7. Clean up.
   ```bash
   sudo make unblock IP=127.0.0.2
   sudo make detach
   ```

## Troubleshooting

- **`asm/types.h: No such file or directory`**: install `gcc-multilib`, or check that
  `/usr/include/$(uname -m)-linux-gnu/asm/types.h` exists. The Makefile already adds that include path.
- **`Operation not permitted`** (attach, bpftool): you forgot `sudo`.
- **`File exists` / program already attached**: run `sudo make detach`, then attach again.
- **Verifier error on attach**: load the object alone to get the verifier log, then remove the pin:
  ```bash
  sudo bpftool prog load xdp_filter.o /sys/fs/bpf/xdp_test
  sudo rm /sys/fs/bpf/xdp_test
  ```
- **`bpftool prog show name ...` finds nothing**: bpftool truncates program names to 15 characters;
  `xdp_filter_prog` is exactly 15. You can also use `sudo bpftool net show dev lo`.
