"use strict";
window.PaperTrailIntegrity = (() => {
  const value = (item) => (item == null ? "" : String(item).trim());
  const eventType = (item) => {
    const normalized = value(item).toLowerCase().replace(/[_\s]+/g, "-");
    if (/retract/.test(normalized)) return "retraction";
    if (/withdraw/.test(normalized)) return "withdrawal";
    if (/expression-of-concern/.test(normalized))
      return "expression_of_concern";
    if (/correct|corrig|errat/.test(normalized)) return "correction";
    return "update";
  };
  const safeUrl = (item) => {
    try {
      const url = new URL(item);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch {
      return "";
    }
  };

  async function hash(item) {
    const digest = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(item),
    );
    return [...new Uint8Array(digest)]
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  async function fetchJson(provider, url) {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const raw = await response.text();
    return { provider, url, raw, hash: await hash(raw), data: JSON.parse(raw) };
  }

  function crossref(result, doi, translate) {
    const message = result.data.message || {},
      events = [
        ...(Array.isArray(message["update-to"])
          ? message["update-to"].map((item) => ({
              ...item,
              direction: "updates_related",
            }))
          : []),
        ...(Array.isArray(message["updated-by"])
          ? message["updated-by"].map((item) => ({
              ...item,
              direction: "applies_to_work",
            }))
          : []),
      ].map((item) => ({
        type: eventType(item.type),
        direction: item.direction,
        description: value(item.label || item.type),
        related_identifier: value(item.DOI || item.doi || item.id),
      })),
      versions = [];
    Object.entries(message.relation || {}).forEach(([relation, items]) => {
      if (!Array.isArray(items)) return;
      items.forEach((item) => {
        const identifier = value(item.id || item.DOI || item.doi);
        if (identifier) versions.push({ identifier, relation });
      });
    });
    return {
      provider: "crossref",
      status: "ok",
      source_url: result.url,
      response_sha256: result.hash,
      limitation: translate("crossref_limitation"),
      identity: {
        title: value((message.title || [])[0]),
        year:
          (
            message["published-print"] ||
            message["published-online"] ||
            message.issued ||
            {}
          )["date-parts"]?.[0]?.[0] || null,
        doi,
        type: value(message.type),
      },
      events,
      versions,
    };
  }

  function openAlex(result, doi, translate) {
    const item = result.data || {};
    return {
      provider: "openalex",
      status: "ok",
      source_url: result.url,
      response_sha256: result.hash,
      limitation: translate("openalex_limitation"),
      identity: {
        title: value(item.display_name || item.title),
        year: item.publication_year || null,
        doi,
        openalex: value(item.id).replace(/^https?:\/\/openalex.org\//i, ""),
        type: value(item.type),
      },
      events:
        item.is_retracted === true
          ? [
              {
                type: "retraction",
                description: translate("openalex_retracted"),
                related_identifier: doi,
              },
            ]
          : [],
      versions: item.ids?.arxiv
        ? [
            {
              identifier: value(item.ids.arxiv).replace(
                /^https?:\/\/arxiv.org\/abs\//i,
                "",
              ),
              relation: "has_preprint",
            },
          ]
        : [],
    };
  }

  async function pubmed(doi, translate) {
    const searchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term=${encodeURIComponent(`${doi}[doi]`)}`,
      search = await fetchJson("pubmed", searchUrl),
      pmid = search.data.esearchresult?.idlist?.[0];
    if (!pmid)
      return {
        provider: "pubmed",
        status: "not_found",
        source_url: searchUrl,
        response_sha256: search.hash,
        limitation: translate("pubmed_not_found_limitation"),
        identity: {},
        events: [],
        versions: [],
      };
    const url = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=${encodeURIComponent(pmid)}`,
      response = await fetch(url, {
        headers: { Accept: "application/xml" },
      });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const raw = await response.text(),
      xml = new DOMParser().parseFromString(raw, "application/xml"),
      relations = [...xml.querySelectorAll("CommentsCorrections")],
      types = [...xml.querySelectorAll("PublicationType")].map((item) =>
        value(item.textContent),
      ),
      events = relations.map((item) => ({
        type: eventType(item.getAttribute("RefType") || ""),
        direction: /in$/i.test(item.getAttribute("RefType") || "")
          ? "applies_to_work"
          : "updates_related",
        description: value(
          item.getAttribute("RefType") ||
            item.querySelector("RefSource")?.textContent,
        ),
        related_identifier: value(item.querySelector("PMID")?.textContent),
      }));
    if (
      types.some((item) => /retracted publication/i.test(item)) &&
      !events.some((item) => item.type === "retraction")
    )
      events.push({
        type: "retraction",
        description: translate("pubmed_retracted"),
        related_identifier: pmid,
      });
    return {
      provider: "pubmed",
      status: "ok",
      source_url: url,
      response_sha256: await hash(raw),
      limitation: translate("pubmed_limitation"),
      identity: {
        title: value(xml.querySelector("ArticleTitle")?.textContent),
        year:
          Number(value(xml.querySelector("PubDate > Year")?.textContent)) ||
          null,
        doi,
        pmid,
      },
      events,
      versions: relations
        .map((item) => ({
          identifier: value(item.querySelector("PMID")?.textContent),
          relation: value(item.getAttribute("RefType"))
            .replace(/([a-z])([A-Z])/g, "$1_$2")
            .toLowerCase(),
        }))
        .filter((item) => item.identifier),
    };
  }

  function createController(translate) {
    const panel = document.getElementById("integrity-network"),
      summary = document.getElementById("integrity-summary"),
      providers = document.getElementById("integrity-providers"),
      graph = document.getElementById("integrity-graph"),
      gaps = document.getElementById("integrity-gaps"),
      button = document.getElementById("integrity-json");
    let current = null;
    const element = (tag, className, content) => {
      const item = document.createElement(tag);
      if (className) item.className = className;
      if (content !== undefined) item.textContent = content;
      return item;
    };
    const render = () => {
      if (!current) return;
      panel.hidden = false;
      button.disabled = false;
      summary.textContent = `${translate("integrity_checked_at")}: ${current.checked_at} · ${translate("integrity_status")}: ${translate(current.status.toLowerCase())}`;
      providers.replaceChildren();
      current.provider_checks.forEach((check) => {
        const card = element("article", "integrity-provider");
        card.append(
          element("strong", "", `${check.provider} · ${check.status}`),
          element("p", "muted", check.limitation),
        );
        if (check.response_sha256)
          card.append(
            element("code", "", `SHA-256 ${check.response_sha256}`),
          );
        if (check.source_url) {
          const paragraph = element("p"),
            link = element("a", "", translate("open_check_source"));
          link.href = safeUrl(check.source_url);
          link.target = "_blank";
          link.rel = "noreferrer";
          paragraph.append(link);
          card.append(paragraph);
        }
        providers.append(card);
      });
      graph.replaceChildren(element("strong", "", translate("version_relations")));
      const rootNode = current.version_graph.nodes[0];
      if (rootNode)
        graph.append(
          element(
            "p",
            "integrity-root",
            `${translate("root_version")}: ${rootNode.id} · ${rootNode.role}`,
          ),
        );
      const relations = element("ul");
      if (current.version_graph.edges.length)
        current.version_graph.edges.forEach((edge) =>
          relations.append(
            element(
              "li",
              "",
              `${edge.source} —${edge.relation}→ ${edge.target} (${edge.provider})`,
            ),
          ),
        );
      else
        relations.append(
          element("li", "muted", translate("no_version_relations")),
        );
      graph.append(relations);
      gaps.replaceChildren(element("strong", "", translate("coverage_gaps")));
      const gapList = element("ul");
      current.coverage_gaps.forEach((gap) =>
        gapList.append(
          element(
            "li",
            "",
            `${gap.provider} / ${gap.status}: ${gap.limitation}`,
          ),
        ),
      );
      gaps.append(gapList);
    };
    const run = async (doi, crossrefResult) => {
      crossrefResult.hash = await hash(crossrefResult.raw);
      const checkedAt = new Date().toISOString(),
        checks = [crossref(crossrefResult, doi, translate)],
        openAlexUrl = `https://api.openalex.org/works/${encodeURIComponent(`https://doi.org/${doi}`)}`,
        settled = await Promise.allSettled([
          fetchJson("openalex", openAlexUrl).then((item) =>
            openAlex(item, doi, translate),
          ),
          pubmed(doi, translate),
        ]);
      ["openalex", "pubmed"].forEach((provider, index) => {
        const result = settled[index];
        checks.push(
          result.status === "fulfilled"
            ? result.value
            : {
                provider,
                status: "error",
                source_url:
                  provider === "openalex"
                    ? openAlexUrl
                    : "https://pubmed.ncbi.nlm.nih.gov/",
                response_sha256: "",
                limitation: `${translate("check_failed")}: ${value(result.reason?.message || result.reason)}`,
                identity: {},
                events: [],
                versions: [],
              },
        );
      });
      checks.push({
        provider: "crossmark",
        status: "manual_required",
        source_url: `https://crossmark.crossref.org/dialog/?doi=${encodeURIComponent(doi)}`,
        response_sha256: "",
        limitation: translate("crossmark_limitation"),
        identity: {},
        events: [],
        versions: [],
      });
      const events = checks.flatMap((check) =>
          check.events.map((event) => ({ ...event, provider: check.provider })),
        ),
        highRisk = [
          ...new Set(
            events
              .map((event) => event.type)
              .filter((type, index) => {
                const event = events[index];
                return (
                  event.direction !== "updates_related" &&
                  [
                    "retraction",
                    "withdrawal",
                    "expression_of_concern",
                  ].includes(type)
                );
              }),
          ),
        ],
        edges = checks.flatMap((check) =>
          check.versions.map((version) => ({
            source: version.identifier,
            target: doi,
            relation: version.relation,
            provider: check.provider,
          })),
        ),
        coverageGaps = checks
          .filter((check) => check.status !== "ok")
          .map((check) => ({
            provider: check.provider,
            status: check.status,
            limitation: check.limitation,
          })),
        identities = checks.filter((check) => check.status === "ok").map((check) => ({
          provider: check.provider,
          ...check.identity,
        })),
        work = identities.find((item) => item.provider === "crossref") || identities[0] || { doi },
        role = /posted-content|preprint/i.test(value(work.type))
          ? "preprint"
          : /journal-article|article|proceedings/i.test(value(work.type))
            ? "version_of_record"
            : "scholarly_work",
        identifierClaims = {};
      for (const identity of identities)
        for (const kind of ["doi", "pmid", "openalex", "arxiv"])
          if (value(identity[kind]))
            (identifierClaims[kind] ||= []).push({
              provider: identity.provider,
              value: value(identity[kind]),
            });
      current = {
        schema_version: 1,
        kind: "research-integrity-network",
        checked_at: checkedAt,
        status: highRisk.length
          ? "REVIEW_REQUIRED"
          : coverageGaps.length
            ? "NO_KNOWN_ISSUES_WITH_LIMITATIONS"
            : "NO_KNOWN_ISSUES",
        query: { kind: "doi", value: doi },
        work,
        identifier_claims: identifierClaims,
        provider_checks: checks,
        integrity_events: events,
        high_risk_events: highRisk,
        coverage_gaps: coverageGaps,
        version_graph: {
          nodes: [{ id: doi, role }],
          edges,
        },
        interpretation: translate("integrity_interpretation"),
      };
      render();
      return current;
    };
    const reset = () => {
      current = null;
      panel.hidden = true;
      button.disabled = true;
    };
    button.addEventListener("click", () => {
      if (!current) return;
      const url = URL.createObjectURL(
          new Blob([JSON.stringify(current, null, 2) + "\n"], {
            type: "application/json",
          }),
        ),
        link = document.createElement("a");
      link.href = url;
      link.download = "integrity.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    return { run, render, reset };
  }

  return { createController };
})();
