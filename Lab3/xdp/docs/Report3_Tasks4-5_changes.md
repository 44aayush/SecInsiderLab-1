# Report 3: changes for Tasks 4 and 5 (simplified XDP part)

**What changed in the work:**
- **Task 4** now uses a minimal XDP program (`Lab3/xdp/ratelimit/xdp_ratelimit.bpf.c`, 78 lines).
  - The limit is fixed at 100 packets/s per source IP.
  - It uses one BPF map, `rl_state`.
  - There is no C loader, no config map and no allow/block lists.
  - `ip` attaches the program and `bpftool` reads the map.
  - The test is a short list of commands typed by hand in one network namespace (see `Lab3/xdp/ratelimit/README.md`).
- **Task 5** keeps the build and install, but the verify script now only runs `help`, `features lo` and `status`. The xdp-filter namespace test is gone. Section 7.3 (the manual loopback check) stays unchanged.

**How to use this file:**
- Section numbers refer to the current 25-page `G8.Report3.pdf`. Each block says what to replace or delete; text that is not mentioned stays as it is.
- All numbers come from the run on 24 Nov 2026 (`Lab3/xdp/ratelimit/task4_run2.txt`, `Lab3/xdp/xdp-tools-build/logs/install_verify.log`).
- New screenshots (in `Lab3/report/images/screenshots/`): `task4_baseline.png`, `task4_flood_xdp.png`, `task4_map_dump.png` and `xdptools_verify.png`.

---

## Abstract (last sentence)

Replace "with a limit of 100 packets/s per source, 679,608 flood packets sent by one
attacker led to only 500 reaching the victim, while benign traffic was unaffected." with:

```latex
with a limit of 100 packets/s per source, 697,064 flood packets sent by one attacker
led to only 500 reaching the victim, while benign traffic was unaffected.
```

## Chapter 6 intro

The last sentence becomes:

```latex
We first summarise eBPF, XDP, their use cases and tools, and then present our
per-source-IP rate limiter, the test and the measured results.
```

## 6.1 eBPF and XDP

The last sentence of the first paragraph ("…(CO-RE) [Nak20]; our program uses a generated
vmlinux.h and a libbpf skeleton.") becomes:

```latex
... (CO-RE) [Nak20]. Our program is small enough to need neither: it is compiled against
the kernel's UAPI headers and attached with iproute2.
```

## 6.2 Use cases and tools

Change the sentence before Table 6.1 to:

```latex
Table~6.1 lists the tools relevant here. We used iproute2 to attach our program and
bpftool to inspect it; Task~5 covers xdp-tools.
```

Table 6.1 has two rows to change:

| Tool | Type | Description |
|---|---|---|
| libbpf, bpftool | Library, CLI | libbpf: BPF loading library used by ip and bpftool; bpftool: inspects programs and maps. |
| iproute2 | CLI | Attaches our XDP object (`ip link set … xdpgeneric obj`). |

## 6.3 Our Filter: a Per-Source-IP Rate Limiter (replace the whole section)

**Delete** Figure 6.1 (the architecture diagram shows the loader and ML interface, which no longer exist) and Table 6.2 (the BPF maps). The single map is now described in the text.

```latex
\section{Our Filter: a Per-Source-IP Rate Limiter}
A volumetric flood such as a SYN flood sends far more packets per second from one source
than any legitimate client. Our XDP program therefore counts packets per IPv4 source
address in a fixed window of one second and drops every packet above a limit of 100
packets per second. We kept the program deliberately small (78 lines): the limit is a
compile-time constant, and all state lives in a single BPF map.

\paragraph{Decision path.} For every frame, the program (Listing~6.1) first checks that the
Ethernet and IPv4 headers lie within \texttt{data\_end}; without this bounds check the
verifier rejects the program. Frames that are not IPv4 (ARP, IPv6) are passed. For IPv4,
the program looks up the source address in \texttt{rl\_state} and creates an entry on the
first packet. If the entry's window has expired, it is reset. The packet count is then
incremented atomically, and a packet whose count exceeds the limit gets
\texttt{XDP\_DROP}; all others get \texttt{XDP\_PASS}. Each entry also counts passed and
dropped packets, so the map shows the effect per source.

\paragraph{Map choice.} \texttt{rl\_state} is an \texttt{LRU\_HASH} with 65,536 entries
(key: the four bytes of the source address; value: window start, count, passed, dropped).
At capacity the least recently used source is evicted, whereas a plain hash map would
refuse new entries, which an attacker could exploit. It is shared, not per-CPU, on
purpose: with receive-side scaling, one source's packets can be spread over several CPUs,
and per-CPU counters would raise the effective limit to limit $\times$ \#CPUs. The price is
an atomic \texttt{fetch\_add} (which requires the BPF v3 instruction set,
\texttt{-mcpu=v3}) and a benign race on the window reset, in which at worst a few extra
packets pass.

\paragraph{Build and loading.} \texttt{make} compiles the object with
\texttt{clang -O2 -g -target bpf -mcpu=v3} against the kernel's UAPI headers and libbpf's
\texttt{bpf\_helpers.h}. No user-space loader is needed: iproute2 attaches the object
(\texttt{ip link set dev veth0 xdpgeneric obj xdp\_ratelimit.bpf.o sec xdp}), and bpftool
shows the program and dumps the map; thanks to the BTF debug information (\texttt{-g}),
it prints the map entries with field names. We built it with clang 21.1.8 and bpftool
v7.7.0 on kernel 7.0.0-43-generic. The verifier accepted the program:
\texttt{bpftool prog show} reports it as loaded and JIT-compiled (584 bytes of
translated bytecode, 349 bytes of native code).
```

**Listing 6.1** gets the new caption *"The XDP program in xdp_ratelimit.bpf.c (map definition and includes above it omitted)."* Its content is lines 36–76 of the new file: use `\lstinputlisting[firstline=36,lastline=76]{xdp_ratelimit.bpf.c}`, or paste the code below with `firstnumber=35`.

```c
SEC("xdp")
int xdp_ratelimit(struct xdp_md *ctx)
{
	void *data     = (void *)(long)ctx->data;
	void *data_end = (void *)(long)ctx->data_end;
	struct ethhdr *eth = data;
	struct iphdr *ip = (void *)(eth + 1);
	struct rate *r;
	__u64 now = bpf_ktime_get_ns();
	__u32 src;

	/* Bounds check before any header access; without it the verifier
	 * rejects the program. Then: IPv4 only. */
	if ((void *)(ip + 1) > data_end)
		return XDP_PASS;
	if (eth->h_proto != bpf_htons(ETH_P_IP))
		return XDP_PASS;
	src = ip->saddr;

	r = bpf_map_lookup_elem(&rl_state, &src);
	if (!r) {                       /* first packet of this source */
		struct rate init = { .win_start = now };

		bpf_map_update_elem(&rl_state, &src, &init, BPF_ANY);
		r = bpf_map_lookup_elem(&rl_state, &src);
		if (!r)
			return XDP_PASS;
	}

	if (now - r->win_start >= WINDOW_NS) {  /* new window */
		r->win_start = now;
		r->count = 0;
	}

	/* Atomic, because packets of one source can arrive on several CPUs. */
	if (__sync_fetch_and_add(&r->count, 1) >= LIMIT_PPS) {
		__sync_fetch_and_add(&r->dropped, 1);
		return XDP_DROP;
	}
	__sync_fetch_and_add(&r->passed, 1);
	return XDP_PASS;
}
```

## 6.4 Test Bed (replace the whole section)

**Delete** Figure 6.2 (the namespace diagram of `run_demo.sh`).

```latex
\section{Test Bed}
To test the filter without touching a physical interface, we use a single network
namespace \texttt{atk}, connected to the host by a veth pair. The namespace has two
addresses on its interface: 10.0.0.2 acts as the attacker and 10.0.0.3 as a benign
client. The host (10.0.0.1, interface \texttt{veth0}) is the victim, and the rate limiter
is attached to \texttt{veth0} in generic (skb) mode. The attacker runs a SYN flood to port
80 (\texttt{hping3 -S -p 80 --flood}) for 5\,s. We count the packets that reach the
host's IP layer, i.e.\ that passed XDP, with the kernel counter \texttt{IpInReceives}
(\texttt{nstat}, reset before each round), and read the exact per-source counts from the
map. The commands are typed by hand (they are listed
in \texttt{README.md}): a baseline flood without XDP, attaching the program with
\texttt{ip}, the same flood while the benign client pings the victim five times per
second, and a dump of \texttt{rl\_state} with bpftool. The limit is 100 packets per second
and source.
```

## 6.5 Results (replace the whole section)

**Delete** the old Figures 6.3, 6.4 and 6.5 (demo phases 4, 5 and 6). Add the three new screenshots.

```latex
\section{Results}
Table~6.2 summarises both rounds. Without XDP, the attacker sent 372,537 packets in 5\,s,
and the host's IP layer received 372,564 packets, i.e.\ the whole flood plus 27 packets of
other host traffic (Figure~6.1). With the rate limiter, the attacker sent 697,064 packets,
and the IP layer received only 525 (Figure~6.2): the 500 flood packets that the limiter let
through (100 per second for 5\,s, as configured) and the 25 benign pings, all of which
were answered (0\,\% loss). The attacker could send almost twice as many packets with the
filter active; we attribute this to the CPU time the host spent on every SYN in the
baseline, since attacker and victim share the same machine.

\begin{table}[h]
\centering
\caption{Results of the two flood rounds (limit 100 packets/s per source, 5\,s flood;
values from \texttt{task4\_run2.txt}).}
\begin{tabular}{lrrr}
\toprule
Round & Packets sent & Packets at victim (IP layer) & Benign ping loss \\
\midrule
Baseline, no XDP         & 372,537 & 372,564 & -- \\
XDP, generic mode (ip)   & 697,064 & 525     & 0\,\% (25/25) \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Map.} The dump of \texttt{rl\_state} after the attack (Figure~6.3) shows one
entry per source. The attacker \texttt{[10,0,0,2]} has 500 packets passed and 696,564
dropped, which together are exactly the 697,064 packets hping3 sent. The benign client
\texttt{[10,0,0,3]} has 25 passed and none dropped. Because the entry is shared by all
CPUs, the limit of 500 in 5\,s held exactly, although the flood was processed on several
CPUs.

\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{task4_baseline.png}
\caption{Baseline without XDP: 372,537 SYN packets sent, 372,564 packets reach the
host's IP layer.}
\end{figure}

\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{task4_flood_xdp.png}
\caption{Flood with the rate limiter attached: 697,064 packets sent, 525 reach the
host's IP layer (500 flood packets and 25 pings); the benign ping has 0\,\% loss.}
\end{figure}

\begin{figure}[h]
\centering
\includegraphics[width=0.7\textwidth]{task4_map_dump.png}
\caption{\texttt{bpftool map dump name rl\_state}: 500 passed and 696,564 dropped for the
attacker, 25 passed and 0 dropped for the benign client.}
\end{figure}
```

## 6.6 Problems and Fixes (replace the old text, which was about the removed demo script)

```latex
\section{Problems and Fixes}
\emph{The firewall hid the flood.} In our first run we counted the TCP segments that
reached the host (\texttt{TcpInSegs}). The counter showed 5 in both rounds, also without
XDP, although hundreds of thousands of SYNs were sent. The reason is the host firewall
(ufw, default policy: deny incoming): netfilter drops the SYNs before TCP sees them, so
\texttt{TcpInSegs} only counted the host's own traffic. We therefore count with
\texttt{IpInReceives}, which the kernel increments when a packet enters the IP layer,
before netfilter, and which thus shows exactly what passed XDP. The map counters were
correct in both runs (500 passed in each).
```

## 6.7 Limitations and Bridge to the ML Model

Keep items (1)–(5). In (5), "our tests used veth on one host" stays. Add a sixth item at the end of the paragraph:

```latex
(6) \emph{Fixed limit.} The limit is a compile-time constant; changing it means
recompiling and re-attaching the program.
```

Replace the second paragraph (which starts "The block-list map rl_block is the interface…") with:

```latex
The program has no interface for a detector yet; this is the natural next step. A second
hash map with blocked source addresses, checked before the rate limit, would let a
user-space classifier (our Lab~3 model or a Lab~4 detector) act on its decision: it
inserts a flagged source with \texttt{bpf\_map\_update\_elem()} or
\texttt{bpftool map update}, and from the next packet on that source is dropped in the
driver. This is the division of labour Cloudflare uses at scale: Gatebot detects in user
space, L4Drop enforces in XDP [Clo17; Clo18b]. The classifier's decision latency
(Section~5.4) then matters once per flow, not per packet.
```

## 7 Task 5: intro (last sentence)

```latex
We downloaded it from GitHub, configured, built and installed it from source and checked
the installed tools.
```

## 7.2 Verification (replace the whole section)

```latex
\section{Verification}
The script \texttt{install\_and\_verify.sh} installs the tools (\texttt{make install},
\texttt{ldconfig}) and runs a few checks: \texttt{xdp-loader help}, \texttt{xdp-filter help}
and \texttt{xdpdump --help} must print their usage text, and \texttt{xdp-loader features lo}
and \texttt{xdp-loader status} must run. The feature query reports ``no'' for all XDP
features of the loopback device (no native XDP support), so only generic mode is possible
there; the status lists all interfaces without an XDP program. The run ended with
\texttt{ALL CHECKS PASSED} (Listing~7.2). Section~7.3 shows xdp-filter at work. It drops by
address with a ready-made tool, but has no rate limiting; our own program (Section~6.3)
limits per source instead.
```

Listing 7.2 gets the new caption *"Abridged excerpt of install_verify.log."* Its content is below. Alternatively, use the screenshot `xdptools_verify.png` as a figure.

```
=== install ===
installed to /usr/local/sbin
=== checks ===
$ xdp-loader help
Usage: xdp-loader COMMAND [options]
$ xdp-filter help
Usage: xdp-filter COMMAND [options]
$ xdpdump --help
Usage: xdpdump [options]
$ xdp-loader features lo
NETDEV_XDP_ACT_BASIC:           no
NETDEV_XDP_ACT_REDIRECT:        no
...
$ xdp-loader status
Interface        Prio  Program name      Mode     ID   Tag
lo                     <No XDP program loaded!>
...
ALL CHECKS PASSED
```

## 7.3 Manual Check on the Loopback Interface

No change.

## 7.4 Problems and Fixes

- Keep (1) Missing compiler, (3) Help commands exit non-zero, (4) No `--version` and (5) Root privileges.
- **Delete (2) "bpffs hidden inside the namespace"**, because the namespace test no longer exists.
- Renumber the remaining items (1)–(4).

## 8 Discussion: "From detection to enforcement" paragraph

```latex
\paragraph{From detection to enforcement.} The models of Tasks 1--3 only classify flows,
and our XDP filter (Chapter~6) only limits packet rates. Connecting them needs a block
list in the XDP program that a user-space detector fills (Section~6.7); since this
happens once per flow, the prediction times of Section~5.4 would be acceptable. We did
not build this connection, and the rate limiter works without any model.
```

## List of figures / tables

These update automatically in LaTeX. Check that no `\ref` points to a deleted figure or table, i.e. the old Fig. 6.1–6.5 and Table 6.2.

---

## Slides (`G8.Lab3.Presentation.pptx`)

| Slide | Change |
|---|---|
| 1 | Stat "500 of 679,608" → "500 of 697,064" |
| 2 | Item 6: "per-source-IP filter in XDP" (no change); item 7: "Test bed: namespaces, SYN flood, results" → "Test: one namespace, SYN flood, results" |
| 9 | Bullet "Our filter": "Per-source-IP rate limiter, limit and lists in maps, changeable at runtime" → "Per-source-IP rate limiter: 100 pkt/s, one LRU map, attached with ip". Replace the architecture image with the code (Listing 6.1) or delete it. |
| 10 | Replace the "Demo phase 4" screenshot with `task4_flood_xdp.png`; caption: "Flood with the limiter: 500 of 697,064 flood packets reach the victim, benign ping 0 % loss (25/25)". Optionally put `task4_baseline.png` next to it ("without XDP: 372,564 of 372,537 arrive") |
| 11 | Delete the block-list slide, or replace it with `task4_map_dump.png` ("Per-source counters in the map") and move "Block list for an ML detector" to future work |
| 12 | Verification: delete "Drop rule: 100 % loss; after removal: ping works"; keep "ALL CHECKS PASSED" and the lo bullet |
| 13 | "XDP limiter: 500 of 679,608" → "500 of 697,064"; "No trained model is connected to the block list yet" → "No block list / ML connection yet (future work)" |
