// Builds the Lab 2 presentation (G8) from the numbers and figures of G8.Report2.pdf.
// Run from anywhere: node build_deck.js
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/home/aayush/.claude/skills/synced/e4cc6236-64d8-44be-b91e-bba57ace04f8_ba5af316-0eaf-43fa-8a67-209d84f411bf/pptx/scripts/apply_theme.js");

const LAB2 = path.resolve(__dirname, "../..");
const P = (...p) => path.join(LAB2, ...p);
const OUT = path.join(__dirname, "G8.Lab2.Presentation.pptx");

const THEME = {
  name: "G8 Lab2 Passau",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2433", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "EEF2F7",
    accent1: "F39200", accent2: "1F3A5F", accent3: "4F7CAC",
    accent4: "8C8C8C", accent5: "C0392B", accent6: "2E8B57",
    hlink: "4F7CAC", folHlink: "8C8C8C",
  },
};
const H = THEME.colors; // hex, only for hex-only options (charts)

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "Justlyn Kaniyanthara Johnson, Aayush Kapoor";
pres.title = "Lab 2: Machine Learning for Network Attack Detection";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

const SW = 13.333, SH = 7.5;
const LOGO = { path: P("reports/images/uni-logo.png"), x: SW - 0.45 - 2.1, y: 0.3, w: 2.1, h: 2.1 * 133 / 500 };
const FOOT = "Group 8 · Security Insider Lab I · Lab 2";

// ---------- layouts ----------
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: C.background1 },
  objects: [
    { rect: { x: 0, y: 0, w: 8.2, h: SH, fill: { color: C.text2 } } },
    { image: LOGO },
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.6, w: 7.0, h: 2.4,
        fontSize: 40, bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.25, w: 7.0, h: 2.5,
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
        fontSize: 32, bold: true, color: C.text2, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: FOOT, options: { x: 0.6, y: 7.05, w: 6, h: 0.3, fontSize: 10, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.7, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

pres.defineSlideMaster({
  title: "CLOSING",
  background: { color: C.background1 },
  objects: [
    { rect: { x: 0, y: 0, w: 5.6, h: SH, fill: { color: C.text2 } } },
    { image: LOGO },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.5, w: 4.6, h: 1.4,
        fontSize: 32, bold: true, color: C.background1, valign: "top", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.7, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

// ---------- helpers ----------
const shadow = () => ({ type: "outer", color: "000000", opacity: 0.15, blur: 6, offset: 2, angle: 90 });

function content(section, title) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}

// fit image (px dims) into box, centered
function img(s, file, pw, ph, x, y, w, h, name, border = true) {
  const r = Math.min(w / pw, h / ph);
  const iw = pw * r, ih = ph * r;
  const ix = x + (w - iw) / 2, iy = y + (h - ih) / 2;
  if (border) s.addShape(pres.shapes.RECTANGLE, { x: ix - 0.04, y: iy - 0.04, w: iw + 0.08, h: ih + 0.08,
    fill: { color: C.background1 }, line: { color: C.background2, width: 1 }, shadow: shadow(), objectName: name + " frame" });
  s.addImage({ path: file, x: ix, y: iy, w: iw, h: ih, altText: name, objectName: name });
  return { x: ix, y: iy, w: iw, h: ih };
}

function caption(s, text, x, y, w) {
  s.addText(text, { x, y, w, h: 0.3, fontSize: 11, italic: true, color: C.accent4, margin: 0, isTextBox: true });
}

// stat callout: big number + label in a tinted card
function stat(s, x, y, w, h, value, label, color = C.text2, fill = C.background2) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: "stat " + label });
  s.addText(value, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: h * 0.52, fontSize: 30, bold: true, color, fontFace: THEME.headFontFace, margin: 0, valign: "bottom", isTextBox: true });
  s.addText(label, { x: x + 0.2, y: y + 0.12 + h * 0.52, w: w - 0.4, h: h * 0.40 - 0.12, fontSize: 13, color: C.text1, margin: 0, valign: "top", isTextBox: true });
}

// numbered circle
function badge(s, x, y, d, n, color = C.accent1) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color }, objectName: "badge " + n });
  s.addText(String(n), { x, y, w: d, h: d, fontSize: d > 0.5 ? 18 : 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
}

function bullets(s, items, x, y, w, h, fontSize = 15) {
  const runs = items.map((it, i) => {
    const last = i === items.length - 1;
    // {b: "Bold lead", t: " rest"}: the bold lead marks each paragraph
    return [
      { text: it.b, options: { bold: true, color: C.text2 } },
      { text: it.t, options: { breakLine: !last } },
    ];
  }).flat();
  s.addText(runs, { x, y, w, h, fontSize, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true });
}

function card(s, x, y, w, h, name, fill = C.background2) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name });
}

const TH = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });

// ====================================================================
// 1. Title
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Introduction" });
  s.addText("Machine Learning for Network Attack Detection", { placeholder: "title" });
  s.addText([
    { text: "Security Insider Lab I · Lab 2", options: { bold: true, color: C.accent1, breakLine: true } },
    { text: "Group 8", options: { breakLine: true } },
    { text: "Justlyn Kaniyanthara Johnson (121024)", options: { breakLine: true } },
    { text: "Aayush Kapoor (120957)", options: { breakLine: true } },
    { text: "6 November 2026", options: { fontSize: 14 } },
  ], { placeholder: "body", paraSpaceAfter: 4 });
  // key results on the right
  const x = 8.75, w = 4.1;
  stat(s, x, 1.55, w, 1.5, "164,179", "clean CIC-IDS2017 flows, 60 features");
  stat(s, x, 3.3, w, 1.5, "0.986", "attack F1 of the Decision Tree (test split)");
  stat(s, x, 5.05, w, 1.5, "0.55 %", "false alarms on our own benign traffic", C.accent5);
  s.addNotes("Lab 2 of the Security Insider Lab: detecting network attacks from flow features with Logistic Regression and Decision Trees. The three numbers on the right are the story of the talk.");
}

// 2. Overview
{
  const s = content("Introduction", "Four Tasks, One Pipeline");
  const tasks = [
    ["Task 1", "Flows", "Capture our own traffic and convert it into flows with CICFlowMeter"],
    ["Task 2", "Dataset", "Choose and analyze CIC-IDS2017: Thursday web-attack file"],
    ["Task 3", "Pre-processing", "Clean inf/NaN and duplicates, min-max scale, select 20 features with χ²"],
    ["Task 4", "Classifiers", "Train LR and Decision Tree, then classify our own flows one by one"],
  ];
  const w = 2.85, gap = 0.3, x0 = 0.6, y = 1.5, h = 3.0;
  tasks.forEach(([t, head, body], i) => {
    const x = x0 + i * (w + gap);
    card(s, x, y, w, h, "task card " + (i + 1));
    badge(s, x + 0.3, y + 0.3, 0.6, i + 1);
    s.addText(t, { x: x + 1.05, y: y + 0.3, w: w - 1.2, h: 0.3, fontSize: 12, color: C.accent4, margin: 0, isTextBox: true });
    s.addText(head, { x: x + 1.05, y: y + 0.58, w: w - 1.2, h: 0.35, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
    s.addText(body, { x: x + 0.3, y: y + 1.15, w: w - 0.6, h: h - 1.35, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  });
  // dataset choice callout
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.9, w: 12.3, h: 1.75, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 }, objectName: "dataset choice" });
  s.addText([
    { text: "Our dataset choice  ", options: { bold: true, color: C.accent1, fontSize: 18, breakLine: true } },
    { text: "The slides suggest the Friday DDoS file. We chose Thursday-WorkingHours-Morning-WebAttacks instead: Brute Force, XSS and SQL injection are low-volume, application-layer attacks whose flows look like ordinary HTTP. Volume alone gives a DDoS away, so web attacks are harder, and more interesting, to detect.", options: { fontSize: 15, color: C.background1 } },
  ], { x: 0.9, y: 5.05, w: 11.7, h: 1.45, valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("Overview of the four lab tasks and why we deviated from the suggested DDoS dataset.");
}

// 3. Task 1: Flows
pres.addSection({ title: "Task 1: Flows" });
{
  const s = content("Task 1: Flows", "Task 1: From Packets to Flows");
  bullets(s, [
    { b: "A flow ", t: "summarizes a bidirectional packet exchange identified by IPs, ports and protocol" },
    { b: "84 columns: ", t: "metadata, 77 numeric features (packet lengths, inter-arrival times, TCP flags, window sizes, idle/active times) and a label" },
    { b: "A flow ends ", t: "on FIN/RST, after 5 s of inactivity or after 120 s in total" },
    { b: "Only flows with ≥ 2 packets ", t: "are written, so a lone DNS query or traceroute probe never appears" },
    { b: "Our capture: ", t: "81,110 frames over 347.4 s of browsing, DNS and the Steam client (4 Nov 2026), benign by construction" },
  ], 0.6, 1.5, 6.2, 5.2, 16);
  const r = img(s, P("SS/SS25.png"), 900, 741, 7.2, 1.45, 5.7, 5.1, "CICFlowMeter offline conversion");
  caption(s, "CICFlowMeter offline mode: 81,110 packets → 569 flows (570 lines incl. header)", r.x, r.y + r.h + 0.1, r.w);
  s.addNotes("Explain what a flow is and how CICFlowMeter terminates flows. The screenshot shows the offline conversion of our final capture with default timeouts.");
}

// 4. IPv6 problem
{
  const s = content("Task 1: Flows", "The IPv6 Problem: 95 % Garbage Flows");
  s.addChart(pres.charts.BAR, [{ name: "Valid TCP/UDP flows", labels: ["1st capture (98 % IPv6)", "2nd capture (89.5 % IPv6)", "3rd capture (IPv6 off)"], values: [14.7, 5.0, 96.1] }], {
    x: 0.6, y: 1.45, w: 6.0, h: 4.6, barDir: "col",
    showTitle: true, title: "Share of valid TCP/UDP flows (%)", titleFontSize: 14, titleColor: H.dk2, titleFontFace: "+mn-lt",
    chartColors: [H.accent4, H.accent4, H.accent6], valAxisMaxVal: 100, valAxisMinVal: 0,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 13, dataLabelColor: H.dk1, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "0.0\"%\"",
    catAxisLabelColor: H.dk1, valAxisLabelColor: H.accent4, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: "E3E7ED", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
    objectName: "valid flow share chart", altText: "Valid TCP/UDP flows: 78 of 532, 67 of 1,327, 547 of 569",
  });
  caption(s, "Valid flows: 78/532, 67/1,327, 547/569", 0.6, 6.15, 6.0);
  bullets(s, [
    { b: "Symptom: ", t: "protocol 0, port 0 and impossible IPs in most flows of the first two captures" },
    { b: "Root cause: ", t: "readIP6 = false is hard-coded in CICFlowMeter (Cmd.java:126); every non-IPv4 frame is force-parsed as an IPv4 header from byte 0" },
    { b: "Fake IPs: ", t: "134.221.96.0 = 86 DD 60 00, i.e. the IPv6 EtherType; 136.225.x = HomePlug, 8.6.x = ARP" },
    { b: "Fix: ", t: "disable IPv6 on the capturing laptop, which keeps flows IPv4-only like the training data" },
  ], 7.0, 1.5, 5.9, 3.9, 15);
  const r = img(s, P("SS/SS24.png"), 559, 148, 7.0, 5.55, 5.9, 1.05, "sysctl disable IPv6");
  s.addNotes("Our first two captures were mostly IPv6. We traced the bogus flows to CICFlowMeter's hard-coded IPv4-only parsing. We did not enable its IPv6 path because its UDP branch reads the header length from the TCP header.");
}

// 5. Final capture
{
  const s = content("Task 1: Flows", "The Final Capture: 547 Usable Flows");
  const w = 2.85, gap = 0.3;
  [["569", "flows written by CICFlowMeter"], ["547", "TCP/UDP flows classified"], ["22", "protocol-0 flows dropped (ICMP, ARP, IPv6)"], ["99.94 %", "of frames are IPv4"]]
    .forEach(([v, l], i) => stat(s, 0.6 + i * (w + gap), 1.45, w, 1.35, v, l, i === 2 ? C.accent4 : C.text2));
  const r = img(s, P("SS/SS15.png"), 1483, 625, 0.6, 3.1, 8.0, 3.45, "Wireshark protocol hierarchy");
  caption(s, "Wireshark protocol hierarchy of task1_lab2.pcapng", r.x, r.y + r.h + 0.1, r.w);
  bullets(s, [
    { b: "289 ", t: "flows are DNS queries (port 53)" },
    { b: "213 ", t: "flows go to port 443, 15 to port 80" },
    { b: "≈ 70 % ", t: "of valid flows are UDP: DNS, QUIC, Steam" },
    { b: "Domain shift ahead: ", t: "QUIC and Steam did not exist in the 2017 testbed" },
  ], 8.95, 3.15, 3.95, 3.5, 15);
  s.addNotes("With IPv6 off, 547 of 569 flows are valid. The classified flows contain 99.8 % of all IPv4 TCP/UDP frames; the rest are single-packet exchanges.");
}

// 6. Task 2: Dataset
pres.addSection({ title: "Task 2: Dataset" });
{
  const s = content("Task 2: Dataset", "Task 2: CIC-IDS2017 Web Attacks");
  s.addText("Thursday-WorkingHours-Morning-WebAttacks: 170,366 flows, 78 features + Label. Attacks were run against DVWA and automated with Selenium.",
    { x: 0.6, y: 1.4, w: 7.4, h: 0.75, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  const rows = [
    [TH("Label"), TH("Raw"), TH("Share"), TH("Cleaned")],
    ["BENIGN", "168,186", "98.72 %", "162,036"],
    ["Web Attack – Brute Force", "1,507", "0.88 %", "1,470"],
    ["Web Attack – XSS", "652", "0.38 %", "652"],
    ["Web Attack – SQL Injection", "21", "0.01 %", "21"],
    [{ text: "Total", options: { bold: true } }, { text: "170,366", options: { bold: true } }, { text: "100 %", options: { bold: true } }, { text: "164,179", options: { bold: true } }],
  ];
  s.addTable(rows, { x: 0.6, y: 2.35, w: 7.4, colW: [3.2, 1.4, 1.4, 1.4], fontSize: 15, color: C.text1,
    border: { type: "solid", color: C.background2, pt: 1 }, rowH: 0.5, align: "left", valign: "middle", objectName: "label distribution" });
  s.addText("Attacks are 1.28 % of the raw flows; only 21 SQL injection flows exist.",
    { x: 0.6, y: 5.6, w: 7.4, h: 0.5, fontSize: 14, italic: true, color: C.accent4, margin: 0, isTextBox: true });
  stat(s, 8.5, 1.45, 4.4, 1.55, "98.7 %", "accuracy of a model that always answers BENIGN, so we report per-class F1 and macro-F1", C.accent5);
  stat(s, 8.5, 3.25, 4.4, 1.55, "Port 80", "is the destination of all 2,180 attack flows, a shortcut a model can learn", C.accent1);
  stat(s, 8.5, 5.05, 4.4, 1.55, "1 : 76", "attacks to benign flows after cleaning");
  s.addNotes("The dataset is extremely imbalanced, so accuracy is meaningless. All attacks target port 80, which becomes a shortcut feature.");
}

// 7. Task 3: pipeline steps
pres.addSection({ title: "Task 3: Pre-processing" });
{
  const s = content("Task 3: Pre-processing", "Task 3: Pre-processing in Nine Steps");
  const steps = [
    ["Load & fix labels", "Strip 65 padded column names; U+FFFD → “-” in labels"],
    ["Drop duplicate column", "Fwd Header Length appears twice"],
    ["±∞ → NaN, drop rows", "135 rows, all BENIGN (Flow Bytes/s, Flow Packets/s)"],
    ["Drop duplicate rows", "Before the split, so no row lands in train and test"],
    ["Drop constant columns", "10 columns that never change"],
    ["Drop identical columns", "7 pairs (tolerance 1e-6), so the 20 features are distinct"],
    ["Stratified 70/30 split", "On the 4-class label, random_state = 42"],
    ["Min-max scaling", "MinMaxScaler(clip=True), fitted on train only"],
    ["SelectKBest(χ², k = 20)", "χ² needs non-negative input, so scaling comes first"],
  ];
  const cols = 3, w = 3.95, h = 1.55, gx = 0.225, gy = 0.25, x0 = 0.6, y0 = 1.5;
  steps.forEach(([head, body], i) => {
    const x = x0 + (i % cols) * (w + gx), y = y0 + Math.floor(i / cols) * (h + gy);
    const fill = i >= 6 ? C.text2 : C.background2;
    card(s, x, y, w, h, "step " + (i + 1), fill);
    badge(s, x + 0.2, y + 0.22, 0.5, i + 1, i >= 6 ? C.accent1 : C.text2);
    s.addText(head, { x: x + 0.85, y: y + 0.2, w: w - 1.0, h: 0.55, fontSize: 16, bold: true, color: i >= 6 ? C.background1 : C.text2, margin: 0, valign: "middle", isTextBox: true });
    s.addText(body, { x: x + 0.85, y: y + 0.78, w: w - 1.0, h: 0.65, fontSize: 14, color: i >= 6 ? C.background2 : C.text1, margin: 0, valign: "top", isTextBox: true });
  });
  s.addNotes("Steps 1 to 6 clean the data and use no labels. Steps 7 to 9, in navy, are fitted on the training split only, so no test statistics leak into training.");
}

// 8. Cleaning results
{
  const s = content("Task 3: Pre-processing", "Cleaning Result: 164,179 Flows × 60 Features");
  const r = img(s, P("SS/SS20.png"), 1852, 525, 0.6, 1.4, 12.3, 3.5, "cleaning log");
  caption(s, "Cleaning steps as logged by task3_preprocess.py", r.x, r.y + r.h + 0.1, r.w);
  const w = 2.85, gap = 0.3, y = 5.3;
  [["−135", "rows with ±∞/NaN (all BENIGN)"], ["−6,052", "duplicate rows (37 Brute Force)"], ["−17", "columns: 10 constant, 7 identical"], ["60", "features remain, 2,143 attacks"]]
    .forEach(([v, l], i) => stat(s, 0.6 + i * (w + gap), y, w, 1.35, v, l, i === 3 ? C.accent1 : C.text2));
  s.addNotes("Fwd PSH Flags is identical to SYN Flag Count although they are different TCP flags, a known feature-extraction problem of the CICFlowMeter version used for CIC-IDS2017 (Engelen et al. 2021).");
}

// 9. Feature selection
{
  const s = content("Task 3: Pre-processing", "The 20 Best Features by χ²");
  const feats = [
    ["Init_Win_bytes_backward", 4525.18], ["PSH Flag Count", 2928.73], ["Init_Win_bytes_forward", 1616.52], ["ACK Flag Count", 238.36],
    ["Destination Port", 185.37], ["Bwd IAT Total", 100.41], ["Down/Up Ratio", 75.32], ["Fwd IAT Std", 68.76], ["Fwd PSH Flags", 68.03],
    ["Bwd Packet Length Min", 56.82], ["Idle Max", 49.80], ["Idle Mean", 48.52], ["Idle Min", 46.57], ["URG Flag Count", 44.97],
    ["Packet Length Mean", 41.21], ["min_seg_size_forward", 40.12], ["Bwd Packet Length Mean", 39.02], ["Bwd IAT Max", 38.44],
    ["Fwd IAT Total", 38.11], ["Flow Duration", 37.96],
  ].reverse();
  s.addChart(pres.charts.BAR, [{ name: "χ² score", labels: feats.map(f => f[0]), values: feats.map(f => f[1]) }], {
    x: 0.6, y: 1.35, w: 7.3, h: 5.55, barDir: "bar", barGapWidthPct: 40,
    showTitle: true, title: "χ² score, binary target (min-max-scaled train set)", titleFontSize: 13, titleColor: H.dk2, titleFontFace: "+mn-lt",
    chartColors: [H.dk2],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: H.dk1, dataLabelFormatCode: "#,##0", dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: H.dk1, valAxisLabelColor: H.accent4, catAxisLabelFontSize: 9, valAxisLabelFontSize: 10, valAxisMaxVal: 5000, catAxisLabelFrequency: 1,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: "E3E7ED", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
    objectName: "chi2 feature chart", altText: "Top-20 features by chi2 score for the binary target",
  });
  const x = 8.3, w = 4.6;
  card(s, x, 1.45, w, 1.7, "insight shortcut port");
  s.addText([
    { text: "Shortcut features", options: { bold: true, color: C.accent5, fontSize: 17, breakLine: true } },
    { text: "Init_Win_bytes_* reflect the 2017 hosts' TCP stacks; Destination Port works because every attack hits port 80.", options: { fontSize: 14 } },
  ], { x: x + 0.25, y: 1.55, w: w - 0.5, h: 1.5, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  card(s, x, 3.35, w, 1.7, "insight behavior");
  s.addText([
    { text: "Behavioral features", options: { bold: true, color: C.accent6, fontSize: 17, breakLine: true } },
    { text: "PSH/ACK/URG flags capture HTTP request patterns; IAT and Idle times capture the regular pacing of Selenium.", options: { fontSize: 14 } },
  ], { x: x + 0.25, y: 3.45, w: w - 0.5, h: 1.5, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  card(s, x, 5.25, w, 1.65, "insight overlap");
  s.addText([
    { text: "18 of 20 shared", options: { bold: true, color: C.text2, fontSize: 17, breakLine: true } },
    { text: "Binary and multiclass lists differ in only two features each. The top 3 score above 1,600, the rest below 250.", options: { fontSize: 14 } },
  ], { x: x + 0.25, y: 5.35, w: w - 0.5, h: 1.45, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("χ² on min-max-scaled continuous data is a heuristic: heavy-tailed features like Flow Bytes/s are squeezed towards 0, which lowers their scores. We expect the testbed-specific features to generalize poorly.");
}

// 10. Task 4 setup
pres.addSection({ title: "Task 4: Classifiers" });
{
  const s = content("Task 4: Classifiers", "Task 4: Eight Models, One Pipeline");
  const boxes = [["MinMaxScaler", "clip = True"], ["SelectKBest", "χ², k = 20"], ["Classifier", "LR or Decision Tree"]];
  const bw = 3.4, bh = 1.25, y = 1.6, gap = 1.05;
  boxes.forEach(([h1, h2], i) => {
    const x = 0.6 + i * (bw + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: bh, rectRadius: 0.1, fill: { color: i === 2 ? C.accent1 : C.text2 }, line: { color: i === 2 ? C.accent1 : C.text2 }, shadow: shadow(), objectName: "pipeline " + h1 });
    s.addText([{ text: h1, options: { bold: true, fontSize: 20, breakLine: true } }, { text: h2, options: { fontSize: 15 } }],
      { x, y, w: bw, h: bh, align: "center", valign: "middle", color: C.background1, margin: 0, isTextBox: true });
    if (i < 2) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.2, y: y + bh / 2 - 0.25, w: gap - 0.4, h: 0.5, fill: { color: C.accent4 }, line: { color: C.accent4 }, objectName: "arrow " + i });
  });
  caption(s, "One scikit-learn Pipeline per model, fitted on the 114,925 training flows and saved with joblib", 0.6, 3.0, 12.3);
  // model grid
  const rows = [
    [TH(""), TH("Default"), TH("class_weight = \"balanced\"")],
    [{ text: "LogisticRegression(max_iter=5000)", options: { bold: true } }, "binary + multiclass", "binary + multiclass"],
    [{ text: "DecisionTreeClassifier(random_state=42)", options: { bold: true } }, "binary + multiclass", "binary + multiclass"],
  ];
  s.addTable(rows, { x: 0.6, y: 3.6, w: 7.6, colW: [3.6, 2.0, 2.0], fontSize: 14, color: C.text1, rowH: 0.6,
    border: { type: "solid", color: C.background2, pt: 1 }, valign: "middle", objectName: "model grid" });
  s.addText("2 algorithms × 2 weightings × 2 targets = 8 models, all converged", { x: 0.6, y: 5.6, w: 7.6, h: 0.4, fontSize: 14, italic: true, color: C.accent4, margin: 0, isTextBox: true });
  stat(s, 8.7, 3.6, 4.2, 1.45, "49,254", "held-out test flows");
  stat(s, 8.7, 5.25, 4.2, 1.45, "643", "attacks in the test split (6 SQL injection)", C.accent5);
  s.addNotes("Scaler and selector are fitted on the training split only. Inference time is the median of five timed predict calls, scaled to 1,000 flows.");
}

// 11. Binary results
{
  const s = content("Task 4: Classifiers", "Binary: The Decision Tree Misses No Attack");
  const hl = (t) => ({ text: t, options: { bold: true, fill: { color: C.background2 }, color: C.text2 } });
  const rows = [
    [TH("Model"), TH("Macro-F1"), TH("Prec."), TH("Recall"), TH("F1"), TH("FP"), TH("FN")],
    ["LR default", "0.8926", "0.7320", "0.8538", "0.7882", "201", "94"],
    ["LR balanced", "0.6789", "0.2349", "0.9907", "0.3797", { text: "2,075", options: { color: C.accent5, bold: true } }, "6"],
    [hl("DT default"), hl("0.9930"), hl("0.9728"), hl("1.0000"), hl("0.9862"), hl("18"), hl("0")],
    ["DT balanced", "0.9925", "0.9815", "0.9891", "0.9853", "12", "7"],
  ];
  s.addTable(rows, { x: 0.6, y: 1.5, w: 7.6, colW: [1.75, 1.15, 0.95, 0.95, 0.95, 0.95, 0.9], fontSize: 15, color: C.text1, rowH: 0.55,
    border: { type: "solid", color: C.background2, pt: 1 }, valign: "middle", objectName: "binary results" });
  caption(s, "Test split; precision, recall, F1 for the attack class", 0.6, 4.4, 7.6);
  bullets(s, [
    { b: "Best model: ", t: "the default Decision Tree finds all 643 attacks with 18 false alarms" },
    { b: "Class weighting ", t: "buys LR recall (0.85 → 0.99) at ten times the false alarms" },
  ], 0.6, 4.95, 7.6, 1.8, 15);
  const r1 = img(s, P("outputs/task4/figures/cm_binary_dt_default.png"), 1000, 920, 8.65, 1.4, 4.25, 2.6, "confusion matrix DT binary", false);
  const r2 = img(s, P("outputs/task4/figures/cm_binary_lr_balanced.png"), 1000, 920, 8.65, 4.2, 4.25, 2.6, "confusion matrix LR balanced binary", false);
  s.addNotes("The default Decision Tree is the best binary model and is the one used in the real-time part. Balanced LR detects 99 % of attacks but raises 2,075 false alarms.");
}

// 12. Multiclass results
{
  const s = content("Task 4: Classifiers", "Multiclass: Accuracy Hides a Blind Model");
  s.addChart(pres.charts.BAR, [
    { name: "LR default", labels: ["BENIGN", "Brute Force", "XSS", "SQLi"], values: [0.9926, 0, 0, 0] },
    { name: "LR balanced", labels: ["BENIGN", "Brute Force", "XSS", "SQLi"], values: [0.9689, 0.0781, 0.2233, 0.0061] },
    { name: "DT default", labels: ["BENIGN", "Brute Force", "XSS", "SQLi"], values: [0.9982, 0.6126, 0.3960, 0.9091] },
    { name: "DT balanced", labels: ["BENIGN", "Brute Force", "XSS", "SQLi"], values: [0.9977, 0.5827, 0.3762, 0.3000] },
  ], {
    x: 0.6, y: 1.35, w: 6.4, h: 4.3, barDir: "col", barGapWidthPct: 60,
    showTitle: true, title: "Per-class F1 on the test split", titleFontSize: 13, titleColor: H.dk2, titleFontFace: "+mn-lt",
    chartColors: ["B8C2CF", H.accent4, H.dk2, H.accent3], valAxisMaxVal: 1, valAxisMinVal: 0,
    catAxisLabelColor: H.dk1, valAxisLabelColor: H.accent4, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, valAxisLabelFormatCode: "0.0",
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: "E3E7ED", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: H.dk1, legendFontFace: "+mn-lt",
    objectName: "multiclass F1 chart", altText: "Per-class F1 of the four multiclass models",
  });
  s.addText([
    { text: "Macro-F1: ", options: { bold: true, color: C.text2 } },
    { text: "DT 0.729 · DT bal. 0.564 · LR bal. 0.319 · LR 0.248" },
  ], { x: 0.6, y: 5.8, w: 6.4, h: 0.4, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  s.addText("Brute Force and XSS are confused (103 and 97 flows): flow statistics cannot see the payload. SQLi F1 0.909 rests on 6 test flows.",
    { x: 0.6, y: 6.2, w: 6.4, h: 0.7, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  img(s, P("outputs/task4/figures/cm_multiclass_dt_default.png"), 1200, 1120, 7.3, 1.35, 2.75, 2.65, "confusion matrix DT multiclass", false);
  img(s, P("outputs/task4/figures/cm_multiclass_lr_default.png"), 1200, 1120, 10.15, 1.35, 2.75, 2.65, "confusion matrix LR multiclass", false);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.3, y: 4.3, w: 5.6, h: 2.55, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 }, objectName: "accuracy paradox" });
  s.addText([
    { text: "98.54 %", options: { bold: true, fontSize: 36, color: C.accent1, fontFace: THEME.headFontFace, breakLine: true } },
    { text: "accuracy of default LR, which detects not a single attack: it predicts almost everything as BENIGN.", options: { fontSize: 15, color: C.background1 } },
  ], { x: 7.6, y: 4.45, w: 5.0, h: 2.25, margin: 0, valign: "middle", isTextBox: true });
  s.addNotes("The accuracy paradox: 98.7 % of the data is benign, so a model that ignores attacks still looks excellent by accuracy. Class weighting does not fix this for LR and hurts the tree.");
}

// 13. Real-time
pres.addSection({ title: "Task 4: Real-Time" });
{
  const s = content("Task 4: Real-Time", "Real-Time Detection on Our Own Flows");
  const steps = ["Capture .pcapng", "CICFlowMeter (offline)", "Map V4 → training columns", "Drop protocol 0, inf/NaN → 0", "Pipeline: verdict per flow"];
  const w = 2.25, gap = 0.26, y = 1.45, h = 0.95;
  steps.forEach((t, i) => {
    const x = 0.6 + i * (w + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: i === 4 ? C.accent1 : C.text2 }, line: { color: i === 4 ? C.accent1 : C.text2 }, objectName: "rt step " + (i + 1) });
    s.addText(t, { x: x + 0.1, y, w: w - 0.2, h, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + w + 0.03, y: y + h / 2 - 0.1, w: 0.2, h: 0.2, fill: { color: C.accent4 }, line: { color: C.accent4 }, objectName: "rt arrow " + i });
  });
  const sw = 2.35, sg = 0.25;
  stat(s, 0.6, 2.75, sw, 1.3, "547", "flows classified, one by one");
  stat(s, 0.6 + sw + sg, 2.75, sw, 1.3, "3", "ATTACK alerts (0.55 %)", C.accent5);
  stat(s, 0.6, 4.25, sw, 1.3, "14.2 ms", "mean latency per flow");
  stat(s, 0.6 + sw + sg, 4.25, sw, 1.3, "0.67 ms", "per 1,000 flows when batched");
  s.addText([
    { text: "Parity test: ", options: { bold: true, color: C.text2 } },
    { text: "the 49,254 test flows streamed through the detector give the offline predictions row for row; 21 unit and 3 full-dataset tests pass." },
  ], { x: 0.6, y: 5.75, w: 4.95, h: 1.1, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  const r = img(s, P("SS/SS12.png"), 816, 791, 6.0, 2.7, 6.9, 3.9, "real-time detector output");
  caption(s, "Detector output: streamed verdicts, summary and the three alerts in red", 6.0, r.y + r.h + 0.08, 6.9);
  s.addNotes("The detector loads the saved binary Decision Tree pipeline unchanged. Real time here means streaming recorded flows one by one; we do not capture live. Detection delay is dominated by CICFlowMeter's flow timeouts.");
}

// 14. False positives
{
  const s = content("Task 4: Real-Time", "Three False Alarms, One Steam Burst");
  const r = img(s, P("SS/SS18.png"), 1495, 344, 0.6, 1.4, 12.3, 2.85, "Steam requests in Wireshark");
  caption(s, "Seven parallel Steam requests to the Steam CDN at 92.226.1.27, all answered 200 OK", r.x, r.y + r.h + 0.1, r.w);
  const cols = [
    ["What happened", "At 16:10:40 Steam sent 7 parallel GET /appinfo/… over plain HTTP to port 80: tiny gzip files, about 101 ms each, 2 PSH flags."],
    ["Why the tree fires", "Server window 507 lies in 235 < x ≤ 1,146 and port ≤ 85. In training, that region holds only attacks: the shortcut features."],
    ["Why only 3 of 7", "A depth-15 split on packet-length features lets 4 near-identical flows pass. The unpruned tree has overfitted."],
  ];
  const w = 3.95, gap = 0.225, y = 4.75, h = 2.05;
  cols.forEach(([head, body], i) => {
    const x = 0.6 + i * (w + gap);
    card(s, x, y, w, h, "fp card " + (i + 1));
    badge(s, x + 0.25, y + 0.25, 0.45, i + 1, i === 1 ? C.accent5 : C.text2);
    s.addText(head, { x: x + 0.85, y: y + 0.25, w: w - 1.0, h: 0.45, fontSize: 17, bold: true, color: C.text2, margin: 0, valign: "middle", isTextBox: true });
    s.addText(body, { x: x + 0.25, y: y + 0.85, w: w - 0.5, h: h - 1.0, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  });
  s.addNotes("All three alerts are false positives, since our traffic is benign by construction. Automated plain-HTTP bursts to port 80 from a small-window server resemble the Selenium-driven attacks of 2017.");
}

// 15. Conclusion
pres.addSection({ title: "Conclusion" });
{
  const s = pres.addSlide({ masterName: "CLOSING", sectionTitle: "Conclusion" });
  s.addText("The benchmark score does not carry over", { placeholder: "title" });
  s.addText([
    { text: "0.037 %", options: { bold: true, fontSize: 40, color: C.background1, fontFace: THEME.headFontFace, breakLine: true } },
    { text: "false-positive rate on the CIC-IDS2017 test split", options: { fontSize: 15, color: C.background2, breakLine: true } },
    { text: " ", options: { fontSize: 12, breakLine: true } },
    { text: "0.55 %", options: { bold: true, fontSize: 40, color: C.accent1, fontFace: THEME.headFontFace, breakLine: true } },
    { text: "on our own benign traffic, about 15 times higher", options: { fontSize: 15, color: C.background2 } },
  ], { x: 0.6, y: 2.3, w: 4.6, h: 4.2, margin: 0, valign: "top", isTextBox: true });

  const x = 6.1, w = 6.8;
  s.addText("Takeaways", { x, y: 1.15, w, h: 0.45, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  bullets(s, [
    { b: "Decision Tree beats LR: ", t: "attack F1 0.986 vs. 0.788, macro-F1 0.729 vs. 0.319" },
    { b: "Never trust accuracy alone: ", t: "98.5 % accuracy with zero attacks detected" },
    { b: "Shortcuts and domain shift: ", t: "port 80 and initial TCP windows, plus a newer CICFlowMeter, QUIC and Steam" },
  ], x, 1.7, w, 2.2, 15);
  s.addText("Limitations and next steps", { x, y: 4.1, w, h: 0.45, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  bullets(s, [
    { b: "Limits: ", t: "single split without cross-validation, only 6 SQLi test flows, replay instead of live capture" },
    { b: "Prune the tree: ", t: "max_depth, min_samples_leaf" },
    { b: "Remove shortcuts: ", t: "drop Destination Port and Init_Win_bytes_*, add benign traffic from the deployment network" },
  ], x, 4.65, w, 2.2, 15);
  s.addNotes("Conclusion: near-perfect benchmark scores, but the model partly learned 'automated HTTP to port 80 from a small-window server' rather than the attack. Thank you; questions welcome.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
