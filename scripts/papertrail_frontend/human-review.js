"use strict";
window.PaperTrailHumanReview = (() => {
  const value = (item) => (item == null ? "" : String(item).trim());
  const decisive = new Set([
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
  ]);
  const forbiddenReviewer = /(?:^|[\s_-])(ai|bot|model|assistant|gpt)(?:$|[\s_-])/i;

  function createController(options) {
    const {
        translate,
        verdictLabel,
        getManifestText,
        setManifestText,
        getClaims,
        getDraft,
        onMessage,
      } = options,
      form = document.getElementById("human-review-form"),
      claimSelect = document.getElementById("review-claim"),
      sourceSelect = document.getElementById("review-source"),
      verdictSelect = document.getElementById("review-verdict"),
      quoteInput = document.getElementById("review-quote"),
      locatorInput = document.getElementById("review-locator"),
      reviewerInput = document.getElementById("reviewer-id"),
      noteInput = document.getElementById("review-note"),
      evidenceIdInput = document.getElementById("review-evidence-id"),
      aiDiff = document.getElementById("review-ai-diff"),
      records = document.getElementById("human-review-records"),
      historyCount = document.getElementById("review-history-count"),
      cancelButton = document.getElementById("cancel-review-edit");

    const readManifest = () => {
      const manifest = JSON.parse(getManifestText());
      if (!Array.isArray(manifest.sources) || !Array.isArray(manifest.evidence))
        throw new Error(translate("manifest_shape"));
      if (!Array.isArray(manifest.review_history)) manifest.review_history = [];
      return manifest;
    };
    const id = () =>
      globalThis.crypto?.randomUUID?.() ||
      `E-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
    const option = (key, label) => {
      const item = document.createElement("option");
      item.value = key;
      item.textContent = label;
      return item;
    };
    const replaceOptions = (select, items, placeholder) => {
      const selected = select.value;
      select.replaceChildren(option("", `— ${placeholder} —`));
      for (const item of items)
        select.append(option(item.id, `${item.id} · ${item.statement || item.title}`));
      if (items.some((item) => item.id === selected)) select.value = selected;
    };
    const aiRecommendation = () => {
      const candidate = (getDraft()?.candidates || []).find(
        (item) => item.id === claimSelect.value,
      );
      return candidate?.evidence_recommendations?.find(
        (item) => item.source_id === sourceSelect.value,
      );
    };
    const renderDifference = () => {
      const recommendation = aiRecommendation();
      aiDiff.className = "review-ai-diff wide";
      if (!recommendation) {
        aiDiff.textContent = translate("ai_diff_none");
        return;
      }
      const humanRelation =
        verdictSelect.value === "CONTRADICTED"
          ? "potential_contradiction"
          : decisive.has(verdictSelect.value)
            ? "potential_support"
            : "";
      const agrees = humanRelation && humanRelation === recommendation.relation;
      aiDiff.classList.add(agrees ? "agrees" : "differs");
      aiDiff.textContent = `${translate("ai_suggested")} ${translate(recommendation.relation)} (${recommendation.score}). ${
        agrees ? translate("ai_human_agree") : translate("ai_human_differ")
      }`;
    };
    const clear = () => {
      evidenceIdInput.value = "";
      quoteInput.value = "";
      locatorInput.value = "";
      noteInput.value = "";
      verdictSelect.value = "SUPPORTED";
      cancelButton.hidden = true;
      renderDifference();
    };
    const currentRows = (manifest) =>
      manifest.evidence.filter(
        (item) => value(item.reviewer_id) || value(item.verdict).toUpperCase() !== "UNREVIEWED",
      );
    const ensureEvidenceIds = (manifest) => {
      let changed = false;
      for (const item of manifest.evidence)
        if (!value(item.id)) {
          item.id = id();
          changed = true;
        }
      return changed;
    };
    const edit = (row) => {
      evidenceIdInput.value = row.id;
      claimSelect.value = row.claim_id;
      sourceSelect.value = row.source_id;
      verdictSelect.value = row.verdict;
      quoteInput.value = value(row.quote);
      locatorInput.value = value(row.locator);
      reviewerInput.value = value(row.reviewer_id);
      noteInput.value = value(row.note);
      cancelButton.hidden = false;
      renderDifference();
      form.scrollIntoView({ behavior: "smooth", block: "center" });
    };
    const revoke = (evidenceId) => {
      try {
        const manifest = readManifest();
        ensureEvidenceIds(manifest);
        const index = manifest.evidence.findIndex((item) => item.id === evidenceId);
        if (index < 0) return;
        const before = manifest.evidence[index];
        const reviewerId = value(reviewerInput.value) || value(before.reviewer_id);
        if (!reviewerId || forbiddenReviewer.test(reviewerId))
          throw new Error(translate("reviewer_human_required"));
        manifest.evidence.splice(index, 1);
        manifest.review_history.push({
          event_id: id(),
          action: "revoked",
          evidence_id: evidenceId,
          performed_at: new Date().toISOString(),
          reviewer_id: reviewerId,
          before,
        });
        setManifestText(`${JSON.stringify(manifest, null, 2)}\n`);
        clear();
        render();
        onMessage(translate("review_revoked"));
      } catch (error) {
        onMessage(error instanceof Error ? error.message : String(error), true);
      }
    };
    const renderRecords = (manifest) => {
      records.replaceChildren();
      const rows = currentRows(manifest);
      historyCount.textContent = `${manifest.review_history.length} ${translate("history_events")}`;
      if (!rows.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = translate("no_human_reviews");
        records.append(empty);
        return;
      }
      for (const row of rows) {
        const card = document.createElement("article"),
          heading = document.createElement("div"),
          title = document.createElement("strong"),
          meta = document.createElement("p"),
          quote = document.createElement("blockquote"),
          actions = document.createElement("div"),
          editButton = document.createElement("button"),
          revokeButton = document.createElement("button");
        card.className = "human-review-record";
        heading.className = "human-review-record-heading";
        title.textContent = `${row.claim_id} → ${row.source_id}`;
        const badge = document.createElement("span");
        badge.className = `badge ${row.verdict}`;
        badge.textContent = verdictLabel(row.verdict);
        heading.append(title, badge);
        meta.className = "muted";
        meta.textContent = `${value(row.locator) || translate("not_recorded")} · ${value(row.reviewer_id) || translate("unattributed")} · ${value(row.reviewed_at) || translate("time_unknown")}`;
        quote.textContent = value(row.quote) || translate("no_quote");
        actions.className = "human-review-actions";
        for (const button of [editButton, revokeButton]) {
          button.type = "button";
          button.className = "button";
        }
        editButton.textContent = translate("edit_review");
        revokeButton.textContent = translate("revoke_review");
        editButton.addEventListener("click", () => edit(row));
        revokeButton.addEventListener("click", () => revoke(row.id));
        actions.append(editButton, revokeButton);
        card.append(heading, meta, quote, actions);
        records.append(card);
      }
    };
    const render = () => {
      try {
        const manifest = readManifest();
        if (ensureEvidenceIds(manifest)) setManifestText(`${JSON.stringify(manifest, null, 2)}\n`);
        replaceOptions(claimSelect, getClaims(), translate("claim_target"));
        replaceOptions(sourceSelect, manifest.sources, translate("source_target"));
        renderRecords(manifest);
        renderDifference();
      } catch {
        records.replaceChildren();
        historyCount.textContent = "";
      }
    };
    const save = (event) => {
      event.preventDefault();
      try {
        const claimId = value(claimSelect.value),
          sourceId = value(sourceSelect.value),
          verdict = value(verdictSelect.value).toUpperCase(),
          quote = value(quoteInput.value),
          locator = value(locatorInput.value),
          reviewerId = value(reviewerInput.value),
          note = value(noteInput.value);
        if (!claimId || !sourceId) throw new Error(translate("review_targets_required"));
        if (!reviewerId || forbiddenReviewer.test(reviewerId))
          throw new Error(translate("reviewer_human_required"));
        if (decisive.has(verdict) && (!quote || !locator))
          throw new Error(translate("review_quote_locator_required"));
        const manifest = readManifest();
        ensureEvidenceIds(manifest);
        const editingId = value(evidenceIdInput.value),
          existingIndex = editingId
            ? manifest.evidence.findIndex((item) => item.id === editingId)
            : manifest.evidence.findIndex(
                (item) =>
                  item.claim_id === claimId &&
                  item.source_id === sourceId &&
                  value(item.verdict).toUpperCase() === "UNREVIEWED",
              ),
          before = existingIndex >= 0 ? structuredClone(manifest.evidence[existingIndex]) : null,
          evidenceId = editingId || before?.id || id(),
          row = {
            ...(before || {}),
            id: evidenceId,
            claim_id: claimId,
            source_id: sourceId,
            verdict,
            quote,
            locator,
            note,
            reviewer_id: reviewerId,
            reviewed_at: new Date().toISOString(),
            review_method: "human",
          };
        if (existingIndex >= 0) manifest.evidence[existingIndex] = row;
        else manifest.evidence.push(row);
        manifest.review_history.push({
          event_id: id(),
          action: before ? "updated" : "created",
          evidence_id: evidenceId,
          performed_at: row.reviewed_at,
          reviewer_id: reviewerId,
          before,
          after: row,
          ai_recommendation: aiRecommendation() || null,
        });
        setManifestText(`${JSON.stringify(manifest, null, 2)}\n`);
        clear();
        render();
        onMessage(translate("review_saved"));
      } catch (error) {
        onMessage(error instanceof Error ? error.message : String(error), true);
      }
    };

    form.addEventListener("submit", save);
    cancelButton.addEventListener("click", clear);
    for (const input of [claimSelect, sourceSelect, verdictSelect])
      input.addEventListener("change", renderDifference);
    return { clear, render };
  }

  return { createController };
})();
