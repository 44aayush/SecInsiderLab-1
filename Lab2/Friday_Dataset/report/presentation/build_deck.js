// Builds the Lab 2 presentation (G8, Friday DDoS) from the numbers and figures of the Friday G8.Report2.pdf.
// Run: cd report/presentation && node build_deck.js
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/home/aayush/.claude/skills/synced/e4cc6236-64d8-44be-b91e-bba57ace04f8_ba5af316-0eaf-43fa-8a67-209d84f411bf/pptx/scripts/apply_theme.js");

const FDS = path.resolve(__dirname, "../..");
const P = (...p) => path.join(FDS, ...p);
const OUT = path.join(__dirname, "G8.Lab2.Presentation.pptx");

const THEME = {
  name: "G8 Lab2 Passau Friday",
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
const LOGO = { path: P("report/images/uni-logo.png"), x: SW - 0.45 - 2.1, y: 0.3, w: 2.1, h: 2.1 * 133 / 500 };
const FOOT = "Group 8 · Security Insider Lab I · Lab 2";

// ---------- layouts ----------
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: C.background1 },
  objects: [
    { rect: { x: 0, y: 0, w: 8.2, h: SH, fill: { color: C.text2 } } },
    { image: LOGO },
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.3, w: 7.0, h: 2.7,
        fontSize: 38, bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "" } },
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
        fontSize: 28, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 }, text: "" } },
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
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.5, w: 4.6, h: 1.6,
        fontSize: 30, bold: true, color: C.background1, align: "left", valign: "top", margin: 0 }, text: "" } },
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
  s.addText(label, { x: x + 0.2, y: y + 0.12 + h * 0.52, w: w - 0.4, h: h * 0.40 - 0.12, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
}

// numbered circle
function badge(s, x, y, d, n, color = C.accent1) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color }, objectName: "badge " + n });
  s.addText(String(n), { x, y, w: d, h: d, fontSize: d > 0.5 ? 18 : 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
}

function bullets(s, items, x, y, w, h, fontSize = 15) {
  const runs = items.map((it, i) => {
    const last = i === items.length - 1;
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

// common native-chart styling
const chartBase = (title, extra = {}) => Object.assign({
  showTitle: true, title, titleFontSize: 14, titleColor: H.dk2, titleFontFace: "+mn-lt",
  catAxisLabelColor: H.dk1, valAxisLabelColor: H.accent4, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  valGridLine: { color: "E3E7ED", size: 0.5 }, catGridLine: { style: "none" },
  showValue: true, dataLabelFontSize: 12, dataLabelColor: H.dk1, dataLabelFontFace: "+mn-lt",
}, extra);

// ====================================================================
// 1. Title
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Introduction" });
  s.addText("Lab 2: Machine Learning for Network Attack Detection", { placeholder: "title" });
  s.addText([
    { text: "CIC-IDS2017 Friday DDoS dataset", options: { bold: true, color: C.accent1, breakLine: true } },
    { text: "Security Insider Lab I · Group 8", options: { breakLine: true } },
    { text: "Justlyn Kaniyanthara Johnson (121024)", options: { breakLine: true } },
    { text: "Aayush Kapoor (120957)", options: { breakLine: true } },
    { text: "9 November 2026", options: { fontSize: 14 } },
  ], { placeholder: "body", paraSpaceAfter: 4 });
  const x = 8.75, w = 4.1;
  stat(s, x, 1.55, w, 1.5, "223,082", "clean CIC-IDS2017 flows, 59 features");
  stat(s, x, 3.3, w, 1.5, "0.9996", "DDoS F1 of the Decision Tree (test split)");
  stat(s, x, 5.05, w, 1.5, "0 alerts", "on our own benign traffic (547 flows)", C.accent6);
  s.addNotes("Lab 2 of the Security Insider Lab: detecting network attacks from flow features with Logistic Regression and Decision Trees. We use the Friday DDoS file of CIC-IDS2017. The three numbers on the right are our main results: a clean set of 223,082 flows with 59 features, a DDoS F1 of 0.9996 for the Decision Tree, and no alert on our own benign capture.");
}

// 2. Overview
{
  const s = content("Introduction", "Four tasks lead from our capture to a detector");
  const tasks = [
    ["Task 1", "Flows", "Capture our own traffic and convert it into flows with CICFlowMeter"],
    ["Task 2", "Dataset", "Analyze CIC-IDS2017: the Friday-afternoon DDoS file"],
    ["Task 3", "Pre-processing", "Clean inf/NaN and duplicates, min-max scale, select 20 features with χ²"],
    ["Task 4", "Classifiers", "Train LR and Decision Tree, then classify our own flows one by one"],
  ];
  const w = 2.85, gap = 0.3, x0 = 0.6, y = 1.7, h = 2.2;
  tasks.forEach(([t, head, body], i) => {
    const x = x0 + i * (w + gap);
    card(s, x, y, w, h, "task card " + (i + 1));
    badge(s, x + 0.3, y + 0.3, 0.6, i + 1);
    s.addText(t, { x: x + 1.05, y: y + 0.3, w: w - 1.2, h: 0.3, fontSize: 12, color: C.accent4, margin: 0, isTextBox: true });
    s.addText(head, { x: x + 1.05, y: y + 0.58, w: w - 1.2, h: 0.35, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
    s.addText(body, { x: x + 0.3, y: y + 1.15, w: w - 0.6, h: h - 1.35, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  });
  s.addText([
    { text: "Our dataset", options: { bold: true, color: C.accent1, fontSize: 18, breakLine: true } },
    { text: "We use Friday-WorkingHours-Afternoon-DDos.csv, the file named in the lab slides. It has two labels, BENIGN and DDoS, so every model is a binary classifier and the real-time detector flags DDoS.", options: { fontSize: 16, color: C.background1 } },
  ], { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 }, x: 0.6, y: 4.4, w: 12.3, h: 1.9, margin: [8, 22, 8, 22], valign: "middle", paraSpaceAfter: 4, objectName: "dataset choice" });
  s.addNotes("Overview of the four lab tasks. For the dataset we follow the lab slides and use the Friday-afternoon DDoS file of CIC-IDS2017. It contains benign flows and DDoS flows, so the problem is binary.");
}

// 3. Task 1: Flows
pres.addSection({ title: "Task 1: Flows" });
{
  const s = content("Task 1: Flows", "A flow summarizes one bidirectional exchange");
  bullets(s, [
    { b: "A flow ", t: "is keyed by source and destination IP, ports and protocol" },
    { b: "84 columns: ", t: "metadata, 77 numeric features (packet lengths, inter-arrival times, TCP flags, window sizes, idle/active times) and a label" },
    { b: "A flow ends ", t: "on FIN/RST, after 5 s of inactivity or after 120 s in total" },
    { b: "Only flows with ≥ 2 packets ", t: "are written, so a lone DNS query or traceroute probe never appears" },
    { b: "Our capture: ", t: "81,110 frames over 347.4 s of browsing, DNS and the Steam client (4 Nov 2026), benign by construction" },
  ], 0.6, 1.5, 6.2, 5.2, 16);
  const r = img(s, P("SS/SS25.png"), 900, 741, 7.2, 1.45, 5.7, 5.1, "CICFlowMeter offline conversion");
  caption(s, "CICFlowMeter offline mode: 81,110 packets → 569 flows (570 lines incl. header)", r.x, r.y + r.h + 0.1, r.w);
  s.addNotes("Explain what a flow is and how CICFlowMeter terminates flows: FIN or RST, 5 s without activity, or 120 s in total. Only flows with at least two packets are written. The screenshot shows the offline conversion of our final capture with the default timeouts; the reported 570 flows count the header line, so there are 569 flows.");
}

// 4. IPv6 problem
{
  const s = content("Task 1: Flows", "Disabling IPv6 lifted valid flows from 5 % to 96 %");
  s.addChart(pres.charts.BAR, [{ name: "Valid TCP/UDP flows", labels: ["1st capture (98 % IPv6)", "2nd capture (89.5 % IPv6)", "3rd capture (IPv6 off)"], values: [14.7, 5.0, 96.1] }], Object.assign(chartBase("Share of valid TCP/UDP flows (%)"), {
    x: 0.6, y: 1.45, w: 6.0, h: 4.6, barDir: "col",
    chartColors: [H.accent4, H.accent4, H.accent6], valAxisMaxVal: 100, valAxisMinVal: 0,
    dataLabelPosition: "outEnd", dataLabelFontSize: 13, dataLabelFormatCode: "0.0\"%\"", showLegend: false,
    objectName: "valid flow share chart", altText: "Valid TCP/UDP flows: 78 of 532, 67 of 1,327, 547 of 569",
  }));
  caption(s, "Valid flows: 78/532, 67/1,327, 547/569", 0.6, 6.15, 6.0);
  bullets(s, [
    { b: "Symptom: ", t: "protocol 0, port 0 and impossible IPs in most flows of the first two captures" },
    { b: "Root cause: ", t: "readIP6 = false is hard-coded in CICFlowMeter (Cmd.java:126); every non-IPv4 frame is force-parsed as an IPv4 header from byte 0" },
    { b: "Fake IPs: ", t: "134.221.96.0 = 86 DD 60 00, i.e. the IPv6 EtherType; 136.225.x = HomePlug, 8.6.x = ARP" },
    { b: "Fix: ", t: "disable IPv6 on the capturing laptop, which keeps flows IPv4-only like the training data" },
  ], 7.0, 1.5, 5.9, 3.9, 15);
  img(s, P("SS/SS24.png"), 559, 148, 7.0, 5.55, 5.9, 1.05, "sysctl disable IPv6");
  s.addNotes("Our first two captures were mostly IPv6, with 98 and 89.5 percent IPv6 frames. We traced the bogus flows to CICFlowMeter's hard-coded IPv4-only parsing. We did not enable its IPv6 path because its UDP branch reads the header length from the TCP header. After sysctl disabled IPv6, the share of valid flows rose from 15 and 5 percent to 96 percent.");
}

// 5. Final capture
{
  const s = content("Task 1: Flows", "The final capture yields 547 usable flows");
  const w = 2.85, gap = 0.3;
  [["569", "flows written by CICFlowMeter"], ["547", "TCP/UDP flows classified"], ["22", "protocol-0 flows dropped (ICMP, ARP, IPv6)"], ["99.94 %", "of frames are IPv4"]]
    .forEach(([v, l], i) => stat(s, 0.6 + i * (w + gap), 1.45, w, 1.35, v, l, i === 2 ? C.accent4 : C.text2));
  const r = img(s, P("SS/SS15.png"), 1483, 625, 0.6, 3.1, 6.2, 2.7, "Wireshark protocol hierarchy");
  caption(s, "Wireshark protocol hierarchy of task1_lab2.pcapng", r.x, r.y + r.h + 0.1, r.w);
  const r2 = img(s, P("SS/SS17.png"), 1689, 371, 7.1, 3.1, 5.8, 1.4, "flow CSV in LibreOffice");
  caption(s, "First rows of task2_lab2.pcap_Flow.csv", r2.x, r2.y + r2.h + 0.1, r2.w);
  bullets(s, [
    { b: "289 ", t: "flows are DNS queries (port 53)" },
    { b: "213 ", t: "flows go to port 443, 15 to port 80" },
    { b: "≈ 70 % ", t: "of valid flows are UDP: DNS, QUIC, Steam" },
  ], 7.1, 5.05, 5.8, 1.9, 15);
  s.addNotes("With IPv6 off, 547 of 569 flows are valid. The 22 protocol-0 flows are 15 real ICMP flows, 4 left-over IPv6 flows and 3 ARP flows. The classified flows contain 99.8 percent of all IPv4 TCP/UDP frames; the rest are single-packet exchanges. The application mix, QUIC and Steam, differs from the 2017 testbed, so we expect domain shift.");
}

// 6. Task 2: Dataset
pres.addSection({ title: "Task 2: Dataset" });
{
  const s = content("Task 2: Dataset", "The Friday file has 57 % attack flows");
  s.addChart(pres.charts.BAR, [
    { name: "Raw", labels: ["BENIGN", "DDoS"], values: [97718, 128027] },
    { name: "Cleaned", labels: ["BENIGN", "DDoS"], values: [95068, 128014] },
  ], Object.assign(chartBase("Flows per label, raw and after cleaning"), {
    x: 0.6, y: 1.4, w: 6.8, h: 4.7, barDir: "col", barGapWidthPct: 60,
    chartColors: [H.accent4, H.dk2], valAxisMinVal: 0, valAxisMaxVal: 150000,
    dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", valAxisLabelFormatCode: "#,##0",
    showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: H.dk1, legendFontFace: "+mn-lt",
    objectName: "label distribution chart", altText: "BENIGN 97,718 raw and 95,068 cleaned; DDoS 128,027 raw and 128,014 cleaned",
  }));
  caption(s, "Shares: BENIGN 43.29 %, DDoS 56.71 % raw; 42.62 % / 57.38 % cleaned", 0.6, 6.25, 6.8);
  stat(s, 7.9, 1.45, 5.0, 1.45, "225,745 × 79", "flows × columns: 78 features and the Label");
  stat(s, 7.9, 3.1, 5.0, 1.45, "Port 80", "is the destination of virtually all DDoS flows", C.accent1);
  stat(s, 7.9, 4.75, 5.0, 1.45, "56.71 %", "DDoS is the majority class, yet we still report per-class P/R/F1 and macro-F1", C.text2);
  s.addNotes("The file has 225,745 flows and 79 columns, with the labels BENIGN, 97,718 flows, and DDoS, 128,027 flows. The attack is the majority class, so accuracy is less misleading than on a dataset with a rare attack, but we still report per-class precision, recall and F1, macro-F1 and confusion matrices. Virtually all DDoS flows target destination port 80.");
}

// 7. Task 3: pipeline steps
pres.addSection({ title: "Task 3: Pre-processing" });
{
  const s = content("Task 3: Pre-processing", "Nine steps turn raw flows into model input");
  const steps = [
    ["Load & strip names", "65 of 79 column names carry stray spaces; labels already clean"],
    ["Drop duplicate column", "Fwd Header Length appears twice"],
    ["±∞ → NaN, drop rows", "34 rows: 32 BENIGN, 2 DDoS"],
    ["Drop duplicate rows", "2,629 rows, before the split so none lands in train and test"],
    ["Drop constant columns", "10 columns that never change"],
    ["Drop identical columns", "8 columns (tolerance 1e-6), so the 20 features are distinct"],
    ["Stratified 70/30 split", "On the label, random_state = 42"],
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
  s.addNotes("Steps 1 to 6 clean the data and use no labels. Steps 7 to 9, in navy, are fitted on the training split only, so no test statistics leak into training. The infinite and NaN values occur only in Flow Bytes/s and Flow Packets/s, because CICFlowMeter divides by a flow duration that is 0 for some flows.");
}

// 8. Cleaning results
{
  const s = content("Task 3: Pre-processing", "Cleaning leaves 223,082 flows with 59 features");
  const r = img(s, P("SS/SS28.png"), 1854, 433, 0.6, 1.35, 12.3, 3.35, "cleaning log");
  caption(s, "Cleaning steps as logged by the pre-processing script", r.x, r.y + r.h + 0.1, r.w);
  const w = 2.85, gap = 0.3, y = 5.0;
  [["−34", "rows with ±∞/NaN (32 BENIGN, 2 DDoS)"], ["−2,629", "duplicate rows (2,618 BENIGN, 11 DDoS)"], ["−18", "columns: 10 constant, 8 identical"], ["59", "features remain, 128,014 DDoS flows"]]
    .forEach(([v, l], i) => stat(s, 0.6 + i * (w + gap), y, w, 1.35, v, l, i === 3 ? C.accent1 : C.text2));
  s.addText([
    { text: "Data quality: ", options: { bold: true, color: C.text2 } },
    { text: "Fwd PSH Flags is identical to SYN Flag Count although PSH and SYN are different TCP flags, and six bulk-transfer features are always 0." },
  ], { x: 0.6, y: 6.5, w: 12.3, h: 0.45, fontSize: 14, color: C.text1, margin: 0, valign: "middle", isTextBox: true });
  s.addNotes("The raw file has 2,633 duplicate rows, but 4 of them contain infinite or NaN values and are already gone after step 3, so the duplicate step drops 2,629. Fwd PSH Flags equal to SYN Flag Count points to a feature-extraction problem in the CICFlowMeter version used for CIC-IDS2017, in line with the literature (Engelen et al. 2021). After cleaning there are 95,068 BENIGN and 128,014 DDoS flows.");
}

// 9. Feature selection
{
  const s = content("Task 3: Pre-processing", "Packet sizes dominate the top 20 features");
  const feats = [
    ["URG Flag Count", 30058.11], ["Destination Port", 28476.04], ["Bwd Packet Length Max", 22196.57], ["Bwd Packet Length Std", 15201.54],
    ["Bwd Packet Length Mean", 13631.13], ["Bwd IAT Total", 10104.71], ["Max Packet Length", 9940.91], ["Packet Length Mean", 9735.77],
    ["Fwd Packet Length Max", 9338.26], ["Packet Length Std", 9282.63], ["Average Packet Size", 8361.12], ["Fwd Packet Length Mean", 8326.59],
    ["Fwd PSH Flags", 7104.49], ["Packet Length Variance", 6816.96], ["Bwd IAT Max", 6626.18], ["Fwd Packet Length Std", 6519.34],
    ["PSH Flag Count", 5771.95], ["Down/Up Ratio", 4499.68], ["Fwd Packet Length Min", 3409.00], ["Bwd IAT Std", 3351.57],
  ].reverse();
  s.addChart(pres.charts.BAR, [{ name: "χ² score", labels: feats.map(f => f[0]), values: feats.map(f => f[1]) }], Object.assign(chartBase("χ² score, binary target (min-max-scaled train set)", { titleFontSize: 13 }), {
    x: 0.6, y: 1.35, w: 7.3, h: 5.55, barDir: "bar", barGapWidthPct: 40,
    chartColors: [H.dk2], dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelFormatCode: "#,##0",
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, valAxisMaxVal: 35000, valAxisLabelFormatCode: "#,##0", catAxisLabelFrequency: 1, showLegend: false,
    objectName: "chi2 feature chart", altText: "Top-20 features by chi2 score for the binary target",
  }));
  const x = 8.3, w = 4.6;
  card(s, x, 1.45, w, 1.7, "insight packet sizes");
  s.addText([
    { text: "Packet sizes", options: { bold: true, color: C.text2, fontSize: 17, breakLine: true } },
    { text: "12 of the 20 features describe packet lengths: forward and backward statistics, maximum, mean, standard deviation, variance.", options: { fontSize: 14 } },
  ], { x: x + 0.25, y: 1.55, w: w - 0.5, h: 1.5, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  card(s, x, 3.35, w, 1.7, "insight port");
  s.addText([
    { text: "Destination Port ranks 2nd", options: { bold: true, color: C.accent5, fontSize: 17, breakLine: true } },
    { text: "Score 28,476. Virtually all DDoS flows target port 80, so a model can learn the port instead of the attack.", options: { fontSize: 14 } },
  ], { x: x + 0.25, y: 3.45, w: w - 0.5, h: 1.5, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  card(s, x, 5.25, w, 1.65, "insight flags timing");
  s.addText([
    { text: "Flags and timing", options: { bold: true, color: C.accent6, fontSize: 17, breakLine: true } },
    { text: "3 TCP flag counts (URG, Fwd PSH, PSH), 3 backward inter-arrival times, and Down/Up Ratio.", options: { fontSize: 14 } },
  ], { x: x + 0.25, y: 5.35, w: w - 0.5, h: 1.45, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("URG Flag Count leads with a score of 30,058, followed by Destination Port at 28,476 and Bwd Packet Length Max at 22,197. The scores fall steadily down the ranking. The χ² test on min-max-scaled continuous data is only a heuristic: heavy-tailed features are squeezed towards 0, which lowers their scores. We expect testbed-specific features such as the destination port to generalize poorly to other networks.");
}

// 10. Task 4 setup
pres.addSection({ title: "Task 4: Classifiers" });
{
  const s = content("Task 4: Classifiers", "Four binary models share one pipeline");
  const boxes = [["MinMaxScaler", "clip = True"], ["SelectKBest", "χ², k = 20"], ["Classifier", "LR or Decision Tree"]];
  const bw = 3.4, bh = 1.25, y = 1.5, gap = 1.05;
  boxes.forEach(([h1, h2], i) => {
    const x = 0.6 + i * (bw + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: bh, rectRadius: 0.1, fill: { color: i === 2 ? C.accent1 : C.text2 }, line: { color: i === 2 ? C.accent1 : C.text2 }, shadow: shadow(), objectName: "pipeline " + h1 });
    s.addText([{ text: h1, options: { bold: true, fontSize: 20, breakLine: true } }, { text: h2, options: { fontSize: 15 } }],
      { x, y, w: bw, h: bh, align: "center", valign: "middle", color: C.background1, margin: 0, isTextBox: true });
    if (i < 2) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.2, y: y + bh / 2 - 0.25, w: gap - 0.4, h: 0.5, fill: { color: C.accent4 }, line: { color: C.accent4 }, objectName: "arrow " + i });
  });
  caption(s, "One scikit-learn Pipeline per model, fitted on the 156,157 training flows and saved with joblib", 0.6, 2.9, 12.3);
  const rows = [
    [TH(""), TH("Default"), TH("class_weight = \"balanced\"")],
    [{ text: "LogisticRegression(max_iter=5000)", options: { bold: true } }, "binary: BENIGN vs. DDoS", "binary: BENIGN vs. DDoS"],
    [{ text: "DecisionTreeClassifier(random_state=42)", options: { bold: true } }, "binary: BENIGN vs. DDoS", "binary: BENIGN vs. DDoS"],
  ];
  s.addTable(rows, { x: 0.6, y: 3.4, w: 12.3, colW: [5.3, 3.5, 3.5], fontSize: 14, color: C.text1, rowH: 0.5,
    border: { type: "solid", color: C.background2, pt: 1 }, valign: "middle", objectName: "model grid" });
  s.addText("The file has one attack class: 2 algorithms × 2 weightings = 4 binary models.", { x: 0.6, y: 5.0, w: 12.3, h: 0.35, fontSize: 14, italic: true, color: C.accent4, margin: 0, isTextBox: true });
  const sw = 3.9, sg = 0.3;
  stat(s, 0.6, 5.5, sw, 1.4, "156,157 / 66,925", "training / test flows");
  stat(s, 0.6 + sw + sg, 5.5, sw, 1.4, "38,404", "DDoS flows in the test split", C.accent5);
  stat(s, 0.6 + 2 * (sw + sg), 5.5, sw, 1.4, "48", "iterations until both LR models converged (limit 5,000)");
  s.addNotes("Scaler and selector are fitted on the training split only. All models are evaluated on the held-out test split of 66,925 flows, 38,404 of them DDoS. Inference time is the median of five timed predict calls on the whole test split after one warm-up call, scaled to 1,000 flows.");
}

// 11. Binary results
{
  const s = content("Task 4: Classifiers", "The Decision Tree makes 32 errors on 66,925 flows");
  const hl = (t) => ({ text: t, options: { bold: true, fill: { color: C.background2 }, color: C.text2 } });
  const rows = [
    [TH("Model"), TH("Macro-F1"), TH("Prec."), TH("Recall"), TH("F1"), TH("FP"), TH("FN")],
    ["LR default", "0.9683", "0.9503", "0.9988", "0.9739", { text: "2,008", options: { color: C.accent5, bold: true } }, "45"],
    ["LR balanced", "0.9689", "0.9511", "0.9988", "0.9744", { text: "1,974", options: { color: C.accent5, bold: true } }, "45"],
    [hl("DT default"), hl("0.9995"), hl("0.9998"), hl("0.9993"), hl("0.9996"), hl("7"), hl("25")],
    ["DT balanced", "0.9995", "0.9998", "0.9993", "0.9996", "7", "25"],
  ];
  s.addTable(rows, { x: 0.6, y: 1.5, w: 7.6, colW: [1.75, 1.15, 0.95, 0.95, 0.95, 0.9, 0.95], fontSize: 15, color: C.text1, rowH: 0.55,
    border: { type: "solid", color: C.background2, pt: 1 }, valign: "middle", objectName: "binary results" });
  caption(s, "Test split; precision, recall, F1 for the DDoS class; FP/FN = false positives/negatives", 0.6, 4.4, 7.6);
  bullets(s, [
    { b: "Decision Tree: ", t: "7 false positives and 25 false negatives, DDoS F1 0.9996" },
    { b: "Logistic Regression: ", t: "finds almost as many attacks (recall 0.9988) but raises about 2,000 false alarms, so precision is about 0.95" },
  ], 0.6, 4.95, 7.6, 1.9, 15);
  img(s, P("outputs/task4/figures/cm_binary_dt_default.png"), 1000, 920, 8.65, 1.4, 4.25, 2.6, "confusion matrix DT default binary", false);
  img(s, P("outputs/task4/figures/cm_binary_lr_balanced.png"), 1000, 920, 8.65, 4.2, 4.25, 2.6, "confusion matrix LR balanced binary", false);
  s.addNotes("The default Decision Tree makes 7 false positives and 25 false negatives, which gives a DDoS precision of 0.9998, a recall of 0.9993 and an F1 of 0.9996. Logistic Regression detects 38,359 of 38,404 DDoS flows but raises 2,008 false alarms for the default and 1,974 for the balanced variant. Right: confusion matrices of the default tree and the balanced Logistic Regression.");
}

// 12. Callouts: class weighting, model choice
{
  const s = content("Task 4: Classifiers", "Class weighting changes almost nothing here");
  s.addChart(pres.charts.BAR, [
    { name: "False positives", labels: ["LR default", "LR balanced", "DT default", "DT balanced"], values: [2008, 1974, 7, 7] },
    { name: "False negatives", labels: ["LR default", "LR balanced", "DT default", "DT balanced"], values: [45, 45, 25, 25] },
  ], Object.assign(chartBase("Errors on the 66,925 test flows"), {
    x: 0.6, y: 1.35, w: 6.6, h: 5.0, barDir: "col", barGapWidthPct: 60,
    chartColors: [H.accent5, H.dk2], valAxisMinVal: 0, valAxisMaxVal: 2400, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", valAxisLabelFormatCode: "#,##0",
    showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: H.dk1, legendFontFace: "+mn-lt",
    objectName: "error chart", altText: "False positives 2008, 1974, 7, 7 and false negatives 45, 45, 25, 25 for the four models",
  }));
  caption(s, "Balanced and default Decision Tree have identical confusion matrices", 0.6, 6.5, 6.6);
  stat(s, 7.6, 1.45, 5.3, 1.35, "57 % : 43 %", "DDoS to BENIGN after cleaning, so balanced weights are close to one", C.text2);
  stat(s, 7.6, 3.0, 5.3, 1.35, "2,008 → 1,974", "false positives of LR: balancing removes only 34", C.accent5);
  s.addText([
    { text: "Why binary_dt_default", options: { bold: true, color: C.accent1, fontSize: 17, breakLine: true } },
    { text: "Identical to the balanced tree on the test split, so we take the simpler model.", options: { fontSize: 16, color: C.background1, breakLine: true } },
    { text: "Fewest errors of all four: 7 FP and 25 FN.", options: { fontSize: 16, color: C.background1 } },
  ], { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 }, x: 7.6, y: 4.55, w: 5.3, h: 1.9, margin: [8, 18, 8, 18], valign: "middle", paraSpaceAfter: 6, objectName: "why dt default" });
  s.addNotes("Because the classes are close to balanced, class_weight balanced gives both classes weights close to one. For the tree, the balanced variant has exactly the same confusion matrix and metrics as the default one; for Logistic Regression the false positives drop only from 2,008 to 1,974. We use binary_dt_default in the real-time part.");
}

// 13. Real-time architecture + parity
pres.addSection({ title: "Task 4: Real-Time" });
{
  const s = content("Task 4: Real-Time", "Streaming reproduces the offline predictions exactly");
  const steps = ["Capture .pcapng", "CICFlowMeter (offline)", "Map V4 → training columns", "Drop protocol 0, inf/NaN → 0", "Pipeline: verdict per flow"];
  const w = 2.25, gap = 0.26, y = 1.45, h = 0.95;
  steps.forEach((t, i) => {
    const x = 0.6 + i * (w + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: i === 4 ? C.accent1 : C.text2 }, line: { color: i === 4 ? C.accent1 : C.text2 }, objectName: "rt step " + (i + 1) });
    s.addText(t, { x: x + 0.1, y, w: w - 0.2, h, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + w + 0.03, y: y + h / 2 - 0.1, w: 0.2, h: 0.2, fill: { color: C.accent4 }, line: { color: C.accent4 }, objectName: "rt arrow " + i });
  });
  stat(s, 0.6, 2.8, 5.9, 1.4, "66,925", "test flows streamed through the detector: identical to the offline predictions, row for row");
  stat(s, 0.6, 4.4, 5.9, 1.4, "24 + 3", "fast and end-to-end tests pass", C.accent6);
  s.addText([
    { text: "Same model: ", options: { bold: true, color: C.text2 } },
    { text: "the detector loads the saved binary_dt_default pipeline unchanged." },
  ], { x: 0.6, y: 6.0, w: 5.9, h: 0.9, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  const r1 = img(s, P("SS/SS36.png"), 314, 65, 7.0, 2.8, 5.9, 1.3, "fast tests passed");
  caption(s, "Fast tests: 24 passed, 3 deselected", r1.x, r1.y + r1.h + 0.1, r1.w);
  const r2 = img(s, P("SS/SS37.png"), 314, 65, 7.0, 4.65, 5.9, 1.3, "end-to-end tests passed");
  caption(s, "End-to-end tests: 3 passed, 24 deselected (includes the parity test)", r2.x, r2.y + r2.h + 0.1, r2.w);
  s.addNotes("The detector streams flows one by one in timestamp order, maps the V4 column names to the training names (all 77 features map), drops Protocol 0 rows, replaces infinite and NaN values by 0 and classifies each flow. The parity test converts the 66,925-flow test split to the V4 column names and streams it through the detector; the predictions equal those of the offline pipeline, both for batches of 1,000 flows and, on the first 500 flows, for batches of one flow. Real time here means replaying a recorded capture; we do not capture live.");
}

// 14. Real-time results
{
  const s = content("Task 4: Real-Time", "547 of our flows classified, 0 DDoS alerts");
  const w = 2.85, gap = 0.3;
  [["569", "flows read"], ["22", "protocol-0 flows dropped"], ["547", "flows classified, all BENIGN"], ["0", "DDoS alerts (0.00 %)"]]
    .forEach(([v, l], i) => stat(s, 0.6 + i * (w + gap), 1.4, w, 1.3, v, l, i === 3 ? C.accent6 : (i === 1 ? C.accent4 : C.text2)));
  const r = img(s, P("SS/SS38.png"), 507, 248, 0.6, 2.95, 5.0, 2.5, "real-time detector summary");
  caption(s, "Summary printed by the real-time detector", r.x, r.y + r.h + 0.1, r.w);
  s.addText([
    { text: "Latency: ", options: { bold: true, color: C.text2 } },
    { text: "13.537 ms mean (12.840 ms median) per flow, one flow at a time. Batched, the model needs 0.695 ms per 1,000 flows." },
  ], { x: 0.6, y: 5.95, w: 5.0, h: 0.95, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  card(s, 6.0, 2.95, 6.9, 1.3, "limit benign only");
  s.addText([
    { text: "Benign-only capture", options: { bold: true, color: C.accent5, fontSize: 17, breakLine: true } },
    { text: "We measure false alarms on our network, but not the detection rate: whether the model would flag a real DDoS in our flows is untested.", options: { fontSize: 16 } },
  ], { x: 6.25, y: 3.05, w: 6.4, h: 1.1, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  card(s, 6.0, 4.45, 6.9, 1.5, "limit domain shift");
  s.addText([
    { text: "Domain shift", options: { bold: true, color: C.text2, fontSize: 17, breakLine: true } },
    { text: "Training flows come from an older CICFlowMeter version on the 2017 testbed; ours come from V4 on a different network with QUIC and Steam traffic.", options: { fontSize: 16 } },
  ], { x: 6.25, y: 4.55, w: 6.4, h: 1.3, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("Of 569 flows, 22 were dropped (protocol 0) and 547 were classified, all as BENIGN. No infinite or NaN cells had to be replaced. Our traffic is benign by construction, so every flow is correctly classified. The per-flow latency is per-call pandas and scikit-learn overhead; in practice the detection delay is dominated by CICFlowMeter, which emits a flow only when it ends or times out after 5 s of inactivity or 120 s in total.");
}

// 15. Conclusion
pres.addSection({ title: "Conclusion" });
{
  const s = pres.addSlide({ masterName: "CLOSING", sectionTitle: "Conclusion" });
  s.addText("Near-perfect on the test split, detection untested outside the testbed", { placeholder: "title" });
  s.addText([
    { text: "0.9996", options: { bold: true, fontSize: 40, color: C.background1, fontFace: THEME.headFontFace, breakLine: true } },
    { text: "DDoS F1 of the Decision Tree on the CIC-IDS2017 test split", options: { fontSize: 15, color: C.background2, breakLine: true } },
    { text: " ", options: { fontSize: 12, breakLine: true } },
    { text: "0 alerts", options: { bold: true, fontSize: 40, color: C.accent1, fontFace: THEME.headFontFace, breakLine: true } },
    { text: "on 547 benign flows of our own capture, which contains no attack", options: { fontSize: 15, color: C.background2 } },
  ], { x: 0.6, y: 2.5, w: 4.6, h: 4.0, margin: 0, valign: "top", isTextBox: true });

  const x = 6.1, w = 6.8;
  s.addText("Takeaways", { x, y: 1.15, w, h: 0.45, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  bullets(s, [
    { b: "Decision Tree beats LR: ", t: "F1 0.9996 vs. 0.9744 at best, 7 vs. about 2,000 false alarms" },
    { b: "Port-80 shortcut: ", t: "Destination Port ranks 2nd, and virtually all DDoS flows use port 80" },
    { b: "No false alarms on our traffic, ", t: "but our capture has no attack, so the detection rate is untested" },
  ], x, 1.7, w, 2.3, 15);
  s.addText("Possible improvements", { x, y: 4.2, w, h: 0.45, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  bullets(s, [
    { b: "Prune the tree: ", t: "max_depth, min_samples_leaf; we use a single split without cross-validation" },
    { b: "Remove shortcuts: ", t: "drop testbed-specific features such as Destination Port" },
    { b: "Test further: ", t: "evaluate on a second attack capture from another network, and add benign traffic from the deployment network to training" },
  ], x, 4.75, w, 2.2, 15);
  s.addNotes("Conclusion: the Decision Tree makes only 32 errors on 66,925 test flows, but the test split comes from the same capture as the training data and cannot reveal a shortcut such as the destination port. The 0 alerts on our capture show only that this benign traffic is not mistaken for DDoS. The improvements are not implemented. Thank you; questions welcome.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
