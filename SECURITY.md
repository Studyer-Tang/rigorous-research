# Security and privacy

Report a suspected vulnerability privately through the repository owner's GitHub security-advisory channel. Do not open a public issue containing credentials, private datasets, unpublished research, or an exploit that could alter sealed evidence.

## Trust boundaries

- `research_workspace.py run` executes the command supplied by the user. It records the run but is not a sandbox or an authorization layer.
- Literature and financial-data retrieval consume untrusted network responses. Preserve raw responses and inspect their provenance before treating them as evidence.
- Hashes detect later changes; they do not establish that the original data, reviewer identity, or scientific interpretation was trustworthy.
- Review identities are self-declared unless an external authentication or signature system is added.
- Optional backends such as SymPy and Lean have their own trust assumptions and version-specific behavior.

## Safe publication checklist

Before publishing a workspace or example:

1. Run `python scripts/skill_quality.py` on the repository.
2. Search the complete release packet for local paths, credentials, personal identifiers, proprietary data, and unpublished material.
3. Confirm that dataset licenses permit redistribution; a checksum and citation do not grant redistribution rights.
4. Use a blinded review packet when review independence matters, and verify its receipt after any author-side change.
5. Re-run the relevant release validator and verify every attached receipt from a clean checkout.

Tagged releases build Python and Agent Plugin artifacts in GitHub Actions, generate a CycloneDX dependency SBOM, and request GitHub build-provenance attestations. These controls describe the build inputs; they do not independently validate scientific conclusions inside a research packet.

The quality validator intentionally detects only high-confidence secret and local-path patterns. It is a guardrail, not a substitute for human privacy and license review.
