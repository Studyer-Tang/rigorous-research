"""Audit a real live-host record and rerun selected tools; this is not model reasoning replay."""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from integer_certificate_verifier import verify
from research_agent.core import digest
from research_agent.worker import produce
from research_workspace import load, validate_workspace


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = json.loads((HERE / "artifact-manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["sha256"].items():
        require(hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, "Archive hash changed: " + name)
    actions = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "actions").glob("*.json"))]
    families, checked = [], 0
    for action in actions:
        require(digest(action["proposal"]["action"]) == action["fingerprint"], "Changed proposal")
        require(digest(action["result"]) == action["result_hash"], "Changed recorded result")
        certificate = action["result"].get("certificate")
        if certificate is None:
            continue
        require(verify(certificate)["status"] == action["result"]["status"], "Certificate status changed")
        checked += 1
        if certificate["operation"] == "unit-fraction-polynomial-family":
            families.append(certificate["claim"])
    covered = set()
    for claim in families:
        n = claim["n"]
        if len(n) != 2 or n[1] not in (24, 840):
            continue
        base, modulus = n
        require(claim["numerator"] == 4 and claim["distinct"] is True, "Coverage uses the wrong original equation")
        require(base - modulus < 3 <= base, "Coverage skips an initial input")
        covered.update(r for r in range(840) if (r - base) % modulus == 0)
    gaps = sorted(set(range(840)) - covered)
    require(gaps == [1, 121, 169, 289, 361, 529], "Unexpected coverage gap")
    # Check the stated unbroken finite prefix, rather than trusting its count in the report.
    passed = set()
    for action in actions:
        if action["proposal"]["action"]["tool"] != "egyptian_scan":
            continue
        c = action["result"]["certificate"]
        if c["claim"]["width"] == 8:
            for window in c["windows"]:
                if verify(window)["status"] == "ESTABLISHED":
                    passed.add(window["claim"]["denominator"])
    require(set(range(25, 99986, 24)) <= passed, "Eight-step finite prefix has a gap")
    rerun = (7, 8, 10, 11, 32, 33, 65, 66, 67)
    for action in actions:
        if action["id"] not in rerun:
            continue
        fresh = produce(action["proposal"]["action"])["certificate"]
        require(fresh == action["result"]["certificate"], "Tool rerun changed its exact certificate")
        require(verify(fresh)["status"] == action["result"]["status"], "Tool rerun did not verify")
    path, workspace = load(HERE / "workspace.json")
    errors, warnings = validate_workspace(workspace, path, release=True)
    require(not errors, "Release validation failed: " + "; ".join(errors))
    print(json.dumps(dict(actions=len(actions),certificates_rechecked=checked,polynomial_families=len(families),
                          representative_tools_rerun=len(rerun),covered_residues=len(covered),uncovered=gaps,
                          original_goal="INCONCLUSIVE",release_warnings=warnings), indent=2))


if __name__ == "__main__":
    main()
