"""Independent set translation, optimizer certificates and assignment replay."""

import hashlib
import json
import math
import sys
import tempfile
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from certificate_verifier import verify
from research_agent.core import Study, digest


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["sha256"].items():
        require(hashlib.sha256((HERE / relative).read_bytes()).hexdigest() == expected, f"checksum: {relative}")
    prior = json.loads((HERE / "../frankl-frontier/ledger.json").read_text(encoding="utf-8"))
    archive = json.loads((HERE / "ledger.json").read_text(encoding="utf-8"))
    require(archive["state"]["objective_status"] == "UNRESOLVED", "original objective must remain unresolved")
    require(archive["state"]["execution"] == "READY", "ongoing research must remain resumable")
    require(len(archive["actions"]) == 8, "unexpected action count")
    earlier = {r["id"] for r in prior["actions"] if r["execution"] == "SUCCEEDED"}
    for index, record in enumerate(archive["actions"], 16):
        require(record["id"] == index, "action sequence changed")
        require(digest(record["proposal"]["action"]) == record["fingerprint"], "action hash mismatch")
        require(digest(record["result"]) == record["result_hash"], "result hash mismatch")
        require(set(record["proposal"]["evidence"]) <= earlier, "invalid historical references")
        if record["execution"] == "SUCCEEDED":
            earlier.add(index)
    records = {r["id"]: r for r in archive["actions"]}
    assignment = json.loads((HERE / "assignment.json").read_text(encoding="utf-8"))
    family = [frozenset(i for i in range(4) if mask & (1 << i)) for mask in assignment["family_masks"]]
    require(len(family) == len(set(family)) == 9 and family[-1] == frozenset(range(4)), "changed family")
    require(
        set(family[:-1]) == {frozenset(i for i in range(3) if mask & (1 << i)) for mask in range(8)}, "changed cube"
    )
    counts = Counter(a | b for a in family for b in family)
    require(set(counts) == set(family), "family not union-closed")
    require([counts[s] for s in family] == assignment["ordered_union_multiplicities"], "incorrect multiplicities")
    with tempfile.TemporaryDirectory(prefix="coupling-replay-") as folder:
        study = Study.create(folder, "replay", "Replay an auxiliary monotonicity counterexample; Frankl remains open")
        for action_id, theta, bound, relation in [(17, 4, "107/50", ">="), (18, 8, "53/25", "<=")]:
            record = records[action_id]
            args = record["proposal"]["action"]["arguments"]
            claim = record["result"]["certificate"]["claim"]
            require(
                claim["kernel"] == args["kernel"] and claim["labels"] == args["labels"], "action translation mismatch"
            )
            require(claim["bound"] == bound and claim["relation"] == relation, "changed entropy target")
            for i, a in enumerate(family):
                for j, b in enumerate(family):
                    require(Fraction(claim["kernel"][i][j]) == Fraction(1, counts[a | b] ** theta), "wrong kernel")
                    require(claim["labels"][i][j] == family.index(a | b), "wrong event label")
            checked = verify(record["result"]["certificate"])
            require(checked["status"] == "ESTABLISHED", "optimizer certificate rejected")
            result = study.submit({**record["proposal"], "evidence": []}, study.state()["revision"])
            require(
                result["execution"] == "SUCCEEDED" and result["result"]["status"] == "ESTABLISHED",
                "worker replay failed",
            )
    require(verify(records[22]["result"]["certificate"])["status"] == "REFUTED", "limiting entropy check changed")
    # A subset dynamic program independently verifies the original permutation enumeration.
    dp = {0: (1, 1, [])}
    for used in range(1 << 9):
        if used not in dp or used == (1 << 9) - 1:
            continue
        best, ways, path = dp[used]
        i = used.bit_count()
        for j in range(9):
            if used & (1 << j):
                continue
            new = used | (1 << j)
            value = best * counts[family[i] | family[j]]
            if new not in dp or value < dp[new][0]:
                dp[new] = (value, ways, path + [j])
            elif value == dp[new][0]:
                dp[new] = (value, dp[new][1] + ways, dp[new][2])
    best, ways, path = dp[(1 << 9) - 1]
    require(
        (best, ways, path) == (assignment["minimum_product"], assignment["minimizers"], assignment["permutation"]),
        "assignment disagreement",
    )
    require(ways == 1 and path == [0, 1, 2, 3, 4, 5, 6, 8, 7], "incorrect unique optimizer")
    require(assignment["permutations_checked"] == math.factorial(9), "incomplete historical enumeration count")
    print(
        "PASS: 8 new actions; exact family translation; 3 certificates; 2 optimizer reruns; independent assignment DP."
    )
    print("General monotonicity is refuted; the full Frankl conjecture remains unresolved.")


if __name__ == "__main__":
    main()
