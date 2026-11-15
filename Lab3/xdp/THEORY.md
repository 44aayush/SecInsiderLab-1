# Task 4 theory: eBPF and XDP

## 1. What eBPF is

eBPF (extended Berkeley Packet Filter) is a small virtual machine inside the Linux kernel. User space loads
small programs into it, and the kernel runs them safely when a given event happens. The kernel does not
need to be recompiled and no kernel module is needed.

- **Programs and hooks.** A program is attached to a *hook*: a network driver receive path (XDP), the
  traffic control layer (tc), a socket, a tracepoint, a kprobe on a kernel function, a cgroup event, and more.
  The program type decides which hook it fits and which context it receives.
- **Verifier.** Before a program runs, the kernel verifier checks every possible path through it. It rejects
  unbounded loops, reads outside the packet or a map value (hence the many bounds checks in C code), use of
  uninitialised data and NULL dereferences. This is what makes it safe to run user-supplied code in the kernel.
- **JIT.** After verification the bytecode is compiled to native machine code, so execution is close to the
  speed of kernel code.
- **Maps.** Maps are key/value stores in kernel memory (hash, array, per-CPU array, LPM trie, ring buffer, ...).
  They hold state between program runs and are the channel between the kernel program and user space:
  user space can read and update them while the program runs.
- **Helpers.** Programs cannot call arbitrary kernel functions. They call a fixed set of helper functions
  (for example `bpf_map_lookup_elem`, `bpf_redirect`, `bpf_ktime_get_ns`).
- **BTF and CO-RE.** BTF is compact type information for the kernel and for the program. With it, "compile
  once, run everywhere" (CO-RE) lets a program adapt to different kernel struct layouts at load time, and
  BTF also lets maps be described declaratively in C (`SEC(".maps")`), as in our filter.
- **Workflow.** Write restricted C, compile with `clang -target bpf` to an ELF object, load it with a
  loader (libbpf, `ip`, `bpftool`), which verifies, JIT-compiles and attaches it.

## 2. What XDP is

XDP (eXpress Data Path) is an eBPF hook at the earliest point of the receive path: in the NIC driver,
right after the packet is DMA-ed into memory and **before** the kernel allocates an `sk_buff`, runs the
protocol stack, connection tracking or netfilter. Skipping that work is what makes XDP fast, which is
why it is used at line rate for packet drops.

The program sees the raw frame (`ctx->data` .. `ctx->data_end`) and returns an action:

| Action | Meaning |
|---|---|
| `XDP_PASS` | hand the packet to the normal network stack |
| `XDP_DROP` | drop it immediately in the driver (cheapest possible drop) |
| `XDP_TX` | send it back out of the same interface (e.g. reflect or load-balance) |
| `XDP_REDIRECT` | send it to another interface, CPU or an AF_XDP socket |
| `XDP_ABORTED` | drop and signal an error (visible via the `xdp_exception` tracepoint) |

**Attach modes**

| Mode | Where it runs | Notes |
|---|---|---|
| Native (driver) | inside the NIC driver | fastest; needs driver support |
| Generic (`xdpgeneric`) | in the core stack, after the skb exists | works on any interface including `lo` and veth; slower; used in our demo |
| Offload | on the NIC hardware (SmartNIC) | no CPU use; only a few NICs and a limited feature set |

**Where packets can be dropped.** iptables/nftables (netfilter) drop after the skb is built and after
several stack stages. tc (`cls_bpf`) runs after the skb exists but earlier than netfilter and can also
filter egress. XDP drops before any of that, so it spends the fewest CPU cycles per dropped packet.
The price is that XDP sees only raw frames (no connection tracking, no socket context), and its program
model is stricter.

## 3. Use cases

- **DDoS mitigation.** Drop floods (SYN, UDP, amplification traffic) at the driver before they consume CPU.
  This ties directly to this lab: Tasks 1-3 train models that detect DDoS flows in CIC-IDS2017. A
  detector works on flow features and runs in user space; once it flags a source, a blocklist entry can
  be written into an XDP map, and the data path enforces it cheaply. Cloudflare and others use XDP this way.
- **Load balancing.** Katran (Meta) is an XDP-based L4 load balancer that rewrites and forwards
  packets with `XDP_TX` without touching the normal stack.
- **Monitoring and observability.** eBPF programs count, sample and trace packets or kernel events with
  low overhead and export them through maps or ring buffers (flow statistics, latency, packet capture with
  `xdpdump`).
- **Firewalling and networking.** Cilium uses eBPF for Kubernetes networking, policy enforcement and
  service load balancing, replacing large iptables rule sets with map lookups.

## 4. Tools

| Tool | What it is |
|---|---|
| **clang/LLVM** | compiler with a BPF backend, produces the ELF object |
| **libbpf** | the standard C library to load objects, create maps and attach programs |
| **libxdp** | library (from xdp-tools) that lets several XDP programs share one interface (dispatcher) |
| **xdp-tools** | `xdp-loader` (load/unload/status), `xdp-filter` (ready-made packet filter), `xdpdump` (capture at XDP), `xdp-bench` (benchmarks), `xdp-trafficgen`, `xdp-monitor` |
| **bpftool** | inspect and manage programs, maps, links and BTF; we use it to update the blocklist and dump counters |
| **iproute2** | `ip link set dev X xdpgeneric obj FILE sec xdp` attaches a program (`xdpgeneric`, `xdpdrv` or `xdpoffload` select the mode) |
| **bcc** | Python/C toolkit with many ready tracing tools; compiles at run time |
| **bpftrace** | high-level awk-like tracing language for one-liners |
| **Cilium** | eBPF-based Kubernetes networking, security and observability |
| **Katran** | XDP-based L4 load balancer |

xdp-tools is the subject of Task 5.

## 5. Our filter

`xdp_filter.c` is a small libbpf-style program: it parses only Ethernet and the fixed IPv4 header (no options or
L4 parsing, the decision reads only the source address), drops packets whose source IPv4 address is in the `blocklist` hash map, and counts PASS and
DROP in the per-CPU `stats` array. The lookup follows the IPv4 header bounds check directly, so malformed
packets from a blocked source are dropped too. IPv6 and VLAN-tagged (802.1Q) frames are passed unfiltered. Build and demo steps are in `README.md`. The code is commented
at every verifier bounds check.

## Sources

- Linux kernel documentation, BPF: https://docs.kernel.org/bpf/
- eBPF documentation and introduction: https://ebpf.io/
- XDP tutorial: https://github.com/xdp-project/xdp-tutorial
- xdp-tools: https://github.com/xdp-project/xdp-tools
- T. Høiland-Jørgensen et al., "The eXpress Data Path: Fast Programmable Packet Processing in the Operating
  System Kernel", ACM CoNEXT 2018.
- Katran: https://github.com/facebookincubator/katran
- Cilium: https://cilium.io/
