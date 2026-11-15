/* SPDX-License-Identifier: GPL-2.0 */
/* Types shared between the XDP program (kernel) and the loader (user space). */
#ifndef XDP_RATELIMIT_H
#define XDP_RATELIMIT_H

/* Single-entry ARRAY map "rl_config", key 0. Changing it takes effect on the
 * next packet - no recompile, no reload. */
struct rl_config {
	__u64 limit;      /* max packets per source IP per window; 0 = limiter off */
	__u64 window_ns;  /* window length in ns; 0 = default (1 s)              */
};

/* Value of the LRU_HASH "rl_state", key = IPv4 source address (network order). */
struct rl_entry {
	__u64 win_start;  /* bpf_ktime_get_ns() at start of current window */
	__u64 count;      /* packets seen in current window                 */
	__u64 total;      /* packets seen since the entry was created       */
	__u64 dropped;    /* packets dropped by the limiter                 */
};

/* Index into the PERCPU_ARRAY "rl_stats". */
enum rl_stat {
	STAT_PASS = 0,     /* IPv4, under the limit (or allow-listed) -> XDP_PASS */
	STAT_DROP_RATE,    /* IPv4, over the limit                    -> XDP_DROP */
	STAT_DROP_BLOCK,   /* IPv4, source in block-list              -> XDP_DROP */
	STAT_NON_IPV4,     /* ARP, IPv6, ... passed untouched         -> XDP_PASS */
	STAT_MAX,
};

#define DEFAULT_WINDOW_NS 1000000000ULL /* 1 s => limit is "packets per second" */

#endif
