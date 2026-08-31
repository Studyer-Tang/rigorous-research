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

`review_method` can be `human`, `ai_assisted`, `automated`, or `unknown`. AI-assisted rows are drafts: PaperTrail rejects a decisive `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `CONTRADICTED` verdict until a human or governed automated review takes responsibility. Multiple reviewers may record separate rows for one claim/source pair. Supporting and contradicting reviewer verdicts on the same pair fail the consensus checklist instead of being silently averaged.

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
  --demo-report examples/papertrail-demo/report.md \
  --demo-manifest examples/papertrail-demo/evidence.json
```

This produces:

- `index.html`: an interactive browser-only tool with paste, file selection, local audit preview, and JSON/HTML downloads;
- `demo/index.html`: the immutable audit generated by the Python implementation;
- `demo/audit.json`: its machine-readable evidence packet;
- `.nojekyll`: a GitHub Pages compatibility marker.

The interactive page reads selected files with the browser file API. It does not send them to this project, GitHub, or an AI model. An explicit DOI lookup sends only the DOI to Crossref. The Python CLI remains the release/CI path; the playground is designed for exploration and drafting evidence manifests.

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

## Run the worked example

```text
rigorous-research audit examples/papertrail-demo/report.md \
  --manifest examples/papertrail-demo/evidence.json \
  --output-dir build/papertrail-demo
```

Open `build/papertrail-demo/index.html` locally. One claim is supported and two intentionally incorrect claims are contradicted.
