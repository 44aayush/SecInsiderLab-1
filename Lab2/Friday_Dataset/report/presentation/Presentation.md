# Lab 2 Presentation: CIC-IDS2017 Friday DDoS (Group 8)

**Security Insider Lab I, Uni Passau, Group 8**
Justlyn Kaniyanthara Johnson (121024), Aayush Kapoor (120957), 9 November 2026

Deck: `G8.Lab2.Presentation.pptx` (15 slides). Sources: `G8.Report2.pdf` and the deck speaker notes. Friday data only, no comparison with Thursday. Every number is taken from the report or the deck.

Sections:

1. Slide-by-slide content and speaking script (slides 1 to 15)
2. Top-20 Selected Features (chi2)
3. Glossary
4. Source discrepancies

---

# 1. Slide-by-Slide Content and Speaking Script

## Slide 1. Lab 2: Machine Learning for Network Attack Detection

CIC-IDS2017 Friday DDoS dataset. Security Insider Lab I, Group 8.

| Headline number | Meaning |
|---|---|
| 223,082 | clean CIC-IDS2017 flows, 59 features |
| 0.9996 | DDoS F1 of the Decision Tree (test split) |
| 0 alerts | on our own benign traffic (547 flows) |

**Script.** Lab 2 of the Security Insider Lab: detecting network attacks from flow features with Logistic Regression and Decision Trees. We use the Friday DDoS file of CIC-IDS2017. The three numbers are our main results: a clean set of 223,082 flows with 59 features, a DDoS F1 of 0.9996 for the Decision Tree, and no alert on our own benign capture of 547 flows.

## Slide 2. Four tasks lead from our capture to a detector

| Task | Name | What we do |
|---|---|---|
| 1 | Flows | Capture our own traffic and convert it into flows with CICFlowMeter |
| 2 | Dataset | Analyze CIC-IDS2017: the Friday-afternoon DDoS file |
| 3 | Pre-processing | Clean inf/NaN and duplicates, min-max scale, select 20 features with chi2 |
| 4 | Classifiers | Train LR and Decision Tree, then classify our own flows one by one |

Dataset: `Friday-WorkingHours-Afternoon-DDos.csv`, the file named in the lab slides. Two labels, BENIGN and DDoS, so every model is a binary classifier and the real-time detector flags DDoS.

**Script.** Overview of the four lab tasks. Instead of inspecting packets one by one, we describe each connection by a vector of statistical features, a flow, and train classifiers to tell benign flows from attack flows. For the dataset we follow the lab slides and use the Friday-afternoon DDoS file of CIC-IDS2017. It contains benign flows and DDoS flows, so the problem is binary. The code is in our `ddosids` Python package.

## Slide 3. A flow summarizes one bidirectional exchange

- A flow is keyed by source and destination IP, ports and protocol.
- CICFlowMeter writes 84 columns: metadata, 77 numeric features (packet lengths, inter-arrival times, TCP flags, window sizes, idle/active times) and a label.
- A flow ends on FIN/RST, after 5 s of inactivity (activity timeout) or after 120 s in total (flow timeout).
- Only flows with at least 2 packets are written, so a lone DNS query or traceroute probe never appears.
- Our capture: 81,110 frames over 347.4 s of browsing, DNS and the Steam client (4 Nov 2026), benign by construction.
- CICFlowMeter offline mode: 81,110 packets give 569 flows (570 lines including the header).

**Script.** Explain what a flow is and how CICFlowMeter terminates flows: FIN or RST, 5 s without activity, or 120 s in total. Only flows with at least two packets are written. Our final capture, `task1_lab2.pcapng`, was recorded with Wireshark between 16:05 and 16:10 and converted offline to `task2_lab2.pcap_Flow.csv`; this file is the real-time input later. The screenshot shows the offline conversion with the default timeouts: 81,110 packets read, 81,109 valid, 1 discarded. The reported "Total 570 flows" counts the header line, so there are 569 flows.

## Slide 4. Disabling IPv6 lifted valid flows from 5 % to 96 %

| Capture | Frames | IPv6 frames | Flows | Protocol 0 | Valid TCP/UDP |
|---|---:|---:|---:|---:|---:|
| 1st (since deleted) | 129,548 | 126,904 (98 %) | 532 | 454 | 78 |
| 2nd (since deleted) | 98,780 | 88,458 (89.5 %) | 1,327 | 1,260 | 67 |
| 3rd, IPv6 off (final) | 81,110 | 24 (0.03 %) | 569 | 22 | 547 |

- Symptom: protocol 0, port 0 and impossible IPs in most flows of the first two captures.
- Root cause: `readIP6 = false` is hard-coded in CICFlowMeter (`Cmd.java` line 126, `ReadPcapFileWorker.java` line 152). Every non-IPv4 frame is force-parsed as an IPv4 header from byte 0.
- Fake IPs: 134.221.96.0 = bytes `86 DD 60 00`, the IPv6 EtherType; 136.225.x.x = HomePlug AV (`88 E1`); 8.6.x.x = ARP (`08 06`). The fake destination 0.0.4.214 is the IPv6 flow label and payload length (1238).
- Fix: `sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1` on the capturing laptop, which keeps flows IPv4-only like the training data.

**Script.** Our first two captures were mostly IPv6, with 98 and 89.5 percent IPv6 frames. We traced the bogus flows to CICFlowMeter's hard-coded IPv4-only parsing. We did not enable its IPv6 path, because its UDP branch reads the header length from the TCP header (`PacketReader.java`, line 204). After sysctl disabled IPv6, the share of valid flows rose from 15 and 5 percent to 96 percent (78 of 532, 67 of 1,327, 547 of 569).

## Slide 5. The final capture yields 547 usable flows

| Quantity | Value |
|---|---:|
| Total flows written by CICFlowMeter | 569 |
| TCP flows (protocol 6) | 162 |
| UDP flows (protocol 17) | 385 |
| TCP/UDP flows classified | 547 |
| Protocol-0 flows dropped (ICMP, ARP, IPv6) | 22 |
| Packets in classified flows | 80,705 |
| Top destination ports | 53 (289 flows), 443 (213 flows), 80 (15 flows) |
| Frames that are IPv4 (Wireshark protocol hierarchy) | 99.94 % |

- 289 flows are DNS queries (port 53), 213 go to port 443, 15 to port 80.
- About 70 % of valid flows are UDP: DNS, QUIC, Steam.

**Script.** With IPv6 off, 547 of 569 flows are valid. The 22 protocol-0 flows are 15 real ICMP flows (CICFlowMeter only sets the protocol number for TCP and UDP), 4 left-over IPv6 flows and 3 ARP flows. The classified flows contain 80,705 packets, 99.8 percent of the 80,900 IPv4 TCP/UDP frames; the rest are single-packet exchanges, mostly traceroute probes. More than half of the classified flows are DNS queries, because every query is its own flow. The application mix, QUIC and Steam, and the network differ from the 2017 testbed, so we expect domain shift.

## Slide 6. The Friday file has 57 % attack flows

| Label | Raw | Share | Cleaned | Share |
|---|---:|---:|---:|---:|
| BENIGN | 97,718 | 43.29 % | 95,068 | 42.62 % |
| DDoS | 128,027 | 56.71 % | 128,014 | 57.38 % |
| Total | 225,745 | 100.00 % | 223,082 | 100.00 % |

- 225,745 flows x 79 columns: 78 features and the Label. No flow ID, IP address or timestamp columns, but Destination Port is present.
- Port 80 is the destination of virtually all DDoS flows.
- DDoS is the majority class (56.71 %), yet we still report per-class P/R/F1 and macro-F1.

**Script.** The file has 225,745 flows and 79 columns, with the labels BENIGN, 97,718 flows, and DDoS, 128,027 flows. It is the pre-computed "MachineLearningCSV" file (77 MB) from the Canadian Institute for Cybersecurity. The attack is the majority class, so accuracy is less misleading than on a dataset with a rare attack, but we still report per-class precision, recall and F1, macro-F1 and confusion matrices, never accuracy alone. Virtually all DDoS flows target destination port 80, while benign traffic is spread over several ports, mostly 53, 443 and 80.

## Slide 7. Nine steps turn raw flows into model input

| # | Step | Detail |
|---|---|---|
| 1 | Load and strip names | 65 of 79 column names carry stray spaces; labels already clean |
| 2 | Drop duplicate column | Fwd Header Length appears twice |
| 3 | +-inf to NaN, drop rows | 34 rows: 32 BENIGN, 2 DDoS |
| 4 | Drop duplicate rows | 2,629 rows, before the split so none lands in train and test |
| 5 | Drop constant columns | 10 columns that never change |
| 6 | Drop identical columns | 8 columns (tolerance 1e-6), so the 20 features are distinct |
| 7 | Stratified 70/30 split | On the label, `random_state=42` |
| 8 | Min-max scaling | `MinMaxScaler(clip=True)`, fitted on train only |
| 9 | `SelectKBest(chi2, k=20)` | chi2 needs non-negative input, so scaling comes first |

**Script.** Steps 1 to 6 clean the data and use no labels, so they leak no label information. Steps 7 to 9, in navy on the slide, are fitted on the training split only, so no test statistics leak into training. The infinite and NaN values occur only in Flow Bytes/s and Flow Packets/s, because CICFlowMeter divides by a flow duration that is 0 for some flows: a positive byte count divided by 0 gives infinity, 0/0 gives NaN. The tolerance in step 6 is needed for one pair, Bwd Packet Length Mean and Avg Bwd Segment Size, which differ in 2 rows by at most 1e-6 because of CSV rounding. `clip=True` keeps unseen values, such as live traffic later, inside [0, 1]. The raw data contains negative values (Init_Win_bytes_* is -1 when no window was observed), which is why scaling must precede chi2.

## Slide 8. Cleaning leaves 223,082 flows with 59 features

| # | Step | Rows | Cols | Detail |
|---|---|---|---|---|
| 1 | Drop duplicate header column | 225,745 to 225,745 | 79 to 78 | -1 column (Fwd Header Length.1) |
| 2 | Replace +-inf by NaN | 225,745 to 225,745 | 78 to 78 | inf: Flow Bytes/s 30, Flow Packets/s 34; NaN: Flow Bytes/s 4 |
| 3 | Drop NaN rows | 225,745 to 225,711 | 78 to 78 | -34 rows (32 BENIGN, 2 DDoS) |
| 4 | Drop duplicate rows | 225,711 to 223,082 | 78 to 78 | -2,629 rows (2,618 BENIGN, 11 DDoS) |
| 5 | Drop constant columns | 223,082 to 223,082 | 78 to 68 | -10 columns |
| 6 | Drop identical columns | 223,082 to 223,082 | 68 to 60 | -8 columns |
| | Result | 223,082 | | 223,082 rows x 59 features (60 columns include Label) |

Removed columns:

| Kind | Columns |
|---|---|
| Constant (10) | Bwd PSH Flags, Fwd URG Flags, Bwd URG Flags, CWE Flag Count, Fwd Avg Bytes/Bulk, Fwd Avg Packets/Bulk, Fwd Avg Bulk Rate, Bwd Avg Bytes/Bulk, Bwd Avg Packets/Bulk, Bwd Avg Bulk Rate |
| Identical (8), first kept, second dropped | Fwd PSH Flags to SYN Flag Count; RST Flag Count to ECE Flag Count; Fwd Packet Length Mean to Avg Fwd Segment Size; Bwd Packet Length Mean to Avg Bwd Segment Size; Total Fwd Packets to Subflow Fwd Packets; Total Length of Fwd Packets to Subflow Fwd Bytes; Total Backward Packets to Subflow Bwd Packets; Total Length of Bwd Packets to Subflow Bwd Bytes |

Data quality: Fwd PSH Flags is identical to SYN Flag Count although PSH and SYN are different TCP flags, and six bulk-transfer features are always 0.

**Script.** The raw file has 2,633 duplicate rows, but 4 of them contain infinite or NaN values and are already gone after step 3, so the duplicate step drops 2,629. We lose 34 rows with infinite or NaN values, which is almost no information and introduces no artificial values. Fwd PSH Flags equal to SYN Flag Count points to a feature-extraction problem in the CICFlowMeter version used for CIC-IDS2017, in line with the literature (Engelen, Rimmer and Joosen 2021). After cleaning there are 95,068 BENIGN and 128,014 DDoS flows, so DDoS stays the majority class.

## Slide 9. Packet sizes dominate the top 20 features

| Group | Count | Content |
|---|---:|---|
| Packet sizes | 12 | Forward and backward length statistics, overall maximum, mean, standard deviation, variance, average packet size |
| TCP flag counts | 3 | URG Flag Count, Fwd PSH Flags, PSH Flag Count |
| Backward inter-arrival times | 3 | Bwd IAT Total, Bwd IAT Max, Bwd IAT Std |
| Traffic asymmetry | 1 | Down/Up Ratio |
| Destination Port | 1 | Rank 2, score 28,476 |

Destination Port ranks 2nd. Virtually all DDoS flows target port 80, so a model can learn the port instead of the attack. The full list with scores is in section 2.

**Script.** URG Flag Count leads with a score of 30,058, followed by Destination Port at 28,476 and Bwd Packet Length Max at 22,197. The scores fall steadily down the ranking. Twelve of the 20 features describe packet lengths, which is plausible for a flooding attack, whose requests are likely more uniform than the mix of benign traffic. The chi2 test on min-max-scaled continuous data is only a heuristic: it treats scaled values like frequencies, and heavy-tailed features are squeezed towards 0, which lowers their scores, so the ranking depends on the scaling. We expect testbed-specific features such as the destination port to generalize poorly to other networks.

## Slide 10. Four binary models share one pipeline

Pipeline: `MinMaxScaler(clip=True)`, then `SelectKBest(chi2, k=20)`, then classifier (LR or Decision Tree). One scikit-learn `Pipeline` per model, fitted on the 156,157 training flows and saved with joblib.

| Algorithm | Default | `class_weight="balanced"` |
|---|---|---|
| `LogisticRegression(max_iter=5000)` | binary_lr_default: BENIGN vs. DDoS | binary_lr_balanced: BENIGN vs. DDoS |
| `DecisionTreeClassifier(random_state=42)` | binary_dt_default: BENIGN vs. DDoS | binary_dt_balanced: BENIGN vs. DDoS |

The file has one attack class: 2 algorithms x 2 weightings = 4 binary models.

| Split (stratified 70/30, `random_state=42`) | Train (70 %) | Test (30 %) |
|---|---:|---:|
| BENIGN | 66,547 | 28,521 |
| DDoS | 89,610 | 38,404 |
| Total | 156,157 | 66,925 |

Both LR models converged after 48 iterations (limit 5,000). The Decision Tree is unpruned.

**Script.** A multiclass target would duplicate the binary one, so we train four binary models. Scaler and selector are fitted on the training split only. All models are evaluated on the held-out test split of 66,925 flows, 38,404 of them DDoS. Inference time is the median of five timed predict calls on the whole test split after one warm-up call, scaled to 1,000 flows.

## Slide 11. The Decision Tree makes 32 errors on 66,925 flows

Test split; Prec., Rec., F1 refer to the DDoS class; Macro-F1 averages both classes.

| Model | Acc. | Macro-F1 | Prec. | Rec. | F1 | FP | FN | Fit (s) | Inf. (ms/1k) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LR default | 0.9693 | 0.9683 | 0.9503 | 0.9988 | 0.9739 | 2,008 | 45 | 6.45 | 0.717 |
| LR balanced | 0.9698 | 0.9689 | 0.9511 | 0.9988 | 0.9744 | 1,974 | 45 | 5.97 | 1.996 |
| **DT default** | 0.9995 | 0.9995 | 0.9998 | 0.9993 | 0.9996 | 7 | 25 | 2.20 | 0.695 |
| DT balanced | 0.9995 | 0.9995 | 0.9998 | 0.9993 | 0.9996 | 7 | 25 | 1.25 | 0.717 |

Confusion matrices shown on the slide (rows true, columns predicted):

| binary_dt_default | BENIGN | DDoS |
|---|---:|---:|
| BENIGN | 28,514 | 7 |
| DDoS | 25 | 38,379 |

| binary_lr_balanced | BENIGN | DDoS |
|---|---:|---:|
| BENIGN | 26,547 | 1,974 |
| DDoS | 45 | 38,359 |

**Script.** The default Decision Tree makes 7 false positives and 25 false negatives, which gives a DDoS precision of 0.9998, a recall of 0.9993 and an F1 of 0.9996. Logistic Regression detects 38,359 of 38,404 DDoS flows (recall 0.9988, 45 missed) but raises 2,008 false alarms for the default and 1,974 for the balanced variant, so its DDoS precision is only about 0.95 and its F1 0.974. The Decision Tree beats LR in every metric. Attacks occupy narrow value ranges of a few features (packet lengths, port 80, flag counts), and a tree isolates such ranges with axis-aligned thresholds. LR draws a single linear boundary through heavy-tailed, min-max-compressed features and cannot separate the classes as sharply. Fit and inference times come from a single run each.

## Slide 12. Class weighting changes almost nothing here

- Balanced and default Decision Tree have identical confusion matrices and metrics.
- 57 % : 43 % DDoS to BENIGN after cleaning, so balanced weights are close to one for both classes.
- LR false positives: 2,008 to 1,974, so balancing removes only 34.
- Why `binary_dt_default`: identical to the balanced tree on the test split, so we take the simpler model; fewest errors of all four (7 FP and 25 FN).

**Script.** Because the classes are close to balanced, `class_weight="balanced"` gives both classes weights close to one. For the tree, the balanced variant has exactly the same confusion matrix and metrics as the default one; for Logistic Regression the false positives drop only from 2,008 to 1,974. We use `binary_dt_default` in the real-time part. One caveat: Destination Port is the second-best feature by chi2 and virtually all DDoS flows use port 80, so the near-perfect scores may partly rest on the port as a shortcut.

## Slide 13. Streaming reproduces the offline predictions exactly

Data flow: capture `.pcapng`, CICFlowMeter (offline), map V4 to training columns, drop protocol 0 and set inf/NaN to 0, pipeline gives a verdict per flow.

| Check | Result |
|---|---|
| Test flows streamed through the detector | 66,925: identical to the offline predictions, row for row |
| Batch sizes compared | batches of 1,000 flows, and batches of one flow on the first 500 flows |
| Fast tests | 24 passed, 3 deselected |
| End-to-end tests | 3 passed, 24 deselected (Task 3 numbers, Task 4 regression guards, parity test) |

Same model: the detector loads the saved `binary_dt_default` pipeline unchanged.

**Script.** The detector streams flows one by one in timestamp order, maps the V4 column names to the training names (all 77 features map), drops Protocol 0 rows, replaces infinite and NaN values by 0 and classifies each flow. Training and serving use exactly the same scaling, selection and classifier. The parity test converts the 66,925-flow test split to the V4 column names and streams it through the detector; the predictions equal those of the offline pipeline, and the DDoS F1 recomputed from the streamed predictions equals the offline value. Real time here means replaying a recorded capture; we do not capture live.

## Slide 14. 547 of our flows classified, 0 DDoS alerts

| Quantity | Value |
|---|---:|
| Flows read | 569 |
| Protocol-0 flows dropped | 22 |
| inf/NaN cells replaced | 0 |
| Flows classified | 547 |
| Classified BENIGN | 547 |
| DDoS alerts | 0 |
| Alert rate | 0.00 % |
| Latency per flow, mean (ms) | 13.537 |
| Latency per flow, median (ms) | 12.840 |

- Latency: one flow at a time. Batched, the model needs 0.695 ms per 1,000 flows.
- Benign-only capture: we measure false alarms on our network, but not the detection rate. Whether the model would flag a real DDoS in our flows is untested.
- Domain shift: training flows come from an older CICFlowMeter version on the 2017 testbed; ours come from V4 on a different network with QUIC and Steam traffic.

**Script.** Of 569 flows, 22 were dropped (protocol 0) and 547 were classified, all as BENIGN. No infinite or NaN cells had to be replaced. Our traffic is benign by construction, so every flow is correctly classified and there is no false positive. The per-flow latency is per-call pandas and scikit-learn overhead; in practice the detection delay is dominated by CICFlowMeter, which emits a flow only when it ends (FIN or RST) or times out after 5 s of inactivity or 120 s in total.

## Slide 15. Near-perfect on the test split, detection untested outside the testbed

| Result | Value |
|---|---|
| DDoS F1 of the Decision Tree on the CIC-IDS2017 test split | 0.9996 |
| Alerts on 547 benign flows of our own capture (no attack in it) | 0 |

Takeaways:

- Decision Tree beats LR: F1 0.9996 vs. 0.9744 at best, 7 vs. about 2,000 false alarms.
- Port-80 shortcut: Destination Port ranks 2nd, and virtually all DDoS flows use port 80.
- No false alarms on our traffic, but our capture has no attack, so the detection rate is untested.

Possible improvements (not implemented):

- Prune the tree (`max_depth`, `min_samples_leaf`); we use a single split without cross-validation.
- Remove shortcuts: drop testbed-specific features such as Destination Port (no ablation was run).
- Test further: evaluate on a second attack capture from another network, and add benign traffic from the deployment network to training.

**Script.** Conclusion: the Decision Tree makes only 32 errors on 66,925 test flows, but the test split comes from the same capture as the training data and cannot reveal a shortcut such as the destination port. The 0 alerts on our capture show only that this benign traffic is not mistaken for DDoS. Other limitations: min-max scaling is sensitive to outliers, and dropping infinite rows removes 34 flows including 2 DDoS flows. The improvements are not implemented. Thank you; questions welcome.

---

# 2. Top-20 Selected Features (chi2)

Selected by `SelectKBest(chi2, k=20)` on the min-max-scaled training set, binary target (BENIGN vs. DDoS). Rank and score from report Table 4.5; the order matches `artifacts/selected_features_binary.json`. Definitions are CICFlowMeter's measurements per flow. Fwd = client to server, Bwd = server to client. Packet lengths are in bytes; times in CICFlowMeter are in microseconds (consistent with the report's Table 4.4, where a maximum of 120,000,000 matches the 120 s flow timeout). The report gives no decision-tree importances, so none are listed.

| Rank | Feature | Definition (CICFlowMeter) | chi2 |
|---:|---|---|---:|
| 1 | URG Flag Count | Number of packets in the flow with the TCP URG (urgent) flag set | 30058.11 |
| 2 | Destination Port | Destination (server-side) port of the flow, for example 80 HTTP, 53 DNS, 443 HTTPS | 28476.04 |
| 3 | Bwd Packet Length Max | Largest packet length in the backward direction, in bytes | 22196.57 |
| 4 | Bwd Packet Length Std | Standard deviation of packet lengths in the backward direction, in bytes | 15201.54 |
| 5 | Bwd Packet Length Mean | Mean packet length in the backward direction, in bytes | 13631.13 |
| 6 | Bwd IAT Total | Sum of the inter-arrival times between consecutive backward packets, in microseconds | 10104.71 |
| 7 | Max Packet Length | Largest packet length in the whole flow (both directions), in bytes | 9940.91 |
| 8 | Packet Length Mean | Mean packet length over all packets of the flow, in bytes | 9735.77 |
| 9 | Fwd Packet Length Max | Largest packet length in the forward direction, in bytes | 9338.26 |
| 10 | Packet Length Std | Standard deviation of packet lengths over the whole flow, in bytes | 9282.63 |
| 11 | Average Packet Size | Average size of a packet in the flow, in bytes | 8361.12 |
| 12 | Fwd Packet Length Mean | Mean packet length in the forward direction, in bytes | 8326.59 |
| 13 | Fwd PSH Flags | Number of times the TCP PSH (push) flag is set in forward packets; identical to SYN Flag Count in this file | 7104.49 |
| 14 | Packet Length Variance | Variance of packet lengths over the whole flow (bytes squared) | 6816.96 |
| 15 | Bwd IAT Max | Longest inter-arrival time between two consecutive backward packets, in microseconds | 6626.18 |
| 16 | Fwd Packet Length Std | Standard deviation of packet lengths in the forward direction, in bytes | 6519.34 |
| 17 | PSH Flag Count | Number of packets in the flow with the TCP PSH flag set (training range 0 to 1, mean 0.3556) | 5771.95 |
| 18 | Down/Up Ratio | Ratio of backward (download) to forward (upload) traffic of the flow | 4499.68 |
| 19 | Fwd Packet Length Min | Smallest packet length in the forward direction, in bytes | 3409.00 |
| 20 | Bwd IAT Std | Standard deviation of the inter-arrival times between backward packets, in microseconds | 3351.57 |

What the report supports about why they help (nothing beyond this is claimed):

- Packet-length features (ranks 3, 4, 5, 7 to 12, 14, 16, 19; 12 in total): the report calls this plausible for a flooding attack, whose requests are likely more uniform than the mix of benign traffic.
- Destination Port (rank 2): virtually all DDoS flows target port 80, while benign traffic is spread over ports 53, 443 and 80. It separates the classes but is a testbed-specific shortcut that may generalize poorly.
- Fwd PSH Flags (rank 13): it is identical to SYN Flag Count although PSH and SYN are different flags, which the report reads as a feature-extraction problem in the CICFlowMeter version.
- Down/Up Ratio (rank 18): captures the traffic asymmetry.
- URG Flag Count, PSH Flag Count, Bwd IAT features: the report only states that they are among the top 20 (3 TCP flag counts, 3 backward inter-arrival times); it gives no further reason.
- Caveat for the ranking itself: chi2 on min-max-scaled continuous data is a heuristic, and heavy-tailed features are squeezed towards 0, which lowers their scores.

---

# 3. Glossary

| Short-hand | Full form | Meaning in this lab context |
|---|---|---|
| Acc. | Accuracy | Share of correct predictions; reported only together with per-class P/R/F1, macro-F1 and the confusion matrix |
| ACK | Acknowledgment (TCP flag) | TCP flag confirming received data; one of the flag counts CICFlowMeter records (not among our selected features) |
| ARP | Address Resolution Protocol | Maps IP to MAC addresses; 3 of the 22 protocol-0 flows in our capture are ARP leftovers |
| ASCII | American Standard Code for Information Interchange | Plain-text encoding; the Friday CSV is pure ASCII |
| BENIGN | Benign | Label for normal, non-attack flows; 97,718 raw, 95,068 cleaned |
| Bwd | Backward | Direction server to client (reply packets) in CICFlowMeter feature names |
| chi2 (chi-squared, χ²) | Chi-squared test | Score used by `SelectKBest` to rank features against the label; needs non-negative input, so it runs after min-max scaling |
| CIC | Canadian Institute for Cybersecurity | University of New Brunswick institute that created CIC-IDS2017 and CICFlowMeter |
| CIC-IDS2017 | CIC Intrusion Detection Systems dataset 2017 | Labeled flow dataset; we use its Friday-afternoon DDoS file |
| CICFlowMeter | CIC Flow Meter | Tool that turns a packet capture into one row of flow features per flow |
| class_weight="balanced" | Class weighting | Classifier option that weights classes inversely to their frequency; changes almost nothing here because the classes are near-balanced |
| clip=True | Clipping option of `MinMaxScaler` | Keeps values outside the training min/max inside [0, 1], for example live traffic |
| CRLF | Carriage Return + Line Feed | Windows line endings used in the raw CSV |
| CSV | Comma-separated values | Format of the dataset and of the CICFlowMeter output (`task2_lab2.pcap_Flow.csv`) |
| CWE | Congestion Window Reduced (TCP flag) | `CWE Flag Count` is one of the 10 constant columns that are dropped |
| DDoS | Distributed Denial of Service | The attack class in the Friday file; 128,027 raw, 128,014 cleaned flows |
| DNS | Domain Name System | Name resolution; 289 of our 547 classified flows are DNS queries to port 53 |
| Down/Up Ratio | Download/upload ratio | Ratio of backward to forward traffic of a flow; selected feature, rank 18 |
| DT | Decision Tree | `DecisionTreeClassifier(random_state=42)`, unpruned; best model, DDoS F1 0.9996 |
| e2e | End-to-end (test) | The 3 slow tests on the full CSV: Task 3 numbers, Task 4 regression guards, real-time parity |
| ECE | ECN-Echo (TCP flag) | `ECE Flag Count` is identical to `RST Flag Count` in this file, so one of them is dropped |
| EtherType | Ethernet type field | 2-byte field naming the protocol of a frame (0x86DD IPv6, 0x0806 ARP, 0x88E1 HomePlug AV); misread as an IP address by CICFlowMeter for non-IPv4 frames |
| F1 | F1 score | Harmonic mean of precision and recall; here for the DDoS class unless stated |
| FIN | Finish (TCP flag) | Connection teardown; together with RST it ends a flow in CICFlowMeter |
| FN | False negative | DDoS flow predicted as BENIGN; 25 for the DT, 45 for LR |
| FP | False positive | BENIGN flow predicted as DDoS; 7 for the DT, 2,008 / 1,974 for LR |
| Fwd | Forward | Direction client to server in CICFlowMeter feature names |
| G8 | Group 8 | Our lab group (Justlyn Kaniyanthara Johnson, Aayush Kapoor) |
| HomePlug AV | HomePlug Audio/Video powerline standard | Non-IPv4 frames (EtherType 0x88E1) in our capture that CICFlowMeter mis-parsed as fake IPs 136.225.x.x |
| HTTP | Hypertext Transfer Protocol | Web protocol on port 80; virtually all DDoS flows target port 80; 26 HTTP frames in our capture |
| HTTPS | HTTP Secure | HTTP over TLS, port 443; 213 of our flows go to port 443 |
| IAT | Inter-arrival time | Time between consecutive packets; `Bwd IAT Total/Max/Std` are selected features |
| ICMP | Internet Control Message Protocol | 15 of the 22 protocol-0 flows are real ICMP flows; CICFlowMeter sets protocol numbers only for TCP and UDP |
| IDS | Intrusion Detection System | System that flags attacks; the subject of the lab |
| inf | Infinity (+inf) | Appears in Flow Bytes/s and Flow Packets/s when the flow duration is 0; replaced by NaN and the rows dropped in training, set to 0 in real time |
| IPv4 | Internet Protocol version 4 | The only IP version CICFlowMeter parses correctly; 99.94 % of our final capture |
| IPv6 | Internet Protocol version 6 | CICFlowMeter does not parse it (`readIP6 = false`), which produced bogus flows until we disabled IPv6; 24 IPv6 frames (0.03 %) remain |
| ISCX | Information Security Centre of Excellence (University of New Brunswick) | Naming scheme of the training columns (CICFlowMeter V3); the detector maps V4 column names to it |
| joblib | joblib library | Python library used to save and load the trained scikit-learn pipelines |
| k | Number of selected features | `k=20` in `SelectKBest(chi2, k=20)` |
| LR | Logistic Regression | `LogisticRegression(max_iter=5000)`; DDoS F1 0.9739 / 0.9744, about 2,000 false alarms |
| Macro-F1 | Macro-averaged F1 | Unweighted mean of the F1 of both classes (BENIGN, DDoS) |
| max_iter | Maximum iterations | LR solver limit, 5,000; both LR models converged after 48 iterations |
| Min / Max / Mean / Std | Minimum / maximum / mean / standard deviation | Statistics in feature names, for example Fwd Packet Length Min, Bwd Packet Length Std |
| MinMax | Min-max scaling (`MinMaxScaler`) | Maps each feature to [0, 1] using training min and max; fitted on train only |
| ms/1k | Milliseconds per 1,000 flows | Batched inference time in Table 5.1 (DT default 0.695) |
| NaN | Not a Number | Missing or undefined value (0/0); 4 in Flow Bytes/s; rows containing inf/NaN are dropped (34 rows) |
| P / R (Prec., Rec.) | Precision / Recall | Precision = TP/(TP+FP), recall = TP/(TP+FN), for the DDoS class |
| PCAP / pcapng | Packet capture file formats | Format of the recorded traffic; `task1_lab2.pcapng` is the Wireshark capture of 81,110 frames |
| Pipeline | scikit-learn `Pipeline` | One object chaining `MinMaxScaler(clip=True)`, `SelectKBest(chi2, k=20)` and the classifier; the detector loads it unchanged |
| Protocol 0 | Protocol number 0 | CICFlowMeter marks non-TCP/UDP flows (ICMP, ARP, IPv6 leftovers) with it; the detector drops all 22 |
| PSH | Push (TCP flag) | Asks the receiver to pass data to the application at once; `Fwd PSH Flags` and `PSH Flag Count` are selected features |
| QUIC | QUIC transport protocol | UDP-based protocol of our browsing traffic (29,682 frames); part of the application mix that differs from 2017 |
| rs | `random_state` | Random seed 42 for the stratified split and the Decision Tree |
| RST | Reset (TCP flag) | Abrupt connection end; ends a flow in CICFlowMeter; `RST Flag Count` is identical to `ECE Flag Count` and dropped |
| SelectKBest | scikit-learn feature selector | Keeps the k highest-scoring features, here by chi2 |
| sklearn | scikit-learn | Python machine-learning library used for scaling, selection, LR and DT |
| SS | Screenshot (SS15, SS27, ...) | Numbered screenshots saved in `SS/` and used in the report |
| SYN | Synchronize (TCP flag) | Connection setup; `SYN Flag Count` is identical to `Fwd PSH Flags` and is dropped |
| TCP | Transmission Control Protocol | 162 TCP flows (protocol 6) in our capture |
| TLS | Transport Layer Security | Encryption layer of HTTPS; 11,994 TLS frames in our capture |
| TN | True negative | BENIGN flow predicted as BENIGN; 28,514 for the DT |
| TP | True positive | DDoS flow predicted as DDoS; 38,379 for the DT |
| UDP | User Datagram Protocol | 385 UDP flows (protocol 17); about 70 % of valid flows |
| URG | Urgent (TCP flag) | `URG Flag Count` is the top-ranked feature (chi2 30058.11) |
| uv | uv (Python package and project manager) | Tool that manages the project's environment and dependencies (`uv run`) |
| V3 / V4 | CICFlowMeter version 3 / version 4 | Training data comes from an older version (V3) on the 2017 testbed; our flows come from V4; source of domain shift and the column-name mapping |
| Wireshark | Wireshark | Packet-capture tool used to record `task1_lab2.pcapng` and to show its protocol hierarchy |

---

# 4. Source Discrepancies

The report and the deck agree on all numbers checked (label counts, cleaning counts, split, chi2 scores, confusion matrices, metrics, real-time results). Minor differences only:

- Slide 4 title says valid flows rose "from 5 % to 96 %"; the report (and the slide-4 notes) say "from 15 % and 5 % to 96 %" (78/532 and 67/1,327). Use the report wording when speaking.
- Table 4.1 of the report numbers the cleaning steps 1 to 6 (duplicate column, replace inf, drop NaN rows, duplicate rows, constant, identical), while the report text and the deck use nine steps with "Load" as step 1 and inf/NaN as one step. Content is the same.
- The deck shows no accuracy, fit or inference columns; those come from report Table 5.1. The report gives no Decision Tree feature importances, so none are in section 2.
