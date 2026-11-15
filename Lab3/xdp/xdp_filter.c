// SPDX-License-Identifier: GPL-2.0
/*
 * xdp_filter.c - Lab 3, Task 4: a small XDP source-IP blocklist filter.
 *
 * Purpose
 *   Drop every IPv4 packet whose source address is in the `blocklist` hash
 *   map and pass everything else. The map is filled from user space (for
 *   example with `bpftool map update`), so a list of attacking hosts, such as
 *   one derived from the DDoS detections of Tasks 1-3, can be enforced in the
 *   driver hook before the kernel allocates an skb.
 *   Every verdict is counted in the per-CPU `stats` map (PASS / DROP).
 *
 * Build   : make                 (clang -O2 -g -target bpf, see Makefile)
 * Attach  : sudo make attach     (generic mode on IFACE, default lo)
 * Detach  : sudo make detach
 * Details : see README.md
 */
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define BLOCKLIST_MAX_ENTRIES 1024 /* upper bound on blocked source IPs */
#define IP_MIN_IHL            5    /* minimum IPv4 header length in 32-bit words */

/* Indices into the `stats` array. */
enum stat_index {
	STAT_PASS = 0,
	STAT_DROP = 1,
	STAT_MAX  = 2, /* number of counters, used as max_entries */
};

/*
 * Blocklist: key = IPv4 source address in network byte order (exactly the
 * raw iph->saddr), value = a flag byte (its content is unused; presence is
 * what counts).
 */
struct {
	__uint(type, BPF_MAP_TYPE_HASH);
	__uint(max_entries, BLOCKLIST_MAX_ENTRIES);
	__type(key, __u32);
	__type(value, __u8);
} blocklist SEC(".maps");

/*
 * Counters: one 64-bit slot per verdict. PERCPU_ARRAY gives every CPU its own
 * copy, so the increment needs no atomic operation; user space sums the
 * per-CPU values when it reads the map.
 */
struct {
	__uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
	__uint(max_entries, STAT_MAX);
	__type(key, __u32);
	__type(value, __u64);
} stats SEC(".maps");

/*
 * Count the verdict and return it. All return paths of the program go
 * through here, so the counters always match what the kernel is told.
 */
static __always_inline int verdict(enum stat_index idx, int action)
{
	__u32 key = idx;
	__u64 *counter = bpf_map_lookup_elem(&stats, &key);

	/* The verifier forces a NULL check: a lookup may fail in general. */
	if (counter)
		(*counter)++;
	return action;
}

SEC("xdp")
int xdp_filter_prog(struct xdp_md *ctx)
{
	/* ctx->data / data_end are the packet bounds as integers. */
	void *data = (void *)(long)ctx->data;
	void *data_end = (void *)(long)ctx->data_end;
	struct ethhdr *eth = data;
	struct iphdr *iph;
	__u32 ihl_bytes;
	void *l4;

	/* Bounds check: the Ethernet header must lie fully inside the packet,
	 * otherwise the verifier rejects any read of eth->h_proto. */
	if ((void *)(eth + 1) > data_end)
		return verdict(STAT_PASS, XDP_PASS);

	/* Only IPv4 is filtered; ARP, IPv6, etc. pass untouched. */
	if (eth->h_proto != bpf_htons(ETH_P_IP))
		return verdict(STAT_PASS, XDP_PASS);

	iph = (struct iphdr *)(eth + 1);

	/* Bounds check: the fixed 20-byte IPv4 header must be present. */
	if ((void *)(iph + 1) > data_end)
		return verdict(STAT_PASS, XDP_PASS);

	/* ihl is the header length in 32-bit words; below 5 the header is
	 * malformed, so let the kernel deal with it. */
	if (iph->ihl < IP_MIN_IHL)
		return verdict(STAT_PASS, XDP_PASS);

	/* The L4 header starts after the IP header including its options. */
	ihl_bytes = iph->ihl * 4;
	l4 = (void *)iph + ihl_bytes;

	/* Bounds check for the options area: l4 must still be inside. */
	if (l4 > data_end)
		return verdict(STAT_PASS, XDP_PASS);

	if (iph->protocol == IPPROTO_TCP) {
		/* Truncated TCP header: pass, the kernel will handle it. */
		if (l4 + sizeof(struct tcphdr) > data_end)
			return verdict(STAT_PASS, XDP_PASS);
	} else if (iph->protocol == IPPROTO_UDP) {
		/* Truncated UDP header: pass, the kernel will handle it. */
		if (l4 + sizeof(struct udphdr) > data_end)
			return verdict(STAT_PASS, XDP_PASS);
	}
	/* Other protocols (ICMP, ...) need no L4 parsing: the decision only
	 * uses the source address. */

	/* Blocklist lookup with the raw network-order source address. */
	__u32 saddr = iph->saddr;

	if (bpf_map_lookup_elem(&blocklist, &saddr))
		return verdict(STAT_DROP, XDP_DROP);

	return verdict(STAT_PASS, XDP_PASS);
}

char LICENSE[] SEC("license") = "GPL";
