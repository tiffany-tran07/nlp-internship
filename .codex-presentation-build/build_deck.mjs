import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "/Users/tiffany/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const workspaceDir = "/Users/tiffany/nlp-internship";
const TMP_DIR = path.join(workspaceDir, ".codex-presentation-build");
const FINAL_PPTX = path.join(workspaceDir, "deliverables", "real_estate_nlp_project_summary_verified_accuracy.pptx");
const RUNTIME_PYTHON = "/Users/tiffany/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const { finalizePresentation } = await import(pathToFileURL(
  path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")
).href);

const W = 1280;
const H = 720;
const FONT = "Avenir Next";
const C = {
  navy: "#102A43",
  navy2: "#183B56",
  teal: "#00A6A6",
  teal2: "#2EC4B6",
  gold: "#F2B134",
  coral: "#E76F51",
  cream: "#F7F4ED",
  white: "#FFFFFF",
  ink: "#243B53",
  muted: "#627D98",
  pale: "#E8F1F2",
  line: "#CBD5E1",
};

const deck = Presentation.create({ slideSize: { width: W, height: H } });

function rect(slide, x, y, w, h, fill, radius = false, line = "none") {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: line === "none" ? { fill: "none", width: 0 } : { fill: line, width: 1 },
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
    typeface: FONT,
    fontSize: size,
    color,
    bold,
    alignment: align,
    verticalAlignment: "middle",
    autoFit: "shrinkText",
  };
  return box;
}

function line(slide, x, y, w, h, color = C.line, width = 2) {
  return slide.shapes.add({
    geometry: "line",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: color, width },
  });
}

function title(slide, value, number, dark = false) {
  text(slide, value, 64, 38, 1060, 60, 34, dark ? C.white : C.navy, true);
  text(slide, String(number).padStart(2, "0"), 1162, 43, 54, 40, 18, dark ? C.teal2 : C.teal, true, "right");
  line(slide, 64, 102, 1152, 0, dark ? "#36566F" : C.line, 1);
}

function note(slide, sources) {
  slide.speakerNotes.textFrame.setText(`Internal project sources: ${sources}`);
}

// 1. Cover
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  text(s, "NLP", 760, 55, 440, 220, 150, "#183B56", true, "right");
  rect(s, 72, 128, 72, 8, C.teal);
  text(s, "Real Estate NLP Platform", 72, 170, 850, 120, 54, C.white, true);
  text(s, "Project summary", 74, 304, 480, 54, 26, C.teal2, false);
  text(s, "Natural-language property search backed by MySQL and exposed through a production FastAPI service", 74, 394, 730, 105, 25, "#D9E2EC", false);
  text(s, "NLP Internship  |  September 2026", 74, 624, 520, 36, 16, "#9FB3C8", false);
  note(s, "scripts/main.py; scripts/frontend/search.py; scripts/query_parser.py");
}

// 2. Scope
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Project scope", 2);
  text(s, "The project turns free-form real estate language into searchable, structured, and reviewable information.", 64, 130, 1110, 72, 28, C.ink, false);

  const metrics = [
    ["5", "core NLP capabilities", C.teal],
    ["12", "application routes", C.gold],
    ["52,742", "listings loaded in verification", C.coral],
  ];
  metrics.forEach(([value, label, color], i) => {
    const x = 76 + i * 395;
    text(s, value, x, 262, 330, 96, i === 2 ? 50 : 64, color, true);
    line(s, x, 372, 300, 0, color, 4);
    text(s, label, x, 392, 310, 70, 21, C.ink, false);
  });
  text(s, "Built as a complete path from data preparation and taxonomy work to an API, database integration, and a Streamlit search interface.", 76, 548, 1090, 72, 24, C.muted, false);
  note(s, "scripts/*.py; scripts/main.py route definitions; verified database load on 2026-08-31");
}

// 3. Architecture
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "System architecture", 3);

  const stages = [
    { x: 58, w: 225, label: "User experience", detail: "Streamlit search\nOpenAPI docs", color: C.pale },
    { x: 332, w: 248, label: "FastAPI service", detail: "Validation\nRouting\nMiddleware", color: "#DDEFFC" },
    { x: 629, w: 280, label: "NLP services", detail: "Parse  |  Extract\nSearch  |  Summarize\nCompliance", color: "#E8F5F1" },
    { x: 958, w: 264, label: "Data layer", detail: "MySQL listings\nTTL response cache", color: "#FFF1D6" },
  ];
  stages.forEach((stage, i) => {
    rect(s, stage.x, 202, stage.w, 310, stage.color, true, C.line);
    text(s, stage.label, stage.x + 20, 226, stage.w - 40, 54, 24, C.navy, true, "center");
    line(s, stage.x + 28, 295, stage.w - 56, 0, C.line, 1);
    text(s, stage.detail, stage.x + 22, 315, stage.w - 44, 150, 21, C.ink, false, "center");
    if (i < stages.length - 1) {
      text(s, "›", stage.x + stage.w + 8, 310, 34, 70, 52, C.teal, false, "center");
    }
  });
  text(s, "Database loading runs during API startup. The NLP layer stays available with conservative fallbacks when optional taxonomy resources are absent.", 72, 574, 1120, 66, 21, C.muted, false, "center");
  note(s, "scripts/main.py NLPServices, lifespan, middleware, and routes; scripts/frontend/search.py");
}

// 4. Capabilities
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "NLP capabilities", 4);
  const rows = [
    ["01", "Search", "Ranks listing remarks by token similarity, then applies numeric and city filters."],
    ["02", "Query parsing", "Extracts price ranges, bedrooms, bathrooms, cities, amenities, and exclusions."],
    ["03", "Entity extraction", "Identifies structured facts such as price, square footage, room counts, and taxonomy terms."],
    ["04", "Summarization", "Selects the most informative listing sentences using entity and position signals."],
    ["05", "Compliance checking", "Flags fair-housing risks in listing language and user search requests."],
  ];
  rows.forEach((row, i) => {
    const y = 132 + i * 103;
    text(s, row[0], 72, y, 60, 48, 18, C.teal, true);
    text(s, row[1], 150, y - 2, 250, 50, 25, C.navy, true);
    text(s, row[2], 405, y - 2, 790, 60, 20, C.ink, false);
    if (i < rows.length - 1) line(s, 150, y + 72, 1040, 0, C.line, 1);
  });
  note(s, "scripts/main.py; scripts/query_parser.py; scripts/entity_extractor.py; scripts/listing_summarizer.py; scripts/compliance_checker.py");
}

// 5. Verified accuracy metrics
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Verified accuracy metrics", 5);

  const metrics = [
    ["100%", "ACCURACY", "Intent classifier", "40 held-out queries after training on 160 labeled queries", C.teal],
    ["100%", "ACCURACY", "Structured field preservation", "4,000 checks across 1,000 listings", C.gold],
    ["100%", "COVERAGE", "Query parser", "60 of 60 on-topic queries produced at least one filter", C.coral],
    ["100%", "F1 SCORE", "Bedroom and bathroom extraction", "Each entity evaluated on 100 labeled remarks", C.teal],
    ["93.6%", "F1 SCORE", "Price extraction", "100% precision and 88% recall on 100 labeled remarks", C.gold],
    ["77.0%", "RECALL", "Taxonomy feature extraction", "191 of 248 gold labels found across 100 listings", C.coral],
  ];
  metrics.forEach((item, i) => {
    const y = 126 + i * 87;
    text(s, item[0], 72, y, 155, 40, 34, item[4], true);
    text(s, item[1], 72, y + 39, 155, 20, 12, item[4], true);
    text(s, item[2], 248, y - 2, 350, 50, 21, C.navy, true);
    text(s, item[3], 625, y - 2, 570, 50, 18, C.ink, false);
    if (i < metrics.length - 1) line(s, 248, y + 65, 947, 0, C.line, 1);
  });
  note(s, "Verified by rerun on September 11, 2026. Sources: tests/test_week7.py; tests/test_week6.py; tests/test_week4.py; tests/test_numericf1.py; data/processed/taxonomy_eval_results.csv");
}

// 6. Accuracy notes
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Accuracy notes", 6);

  const notes = [
    ["Intent classification", "The 100% result comes from a fixed 80/20 split of 200 labeled queries. The held-out set contains 40 examples across three intent labels."],
    ["Structured fields", "This test checks whether the signal extractor preserves four existing listing fields. It does not measure free-text extraction."],
    ["Query parsing", "The 100% parser result is a coverage rate. A query counts as successful when it yields at least one filter, so this is not exact-match accuracy."],
    ["Numeric entities", "Bedroom and bathroom F1 reached 100%. Price extraction missed 12 of 100 labels, producing 88% recall and no false positives."],
    ["Taxonomy features", "The stored evaluation reports recall only. It measures found gold labels and does not penalize extra predicted features."],
    ["Test run status", "Eight selected pytest cases passed, and the numeric F1 evaluation completed. Semantic retrieval lacks a current precision-at-k result because its model fixture was unavailable offline."],
  ];
  notes.forEach((item, i) => {
    const column = i < 3 ? 0 : 1;
    const row = i % 3;
    const x = column === 0 ? 72 : 662;
    const y = 138 + row * 174;
    text(s, item[0], x, y, 500, 42, 22, column === 0 ? C.teal : C.coral, true);
    text(s, item[1], x, y + 48, 500, 104, 18, C.ink, false);
    if (row < 2) line(s, x, y + 158, 500, 0, C.line, 1);
  });
  line(s, 628, 138, 0, 500, C.line, 2);
  note(s, "Evaluation definitions in tests/test_week4.py, tests/test_week6.py, tests/test_week7.py, tests/test_numericf1.py, tests/test_semanticSearcher.py, and tests/test_week9.py");
}

// 7. Search example
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  title(s, "A verified query path", 7, true);
  text(s, "“3 bed 2 bath under 700k in Irvine”", 76, 140, 1120, 70, 34, C.white, true, "center");

  const items = [
    ["PARSED", "price ≤ $700,000\n3 bedrooms\n2 bathrooms\ncity = Irvine", "#183B56"],
    ["SEARCHED", "52,742 database listings\nmetadata filters first\ntext relevance second", "#174A5B"],
    ["RETURNED", "1 matching listing\nIrvine, CA\n$610,000", "#6B4B22"],
  ];
  items.forEach((item, i) => {
    const x = 72 + i * 400;
    rect(s, x, 260, 336, 260, item[2], true, "#36566F");
    text(s, item[0], x + 24, 284, 288, 35, 16, C.teal2, true, "center");
    text(s, item[1], x + 26, 338, 284, 140, 22, C.white, false, "center");
    if (i < 2) text(s, "›", x + 350, 344, 38, 70, 54, C.gold, false, "center");
  });
  text(s, "Verification used the Dockerized API connected to the local idx_exchange database.", 78, 586, 1110, 44, 18, "#B8C8D8", false, "center");
  note(s, "scripts/main.py; observed API smoke-test response on 2026-08-31");
}

// 8. API surface
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "REST API surface", 8);
  const groups = [
    {
      x: 64, title: "NLP", color: C.teal,
      lines: ["POST  /search", "POST  /parse-query", "POST  /extract-entities", "POST  /summarize", "POST  /check-compliance"],
    },
    {
      x: 462, title: "Search data", color: C.gold,
      lines: ["PUT   /documents", "POST  /documents/reload", "", "MySQL autoload at startup", "Database status in /ready"],
    },
    {
      x: 860, title: "Operations", color: C.coral,
      lines: ["GET   /health", "GET   /ready", "GET   /cache/stats", "DELETE /cache", "GET   /openapi.json"],
    },
  ];
  groups.forEach((g) => {
    text(s, g.title, g.x, 146, 330, 48, 27, g.color, true);
    line(s, g.x, 204, 320, 0, g.color, 4);
    text(s, g.lines.join("\n"), g.x, 236, 330, 300, 21, C.ink, false);
  });
  rect(s, 64, 580, 1130, 62, C.pale, true, "none");
  text(s, "Pydantic validates every request. FastAPI generates interactive documentation at /docs and /redoc.", 88, 590, 1082, 42, 20, C.navy, true, "center");
  note(s, "scripts/main.py route decorators and Pydantic models");
}

// 9. Production controls
{
  const s = deck.slides.add();
  s.background.fill = C.cream;
  title(s, "Production controls", 9);

  text(s, "10 requests / second / IP", 72, 142, 540, 64, 36, C.coral, true);
  text(s, "Sliding-window rate limiting returns HTTP 429 with Retry-After and remaining-limit headers.", 74, 212, 520, 88, 21, C.ink, false);
  line(s, 640, 142, 0, 410, C.line, 2);
  text(s, "Bounded TTL cache", 690, 142, 490, 54, 30, C.teal, true);
  text(s, "Cached NLP responses include HIT or MISS headers. Corpus reloads invalidate stale search results.", 690, 206, 470, 84, 21, C.ink, false);

  const controls = [
    ["Structured logs", "JSON request events include method, path, status, duration, client IP, and request ID."],
    ["Responsive concurrency", "Synchronous NLP work runs in a thread pool instead of blocking FastAPI's event loop."],
    ["Graceful diagnostics", "Readiness reports database failures while health checks keep the process observable."],
  ];
  controls.forEach((item, i) => {
    const x = 72 + i * 390;
    text(s, item[0], x, 390, 340, 42, 22, C.navy, true);
    text(s, item[1], x, 438, 340, 122, 18, C.muted, false);
  });
  note(s, "scripts/main.py TTLCache, SlidingWindowRateLimiter, cached_compute, middleware, and /ready");
}

// 10. Database and deployment
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  title(s, "Database and container deployment", 10);

  const flow = [
    ["MySQL", "rets_property"],
    ["Startup loader", "validated documents"],
    ["FastAPI", "search corpus"],
    ["Docker", "port 8000"],
  ];
  flow.forEach((item, i) => {
    const x = 58 + i * 305;
    rect(s, x, 160, 245, 125, i === 0 ? "#FFF1D6" : i === 3 ? "#DDEFFC" : C.pale, true, C.line);
    text(s, item[0], x + 16, 177, 213, 42, 24, C.navy, true, "center");
    text(s, item[1], x + 16, 223, 213, 35, 17, C.muted, false, "center");
    if (i < flow.length - 1) text(s, "›", x + 254, 184, 42, 70, 48, C.teal, false, "center");
  });

  text(s, "Runtime configuration", 72, 350, 430, 46, 27, C.navy, true);
  text(s, "DB_HOST\nDB_PORT\nDB_USER\nDB_PASSWORD\nDB_NAME", 74, 408, 220, 185, 20, C.teal, true);
  text(s, "Credentials stay outside source control. Docker reaches a host database through host.docker.internal.", 310, 408, 330, 140, 20, C.ink, false);

  text(s, "Container safeguards", 708, 350, 430, 46, 27, C.navy, true);
  text(s, "Non-root UID 10001\nBuilt-in health check\nPinned application dependencies\nOptimized build context", 710, 408, 440, 170, 20, C.ink, false);
  note(s, "Dockerfile; .dockerignore; requirements.txt; scripts/main.py database settings and loader");
}

// 11. Frontend and next steps
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  title(s, "Current experience and next steps", 11, true);

  text(s, "Streamlit experience", 72, 140, 500, 52, 29, C.teal2, true);
  text(s, "Natural-language query form\nAPI readiness and database status\nParsed filter inspection\nListing metadata and relevance scores\nClear timeout and rate-limit errors", 74, 212, 500, 240, 21, C.white, false);

  line(s, 630, 142, 0, 430, "#36566F", 2);
  text(s, "Recommended next steps", 686, 140, 500, 52, 29, C.gold, true);
  const next = [
    ["1", "Move cache and rate-limit state to Redis before adding multiple API workers."],
    ["2", "Connect the existing FAISS semantic searcher to the database-loaded corpus."],
    ["3", "Add authenticated operations endpoints and scheduled database refreshes."],
    ["4", "Expand integration tests around database failures and result quality."],
  ];
  next.forEach((item, i) => {
    const y = 214 + i * 90;
    text(s, item[0], 690, y, 38, 38, 18, C.teal2, true, "center");
    text(s, item[1], 748, y - 4, 430, 62, 19, C.white, false);
  });
  text(s, "The project now supports an end-to-end demonstration: database to NLP API to interactive search.", 74, 622, 1110, 38, 19, "#B8C8D8", false);
  note(s, "scripts/frontend/search.py; scripts/semantic_searcher.py; scripts/main.py; tests/");
}

const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
const candidatePath = path.join(stagingDir, "real_estate_nlp_project_summary_verified_accuracy_candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 11,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
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
  ],
  fontPolicy: { basis: "design", families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "real_estate_nlp_project_summary_verified_accuracy.validation.json"),
});
console.log(JSON.stringify({ finalPath: FINAL_PPTX, result }, null, 2));
