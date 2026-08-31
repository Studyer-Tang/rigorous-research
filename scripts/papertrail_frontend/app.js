"use strict";
const demo = JSON.parse(document.getElementById("demo-data").textContent);
const appCss = document.getElementById("app-css").textContent.trim();
const reportInput = document.getElementById("report-input"),
  manifestInput = document.getElementById("manifest-input"),
  preview = document.getElementById("preview"),
  errorBox = document.getElementById("error");
const jsonButton = document.getElementById("json-button"),
  htmlButton = document.getElementById("html-button"),
  languageSelect = document.getElementById("language-select");
const pdfFile = document.getElementById("pdf-file"),
  pdfViewer = document.getElementById("pdf-viewer"),
  pdfStatus = document.getElementById("pdf-status"),
  pdfCanvas = document.getElementById("pdf-canvas"),
  pdfText = document.getElementById("pdf-text"),
  pdfPassages = document.getElementById("pdf-passages"),
  selectedQuote = document.getElementById("selected-quote"),
  attachSelection = document.getElementById("attach-selection"),
  pdfPageLabel = document.getElementById("pdf-page-label"),
  pdfPrev = document.getElementById("pdf-prev"),
  pdfNext = document.getElementById("pdf-next"),
  pdfOcr = document.getElementById("pdf-ocr"),
  anchorClaim = document.getElementById("anchor-claim"),
  anchorSource = document.getElementById("anchor-source");
const PDF_JS_URL =
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.min.mjs",
  PDF_WORKER_URL =
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs",
  TESSERACT_URL =
    "https://cdn.jsdelivr.net/npm/tesseract.js@6.0.1/dist/tesseract.min.js",
  MAX_PDF_BYTES = 50 * 1024 * 1024;
const { messages, verdictLabels, checkLabels, checklistLabels, detailZh } =
  window.PaperTrailLocale;
const verdicts = new Set(Object.keys(verdictLabels.en)),
  reviewMethods = new Set(["human", "ai_assisted", "automated", "unknown"]),
  claimSections = new Set([
    "claims",
    "key claims",
    "conclusions",
    "主要结论",
    "核心结论",
    "结论",
  ]),
  highRisk = new Set(["retracted", "withdrawn", "expression_of_concern"]);
let currentAudit = null,
  language = "en",
  pdfLibrary = null,
  pdfDocument = null,
  pdfPageNumber = 1,
  pdfFileHash = "",
  pdfExtractionKind = "pdf_text",
  pendingPdfSelection = null;
const t = (key) => messages[language][key] || messages.en[key] || key;
const verdictText = (value) => verdictLabels[language][value] || value;
const checkText = (value) => checkLabels[language][value] || value;
function localizeDetail(value) {
  if (language === "en") return value;
  if (detailZh[value]) return detailZh[value];
  return value
    .replace(
      /^Unresolved source IDs: (.+)$/,
      (_, ids) => `未解析的来源 ID：${ids}`,
    )
    .replace(
      /^High-risk publication status: (.+)\.$/,
      (_, ids) => `高风险发表状态：${ids}。`,
    )
    .replace(
      /^Version conflicts require review: (.+)\.$/,
      (_, ids) => `需要审阅的版本冲突：${ids}。`,
    )
    .replace(
      /^Conflicting reviewer verdicts: (.+)\.$/,
      (_, ids) => `存在冲突的审阅结论：${ids}。`,
    );
}
const text = (value) => (value == null ? "" : String(value).trim());
const node = (tag, className, content) => {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (content !== undefined) item.textContent = content;
  return item;
};
const add = (parent, ...children) => {
  for (const child of children) parent.append(child);
  return parent;
};
const safeUrl = (value) => {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
};
const citationIds = (value) => {
  const found = [];
  for (const match of value.matchAll(/\[@([^\]]+)\]/g))
    for (const part of match[1].split(/[;,]/)) {
      const key = part.trim().replace(/^@/, "").trim();
      if (key && !found.includes(key)) found.push(key);
    }
  return found;
};
const cleanStatement = (value) =>
  value
    .replace(/\[@([^\]]+)\]/g, "")
    .replace(/\s+/g, " ")
    .trim();
function draftClaims() {
  setError();
  if (
    /^#{1,6}\s+(?:claims|key claims|conclusions|结论|主要结论|核心结论)\s*$/im.test(
      reportInput.value,
    )
  ) {
    setError(t("draft_exists"));
    return;
  }
  const prose = reportInput.value
      .split(/\r?\n/)
      .filter((line) => !/^\s*(?:#{1,6}\s|```|>)/.test(line))
      .join(" "),
    sentences = prose.replace(/\s+/g, " ").split(/(?<=[.!?。！？])\s+/),
    signals =
      /(?:\d|%|percent|increase|decrease|associated|significant|demonstrat|suggest|show|find|表明|显示|增加|减少|显著|相关)/i,
    candidates = sentences
      .map(text)
      .filter(
        (value) =>
          value.length >= 30 && value.length <= 500 && signals.test(value),
      )
      .slice(0, 20);
  if (!candidates.length) {
    setError(t("draft_none"));
    return;
  }
  reportInput.value = `${reportInput.value.trim()}\n\n## ${language === "zh" ? "结论" : "Claims"}\n\n${candidates.map((value, index) => `- [C${String(index + 1).padStart(3, "0")}] ${value}`).join("\n")}\n`;
  refreshAnchorTargets();
  setError(t("draft_added"));
}
const normalizeDoi = (value) => {
  const doi = value
    .trim()
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "")
    .replace(/^doi:\s*/i, "");
  if (!/^10\.\d{4,9}\/\S+$/.test(doi)) throw new Error(t("invalid_doi"));
  return doi;
};
async function addDoiSource() {
  setError();
  const button = document.getElementById("doi-button");
  button.disabled = true;
  try {
    const doi = normalizeDoi(document.getElementById("doi-input").value),
      response = await fetch(
        `https://api.crossref.org/works/${encodeURIComponent(doi)}`,
        { headers: { Accept: "application/json" } },
      );
    if (!response.ok)
      throw new Error(`${t("crossref_failed")} (HTTP ${response.status})`);
    const message = (await response.json()).message || {},
      updates = Array.isArray(message["update-to"]) ? message["update-to"] : [],
      types = new Set(updates.map((item) => text(item.type).toLowerCase())),
      status = types.has("retraction")
        ? "retracted"
        : types.has("withdrawal")
          ? "withdrawn"
          : types.size
            ? "corrected"
            : "active",
      authors = (message.author || [])
        .map((author) => `${text(author.given)} ${text(author.family)}`.trim())
        .filter(Boolean),
      dates =
        message["published-print"] ||
        message["published-online"] ||
        message.issued ||
        {},
      parts = dates["date-parts"] || [],
      source = {
        id: doi
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-|-$/g, ""),
        title: (message.title || [])[0] || doi,
        authors,
        year: parts[0]?.[0] || null,
        doi,
        url: `https://doi.org/${doi}`,
        publication_status: status,
        integrity_checked_at: new Date().toISOString().slice(0, 10),
        integrity_url: `https://api.crossref.org/works/${encodeURIComponent(doi)}`,
        version: "version of record",
        version_url: message.URL || `https://doi.org/${doi}`,
        version_conflict: null,
        version_notes: `Crossref update metadata: ${types.size ? [...types].sort().join(", ") : "none recorded"}`,
        data_availability: "unknown",
        code_availability: "unknown",
      },
      manifest = JSON.parse(manifestInput.value);
    if (!Array.isArray(manifest.sources) || !Array.isArray(manifest.evidence))
      throw new Error(t("manifest_shape"));
    const index = manifest.sources.findIndex((item) => item.id === source.id);
    if (index >= 0) manifest.sources[index] = source;
    else manifest.sources.push(source);
    manifestInput.value = JSON.stringify(manifest, null, 2);
    document.getElementById("doi-input").value = "";
    refreshAnchorTargets();
  } catch (exc) {
    setError(exc instanceof Error ? exc.message : String(exc));
  } finally {
    button.disabled = false;
  }
}
function parseReport(markdown) {
  const lines = markdown.split(/\r?\n/),
    claims = [];
  let title = "Untitled report",
    inClaims = false;
  lines.forEach((line, index) => {
    const heading = line.match(/^(#{1,6})\s+(.+?)\s*$/);
    if (heading) {
      const headingText = heading[2].replace(/#+$/, "").trim();
      if (heading[1].length === 1 && title === "Untitled report")
        title = headingText;
      inClaims = claimSections.has(headingText.toLowerCase());
      return;
    }
    if (!inClaims) return;
    const listed = line.match(/^\s*(?:[-+*]|\d+[.)])\s+(.+?)\s*$/);
    if (!listed) return;
    const explicit = listed[1].match(/^\[(C[A-Za-z0-9_-]+)]\s*(.+)$/i),
      body = explicit ? explicit[2] : listed[1],
      statement = cleanStatement(body);
    if (statement)
      claims.push({
        id: explicit
          ? explicit[1].toUpperCase()
          : `C${String(claims.length + 1).padStart(3, "0")}`,
        statement,
        citations: citationIds(body),
        locator: `report.md#line-${index + 1}`,
      });
  });
  if (!claims.length)
    throw new Error("No claims found. Add a '## Claims' or '## 结论' list.");
  const ids = claims.map((x) => x.id),
    duplicate = ids.find((id, index) => ids.indexOf(id) !== index);
  if (duplicate) throw new Error(`Duplicate claim ID: ${duplicate}`);
  return { title, claims };
}
function evidenceAnchor(value, index) {
  if (value == null) return null;
  if (typeof value !== "object" || Array.isArray(value))
    throw new Error(`evidence[${index}].anchor must be an object.`);
  if (!["pdf_text", "pdf_ocr"].includes(value.kind))
    throw new Error(`evidence[${index}].anchor has an invalid kind.`);
  if (!/^[0-9a-f]{64}$/i.test(text(value.file_sha256)))
    throw new Error(`evidence[${index}].anchor requires a SHA-256 digest.`);
  if (
    !Number.isInteger(value.page) ||
    value.page < 1 ||
    !Number.isInteger(value.start) ||
    value.start < 0 ||
    !Number.isInteger(value.end) ||
    value.end <= value.start
  )
    throw new Error(`evidence[${index}].anchor has invalid page or offsets.`);
  const rects = value.rects ?? [];
  if (
    !Array.isArray(rects) ||
    rects.length > 100 ||
    rects.some(
      (rect) =>
        !rect ||
        ["x", "y", "width", "height"].some(
          (name) =>
            typeof rect[name] !== "number" ||
            !Number.isFinite(rect[name]) ||
            rect[name] < 0 ||
            rect[name] > 1,
        ),
    )
  )
    throw new Error(`evidence[${index}].anchor has invalid rectangles.`);
  return {
    kind: value.kind,
    file_sha256: text(value.file_sha256).toLowerCase(),
    page: value.page,
    start: value.start,
    end: value.end,
    rects: rects.map((rect) => ({
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
    })),
  };
}
function parseManifest(raw) {
  let data;
  try {
    data = JSON.parse(raw);
  } catch (exc) {
    throw new Error(`Invalid evidence JSON: ${exc.message}`);
  }
  if (!data || typeof data !== "object" || Array.isArray(data))
    throw new Error("Manifest root must be an object.");
  if (!Array.isArray(data.sources) || !Array.isArray(data.evidence))
    throw new Error("Manifest sources and evidence must be arrays.");
  const sources = new Map();
  data.sources.forEach((source, index) => {
    if (!source || typeof source !== "object" || Array.isArray(source))
      throw new Error(`sources[${index}] must be an object.`);
    const id = text(source.id),
      title = text(source.title);
    if (!id || !title)
      throw new Error(`sources[${index}] requires id and title.`);
    if (sources.has(id)) throw new Error(`Duplicate source ID: ${id}`);
    if (
      source.version_conflict !== undefined &&
      source.version_conflict !== null &&
      typeof source.version_conflict !== "boolean"
    )
      throw new Error(
        `sources[${index}].version_conflict must be true, false, or null.`,
      );
    sources.set(id, {
      id,
      title,
      authors: Array.isArray(source.authors)
        ? source.authors.map(text).filter(Boolean)
        : text(source.authors)
          ? [text(source.authors)]
          : [],
      year: source.year ?? "",
      doi: text(source.doi),
      url: text(source.url),
      publication_status: text(
        source.publication_status || "unknown",
      ).toLowerCase(),
      integrity_checked_at: text(source.integrity_checked_at),
      integrity_url: text(source.integrity_url),
      version: text(source.version),
      version_url: text(source.version_url),
      version_conflict: source.version_conflict ?? null,
      version_notes: text(source.version_notes),
      data_availability: text(
        source.data_availability || "unknown",
      ).toLowerCase(),
      data_url: text(source.data_url),
      code_availability: text(
        source.code_availability || "unknown",
      ).toLowerCase(),
      code_url: text(source.code_url),
    });
  });
  const evidence = data.evidence.map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item))
      throw new Error(`evidence[${index}] must be an object.`);
    const row = {
      claim_id: text(item.claim_id).toUpperCase(),
      source_id: text(item.source_id),
      verdict: text(item.verdict || "UNREVIEWED").toUpperCase(),
      quote: text(item.quote),
      locator: text(item.locator),
      note: text(item.note),
      reviewer_id: text(item.reviewer_id),
      reviewed_at: text(item.reviewed_at),
      review_method: text(item.review_method || "unknown").toLowerCase(),
      review_receipt: text(item.review_receipt),
      anchor: evidenceAnchor(item.anchor, index),
    };
    if (!row.claim_id || !row.source_id)
      throw new Error(`evidence[${index}] requires claim_id and source_id.`);
    if (!verdicts.has(row.verdict))
      throw new Error(`evidence[${index}] has invalid verdict: ${row.verdict}`);
    if (!reviewMethods.has(row.review_method))
      throw new Error(
        `evidence[${index}] has invalid review_method: ${row.review_method}`,
      );
    if (
      ["SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED"].includes(
        row.verdict,
      ) &&
      (!row.quote || !row.locator)
    )
      throw new Error(
        `evidence[${index}] verdict ${row.verdict} requires quote and locator.`,
      );
    if (
      row.review_method === "ai_assisted" &&
      ["SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED"].includes(row.verdict)
    )
      throw new Error(
        `evidence[${index}] AI-assisted draft must remain UNREVIEWED or UNVERIFIABLE.`,
      );
    return row;
  });
  return { sources, evidence };
}
const aggregate = (citations, rows) => {
  if (!citations.length || rows.some((row) => !row.source_resolved))
    return "UNVERIFIABLE";
  const values = rows.map((row) => row.verdict);
  if (!values.length || values.every((x) => x === "UNREVIEWED"))
    return "UNREVIEWED";
  if (values.includes("CONTRADICTED")) return "CONTRADICTED";
  if (values.includes("PARTIALLY_SUPPORTED")) return "PARTIALLY_SUPPORTED";
  if (values.every((x) => x === "SUPPORTED")) return "SUPPORTED";
  if (values.every((x) => x === "NOT_FOUND")) return "NOT_FOUND";
  if (values.includes("UNVERIFIABLE")) return "UNVERIFIABLE";
  return "PARTIALLY_SUPPORTED";
};
async function digest(value) {
  const bytes = new TextEncoder().encode(value),
    hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)]
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");
}
async function digestBytes(value) {
  const hash = await crypto.subtle.digest("SHA-256", value);
  return [...new Uint8Array(hash)]
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");
}
function setPdfStatus(message, error = false) {
  pdfStatus.removeAttribute("data-i18n");
  pdfStatus.textContent = message;
  pdfStatus.classList.toggle("error-text", error);
}
async function ensurePdfLibrary() {
  if (pdfLibrary) return pdfLibrary;
  setPdfStatus(t("pdf_loading"));
  pdfLibrary = await import(PDF_JS_URL);
  pdfLibrary.GlobalWorkerOptions.workerSrc = PDF_WORKER_URL;
  return pdfLibrary;
}
function loadScript(url) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${url}"]`);
    if (existing) {
      if (window.Tesseract) resolve();
      else existing.addEventListener("load", resolve, { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = url;
    script.crossOrigin = "anonymous";
    script.addEventListener("load", resolve, { once: true });
    script.addEventListener(
      "error",
      () => reject(new Error("script load failed")),
      { once: true },
    );
    document.head.append(script);
  });
}
function refreshAnchorTargets() {
  let claims = [],
    sources = [];
  try {
    claims = parseReport(reportInput.value).claims;
  } catch {}
  try {
    const manifest = JSON.parse(manifestInput.value);
    if (Array.isArray(manifest.sources))
      sources = manifest.sources.filter(
        (item) => item && text(item.id) && text(item.title),
      );
  } catch {}
  const replace = (select, items, label) => {
    const selected = select.value;
    select.replaceChildren();
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = `— ${label} —`;
    select.append(empty);
    for (const item of items) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = `${item.id} · ${item.statement || item.title}`;
      select.append(option);
    }
    if (items.some((item) => item.id === selected)) select.value = selected;
  };
  replace(anchorClaim, claims, t("claim_target"));
  replace(anchorSource, sources, t("source_target"));
  updatePdfSelectionUi();
}
function updatePdfSelectionUi() {
  if (pendingPdfSelection) {
    selectedQuote.removeAttribute("data-i18n");
    selectedQuote.textContent = pendingPdfSelection.quote;
    selectedQuote.classList.remove("muted");
  } else {
    selectedQuote.setAttribute("data-i18n", "nothing_selected");
    selectedQuote.textContent = t("nothing_selected");
    selectedQuote.classList.add("muted");
  }
  attachSelection.disabled = !(
    pendingPdfSelection &&
    anchorClaim.value &&
    anchorSource.value
  );
}
function clearPdfSelection() {
  pendingPdfSelection = null;
  for (const card of pdfPassages.querySelectorAll(".passage-card"))
    card.setAttribute("aria-pressed", "false");
  window.getSelection()?.removeAllRanges();
  updatePdfSelectionUi();
}
function passageRanges(value, maxLength = 420) {
  const ranges = [];
  let cursor = 0;
  while (cursor < value.length && ranges.length < 80) {
    while (cursor < value.length && /\s/.test(value[cursor])) cursor += 1;
    if (cursor >= value.length) break;
    const hardEnd = Math.min(value.length, cursor + maxLength);
    let end = hardEnd;
    if (hardEnd < value.length) {
      const windowText = value.slice(cursor, hardEnd + 1);
      const boundary = /[.!?。！？](?:\s|$)|\n{2,}/g;
      let match;
      let candidate = 0;
      while ((match = boundary.exec(windowText)) !== null) {
        const boundaryEnd = match.index + match[0].length;
        if (boundaryEnd >= 90) candidate = boundaryEnd;
      }
      if (candidate) {
        end = cursor + candidate;
      } else {
        const whitespace = Math.max(
          windowText.lastIndexOf(" "),
          windowText.lastIndexOf("\n"),
        );
        if (whitespace >= 90) end = cursor + whitespace;
      }
    }
    while (end > cursor && /\s/.test(value[end - 1])) end -= 1;
    if (end <= cursor) end = Math.min(value.length, cursor + maxLength);
    const quote = value.slice(cursor, end).replace(/\s+/g, " ").trim();
    if (quote) ranges.push({ quote, start: cursor, end });
    cursor = end;
  }
  return ranges;
}
function renderPdfPassages(value) {
  pdfPassages.replaceChildren();
  const passages = passageRanges(value);
  if (!passages.length) {
    const empty = document.createElement("p");
    empty.className = "passage-empty";
    empty.setAttribute("data-i18n", "passages_empty");
    empty.textContent = t("passages_empty");
    pdfPassages.append(empty);
    return;
  }
  passages.forEach((passage, index) => {
    const card = document.createElement("button");
    const label = document.createElement("small");
    const body = document.createElement("span");
    card.type = "button";
    card.className = "passage-card";
    card.setAttribute("aria-pressed", "false");
    label.textContent = `${t("passage_label")} ${index + 1}`;
    body.textContent = passage.quote;
    card.append(label, body);
    card.addEventListener("click", () => {
      const wasSelected = card.getAttribute("aria-pressed") === "true";
      clearPdfSelection();
      if (wasSelected) return;
      card.setAttribute("aria-pressed", "true");
      pendingPdfSelection = { ...passage, rects: [] };
      updatePdfSelectionUi();
    });
    pdfPassages.append(card);
  });
}
function pdfTextFromItems(items) {
  return items
    .map((item) => `${text(item.str)}${item.hasEOL ? "\n" : " "}`)
    .join("")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
async function renderPdfPage(pageNumber) {
  if (!pdfDocument) return;
  pdfPageNumber = Math.min(Math.max(1, pageNumber), pdfDocument.numPages);
  pdfPrev.disabled = pdfPageNumber <= 1;
  pdfNext.disabled = pdfPageNumber >= pdfDocument.numPages;
  pdfPageLabel.textContent = `${pdfPageNumber} / ${pdfDocument.numPages}`;
  clearPdfSelection();
  pdfExtractionKind = "pdf_text";
  const page = await pdfDocument.getPage(pdfPageNumber),
    viewport = page.getViewport({ scale: 1.45 }),
    context = pdfCanvas.getContext("2d", { alpha: false });
  pdfCanvas.width = Math.ceil(viewport.width);
  pdfCanvas.height = Math.ceil(viewport.height);
  await page.render({ canvasContext: context, viewport }).promise;
  const content = await page.getTextContent(),
    extracted = pdfTextFromItems(content.items);
  pdfText.textContent = extracted || t("pdf_no_text");
  renderPdfPassages(extracted);
  setPdfStatus(
    `${t("pdf_ready")} · SHA-256 ${pdfFileHash.slice(0, 12)}… · ${pdfDocument.numPages} ${language === "zh" ? "页" : "pages"}`,
  );
}
async function loadPdf(file) {
  if (!file) return;
  if (file.size > MAX_PDF_BYTES) {
    setPdfStatus(t("pdf_limit"), true);
    return;
  }
  pdfViewer.hidden = true;
  try {
    const buffer = await file.arrayBuffer(),
      library = await ensurePdfLibrary();
    pdfFileHash = await digestBytes(buffer);
    pdfDocument = await library.getDocument({
      data: new Uint8Array(buffer),
      isEvalSupported: false,
    }).promise;
    pdfViewer.hidden = false;
    await renderPdfPage(1);
    refreshAnchorTargets();
  } catch (exc) {
    pdfDocument = null;
    setPdfStatus(
      `${t("pdf_failed")}: ${exc instanceof Error ? exc.message : String(exc)}`,
      true,
    );
  }
}
function capturePdfSelection() {
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount) {
    pendingPdfSelection = null;
    return;
  }
  const range = selection.getRangeAt(0);
  if (range.collapsed || !pdfText.contains(range.commonAncestorContainer)) {
    pendingPdfSelection = null;
    return;
  }
  const quote = selection.toString().replace(/\s+/g, " ").trim();
  if (!quote) {
    pendingPdfSelection = null;
    return;
  }
  const prefix = document.createRange();
  prefix.selectNodeContents(pdfText);
  prefix.setEnd(range.startContainer, range.startOffset);
  const start = prefix.toString().length,
    end = start + range.toString().length,
    base = pdfText.getBoundingClientRect(),
    width = Math.max(1, pdfText.scrollWidth),
    height = Math.max(1, pdfText.scrollHeight),
    clamp = (value) => Math.min(1, Math.max(0, value)),
    rects = [...range.getClientRects()].slice(0, 100).map((rect) => ({
      x: Number(
        clamp((rect.left - base.left + pdfText.scrollLeft) / width).toFixed(6),
      ),
      y: Number(
        clamp((rect.top - base.top + pdfText.scrollTop) / height).toFixed(6),
      ),
      width: Number(clamp(rect.width / width).toFixed(6)),
      height: Number(clamp(rect.height / height).toFixed(6)),
    }));
  for (const card of pdfPassages.querySelectorAll(".passage-card"))
    card.setAttribute("aria-pressed", "false");
  pendingPdfSelection = { quote, start, end, rects };
  updatePdfSelectionUi();
}
async function attachPdfSelection() {
  if (!pendingPdfSelection) capturePdfSelection();
  if (!anchorClaim.value || !anchorSource.value) {
    setPdfStatus(t("choose_target"), true);
    return;
  }
  if (!pendingPdfSelection) {
    setPdfStatus(t("select_quote"), true);
    return;
  }
  let manifest;
  try {
    manifest = JSON.parse(manifestInput.value);
  } catch {
    setPdfStatus(t("manifest_invalid"), true);
    return;
  }
  if (!Array.isArray(manifest.sources) || !Array.isArray(manifest.evidence)) {
    setPdfStatus(t("manifest_shape"), true);
    return;
  }
  manifest.evidence.push({
    claim_id: anchorClaim.value,
    source_id: anchorSource.value,
    verdict: "UNREVIEWED",
    quote: pendingPdfSelection.quote,
    locator: `PDF page ${pdfPageNumber}`,
    note: "",
    reviewer_id: "",
    reviewed_at: "",
    review_method: "unknown",
    anchor: {
      kind: pdfExtractionKind,
      file_sha256: pdfFileHash,
      page: pdfPageNumber,
      start: pendingPdfSelection.start,
      end: pendingPdfSelection.end,
      rects: pendingPdfSelection.rects,
    },
  });
  manifestInput.value = JSON.stringify(manifest, null, 2);
  currentAudit = null;
  jsonButton.disabled = true;
  htmlButton.disabled = true;
  setPdfStatus(t("selection_attached"));
  clearPdfSelection();
}
async function runPdfOcr() {
  if (!pdfDocument) return;
  pdfOcr.disabled = true;
  try {
    setPdfStatus(t("ocr_loading"));
    if (!window.Tesseract) await loadScript(TESSERACT_URL);
    const result = await window.Tesseract.recognize(
      pdfCanvas,
      language === "zh" ? "chi_sim+eng" : "eng",
      {
        logger: (event) => {
          if (event.status === "recognizing text")
            setPdfStatus(
              `${t("ocr_running")} ${Math.round((event.progress || 0) * 100)}%`,
            );
        },
      },
    );
    const extracted = text(result?.data?.text);
    if (!extracted) throw new Error("no text recognized");
    pdfText.textContent = extracted;
    renderPdfPassages(extracted);
    pdfExtractionKind = "pdf_ocr";
    clearPdfSelection();
    setPdfStatus(t("ocr_done"));
  } catch (exc) {
    setPdfStatus(
      `${t("ocr_failed")}: ${exc instanceof Error ? exc.message : String(exc)}`,
      true,
    );
  } finally {
    pdfOcr.disabled = false;
  }
}
function availability(sources, kind) {
  if (!sources.length)
    return { status: "WARN", detail: "No resolved sources were available." };
  const states = sources.map((x) => x[`${kind}_availability`]);
  if (states.every((x) => ["available", "not_applicable"].includes(x)))
    return {
      status: "PASS",
      detail: `Every source declares ${kind} availability.`,
    };
  if (states.includes("unavailable"))
    return {
      status: "FAIL",
      detail: `At least one source declares ${kind} unavailable.`,
    };
  return {
    status: "WARN",
    detail: `At least one source has unknown ${kind} availability.`,
  };
}
function renderGraph(audit) {
  const ns = "http://www.w3.org/2000/svg",
    wrap = node("div", "graph-wrap"),
    svg = document.createElementNS(ns, "svg"),
    height = Math.max(
      180,
      Math.max(audit.claims.length, audit.sources.length) * 82 + 36,
    ),
    claimGap = (height - 56) / Math.max(1, audit.claims.length),
    sourceGap = (height - 56) / Math.max(1, audit.sources.length),
    claimY = new Map(
      audit.claims.map((item, index) => [item.id, 28 + index * claimGap]),
    ),
    sourceY = new Map(
      audit.sources.map((item, index) => [item.id, 28 + index * sourceGap]),
    );
  svg.setAttribute("viewBox", `0 0 960 ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    language === "zh"
      ? "左侧结论与右侧引用来源之间的关系图"
      : "Claims on the left connected to cited sources on the right",
  );
  for (const claim of audit.claims)
    for (const sourceId of claim.citations)
      if (sourceY.has(sourceId)) {
        const path = document.createElementNS(ns, "path"),
          y1 = claimY.get(claim.id) + 22,
          y2 = sourceY.get(sourceId) + 22;
        path.setAttribute("d", `M 330 ${y1} C 470 ${y1}, 510 ${y2}, 650 ${y2}`);
        path.setAttribute("class", `graph-edge ${claim.verdict}`);
        svg.append(path);
      }
  const addNode = (x, y, id, label, width) => {
    const group = document.createElementNS(ns, "g"),
      rect = document.createElementNS(ns, "rect"),
      idText = document.createElementNS(ns, "text"),
      labelText = document.createElementNS(ns, "text"),
      short = label.length <= 48 ? label : `${label.slice(0, 47).trim()}…`;
    group.setAttribute("transform", `translate(${x} ${y})`);
    rect.setAttribute("width", String(width));
    rect.setAttribute("height", "44");
    rect.setAttribute("rx", "9");
    rect.setAttribute("class", "graph-node");
    idText.setAttribute("x", "12");
    idText.setAttribute("y", "18");
    idText.setAttribute("class", "graph-text");
    idText.textContent = id;
    labelText.setAttribute("x", "12");
    labelText.setAttribute("y", "35");
    labelText.setAttribute("class", "graph-label");
    labelText.textContent = short;
    group.append(rect, idText, labelText);
    svg.append(group);
  };
  for (const claim of audit.claims)
    addNode(20, claimY.get(claim.id), claim.id, claim.statement, 310);
  for (const source of audit.sources)
    addNode(650, sourceY.get(source.id), source.id, source.title, 290);
  wrap.append(svg);
  return wrap;
}
async function buildAudit(markdown, manifestRaw) {
  const report = parseReport(markdown),
    manifest = parseManifest(manifestRaw),
    claimIds = new Set(report.claims.map((x) => x.id));
  for (const row of manifest.evidence) {
    if (!claimIds.has(row.claim_id))
      throw new Error(`Evidence references unknown claim: ${row.claim_id}`);
    if (!manifest.sources.has(row.source_id))
      throw new Error(`Evidence references unknown source: ${row.source_id}`);
  }
  const pairs = new Map();
  for (const row of manifest.evidence) {
    const key = `${row.claim_id}\u0000${row.source_id}`;
    if (!pairs.has(key)) pairs.set(key, []);
    pairs.get(key).push(row);
  }
  const cited = [],
    claims = report.claims.map((claim) => {
      const rows = [];
      for (const sourceId of claim.citations) {
        if (!cited.includes(sourceId)) cited.push(sourceId);
        const matched = pairs.get(`${claim.id}\u0000${sourceId}`) || [
          {
            claim_id: claim.id,
            source_id: sourceId,
            verdict: "UNREVIEWED",
            quote: "",
            locator: "",
            note: "No evidence review has been recorded.",
            reviewer_id: "",
            reviewed_at: "",
            review_method: "unknown",
            review_receipt: "",
            anchor: null,
          },
        ];
        for (const item of matched)
          rows.push({
            ...item,
            source_resolved: manifest.sources.has(sourceId),
          });
      }
      return {
        ...claim,
        verdict: aggregate(claim.citations, rows),
        evidence: rows,
      };
    });
  const sources = cited
      .filter((id) => manifest.sources.has(id))
      .map((id) => manifest.sources.get(id)),
    unresolved = cited.filter((id) => !manifest.sources.has(id)),
    reviewed = manifest.evidence.filter((x) => x.verdict !== "UNREVIEWED"),
    risky = sources.filter((x) => highRisk.has(x.publication_status)),
    conflicts = sources.filter((x) => x.version_conflict === true),
    allCited = claims.every((x) => x.citations.length),
    allKnown =
      sources.length &&
      sources.every((x) => x.publication_status !== "unknown"),
    versionsClear =
      sources.length && sources.every((x) => x.version_conflict === false),
    provenanceComplete =
      reviewed.length &&
      reviewed.every(
        (x) => x.reviewer_id && x.reviewed_at && x.review_method !== "unknown",
      ),
    reviewConflicts = [];
  for (const [key, rows] of pairs) {
    const values = new Set(rows.map((x) => x.verdict));
    if (
      values.has("CONTRADICTED") &&
      ["SUPPORTED", "PARTIALLY_SUPPORTED"].some((x) => values.has(x))
    )
      reviewConflicts.push(key.replace("\u0000", "/"));
  }
  const checklist = {
    claims_have_citations: {
      status: allCited ? "PASS" : "FAIL",
      detail: allCited
        ? "Every claim has at least one citation."
        : "At least one claim has no citation.",
    },
    sources_resolved: {
      status: unresolved.length ? "FAIL" : "PASS",
      detail: unresolved.length
        ? `Unresolved source IDs: ${unresolved.join(", ")}`
        : "Every citation resolves in the manifest.",
    },
    reviewed_evidence_has_quotes: {
      status:
        reviewed.length && reviewed.every((x) => x.quote) ? "PASS" : "WARN",
      detail: "Decisive assessments require exact source text.",
    },
    reviewed_evidence_has_locators: {
      status:
        reviewed.length && reviewed.every((x) => x.locator) ? "PASS" : "WARN",
      detail:
        "Decisive assessments require a page, section, paragraph, table, or URL locator.",
    },
    publication_status: {
      status: risky.length ? "FAIL" : allKnown ? "PASS" : "WARN",
      detail: risky.length
        ? `High-risk publication status: ${risky.map((x) => x.id).join(", ")}.`
        : allKnown
          ? "Publication status is recorded for every resolved source."
          : "At least one source has unknown correction or retraction status.",
    },
    version_conflicts: {
      status: conflicts.length ? "FAIL" : versionsClear ? "PASS" : "WARN",
      detail: conflicts.length
        ? `Version conflicts require review: ${conflicts.map((x) => x.id).join(", ")}.`
        : versionsClear
          ? "Every resolved source records no known version conflict."
          : "At least one source has not been checked for version conflicts.",
    },
    review_provenance: {
      status: provenanceComplete ? "PASS" : "WARN",
      detail: provenanceComplete
        ? "Every reviewed row records reviewer, time, and method."
        : "Some reviewed evidence lacks reviewer, timestamp, or review method.",
    },
    review_consensus: {
      status: reviewConflicts.length ? "FAIL" : "PASS",
      detail: reviewConflicts.length
        ? `Conflicting reviewer verdicts: ${reviewConflicts.join(", ")}.`
        : "No claim/source pair contains both supporting and contradicting reviewer verdicts.",
    },
    data_availability: availability(sources, "data"),
    code_availability: availability(sources, "code"),
  };
  const counts = {};
  for (const key of verdicts)
    counts[key] = claims.filter((x) => x.verdict === key).length;
  return {
    schema_version: 1,
    tool: "PaperTrail Web",
    generated_at: new Date().toISOString(),
    report: {
      title: report.title,
      file: "report.md",
      sha256: await digest(markdown),
    },
    manifest: { file: "evidence.json", sha256: await digest(manifestRaw) },
    summary: {
      claims: claims.length,
      sources: sources.length,
      unresolved_sources: unresolved.length,
      verdicts: counts,
    },
    claims,
    sources,
    unresolved_source_ids: unresolved,
    reproducibility_checklist: checklist,
    limitations: [
      "A citation match does not by itself establish that a source supports a claim.",
      "Verdicts reflect recorded evidence rows and require independent review for high-stakes use.",
      "Files were processed locally in this browser and were not uploaded by PaperTrail.",
    ],
  };
}
function renderAudit(audit) {
  preview.className = "";
  preview.removeAttribute("data-i18n");
  preview.replaceChildren();
  const head = node("div", "preview-head"),
    titleWrap = node("div");
  add(
    titleWrap,
    node("div", "eyebrow", t("audit_eyebrow")),
    node("h2", "", audit.report.title),
  );
  const hashes = node(
    "div",
    "hashes",
    `${t("report_hash")} ${audit.report.sha256}\n${t("manifest_hash")} ${audit.manifest.sha256}`,
  );
  add(head, titleWrap, hashes);
  preview.append(head);
  const risky = audit.sources.filter(
    (x) => highRisk.has(x.publication_status) || x.version_conflict === true,
  );
  if (risky.length)
    preview.append(
      node(
        "div",
        "integrity-alert",
        `${t("integrity_review")}：${risky.map((x) => x.id).join(", ")}`,
      ),
    );
  const metrics = node("div", "metrics");
  for (const [verdict, count] of Object.entries(audit.summary.verdicts))
    if (count) {
      const card = node("div", "metric");
      add(
        card,
        node("strong", "", String(count)),
        node("span", "", verdictText(verdict)),
      );
      metrics.append(card);
    }
  preview.append(
    metrics,
    node("h2", "", t("evidence_graph")),
    renderGraph(audit),
  );
  preview.append(node("h2", "", t("claims")));
  const claims = node("div", "claims");
  for (const claim of audit.claims) {
    const card = node("article", "claim"),
      top = node("div", "claim-top");
    add(
      top,
      node("span", "claim-id", claim.id),
      node("span", `badge ${claim.verdict}`, verdictText(claim.verdict)),
    );
    add(
      card,
      top,
      node("h3", "", claim.statement),
      node("div", "muted", claim.locator),
    );
    const rows = node("div", "evidence");
    if (!claim.evidence.length)
      rows.append(node("p", "muted", t("no_citations")));
    for (const item of claim.evidence) {
      const source = audit.sources.find((x) => x.id === item.source_id),
        row = node("div", "evidence-row"),
        sourceField = node("div", "field");
      sourceField.append(node("small", "", t("source")));
      const href = source && safeUrl(source.url);
      if (href) {
        const link = node("a", "", source.title);
        link.href = href;
        link.rel = "noreferrer";
        sourceField.append(link);
      } else
        sourceField.append(
          node(
            "div",
            "",
            source ? source.title : `${t("unresolved")}：${item.source_id}`,
          ),
        );
      sourceField.append(node("div", "muted", item.source_id));
      const verdictField = node("div", "field");
      add(
        verdictField,
        node("small", "", t("assessment")),
        node("span", `badge ${item.verdict}`, verdictText(item.verdict)),
      );
      const quoteField = node("div", "field quote-field");
      add(
        quoteField,
        node("small", "", t("exact_evidence")),
        node(
          "div",
          item.quote ? "quote" : "muted",
          item.quote || t("no_quote"),
        ),
      );
      const locatorField = node("div", "field"),
        anchorNote = item.anchor
          ? node(
              "p",
              "muted",
              `PDF ${item.anchor.page} · ${item.anchor.kind} · SHA-256 ${item.anchor.file_sha256.slice(0, 12)}…`,
            )
          : null;
      add(
        locatorField,
        node("small", "", t("locator")),
        node("div", "", item.locator || t("not_recorded")),
        node(
          "p",
          "muted",
          `${item.reviewer_id || t("unattributed")} · ${item.review_method || t("unknown")} · ${item.reviewed_at || t("time_unknown")}`,
        ),
        node("p", "muted", item.note),
      );
      if (anchorNote) locatorField.append(anchorNote);
      add(row, sourceField, verdictField, quoteField, locatorField);
      rows.append(row);
    }
    card.append(rows);
    claims.append(card);
  }
  preview.append(claims);
  preview.append(node("h2", "", t("checklist")));
  const checklist = node("div", "checklist");
  for (const [name, item] of Object.entries(audit.reproducibility_checklist)) {
    const card = node("div", "check-card");
    add(card, node("span", `check ${item.status}`, checkText(item.status)));
    const body = node("div");
    add(
      body,
      node("strong", "", checklistLabels[language][name] || name),
      node("p", "", localizeDetail(item.detail)),
    );
    add(card, body);
    checklist.append(card);
  }
  preview.append(checklist);
  preview.append(node("h2", "", t("source_registry")));
  const sources = node("div", "sources");
  for (const source of audit.sources) {
    const card = node("article", "source-card");
    add(
      card,
      node("h3", "", source.title),
      node(
        "div",
        "source-meta",
        `${source.authors.join(", ") || t("unknown")} · ${source.year || t("unknown")}`,
      ),
      node("p", "", `ID: ${source.id} · DOI: ${source.doi || "—"}`),
      node(
        "p",
        "",
        `${t("version")}：${source.version || t("unknown")} · ${t("integrity")}：${source.publication_status} · ${t("conflict")}：${source.version_conflict === null ? t("unknown") : source.version_conflict ? t("yes") : t("no")}`,
      ),
    );
    if (source.version_notes) card.append(node("p", "", source.version_notes));
    sources.append(card);
  }
  preview.append(sources);
}
function setError(message = "") {
  errorBox.textContent = message;
  errorBox.classList.toggle("visible", Boolean(message));
}
function applyLanguage(value, { remember = true } = {}) {
  language = value === "zh" ? "zh" : "en";
  languageSelect.value = language;
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = t("page_title");
  for (const item of document.querySelectorAll("[data-i18n]"))
    item.textContent = t(item.dataset.i18n);
  if (currentAudit) renderAudit(currentAudit);
  else {
    preview.className = "preview-empty";
    preview.setAttribute("data-i18n", "preview_empty");
    preview.textContent = t("preview_empty");
  }
  if (pdfDocument)
    setPdfStatus(
      `${t("pdf_ready")} · SHA-256 ${pdfFileHash.slice(0, 12)}… · ${pdfDocument.numPages} ${language === "zh" ? "页" : "pages"}`,
    );
  for (const [index, label] of [
    ...pdfPassages.querySelectorAll(".passage-card small"),
  ].entries())
    label.textContent = `${t("passage_label")} ${index + 1}`;
  refreshAnchorTargets();
  if (remember)
    try {
      localStorage.setItem("papertrail-language", language);
    } catch {}
}
function restore() {
  reportInput.value = demo.report;
  manifestInput.value = demo.manifest;
  currentAudit = null;
  jsonButton.disabled = true;
  htmlButton.disabled = true;
  preview.className = "preview-empty";
  preview.setAttribute("data-i18n", "preview_empty");
  preview.textContent = t("preview_empty");
  refreshAnchorTargets();
  setError();
}
async function run() {
  setError();
  try {
    currentAudit = await buildAudit(reportInput.value, manifestInput.value);
    renderAudit(currentAudit);
    jsonButton.disabled = false;
    htmlButton.disabled = false;
    preview.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (exc) {
    currentAudit = null;
    jsonButton.disabled = true;
    htmlButton.disabled = true;
    preview.className = "preview-empty";
    preview.setAttribute("data-i18n", "preview_empty");
    preview.textContent = t("audit_failed");
    setError(exc instanceof Error ? exc.message : String(exc));
  }
}
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type })),
    link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
document.getElementById("audit-button").addEventListener("click", run);
document.getElementById("draft-button").addEventListener("click", draftClaims);
document.getElementById("reset-button").addEventListener("click", restore);
document.getElementById("doi-button").addEventListener("click", addDoiSource);
document
  .getElementById("attach-selection")
  .addEventListener("click", attachPdfSelection);
languageSelect.addEventListener("change", () =>
  applyLanguage(languageSelect.value),
);
pdfFile.addEventListener("change", (event) => loadPdf(event.target.files[0]));
pdfPrev.addEventListener("click", () => renderPdfPage(pdfPageNumber - 1));
pdfNext.addEventListener("click", () => renderPdfPage(pdfPageNumber + 1));
pdfOcr.addEventListener("click", runPdfOcr);
pdfText.addEventListener("mouseup", capturePdfSelection);
pdfText.addEventListener("keyup", capturePdfSelection);
anchorClaim.addEventListener("change", updatePdfSelectionUi);
anchorSource.addEventListener("change", updatePdfSelectionUi);
reportInput.addEventListener("input", refreshAnchorTargets);
manifestInput.addEventListener("input", refreshAnchorTargets);
jsonButton.addEventListener(
  "click",
  () =>
    currentAudit &&
    download(
      "audit.json",
      JSON.stringify(currentAudit, null, 2) + "\n",
      "application/json",
    ),
);
htmlButton.addEventListener("click", () => {
  if (!currentAudit) return;
  const title = currentAudit.report.title.replace(
      /[&<>"']/g,
      (x) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[x],
    ),
    body = preview.outerHTML;
  download(
    "papertrail-report.html",
    `<!doctype html><html lang="${document.documentElement.lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title} · PaperTrail</title><style>${appCss}</style></head><body><main>${body}<footer>${t("export_footer")}</footer></main></body></html>`,
    "text/html",
  );
});
for (const [fileId, input] of [
  ["report-file", reportInput],
  ["manifest-file", manifestInput],
])
  document.getElementById(fileId).addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (file) {
      input.value = await file.text();
      refreshAnchorTargets();
    }
  });
let preferred = "";
try {
  preferred = localStorage.getItem("papertrail-language") || "";
} catch {}
applyLanguage(
  preferred ||
    ((navigator.language || "").toLowerCase().startsWith("zh") ? "zh" : "en"),
  { remember: false },
);
restore();
