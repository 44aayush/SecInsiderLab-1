# Lab 3, Task 5 - Download, configure and build xdp-tools (Group 8)

## 1. Source
- Repository: https://github.com/xdp-project/xdp-tools
- Commit: `92a98287fd59ec9392b8c609a09f4e36978cbd5d` (`v1.6.3-32-g92a9828`, TOOLS_VERSION 1.6.3, libxdp 1.7.0 .so)
- libbpf submodule (lib/libbpf): `f5dcbae736e5d7f83a35718e01be1a8e3010fa39` (v1.7.0). It was NOT used: configure found a recent enough system libbpf (v1.6.3 from libbpf-dev).
- Host: Ubuntu, kernel 7.0.0-43-generic, clang 21.1.8, bpftool v7.7.0.

## 2. What the tools do
| Tool | Purpose |
|---|---|
| libxdp | Library on top of libbpf for loading XDP programs. Lets several XDP programs share one interface via a dispatcher program (multi-prog support), plus helpers and the AF_XDP socket helper code. Built as libxdp.so / libxdp.a. |
| xdp-loader | CLI to load/unload/list XDP programs on an interface (`load`, `unload`, `status`, `clean`, `features`). Modes: native, skb (generic), hw. |
| xdp-filter | Simple packet filter running in XDP. Filters by IPv4/IPv6 address, TCP/UDP port, Ethernet MAC; allow or deny policy; drops at very high rate. Commands: load, unload, port, ip, ether, status, poll. |
| xdpdump | tcpdump-like capture at the XDP layer. Can attach to an already loaded XDP program (entry/exit of it) and write pcap files. |
| xdp-bench | Benchmarking tool for XDP actions (drop, pass, tx, redirect, devmap/cpumap redirect), reports packet rates. |
| xdp-monitor | Watches the kernel XDP tracepoints (redirect errors, exceptions, cpumap/devmap stats). |
| xdp-trafficgen | XDP-based packet generator (UDP) for load generation. |
| xdp-forward | XDP fast-path forwarding plane (uses the kernel FIB/flowtable). |

## 3. Dependencies
Required (from README/configure): clang >= 11 (LLVM, to compile BPF programs), llc/llvm, libbpf (system >= recent or the submodule), libelf, zlib, libpcap (xdpdump), m4, pkg-config, gcc/make; gcc-multilib (32-bit headers for BPF builds on some distros); bpftool (skeleton generation, "not building all tools" without it). Optional: emacs >= 26 (only to regenerate man pages from org files), libcap-ng (capability handling).

```
sudo apt install clang llvm libbpf-dev libelf-dev libpcap-dev m4 pkg-config build-essential gcc-multilib bpftool
# optional: libcap-ng-dev emacs
```

## 4. Commands used
```
cd Lab3/xdp/xdp-tools-build
git clone --recurse-submodules https://github.com/xdp-project/xdp-tools.git
cd xdp-tools
git rev-parse HEAD; git submodule status
./configure 2>&1 | tee ../logs/configure.log
make -j8     2>&1 | tee ../logs/make.log
sudo ../install_and_verify.sh      # installs + verifies, log in logs/install_verify.log
```

## 5. configure summary (logs/configure.log)
- clang 21.1.8 found (>= 11 required)
- bpftool v7.7.0 found, supports skeleton generation
- libbpf: system v1.6.3 used (submodule not needed)
- All feature probes "yes": perf_buffer__consume, btf__load_from_kernel_by_id, btf__type_cnt, bpf_object__next_map/program, bpf_program__insn_cnt/type/flags/expected_attach_type, bpf_map_create, perf_buffer__new_raw, bpf_xdp_attach, bpf_map__set_autocreate, bpf_prog_test_run_opts, bpf_xdp_query
- secure_getenv: yes
- cap-ng: no (libcap-ng-dev not installed; optional, no build impact)
- emacs not installed (only affects man-page regeneration; pre-generated man pages are in the repo)

## 6. Build result (logs/make.log)
`make -j8` finished with no errors and no warnings. Produced:
`lib/libxdp/libxdp.so(.1, .1.7.0)`, `libxdp.a`, `xdp-loader/xdp-loader`, `xdp-filter/xdp-filter`, `xdp-dump/xdpdump`, `xdp-bench/xdp-bench`, `xdp-monitor/xdp-monitor`, `xdp-trafficgen/xdp-trafficgen`, `xdp-forward/xdp-forward`, plus the BPF objects (xdpfilt_*.o, xdpdump_*.o, xdp_*.bpf.o).

## 7. Problems and fixes
1. clang/llc missing at first: the build dependencies were still being installed with apt; waited until `clang` and `llc` were on PATH, then ran configure. No source change.
2. `xdp-loader --version` does not exist in this version (prints "Command '--version' is unknown"). The verify script therefore uses `xdp-loader help` and reads version.mk (1.6.3) instead.
3. Without root, `xdp-loader features lo` prints "This program must be run as root." - expected; run through the sudo script.

## 8. Verification (install_and_verify.sh, log: logs/install_verify.log)
Run `sudo ./install_and_verify.sh`. It is kept short on purpose:
1. `make install` (binaries to /usr/local/sbin, BPF objects to /usr/local/lib/bpf, man pages) and `ldconfig`.
2. `xdp-loader help`, `xdp-filter help`, `xdpdump --help` must print their usage text.
3. `xdp-loader features lo` and `xdp-loader status` must run.
Ends with "ALL CHECKS PASSED".

The earlier version also ran an xdp-filter drop/allow test in a network namespace; it was
removed to keep Task 5 simple (kept in ../_archive_full_version/). The manual xdp-filter
check on `lo` (report section 7.3) shows the same thing by hand.
