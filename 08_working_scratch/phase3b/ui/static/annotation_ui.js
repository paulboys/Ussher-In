let currentPayload = null;
let activeInput = null;
let currentPdfSource = "";
const DEFAULT_REVIEWER = "Paul Boys";

const pageSelect = document.getElementById("pageSelect");
const loadBtn = document.getElementById("loadBtn");
const saveBtn = document.getElementById("saveBtn");
const statusEl = document.getElementById("status");
const pdfFrame = document.getElementById("pdfFrame");

const metaReviewer = document.getElementById("metaReviewer");
const metaAnnotationStatus = document.getElementById("metaAnnotationStatus");
const metaReviewStatus = document.getElementById("metaReviewStatus");
const metaNotes = document.getElementById("metaNotes");

const derivedContainsHeaderPageNumber = document.getElementById("derivedContainsHeaderPageNumber");
const derivedContainsHeaderChapterNumber = document.getElementById("derivedContainsHeaderChapterNumber");
const derivedHeaderParityConsistent = document.getElementById("derivedHeaderParityConsistent");
const derivedHeaderPageNumberSide = document.getElementById("derivedHeaderPageNumberSide");
const derivedHeaderChapterSide = document.getElementById("derivedHeaderChapterSide");

const overrideContainsHeaderPageNumberEnabled = document.getElementById("overrideContainsHeaderPageNumberEnabled");
const overrideContainsHeaderPageNumberValue = document.getElementById("overrideContainsHeaderPageNumberValue");
const overrideContainsHeaderChapterNumberEnabled = document.getElementById("overrideContainsHeaderChapterNumberEnabled");
const overrideContainsHeaderChapterNumberValue = document.getElementById("overrideContainsHeaderChapterNumberValue");
const overrideHeaderParityConsistentEnabled = document.getElementById("overrideHeaderParityConsistentEnabled");
const overrideHeaderParityConsistentValue = document.getElementById("overrideHeaderParityConsistentValue");
const overrideHeaderPageNumberSideEnabled = document.getElementById("overrideHeaderPageNumberSideEnabled");
const overrideHeaderPageNumberSideValue = document.getElementById("overrideHeaderPageNumberSideValue");
const overrideHeaderChapterSideEnabled = document.getElementById("overrideHeaderChapterSideEnabled");
const overrideHeaderChapterSideValue = document.getElementById("overrideHeaderChapterSideValue");

const headerTable = document.getElementById("headerTable");
const bodyTable = document.getElementById("bodyTable");
const footnoteTable = document.getElementById("footnoteTable");
const addHeaderBtn = document.getElementById("addHeaderBtn");
const addFootnoteBtn = document.getElementById("addFootnoteBtn");

const glyphBar = document.getElementById("glyphBar");
const superscriptInput = document.getElementById("superscriptInput");
const insertSuperscriptRawBtn = document.getElementById("insertSuperscriptRawBtn");
const insertSuperscriptBtn = document.getElementById("insertSuperscriptBtn");

const TRACKED_GLYPHS = ["æ", "Æ", "œ", "Œ", "Ↄ", "ↄ", "ↀ", "ↁ", "ↂ", "ᵃ", "ᵇ", "ᶜ", "ᵈ", "ᵉ", "ⁿ"];
const FOOTNOTE_MARKERS = Array.from({ length: 26 }, (_, idx) => String.fromCharCode(97 + idx));
const SUPERSCRIPT_MAP = {
  a: "ᵃ",
  b: "ᵇ",
  c: "ᶜ",
  d: "ᵈ",
  e: "ᵉ",
  f: "ᶠ",
  g: "ᵍ",
  h: "ʰ",
  i: "ᶦ",
  j: "ʲ",
  k: "ᵏ",
  l: "ˡ",
  m: "ᵐ",
  n: "ⁿ",
  o: "ᵒ",
  p: "ᵖ",
  r: "ʳ",
  s: "ˢ",
  t: "ᵗ",
  u: "ᵘ",
  v: "ᵛ",
  w: "ʷ",
  x: "ˣ",
  y: "ʸ",
  z: "ᶻ",
  A: "ᴬ",
  B: "ᴮ",
  D: "ᴰ",
  E: "ᴱ",
  G: "ᴳ",
  H: "ᴴ",
  I: "ᴵ",
  J: "ᴶ",
  K: "ᴷ",
  L: "ᴸ",
  M: "ᴹ",
  N: "ᴺ",
  O: "ᴼ",
  P: "ᴾ",
  R: "ᴿ",
  T: "ᵀ",
  U: "ᵁ",
  V: "ⱽ",
  W: "ᵂ",
  0: "⁰",
  1: "¹",
  2: "²",
  3: "³",
  4: "⁴",
  5: "⁵",
  6: "⁶",
  7: "⁷",
  8: "⁸",
  9: "⁹",
  "+": "⁺",
  "-": "⁻",
  "=": "⁼",
  "(": "⁽",
  ")": "⁾",
};

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

function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function toBoolString(value) {
  return value ? "true" : "false";
}

function normalizeSide(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "left" || normalized === "right") {
    return normalized;
  }
  return "";
}

function normalizeHeaderMeta(meta) {
  meta.derived_contains_header_page_number = Boolean(meta.derived_contains_header_page_number ?? meta.contains_header_page_number);
  meta.derived_contains_header_chapter_number = Boolean(
    meta.derived_contains_header_chapter_number ?? meta.contains_header_chapter_number,
  );
  meta.derived_header_parity_consistent = Boolean(meta.derived_header_parity_consistent ?? meta.header_parity_consistent);
  meta.derived_header_page_number_side = normalizeSide(meta.derived_header_page_number_side ?? meta.header_page_number_side);
  meta.derived_header_chapter_side = normalizeSide(meta.derived_header_chapter_side ?? meta.header_chapter_side);

  meta.override_contains_header_page_number_enabled = Boolean(meta.override_contains_header_page_number_enabled);
  meta.override_contains_header_page_number_value = Boolean(
    meta.override_contains_header_page_number_value ?? meta.contains_header_page_number,
  );
  meta.override_contains_header_chapter_number_enabled = Boolean(meta.override_contains_header_chapter_number_enabled);
  meta.override_contains_header_chapter_number_value = Boolean(
    meta.override_contains_header_chapter_number_value ?? meta.contains_header_chapter_number,
  );
  meta.override_header_parity_consistent_enabled = Boolean(meta.override_header_parity_consistent_enabled);
  meta.override_header_parity_consistent_value = Boolean(
    meta.override_header_parity_consistent_value ?? meta.header_parity_consistent,
  );
  meta.override_header_page_number_side_enabled = Boolean(meta.override_header_page_number_side_enabled);
  meta.override_header_page_number_side_value = normalizeSide(
    meta.override_header_page_number_side_value ?? meta.header_page_number_side,
  );
  meta.override_header_chapter_side_enabled = Boolean(meta.override_header_chapter_side_enabled);
  meta.override_header_chapter_side_value = normalizeSide(
    meta.override_header_chapter_side_value ?? meta.header_chapter_side,
  );
}

function refreshHeaderIndicatorDisplay(meta) {
  if (!meta) return;
  if (derivedContainsHeaderPageNumber) {
    derivedContainsHeaderPageNumber.value = toBoolString(Boolean(meta.derived_contains_header_page_number));
  }
  if (derivedContainsHeaderChapterNumber) {
    derivedContainsHeaderChapterNumber.value = toBoolString(Boolean(meta.derived_contains_header_chapter_number));
  }
  if (derivedHeaderParityConsistent) {
    derivedHeaderParityConsistent.value = toBoolString(Boolean(meta.derived_header_parity_consistent));
  }
  if (derivedHeaderPageNumberSide) {
    derivedHeaderPageNumberSide.value = normalizeSide(meta.derived_header_page_number_side);
  }
  if (derivedHeaderChapterSide) {
    derivedHeaderChapterSide.value = normalizeSide(meta.derived_header_chapter_side);
  }
}

function bindHeaderOverrideControls(meta) {
  if (!meta) return;

  const syncState = () => {
    overrideContainsHeaderPageNumberValue.disabled = !overrideContainsHeaderPageNumberEnabled.checked;
    overrideContainsHeaderChapterNumberValue.disabled = !overrideContainsHeaderChapterNumberEnabled.checked;
    overrideHeaderParityConsistentValue.disabled = !overrideHeaderParityConsistentEnabled.checked;
    overrideHeaderPageNumberSideValue.disabled = !overrideHeaderPageNumberSideEnabled.checked;
    overrideHeaderChapterSideValue.disabled = !overrideHeaderChapterSideEnabled.checked;
  };

  overrideContainsHeaderPageNumberEnabled.checked = Boolean(meta.override_contains_header_page_number_enabled);
  overrideContainsHeaderPageNumberValue.checked = Boolean(meta.override_contains_header_page_number_value);
  overrideContainsHeaderChapterNumberEnabled.checked = Boolean(meta.override_contains_header_chapter_number_enabled);
  overrideContainsHeaderChapterNumberValue.checked = Boolean(meta.override_contains_header_chapter_number_value);
  overrideHeaderParityConsistentEnabled.checked = Boolean(meta.override_header_parity_consistent_enabled);
  overrideHeaderParityConsistentValue.checked = Boolean(meta.override_header_parity_consistent_value);
  overrideHeaderPageNumberSideEnabled.checked = Boolean(meta.override_header_page_number_side_enabled);
  overrideHeaderPageNumberSideValue.value = normalizeSide(meta.override_header_page_number_side_value);
  overrideHeaderChapterSideEnabled.checked = Boolean(meta.override_header_chapter_side_enabled);
  overrideHeaderChapterSideValue.value = normalizeSide(meta.override_header_chapter_side_value);

  syncState();

  overrideContainsHeaderPageNumberEnabled.onchange = () => {
    meta.override_contains_header_page_number_enabled = overrideContainsHeaderPageNumberEnabled.checked;
    syncState();
  };
  overrideContainsHeaderPageNumberValue.onchange = () => {
    meta.override_contains_header_page_number_value = overrideContainsHeaderPageNumberValue.checked;
  };

  overrideContainsHeaderChapterNumberEnabled.onchange = () => {
    meta.override_contains_header_chapter_number_enabled = overrideContainsHeaderChapterNumberEnabled.checked;
    syncState();
  };
  overrideContainsHeaderChapterNumberValue.onchange = () => {
    meta.override_contains_header_chapter_number_value = overrideContainsHeaderChapterNumberValue.checked;
  };

  overrideHeaderParityConsistentEnabled.onchange = () => {
    meta.override_header_parity_consistent_enabled = overrideHeaderParityConsistentEnabled.checked;
    syncState();
  };
  overrideHeaderParityConsistentValue.onchange = () => {
    meta.override_header_parity_consistent_value = overrideHeaderParityConsistentValue.checked;
  };

  overrideHeaderPageNumberSideEnabled.onchange = () => {
    meta.override_header_page_number_side_enabled = overrideHeaderPageNumberSideEnabled.checked;
    syncState();
  };
  overrideHeaderPageNumberSideValue.onchange = () => {
    meta.override_header_page_number_side_value = normalizeSide(overrideHeaderPageNumberSideValue.value);
  };

  overrideHeaderChapterSideEnabled.onchange = () => {
    meta.override_header_chapter_side_enabled = overrideHeaderChapterSideEnabled.checked;
    syncState();
  };
  overrideHeaderChapterSideValue.onchange = () => {
    meta.override_header_chapter_side_value = normalizeSide(overrideHeaderChapterSideValue.value);
  };
}

function bindFocusTracking(container) {
  container.querySelectorAll("input, textarea, select").forEach((el) => {
    el.addEventListener("focus", () => {
      if (el.classList.contains("text-gold") || el.classList.contains("marker-field") || el.classList.contains("notes-field")) {
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
  const text = String(value || "");
  let output = "";
  for (const ch of text) {
    output += SUPERSCRIPT_MAP[ch] || ch;
  }
  return output;
}

function insertCustomSuperscript(rawMode = false) {
  if (!superscriptInput) return;
  const value = superscriptInput.value || "";
  if (!value.trim()) {
    return;
  }
  const text = rawMode ? value : toSuperscript(value);
  insertGlyph(text);
}

function pad4(number) {
  return String(number).padStart(4, "0");
}

function makeLineId(pageId, regionName, ordinal) {
  return `${pageId}_${regionName}_l${pad4(ordinal)}`;
}

function createEmptyLine(pageId, regionName, ordinal) {
  return {
    page_id: pageId,
    region: regionName,
    line_id: makeLineId(pageId, regionName, ordinal),
    text_gold: "",
    contains_ae_target: false,
    contains_marker: false,
    marker_id: "",
    marker_link_target: "",
    uncertain_ae: false,
    marker_uncertain: false,
    reviewer: DEFAULT_REVIEWER,
    review_status: "draft",
    notes: "",
    glyph_counts: {},
  };
}

function hasAeTarget(text) {
  const value = String(text || "");
  return /(ae|æ)/i.test(value);
}

function computeGlyphCounts(text) {
  const value = String(text || "");
  const counts = {};
  TRACKED_GLYPHS.forEach((glyph) => {
    let count = 0;
    for (const ch of value) {
      if (ch === glyph) {
        count += 1;
      }
    }
    if (count > 0) {
      counts[glyph] = count;
    }
  });
  return counts;
}

function formatGlyphCounts(counts) {
  const entries = Object.entries(counts || {});
  if (!entries.length) return "none";
  return entries.map(([glyph, count]) => `${glyph}:${count}`).join(", ");
}

function normalizeMarkerIdForRegion(markerId, regionName) {
  const value = String(markerId || "").trim();
  if (regionName !== "footnote") {
    return value;
  }
  if (!value) {
    return "";
  }
  const normalized = value.toLowerCase();
  return FOOTNOTE_MARKERS.includes(normalized) ? normalized : "";
}

function refreshDerivedLineFields(line, card = null) {
  line.contains_ae_target = hasAeTarget(line.text_gold || "");
  line.glyph_counts = computeGlyphCounts(line.text_gold || "");

  if (!card) return;

  const aeCheckbox = card.querySelector('input[data-field="contains_ae_target"]');
  if (aeCheckbox) {
    aeCheckbox.checked = Boolean(line.contains_ae_target);
  }

  const glyphSummaryEl = card.querySelector(".glyph-summary");
  if (glyphSummaryEl) {
    glyphSummaryEl.value = formatGlyphCounts(line.glyph_counts);
  }
}

function applyDefaultReviewer(payload) {
  if (!payload) return;
  payload.meta = payload.meta || {};
  payload.meta.reviewer = DEFAULT_REVIEWER;
  payload.regions = payload.regions || {};
  ["header", "body", "footnote"].forEach((regionName) => {
    const lines = payload.regions[regionName];
    if (!Array.isArray(lines)) return;
    lines.forEach((line) => {
      if (line && typeof line === "object") {
        line.reviewer = DEFAULT_REVIEWER;
      }
    });
  });
}

function getNextOrdinal(regionName) {
  const pageId = currentPayload?.page_id || pageSelect.value;
  const lines = currentPayload?.regions?.[regionName] || [];
  let maxOrdinal = 0;
  const pattern = new RegExp(`^${pageId}_${regionName}_l(\\d{4})$`);
  lines.forEach((line, idx) => {
    const candidate = String(line?.line_id || "");
    const match = candidate.match(pattern);
    if (match) {
      maxOrdinal = Math.max(maxOrdinal, Number(match[1]));
    } else {
      maxOrdinal = Math.max(maxOrdinal, idx + 1);
    }
  });
  return maxOrdinal + 1;
}

function normalizeRegionLines(regionName) {
  if (!currentPayload) return;
  const pageId = currentPayload.page_id || pageSelect.value;
  currentPayload.regions = currentPayload.regions || {};
  const regionValue = currentPayload.regions[regionName];
  if (!Array.isArray(regionValue)) {
    currentPayload.regions[regionName] = [];
    return;
  }

  currentPayload.regions[regionName] = regionValue.map((line, idx) => {
    if (typeof line === "string") {
      const newLine = createEmptyLine(pageId, regionName, idx + 1);
      newLine.text_gold = line;
      return newLine;
    }

    if (!line || typeof line !== "object") {
      return createEmptyLine(pageId, regionName, idx + 1);
    }

    return {
      page_id: line.page_id || pageId,
      region: line.region || regionName,
      line_id: line.line_id || makeLineId(pageId, regionName, idx + 1),
      text_gold: line.text_gold || "",
      contains_ae_target: hasAeTarget(line.text_gold || ""),
      contains_marker: Boolean(line.contains_marker),
      marker_id: normalizeMarkerIdForRegion(line.marker_id || "", regionName),
      marker_link_target: line.marker_link_target || "",
      uncertain_ae: Boolean(line.uncertain_ae),
      marker_uncertain: Boolean(line.marker_uncertain),
      reviewer: DEFAULT_REVIEWER,
      review_status: line.review_status || "draft",
      notes: line.notes || "",
      glyph_counts: computeGlyphCounts(line.text_gold || ""),
    };
  });
}

function renumberRegionLines(regionName, removedLineIds = []) {
  if (!currentPayload) return;
  const pageId = currentPayload.page_id || pageSelect.value;
  const regionLines = currentPayload.regions?.[regionName] || [];
  const idMap = new Map();

  regionLines.forEach((line, idx) => {
    const oldId = String(line.line_id || "");
    const newId = makeLineId(pageId, regionName, idx + 1);
    line.page_id = pageId;
    line.region = regionName;
    line.line_id = newId;
    if (oldId) {
      idMap.set(oldId, newId);
    }
  });

  if (regionName === "footnote") {
    const bodyLines = currentPayload.regions?.body || [];
    bodyLines.forEach((line) => {
      const target = String(line.marker_link_target || "");
      if (!target) return;
      if (idMap.has(target)) {
        line.marker_link_target = idMap.get(target);
      } else if (removedLineIds.includes(target)) {
        line.marker_link_target = "";
      }
    });
  }
}

function buildLineCard(line, idx, regionName, options = {}) {
  refreshDerivedLineFields(line);

  const card = document.createElement("div");
  card.className = "line-card";
  const safeLineId = escapeHtml(line.line_id || `${regionName}_${idx + 1}`);
  const safeRegionName = escapeHtml(regionName);
  const safeTextGold = escapeHtml(line.text_gold || "");
  const safeMarkerId = escapeHtml(line.marker_id || "");
  const safeMarkerTarget = escapeHtml(line.marker_link_target || "");
  const safeReviewer = escapeHtml(line.reviewer || "");
  const safeNotes = escapeHtml(line.notes || "");
  const safeGlyphSummary = escapeHtml(formatGlyphCounts(line.glyph_counts));
  const markerIdControl = regionName === "footnote"
    ? `<label>marker_id
        <select class="marker-field" data-field="marker_id">
          <option value=""></option>
          ${FOOTNOTE_MARKERS.map((marker) => `<option value="${marker}" ${line.marker_id === marker ? "selected" : ""}>${marker}</option>`).join("")}
        </select>
      </label>`
    : `<label>marker_id <input class="marker-field" type="text" data-field="marker_id" value="${safeMarkerId}"></label>`;

  card.innerHTML = `
    <div class="line-head">
      <span>${safeLineId}</span>
      <div>
        <span>${safeRegionName}</span>
        ${options.showRemove ? '<button type="button" class="line-remove-btn">Remove</button>' : ""}
      </div>
    </div>
    <label>text_gold
      <textarea class="text-gold" data-field="text_gold" rows="2">${safeTextGold}</textarea>
    </label>
    <div class="line-grid">
      <label class="inline-check"><input type="checkbox" data-field="contains_ae_target" ${line.contains_ae_target ? "checked" : ""} disabled> contains_ae_target (auto)</label>
      <label class="inline-check"><input type="checkbox" data-field="contains_marker" ${line.contains_marker ? "checked" : ""}> contains_marker</label>
      <label class="inline-check"><input type="checkbox" data-field="uncertain_ae" ${line.uncertain_ae ? "checked" : ""}> uncertain_ae</label>
      <label class="inline-check"><input type="checkbox" data-field="marker_uncertain" ${line.marker_uncertain ? "checked" : ""}> marker_uncertain</label>
      <label>glyphs_auto <input class="glyph-summary" type="text" value="${safeGlyphSummary}" readonly></label>
      ${markerIdControl}
      <label>marker_link_target <input class="marker-field" type="text" data-field="marker_link_target" value="${safeMarkerTarget}"></label>
      <label>reviewer <input type="text" data-field="reviewer" value="${safeReviewer}" readonly></label>
      <label>review_status
        <select data-field="review_status">
          <option value="draft" ${line.review_status === "draft" ? "selected" : ""}>draft</option>
          <option value="reviewed" ${line.review_status === "reviewed" ? "selected" : ""}>reviewed</option>
          <option value="locked" ${line.review_status === "locked" ? "selected" : ""}>locked</option>
        </select>
      </label>
    </div>
    <label>notes
      <input class="notes-field" type="text" data-field="notes" value="${safeNotes}">
    </label>
  `;

  card.querySelectorAll("[data-field]").forEach((el) => {
    el.addEventListener("input", () => {
      const field = el.dataset.field;
      if (el.type === "checkbox") {
        line[field] = el.checked;
      } else {
        line[field] = el.value;
      }
      if (field === "marker_id") {
        line.marker_id = normalizeMarkerIdForRegion(line.marker_id, regionName);
        if (el.value !== line.marker_id) {
          el.value = line.marker_id;
        }
      }
      if (field === "text_gold") {
        refreshDerivedLineFields(line, card);
      }
    });
    el.addEventListener("change", () => {
      const field = el.dataset.field;
      if (el.type === "checkbox") {
        line[field] = el.checked;
      } else {
        line[field] = el.value;
      }
      if (field === "marker_id") {
        line.marker_id = normalizeMarkerIdForRegion(line.marker_id, regionName);
        if (el.value !== line.marker_id) {
          el.value = line.marker_id;
        }
      }
      if (field === "text_gold") {
        refreshDerivedLineFields(line, card);
      }
    });
  });

  bindFocusTracking(card);

  if (options.showRemove) {
    const removeBtn = card.querySelector(".line-remove-btn");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        options.onRemove?.(idx);
      });
    }
  }

  return card;
}

function renderRegion(container, regionName, lines, options = {}) {
  container.innerHTML = "";
  (lines || []).forEach((line, idx) => {
    container.appendChild(buildLineCard(line, idx, regionName, options));
  });
}

function renderAllRegions() {
  if (!currentPayload) return;

  renderRegion(headerTable, "header", currentPayload.regions?.header || [], {
    showRemove: true,
    onRemove: (idx) => {
      currentPayload.regions.header.splice(idx, 1);
      renumberRegionLines("header");
      renderAllRegions();
    },
  });

  renderRegion(bodyTable, "body", currentPayload.regions?.body || [], {
    showRemove: true,
    onRemove: (idx) => {
      currentPayload.regions.body.splice(idx, 1);
      renumberRegionLines("body");
      renderAllRegions();
    },
  });

  renderRegion(footnoteTable, "footnote", currentPayload.regions?.footnote || [], {
    showRemove: true,
    onRemove: (idx) => {
      const removed = currentPayload.regions.footnote[idx];
      const removedId = removed?.line_id ? [String(removed.line_id)] : [];
      currentPayload.regions.footnote.splice(idx, 1);
      renumberRegionLines("footnote", removedId);
      renderAllRegions();
    },
  });
}

function bindMeta(meta) {
  meta.reviewer = DEFAULT_REVIEWER;
  normalizeHeaderMeta(meta);
  metaReviewer.value = DEFAULT_REVIEWER;
  metaAnnotationStatus.value = meta.annotation_status || "draft";
  metaReviewStatus.value = meta.review_status || "draft";
  metaNotes.value = meta.notes || "";
  refreshHeaderIndicatorDisplay(meta);
  bindHeaderOverrideControls(meta);

  metaReviewer.oninput = () => {
    meta.reviewer = DEFAULT_REVIEWER;
    metaReviewer.value = DEFAULT_REVIEWER;
  };
  metaAnnotationStatus.oninput = () => { meta.annotation_status = metaAnnotationStatus.value; };
  metaReviewStatus.onchange = () => { meta.review_status = metaReviewStatus.value; };
  metaNotes.oninput = () => { meta.notes = metaNotes.value; };
}

async function loadPage(pageId) {
  try {
    setStatus("Loading...");
    const res = await fetch(`/api/page/${pageId}`);
    if (!res.ok) {
      throw new Error(`Load failed: ${res.status}`);
    }
    currentPayload = await res.json();
    currentPayload.regions = currentPayload.regions || {};
    normalizeRegionLines("header");
    normalizeRegionLines("body");
    normalizeRegionLines("footnote");
    applyDefaultReviewer(currentPayload);
    bindMeta(currentPayload.meta || (currentPayload.meta = {}));
    renderAllRegions();

    const parsedPageNum = Number(currentPayload.page_num);
    const fallbackPageNum = Number(String(pageId || "").replace(/^p/, ""));
    const pdfPageNum = Number.isFinite(parsedPageNum) && parsedPageNum > 0
      ? parsedPageNum
      : (Number.isFinite(fallbackPageNum) && fallbackPageNum > 0 ? fallbackPageNum : 1);

    const sourcePdfKey = String(currentPayload.source_pdf || "");
    if (!pdfFrame.src || currentPdfSource !== sourcePdfKey) {
      // New source PDF: load dedicated PDF.js viewer at target page.
      currentPdfSource = sourcePdfKey;
      pdfFrame.src = `/pdfjs/${pageId}?page=${pdfPageNum}#page=${pdfPageNum}`;
    } else {
      // Same source PDF: keep viewer loaded and instruct it to switch pages.
      pdfFrame.contentWindow?.postMessage({ type: "setPage", page: pdfPageNum }, window.location.origin);
    }
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
      normalizeHeaderMeta(currentPayload.meta);
      refreshHeaderIndicatorDisplay(currentPayload.meta);
      bindHeaderOverrideControls(currentPayload.meta);
    }
    setStatus(`Saved ${pageId}`);
  } catch (err) {
    setStatus(String(err), true);
  }
}

loadBtn.addEventListener("click", () => loadPage(pageSelect.value));
saveBtn.addEventListener("click", savePage);

addHeaderBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  const nextOrdinal = getNextOrdinal("header");
  currentPayload.regions.header.push(createEmptyLine(currentPayload.page_id || pageSelect.value, "header", nextOrdinal));
  renumberRegionLines("header");
  renderAllRegions();
});

addFootnoteBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  const nextOrdinal = getNextOrdinal("footnote");
  currentPayload.regions.footnote.push(createEmptyLine(currentPayload.page_id || pageSelect.value, "footnote", nextOrdinal));
  renumberRegionLines("footnote");
  renderAllRegions();
});

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

  if (event.key === "e" && !event.shiftKey) {
    event.preventDefault();
    insertGlyph("æ");
  } else if (event.key === "E" || (event.key === "e" && event.shiftKey)) {
    event.preventDefault();
    insertGlyph("Æ");
  } else if (event.key === "o" && !event.shiftKey) {
    event.preventDefault();
    insertGlyph("œ");
  } else if (event.key === "O" || (event.key === "o" && event.shiftKey)) {
    event.preventDefault();
    insertGlyph("Œ");
  } else if (event.key === "6") {
    event.preventDefault();
    insertGlyph("Ↄ");
  } else if (event.key === "7") {
    event.preventDefault();
    insertGlyph("ↄ");
  } else if (event.key.toLowerCase() === "d") {
    event.preventDefault();
    insertGlyph("ᵈ");
  } else if (event.key.toLowerCase() === "n") {
    event.preventDefault();
    insertGlyph("ⁿ");
  }
});

if (window.__PAGES__ && window.__PAGES__.length > 0) {
  pageSelect.value = window.__PAGES__[0];
  loadPage(window.__PAGES__[0]);
}
