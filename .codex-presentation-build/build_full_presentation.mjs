import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "/Users/tiffany/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const workspaceDir = "/Users/tiffany/nlp-internship";
const FINAL_PPTX = path.join(workspaceDir, "deliverables", "real_estate_nlp_final_presentation_v3.pptx");
const RUNTIME_PYTHON = "/Users/tiffany/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const { finalizePresentation, applyPresentationChartFont } = await import(pathToFileURL(
  path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")
).href);

const W = 1280;
const H = 720;
const FONT = "Avenir Next";
const C = {
  navy: "#102A43", navy2: "#183B56", teal: "#00A6A6", teal2: "#2EC4B6",
  gold: "#F2B134", coral: "#E76F51", cream: "#F7F4ED", white: "#FFFFFF",
  ink: "#243B53", muted: "#627D98", pale: "#E8F1F2", line: "#CBD5E1",
  blue: "#DDEFFC", green: "#E8F5F1", sand: "#FFF1D6",
};

const deck = Presentation.create({ slideSize: { width: W, height: H } });

function rect(slide, x, y, w, h, fill, radius = false, stroke = "none") {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: stroke === "none" ? { fill: "none", width: 0 } : { fill: stroke, width: 1 },
  });
}

function text(slide, value, x, y, w, h, size = 24, color = C.ink, bold = false, align = "left") {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  box.text = value;
  box.text.style = {
    typeface: FONT, fontSize: size, color, bold, alignment: align,
    verticalAlignment: "middle", autoFit: "shrinkText",
  };
  return box;
}

function line(slide, x, y, w, h, color = C.line, width = 2) {
  return slide.shapes.add({
    geometry: "line", position: { left: x, top: y, width: w, height: h },
    fill: "none", line: { fill: color, width },
  });
}

function title(slide, value, number, dark = false) {
  text(slide, value, 64, 38, 1060, 60, 34, dark ? C.white : C.navy, true);
  text(slide, String(number).padStart(2, "0"), 1162, 43, 54, 40, 18, dark ? C.teal2 : C.teal, true, "right");
  line(slide, 64, 102, 1152, 0, dark ? "#36566F" : C.line, 1);
}

function note(slide, value) {
  slide.speakerNotes.textFrame.setText(value);
}

function metric(slide, value, label, x, y, color, width = 330) {
  text(slide, value, x, y, width, 72, 48, color, true);
  line(slide, x, y + 82, width - 24, 0, color, 4);
  text(slide, label, x, y + 96, width, 64, 20, C.ink);
}

function sectionRows(slide, rows, startY = 145) {
  rows.forEach((row, i) => {
    const y = startY + i * 92;
    text(slide, row[0], 76, y, 70, 44, 17, row[3] ?? C.teal, true);
    text(slide, row[1], 160, y - 2, 310, 48, 22, C.navy, true);
    text(slide, row[2], 485, y - 2, 700, 54, 18, C.ink);
    if (i < rows.length - 1) line(slide, 160, y + 64, 1025, 0, C.line, 1);
  });
}

// 1. Cover
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  text(s, "NLP", 760, 55, 440, 220, 150, C.navy2, true, "right");
  rect(s, 72, 128, 72, 8, C.teal);
  text(s, "Real Estate NLP Platform", 72, 170, 850, 120, 54, C.white, true);
  text(s, "Technical project presentation", 74, 304, 560, 54, 26, C.teal2);
  text(s, "Natural language search, structured extraction, summarization, and fair housing compliance through a production FastAPI service", 74, 390, 820, 120, 24, "#D9E2EC");
  text(s, "NLP Internship  |  September 2026", 74, 624, 520, 36, 16, "#9FB3C8");
  note(s, "Opening: This presentation covers the problem, system design, measured results, live demo, technical challenges, production considerations, and lessons learned.");
}

// 2. Problem
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "The search problem", 2);
  text(s, "Real estate intent arrives as free text, while listing systems store structured fields and long remarks.", 72, 132, 1120, 72, 28, C.ink);
  const items = [
    ["Natural language", "Users mix location, price, rooms, amenities, and exclusions in one sentence.", C.teal],
    ["Fragmented data", "Useful facts appear across database columns and inconsistent listing remarks.", C.gold],
    ["Compliance risk", "Search and listing language can reference protected classes or exclusionary preferences.", C.coral],
  ];
  items.forEach((item, i) => {
    const x = 74 + i * 397;
    text(s, item[0], x, 265, 330, 54, 25, item[2], true);
    line(s, x, 326, 300, 0, item[2], 4);
    text(s, item[1], x, 350, 330, 170, 21, C.ink);
  });
  text(s, "Goal: return useful property results while preserving explainable filters and visible safety checks.", 74, 590, 1110, 56, 23, C.muted, true);
  note(s, "Project framing based on scripts/main.py, scripts/query_parser.py, scripts/entity_extractor.py, and scripts/compliance_checker.py.");
}

// 3. Approach
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Solution approach", 3);
  const stages = [
    ["1", "Parse", "Convert the query into price, room, location, amenity, and exclusion filters.", C.pale],
    ["2", "Retrieve", "Apply metadata filters first, then rank matching remarks by token similarity.", C.blue],
    ["3", "Enrich", "Extract listing entities and select informative sentences for summaries.", C.green],
    ["4", "Review", "Check listing or query text for fair housing risks and return evidence.", C.sand],
  ];
  stages.forEach((item, i) => {
    const x = 56 + i * 303;
    rect(s, x, 180, 266, 350, item[3], true, C.line);
    text(s, item[0], x + 24, 202, 48, 48, 22, C.teal, true, "center");
    text(s, item[1], x + 74, 198, 160, 58, 26, C.navy, true);
    line(s, x + 28, 275, 210, 0, C.line, 1);
    text(s, item[2], x + 26, 300, 214, 176, 20, C.ink, false, "center");
  });
  text(s, "FastAPI exposes the same pipeline to the Streamlit interface, OpenAPI clients, and operations tooling.", 78, 584, 1120, 60, 22, C.muted, false, "center");
  note(s, "The implementation uses deterministic parsing and extraction, database-backed retrieval, extractive summarization, and rule-based compliance checks.");
}

// 4. Architecture
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "System architecture", 4);
  const stages = [
    { x: 58, w: 225, label: "User experience", detail: "Streamlit search\nOpenAPI documentation", color: C.pale },
    { x: 332, w: 248, label: "FastAPI service", detail: "Pydantic validation\nRouting and middleware", color: C.blue },
    { x: 629, w: 280, label: "NLP services", detail: "Parse and extract\nSearch and summarize\nCompliance", color: C.green },
    { x: 958, w: 264, label: "Data layer", detail: "MySQL listings\nTTL response cache", color: C.sand },
  ];
  stages.forEach((stage, i) => {
    rect(s, stage.x, 202, stage.w, 310, stage.color, true, C.line);
    text(s, stage.label, stage.x + 20, 226, stage.w - 40, 54, 24, C.navy, true, "center");
    line(s, stage.x + 28, 295, stage.w - 56, 0, C.line, 1);
    text(s, stage.detail, stage.x + 22, 315, stage.w - 44, 150, 21, C.ink, false, "center");
    if (i < stages.length - 1) text(s, "›", stage.x + stage.w + 8, 310, 34, 70, 52, C.teal, false, "center");
  });
  text(s, "The API loads database records at startup and keeps conservative NLP fallbacks available when optional resources fail.", 72, 574, 1120, 66, 21, C.muted, false, "center");
  note(s, "Sources: scripts/main.py lifespan, NLPServices, middleware, and route definitions; scripts/frontend/search.py.");
}

// 5. API surface
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "API surface", 5);
  sectionRows(s, [
    ["POST", "/search", "Natural language retrieval with optional inline documents and structured filters."],
    ["POST", "/parse-query", "Filters plus optional SQL and bound parameters."],
    ["POST", "/extract-entities", "Bedrooms, bathrooms, price, square footage, and taxonomy terms."],
    ["POST", "/summarize", "Extractive summary with sentence and character limits."],
    ["POST", "/check-compliance", "Separate listing and query modes with evidence."],
  ]);
  text(s, "Operations routes add readiness, health, cache statistics, cache clearing, document replacement, and database reload.", 76, 612, 1110, 44, 18, C.muted);
  note(s, "Source: scripts/main.py. OpenAPI documentation is generated automatically at /docs and /redoc.");
}

// 6. Evaluation framework
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  title(s, "Evaluation framework", 6, true);
  const columns = [
    ["Accuracy", "Does the component return the expected label or field?", "Examples: intent accuracy and compliance accuracy", C.teal2],
    ["Coverage", "How often does the component produce a usable result or find a gold label?", "Examples: parser coverage and extraction recall", C.gold],
    ["Latency", "How long does the warm component path take on the local host?", "Reported as p50 and p95 milliseconds", C.coral],
  ];
  columns.forEach((item, i) => {
    const x = 74 + i * 397;
    text(s, item[0], x, 160, 330, 58, 28, item[3], true);
    line(s, x, 226, 300, 0, item[3], 3);
    text(s, item[1], x, 252, 325, 118, 21, C.white);
    text(s, item[2], x, 400, 325, 95, 18, "#B8C8D8");
  });
  text(s, "Labels stay explicit because coverage, recall, F1, and accuracy answer different questions.", 74, 585, 1110, 58, 22, C.white, true, "center");
  note(s, "Latency method: warm local component runtime on an Apple Silicon host. Search used 52,742 generated records. Measurements exclude network transport and database startup.");
}

// 7. Metrics scorecard
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Component metrics scorecard", 7);
  const values = [
    ["Component", "Quality result", "Coverage result", "Warm p50"],
    ["Search", "Relevance quality not measured", "52,742 records searched", "68.43 ms"],
    ["Query parsing", "Coverage metric only", "60/60 queries produced a filter", "0.07 ms"],
    ["Entity extraction", "Beds and baths F1 100%; price F1 93.6%", "288/300 numeric labels; taxonomy recall 77%", "0.03 ms"],
    ["Summarization", "No labeled quality set", "Evaluation coverage not measured", "0.18 ms"],
    ["Compliance", "Query accuracy 100%; listing accuracy 71.7%", "Recall 100% for queries; 50% for listings", "0.12 ms"],
  ];
  const table = s.tables.add({ rows: 6, columns: 4, left: 58, top: 142, width: 1164, height: 450, columnWidths: [195, 335, 425, 209], values });
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 4 }).assign({
    fill: C.navy,
    textStyle: { typeface: FONT, color: C.white, fontSize: 17, bold: true },
    margins: { left: 10, right: 10, top: 7, bottom: 7 },
  });
  table.cells.block({ row: 1, column: 0, rowCount: 5, columnCount: 4 }).assign({
    textStyle: { typeface: FONT, color: C.ink, fontSize: 15 },
    margins: { left: 10, right: 10, top: 7, bottom: 7 },
  });
  [1, 3, 5].forEach(row => table.cells.block({ row, column: 0, rowCount: 1, columnCount: 4 }).fill = C.cream);
  table.cells.block({ row: 1, column: 0, rowCount: 5, columnCount: 1 }).textStyle.bold = true;
  text(s, "Quality gaps remain visible instead of converting missing evaluations into proxy scores.", 70, 608, 1120, 42, 18, C.muted, true);
  note(s, "Sources: accuracy tests rerun September 11, 2026; compliance evaluation datasets; local benchmark in .codex-presentation-build/benchmark_components.py.");
}

// 8. Accuracy results
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Accuracy and coverage results", 8);
  const rows = [
    ["100%", "Intent classification accuracy", "40 held-out examples after training on 160 labeled queries", C.teal],
    ["100%", "Query parser coverage", "60 of 60 on-topic queries produced at least one filter", C.gold],
    ["100%", "Bedroom and bathroom F1", "Each entity evaluated on 100 labeled remarks", C.teal],
    ["93.6%", "Price extraction F1", "Precision 100% and recall 88% on 100 labels", C.gold],
    ["77.0%", "Taxonomy feature recall", "191 of 248 gold labels found across 100 listings", C.coral],
  ];
  rows.forEach((item, i) => {
    const y = 126 + i * 96;
    text(s, item[0], 74, y, 155, 54, 34, item[3], true);
    text(s, item[1], 250, y - 2, 385, 48, 21, C.navy, true);
    text(s, item[2], 660, y - 2, 525, 52, 18, C.ink);
    if (i < rows.length - 1) line(s, 250, y + 69, 935, 0, C.line, 1);
  });
  text(s, "Parser coverage indicates a nonempty result, not exact filter correctness.", 250, 621, 935, 36, 17, C.coral, true);
  note(s, "Sources: tests/test_week7.py, tests/test_week4.py, tests/test_numericf1.py, and data/processed/taxonomy_eval_results.csv. The structured field preservation test also scored 4,000/4,000 but does not test free text extraction.");
}

// 9. Latency results
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Warm component latency", 9);
  text(s, "Search over 52,742 records", 70, 132, 500, 44, 23, C.navy, true);
  metric(s, "68.43", "p50 milliseconds", 76, 210, C.teal, 205);
  metric(s, "76.28", "p95 milliseconds", 330, 210, C.teal, 205);
  text(s, "15 warm runs using the direct service path", 76, 404, 460, 52, 19, C.ink);
  text(s, "p95 was 11% above the median", 76, 466, 460, 44, 18, C.muted, true);
  text(s, "Other components, p95", 654, 132, 500, 44, 23, C.navy, true);
  const otherChart = s.charts.add("bar", {
    position: { left: 640, top: 180, width: 570, height: 350 },
    categories: ["Parse", "Entities", "Summary", "Compliance"],
    series: [{ name: "Milliseconds", values: [0.07, 0.03, 0.36, 0.22], fill: C.gold }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 48 },
    hasLegend: false,
    xAxis: { min: 0, max: 0.42, numberFormatCode: "0.00", majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { typeface: FONT, fontSize: 13, fill: C.muted } },
    yAxis: { textStyle: { typeface: FONT, fontSize: 14, fill: C.ink }, line: { fill: C.line, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: FONT, fontSize: 13, fill: C.navy, bold: true } },
    chartFill: C.white, chartLine: { fill: "none", width: 0 }, plotAreaFill: C.white, plotAreaLine: { fill: "none", width: 0 },
  });
  applyPresentationChartFont(otherChart, { fontFamily: FONT });
  text(s, "Warm direct service path. Measurements exclude HTTP transport, cache hits, database startup, and concurrent load.", 74, 575, 1120, 66, 18, C.muted, false, "center");
  note(s, "Benchmark runs: search 15; parse 100; entities 100; summary 100; compliance 100. Search p50/p95 68.43/76.28 ms. Parse 0.07/0.07. Entities 0.03/0.03. Summary 0.18/0.36. Compliance 0.12/0.22.");
}

// 10. Demo plan
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  title(s, "Five-minute live demo", 10, true);
  const items = [
    ["0:00", "Readiness", "Confirm API and database status"],
    ["0:30", "Parse", "Inspect filters and safe SQL parameters"],
    ["1:15", "Search", "Return ranked Irvine listings"],
    ["2:30", "Enrich", "Extract entities and summarize a remark"],
    ["3:45", "Compliance", "Compare query and listing checks"],
    ["4:40", "Wrap", "Show cache status and key result"],
  ];
  line(s, 116, 315, 1040, 0, "#36566F", 4);
  items.forEach((item, i) => {
    const x = 72 + i * 198;
    rect(s, x + 40, 294, 24, 24, i === 5 ? C.gold : C.teal2, true);
    text(s, item[0], x, 170, 145, 46, 22, i === 5 ? C.gold : C.teal2, true, "center");
    text(s, item[1], x, 225, 145, 44, 21, C.white, true, "center");
    text(s, item[2], x, 350, 145, 105, 17, "#D9E2EC", false, "center");
  });
  text(s, "Demo path: Streamlit for the audience, OpenAPI docs as the fallback interface.", 74, 565, 1110, 58, 22, C.white, true, "center");
  note(s, "Demo timing: 30 seconds readiness, 45 seconds parsing, 75 seconds search, 75 seconds enrichment, 55 seconds compliance, 20 seconds wrap. Keep /docs open as backup if Streamlit fails.");
}

// 11. Demo script
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Demo prompts and expected results", 11);
  const items = [
    ["1", "GET /ready", "Database status and loaded document count"],
    ["2", "3 bed 2 bath under 700k in Irvine", "Price, bedroom, bathroom, and city filters"],
    ["3", "POST /search with the same query", "Ranked matches with scores and metadata"],
    ["4", "Updated 3 bed, 2 bath home with pool at $695k", "Entities followed by a two-sentence summary"],
    ["5", "Ideal for families with children", "Compliance flag, category, severity, and evidence"],
  ];
  items.forEach((item, i) => {
    const y = 130 + i * 98;
    rect(s, 72, y, 50, 50, i === 4 ? C.coral : C.teal, true);
    text(s, item[0], 72, y, 50, 50, 20, C.white, true, "center");
    text(s, item[1], 152, y - 2, 465, 54, 20, C.navy, true);
    text(s, item[2], 635, y - 2, 550, 56, 18, C.ink);
    if (i < items.length - 1) line(s, 152, y + 67, 1033, 0, C.line, 1);
  });
  text(s, "Fallback: use /docs to execute the same requests if the frontend is unavailable.", 152, 625, 1033, 34, 17, C.muted, true);
  note(s, "Before presenting: start the API, confirm /ready, open the Streamlit search page, preload the query, and keep /docs open. Avoid typing long JSON live.");
}

// 12. Deep dive 1
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Deep dive: query parsing", 12);
  text(s, "Input", 76, 138, 180, 42, 19, C.teal, true);
  text(s, "“3 bed 2 bath under 700k in Irvine with a pool”", 76, 184, 470, 92, 27, C.navy, true);
  line(s, 576, 136, 0, 440, C.line, 2);
  text(s, "Structured output", 620, 138, 300, 42, 19, C.gold, true);
  const filters = [
    ["price_max", "700000"], ["bedrooms", "3"], ["bathrooms", "2"],
    ["city", "Irvine"], ["amenities", "pool"],
  ];
  filters.forEach((item, i) => {
    const y = 196 + i * 65;
    text(s, item[0], 620, y, 230, 42, 19, C.navy, true);
    text(s, item[1], 875, y, 270, 42, 19, C.ink);
    if (i < filters.length - 1) line(s, 620, y + 49, 520, 0, C.line, 1);
  });
  text(s, "Challenge", 76, 338, 170, 42, 19, C.coral, true);
  text(s, "Normalize compact forms such as 700k, distinguish exact room counts from minimums, and keep SQL values parameterized.", 76, 382, 450, 150, 20, C.ink);
  text(s, "Measured result: 60/60 queries produced a filter. Exact-match correctness still needs a labeled benchmark.", 76, 585, 1080, 56, 20, C.muted, true);
  note(s, "Source: scripts/query_parser.py and scripts/main.py. Explain that to_sql returns placeholders and parameters instead of concatenating values.");
}

// 13. Deep dive 2
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Deep dive: retrieval and caching", 13);
  const stages = [
    ["Database corpus", "52,742 listings in the verified load", C.sand],
    ["Metadata gate", "Price, rooms, and city remove invalid candidates", C.blue],
    ["Text ranking", "Token cosine similarity orders the remaining remarks", C.green],
    ["TTL cache", "Payload hash returns repeat results without recomputation", C.pale],
  ];
  stages.forEach((item, i) => {
    const x = 54 + i * 305;
    rect(s, x, 185, 270, 260, item[2], true, C.line);
    text(s, item[0], x + 22, 215, 226, 54, 23, C.navy, true, "center");
    line(s, x + 28, 283, 214, 0, C.line, 1);
    text(s, item[1], x + 24, 305, 222, 108, 18, C.ink, false, "center");
  });
  text(s, "Challenge", 74, 492, 150, 38, 19, C.coral, true);
  text(s, "The current ranker scans the corpus, so latency grows with record count. Cache keys include the document version to prevent stale search results after reload.", 74, 530, 1110, 90, 20, C.ink);
  text(s, "Local result: 68.43 ms p50 and 76.28 ms p95 over 52,742 generated records.", 74, 625, 1110, 34, 18, C.teal, true);
  note(s, "Source: scripts/main.py search, cached_compute, TTLCache, replace_documents, and documents_version. Future semantic search should preserve the metadata-first filter path.");
}

// 14. Deep dive 3
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Deep dive: compliance tradeoffs", 14);
  text(s, "Query mode", 74, 145, 470, 48, 26, C.teal, true);
  metric(s, "100%", "accuracy on 48 labeled queries", 74, 214, C.teal, 450);
  text(s, "28 risky and 20 compliant examples were classified correctly.", 74, 390, 450, 78, 20, C.ink);
  line(s, 624, 140, 0, 450, C.line, 2);
  text(s, "Listing mode", 684, 145, 470, 48, 26, C.coral, true);
  metric(s, "71.7%", "accuracy on 60 labeled listings", 684, 214, C.coral, 450);
  text(s, "Precision remained 100%, but recall fell to 50%. The checker missed paraphrases and indirect protected-class references.", 684, 390, 450, 112, 20, C.ink);
  text(s, "Production implication: keep the checker as a review aid until listing recall improves.", 74, 594, 1080, 54, 22, C.navy, true, "center");
  note(s, "Compliance evaluation rerun September 11, 2026. Query confusion matrix: TP 28, FP 0, FN 0, TN 20. Listing matrix: TP 17, FP 0, FN 17, TN 26.");
}

// 15. Production considerations
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Production considerations", 15);
  const rows = [
    ["01", "Rate limiting", "Sliding one-second window permits 10 requests per second per client IP."],
    ["02", "Caching", "Bounded TTL cache reduces repeat NLP work; Redis is needed for multiple workers."],
    ["03", "Database", "Startup autoload and readiness state expose connection failures without hiding them."],
    ["04", "Observability", "Structured request logs include method, path, status, duration, client IP, and request ID."],
    ["05", "Failure handling", "Thread-pool execution keeps slow NLP work off the event loop; fallbacks preserve basic service."],
  ];
  sectionRows(s, rows, 135);
  text(s, "Credentials remain in environment variables, and the Docker image runs as a non-root user.", 160, 617, 1020, 40, 18, C.muted, true);
  note(s, "Source: scripts/main.py settings, middleware, lifespan, cached_compute, and readiness route; Docker configuration reviewed in the project root.");
}

// 16. Learnings
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  title(s, "Project learnings", 16, true);
  const lessons = [
    ["Metric definitions matter", "A 100% parser result measured nonempty output, not exact filter correctness."],
    ["Structured filters improve trust", "Showing extracted constraints makes search behavior easier to inspect and debug."],
    ["Rules perform unevenly by context", "Compliance queries were easy for the rules, while nuanced listing language reduced recall."],
    ["Operational behavior belongs in the API", "Readiness, cache visibility, rate limits, and request IDs support real deployment work."],
  ];
  lessons.forEach((item, i) => {
    const y = 140 + i * 118;
    text(s, String(i + 1).padStart(2, "0"), 78, y, 72, 46, 19, i % 2 ? C.gold : C.teal2, true);
    text(s, item[0], 165, y - 2, 390, 48, 23, C.white, true);
    text(s, item[1], 575, y - 2, 600, 62, 19, "#D9E2EC");
    if (i < lessons.length - 1) line(s, 165, y + 77, 1010, 0, "#36566F", 1);
  });
  note(s, "Use this slide to connect technical work to engineering judgment: define metrics precisely, preserve explainability, and measure known weaknesses.");
}

// 17. Future work
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Future work", 17);
  const items = [
    ["Near term", "Add an exact-match parser benchmark and labeled summarization evaluation.", C.teal],
    ["Retrieval", "Connect FAISS semantic retrieval to the database corpus and report precision at k.", C.gold],
    ["Compliance", "Expand indirect language patterns, then retest listing recall without sacrificing precision.", C.coral],
    ["Scale", "Move cache and rate-limit state to Redis and load test multiple API workers.", C.teal],
    ["Security", "Add authentication for document reload and cache administration routes.", C.gold],
  ];
  items.forEach((item, i) => {
    const y = 132 + i * 99;
    text(s, item[0], 76, y, 210, 48, 21, item[2], true);
    line(s, 286, y + 23, 55, 0, item[2], 3);
    text(s, item[1], 370, y - 3, 810, 58, 20, C.ink);
  });
  text(s, "Highest-value next measurement: end-to-end search relevance on real user queries.", 76, 625, 1100, 34, 19, C.navy, true);
  note(s, "Prioritize measurement gaps before expanding model complexity. Search relevance and summarization quality currently lack labeled benchmarks.");
}

// 18. Q&A
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Technical Q&A preparation", 18);
  const qa = [
    ["Why rules instead of an LLM?", "Rules provide deterministic behavior, low latency, and visible evidence. They also establish a baseline for later model comparison."],
    ["What limits search quality?", "The API currently uses token similarity after metadata filtering. A labeled relevance set and semantic index are the next steps."],
    ["Why is compliance listing recall low?", "Listings use indirect and contextual language that exact patterns miss. The test found 17 false negatives and no false positives."],
    ["Will the rate limit work with multiple workers?", "Each worker has local state today. Redis or an API gateway should enforce a shared production limit."],
    ["How do you prevent stale cached search results?", "The document version forms part of each search cache key, and reload operations clear cached entries."],
  ];
  qa.forEach((item, i) => {
    const y = 124 + i * 104;
    text(s, item[0], 72, y, 400, 58, 20, C.navy, true);
    text(s, item[1], 495, y - 1, 700, 68, 18, C.ink);
    if (i < qa.length - 1) line(s, 72, y + 78, 1123, 0, C.line, 1);
  });
  text(s, "Closing point: the platform demonstrates an end-to-end NLP product and makes its current measurement gaps explicit.", 72, 632, 1120, 32, 18, C.teal, true);
  note(s, "Additional questions to prepare for: database schema mapping, cache invalidation, CORS configuration, input limits, SQL injection protection, and how to build a human-reviewed compliance workflow.");
}

const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
const candidatePath = path.join(stagingDir, "real_estate_nlp_final_presentation_v3_candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 18,
  requiredNativeTableOwnerSlides: [7],
  requiredNativeChartOwnerSlides: [9],
  materializeLiteralChartWorkbooks: true,
};
const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "7",
  ],
  fontPolicy: { basis: "design", families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "real_estate_nlp_final_presentation_v3.validation.json"),
});
console.log(JSON.stringify({ finalPath: FINAL_PPTX, result }, null, 2));
