# XDP per-source-IP rate limiter (Lab 3, Task 4 – Group 8)

A small XDP program that counts packets per IPv4 source address in a fixed
time window and drops (`XDP_DROP`) everything above a configurable threshold.
Thresholds, allow-list and block-list live in BPF maps and can be changed at
runtime from user space without recompiling or reloading.

| File | Purpose |
|---|---|
| `xdp_ratelimit.bpf.c` | kernel part (SEC("xdp"), ~150 lines incl. comments) |
| `xdp_ratelimit.h` | structs/enums shared by kernel and user space |
| `xdp_ratelimit_user.c` | libbpf skeleton loader: configures maps, attaches, prints stats, detaches on Ctrl-C |
| `Makefile` | builds `vmlinux.h`, `xdp_ratelimit.bpf.o`, `xdp_ratelimit.skel.h`, `xdp_ratelimit_user` |
| `run_demo.sh` | namespace-based demo (attacker / benign / victim), writes `logs/demo.log` |

## Build

Dependencies (Ubuntu): `clang llvm libbpf-dev libelf-dev zlib1g-dev bpftool hping3 tcpdump`
(bpftool comes from `linux-tools-$(uname -r)` / `linux-tools-common`).

```bash
make            # vmlinux.h is generated from /sys/kernel/btf/vmlinux on first build
make dump       # llvm-objdump -S: BPF bytecode interleaved with C source
```

## Run the demo (needs root)

```bash
sudo ./run_demo.sh                         # limit 100 pkt/s, 5 s SYN flood
sudo PPS=50 FLOOD_SECS=8 ./run_demo.sh     # other parameters
sudo ATTACK="-i u200" ./run_demo.sh        # 5 kpps instead of hping3 --flood
```

The script builds four namespaces (`rl-attacker` 10.10.0.2, `rl-benign`
10.10.0.3, `rl-victim` 10.10.0.1 and `rl-lan` with a bridge), then runs these
labelled phases:

0. topology + connectivity check
1. baseline flood **without** XDP (tcpdump on the victim counts what arrives)
2. attach in **generic/skb** mode (`ip link`, `bpftool prog show`, `bpftool net`)
3. benign ping alone, 0 % loss
4. **flood + benign ping at the same time**: most of the flood is dropped,
   benign ping still gets 0 % loss (the main result)
5. `bpftool map dump` of `rl_state`, `rl_stats`, `rl_config`
6. runtime control: raise the limit via `bpftool map update`, then put the
   attacker on the block-list (`rl_block`) – the hook an IDS/ML model would use
7. the same program in **native** (driver) mode on veth
8. alternative loading with only `ip link set dev vic0 xdpgeneric obj … sec xdp`
   + `bpftool map update` for the config

A trap removes all namespaces (and with them the XDP attachments) on any exit,
including Ctrl-C. Raw tool output is kept in `logs/` (`hping3_*.log`,
`tcpdump_*.log`, `benign_*.log`, `loader_*.log`).

## Using the loader directly

```bash
sudo ./xdp_ratelimit_user eth0 --pps 100 --mode skb
sudo ./xdp_ratelimit_user eth0 --pps 500 --window-ms 100 --mode native \
     --allow 192.168.1.10 --block 203.0.113.7 --duration 60
```

Output every second: global pass / drop counters (with per-second deltas) and
the top source IPs from the LRU map sorted by drops. Ctrl-C detaches the
program. Run with `-v` to see the libbpf/verifier log if loading fails.

## Loading without the custom loader (iproute2 + bpftool)

```bash
sudo ip link set dev eth0 xdpgeneric obj xdp_ratelimit.bpf.o sec xdp
ID=$(sudo bpftool map show name rl_config | awk -F: 'NR==1{print $1}')
# value = {u64 limit = 100, u64 window_ns = 1e9}, little endian
sudo bpftool map update id $ID key 0 0 0 0 value hex 64 00 00 00 00 00 00 00 00 ca 9a 3b 00 00 00 00
sudo bpftool map update name rl_block key 203 0 113 7 value 1    # block a source
sudo bpftool map dump name rl_state                              # per-source counters
sudo ip link set dev eth0 xdpgeneric off
```

After an `ip`-based load the config map is all zero, which means "limiter
off": the program passes everything until a limit is written.

## Design notes / limitations

* `rl_state` is a shared `LRU_HASH`, not `LRU_PERCPU_HASH`: with RSS a single
  source can hit several CPUs and a per-CPU map would give it `limit × nCPU`.
  Counters are updated with atomic fetch-add; the window reset is a benign race.
* Fixed window ⇒ up to `2 × limit` packets can pass around a window boundary.
* Spoofed (random) source addresses defeat per-source limiting and churn the
  LRU map; that is a job for SYN cookies / aggregate limits / the block-list.
* IPv6 is passed through unfiltered (counted as non-IPv4).

See `../THEORY.md` for the background and `../figures/xdp_pipeline.png` for
the architecture diagram.
