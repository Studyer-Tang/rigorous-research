# Cartea-Jin-Shi PaperTrail experiment / 论文贯穿实验

This public, redistributable fixture exercises PaperTrail with *The Limited Virtue of Complexity in a Noisy World* (Cartea, Jin, and Shi, 2025). It does not include the copyrighted source PDF or its full extracted text.

这个可公开再分发的夹具使用 Cartea、Jin 与 Shi（2025）的论文对 PaperTrail 做贯穿测试，但不包含原始 PDF 或全文抽取内容。

## What the experiment tests / 测试内容

- A qualified claim about the interaction between complexity, noise, data quality, and infrastructure.
- An intentionally overgeneralized claim that should trigger `possible_overgeneralization` and possible contradiction suggestions.
- A Figure 5 claim bounded to the paper's sample and experiment.
- Crossref `posted-content` and OpenAlex `preprint` identity agreement.
- PubMed `not_found` as a domain-coverage limitation, not a network error.
- Crossmark as an explicit `manual_required` gap.
- AI excerpts remain `UNREVIEWED`; a decisive verdict must be saved by a human in the browser review desk.

## Reproduce locally / 本地复现

```text
rigorous-research integrity check 10.2139/ssrn.5202064 \
  --checked-at 2026-08-31T00:00:00+00:00 \
  --fixture crossref=examples/papertrail-cartea/fixtures/crossref.json \
  --fixture openalex=examples/papertrail-cartea/fixtures/openalex.json \
  --fixture pubmed=examples/papertrail-cartea/fixtures/pubmed-search.json \
  --output-dir build/cartea-integrity

rigorous-research ai-review draft examples/papertrail-cartea/report.md \
  --manifest examples/papertrail-cartea/evidence.json \
  --output examples/papertrail-cartea/ai-review-draft.json

rigorous-research audit examples/papertrail-cartea/report.md \
  --manifest examples/papertrail-cartea/evidence.json \
  --output-dir build/cartea-audit
```

The provider fixtures are deliberately minimal deterministic replay payloads containing only fields used by the parser. The generated `integrity.json` records their hashes. Live provider results can change after the stated check time.

提供商夹具是最小化、确定性的重放数据，只保留解析器使用的字段；生成的 `integrity.json` 会记录其哈希。实时查询结果可能在检查日期之后发生变化。
