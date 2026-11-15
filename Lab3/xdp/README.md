# Lab 3, Task 4: XDP source-IP blocklist filter

`xdp_filter.c` is a small XDP program. It parses only the Ethernet header and the fixed 20-byte IPv4
header. If the packet's source IPv4 address is in the BPF hash map `blocklist`, it returns `XDP_DROP`;
everything else returns `XDP_PASS`. The blocklist lookup happens right after the IPv4 header bounds check, so a
truncated or malformed packet (bad options, cut-off L4 header) from a blocked source is dropped too. No L4 parsing
is done, because the decision reads only `iph->saddr`. A per-CPU array map `stats` counts the verdicts
(index 0 = PASS, 1 = DROP). **Not filtered (always passed):** IPv6 and VLAN-tagged (802.1Q) frames, because
their EtherType is not `ETH_P_IP`; ARP and other non-IPv4 traffic as well.
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
   ping retries are included). PASS counts every other packet that reached the hook (non-IPv4 and short
   frames included), so only the DROP count and the IPv4-versus-blocked decisions are exact figures
   of interest; do not read PASS as "IPv4 packets allowed".
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

## Task 5: xdp-tools

Build (no root; log to `xdp/logs/xdp-tools-build.log`):

```bash
git clone --recurse-submodules https://github.com/xdp-project/xdp-tools ~/src/xdp-tools
cd ~/src/xdp-tools
./configure
make 2>&1 | tee ~/Desktop/SecInsiderLab1/SecInsiderLab-1/Lab3/xdp/logs/xdp-tools-build.log
```

Demo with `xdp-filter` and `xdp-loader` on `lo` (generic/skb mode), run in any directory:

```bash
XF=~/src/xdp-tools/xdp-filter/xdp-filter; XL=~/src/xdp-tools/xdp-loader/xdp-loader
sudo LIBXDP_OBJECT_PATH=$HOME/src/xdp-tools/xdp-filter $XF load lo -m skb -f ipv4
sudo $XL status
sudo $XF ip 127.0.0.2 -m src
ping -c 3 127.0.0.1
ping -c 3 -I 127.0.0.2 127.0.0.1
sudo $XF status
sudo $XF unload lo
sudo $XL status
```

Why `LIBXDP_OBJECT_PATH`: this is an uninstalled build (no `make install`). libxdp looks for the
`xdp-filter` BPF object in its default directory `/usr/local/lib/bpf`, where nothing was installed, so the
variable points it at the build directory that holds the object. Without it, `load` fails with an object-not-found
error. The `ping` from 127.0.0.2 should fail after the `ip` rule, the one from 127.0.0.1 should work.
