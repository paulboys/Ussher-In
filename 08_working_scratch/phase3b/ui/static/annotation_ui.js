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
const undoBtn = document.getElementById("undoBtn");
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
const footnoteSection = document.getElementById("footnoteSection");
const stickyFootnoteSection = document.getElementById("stickyFootnoteSection");
const stickyFootnoteContainer = document.getElementById("stickyFootnoteContainer");
const bodySection = document.getElementById("bodySection");
const metaEditionBadge = document.getElementById("metaEditionBadge");
const metaEditionChangeBtn = document.getElementById("metaEditionChangeBtn");

// Edition chooser modal.
const editionChooserModal = document.getElementById("editionChooserModal");
const editionChooserConfirmBtn = document.getElementById("editionChooserConfirmBtn");
const editionChooserCancelBtn = document.getElementById("editionChooserCancelBtn");

const EDITIONS = {
  "1687_second": {
    label: "1687 Second Edition",
    blurb: "Second-edition typesetting with marginalia rail; long-s, ligatures, Greek/Latin paleography.",
    hasMarginalia: true,
    stickyFootnotes: false,
  },
  "1847_elrington_todd": {
    label: "Elrington & Todd 1847",
    blurb: "Reprint with no marginalia; footnotes typeset at the bottom of the page; 19th-c. Latin/Greek lithography and ligatures.",
    hasMarginalia: false,
    stickyFootnotes: true,
  },
};
const DEFAULT_EDITION = "1687_second";
const EDITION_LS_KEY = "ussherInEdition";

function editionConfig(key) {
  return EDITIONS[key] || EDITIONS[DEFAULT_EDITION];
}

function currentEdition() {
  const v = String(currentPayload?.edition || "");
  return EDITIONS[v] ? v : DEFAULT_EDITION;
}

const addHeaderBtn = document.getElementById("addHeaderBtn");
const addBodyBtn = document.getElementById("addBodyBtn");
const addFootnoteBtn = document.getElementById("addFootnoteBtn");
const addCatchwordBtn = document.getElementById("addCatchwordBtn");

// Formatting bar.
const superscriptSelectionBtn = document.getElementById("superscriptSelectionBtn");

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

// ---------------------------------------------------------------------------
// Undo stack: destructive ops (remove line, delete footnote) push an entry.
// Cleared on page change. Capped at UNDO_LIMIT.
// ---------------------------------------------------------------------------
const undoStack = [];
const UNDO_LIMIT = 30;

function pushUndo(label, undoFn) {
  undoStack.push({ label, undo: undoFn });
  if (undoStack.length > UNDO_LIMIT) undoStack.shift();
  refreshUndoButton();
}

function clearUndoStack() {
  undoStack.length = 0;
  refreshUndoButton();
}

function performUndo() {
  const entry = undoStack.pop();
  if (!entry) return;
  try {
    entry.undo();
    setStatus(`Undid: ${entry.label}`);
  } catch (err) {
    console.error(err);
    setStatus(`Undo failed: ${err}`, true);
  }
  refreshUndoButton();
}

function refreshUndoButton() {
  if (!undoBtn) return;
  if (undoStack.length === 0) {
    undoBtn.disabled = true;
    undoBtn.title = "Nothing to undo";
    undoBtn.textContent = "Undo";
  } else {
    undoBtn.disabled = false;
    const last = undoStack[undoStack.length - 1];
    undoBtn.title = `Undo: ${last.label} (Ctrl+Z)`;
    undoBtn.textContent = `Undo (${undoStack.length})`;
  }
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

function toSuperscript(value) {
  let output = "";
  for (const ch of String(value || "")) {
    output += SUPERSCRIPT_MAP[ch] || ch;
  }
  return output;
}

function superscriptSelection() {
  if (!activeInput) return;
  const start = activeInput.selectionStart ?? 0;
  const end = activeInput.selectionEnd ?? 0;
  if (start === end) return; // nothing selected
  const value = activeInput.value;
  const replacement = toSuperscript(value.slice(start, end));
  activeInput.value = value.slice(0, start) + replacement + value.slice(end);
  activeInput.selectionStart = start;
  activeInput.selectionEnd = start + replacement.length;
  activeInput.dispatchEvent(new Event("input", { bubbles: true }));
  activeInput.focus();
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
  // Normalise edition: empty/legacy stays empty so loadPage can prompt.
  if (typeof payload.edition !== "string") payload.edition = "";
  if (payload.edition && !EDITIONS[payload.edition]) payload.edition = "";
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

  // Preserve existing char_offset values keyed by footnote_id so re-numbering
  // doesn't wipe out positional anchors set by the user.
  const oldOffsetByFnId = new Map();
  bodyLines.forEach((line) => {
    (line.markers || []).forEach((m) => {
      if (m && m.footnote_id != null && m.char_offset != null) {
        oldOffsetByFnId.set(String(m.footnote_id), m.char_offset);
      }
    });
  });

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
        const preserved = oldOffsetByFnId.has(String(fn.footnote_id))
          ? oldOffsetByFnId.get(String(fn.footnote_id))
          : null;
        bodyLine.markers.push({
          number: idx + 1,
          footnote_id: fn.footnote_id,
          char_offset: preserved,
        });
      }
    }
  });
  currentPayload.footnotes = sorted;
}

function renderBodyTextWithMarkers(line) {
  // Returns HTML: text_gold escaped, with <sup> markers spliced inline at
  // each marker.char_offset. Markers without an offset stack at end-of-line.
  const text = line.text_gold || "";
  const all = (line.markers || []).slice();
  const positioned = all
    .filter((m) => m && m.char_offset != null)
    .sort((a, b) => a.char_offset - b.char_offset);
  const trailing = all.filter((m) => !m || m.char_offset == null);
  const fnByNumber = (n) => (currentPayload?.footnotes || []).find((fn) => fn.marker_number === n);
  const renderBadge = (m) => {
    const fn = fnByNumber(m.number);
    const tip = fn ? escapeHtml((fn.text_gold || "").slice(0, 60)) : `footnote ${m.number}`;
    return `<sup class="marker-badge" data-fn-id="${escapeHtml(m.footnote_id)}" title="${tip}">${m.number}</sup>`;
  };
  let html = "";
  let cursor = 0;
  for (const m of positioned) {
    const offset = Math.max(cursor, Math.min(text.length, m.char_offset));
    html += escapeHtml(text.slice(cursor, offset));
    html += renderBadge(m);
    cursor = offset;
  }
  html += escapeHtml(text.slice(cursor));
  if (trailing.length > 0) {
    html += " " + trailing.map(renderBadge).join(" ");
  }
  return html || "&nbsp;";
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
        <button type="button" class="add-marker-btn" title="Insert footnote marker at the cursor position in this line (or end of line)">+ Footnote here</button>
        <select class="review-status-chip" data-field="review_status">${reviewOpts}</select>
        ${options.showRemove ? '<button type="button" class="line-remove-btn">Remove</button>' : ""}
      </div>
    </div>
    <textarea class="text-gold body-text-gold" data-field="text_gold" data-line-id="${escapeHtml(line.line_id || "")}" rows="1">${safeText}</textarea>
    <div class="body-markers-preview"></div>
    <input class="notes-field" type="text" data-field="notes" placeholder="notes" value="${safeNotes}">
  `;

  bindLineFieldEvents(card, line);
  bindFocusTracking(card);

  const ta = card.querySelector(".body-text-gold");
  const preview = card.querySelector(".body-markers-preview");
  const renderMarkers = () => {
    preview.innerHTML = renderBodyTextWithMarkers(line);
  };
  renderMarkers();
  // Re-render preview live as the user types.
  ta.addEventListener("input", renderMarkers);

  const addBtn = card.querySelector(".add-marker-btn");
  // Don't steal focus on mousedown so the textarea selection survives.
  addBtn.addEventListener("mousedown", (e) => e.preventDefault());
  addBtn.addEventListener("click", () => {
    const offset = (document.activeElement === ta || activeInput === ta)
      ? (ta.selectionStart ?? null)
      : null;
    addFootnoteAnchored(line.line_id, offset);
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
        <button type="button" class="line-remove-btn marginalia-remove-btn" title="Remove this marginalia line">Remove</button>
      </div>
    </div>
    <textarea class="text-gold" data-field="text_gold" rows="1">${safeText}</textarea>
    <div class="line-row">
      <label class="anchor-row">Anchor
        <select class="anchor-select">${anchorOpts}</select>
      </label>
      <button type="button" class="anchor-at-cursor-btn" title="Click in a body line at the desired position, then click here to anchor this marginalia to that position">📍 At body cursor</button>
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
  const atCursorBtn = card.querySelector(".anchor-at-cursor-btn");
  atCursorBtn.addEventListener("mousedown", (e) => e.preventDefault());
  atCursorBtn.addEventListener("click", () => {
    if (!activeInput || !activeInput.classList.contains("body-text-gold")) {
      setStatus("Click inside a body line first, then 📍 At body cursor.", true);
      return;
    }
    const bodyLineId = activeInput.dataset.lineId || "";
    const offset = activeInput.selectionStart ?? null;
    setMarginaliaAnchor(line, bodyLineId, offset);
    renderAll();
  });
  const removeBtn = card.querySelector(".marginalia-remove-btn");
  if (removeBtn) {
    removeBtn.addEventListener("click", () => removeMarginaliaLine(line));
  }
  return card;
}

function removeMarginaliaLine(line) {
  if (!currentPayload) return;
  const marg = currentPayload.regions?.marginalia;
  if (!Array.isArray(marg)) return;
  const idx = marg.findIndex((l) => l.line_id === line.line_id);
  if (idx < 0) return;

  // Snapshot the line and any footnote(s) referencing it so undo can restore both.
  const lineSnapshot = clone(marg[idx]);
  const fns = currentPayload.footnotes || [];
  const fnSnapshots = fns
    .map((fn, i) => ({ index: i, fn: clone(fn) }))
    .filter(({ fn }) =>
      Array.isArray(fn.source_marginalia_line_ids) &&
      fn.source_marginalia_line_ids.includes(line.line_id)
    );

  // Remove the marginalia line.
  marg.splice(idx, 1);

  // Detach from any footnote and drop now-empty marginalia-derived footnotes.
  fns.forEach((fn) => {
    if (Array.isArray(fn.source_marginalia_line_ids)) {
      fn.source_marginalia_line_ids = fn.source_marginalia_line_ids.filter(
        (id) => id !== line.line_id
      );
    }
  });
  for (let i = fns.length - 1; i >= 0; i--) {
    const fn = fns[i];
    if (
      fn.source_region === "marginalia" &&
      (!fn.source_marginalia_line_ids || fn.source_marginalia_line_ids.length === 0) &&
      !fn.text_gold
    ) {
      fns.splice(i, 1);
    }
  }
  renumberFootnotes();

  pushUndo(`Remove marginalia ${lineSnapshot.line_id || idx + 1}`, () => {
    const margList = currentPayload.regions.marginalia || (currentPayload.regions.marginalia = []);
    margList.splice(Math.min(idx, margList.length), 0, lineSnapshot);
    const fnList = currentPayload.footnotes || (currentPayload.footnotes = []);
    fnSnapshots
      .slice()
      .sort((a, b) => a.index - b.index)
      .forEach(({ index, fn }) => {
        const existing = fnList.findIndex((f) => f.footnote_id === fn.footnote_id);
        if (existing >= 0) {
          fnList[existing] = fn;
        } else {
          fnList.splice(Math.min(index, fnList.length), 0, fn);
        }
      });
    renumberFootnotes();
    renderAll();
  });
  renderAll();
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

function setMarginaliaAnchor(marginaliaLine, newBodyLineId, charOffset = null) {
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
  let targetFnId = null;
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
    targetFnId = target.footnote_id;
  }
  renumberFootnotes();
  if (charOffset != null && newBodyLineId && targetFnId) {
    const bodyLine = (currentPayload.regions.body || []).find(
      (l) => String(l.line_id) === String(newBodyLineId)
    );
    const marker = (bodyLine?.markers || []).find(
      (m) => String(m.footnote_id) === String(targetFnId)
    );
    if (marker) marker.char_offset = charOffset;
  }
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
      <button type="button" class="anchor-at-cursor-btn" title="Click in a body line at the desired position, then click here to position this footnote's marker there">📍 At body cursor</button>
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

  const fnAtCursorBtn = card.querySelector(".anchor-at-cursor-btn");
  fnAtCursorBtn.addEventListener("mousedown", (e) => e.preventDefault());
  fnAtCursorBtn.addEventListener("click", () => {
    if (!activeInput || !activeInput.classList.contains("body-text-gold")) {
      setStatus("Click inside a body line first, then 📍 At body cursor.", true);
      return;
    }
    const bodyLineId = activeInput.dataset.lineId || "";
    const offset = activeInput.selectionStart ?? null;
    fn.body_line_id = bodyLineId;
    renumberFootnotes();
    if (bodyLineId && offset != null) {
      const bodyLine = (currentPayload.regions.body || []).find(
        (l) => String(l.line_id) === String(bodyLineId)
      );
      const marker = (bodyLine?.markers || []).find(
        (m) => String(m.footnote_id) === String(fn.footnote_id)
      );
      if (marker) marker.char_offset = offset;
    }
    renderAll();
  });

  card.querySelector(".footnote-remove-btn").addEventListener("click", () => {
    const fns = currentPayload.footnotes || [];
    const idx = fns.indexOf(fn);
    if (idx < 0) return;
    const snapshot = clone(fn);
    const labelNum = snapshot.marker_number || snapshot.footnote_id;
    fns.splice(idx, 1);
    renumberFootnotes();
    pushUndo(`Delete footnote ${labelNum}`, () => {
      const list = currentPayload.footnotes || (currentPayload.footnotes = []);
      list.splice(Math.min(idx, list.length), 0, snapshot);
      renumberFootnotes();
      renderAll();
    });
    renderAll();
  });

  return card;
}

function addFootnoteAnchored(bodyLineId, charOffset = null) {
  if (!currentPayload) return;
  const fns = currentPayload.footnotes || (currentPayload.footnotes = []);
  const newId = nextFootnoteId(currentPayload.page_id, fns);
  fns.push({
    footnote_id: newId,
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
  if (charOffset != null && bodyLineId) {
    const bodyLine = (currentPayload.regions.body || []).find(
      (l) => String(l.line_id) === String(bodyLineId)
    );
    const marker = (bodyLine?.markers || []).find((m) => String(m.footnote_id) === String(newId));
    if (marker) marker.char_offset = charOffset;
  }
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
          const removed = lines[idx];
          const removedClone = clone(removed);
          lines.splice(idx, 1);
          pushUndo(`Remove header line ${removedClone.line_id || idx + 1}`, () => {
            (currentPayload.regions.header || []).splice(idx, 0, removedClone);
            renderHeader();
          });
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
  const cfg = editionConfig(currentEdition());
  const showMarginalia = cfg.hasMarginalia;

  // Group marginalia by anchored body_line_id (resolved via footnotes).
  const bodyToMarginalia = new Map();
  const unanchored = [];
  if (showMarginalia) {
    marginaliaLines.forEach((line) => {
      const anchor = resolveMarginaliaAnchor(line);
      if (anchor) {
        if (!bodyToMarginalia.has(anchor)) bodyToMarginalia.set(anchor, []);
        bodyToMarginalia.get(anchor).push(line);
      } else {
        unanchored.push(line);
      }
    });
  }

  // Unanchored rail at the top.
  if (showMarginalia && unanchored.length > 0) {
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
          const removedClone = clone(line);
          bodyLines.splice(idx, 1);
          renumberFootnotes();
          pushUndo(`Remove body line ${removedClone.line_id || idx + 1}`, () => {
            (currentPayload.regions.body || []).splice(idx, 0, removedClone);
            renumberFootnotes();
            renderAll();
          });
          renderAll();
        },
      })
    );

    const margCell = document.createElement("div");
    margCell.className = "marg-cell";
    if (showMarginalia) {
      const margForLine = bodyToMarginalia.get(line.line_id) || [];
      if (margForLine.length > 0) {
        margCell.appendChild(buildMarginaliaBlock(margForLine));
      }
    }

    row.appendChild(bodyCell);
    row.appendChild(margCell);
    bodyContainer.appendChild(row);
  });
}

function renderFootnotes() {
  const cfg = editionConfig(currentEdition());
  const target = cfg.stickyFootnotes ? stickyFootnoteContainer : footnoteContainer;
  // Clear both so stale cards from the other edition layout don't linger.
  if (footnoteContainer) footnoteContainer.innerHTML = "";
  if (stickyFootnoteContainer) stickyFootnoteContainer.innerHTML = "";
  if (!target) return;
  const fns = currentPayload?.footnotes || [];
  if (fns.length === 0) {
    const empty = document.createElement("div");
    empty.className = "footnote-empty";
    empty.textContent = "No footnotes yet. Use \u201c+ Footnote here\u201d on a body line, or anchor a marginalia.";
    target.appendChild(empty);
    return;
  }
  fns.forEach((fn) => target.appendChild(buildFootnoteCard(fn)));
}

function renderCatchword() {
  catchwordContainer.innerHTML = "";
  const lines = currentPayload?.regions?.catchword || [];
  lines.forEach((line, idx) => {
    catchwordContainer.appendChild(
      buildLineCardSimple(line, "catchword", {
        showRemove: true,
        onRemove: () => {
          const removedClone = clone(lines[idx]);
          lines.splice(idx, 1);
          pushUndo(`Remove catchword ${removedClone.line_id || idx + 1}`, () => {
            (currentPayload.regions.catchword || []).splice(idx, 0, removedClone);
            renderCatchword();
          });
          renderCatchword();
        },
      })
    );
  });
}

function renderAll() {
  if (!currentPayload) return;
  applyEditionLayout();
  renderHeader();
  renderBodyWithMarginalia();
  renderFootnotes();
  renderCatchword();
}

function applyEditionLayout() {
  const cfg = editionConfig(currentEdition());
  // Toggle a class on <body> so CSS can target the layout variant.
  document.body.classList.toggle("layout-1847", !cfg.hasMarginalia);
  document.body.classList.toggle("layout-1687", cfg.hasMarginalia);
  // Show/hide marginalia rail container; the renderer also checks the flag,
  // but hiding the empty container avoids leaving a gap above the body grid.
  if (unanchoredMarginaliaContainer) {
    unanchoredMarginaliaContainer.hidden = !cfg.hasMarginalia;
  }
  // Inline footnote section vs. sticky pane at bottom.
  if (footnoteSection) footnoteSection.hidden = cfg.stickyFootnotes;
  if (stickyFootnoteSection) stickyFootnoteSection.hidden = !cfg.stickyFootnotes;
  // Edition badge in meta-card.
  if (metaEditionBadge) {
    metaEditionBadge.textContent = cfg.label;
    metaEditionBadge.dataset.edition = currentEdition();
  }
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
    if (!currentPayload.edition) {
      const picked = await chooseEditionInteractive({ title: "Select edition for this page" });
      currentPayload.edition = picked || DEFAULT_EDITION;
    }
    bindMeta(currentPayload);
    renderAll();
    clearUndoStack();

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
if (undoBtn) undoBtn.addEventListener("click", performUndo);

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
// Formatting bar (superscript selection)
// ---------------------------------------------------------------------------
if (superscriptSelectionBtn) {
  // Don't steal focus on mousedown so the active input's selection survives.
  superscriptSelectionBtn.addEventListener("mousedown", (e) => e.preventDefault());
  superscriptSelectionBtn.addEventListener("click", superscriptSelection);
}

document.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key.toLowerCase() === "s") {
    event.preventDefault();
    savePage();
    return;
  }
  if (event.ctrlKey && !event.shiftKey && event.key.toLowerCase() === "z") {
    // Don't hijack undo inside textarea/input — let the browser do native
    // text-edit undo. Only intercept when focus is outside an editable.
    const tag = (document.activeElement && document.activeElement.tagName) || "";
    const editable = tag === "INPUT" || tag === "TEXTAREA" || (document.activeElement && document.activeElement.isContentEditable);
    if (!editable) {
      event.preventDefault();
      performUndo();
    }
    return;
  }
  if (event.altKey && event.key.toLowerCase() === "s") {
    event.preventDefault();
    superscriptSelection();
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
const ocrEditionSelect = document.getElementById("ocrEditionSelect");
const ocrEditionBlurb = document.getElementById("ocrEditionBlurb");
const ocrOverwrite = document.getElementById("ocrOverwrite");
const ocrRunBtn = document.getElementById("ocrRunBtn");
const ocrStatus = document.getElementById("ocrStatus");

// Restore last-picked edition from localStorage and wire the blurb.
if (ocrEditionSelect) {
  const saved = (typeof localStorage !== "undefined" && localStorage.getItem(EDITION_LS_KEY)) || "";
  if (EDITIONS[saved]) ocrEditionSelect.value = saved;
  const updateBlurb = () => {
    if (ocrEditionBlurb) {
      ocrEditionBlurb.textContent = editionConfig(ocrEditionSelect.value).blurb;
    }
  };
  updateBlurb();
  ocrEditionSelect.addEventListener("change", () => {
    try { localStorage.setItem(EDITION_LS_KEY, ocrEditionSelect.value); } catch (e) { /* ignore */ }
    updateBlurb();
  });
}

// ---------------------------------------------------------------------------
// Edition chooser modal (shown when loading a page with no edition recorded
// or when the user clicks "Change..." in the meta card).
// ---------------------------------------------------------------------------
let _editionChooserResolver = null;

function chooseEditionInteractive({ title, currentValue } = {}) {
  if (!editionChooserModal) return Promise.resolve(DEFAULT_EDITION);
  const titleEl = document.getElementById("editionChooserTitle");
  if (titleEl && title) titleEl.textContent = title;
  const initial = EDITIONS[currentValue] ? currentValue : DEFAULT_EDITION;
  editionChooserModal.querySelectorAll('input[name="editionChoice"]').forEach((r) => {
    r.checked = r.value === initial;
  });
  editionChooserModal.hidden = false;
  return new Promise((resolve) => {
    _editionChooserResolver = resolve;
  });
}

function closeEditionChooser(value) {
  if (!editionChooserModal) return;
  editionChooserModal.hidden = true;
  const resolve = _editionChooserResolver;
  _editionChooserResolver = null;
  if (resolve) resolve(value);
}

if (editionChooserConfirmBtn) {
  editionChooserConfirmBtn.addEventListener("click", () => {
    const picked = editionChooserModal.querySelector('input[name="editionChoice"]:checked');
    closeEditionChooser(picked ? picked.value : DEFAULT_EDITION);
  });
}
if (editionChooserCancelBtn) {
  editionChooserCancelBtn.addEventListener("click", () => closeEditionChooser(null));
}
if (editionChooserModal) {
  editionChooserModal.addEventListener("click", (event) => {
    if (event.target === editionChooserModal) closeEditionChooser(null);
  });
}

if (metaEditionChangeBtn) {
  metaEditionChangeBtn.addEventListener("click", async () => {
    if (!currentPayload) return;
    const picked = await chooseEditionInteractive({
      title: "Change edition for this page",
      currentValue: currentEdition(),
    });
    if (!picked || picked === currentEdition()) return;
    currentPayload.edition = picked;
    renderAll();
    setStatus(`Edition changed to ${editionConfig(picked).label} (unsaved)`);
  });
}

// "+ Footnote" in the sticky pane uses the same flow as the inline button.
const addStickyFootnoteBtn = document.getElementById("addStickyFootnoteBtn");
if (addStickyFootnoteBtn) {
  addStickyFootnoteBtn.addEventListener("click", () => addFootnoteAnchored(""));
}

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
  // Derive part from the PDF filename (e.g. "..._Part2.pdf" -> part2; default part1).
  const part = /_part2/i.test(String(pdf || "")) ? "part2" : "part1";
  const edition = ocrEditionSelect?.value && EDITIONS[ocrEditionSelect.value]
    ? ocrEditionSelect.value
    : DEFAULT_EDITION;
  if (!pdf) { setOcrStatus("Pick a PDF first.", true); return; }
  if (!Number.isFinite(page) || page < 1) { setOcrStatus("Page must be a positive integer.", true); return; }

  ocrRunBtn.disabled = true;
  setOcrStatus("Starting...");
  try {
    const res = await fetch("/api/ocr/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pdf, page, part, edition, overwrite: !!(forceOverwrite || ocrOverwrite?.checked) }),
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
