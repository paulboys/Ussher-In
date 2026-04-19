let currentPayload = null;
let activeInput = null;

const pageSelect = document.getElementById("pageSelect");
const loadBtn = document.getElementById("loadBtn");
const saveBtn = document.getElementById("saveBtn");
const statusEl = document.getElementById("status");
const pdfFrame = document.getElementById("pdfFrame");

const metaReviewer = document.getElementById("metaReviewer");
const metaAnnotationStatus = document.getElementById("metaAnnotationStatus");
const metaReviewStatus = document.getElementById("metaReviewStatus");
const metaNotes = document.getElementById("metaNotes");

const bodyTable = document.getElementById("bodyTable");
const footnoteTable = document.getElementById("footnoteTable");

const glyphBar = document.getElementById("glyphBar");

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

function buildLineCard(line, idx, regionName) {
  const card = document.createElement("div");
  card.className = "line-card";
  const safeLineId = escapeHtml(line.line_id || `${regionName}_${idx + 1}`);
  const safeRegionName = escapeHtml(regionName);
  const safeTextGold = escapeHtml(line.text_gold || "");
  const safeMarkerId = escapeHtml(line.marker_id || "");
  const safeMarkerTarget = escapeHtml(line.marker_link_target || "");
  const safeReviewer = escapeHtml(line.reviewer || "");
  const safeNotes = escapeHtml(line.notes || "");
  card.innerHTML = `
    <div class="line-head">
      <span>${safeLineId}</span>
      <span>${safeRegionName}</span>
    </div>
    <label>text_gold
      <textarea class="text-gold" data-field="text_gold" rows="2">${safeTextGold}</textarea>
    </label>
    <div class="line-grid">
      <label class="inline-check"><input type="checkbox" data-field="contains_ae_target" ${line.contains_ae_target ? "checked" : ""}> contains_ae_target</label>
      <label class="inline-check"><input type="checkbox" data-field="contains_marker" ${line.contains_marker ? "checked" : ""}> contains_marker</label>
      <label class="inline-check"><input type="checkbox" data-field="uncertain_ae" ${line.uncertain_ae ? "checked" : ""}> uncertain_ae</label>
      <label class="inline-check"><input type="checkbox" data-field="marker_uncertain" ${line.marker_uncertain ? "checked" : ""}> marker_uncertain</label>
      <label>marker_id <input class="marker-field" type="text" data-field="marker_id" value="${safeMarkerId}"></label>
      <label>marker_link_target <input class="marker-field" type="text" data-field="marker_link_target" value="${safeMarkerTarget}"></label>
      <label>reviewer <input type="text" data-field="reviewer" value="${safeReviewer}"></label>
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
    });
    el.addEventListener("change", () => {
      const field = el.dataset.field;
      if (el.type === "checkbox") {
        line[field] = el.checked;
      } else {
        line[field] = el.value;
      }
    });
  });

  bindFocusTracking(card);
  return card;
}

function renderRegion(container, regionName, lines) {
  container.innerHTML = "";
  (lines || []).forEach((line, idx) => {
    container.appendChild(buildLineCard(line, idx, regionName));
  });
}

function bindMeta(meta) {
  metaReviewer.value = meta.reviewer || "";
  metaAnnotationStatus.value = meta.annotation_status || "draft";
  metaReviewStatus.value = meta.review_status || "draft";
  metaNotes.value = meta.notes || "";

  metaReviewer.oninput = () => { meta.reviewer = metaReviewer.value; };
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
    bindMeta(currentPayload.meta || (currentPayload.meta = {}));
    renderRegion(bodyTable, "body", currentPayload.regions?.body || []);
    renderRegion(footnoteTable, "footnote", currentPayload.regions?.footnote || []);
    pdfFrame.src = `/pdf/${pageId}`;
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
    setStatus(`Saved ${pageId}`);
  } catch (err) {
    setStatus(String(err), true);
  }
}

loadBtn.addEventListener("click", () => loadPage(pageSelect.value));
saveBtn.addEventListener("click", savePage);

glyphBar.querySelectorAll("button[data-glyph]").forEach((btn) => {
  btn.addEventListener("click", () => insertGlyph(btn.dataset.glyph));
});

document.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key.toLowerCase() === "s") {
    event.preventDefault();
    savePage();
    return;
  }

  if (!event.altKey) return;

  if (event.key === "e" && !event.shiftKey) {
    event.preventDefault();
    insertGlyph("??");
  } else if (event.key === "E" || (event.key === "e" && event.shiftKey)) {
    event.preventDefault();
    insertGlyph("??");
  } else if (event.key === "6") {
    event.preventDefault();
    insertGlyph("???");
  } else if (event.key === "7") {
    event.preventDefault();
    insertGlyph("???");
  } else if (event.key.toLowerCase() === "d") {
    event.preventDefault();
    insertGlyph("???");
  } else if (event.key.toLowerCase() === "n") {
    event.preventDefault();
    insertGlyph("???");
  }
});

if (window.__PAGES__ && window.__PAGES__.length > 0) {
  pageSelect.value = window.__PAGES__[0];
  loadPage(window.__PAGES__[0]);
}
