# Lab 4: commands to run everything end to end

Run from a clean state: no Docker images of this lab, nothing running. All paths are relative to `Lab4/`. Commands marked **[SUDO]** need root; everything else runs as your normal user (in the `docker` group).

Screenshots go in `Lab4/SS/` as `SS_<name>.png`:

```bash
mkdir -p SS
```

| Name | Content | Section |
|---|---|---|
| SS_T1_1 .. SS_T1_10 | one per demo section of `task1_demo.sh` | 2 |
| SS_T4_1 | `docker compose ps` | 4 |
| SS_T4_2 | `task4_check.sh` output | 4 |
| SS_T2_1 .. SS_T2_3 | agent CLI: DT, XGB, ALL | 5 |
| SS_T2_5 | filter demo: `docker compose logs -f client` (fails during a block, recovers) | 5 |
| SS_K_1 .. SS_K_7 | kernel proof: XDP attached, program, maps, counters, blocklist, Malicious rows, detached | 7 |
| SS_T3_1 .. SS_T3_3 | UI with 20 replayed dataset flows (mixed Normal and Malicious): DT, XGB, ALL (SS_T3_3 shows Malicious rows and the blocks counter) | 6 |

---

## 0. Prerequisites (once)

```bash
# Host packages (Debian/Ubuntu)
# only on a fresh machine: already present on this VM (clang 21, libbpf-dev 1.6.3, tcpdump; git-lfs 3.8.1 is present at /usr/local/bin/git-lfs)
sudo apt-get install -y git-lfs make clang libbpf-dev tcpdump python3   # [SUDO]
docker --version && docker compose version     # Engine >= 28.1, Compose plugin, user in the docker group

# uv (installs CPython 3.12) - only on a fresh machine: already present on this VM (uv 0.13.5)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

xdp-tools, built from source and installed (**[SUDO]**; do not also apt-install xdp-tools):

```bash
cd ~/src/xdp-tools && make && sudo make install && sudo ldconfig     # [SUDO]
cd -                                                                  # back to Lab4
```

Verify (expect paths under `/usr/local/sbin` and a version string, no error):

```bash
which xdp-loader xdp-filter xdpdump
xdp-filter help | head -5
sudo xdpdump -D                                                       # [SUDO] lists interfaces
```

Dataset (git-lfs; the file must be large, not a pointer):

```bash
git lfs pull
ls -lh Friday-WorkingHours-Afternoon-DDos.csv
```

## 1. Python environment, training, unit tests

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python script/train.py            # clean, split, train DT + XGB, export to models/, parity check
.venv/bin/pytest -m "not kernel and not docker" -q    # unit + e2e (full CSV), no root
```

Expect: `models/kernel_model.json` and `outputs/metrics/` exist; pytest ends with `passed` and no failures. (Faster, without the e2e test: `-m "not e2e and not kernel and not docker"`.)

## 2. Task 1: xdp-tools demo (**[SUDO]**)

```bash
mkdir -p xdp_tools/logs
sudo bash xdp_tools/task1_demo.sh 2>&1 | tee xdp_tools/logs/task1_demo.log      # [SUDO]
ip netns list        # must not contain lab4t1 afterwards
```

The script uses its own netns and veth pair and cleans up on exit. It prints 10 sections; take one screenshot per section:

| Screenshot | Section |
|---|---|
| SS_T1_1 | `xdpdump -D`, nothing loaded |
| SS_T1_2 | `xdp-filter load`, then `xdpdump -D` shows `xdp_dispatcher` |
| SS_T1_3 | ping passes, 0% loss |
| SS_T1_4 | IP rule: ping 100% loss, `xdp-filter status` with hits |
| SS_T1_5 | `xdpdump` shows `XDP_DROP`; after removing the rule the ping works |
| SS_T1_6 | port filter: HTTP 200, timeout, status, 200 again |
| SS_T1_7 | `xdpdump -x` hex dump |
| SS_T1_8 | `xdpdump -w - \| tcpdump -r - -n` |
| SS_T1_9 | `xdp-filter poll -i 1000` rates |
| SS_T1_10 | `xdp-filter unload`, `xdpdump -D` empty again |

To take screenshots at your own pace, scroll the terminal or `less -R xdp_tools/logs/task1_demo.log` afterwards.

## 3. Build the BPF object and the IDS image, kernel tests

```bash
export LAB4_UID=$(id -u) LAB4_GID=$(id -g)      # files written by the privileged container are owned by you; repeat in every new shell
make -C xdp                                      # BPF object on the host, no root
docker compose build ids                         # pulls python:3.12-slim, builds lab4-ids:latest
docker run --rm --privileged -v "$PWD/models:/lab4/models:ro" lab4-ids:latest \
  python3 -m pytest tests/test_kernel.py -m kernel -q
```

Expect: build finishes; kernel tests end with `passed`.

(`bash run.sh` runs sections 1, 3, 4 in one go, `bash run.sh --quick` with the small fixture. Use the explicit commands below when you want to screenshot each step.)

## 4. Task 4: containers (Nginx, Apache, ping)

```bash
docker compose up -d                  # nginx, apache, pinger, client, ids; pulls the base images
sleep 5
docker compose ps                     # SS_T4_1: all 5 services Up
bash docker/task4_check.sh            # SS_T4_2: ends with "RESULT: all checks PASSED"
```

Optional manual pings from the pinger container:

```bash
docker compose exec pinger ping -c 3 nginx
docker compose exec pinger ping -c 3 apache
docker compose exec pinger ping -c 3 172.28.2.10
docker compose exec pinger ping -c 3 172.28.2.11
```

The log is also written to `outputs/task4/task4_check.log`. Leave the stack up for sections 5 and 6.

## 5. Task 2: real-time CLI (inside the IDS container)

The client container sends steady normal traffic through the IDS. Run each model for 30 s; the output is one JSON line per classified flow, then a summary. Expect `Malicious` count 0 and no drops.

```bash
docker compose exec ids python3 script/agent.py --iface ext0 --model DT  --timespan 30    # SS_T2_1
docker compose exec ids python3 script/agent.py --iface ext0 --model XGB --timespan 30    # SS_T2_2
docker compose exec ids python3 script/agent.py --iface ext0 --model ALL --timespan 30    # SS_T2_3
```

Optional: `--block-seconds N` (default 60), `--xdp-mode {skb,native}` (default skb). Results are written to `outputs/realtime/`.

Filter demo (no attack tools): an always-Malicious stub model makes the filter fire on the client's normal traffic.

```bash
docker compose exec ids python3 script/agent.py --iface ext0 --model DT \
  --model-file tests/fixtures/always_malicious.json --timespan 30 --block-seconds 20      # filter demo; evidence screenshot is SS_T2_5 (client log, below)
```

Expect: drops greater than 0 and 2 blocks in the summary (the source is re-blocked after the 20 s expiry). Optionally, in a second terminal while it runs, watch the client fail and recover (**SS_T2_5**):

```bash
docker compose logs -f client
```

Only one capture can run per interface at a time (a lock): do not start the UI capture while a CLI run is active.

## 6. Task 3: web UI (in the browser)

The UI starts with the stack. It listens on the management network only, so open it from the host:

```bash
xdg-open http://172.28.0.2:8080       # or paste the URL in the browser
```

For each model, in the page:

1. Available Local Interfaces: select `ext0`.
2. Enter Timespan: `30`.
3. Model: select **DT**, click **Start Packet Capture**, wait for the Algorithm Output table to fill (Src IP, Src Port, Dst IP, Dst Port, Timestamp, Result = Normal). Screenshot **SS_T3_1**.
4. Repeat with **XGB** (**SS_T3_2**) and **ALL** (**SS_T3_3**), waiting for the previous capture to finish (or press stop).

Replay dataset flows is **20** by default (allowed 0..100, set it higher for a longer table). Each start replays that many CIC-IDS2017 test-split flows through the kernel program, half BENIGN and half DDoS, drawn at random and injected at random times during the first 80 % of the capture (so they interleave with live rows), so the table shows at least 20 rows with a random mix of Normal and Malicious (plus the client's own flows). Replayed sources are 10.99.x.y; no attack tool is used and nothing goes on the wire. Inter-arrival times are not reproduced.


## 7. Proof: classifier and XDP filter run in the kernel and block malicious flows

Use two terminals in `Lab4/` with the stack up. Terminal B only works while A runs: the pins under `/sys/fs/bpf/lab4/ext0/` vanish when the capture ends. All values below are real output from the 2026-11-26 live run; IDs, counts and addresses differ on every run.

**Terminal A (keep running):**

```bash
docker compose exec ids python3 script/agent.py --iface ext0 --model ALL --timespan 120 --replay 60
```

Malicious lines appear with `DT: Malicious · XGB: Malicious` from 10.99.x.y sources. Alternative: the UI with Replay 60 and timespan 120.

**Terminal B (while A runs), one screenshot each:**

```bash
# SS_K_1: XDP program attached in the kernel (skb mode)
docker compose exec ids bpftool net show dev ext0
```
Expect under `xdp:` the line `ext0(3) generic id 611` (the id differs per run).

```bash
# SS_K_2: the verified, JIT-compiled kernel program
docker compose exec ids bpftool prog show name xdp_ids
```
Expect `611: xdp  name xdp_ids … xlated 5664B  jited 3263B`.

```bash
# SS_K_3: the model and config live in kernel maps (one command, paste in Terminal B while A runs)
docker compose exec ids sh -c 'P=/sys/fs/bpf/lab4/ext0; echo "== maps =="; ls $P/maps; echo "== programs =="; ls $P/progs; echo "== config (mode 3 = ALL) =="; bpftool map lookup pinned $P/maps/config key 0 0 0 0; echo "== first node of the decision tree =="; bpftool map lookup pinned $P/maps/nodes key 0 0 0 0'
```
- `maps` / `progs`: the model and the blocklist live in pinned kernel maps, next to the program.
- Config: `mode: 3` = ALL, `n_xgb_trees: 20`, `block_ns: 60000000000` = 60 s block time.
- Node 0 is the DT root: `feature 2` = Fwd Packet Length Max, its threshold, and the left/right child indices (`threshold 21, left 1, right 46` in the real run).

```bash
# SS_K_4: counters kept inside the XDP program
docker compose exec ids python3 -c "import sys; sys.path.insert(0, 'script'); import bpf_ctl, flowview; print(flowview.parse_stats(bpf_ctl.dump('stats', '/sys/fs/bpf/lab4/ext0')))"
```
Real run: `ST_PKTS 1202, ST_PASS 1172, ST_DROP 33, ST_FLOWS_CLASSIFIED 208, ST_FLOWS_MALICIOUS 30, ST_BLOCKS_ADDED 30, ST_NOT_TRACKED 3`. Expect `ST_FLOWS_MALICIOUS`, `ST_BLOCKS_ADDED` and `ST_DROP` all greater than 0. `ST_DROP` is at least `ST_BLOCKS_ADDED` because later packets of a blocked source are dropped too.

```bash
# SS_K_5: the kernel blocklist
docker compose exec ids bpftool map dump pinned /sys/fs/bpf/lab4/ext0/maps/blocklist
```
bpftool prints this map with BTF formatting, so key and value are decimal numbers, not hex bytes.
- Key = the source IPv4 read as a little-endian u32. To decode, split it into bytes starting from the lowest: key `182543114` = 10.99.225.10 and `4272710410` = 10.99.172.254 (real values from the 2026-11-26 run). Every key decodes to 10.99.x.y, a blocked replay source.
- Value = expiry time in ns (kernel monotonic clock).
- Decode one-liner:

```bash
python3 -c "import socket,struct; print(socket.inet_ntoa(struct.pack('<I', 182543114)))"
```

**SS_K_6:** Terminal A with the Malicious rows (or the UI table and status counters). Take it while Terminal A is still running.

**SS_K_7:** after A finishes:

```bash
docker compose exec ids bpftool net show dev ext0
```
Expect no `xdp:` entry: the program was cleanly detached.

Note: the live client (172.28.1.20) stays Normal and is never blocked. The malicious flows are dataset replays (no attack tools, slide 8), pushed through the same attached program with BPF_PROG_TEST_RUN. Blocking of live requests on the real wire is shown by the filter demo in section 5 (SS_T2_5, client FAIL lines).

## 8. Full teardown

Stops and removes the containers, networks, every image the stack uses (lab4-ids, nginx, httpd, alpine) and volumes:

```bash
docker compose down --rmi all --volumes --remove-orphans
docker rmi python:3.12-slim          # the base image of the IDS build
docker builder prune -f              # optional: build cache
```

Check that nothing is left (each should show no lab4 entries):

```bash
docker ps -a
docker images
docker network ls                    # no lab4_* networks
ip netns list                        # no lab4t1
sudo xdpdump -D                      # [SUDO] no XDP program on any interface
```

`.venv/`, `models/` and `outputs/` stay on disk. To go back to a fully clean state: `rm -rf .venv models_quick outputs_quick` (keep `models/` and `outputs/`, the report and deck reuse them).
