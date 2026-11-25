# Task 1: xdp-tools (xdp-filter, xdpdump)

## Install (T1.1)

Built from `~/src/xdp-tools` (v1.6.3-32-g92a9828) and installed by the user:

```bash
cd ~/src/xdp-tools && make && sudo make install && sudo ldconfig
```

Binaries land in `/usr/local/sbin` (`xdp-loader`, `xdp-filter`, `xdpdump`, `xdp-bench`), libxdp in `/usr/local/lib`, BPF objects in `/usr/local/lib/bpf`. Verification output: `logs/install_verify.log`. The demo also needs `tcpdump` and `python3`.

## Run

```bash
mkdir -p xdp_tools/logs
sudo bash xdp_tools/task1_demo.sh 2>&1 | tee xdp_tools/logs/task1_demo.log
```

The script refuses to run without root and exits with a clear message if `xdp-filter` or `xdpdump` are missing. It never touches a real interface.

## Sandbox

Netns `lab4t1` with a veth pair: `t1-host` (10.10.0.1/24, host side, where XDP is attached in generic/skb mode) and `t1-ns` (10.10.0.2/24, inside the netns). A `trap` on exit unloads xdp-filter, stops the HTTP server and deletes the netns and veth, on success and on failure. Commands are the forms from `xdp-filter/README.org` and `xdp-dump/README.org` with the interface swapped for `t1-host`. Steps marked "expected to fail" are tolerated.

## Sections and screenshots

1. **`xdpdump -D`, nothing loaded.** Lists interfaces with no XDP program. Screenshot `SS_T1_1`.
2. **`xdp-filter load --mode skb t1-host`, then `xdpdump -D`.** Now shows `xdp_dispatcher` and the `xdpfilt_alw_all` program on `t1-host`. `SS_T1_2`.
3. **Ping from the netns.** 3 packets, 0% loss: the filter passes everything by default. `SS_T1_3`.
4. **`xdp-filter ip 10.10.0.2 -m src`, ping, `xdp-filter status`.** The ping fails with 100% loss (expected); status lists the IP with non-zero hit counters. `SS_T1_4`.
5. **`xdpdump --rx-capture=entry,exit` during the ping, then remove the rule and ping.** Exit records show action `XDP_DROP`; after `-r` the ping has 0% loss. `SS_T1_5`.
6. **Port filter.** A Python HTTP server on 10.10.0.1:8000; GET from the netns returns 200; after `xdp-filter port 8000` the GET times out (expected); `status` shows the port; after `-r` the GET returns 200 again. `SS_T1_6`.
7. **`xdpdump -x`.** Hex dump of the ICMP packets seen at the XDP hook. `SS_T1_7`.
8. **`xdpdump -w - | tcpdump -r - -n`.** The same packets decoded by tcpdump (`IP 10.10.0.2 > 10.10.0.1: ICMP echo request`). `SS_T1_8`.
9. **`xdp-filter poll -i 1000`.** Per-second packet and byte rates per action for 5 s. `SS_T1_9`.
10. **`xdp-filter unload t1-host`, then `xdpdump -D`.** Nothing loaded again. `SS_T1_10`.
