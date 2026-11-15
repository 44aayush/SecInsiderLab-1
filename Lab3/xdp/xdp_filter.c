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
 *   Only the Ethernet and the fixed IPv4 header are parsed; the decision
 *   needs nothing else, so no options or L4 parsing is done.
 *
 * Build   : make                 (clang -O2 -g -target bpf, see Makefile)
 * Attach  : sudo make attach     (generic mode on IFACE, default lo)
 * Detach  : sudo make detach
 * Details : see README.md
 */
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define BLOCKLIST_MAX_ENTRIES 1024 /* upper bound on blocked source IPs */

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

	/* Bounds check: the Ethernet header must lie fully inside the packet,
	 * otherwise the verifier rejects any read of eth->h_proto. */
	if ((void *)(eth + 1) > data_end)
		return verdict(STAT_PASS, XDP_PASS);

	/* Only plain IPv4 is filtered; ARP, IPv6 and VLAN-tagged (802.1Q) frames
	 * pass untouched, because h_proto is then not ETH_P_IP. */
	if (eth->h_proto != bpf_htons(ETH_P_IP))
		return verdict(STAT_PASS, XDP_PASS);

	iph = (struct iphdr *)(eth + 1);

	/* Bounds check: the fixed 20-byte IPv4 header must be present. This is
	 * all the decision needs (it reads only iph->saddr), so the lookup
	 * follows immediately: a packet from a blocked source is dropped even if
	 * its options or L4 header are truncated or malformed. */
	if ((void *)(iph + 1) > data_end)
		return verdict(STAT_PASS, XDP_PASS);

	/* Blocklist lookup with the raw network-order source address. */
	__u32 saddr = iph->saddr;

	if (bpf_map_lookup_elem(&blocklist, &saddr))
		return verdict(STAT_DROP, XDP_DROP);

	return verdict(STAT_PASS, XDP_PASS);
}

char LICENSE[] SEC("license") = "GPL";
