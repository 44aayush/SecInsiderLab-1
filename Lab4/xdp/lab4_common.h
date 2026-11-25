/* Lab 4 shared definitions (CLAUDE.md 5.3). script/common.py mirrors these values;
 * tests/test_consistency.py parses this file and compares them. */
#ifndef LAB4_COMMON_H
#define LAB4_COMMON_H

#include <linux/types.h>

#define N_FEATURES        10
#define MAX_NODES         8192
#define MAX_TREES         64   /* roots[0] = DT, roots[1..n] = XGB trees */
#define MAX_TREE_DEPTH    10   /* walk bound = MAX_TREE_DEPTH + 1 steps */
#define LEAF_SHIFT        16
#define CLASSIFY_MIN_PKTS 8
#define MAX_FLOWS         65536
#define MAX_BLOCKED       65536
#define N_TEST_VECS       1024

enum ids_mode { MODE_OFF = 0, MODE_DT = 1, MODE_XGB = 2, MODE_ALL = 3 };
enum ids_verdict { V_NORMAL = 0, V_MALICIOUS = 1, V_NONE = 255 };
enum ids_stat {
	ST_PKTS = 0,
	ST_PASS,
	ST_DROP,
	ST_FLOWS_CLASSIFIED,
	ST_FLOWS_MALICIOUS,
	ST_BLOCKS_ADDED,
	ST_NOT_TRACKED,
	N_STATS
};

/* 24 B; feature < 0 marks a leaf. */
struct tree_node {
	__s64 threshold;
	__s32 feature;
	__u32 left;
	__u32 right;
	__s32 leaf;
};

/* 24 B */
struct ids_config {
	__u32 mode;
	__u32 n_xgb_trees;
	__s64 xgb_base_margin;
	__u64 block_ns;
};

/* 16 B; saddr/daddr in network order, ports in host order. */
struct flow_key {
	__u32 saddr;
	__u32 daddr;
	__u16 sport;
	__u16 dport;
	__u8 proto;
	__u8 pad[3];
};

/* classified_ns 0 = not yet classified. */
struct flow_state {
	__u64 first_ns, last_ns, pkts, bytes, len_max, len_min, iat_max_ns, iat_min_ns,
		act_data_pkts, classified_ns;
	__s64 xgb_margin;
	__u32 dt_verdict, xgb_verdict, verdict, tcp_flags;
};

struct test_vec {
	__s64 x[N_FEATURES];
};

struct test_result {
	__s64 xgb_margin;
	__u32 dt_verdict;
	__u32 xgb_verdict;
};

#endif /* LAB4_COMMON_H */
