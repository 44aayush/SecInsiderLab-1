// SPDX-License-Identifier: GPL-2.0
/*
 * xdp_ratelimit.bpf.c - per-source-IPv4 rate limiter at the XDP hook.
 * Group 8 - Security Insider Lab, Lab 3 Task 4.
 *
 * Every IPv4 source address may send LIMIT_PPS packets per second.
 * Packets above the limit are dropped in XDP, before the kernel allocates
 * an sk_buff. Everything that is not IPv4 (ARP, IPv6, ...) is passed.
 */
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define LIMIT_PPS 100                   /* packets per second and source IP */
#define WINDOW_NS 1000000000ULL         /* fixed window of 1 s */

struct rate {
	__u64 win_start;                /* start of the current window (ns) */
	__u64 count;                    /* packets seen in the current window */
	__u64 passed;                   /* total packets passed */
	__u64 dropped;                  /* total packets dropped */
};

/* One entry per source IP. LRU: when the map is full, the least recently
 * used source is evicted instead of new sources being refused. */
struct {
	__uint(type, BPF_MAP_TYPE_LRU_HASH);
	__uint(max_entries, 65536);
	__type(key, __u8[4]);           /* source IPv4 address, e.g. [10,0,0,2] */
	__type(value, struct rate);
} rl_state SEC(".maps");

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

char LICENSE[] SEC("license") = "GPL";
