# PaperTrail audit

PaperTrail turns a Markdown report and a versioned evidence manifest into a claim-to-source matrix, a reproducibility checklist, machine-readable JSON, and a self-contained HTML report.

It does not infer support merely because a citation appears after a sentence. Every `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `CONTRADICTED` assessment must be recorded with an exact quote and locator. Missing review remains visible as `UNREVIEWED`.

## Write claims

Add a `Claims`, `Key Claims`, `Conclusions`, `结论`, `主要结论`, or `核心结论` section to a Markdown report. Use Pandoc-style citation keys:

```markdown
## Claims

- [C001] The measured value increased by 18%. [@study-2026]
- [C002] The result generalizes to every population. [@study-2026; @replication-2026]
```

Explicit `C...` identifiers are recommended because evidence rows refer to them. If identifiers are omitted, PaperTrail assigns `C001`, `C002`, and so on in document order.

## Record sources and evidence

Create a JSON manifest:

```json
{
  "sources": [
    {
      "id": "study-2026",
      "title": "Controlled study",
      "authors": ["A. Researcher"],
      "year": 2026,
      "doi": "10.0000/example",
      "url": "https://example.org/study",
      "publication_status": "active",
      "integrity_checked_at": "2026-08-31",
      "integrity_url": "https://example.org/study",
      "version": "version of record",
      "version_url": "https://example.org/study",
      "version_conflict": false,
      "version_notes": "No conflicting result-bearing version is known.",
      "data_availability": "available",
      "data_url": "https://example.org/data",
      "code_availability": "unavailable"
    }
  ],
  "evidence": [
    {
      "claim_id": "C001",
      "source_id": "study-2026",
      "verdict": "SUPPORTED",
      "quote": "The measured value increased by 18%.",
      "locator": "Results, paragraph 2",
      "note": "The population and time window match the report claim.",
      "reviewer_id": "reviewer-a",
      "reviewed_at": "2026-08-31",
      "review_method": "human",
      "review_receipt": "optional portable receipt identifier"
    }
  ]
}
```

Allowed verdicts are `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, `NOT_FOUND`, `UNVERIFIABLE`, and `UNREVIEWED`.

Availability values should be `available`, `unavailable`, `not_applicable`, or `unknown`. Publication status is deliberately free text so providers can preserve distinctions such as `active`, `corrected`, `retracted`, or `unknown`.

`version_conflict` must be `true`, `false`, or `null`/omitted. PaperTrail fails the checklist for a recorded conflict, warns when the field is unknown, and passes only when every cited source explicitly records `false`. A `retracted`, `withdrawn`, or `expression_of_concern` publication status also fails the integrity check. These are recorded checks—not live promises that a publisher has never changed the source.

`review_method` can be `human`, `ai_assisted`, `automated`, or `unknown`. AI-assisted and automated rows may remain drafts or non-decisive records, but PaperTrail accepts a decisive `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `CONTRADICTED` verdict only with `review_method: human`, a non-AI reviewer ID, an exact quote, and a locator. Multiple reviewers may record separate rows for one claim/source pair. Supporting and contradicting reviewer verdicts on the same pair fail the consensus checklist instead of being silently averaged.

The browser human-review desk writes its decisions back to the local manifest and maintains a top-level `review_history` array. Each `created`, `updated`, or `revoked` event records its evidence ID, time, reviewer, prior state, resulting state when present, and the AI recommendation visible at confirmation time. Revocation removes the active evidence row but keeps its prior state in history. This local history is provenance, not authenticated identity; high-stakes workflows should additionally sign or externally bind the exported manifest.

Browser-selected PDF evidence may include a portable anchor:

```json
{
  "kind": "pdf_text",
  "file_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "page": 3,
  "start": 120,
  "end": 188,
  "rects": [{"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.04}]
}
```

The anchor is stored in the evidence row as `anchor`. `kind` is `pdf_text` for embedded text or `pdf_ocr` for locally recognized text. Normalized rectangles are inspection hints; the exact quote, page locator, and PDF SHA-256 remain the portable verification record. OCR-derived quotes require especially careful human comparison with the rendered page.

## Import PDF, web, and DOI sources

Install the optional PDF reader:

```text
python -m pip install -e ".[papertrail]"
```

Then use the import commands:

```text
rigorous-research import pdf paper.pdf --output paper-draft.md
rigorous-research import url https://example.org/article --output article-draft.md
rigorous-research import doi 10.1234/example --output source.json
rigorous-research import assist report.md --output assistance.json
```

PDF extraction preserves page boundaries and records the input SHA-256. It does not perform OCR; image-only scans fail visibly. Web import removes scripts, styles, forms, navigation, and footers, restricts requests to public HTTP(S) destinations, rechecks redirects, limits response size, and never executes page code. DOI import queries Crossref and records its update metadata, but absence of a Crossref retraction notice is not proof that no integrity issue exists.

The assistance command and browser candidate button use local claim signals to prepare drafts. Their output is explicitly `DRAFT_REQUIRES_HUMAN_REVIEW`; citations, exact excerpts, locators, and reviewer provenance must still be supplied.

## Generate the static report

```text
rigorous-research audit report.md \
  --manifest evidence.json \
  --output-dir papertrail-site
```

The output directory contains:

- `index.html`: a self-contained, responsive report with claim filters;
- `audit.json`: the complete audit record, input hashes, summary, and checklist.

No server, database, JavaScript build system, or external font is required. The directory can be published by GitHub Pages as-is. Use `--strict` in CI when every released claim must resolve to `SUPPORTED`.

## Build the browser playground

```text
rigorous-research papertrail \
  --output-dir build/papertrail-site \
  --demo-report examples/papertrail-cartea/report.md \
  --demo-manifest examples/papertrail-cartea/evidence.json
```

This produces:

- `index.html`: an interactive browser-only tool with paste, file selection, local audit preview, and JSON/HTML downloads;
- `demo/index.html`: the immutable audit generated by the Python implementation;
- `demo/audit.json`: its machine-readable evidence packet;
- `.nojekyll`: a GitHub Pages compatibility marker.

The interactive page reads selected files with the browser file API. It does not send them to this project, GitHub, or an AI model. The PDF workspace supports files up to 50 MB, renders pages, extracts embedded text, records the file SHA-256, and attaches selected passages to claim/source pairs as `UNREVIEWED` evidence. It turns each page into short passage cards: click a card once to select it, then attach it. Manual text dragging remains available in a collapsed precision editor. The human-review desk can promote an inspected excerpt to a decisive verdict, edit it, or revoke it while preserving history. An explicit DOI lookup sends only the DOI to Crossref, OpenAlex, and PubMed; the report text is not included. The Python CLI remains the release/CI authority.

The playground source is intentionally separated by responsibility under `scripts/papertrail_frontend/`: HTML defines structure, CSS defines presentation, and JavaScript owns browser behavior. `papertrail_web.py` is only the static-site builder; it no longer contains the complete frontend as an embedded Python string.

PDF.js is downloaded from a pinned jsDelivr URL only after a PDF is selected. OCR is never automatic: its button downloads a pinned Tesseract.js runtime and the selected English or Chinese/English language data, then recognizes the rendered page locally. These optional downloads disclose network activity but do not transmit the PDF or page image. Self-hosters may vendor the pinned assets and replace the constants in `papertrail_web.py` when an offline deployment is required.

The playground supports English and Simplified Chinese. It initially follows the browser language, provides a manual language selector, remembers that preference locally, and uses the selected language for the live audit and downloaded HTML report. Markdown claim headings may use either `Claims`/`Conclusions` or `结论`/`主要结论`/`核心结论`; report content is never machine-translated.

Both generated reports and the playground include an evidence graph linking claims on the left to cited sources on the right. The graph is an inspection aid; verdict text and the evidence table remain the authoritative accessible representation.

## Publish with GitHub Pages

The repository includes a manually triggered `Publish PaperTrail site` workflow. It builds the browser playground and worked example entirely inside GitHub Actions and deploys only the resulting static site—not the source tree, local files, environment variables, or credentials.

To enable it for a fork:

1. Open the repository's **Settings → Pages** page.
2. Under **Build and deployment**, choose **GitHub Actions** as the source.
3. Open **Actions → Publish PaperTrail site → Run workflow**.
4. After the workflow succeeds, open the deployment URL shown in the job summary.

For a project repository named `rigorous-research`, the normal address is `https://<account>.github.io/rigorous-research/`. A root address such as `https://<account>.github.io/` requires a repository named exactly `<account>.github.io`.

The workflow is intentionally manual while PaperTrail is evolving. It can later be changed to publish on every push to `main` after the public content and release policy are stable.

## Run the real-paper experiment

```text
rigorous-research audit examples/papertrail-cartea/report.md \
  --manifest examples/papertrail-cartea/evidence.json \
  --output-dir build/papertrail-cartea
```

Open `build/papertrail-cartea/index.html` locally. The experiment includes one qualified claim, one intentionally overgeneralized negative control, and one Figure 5 claim. All source excerpts intentionally remain `UNREVIEWED`; use the browser human-review desk to confirm them after inspecting the source PDF.
