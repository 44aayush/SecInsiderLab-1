# REALTIME.md: the real-time path of Lab 4 (capture, Flowmeter, classifier, filter)

This file explains how traffic reaches the XDP program, what the in-kernel Flowmeter computes, how the classifier and the filter decide, how user space drives it, and how a dataset is pushed through the same kernel classifier. Every name, struct, formula and number is taken from the code (`xdp/lab4_common.h`, `xdp/lab4_xdp.bpf.c`, `script/*.py`, `docker/*`, `tests/*`) or from `CLAUDE.md` section 3 (measured facts). Section 7 and the snippet in section 8.1 were composed from tested helpers; where something was not run, the text says so.

Contents: 1 Topology | 2 Capture | 3 Flowmeter | 4 Classifier | 5 Filter | 6 User space | 7 A dataset through the kernel classifier | 8 Manual traffic collection | 9 Measured numbers | 10 Limitations and gotchas

---

## 1. Topology and where traffic is collected

`docker-compose.yml` (project name `lab4`) builds three networks. The IDS container is an inline gateway; XDP is attached to its `ext0` interface only.

```
 host browser ──(http://172.28.0.2:8080)──────────────┐
                                                      │ mgmt 172.28.0.0/24
                                         ┌────────────▼────────────────────────────────┐
                                         │ ids  (lab4-ids:latest, privileged, ip_forward=1)
                                         │  mgmt0 172.28.0.2   <- UI/agent HTTP only    │
 client 172.28.1.20 ──front 172.28.1.0/24─▶ ext0 172.28.1.2                              │
  (alpine, wget loop)                     │   XDP ingress (generic/skb mode): xdp_ids    │
                                         │        │ XDP_PASS                            │
                                         │        ▼  ip_forward                         │
                                         │  int0 172.28.2.2  (iptables MASQUERADE)      │
                                         └────────────┬────────────────────────────────┘
                                                      │ back 172.28.2.0/24
                          nginx 172.28.2.10 ◀─────────┼─────────▶ apache 172.28.2.11
                                                    pinger 172.28.2.30
```

- **Interface names.** The compose file sets `interface_name: mgmt0`, `ext0`, `int0` on the three networks of the `ids` service (needs Docker Engine 28.1 or newer; 29.9.3 here; confirmed working in the live run, CLAUDE.md 3.6).
- **Client.** `docker/client_traffic.sh` runs `ip route add 172.28.2.0/24 via 172.28.1.2` (the client has `NET_ADMIN`) and then loops forever: `wget -q -T 3 -O /dev/null http://172.28.2.10/` and `.../172.28.2.11/`, one log line per request (`<ISO time> <server> OK|FAIL`), then `sleep $CLIENT_INTERVAL_S` (default 1). Normal traffic only.
- **Gateway.** `docker/ids_entrypoint.sh` mounts bpffs on `/sys/fs/bpf` if missing and, when `int0` exists, adds `iptables -t nat -A POSTROUTING -o int0 -j MASQUERADE` (only once, checked with `-C`). The web servers therefore see the IDS (172.28.2.2) as the peer; their replies go back to the IDS and are forwarded to the client. Plain `docker run` (kernel tests) has no `int0`, so no NAT rule is added.
- **Why ingress only means the forward direction.** XDP runs on receive. A client request enters the IDS through `ext0` (seen). The server's reply enters through `int0` (no XDP there) and leaves through `ext0` (egress, XDP never runs). So the program only ever sees client-to-server packets: Total Fwd Packets, Fwd Packet Length, Fwd IAT, and nothing bidirectional (CLAUDE.md 4.2).
- **Why the UI is on mgmt0.** The browser's polling of the UI never crosses `ext0`, so it is neither captured nor droppable, and the client (on `front`) cannot reach the UI because it binds to the `mgmt` IP only (`webui.py --host 172.28.0.2 --port 8080`, the image's default CMD). `agent.validate_iface` refuses `mgmt0` and `/api/interfaces` hides it.
- **Blast radius.** The IDS owns its own network namespace. XDP can never reach the host uplink `enp0s3`; stopping the container removes the program, the pins and all blocks.

---

## 2. Capture: the XDP hook and `parse_pkt`

`bpftool net attach xdpgeneric pinned <pin>/progs/xdp_ids dev ext0` attaches `SEC("xdp") xdp_ids` in **generic (skb) mode**, the default on veth (`--xdp-mode skb`; `native` maps to `xdpdrv` and is not used in the acceptance runs). It runs on every received frame of `ext0` before the IP stack, routing and netfilter see it.

`parse_pkt(ctx, &p)` returns 0 for a tracked packet and -1 for anything else. Rules, in order (every pointer access is bounds-checked against `data_end`):

1. Ethernet header must fit and `h_proto == htons(ETH_P_IP)` (so ARP, IPv6, 802.1Q VLAN frames are not tracked).
2. IPv4 base header (20 B) must fit; `ihl >= 5`; the fragment field must be clear: `frag_off & htons(0x3FFF)` (MF flag or any fragment offset means not tracked).
3. `ihl_bytes = ihl * 4`; L4 starts at `ip + ihl_bytes`.
4. TCP: the 20 B header must fit (this also covers the flag octet at byte offset 13); `doff >= 5`; `l4len = doff * 4`; ports via `bpf_ntohs`; `tcp_flags` = the flag octet.
5. UDP: the 8 B header must fit; `l4len = 8`; ports via `bpf_ntohs`.
6. Any other IP protocol (ICMP, ...) is not tracked.
7. `payload = (s32)ntohs(tot_len) - ihl_bytes - l4len`; negative means inconsistent lengths, not tracked. **Payload is derived from the IP length, never from the frame length, so Ethernet padding is never counted.**

The flow key (`struct flow_key`, 16 B) is filled with `saddr`, `daddr` (network byte order, as in the header), `sport`, `dport` (host order), `proto` and 3 pad bytes (zeroed by `__builtin_memset`, which matters because the map hashes all 16 bytes).

**Not tracked** (ARP, IPv6, ICMP, fragments, VLAN, truncated or malformed headers, `ihl < 5`, `doff < 5`): `ST_NOT_TRACKED` and `ST_PASS` are incremented and the packet returns `XDP_PASS` untouched. These packets are also **not** subject to the blocklist (section 5).

---

## 3. The Flowmeter in the kernel

### 3.1 State

`flows` is a `BPF_MAP_TYPE_LRU_HASH` with `MAX_FLOWS = 65536` entries, key `struct flow_key`, value `struct flow_state` (derived size: 10 u64 + 1 s64 + 4 u32 = 104 B):

| Field | Meaning |
|---|---|
| `first_ns`, `last_ns` | `bpf_ktime_get_ns()` of the first and the latest packet (CLOCK_MONOTONIC, ns) |
| `pkts`, `bytes` | packet count, sum of L4 payload bytes |
| `len_max`, `len_min` | largest and smallest payload; `len_min` starts at `~0ULL` |
| `iat_max_ns`, `iat_min_ns` | largest and smallest gap between consecutive packets |
| `act_data_pkts` | packets with payload > 0 |
| `classified_ns` | time of the latest classification; 0 means never classified |
| `xgb_margin` | latest XGB margin (fixed point, 2^16) |
| `dt_verdict`, `xgb_verdict`, `verdict` | latest per-model and final verdicts; initial value `V_NONE = 255` |
| `tcp_flags` | OR of the TCP flag octets seen |

A new flow is created with `bpf_map_update_elem(&flows, &key, &init, BPF_NOEXIST)` followed by a fresh lookup (if the LRU raced the entry away, the packet is counted as not tracked and passes: fail open).

### 3.2 Update rules (`flow_update`, in this order)

- If `pkts == 1` (this is the 2nd packet): `iat = now - last_ns` sets **both** `iat_max_ns` and `iat_min_ns`.
- If `pkts > 1`: update `iat_max_ns` (larger) and `iat_min_ns` (smaller) with `iat = now - last_ns`.
- `pkts++`; `bytes += payload`; `len_max`, `len_min` updated; `act_data_pkts++` if `payload > 0`; `last_ns = now`; `tcp_flags |= p->tcp_flags`.

The first packet of a 5-tuple (as seen on ingress) defines the forward direction.

### 3.3 The 10 features (`build_features`; order is the contract with `common.KERNEL_FEATURES`)

| Idx | CIC column | Kernel formula | Scale s (kernel unit per CIC unit) |
|---:|---|---|---:|
| 0 | `Total Fwd Packets` | `pkts` | 1 |
| 1 | `Total Length of Fwd Packets` | `bytes` | 1 |
| 2 | `Fwd Packet Length Max` | `len_max` | 1 |
| 3 | `Fwd Packet Length Min` | `len_min` | 1 |
| 4 | `Fwd Packet Length Mean` | `bytes * 1000 / pkts` | 1000 (milli-bytes) |
| 5 | `Fwd IAT Total` | `span = last_ns - first_ns` | 1000 (CIC us -> ns) |
| 6 | `Fwd IAT Mean` | `span / (pkts - 1)`, 0 if `pkts == 1` | 1000 |
| 7 | `Fwd IAT Max` | `iat_max_ns`, 0 if `pkts == 1` | 1000 |
| 8 | `Fwd IAT Min` | `iat_min_ns`, 0 if `pkts == 1` | 1000 |
| 9 | `act_data_pkt_fwd` | `act_data_pkts` | 1 |

All divisions are unsigned 64-bit integer divisions (floor). CIC IAT columns are in microseconds, the kernel measures nanoseconds, hence s = 1000. Dataset rows are converted the same way: `x_int = floor(x * s)` in float64 (`export_model.to_int_features`).

Worked example (the flow of `test_flowmeter_tcp_fin`: SYN 0 B, PSH/ACK 100 B, ACK 50 B, FIN/ACK 0 B): `pkts = 4`, `bytes = 150`, `len_max = 100`, `len_min = 0`, `act_data_pkts = 2`, so `x = [4, 150, 100, 0, 37500, span, span/3, iat_max, iat_min, 2]` with the IAT entries in ns.

### 3.4 Differences from CICFlowMeter (why the model uses only these features)

| Aspect | Kernel Flowmeter | CICFlowMeter (training data) |
|---|---|---|
| Direction | forward only (ingress of `ext0`) | forward and backward |
| Bwd and bidirectional features (Flow Duration, Flow Bytes/s, Flow Packets/s, Fwd Packets/s, all Bwd) | not available, so not used | present |
| Flow timeout | none; an entry lives until LRU eviction | flow timeout and FIN termination end a flow |
| Port reuse | a new connection with the same 5-tuple **continues** the old entry | a flow ends at FIN/timeout, the next one starts fresh |
| Completed flows | classifies at flow end (FIN/RST) or at 8, 16, 32 ... packets | one row per completed flow |
| Std features, header-length features | left out (integer sqrt, known CIC quirks) | present |
| Destination Port, Init_Win_bytes_forward | excluded on purpose (shortcut features; port 80 is the demo servers' port) | present |

---

## 4. The classifier (inside `xdp_ids`)

### 4.1 When it runs

After the flow update, the packet is classified only if `config` exists, `mode != MODE_OFF`, and either

- the **current** packet has FIN or RST set (`p.tcp_flags & (TCP_FIN | TCP_RST)`, `0x01` / `0x04`; the cumulative `st->tcp_flags` is not used for the trigger), or
- `st->pkts >= CLASSIFY_MIN_PKTS (8)` and `(pkts & (pkts - 1)) == 0` (a power of two: 8, 16, 32, ...).

Otherwise the packet counts as `ST_PASS` and returns `XDP_PASS`. A flow with fewer than 8 packets and no FIN/RST is never classified (e.g. short UDP). A flow can be classified several times; each time `verdict`, `dt_verdict`, `xgb_verdict`, `xgb_margin` and `classified_ns` are overwritten.

### 4.2 Integer tree walk

Trees live in the `nodes` ARRAY map (`MAX_NODES = 8192`, 24 B `struct tree_node { s64 threshold; s32 feature; u32 left; u32 right; s32 leaf; }`; `feature < 0` marks a leaf). `roots` (ARRAY, `MAX_TREES + 1 = 65` u32) holds `roots[0]` = DT root and `roots[1..n]` = the XGB tree roots.

`walk_tree(root, x)`: at most `MAX_TREE_DEPTH + 1 = 11` steps (a constant bound so the verifier can prove termination); at each node: lookup failure returns 0; `feature < 0` returns `leaf`; `feature >= N_FEATURES` returns 0; otherwise `idx = (x[feature] <= threshold) ? left : right`. An exhausted bound returns 0, so errors fail open.

**Threshold conversion** (`export_model.py`; the kernel and the Python twin `kmodel.walk` both use "left iff x_int <= T", signed 64-bit):

- sklearn DT goes left if `x <= t`, so `T = floor(t * s)`. A DT leaf is class 1 if `P(DDoS) > 0.5`, else 0.
- XGBoost goes left if `x < t` (float32 `t`), so `T = ceil(t * s) - 1`. A leaf is `round(leaf * 2^16)` (`LEAF_SHIFT = 16`).
- Base margin: `round(logit(base_score) * 2^16)`; `base_score` is read from `booster.save_config()` (it can be a string like `"[5.6E-1]"`).

### 4.3 Verdicts and modes

- DT verdict: `walk_tree(roots[0]) > 0` is Malicious (`V_MALICIOUS = 1`), else Normal (0).
- XGB margin: `config.xgb_base_margin + sum of walk_tree(roots[i+1])` over `n_xgb_trees` trees (capped at `MAX_TREES`), summed with **`bpf_loop(n, xgb_cb, &ctx, 0)`** (callback `xgb_cb` adds one tree per iteration). Verdict is `margin > 0`; an exact 0 is Normal.
- `mode` is a bit mask: `MODE_DT = 1`, `MODE_XGB = 2`, `MODE_ALL = 3` (`mode & MODE_DT` runs DT, `mode & MODE_XGB` runs XGB). The model not run reports `V_NONE` (255), which the UI shows as `n/a`.
- Final verdict: DT mode returns the DT verdict, XGB mode the XGB verdict, **ALL is Malicious only if DT and XGB both say Malicious** (AND, design decision O6).
- **Fail-open:** missing config or map entries, a bad feature index, an exhausted walk bound, an LRU race: all return `XDP_PASS` or leaf 0 (Normal).

The model comes from `models/kernel_model.json` (format 1: 10 feature names, `scales`, `nodes` as `[feature, threshold, left, right, leaf]` with absolute indices, `dt_root`, `xgb_roots`, `xgb_base_margin`, `meta`). The selected depths are DT 6 and XGB 4 (20 trees), 387 nodes in total (CLAUDE.md 3.4). `kmodel.validate` rejects more than `MAX_NODES` nodes, more than `MAX_TREES + 1` roots, depth above `MAX_TREE_DEPTH`, bad feature or child indices, before anything is written to the kernel.

---

## 5. The filter

- **Blocklist:** `blocklist` is an LRU_HASH (`MAX_BLOCKED = 65536`), key = source IPv4 (`u32`, network-order bytes), value = `u64 expiry_ns`.
- **Check order in `xdp_ids`:** parse -> `ST_PKTS++` -> `now` -> **blocklist lookup** -> flow update -> classify. If the source is blocked and `expiry > now`: `ST_DROP++` and `XDP_DROP` immediately, with no flow update. If the entry has expired it is deleted on this packet and processing continues normally.
- **On a Malicious verdict:** `blocklist[saddr] = now + config.block_ns` (`BPF_ANY`), `ST_BLOCKS_ADDED++`, `ST_FLOWS_MALICIOUS++`, `ST_DROP++`, and **the classifying packet itself is dropped**. The block key is the source **address**, not the flow: all later TCP/UDP packets from that IP are dropped until expiry.
- **Block time:** `--block-seconds` (default 60, range 1..3600), stored as `block_ns` in `config`.
- **Counters** (`stats` PERCPU_ARRAY of `N_STATS = 7` u64; user space sums the CPUs): `ST_PKTS` (tracked packets), `ST_PASS`, `ST_DROP`, `ST_FLOWS_CLASSIFIED`, `ST_FLOWS_MALICIOUS`, `ST_BLOCKS_ADDED`, `ST_NOT_TRACKED`. Every packet of a tracked flow ends in exactly one of `ST_PASS` or `ST_DROP`; not-tracked packets add to `ST_NOT_TRACKED` and `ST_PASS` but not to `ST_PKTS`.
- **Not covered by the filter:** not-tracked packets (ICMP, ARP, IPv6, fragments, VLAN, malformed) are never dropped, even from a blocked source, because the blocklist lookup happens after `parse_pkt`.

---

## 6. User space (`agent.py`, `bpf_ctl.py`, `kmodel.py`, `flowview.py`, `webui.py`)

User space never classifies or filters. It uses **bpftool only** (every call is an argument list, no shell).

### 6.1 `Session.start()` order (`agent.py`)

1. `_acquire`: non-blocking `fcntl.flock(LOCK_EX | LOCK_NB)` on `/run/lab4-<iface>.lock` (mode 0600). A second capture on the same interface fails with "capture already running on <iface>"; the kernel drops the lock when the process dies.
2. `kmodel.load(model_file)` (also validates).
3. `bpf_ctl.unpin(pin)`: remove stale pins (`pin = /sys/fs/bpf/lab4/<iface>`; refuses any path outside `/sys/fs/bpf/`).
4. `bpf_ctl.load`: `bpftool prog loadall <obj> <pin>/progs type xdp pinmaps <pin>/maps`.
5. `bpf_ctl.batch(kmodel.batch_lines(...))`: one `bpftool batch file` with a line per node and per root, e.g. `map update pinned <pin>/maps/nodes key hex <u32 LE> value hex <24 B>`. Node bytes are `struct.pack("<qiIIi", threshold, feature, left, right, leaf)`; roots are `"<I"`.
6. `bpf_ctl.batch([config_line(...)])`: `config[0]` = `struct.pack("<IIqQ", mode, n_xgb_trees, xgb_base_margin, block_ns)` with `block_ns = block_s * 10**9`.
7. `bpf_ctl.detach(iface)` (`bpftool net detach xdpgeneric dev <iface>`, errors ignored): removes any stale program.
8. `bpf_ctl.attach(iface, pin, mode)`: **attach is always last**, so the program never runs with an empty model (and an all-zero config means Flowmeter only, no classification, no drops).

If any step raises, `stop()` runs. `stop()` order: detach, unpin, close the lock fd. `__exit__` and SIGINT/SIGTERM (a `threading.Event`) always reach it.

### 6.2 Poll loop

`agent._capture` loops until `--timespan` (default 30 s, 1..3600) or a signal: `session.poll()` then `stop.wait(POLL_INTERVAL_S = 1.0)`. `poll()` runs `bpftool -j map dump pinned <pin>/maps/flows` and `.../stats`. The dumps are BTF-decoded: every element has a `formatted` dict (`key`, `value`; per-CPU maps give `values[{cpu, value}]`). The whole `flows` map is dumped every second.

- `saddr`/`daddr` come out as a little-endian read of the network-order bytes (33554442 = 10.0.0.2), so `flowview._ip` uses `value.to_bytes(4, "little")` and `socket.inet_ntoa`.
- Only flows with `classified_ns != 0` become rows.
- **Time conversion:** `wall = time.time() - (time.monotonic_ns() - classified_ns) / 1e9` (same CLOCK_MONOTONIC as `bpf_ktime_get_ns()` inside one container), formatted with `"%d-%m-%Y %I:%M:%S %p"` in the container's local time (the Dockerfile sets no timezone).
- `FlowRow(src_ip, src_port, dst_ip, dst_port, proto, timestamp, result, models, pkts)`; `result` is `Normal` or `Malicious`; `models` looks like `DT: Normal · XGB: Normal`.

### 6.3 Outputs

- stdout: one JSON line per **new or changed** flow (change = a different `(result, models)` pair; `pkts` changes are not reported).
- `outputs/realtime/<YYYYmmdd-HHMMSS>_<iface>_<model>.jsonl`: the same lines.
- `..._replay.json` (only with `--replay N`): the ground truth of the replayed flows (`src_ip`, `sport`, `label`, `retvals`; section 7.4).
- `..._summary.json`: `iface`, `model`, `timespan_s`, `started`, `ended`, `stats` (the 7 counters), `flows_classified`, `flows_malicious`. `run.log` in the same folder. Files are `chown`ed to `LAB4_UID`/`LAB4_GID` when set (the container writes as root).
- Exit code 0 on success, 1 if the capture could not start or failed.

### 6.4 UI API (`webui.py`, stdlib `ThreadingHTTPServer`, one capture at a time)

`GET /` (`web/index.html`), `GET /api/interfaces` -> `{"interfaces": [...], "default": "ext0"}` (mgmt0 excluded), `POST /api/start` `{iface, timespan, model, replay}` (`replay` 0..100, default 20) -> 202 / 400 / 409, `GET /api/flows` -> `{running, remaining_s, iface, model, stats, rows, replay}` (`replay` = ground truth of the replayed flows) (newest first, at most 500 rows), `POST /api/stop` -> 200. Inputs are validated at the trust boundary: interface exists and is not `mgmt0`, timespan an int in 1..3600, model in DT/XGB/ALL, body at most 4096 B. A second start fails with 409 (in-process or via the flock).

CLI (inside the container):
```bash
docker compose exec ids python3 script/agent.py --iface ext0 --model ALL --timespan 30
# options: --model DT|XGB|ALL  --block-seconds 60  --model-file models/kernel_model.json
#          --xdp-mode skb|native  --out outputs/realtime  --replay 0..100 (default 0)
```

---

## 7. Running a dataset through the kernel classifier

The dataset path exercises the **classifier code** of the kernel program (`classify()` with the same `walk_tree` and `bpf_loop`), not the packet parser or the Flowmeter: CSV rows already are flow features. Packets exercise the full `xdp_ids` (section 7.3).

```
 Friday CSV (CIC rows, 79 columns)
   │ script/preprocess.py   strip names, inf->NaN, drop NaN rows, drop duplicate rows,
   │                        drop constant + identical columns, BENIGN=0/DDoS=1, 70/15/15 split (seed 42)
   ▼
 10 kernel features (CIC units, float64, unscaled)         [select_kernel_features, order of 3.3]
   │ export_model.to_int_features   x_int = floor(x * s)  (s = 1,1,1,1,1000,1000,1000,1000,1000,1)
   ▼
 models/kernel_model.json  <- DT: T=floor(t*s), XGB: T=ceil(t*s)-1, leaf*2^16, base margin
 models/test_vectors.json  {"x": 1024 x 10 ints, "dt": [...], "xgb_margin": [...]}   (Python-evaluated)
   │ docker run --privileged ... pytest tests/test_kernel.py -m kernel
   ▼
 test_vecs[i] <- x ; config <- MODE_ALL ; nodes/roots <- model        (bpftool batch)
 bpftool prog run pinned .../classify_test data_in <dummy 64 B> repeat 1024   (BPF_PROG_TEST_RUN)
   │ classify_test: i = test_idx; classify(MODE_ALL, test_vecs[i]) -> test_results[i]; test_idx++
   ▼
 bpftool -j map dump test_results  ->  assert dt_verdict == vecs["dt"] and xgb_margin == vecs["xgb_margin"]
```

### 7.1 Commands

Host, once (no root): train, export, parity on the host:
```bash
cd /home/aayush/Desktop/SecInsiderLab1/SecInsiderLab-1/Lab4
.venv/bin/python script/train.py     # writes models/kernel_model.json and models/test_vectors.json,
                                     # outputs/metrics/* (parity.json, parity_mismatches.csv, ...)
make -C xdp                          # optional: builds xdp/lab4_xdp.bpf.o on the host (no root)
```

`train.py` takes 512 BENIGN + 512 DDoS rows of the test split (`N_VECTORS_PER_CLASS = N_TEST_VECS // 2`, seed 42), converts them with `to_int_features` and evaluates them with the Python integer model (`kmodel.dt_verdict`, `kmodel.xgb_margin`). Before that it checks the float models against the integer model on every test row (`export_model.parity`).

Kernel tests (root needed, so inside a privileged container; no host sudo):
```bash
docker compose build ids
docker run --rm --privileged -v "$PWD/models:/lab4/models:ro" lab4-ids:latest \
    python3 -m pytest tests/test_kernel.py -m kernel -q
# keep the evidence files (timing.json, prog_sizes.json, dumps) on the host as well:
#   add  -v "$PWD/outputs:/lab4/outputs"   (files are then root-owned)
```

Use `docker run`, not `docker compose run` (the fixed IPs collide with a running stack), and run only `tests/test_kernel.py` (the image cannot import the host-only test modules).

### 7.2 What `test_kernel_parity` does exactly

1. `bpf_ctl.load(BPF_OBJ, pin)` into a fresh `/sys/fs/bpf/lab4_test_<random>` (the `pin` fixture; unpinned afterwards).
2. One bpftool batch: nodes + roots, `config` with `MODE_ALL` and `block_ns = 0`, plus one `map update ... test_vecs key hex <u32> value hex <10 x s64>` per vector (`struct.pack("<10q", ...)`).
3. `bpf_ctl.prog_run("classify_test", pin, bytes(64), count)` = `bpftool -j prog run pinned <pin>/progs/classify_test data_in <file> repeat <count>` (BPF_PROG_TEST_RUN). Each run takes the next vector because the program increments `test_idx`; `count` is 1024.
4. Dump `test_results` and require, for all vectors, `dt_verdict` equal to `vecs["dt"]` and `xgb_margin` equal to `vecs["xgb_margin"]` **exactly** (integers, no tolerance).

Together with the offline check on all 33,463 test rows, this chain gives: float model ~ Python integer model == kernel C. Float-vs-integer agreement: 100 % for both models on 33,463 rows, max margin error 4.5e-5 (CLAUDE.md 3.4).

### 7.3 Crafted packets through `xdp_ids` (no dataset)

The other kernel tests send frames built by `script/pktbuild.py` (stdlib; checksums stay 0 because XDP ignores them) with `bpf_ctl.prog_run("xdp_ids", pin, frame, repeat)` and read the maps afterwards:

- `pktbuild.tcp(src, dst, sport, dport, flags, payload=0, ihl=5, doff=5, frag=0)`, `udp(...)`, `icmp`, `arp`, `ipv6`, `vlan(inner_ip)`, `truncated(frame, size)`; flags `SYN 0x02`, `FIN 0x01`, `PSH 0x08`, `ACK 0x10`, `RST 0x04`, `MF 0x2000`.
- Covered: flowmeter counters of a SYN/PSH/ACK/FIN flow, trigger at the 8th UDP packet and not before (7 packets leave `classified_ns == 0`), Malicious -> drop of the classifying packet + block of that source only (second source passes), block expiry, ALL needing both models (a `SPLIT` model with DT Malicious and XGB negative passes), mode off, and the not-tracked set (`arp`, `ipv6`, `icmp`, `fragment`, `short`, `ihl4`, `doff4`, `vlan`: pass, no flow created, `ST_NOT_TRACKED == 1`).
- The Malicious path is proven **without attack tools** by `tests/fixtures/always_malicious.json` (DT = one leaf with value 1; XGB = one tree, leaf `+2**16`, base margin 0), on normal traffic.

### 7.4 Dataset replay into the live program (`--replay N`, UI "Replay dataset flows")

So that the UI shows a mix of Normal and Malicious rows without any attack tool, flows from the **CIC-IDS2017 test split** are rebuilt as packets and sent through the real, pinned `xdp_ids` with `BPF_PROG_TEST_RUN` (`bpftool prog run`). The real flowmeter, model and blocklist produce the verdicts; nothing goes on the wire.

- **Pool:** `train.py` writes `models/replay_flows.json`: up to 500 BENIGN and 500 DDoS test-split rows (a seeded shuffle) whose forward packets can be rebuilt **exactly**: at most 32 packets, payloads of at most 1460 B, and a payload list that reproduces Total Fwd Packets, Total Length, Max, Min, Mean (x1000, floor) and act_data_pkt_fwd (`replay.payloads_from_row`; other rows are skipped). Entries are `{label, payloads}`.
- **Sampling:** at capture start, N/2 flows of each class are drawn at random (no fixed seed) and shuffled (`replay.sample`). The UI default is 20; the CLI default is 0.
- **Timing:** each sampled flow gets a random due time, uniform in [0, 0.8 x timespan) (`replay.Schedule`), and is injected on the first poll tick after it is due, so replayed rows interleave randomly with live rows instead of all appearing at start. The ground truth grows as flows are injected (UI `replay` key) and `<stamp>_replay.json` is written when the capture ends.
- **Packets:** each flow gets its own random source in 10.99.0.0/16 and a random source port, destination 172.28.2.10:80. All packets are TCP ACK (PSH|ACK when they carry payload); the last one carries FIN|ACK, which triggers the classification.
- **Ground truth:** `outputs/realtime/<stamp>_<iface>_<model>_replay.json` (CLI) and the `replay` key of `GET /api/flows` (UI) list `src_ip`, `sport`, dataset `label` and the XDP action of every packet. Join them with the table on (src_ip, src_port) to compare verdict and label.
- **Blocks** hit only 10.99.x.y sources, never the client or the servers.
- **Limits:** inter-arrival times are **not** reproduced (the packets are microseconds apart), so the four IAT features differ from the dataset; they carry under 0.5 % of the model importance (CLAUDE.md 3.4). A flow with more than 8 packets is also classified at its 8th packet (section 4.1). No attack tool is used.

Kernel test evidence: `test_replay_through_xdp_ids` (4 flows) and `test_replay_evidence` (100 flows, `outputs/kernel/replay_summary.json`).

---

## 8. Optional manual traffic collection for inspection

Only tools that exist on this machine are used (CLAUDE.md 3.1: tcpdump, tshark, nstat, nc, ping, ethtool; hping3, tcpreplay, iperf3, ncat, scapy are absent and not needed). **Per the slide 8 note, no attack tools are used: the interface carries normal traffic only, and classifier performance against malicious live traffic is not checked.**

**Replaying pcaps through `xdp_ids` is NOT implemented** (dataset flows are replayed instead, section 7.4). There is no pcap reader, no `tcpreplay`, and no code path that feeds a capture file into the program. A pcap could only be turned into packets by a tool that does not exist in this repo; the supported ways to drive `xdp_ids` with chosen packets are `pktbuild.py` + `BPF_PROG_TEST_RUN` (section 7.3) and the live client.

### 8.1 Drive `xdp_ids` by hand with the real model (composed from tested helpers; not run separately)

Save as e.g. `manual.py` and run it in the IDS image (the same helpers `test_kernel.py` uses):
```bash
docker run --rm --privileged -v "$PWD/models:/lab4/models:ro" \
    -v "$PWD/manual.py:/manual.py:ro" lab4-ids:latest python3 /manual.py
```
```python
import sys
sys.path[:0] = ["/lab4/script", "/lab4/tests"]
import bpf_ctl, kmodel, pktbuild
from common import BPF_OBJ, KERNEL_MODEL_PATH, MODE_ALL

pin = "/sys/fs/bpf/lab4_manual"
bpf_ctl.load(BPF_OBJ, pin)
m = kmodel.load(KERNEL_MODEL_PATH)
bpf_ctl.batch(kmodel.batch_lines(m, pin) + [kmodel.config_line(MODE_ALL, m, 60 * 10**9, pin)])
steps = [(pktbuild.SYN, 0), (pktbuild.PSH | pktbuild.ACK, 100), (pktbuild.ACK, 50), (pktbuild.FIN | pktbuild.ACK, 0)]
for flags, n in steps:  # XDP_PASS = 2, XDP_DROP = 1
    print("action", bpf_ctl.prog_run("xdp_ids", pin, pktbuild.tcp("10.0.0.2", "10.0.0.1", 40000, 80, flags, n))[0])
print(bpf_ctl.dump("flows", pin)[0]["formatted"]["value"])   # features' raw state + verdicts
print({e["formatted"]["key"]: sum(v["value"] for v in e["formatted"]["values"]) for e in bpf_ctl.dump("stats", pin)})
bpf_ctl.unpin(pin)
```

### 8.2 Look at the live cycle

```bash
docker compose up -d                                   # nginx, apache, pinger, client, ids
docker compose logs -f client                          # one OK/FAIL line per request
docker compose exec ids python3 script/agent.py --iface ext0 --model ALL --timespan 60
# in a second shell, while the agent runs (the pins exist only during a session):
docker compose exec ids bpftool net show               # xdpgeneric on ext0
docker compose exec ids bpftool map dump pinned /sys/fs/bpf/lab4/ext0/maps/stats
docker compose exec ids bpftool map dump pinned /sys/fs/bpf/lab4/ext0/maps/flows
docker compose down
```

### 8.3 Packet capture of the same traffic

- The IDS image has **no tcpdump** (it installs only `bpftool iproute2 iptables`). From the host, run tcpdump inside the container's network namespace (needs root, so the user runs it):
  ```bash
  sudo nsenter --target "$(docker inspect -f '{{.State.Pid}}' "$(docker compose ps -q ids)")" --net \
      tcpdump -ni ext0 -w /tmp/ext0.pcap
  ```
  Expect to see only packets the XDP program did **not** drop: generic XDP runs before the packet taps, so tcpdump never shows XDP_DROP'ed frames (a documented behaviour of generic XDP, not measured in this lab).
- **xdpdump (Task 1):** the verified use is in the Task 1 sandbox on the host (netns `lab4t1`, veth `t1-host` / `t1-ns`, 10.10.0.0/24; see `xdp_tools/README.md`): `xdpdump -D`, `xdpdump --rx-capture=entry,exit` (exit records show `XDP_DROP`), `xdpdump -x`, `xdpdump -w - | tcpdump -r - -n`. Attaching xdpdump to the `xdp_ids` program that bpftool loaded inside the IDS namespace was **not tried**, so no claim is made about it.

---

## 9. Measured numbers (CLAUDE.md 3.4 to 3.6 only)

**Models** (test split, 33,463 rows): DT depth 6: F1 0.9991 (FP 4, FN 32); XGB 20 trees depth 4: F1 0.9989 (FP 11, FN 31). Depth selection on validation F1 with tolerance 0.0005. Integer models give identical confusion matrices; parity 100 % on 33,463 rows, max margin error 4.5e-5. Fwd Packet Length Max and Total Length of Fwd Packets carry about 99 % of the importance, so the kernel model is essentially a payload-size rule.

**Program** (verifier-accepted, `xdp_ids` and `classify_test`): 5,664 B xlated, 3,263 B JIT.

**Time per packet** (`BPF_PROG_TEST_RUN`, 100,000 repeats, average ns; program time only, not driver or skb cost):

| Packet | DT | XGB | ALL |
|---|---:|---:|---:|
| not tracked | 11 | 11 | 11 |
| mid-flow | 84 | 69 | 65 |
| classifying (FIN) | 92 | 377 | 384 |

**Kernel tests:** 16/16 pass, including exact parity on 1,024 test vectors. **Docker tests:** 6/6 pass. `task4_check.sh`: all PASS (ping by name and IP, HTTP to nginx and apache).

**Live runs** (normal traffic, 60 s per model on `ext0`): DT, XGB and ALL each classified 118 flows (5 to 7 packets each, at FIN); 0 Malicious, 0 drops; client 138 / 138 / 140 OK, 0 FAIL. **Filter demo** (`always_malicious.json`, DT, block 20 s, 30 s run): 55 drops, 2 blocks (re-blocked after the 20 s expiry); the client timed out during each block and recovered in between. **UI API:** a 20 s ALL capture gave 41 classifications, all Normal. No XDP program was left on `ext0` after the runs.

---

## 10. Limitations and gotchas

- **Ingress only:** no Bwd or bidirectional features; the model cannot use them.
- **Partial flows:** fewer than 8 packets and no FIN/RST means never classified.
- **Port reuse:** a repeated 5-tuple continues the old entry (counters, IATs and `pkts` keep growing); there is no flow timeout.
- **Per-source blocking:** one Malicious flow blocks every TCP/UDP packet from that IP (a NAT'd network behind one address is blocked together). Not-tracked protocols still pass.
- **Re-classification:** `verdict` is overwritten at each trigger; the UI shows the latest.
- **Counters are not atomic across CPUs** (the flow state is updated without locks); small races are accepted at demo rates. `stats` is per-CPU and exact once summed.
- **Dumping cost:** the agent dumps the whole `flows` map once per second; the maps hold up to 65,536 flows and 65,536 blocked sources (LRU eviction, no expiry sweep).
- **float32:** sklearn and XGBoost compare float32 inputs; IAT values above 2^24 us could flip a split in rare cases (the parity step measures this).
- **Domain shift:** the models learned the 2017 testbed. The live demo (Docker-local HTTP, sub-millisecond IATs, tiny busybox GETs) produced no Malicious verdicts; if normal flows ever do, the client gets blocked: stop and report, do not tune thresholds ad hoc.
- **Generic XDP** is slower than native and runs after skb allocation; `--xdp-mode native` exists but is not used or verified here.
- **One capture per interface:** the flock refuses a second one (CLI or UI).
- **Pins and stale programs:** a start detaches and unpins whatever is on the interface first. Pins exist only while a session runs.
- **Root-owned output files:** the privileged container writes as root; `run.sh` passes `LAB4_UID`/`LAB4_GID` for the `chown`.
- **Timing caveat:** repeated `prog run` of one frame accumulates flow state (the "mid-flow" frame reaches 8, 16, ... packets and is classified at those powers of two only rarely; the FIN frame classifies on every run, with `block_ns = 0` so a Malicious verdict never blocks the loop).
- **No pcap replay, no attack tools** (section 8).
