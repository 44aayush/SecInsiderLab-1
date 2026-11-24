# Task 4 – eBPF and XDP: Background, Use Cases, Tools and a Rate-Limiting Filter

*Security Insider Lab – Lab 3, Group 8*

## 1. What eBPF and XDP are

### 1.1 eBPF

The **extended Berkeley Packet Filter (eBPF)** lets you run small, sandboxed
programs inside the Linux kernel without changing kernel source code or loading
kernel modules [1, 2]. It started as the classic BPF packet filter used by
`tcpdump`. Today it is a general in-kernel execution environment with these parts:

* **Instruction set / virtual machine.** eBPF programs are written in a
  restricted C (or Rust and other languages) and compiled by LLVM/clang
  (`-target bpf`) to a 64-bit RISC-like bytecode with 11 registers and a
  512-byte stack [1, 3].
* **Verifier.** Before a program is accepted, the in-kernel verifier simulates
  every path through it. It checks that the program terminates (bounded loops),
  that every memory access is in bounds (e.g. each packet pointer has to be
  compared with `data_end` before it is dereferenced), that pointers are not
  leaked, and that only allowed helpers are called for the program type [3].
  This is what makes eBPF safe enough to run in the kernel's fast paths.
* **JIT compiler.** Verified bytecode is translated to native machine code
  (x86-64, arm64, …), so it runs at close to native speed [1, 2].
* **Maps.** Programs keep state in key/value data structures shared with user
  space through the `bpf()` syscall. Examples are hash maps, arrays, LRU hashes,
  per-CPU variants, ring buffers, LPM tries and device/CPU/XSK maps for
  redirection [4, 5]. Maps are the control and observability channel: user
  space writes configuration into them and reads results back.
* **Helpers and kfuncs.** A stable set of kernel functions that programs may
  call, e.g. `bpf_map_lookup_elem`, `bpf_ktime_get_ns`, `bpf_redirect_map` [1].
* **Program types / hooks.** The program type decides where a program attaches
  and what context it gets. Examples: XDP and tc (networking), kprobes,
  tracepoints and fentry (tracing), cgroup hooks, LSM (security), socket
  filters [1, 2].
* **BTF and CO-RE.** The BPF Type Format describes kernel and program types [6].
  With BTF, "Compile Once – Run Everywhere" (CO-RE) lets libbpf adjust field
  offsets at load time, so one binary runs on many kernel versions [7]. Our
  program uses a `vmlinux.h` generated from the running kernel's BTF
  (`bpftool btf dump file /sys/kernel/btf/vmlinux format c`) and a libbpf
  *skeleton* (`bpftool gen skeleton`) for typed access from user space.

### 1.2 XDP – the eXpress Data Path

**XDP** is an eBPF hook at the earliest possible point of the Linux receive
path: inside the NIC driver's RX handler, right after DMA and *before* the
kernel allocates an `sk_buff` [8, 9]. The program gets a minimal context
(`struct xdp_md`: `data`, `data_end`, ingress ifindex, RX queue) and returns
a verdict:

| Action | Meaning |
|---|---|
| `XDP_DROP` | discard the frame immediately; the buffer is recycled |
| `XDP_PASS` | continue into the normal network stack (skb allocated) |
| `XDP_TX` | send the (possibly rewritten) frame back out of the same NIC |
| `XDP_REDIRECT` | send to another NIC, another CPU (cpumap) or an AF_XDP socket |
| `XDP_ABORTED` | program error; dropped and visible through a tracepoint |

Since no skb exists yet, a drop costs only a few hundred instructions. In
Høiland-Jørgensen et al. [8], XDP drops packets at tens of millions of packets
per second on a single core. It scales linearly with cores and comes close to
kernel-bypass frameworks like DPDK, while the kernel keeps control of the NIC
and the normal stack stays available for the traffic that is passed.

XDP has three attach modes [8, 9, 10]:

* **Native / driver mode** (`xdpdrv`): runs in the driver's NAPI poll loop.
  This is the fast path. Most 10/25/40/100G drivers support it (mlx5, i40e,
  ice, ixgbe, bnxt, …), and so do virtual devices such as `veth`, `virtio_net`
  and `tun`.
* **Generic / skb mode** (`xdpgeneric`): a driver-independent fallback that
  runs after the skb has been allocated (in `netif_receive_skb`). It works on
  any interface and suits testing, but most of the performance advantage is
  lost.
* **Offloaded mode** (`xdpoffload`): the program runs on the NIC itself
  (e.g. Netronome SmartNICs), so the host CPU never sees dropped packets.

### 1.3 Comparison with other packet-processing options

| | XDP (native) | tc-BPF (cls_bpf) | iptables / nftables | DPDK (kernel bypass) |
|---|---|---|---|---|
| Hook position | driver RX, before skb | after skb alloc (ingress/egress) | netfilter hooks in IP stack | user space, NIC taken from kernel |
| Programmability | arbitrary eBPF + maps | arbitrary eBPF + maps | rule language (sets, maps in nft) | arbitrary C |
| Typical drop cost | lowest (no skb) | skb alloc + GRO | skb + conntrack/rule walk | very low (busy polling) |
| Egress support | no (RX only) | yes | yes | yes |
| Kernel stack still usable | yes (`XDP_PASS`) | yes | yes | no (needs re-injection) |
| CPU when idle | none (interrupt/NAPI driven) | none | none | dedicated busy-polling cores |
| Safety | verifier | verifier | kernel code | user-space process |

In Cloudflare's own measurements [11], the same drop rule handled the most
packets per second at the XDP layer. iptables in the `raw` table and tc
were slower, and dropping in an application socket was much slower still.
nftables and iptables remain the right tools for stateful, policy-rich
firewalling. tc-BPF is needed when you need egress or full skb metadata.
XDP is the right place for cheap, early decisions on huge packet volumes.

## 2. Use cases and real deployments

* **DDoS mitigation.** Dropping attack traffic before the stack spends
  memory on it is the classic XDP use case. Cloudflare's *L4Drop* compiles
  mitigation rules produced by its automatic DDoS system (Gatebot) into XDP
  programs that run on every edge server [12, 13]. Their *flowtrackd*
  adds stateful TCP flow tracking for the Magic Transit product [14].
* **Load balancing.** Facebook's **Katran** is an L4 load balancer built
  on XDP with `XDP_TX` and IP-in-IP encapsulation. Facebook runs it in production
  in front of its services and open-sourced it in 2018 [15, 16]. Cloudflare's
  **Unimog** is another XDP-based edge load balancer [17].
* **Firewalling and policy.** **Cilium** uses eBPF for Kubernetes networking
  and network policy. It uses XDP for a pre-filter (CIDR deny lists) and to
  accelerate NodePort/LoadBalancer services in its kube-proxy replacement
  [10, 18]. `xdp-filter` in xdp-tools is a small ready-made packet filter [19].
* **Monitoring and observability.** XDP programs can count, sample and
  timestamp packets at line rate, writing to per-CPU maps or ring buffers.
  `xdpdump` captures packets at the XDP layer [19]. More broadly, eBPF
  tracing (bcc, bpftrace) is used for performance analysis and debugging [20, 21].
* **IDS/IPS acceleration.** Suricata can load an XDP program that *bypasses*
  flows it has finished inspecting (e.g. large encrypted transfers), drops
  them early, and spreads load across CPUs [22].
* **AF_XDP user-space fast path.** With `XDP_REDIRECT` into an XSK map,
  chosen packets go zero-copy to a user-space `AF_XDP` socket. This gives
  DPDK-like performance for applications, while all other traffic stays
  with the kernel [23].

## 3. Survey of eBPF/XDP tools

| Tool | Type | Short description |
|---|---|---|
| **xdp-tools** (`xdp-loader`, `xdp-filter`, `xdpdump`, `xdp-bench`, `xdp-monitor`, libxdp) [19] | XDP utilities | Loader that supports several programs on one interface (libxdp dispatcher), a simple IP/port/MAC filter, a tcpdump-like capture at the XDP layer, benchmarking of XDP actions. |
| **xdp-tutorial** [24] | Teaching | Step-by-step lessons (basic → packet parsing → redirect → AF_XDP). It was the basis for the structure of our program. |
| **bpftool** [1] | Kernel-tree CLI | Inspect/load programs and maps (`prog show`, `map dump/update`, `net show`), generate `vmlinux.h` and skeletons. |
| **libbpf** [25] | Library | Reference C loader library: CO-RE relocations, skeletons, `bpf_xdp_attach()`. |
| **iproute2** (`ip link … xdp obj`) | CLI | Attach an XDP object directly to a device without a custom loader. |
| **bcc** [20] | Toolkit | Python/Lua front-end with on-the-fly compilation; more than 100 tracing tools and XDP examples. |
| **bpftrace** [21] | Tracing language | awk-like one-liners for kprobes and tracepoints; useful for observing the stack during an attack. |
| **Cilium** [18] | CNI / service mesh | eBPF-native Kubernetes networking, policy, load balancing and XDP acceleration. Hubble provides flow visibility. |
| **Katran** [15] | L4 load balancer | Facebook's XDP/`XDP_TX` load balancer with consistent hashing. |
| **Cloudflare L4Drop / Gatebot / flowtrackd** [12–14] | DDoS pipeline | Gatebot detects attacks and generates rules, L4Drop enforces them in XDP, flowtrackd adds stateful TCP protection. |
| **Suricata XDP bypass** [22] | IDS/IPS | XDP/eBPF flow bypass and load balancing for the Suricata IDS. |
| **Falco** [26] | Runtime security | Detects anomalous syscall behaviour (eBPF driver). Host- and container-level, not packet-level. |
| **Tetragon** [27] | Runtime security | Cilium's eBPF security observability and in-kernel enforcement (process, file, network events). |
| **Polycube** [28] | NFV framework | Chains eBPF/XDP network functions (bridge, router, firewall, DDoS mitigator) on a common framework. |

## 4. Our filter: a per-source-IP rate limiter

### 4.1 Design

```
             +-------------------- user space ---------------------+
             | xdp_ratelimit_user  | bpftool / ip | IDS / ML model  |
             +-------|-------------------|---------------|----------+
                     | bpf() syscalls: config, stats, block-list
   kernel            v                   v               v
   NIC RX --> [ XDP: xdp_ratelimit ] <--> maps: rl_config  ARRAY[1]
                 | parse Eth/VLAN/IPv4       rl_state   LRU_HASH  saddr -> window state
                 | block-list? -> DROP       rl_stats   PERCPU_ARRAY counters
                 | allow-list? -> PASS       rl_allow   HASH
                 | count in window           rl_block   HASH
                 | > limit ?  DROP : PASS
                 v                    \
            XDP_PASS: skb -> tc ->    XDP_DROP: buffer recycled
            netfilter -> TCP/IP
```

(The figure `figures/xdp_pipeline.png` shows the same architecture.)

For every frame the program parses Ethernet and an optional 802.1Q/802.1ad
tag, then IPv4. Each header access is preceded by a `data_end` bounds check,
so the verifier accepts the program. Non-IPv4 frames (ARP, IPv6) are passed
and counted. For IPv4, it first checks the source address against the block
list (drop) and the allow list (pass). It then runs a **fixed-window counter**:
the `rl_state` entry stores `win_start` (from `bpf_ktime_get_ns()`) and
`count`. When `now − win_start ≥ window`, the window is reset. `count` is
incremented atomically, and packets with `count > limit` get `XDP_DROP`. The
limit and window length are read from the `rl_config` array map on every
packet, so the operator can change them at runtime without recompiling or
reloading (shown with `bpftool map update` in phase 6 of the demo).

**Map choices.**

* `rl_state` is a **`BPF_MAP_TYPE_LRU_HASH`** with 65,536 entries. An LRU map
  cannot become "full": when capacity is reached, the least recently used
  source is evicted. A plain hash would start refusing new sources, and
  an attacker could exploit that. We chose the **shared** variant over
  `LRU_PERCPU_HASH` on purpose. With RSS, packets from one source can be
  spread over several RX queues and CPUs. Per-CPU counters would give each
  CPU its own budget, so the effective limit would be `limit × #CPUs` and
  would depend on hashing. The price is atomic `fetch_add` on a shared cache
  line (needs `-mcpu=v3`) and a benign race on the window reset, where at worst
  a few extra packets pass.
* `rl_stats` is a **`PERCPU_ARRAY`**. Global counters are written by every
  packet, so per-CPU slots avoid contention. User space sums them.
* `rl_allow` / `rl_block` are plain **`HASH`** maps. Exact-match lookups are
  O(1). An `LPM_TRIE` would be the natural extension for prefixes.
* `rl_config` is a single-entry **`ARRAY`**, the cheapest lookup there is.

The loader uses the libbpf skeleton. It writes the config and the
allow/block lists *before* attaching (so the first packet is already
governed), attaches with `bpf_xdp_attach()` in skb or native mode, prints the
per-second counters and the top sources by drops, and detaches on
SIGINT/SIGTERM.

### 4.2 Limitations

1. **Spoofed source addresses.** Per-source limiting assumes the source IP
   identifies the sender. A SYN flood with random spoofed sources sends only
   one or two packets per address and is never limited. The same flood also
   churns the LRU map: legitimate entries are evicted, so their counters
   reset all the time. Real systems combine per-source limits with aggregate
   limits (per destination or port), SYN cookies (which can also be generated
   in XDP), and signature rules like the ones Gatebot/L4Drop generate.
2. **Window boundary effect.** A fixed window lets up to `2 × limit` packets
   through in a short interval around the boundary. A token bucket
   (tokens += elapsed × rate, capped at a burst size) or a sliding window
   smooths this, at the cost of slightly more arithmetic per packet.
3. **Carrier-grade NAT / shared addresses.** Many benign users behind one NAT
   share one budget and can be limited together (collateral damage). The
   allow-list helps for known gateways.
4. **IPv6 is not handled.** IPv6 packets are passed unfiltered. Support would
   need a second state map keyed by `struct in6_addr` (or by /64 prefix).
5. **Generic mode performance.** In generic mode the skb has already been
   allocated, so most of the XDP speedup is lost. Our demo uses `veth`, which
   also supports native XDP (phase 7). Real gains need native mode on a
   physical NIC.
6. **Ingress only.** XDP sees received packets only. It does not protect
   against the host taking part in an attack, and it cannot drop outgoing
   responses.
7. **Fairness under racing CPUs.** The window reset is not atomic with the
   increment. This is acceptable for rate limiting but not for exact
   accounting.

### 4.3 Bridge to Lab 4 and to our ML model

The `rl_block` map is the interface between *detection* and *enforcement*.
A user-space component (the Lab 3 ML classifier or a Lab 4 detector) can
analyse flow features from captured or exported traffic. When it classifies
a source as malicious, it inserts the address with
`bpf_map_update_elem(rl_block_fd, &ip, &one, BPF_ANY)` or
`bpftool map update name rl_block key A B C D value 1`. From the next packet
on, that source is dropped in the driver, before it costs any stack
resources. We show this at runtime in phase 6 of the demo. This is the same
split that Cloudflare uses at scale: Gatebot detects attacks in user space
and L4Drop enforces in XDP [12, 13]. Possible extensions for Lab 4:

* give block-list entries an expiry time (value = timestamp) so that
  false positives heal themselves;
* use an `LPM_TRIE` to block whole prefixes found by the model;
* export per-source features from XDP (packet counts, SYN ratio, size
  histogram) through a ring buffer, so the model can be fed from the data
  path itself instead of from pcap files;
* replace the fixed window with a token bucket and add aggregate
  per-destination limits to cope with spoofed floods.

## References

1. Linux kernel documentation, "BPF Documentation". https://docs.kernel.org/bpf/index.html
2. eBPF Foundation, "What is eBPF?". https://ebpf.io/what-is-ebpf/
3. Linux kernel documentation, "eBPF verifier". https://docs.kernel.org/bpf/verifier.html
4. Linux kernel documentation, "BPF maps". https://docs.kernel.org/bpf/maps.html
5. Linux kernel documentation, "BPF_MAP_TYPE_HASH, with PERCPU and LRU variants". https://docs.kernel.org/bpf/map_hash.html
6. Linux kernel documentation, "BPF Type Format (BTF)". https://docs.kernel.org/bpf/btf.html
7. A. Nakryiko, "BPF Portability and CO-RE", 2020. https://nakryiko.com/posts/bpf-portability-and-co-re/
8. T. Høiland-Jørgensen, J. D. Brouer, D. Borkmann, J. Fastabend, T. Herbert, D. Ahern, D. Miller, "The eXpress Data Path: Fast Programmable Packet Processing in the Operating System Kernel", *Proc. 14th Int. Conf. on emerging Networking EXperiments and Technologies (CoNEXT '18)*, ACM, 2018, pp. 54–66. doi:10.1145/3281411.3281443. Paper and artefacts: https://github.com/xdp-project/xdp-paper
9. eBPF Docs, "Program type BPF_PROG_TYPE_XDP". https://docs.ebpf.io/linux/program-type/BPF_PROG_TYPE_XDP/
10. Cilium documentation, "BPF and XDP Reference Guide". https://docs.cilium.io/en/stable/reference-guides/bpf/index.html
11. Cloudflare blog, "How to drop 10 million packets per second", 2018. https://blog.cloudflare.com/how-to-drop-10-million-packets/
12. Cloudflare blog, "L4Drop: XDP DDoS Mitigations", 2018. https://blog.cloudflare.com/l4drop-xdp-ebpf-based-ddos-mitigations/
13. Cloudflare blog, "Meet Gatebot – a bot that allows us to sleep", 2017. https://blog.cloudflare.com/meet-gatebot-a-bot-that-allows-us-to-sleep/
14. Cloudflare blog, "Announcing flowtrackd", 2020. https://blog.cloudflare.com/announcing-flowtrackd/
15. Facebook Incubator, "Katran" (source repository). https://github.com/facebookincubator/katran
16. Engineering at Meta, "Open-sourcing Katran, a scalable network load balancer", 2018. https://engineering.fb.com/2018/05/22/open-source/open-sourcing-katran-a-scalable-network-load-balancer/
17. Cloudflare blog, "Unimog – Cloudflare's edge load balancer", 2020. https://blog.cloudflare.com/unimog-cloudflares-edge-load-balancer/
18. Cilium documentation, "Kubernetes Without kube-proxy" (incl. XDP acceleration). https://docs.cilium.io/en/stable/network/kubernetes/kubeproxy-free/ – project: https://github.com/cilium/cilium
19. XDP project, "xdp-tools". https://github.com/xdp-project/xdp-tools
20. IO Visor, "BCC – BPF Compiler Collection". https://github.com/iovisor/bcc
21. bpftrace project. https://github.com/bpftrace/bpftrace
22. Suricata documentation, "eBPF and XDP". https://docs.suricata.io/en/latest/capture-hardware/ebpf-xdp.html
23. Linux kernel documentation, "AF_XDP". https://docs.kernel.org/networking/af_xdp.html
24. XDP project, "xdp-tutorial". https://github.com/xdp-project/xdp-tutorial
25. libbpf. https://github.com/libbpf/libbpf
26. Falco project. https://falco.org/
27. Tetragon project. https://tetragon.io/
28. Polycube project. https://github.com/polycube-network/polycube
