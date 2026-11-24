// Builds the Lab 3 presentation (G8) from the numbers and figures of G8.Report3.pdf
// and writes the matching speaking script Presentation.md from the same slide data.
// Run: cd report/ppt && node build_deck.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/home/aayush/.claude/skills/synced/e4cc6236-64d8-44be-b91e-bba57ace04f8_ba5af316-0eaf-43fa-8a67-209d84f411bf/pptx/scripts/apply_theme.js");

const REPORT = path.resolve(__dirname, "..");
const LAB3 = path.resolve(REPORT, "..");
const FIG = (n) => path.join(LAB3, "outputs/figures", n);
const XDPI = (n) => path.join(REPORT, "images/xdp", n);
const SS = (n) => path.join(LAB3, "xdp/SS_T7", n);
const OUT = path.join(__dirname, "G8.Lab3.Presentation.pptx");
const MD = path.join(__dirname, "Presentation.md");

const A = "Aayush Kapoor", J = "Justlyn Kaniyanthara Johnson";

const THEME = {
  name: "G8 Lab3 Passau",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2433", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "EEF2F7",
    accent1: "F39200", accent2: "1F3A5F", accent3: "4F7CAC",
    accent4: "6B7280", accent5: "C0392B", accent6: "2E8B57",
    hlink: "4F7CAC", folHlink: "6B7280",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = `${J}, ${A}`;
pres.title = "Lab 3: ML and DL Detection of DDoS, Enforced with eBPF/XDP";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const SW = 13.333, SH = 7.5;
const LOGO = { path: path.join(REPORT, "images/uni-logo.png"), x: SW - 0.45 - 2.1, y: 0.3, w: 2.1, h: 2.1 * 133 / 500 };
const FOOT = "Group 8 · Security Insider Lab I · Lab 3";

// ---------- layouts ----------
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: C.background1 },
  objects: [
    { rect: { x: 0, y: 0, w: 8.2, h: SH, fill: { color: C.text2 } } },
    { image: LOGO },
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.0, w: 7.0, h: 3.0,
        fontSize: 38, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.35, w: 7.0, h: 2.4,
        fontSize: 18, color: C.background2, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  margin: [0.5, 0.5, 0.7, 0.5],
  objects: [
    { image: LOGO },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 9.9, h: 0.8,
        fontSize: 30, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: FOOT, options: { x: 0.6, y: 7.05, w: 6, h: 0.3, fontSize: 10, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.7, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});
pres.defineSlideMaster({
  title: "CLOSING",
  background: { color: C.background1 },
  objects: [
    { rect: { x: 0, y: 0, w: 5.0, h: SH, fill: { color: C.text2 } } },
    { image: LOGO },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.6, w: 3.9, h: 1.4,
        fontSize: 34, bold: true, color: C.background1, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.7, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

// ---------- helpers ----------
const shadow = () => ({ type: "outer", color: "000000", opacity: 0.15, blur: 6, offset: 2, angle: 90 });
const SLIDES = []; // data for Presentation.md
const SECS = new Set();
function ensureSection(name) { if (!SECS.has(name)) { pres.addSection({ title: name }); SECS.add(name); } }

function content(section, title, meta) {
  ensureSection(section);
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  SLIDES.push({ title, ...meta });
  s.addNotes(`Speaker: ${meta.speaker} (about ${meta.time}).\n\n${meta.notes}`);
  // speaker chip next to the footer
  s.addText(meta.speaker, { x: 8.2, y: 7.05, w: 3.8, h: 0.3, fontSize: 10, color: C.accent4, align: "right", margin: 0, isTextBox: true, objectName: "speaker" });
  return s;
}

// fit image into a box, centred; returns the placed rectangle
function img(s, file, pw, ph, x, y, w, h, name) {
  const r = Math.min(w / pw, h / ph);
  const iw = pw * r, ih = ph * r;
  const ix = x + (w - iw) / 2, iy = y + (h - ih) / 2;
  s.addShape(pres.shapes.RECTANGLE, { x: ix - 0.04, y: iy - 0.04, w: iw + 0.08, h: ih + 0.08,
    fill: { color: C.background1 }, line: { color: C.background2, width: 1 }, shadow: shadow(), objectName: name + " frame" });
  s.addImage({ path: file, x: ix, y: iy, w: iw, h: ih, altText: name, objectName: name });
  return { x: ix, y: iy, w: iw, h: ih };
}
function caption(s, text, x, y, w, align = "left") {
  s.addText(text, { x, y, w, h: 0.3, fontSize: 12, italic: true, color: C.accent4, margin: 0, align, isTextBox: true });
}
function stat(s, x, y, w, h, value, label, color = C.text2, fill = C.background2, vsize = 30) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: "stat " + label });
  s.addText(value, { x: x + 0.2, y: y + 0.1, w: w - 0.4, h: h * 0.5, fontSize: vsize, bold: true, color, fontFace: THEME.headFontFace, margin: 0, valign: "bottom", isTextBox: true });
  s.addText(label, { x: x + 0.2, y: y + 0.1 + h * 0.5, w: w - 0.4, h: h * 0.5 - 0.2, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
}
function card(s, x, y, w, h, head, lines, headColor = C.text2) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "card " + head });
  s.addText(head, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.4, fontSize: 18, bold: true, color: headColor, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  s.addText(lines.map((t, i) => ({ text: t, options: { breakLine: i < lines.length - 1 } })),
    { x: x + 0.2, y: y + 0.58, w: w - 0.4, h: h - 0.7, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4, margin: 0, isTextBox: true });
}
function badge(s, x, y, d, n, color = C.accent1) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color }, objectName: "badge " + n });
  s.addText(String(n), { x, y, w: d, h: d, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
}
const hcell = (t, al = "left") => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, align: al, fontSize: 14 } });
const cell = (t, al = "left", o = {}) => ({ text: t, options: { align: al, fontSize: 14, color: C.text1, ...o } });
function table(s, rows, x, y, w, colW, rowH) {
  s.addTable(rows, { x, y, w, colW, rowH, border: { type: "solid", pt: 0.5, color: "C9D1DC" }, fontFace: THEME.bodyFontFace, valign: "middle", margin: [0.03, 0.1, 0.03, 0.1], objectName: "table" });
}

// ============ 1. Title ============
{
  const meta = { speaker: A, time: "0:20",
    notes: "Welcome. This is Lab 3 of the Security Insider Lab, group 8. Our lab has two halves: detecting DDoS flows with machine learning and deep learning, and dropping attack traffic early in the kernel with eBPF and XDP. I present the detection part, Justlyn presents the XDP part. The three numbers on the right are the headline results: eight models compared on 33,463 test flows, XGBoost with zero errors, and an XDP rate limiter that lets only 500 flood packets of 697,064 through." };
  ensureSection("Intro");
  const s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Intro" });
  const title = "Lab 3: ML and DL Detection of DDoS, Enforced with eBPF/XDP";
  s.addText(title, { placeholder: "title" });
  s.addText([
    { text: "Security Insider Lab I · Group 8", options: { breakLine: true } },
    { text: `${A}, ${J}`, options: { breakLine: true } },
    { text: "Presentation, 25 November 2026" },
  ], { placeholder: "body", paraSpaceAfter: 6 });
  s.addNotes(`Speaker: ${meta.speaker} (about ${meta.time}).\n\n${meta.notes}`);
  SLIDES.push({ title, ...meta, summary: ["Headline numbers: 8 models on 33,463 test flows; XGBoost 0 errors; 500 of 697,064 flood packets reach the victim."] });
  stat(s, 8.9, 2.6, 3.9, 1.3, "8 models", "compared on 33,463 test flows");
  stat(s, 8.9, 4.15, 3.9, 1.3, "0 errors", "XGBoost on the test set (FP 0, FN 0)", C.accent6);
  stat(s, 8.9, 5.7, 3.9, 1.3, "500 of 697,064", "flood packets reach the victim", C.accent1);
}

// ============ 2. Pipeline ============
{
  const s = content("Intro", "From detection to enforcement", { speaker: A, time: "0:30",
    summary: ["Tasks 1-3 (Aayush Kapoor): data preparation, 5 classical models, 3 neural networks, comparison.", "Tasks 4-5 (Justlyn Kaniyanthara Johnson): eBPF/XDP theory and filter, xdp-tools.", "Future work: a block list as the bridge between the two parts."],
    notes: "The lab has five tasks and they form one story. On the left, detection: we clean the CIC-IDS2017 Friday DDoS file, train five classical classifiers in Task 1 and three neural networks in Task 2, and compare all eight in Task 3. On the right, enforcement: in Task 4 Justlyn explains eBPF and XDP and presents our own XDP rate limiter, and in Task 5 the xdp-tools collection. The arrow in the middle is future work: a block list in the XDP program, where a detector would hand over a flagged source. That block list does not exist yet; our rate limiter works on its own. The whole detection pipeline runs with one command, python script/main.py." });
  // left panel
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.4, w: 5.6, h: 5.3, rectRadius: 0.1, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "detection panel" });
  s.addText("Detection · Tasks 1-3", { x: 0.9, y: 1.55, w: 5.0, h: 0.5, fontSize: 22, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  const left = [["Data", "clean 223,082 flows, 59 features"], ["Task 1", "5 classical classifiers"], ["Task 2", "MLP, LSTM, 1D-CNN"], ["Task 3", "table, errors, ROC, cost"]];
  left.forEach((r, i) => {
    const y = 2.3 + i * 1.05;
    badge(s, 0.9, y + 0.1, 0.5, i + 1, C.text2);
    s.addText(r[0], { x: 1.6, y, w: 4.3, h: 0.4, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
    s.addText(r[1], { x: 1.6, y: y + 0.4, w: 4.3, h: 0.4, fontSize: 16, color: C.text1, margin: 0, isTextBox: true });
  });
  // right panel
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.1, y: 1.4, w: 5.6, h: 5.3, rectRadius: 0.1, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "enforcement panel" });
  s.addText("Enforcement · Tasks 4-5", { x: 7.4, y: 1.55, w: 5.0, h: 0.5, fontSize: 22, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  const right = [["eBPF and XDP", "theory, use cases, tools"], ["Rate limiter", "per-source-IP filter in XDP"], ["Test", "one namespace, SYN flood, results"], ["xdp-tools", "built from source, verified"]];
  right.forEach((r, i) => {
    const y = 2.3 + i * 1.05;
    badge(s, 7.4, y + 0.1, 0.5, i + 5, C.accent1);
    s.addText(r[0], { x: 8.1, y, w: 4.3, h: 0.4, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
    s.addText(r[1], { x: 8.1, y: y + 0.4, w: 4.3, h: 0.4, fontSize: 16, color: C.text1, margin: 0, isTextBox: true });
  });
  // bridge arrow
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 6.25, y: 3.55, w: 0.8, h: 0.6, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "bridge arrow" });
  s.addText("future:\nblock list", { x: 6.0, y: 4.25, w: 1.3, h: 0.55, fontSize: 14, bold: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  s.addText("Aayush Kapoor", { x: 0.9, y: 6.2, w: 5.0, h: 0.35, fontSize: 14, italic: true, color: C.accent4, margin: 0, isTextBox: true });
  s.addText("Justlyn Kaniyanthara Johnson", { x: 7.4, y: 6.2, w: 5.0, h: 0.35, fontSize: 14, italic: true, color: C.accent4, margin: 0, isTextBox: true });
}

// ============ 3. Data ============
{
  const s = content("Tasks 1-3", "Dataset and preprocessing", { speaker: A, time: "0:45",
    summary: ["225,745 raw flows to 223,082 clean flows; 78 to 59 features.", "Cleaning: 34 inf/NaN rows, 2,629 duplicates, 10 constant and 9 identical columns.", "Stratified 70/15/15 split, seed 42; scaler fitted on train only.", "Caveat: 128,011 of 128,014 DDoS flows target port 80."],
    notes: "We use the Friday-afternoon DDoS file of CIC-IDS2017: 225,745 flows with 78 features. Cleaning removes 34 rows with infinite or NaN values and 2,629 duplicate rows. We remove duplicates on purpose, otherwise identical flows would land in both the training and the test set and inflate the scores. We also drop 10 constant and 9 identical columns, which leaves 223,082 flows with 59 features, 128,014 DDoS and 95,068 benign. The split is a stratified 70, 15, 15 with seed 42, and the scaler is fitted on the training set only. One caveat matters for everything that follows: almost all DDoS flows, 128,011 of 128,014, target port 80, so the destination port is a strong shortcut. We keep it, we did not run an ablation, and the near-perfect scores must be read with this in mind." });
  stat(s, 0.6, 1.35, 3.9, 1.35, "225,745 → 223,082", "flows after cleaning", C.text2, C.background2, 26);
  stat(s, 4.7, 1.35, 3.9, 1.35, "78 → 59", "features (10 constant, 9 identical dropped)");
  stat(s, 8.8, 1.35, 3.9, 1.35, "70 / 15 / 15", "stratified split, seed 42", C.text2, C.background2, 28);
  const rows = [
    [hcell("Step"), hcell("Dropped"), hcell("Rows after", "right")],
    [cell("Raw file"), cell("-"), cell("225,745", "right")],
    [cell("Infinite or NaN"), cell("34 rows"), cell("225,711", "right")],
    [cell("Duplicate rows"), cell("2,629 rows"), cell("223,082", "right")],
    [cell("Constant columns"), cell("10 columns"), cell("223,082", "right")],
    [cell("Identical columns"), cell("9 columns"), cell("223,082", "right")],
  ];
  table(s, rows, 0.6, 3.1, 7.2, [2.8, 2.4, 2.0], 0.5);
  s.addText("Train 156,157 · Validation 33,462 · Test 33,463. The validation set is used only for early stopping and tuning choices; all final results use the test set.",
    { x: 0.6, y: 6.2, w: 7.2, h: 0.65, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.2, y: 3.1, w: 4.5, h: 3.75, rectRadius: 0.08, fill: { color: "FDF1DC" }, line: { color: "FDF1DC" }, objectName: "caveat card" });
  s.addText("Caveat: port 80", { x: 8.45, y: 3.25, w: 4.0, h: 0.45, fontSize: 20, bold: true, color: C.text1, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  s.addText([
    { text: "128,011 of 128,014 DDoS flows target port 80", options: { bullet: true, breakLine: true } },
    { text: "Destination Port is a strong shortcut", options: { bullet: true, breakLine: true } },
    { text: "Kept, no ablation: read the near-perfect scores with this in mind", options: { bullet: true } },
  ], { x: 8.45, y: 3.8, w: 4.0, h: 2.9, fontSize: 16, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true });
}

// ============ 4. Task 1 ============
{
  const s = content("Tasks 1-3", "Task 1: five classical classifiers", { speaker: A, time: "0:35",
    summary: ["Slide suggestion: GNB, Gradient Boosting, AdaBoost, KNN, SVM. Ours: GNB, LR, KNN, RF, XGBoost.", "Score = P(DDoS), predict DDoS above 0.5. Only XGBoost uses the validation set.", "KNN with k = 5 gives only six score values, so its ROC curve has few points."],
    notes: "The task slide suggests Gaussian Naive Bayes, Gradient Boosting, AdaBoost, KNN and SVM but allows our own selection. We kept Gaussian Naive Bayes and KNN and chose Logistic Regression, Random Forest and XGBoost instead. That covers a probabilistic model, a linear model, an instance-based model and two tree ensembles, one bagging and one boosting. Gradient Boosting, AdaBoost and SVM were not trained, XGBoost is itself a gradient-boosting implementation. Hyper-parameters are fixed, no search. Every model outputs the probability of DDoS and we predict DDoS above 0.5. Only XGBoost uses the validation set, to stop after 20 rounds without improvement. One detail for later: KNN with k equal to 5 can only output six different scores, so its ROC curve has few points." });
  const rows = [
    [hcell("Model"), hcell("Type"), hcell("Fixed settings")],
    [cell("Gaussian Naive Bayes"), cell("probabilistic"), cell("defaults")],
    [cell("Logistic Regression"), cell("linear"), cell("max_iter 2000")],
    [cell("KNN"), cell("instance-based"), cell("k = 5")],
    [cell("Random Forest"), cell("bagging ensemble"), cell("100 trees")],
    [cell("XGBoost"), cell("boosting ensemble"), cell("500 trees, depth 6, lr 0.1, early stop 20")],
  ];
  table(s, rows, 0.6, 1.4, 7.9, [2.5, 2.0, 3.4], 0.62);
  card(s, 8.9, 1.4, 3.85, 2.2, "Our own selection", ["Slide list: GNB, Gradient Boosting, AdaBoost, KNN, SVM", "Kept GNB and KNN; replaced the other three"]);
  card(s, 8.9, 3.85, 3.85, 2.2, "Common rules", ["Score = P(DDoS); DDoS if above 0.5", "Only XGBoost uses the validation set"]);
  s.addText("No hyper-parameter search. KNN with k = 5 outputs only six score values, so its ROC curve has few points.",
    { x: 0.6, y: 5.4, w: 7.9, h: 0.9, fontSize: 16, color: C.text1, margin: 0, valign: "top", isTextBox: true });
}

// ============ 5. Task 2 ============
{
  const s = content("Tasks 1-3", "Task 2: MLP, LSTM and 1D-CNN", { speaker: A, time: "0:50",
    summary: ["MLP 59-128-64-1; LSTM reads 59 features as a sequence; 1D-CNN with two conv layers and global max-pool.", "Early stopping on validation loss; best epochs MLP 29, LSTM 31, CNN 22.", "LSTM: gradient clipping 1.0, lr 5e-4, patience 7, chosen by lowest validation loss; F1 0.9943 to 0.9992."],
    notes: "All three networks take the same 59 standardized features and output one logit. The MLP has two hidden layers with dropout. The LSTM reads the features as a sequence of 59 steps, and the 1D-CNN treats them as a one-channel signal. Flow features have no natural order, so these are pseudo-sequences, we use them because the task asks for them. Training stops by early stopping on the validation loss, and the best epoch is restored. The LSTM needed tuning. With shared settings its training loss spiked, probably from exploding gradients, and it reached an F1 of only 0.9943. We added gradient clipping at 1.0, a learning rate of 5 times 10 to the minus 4 and a patience of 7, chosen by the lowest validation loss over three configurations. That raised the F1 to 0.9992. The plot shows the loss curves; note that the LSTM validation loss still oscillates, so clipping reduces the instability but does not remove it." });
  card(s, 0.6, 1.3, 3.95, 1.5, "MLP", ["59 → 128 → 64 → 1, dropout 0.2", "Best epoch 29 · F1 0.9995"]);
  card(s, 4.69, 1.3, 3.95, 1.5, "LSTM", ["59-step sequence, 32 hidden units", "Clip 1.0, lr 5e-4, patience 7", "F1 0.9943 → 0.9992"], C.accent1);
  card(s, 8.78, 1.3, 3.95, 1.5, "1D-CNN", ["Conv 32 and 64, global max-pool", "Best epoch 22 · F1 0.9991"]);
  img(s, FIG("dl_history_grid.png"), 2543, 783, 0.6, 3.05, 12.1, 3.8, "Training history per DL model");
}

// ============ 6. Task 3 table ============
{
  const s = content("Tasks 1-3", "Task 3: all eight models on the test set", { speaker: A, time: "0:45",
    summary: ["Test split of 33,463 flows, DDoS positive; rows sorted by F1.", "XGBoost 0 FP / 0 FN; Gaussian Naive Bayes weakest (327 FP)."],
    notes: "This is the comparison table from the test split, sorted by F1, DDoS is the positive class. All eight models are between 0.9895 and 1.0000 accuracy and from 0.9909 to 1.0000 F1. XGBoost has no error at all. Random Forest and KNN follow, then the MLP, the LSTM and the CNN. Logistic Regression has 44 false positives and Gaussian Naive Bayes is the weakest with 327 false positives, which lowers its precision to 0.9832. Because the scores are so close to 1, we look at errors on the next slide rather than at accuracy." });
  const H = ["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "FP", "FN"];
  const D = [
    ["XGBoost", "1.0000", "1.0000", "1.0000", "1.0000", "1.0000", "0", "0"],
    ["Random Forest", "0.9999", "1.0000", "0.9998", "0.9999", "1.0000", "0", "3"],
    ["K-Nearest Neighbors", "0.9998", "0.9999", "0.9997", "0.9998", "0.9999", "1", "5"],
    ["MLP", "0.9995", "0.9997", "0.9994", "0.9995", "1.0000", "6", "12"],
    ["LSTM", "0.9990", "0.9992", "0.9992", "0.9992", "1.0000", "16", "16"],
    ["1D-CNN", "0.9990", "0.9993", "0.9990", "0.9991", "1.0000", "13", "20"],
    ["Logistic Regression", "0.9980", "0.9977", "0.9988", "0.9983", "0.9999", "44", "23"],
    ["Gaussian Naive Bayes", "0.9895", "0.9832", "0.9986", "0.9909", "0.9880", "327", "26"],
  ];
  const rows = [H.map((h, i) => hcell(h, i ? "right" : "left"))].concat(D.map((r, ri) => r.map((v, i) => cell(v, i ? "right" : "left", ri === 0 ? { bold: true } : {}))));
  table(s, rows, 0.6, 1.4, 12.1, [3.1, 1.35, 1.35, 1.25, 1.25, 1.35, 1.2, 1.25], 0.52);
  stat(s, 0.6, 6.2, 12.1, 0.7, "", "", C.text2);
  s.addText("Test split: 33,463 flows (19,202 DDoS, 14,261 BENIGN). FP = benign flagged as attack, FN = missed attack.",
    { x: 0.6, y: 6.2, w: 12.1, h: 0.7, fontSize: 14, color: C.text1, margin: [0, 0.2, 0, 0.2], valign: "middle", isTextBox: true });
}

// ============ 7. Errors ============
{
  const s = content("Tasks 1-3", "Errors tell the models apart, not accuracy", { speaker: A, time: "0:35",
    summary: ["Total errors: XGBoost 0, Random Forest 3, KNN 6, MLP 18, LSTM 32, 1D-CNN 33, Logistic Regression 67, Gaussian NB 353 (327 FP).", "Log-scale FP/FN bars (errors_bar)."],
    notes: "Accuracy alone says little when every model lies between 0.9895 and 1.0000, so we count errors. XGBoost makes none, Random Forest 3, KNN 6. The three networks make 18, 32 and 33 errors, Logistic Regression 67 and Gaussian Naive Bayes 353, of which 327 are false positives. So Gaussian Naive Bayes misses few attacks, recall 0.9986, but raises many false alarms. For a detector, these false alarms and missed attacks decide which model to prefer. The y-axis is logarithmic." });
  img(s, FIG("errors_bar.png"), 2220, 1235, 0.6, 1.3, 8.1, 5.5, "FP and FN per model");
  const rows = [
    [hcell("Model"), hcell("Errors", "right")],
    [cell("XGBoost"), cell("0", "right")],
    [cell("Random Forest"), cell("3", "right")],
    [cell("KNN"), cell("6", "right")],
    [cell("MLP"), cell("18", "right")],
    [cell("LSTM"), cell("32", "right")],
    [cell("1D-CNN"), cell("33", "right")],
    [cell("Logistic Regression"), cell("67", "right")],
    [cell("Gaussian NB"), cell("353", "right")],
  ];
  table(s, rows, 9.0, 1.4, 3.7, [2.5, 1.2], 0.5);
  s.addText("GNB: 327 of 353 are false alarms", { x: 9.0, y: 6.0, w: 3.7, h: 0.6, fontSize: 14, bold: true, color: C.accent1, margin: 0, valign: "top", isTextBox: true });
}

// ============ 8. ROC ============
{
  const s = content("Tasks 1-3", "ROC curves: zoomed in", { speaker: A, time: "0:35",
    summary: ["ROC-AUC 1.0000: RF, XGBoost, MLP, LSTM, 1D-CNN; 0.9999: LR, KNN; 0.9880: GNB.", "XGBoost, Random Forest and KNN lie on top; GNB needs FPR about 0.02.", "Log-x: FPR 0 clipped at 1e-5."],
    notes: "A plain ROC plot would show eight curves in the top-left corner, so we show two zoomed versions. AUC is 1.0000 for Random Forest, XGBoost, MLP, LSTM and the CNN, 0.9999 for Logistic Regression and KNN, and 0.9880 for Gaussian Naive Bayes. On the left, zoomed on small false-positive rates, XGBoost, Random Forest and KNN lie at the top, and the dashed neural networks stay above Logistic Regression. On the right, the false-positive axis is logarithmic, which stresses the low false-alarm region that matters for a detector. FPR zero is clipped at 10 to the minus 5. The curves that rise along a curve at the left edge are an interpolation effect on the log axis, not poor performance. Gaussian Naive Bayes needs a false-positive rate of about 0.02 to reach a true-positive rate near 1." });
  img(s, FIG("roc_test_zoom.png"), 2023, 1223, 0.5, 1.3, 6.1, 3.75, "ROC zoom");
  img(s, FIG("roc_test_logx.png"), 2023, 1223, 6.75, 1.3, 6.1, 3.75, "ROC log-x");
  caption(s, "FPR up to 0.01, TPR from 0.990", 0.5, 5.15, 6.1, "center");
  caption(s, "Logarithmic FPR axis, FPR 0 clipped at 1e-5", 6.75, 5.15, 6.1, "center");
  stat(s, 0.6, 5.65, 3.9, 1.2, "1.0000", "AUC of RF, XGBoost, MLP, LSTM, 1D-CNN", C.text2, C.background2, 26);
  stat(s, 4.7, 5.65, 3.9, 1.2, "0.9999", "AUC of Logistic Regression and KNN", C.text2, C.background2, 26);
  stat(s, 8.8, 5.65, 3.9, 1.2, "0.9880", "AUC of Gaussian Naive Bayes", C.accent1, C.background2, 26);
}

// ============ 9. Cost ============
{
  const s = content("Tasks 1-3", "Cost: training and prediction time", { speaker: A, time: "0:25",
    summary: ["Train: GNB 0.063 s, KNN 0.008 s, XGBoost 2.021 s, RF 3.847 s, LR 17.348 s, MLP 42.244 s, 1D-CNN 65.544 s, LSTM 136.034 s.", "KNN predict 4.204 s vs at most 0.173 s for the others.", "Single run, order of magnitude only."],
    notes: "Training cost: Gaussian Naive Bayes 0.063 seconds, KNN 0.008 seconds because it only stores the data, XGBoost 2 seconds, Random Forest 3.8 seconds. The neural networks are the most expensive: MLP 42 seconds, CNN 66 and LSTM 136 seconds. KNN reverses the picture at prediction time, 4.2 seconds for the test set against at most 0.173 seconds for every other model. These times come from a single run and only show the order of magnitude." });
  img(s, FIG("time_bar.png"), 2223, 1223, 0.6, 1.3, 7.9, 5.5, "Train and predict time");
  stat(s, 8.9, 1.4, 3.85, 1.5, "2.021 s", "XGBoost training, best model");
  stat(s, 8.9, 3.1, 3.85, 1.5, "136.034 s", "LSTM training, slowest", C.accent1);
  stat(s, 8.9, 4.8, 3.85, 1.5, "4.204 s", "KNN prediction on the test set; at most 0.173 s for the others", C.text2, C.background2, 28);
  s.addText("Single run, order of magnitude only.", { x: 8.9, y: 6.45, w: 3.85, h: 0.35, fontSize: 12, italic: true, color: C.accent4, margin: 0, isTextBox: true });
}

// ============ 10. XDP ============
{
  const s = content("Tasks 4-5", "Task 4: eBPF and XDP in one slide", { speaker: J, time: "0:50",
    summary: ["eBPF: sandboxed programs in the kernel, checked by the verifier, state in maps.", "XDP: hook in the NIC driver before sk_buff allocation; actions DROP, PASS, TX, REDIRECT, ABORTED.", "Our filter: per-source-IP rate limiter, 100 pkt/s, one LRU map, attached with ip."],
    notes: "Task 4 asks what eBPF and XDP are and for a small filter program. eBPF runs small sandboxed programs inside the Linux kernel. The verifier checks every path before loading, and state lives in maps that are shared with user space. XDP is an eBPF hook in the network driver, right after the packet arrives and before the kernel allocates an sk_buff. The program returns one of five actions: drop, pass, transmit back, redirect, or aborted. Because there is no sk_buff yet, drops are cheap, tens of millions of packets per second per core is the order of magnitude reported in the literature, and that is why XDP suits DDoS mitigation. Our filter is a per-source-IP rate limiter of about 80 lines, attached with a single ip link command. The decision path: first a bounds check on every header, then IPv4 only, everything else passes. Then we look up the source address in one map called rl_state, or create an entry. If more than one second has passed since the window started, the window and the counter are reset. The counter is incremented atomically, and above 100 packets in the window the program returns XDP_DROP, otherwise XDP_PASS. The map is an LRU hash, so a flood of new spoofed sources can never make the program refuse a new entry: the oldest one is evicted. It is a shared map, not per-CPU, so the limit of 100 holds across all CPUs even when packets of one source arrive on several of them. The box on the right shows exactly this last part of the program." });
  const items = [
    ["What", "Sandboxed programs in the kernel; the verifier checks them; state in maps"],
    ["Hook", "In the NIC driver, before the sk_buff is allocated"],
    ["Actions", "DROP, PASS, TX, REDIRECT, ABORTED"],
    ["Why cheap", "No sk_buff yet: tens of millions of drops per second per core"],
    ["Our filter", "Per-source-IP rate limiter: 100 pkt/s, one LRU map, attached with ip"],
  ];
  items.forEach((r, i) => {
    const y = 1.35 + i * 1.08;
    s.addText(r[0], { x: 0.6, y, w: 1.5, h: 0.35, fontSize: 16, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    s.addText(r[1], { x: 0.6, y: y + 0.35, w: 4.9, h: 0.65, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  });
const CODE = [
  "\tif (now - r->win_start >= WINDOW_NS) {  /* new window */",
  "\t\tr->win_start = now;",
  "\t\tr->count = 0;",
  "\t}",
  "",
  "\t/* Atomic, because packets of one source can arrive on several CPUs. */",
  "\tif (__sync_fetch_and_add(&r->count, 1) >= LIMIT_PPS) {",
  "\t\t__sync_fetch_and_add(&r->dropped, 1);",
  "\t\treturn XDP_DROP;",
  "\t}",
  "\t__sync_fetch_and_add(&r->passed, 1);",
  "\treturn XDP_PASS;",
].map((l) => l.replace(/\t/g, "    ")).join("\n");
  s.addShape(pres.shapes.RECTANGLE, { x: 5.6, y: 1.3, w: 7.2, h: 3.8, fill: { color: "1B2433" }, line: { color: "1B2433" }, objectName: "code box" });
  s.addText(CODE, { x: 5.75, y: 1.4, w: 6.95, h: 3.6, fontFace: "Courier New", fontSize: 11, color: "EEF2F7", valign: "top", margin: 0, isTextBox: true, objectName: "code" });
  caption(s, "xdp_ratelimit.bpf.c, lines 64-75: window reset, atomic count, drop or pass", 5.6, 5.25, 7.2);
}

// ============ 11. Test bed + results ============
{
  const s = content("Tasks 4-5", "Limit of 100 packets/s per source holds", { speaker: J, time: "0:55",
    summary: ["Test bed: one namespace (attacker 10.0.0.2, benign client 10.0.0.3), host 10.0.0.1 on veth0 is the victim; 5 s hping3 SYN flood to port 80; limit 100 pkt/s.", "Packets counted with nstat IpInReceives: the host's ufw firewall drops SYNs before TCP, so TcpInSegs stayed near zero.", "Baseline 372,537 sent / 372,564 at the IP layer (27 other host traffic); with XDP 697,064 sent / 525 = 500 flood + 25 pings; benign ping 25/25, 0 % loss.", "Not a throughput measurement: attacker and victim share one machine."],
    notes: "To test without touching the real network, we use one network namespace called atk. It holds the attacker at 10.0.0.2 and a benign client at 10.0.0.3. The host itself is 10.0.0.1 on a virtual interface, veth0, and is the victim. The filter is attached to veth0 in generic mode with one ip link command. The attacker runs a SYN flood with hping3 for 5 seconds against port 80, and the benign client pings. The limit is 100 packets per second per source. We count packets with the kernel counter IpInReceives from nstat, not TcpInSegs, because the host's ufw firewall drops the SYNs before they reach TCP, so the TCP counter stayed near zero. Without XDP the attacker sends 372,537 packets and 372,564 arrive at the IP layer; the 27 extra are other traffic on the host. With the filter the attacker sends 697,064 packets and the victim sees 525 packets: that is exactly 500 flood packets, 100 per second for 5 seconds, plus the 25 pings of the benign client. The benign ping has no loss, 25 of 25. The attacker sent almost twice as many packets with the filter on. We attribute this to the host no longer spending time on every SYN, since attacker and victim share one machine. So this is not a throughput measurement of XDP; it shows that the limit is enforced and that benign traffic is not affected." });
  const rows = [
    [hcell("Round"), hcell("XDP mode / loader"), hcell("Packets sent", "right"), hcell("Packets at victim (IP layer)", "right"), hcell("Benign ping loss", "right")],
    [cell("Baseline"), cell("none"), cell("372,537", "right"), cell("372,564", "right"), cell("\u2013", "right")],
    [cell("XDP"), cell("generic, ip"), cell("697,064", "right"), cell("525 (500 flood + 25 ping)", "right", { bold: true }), cell("0 %", "right")],
  ];
  table(s, rows, 0.6, 1.3, 12.1, [1.6, 2.6, 2.0, 3.9, 2.0], 0.45);
  // real size of task4_flood_xdp.png is 856 x 401
  caption(s, "Flood with the limiter: 500 of 697,064 flood packets reach the victim, benign ping 0 % loss (25/25)", 0.6, 2.85, 12.1);
  img(s, XDPI("task4_flood_xdp.png"), 856, 401, 1.5, 3.3, 10.3, 3.6, "Flood with XDP");
}

// ============ 12. Per-source counters ============
{
  const s = content("Tasks 4-5", "Per-source counters in the map", { speaker: J, time: "0:40",
    summary: ["bpftool dump of rl_state: attacker passed 500 + dropped 696,564 = 697,064 sent; benign passed 25, dropped 0.", "Future work: a block-list map that a user-space detector fills (Gatebot detects, L4Drop enforces at Cloudflare).", "No block list and no trained model connected yet; the rate limiter works without any model."],
    notes: "After the test we read the state map with bpftool. It has one entry per source address. The attacker, 10.0.0.2, has 500 packets passed and 696,564 dropped, together 697,064, which is exactly the number hping3 reported as sent. The benign client, 10.0.0.3, has 25 passed and none dropped. So the counters match the test result and the limiter treats the two sources separately. A natural next step, which we did not build, is a second map as a block list that a user-space detector fills. This is the division of labour Cloudflare uses at scale: Gatebot detects in user space and L4Drop enforces in XDP. The classifier's decision latency would then matter once per flow, not per packet, which is why the prediction times on the cost slide would be acceptable. Honest limit: there is no block list in our program and no trained model is connected to it. The rate limiter works without any model." });
  // real size of task4_map_dump.png is 851 x 382
  img(s, XDPI("task4_map_dump.png"), 851, 382, 0.6, 1.3, 7.4, 3.5, "bpftool map dump");
  s.addText([
    { text: "Attacker: 500 passed + 696,564 dropped = 697,064 sent", options: { bullet: true, breakLine: true } },
    { text: "Benign client: 25 passed, 0 dropped", options: { bullet: true, breakLine: true } },
    { text: "Counters match the test: one entry per source", options: { bullet: true } },
  ], { x: 8.3, y: 1.4, w: 4.5, h: 3.4, fontSize: 18, color: C.text1, valign: "top", paraSpaceAfter: 10, margin: 0, isTextBox: true });
  s.addText("Future work (not built)", { x: 0.6, y: 5.0, w: 12.1, h: 0.4, fontSize: 18, bold: true, color: C.accent1, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  const chips = [["Detector", "ML model in user space flags a source"], ["Block-list map", "a second BPF map, filled by user space"], ["XDP drop", "decision latency matters once per flow"]];
  chips.forEach((c, i) => {
    const x = 0.6 + i * 4.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.5, w: 3.6, h: 1.3, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "chip " + c[0] });
    s.addText(c[0], { x: x + 0.2, y: 5.55, w: 3.2, h: 0.45, fontSize: 18, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    s.addText(c[1], { x: x + 0.2, y: 6.0, w: 3.2, h: 0.75, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
    if (i < 2) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 3.7, y: 5.95, w: 0.4, h: 0.4, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "arrow " + i });
  });
}

// ============ 13. Task 5 ============
{
  const s = content("Tasks 4-5", "Task 5: xdp-tools built from source", { speaker: J, time: "0:45",
    summary: ["Cloned at commit 92a98287fd59 (v1.6.3-32), clang 21.1.8, bpftool v7.7.0; make finished without errors.", "Tools: libxdp, xdp-loader, xdp-filter, xdpdump, xdp-bench and others.", "install_and_verify.sh: make install + help, features lo, status: ALL CHECKS PASSED.", "Screenshot: xdp-filter on lo, ping from 127.0.0.2 blocked (SS_T7_9)."],
    notes: "Task 5 asks to download and configure xdp-tools. We cloned the repository at commit 92a98287fd59, configured it with clang 21 and bpftool 7.7, and built it with make without errors or warnings. It produces libxdp and the tools xdp-loader, xdp-filter, xdpdump, xdp-bench and others. To verify it, our script install_and_verify.sh runs make install and then the help commands of xdp-loader, xdp-filter and xdpdump, xdp-loader features on lo, and xdp-loader status. The final run ended with ALL CHECKS PASSED. The screenshot shows the manual check on the loopback interface: a drop rule for 127.0.0.2, pings from 127.0.0.1 have no loss and pings from 127.0.0.2 are lost completely. xdp-filter drops by address with a ready-made tool but has no rate limiting; our program limits per source." });
  card(s, 0.6, 1.3, 5.6, 1.7, "Build", ["Commit 92a98287fd59 (v1.6.3-32)", "clang 21.1.8, bpftool v7.7.0, make without errors"]);
  card(s, 0.6, 3.2, 5.6, 1.7, "Tools", ["libxdp, xdp-loader, xdp-filter, xdpdump, xdp-bench, xdp-monitor, xdp-trafficgen, xdp-forward"]);
  card(s, 0.6, 5.1, 5.6, 1.7, "Verification", ["install_and_verify.sh: make install + help, features lo, status: ALL CHECKS PASSED"], C.accent6);
  const r13 = img(s, SS("SS_T7_9.png"), 543, 312, 6.5, 1.3, 6.3, 4.8, "xdp-filter drop rule on lo");
  caption(s, "xdp-filter on lo: pings from 127.0.0.1 0 % loss, from 127.0.0.2 100 % loss", 6.5, r13.y + r13.h + 0.15, 6.3);
}

// ============ 14. Conclusion ============
{
  const meta = { speaker: `${A}, ${J}`, time: "0:50",
    summary: ["Tree ensembles and KNN best (0-6 errors, order within noise); MLP best DL (F1 0.9995).", "Limits: port-80 shortcut, one dataset/split, no block list / ML connection yet (future work).", "Questions."],
    notes: "To summarize the detection part, Aayush: all eight models detect the DDoS flows very well, F1 from 0.9909 to 1.0000. The tree ensembles and KNN are best with zero to six errors on 33,463 test flows, and their order is within noise. Among the networks the MLP is best with F1 0.9995, but none beats the tree ensembles, which also train in seconds. The LSTM only became competitive after tuning. Limitations: the destination port is a shortcut, we use one dataset from one day, one attack type and one split, and differences of a few errors could change with another seed. Justlyn: on the enforcement side, an XDP rate limiter drops floods in the driver and leaves benign traffic untouched. A block list that a detector fills is future work: we did not build it and did not connect a trained model, and the filter assumes honest source addresses and covers IPv4 only. Thank you, we are happy to take questions." };
  ensureSection("Conclusion");
  const s = pres.addSlide({ masterName: "CLOSING", sectionTitle: "Conclusion" });
  const title = "Conclusion and limitations";
  s.addText(title, { placeholder: "title" });
  s.addNotes(`Speaker: ${meta.speaker} (about ${meta.time}).\n\n${meta.notes}`);
  SLIDES.push({ title, ...meta });
  s.addText("Questions?", { x: 0.6, y: 5.6, w: 4.0, h: 0.8, fontSize: 34, bold: true, color: C.background1, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  s.addText("Aayush Kapoor · Justlyn Kaniyanthara Johnson", { x: 0.6, y: 6.4, w: 4.1, h: 0.6, fontSize: 14, color: C.background2, margin: 0, valign: "top", isTextBox: true });
  s.addText("Findings", { x: 5.5, y: 0.6, w: 7.3, h: 0.45, fontSize: 22, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  s.addText([
    { text: "Tree ensembles and KNN are best: 0-6 errors on 33,463 flows, order within noise", options: { bullet: true, breakLine: true } },
    { text: "MLP is the best network (F1 0.9995); none beats the tree ensembles", options: { bullet: true, breakLine: true } },
    { text: "XDP limiter: 500 of 697,064 flood packets reach the victim, benign ping 0 % loss", options: { bullet: true } },
  ], { x: 5.5, y: 1.15, w: 7.3, h: 2.5, fontSize: 18, color: C.text1, valign: "top", paraSpaceAfter: 10, margin: 0, isTextBox: true });
  s.addText("Limitations", { x: 5.5, y: 3.85, w: 7.3, h: 0.45, fontSize: 22, bold: true, color: C.accent1, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  s.addText([
    { text: "Port-80 shortcut, no ablation", options: { bullet: true, breakLine: true } },
    { text: "One dataset, one day, one attack type, one split", options: { bullet: true, breakLine: true } },
    { text: "No block list / ML connection yet (future work)", options: { bullet: true, breakLine: true } },
    { text: "Rate limiter: IPv4 only, trusts source addresses", options: { bullet: true } },
  ], { x: 5.5, y: 4.4, w: 7.3, h: 2.4, fontSize: 18, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true });
}

// ---------- Presentation.md ----------
function writeMd() {
  const total = SLIDES.reduce((t, s) => { const [m, sec] = s.time.split(":").map(Number); return t + m * 60 + sec; }, 0);
  const per = {};
  SLIDES.forEach((s) => { const [m, sec] = s.time.split(":").map(Number); s.speaker.split(", ").forEach((n) => { per[n] = (per[n] || 0) + (m * 60 + sec) / s.speaker.split(", ").length; }); });
  const fmt = (t) => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, "0")}`;
  let md = `# Lab 3 Presentation: ML/DL DDoS Detection and eBPF/XDP (Group 8)\n\n**Security Insider Lab I, Uni Passau, Group 8**\nJustlyn Kaniyanthara Johnson (121024), Aayush Kapoor (120957), presentation 25 November 2026\n\nDeck: \`G8.Lab3.Presentation.pptx\` (${SLIDES.length} slides), built by \`build_deck.js\`. Source: \`G8.Report3.pdf\`; every number comes from the report, \`outputs/metrics/comparison_test.md\` or \`xdp/ratelimit/task4_terminal_output.txt\`. The scripts below are the speaker notes of each slide.\n\nTime budget: 10 minutes plus 2 minutes discussion. Planned total ${fmt(total)}. Aayush Kapoor presents Tasks 1-3 (about ${fmt(per[A])}), Justlyn Kaniyanthara Johnson presents Tasks 4-5 (about ${fmt(per[J])}); the conclusion is shared.\n\n| Slide | Title | Speaker | Time |\n|---|---|---|---|\n`;
  SLIDES.forEach((s, i) => { md += `| ${i + 1} | ${s.title} | ${s.speaker} | ${s.time} |\n`; });
  md += "\n---\n\n";
  SLIDES.forEach((s, i) => {
    md += `## Slide ${i + 1}. ${s.title}\n\n**Speaker:** ${s.speaker} · **Time:** about ${s.time}\n\n`;
    if (s.summary) md += s.summary.map((t) => `- ${t}`).join("\n") + "\n\n";
    md += `**Script.** ${s.notes}\n\n`;
  });
  fs.writeFileSync(MD, md);
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  writeMd();
  console.log("wrote", OUT);
})();
