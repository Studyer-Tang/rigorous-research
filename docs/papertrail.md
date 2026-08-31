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
      "note": "The population and time window match the report claim."
    }
  ]
}
```

Allowed verdicts are `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, `NOT_FOUND`, `UNVERIFIABLE`, and `UNREVIEWED`.

Availability values should be `available`, `unavailable`, `not_applicable`, or `unknown`. Publication status is deliberately free text so providers can preserve distinctions such as `active`, `corrected`, `retracted`, or `unknown`.

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

## Publish with GitHub Pages

The repository includes a manually triggered `Publish PaperTrail demo` workflow. It generates the worked example entirely inside GitHub Actions and deploys only the resulting static `index.html` and `audit.json`—not the source tree, local files, environment variables, or credentials.

To enable it for a fork:

1. Open the repository's **Settings → Pages** page.
2. Under **Build and deployment**, choose **GitHub Actions** as the source.
3. Open **Actions → Publish PaperTrail demo → Run workflow**.
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
