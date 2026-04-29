// Phase 3b annotator — Gemini-OCR redesign.
// Document-shaped editor: page-meta card + header + body|marginalia 2-col grid
// + auto-numbered footnotes + catchword. Body markers (footnote refs) are
// stored as structured records on each body line; superscripts in the rendered
// view are derived from `markers[]`, not free-typed.

let currentPayload = null;
let activeInput = null;
let currentPdfSource = "";
const DEFAULT_REVIEWER = "Paul Boys";

// ---------------------------------------------------------------------------
// Top bar / status / page selector
// ---------------------------------------------------------------------------
const pageSelect = document.getElementById("pageSelect");
const loadBtn = document.getElementById("loadBtn");
const saveBtn = document.getElementById("saveBtn");
const statusEl = document.getElementById("status");
const pdfFrame = document.getElementById("pdfFrame");
const pdfPaneSourceName = document.getElementById("pdfPaneSourceName");
const pdfPanePageNum = document.getElementById("pdfPanePageNum");

// Page meta fields.
const metaPageNum = document.getElementById("metaPageNum");
const metaSourcePdf = document.getElementById("metaSourcePdf");
const metaReviewer = document.getElementById("metaReviewer");
const metaAnnotationStatus = document.getElementById("metaAnnotationStatus");
const metaReviewStatus = document.getElementById("metaReviewStatus");
const metaNotes = document.getElementById("metaNotes");
const metaOcrPageSummary = document.getElementById("metaOcrPageSummary");
const metaOcrEngine = document.getElementById("metaOcrEngine");
const metaOcrModel = document.getElementById("metaOcrModel");
const metaOcrLang = document.getElementById("metaOcrLang");

// Region containers.
const headerContainer = document.getElementById("headerContainer");
const bodyContainer = document.getElementById("bodyContainer");
const unanchoredMarginaliaContainer = document.getElementById(
  "unanchoredMarginaliaContainer"
);
const footnoteContainer = document.getElementById("footnoteContainer");
const catchwordContainer = document.getElementById("catchwordContainer");

const addHeaderBtn = document.getElementById("addHeaderBtn");
const addBodyBtn = document.getElementById("addBodyBtn");
const addFootnoteBtn = document.getElementById("addFootnoteBtn");
const addCatchwordBtn = document.getElementById("addCatchwordBtn");

// Glyph bar.
const glyphBar = document.getElementById("glyphBar");
const superscriptInput = document.getElementById("superscriptInput");
const insertSuperscriptRawBtn = document.getElementById("insertSuperscriptRawBtn");
const insertSuperscriptBtn = document.getElementById("insertSuperscriptBtn");

const FOOTNOTE_KINDS = ["citation", "gloss", "cross_ref", "not_a_note", "other"];
const REVIEW_STATUSES = ["draft", "reviewed", "locked"];

const SUPERSCRIPT_MAP = {
  a: "ᵃ", b: "ᵇ", c: "ᶜ", d: "ᵈ", e: "ᵉ", f: "ᶠ", g: "ᵍ", h: "ʰ", i: "ᶦ",
  j: "ʲ", k: "ᵏ", l: "ˡ", m: "ᵐ", n: "ⁿ", o: "ᵒ", p: "ᵖ", r: "ʳ", s: "ˢ",
  t: "ᵗ", u: "ᵘ", v: "ᵛ", w: "ʷ", x: "ˣ", y: "ʸ", z: "ᶻ",
  A: "ᴬ", B: "ᴮ", D: "ᴰ", E: "ᴱ", G: "ᴳ", H: "ᴴ", I: "ᴵ", J: "ᴶ", K: "ᴷ",
  L: "ᴸ", M: "ᴹ", N: "ᴺ", O: "ᴼ", P: "ᴾ", R: "ᴿ", T: "ᵀ", U: "ᵁ", V: "ⱽ", W: "ᵂ",
  0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹",
  "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
};

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#a30000" : "#224b2b";
}

function updatePdfPaneHeader(sourcePdfKey, pageNum) {
  if (pdfPaneSourceName) {
    const baseName = String(sourcePdfKey || "").split(/[\\/]/).pop() || "";
    pdfPaneSourceName.textContent = baseName || "\u2014";
    pdfPaneSourceName.title = String(sourcePdfKey || "");
  }
  if (pdfPanePageNum) {
    pdfPanePageNum.textContent =
      Number.isFinite(pageNum) && pageNum > 0 ? String(pageNum) : "\u2014";
  }
}

function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function pad4(n) { return String(n).padStart(4, "0"); }

function makeLineId(pageId, region, ordinal) {
  return `${pageId}_${region}_l${pad4(ordinal)}`;
}

function nextFootnoteId(pageId, footnotes) {
  const used = new Set((footnotes || []).map((fn) => String(fn.footnote_id)));
  for (let i = 1; i < 10000; i++) {
    const candidate = `${pageId}_fn_${String(i).padStart(3, "0")}`;
    if (!used.has(candidate)) return candidate;
  }
  return `${pageId}_fn_${Date.now()}`;
}

function bindFocusTracking(container) {
  container.querySelectorAll("input, textarea, select").forEach((el) => {
    el.addEventListener("focus", () => {
      if (el.classList.contains("text-gold") || el.classList.contains("notes-field")) {
        activeInput = el;
      }
    });
  });
}

function insertGlyph(text) {
  if (!activeInput) return;
  const start = activeInput.selectionStart ?? activeInput.value.length;
  const end = activeInput.selectionEnd ?? activeInput.value.length;
  const value = activeInput.value;
  activeInput.value = value.slice(0, start) + text + value.slice(end);
  const next = start + text.length;
  activeInput.selectionStart = next;
  activeInput.selectionEnd = next;
  activeInput.dispatchEvent(new Event("input", { bubbles: true }));
  activeInput.focus();
}

function toSuperscript(value) {
  let output = "";
  for (const ch of String(value || "")) {
    output += SUPERSCRIPT_MAP[ch] || ch;
  }
  return output;
}

function insertCustomSuperscript(rawMode = false) {
  if (!superscriptInput) return;
  const value = superscriptInput.value || "";
  if (!value.trim()) return;
  insertGlyph(rawMode ? value : toSuperscript(value));
}

// ---------------------------------------------------------------------------
// Schema helpers (load / save normalization)
// ---------------------------------------------------------------------------
const REGION_NAMES = ["header", "body", "marginalia", "catchword"];

function normalizePayload(payload) {
  if (!payload || typeof payload !== "object") return;
  payload.regions = payload.regions || {};
  REGION_NAMES.forEach((r) => {
    if (!Array.isArray(payload.regions[r])) payload.regions[r] = [];
  });
  // Ignore legacy regions.footnote (kept on disk for older files but unused).
  if (Array.isArray(payload.regions.footnote)) {
    delete payload.regions.footnote;
  }
  if (!Array.isArray(payload.footnotes)) payload.footnotes = [];

  payload.regions.body.forEach((line) => {
    if (line && typeof line === "object" && !Array.isArray(line.markers)) {
      line.markers = [];
    }
  });

  payload.meta = payload.meta || {};
  payload.meta.reviewer = DEFAULT_REVIEWER;
}

function applyDefaultReviewer(payload) {
  if (!payload) return;
  payload.meta = payload.meta || {};
  payload.meta.reviewer = DEFAULT_REVIEWER;
  REGION_NAMES.forEach((r) => {
    (payload.regions[r] || []).forEach((line) => {
      if (line && typeof line === "object") line.reviewer = DEFAULT_REVIEWER;
    });
  });
  (payload.footnotes || []).forEach((fn) => {
    if (fn && typeof fn === "object") fn.reviewer = DEFAULT_REVIEWER;
  });
}

function getNextOrdinal(regionName) {
  const lines = currentPayload?.regions?.[regionName] || [];
  let max = 0;
  const pageId = currentPayload?.page_id || pageSelect.value;
  const pattern = new RegExp(`^${pageId}_${regionName}_l(\\d{4})$`);
  lines.forEach((line, idx) => {
    const match = String(line?.line_id || "").match(pattern);
    if (match) max = Math.max(max, Number(match[1]));
    else max = Math.max(max, idx + 1);
  });
  return max + 1;
}

function createEmptyLine(pageId, regionName, ordinal) {
  const line = {
    page_id: pageId,
    region: regionName,
    line_id: makeLineId(pageId, regionName, ordinal),
    text_gold: "",
    text_ocr_original: "",
    marker_id: "",
    review_status: "draft",
    reviewer: DEFAULT_REVIEWER,
    notes: "",
  };
  if (regionName === "body") line.markers = [];
  return line;
}

// ---------------------------------------------------------------------------
// Footnote logic: numbering, body-line rendering, marker insertion
// ---------------------------------------------------------------------------
function bodyLineIndex(pageId, footnote, bodyLines) {
  const target = String(footnote.body_line_id || "");
  const idx = bodyLines.findIndex((line) => String(line.line_id) === target);
  return idx;
}

function renumberFootnotes() {
  if (!currentPayload) return;
  const bodyLines = currentPayload.regions.body || [];
  const fns = currentPayload.footnotes || [];
  // Sort: anchored (by body line position) first, then orphans in their
  // existing relative order.
  const orphanOrder = new Map();
  fns.forEach((fn, i) => {
    if (!fn.body_line_id) orphanOrder.set(fn.footnote_id, i);
  });
  const sorted = fns.slice().sort((a, b) => {
    const ia = bodyLineIndex(null, a, bodyLines);
    const ib = bodyLineIndex(null, b, bodyLines);
    const aOrphan = ia < 0;
    const bOrphan = ib < 0;
    if (aOrphan && !bOrphan) return 1;
    if (!aOrphan && bOrphan) return -1;
    if (aOrphan && bOrphan) {
      return (orphanOrder.get(a.footnote_id) ?? 0) - (orphanOrder.get(b.footnote_id) ?? 0);
    }
    return ia - ib;
  });

  // Assign sequential marker_number; rebuild markers[] on body lines.
  bodyLines.forEach((line) => { line.markers = []; });
  sorted.forEach((fn, idx) => {
    fn.marker_number = idx + 1;
    if (fn.body_line_id) {
      const bodyLine = bodyLines.find((l) => String(l.line_id) === String(fn.body_line_id));
      if (bodyLine) {
        bodyLine.markers = bodyLine.markers || [];
        bodyLine.markers.push({
          number: idx + 1,
          footnote_id: fn.footnote_id,
          char_offset: null,
        });
      }
    }
  });
  currentPayload.footnotes = sorted;
}

function renderBodyTextWithMarkers(line) {
  // Returns HTML: text_gold escaped + <sup> markers appended at end of line.
  // Markers with char_offset null render at end-of-line (default).
  const safe = escapeHtml(line.text_gold || "");
  const markers = (line.markers || []).slice().sort((a, b) => {
    const oa = a.char_offset == null ? Number.MAX_SAFE_INTEGER : a.char_offset;
    const ob = b.char_offset == null ? Number.MAX_SAFE_INTEGER : b.char_offset;
    return oa - ob;
  });
  if (markers.length === 0) return safe;
  // For now char_offset positions are not honoured for rendering; all markers
  // stack at end. The structure is preserved for future positional rendering.
  const sups = markers
    .map((m) => `<sup class="marker-badge" data-fn-id="${escapeHtml(m.footnote_id)}" title="footnote ${m.number}">${m.number}</sup>`)
    .join("");
  return `${safe} ${sups}`;
}

// ---------------------------------------------------------------------------
// Card builders
// ---------------------------------------------------------------------------
function buildLineCardSimple(line, regionName, options = {}) {
  const card = document.createElement("div");
  card.className = `line-card line-card-${regionName}`;
  card.dataset.lineId = line.line_id || "";

  const safeId = escapeHtml(line.line_id || regionName);
  const safeText = escapeHtml(line.text_gold || "");
  const safeNotes = escapeHtml(line.notes || "");
  const reviewOpts = REVIEW_STATUSES.map(
    (s) => `<option value="${s}" ${line.review_status === s ? "selected" : ""}>${s}</option>`
  ).join("");

  card.innerHTML = `
    <div class="line-head">
      <span class="line-id">${safeId}</span>
      <div class="line-head-right">
        <select class="review-status-chip" data-field="review_status">${reviewOpts}</select>
        ${options.showRemove ? '<button type="button" class="line-remove-btn">Remove</button>' : ""}
      </div>
    </div>
    <textarea class="text-gold" data-field="text_gold" rows="1">${safeText}</textarea>
    <input class="notes-field" type="text" data-field="notes" placeholder="notes" value="${safeNotes}">
  `;

  bindLineFieldEvents(card, line);
  bindFocusTracking(card);

  if (options.showRemove) {
    card.querySelector(".line-remove-btn").addEventListener("click", () => options.onRemove?.());
  }
  return card;
}

function buildBodyLineCard(line, idx, options = {}) {
  const card = document.createElement("div");
  card.className = "line-card line-card-body";
  card.dataset.lineId = line.line_id || "";

  const safeId = escapeHtml(line.line_id || `body_${idx + 1}`);
  const safeText = escapeHtml(line.text_gold || "");
  const safeNotes = escapeHtml(line.notes || "");
  const reviewOpts = REVIEW_STATUSES.map(
    (s) => `<option value="${s}" ${line.review_status === s ? "selected" : ""}>${s}</option>`
  ).join("");

  card.innerHTML = `
    <div class="line-head">
      <span class="line-id">${safeId}</span>
      <div class="line-head-right">
        <button type="button" class="add-marker-btn" title="Insert footnote marker at end of this line">+ Footnote here</button>
        <select class="review-status-chip" data-field="review_status">${reviewOpts}</select>
        ${options.showRemove ? '<button type="button" class="line-remove-btn">Remove</button>' : ""}
      </div>
    </div>
    <textarea class="text-gold" data-field="text_gold" rows="1">${safeText}</textarea>
    <div class="body-markers-preview"></div>
    <input class="notes-field" type="text" data-field="notes" placeholder="notes" value="${safeNotes}">
  `;

  bindLineFieldEvents(card, line);
  bindFocusTracking(card);

  // Render marker badges (live preview, derived from line.markers).
  const preview = card.querySelector(".body-markers-preview");
  const renderMarkers = () => {
    const fnByNumber = (n) => (currentPayload.footnotes || []).find((fn) => fn.marker_number === n);
    preview.innerHTML = (line.markers || [])
      .slice()
      .sort((a, b) => a.number - b.number)
      .map((m) => {
        const fn = fnByNumber(m.number);
        const snippet = fn ? escapeHtml((fn.text_gold || "").slice(0, 60)) : "";
        return `<sup class="marker-badge" data-fn-id="${escapeHtml(m.footnote_id)}" title="${snippet}">${m.number}</sup>`;
      })
      .join(" ");
  };
  renderMarkers();

  card.querySelector(".add-marker-btn").addEventListener("click", () => {
    addFootnoteAnchored(line.line_id);
  });

  if (options.showRemove) {
    card.querySelector(".line-remove-btn").addEventListener("click", () => options.onRemove?.());
  }

  return card;
}

function bindLineFieldEvents(card, line) {
  card.querySelectorAll("[data-field]").forEach((el) => {
    const handler = () => {
      const field = el.dataset.field;
      line[field] = el.type === "checkbox" ? el.checked : el.value;
    };
    el.addEventListener("input", handler);
    el.addEventListener("change", handler);
  });
}

// ---------------------------------------------------------------------------
// Marginalia block (Option C: stacked fragments visually grouped)
// ---------------------------------------------------------------------------
function buildMarginaliaBlock(marginaliaList) {
  const block = document.createElement("div");
  block.className = "marginalia-block";
  marginaliaList.forEach((line) => {
    block.appendChild(buildMarginaliaCard(line));
  });
  return block;
}

function buildMarginaliaCard(line) {
  const card = document.createElement("div");
  card.className = "line-card line-card-marginalia";
  card.dataset.lineId = line.line_id || "";

  const safeId = escapeHtml(line.line_id || "marg");
  const safeText = escapeHtml(line.text_gold || "");
  const safeNotes = escapeHtml(line.notes || "");
  const safeMarker = escapeHtml(line.marker_id || "");

  // Anchor dropdown: list all body line_ids on the page + an "(unanchored)" option.
  const bodyLines = currentPayload?.regions?.body || [];
  const currentTarget = resolveMarginaliaAnchor(line);
  const anchorOpts = ['<option value="">(unanchored)</option>']
    .concat(
      bodyLines.map(
        (b) =>
          `<option value="${escapeHtml(b.line_id)}" ${b.line_id === currentTarget ? "selected" : ""}>${escapeHtml(b.line_id)}</option>`
      )
    )
    .join("");

  card.innerHTML = `
    <div class="line-head">
      <span class="line-id">${safeId}</span>
      <div class="line-head-right">
        <input class="marker-id-mini" type="text" data-field="marker_id" placeholder="m" value="${safeMarker}">
      </div>
    </div>
    <textarea class="text-gold" data-field="text_gold" rows="1">${safeText}</textarea>
    <div class="line-row">
      <label class="anchor-row">Anchor
        <select class="anchor-select">${anchorOpts}</select>
      </label>
      <input class="notes-field" type="text" data-field="notes" placeholder="notes" value="${safeNotes}">
    </div>
  `;

  bindLineFieldEvents(card, line);
  bindFocusTracking(card);

  card.querySelector(".anchor-select").addEventListener("change", (event) => {
    const newTarget = event.target.value || null;
    setMarginaliaAnchor(line, newTarget);
    renderAll();
  });
  return card;
}

function resolveMarginaliaAnchor(marginaliaLine) {
  // Look for a footnote whose source_marginalia_line_ids contains this line.
  const fns = currentPayload?.footnotes || [];
  const fn = fns.find((f) =>
    Array.isArray(f.source_marginalia_line_ids) &&
    f.source_marginalia_line_ids.includes(marginaliaLine.line_id)
  );
  return fn ? fn.body_line_id || "" : "";
}

function setMarginaliaAnchor(marginaliaLine, newBodyLineId) {
  // Move this marginalia line out of any existing footnote and into either an
  // existing footnote anchored to newBodyLineId (if exactly one) or a new one.
  // Then renumber. Keeps things simple — full split/merge UI is a follow-up.
  const fns = currentPayload.footnotes || (currentPayload.footnotes = []);
  // Remove from current footnote.
  fns.forEach((fn) => {
    if (Array.isArray(fn.source_marginalia_line_ids)) {
      fn.source_marginalia_line_ids = fn.source_marginalia_line_ids.filter(
        (id) => id !== marginaliaLine.line_id
      );
    }
  });
  // Drop empty footnotes.
  for (let i = fns.length - 1; i >= 0; i--) {
    const fn = fns[i];
    if (
      (!fn.source_marginalia_line_ids || fn.source_marginalia_line_ids.length === 0) &&
      fn.source_region === "marginalia" &&
      !fn.text_gold
    ) {
      fns.splice(i, 1);
    }
  }
  if (newBodyLineId) {
    // Find an existing footnote on this body line, or create a new one.
    let target = fns.find((fn) => fn.body_line_id === newBodyLineId);
    if (!target) {
      target = {
        footnote_id: nextFootnoteId(currentPayload.page_id, fns),
        page_id: currentPayload.page_id,
        marker_number: 0,
        body_line_id: newBodyLineId,
        text_gold: marginaliaLine.text_gold || "",
        text_ocr_original: marginaliaLine.text_ocr_original || marginaliaLine.text_gold || "",
        kind: "citation",
        source_region: "marginalia",
        source_marginalia_line_ids: [],
        review_status: "draft",
        notes: "",
      };
      fns.push(target);
    }
    if (!target.source_marginalia_line_ids.includes(marginaliaLine.line_id)) {
      target.source_marginalia_line_ids.push(marginaliaLine.line_id);
    }
  }
  renumberFootnotes();
}

// ---------------------------------------------------------------------------
// Footnote cards
// ---------------------------------------------------------------------------
function buildFootnoteCard(fn) {
  const card = document.createElement("div");
  card.className = "footnote-card";
  card.dataset.footnoteId = fn.footnote_id || "";

  const safeId = escapeHtml(fn.footnote_id || "");
  const safeText = escapeHtml(fn.text_gold || "");
  const safeNotes = escapeHtml(fn.notes || "");
  const safeAnchor = escapeHtml(fn.body_line_id || "(unanchored)");
  const kindOpts = FOOTNOTE_KINDS.map(
    (k) => `<option value="${k}" ${fn.kind === k ? "selected" : ""}>${k}</option>`
  ).join("");
  const reviewOpts = REVIEW_STATUSES.map(
    (s) => `<option value="${s}" ${fn.review_status === s ? "selected" : ""}>${s}</option>`
  ).join("");

  const bodyLines = currentPayload?.regions?.body || [];
  const anchorOpts = ['<option value="">(unanchored)</option>']
    .concat(
      bodyLines.map(
        (b) =>
          `<option value="${escapeHtml(b.line_id)}" ${b.line_id === fn.body_line_id ? "selected" : ""}>${escapeHtml(b.line_id)}</option>`
      )
    )
    .join("");

  card.innerHTML = `
    <div class="footnote-head">
      <sup class="footnote-marker-badge">${fn.marker_number || "?"}</sup>
      <span class="footnote-id">${safeId}</span>
      <span class="footnote-anchor">→ ${safeAnchor}</span>
      <select class="footnote-kind" data-field="kind">${kindOpts}</select>
      <select class="review-status-chip" data-field="review_status">${reviewOpts}</select>
      <button type="button" class="footnote-remove-btn">Delete</button>
    </div>
    <textarea class="text-gold" data-field="text_gold" rows="1">${safeText}</textarea>
    <div class="line-row">
      <label class="anchor-row">Anchor
        <select class="anchor-select">${anchorOpts}</select>
      </label>
      <input class="notes-field" type="text" data-field="notes" placeholder="notes" value="${safeNotes}">
    </div>
  `;

  card.querySelectorAll("[data-field]").forEach((el) => {
    const handler = () => {
      const field = el.dataset.field;
      fn[field] = el.type === "checkbox" ? el.checked : el.value;
    };
    el.addEventListener("input", handler);
    el.addEventListener("change", handler);
  });
  bindFocusTracking(card);

  card.querySelector(".anchor-select").addEventListener("change", (event) => {
    fn.body_line_id = event.target.value || "";
    renumberFootnotes();
    renderAll();
  });

  card.querySelector(".footnote-remove-btn").addEventListener("click", () => {
    const fns = currentPayload.footnotes || [];
    const idx = fns.indexOf(fn);
    if (idx >= 0) fns.splice(idx, 1);
    renumberFootnotes();
    renderAll();
  });

  return card;
}

function addFootnoteAnchored(bodyLineId) {
  if (!currentPayload) return;
  const fns = currentPayload.footnotes || (currentPayload.footnotes = []);
  fns.push({
    footnote_id: nextFootnoteId(currentPayload.page_id, fns),
    page_id: currentPayload.page_id,
    marker_number: 0,
    body_line_id: bodyLineId || "",
    text_gold: "",
    text_ocr_original: "",
    kind: "citation",
    source_region: "manual",
    source_marginalia_line_ids: [],
    review_status: "draft",
    notes: "",
  });
  renumberFootnotes();
  renderAll();
}

// ---------------------------------------------------------------------------
// Region renderers
// ---------------------------------------------------------------------------
function renderHeader() {
  headerContainer.innerHTML = "";
  const lines = currentPayload?.regions?.header || [];
  lines.forEach((line, idx) => {
    headerContainer.appendChild(
      buildLineCardSimple(line, "header", {
        showRemove: true,
        onRemove: () => {
          lines.splice(idx, 1);
          renderHeader();
        },
      })
    );
  });
}

function renderBodyWithMarginalia() {
  bodyContainer.innerHTML = "";
  unanchoredMarginaliaContainer.innerHTML = "";

  const bodyLines = currentPayload?.regions?.body || [];
  const marginaliaLines = currentPayload?.regions?.marginalia || [];

  // Group marginalia by anchored body_line_id (resolved via footnotes).
  const bodyToMarginalia = new Map();
  const unanchored = [];
  marginaliaLines.forEach((line) => {
    const anchor = resolveMarginaliaAnchor(line);
    if (anchor) {
      if (!bodyToMarginalia.has(anchor)) bodyToMarginalia.set(anchor, []);
      bodyToMarginalia.get(anchor).push(line);
    } else {
      unanchored.push(line);
    }
  });

  // Unanchored rail at the top.
  if (unanchored.length > 0) {
    const heading = document.createElement("div");
    heading.className = "unanchored-heading";
    heading.textContent = `Unanchored marginalia (${unanchored.length})`;
    unanchoredMarginaliaContainer.appendChild(heading);
    unanchoredMarginaliaContainer.appendChild(buildMarginaliaBlock(unanchored));
  }

  // Body rows: each row = body line + its marginalia block.
  bodyLines.forEach((line, idx) => {
    const row = document.createElement("div");
    row.className = "body-row";

    const bodyCell = document.createElement("div");
    bodyCell.className = "body-cell";
    bodyCell.appendChild(
      buildBodyLineCard(line, idx, {
        showRemove: true,
        onRemove: () => {
          bodyLines.splice(idx, 1);
          renumberFootnotes();
          renderAll();
        },
      })
    );

    const margCell = document.createElement("div");
    margCell.className = "marg-cell";
    const margForLine = bodyToMarginalia.get(line.line_id) || [];
    if (margForLine.length > 0) {
      margCell.appendChild(buildMarginaliaBlock(margForLine));
    }

    row.appendChild(bodyCell);
    row.appendChild(margCell);
    bodyContainer.appendChild(row);
  });
}

function renderFootnotes() {
  footnoteContainer.innerHTML = "";
  const fns = currentPayload?.footnotes || [];
  if (fns.length === 0) {
    const empty = document.createElement("div");
    empty.className = "footnote-empty";
    empty.textContent = "No footnotes yet. Use \u201c+ Footnote here\u201d on a body line, or anchor a marginalia.";
    footnoteContainer.appendChild(empty);
    return;
  }
  fns.forEach((fn) => footnoteContainer.appendChild(buildFootnoteCard(fn)));
}

function renderCatchword() {
  catchwordContainer.innerHTML = "";
  const lines = currentPayload?.regions?.catchword || [];
  lines.forEach((line, idx) => {
    catchwordContainer.appendChild(
      buildLineCardSimple(line, "catchword", {
        showRemove: true,
        onRemove: () => {
          lines.splice(idx, 1);
          renderCatchword();
        },
      })
    );
  });
}

function renderAll() {
  if (!currentPayload) return;
  renderHeader();
  renderBodyWithMarginalia();
  renderFootnotes();
  renderCatchword();
}

// ---------------------------------------------------------------------------
// Page meta binding
// ---------------------------------------------------------------------------
function bindMeta(payload) {
  const meta = payload.meta || (payload.meta = {});
  metaPageNum.value = String(payload.page_num || "");
  metaSourcePdf.value = String(payload.source_pdf || "");
  metaReviewer.value = DEFAULT_REVIEWER;
  metaAnnotationStatus.value = meta.annotation_status || "";
  metaReviewStatus.value = meta.review_status || "draft";
  metaNotes.value = meta.notes || "";
  metaOcrPageSummary.value = meta.ocr_page_summary || "";

  metaOcrEngine.textContent = meta.ocr_engine || "\u2014";
  metaOcrModel.textContent = meta.ocr_provider_model || "\u2014";
  metaOcrLang.textContent = (meta.ocr_lang || []).join(", ") || "\u2014";

  metaPageNum.oninput = () => {
    const v = parseInt(metaPageNum.value, 10);
    payload.page_num = Number.isFinite(v) ? v : payload.page_num;
  };
  metaSourcePdf.oninput = () => { payload.source_pdf = metaSourcePdf.value; };
  metaAnnotationStatus.oninput = () => { meta.annotation_status = metaAnnotationStatus.value; };
  metaReviewStatus.onchange = () => { meta.review_status = metaReviewStatus.value; };
  metaNotes.oninput = () => { meta.notes = metaNotes.value; };
  metaOcrPageSummary.oninput = () => { meta.ocr_page_summary = metaOcrPageSummary.value; };
}

// ---------------------------------------------------------------------------
// Load / Save
// ---------------------------------------------------------------------------
async function loadPage(pageId) {
  try {
    setStatus("Loading...");
    const res = await fetch(`/api/page/${pageId}`);
    if (!res.ok) throw new Error(`Load failed: ${res.status}`);
    currentPayload = await res.json();
    normalizePayload(currentPayload);
    applyDefaultReviewer(currentPayload);
    renumberFootnotes();
    bindMeta(currentPayload);
    renderAll();

    const parsed = Number(currentPayload.page_num);
    const fallback = Number(String(pageId || "").replace(/^p/, ""));
    const pdfPageNum = Number.isFinite(parsed) && parsed > 0 ? parsed
      : (Number.isFinite(fallback) && fallback > 0 ? fallback : 1);

    const sourcePdfKey = String(currentPayload.source_pdf || "");
    if (!pdfFrame.src || currentPdfSource !== sourcePdfKey) {
      currentPdfSource = sourcePdfKey;
      pdfFrame.src = `/pdfjs/${pageId}?page=${pdfPageNum}#page=${pdfPageNum}`;
    } else {
      pdfFrame.contentWindow?.postMessage({ type: "setPage", page: pdfPageNum }, window.location.origin);
    }
    updatePdfPaneHeader(sourcePdfKey, pdfPageNum);
    setStatus(`Loaded ${pageId}`);
  } catch (err) {
    setStatus(String(err), true);
  }
}

async function savePage() {
  if (!currentPayload) return;
  try {
    const pageId = pageSelect.value;
    setStatus("Saving...");
    applyDefaultReviewer(currentPayload);
    const res = await fetch(`/api/page/${pageId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clone(currentPayload)),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const errors = (data.errors || ["Save failed"]).join(" | ");
      throw new Error(errors);
    }
    if (data.meta && currentPayload?.meta) {
      currentPayload.meta = { ...currentPayload.meta, ...data.meta };
    }
    const editsCount = data.edits_recorded ?? 0;
    setStatus(`Saved ${pageId} (${editsCount} edits logged)`);
  } catch (err) {
    setStatus(String(err), true);
  }
}

loadBtn.addEventListener("click", () => loadPage(pageSelect.value));
saveBtn.addEventListener("click", savePage);

addHeaderBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  const ord = getNextOrdinal("header");
  currentPayload.regions.header.push(
    createEmptyLine(currentPayload.page_id || pageSelect.value, "header", ord)
  );
  renderHeader();
});

addBodyBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  const ord = getNextOrdinal("body");
  currentPayload.regions.body.push(
    createEmptyLine(currentPayload.page_id || pageSelect.value, "body", ord)
  );
  renderBodyWithMarginalia();
});

addFootnoteBtn.addEventListener("click", () => addFootnoteAnchored(""));

addCatchwordBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  const ord = getNextOrdinal("catchword");
  currentPayload.regions.catchword.push(
    createEmptyLine(currentPayload.page_id || pageSelect.value, "catchword", ord)
  );
  renderCatchword();
});

// ---------------------------------------------------------------------------
// Glyph bar / superscripts
// ---------------------------------------------------------------------------
glyphBar.querySelectorAll("button[data-glyph]").forEach((btn) => {
  btn.addEventListener("click", () => insertGlyph(btn.dataset.glyph));
});
if (insertSuperscriptRawBtn) {
  insertSuperscriptRawBtn.addEventListener("click", () => insertCustomSuperscript(true));
}
if (insertSuperscriptBtn) {
  insertSuperscriptBtn.addEventListener("click", () => insertCustomSuperscript(false));
}
if (superscriptInput) {
  superscriptInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      insertCustomSuperscript(false);
    }
  });
}

document.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key.toLowerCase() === "s") {
    event.preventDefault();
    savePage();
    return;
  }
  if (!event.altKey) return;
  const k = event.key;
  const map = { e: "æ", E: "Æ", o: "œ", O: "Œ", "6": "Ↄ", "7": "ↄ", d: "ᵈ", n: "ⁿ" };
  if (map[k]) {
    event.preventDefault();
    insertGlyph(map[k]);
  }
});

if (window.__PAGES__ && window.__PAGES__.length > 0) {
  pageSelect.value = window.__PAGES__[0];
  loadPage(window.__PAGES__[0]);
}

// ---------------------------------------------------------------------------
// OCR-from-UI controls
// ---------------------------------------------------------------------------
const ocrPdfSelect = document.getElementById("ocrPdfSelect");
const ocrPageInput = document.getElementById("ocrPageInput");
const ocrPartSelect = document.getElementById("ocrPartSelect");
const ocrOverwrite = document.getElementById("ocrOverwrite");
const ocrRunBtn = document.getElementById("ocrRunBtn");
const ocrStatus = document.getElementById("ocrStatus");

function setOcrStatus(msg, isError = false) {
  if (!ocrStatus) return;
  ocrStatus.textContent = msg;
  ocrStatus.style.color = isError ? "#c0392b" : "";
}

async function loadSourcePdfList() {
  if (!ocrPdfSelect) return;
  try {
    const res = await fetch("/api/source-pdfs");
    const data = await res.json();
    const pdfs = data.pdfs || [];
    ocrPdfSelect.innerHTML = "";
    if (pdfs.length === 0) {
      const opt = document.createElement("option");
      opt.textContent = "(no PDFs in 00_source_pdf/)";
      opt.value = "";
      ocrPdfSelect.appendChild(opt);
      return;
    }
    for (const name of pdfs) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      ocrPdfSelect.appendChild(opt);
    }
  } catch (err) {
    setOcrStatus(`PDF list failed: ${err}`, true);
  }
}

async function pollOcrJob(jobId, pageId) {
  const start = Date.now();
  while (true) {
    await new Promise((r) => setTimeout(r, 4000));
    const res = await fetch(`/api/ocr/status/${jobId}`);
    if (!res.ok) throw new Error(`status fetch failed: ${res.status}`);
    const job = await res.json();
    const elapsed = Math.round((Date.now() - start) / 1000);
    setOcrStatus(`${job.state} (${elapsed}s): ${job.message || ""}`);
    if (job.state === "done") return job;
    if (job.state === "error") throw new Error(job.message || "OCR job failed");
  }
}

async function runOcr(forceOverwrite) {
  const pdf = ocrPdfSelect?.value;
  const page = parseInt(ocrPageInput?.value || "0", 10);
  const part = ocrPartSelect?.value || "part1";
  if (!pdf) { setOcrStatus("Pick a PDF first.", true); return; }
  if (!Number.isFinite(page) || page < 1) { setOcrStatus("Page must be a positive integer.", true); return; }

  ocrRunBtn.disabled = true;
  setOcrStatus("Starting...");
  try {
    const res = await fetch("/api/ocr/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pdf, page, part, overwrite: !!(forceOverwrite || ocrOverwrite?.checked) }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 409 && data.error === "annotation_exists") {
      const proceed = window.confirm(`${data.message}\n\nOverwrite the existing annotation?`);
      if (!proceed) { setOcrStatus("Cancelled."); return; }
      ocrRunBtn.disabled = false;
      return runOcr(true);
    }
    if (!res.ok || !data.ok) throw new Error(data.error || data.message || `HTTP ${res.status}`);

    const { job_id: jobId, page_id: pageId } = data;
    setOcrStatus(`Queued (${pageId})`);
    const finalJob = await pollOcrJob(jobId, pageId);
    setOcrStatus(`Done: ${finalJob.message || pageId}`);

    const pagesRes = await fetch("/api/pages");
    const pagesData = await pagesRes.json();
    const pages = pagesData.pages || [];
    pageSelect.innerHTML = "";
    for (const p of pages) {
      const opt = document.createElement("option");
      opt.value = p; opt.textContent = p;
      pageSelect.appendChild(opt);
    }
    if (pages.includes(pageId)) {
      pageSelect.value = pageId;
      await loadPage(pageId);
    }
  } catch (err) {
    setOcrStatus(String(err.message || err), true);
  } finally {
    ocrRunBtn.disabled = false;
  }
}

if (ocrRunBtn) {
  ocrRunBtn.addEventListener("click", () => runOcr(false));
  loadSourcePdfList().then(previewOcrSelection);
}

function previewOcrSelection() {
  if (!ocrPdfSelect || !pdfFrame) return;
  const pdfName = String(ocrPdfSelect.value || "").trim();
  if (!pdfName) return;
  const page = parseInt(ocrPageInput?.value || "1", 10);
  const safePage = Number.isFinite(page) && page > 0 ? page : 1;
  const previewKey = `source-pdf:${pdfName}`;
  if (currentPdfSource !== previewKey) {
    currentPdfSource = previewKey;
    pdfFrame.src = `/pdfjs-source?pdf=${encodeURIComponent(pdfName)}&page=${safePage}#page=${safePage}`;
  } else {
    pdfFrame.contentWindow?.postMessage({ type: "setPage", page: safePage }, window.location.origin);
  }
  updatePdfPaneHeader(pdfName, safePage);
}

if (ocrPdfSelect) ocrPdfSelect.addEventListener("change", previewOcrSelection);
if (ocrPageInput) {
  ocrPageInput.addEventListener("change", previewOcrSelection);
  ocrPageInput.addEventListener("input", () => {
    clearTimeout(ocrPageInput._previewTimer);
    ocrPageInput._previewTimer = setTimeout(previewOcrSelection, 300);
  });
}
