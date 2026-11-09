# CLAUDE.md: Security Insider Lab, Lab 2 (Tasks 3 & 4)

This lab does ML-based intrusion detection on CIC-IDS2017 flow features. The workspace covers **Task 3 (Data Pre-processing)** and **Task 4 (Logistic Regression + Decision Tree, plus real-time use)**. Tasks 1 and 2 are already done; their outputs are listed in §4.

- Course: Security Insider Lab, Uni Passau, group **G8**. Deadline: **2026-11-11**.
- Specs: `Task3.png` and `Task4.png` (in this root), and slides 9–10 of `Thursday_Dataset/lab-2.pptx`. Progress is tracked in `TASKS.md` of each dataset folder.
- **Scope rule:** implement only what the specs ask for, plus the tests needed to trust the results. Do not add tasks, features, or demos without the user's approval.

## Datasets

> **Thursday (`Thursday_Dataset/`):** `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`. The user chose this file, and the report covers it. Slide 8 names the Friday DDoS file, so this is a deliberate deviation. Do not switch datasets (do not swap the file in `Thursday_Dataset/`).

> **Friday DDoS (parallel, 2026-11-09), `Friday_Dataset/`:** a separate, self-contained implementation of Tasks 3 & 4 on `Friday-WorkingHours-Afternoon-DDos.csv` (user request). It has its own uv project, CLAUDE.md and TASKS.md, and it does not replace the Thursday pipeline.

Each folder has its own `CLAUDE.md`, `TASKS.md`, uv project (`.venv`), `SS/` (screenshots) and its own report folder (`Thursday_Dataset/reports/`, `Friday_Dataset/report/`). **Always `cd` into the dataset folder before `uv run`.** Verified data facts, design decisions and commands are in that folder's CLAUDE.md. (Old section numbers §2, §3 and §5 moved to `Thursday_Dataset/CLAUDE.md`; §1, §4 and §6–§9 stay here.)

---

## 1. Model routing (MANDATORY)

The main session runs on **Opus 5.5**. It orchestrates, analyzes, and reviews. It does not write bulk code or run long command sequences itself, and delegates with the `Agent` tool:

| Work type | Model | How to delegate |
|---|---|---|
| Analysis, planning, design decisions, interpreting metrics, reviewing subagent output | **Opus 5.5** (main session) | inline |
| Development: writing code, unit tests, e2e tests, debugging | **Sonnet 5.5** | `Agent(subagent_type="general-purpose", model="sonnet", ...)` |
| Presentations and documents: creating or updating `.pptx` decks, `Presentation.md`, speaking scripts, report text | **Sonnet 5.5** | `Agent(subagent_type="general-purpose", model="sonnet", ...)` |
| Browser use, running terminal commands, env setup, running scripts and collecting output, light tasks | **Haiku 5.5** | `Agent(subagent_type="general-purpose", model="haiku", ...)` |

Delegation rules:

1. Subagents start cold. Each prompt names the **TASKS.md ID** and tells the agent to read `CLAUDE.md` plus that task's spec and AC first.
2. Give each subagent one task and expect one result back. Independent tasks may run in parallel.
3. Haiku runs commands and reports output verbatim. It does **not** edit `src/`. Opus routes code fixes to Sonnet.
4. Opus checks every result against its AC and against §2, then ticks the box in `TASKS.md`. Subagents never tick boxes.
5. `sudo` is not available non-interactively. Hand any root step to the user as a `! sudo ...` command.

---

## 4. Repository layout

```
Lab2/
├── CLAUDE.md  .gitattributes      # this file: lab-wide rules
├── Task3.png  Task4.png           # task specs (common)
├── task1_lab2.pcapng              # Task 1 capture: 81,110 frames, 347 s, 99.9% IPv4 (IPv6 off), benign
├── task2_lab2.pcap_Flow.csv       # CICFlowMeter V4 flows of task1_lab2.pcapng (569 flows); REAL-TIME INPUT for both datasets
├── Thursday_Dataset/              # Thursday Web Attacks project (own uv project; see Thursday_Dataset/CLAUDE.md)
│   ├── CLAUDE.md TASKS.md README.md pyproject.toml uv.lock  src/lab2ids/  scripts/  tests/  artifacts/  outputs/  <Thursday CSV>
│   ├── lab-2.pptx                 # course slides
│   ├── SS/                        # screenshots SS1-SS25 (no SS16)
│   └── reports/                   # LaTeX report + reports/presentation/ (moved here 2026-11-09)
└── Friday_Dataset/                # parallel Friday DDoS project (own uv project; see Friday_Dataset/CLAUDE.md)
    ├── CLAUDE.md TASKS.md  src/ddosids/  scripts/  tests/  artifacts/  outputs/  <Friday CSV>
    ├── SS/                        # screenshots SS15/17/18/24/25 (common) and SS26-SS38 (SS26 unused)
    └── report/                    # LaTeX report (singular; written, in review)
```

---

## 6. Real-time input (common to both datasets; implemented last)

```
 Task 1 pcap ──(user runs CICFlowMeter, Task 1/2)──► Task 2 flow CSV (V4 columns)
                                                          │ streamed row by row, Timestamp order
                                                          ▼
   colmap (V4 → ISCX names) → inf/NaN→0, drop Protocol-0 rows → joblib Pipeline → per-flow verdict
```

- **Real-time input:** `task2_lab2.pcap_Flow.csv`, made from `task1_lab2.pcapng` (benign browsing, 2026-11-04, 16:05–16:10). The flow CSV path is always a CLI argument; never hard-code it.
- **Expect domain shift.** The training data was produced by CICFlowMeter V3 on the 2017 testbed; the Task 2 flows come from V4 on a different network. Report any false positives honestly.
- Model choice (`REALTIME_MODEL`) and run expectations are in each dataset folder's CLAUDE.md.

---

## 7. Gotchas (common)

- **Column names differ between CICFlowMeter V4 and ISCX.** 20 names differ; `Thursday_Dataset/TASKS.md` T5.1 has the table. The remaining 57 match after normalization. All 77 features map (verified). V4's metadata columns are for display only and must never be used as features.
- **Earlier captures (deleted; the files were 89–98% IPv6) produced bogus flows.** 85–95% of their flows had `Protocol=0` and `Dst Port=0`, implausible IPs (e.g. `136.225.0.0 → 160.0.176.82`) and 0 backward packets. If a future capture shows this, IPv6 was on.
  **Verified cause:** CICFlowMeter hard-codes `readIP6 = false` (`Cmd.java:126`, `ReadPcapFileWorker.java:152`). Every non-IPv4 frame (IPv6, ARP, HomePlug) falls into `getVPNInfo()`, which force-parses the frame as IPv4 from byte 0. The "src IP" is therefore EtherType + 2 bytes (`134.221.x` = `86 DD` IPv6, `136.225` = `88 E1` HomePlug, `8.6` = ARP). The "dst IP" is the IPv6 flow label + payload length. The IPv4 flows themselves are parsed correctly.
  The detector must always drop `Protocol==0` rows and log the count.
- **`task2_lab2.pcap_Flow.csv` (from `task1_lab2.pcapng`) is the good file.** IPv6 was off for the capture. The user renamed it from `benign_lab2_3.*`; the old `task1_lab2.pcap`/`task2_lab2.pcap_Flow.csv` are gone.
  - 569 flows: 162 TCP, 385 UDP, 22 with Protocol 0
  - the 22 Protocol-0 rows are 15 real ICMP flows (CICFlowMeter gives every non-TCP/UDP flow protocol 0) plus 4 IPv6 and 3 ARP leftovers
  - CICFlowMeter only writes flows with ≥2 packets (`FlowGenerator.java:94`), so single-packet traceroute probes and DNS queries are absent by design
- **`tshark -r <file in $HOME>` fails with "You don't have permission".** Ubuntu's AppArmor profile `/etc/apparmor.d/tshark` blocks tshark from reading files outside `/tmp`. Without sudo, pipe the file in: `cat f.pcap | tshark -r - ...`. To write, use `-w -` and redirect: `> out.pcap`. `capinfos` is not affected.
- **Save figures as PNG (200 dpi) and PDF;** they are reused in the report.

(The dataset-specific gotchas moved: multiclass LR `max_iter` ≥ 2000 and the `artifacts/clean.parquet` cache are in `Thursday_Dataset/CLAUDE.md` §7.)

## 8. Conventions

- Use type hints and small functions in `Thursday_Dataset/src/lab2ids` (`Friday_Dataset/src/ddosids` for Friday). Scripts are thin argparse CLIs.
- Use `random_state=42` everywhere. Log every row and column drop with its count.
- Do not create a git repo or commit unless the user asks.

---

## 9. Reports

- Each dataset folder has its own report folder (`Thursday_Dataset/reports/`, `Friday_Dataset/report/`) and its own screenshots in `<folder>/SS/` (user decision, 2026-11-09).
- The `latexmkrc_2` build rule (always build with `latexmkrc_2`, from inside the report folder) applies to both reports.
- Details: `Thursday_Dataset/CLAUDE.md` §9 and `Friday_Dataset/CLAUDE.md` §9.
