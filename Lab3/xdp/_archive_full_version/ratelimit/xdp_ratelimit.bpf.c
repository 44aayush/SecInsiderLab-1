// SPDX-License-Identifier: GPL-2.0
/*
 * xdp_ratelimit.bpf.c - per-source-IPv4 rate limiter at the XDP hook.
 *
 * For every received frame:
 *   Ethernet (+ optional one 802.1Q/802.1ad tag) -> IPv4 ?
 *     no  -> XDP_PASS               (ARP, IPv6, ... are not our business)
 *     yes -> src in rl_block ?      -> XDP_DROP  (static / ML-fed block-list)
 *            src in rl_allow ?      -> XDP_PASS  (trusted hosts bypass limit)
 *            fixed-window counter for src in rl_state:
 *              count <= limit       -> XDP_PASS
 *              count >  limit       -> XDP_DROP
 *
 * Group 8 - Security Insider Lab, Lab 3 Task 4.
 */
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>
#include "xdp_ratelimit.h"

#define ETH_P_IP      0x0800
#define ETH_P_8021Q   0x8100
#define ETH_P_8021AD  0x88A8

struct vlan_tag { __be16 tci; __be16 encap_proto; };

/* ---------------------------------------------------------------- maps -- */

/* Runtime configuration (written by user space). */
struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, __u32);
	__type(value, struct rl_config);
} rl_config SEC(".maps");

/* Per-source state. LRU so that the map can never fill up: when it is full the
 * least-recently-used source is evicted instead of new inserts failing.
 * Shared (not per-CPU) on purpose: with RSS one source may be spread over
 * several CPUs/queues; a per-CPU map would give each CPU its own budget and
 * the effective limit would become limit * nr_cpus. */
struct {
	__uint(type, BPF_MAP_TYPE_LRU_HASH);
	__uint(max_entries, 65536);
	__type(key, __u32);                 /* IPv4 saddr, network byte order */
	__type(value, struct rl_entry);
} rl_state SEC(".maps");

/* Global counters, per-CPU so that the hot path needs no atomics. */
struct {
	__uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
	__uint(max_entries, STAT_MAX);
	__type(key, __u32);
	__type(value, __u64);
} rl_stats SEC(".maps");

/* Allow-list: sources that are never limited. */
struct {
	__uint(type, BPF_MAP_TYPE_HASH);
	__uint(max_entries, 1024);
	__type(key, __u32);
	__type(value, __u8);
} rl_allow SEC(".maps");

/* Block-list: sources that are always dropped (e.g. fed by an IDS/ML model). */
struct {
	__uint(type, BPF_MAP_TYPE_HASH);
	__uint(max_entries, 65536);
	__type(key, __u32);
	__type(value, __u8);
} rl_block SEC(".maps");

/* ------------------------------------------------------------- helpers -- */

static __always_inline int count_and(__u32 stat, int action)
{
	__u64 *v = bpf_map_lookup_elem(&rl_stats, &stat);

	if (v)
		*v += 1;            /* per-CPU slot: no other CPU writes it */
	return action;
}

/* ------------------------------------------------------------- program -- */

SEC("xdp")
int xdp_ratelimit(struct xdp_md *ctx)
{
	void *data     = (void *)(long)ctx->data;
	void *data_end = (void *)(long)ctx->data_end;
	struct ethhdr *eth = data;
	struct iphdr *iph;
	struct rl_config *cfg;
	struct rl_entry *st;
	__u64 now, window, cnt;
	__u32 key = 0, saddr;
	__u16 proto;
	void *l3;

	/* 1. Ethernet. Every pointer must be checked against data_end before it
	 *    is dereferenced, otherwise the verifier rejects the program. */
	if ((void *)(eth + 1) > data_end)
		return count_and(STAT_NON_IPV4, XDP_PASS);
	proto = eth->h_proto;
	l3 = eth + 1;

	/* 2. Optional single VLAN tag. */
	if (proto == bpf_htons(ETH_P_8021Q) || proto == bpf_htons(ETH_P_8021AD)) {
		struct vlan_tag *vh = l3;

		if ((void *)(vh + 1) > data_end)
			return count_and(STAT_NON_IPV4, XDP_PASS);
		proto = vh->encap_proto;
		l3 = vh + 1;
	}

	/* 3. IPv4 only; everything else is passed to the normal stack. */
	if (proto != bpf_htons(ETH_P_IP))
		return count_and(STAT_NON_IPV4, XDP_PASS);
	iph = l3;
	if ((void *)(iph + 1) > data_end)
		return count_and(STAT_NON_IPV4, XDP_PASS);
	saddr = iph->saddr;

	/* 4. Block-list / allow-list (plain hash lookups, O(1)). */
	if (bpf_map_lookup_elem(&rl_block, &saddr))
		return count_and(STAT_DROP_BLOCK, XDP_DROP);
	if (bpf_map_lookup_elem(&rl_allow, &saddr))
		return count_and(STAT_PASS, XDP_PASS);

	/* 5. Read configuration; limit 0 disables limiting. */
	cfg = bpf_map_lookup_elem(&rl_config, &key);
	if (!cfg || cfg->limit == 0)
		return count_and(STAT_PASS, XDP_PASS);
	window = cfg->window_ns ? cfg->window_ns : DEFAULT_WINDOW_NS;

	/* 6. Fixed-window counter per source IP. */
	now = bpf_ktime_get_ns();
	st = bpf_map_lookup_elem(&rl_state, &saddr);
	if (!st) {
		struct rl_entry fresh = { .win_start = now, .count = 1, .total = 1 };

		bpf_map_update_elem(&rl_state, &saddr, &fresh, BPF_ANY);
		return count_and(STAT_PASS, XDP_PASS);
	}

	if (now - st->win_start >= window) {
		/* New window. Two CPUs may race here; worst case a handful of
		 * extra packets pass - acceptable for a rate limiter. */
		st->win_start = now;
		st->count = 0;
	}
	__sync_fetch_and_add(&st->total, 1);
	cnt = __sync_fetch_and_add(&st->count, 1) + 1;   /* atomic: shared map */

	if (cnt > cfg->limit) {
		__sync_fetch_and_add(&st->dropped, 1);
		return count_and(STAT_DROP_RATE, XDP_DROP);
	}
	return count_and(STAT_PASS, XDP_PASS);
}

char LICENSE[] SEC("license") = "GPL";
