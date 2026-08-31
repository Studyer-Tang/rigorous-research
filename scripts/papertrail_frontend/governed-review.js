"use strict";
window.PaperTrailGovernedReview = (() => {
  const value = (item) => (item == null ? "" : String(item).trim());
  const tokens = (item) =>
    new Set(
      (item.toLowerCase().match(/[\p{L}\p{N}_]+/gu) || []).filter(
        (token) => token.length > 1,
      ),
    );

  async function hash(item) {
    const digest = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(item),
    );
    return [...new Uint8Array(digest)]
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  function recommendations(statement, manifest) {
    const claimTokens = tokens(statement),
      claimNegated = /\b(?:no|not|never|without|failed)\b|不|未|无|没有/i.test(
        statement,
      );
    return (manifest.sources || [])
      .map((source) => {
        const quotes = (manifest.evidence || [])
            .filter((item) => item.source_id === source.id)
            .map((item) => value(item.quote))
            .join(" "),
          body = `${value(source.title)} ${value(source.abstract)} ${value(source.version_notes)} ${quotes}`,
          sourceTokens = tokens(body),
          overlap =
            [...claimTokens].filter((token) => sourceTokens.has(token)).length /
            Math.max(1, claimTokens.size),
          sourceNegated =
            /\b(?:no|not|never|without|failed)\b|不|未|无|没有/i.test(body);
        return {
          source_id: source.id,
          relation:
            claimNegated !== sourceNegated
              ? "potential_contradiction"
              : "potential_support",
          score: Number(overlap.toFixed(4)),
          status: "SUGGESTION_NOT_A_VERDICT",
          body,
        };
      })
      .filter((item) => item.source_id && item.score > 0)
      .sort((left, right) => right.score - left.score)
      .slice(0, 5);
  }

  function issues(statement, candidates) {
    const evidence = candidates.map((item) => item.body).join(" "),
      found = [];
    if (
      /\b(?:all|always|every|everyone|guarantees?|proves?|never)\b|所有|全部|总是|必然|证明|绝不/i.test(
        statement,
      ) &&
      (!evidence ||
        /\b(?:may|might|suggests?|associated|sample|respondents?|observed|correlat)\b|可能|表明|样本|受访者|相关/i.test(
          evidence,
        ))
    )
      found.push("possible_overgeneralization");
    if (
      /\b(?:causes?|leads? to|results? in|drives?)\b|导致|造成|使得/i.test(
        statement,
      ) &&
      (!evidence || /associated|correlat|相关/i.test(evidence))
    )
      found.push("possible_causal_overreach");
    if (!candidates.length) found.push("no_candidate_evidence");
    return found;
  }

  function createController(translate) {
    const panel = document.getElementById("governed-review"),
      container = document.getElementById("review-candidates"),
      button = document.getElementById("review-json");
    let current = null;
    const element = (tag, className, content) => {
      const item = document.createElement(tag);
      if (className) item.className = className;
      if (content !== undefined) item.textContent = content;
      return item;
    };
    const download = () => {
      if (!current) return;
      const url = URL.createObjectURL(
          new Blob([JSON.stringify(current, null, 2) + "\n"], {
            type: "application/json",
          }),
        ),
        link = document.createElement("a");
      link.href = url;
      link.download = "ai-review-draft.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    const render = () => {
      if (!current) return;
      panel.hidden = false;
      button.disabled = false;
      container.replaceChildren();
      current.candidates.forEach((candidate) => {
        const card = element("article", "review-candidate");
        card.append(
          element("strong", "", `${candidate.id} · ${translate("ai_draft")}`),
          element("p", "", candidate.statement),
        );
        if (candidate.evidence_recommendations.length)
          card.append(
            element(
              "p",
              "muted",
              `${translate("evidence_suggestions")}: ${candidate.evidence_recommendations
                .map(
                  (item) =>
                    `${item.source_id} (${translate(item.relation)}, ${item.score})`,
                )
                .join(" · ")}`,
            ),
          );
        if (candidate.scope_issues.length)
          card.append(
            element(
              "p",
              "review-warning",
              `${translate("scope_warnings")}: ${candidate.scope_issues
                .map(translate)
                .join(" · ")}`,
            ),
          );
        card.append(element("p", "muted", translate("human_gate")));
        container.append(card);
      });
    };
    const draft = async (claims, manifest, reportText) => {
      const candidates = claims.map((claim) => {
        const suggested = recommendations(claim.statement, manifest);
        return {
          ...claim,
          status: "AI_DRAFT_REQUIRES_HUMAN_REVIEW",
          evidence_recommendations: suggested.map(({ body, ...item }) => item),
          scope_issues: issues(claim.statement, suggested),
        };
      });
      current = {
        schema_version: 1,
        kind: "governed-ai-review-draft",
        created_at: new Date().toISOString(),
        report_sha256: await hash(reportText),
        governance: {
          state: "AI_DRAFT",
          formal_judgments_created: false,
          human_confirmation_required: true,
          provider: "deterministic-browser-rules",
          data_sent: "none",
        },
        candidates,
      };
      render();
      return current;
    };
    const reset = () => {
      current = null;
      panel.hidden = true;
      button.disabled = true;
    };
    button.addEventListener("click", download);
    return { draft, render, reset };
  }

  return { createController };
})();
