Lab 3 - Tasks 4 and 5 (simplified version, 24 Nov 2026)    Group 8
==================================================================

Start here: Report3_Tasks4-5_changes.md
  Section-by-section replacement text (LaTeX) for G8.Report3.pdf Chapters 6 and 7,
  plus the changes for the slides. All numbers are filled in.

task4_xdp_ratelimiter/
  xdp_ratelimit.bpf.c        the XDP program (78 lines): 100 packets/s per source IP,
                             one BPF map rl_state (LRU hash); no loader program
  Makefile                   make  ->  xdp_ratelimit.bpf.o
  README.md                  the commands we typed for the test (one network namespace)
  task4_terminal_output.txt  the terminal output of that test
  THEORY.md                  eBPF/XDP background, use cases, tools

  Result (limit 100 packets/s, 5 s SYN flood):
    no XDP     372,537 sent -> 372,564 packets at the host's IP layer
    with XDP   697,064 sent -> 525 at the IP layer (500 flood + 25 pings)
    map        attacker 10.0.0.2: passed 500, dropped 696,564
               benign   10.0.0.3: passed 25,  dropped 0  (ping 25/25)
    program    584 B bytecode, 349 B JIT code

  Note: count with IpInReceives, not TcpInSegs. Our ufw firewall drops the SYNs
  before TCP, so TcpInSegs stayed at 5 even without XDP.

task5_xdp_tools/
  NOTES.md                   how xdp-tools was downloaded, configured and built
  install_and_verify.sh      sudo ./install_and_verify.sh: make install + checks
  logs/                      configure.log, make.log, install_verify.log (ALL CHECKS PASSED)

screenshots/
  task4_baseline.png, task4_flood_xdp.png, task4_map_dump.png, xdptools_verify.png
