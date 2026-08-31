# Architecture

Rigorous Research separates the public PaperTrail product from the deeper research-governance engine. A module should have one primary responsibility and depend inward on validated data rather than browser state.

## PaperTrail

| Component | Responsibility |
|---|---|
| `scripts/papertrail_frontend/index.html` | Accessible page structure only |
| `scripts/papertrail_frontend/app.css` | Responsive presentation only |
| `scripts/papertrail_frontend/i18n.js` | English and Simplified Chinese interface copy |
| `scripts/papertrail_frontend/app.js` | Browser interaction, local PDF/OCR handling, and live preview |
| `scripts/papertrail_frontend/integrity-network.js` | Browser-only DOI integrity checks and coverage display |
| `scripts/papertrail_frontend/governed-review.js` | Browser-only draft recommendations and scope warnings |
| `scripts/papertrail_frontend/human-review.js` | Human-only manifest write-back, edit/revoke history, and AI/human difference display |
| `scripts/papertrail_web.py` | Copy static assets and inject the worked demo |
| `scripts/papertrail_audit.py` | Authoritative manifest validation, verdict aggregation, and static reports |
| `scripts/papertrail_import.py` | Explicit PDF, URL, DOI, and assistance imports |

The browser is a drafting surface. The Python audit implementation remains the release and CI authority.

## Research engine

| Component | Responsibility |
|---|---|
| `research_workspace.py` | Work packages, execution records, artifacts, and release validation |
| `inference_case.py` | Claims, assumptions, falsifiers, evidence roles, and calibrated verdicts |
| `research_seal.py` | Plan seals and computation receipts |
| `review_protocol.py` | Blind review packets and adjudication |
| `literature_search.py` | Multi-provider discovery and conservative deduplication |
| `research_integrity.py` | Replayable provider checks, integrity events, coverage gaps, and version graph |
| `governed_ai_reviewer.py` | Local/model-assisted drafts and mandatory human confirmation receipts |
| `math_backend.py`, `statistics_backend.py`, `finance_data.py` | Domain-specific verification |

## Dependency rule

Frontends may call validators; validators never import frontend code. Network imports produce drafts or frozen records; they never directly assign a decisive evidence verdict. AI-assisted output remains reviewable data and cannot bypass the human release gate.
