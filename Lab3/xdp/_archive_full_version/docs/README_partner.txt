Lab 3 - Tasks 4 and 5 (eBPF/XDP rate limiter, xdp-tools)    Group 8
=====================================================================

Start here: Lab3_Tasks4-5_Walkthrough.pdf (24 pages: what was done, how, and why,
including every problem we hit and how it was fixed).

task4_xdp_ratelimiter/
  THEORY.md                eBPF/XDP background, use cases, tools (report section 5.1)
  xdp_ratelimit.bpf.c/.h   kernel-side XDP program: per-source-IP fixed-window rate
                           limiter + allow/block lists (BPF maps rl_state, rl_config,
                           rl_block, rl_allow, rl_stats)
  xdp_ratelimit_user.c     libbpf loader: attach (skb/native), set limit, live stats
  Makefile                 build:  make     (needs clang, llvm, libbpf-dev, bpftool)
  run_demo.sh              full demo in throw-away network namespaces:
                           sudo ./run_demo.sh   (phases 0-8, writes logs/demo.log)
  logs/demo.log            the successful run used in the report
  figures/                 architecture diagram + the script that draws it

  Key results (logs/demo.log):
    baseline, no XDP     331,744 SYNs sent -> 331,745 reached victim
    XDP generic (skb)    679,608 sent -> 500 reached (100 pps x 5 s), benign ping 25/25
    XDP native           613,271 sent -> 500 reached
    iproute2 load        383,335 sent -> 300 reached (3 s)
    block-list           attacker 0/5 pings, benign 5/5
    verifier accepted: 2208 B xlated, 1257 B jited

task5_xdp_tools/
  NOTES.md                 how xdp-tools was downloaded/configured/built
                           (commit 92a98287fd59, system libbpf 1.6.3)
  install_and_verify.sh    sudo ./install_and_verify.sh  - install + functional test
                           (xdp-filter drops a source IP on a veth, then lets it pass)
  logs/                    configure.log, make.log, install_verify.log (ALL CHECKS PASSED)

screenshots/               cropped versions used in the report
  original_full/           the full-screen originals

report_extract/            report pages 11-19 (Tasks 4 and 5) + their LaTeX sources
