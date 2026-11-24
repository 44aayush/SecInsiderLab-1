// SPDX-License-Identifier: GPL-2.0
/*
 * xdp_ratelimit_user.c - loader / monitor for xdp_ratelimit.bpf.c
 *
 *   sudo ./xdp_ratelimit_user IFACE [--pps N] [--window-ms MS] [--mode skb|native]
 *                             [--allow IP]... [--block IP]... [--duration S] [--top N]
 *
 * Opens + loads the BPF skeleton, writes the config map, fills the
 * allow/block lists, attaches to IFACE, prints statistics every second and
 * detaches cleanly on Ctrl-C / SIGTERM (or after --duration seconds).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <errno.h>
#include <getopt.h>
#include <time.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <linux/types.h>
#include <linux/if_link.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include "xdp_ratelimit.h"
#include "xdp_ratelimit.skel.h"

static volatile sig_atomic_t stop;
static void on_signal(int sig) { (void)sig; stop = 1; }

static int verbose;
static int libbpf_print(enum libbpf_print_level lvl, const char *fmt, va_list ap)
{
	if (lvl == LIBBPF_DEBUG && !verbose)
		return 0;
	return vfprintf(stderr, fmt, ap);
}

static void usage(const char *p)
{
	fprintf(stderr,
		"Usage: %s IFACE [options]\n"
		"  --pps N          packets per window per source IP (default 100, 0 = off)\n"
		"  --window-ms MS   window length in ms (default 1000)\n"
		"  --mode skb|native  XDP attach mode (default skb = generic)\n"
		"  --allow IP       never rate-limit IP (repeatable)\n"
		"  --block IP       always drop IP (repeatable)\n"
		"  --duration S     detach and exit after S seconds (default: run until Ctrl-C)\n"
		"  --top N          show N top sources (default 5)\n"
		"  -v               libbpf debug output (verifier log on failure)\n", p);
}

static int add_ip(int map_fd, const char *s)
{
	struct in_addr a;
	__u8 one = 1;

	if (inet_pton(AF_INET, s, &a) != 1) {
		fprintf(stderr, "bad IPv4 address: %s\n", s);
		return -1;
	}
	return bpf_map_update_elem(map_fd, &a.s_addr, &one, BPF_ANY);
}

struct src { __u32 ip; struct rl_entry e; };

static int cmp_src(const void *a, const void *b)
{
	const struct src *x = a, *y = b;

	if (x->e.dropped != y->e.dropped)
		return x->e.dropped < y->e.dropped ? 1 : -1;
	return x->e.total < y->e.total ? 1 : (x->e.total > y->e.total ? -1 : 0);
}

/* Sum one per-CPU counter over all possible CPUs. */
static __u64 read_stat(int fd, __u32 idx, int ncpu)
{
	__u64 vals[ncpu], sum = 0;

	if (bpf_map_lookup_elem(fd, &idx, vals))
		return 0;
	for (int i = 0; i < ncpu; i++)
		sum += vals[i];
	return sum;
}

static void print_top(int fd, int top)
{
	static struct src s[4096];
	__u32 key, next, *prev = NULL;
	int n = 0;

	/* Iterate the LRU hash. (Entries may be evicted while we walk; fine.) */
	while (n < 4096 && bpf_map_get_next_key(fd, prev, &next) == 0) {
		if (bpf_map_lookup_elem(fd, &next, &s[n].e) == 0)
			s[n++].ip = next;
		key = next;
		prev = &key;
	}
	qsort(s, n, sizeof(s[0]), cmp_src);
	printf("    %-16s %12s %12s %10s\n", "source", "seen", "dropped", "drop%");
	for (int i = 0; i < n && i < top; i++) {
		char buf[INET_ADDRSTRLEN];
		struct in_addr a = { .s_addr = s[i].ip };

		inet_ntop(AF_INET, &a, buf, sizeof(buf));
		printf("    %-16s %12llu %12llu %9.1f%%\n", buf,
		       (unsigned long long)s[i].e.total,
		       (unsigned long long)s[i].e.dropped,
		       s[i].e.total ? 100.0 * s[i].e.dropped / s[i].e.total : 0.0);
	}
	if (n == 0)
		printf("    (no IPv4 sources seen yet)\n");
}

int main(int argc, char **argv)
{
	static const struct option opts[] = {
		{ "pps", required_argument, 0, 'p' },
		{ "window-ms", required_argument, 0, 'w' },
		{ "mode", required_argument, 0, 'm' },
		{ "allow", required_argument, 0, 'a' },
		{ "block", required_argument, 0, 'b' },
		{ "duration", required_argument, 0, 'd' },
		{ "top", required_argument, 0, 't' },
		{ "help", no_argument, 0, 'h' },
		{ 0 }
	};
	struct rl_config cfg = { .limit = 100, .window_ns = DEFAULT_WINDOW_NS };
	const char *allow[64], *block[64], *mode = "skb";
	int nallow = 0, nblock = 0, duration = 0, top = 5, c, err, ifindex;
	__u32 flags = XDP_FLAGS_UPDATE_IF_NOEXIST, zero = 0;
	struct xdp_ratelimit_bpf *skel;
	__u64 last[STAT_MAX] = { 0 };

	while ((c = getopt_long(argc, argv, "vh", opts, NULL)) != -1) {
		switch (c) {
		case 'p': cfg.limit = strtoull(optarg, NULL, 0); break;
		case 'w': cfg.window_ns = strtoull(optarg, NULL, 0) * 1000000ULL; break;
		case 'm': mode = optarg; break;
		case 'a': if (nallow < 64) allow[nallow++] = optarg; break;
		case 'b': if (nblock < 64) block[nblock++] = optarg; break;
		case 'd': duration = atoi(optarg); break;
		case 't': top = atoi(optarg); break;
		case 'v': verbose = 1; break;
		default: usage(argv[0]); return 1;
		}
	}
	if (optind >= argc) { usage(argv[0]); return 1; }
	ifindex = if_nametoindex(argv[optind]);
	if (!ifindex) { fprintf(stderr, "unknown interface %s\n", argv[optind]); return 1; }
	if (!strcmp(mode, "native") || !strcmp(mode, "drv"))
		flags |= XDP_FLAGS_DRV_MODE;
	else if (!strcmp(mode, "skb") || !strcmp(mode, "generic"))
		flags |= XDP_FLAGS_SKB_MODE;
	else { usage(argv[0]); return 1; }

	setvbuf(stdout, NULL, _IOLBF, 0);         /* line-buffered for tee/logs */
	libbpf_set_print(libbpf_print);

	/* open + load: the verifier runs inside load(). */
	skel = xdp_ratelimit_bpf__open_and_load();
	if (!skel) {
		fprintf(stderr, "failed to open/load BPF object (run with -v for verifier log)\n");
		return 1;
	}

	/* Configure BEFORE attaching so the first packet already sees it. */
	err = bpf_map_update_elem(bpf_map__fd(skel->maps.rl_config), &zero, &cfg, BPF_ANY);
	for (int i = 0; !err && i < nallow; i++)
		err = add_ip(bpf_map__fd(skel->maps.rl_allow), allow[i]);
	for (int i = 0; !err && i < nblock; i++)
		err = add_ip(bpf_map__fd(skel->maps.rl_block), block[i]);
	if (err) { fprintf(stderr, "map setup failed\n"); goto out; }

	err = bpf_xdp_attach(ifindex, bpf_program__fd(skel->progs.xdp_ratelimit), flags, NULL);
	if (err) {
		fprintf(stderr, "attach to %s (%s mode) failed: %s\n",
			argv[optind], mode, strerror(-err));
		goto out;
	}
	signal(SIGINT, on_signal);
	signal(SIGTERM, on_signal);
	printf("attached xdp_ratelimit to %s (ifindex %d, %s mode): limit %llu pkts / %llu ms per source IP\n",
	       argv[optind], ifindex, mode, (unsigned long long)cfg.limit,
	       (unsigned long long)(cfg.window_ns / 1000000ULL));

	int sfd = bpf_map__fd(skel->maps.rl_stats);
	int ncpu = libbpf_num_possible_cpus();
	for (int t = 1; !stop && (!duration || t <= duration); t++) {
		__u64 cur[STAT_MAX];

		sleep(1);
		for (int i = 0; i < STAT_MAX; i++)
			cur[i] = read_stat(sfd, i, ncpu);
		printf("[t=%3ds] pass %8llu (+%6llu/s) | drop-rate %8llu (+%6llu/s) | "
		       "drop-block %6llu | non-IPv4 %6llu\n", t,
		       (unsigned long long)cur[STAT_PASS],
		       (unsigned long long)(cur[STAT_PASS] - last[STAT_PASS]),
		       (unsigned long long)cur[STAT_DROP_RATE],
		       (unsigned long long)(cur[STAT_DROP_RATE] - last[STAT_DROP_RATE]),
		       (unsigned long long)cur[STAT_DROP_BLOCK],
		       (unsigned long long)cur[STAT_NON_IPV4]);
		print_top(bpf_map__fd(skel->maps.rl_state), top);
		memcpy(last, cur, sizeof(last));
	}

	bpf_xdp_detach(ifindex, flags & ~XDP_FLAGS_UPDATE_IF_NOEXIST, NULL);
	printf("detached xdp_ratelimit from %s\n", argv[optind]);
out:
	xdp_ratelimit_bpf__destroy(skel);
	return err ? 1 : 0;
}
