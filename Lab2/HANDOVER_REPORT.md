# Handover Report: Lab 2, Group G8 (input for LaTeX Report 2)

**Status as of:** 2026-11-04 · **Report:** `G8.Report2.pdf` (10–15 pages, screenshots required) · **Due:** 2026-11-11 (presentation the same day)
**LaTeX template:** `../Lab1/G8_Report1_Version_2/G8_Report1_source/`
- Chapters: `introduction`, `methods`, `results`, `attacks`, `ml`, `discussion`
- Bibliography: `bibliography.bib`

> **Source-of-truth rule.** Every number below was read from the generated files listed in §9. Some numbers will change, e.g. after a re-run or when Task 4 is done. When that happens, re-read the files rather than trusting this document or any agent transcript. Agent transcripts have contained copy errors before.

---

## 1. Status overview

| Task | Status | Report-ready? | Notes |
|---|---|---|---|
| Task 1: pcap → flows (CICFlowMeter) | ✅ **Good capture available** | Yes (§7) | The first two captures produced mostly bogus flows (root cause in §7). The third capture, `task1_lab2.pcapng` with its flows `task2_lab2.pcap_Flow.csv` (renamed from `benign_lab2_3.*`), was made with IPv6 off and is clean: 96 % of its flows are valid. It is the real-time input for Task 4. |
| Task 2: CIC-IDS2017 dataset | ✅ Downloaded | Yes (§2) | The group uses **Thursday-WorkingHours-Morning-WebAttacks**, not the Friday DDoS file named on slide 8. **TODO (group):** state the reason in the report. |
| **Task 3: Data pre-processing** | ✅ **Done, reviewed** | **Yes (§3–§6)** | All numbers verified twice, independently. Tests pass. |
| **Task 4: LR + Decision Tree** | ✅ **Done, reviewed** | **Yes (§8.1–§8.3, §8.6)** | 8 models. Metrics reproduced in 3 runs. The group recorded the final run (screenshots in `SS/`). |
| **Task 4: real-time use** | ✅ **Done, reviewed** | **Yes (§8.4)** | 569 flows of our capture were classified. A parity test proves the real-time path equals the offline model. The 3 alerts are false positives, explained in §8.4. |

Suggested placement in the template:

| Chapter | Content |
|---|---|
| `methods.tex` | §2 dataset and §3 pipeline |
| `results.tex` | §4 tables and §5 figures |
| `discussion.tex` | §6 |
| `ml.tex` | Task 4, later |

`attacks.tex` can briefly describe the three web attacks (Brute Force, XSS, SQL Injection).

---

## 2. Dataset (Task 2), for Introduction/Methods

- **Source:** CIC-IDS2017, Canadian Institute for Cybersecurity, University of New Brunswick [Sharafaldin et al. 2018]. Flows were extracted with CICFlowMeter [Lashkari et al. 2017]. We use the pre-computed "MachineLearningCSV" file.
- **File:** `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`, 52 MB.
  - It has **170,366 flows × 79 columns** (78 numeric flow features + `Label`).
  - It has no Flow ID, IP address or timestamp columns. `Destination Port` is present.
- **Attack scenario:** the dataset paper describes web attacks (Brute Force, XSS, SQL Injection) against a Damn Vulnerable Web Application (DVWA). The attacks were automated with Selenium on Thursday morning.
- **Class distribution (raw):**

| Label | Flows | Share | Ratio to BENIGN |
|---|---:|---:|---:|
| BENIGN | 168,186 | 98.7204 % | 1 |
| Web Attack – Brute Force | 1,507 | 0.8846 % | 1 : 112 |
| Web Attack – XSS | 652 | 0.3827 % | 1 : 258 |
| Web Attack – Sql Injection | 21 | 0.0123 % | 1 : 8,009 |

- **Key message: the dataset is extremely imbalanced.** Attacks are 1.28 % of flows, and SQL Injection is 21 flows. A classifier that always answers "BENIGN" would already be 98.7 % accurate, so accuracy alone is meaningless for this dataset (relevant for Task 4).
- **Port distribution (raw file):**
  - All 2,180 attack flows target `Destination Port` 80.
  - BENIGN flows are spread across ports: 53 (76,545), 443 (35,833), 80 (18,682), 123 (3,746), 22 (1,035), …

---

## 3. Task 3 methodology, for `methods.tex`

The spec (slide 9) asks for five things: analyze labels; manage Infinity/NaN; scale with min-max; find the best features with SelectKBest; select 20.

The implementation is Python 3.12, pandas and scikit-learn, in `src/lab2ids/data.py` and `features.py`. The CLI is `scripts/task3_preprocess.py`. Each step below states *what* was done and *why*.

1. **Load & label analysis.**
   - Column names carry stray leading spaces (65 of 79), so they are stripped.
   - The attack labels contain a broken character: the original en dash was stored as an invalid byte and decodes as U+FFFD "�", giving `Web Attack � XSS`. We read the file as UTF-8 with replacement, map "�" to "-", and collapse whitespace.
   - Every label is then validated against the 4 expected classes.
2. **Duplicate column.**
   - `Fwd Header Length` appears twice in the header; this is a known artifact of the CICFlowMeter export.
   - The second copy is dropped.
3. **Infinity/NaN.**
   - ±Infinity is replaced by NaN, then rows containing NaN are **dropped**.
   - *Why drop rather than impute:* only 135 rows (0.08 %) are affected, all of them BENIGN, so no attack information is lost and no artificial values are introduced.
   - *Where they come from:* the infinite values sit only in the rate features `Flow Bytes/s` and `Flow Packets/s`. CICFlowMeter divides by the flow duration, and the duration is 0 for single-packet flows.
4. **Duplicate rows.**
   - Exact duplicate flows are removed **before** splitting.
   - *Why:* otherwise identical rows end up in both train and test, which inflates test scores.
5. **Constant columns.**
   - These carry zero information, and they break or warn in SelectKBest.
6. **Identical columns.**
   - Columns equal to an earlier column (tolerance |Δ| ≤ 1e-6) are removed, keeping the first.
   - *Why:* otherwise SelectKBest would spend several of the 20 slots on copies of the same feature.
   - *The tolerance:* one pair, `Bwd Packet Length Mean` and `Avg Bwd Segment Size`, is the same quantity by definition but differs in 2 rows by 1e-6 because of CSV rounding.
7. **Train/test split.**
   - Stratified on the 4-class label: 70 % train, 30 % test, `random_state=42`.
   - The same split is reused for both targets: binary (BENIGN vs. ATTACK) and multiclass (4 labels).
   - The split happens **before** any fitting.
8. **Min-max scaling.**
   - `MinMaxScaler(clip=True)` maps each feature to [0, 1].
   - It is **fitted on the training set only**, which avoids leaking test statistics into training.
   - `clip=True` keeps unseen values, from the test set or live traffic later, inside [0, 1].
9. **Feature selection.**
   - `SelectKBest(chi2, k=20)` on the scaled training set, run once per target.
   - *Why chi2 after min-max:* chi2 requires non-negative inputs, and the raw data contains negatives (`Init_Win_bytes_*` = −1 means "not observed"; a few negative `Flow Duration`/IAT values). Min-max scaling makes every value ≥ 0.

The column-level steps (constant and identical columns) use only feature values, never labels, so no label information leaks.

---

## 4. Task 3 results, for `results.tex`

### 4.1 Cleaning steps (Table)

Source: `outputs/task3/cleaning_report.json`.

| # | Step | Rows | Columns | Detail |
|---|---|---|---|---|
| 1 | Drop duplicate header column | 170,366 → 170,366 | 79 → 78 | `Fwd Header Length.1` |
| 2 | Replace ±Inf with NaN | 170,366 | 78 | Inf: `Flow Bytes/s` 115, `Flow Packets/s` 135; NaN: `Flow Bytes/s` 20 |
| 3 | Drop NaN rows | 170,366 → 170,231 | 78 | −135 rows (all BENIGN) |
| 4 | Drop duplicate rows | 170,231 → 164,179 | 78 | −6,052 rows (6,015 BENIGN, 37 Brute Force) |
| 5 | Drop constant columns | 164,179 | 78 → 68 | −10 columns (§4.2) |
| 6 | Drop identical columns | 164,179 | 68 → 61 | −7 columns (§4.2) |
| | **Final** | **164,179** | **60 features** + `Label` + `binary_label` | |

Note on step 4: the raw file has 6,066 duplicate rows. 14 of them were already removed in step 3 because they contained Inf/NaN, which leaves 6,052 for this step.

### 4.2 Removed columns

- **Constant (10):** `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.
  The six bulk-transfer features are always 0 in this CICFlowMeter version.
- **Identical (7).** The second column of each pair was dropped:

| Kept | Dropped |
|---|---|
| `Fwd PSH Flags` | `SYN Flag Count` |
| `RST Flag Count` | `ECE Flag Count` |
| `Fwd Packet Length Mean` | `Avg Fwd Segment Size` |
| `Bwd Packet Length Mean` | `Avg Bwd Segment Size` (≈, 2 rows differ by 1e-6) |
| `Total Fwd Packets` | `Subflow Fwd Packets` |
| `Total Length of Fwd Packets` | `Subflow Fwd Bytes` |
| `Total Backward Packets` | `Subflow Bwd Packets` |

`Fwd PSH Flags` ≡ `SYN Flag Count` is suspicious in itself: these are different TCP flags. It points to a feature-extraction issue in the CICFlowMeter version used for CIC-IDS2017 [cf. Engelen et al. 2021].

### 4.3 Class distribution after cleaning

| Label | Flows | Share |
|---|---:|---:|
| BENIGN | 162,036 | 98.6947 % |
| Web Attack – Brute Force | 1,470 | 0.8954 % |
| Web Attack – XSS | 652 | 0.3971 % |
| Web Attack – Sql Injection | 21 | 0.0128 % |
| **Total** | **164,179** | attacks: 2,143 (1.31 %), BENIGN : ATTACK ≈ 76 : 1 |

### 4.4 Train/test split

Stratified on `Label`, 70/30, `random_state=42`.

| Label | Train | Test |
|---|---:|---:|
| BENIGN | 113,425 | 48,611 |
| Brute Force | 1,029 | 441 |
| XSS | 456 | 196 |
| Sql Injection | 15 | 6 |
| **Total** | **114,925** | **49,254** |

### 4.5 Min-max scaling (example excerpt)

Values are for the training set. Source: `outputs/task3/describe_train_{before,after}_scaling.csv`.

| Feature | min before | max before | mean before | min after | max after | mean after |
|---|---:|---:|---:|---:|---:|---:|
| `Init_Win_bytes_backward` | −1 | 65,535 | 2,493.26 | 0 | 1 | 0.0381 |
| `Init_Win_bytes_forward` | −1 | 65,535 | 6,353.91 | 0 | 1 | 0.0970 |
| `Destination Port` | 0 | 65,529 | 8,151.67 | 0 | 1 | 0.1244 |
| `Flow Duration` (µs) | −1 | 119,999,993 | 12,876,960 | 0 | 1 | 0.1073 |
| `Bwd IAT Total` (µs) | 0 | 120,000,000 | 11,635,100 | 0 | 1 | 0.0970 |
| `PSH Flag Count` | 0 | 1 | 0.2469 | 0 | 1 | 0.2469 |

Across all 60 training columns the scaled minimum is exactly 0 and the maximum is 1. Some maxima come out as 0.9999999999999999, which is ordinary floating-point rounding.

### 4.6 The 20 best features (SelectKBest, chi2)

Source: `outputs/task3/feature_scores_{binary,multiclass}.csv` and `artifacts/selected_features_{binary,multiclass}.json`.

**Binary target (BENIGN vs. ATTACK):**

| Rank | Feature | chi2 score | p-value |
|---:|---|---:|---:|
| 1 | `Init_Win_bytes_backward` | 4525.18 | < 1e-300 |
| 2 | `PSH Flag Count` | 2928.73 | < 1e-300 |
| 3 | `Init_Win_bytes_forward` | 1616.52 | < 1e-300 |
| 4 | `ACK Flag Count` | 238.36 | 8.94e-54 |
| 5 | `Destination Port` | 185.37 | 3.26e-42 |
| 6 | `Bwd IAT Total` | 100.41 | 1.24e-23 |
| 7 | `Down/Up Ratio` | 75.32 | 4.00e-18 |
| 8 | `Fwd IAT Std` | 68.76 | 1.11e-16 |
| 9 | `Fwd PSH Flags` | 68.03 | 1.61e-16 |
| 10 | `Bwd Packet Length Min` | 56.82 | 4.77e-14 |
| 11 | `Idle Max` | 49.80 | 1.70e-12 |
| 12 | `Idle Mean` | 48.52 | 3.27e-12 |
| 13 | `Idle Min` | 46.57 | 8.85e-12 |
| 14 | `URG Flag Count` | 44.97 | 2.00e-11 |
| 15 | `Packet Length Mean` | 41.21 | 1.37e-10 |
| 16 | `min_seg_size_forward` | 40.12 | 2.39e-10 |
| 17 | `Bwd Packet Length Mean` | 39.02 | 4.20e-10 |
| 18 | `Bwd IAT Max` | 38.44 | 5.66e-10 |
| 19 | `Fwd IAT Total` | 38.11 | 6.68e-10 |
| 20 | `Flow Duration` | 37.96 | 7.22e-10 |
| *21* | *`Average Packet Size` (not selected)* | *37.77* | *7.94e-10* |

**Multiclass target (4 labels):**

| Rank | Feature | chi2 score | p-value |
|---:|---|---:|---:|
| 1 | `Init_Win_bytes_backward` | 4596.70 | < 1e-300 |
| 2 | `PSH Flag Count` | 2937.06 | < 1e-300 |
| 3 | `Init_Win_bytes_forward` | 1620.67 | < 1e-300 |
| 4 | `ACK Flag Count` | 246.02 | 4.76e-53 |
| 5 | `Destination Port` | 185.37 | 6.10e-40 |
| 6 | `Bwd IAT Total` | 100.44 | 1.25e-21 |
| 7 | `Down/Up Ratio` | 77.20 | 1.22e-16 |
| 8 | `Fwd IAT Std` | 70.42 | 3.47e-15 |
| 9 | `URG Flag Count` | 69.62 | 5.14e-15 |
| 10 | `Fwd PSH Flags` | 68.03 | 1.13e-14 |
| 11 | `Bwd Packet Length Min` | 56.82 | 2.80e-12 |
| 12 | `Idle Max` | 49.80 | 8.80e-11 |
| 13 | `Idle Mean` | 48.52 | 1.65e-10 |
| 14 | `Bwd Packet Length Std` | 47.63 | 2.56e-10 |
| 15 | `Idle Min` | 46.57 | 4.30e-10 |
| 16 | `Packet Length Mean` | 42.83 | 2.68e-09 |
| 17 | `Bwd Packet Length Mean` | 41.50 | 5.13e-09 |
| 18 | `min_seg_size_forward` | 40.12 | 1.00e-08 |
| 19 | `Average Packet Size` | 39.13 | 1.63e-08 |
| 20 | `Bwd IAT Max` | 38.67 | 2.04e-08 |
| *21* | *`Fwd IAT Total` (not selected)* | *38.51* | *2.20e-08* |

The CSV stores the top three p-values as 0.0, meaning they underflow double precision; write them as "< 1e-300".

**Overlap between the two lists: 18 of 20 features.**
- Only in the binary list: `Fwd IAT Total`, `Flow Duration`.
- Only in the multiclass list: `Average Packet Size`, `Bwd Packet Length Std`.

The lowest-scoring features overall (binary) are `Total Fwd Packets` (2.0e-6), `Bwd Header Length` (0.012) and `Fwd Header Length` (0.014).

---

## 5. Figures & screenshots

| File | Suggested caption |
|---|---|
| `outputs/task3/figures/feature_scores_binary.pdf` (and `.png`) | Top-20 flow features by chi2 score for binary classification (BENIGN vs. ATTACK), computed on the min-max-scaled training set. |
| `outputs/task3/figures/feature_scores_multiclass.pdf` (and `.png`) | Top-20 flow features by chi2 score for the 4-class problem. |
| `outputs/task3/run_log.txt` | Console output of the pre-processing script, for a terminal screenshot (spec: "include screenshots"). Run `cat outputs/task3/run_log.txt` in a terminal and screenshot it, or include it with `\lstinputlisting`. |

Figure note: the scores are dominated by the top 3 (more than 1,600 each, against less than 250 for the rest), so ranks 6–20 look similar on the linear axis. Mention this in the caption or text.

There is no label-distribution chart; §4.3 is a table. Generate a chart only if the group wants one.

---

## 6. Discussion points, for `discussion.tex`

1. **The top features are partly testbed-specific.**
   - `Init_Win_bytes_backward`/`_forward` (the initial TCP window size) dominate the ranking.
   - They depend on the OS and TCP stack of the attacker and victim hosts in the 2017 testbed, not on the attack itself.
   - Expect them to generalize poorly to our own network traffic. This is relevant for Task 4's real-time part.
2. **`Destination Port` is a shortcut feature.**
   - Every attack targets port 80, while benign traffic uses many ports.
   - A model can therefore learn "port 80 ⇒ suspicious" instead of learning the attack's behaviour.
3. **The flag features (`PSH`, `ACK`, `URG`, `Fwd PSH`) capture HTTP request/response patterns.** The timing features (`IAT`, `Idle`, `Flow Duration`) capture the regular, automated pacing of the Selenium-driven attacks, especially brute force.
4. **Binary and multiclass selection agree on 18/20 features.** The features that separate attacks from benign traffic are largely the same ones that separate the attack types.
5. **chi2 on min-max-scaled continuous data is a heuristic.** chi2 treats the scaled values like frequencies. Heavy-tailed features, such as `Flow Bytes/s` and durations up to 120 s, are squeezed close to 0 by min-max scaling, which lowers their chi2 scores. The ranking therefore depends on the scaling choice.
6. **Data-quality issues in CIC-IDS2017:**
   - the broken label encoding
   - the duplicated column
   - Inf values from zero-duration flows
   - 6k duplicate rows
   - `Fwd PSH Flags` ≡ `SYN Flag Count`

   These match issues reported in the literature [Engelen et al. 2021] and justify careful pre-processing before any machine learning.
7. **Limitations:**
   - **SQL Injection** has 21 samples, 6 in the test set, so any per-class metric for it will be statistically weak.
   - **Dropping rows** (instead of imputing them) slightly changes the BENIGN distribution; the effect is negligible at 0.08 %.
   - **Min-max scaling** is sensitive to outliers.

---

## 7. Task 1/2 findings: CICFlowMeter on our captures

**Problem.** The first two captures produced flow CSVs in which most flows are garbage: `Protocol = 0`, ports 0, and implausible "IP addresses". The third capture, recorded with IPv6 disabled, is clean.

| Capture | Frames | Duration | IPv6 frames | IPv4 frames | Flows in CSV | Protocol-0 flows | Valid TCP/UDP flows |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1st capture (old `task1_lab2.pcap`, since deleted) | 129,548 | 687.5 s | 126,904 (98 %) | 1,924 | 532 | 454 | 78 |
| 2nd capture (`benign_lab2_2.pcap`, since deleted; 2026-11-04, 15:44–15:49) | 98,780 | 301.6 s | 88,458 (89.5 %) | 10,306 | 1,327 | 1,260 | 67 (53 TCP, 14 UDP) |
| **`task1_lab2.pcapng` → `task2_lab2.pcap_Flow.csv`** (2026-11-04, 16:05:01–16:10:49, **IPv6 off**) | **81,110** | **347.4 s** | **24 (0.03 %)** | **81,060 (99.94 %)** | **569** | **22** | **547 (162 TCP, 385 UDP)** |

**Final capture `task1_lab2.pcapng` (flows: `task2_lab2.pcap_Flow.csv`).** This is the one used for the report and for Task 4 real-time.
- **Protocol mix:**
  - UDP: 47,682 frames, of which 29,682 are QUIC, 580 DNS, and 17,394 unidentified UDP payload. Steam ports 27018/27019 appear.
  - TCP: 33,218 frames, of which 11,994 are TLS and 26 HTTP.
  - ICMP: 160 frames. Traceroute "time exceeded" replies from routers also appear.
  - ARP: 26 frames.
- **Flow destinations:**
  - 289 of the 547 valid flows are DNS to the local resolver `10.241.62.246:53`, since every DNS query is its own flow. One more flow to the same router is DHCP (UDP port 67).
  - 213 go to port 443 and 15 to port 80.
- **Coverage:** the valid flows contain 80,705 packets, which is **99.8 %** of the 80,900 IPv4 TCP/UDP frames.
  - The roughly 195 missing packets are single-packet UDP exchanges, mostly traceroute probes on ports 33434+.
  - CICFlowMeter only writes flows with ≥ 2 packets (`FlowGenerator.java:94`). That is also why tshark counts 568 UDP conversations but the CSV has 385 UDP flows (197 conversations have a single packet).
- **The 22 Protocol-0 rows:**
  - 15 are real ICMP flows. CICFlowMeter only sets the protocol number for TCP/UDP.
  - 4 are left-over IPv6 frames and 3 are ARP frames, both mis-parsed as described below.
  - The real-time detector drops all 22 (3.9 %).
- **Data quality:** there are no Inf/NaN values in the valid flows, and the timestamps parse and match the capture window.
  - `Label` is `NeedManualLabel` for every row; the traffic is benign by construction.
  - The header is identical to the earlier CSVs, and all 77 features map to the training feature names.
- **File names:** the group renamed the files from `benign_lab2_3.*` to `task1_lab2.pcapng` (capture) and `task2_lab2.pcap_Flow.csv` (flows). The CSV's time window and packet counts match the capture.
- **Domain shift to expect in Task 4:** about 70 % of the valid flows are UDP: DNS, QUIC/HTTP-3 and Steam. The 2017 benign training traffic also contains a lot of DNS (port 53: 76,545 of 168,186 raw BENIGN flows), so UDP as such is not new. What differs is the mix of applications (QUIC, Steam) and the network itself, i.e. hosts, TCP stacks and CICFlowMeter version.

**Root cause (verified in the CICFlowMeter source).**
- IPv6 support is switched off in the code: `readIP6 = false` is hard-coded in `Cmd.java:126` and `ReadPcapFileWorker.java:152`.
- Every frame that is not IPv4 (IPv6, ARP, HomePlug powerline frames) falls through to `getVPNInfo()`. That function force-parses the raw frame as an IPv4 header starting at byte 0.
- The fake "source IP" is therefore just frame bytes 12–15, i.e. the EtherType plus 2 header bytes:

| Fake "IP" | Bytes | Actually |
|---|---|---|
| `134.221.96.0` | `86 DD 60 00` | EtherType 0x86DD (IPv6) + first IPv6 header bytes |
| `0.0.4.214` (dst) | `00 00 04 D6` | IPv6 flow label + payload length (1238) |
| `136.225.0.0` | `88 E1 …` | EtherType 0x88E1 (HomePlug AV) |
| `8.6.x.x` | `08 06 …` | EtherType 0x0806 (ARP) |

**Fix for the recapture.** Disable IPv6 during the capture and use the Wireshark capture filter `ip`:

```
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
# capture in Wireshark, then re-enable:
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0
```

This also matches the training data, which is IPv4 only. We decided against enabling CICFlowMeter's IPv6 path: its UDP branch takes the header length from the TCP header (`PacketReader.java:204`), which is a bug.

**Environment note (optional).** On Ubuntu, `tshark -r <file in $HOME>` fails with "You don't have permission to read the file". The cause is the shipped AppArmor profile `/etc/apparmor.d/tshark`. The workaround is `cat file.pcap | tshark -r - …`. `capinfos` and the Wireshark GUI are not affected.

---

## 8. Task 4 results, for `ml.tex` / `results.tex` / `discussion.tex`

**Sources:**
- `outputs/task4/comparison.csv`, `metrics.json`, `report_*.csv`, `run_log.txt`
- the group's recorded runs on 2026-11-04: training at 17:17 (`SS/SS1.png`–`SS/SS11.png`), real-time and final tests at about 17:42 (`SS/SS12.png`–`SS/SS14.png`)
- the real-time results: `outputs/realtime/run_log.txt` and `predictions.csv`

The metrics are deterministic and were reproduced exactly in three independent runs. The timings below come from the group's run, the only one with no other load on the machine.

### 8.1 Setup (methods)
- **Pipeline:** `MinMaxScaler(clip=True) → SelectKBest(chi2, k=20) → classifier`. It is fit on the §4.4 train split (114,925 flows) and evaluated on the held-out test split (49,254 flows, of which 643 are attacks).
- **8 models:** {Logistic Regression `max_iter=5000`, Decision Tree `random_state=42`, unpruned} × {default, `class_weight="balanced"`} × {binary, multiclass}.
- **Convergence:** all four LR models converged, with `n_iter` 28 / 51 / 38 / 190, far below the limit.
- **Timing method:** inference time is the median of 5 timed `predict` calls on the whole test split, after one warm-up call, scaled to 1,000 flows.
- **Consistency check:** each saved pipeline's 20 selected features were verified to equal the Task 3 lists exactly.

### 8.2 Binary results (BENIGN vs. ATTACK)

| Model | Accuracy | Macro-F1 | Attack P | Attack R | **Attack F1** | False pos. | False neg. | Fit (s) | Inference (ms / 1k flows) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LR default | 0.9940 | 0.8926 | 0.7320 | 0.8538 | 0.7882 | 201 | 94 | 5.74 | 0.708 |
| LR balanced | 0.9577 | 0.6789 | 0.2349 | 0.9907 | 0.3797 | 2,075 | 6 | 23.26 | 0.672 |
| **DT default** | **0.9996** | **0.9930** | 0.9728 | **1.0000** | **0.9862** | 18 | **0** | 0.36 | 0.667 |
| DT balanced | 0.9996 | 0.9925 | 0.9815 | 0.9891 | 0.9853 | 12 | 7 | 0.35 | 0.683 |

### 8.3 Multiclass results (4 labels)

| Model | Accuracy | **Macro-F1** | F1 BENIGN | F1 Brute Force | F1 XSS | F1 SQLi | Fit (s) | Inference (ms / 1k) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LR default | **0.9854** | **0.2482** | 0.9926 | 0.0000 | 0.0000 | 0.0000 | 11.67 | 0.688 |
| LR balanced | 0.9321 | 0.3191 | 0.9689 | 0.0781 | 0.2233 | 0.0061 | 26.40 | 0.835 |
| **DT default** | 0.9923 | **0.7290** | 0.9982 | 0.6126 | 0.3960 | 0.9091 | 0.73 | 0.701 |
| DT balanced | 0.9913 | 0.5642 | 0.9977 | 0.5827 | 0.3762 | 0.3000 | 0.77 | 0.675 |

**Key confusion matrices.** Rows are true and columns predicted, in the order BENIGN, Brute Force, XSS, SQLi:

| Model | BENIGN | Brute Force | XSS | SQLi |
|---|---|---|---|---|
| DT default | 48,522 / 68 / 21 / 0 | 70 / **268** / 103 / 0 | 20 / 97 / **79** / 0 | 0 / 1 / 0 / **5** |
| LR default | 48,535 / 76 / 0 / 0 | 441 / 0 / 0 / 0 | 196 / 0 / 0 / 0 | 6 / 0 / 0 / 0 |
| LR balanced | 45,681 / 370 / 971 / 1,589 | 0 / 33 / 369 / 39 | 0 / 0 / 193 / 3 | 0 / 1 / 0 / 5 |

### 8.4 Real-time use (Task 4, second part)
- **Model:** `binary_dt_default` (set as `REALTIME_MODEL` in `config.py`). It has the best attack-F1, no missed attacks on the test split, and a false-positive rate of 18 / 48,611 = **0.037 %**.
- **Input:** `task2_lab2.pcap_Flow.csv`, the 569 CICFlowMeter V4 flows of our capture `task1_lab2.pcapng`. The traffic is benign: browsing, DNS, QUIC and the Steam client.
- **Procedure:**
  - The flows are streamed one by one in timestamp order.
  - V4 column names are mapped to the training names; all 77 features map.
  - `Protocol = 0` rows are dropped: ICMP, plus IPv6 and ARP leftovers.
  - Each flow is classified by the saved pipeline, unchanged from training.
- **Correctness proof (parity test):**
  - The 49,254-flow test split was converted to V4 column names and streamed through the real-time detector.
  - Its predictions are **identical, row for row**, to the offline pipeline, for batch size 1,000 and for batch size 1.
  - The attack-F1 recomputed from the streamed predictions equals §8.2.
- **Result:**

| Flows read | Dropped (Protocol 0) | Inf/NaN cells | Classified | BENIGN | ATTACK alerts | Alert rate |
|---:|---:|---:|---:|---:|---:|---:|
| 569 | 22 | 0 | 547 | 544 | **3** | **0.55 %** |

- **All 3 alerts are false positives** (analysis verified against the pcap):
  - **What they were:** the Steam client sent 7 parallel `GET /appinfo/<id>/sha/<hash>.txt.gz` requests over plain HTTP to `clientconfig.akamai.steamstatic.com` (`92.226.1.27:80`) at 16:10:40. All received `200 OK` with small gzip files (0.8–3.7 kB).
  - **The 7 flows are nearly identical:** server initial window `Init_Win_bytes_backward = 507`, client window 64,240, port 80, about 101 ms duration, 2 PSH flags.
  - **Why the tree flagged them:** its first splits route all 7 into the region "small server initial window (235 < 507 ≤ 1,146) **and** destination port ≤ 85". In training, that region holds attacks: Brute Force/XSS servers had small windows (235/236/1,150), and every attack targets port 80.
  - **Why only 3 of 7:** the final verdict comes from a split at **depth 15** on packet-length features. The unpruned tree flags 3 of the 7 near-identical flows and lets 4 pass, which shows overfitting to very fine splits.
- **Latency:**
  - Classifying one flow at a time takes 14.2 ms on average (median 13.5 ms) in the group's recorded run; an earlier run measured 11.6 ms, so expect run-to-run variance. That is per-call pandas/sklearn overhead, against 0.67 ms per 1,000 flows when batched.
  - In practice, detection delay is dominated by CICFlowMeter: it emits a flow only when the flow ends (FIN/RST) or times out (5 s activity, 120 s flow timeout).
- **Honest scope note:** "real time" here means streaming the flows of a recorded capture through the detector, flow by flow. It is not live packet capture.

### 8.5 Figures & screenshots for Task 4

| File | Suggested caption |
|---|---|
| `outputs/task4/figures/cm_binary_dt_default.pdf` | Confusion matrix of the Decision Tree (binary): all 643 attacks detected, 18 false positives. |
| `outputs/task4/figures/cm_multiclass_dt_default.pdf` | Confusion matrix of the Decision Tree (4 classes): Brute Force and XSS are frequently confused. |
| `outputs/task4/figures/cm_multiclass_lr_default.pdf` | Logistic Regression (4 classes) predicts almost everything as BENIGN: 98.5 % accuracy, 0 attacks detected. |
| `outputs/task4/figures/cm_binary_lr_balanced.pdf` | Balanced Logistic Regression: 99 % attack recall at the cost of 2,075 false alarms. |
| `SS/SS1.png`–`SS/SS8.png` | Terminal output of the training run, one model per screenshot. |
| `SS/SS9.png` | Comparison table of all 8 models. |
| `SS/SS10.png`, `SS/SS11.png` | Test results after training (13 unit tests, 2 full-dataset tests). Superseded by SS13/SS14. |
| `SS/SS12.png` | **Real-time detector output:** streamed flow verdicts, the summary (569 read, 22 dropped, 547 classified, 3 alerts = 0.55 %) and the 3 alerts in red. |
| `SS/SS13.png` | Final unit tests: **21 passed**. |
| `SS/SS14.png` | Final full-dataset tests: **3 passed** (Task 3 numbers, Task 4 regression guards, real-time parity). |
| `SS/SS15.png` | Wireshark protocol hierarchy of `task1_lab2.pcapng`: IPv4 99.9 % (81,060 of 81,110 packets), IPv6 24 packets (Task 1). |
| `SS/SS16.png` | **Pending:** a CICFlowMeter offline-conversion screenshot from the teammate who ran Task 1/2. The report reserves a placeholder box for it. |
| `SS/SS17.png` | `task2_lab2.pcap_Flow.csv` in LibreOffice Calc, columns A–M (Task 1/2). |
| `SS/SS18.png` | Wireshark, filter `ip.addr==92.226.1.27 && http`: the 7 Steam `GET /appinfo/…` requests and their `200 OK` responses (false-positive evidence). |
| `SS/SS19.png` | Pre-processing console output: raw label summary (Task 3). |
| `SS/SS20.png` | Pre-processing console output: the 6 cleaning steps with counts (Task 3). |
| `SS/SS21.png` | Pre-processing console output: final label summary and the 70/30 split counts (Task 3). |
| `SS/SS22.png` | Pre-processing console output: top-20 features by chi2, binary (Task 3). |
| `SS/SS23.png` | Pre-processing console output: top-20 features by chi2, multiclass (Task 3). |
| `outputs/realtime/run_log.txt` | Full real-time detector output (all 547 verdict lines and the summary); SS12 shows its end. |

### 8.6 Discussion points (Task 4)
1. **The Decision Tree beats Logistic Regression clearly** on both targets: binary attack-F1 0.986 vs. at best 0.788, multiclass macro-F1 0.729 vs. 0.319.
   - Attacks are characterized by *specific value ranges* of a few features (small TCP windows, port 80, flag counts). A tree isolates these with axis-aligned thresholds.
   - LR draws one linear boundary through heavy-tailed, min-max-compressed features and cannot.
2. **Accuracy paradox.** Multiclass LR default reaches 98.54 % accuracy while detecting **zero** attacks (macro-F1 0.248). On data that is 98.7 % BENIGN, accuracy is not a meaningful metric.
3. **Class weighting is a trade-off, not a fix.**
   - For LR, `balanced` raises attack recall from 0.85 to 0.99 but lowers precision from 0.73 to 0.23: false alarms grow 10× (201 to 2,075).
   - For the DT, it hardly changes the binary result and *lowers* multiclass macro-F1 (0.729 to 0.564).
4. **Brute Force and XSS are hard to separate:** 103 Brute Force flows are predicted as XSS and 97 XSS flows as Brute Force.
   - Both are automated HTTP requests from the same client to the same DVWA server.
   - Flow-level statistics cannot see the HTTP payload, which is the only thing that really differs.
5. **SQL Injection results are statistically weak.** There are only 6 test flows, and the DT default gets 5 of them right. One flow more or less changes the F1 by about 0.1.
6. **Domain shift and shortcut features (real-time result).**
   - On our own benign traffic the false-positive rate is 0.55 %, about **15× higher** than on the CIC-IDS2017 test split (0.037 %).
   - The false alarms are exactly the shortcut features found in Task 3 at work (`Destination Port`, `Init_Win_bytes_*`), applied to automated plain-HTTP bursts that resemble the Selenium-driven attacks.
   - The model partly learned "automated HTTP to port 80 from a small-window server", not the attack itself.
7. **Limitations:**
   - a single train/test split, without cross-validation
   - an unpruned tree, whose deep, fine splits appear in §8.4
   - our capture contains no attacks, so only the false-positive rate (not the detection rate) can be measured on our network
   - the real-time part replays recorded flows
8. **Improvements (not implemented, outside the task scope):** prune the tree (`max_depth`, `min_samples_leaf`), drop the testbed-specific features (`Destination Port`, `Init_Win_bytes_*`), and add benign traffic from the deployment network to the training data.

---

## 9. Reproducibility

**Environment:**
- Python 3.12.15 (uv-managed venv)
- pandas 3.1.0
- numpy 2.5.4
- scikit-learn 1.9.1
- matplotlib 3.11.2
- pyarrow 26.0.1

**Random seed:** 42 everywhere.

**Commands:**

```bash
cd Lab2
uv sync
uv run python scripts/task3_preprocess.py      # Task 3 (~10 s)
uv run python scripts/task4_train.py           # Task 4: trains + evaluates the 8 models (~1–3 min)
uv run python scripts/realtime_detect.py task2_lab2.pcap_Flow.csv   # Task 4 real-time (~7 s)
uv run pytest -m "not e2e" -q                  # 21 unit tests on a 2,951-row fixture
uv run pytest -m e2e -q                        # 3 full-dataset tests: Task 3 numbers, Task 4 guards, real-time parity
```

**Task 4 / real-time outputs:**
- `outputs/task4/{comparison.csv, metrics.json, report_*.csv, run_log.txt, figures/cm_*.{pdf,png}}`
- `artifacts/models/{8 × *.joblib, meta.json}`
- `outputs/realtime/{predictions.csv, run_log.txt}`

**Task 4 code:**
- `src/lab2ids/{models,evaluate,colmap}.py`
- `src/lab2ids/realtime/detector.py`
- `scripts/{task4_train,realtime_detect}.py`
- `tests/{test_task4,test_realtime}.py`

**Generated files (source of truth):**

| File | Content |
|---|---|
| `outputs/task3/cleaning_report.json` | every cleaning step with counts (§4.1, §4.2) |
| `outputs/task3/label_summary_{raw,clean}.csv` | §2, §4.3 |
| `outputs/task3/describe_train_{before,after}_scaling.csv` | §4.5 (all 60 features) |
| `outputs/task3/feature_scores_{binary,multiclass}.csv` | all 60 chi2 scores + p-values (§4.6) |
| `outputs/task3/figures/*.pdf` / `*.png` | §5 |
| `outputs/task3/run_log.txt` | console summary (screenshot) |
| `artifacts/clean.parquet` | cleaned dataset (164,179 × 62) |
| `artifacts/split_indices.json` | train/test row indices |
| `artifacts/selected_features_{binary,multiclass}.json` | the 20 selected features |

**Code:** `src/lab2ids/{config,data,features}.py`, `scripts/task3_preprocess.py`, `tests/test_task3.py`, `tests/fixtures/make_fixture.py`.

**Final 60 features** (appendix candidate):
- `Destination Port`, `Flow Duration`
- `Total Fwd Packets`, `Total Backward Packets`, `Total Length of Fwd Packets`, `Total Length of Bwd Packets`
- `Fwd Packet Length Max/Min/Mean/Std`, `Bwd Packet Length Max/Min/Mean/Std`
- `Flow Bytes/s`, `Flow Packets/s`, `Flow IAT Mean/Std/Max/Min`
- `Fwd IAT Total/Mean/Std/Max/Min`, `Bwd IAT Total/Mean/Std/Max/Min`
- `Fwd PSH Flags`, `Fwd Header Length`, `Bwd Header Length`, `Fwd Packets/s`, `Bwd Packets/s`
- `Min Packet Length`, `Max Packet Length`, `Packet Length Mean/Std/Variance`
- `FIN/RST/PSH/ACK/URG Flag Count`
- `Down/Up Ratio`, `Average Packet Size`, `Subflow Bwd Bytes`
- `Init_Win_bytes_forward`, `Init_Win_bytes_backward`, `act_data_pkt_fwd`, `min_seg_size_forward`
- `Active Mean/Std/Max/Min`, `Idle Mean/Std/Max/Min`

---

## 10. LaTeX notes

- **Escape underscores in feature names,** e.g. `\texttt{Init\_Win\_bytes\_backward}`, `\texttt{min\_seg\_size\_forward}`. Also escape `%` in the share columns.
- **Use the PDF figures** (vector graphics) with `\includegraphics[width=\linewidth]{.../feature_scores_binary.pdf}`.
- **Tables:** `booktabs` (`\toprule/\midrule/\bottomrule`). Right-align numbers, e.g. `siunitx` `S` columns with `group-separator={,}`.
- **Write the label en dash** as `Web Attack -- Brute Force`.
- **Page budget suggestion:** Task 3 ≈ 2–3 pages (§3 method, tables 4.1/4.3/4.6, one figure, §6 discussion). Task 4 ≈ 3–4 pages once done. Task 1/2 ≈ 1–2 pages after the recapture.

---

## 11. References (BibTeX)

```bibtex
@inproceedings{sharafaldin2018cicids,
  author    = {Sharafaldin, Iman and Lashkari, Arash Habibi and Ghorbani, Ali A.},
  title     = {Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization},
  booktitle = {Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP)},
  pages     = {108--116},
  year      = {2018},
  doi       = {10.5220/0006639801080116}
}
@inproceedings{lashkari2017cicflowmeter,
  author    = {Lashkari, Arash Habibi and Draper-Gil, Gerard and Mamun, Mohammad Saiful Islam and Ghorbani, Ali A.},
  title     = {Characterization of Tor Traffic Using Time Based Features},
  booktitle = {Proceedings of the 3rd International Conference on Information Systems Security and Privacy (ICISSP)},
  pages     = {253--262},
  year      = {2017},
  doi       = {10.5220/0006105602530262}
}
@article{pedregosa2011sklearn,
  author  = {Pedregosa, Fabian and others},
  title   = {Scikit-learn: Machine Learning in {P}ython},
  journal = {Journal of Machine Learning Research},
  volume  = {12},
  number  = {85},
  pages   = {2825--2830},
  year    = {2011}
}
@inproceedings{engelen2021troubleshooting,
  author    = {Engelen, Gints and Rimmer, Vera and Joosen, Wouter},
  title     = {Troubleshooting an Intrusion Detection Dataset: the {CICIDS2017} Case Study},
  booktitle = {2021 IEEE Security and Privacy Workshops (SPW)},
  pages     = {7--12},
  year      = {2021},
  doi       = {10.1109/SPW53761.2021.00009}
}
```

**Verified 2026-11-04** against Crossref DOI records and the JMLR page: authors, titles, venues, years and pages all match. DOIs, the Engelen pages and the JMLR issue number were added. The same entries are in `reports/bibliography.bib`.

---

## 12. Open items for the group

1. State why the Thursday WebAttacks file was chosen over the Friday DDoS file (slide 8).
2. ~~Share a new Task 1 capture~~. Done: `task1_lab2.pcapng` / `task2_lab2.pcap_Flow.csv` are clean (§7).
3. ~~Approve the start of Task 4~~. Done (§8).
   - The real-time run and the final tests are recorded in `SS/SS12.png`–`SS/SS14.png`.
4. Decide who presents which task (10 min + 2 min Q&A).
