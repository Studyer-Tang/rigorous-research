"""Small proof-obligation graph with derived, evidence-bound resolution states."""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from typing import Any

from research_io import canonical_hash, load_json_object, resolve_locator, sha256

SIDE_CONDITIONS = {
    "division": "nonzero",
    "matrix-inverse": "invertible",
    "limit-interchange": "interchange_justified",
    "generalization": "exhaustive_argument",
}
KINDS = ("translation", "domain", "proof", "counterexample", "theorem-application", "finite-check")


def initial_obligations(claim_id: str = "C001") -> list[dict[str, Any]]:
    return [
        {
            "id": "P001",
            "target_claim": claim_id,
            "kind": "translation",
            "statement": "Check the original claim's types, domain, quantifiers, assumptions, and scope against the proposed derivation.",
            "coverage": "full",
            "depends_on": [],
            "assumption_ids": [],
            "operation": "plain",
            "side_conditions": {},
        },
        {
            "id": "P002",
            "target_claim": claim_id,
            "kind": "proof",
            "statement": "Establish the scoped claim or replace this obligation with an admissible counterexample.",
            "coverage": "full",
            "depends_on": ["P001"],
            "assumption_ids": [],
            "operation": "plain",
            "side_conditions": {},
        },
    ]


def review_context(case: dict[str, Any]) -> str:
    """Hash shared scientific context once per graph evaluation."""
    return canonical_hash(
        {
            "claims": [
                {key: claim.get(key) for key in ("id", "statement", "scope", "assumption_ids")}
                for claim in case["claims"]
            ],
            "contract": case["contract"],
            "assumptions": case["assumptions"],
            "graph": [
                {key: value for key, value in node.items() if key != "resolution"}
                for node in case.get("proof_obligations", [])
            ],
            "statistical_contract": case.get("statistical_contract"),
        }
    )


def review_binding(
    case: dict[str, Any], obligation: dict[str, Any], evidence: dict[str, Any], context_hash: str | None = None
) -> str:
    return canonical_hash(
        {"context": context_hash or review_context(case), "obligation_id": obligation["id"], "evidence": evidence}
    )


def resolve_obligation(
    case: dict[str, Any], node: dict[str, Any], case_dir: Path, context_hash: str | None = None
) -> str:
    resolution = node.get("resolution")
    if not resolution:
        return "OPEN"
    if not isinstance(resolution, dict):
        raise ValueError("resolution must be an object")
    evidence = next((item for item in case["evidence"] if item["id"] == resolution.get("evidence_id")), None)
    if evidence is None:
        raise ValueError("resolution must reference case evidence")
    path = resolve_locator(evidence["locator"], case_dir)
    if not path.is_file() or sha256(path) != evidence.get("sha256"):
        raise ValueError("resolution evidence is missing or changed")
    if resolution.get("binding") != review_binding(case, node, evidence, context_hash):
        raise ValueError("resolution is stale after claim, assumption, obligation, or evidence changes")
    if node["coverage"] != "full" or node["kind"] == "finite-check":
        return "PARTIAL"
    if resolution.get("method") == "review":
        reviewer = resolution.get("reviewer_id", "")
        if (
            not isinstance(reviewer, str)
            or not reviewer.strip()
            or re.fullmatch(r"(?:ai|assistant|model|bot|automated)(?:[-_ ].*)?", reviewer, re.I)
        ):
            raise ValueError("review must name a human reviewer")
        if not isinstance(resolution.get("note"), str) or not resolution["note"].strip():
            raise ValueError("review must explain the checked derivation and conditions")
        return "REVIEWED"
    if resolution.get("method") != "certificate" or node["kind"] == "translation":
        raise ValueError("translation requires review; other resolutions require review or certificate")
    from certificate_verifier import verify

    certificate = load_json_object(path)
    if certificate.get("claim") != node.get("certificate_claim") or certificate.get("assumptions", {}) != node.get(
        "certificate_assumptions", {}
    ):
        raise ValueError("certificate claim or assumptions differ from the declared proof obligation")
    inputs = [resolve_locator(item["locator"], case_dir) for item in case["evidence"] if item.get("sha256")]
    result = verify(certificate, inputs)
    expected = "REFUTED" if node["kind"] == "counterexample" else "ESTABLISHED"
    if result["status"] != expected:
        raise ValueError("independent certificate check failed: " + "; ".join(result["errors"] or [result["status"]]))
    return "MACHINE_VERIFIED"


def evaluate(case: dict[str, Any], case_dir: Path) -> dict[str, Any]:
    nodes = case.get("proof_obligations", [])
    if not isinstance(nodes, list) or len(nodes) > 1000:
        raise ValueError("proof_obligations must be an array of at most 1000 entries")
    claims = {item["id"] for item in case["claims"]}
    assumptions = {item["id"]: item for item in case["assumptions"]}
    graph = {}
    for node in nodes:
        if (
            not isinstance(node, dict)
            or not isinstance(node.get("id"), str)
            or not re.fullmatch(r"P\d{3}", node["id"])
            or node["id"] in graph
        ):
            raise ValueError("proof obligations require unique P-prefixed IDs")
        if (
            not isinstance(node.get("target_claim"), str)
            or node.get("target_claim") not in claims
            or node.get("kind") not in KINDS
            or node.get("coverage") not in ("full", "partial")
        ):
            raise ValueError(f"{node['id']}: invalid claim, kind, or coverage")
        if not isinstance(node.get("statement"), str) or not node["statement"].strip():
            raise ValueError("proof obligations require an explicit statement")
        for key in ("depends_on", "assumption_ids"):
            values = node.get(key, [])
            if (
                not isinstance(values, list)
                or any(not isinstance(value, str) for value in values)
                or len(values) != len(set(values))
            ):
                raise ValueError(f"{node['id']}: {key} requires unique string IDs")
        if set(node.get("assumption_ids", [])) - assumptions.keys():
            raise ValueError(f"{node['id']}: unknown assumption")
        if (
            not isinstance(node.get("operation", "plain"), str)
            or node.get("operation", "plain") not in {"plain", *SIDE_CONDITIONS}
            or not isinstance(node.get("side_conditions", {}), dict)
        ):
            raise ValueError(f"{node['id']}: invalid operation or side conditions")
        graph[node["id"]] = node
    successors = {key: [] for key in graph}
    degrees = {}
    for key, node in graph.items():
        dependencies = node.get("depends_on", [])
        if set(dependencies) - graph.keys():
            raise ValueError(f"{key}: unknown proof dependency")
        degrees[key] = len(dependencies)
        for dependency in dependencies:
            successors[dependency].append(key)
    queue = deque(key for key in graph if not degrees[key])
    context_hash = review_context(case)
    states, errors, attacks = {}, [], []
    while queue:
        key = queue.popleft()
        node = graph[key]
        blocked = any(
            states[dependency] not in ("REVIEWED", "MACHINE_VERIFIED") for dependency in node.get("depends_on", [])
        )
        condition = SIDE_CONDITIONS.get(node.get("operation"))
        if condition:
            reference = node.get("side_conditions", {}).get(condition)
            if (
                not isinstance(reference, str)
                or reference not in node.get("depends_on", [])
                or graph[reference]["kind"] != "domain"
            ):
                errors.append(f"{key}: {condition} must reference a domain obligation in depends_on")
                blocked = True
            attacks.append(
                {
                    "obligation_id": key,
                    "check": condition,
                    "task": f"Construct a boundary or degenerate case violating {condition}; no witness does not discharge this obligation.",
                }
            )
        if any(
            assumptions[value].get("status") not in ("JUSTIFIED", "CONDITIONAL")
            for value in node.get("assumption_ids", [])
        ):
            blocked = True
        try:
            state = resolve_obligation(case, node, case_dir, context_hash)
            states[key] = "BLOCKED" if blocked else state
        except (ValueError, OSError, RuntimeError) as exc:
            states[key] = "INVALID"
            errors.append(f"{key}: {exc}")
        for child in successors[key]:
            degrees[child] -= 1
            if degrees[child] == 0:
                queue.append(child)
    if len(states) != len(graph):
        errors.append("proof dependencies contain a cycle")
        states.update({key: "BLOCKED" for key in graph if key not in states})
    return {
        "states": states,
        "errors": errors,
        "falsification_tasks": attacks,
        "warning": "REVIEWED is a local human attestation, not a machine proof or authenticated identity. Machine checks cover only the recorded subclaim.",
    }


def release_errors(case: dict[str, Any], report: dict[str, Any]) -> list[str]:
    decision = case["decision"]
    if decision["verdict"] not in ("SUPPORTED", "REFUTED"):
        return []
    target = decision["claim_id"]
    nodes = [node for node in case["proof_obligations"] if node["target_claim"] == target]
    required_kind = "counterexample" if decision["verdict"] == "REFUTED" else "proof"
    errors = []
    for kind in ("translation", required_kind):
        if not any(node["kind"] == kind for node in nodes):
            errors.append(f"headline claim requires a {kind} obligation")
    unfinished = [node["id"] for node in nodes if report["states"][node["id"]] not in ("REVIEWED", "MACHINE_VERIFIED")]
    if unfinished:
        errors.append("unclosed proof obligations: " + ", ".join(unfinished))
    return errors
