// SPDX-License-Identifier: GPL-2.0
/* Lab 4: in-kernel DDoS detection and filtering (CLAUDE.md 4.1, 5.1-5.3).
 * Program xdp_ids: parse, per-flow counters, DT/XGB tree walk, source blocklist.
 * Program classify_test: runs the same classifier on test_vecs[] for parity tests.
 * Fail-open: every internal error returns XDP_PASS. */
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/in.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <bpf/bpf_endian.h>
#include <bpf/bpf_helpers.h>

#include "lab4_common.h"

#define IP_FRAG_MASK 0x3FFF /* MF flag | fragment offset */
#define TCP_FLAGS_OFF 13    /* byte offset of the flag octet in the TCP header */
#define TCP_FIN 0x01
#define TCP_RST 0x04
#define NS_PER_UNIT 1000 /* milli-bytes scale of the mean packet length */

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, __u32);
	__type(value, struct ids_config);
} config SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, MAX_NODES);
	__type(key, __u32);
	__type(value, struct tree_node);
} nodes SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, MAX_TREES + 1);
	__type(key, __u32);
	__type(value, __u32);
} roots SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_LRU_HASH);
	__uint(max_entries, MAX_FLOWS);
	__type(key, struct flow_key);
	__type(value, struct flow_state);
} flows SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_LRU_HASH);
	__uint(max_entries, MAX_BLOCKED);
	__type(key, __u32);
	__type(value, __u64);
} blocklist SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
	__uint(max_entries, N_STATS);
	__type(key, __u32);
	__type(value, __u64);
} stats SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, N_TEST_VECS);
	__type(key, __u32);
	__type(value, struct test_vec);
} test_vecs SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, N_TEST_VECS);
	__type(key, __u32);
	__type(value, struct test_result);
} test_results SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, __u32);
	__type(value, __u32);
} test_idx SEC(".maps");

/* Parsed packet: only what the flowmeter needs. */
struct pkt_info {
	struct flow_key key;
	__u64 payload;
	__u32 tcp_flags;
};

/* Context handed to the bpf_loop callback that sums the XGB trees. */
struct xgb_ctx {
	const __s64 *x;
	__s64 sum;
};

/* Purpose: increment one per-CPU counter. Inputs: stat index. */
static __always_inline void stat_inc(__u32 idx)
{
	__u64 *v = bpf_map_lookup_elem(&stats, &idx);

	if (v) /* lookup can fail: the verifier requires the NULL check */
		(*v)++;
}

/* Purpose: walk one tree with integer thresholds (left iff x <= T).
 * Inputs: root node index, feature vector. Return: leaf value; 0 on any error (fail open). */
static __always_inline __s32 walk_tree(__u32 root, const __s64 *x)
{
	__u32 idx = root;

	/* constant bound so the verifier can prove termination */
	for (int step = 0; step <= MAX_TREE_DEPTH; step++) {
		struct tree_node *n = bpf_map_lookup_elem(&nodes, &idx);

		if (!n) /* idx out of range or map not loaded */
			return 0;
		if (n->feature < 0)
			return n->leaf;
		__u32 f = n->feature;

		if (f >= N_FEATURES) /* bounds the variable stack/map offset */
			return 0;
		idx = x[f] <= n->threshold ? n->left : n->right;
	}
	return 0;
}

/* Purpose: bpf_loop callback, adds the leaf of XGB tree i (roots[i + 1]).
 * Return: 0 to continue. */
static long xgb_cb(__u32 i, void *data)
{
	struct xgb_ctx *c = data;
	__u32 k = i + 1;
	__u32 *root = bpf_map_lookup_elem(&roots, &k);

	if (root)
		c->sum += walk_tree(*root, c->x);
	return 0;
}

/* Purpose: decision-tree verdict. Inputs: feature vector. Return: V_NORMAL / V_MALICIOUS. */
static __always_inline __u32 dt_classify(const __s64 *x)
{
	__u32 zero = 0;
	__u32 *root = bpf_map_lookup_elem(&roots, &zero);

	if (!root)
		return V_NORMAL;
	return walk_tree(*root, x) > 0 ? V_MALICIOUS : V_NORMAL;
}

/* Purpose: XGBoost margin (fixed point, 2^LEAF_SHIFT). Inputs: config, feature vector.
 * Return: base margin plus the sum of all tree leaves. */
static __always_inline __s64 xgb_margin(const struct ids_config *cfg, const __s64 *x)
{
	struct xgb_ctx c = { .x = x, .sum = 0 };
	__u32 n = cfg->n_xgb_trees;

	if (n > MAX_TREES) /* cap: roots has MAX_TREES + 1 slots */
		n = MAX_TREES;
	bpf_loop(n, xgb_cb, &c, 0);
	return cfg->xgb_base_margin + c.sum;
}

/* Purpose: classify one feature vector for a mode (DT, XGB or ALL = both agree).
 * Inputs: config, mode, vector, outputs for the per-model verdicts and the margin.
 * Return: final verdict. The model not run gets V_NONE. */
static __always_inline __u32 classify(const struct ids_config *cfg, __u32 mode, const __s64 *x,
				      __u32 *dt, __u32 *xgb, __s64 *margin)
{
	*dt = V_NONE;
	*xgb = V_NONE;
	*margin = 0;
	if (mode & MODE_DT)
		*dt = dt_classify(x);
	if (mode & MODE_XGB) {
		*margin = xgb_margin(cfg, x);
		*xgb = *margin > 0 ? V_MALICIOUS : V_NORMAL; /* exact 0 is Normal */
	}
	if (mode == MODE_DT)
		return *dt;
	if (mode == MODE_XGB)
		return *xgb;
	return (*dt == V_MALICIOUS && *xgb == V_MALICIOUS) ? V_MALICIOUS : V_NORMAL;
}

/* Purpose: parse Ethernet/IPv4/TCP|UDP with bounds checks (step 1).
 * Inputs: xdp context, output. Return: 0 if tracked, -1 for anything else. */
static __always_inline int parse_pkt(struct xdp_md *ctx, struct pkt_info *p)
{
	void *data = (void *)(long)ctx->data;
	void *data_end = (void *)(long)ctx->data_end;
	struct ethhdr *eth = data;
	struct iphdr *ip;
	void *l4;
	__u32 ihl_bytes, l4len;
	__s32 payload;

	if ((void *)(eth + 1) > data_end)
		return -1;
	if (eth->h_proto != bpf_htons(ETH_P_IP))
		return -1;
	ip = (void *)(eth + 1);
	if ((void *)(ip + 1) > data_end)
		return -1;
	if (ip->ihl < 5 || (ip->frag_off & bpf_htons(IP_FRAG_MASK)))
		return -1;
	ihl_bytes = ip->ihl * 4;
	l4 = (void *)ip + ihl_bytes;
	__builtin_memset(p, 0, sizeof(*p));
	p->key.saddr = ip->saddr;
	p->key.daddr = ip->daddr;
	p->key.proto = ip->protocol;
	if (ip->protocol == IPPROTO_TCP) {
		struct tcphdr *tcp = l4;

		if ((void *)(tcp + 1) > data_end) /* also covers the flag octet read below */
			return -1;
		if (tcp->doff < 5)
			return -1;
		l4len = tcp->doff * 4;
		p->key.sport = bpf_ntohs(tcp->source);
		p->key.dport = bpf_ntohs(tcp->dest);
		p->tcp_flags = *((__u8 *)tcp + TCP_FLAGS_OFF);
	} else if (ip->protocol == IPPROTO_UDP) {
		struct udphdr *udp = l4;

		if ((void *)(udp + 1) > data_end)
			return -1;
		l4len = sizeof(*udp);
		p->key.sport = bpf_ntohs(udp->source);
		p->key.dport = bpf_ntohs(udp->dest);
	} else {
		return -1;
	}
	payload = (__s32)bpf_ntohs(ip->tot_len) - (__s32)ihl_bytes - (__s32)l4len;
	if (payload < 0) /* inconsistent lengths: not tracked */
		return -1;
	p->payload = payload;
	return 0;
}

/* Purpose: fold one packet into the flow state (step 4). Inputs: state, packet, time. */
static __always_inline void flow_update(struct flow_state *st, const struct pkt_info *p, __u64 now)
{
	if (st->pkts == 1) {
		__u64 iat = now - st->last_ns;

		st->iat_max_ns = iat; /* second packet sets both */
		st->iat_min_ns = iat;
	} else if (st->pkts > 1) {
		__u64 iat = now - st->last_ns;

		if (iat > st->iat_max_ns)
			st->iat_max_ns = iat;
		if (iat < st->iat_min_ns)
			st->iat_min_ns = iat;
	}
	st->pkts++;
	st->bytes += p->payload;
	if (p->payload > st->len_max)
		st->len_max = p->payload;
	if (p->payload < st->len_min)
		st->len_min = p->payload;
	if (p->payload > 0)
		st->act_data_pkts++;
	st->last_ns = now;
	st->tcp_flags |= p->tcp_flags;
}

/* Purpose: build the 10 kernel features of CLAUDE.md 5.1. Inputs: state, output vector. */
static __always_inline void build_features(const struct flow_state *st, __s64 *x)
{
	__u64 span = st->last_ns - st->first_ns;

	x[0] = st->pkts;
	x[1] = st->bytes;
	x[2] = st->len_max;
	x[3] = st->len_min;
	x[4] = st->pkts ? st->bytes * NS_PER_UNIT / st->pkts : 0;
	x[5] = span;
	x[6] = st->pkts > 1 ? span / (st->pkts - 1) : 0;
	x[7] = st->pkts > 1 ? st->iat_max_ns : 0;
	x[8] = st->pkts > 1 ? st->iat_min_ns : 0;
	x[9] = st->act_data_pkts;
}

/* Purpose: the real-time cycle. Return: XDP_PASS or XDP_DROP. */
SEC("xdp")
int xdp_ids(struct xdp_md *ctx)
{
	struct pkt_info p;
	struct flow_state *st;
	struct ids_config *cfg;
	__u32 zero = 0, dt, xgb, verdict;
	__s64 margin, x[N_FEATURES];
	__u64 now, *expiry;

	if (parse_pkt(ctx, &p) < 0) {
		stat_inc(ST_NOT_TRACKED);
		stat_inc(ST_PASS);
		return XDP_PASS;
	}
	stat_inc(ST_PKTS);
	now = bpf_ktime_get_ns();

	expiry = bpf_map_lookup_elem(&blocklist, &p.key.saddr);
	if (expiry) {
		if (*expiry > now) {
			stat_inc(ST_DROP);
			return XDP_DROP;
		}
		bpf_map_delete_elem(&blocklist, &p.key.saddr);
	}

	st = bpf_map_lookup_elem(&flows, &p.key);
	if (!st) {
		struct flow_state init = {
			.first_ns = now, .last_ns = now, .len_min = ~0ULL,
			.dt_verdict = V_NONE, .xgb_verdict = V_NONE, .verdict = V_NONE,
		};

		bpf_map_update_elem(&flows, &p.key, &init, BPF_NOEXIST);
		st = bpf_map_lookup_elem(&flows, &p.key);
		if (!st) { /* LRU raced away the entry: fail open */
			stat_inc(ST_NOT_TRACKED);
			stat_inc(ST_PASS);
			return XDP_PASS;
		}
	}
	flow_update(st, &p, now);

	cfg = bpf_map_lookup_elem(&config, &zero);
	if (!cfg || cfg->mode == MODE_OFF ||
	    !((p.tcp_flags & (TCP_FIN | TCP_RST)) ||
	      (st->pkts >= CLASSIFY_MIN_PKTS && (st->pkts & (st->pkts - 1)) == 0))) {
		stat_inc(ST_PASS);
		return XDP_PASS;
	}

	build_features(st, x);
	verdict = classify(cfg, cfg->mode, x, &dt, &xgb, &margin);
	st->dt_verdict = dt;
	st->xgb_verdict = xgb;
	st->xgb_margin = margin;
	st->verdict = verdict;
	st->classified_ns = now;
	stat_inc(ST_FLOWS_CLASSIFIED);

	if (verdict == V_MALICIOUS) {
		__u64 until = now + cfg->block_ns;

		bpf_map_update_elem(&blocklist, &p.key.saddr, &until, BPF_ANY);
		stat_inc(ST_BLOCKS_ADDED);
		stat_inc(ST_FLOWS_MALICIOUS);
		stat_inc(ST_DROP);
		return XDP_DROP;
	}
	stat_inc(ST_PASS);
	return XDP_PASS;
}

/* Purpose: parity test. Classifies test_vecs[test_idx] with DT and XGB, stores the result in
 * test_results[idx], advances test_idx. Return: XDP_PASS (run with bpftool prog run repeat N). */
SEC("xdp")
int classify_test(struct xdp_md *ctx)
{
	__u32 zero = 0, dt, xgb;
	__s64 margin;
	__u32 *idx = bpf_map_lookup_elem(&test_idx, &zero);
	struct ids_config *cfg = bpf_map_lookup_elem(&config, &zero);
	struct test_vec *v;
	struct test_result *r;
	__u32 i;

	if (!idx || !cfg)
		return XDP_PASS;
	i = *idx;
	v = bpf_map_lookup_elem(&test_vecs, &i);
	r = bpf_map_lookup_elem(&test_results, &i);
	if (!v || !r) /* idx past N_TEST_VECS: nothing to do */
		return XDP_PASS;
	classify(cfg, MODE_ALL, v->x, &dt, &xgb, &margin);
	r->xgb_margin = margin;
	r->dt_verdict = dt;
	r->xgb_verdict = xgb;
	*idx = i + 1;
	return XDP_PASS;
}

char LICENSE[] SEC("license") = "GPL";
