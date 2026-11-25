# CLAUDE.md: Security Insider Lab, Lab 4 (DDoS defense with eBPF/XDP: in-kernel detection and filtering)

Lab 4 has four tasks. Task 1 configures xdp-tools (xdp-filter, xdpdump). Task 2 builds a **complete real-time cycle**: capture packets, compute flow features, classify the flow, filter it. Task 3 is a front-end. Task 4 is Docker containerization (Nginx, Apache, ping).

The user chose the **Best case** of slide 9 only: the classifier (Decision Tree and/or XGBoost, `--model DT|XGB|ALL`) **and** the filter both run **in the kernel**, inside one XDP program. User space only loads the model, configures the program and displays results.

- Course: Security Insider Lab, Uni Passau, group **G8** (max 2 members).
- Spec: `Lab-4.pptx` (12 slides; tasks on slides 7–11, submission on slide 12). The deck has no speaker notes. Slide 10's content is a screenshot of a sample UI (§2). Progress is tracked in `TASKS.md`.
- **Scope rule:** build what the spec and the user's decisions (§2) ask for, plus the tests needed to trust the results. Do not add tasks, features, models or demos without the user's approval.
- **Self-contained:** Lab 4 never imports from `../Lab2` or `../Lab3`. Porting verified logic (copy and adapt) is encouraged; name the source file in the module docstring.
- **Task work starts only when the user prompts.** The user reviews these docs first.
- **Wednesday data is excluded for now (user, 2026-11-26).** Do not include `Wednesday_dataset/` or anything derived from it (CSV, `Wednesday_dataset/outputs/`, §3.7 numbers) in commits, the README, `run.sh`, `USER_COMMANDS_RUN.md`, the report or the deck. The folder is git-ignored (`Lab4/.gitignore`). The code (`script/crossday.py`, its tests) stays, but no deliverable references its results until the user says otherwise.
- **Screenshots** taken by the user go to `Lab4/SS/` (names in `USER_COMMANDS_RUN.md`).

---

## 1. Model routing (MANDATORY; same table as `~/.claude/CLAUDE.md` and `../Lab3/CLAUDE.md` §1)

| Work type | Model | How to delegate |
|---|---|---|
| Orchestration, planning, analysis of the specs, design decisions, audit and review of code and outputs, **writing and maintaining this `CLAUDE.md` and `TASKS.md`** | **Opus 5.5** (main session) | inline |
| Coding: Python, C (eBPF), shell, Dockerfile/compose, HTML/JS, unit/kernel/e2e tests, debugging, pylint fixes. Docs (README, report text), LaTeX, presentation | **Sonnet 5.5** | `Agent(subagent_type="general-purpose", model="sonnet", ...)` |
| Command-line execution (env setup, builds, `docker`, running scripts/tests, collecting output), file inventory, text extraction, browser use, light tasks | **Haiku 5.5** | `Agent(subagent_type="general-purpose", model="haiku", ...)` |

Rules:

1. **Exception** (user, 2026-11-13, kept for Lab 4): the lab's `CLAUDE.md` and `TASKS.md` are written by Opus. Every other document goes to Sonnet. **No Fable review** of these docs (user, 2026-11-25).
2. Subagents start cold. Each prompt names the `TASKS.md` ID(s), tells the agent to read this file and its `TASKS.md` entry first, and gives the exact output paths and the AC.
3. Sonnet may run `pytest`, `pylint`, `radon`, `make -C xdp` and short smoke runs while debugging its own code. Env setup, image builds, the full training run, kernel/docker tests and the official verification runs stay with Haiku.
4. Haiku reports output verbatim and edits no files (commands may create `.venv/`, caches, logs via `tee`, `outputs/`, `models/`). Opus routes every fix to Sonnet.
5. Opus checks each result against its AC and §3–§5, then ticks the box in `TASKS.md`. **Only Opus ticks boxes.**
6. **sudo is not available non-interactively** (`sudo -n true` fails). Root steps on the **host** are run by the user personally ([U] tasks give the exact commands). Root inside Docker needs no sudo: the user is in the `docker` group, so Haiku can run privileged containers (§4.9). Kernel tests therefore run in the IDS image.

---

## 2. Specs and user decisions

| Task | Spec (slide) | What is built |
|---|---|---|
| 1 | "Configuration of eBPF/XDP": download and configure xdp-tools completely; consider **xdp-filter** and **xdp-dump**; run example commands; screenshots in the report (slide 7) | Install the existing build (prerequisite T1.1), then `xdp_tools/task1_demo.sh` runs the README example commands in a netns/veth sandbox; the user takes screenshots |
| 2 | "Real time cycle": capture packets → flowmeter → classifier for detection → filtration (slide 8). **Note on the slide:** no attacking tools in real-time testing; the interface may show only normal traffic; classifier performance against malicious live traffic need not be checked. Slide 9 lists Acceptable / **Best** / Also-acceptable cases | **Best case only (user):** one XDP program `xdp/lab4_xdp.bpf.c` does capture (XDP hook), flowmeter (per-flow map), classification (DT/XGB trees in BPF maps) and filtering (source blocklist, `XDP_DROP`). Offline training in `script/train.py`; real-time CLI `script/agent.py --model DT|XGB|ALL` |
| 3 | "Design a front end Interface (sample)" (slide 10): sample shows a dark page with **Available Local Interfaces** (dropdown, e.g. `vethwe-bridge`), **Enter Timespan** (number), **Start Packet Capture** (button), and an **Algorithm Output** table with Src IP, Src Port, Dst IP, Dst Port, Timestamp (`23-02-2024 07:46:10 PM`), Result (Normal/Malicious) | `script/webui.py` + `web/index.html` (stdlib server, one page), same controls plus a Model dropdown (DT/XGB/ALL) and a status line |
| 4 | "Containerization & Orchestration" (slide 11): Docker container for Nginx, for Apache, and a container that pings both; check whether communication is possible. Slide note: optional if the best case is reached | **Required (user).** `docker-compose.yml`: nginx, apache, pinger (+ the IDS gateway and a normal-traffic client used by Tasks 2–3); `docker/task4_check.sh` |

Binding user instructions (2026-11-25):

- **D1 Best case only:** classifier **and** filter at kernel level (XDP). No user-level classifier path, no "acceptable case" fallback.
- **D2 Models:** Decision Tree and XGBoost. Flag `--model` with values `DT`, `XGB`, `ALL` (ALL = both models run in the kernel). It exists on `agent.py` and as the UI default (`webui.py --model`); the UI also has a Model dropdown.
- **D3 Docker is required** (Task 4 is not optional). Docker also hosts the IDS gateway, which is how kernel tests and the live cycle run without host sudo.
- **D4 Prerequisite:** check XDP with Haiku before planning; install whatever is missing as a prerequisite task. Result (2026-11-25): xdp-tools is **built but not installed** on this machine (§3.1), so T1.1 installs it.
- **D5** Opus writes these docs; no task work until the user prompts (plan-review gate).
- **D6 (2026-11-25, Lab 3 side experiment):** the user asked for XGBoost with **20 trees, depth 4–6**. Lab 4 uses **20 trees** for the kernel XGBoost; the depth is selected on validation from {4, 5, 6} (§4.4). Evidence: `../Lab3/outputs_xgb20/` (§3.3).

- **D7 (2026-11-26, user): cross-day test on Wednesday.** After training, testing and the kernel work, use `Wednesday_dataset/Wednesday-workingHours.pcap_ISCX.csv` as a test dataset; every output goes under `Wednesday_dataset/`.
  - File: sha256 `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`, 225,166,395 B, 692,703 rows × 79 columns (same columns as Friday).
  - Labels: BENIGN 440,031; DoS Hulk 231,073; DoS GoldenEye 10,293; DoS slowloris 5,796; DoS Slowhttptest 5,499; Heartbleed 11.
  - inf/NaN occur only in Flow Bytes/s and Flow Packets/s.
  - Opus design (O14):
    - Score the **frozen** `models/kernel_model.json` (the deployed artefact; no retraining or refitting).
    - Row cleaning only: inf/NaN rows and duplicate rows, as Lab 3 steps 2–4. No column drops, so Wednesday's data cannot remove a kernel feature.
    - Labels: BENIGN → 0, every other label → 1. These are DoS attacks, which are **not** in the Friday training data, so this measures cross-day, cross-attack generalisation.
    - Outputs: metrics for DT, XGB and ALL; per-label detection rate; BENIGN false-alarm rate; kernel parity on a stratified 1,024-row sample.
    - The CSV is tracked with git-lfs (> 100 MB GitHub limit).

### 2.1 Opus design decisions (the user may override any of them at review; reasons in §4)

| ID | Decision |
|---|---|
| O1 | Kernel feature set = 10 forward-direction, behaviour-only CIC features (§5.1). **Destination Port and Init_Win_bytes_forward are excluded** (shortcut/fingerprint features; port 80 is exactly the demo servers' port) |
| O2 | Trees are trained on **raw** feature values (no scaler); thresholds become integers in kernel units (§5.2) |
| O3 | Same cleaning and 70/15/15 split as Lab 3 (the test split holds the same rows), then projection onto the 10 features |
| O4 | Depth from validation: DT {6, 8, 10}, XGB {4, 5, 6} at 20 trees; the smallest depth whose val F1 is within 0.0005 of the best |
| O5 | A flow is classified on a packet with FIN or RST, and when its packet count is a power of two and ≥ 8 |
| O6 | `ALL` = both models; the flow is **Malicious only if DT and XGB agree** (consensus, fewer false drops) |
| O7 | Malicious → source IPv4 is blocked for 60 s (`--block-seconds`); the classifying packet is dropped too; internal errors fail open (pass) |
| O8 | User space uses **bpftool only** (load, pin, batch map updates, attach/detach, map dumps, `prog run`); no custom C loader |
| O9 | Topology: the IDS container is an **inline gateway** (`ext0` → XDP → forward → `int0`) in front of nginx/apache; the UI listens only on `mgmt0` |
| O10 | Verification chain: float model ≈ Python integer model (all 33,463 test rows) **==** kernel C (exact, 1,024 vectors) |
| O11 | The filter path is demonstrated **without attack tools**: kernel tests and a live demo use an always-Malicious stub model on normal traffic |
| O12 | Task 1 runs on the host in a netns/veth sandbox, never on `enp0s3` |
| O13 | IPv4 TCP/UDP only. Everything else (ARP, IPv6, ICMP, fragments, VLAN, malformed) passes untouched and is counted |

---

## 3. Verified facts (Haiku, 2026-11-25)

### 3.1 Toolchain and machine

- Ubuntu 26.04.1 LTS, kernel **7.0.0-43-generic**, 6 CPUs, 15 GiB RAM, 31 GB free. VirtualBox VM (`enp0s3` MAC 08:00:27:…). Interfaces: `lo`, `enp0s3` (192.168.57.17/24), `docker0` (down).
- Present: `/sys/kernel/btf/vmlinux`; clang/llc **21.1.8** (BPF target); bpftool **7.7.0**; libbpf-dev **1.6.3** (`/usr/include/bpf/bpf_helpers.h`); `asm/types.h`; make, gcc, git, pkg-config, ip; libelf 0.194, zlib 1.3.1, libpcap 1.10.6.
- BPF settings: lockdown `[none]`, `kernel.unprivileged_bpf_disabled = 2` (BPF needs root), `bpf_jit_enable = 1`; bpffs mounted at `/sys/fs/bpf` (mode 700).
- **xdp-tools:** source at `~/src/xdp-tools`, **v1.6.3-32-g92a9828** (commit 92a98287, 2026-11-08), configured and **built** (`xdp-loader`, `xdp-filter`, `xdpdump`, `xdp-bench`, …). **Not installed:** nothing in `/usr/local/sbin`, no libxdp (`pkg-config libxdp` fails), no `/usr/local/lib/bpf`.
  - **Lab 3 log discrepancy:** `../Lab3/xdp/xdp-tools/logs/install_verify.log` says ALL CHECKS PASSED, but it lists `enp2s0f0`, `wlp3s0` and `br-*` interfaces, which this machine does not have. That install ran on the partner's machine. On this machine only the uninstalled build exists (Lab 3 README used `LIBXDP_OBJECT_PATH` for that reason).
- **Docker** 29.9.3, **Compose 5.7.1**, daemon active, cgroup v2, AppArmor + seccomp; the user is in group `docker` (so privileged containers run without sudo). No Lab 4 images yet.
- Traffic tools: tcpdump, tshark, nstat, nc, ping, ethtool present; hping3, tcpreplay, iperf3, ncat, scapy absent (**not needed**: no attack tools, spec slide 8).
- Python: uv 0.13.5; uv-managed CPython **3.12.15** installed (system Python 3.14.4 must not be used). Lab 4 `.venv` created 2026-11-25 (T1.4): 30 packages, pins as requirements.txt.
- Images (T1.4, 2026-11-25): `nginx:stable-alpine` sha256:8eb04fe3…c0d3, `httpd:2.4-alpine` sha256:32bd0639…3a24, `alpine:3` sha256:f59abe65…71bf, `python:3.12-slim` sha256:191083cd…51b4b. Only the default Docker networks exist (no 172.28.x conflict). Privileged container + bpffs mount works (`BPFFS_OK`).
- Lab 4 CSV copy: sha256 verified; git-lfs did not cover it (rule was Lab3-only), so `.gitattributes` gets a Lab4 line (T3.1).
- Repo: CSVs are stored with **git-lfs** (`.gitattributes`, README says `git lfs pull`); `Lab3/Friday-WorkingHours-Afternoon-DDos.csv` is tracked. No root `.gitignore`. Root `README.md` has a lab table (Labs 1–3) and a Quick start.

### 3.2 Data (reused from `../Lab3/CLAUDE.md` §3; pinned again by the Lab 4 e2e test)

- CSV sha256 `646fd1282cf584bd330caf4dab51c689799b223425cf643edde172a1a655793d` (77,349,605 bytes). Raw 225,745 × 79; DDoS 128,027, BENIGN 97,718.
- Lab 3 cleaning (inf/NaN rows 34, duplicates 2,629, 10 constant + 9 identical columns) → **223,082 rows** (DDoS 128,014, BENIGN 95,068).
- 70/15/15 two-stage stratified split, seed 42: train 156,157 (89,610 / 66,547), val 33,462 (19,202 / 14,260), test 33,463 (19,202 / 14,261) as DDoS / BENIGN.
- Fixture: `../Lab3/tests/fixtures/sample_ddos.csv` (3,187 rows: 1,665 BENIGN / 1,522 DDoS, 34 inf rows), sha256 `e11e365a1de7456954074532a1bd9c6583d7046d666b7a4ae8c360fcdd01db3f`.
- Lab 3 full-feature reference (test): XGBoost F1 1.0000 (FP 0, FN 0); Lab 2 DT F1 0.9996. The Lab 4 kernel models use 10 of the 59 features, so slightly lower scores are expected; the report compares them honestly.

### 3.3 Lab 3 side experiment: XGBoost with 20 trees (user, 2026-11-25)

[S] wrote `../Lab3/script/xgb_small.py` (+ `tests/test_xgb_small.py`, pylint 10.00/10, Lab 3 suite 87 passed) and [H] ran it in 11 s; outputs in `../Lab3/outputs_xgb20/` (git-ignored). Same Lab 3 data path (59 standardised features, 70/15/15). The small models use the Lab 3 XGBoost settings (lr 0.1, hist, seed 42) with `n_estimators=20`, `max_depth` 4/5/6 and no early stopping. The refit of the original reproduced the stored test metrics exactly.

| Model (test split) | Trees | Nodes | Acc | Prec | Rec | F1 | ROC-AUC | FP | FN | Val F1 |
|---|---:|---:|---|---|---|---|---|---:|---:|---|
| Original (early-stopped at 341) | 341 | 4,867 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1.0000 |
| 20 trees, depth 4 | 20 | 312 | 0.9992 | 0.9997 | 0.9989 | 0.9993 | 1.0000 | 5 | 22 | 0.9994 |
| 20 trees, depth 5 | 20 | 408 | 0.9992 | 0.9997 | 0.9989 | 0.9993 | 1.0000 | 5 | 22 | 0.9994 |
| 20 trees, depth 6 | 20 | 482 | 0.9993 | 0.9998 | 0.9989 | 0.9993 | 1.0000 | 4 | 21 | 0.9995 |

Opus reading:
- 6 % of the trees and 6–10 % of the nodes cost 0.0007 F1: 21–22 more missed attacks and 4–5 more false alarms among 33,463 test flows.
- Depth hardly matters at 20 trees. Depths 4 and 5 give identical confusion matrices; depth 6 saves one FP and one FN for 170 more nodes. The O4 rule would pick depth 4 here.
- At lr 0.1, 20 rounds leave the ensemble under-boosted: the extra errors are mostly missed attacks. If the Lab 4 kernel XGBoost falls short at T3.6, the learning rate is the first knob, and only with the user's approval.
- Kernel cost: about 20 × 5 = 100 node visits per classification at depth 4 (vs 341 trees); 312–482 nodes fit easily in MAX_NODES 8192.
- These runs use 59 features; Lab 4 uses 10, so they are an upper reference, not the expected Lab 4 result.

### 3.4 Lab 4 kernel models (T3.5, 2026-11-25; `outputs/metrics/`, 9 s run)

Depth selection (val F1, tolerance 0.0005): DT {6: 0.99904, 8: 0.99914, 10: 0.99906} → **6**; XGB (20 trees) {4: 0.99896, 5: 0.99906, 6: 0.99904} → **4**. Model: 387 nodes in total.

| Model (test) | Acc | Prec | Rec | F1 | ROC-AUC | TP | TN | FP | FN |
|---|---|---|---|---|---|---:|---:|---:|---:|
| Decision Tree (d6) | 0.9989 | 0.9998 | 0.9983 | 0.9991 | 0.9999 | 19170 | 14257 | 4 | 32 |
| XGBoost (20 trees, d4) | 0.9987 | 0.9994 | 0.9984 | 0.9989 | 0.9998 | 19171 | 14250 | 11 | 31 |

- Integer models: identical confusion matrices. DT integer ROC-AUC is 0.9990 because the kernel DT outputs hard classes.
- Parity: 100 % for both models on 33,463 rows; max margin error 4.5e-5; `ac_pass` true.
- Opus reading:
  - The 10 behaviour-only features keep test F1 within 0.001 of the 59-feature Lab 3 models (DT 0.9996 in Lab 2; XGB 20t 0.9993 in §3.3).
  - Importance is concentrated: Fwd Packet Length Max (DT 0.58 / XGB 0.72) and Total Length of Fwd Packets (0.42 / 0.28) carry about 99 %. The kernel model is essentially a payload-size rule, so the live demo's request sizes decide T6.4.


### 3.5 Kernel evidence (T4.4, 2026-11-25; `outputs/kernel/`)

- Verifier accepts `xdp_ids` and `classify_test`; `xdp_ids` is 5,664 B xlated / 3,263 B JIT.
- 16/16 kernel tests pass, including exact parity on 1,024 test vectors.
- Average ns per packet (BPF_PROG_TEST_RUN, 100k repeats):

  | Packet | DT | XGB | ALL |
  |---|---:|---:|---:|
  | not tracked | 11 | 11 | 11 |
  | mid-flow | 84 | 69 | 65 |
  | classifying (FIN) | 92 | 377 | 384 |

- bpftool `-j` dumps carry a `formatted` dict (BTF). Per-CPU stats come as `formatted.values[{cpu, value}]`. `saddr` is a little-endian read of the network-order bytes (33554442 = 10.0.0.2).

### 3.6 Live cycle (T6.2–T6.3, 2026-11-25; `outputs/realtime/`)

- Task 4: `task4_check.sh` all PASS (ping by name and IP, HTTP to nginx and apache).
- `interface_name` works: `mgmt0/ext0/int0` with the §5.6 IPs. The client routes to 172.28.2.0/24 via 172.28.1.2.
- 6/6 docker tests pass.
- Normal traffic, 60 s per model on `ext0`: DT, XGB and ALL each classified 118 flows (5–7 packets each, at FIN). **0 Malicious, 0 drops**; client 138/138/140 OK, 0 FAIL. The domain-shift risk (§9) did not occur for busybox wget.
- Filter demo (`always_malicious.json`, DT, block 20 s, 30 s run): 55 drops, 2 blocks (re-blocked after the 20 s expiry). The client timed out during each block and recovered in between.
- No XDP was left on `ext0` after the runs.
- UI API: `/api/interfaces` gives `[ext0, int0, lo]` (mgmt0 hidden). A 20 s ALL capture via the API: 41 classifications, all Normal. Browser screenshot: not produced (no Chrome); it comes from the user (T6.5).


### 3.7 Cross-day test on Wednesday (T10.2, 2026-11-26; `Wednesday_dataset/outputs/`, 71 s)

Row cleaning: 1,297 inf/NaN rows (Hulk 949, BENIGN 348) and 80,914 duplicates removed → 610,492 rows (BENIGN 416,736; attacks 193,756). The frozen kernel model gives:

| Mode | Recall (attacks) | Precision | F1 | False-alarm rate (BENIGN) | TP | FP | FN |
|---|---|---|---|---|---:|---:|---:|
| DT | 0.0033 | 0.7108 | 0.0065 | 0.0006 | 634 | 258 | 193,122 |
| XGB | 0.0029 | 0.5895 | 0.0058 | 0.0009 | 560 | 390 | 193,196 |
| ALL | 0.0025 | 0.7070 | 0.0050 | 0.0005 | 485 | 201 | 193,271 |

Per-label detection (DT / XGB / ALL):

| Label | Detection |
|---|---|
| Hulk (172,846) | 0.36 % / 0.32 % / 0.28 % |
| GoldenEye (10,286) | 0 / 0 / 0 |
| slowloris (5,385) | 0.02 % / 0 / 0 |
| Slowhttptest (5,228) | 0.13 % / 0.17 % / 0 |
| Heartbleed (11) | 0 / 0 / 0 |

Kernel parity on 1,024 Wednesday vectors: exact.

**Opus reading:**
- The Friday-trained models **do not generalise** to Wednesday's DoS attacks; they detect almost nothing.
- They also raise almost no false alarms (≤ 0.09 %).
- This is consistent with §3.4: the model is a payload-size rule tuned to Friday's LOIC HTTP flood. My prior expectation that Hulk/GoldenEye would be partly detected was wrong.
- For the report: within-day test F1 ≈ 0.999 says little about cross-attack robustness.
- Remedies are out of scope unless the user asks: multi-day or DoS-labelled training data, more features.

---

## 4. Architecture and design rationale

### 4.1 Data path (Best case)

```
client (172.28.1.20) ──front──▶ ext0 [IDS container: XDP program xdp_ids]
                                  1 capture   : XDP hook, ingress of ext0 (before the kernel stack)
                                  2 blocklist : source IPv4 blocked? → XDP_DROP
                                  3 flowmeter : LRU map "flows" (5-tuple → counters, sizes, IATs)
                                  4 classify  : DT / XGB tree walk over maps "nodes"/"roots" (integer)
                                  5 filter    : Malicious → blocklist[src] = now + block_ns; XDP_DROP
                               PASS → ip_forward → int0 (MASQUERADE) ──back──▶ nginx 172.28.2.10 / apache 172.28.2.11
user space (same container): agent.py / webui.py → bpftool: load, map batch, attach, dump every 1 s
browser on the host → http://172.28.0.2:8080 (mgmt0 only)
```

### 4.2 Why this design

1. **Kernel features (O1).** XDP sees **ingress only**, so only the forward direction (client → server) is visible; every Bwd feature and every bidirectional feature (Flow Duration, Flow Bytes/s, Flow Packets/s, Fwd Packets/s) would be computed differently from CICFlowMeter. The 10 features of §5.1 are exactly computable with integer arithmetic from forward packets.
   - Std features need integer sqrt and CICFlowMeter's sample-std convention; header-length features have known CICFlowMeter quirks. Both are left out.
   - **Destination Port** (0.35 DT importance in Lab 2; DDoS is 128,011 / 128,014 port 80) and **Init_Win_bytes_forward** (OS fingerprint of the 2017 attack hosts) are shortcut features. The demo servers listen on **port 80**, so a port-based model would flag normal demo traffic and the filter would drop it. Behaviour-only features make the in-kernel decision meaningful. The report states the cost in test F1 against Lab 3.
2. **Integer inference (O2).** eBPF has no floating point. Trees are scale-invariant, so they are trained on raw values; each threshold becomes an integer in kernel units (§5.2) and the walk is "x ≤ T → left". XGBoost leaves become fixed-point integers (× 2^16). The rounding effect is measured, not assumed (O10).
3. **Model size (D6, O4).** Every classified packet walks the trees: DT ≤ 10 levels, XGB 20 trees × ≤ 6 levels = at most 120 node visits. Depth is chosen on **validation** with a bias to the smaller model; the test set is used once.
4. **When to classify (O5).** CICFlowMeter rows are **completed** flows; a SYN-only partial flow looks like a "1-packet flow" from the training set, which is a different thing. So the kernel classifies at flow end (FIN/RST) and re-checks long or connectionless flows at 8, 16, 32, … packets. Flows with fewer than 8 packets and no FIN/RST are not classified (documented limitation, §9).
5. **ALL = consensus (O6).** The action is a drop, so false positives cost more than false negatives in this demo (normal traffic only). AND keeps both verdicts visible in the UI and drops only when both models agree.
6. **bpftool user space (O8).** bpftool can do everything the cycle needs: `prog loadall` + `pinmaps`, `batch file` (thousands of map updates in one call), `net attach/detach`, `-j map dump` (BTF-formatted JSON) and `prog run` (BPF_PROG_TEST_RUN). A custom libbpf loader would add a C build and ring-buffer code without changing what is shown. Polling the flow map once per second is enough for a demo UI.
7. **Inline gateway in Docker (O9, D3).**
   - The IDS owns its interfaces (`mgmt0`, `ext0`, `int0`) in its own network namespace. XDP can never touch the host uplink `enp0s3`, and stopping the container removes the program, the pins and all blocks.
   - All client → server traffic must cross `ext0`, exactly like a DDoS scrubbing box in front of web servers.
   - The UI is on a separate management network, so its own HTTP polling never crosses the XDP hook. The client cannot reach it either, because it binds to the mgmt IP only.
8. **Verification chain (O10).** (a) `train.py` compares sklearn/XGBoost predictions with the Python integer evaluator on all 33,463 test rows. (b) The kernel program `classify_test` evaluates 1,024 test vectors in the kernel, and their DT verdicts and XGB margins must **equal** the Python integer evaluator exactly. Together: the kernel decides what the trained model decides.
9. **Privileged container.** Loading BPF needs CAP_BPF/CAP_NET_ADMIN/CAP_SYS_ADMIN (`unprivileged_bpf_disabled=2`). The IDS runs `privileged: true` and mounts its own bpffs. The `docker` group is root-equivalent; this is accepted for a lab VM and stated in the README.
10. **Filter demo without attack tools (O11).** With normal traffic and a good model the filter never fires. The filter path is proven by kernel tests and by a live run with `tests/fixtures/always_malicious.json` (one DT leaf = Malicious). The client's normal requests then start failing and the drop counter rises, with no attack tool used.

### 4.3 Training and evaluation (offline, host venv)

1. `preprocess.py` ports the Lab 3 cleaning (`../Lab3/script/preprocess.py`: load/strip, inf→NaN, drop NaN rows, drop duplicate rows on the full row, drop constant and identical columns with `atol=1e-6`), encodes BENIGN 0 / DDoS 1 (other labels → `ValueError`), splits 70/15/15 (seed 42, the same two-stage stratified split), then keeps the 10 kernel features in §5.1 order (a missing column → `KeyError` naming it). Arrays stay **float64, unscaled**.
2. Models (`train.py`, constants in `common.py`):
   - DT: `DecisionTreeClassifier(max_depth=d, random_state=42)`, d ∈ `DT_DEPTHS = (6, 8, 10)`.
   - XGB: `XGBClassifier(n_estimators=20, max_depth=d, learning_rate=XGB_LR, tree_method="hist", eval_metric="logloss", n_jobs=-1, random_state=42)`, d ∈ `XGB_DEPTHS = (4, 5, 6)`, **no early stopping** (exactly 20 trees go to the kernel), `fit(..., verbose=False)`. `XGB_LR = 0.1` (the Lab 3 value, also used in the D6 experiment).
   - `select_depth`: the smallest d whose **val** F1 ≥ best val F1 − 0.0005. The val scores of all candidates go to `outputs/metrics/depth_selection.json`.
3. Metrics (port of Lab 3 `evaluate.compute_metrics`; DDoS positive, `zero_division=0`, `y_pred = score > 0.5`): accuracy, precision, recall, F1, macro-F1, ROC-AUC, TN/FP/FN/TP, train and predict time; val and test; for the float models **and** the integer kernel models. **Never report accuracy alone.**
4. **Feasibility gate:** if the selected DT or XGB has test F1 < 0.99, Opus stops the plan and asks the user (feature set O1 is then the first thing to revisit). No silent feature changes.

### 4.4 Real-time semantics

- Flow key = (saddr, daddr, sport, dport, proto) as seen on ingress; the first packet's sender is the forward direction (as in CICFlowMeter for client-initiated flows).
- Payload length = IPv4 `tot_len` − IHL·4 − L4 header (TCP `doff`·4, UDP 8). Ethernet padding is never counted.
- Timestamps: `bpf_ktime_get_ns()` (CLOCK_MONOTONIC). The agent converts to wall time with `time.time() − (time.monotonic_ns() − t_ns)/1e9`; both clocks are the same kernel clock inside the container.
- Blocklist entries expire at `expiry_ns`; an expired entry is deleted on the next packet from that source.
- Mode `0` (all-zero config) = flowmeter only, no classification, no drops: a safe default before the agent writes the config.
- **One capture per interface.** `Session.start` takes a non-blocking `fcntl.flock` on `/run/lab4-<iface>.lock`. The kernel releases it when the process dies, so a crashed agent never leaves a stale lock. A second capture on the same interface, CLI or UI, fails with "capture already running on <iface>". Pins live in `PIN_DIR/<iface>`.
- The agent attaches only **after** the model and config are written, detaches **before** unpinning, and always detaches in `finally` / on SIGTERM. Once it holds the lock, any program already on the interface is stale, so a start detaches and unpins it first.

---

## 5. Contracts (Sonnet must follow them exactly; tests rely on them)

### 5.1 Kernel features (index order is the contract; `common.KERNEL_FEATURES` mirrors `N_FEATURES`)

| Idx | CIC column (stripped name) | Kernel computation (forward packets of the flow) | Scale s (kernel unit) |
|---:|---|---|---:|
| 0 | `Total Fwd Packets` | `pkts` | 1 |
| 1 | `Total Length of Fwd Packets` | `bytes` (sum of L4 payload) | 1 |
| 2 | `Fwd Packet Length Max` | `len_max` | 1 |
| 3 | `Fwd Packet Length Min` | `len_min` | 1 |
| 4 | `Fwd Packet Length Mean` | `bytes * 1000 / pkts` | 1000 (milli-bytes) |
| 5 | `Fwd IAT Total` | `last_ns − first_ns` | 1000 (µs → ns) |
| 6 | `Fwd IAT Mean` | `(last_ns − first_ns) / (pkts − 1)`, 0 if pkts = 1 | 1000 |
| 7 | `Fwd IAT Max` | `iat_max_ns`, 0 if pkts = 1 | 1000 |
| 8 | `Fwd IAT Min` | `iat_min_ns`, 0 if pkts = 1 | 1000 |
| 9 | `act_data_pkt_fwd` | `act_data_pkts` (packets with payload > 0) | 1 |

CIC IAT columns are in microseconds; the kernel measures nanoseconds, hence s = 1000. All divisions are unsigned 64-bit integer divisions (floor).

### 5.2 Threshold and feature conversion (`export_model.py`, `kmodel.py`)

- Python kernel-unit features: `x_int = floor(x * s)` as int64 (computed in float64 from the CSV values).
- sklearn DT goes left if `x <= t` → `T = floor(t * s)`.
- XGBoost goes left if `x < t` (t is float32) → `T = ceil(t * s) − 1`.
- Kernel and Python evaluator: **left iff `x_int <= T`** (signed 64-bit).
- DT leaf = class 1 if `P(DDoS) > 0.5` else 0. XGB leaf = `round(leaf * 2**16)` (s32); base margin = `round(logit(base_score) * 2**16)` (s64; base_score read from `booster.save_config()`, which may be a string like `"[5.6E-1]"`). XGB verdict = `margin_int > 0` (an exact 0 → Normal, as Lab 3's `score > 0.5` rule).
- Parity AC (on all test rows): DT verdict agreement **100 %**; XGB verdict agreement ≥ **99.99 %** and `|margin_int / 2**16 − margin_float| ≤ 1e-3` on every agreeing row. Every mismatch is written to `outputs/metrics/parity_mismatches.csv`. If the AC fails, stop and report to Opus.

### 5.3 C contract (`xdp/lab4_common.h`; `tests/test_consistency.py` parses it and compares with `common.py`)

```c
#define N_FEATURES        10
#define MAX_NODES         8192
#define MAX_TREES         64          /* roots[0] = DT, roots[1..n] = XGB trees */
#define MAX_TREE_DEPTH    10          /* walk bound = MAX_TREE_DEPTH + 1 steps */
#define LEAF_SHIFT        16
#define CLASSIFY_MIN_PKTS 8
#define MAX_FLOWS         65536
#define MAX_BLOCKED       65536
#define N_TEST_VECS       1024
enum ids_mode    { MODE_OFF = 0, MODE_DT = 1, MODE_XGB = 2, MODE_ALL = 3 };
enum ids_verdict { V_NORMAL = 0, V_MALICIOUS = 1, V_NONE = 255 };
enum ids_stat    { ST_PKTS = 0, ST_PASS, ST_DROP, ST_FLOWS_CLASSIFIED, ST_FLOWS_MALICIOUS,
                   ST_BLOCKS_ADDED, ST_NOT_TRACKED, N_STATS };
struct tree_node  { __s64 threshold; __s32 feature; __u32 left; __u32 right; __s32 leaf; };  /* 24 B; feature < 0 = leaf */
struct ids_config { __u32 mode; __u32 n_xgb_trees; __s64 xgb_base_margin; __u64 block_ns; };  /* 24 B */
struct flow_key   { __u32 saddr; __u32 daddr; __u16 sport; __u16 dport; __u8 proto; __u8 pad[3]; };  /* 16 B */
struct flow_state { __u64 first_ns, last_ns, pkts, bytes, len_max, len_min, iat_max_ns, iat_min_ns,
                    act_data_pkts, classified_ns; __s64 xgb_margin;
                    __u32 dt_verdict, xgb_verdict, verdict, tcp_flags; };  /* classified_ns 0 = not yet */
struct test_vec    { __s64 x[N_FEATURES]; };
struct test_result { __s64 xgb_margin; __u32 dt_verdict; __u32 xgb_verdict; };
```

- Byte order: `saddr`/`daddr` as in the IP header (network order); ports in host order (`bpf_ntohs`).
- Maps (the pin names): `config` (ARRAY 1), `nodes` (ARRAY MAX_NODES), `roots` (ARRAY MAX_TREES + 1, `__u32`), `flows` (LRU_HASH MAX_FLOWS), `blocklist` (LRU_HASH MAX_BLOCKED, `__u32` saddr → `__u64` expiry_ns), `stats` (PERCPU_ARRAY N_STATS, `__u64`), `test_vecs`, `test_results` (ARRAY N_TEST_VECS), `test_idx` (ARRAY 1, `__u32`).
- Programs: `SEC("xdp") xdp_ids` (the cycle) and `SEC("xdp") classify_test` (reads `test_idx`, classifies `test_vecs[idx]` with DT **and** XGB, writes `test_results[idx]`, increments `test_idx`, returns `XDP_PASS`; run with `bpftool prog run … repeat 1024`). Both share the same classification functions.
- Tree walk: bounded loop of `MAX_TREE_DEPTH + 1` steps; XGB sums trees with `bpf_loop(n_xgb_trees, …)` (n capped at MAX_TREES); a failed lookup or exhausted bound returns leaf 0 (fail open).
- Build: `clang -O2 -g -target bpf -Wall -Werror -I/usr/include/$(uname -m)-linux-gnu` → `xdp/lab4_xdp.bpf.o` (BTF required for the JSON dumps).

### 5.4 kernel_model.json (`models/`, written by `train.py`, read by `kmodel.load`)

```python
{"format": 1,
 "features": ["Total Fwd Packets", ...],            # the 10 names of §5.1, in order
 "scales": [1, 1, 1, 1, 1000, 1000, 1000, 1000, 1000, 1],
 "leaf_shift": 16,
 "nodes": [[feature, threshold, left, right, leaf], ...],   # DT nodes first, then XGB; absolute indices
 "dt_root": 0, "xgb_roots": [r1, ..., r20], "xgb_base_margin": int,
 "meta": {"dt_depth": d, "xgb_depth": d, "xgb_trees": 20, "n_nodes": n,
          "csv_sha256": "...", "created": "ISO-8601"}}
```

A leaf is `[-1, 0, 0, 0, value]`. `kmodel.validate` raises `ValueError` if n_nodes > MAX_NODES, 1 + len(xgb_roots) > MAX_TREES + 1, any depth > MAX_TREE_DEPTH, a feature index ∉ [−1, N_FEATURES), or a child index out of range. `models/test_vectors.json` = `{"x": [[10 ints] × 1024], "dt": [...], "xgb_margin": [...]}` (512 BENIGN + 512 DDoS test rows, seed 42, Python-evaluated). `tests/fixtures/always_malicious.json`: DT = one leaf with value 1, XGB = 1 tree, one leaf `+2**16`, base margin 0.

### 5.5 Python modules (`script/` is the import root, as in Lab 3)

| Module | Runs in | Public API |
|---|---|---|
| `common.py` | host + image (**stdlib only**) | paths (`LAB4_DIR`, `DEFAULT_CSV`, `DEFAULT_OUT`, `MODELS_DIR`, `KERNEL_MODEL_PATH`, `TEST_VECTORS_PATH`, `BPF_OBJ`), `SEED`, split fractions, labels, `DROP_DUPLICATES`, `IDENTICAL_ATOL`, `KERNEL_FEATURES` (tuple of (name, scale)), the §5.3 constants, `MODEL_MODES = {"DT": 1, "XGB": 2, "ALL": 3}`, `DT_DEPTHS`, `XGB_TREES = 20`, `XGB_DEPTHS`, `XGB_LR`, `DEPTH_F1_TOL = 0.0005`, `PIN_DIR = "/sys/fs/bpf/lab4"`, `MGMT_IFACE = "mgmt0"`, `DEFAULT_IFACE = "ext0"`, `DEFAULT_TIMESPAN_S = 30`, `MAX_TIMESPAN_S = 3600`, `DEFAULT_BLOCK_S = 60`, `POLL_INTERVAL_S = 1.0`, `TIMESTAMP_FMT = "%d-%m-%Y %I:%M:%S %p"`, `setup_logging(out_dir)` (idempotent; console + `out_dir/run.log`) |
| `preprocess.py` | host | `load_raw`, `clean(df) -> (df, summary)`, `encode_labels`, `split_data`, `select_kernel_features(df) -> df`, `@dataclass(frozen=True) KernelSplits(x_train, x_val, x_test, y_train, y_val, y_test, feature_names)`, `preprocess(csv) -> (KernelSplits, summary)` |
| `train.py` | host | `compute_metrics(y_true, y_score) -> dict` (Lab 3 schema), `select_depth(val_f1: dict[int, float], tol) -> int`, `fit_dt(splits, depth)`, `fit_xgb(splits, depth)`, `main(argv) -> int` (`--csv`, `--out`, `--models-dir`) |
| `export_model.py` | host | `to_int_features(x) -> np.ndarray[int64]`, `export_dt(model) -> list[list[int]]`, `export_xgb(model) -> (base_margin_int, list[list[list[int]]])`, `build_kernel_model(dt, xgb, meta) -> dict`, `parity(dt, xgb, kmodel, x, y) -> dict`, `sample_test_vectors(x_int, y, kmodel, n, seed) -> dict` |
| `kmodel.py` | host + image (stdlib) | `load(path)`, `save(model, path)`, `validate(model)`, `walk(nodes, root, x_int) -> int`, `dt_verdict(model, x_int)`, `xgb_margin(model, x_int)`, `xgb_verdict(margin)`, `final_verdict(mode, dt, xgb)`, `pack_node(node) -> bytes` (`struct "<qiIIi"`, 24 B), `batch_lines(model, pin_dir) -> list[str]` (nodes + roots), `config_line(mode, model, block_ns, pin_dir) -> str` |
| `bpf_ctl.py` | image (stdlib) | `run(args: list[str]) -> str` (never `shell=True`), `load(obj, pin_dir)`, `batch(lines)`, `attach(iface, pin_dir, mode="skb")`, `detach(iface)`, `dump(map_name, pin_dir) -> list[dict]`, `prog_run(prog, pin_dir, data: bytes, repeat=1) -> tuple[int, int]` (retval, avg ns), `unpin(pin_dir)` |
| `flowview.py` | image (stdlib) | `@dataclass FlowRow(src_ip, src_port, dst_ip, dst_port, proto, timestamp, result, models, pkts)`, `parse_flows(dump, mode, now_wall, now_mono_ns) -> list[FlowRow]` (classified flows only), `parse_stats(dump) -> dict[str, int]` (per-CPU values summed) |
| `agent.py` | image (stdlib) | `class Session` (context manager: `start()` takes the per-interface flock of §4.4 and raises `RuntimeError` if it is held, `poll() -> (rows, stats)`, `stop()`; `__exit__` always detaches, unpins and releases the lock), `validate_iface(name)`, `main(argv) -> int`. CLI: `--iface` (default `ext0`), `--model {DT,XGB,ALL}` (default ALL, case-insensitive), `--timespan` (s, 1..3600, default 30), `--block-seconds` (default 60), `--model-file` (default `models/kernel_model.json`), `--xdp-mode {skb,native}` (default skb), `--out` (default `outputs/realtime`). Prints one JSON line per new/changed classified flow; writes `<out>/<YYYYmmdd-HHMMSS>_<iface>_<model>.jsonl` and `…_summary.json` |
| `webui.py` | image (stdlib) | `ThreadingHTTPServer`; `GET /` (web/index.html), `GET /api/interfaces` → `{"interfaces": [...], "default": "ext0"}` (mgmt0 excluded), `POST /api/start` `{iface, timespan, model}` → 202 / 400 / 409, `GET /api/flows` → `{running, remaining_s, iface, model, stats, rows}`, `POST /api/stop` → 200. CLI `--host` (default 127.0.0.1), `--port` (8080), `--model` |

**Input validation (trust boundary):** interface ∈ `/sys/class/net` and ≠ `mgmt0`; timespan int in [1, 3600]; model ∈ {DT, XGB, ALL}; block seconds int in [1, 3600]; JSON body ≤ 4 KB. Every subprocess call uses an argument list.

### 5.6 Docker topology (`docker-compose.yml`, project name `lab4`)

| Network | Subnet | Members (IP, interface name) |
|---|---|---|
| `mgmt` | 172.28.0.0/24 | ids 172.28.0.2 (`mgmt0`) |
| `front` | 172.28.1.0/24 | ids 172.28.1.2 (`ext0`), client 172.28.1.20 |
| `back` | 172.28.2.0/24 | ids 172.28.2.2 (`int0`), nginx .10, apache .11, pinger .30 |

| Service | Image | Notes |
|---|---|---|
| `nginx` | `nginx:stable-alpine` | Task 4 |
| `apache` | `httpd:2.4-alpine` | Task 4 |
| `pinger` | `alpine:3` | Task 4, `sleep infinity`; `docker compose exec pinger ping -c 3 nginx` |
| `client` | `alpine:3` | `cap_add: [NET_ADMIN]`; `docker/client_traffic.sh`: `ip route add 172.28.2.0/24 via 172.28.1.2`, then a loop of `wget -q -O /dev/null http://172.28.2.10/` and `…11/`, `sleep ${CLIENT_INTERVAL_S:-1}` (normal traffic only) |
| `ids` | built from `docker/Dockerfile`, tag `lab4-ids:latest` | `privileged: true`, `sysctls: net.ipv4.ip_forward=1`, `interface_name` per network, volumes `./models:/lab4/models:ro`, `./outputs:/lab4/outputs`. Entrypoint `docker/ids_entrypoint.sh`: mount bpffs if needed, `iptables -t nat -A POSTROUTING -o int0 -j MASQUERADE`, then `exec "$@"`. Default CMD `python3 script/webui.py --host 172.28.0.2 --port 8080` |

Image: build stage `python:3.12-slim` + `clang llvm libbpf-dev linux-libc-dev make` → `make -C xdp`; runtime `python:3.12-slim` + `bpftool iproute2 iptables` + `pytest==9.2.0`; copies `script/ web/ tests/ pytest.ini docker/ids_entrypoint.sh` and the BPF object to `/lab4`. The image has **no** numpy/pandas/sklearn.

---

## 6. Layout

```
Lab4/
├── CLAUDE.md  TASKS.md                       # Opus-owned
├── Lab-4.pptx                                # spec (read-only)
├── Friday-WorkingHours-Afternoon-DDos.csv    # copy of the Lab 3 CSV (sha256 §3.2, git-lfs)
├── README.md  run.sh                         # reproduction (slide 12: GitHub link with instructions)
├── requirements.txt  .python-version  .pylintrc  pytest.ini  .gitignore  docker-compose.yml
├── script/   common.py preprocess.py train.py export_model.py kmodel.py bpf_ctl.py flowview.py agent.py webui.py
├── web/      index.html                      # Task 3 page (HTML + CSS + JS, no CDN)
├── xdp/      lab4_common.h  lab4_xdp.bpf.c  Makefile
├── xdp_tools/ task1_demo.sh  README.md  logs/  # Task 1
├── docker/   Dockerfile  ids_entrypoint.sh  client_traffic.sh  task4_check.sh
├── tests/    conftest.py (stdlib only)  fixtures/{sample_ddos.csv, flows_dump.json, stats_dump.json, always_malicious.json}  test_*.py
├── models/   GENERATED, tracked: kernel_model.json  test_vectors.json
├── outputs/  GENERATED, tracked: metrics/  realtime/  task4/  kernel/
└── SS/       screenshots taken by the user (SS_T1_*, SS_T2_*, SS_T3_*, SS_T4_*)
```

`outputs/metrics/`: `preprocess_summary.json depth_selection.json metrics.json comparison_{test,val}.{csv,md} feature_importance.md parity.json parity_mismatches.csv`. `outputs/kernel/`: `kernel_tests.log prog_sizes.txt timing.json`. `outputs/realtime/`: agent JSONL + summaries. `outputs/task4/`: `task4_check.log`.

---

## 7. Commands

Run from `Lab4/`.

```bash
cd /home/aayush/Desktop/SecInsiderLab1/SecInsiderLab-1/Lab4
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt   # once
.venv/bin/python script/train.py                     # clean, split, depth selection, train DT + XGB, export, parity
.venv/bin/pytest -m "not e2e and not kernel and not docker" -q    # unit tests (host, no root)
.venv/bin/pytest -m e2e -q                           # full CSV; pins §3.2
make -C xdp                                          # compile the BPF object on the host (no root)
.venv/bin/pylint script tests && .venv/bin/radon cc -n C script tests   # 10.00/10; radon prints nothing
docker compose build ids
docker run --rm --privileged -v "$PWD/models:/lab4/models:ro" lab4-ids:latest \
    python3 -m pytest tests/test_kernel.py -m kernel -q            # kernel tests (BPF_PROG_TEST_RUN)
docker compose up -d                                 # nginx, apache, pinger, client, ids
bash docker/task4_check.sh                           # Task 4: ping + HTTP from pinger
docker compose exec ids python3 script/agent.py --iface ext0 --model ALL --timespan 30   # Task 2 CLI
xdg-open http://172.28.0.2:8080                      # Task 3 UI (host only)
docker compose down
sudo bash xdp_tools/task1_demo.sh 2>&1 | tee xdp_tools/logs/task1_demo.log   # Task 1 (user, sudo)
```

---

## 8. Code-quality rules

Python: the Lab 3 rules (`../Lab3/CLAUDE.md` §8) apply unchanged:
- McCabe ≤ 10 (radon A–B only)
- pylint 10.00/10 (every disable has a reason comment)
- Google docstrings on every function, method and class
- type hints everywhere
- no magic numbers (constants in `common.py` or module level)
- `pathlib`, `logging` and no `print`, except the agent's JSON lines on stdout, which are its output contract
- modules under about 200 lines

Also:
- **Stdlib-only modules** (`common`, `kmodel`, `bpf_ctl`, `flowview`, `agent`, `webui`, `tests/conftest.py`) never import numpy, pandas, sklearn or xgboost, because the IDS image does not have them. `tests/test_stdlib_only.py` checks the imports.
- C: `-Wall -Werror`. Every function has a comment block (purpose, inputs, return). Every bounds check and every verifier-motivated construct gets a one-line "why" comment. Use `static __always_inline` helpers plus the `bpf_loop` callback, with no global variables except maps.
- Shell: `set -euo pipefail`, a `trap` that cleans up (netns, XDP detach), `shellcheck`-clean if shellcheck is present.
- Unit tests never read the 77 MB CSV (only `@pytest.mark.e2e`). Markers: `e2e` (full CSV), `kernel` (root; IDS image only), `docker` (needs the compose stack).
- No git commits unless the user asks.

---

## 9. Gotchas

- **XDP is ingress-only.** Forward features only; the report must say why Flow Duration and all Bwd features are absent (§4.2).
- **Partial flows.** Flows with < 8 packets and no FIN/RST are never classified (e.g. short UDP). This is a documented limitation; the alternative (bpf_timer idle expiry) is out of scope unless the user asks.
- **Port reuse:** a new connection with the same 5-tuple continues the old flow entry. Rare with ephemeral ports; documented.
- **Flow counters are not atomic** across CPUs; small races are accepted at demo rates.
- **XGBoost** must not use early stopping in Lab 4 (exactly 20 trees go to the kernel). Pass `verbose=False` to `fit`. Read base_score from `save_config()` and convert it to a margin; check with `predict(..., output_margin=True)`.
- **float32:** sklearn and XGBoost compare float32 inputs. Large IAT values (> 2^24 µs) can flip a split in rare cases; the parity step measures this (§5.2).
- **Domain shift:** the models learned the 2017 testbed. Docker-local HTTP has sub-millisecond IATs and tiny busybox GETs. If normal demo flows come out Malicious, the client gets blocked: **stop and report to Opus (T6.4); no ad-hoc threshold or feature changes.**
- **Generic XDP** (`xdpgeneric`) is the default on veth. Native mode on veth needs extra setup; `--xdp-mode native` exists but is not used in the AC.
- `interface_name` in compose needs Engine ≥ 28.1 (29.9.3 here). If `ip -br addr` in the ids container shows `eth0/eth1/eth2`, report to Opus (fallback: rename by IP in the entrypoint).
- **Subnets** 172.28.0–2.0/24 must not collide with existing Docker networks; `docker network ls` in T1.3.
- **Files written by the privileged container are root-owned.** `run.sh` exports `LAB4_UID`/`LAB4_GID`, and the agent `chown`s its outputs to them when set.
- **Kernel tests:** run `tests/test_kernel.py` only (the image cannot import the host-only test modules). Use `docker run`, not `docker compose run`: the fixed IPs would collide with a running stack.
- bpftool `-j map dump` prints BTF-formatted values only if the object has BTF (`-g`). Per-CPU maps dump one value per CPU. The parsers are tested against **captured real dumps** (T4.4), not hand-written JSON.
- Debian's clang does not find `asm/types.h` without `-I/usr/include/$(uname -m)-linux-gnu` (host Ubuntu has it via gcc-multilib). The build stage has no gcc, so the Makefile uses `uname -m`.
- The xgboost Linux wheel pulls `nvidia-nccl-cu13` (about 200 MB); this is harmless on CPU (Lab 3 §9).
- **Task 1 sandbox:** never attach xdp-filter to `enp0s3` (the README warns: "this can lock you out of remote access"). The script uses its own netns and cleans up on exit.
- Haiku's foreground limit is 10 minutes; image builds and the full training run go to the background.

---

## 10. Report, presentation, code submission (deferred until the user asks; `TASKS.md` P9)

- **Report:** `G8.Report4.pdf`, **15–20 pages** (slide 12; slide 3's general 10–15 is superseded), screenshots, "document everything". Due **2026-12-09**. Send to tf@sec.uni-passau.de (slide 12). Slide 3 asks for every report in the **same email thread** (also to aeg@sec.uni-passau.de) with subject `Lab-2026: matriculation ID-1, matriculation ID-2`. The user sends it.
- **Code:** GitHub repo with all labs and **clear reproduction instructions**, due **2026-12-10** (slide 12). Covered by P8 (README, run.sh, root README row). Pushing is the user's decision.
- **Presentation:** **2026-12-16**; 10 min + 2 min discussion; each member presents their own task; standard slide design.
- Numbers rule: every number in the report comes from `outputs/` or `models/kernel_model.json` meta; no hardware statements (Lab 3 rule). Report template and build rule: `../Lab3/report/` (`latexmkrc_2`).

---

## 11. Open points for the user's review

1. O1: exclude Destination Port and Init_Win_bytes_forward? Recommended yes (§4.2.1).
2. O6: ALL = AND (consensus). The alternative is OR (more detections, more false drops).
3. O9: inline-gateway topology. The alternative is a host-network IDS attached to a container's host-side veth (simpler compose, but it exposes host interfaces).
4. O4: depth grids DT {6, 8, 10}, XGB {4, 5, 6} at 20 trees with the "smallest within 0.0005 val F1" rule.
5. The report email recipients differ between slides 3 and 12.
