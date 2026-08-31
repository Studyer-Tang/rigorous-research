# Governed AI Reviewer

The governed reviewer automates draft work, not judgment. It can extract candidate claims, recommend sources that may support or contradict them, and flag likely overgeneralization, causal overreach, or unclear population scope. Every result remains `AI_DRAFT` until a named human confirms an exact source passage.

## Local deterministic draft

```text
rigorous-research ai-review draft report.md \
  --manifest evidence.json \
  --output ai-review-draft.json
```

This mode sends no data anywhere and requires no model. It is also the mode available in the public browser playground. Candidate direction is based on the best-matching local passage, not a verdict and not source-level sentiment.

## Local model with Ollama

```text
rigorous-research ai-review draft report.md \
  --manifest evidence.json \
  --provider ollama \
  --endpoint http://127.0.0.1:11434 \
  --model qwen3:8b \
  --output ai-review-draft.json
```

## User-provided OpenAI-compatible endpoint

Provide the secret only through an environment variable. Its value is used in the request header and is never written to a draft or report.

```powershell
$env:PAPERTRAIL_AI_API_KEY = "your-key"
rigorous-research ai-review draft report.md `
  --manifest evidence.json `
  --provider openai-compatible `
  --endpoint https://your-provider.example/v1 `
  --model your-model `
  --output ai-review-draft.json
```

Only `rationale`, additional scope issues, and search suggestions are accepted from a model response. A model-supplied verdict is discarded.

## Human confirmation

A decisive judgment requires a human reviewer ID, an exact quote, and a locator:

```text
rigorous-research ai-review confirm ai-review-draft.json \
  --claim-id C001 \
  --source-id source-1 \
  --verdict CONTRADICTED \
  --quote "Exact words from the source" \
  --locator "p. 7, Results, paragraph 2" \
  --reviewer-id reviewer-name \
  --output confirmation.json
```

The CLI confirmation contains a PaperTrail-compatible evidence row, the human review method, time, and a SHA-256 binding to the draft. It does not automatically modify the evidence manifest or bypass independent review.

The browser human-review desk provides the interactive write-back path. It can reuse an `UNREVIEWED` excerpt, requires a non-AI reviewer ID plus exact quote and locator for decisive judgments, appends create/update/revoke events to `review_history`, and displays whether the saved human direction agrees with the current AI suggestion. All operations remain in the browser until the user downloads or copies the manifest.
