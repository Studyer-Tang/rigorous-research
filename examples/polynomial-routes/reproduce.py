"""Audit a real hosted archive, then deterministically rerun its successful mathematics."""

import hashlib
import json
import sys
import tempfile
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
    raw = (HERE / "ledger.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == manifest["ledger_sha256"], "archive checksum mismatch")
    archive = json.loads(raw)
    require(archive["state"]["objective_status"] == "UNRESOLVED", "benchmark cannot accept the research objective")
    require(len(archive["actions"]) == 17, "unexpected action count")
    expected = {
        3: "REFUTED",
        5: "ESTABLISHED",
        9: "REFUTED",
        10: "ESTABLISHED",
        12: "INCONCLUSIVE",
        13: "INCONCLUSIVE",
        15: "ESTABLISHED",
    }
    successful = set()
    with tempfile.TemporaryDirectory(prefix="polynomial-replay-") as directory:
        study = Study.create(directory, "replay", "Deterministic tool regression; no model discovery claim.")
        for index, action in enumerate(archive["actions"], 1):
            require(action["id"] == index, "action sequence changed")
            require(digest(action["proposal"]["action"]) == action["fingerprint"], "action hash mismatch")
            require(digest(action["result"]) == action["result_hash"], "result hash mismatch")
            require(set(action["proposal"]["evidence"]) <= successful, "invalid historical evidence reference")
            if action["execution"] == "SUCCEEDED":
                successful.add(index)
            if index == 2:
                require(action["execution"] == "FAILED", "historical failure was erased")
            if index not in expected:
                continue
            certificate = action["result"]["certificate"]
            require(verify(certificate)["status"] == expected[index], f"certificate {index} changed verdict")
            proposal = {**action["proposal"], "evidence": []}
            replay = study.submit(proposal, study.state()["revision"])
            require(replay["execution"] == "SUCCEEDED", f"action {index} failed to rerun: {replay['result']}")
            require(replay["result"]["status"] == expected[index], f"action {index} changed verdict")
            require(replay["result"]["certificate"]["claim"] == certificate["claim"], "claim changed on replay")
    print("PASS: 17 archived actions; 7 independently checked certificates; 7 real worker reruns.")
    print("Known benchmarks and deterministic replay; no novel theorem or external-model evaluation.")


if __name__ == "__main__":
    main()
