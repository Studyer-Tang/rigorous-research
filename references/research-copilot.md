# Research Copilot

Research Copilot connects model-assisted planning to reproducible local checks. It can prepare context for mathematics, statistics, or finance, but its automatic verifier currently handles mathematical identity, counterexample, and polynomial-bound subclaims only. Statistical identification and financial validity remain governed by the existing domain tools and inference contracts.

For a skill-only installation without the unified CLI, replace `rigorous-research copilot` with `python scripts/research_copilot.py`, and `rigorous-research workspace` with `python scripts/research_workspace.py`, from the skill directory. Install SymPy before mathematical verification.

## Reproduce the complete workflow offline

Install the toolkit with `python -m pip install -e ".[math]"`, then run:

```text
rigorous-research workspace init build copilot-demo --domain mathematics --question "Is x*(1-x) nonnegative on [0,1]?" --claim "For every real x in [0,1], x*(1-x) >= 0."
rigorous-research copilot prepare build/copilot-demo/workspace.json --output build/packet.json
rigorous-research copilot advise build/packet.json --response assets/copilot-model-response.json --output build/advice.json
rigorous-research copilot verify build/copilot-demo/workspace.json --packet build/packet.json --advice build/advice.json --output build/verification.json
```

Use a fresh workspace slug if the demo already exists. The frozen response is a hand-authored replay fixture, not the claimed output of a live frontier model. The result proves the proposed polynomial subclaim. The inference case stays `OPEN` because its contract, evidence registration, and independent review have not been completed.

## Use your usual AI chat

1. Run `copilot prepare` against your workspace.
2. Inspect `packet.json`, then attach it to the chat you want to use. Its `instructions` and `response_schema` describe the required response. Ask for concrete next steps, falsifiers, and mathematical checks.
3. Save the returned JSON object as a local file and pass it to `copilot advise --response`.
4. Run `copilot verify` against the same workspace. Inspect every certificate and the relationship between its expression and your original claim.

The packet includes the question, contract, claim/assumption/check text, proof-obligation states, statistical applicability, source citations, and task/release gaps. It does not load source PDFs, datasets, raw artifacts, or evidence-file contents. Research text inside the packet can still be confidential; `prepare` sends nothing. Sharing it through a chat or API is a separate action initiated by the user.

## Connect an API model

The toolkit has no bundled model, subscription, or key. Configure the key through `RESEARCH_AI_API_KEY` (or choose another variable with `--api-key-env`). Choose the exact model ID supported by your account; no model is silently substituted.

PowerShell example, after setting `RESEARCH_AI_API_KEY` and `RESEARCH_AI_MODEL` in your environment:

```powershell
rigorous-research copilot advise build/packet.json --provider openai-responses --endpoint https://api.openai.com/v1 --model "$env:RESEARCH_AI_MODEL" --output build/advice.json
```

OpenAI Responses requests use `text.format` with strict JSON Schema and `store: false`, and reject incomplete or refused responses. The implementation follows the [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs). Structured output constrains the response format, not scientific truth.

For another provider that implements Chat Completions, use `--provider openai-compatible --endpoint <your-base-url> --model <your-model-id>`. This adapter requests JSON mode; compatibility depends on the provider. Local validation still enforces the proposal shape.

For an installed local Ollama model:

```powershell
rigorous-research copilot advise build/packet.json --provider ollama --endpoint http://127.0.0.1:11434 --model "$env:RESEARCH_AI_MODEL" --output build/advice.json
```

Ollama requests use its schema-based `format` field. Remote endpoints require HTTPS; loopback HTTP is supported for local services. Credentials in URLs, query strings, and redirects are rejected. There is one request with a 120-second timeout and a 2 MB response limit, with no automatic retry. Errors should be inspected before making another potentially billable call. Provider tests use deterministic replay, not paid live requests.

## Proposal and verification contracts

Every action identifies an existing task/claim or uses an empty ID for unassigned scoping. It contains `objective`, `rationale`, `falsifier`, `search_queries`, and `tests`. Search queries are suggestions; Copilot does not execute a literature search or treat a suggested citation as evidence. Call the literature tools separately when appropriate.

Each test has `operation`, `lhs`, `rhs`, `symbols`, `lower`, `upper`, and `values`. Unused interval fields are empty strings and unused values are an empty array. The [replay fixture](../assets/copilot-model-response.json) is a complete example.

- `identity`: explicit exact symbolic equality. General non-rational simplification remains diagnostic.
- `counterexample`: exact rational arithmetic on a finite grid, at most 1,000 visited points. No witness means `INCONCLUSIVE`.
- Negative fractional grid values are passed through an internal JSON file so they cannot be misread as command options. The direct math CLI also accepts `--grid-file` with an array such as `["-1/2", "0", "1/2"]`.
- `bound`: one-variable polynomial `lhs >= rhs` on a closed rational interval. Copilot limits subdivision depth to 6; the direct CLI supports up to 10 and degree up to 40.

At most 8 actions, 4 tests per action, and 12 tests total are accepted. Each proposal runs a producer and an independent checker in separate child processes sharing a 30-second default timeout (`--timeout` accepts 1–120 seconds). Total time can therefore approach 12 times the selected timeout; this is not a CPU or memory sandbox. Model output cannot supply commands, file paths, verdicts, or arbitrary executable tools. Input expressions are parsed using the restricted arithmetic parser.

Verification binds the packet to the current workspace and case file hashes. If either file changes, prepare new context and obtain/review fresh advice. It also checks existing workspace artifact integrity. These are tamper-evident local records, not authenticated model signatures.

Inspect `execution_status`, the nested certificate, and the independent verification result. `CHECKED` means the backend completed, which can yield a proof, a counterexample, or an inconclusive result. A timeout or parsing error yields no certificate. A returned proof does not validate the model's translation, quantifiers, omitted assumptions, or connection to the research claim. No task is marked complete and no evidence or case verdict is written automatically. Strict receipts accept independently established identities and interval bounds. Counterexamples remain refutations and cannot be relabeled as established identities. See [proof assurance](proof-assurance.md) for case integration.

CLI exit codes: `prepare`/`advise` return 0 on success and 2 on invalid input or service errors. `verify` returns 0 when all requested backends complete (including negative/inconclusive mathematical results), 1 when any backend errors or times out, and 2 when context/proposal validation fails. An empty proposal records `NO_CHECKS`.
