# Lab 4: DDoS defense with eBPF/XDP (in-kernel detection and filtering)

Group G8. One XDP program (`xdp/lab4_xdp.bpf.c`) captures packets, computes flow features, classifies each flow with a Decision Tree and/or XGBoost (trees stored in BPF maps) and drops the source of a Malicious flow. User space only trains offline, loads the model, configures the program and displays results. Spec: `Lab-4.pptx`. Design details and decisions: `CLAUDE.md`.

## Architecture

```
client (172.28.1.20) --front--> ext0 [IDS container: XDP program xdp_ids]
                                  1 capture   : XDP hook, ingress of ext0 (before the kernel stack)
                                  2 blocklist : source IPv4 blocked? -> XDP_DROP
                                  3 flowmeter : LRU map "flows" (5-tuple -> counters, sizes, IATs)
                                  4 classify  : DT / XGB tree walk over maps "nodes"/"roots" (integer)
                                  5 filter    : Malicious -> blocklist[src] = now + block_ns; XDP_DROP
                               PASS -> ip_forward -> int0 (MASQUERADE) --back--> nginx 172.28.2.10 / apache 172.28.2.11
user space (same container): agent.py / webui.py -> bpftool: load, map batch, attach, dump every 1 s
browser on the host -> http://172.28.0.2:8080 (mgmt0 only)
```

## Prerequisites

- Linux with Docker (Engine 28.1 or newer, for `interface_name` in compose) and the Compose plugin; your user in the `docker` group.
- [uv](https://docs.astral.sh/uv/) (installs CPython 3.12), git-lfs, make, clang, libbpf-dev (for the host `make -C xdp`).
- Task 1 only: xdp-tools installed on the host (see Task 1 below). Nothing else is needed on the host: the BPF build and runtime for Tasks 2-4 live in the IDS image.
- The dataset `Friday-WorkingHours-Afternoon-DDos.csv` is stored with git-lfs: run `git lfs pull` after cloning.

## Reproduce everything

```bash
cd Lab4
bash run.sh --quick    # fixture CSV into outputs_quick/ and models_quick/ (kernel/docker steps still run)
bash run.sh            # full CSV into outputs/ and models/
```

`run.sh` checks the CSV, creates the venv, trains, runs the unit tests, builds the BPF object and the IDS image, runs the kernel tests in the image, starts the compose stack, runs the Task 4 check and a 10 s agent run, then prints the UI URL and the Task 1 sudo command. It exports `LAB4_UID`/`LAB4_GID` so files written by the privileged container belong to you. The stack stays up; stop it with `docker compose down`.

## Task 1: xdp-tools (xdp-filter, xdpdump)

Install from source (once, needs sudo; do not also apt-install xdp-tools):

```bash
cd ~/src/xdp-tools && make && sudo make install && sudo ldconfig
```

Run the example commands in a netns/veth sandbox (never touches a real interface):

```bash
sudo bash xdp_tools/task1_demo.sh 2>&1 | tee xdp_tools/logs/task1_demo.log
```

Details and the screenshot list: `xdp_tools/README.md`.

## Task 2: real-time cycle (capture, flowmeter, classifier, filter)

Offline training and export (also run by `run.sh`):

```bash
.venv/bin/python script/train.py     # clean, split, depth selection, train DT + XGB, export, parity
make -C xdp                          # compile the BPF object (no root)
```

Live CLI, inside the IDS container (the stack must be up):

```bash
docker compose up -d
docker compose exec ids python3 script/agent.py --iface ext0 --model ALL --timespan 30
```

Flags: `--iface` (default `ext0`), `--model {DT,XGB,ALL}` (default ALL), `--timespan` seconds, `--block-seconds` (default 60), `--model-file`, `--xdp-mode {skb,native}` (default skb), `--out`. Output: one JSON line per classified flow and `outputs/realtime/<time>_<iface>_<model>.jsonl` plus `_summary.json`.

ALL runs both models in the kernel; a flow is Malicious only if DT and XGB agree. A Malicious source is blocked for `--block-seconds`. Only IPv4 TCP/UDP is classified; everything else passes. XDP sees ingress only, so only forward-direction features are used.

Results (test split, 33,463 flows; `outputs/metrics/`):

| Model | Acc | Prec | Rec | F1 | ROC-AUC | FP | FN |
|---|---|---|---|---|---|---:|---:|
| Decision Tree (depth 6) | 0.9989 | 0.9998 | 0.9983 | 0.9991 | 0.9999 | 4 | 32 |
| XGBoost (20 trees, depth 4) | 0.9987 | 0.9994 | 0.9984 | 0.9989 | 0.9998 | 11 | 31 |

The kernel C code matches the integer model exactly on 1,024 test vectors; the integer model matches the float model on all 33,463 test rows (100 %). Kernel cost, average ns per packet (`outputs/kernel/timing.json`): untracked packet 11; mid-flow 84 (DT), 69 (XGB), 65 (ALL); classifying packet 92 (DT), 377 (XGB), 384 (ALL). `xdp_ids` is 5,664 B translated, 3,263 B JIT.

Live normal traffic, 60 s per model: DT, XGB and ALL each classified 118 flows, 0 Malicious, 0 drops. Filter demo with an always-Malicious stub model (no attack tools): 55 drops, 2 blocks in 30 s.

## Task 3: front end

The UI starts with the stack (the IDS container's default command). Open it from the host:

```bash
xdg-open http://172.28.0.2:8080
```

Controls: Available Local Interfaces, Enter Timespan, Model (DT/XGB/ALL), Start Packet Capture, and the Algorithm Output table (Src IP, Src Port, Dst IP, Dst Port, Timestamp, Result). The UI listens only on `mgmt0`.

## Task 4: containers (Nginx, Apache, ping)

```bash
docker compose up -d
bash docker/task4_check.sh     # ping nginx/apache by name and IP, HTTP GET to both; log in outputs/task4/
docker compose down
```

Services: nginx (172.28.2.10), apache (172.28.2.11), pinger (172.28.2.30), client (172.28.1.20, steady normal traffic), ids (gateway, 172.28.1.2 / 172.28.2.2 / mgmt 172.28.0.2). All checks pass.

## Tests

```bash
.venv/bin/pytest -m "not e2e and not kernel and not docker" -q   # unit tests, no root
.venv/bin/pytest -m e2e -q                                        # full CSV
docker run --rm --privileged -v "$PWD/models:/lab4/models:ro" lab4-ids:latest \
    python3 -m pytest tests/test_kernel.py -m kernel -q            # kernel tests
.venv/bin/pytest -m docker -q                                     # needs the stack up
```

## Security note

The IDS container runs `privileged` (it loads BPF programs, mounts bpffs, changes sysctls) and Docker access via the `docker` group is root-equivalent on the host. Use this on a lab VM only. Task 1 never attaches to a real interface.

## Troubleshooting

- `git lfs pull` if `run.sh` reports a git-lfs pointer.
- `ip -br addr` in the ids container shows `eth0/eth1/eth2` instead of `mgmt0/ext0/int0`: Docker Engine is older than 28.1.
- Subnets 172.28.0-2.0/24 collide with an existing network: check `docker network ls` and `docker network rm` the stale one.
- Output files owned by root: run through `run.sh` (exports `LAB4_UID`/`LAB4_GID`) or `chown` them.
- Partial flows (fewer than 8 packets and no FIN/RST) are never classified: a documented limitation.
- Do not attach xdp-filter to your real interface (`enp0s3`): it can lock you out of remote access.
