# TASKS.md: Lab 4 (xdp-tools; in-kernel DT/XGBoost real-time cycle; front-end; Docker)

> **For Opus (orchestrator):** run this plan task by task with one subagent per task, using the routing of CLAUDE.md §1 (superpowers:subagent-driven-development). Steps use checkboxes. **Only Opus ticks boxes**, after checking the AC. **Task work starts only when the user prompts** (plan-review gate).

**Goal:** a reproducible Lab 4 with four parts:
- Task 1: xdp-tools (xdp-filter, xdpdump) installed and demonstrated.
- Task 2: a real-time cycle whose capture, flowmeter, DT/XGBoost classifier (`--model DT|XGB|ALL`) and filter all run **inside one XDP program** (slide 9, Best case).
- Task 3: a sample-style web front-end.
- Task 4: Docker Nginx/Apache/ping, all orchestrated with Docker Compose.

**Architecture:**
- Offline (host venv): trees are trained on 10 forward-direction CIC-IDS2017 features and exported to integer node tables.
- Kernel: `xdp/lab4_xdp.bpf.c` walks the trees from BPF maps per flow and blocks Malicious sources with `XDP_DROP`.
- User space: bpftool (load, maps, attach, dumps) plus a stdlib Python agent and UI, inside a privileged IDS container. That container is the inline gateway between a normal-traffic client and the Nginx/Apache servers.

**Tech stack:** Python 3.12 (uv), pandas/numpy/scikit-learn/XGBoost (host only); C eBPF (clang, libbpf headers, `bpf_loop`); bpftool; xdp-tools v1.6.3-32; Docker 29.9.3 + Compose 5.7.1; stdlib `http.server` with a single HTML page.

**Spec:** `Lab-4.pptx` slides 7–12 and CLAUDE.md §2 (user decisions D1–D6, Opus decisions O1–O13). Contracts are in CLAUDE.md §5; read them before any [S] task.

Legend: **[O]** Opus 5.5 · **[S]** Sonnet 5.5 (code, tests, docs) · **[H]** Haiku 5.5 (commands, runs, inventory) · **[U]** the user (host sudo, screenshots, decisions). Commands run from `Lab4/` unless a task says otherwise.

---

## Global constraints (every task implicitly includes these)

- Python **3.12** via uv (`.python-version`); never the system 3.14. Pins as Lab 3: numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, xgboost 3.4.1, tabulate 0.10.0, pylint 4.1.3, pytest 9.2.0, radon 6.0.1. No torch, no matplotlib (nothing in Lab 4 needs them).
- Kernel ≥ 5.17 (`bpf_loop`); this machine runs 7.0.0-43. BPF objects carry BTF (`-g`). XDP mode default `skb` (generic).
- Models: Decision Tree and XGBoost only. `--model` ∈ {DT, XGB, ALL}; ALL = both in the kernel, final verdict = DT AND XGB. XGBoost has exactly 20 trees.
- Kernel feature list, units and order: CLAUDE.md §5.1. Threshold rules: §5.2. C structs, maps and constants: §5.3. Python APIs: §5.5. Compose topology: §5.6. These are contracts: do not rename.
- Quality (CLAUDE.md §8): McCabe ≤ 10, pylint 10.00/10, docstrings + type hints, logging, no magic numbers; stdlib-only modules stay stdlib-only; C `-Wall -Werror` and commented; shell `set -euo pipefail` with cleanup traps.
- Lab 4 never imports from Lab 2/Lab 3 (port and name the source).
- **No attack tools** (slide 8); live traffic is normal `wget` traffic only.
- Security: the UI binds to the mgmt IP only; every input is validated (CLAUDE.md §5.5); subprocesses use argument lists (never `shell=True`); XDP never on `enp0s3`.
- Agents never use sudo; host root steps are [U]. Privileged Docker is allowed (user in group `docker`).
- No git commits or pushes unless the user asks.

**Quality gate (every [S] code task):** pylint 10.00/10 and `radon cc -n C` empty on the touched Python files; `make -C xdp` warning-free when C is touched; every function documented; the task's tests pass; the stdlib-only check passes.

---

## Review focus (failure modes the spec implies but a happy-path test would miss; each has a test in its owning task)

1. **Normal live traffic classified Malicious → the filter drops the legitimate client** (domain shift: Docker-local sub-ms IATs, tiny busybox GETs). Expected: normal flows are Normal and the client's request success stays 100 %. Pinned by `test_docker.py::test_agent_normal_traffic_not_blocked` (T6.1), with an Opus gate in T6.4.
2. **Malformed or unsupported packets** (truncated frame, IHL < 5, TCP doff < 5, IPv4 fragment, ARP, IPv6, ICMP, VLAN) must pass untouched, create no flow and never be dropped. Pinned by `test_kernel.py::test_not_tracked_pass` (T4.3).
3. **Stale kernel state:** an agent crash or kill or Ctrl-C leaves XDP attached and blocks active; a second start attaches over an old program. Expected: detach and unpin always run; start removes a stale program. Pinned by `test_agent.py::test_session_cleans_up_on_error` and `test_docker.py::test_agent_short_run` (no XDP left on `ext0`) (T5.1, T6.1).
4. **Untrusted UI input:** interface names like `../x`, `eth0;rm`, `mgmt0`, timespan 0 / 3601 / "abc", model "RF", oversized bodies, a second start while running. Expected: 400/409/413 and no subprocess call. Pinned by `test_webui.py::test_start_rejects_bad_input` (T5.2).
5. **Integer/float disagreement at split thresholds** (≤ vs <, float32 inputs > 2^24, milli-unit means). Expected: DT parity 100 %, XGB ≥ 99.99 % with the mismatches listed, kernel == Python exactly. Pinned by `test_export_model.py::test_threshold_conversion_le_vs_lt`, `train.py` parity (T3.4/T3.5) and `test_kernel.py::test_kernel_parity` (T4.3).

---

## Order and parallelism

```
P0 ─▶ P1 (T1.1 [U] ─▶ T1.2 [H];  T1.3 [S] ─▶ T1.4 [H])
       ├─▶ P2 Task 1 (needs T1.2)
       ├─▶ P3 models (needs T1.4) ─▶ T3.5 [H] ─▶ T3.6 [O] gate
       └─▶ T4.1, T4.2 (need T1.3; run beside P3) ─▶ T4.3 (needs T3.5 models) ─▶ T4.4 [H] ─▶ T4.5 [O]
P5 (needs T4.4 dump fixtures) ─▶ P6 (needs P5) ─▶ P7 ─▶ P8 ;  P9 deferred
```

---

## P0: Planning

- [x] **T0.1 [O + H] Analyse the spec.** [H] extracted all 12 slides of `Lab-4.pptx` (no notes) and rendered them; Opus viewed slides 7–11 (slide 10 = sample UI screenshot). *AC:* CLAUDE.md §2 filled. Done 2026-11-25.
- [x] **T0.2 [H] Prerequisite check (D4).** XDP toolchain, xdp-tools, Docker, Python, bpffs, BPF sysctls, git-lfs. Result in CLAUDE.md §3.1: **xdp-tools built but not installed**; Lab 3's "ALL CHECKS PASSED" log came from the partner's machine. Done 2026-11-25.
- [x] **T0.3 [O] Write `CLAUDE.md` and `TASKS.md`.** *AC:* every user instruction of 2026-11-25 (D1–D6) is in CLAUDE.md §2 and maps to at least one task. Done 2026-11-25.
- [x] **T0.4 [U] Review** (2026-11-25: user said "start working"; §11 defaults accepted) both files and answer CLAUDE.md §11 (O1, O4, O6, O9, emails). Opus applies changes, then waits for the go-ahead.

---

## P1: Prerequisites and environment

- [x] **T1.1 [U] Install xdp-tools on the host** (the build from 2026-11-15 is in `~/src/xdp-tools`, v1.6.3-32-g92a9828):
  ```bash
  cd ~/src/xdp-tools
  make                      # no root; should report nothing to do
  sudo make install         # xdp-loader, xdp-filter, xdpdump, xdp-bench, ... → /usr/local/sbin; libxdp → /usr/local/lib; BPF objects → /usr/local/lib/bpf
  sudo ldconfig
  ```
  Do **not** apt-install `xdp-tools` or `libxdp-dev` (two copies on PATH would conflict). Nothing else is needed on the host: Lab 4's BPF build and runtime live in the IDS image.
- [ ] **T1.2 [H → U] Verify the install**, appending to `xdp_tools/logs/install_verify.log` with `tee -a`: `command -v xdp-loader xdp-filter xdpdump xdp-bench`; `xdp-filter help | head -5`; `xdpdump --version`; `ls /usr/local/lib/bpf | head`; `ldconfig -p | grep libxdp`; `PKG_CONFIG_PATH=/usr/local/lib/pkgconfig pkg-config --modversion libxdp`. Then [U] runs `sudo xdp-loader status | tee -a xdp_tools/logs/install_verify.log` and `sudo xdp-loader features lo | tee -a …`.

  *AC:* all four binaries resolve to `/usr/local/sbin`; libxdp is in the ldconfig cache; `/usr/local/lib/bpf` holds the xdp-filter objects; `xdp-loader status` lists `lo`, `enp0s3`, `docker0` with no program.
- [x] **T1.3 [S] Project config files.** (2026-11-25; collect rc 5, no warnings)
  - `requirements.txt`: the pins of the global constraints, grouped with comments, plus a header with the uv commands. No torch, so no `--torch-backend`.
  - `.python-version` = `3.12`.
  - `.pylintrc`: copy Lab 3's `.pylintrc` without the torch and `max-attributes` lines; `source-roots=script`, `recursive=yes`; every disable has a reason comment.
  - `pytest.ini`: `pythonpath = script`, `testpaths = tests`, markers `e2e`, `kernel`, `docker` with one-line descriptions.
  - `.gitignore`: `.venv/ __pycache__/ *.py[cod] .pytest_cache/ outputs_*/ xdp/*.o .~lock.*#` (`outputs/` and `models/` stay tracked).
  - `.dockerignore`: `.venv outputs* models *.csv SS report .pytest_cache **/__pycache__`.

  *AC:* `.venv/bin/pytest --collect-only -q` exits 0 or 5 with no config or marker warnings (checked after T1.4).
- [x] **T1.4 [H] Environment and data.** (2026-11-25; all AC pass; digests in CLAUDE.md §3.1)
  1. `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt && uv pip freeze --python .venv/bin/python`.
  2. `cp ../Lab3/Friday-WorkingHours-Afternoon-DDos.csv .` and `mkdir -p tests/fixtures && cp ../Lab3/tests/fixtures/sample_ddos.csv tests/fixtures/`; `sha256sum` both (must equal CLAUDE.md §3.2).
  3. `cat ../.gitattributes` and `git check-attr filter -- Lab4/Friday-WorkingHours-Afternoon-DDos.csv` (report whether git-lfs covers the Lab 4 copy; [O] decides).
  4. `docker pull nginx:stable-alpine httpd:2.4-alpine alpine:3 python:3.12-slim` and `docker image inspect --format '{{.RepoDigests}}'` for each.
  5. `docker network ls` and `docker network inspect $(docker network ls -q) --format '{{.Name}} {{range .IPAM.Config}}{{.Subnet}}{{end}}'` (no 172.28.0–2.0/24 conflicts).
  6. Privileged smoke test: `docker run --rm --privileged alpine:3 sh -c 'mount -t bpf bpf /sys/fs/bpf && echo BPFFS_OK'`.

  *AC:* the freeze shows the pins; both sha256 values match; the 4 images are pulled with digests recorded; no subnet conflict; `BPFFS_OK` is printed. [O] records the digests and the lfs result in CLAUDE.md §3.1.

---

## P2: Task 1, xdp-tools (xdp-filter, xdpdump)

- [x] **T2.1 [S] `xdp_tools/task1_demo.sh` and `xdp_tools/README.md`.**

  **Files:** create `xdp_tools/task1_demo.sh`, `xdp_tools/README.md`.

  The script:
  - exits 1 with "Run as root: sudo $0" when not root;
  - uses `set -euo pipefail`;
  - creates the sandbox netns `lab4t1` with a veth pair `t1-host` (10.10.0.1/24, host) ↔ `t1-ns` (10.10.0.2/24, in the netns);
  - installs a `trap` that runs `xdp-filter unload t1-host`, kills the HTTP server and deletes the netns on every exit;
  - prints a banner `== N. title ==` per section and echoes each command before running it;
  - lets the steps marked "expected to fail" fail without aborting.

  Sections (all commands are the README.org forms from `~/src/xdp-tools/xdp-filter/README.org` and `xdp-dump/README.org`, interface swapped for `t1-host`):
  1. `xdpdump -D` (nothing loaded).
  2. `xdp-filter load --mode skb t1-host`, then `xdpdump -D` (dispatcher + `xdpfilt_alw_all`).
  3. `ip netns exec lab4t1 ping -c 3 10.10.0.1` (0 % loss).
  4. `xdp-filter ip 10.10.0.2 -m src`; ping again (**expected to fail**, 100 % loss); `xdp-filter status` (shows the IP and hit counters).
  5. `timeout 8 xdpdump -i t1-host --rx-capture=entry,exit` while the ping runs in the background (shows the exit action `XDP_DROP`); then `xdp-filter ip 10.10.0.2 -m src -r` and ping (0 % loss).
  6. Port filter: `python3 -m http.server 8000 --bind 10.10.0.1` in the background; `ip netns exec lab4t1 python3 -c` (urllib GET with a 3 s timeout) gives 200; `xdp-filter port 8000`; GET again (**expected to fail**, timeout); `xdp-filter status`; `xdp-filter port 8000 -r`; GET gives 200.
  7. `timeout 6 xdpdump -i t1-host -x` while pinging (hex dump).
  8. `timeout 6 xdpdump -i t1-host -w - | tcpdump -r - -n` while pinging.
  9. `timeout 5 xdp-filter poll -i 1000`.
  10. `xdp-filter unload t1-host`; `xdpdump -D` (nothing loaded).

  `README.md`: the install (T1.1) with versions, the sandbox, one paragraph per section saying what it demonstrates and the expected output, and the screenshot list `SS_T1_1 … SS_T1_10` (one per section).

  *Checks (Sonnet):* `bash -n`; `shellcheck` if installed; running it without root prints the message and exits 1.

  *AC:* the quality gate for shell passes; every command is a README.org form; cleanup runs on success and on failure.
- [x] **T2.2 [U] Run Task 1.** `sudo bash xdp_tools/task1_demo.sh 2>&1 | tee xdp_tools/logs/task1_demo.log`; take the screenshots `SS/SS_T1_*.png`.
- [x] **T2.3 [O] Review the log.** (2026-11-26, re-run after the fixes: all 10 sections as expected; poll shows 5 periods; HTTP 200 → timeout → 200)

  *AC:*
  - section 3 shows 0 % loss and section 4 100 % loss;
  - `xdp-filter status` shows the src IP and port entries with non-zero hits;
  - section 5 shows `XDP_DROP` at exit;
  - HTTP returns 200, then times out, then returns 200;
  - xdpdump captures packets (> 0);
  - the last `xdpdump -D` shows no program;
  - afterwards `ip netns list` does not contain `lab4t1`.

---

## P3: Task 2 offline: training the kernel models

- [x] **T3.1 [S] `script/common.py`, `script/preprocess.py`, conftest and tests.**

  **Files:** create `script/common.py`, `script/preprocess.py`, `tests/conftest.py`, `tests/test_preprocess.py`, `tests/test_stdlib_only.py`.

  **Interfaces:** produces everything in CLAUDE.md §5.5 for `common` and `preprocess`. The `KERNEL_FEATURES` order is §5.1. The cleaning is ported from `../Lab3/script/preprocess.py`.

  Tests (port the Lab 3 cleaning tests from `../Lab3/tests/test_preprocess.py`, then add):
  - `test_select_kernel_features_order`: the columns equal `[n for n, _ in common.KERNEL_FEATURES]`.
  - `test_select_kernel_features_missing_raises`: dropping `act_data_pkt_fwd` raises `KeyError` whose message contains that name.
  - `test_split_sizes_stratified_disjoint`: 70/15/15 ±1 row, class ratio within 1 pp, disjoint indices.
  - `test_no_scaling`: `x_train` equals the selected cleaned values (float64, unscaled).
  - `test_preprocess_fixture`: on `tests/fixtures/sample_ddos.csv`, there is no inf/NaN, `y ⊆ {0, 1}`, `feature_names` has the 10 names, and `json.dumps(summary)` succeeds.
  - `test_stdlib_only`: AST-parse `common`, `kmodel`, `bpf_ctl`, `flowview`, `agent`, `webui` and `tests/conftest.py` (the ones that exist); none imports numpy, pandas, sklearn or xgboost.

  `tests/conftest.py` (stdlib only): the fixture CSV path and `always_malicious.json` path. Numpy fixtures live in the test modules that need them.

  *AC:* the quality gate passes; the tests run in under 30 s.
- [x] **T3.2 [S] `script/kmodel.py` (stdlib integer model) and tests.**

  **Interfaces:** CLAUDE.md §5.4 and §5.5 (`kmodel`). The batch line format is `map update pinned <pin_dir>/maps/<map> key hex <4 bytes LE> value hex <bytes>` with bytes as lowercase two-digit hex separated by spaces; `roots` values are `<I`, the `config` value is `<IIqQ` (24 B).

  Also create `tests/fixtures/always_malicious.json` (CLAUDE.md §5.4).

  Tests (`tests/test_kmodel.py`):
  - `test_walk_hand_tree`: root `[2, 5, 1, 2, 0]`, leaves `[-1,0,0,0,0]`, `[-1,0,0,0,1]`; `x[2]=5` → 0, `x[2]=6` → 1.
  - `test_pack_node_is_24_bytes_and_roundtrips`.
  - `test_validate_rejects` (parametrised): `MAX_NODES + 1` nodes, depth 11, feature 10, child out of range, `MAX_TREES + 1` roots → `ValueError`.
  - `test_xgb_margin_sums_base_and_leaves`; `test_xgb_verdict_zero_is_normal` (margin 0 → 0, 1 → 1).
  - `test_final_verdict_modes`: the DT, XGB and ALL (AND) truth table.
  - `test_batch_lines_format`: line count = n_nodes + 1 + n_xgb_trees; the first line matches the format exactly; `config_line` decodes back to (mode, n_trees, base_margin, block_ns).
  - `test_load_save_roundtrip`; `test_always_malicious_fixture` validates, and DT and XGB verdicts are 1 for any x.

  *AC:* the quality gate passes; the module is stdlib-only.
- [x] **T3.3 [S] `script/export_model.py` and tests.**

  **Interfaces:**
  - consumes `kmodel` (T3.2) and `common.KERNEL_FEATURES`;
  - produces the §5.5 `export_model` API, following the §5.2 rules exactly.
  - XGB trees come from `booster.get_dump(dump_format="json")` (or `trees_to_dataframe()`). Node indices are made absolute after the DT nodes. A missing-value direction is ignored, because kernel features are never missing.

  Tests (`tests/test_export_model.py`; synthetic integer-valued data from `make_classification`, scaled and rounded to kernel-unit-compatible values):
  - `test_to_int_features_floor_and_scale`.
  - `test_threshold_conversion_le_vs_lt`: DT t=5.5,s=1 → T=5; XGB t=5.0,s=1 → T=4 (x=5 goes right); XGB t=5.5 → T=5; s=1000, t=0.0015 → DT T=1, XGB T=1.
  - `test_export_dt_matches_sklearn`: 100 % verdict agreement with `predict` on 2,000 synthetic rows.
  - `test_export_xgb_matches_margin`: `|margin_int / 2**16 − predict(output_margin=True)| ≤ 1e-3` and verdicts equal on every row.
  - `test_base_margin_parsing`: `"[5.6E-1]"` and `"0.56"` both give `logit(0.56)`.
  - `test_sample_test_vectors_balanced`: n = min(512, class count) per class; the stored dt/margin values equal the `kmodel` evaluation.
  - `test_parity_lists_mismatches`: a forced flip appears in the mismatch rows.

  *AC:* the quality gate passes.
- [x] **T3.4 [S] `script/train.py` and tests.**

  **Interfaces:**
  - consumes `preprocess.preprocess`, `export_model.*`, `kmodel.save`, `kmodel.validate`;
  - produces `models/kernel_model.json`, `models/test_vectors.json` and the `outputs/metrics/*` files of CLAUDE.md §6.

  `main` order:
  1. `setup_logging(out)`.
  2. `preprocess` → `preprocess_summary.json`.
  3. Fit DT for each of `DT_DEPTHS` and XGB for each of `XGB_DEPTHS`; score val F1; `select_depth` → `depth_selection.json` (every candidate's val F1, the chosen depth).
  4. Evaluate the two selected models on val and test (float) → `metrics.json`, `comparison_{test,val}.{csv,md}` (Lab 3 columns: Model, Accuracy, Precision, Recall, F1, Macro-F1, ROC-AUC, TP, TN, FP, FN, Train time (s), Predict time (s)).
  5. `feature_importance.md` (DT `feature_importances_`, XGB gain).
  6. Export → `kmodel.validate` → save `kernel_model.json` (meta incl. CSV sha256).
  7. Parity on all test rows → `parity.json` (+ `parity_mismatches.csv`) plus integer-model metrics.
  8. `test_vectors.json`.
  9. Log the test table; return 0.

  The test set is evaluated only after the depths are fixed.

  Tests (`tests/test_train.py`):
  - `test_compute_metrics_hand_checked` (port Lab 3's 10-sample case; score 0.5 → BENIGN).
  - `test_select_depth`: {4: .9990, 5: .9994, 6: .9995} → 4; {4: .9900, 5: .9994, 6: .9995} → 5; exact ties → the smallest.
  - `test_fit_xgb_exactly_20_trees`: `num_boosted_rounds() == 20` and no `best_iteration`.
  - `test_fit_dt_respects_depth`.
  - `test_main_smoke`: `main(["--csv", fixture, "--out", tmp, "--models-dir", tmp/"models"]) == 0`; every listed file exists; `kernel_model.json` validates.

  Also `tests/test_e2e.py` (`@pytest.mark.e2e`): `preprocess` on the full CSV reproduces CLAUDE.md §3.2 (raw, clean and split counts per class) and the 10 kernel features exist.

  *AC:* the quality gate passes; the non-e2e suite runs in under 60 s.
- [x] **T3.5 [H] Full training run.** Run `time .venv/bin/python script/train.py` (in the background if it may exceed 10 min), then `.venv/bin/pytest -m e2e -q`. Paste verbatim: the wall time, `outputs/metrics/{depth_selection.json, comparison_test.md, comparison_val.md, parity.json, feature_importance.md}`, `head -5 outputs/metrics/parity_mismatches.csv` and `python3 -c` printing `kernel_model.json` meta.

  *AC:* exit 0; e2e passes; the files exist.
- [x] **T3.6 [O] Gate review.**
  - Feasibility (CLAUDE.md §4.3.4): the selected DT and XGB have test F1 ≥ 0.99, or else **stop and ask the user**.
  - Parity AC (§5.2) holds.
  - Node count ≤ `MAX_NODES`, depth ≤ `MAX_TREE_DEPTH`.
  - The val/test gap is small.
  - The depth choice follows the rule.
  - Record the numbers in CLAUDE.md §3 (new §3.4) and the review log.

---

## P4: Task 2 kernel: the XDP program and its tests

- [x] **T4.1 [S] `xdp/lab4_common.h`, `xdp/lab4_xdp.bpf.c`, `xdp/Makefile`, consistency and build tests.**

  **Interfaces:** exactly CLAUDE.md §5.3. Programs `xdp_ids` and `classify_test`.

  `xdp_ids` algorithm (pinned; the rest is the implementer's choice):
  1. Parse Ethernet → IPv4 (`ihl ≥ 5`, no fragment: `frag_off & 0x3FFF == 0`) → TCP (`doff ≥ 5`) or UDP. Every pointer is bounds-checked against `data_end`; payload = `tot_len − ihl·4 − l4len`, and a negative payload means "not tracked". Anything else is not tracked: `ST_NOT_TRACKED++`, `ST_PASS++`, `XDP_PASS`.
  2. `ST_PKTS++`.
  3. `blocklist[saddr]`: if expiry > now → `ST_DROP++`, `XDP_DROP`; if expired → delete it.
  4. Look up the flow; if it is missing, insert an initialised state with `BPF_NOEXIST` and look up again. Update it: IAT (second packet sets min = max = iat; later packets update min/max), pkts, bytes, len min/max, act_data, last_ns, OR of the TCP flags.
  5. `config[0]`: if `mode == MODE_OFF` or not (FIN/RST on this packet, or `pkts ≥ CLASSIFY_MIN_PKTS` and pkts is a power of two) → `ST_PASS++`, `XDP_PASS`.
  6. Build `x[N_FEATURES]` (§5.1) and classify by mode (DT walk / XGB `bpf_loop` sum / both with AND); the unused model's verdict is `V_NONE`; store the verdicts, margin and `classified_ns = now`; `ST_FLOWS_CLASSIFIED++` (counts classification events).
  7. Malicious → `blocklist[saddr] = now + block_ns`, `ST_BLOCKS_ADDED++`, `ST_FLOWS_MALICIOUS++`, `ST_DROP++`, `XDP_DROP`; else `ST_PASS++`, `XDP_PASS`.

  `Makefile`: target `lab4_xdp.bpf.o` with the CLAUDE.md §5.3 flags, plus `clean`.

  Tests:
  - `tests/test_consistency.py` parses `#define` and enum values from the header and compares them with `common.py`.
  - `tests/test_bpf_build.py` (skipped if clang/bpftool are missing): `make -C xdp` exits 0 with no warnings; `bpftool btf dump file xdp/lab4_xdp.bpf.o` shows sizes 24/24/16/80/16 for `tree_node`, `ids_config`, `flow_key`, `test_vec`, `test_result`; `llvm-objdump -h` lists the `xdp` sections.

  *AC:* the quality gate passes. Verifier acceptance is checked in T4.4.
- [x] **T4.2 [S] `script/bpf_ctl.py` and tests.**

  **Interfaces:** CLAUDE.md §5.5 (`bpf_ctl`). Exact commands:
  - `bpftool prog loadall <obj> <pin>/progs type xdp pinmaps <pin>/maps`
  - `bpftool batch file <tmp>`
  - `bpftool net detach xdpgeneric dev <if>` (errors ignored when nothing is attached)
  - `bpftool net attach xdpgeneric|xdpdrv pinned <pin>/progs/xdp_ids dev <if>`
  - `bpftool -j map dump pinned <pin>/maps/<name>`
  - `bpftool -j prog run pinned <pin>/progs/<prog> data_in <tmp> repeat <n>`
  - unpin = `rm -rf <pin>` after a `<pin>` prefix sanity check.

  A failed command raises `RuntimeError` with the command and its stderr.

  Tests (`tests/test_bpf_ctl.py`, `subprocess.run` monkeypatched): the exact argument lists for each call; no `shell=True`; `dump` returns the parsed JSON list; `prog_run` returns (retval, duration); a non-zero exit raises; `unpin` refuses paths outside `/sys/fs/bpf/`.

  The JSON key names of `prog run` are confirmed against real output in T4.4 (fix them there if they differ).

  *AC:* the quality gate passes.
- [x] **T4.3 [S] IDS image and kernel tests.**

  **Files:**
  - `docker/Dockerfile`, `docker/ids_entrypoint.sh` (CLAUDE.md §5.6);
  - `tests/pktgen.py` (stdlib frame builder: Ethernet/IPv4/TCP/UDP/ICMP, ARP, IPv6, with options for flags, payload, fragment, ihl, doff and truncation);
  - `tests/test_kernel.py` (all tests `@pytest.mark.kernel`; a module fixture loads the object into a fresh pin dir per test and unpins afterwards).

  Tests:
  - `test_flowmeter_tcp_fin`: an always-Normal model (DT leaf 0) in DT mode. Packets 10.0.0.2:40000 → 10.0.0.1:80: SYN (0 B), PSH/ACK (100 B), ACK (50 B), FIN/ACK (0 B). All return `XDP_PASS` (2); the flow has pkts 4, bytes 150, len_max 100, len_min 0, act_data_pkts 2, `0 ≤ iat_min_ns ≤ iat_max_ns ≤ last_ns − first_ns`, `classified_ns > 0`, verdict 0.
  - `test_classify_trigger`: a UDP flow without FIN has `classified_ns == 0` after 7 packets and `> 0` after 8.
  - `test_filter_blocks_after_malicious`: `always_malicious.json`, DT mode, block 60 s. The FIN packet returns `XDP_DROP` (1); `blocklist` holds 10.0.0.2; the next packet from 10.0.0.2 is DROP; 10.0.0.3 is PASS; the stats have DROP 2 and BLOCKS_ADDED 1.
  - `test_block_expiry`: block_ns 1 ms; after the drop, sleep 50 ms; the next packet is PASS and the blocklist entry is gone.
  - `test_mode_all_requires_both`: DT leaf 1 with XGB margin < 0. ALL mode gives verdict 0 and no block; DT mode blocks.
  - `test_mode_off`: a zero config; the FIN packet is PASS and `classified_ns == 0`.
  - `test_not_tracked_pass` (parametrised): ARP, IPv6, ICMP, IPv4 with the MF flag, a 20-byte frame, ihl 4, doff 4, an 802.1Q frame → PASS, no flow entry, and ST_NOT_TRACKED rises by one each.
  - `test_kernel_parity`: `models/kernel_model.json` + `test_vectors.json` (skipped with a reason if absent). Batch-load `test_vecs`, set `test_idx` 0, `prog run classify_test repeat n`, dump `test_results`: every DT verdict and XGB margin **equals** the JSON (exact integers).
  - `test_record_evidence`: writes `outputs/kernel/timing.json` (avg ns per run of `xdp_ids`, `repeat 100000`, for a mid-flow packet in modes DT, XGB, ALL, a classifying FIN packet in each mode, and a not-tracked packet), `outputs/kernel/prog_sizes.json` (`bpftool -j prog show pinned …`: xlated and jited bytes) and the raw `flows_dump.json` / `stats_dump.json` captured after `test_flowmeter_tcp_fin`'s packets.

  *AC:* the quality gate passes; `docker compose build ids` (or `docker build -f docker/Dockerfile -t lab4-ids:latest .`) succeeds locally if Sonnet tries it.
- [x] **T4.4 [H] Build and run the kernel tests.**
  - `docker build -f docker/Dockerfile -t lab4-ids:latest .` (background if long).
  - `docker run --rm --privileged -v "$PWD/models:/lab4/models:ro" -v "$PWD/outputs:/lab4/outputs" lab4-ids:latest python3 -m pytest tests/test_kernel.py -m kernel -v 2>&1 | tee outputs/kernel/kernel_tests.log`.
  - Paste verbatim: the test log, `outputs/kernel/timing.json`, `prog_sizes.json`, the first 60 lines of `flows_dump.json` and of `stats_dump.json`.
  - On a verifier error, paste the full verifier log (route the fix to [S]).

  *AC:* all kernel tests pass (parity exact); the evidence files exist.
- [x] **T4.5 [O] Review.** The verifier accepts both programs. Parity is exact. Timing is plausible (not-tracked < mid-flow < classifying FIN; DT < XGB ≤ ALL). The sizes are recorded in CLAUDE.md §3 and the review log. bpftool JSON keys match `bpf_ctl` (or there is a fix task).

---

## P5: Tasks 2–3 user space: agent and front-end

- [x] **T5.1 [S] `script/flowview.py`, `script/agent.py` and tests.**

  **Files:** also copy `outputs/kernel/flows_dump.json` and `stats_dump.json` (from T4.4) to `tests/fixtures/`.

  **Interfaces:** consumes `bpf_ctl`, `kmodel.batch_lines`, `kmodel.config_line`; produces the §5.5 `flowview` and `agent` APIs.

  `Session.start` order: `unpin` (stale) → `load` → `batch(model lines)` → `batch([config line])` → `detach` (stale) → `attach`. `stop`/`__exit__`: `detach` → `unpin`. The CLI polls every `POLL_INTERVAL_S` until the timespan ends or SIGINT/SIGTERM.

  Tests:
  - `tests/test_flowview.py` on the real fixtures: dotted-quad IPs (10.0.0.2 → 10.0.0.1), ports 40000/80, `result` ∈ {Normal, Malicious}, `models` strings per mode (`"DT: Normal"`, `"XGB: Malicious"`, `"DT: Normal · XGB: Normal"`), the timestamp matches `TIMESTAMP_FMT`, unclassified flows are excluded, `parse_stats` sums the per-CPU values.
  - `tests/test_agent.py` (fake `bpf_ctl` recording calls):
    - `test_session_call_order`;
    - `test_session_cleans_up_on_error` (an exception in `poll` still leads to detach + unpin + lock release);
    - `test_second_session_same_iface_fails` (the lock is held → `RuntimeError`; a lock path in `tmp_path` is monkeypatched);
    - `test_validate_iface` (rejects `mgmt0`, unknown names, `../x`, names with spaces or `;`);
    - `test_cli_model_case_insensitive` (`--model xgb` → XGB) and bounds for timespan/block seconds;
    - `test_jsonl_one_line_per_new_or_changed_flow`;
    - `test_summary_keys` ({iface, model, timespan_s, started, ended, stats, flows_classified, flows_malicious});
    - `test_chown_when_env_set`.

  *AC:* the quality gate passes; both modules are stdlib-only.
- [x] **T5.2 [S] `script/webui.py` and `web/index.html` (Task 3) and tests.** First load the `modern-web-guidance` skill (mandatory for HTML/CSS/JS work).

  **Interfaces:** consumes `agent.Session`, `agent.validate_iface`, `flowview`; produces the §5.5 `webui` routes. One session at a time in a daemon thread; `rows` newest first, capped at 500.

  The page reproduces the slide-10 sample:
  - dark theme;
  - labelled controls "Available Local Interfaces" (select, default `ext0`), "Enter Timespan" (seconds, 1–3600), "Model" (DT/XGB/ALL, default from `--model`), buttons "Start Packet Capture" and "Stop";
  - a status line (running, remaining s, packets, dropped, classifications, malicious, blocks);
  - an "Algorithm Output" table with Src IP, Src Port, Dst IP, Dst Port, Timestamp, Result, Models, with Malicious rows highlighted;
  - polls `/api/flows` every second;
  - no external resources;
  - element ids `iface`, `timespan`, `model`, `start`, `stop`, `status`, `flows`.

  Tests (`tests/test_webui.py`; server on port 0 in a thread, `urllib`, fake `Session`):
  - `test_index_has_controls_and_columns` (ids and header order);
  - `test_interfaces_excludes_mgmt`;
  - `test_start_rejects_bad_input` (parametrised: iface `../x`, `eth0;rm`, `mgmt0`; timespan 0, 3601, "abc"; model "RF"; missing keys → 400; body > 4 KB → 413);
  - `test_start_accepts_and_passes_args` (202; the fake got the exact values);
  - `test_second_start_conflicts` (409);
  - `test_flows_shape`; `test_stop`;
  - `test_binds_given_host_only`.

  *AC:* the quality gate passes; the page renders in a browser with the sample's layout (checked by Opus from a [H] screenshot in T6.3).

- [x] **T5.3 [S] Dataset replay into the live kernel program (D8).**

  **Files:**
  - Create `script/pktbuild.py` (stdlib frame builder, moved from `tests/pktgen.py`; tests import it from there) and `script/replay.py`.
  - Edit `script/train.py` (write `models/replay_flows.json`), `script/agent.py` (`--replay N`, 0..100, default 0; `Session.replay(flows)`), `script/webui.py` (`replay` field 0..100, default 20) and `web/index.html` (number input "Replay dataset flows" plus a one-line note that replayed flows come from the CIC-IDS2017 test split).
  - Tests: `tests/test_replay.py`, `tests/test_kernel.py::test_replay_through_xdp_ids`. Docs: `USER_COMMANDS_RUN.md`, `REALTIME.md`, `README.md`.

  **Interfaces:**
  - `replay.payloads_from_row(row: dict) -> list[int] | None`: returns None when the row is not exactly rebuildable.
  - `replay.build_pool(df, y, per_class=500, max_pkts=32) -> list[dict]`.
  - `replay.sample(pool, n, rng) -> list[dict]`: n/2 of each class, shuffled.
  - `replay.frames(flow, src_ip, sport) -> list[bytes]`.
  - `replay.run(pin, flows, rng) -> list[dict]` returns `{src_ip, sport, label, retvals}`; it uses `bpf_ctl.prog_run("xdp_ids", pin, frame)`.
  - Ground truth goes to `<out>/<stamp>_replay.json` (agent) and to the `/api/flows` payload key `replay` (webui).

  Tests:
  - `payloads_from_row` reproduces the 6 packet features exactly for a hand row and returns None for an infeasible one.
  - `sample` is balanced and has no duplicates.
  - The agent and webui validate `replay` bounds (400 on -1, 101, "x").
  - Kernel: replaying 4 flows (2 per class) with the real model creates 4 classified flows from 10.99.x.y in the `flows` map, and the blocklist holds only 10.99.x.y addresses.

  *AC:* the quality gate passes; the kernel suite passes; the docs say IATs are not reproduced and no attack tool is used.
- [x] **T5.4 [H] Verify D8 live:**
  - rebuild the image; run the kernel tests;
  - `docker compose up -d --build`;
  - POST `/api/start` with `{"iface":"ext0","timespan":30,"model":"ALL","replay":24}`, wait 35 s, GET `/api/flows`;
  - report the row count, Normal/Malicious counts, how many replayed flows of each label were classified Malicious, and that the client logged 0 FAIL;
  - then `docker compose down --rmi all --volumes --remove-orphans` and `docker rmi python:3.12-slim`.

  *AC:* ≥ 20 rows with both results present; the client is unaffected.

---

## P6: Task 4 and the live cycle in Docker

- [x] **T6.1 [S] `docker-compose.yml`, `docker/client_traffic.sh`, `docker/task4_check.sh`, `tests/test_docker.py`.**

  **Interfaces:** CLAUDE.md §5.6 exactly (names, subnets, IPs, `interface_name`, image tags, `image: lab4-ids:latest` with `build`).

  `client_traffic.sh`: add the route, then loop `wget` to both servers, logging one line per request `<ISO time> <server> OK|FAIL` to stdout (visible in `docker compose logs client`).

  `task4_check.sh`: `docker compose ps`; from `pinger`: `ping -c 3 nginx`, `ping -c 3 apache`, `ping -c 3 172.28.2.10`, `ping -c 3 172.28.2.11`, `wget -qO- http://nginx | head -4`, `wget -qO- http://apache | head -4`; prints a PASS/FAIL line per check and exits 1 on any FAIL; tees to `outputs/task4/task4_check.log`.

  Tests (`@pytest.mark.docker`; skipped unless `docker compose ps` shows the stack running):
  - `test_task4_check` (exit 0);
  - `test_ids_interfaces` (`mgmt0/ext0/int0` with the §5.6 IPs);
  - `test_client_routes_via_ids`;
  - `test_ui_only_on_mgmt` (host GET http://172.28.0.2:8080/api/interfaces is 200 and lacks mgmt0; client `wget http://172.28.1.2:8080` fails);
  - `test_agent_short_run` (`docker compose exec ids python3 script/agent.py --iface ext0 --model ALL --timespan 10` exits 0; ≥ 1 classified flow from 172.28.1.20 to each server; afterwards `bpftool net show dev ext0` shows no XDP);
  - `test_agent_normal_traffic_not_blocked` (during a 20 s ALL run there are 0 Malicious rows and no client FAIL lines; on failure the test prints the offending flow features).

  *AC:* the quality gate passes for shell and Python; `docker compose config` validates.
- [x] **T6.2 [H] Task 4 run.** `docker compose up -d --build`; `bash docker/task4_check.sh`; `docker compose exec ids ip -br addr`; `.venv/bin/pytest -m docker -v`. Paste verbatim.

  *AC:* Task 4 is PASS; the docker tests pass, or the failures are reported verbatim. Review Focus 1 failures go to T6.4, **not** to a fix.
- [x] **T6.3 [H] Live cycle runs (Task 2 evidence)**, with the stack up and the client running:
  1. For each of DT, XGB, ALL: `docker compose exec ids python3 script/agent.py --iface ext0 --model <M> --timespan 60`; paste the summary JSON and the first 10 JSONL lines.
  2. Count the client OK/FAIL lines in that window.
  3. Filter demo (O11): `… --model DT --model-file tests/fixtures/always_malicious.json --timespan 30 --block-seconds 20`; paste the summary (drops > 0, blocks 1) and the client log around the block (FAILs, then OKs after 20 s).
  4. Open http://172.28.0.2:8080 (browser use), start an ALL capture for 20 s, and save a screenshot to `outputs/realtime/ui_check.png`.

  *AC:* all runs exit 0 with no XDP left on `ext0`; outputs are saved under `outputs/realtime/`.
- [x] **T6.4 [O] Gate: normal traffic.** If any normal flow was Malicious, or the client logged FAIL outside the filter demo: stop, compare the flow's 10 features with the training distribution (DDoS vs BENIGN quantiles from `train.py` data), and present options to the user (for example more realistic client traffic, `CLASSIFY_MIN_PKTS`, the feature set). **No silent fixes.** Otherwise record the results (the counts per model) in CLAUDE.md §3 and the review log.
- [x] **T6.5 [U] Screenshots:**
  - `SS_T2_1–3`: agent CLI per model;
  - `SS_T2_4`: the filter demo summary;
  - `SS_T3_1–3`: the UI with normal traffic per model;
  - `SS_T3_4`: the UI during the filter demo;
  - `SS_T4_1`: `docker compose ps`;
  - `SS_T4_2`: `task4_check.sh`.

---

## P7: Verification and audit

- [x] **T7.1 [H] Full verification.**
  1. A fresh throw-away venv in the scratchpad: `uv venv --python 3.12 "$SCRATCH/v" && uv pip install --python "$SCRATCH/v/bin/python" -r requirements.txt && uv pip check --python "$SCRATCH/v/bin/python"`, then delete it.
  2. `pylint script tests`; `radon cc -s -a script tests`; `radon cc -n C script tests`.
  3. `pytest -m "not e2e and not kernel and not docker" -q`; `pytest -m e2e -q`.
  4. The kernel tests (T4.4 command).
  5. `pytest -m docker -q` with the stack up.
  6. `make -C xdp clean all`.

  Paste everything verbatim.

  *AC:* pylint 10.00/10; radon `-n C` empty; every suite passes.
- [x] **T7.2 [O] Audit.** (2026-11-26: all suites green in T7.1, parity chain complete (T3.5 + T4.4), UI only on mgmt0 and validated (T5.2/T6.1 tests), no stale XDP after runs, §3 numbers match outputs; one fix: `models_quick/` git-ignored)
  - The contracts (§5) hold.
  - **No leakage:** depth selection on val only; test touched once; no labels in cleaning.
  - The parity chain is complete (T3.5 + T4.4).
  - **Security:** UI binding, validation, no shell, privileged scope.
  - Every number in CLAUDE.md §3 equals `outputs/`.
  - No stale XDP or pins after `docker compose down`.

  Fixes go to [S], re-runs to [H]. *AC:* Opus signs off in the review log.

---

## P8: Reproducibility and code submission (slide 12; code due 2026-12-10)

- [ ] **T8.1 [S] `Lab4/README.md`, `Lab4/run.sh` and the root `README.md`.**
  - The README covers prerequisites (host xdp-tools install, Docker, uv, git-lfs), one section per task with exact commands, the architecture figure of CLAUDE.md §4.1, the security note (privileged container, `docker` group), and troubleshooting.
  - `run.sh [--quick]` follows the Lab 3 style:
    1. check the CSV / lfs pointer;
    2. venv + install;
    3. train (`--quick`: fixture CSV into `outputs_quick/`, `models_quick/`);
    4. unit tests;
    5. `make -C xdp`;
    6. image build + kernel tests;
    7. `docker compose up -d` + Task 4 check + a 10 s agent run;
    8. print the UI URL and the Task 1 sudo command;

    with exports of `LAB4_UID`/`LAB4_GID`.
  - Root README: a Lab 4 row in the lab table and the Lab 4 requirements line.
- [x] **T8.2 [H] `bash run.sh --quick` then `bash run.sh`**; paste verbatim. *AC:* both exit 0.
- [ ] **T8.3 [U] Commit and push** when the user decides (Opus prepares the message on request).

---

## P9: Report and presentation (deferred until the user asks; CLAUDE.md §10)

- [ ] **T9.1 [S] `G8.Report4.pdf`** (started 2026-11-26; user: "continue with next tasks"; SS_K_1–7 kernel-proof shots as placeholders until taken) (LaTeX, Lab 3 template and build rule; 15–20 pages):
  - Task 1 with the SS_T1 screenshots;
  - Task 2: method (kernel features, integer trees, classification trigger, blocking), the verification chain, metrics vs Lab 3, kernel timing/size, limitations;
  - Task 3 (UI);
  - Task 4.

  Numbers come only from `outputs/` and `models/` meta.
- [ ] **T9.2 [U] Submit by 2026-12-09** (recipients per CLAUDE.md §10).
- [ ] **T9.3 [S] Presentation for 2026-12-16** (10 + 2 min; each member presents their own task).

## Review log

| Date | Source | Finding | Outcome |
|---|---|---|---|
| 2026-11-25 | Haiku T0.2 | Lab 3 "ALL CHECKS PASSED" install log came from the partner's machine; here xdp-tools is built but not installed | T1.1 [U] install added (D4) |
| 2026-11-25 | User + Lab 3 side run | XGBoost 20 trees, depth 4–6 (`../Lab3/outputs_xgb20/`) | Lab 4 XGB = 20 trees; depth by validation (D6, O4); results in CLAUDE.md §3.3 |
| 2026-11-25 | Opus T3.6 gate | DT d6 F1 0.9991, XGB 20t d4 F1 0.9989 (≥ 0.99); parity 100 %/100 %, max err 4.5e-5; 387 nodes; depth rule followed; 2 size features ≈ 99 % importance | Passed; CLAUDE.md §3.4 |
| 2026-11-25 | Opus T6.4 gate | Normal traffic DT/XGB/ALL: 118 flows each, 0 Malicious, 0 client FAIL; filter demo 55 drops, 2 blocks (expiry + re-block; the T6.3 "blocks 1" expectation was wrong) | Passed; CLAUDE.md §3.6 |
| 2026-11-26 | Haiku T8.2 | `run.sh` full exit 0 (73 s); `--quick` failed: `test_kernel_parity` asserted exactly 1,024 vectors (fixture gives 439) | [S] fixed to 1 ≤ n ≤ 1,024; kernel suite 16/16 with `models/` and `models_quick/` |
| 2026-11-26 | Haiku T5.4 + Opus | Replay 24 (ALL): 84 rows, 12 DDoS→Malicious, 12 BENIGN→Normal, 60 live Normal, client 0 FAIL; replay at start was buried under live rows → [S] spread replay over 0–80 % of the capture; recheck (another capture was already running) showed replay rows interleaved, 6/6 match labels | Done; stack and images torn down |
| 2026-11-26 | Opus screenshot review (`Lab4/SS/`, 23 files) | Task 1 sections 1–8 and 10 OK; section 9 `xdp-filter poll` empty (output buffered through tee); SS_T3_2–4 missing; SS_T3_1 is ALL with 16 rows and "Idle" status (retake per model before timespan ends); SS_Docker_IDS shows 16 kernel tests (now 18) | Reported to the user; T2.3 open until SS_T1_9 retaken |
