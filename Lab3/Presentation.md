# Lab 3 Speaking Script: DDoS Detection with ML/DL and Enforcement with eBPF/XDP

- **Date:** 2026-11-25, Security Insider Lab, Uni Passau, group 8
- **Speakers:** Aayush (detection, Tasks 1-3, slides 1-9 and half of 14), Justlyn (XDP, Tasks 4-5, slides 10-13 and half of 14)
- **Total spoken time:** 8:08 (1057 words; limit 9:00, leaving 1:00 of the 10-minute slot as buffer)
- **Pacing basis:** 130 words per minute, Script blocks only. On-screen text, takeaways and Q&A are not counted.
- **Speaker notes:** the "Speaker notes (if asked)" blocks are backup only. They are not spoken and not counted in the 9 minutes.
- Slide order and titles follow `report/ppt/G8.Lab3.Presentation.pptx` (14 slides).

## Timing table

| Slide | Title | Speaker | Words | Time | Cumulative |
|---|---|---|---:|---:|---:|
| 1 | Lab 3: ML and DL Detection of DDoS, Enforced with eBPF/XDP | Aayush | 61 | 0:28 | 0:28 |
| 2 | From detection to enforcement | Aayush | 68 | 0:31 | 1:00 |
| 3 | Dataset and preprocessing | Aayush | 101 | 0:47 | 1:46 |
| 4 | Task 1: five classical classifiers | Aayush | 88 | 0:41 | 2:27 |
| 5 | Task 2: MLP, LSTM and 1D-CNN | Aayush | 95 | 0:44 | 3:11 |
| 6 | Task 3: all eight models on the test set | Aayush | 56 | 0:26 | 3:36 |
| 7 | Errors tell the models apart, not accuracy | Aayush | 48 | 0:22 | 3:59 |
| 8 | ROC curves: zoomed in | Aayush | 58 | 0:27 | 4:25 |
| 9 | Cost: training and prediction time | Aayush | 59 | 0:27 | 4:53 |
| 10 | Task 4: eBPF and XDP in one slide | Justlyn | 91 | 0:42 | 5:35 |
| 11 | Limit of 100 packets/s per source holds | Justlyn | 91 | 0:42 | 6:17 |
| 12 | The block list bridges ML and XDP | Justlyn | 75 | 0:35 | 6:51 |
| 13 | Task 5: xdp-tools built from source | Justlyn | 68 | 0:31 | 7:23 |
| 14 | Conclusion and limitations | Aayush, then Justlyn | 98 | 0:45 | 8:08 |
| | **Total** | | **1057** | **8:08** | |

---

## Slide 1. Lab 3: ML and DL Detection of DDoS, Enforced with eBPF/XDP
**Speaker:** Aayush

**On screen**
- 8 models on 33,463 test flows
- XGBoost: 0 errors
- 500 of 679,608 flood packets reach the victim

**Script**
A flood of nearly seven hundred thousand packets hits a server, and only five hundred get through. How? That is our Lab 3, group 8. The first half is detection: eight machine learning and deep learning models on DDoS traffic. The second half is enforcement: dropping attack packets inside the kernel with eBPF and XDP. I take detection, Justlyn takes XDP.

**Takeaway:** One lab, two halves: detect, then enforce.

**Speaker notes (if asked)**
- Why two halves? A detector only labels flows; XDP drops packets early in the kernel. The block list is where they meet (slide 12).
- Why 500 of 679,608? The limit is 100 packets/s per source for 5 s, so exactly 500 pass (slide 11).
- Is XGBoost's 0 errors proof of a perfect detector? No. It is one dataset, one day, one split, with a port-80 shortcut (slide 3).

## Slide 2. From detection to enforcement
**Speaker:** Aayush

**On screen**
- Tasks 1-3: data, 5 classical models, 3 neural networks, comparison
- Tasks 4-5: eBPF/XDP filter, xdp-tools
- The block list is the bridge

**Script**
Five tasks, one story. In tasks one to three we clean the CIC-IDS2017 Friday DDoS file, train five classical models and three neural networks, and compare all eight. In tasks four and five, Justlyn presents our XDP rate limiter and the xdp-tools collection. The bridge between the halves is a block list, where a detector hands over a flagged source. The whole detection pipeline runs with one command.

**Takeaway:** The detector decides, XDP enforces.

**Speaker notes (if asked)**
- Why does one command matter? `python script/main.py` runs preprocess, classifiers, networks and comparison, so every number is reproducible from the output files.
- What exactly is the bridge? The `rl_block` map of the XDP program, which the report calls the interface for an IDS/ML model. Nothing trained is connected yet.
- Why Tasks 4-5 after Tasks 1-3? Project decision: detection first, then enforcement.

## Slide 3. Dataset and preprocessing
**Speaker:** Aayush

**On screen**
- 225,745 raw flows to 223,082 clean flows; 78 to 59 features
- 34 inf/NaN rows, 2,629 duplicates, 10 constant and 9 identical columns
- Stratified 70/15/15 split, seed 42
- Caveat: 128,011 of 128,014 DDoS flows use port 80

**Script**
The data: 225,745 flows with 78 features. Cleaning removes 34 rows with infinite or NaN values and 2,629 duplicates. Duplicates go on purpose, because identical flows in both train and test would inflate the scores. Ten constant and nine identical columns go too. That leaves 223,082 flows with 59 features. We split 70, 15, 15, stratified, so the test set holds 33,463 flows, and the scaler sees training data only. One caveat: 128,011 of 128,014 DDoS flows target port 80. The destination port is a shortcut. We kept it and ran no ablation, so read every score with that in mind.

**Takeaway:** Clean, leak-free data, with one honest shortcut.

**Speaker notes (if asked)**
- Why 70/15/15 and not 70/30? The validation set drives early stopping (XGBoost and the three networks), so the test set stays unbiased. The split is stratified with seed 42, so each part keeps the class ratio (DDoS about 57 %).
- Why remove duplicates? Otherwise identical flows sit in both train and test and inflate the scores. The comparison uses the full row including the label: 2,629 rows (2,618 BENIGN, 11 DDoS).
- Why atol 1e-6 for identical columns? `Avg Bwd Segment Size` is a twin that differs in 2 rows by less than 1e-6, so an exact comparison would miss it.
- Why StandardScaler fitted on train only? So nothing from val or test leaks into training. All eight models get the same scaled arrays; trees and Naive Bayes are not hurt by scaling, and one data path keeps the pipeline simple.
- Why keep the port feature? It is a legitimate flow feature and the lab asked for no feature selection. We did no ablation, so the scores may partly reflect the shortcut; the report lists this as limitation 1.

## Slide 4. Task 1: five classical classifiers
**Speaker:** Aayush

**On screen**
- Suggested: GNB, Gradient Boosting, AdaBoost, KNN, SVM
- Ours: GNB, LR, KNN, RF, XGBoost
- Fixed hyper-parameters; only XGBoost uses the validation set

**Script**
Task one suggested Naive Bayes, Gradient Boosting, AdaBoost, KNN and SVM, but allows our own picks. We kept Naive Bayes and KNN, and chose Logistic Regression, Random Forest and XGBoost. That covers probabilistic, linear, instance-based, bagging and boosting. Gradient Boosting, AdaBoost and SVM were not trained; XGBoost already is gradient boosting. Hyper-parameters are fixed, with no search. Only XGBoost sees the validation set, for early stopping after 20 rounds. One detail: KNN with k equal to five gives only six distinct scores, so its ROC curve is coarse.

**Takeaway:** Five diverse model families, no tuning tricks.

**Speaker notes (if asked)**
- Why these five? Project choice for diversity: probabilistic (Naive Bayes), linear (LR), instance-based (KNN), bagging (RF), boosting (XGBoost). Why no Gradient Boosting, AdaBoost or SVM? The task allows an own selection; XGBoost is already gradient boosting, and the report says they were not trained.
- Why the 0.5 threshold? Every model outputs P(DDoS) and predicts DDoS above 0.5, the same rule as scikit-learn's `predict`.
- Why no hyper-parameter search? Parameters are fixed (the table in the report); the small exceptions are the epoch caps and the LSTM settings (slide 5).
- Why are validation scores optimistic? XGBoost stops on validation log-loss after 20 rounds, so the val set was used for selection; the test scores are the figures to trust.
- Why is KNN's ROC coarse? With k = 5 its scores take only six values.

## Slide 5. Task 2: MLP, LSTM and 1D-CNN
**Speaker:** Aayush

**On screen**
- MLP 59-128-64-1; LSTM and 1D-CNN read the 59 features as a sequence
- Early stopping on validation loss
- LSTM: clip 1.0, lr 5e-4, patience 7; F1 0.9943 to 0.9992

**Script**
Task two: MLP, LSTM and 1D-CNN, all on the same 59 standardized features. Flow features have no natural order, so the LSTM and CNN read pseudo-sequences, because the task asks for them. Early stopping on validation loss restores the best epoch. The LSTM was unstable: its training loss spiked. We added gradient clipping at 1.0, a learning rate of five times ten to the minus four, and patience 7, chosen by lowest validation loss. F1 rose from 0.9943 to 0.9992. The validation loss still oscillates, so clipping reduces the problem but does not remove it.

**Takeaway:** The LSTM needed tuning, chosen on validation data.

**Speaker notes (if asked)**
- Why pseudo-sequences? Flow features have no natural order. LSTM and CNN treat the 59-feature vector as a sequence because the task asks for these models; the data is not sequential.
- Why was the LSTM unstable? Probably exploding gradients over the 59-step sequence on heavy-tailed inputs (training loss spiked; 101 FP, 118 FN, F1 0.9943). Clipping the gradient norm at 1.0 limits the size of one update, so a spike cannot throw the weights far.
- Why are the LSTM settings credible? They were chosen by lowest validation loss over three configurations (0.00529 vs 0.00567 vs 0.00720), not by test scores. Earlier LSTM variants' test scores were known when we decided to tune, which the report admits.
- Was the test set ever used for a choice? Yes, the first epoch limits for MLP and CNN were chosen on test metrics. We re-justified them on validation evidence; the effect was small (MLP F1 0.9994 to 0.9995). The report discloses this as limitation 4.
- Is the LSTM now stable? Not fully: the validation loss still oscillates, so clipping reduces the instability without removing it.

## Slide 6. Task 3: all eight models on the test set
**Speaker:** Aayush

**On screen**
- Comparison table, 33,463 test flows, sorted by F1
- XGBoost 0 FP / 0 FN; Gaussian NB weakest (327 FP)

**Script**
Here are all eight on 33,463 test flows, sorted by F1. XGBoost makes no error. Random Forest and KNN follow, then MLP, LSTM and CNN. Logistic Regression has 44 false positives. Naive Bayes is weakest: 327 false alarms and precision 0.9832, though its recall stays at 0.9986. When everything sits near one, accuracy hides the story.

**Takeaway:** Near-perfect everywhere; Naive Bayes raises the most false alarms.

**Speaker notes (if asked)**
- Why DDoS as positive class? Missed attacks (FN) and false alarms (FP) are then read directly from the confusion matrix.
- Why is Naive Bayes weakest? It makes 327 false alarms (precision 0.9832) while recall stays 0.9986; its errors are mostly false positives.
- Why not report accuracy alone? Everything lies between 0.9895 and 1.0000, so accuracy hides the differences; the table also gives Precision, Recall, F1, Macro-F1, ROC-AUC and TP/TN/FP/FN.
- Are these test scores biased by early stopping? No: the test set was not used for early stopping; the val scores are the optimistic ones.

## Slide 7. Errors tell the models apart, not accuracy
**Speaker:** Aayush

**On screen**
- Errors (FP+FN): XGBoost 0, RF 3, KNN 6, MLP 18, LSTM 32, CNN 33, LR 67, GNB 353
- Log-scale bars

**Script**
So we count errors. XGBoost zero, Random Forest three, KNN six. The networks make 18, 32 and 33. Logistic Regression 67, Naive Bayes 353. The axis is logarithmic. A gap of a few errors is within noise; the gap between the tree models and Naive Bayes is not.

**Takeaway:** Compare error counts, not accuracy.

**Speaker notes (if asked)**
- Why log-scale bars? Error counts range from 0 to 353, so a linear axis would flatten the small ones.
- Is XGBoost really better than Random Forest? Not reliably: 0 vs 3 errors is within what another seed or split could change (limitation 2).
- Why prefer errors over accuracy? For a detector, false alarms and missed attacks decide which model to prefer, more than accuracy does.

## Slide 8. ROC curves: zoomed in
**Speaker:** Aayush

**On screen**
- AUC 1.0000: RF, XGBoost, MLP, LSTM, CNN; 0.9999: LR, KNN; 0.9880: GNB
- Log-x axis, FPR 0 clipped at 1e-5

**Script**
ROC curves, zoomed in. AUC is 1.0000 for five models, 0.9999 for Logistic Regression and KNN, and 0.9880 for Naive Bayes. On the log axis, a false-positive rate of zero is clipped at ten to the minus five. Naive Bayes needs a false-positive rate near 0.02 to catch almost every attack. KNN's curve has few points, as announced.

**Takeaway:** Zoom in to see differences that full axes hide.

**Speaker notes (if asked)**
- Why zoom the ROC? A plain plot shows eight curves hugging the top-left corner; the zoom separates them.
- Why a log-x axis? It stresses the low false-alarm region that matters for a detector. FPR 0 cannot be drawn on a log axis, so it is clipped at 1e-5 (one false positive is about 7e-5).
- Why is the KNN curve coarse? Its scores take only six values, so few distinct points.
- Why is AUC 1.0000 for five models yet errors differ? AUC is rounded to four decimals and measures ranking, while the error counts apply the 0.5 threshold.

## Slide 9. Cost: training and prediction time
**Speaker:** Aayush

**On screen**
- Train: GNB 0.063 s, XGBoost 2.021 s, RF 3.847 s, MLP 42.244 s, CNN 65.544 s, LSTM 136.034 s
- KNN predict 4.204 s

**Script**
Cost. Naive Bayes trains in 0.063 seconds, XGBoost in 2, Random Forest in 3.8. The networks cost most: MLP 42, CNN 66, LSTM 136 seconds. KNN trains in 0.008 seconds but needs 4.2 seconds to predict, against at most 0.173 for the others. One run, order of magnitude only. That was detection. Justlyn, how do we stop the flood?

**Takeaway:** Trees are accurate and cheap; networks cost more for no gain.

**Speaker notes (if asked)**
- Why is KNN training so cheap? It only stores the data; the cost moves to prediction (4.204 s).
- Why does prediction cost matter? A detector must decide quickly, and KNN is the slowest there.
- Can we compare the times strictly? No; they come from a single run and show the order of magnitude only.

## Slide 10. Task 4: eBPF and XDP in one slide
**Speaker:** Justlyn

**On screen**
- eBPF: sandboxed kernel programs, verifier, maps
- XDP: hook in the driver before sk_buff; five actions
- Our filter: per-source-IP rate limiter with allow/block lists

**Script**
Thanks. eBPF runs small sandboxed programs inside the kernel; the verifier checks every path, and maps share state with user space. XDP hooks into the network driver before the kernel allocates an sk_buff, so dropping is cheap. It has five actions: drop, pass, transmit, redirect, aborted. Our filter is a per-source-IP rate limiter with allow and block lists. For each IPv4 packet it checks the lists, counts packets per source in a fixed window, and drops everything above the limit. Limit, window and lists live in maps and change at runtime.

**Takeaway:** Drop attack packets before the kernel does any work.

**Speaker notes (if asked)**
- Why XDP for DDoS? It runs in the driver before sk_buff allocation, so dropping is cheap.
- Generic vs native? Native runs in the driver's NAPI loop (veth supports it); generic runs after sk_buff allocation, is driver-independent and slow, good for testing. A third mode, offloaded, runs on a SmartNIC.
- Why a rate limiter? A flood sends far more packets per second from a source than a legitimate client, so counting per source address and dropping above a limit stops it.
- Why bounds checks everywhere? Without a check against `data_end` before each header access the verifier rejects the program.

## Slide 11. Limit of 100 packets/s per source holds
**Speaker:** Justlyn

**On screen**
- Four namespaces: attacker, benign client, victim, bridge; 5 s SYN flood; limit 100 pkt/s
- Baseline 331,744 sent / 331,745 received; generic 679,608 / 500; native 613,271 / 500; iproute2 383,335 / 300

**Script**
We tested in four network namespaces: attacker, benign client, victim and bridge. The attacker runs a five-second SYN flood; the limit is 100 packets per second per source. Without XDP, 331,744 flood packets are sent and 331,745 arrive. With the limiter in generic mode, 679,608 are sent and exactly 500 arrive: 100 per second for five seconds. Native mode: 613,271 sent, 500 arrive. Loading with iproute2 for 3 seconds: 383,335 sent, 300 arrive. The benign client loses no pings. Caveat: everything shares one host, so this is not a throughput benchmark.

**Takeaway:** The limit holds exactly, and benign traffic is untouched.

**Speaker notes (if asked)**
- Why `rl_state` as LRU_HASH? It can never become full: at capacity the least recently used source is evicted, whereas a plain hash would refuse new entries, which an attacker could exploit. It holds 65,536 entries.
- Why shared state and not per-CPU counters? With receive-side scaling one source's packets can spread over several CPUs, and per-CPU counters would raise the effective limit to limit times the number of CPUs. The map dump showed drops on three CPUs. The global stats use a per-CPU array so the hot path needs no atomics there.
- Why a fixed window? It is simple and cheap, but up to twice the limit can pass around a window boundary; a token bucket would smooth that.
- Why did the attacker send about twice as many packets with the filter on? We attribute it to CPU time the victim's stack no longer spends on every SYN, since all namespaces share one host. Drop rates are limited by hping3, so this is no XDP throughput measurement.
- Why 331,745 received vs 331,744 sent? One-packet differences between hping3 and kernel counters are within counting granularity.

## Slide 12. The block list bridges ML and XDP
**Speaker:** Justlyn

**On screen**
- Block-list map: a detector inserts a source address
- Phase 6: attacker 100% loss, benign 0%; limit raised to 1,000 at runtime
- No trained model connected yet

**Script**
The block list connects detection to enforcement. When a classifier flags a source, user space writes the address into the map, and the next packet is dropped in the driver. So classifier latency counts once per flow, not per packet. In phase six we raised the limit to 1,000 at runtime without reloading, then blocked the attacker: 100 percent ping loss, benign client zero. Honest limit: no trained model is connected to the map yet.

**Takeaway:** The interface exists; the model is not plugged in yet.

**Speaker notes (if asked)**
- Why is spoofing a problem? Per-source limiting assumes the source IP identifies the sender. A flood with random spoofed sources sends one or two packets per address and is never limited. Real systems add aggregate limits, SYN cookies and signature rules.
- IPv4 only? Yes; IPv6 is passed unfiltered, and non-IPv4 frames are passed and counted.
- How would the detector feed the block list? A user-space classifier scores each flow and writes the flagged source into `rl_block` with `bpf_map_update_elem` or `bpftool`; the next packet is dropped. This is not built yet.
- Why can the limit change without reload? The program reads `rl_config` on every packet, so a map update takes effect on the next packet.

## Slide 13. Task 5: xdp-tools built from source
**Speaker:** Justlyn

**On screen**
- Commit 92a98287fd59, clang 21.1.8, bpftool v7.7.0; make without errors
- install_and_verify.sh: ALL CHECKS PASSED
- Manual check on loopback with xdp-filter

**Script**
Task five: xdp-tools. We cloned commit 92a98287fd59, configured with clang 21 and bpftool 7.7, and built with make, without errors. That gives libxdp, xdp-loader, xdp-filter, xdpdump and xdp-bench. Our script install_and_verify.sh ended with ALL CHECKS PASSED: a drop rule made ping fail with 100 percent loss, and after removal ping worked again. On loopback, 127.0.0.2 was blocked and 127.0.0.1 was fine. xdp-filter blocks, but it cannot rate limit.

**Takeaway:** xdp-tools built and verified; it complements our own filter.

**Speaker notes (if asked)**
- Why xdp-tools if we have our own program? It is a ready-made, maintained toolset (libxdp, xdp-loader, xdp-filter, xdpdump, xdp-bench). xdp-filter does what our block list does but has no rate limiting; our own program adds per-source counting.
- How do we know the build works? Make ended without errors, and `install_and_verify.sh` ended with ALL CHECKS PASSED (drop rule: 100 % loss, after removal ping works).
- Why a manual check on loopback? It is a short second confirmation with screenshots: 127.0.0.2 blocked, 127.0.0.1 unaffected.

## Slide 14. Conclusion and limitations
**Speaker:** Aayush, then Justlyn

**On screen**
- Trees and KNN best (0-6 errors); MLP best network (F1 0.9995)
- Limits: port-80 shortcut, one dataset and split, no model connected to the block list yet
- Questions

**Script**
Aayush: detection works. F1 runs from 0.9909 to 1.0000, and trees and KNN are best with zero to six errors. MLP is the best network at 0.9995, and the LSTM became competitive only after tuning. Limits: the port-80 shortcut, one dataset, one day, one split. Justlyn: enforcement works too. The rate limiter drops floods in the driver and leaves benign traffic alone. The block list is ready for a detector, but not yet connected, and the filter covers IPv4 with honest source addresses only. Seven hundred thousand packets in, five hundred out. Thank you, we welcome your questions.

**Takeaway:** Accurate detection plus fast enforcement; the connection is future work.

**Speaker notes (if asked)**
- Why do trees and KNN beat the networks here? On these tabular flow features none of the networks beat the tree ensembles, which also train in seconds instead of minutes.
- Why is the LSTM only competitive after tuning? With shared settings it trained unstably (F1 0.9943); clipping, lower lr and longer patience raised it to 0.9992.
- What would you do next? Run an ablation without the port feature, use more seeds, splits and attack types, and connect a trained model to `rl_block`; these are the stated limitations.

---

## Q&A prep (not counted in the 9 minutes)

Most follow-up questions are covered by the per-slide speaker notes above. Pointers: near-perfect scores and the port-80 shortcut, slide 3; why remove duplicates, slide 3; LSTM instability, slide 5; generic vs native XDP, slide 10; how the detector would feed the block list, slide 12. Cross-cutting answers:

1. **Why are the scores near-perfect?** The port-80 shortcut (128,011 of 128,014 DDoS flows) plus one attack type from one day make the task easy. That is why we compare error counts and read the scores with that caveat.
2. **What is your main caveat?** One dataset, one day, one split; differences of a few errors are within noise, and the early-stopped models' validation scores are optimistic.
