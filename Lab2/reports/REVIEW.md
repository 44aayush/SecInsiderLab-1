# REVIEW: prose edits for G8.Report2 (AI-pattern pass)

Reviewer: Opus 5.5, 2026-11-06. Source reviewed: `reports/G8.Report2.pdf` and the LaTeX it is built from.
Applier: a Sonnet 5.5 agent, in a later step.
**Status: applied and verified on 2026-11-06.** All 33 edits are in. The edited sources are byte-identical to Opus's pre-applied copy. The PDF is rebuilt, and the bibliography still starts on p. 16.

The prose is already concise and factual. It has no em dashes and none of the banned vocabulary. What makes it read as machine-written is structural:

- 13 paragraphs open with "Table/Figure X shows/lists/summarizes".
- The point that accuracy alone is meaningless is made four times.
- "Class weighting is a trade-off" appears twice.
- A few filler words ("Notably", "clearly"), trailing "which is a bug / which shows" clauses, one foreshadowing aside, one fake-profound closing line, and three run-on sentences.

The edits below fix only those. Everything else stays.

---

## 1. How to apply (Sonnet: read this first)

1. Read `CLAUDE.md` §9 (report rules) before you start. If the baseline directory `$S` from §6 does not exist (a new session clears the scratchpad), create one **before any edit**. Set `S` to a fresh scratch directory, then run from `reports/`:
   `mkdir -p $S/chapters $S/includes && cp chapters/*.tex $S/chapters/ && cp includes/abstract.tex $S/includes/ && cat chapters/*.tex includes/abstract.tex | grep -oE '[0-9][0-9,.]*[0-9]|[0-9]' | sort -u > $S/nums_before.txt`
2. Edit **only** `reports/chapters/*.tex` and `reports/includes/abstract.tex`.
   - Never touch `reports/tables/*.tex` (generated), `thesis.tex`, the figures or `src/`.
3. Every edit is an exact replacement. Use the **Old** block as `old_string` and the **New** block as `new_string`, byte for byte.
   - Line numbers are hints only. Match on the text.
   - If an Old block no longer matches exactly once, skip that edit and list it in your report. Do not improvise a replacement.
4. Do **not** add, remove, change or round any number. Keep every `\ref`, `\cite`, `\texttt`, `\,`, `~` and `--` exactly as written in the New blocks.
5. Do not rephrase anything that is not listed here, and leave everything in §2 alone.
6. After all edits, run §6 and report each check's output verbatim. Do not tick boxes in `TASKS.md`; Opus reviews the diff and does that.

## 2. Keep list (the writers' voice; do not polish)

These lines are human and specific, so they stay as they are:

- `task1_flows.tex` L16: "most flows were garbage"
- `introduction.tex` L13: "harder, and in our view more interesting, to detect"
- `task4_ml.tex` L30: "flow statistics cannot see the payload, which is the only thing that really differs" and "one flow more or less changes it by about 0.1"
- `task4_ml.tex` L30: "This is the accuracy paradox" (it names the concept the Discussion heading uses)
- `task4_ml.tex` L63: "LR draws a single linear boundary … and cannot."
- `task3_preprocessing.tex` L113: "plausibly capture the regular pacing" (a real hedge)
- `task4_realtime.tex` L67: the Steam false-positive narrative (times, URL, window values)
- `discussion.tex` L4: "The model partly learned ``automated HTTP to port 80 from a small-window server'', not the attack itself."
- `discussion.tex` L8: the Limitations paragraph as a whole
- `discussion.tex` L10: "should reduce the false positives" (an honest hedge)

## 3. Edits

Tags:

- **[S]** marks a style (AI-pattern) edit.
- **[P]** marks a precision fix found during the read. Each [P] fix makes the text agree with what the report states elsewhere and adds no new claim.

### `includes/abstract.tex`

#### E01 · L5 · [S] throat-clearing opener (repeated verbatim in the Introduction)
Old:
```tex
This report documents the second lab of the Security Insider Lab: detecting network attacks from flow features with machine learning.
```
New:
```tex
In the second lab of the Security Insider Lab, we detect network attacks from flow features with machine learning.
```

#### E02 · L5 · [S] run-on sentence, three clauses joined by `;` and `so`
Old:
```tex
We first recorded our own traffic and converted it into flows with CICFlowMeter; an IPv6 capture produced mostly bogus flows because CICFlowMeter force-parses non-IPv4 frames as IPv4, so we disabled IPv6 and obtained 569 flows, 547 of them valid TCP/UDP flows.
```
New:
```tex
We first recorded our own traffic and converted it into flows with CICFlowMeter. Our first captures were mostly IPv6 and produced bogus flows, because CICFlowMeter force-parses non-IPv4 frames as IPv4. With IPv6 disabled, we obtained 569 flows, 547 of them valid TCP/UDP flows.
```

#### E03 · L5 · [S] tangled "leaving … followed by" chain
Old:
```tex
Pre-processing removed infinite values, duplicate rows, constant and identical columns, leaving 164,179 flows with 60 features, followed by a stratified split, min-max scaling and selection of the 20 best features with $\chi^2$.
```
New:
```tex
Pre-processing removed infinite values, duplicate rows and constant and identical columns, which left 164,179 flows with 60 features. We then made a stratified split, min-max scaled the features and selected the 20 best with $\chi^2$.
```

#### E04 · L5 · [P] the 98.5 % result belongs to the *multiclass* LR
The binary default LR does detect attacks (recall 0.8538, `task4_ml.tex` L12).
Old:
```tex
whereas default Logistic Regression reaches 98.5\,\% accuracy while detecting no attack.
```
New:
```tex
whereas default multiclass Logistic Regression reaches 98.5\,\% accuracy while detecting no attack.
```

### `chapters/introduction.tex`

#### E05 · L4 · [S] throat-clearing opener + "Its goal is"
Old:
```tex
This report documents the second lab of the Security Insider Lab. Its goal is to detect network attacks with machine learning. Instead
```
New:
```tex
In the second lab of the Security Insider Lab, we detect network attacks with machine learning. Instead
```

### `chapters/task1_flows.tex`

#### E06 · L35 · [S] tacked-on "which is a bug"; inanimate subject ("Disabling IPv6 … matches")
Old:
```tex
because its UDP branch takes the header length from the TCP header (\texttt{PacketReader.java}, line 204), which is a bug. Disabling IPv6 also matches the training data, which is IPv4 only.
```
New:
```tex
because its UDP branch wrongly reads the header length from the TCP header (\texttt{PacketReader.java}, line 204). With IPv6 off, our flows are IPv4-only, like the training data.
```

#### E07 · L58 · [S] "Figure X shows … Table Y summarizes" opener
The frame counts go first and the references move into parentheses. Every reference is kept.
Old:
```tex
Figure~\ref{fig:ss15} shows the protocol hierarchy of the final capture and Figure~\ref{fig:ss25} the offline conversion. The capture contains 47,682 UDP frames (29,682 QUIC, 580 DNS), 33,218 TCP frames (11,994 TLS, 26 HTTP), 160 ICMP frames and 26 ARP frames. Table~\ref{tab:t1flows} summarizes the resulting 569 flows (Figure~\ref{fig:ss17}).
```
New:
```tex
The final capture contains 47,682 UDP frames (29,682 QUIC, 580 DNS), 33,218 TCP frames (11,994 TLS, 26 HTTP), 160 ICMP frames and 26 ARP frames (Figure~\ref{fig:ss15}). Its offline conversion (Figure~\ref{fig:ss25}) yields 569 flows (Table~\ref{tab:t1flows}, Figure~\ref{fig:ss17}).
```

#### E08 · L67 · [P] these are flows, not frames
Old:
```tex
4 left-over IPv6 frames and 3 ARP frames, the last two mis-parsed as described above.
```
New:
```tex
4 flows from left-over IPv6 frames and 3 from ARP frames, the last two groups mis-parsed as described above.
```

### `chapters/task2_dataset.tex`

#### E09 · L6 · [S] "Table X shows" opener
The table caption already says "raw and after the cleaning steps of Chapter 4", so that half of the sentence can go.
Old:
```tex
Table~\ref{tab:t2labels} shows the label distribution before and after cleaning (Chapter~\ref{chap:task3_preprocessing}). The dataset is extremely imbalanced:
```
New:
```tex
The dataset is extremely imbalanced (Table~\ref{tab:t2labels}):
```

#### E10 · L6 · [S] run-on sentence ("…meaningless here, and we report…")
Old:
```tex
would already be 98.7\,\% accurate, so accuracy alone is meaningless here, and we report per-class precision, recall and F1, the macro-F1 and confusion matrices throughout.
```
New:
```tex
would already be 98.7\,\% accurate. We therefore report per-class precision, recall and F1, the macro-F1 and confusion matrices throughout, never accuracy alone.
```

#### E11 · L6 · [S] foreshadowing metadiscourse ("This will turn out to be…")
Old:
```tex
This will turn out to be a shortcut that models can exploit (Chapter~\ref{chap:discussion}).
```
New:
```tex
Models can exploit this as a shortcut (Section~\ref{sec:t3-interp} and Chapter~\ref{chap:discussion}).
```

### `chapters/task3_preprocessing.tex`

#### E12 · L4 · [P] grammar: two modules
Old:
```tex
(module \texttt{data.py}, \texttt{features.py} and the script \texttt{task3\_preprocess.py})
```
New:
```tex
(modules \texttt{data.py} and \texttt{features.py}, script \texttt{task3\_preprocess.py})
```

#### E13 · L25 · [S] tangled sentence (14 of 6,066 …)
Old:
```tex
The 14 of the 6,066 duplicate rows of the raw file that contain infinite or NaN values were already removed in step 3, which leaves 6,052 for step 4.
```
New:
```tex
The raw file has 6,066 duplicate rows, but 14 of them contain infinite or NaN values and are already gone after step 3, so step 4 drops 6,052.
```

#### E14 · L25 · [S] "Notably" (tells the reader what to notice); vague "these"
Old:
```tex
Notably, \texttt{Fwd PSH Flags} is identical to \texttt{SYN Flag Count}, although these are different TCP flags.
```
New:
```tex
\texttt{Fwd PSH Flags} is identical to \texttt{SYN Flag Count}, although PSH and SYN are different TCP flags.
```

#### E15 · L71 · [S] "exactly 0 … (up to rounding)" contradicts itself
Old:
```tex
the scaled minimum is exactly 0 and the maximum 1
```
New:
```tex
the scaled minimum is 0 and the maximum 1
```

#### E16 · L80 · [S] "Table X lists … Figure Y shows" opener
Old:
```tex
Table~\ref{tab:t3top20} lists the 20 selected features per target and Figure~\ref{fig:fsbin} shows the binary scores. The two lists share 18 of 20 features:
```
New:
```tex
The binary and multiclass feature lists share 18 of 20 features (Table~\ref{tab:t3top20}; binary scores in Figure~\ref{fig:fsbin}):
```

#### E17 · L80 · [S] passive "are dominated by … which is why"
Old:
```tex
The scores are dominated by the top three features (above 1,600 each, against less than 250 for the rest), which is why ranks 6--20 look similar on the linear axis.
```
New:
```tex
The top three features score above 1,600 each and the rest below 250, so ranks 6--20 look alike on the linear axis.
```

#### E18 · L113 · [S] abstract opener that fails the portability test
The next sentence already explains the claim.
Old:
```tex
The ranking tells us what the data lets a model learn, and some of it is testbed-specific.
```
New:
```tex
Several of the top features are specific to the 2017 testbed.
```

#### E19 · L113 · [S] dangling final sentence that repeats L80
Delete it. The leading space is part of the Old text.
Old:
```tex
 The multiclass ranking is given in the right half of Table~\ref{tab:t3top20}.
```
New: *(empty; delete)*
```tex
```

### `chapters/task4_ml.tex`

#### E20 · L6 · [S] third repetition of "not accuracy alone"
Chapter 3 states this point (E10), and Section 5.3 demonstrates it. Delete the sentence, including its leading space.
Old:
```tex
 Because of the imbalance, we report precision, recall, F1, macro-F1 and confusion matrices, not accuracy alone.
```
New: *(empty; delete)*
```tex
```

#### E21 · L12 · [S] "Table X shows" opener, "clearly worse", stacked commas · [P] "the two models" is ambiguous
The paragraph just discussed two LR models, but subfigures (a) and (b) show the default DT and the balanced LR.
Old:
```tex
Table~\ref{tab:t4binary} shows the binary results. The default Decision Tree is the best model: it detects all 643 attacks (recall 1.0000) with 18 false positives and an attack F1 of 0.9862. Its balanced variant is almost identical. Logistic Regression is clearly worse. The default LR misses 94 attacks (recall 0.8538). With \texttt{class\_weight="balanced"}, LR reaches a recall of 0.9907 but at a precision of only 0.2349, with 2,075 false alarms, ten times more than the default (201). Figure~\ref{fig:cm} (a) and (b) show the confusion matrices of the two models.
```
New:
```tex
The default Decision Tree is the best binary model (Table~\ref{tab:t4binary}): it detects all 643 attacks (recall 1.0000) with 18 false positives and an attack F1 of 0.9862. Its balanced variant is almost identical. Logistic Regression does worse in both variants. The default LR misses 94 attacks (recall 0.8538). With \texttt{class\_weight="balanced"}, LR reaches a recall of 0.9907, but its precision drops to 0.2349. It raises 2,075 false alarms, ten times as many as the default LR (201). Figure~\ref{fig:cm} (a) and (b) show the confusion matrices of the default DT and the balanced LR.
```

#### E22 · L30 · [S] "Table X shows" opener
Old:
```tex
Table~\ref{tab:t4multi} shows the multiclass results. The default Decision Tree again leads with a macro-F1 of 0.7290.
```
New:
```tex
In the multiclass setting, the default Decision Tree again leads, with a macro-F1 of 0.7290 (Table~\ref{tab:t4multi}).
```

#### E23 · L57 · [S] "key" (mild puffery) in a caption
Old:
```tex
\caption{Confusion matrices of four key models (test split).}
```
New:
```tex
\caption{Confusion matrices of four of the eight models (test split).}
```

#### E24 · L63 · [S] passive "are characterized by"
Old:
```tex
Attacks are characterized by specific value ranges of a few features (small TCP windows, port 80, flag counts), which a tree isolates with axis-aligned thresholds.
```
New:
```tex
Attacks occupy narrow value ranges of a few features (small TCP windows, port 80, flag counts), and a tree isolates such ranges with axis-aligned thresholds.
```

#### E25 · L63 · [S] binary contrast + colon reveal ("a trade-off, not a fix:")
Old:
```tex
Class weighting is a trade-off, not a fix: for LR it buys recall at the price of precision, and for the DT it hardly changes the binary result and hurts the multiclass result.
```
New:
```tex
Class weighting buys LR recall at the price of precision; for the DT it hardly changes the binary result and hurts the multiclass result.
```

### `chapters/task4_realtime.tex`

#### E26 · L6 · [S] spec-checklist sentence ("nothing is hard-coded")
The edit replaces the checklist phrasing with what the design allows.
Old:
```tex
The path of the flow CSV is a command-line argument and nothing is hard-coded.
```
New:
```tex
The flow CSV is a command-line argument, so the detector can be pointed at any other V4 flow file.
```

#### E27 · L49 · [S] "Table X summarizes … Figure Y shows" opener; two sentences that both say "no attacks"
Old:
```tex
Table~\ref{tab:t5rt} summarizes the run and Figure~\ref{fig:ss12} shows the detector output. Of 569 flows, 22 were dropped (protocol 0) and 547 were classified: 544 as BENIGN and 3 as ATTACK, an alert rate of 0.55\,\%. Since our traffic is benign by construction, all three alerts are false positives. Our capture contains no attacks, so we can measure the false-positive rate on our network, but not the detection rate.
```
New:
```tex
Of 569 flows, 22 were dropped (protocol 0) and 547 were classified: 544 as BENIGN and 3 as ATTACK, an alert rate of 0.55\,\% (Table~\ref{tab:t5rt}, Figure~\ref{fig:ss12}). Our traffic is benign by construction, so all three alerts are false positives. For the same reason, we can measure the false-positive rate on our network but not the detection rate.
```

#### E28 · L69 · [S] "exactly the …"; trailing "which shows overfitting" clause · [P] point to the section that defines the shortcuts
Old:
```tex
These are exactly the shortcut features of Chapter~\ref{chap:task3_preprocessing}. Only 3 of the 7 flows are flagged because the final verdict comes from a split at depth 15 on packet-length features: the unpruned tree lets 4 near-identical flows pass and flags 3, which shows overfitting to very fine splits.
```
New:
```tex
These are the shortcut features of Section~\ref{sec:t3-interp}. Only 3 of the 7 flows are flagged because the final verdict comes from a split at depth 15 on packet-length features, where the unpruned tree lets 4 near-identical flows pass and flags 3. The tree has overfitted to these fine splits.
```

#### E29 · L75 · [S] tacked-on negative sentence
Old:
```tex
through the detector, flow by flow. It is not live packet capture.
```
New:
```tex
through the detector one by one; we do not capture packets live.
```

### `chapters/discussion.tex`

#### E30 · L4 · [S] "… at work:" colon reveal · [P] point to the section that defines the shortcuts
Old:
```tex
The false alarms are the shortcut features of Chapter~\ref{chap:task3_preprocessing} at work: \texttt{Destination Port} and \texttt{Init\_Win\_bytes\_*} applied to automated plain-HTTP bursts that resemble the Selenium-driven attacks.
```
New:
```tex
The false alarms come from the shortcut features of Section~\ref{sec:t3-interp}, \texttt{Destination Port} and \texttt{Init\_Win\_bytes\_*}, applied to automated plain-HTTP bursts that resemble the Selenium-driven attacks.
```

#### E31 · L4 · [S] generic ending ("justify careful pre-processing") that fails the portability test
Each listed problem maps to a step in Chapter 4: the label fix, step 2, step 3, step 4 and step 6.
Old:
```tex
They match issues reported in the literature~\cite{engelen2021troubleshooting} and justify careful pre-processing.
```
New:
```tex
They match issues reported in the literature~\cite{engelen2021troubleshooting}, and each of them needed its own cleaning step in Chapter~\ref{chap:task3_preprocessing}.
```

#### E32 · L6 · [S] fourth "accuracy is meaningless"; second "class weighting is a trade-off:" colon reveal
Old:
```tex
Accuracy is not a meaningful metric here. Class weighting is a trade-off: it raises LR's attack recall
```
New:
```tex
Class weighting does not solve the imbalance either. It raises LR's attack recall
```

#### E33 · L12 · [S] "clearly better", a chained run-on, and a fake-profound closing line
The closing line was "Trustworthy detection needs…". The new ending is the concrete false-positive result, using numbers already in the report (`task4_realtime.tex` L6 and L49). The fix it hinted at is already in "Possible improvements".
Old:
```tex
The Decision Tree is clearly better and detects all attacks in the binary test split, but accuracy hides the failures of the other models, and the real-time test on our own traffic shows that a high score on a benchmark does not carry over to another network. Trustworthy detection needs more diverse training data and features that describe attack behavior rather than the testbed.
```
New:
```tex
The Decision Tree outperforms Logistic Regression on both targets and detects all attacks in the binary test split, while accuracy hides that default multiclass LR detects none. On our own benign traffic, the tree's false-positive rate rose from 0.037\,\% to 0.55\,\%, so its benchmark score does not carry over to our network.
```

## 4. Coverage: what was checked and left alone

- **The remaining "Table/Figure X shows" openers** (`task3` L25, L48, L71; `task4_realtime` L6, L31) are plain pointers in a results section. With six removed, the repetition no longer stands out.
- **Banned vocabulary and em dashes:** none in the sources. `--` appears only in numeric ranges (e.g. `16:05--16:10`), which is correct.
- **"deliberately"** (`introduction.tex` L13) records a real choice, so it stays. **"exactly"** in `task4_ml.tex` L6 and `task4_realtime.tex` L6 describes a real technical equality, so it stays too.
- **The Structure paragraph** (`introduction.tex` L15) is conventional for a lab report and short, so it stays.

## 5. Noted, no change (Opus decision; do not act)

- **Step numbering.** The Task 3 list starts with "Load and analyze labels" as step 1. `tables/t3_cleaning.tex` (generated) starts with "Drop duplicate header column" as step 1, and splits inf→NaN and NaN-drop into steps 2 and 3. Steps 4–6 agree, and every in-text step reference (steps 3, 4, 5, 6, "2–6") reads correctly. Leave it.
- **Quote styles.** The sources mix `` ``…'' `` and `\enquote{}`. Both render as the same curly quotes in LuaLaTeX.

## 6. Verification (run after applying; report outputs verbatim)

Run from `Lab2/reports/`. `$S` is the baseline that Opus saved before review:
`S=/tmp/claude-1000/-home-aayush-Desktop-SecInsiderLab1-SecInsiderLab-1-Lab2/7d041166-642a-4d2e-b9a0-dd535825719c/scratchpad/baseline`

1. **Build** (CLAUDE.md §9):
   ```
   latexmk -C -r latexmkrc_2 -jobname=thesis thesis.tex && latexmk -r latexmkrc_2 -jobname=thesis thesis.tex && cp thesis.pdf G8.Report2.pdf
   ```
2. **Page budget.** The main matter must stay at 15 pages or fewer. The ToC line for Bibliography must show page 16 or lower:
   `pdftotext -layout G8.Report2.pdf - | grep -m1 -E '^Bibliography +[0-9]+'`
3. **No broken references.** `latexmkrc_2` deletes `thesis.log`, so check the build's console output for "undefined" in the final pass, and check the PDF. The command below must print `0`.
   ```
   pdftotext G8.Report2.pdf - | grep -c '??'
   ```
4. **Numbers unchanged.** The diff must be empty.
   `cat chapters/*.tex includes/abstract.tex | grep -oE '[0-9][0-9,.]*[0-9]|[0-9]' | sort -u | diff $S/nums_before.txt -`
5. **Word count down.** The baseline is 4,613 words. With all 33 edits applied, expect exactly 4,524 (Opus pre-checked this on a scratch copy).
   `cat chapters/*.tex includes/abstract.tex | wc -w`
6. **Slop rescan.** Expect no `Notably`, no `clearly`, and exactly 5 opener hits (baseline 14):
   ```
   grep -noiE '\b(notably|clearly|key models)\b' chapters/*.tex includes/abstract.tex
   grep -noE '(Table|Figure)~\\ref\{[^}]+\} (shows|lists|summarizes)' chapters/*.tex | wc -l
   ```
7. **Diff for Opus review:**
   `diff -ru $S/chapters chapters; diff -u $S/includes/abstract.tex includes/abstract.tex`
