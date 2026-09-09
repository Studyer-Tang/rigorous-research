"""Check the ongoing Frankl archive and rerun its six finite entropy calculations."""

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
    require(archive["state"]["objective_status"] == "UNRESOLVED", "original conjecture must remain unresolved")
    require(archive["state"]["execution"] == "READY", "research should remain resumable")
    require(len(archive["actions"]) == 15, "unexpected historical action count")
    expected = {5: -1, 7: 1, 10: 0, 11: 0, 12: 0, 13: 1}
    with tempfile.TemporaryDirectory(prefix="frankl-replay-") as folder:
        study = Study.create(folder, "replay", "Deterministic finite entropy replay, not a conjecture solution")
        for index, record in enumerate(archive["actions"], 1):
            require(record["id"] == index, "action sequence changed")
            require(digest(record["proposal"]["action"]) == record["fingerprint"], "action hash mismatch")
            require(digest(record["result"]) == record["result_hash"], "result hash mismatch")
            if index not in expected:
                continue
            checked = verify(record["result"]["certificate"])
            require(checked.get("computation", {}).get("sign") == expected[index], f"certificate {index} changed sign")
            result = study.submit({**record["proposal"], "evidence": []}, study.state()["revision"])
            require(result["execution"] == "SUCCEEDED", f"replay {index} failed: {result['result']}")
            require(
                result["result"]["independent_check"]["computation"]["sign"] == expected[index], "replay changed sign"
            )
            require(
                result["result"]["certificate"]["claim"] == record["result"]["certificate"]["claim"],
                "replay changed claim",
            )
    print("PASS: 15 archived actions; 6 exact entropy checks; 6 worker reruns. Frankl remains unresolved.")


if __name__ == "__main__":
    main()
