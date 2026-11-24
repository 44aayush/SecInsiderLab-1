# Lab 3 Presentation: ML/DL DDoS Detection and eBPF/XDP (Group 8)

**Security Insider Lab I, Uni Passau, Group 8**
Justlyn Kaniyanthara Johnson (121024), Aayush Kapoor (120957), presentation 25 November 2026

Deck: `G8.Lab3.Presentation.pptx` (14 slides), built by `build_deck.js`. Source: `G8.Report3.pdf`; every number comes from the report, `outputs/metrics/comparison_test.md` or `xdp/ratelimit/task4_terminal_output.txt`. The scripts below are the speaker notes of each slide.

Time budget: 10 minutes plus 2 minutes discussion. Planned total 9:20. Aayush Kapoor presents Tasks 1-3 (about 5:45), Justlyn Kaniyanthara Johnson presents Tasks 4-5 (about 3:35); the conclusion is shared.

| Slide | Title | Speaker | Time |
|---|---|---|---|
| 1 | Lab 3: ML and DL Detection of DDoS, Enforced with eBPF/XDP | Aayush Kapoor | 0:20 |
| 2 | From detection to enforcement | Aayush Kapoor | 0:30 |
| 3 | Dataset and preprocessing | Aayush Kapoor | 0:45 |
| 4 | Task 1: five classical classifiers | Aayush Kapoor | 0:35 |
| 5 | Task 2: MLP, LSTM and 1D-CNN | Aayush Kapoor | 0:50 |
| 6 | Task 3: all eight models on the test set | Aayush Kapoor | 0:45 |
| 7 | Errors tell the models apart, not accuracy | Aayush Kapoor | 0:35 |
| 8 | ROC curves: zoomed in | Aayush Kapoor | 0:35 |
| 9 | Cost: training and prediction time | Aayush Kapoor | 0:25 |
| 10 | Task 4: eBPF and XDP in one slide | Justlyn Kaniyanthara Johnson | 0:50 |
| 11 | Limit of 100 packets/s per source holds | Justlyn Kaniyanthara Johnson | 0:55 |
| 12 | Per-source counters in the map | Justlyn Kaniyanthara Johnson | 0:40 |
| 13 | Task 5: xdp-tools built from source | Justlyn Kaniyanthara Johnson | 0:45 |
| 14 | Conclusion and limitations | Aayush Kapoor, Justlyn Kaniyanthara Johnson | 0:50 |

---

## Slide 1. Lab 3: ML and DL Detection of DDoS, Enforced with eBPF/XDP

**Speaker:** Aayush Kapoor · **Time:** about 0:20

- Headline numbers: 8 models on 33,463 test flows; XGBoost 0 errors; 500 of 697,064 flood packets reach the victim.

**Script.** Welcome. This is Lab 3 of the Security Insider Lab, group 8. Our lab has two halves: detecting DDoS flows with machine learning and deep learning, and dropping attack traffic early in the kernel with eBPF and XDP. I present the detection part, Justlyn presents the XDP part. The three numbers on the right are the headline results: eight models compared on 33,463 test flows, XGBoost with zero errors, and an XDP rate limiter that lets only 500 flood packets of 697,064 through.

## Slide 2. From detection to enforcement

**Speaker:** Aayush Kapoor · **Time:** about 0:30

- Tasks 1-3 (Aayush Kapoor): data preparation, 5 classical models, 3 neural networks, comparison.
- Tasks 4-5 (Justlyn Kaniyanthara Johnson): eBPF/XDP theory and filter, xdp-tools.
- Future work: a block list as the bridge between the two parts.

**Script.** The lab has five tasks and they form one story. On the left, detection: we clean the CIC-IDS2017 Friday DDoS file, train five classical classifiers in Task 1 and three neural networks in Task 2, and compare all eight in Task 3. On the right, enforcement: in Task 4 Justlyn explains eBPF and XDP and presents our own XDP rate limiter, and in Task 5 the xdp-tools collection. The arrow in the middle is future work: a block list in the XDP program, where a detector would hand over a flagged source. That block list does not exist yet; our rate limiter works on its own. The whole detection pipeline runs with one command, python script/main.py.

## Slide 3. Dataset and preprocessing

**Speaker:** Aayush Kapoor · **Time:** about 0:45

- 225,745 raw flows to 223,082 clean flows; 78 to 59 features.
- Cleaning: 34 inf/NaN rows, 2,629 duplicates, 10 constant and 9 identical columns.
- Stratified 70/15/15 split, seed 42; scaler fitted on train only.
- Caveat: 128,011 of 128,014 DDoS flows target port 80.

**Script.** We use the Friday-afternoon DDoS file of CIC-IDS2017: 225,745 flows with 78 features. Cleaning removes 34 rows with infinite or NaN values and 2,629 duplicate rows. We remove duplicates on purpose, otherwise identical flows would land in both the training and the test set and inflate the scores. We also drop 10 constant and 9 identical columns, which leaves 223,082 flows with 59 features, 128,014 DDoS and 95,068 benign. The split is a stratified 70, 15, 15 with seed 42, and the scaler is fitted on the training set only. One caveat matters for everything that follows: almost all DDoS flows, 128,011 of 128,014, target port 80, so the destination port is a strong shortcut. We keep it, we did not run an ablation, and the near-perfect scores must be read with this in mind.

## Slide 4. Task 1: five classical classifiers

**Speaker:** Aayush Kapoor · **Time:** about 0:35

- Slide suggestion: GNB, Gradient Boosting, AdaBoost, KNN, SVM. Ours: GNB, LR, KNN, RF, XGBoost.
- Score = P(DDoS), predict DDoS above 0.5. Only XGBoost uses the validation set.
- KNN with k = 5 gives only six score values, so its ROC curve has few points.

**Script.** The task slide suggests Gaussian Naive Bayes, Gradient Boosting, AdaBoost, KNN and SVM but allows our own selection. We kept Gaussian Naive Bayes and KNN and chose Logistic Regression, Random Forest and XGBoost instead. That covers a probabilistic model, a linear model, an instance-based model and two tree ensembles, one bagging and one boosting. Gradient Boosting, AdaBoost and SVM were not trained, XGBoost is itself a gradient-boosting implementation. Hyper-parameters are fixed, no search. Every model outputs the probability of DDoS and we predict DDoS above 0.5. Only XGBoost uses the validation set, to stop after 20 rounds without improvement. One detail for later: KNN with k equal to 5 can only output six different scores, so its ROC curve has few points.

## Slide 5. Task 2: MLP, LSTM and 1D-CNN

**Speaker:** Aayush Kapoor · **Time:** about 0:50

- MLP 59-128-64-1; LSTM reads 59 features as a sequence; 1D-CNN with two conv layers and global max-pool.
- Early stopping on validation loss; best epochs MLP 29, LSTM 31, CNN 22.
- LSTM: gradient clipping 1.0, lr 5e-4, patience 7, chosen by lowest validation loss; F1 0.9943 to 0.9992.

**Script.** All three networks take the same 59 standardized features and output one logit. The MLP has two hidden layers with dropout. The LSTM reads the features as a sequence of 59 steps, and the 1D-CNN treats them as a one-channel signal. Flow features have no natural order, so these are pseudo-sequences, we use them because the task asks for them. Training stops by early stopping on the validation loss, and the best epoch is restored. The LSTM needed tuning. With shared settings its training loss spiked, probably from exploding gradients, and it reached an F1 of only 0.9943. We added gradient clipping at 1.0, a learning rate of 5 times 10 to the minus 4 and a patience of 7, chosen by the lowest validation loss over three configurations. That raised the F1 to 0.9992. The plot shows the loss curves; note that the LSTM validation loss still oscillates, so clipping reduces the instability but does not remove it.

## Slide 6. Task 3: all eight models on the test set

**Speaker:** Aayush Kapoor · **Time:** about 0:45

- Test split of 33,463 flows, DDoS positive; rows sorted by F1.
- XGBoost 0 FP / 0 FN; Gaussian Naive Bayes weakest (327 FP).

**Script.** This is the comparison table from the test split, sorted by F1, DDoS is the positive class. All eight models are between 0.9895 and 1.0000 accuracy and from 0.9909 to 1.0000 F1. XGBoost has no error at all. Random Forest and KNN follow, then the MLP, the LSTM and the CNN. Logistic Regression has 44 false positives and Gaussian Naive Bayes is the weakest with 327 false positives, which lowers its precision to 0.9832. Because the scores are so close to 1, we look at errors on the next slide rather than at accuracy.

## Slide 7. Errors tell the models apart, not accuracy

**Speaker:** Aayush Kapoor · **Time:** about 0:35

- Total errors: XGBoost 0, Random Forest 3, KNN 6, MLP 18, LSTM 32, 1D-CNN 33, Logistic Regression 67, Gaussian NB 353 (327 FP).
- Log-scale FP/FN bars (errors_bar).

**Script.** Accuracy alone says little when every model lies between 0.9895 and 1.0000, so we count errors. XGBoost makes none, Random Forest 3, KNN 6. The three networks make 18, 32 and 33 errors, Logistic Regression 67 and Gaussian Naive Bayes 353, of which 327 are false positives. So Gaussian Naive Bayes misses few attacks, recall 0.9986, but raises many false alarms. For a detector, these false alarms and missed attacks decide which model to prefer. The y-axis is logarithmic.

## Slide 8. ROC curves: zoomed in

**Speaker:** Aayush Kapoor · **Time:** about 0:35

- ROC-AUC 1.0000: RF, XGBoost, MLP, LSTM, 1D-CNN; 0.9999: LR, KNN; 0.9880: GNB.
- XGBoost, Random Forest and KNN lie on top; GNB needs FPR about 0.02.
- Log-x: FPR 0 clipped at 1e-5.

**Script.** A plain ROC plot would show eight curves in the top-left corner, so we show two zoomed versions. AUC is 1.0000 for Random Forest, XGBoost, MLP, LSTM and the CNN, 0.9999 for Logistic Regression and KNN, and 0.9880 for Gaussian Naive Bayes. On the left, zoomed on small false-positive rates, XGBoost, Random Forest and KNN lie at the top, and the dashed neural networks stay above Logistic Regression. On the right, the false-positive axis is logarithmic, which stresses the low false-alarm region that matters for a detector. FPR zero is clipped at 10 to the minus 5. The curves that rise along a curve at the left edge are an interpolation effect on the log axis, not poor performance. Gaussian Naive Bayes needs a false-positive rate of about 0.02 to reach a true-positive rate near 1.

## Slide 9. Cost: training and prediction time

**Speaker:** Aayush Kapoor · **Time:** about 0:25

- Train: GNB 0.063 s, KNN 0.008 s, XGBoost 2.021 s, RF 3.847 s, LR 17.348 s, MLP 42.244 s, 1D-CNN 65.544 s, LSTM 136.034 s.
- KNN predict 4.204 s vs at most 0.173 s for the others.
- Single run, order of magnitude only.

**Script.** Training cost: Gaussian Naive Bayes 0.063 seconds, KNN 0.008 seconds because it only stores the data, XGBoost 2 seconds, Random Forest 3.8 seconds. The neural networks are the most expensive: MLP 42 seconds, CNN 66 and LSTM 136 seconds. KNN reverses the picture at prediction time, 4.2 seconds for the test set against at most 0.173 seconds for every other model. These times come from a single run and only show the order of magnitude.

## Slide 10. Task 4: eBPF and XDP in one slide

**Speaker:** Justlyn Kaniyanthara Johnson · **Time:** about 0:50

- eBPF: sandboxed programs in the kernel, checked by the verifier, state in maps.
- XDP: hook in the NIC driver before sk_buff allocation; actions DROP, PASS, TX, REDIRECT, ABORTED.
- Our filter: per-source-IP rate limiter, 100 pkt/s, one LRU map, attached with ip.

**Script.** Task 4 asks what eBPF and XDP are and for a small filter program. eBPF runs small sandboxed programs inside the Linux kernel. The verifier checks every path before loading, and state lives in maps that are shared with user space. XDP is an eBPF hook in the network driver, right after the packet arrives and before the kernel allocates an sk_buff. The program returns one of five actions: drop, pass, transmit back, redirect, or aborted. Because there is no sk_buff yet, drops are cheap, tens of millions of packets per second per core is the order of magnitude reported in the literature, and that is why XDP suits DDoS mitigation. Our filter is a per-source-IP rate limiter of about 80 lines, attached with a single ip link command. The decision path: first a bounds check on every header, then IPv4 only, everything else passes. Then we look up the source address in one map called rl_state, or create an entry. If more than one second has passed since the window started, the window and the counter are reset. The counter is incremented atomically, and above 100 packets in the window the program returns XDP_DROP, otherwise XDP_PASS. The map is an LRU hash, so a flood of new spoofed sources can never make the program refuse a new entry: the oldest one is evicted. It is a shared map, not per-CPU, so the limit of 100 holds across all CPUs even when packets of one source arrive on several of them. The box on the right shows exactly this last part of the program.

## Slide 11. Limit of 100 packets/s per source holds

**Speaker:** Justlyn Kaniyanthara Johnson · **Time:** about 0:55

- Test bed: one namespace (attacker 10.0.0.2, benign client 10.0.0.3), host 10.0.0.1 on veth0 is the victim; 5 s hping3 SYN flood to port 80; limit 100 pkt/s.
- Packets counted with nstat IpInReceives: the host's ufw firewall drops SYNs before TCP, so TcpInSegs stayed near zero.
- Baseline 372,537 sent / 372,564 at the IP layer (27 other host traffic); with XDP 697,064 sent / 525 = 500 flood + 25 pings; benign ping 25/25, 0 % loss.
- Not a throughput measurement: attacker and victim share one machine.

**Script.** To test without touching the real network, we use one network namespace called atk. It holds the attacker at 10.0.0.2 and a benign client at 10.0.0.3. The host itself is 10.0.0.1 on a virtual interface, veth0, and is the victim. The filter is attached to veth0 in generic mode with one ip link command. The attacker runs a SYN flood with hping3 for 5 seconds against port 80, and the benign client pings. The limit is 100 packets per second per source. We count packets with the kernel counter IpInReceives from nstat, not TcpInSegs, because the host's ufw firewall drops the SYNs before they reach TCP, so the TCP counter stayed near zero. Without XDP the attacker sends 372,537 packets and 372,564 arrive at the IP layer; the 27 extra are other traffic on the host. With the filter the attacker sends 697,064 packets and the victim sees 525 packets: that is exactly 500 flood packets, 100 per second for 5 seconds, plus the 25 pings of the benign client. The benign ping has no loss, 25 of 25. The attacker sent almost twice as many packets with the filter on. We attribute this to the host no longer spending time on every SYN, since attacker and victim share one machine. So this is not a throughput measurement of XDP; it shows that the limit is enforced and that benign traffic is not affected.

## Slide 12. Per-source counters in the map

**Speaker:** Justlyn Kaniyanthara Johnson · **Time:** about 0:40

- bpftool dump of rl_state: attacker passed 500 + dropped 696,564 = 697,064 sent; benign passed 25, dropped 0.
- Future work: a block-list map that a user-space detector fills (Gatebot detects, L4Drop enforces at Cloudflare).
- No block list and no trained model connected yet; the rate limiter works without any model.

**Script.** After the test we read the state map with bpftool. It has one entry per source address. The attacker, 10.0.0.2, has 500 packets passed and 696,564 dropped, together 697,064, which is exactly the number hping3 reported as sent. The benign client, 10.0.0.3, has 25 passed and none dropped. So the counters match the test result and the limiter treats the two sources separately. A natural next step, which we did not build, is a second map as a block list that a user-space detector fills. This is the division of labour Cloudflare uses at scale: Gatebot detects in user space and L4Drop enforces in XDP. The classifier's decision latency would then matter once per flow, not per packet, which is why the prediction times on the cost slide would be acceptable. Honest limit: there is no block list in our program and no trained model is connected to it. The rate limiter works without any model.

## Slide 13. Task 5: xdp-tools built from source

**Speaker:** Justlyn Kaniyanthara Johnson · **Time:** about 0:45

- Cloned at commit 92a98287fd59 (v1.6.3-32), clang 21.1.8, bpftool v7.7.0; make finished without errors.
- Tools: libxdp, xdp-loader, xdp-filter, xdpdump, xdp-bench and others.
- install_and_verify.sh: make install + help, features lo, status: ALL CHECKS PASSED.
- Screenshot: xdp-filter on lo, ping from 127.0.0.2 blocked (SS_T7_9).

**Script.** Task 5 asks to download and configure xdp-tools. We cloned the repository at commit 92a98287fd59, configured it with clang 21 and bpftool 7.7, and built it with make without errors or warnings. It produces libxdp and the tools xdp-loader, xdp-filter, xdpdump, xdp-bench and others. To verify it, our script install_and_verify.sh runs make install and then the help commands of xdp-loader, xdp-filter and xdpdump, xdp-loader features on lo, and xdp-loader status. The final run ended with ALL CHECKS PASSED. The screenshot shows the manual check on the loopback interface: a drop rule for 127.0.0.2, pings from 127.0.0.1 have no loss and pings from 127.0.0.2 are lost completely. xdp-filter drops by address with a ready-made tool but has no rate limiting; our program limits per source.

## Slide 14. Conclusion and limitations

**Speaker:** Aayush Kapoor, Justlyn Kaniyanthara Johnson · **Time:** about 0:50

- Tree ensembles and KNN best (0-6 errors, order within noise); MLP best DL (F1 0.9995).
- Limits: port-80 shortcut, one dataset/split, no block list / ML connection yet (future work).
- Questions.

**Script.** To summarize the detection part, Aayush: all eight models detect the DDoS flows very well, F1 from 0.9909 to 1.0000. The tree ensembles and KNN are best with zero to six errors on 33,463 test flows, and their order is within noise. Among the networks the MLP is best with F1 0.9995, but none beats the tree ensembles, which also train in seconds. The LSTM only became competitive after tuning. Limitations: the destination port is a shortcut, we use one dataset from one day, one attack type and one split, and differences of a few errors could change with another seed. Justlyn: on the enforcement side, an XDP rate limiter drops floods in the driver and leaves benign traffic untouched. A block list that a detector fills is future work: we did not build it and did not connect a trained model, and the filter assumes honest source addresses and covers IPv4 only. Thank you, we are happy to take questions.

