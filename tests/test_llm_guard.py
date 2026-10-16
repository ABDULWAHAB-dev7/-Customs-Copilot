"""Gate tests: a model that lies must not reach the reply. Run: python tests/test_llm_guard.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.copilot import draft  # noqa: E402

SHIPMENT = json.loads((ROOT / "data" / "shipments.json").read_text(encoding="utf-8"))[0]
Q = "Provide the CTH declared for this shipment."
failures = []


def expect(cond, msg):
    if not cond:
        failures.append(msg)


def fake(proposals):
    return lambda prompt: proposals


def main():
    unknown_cite = [{"text": "The HS code is 8524.11.", "cite": "invoice:99", "quote": "HS Code: 8524.11"}]
    r = draft(SHIPMENT, Q, use_llm=True, llm_call=fake(unknown_cite))
    expect(r["mode"] == "offline", "unknown citation should fall back to offline")
    expect(any(x["reason"] == "citation not in this shipment" for x in r["rejected"]), "unknown cite not reported")

    invented_quote = [{"text": "The HS code is 8524.11.", "cite": "invoice:8", "quote": "HS Code: 9999.99"}]
    r = draft(SHIPMENT, Q, use_llm=True, llm_call=fake(invented_quote))
    expect(r["mode"] == "offline", "invented quote should fall back")
    expect(any(x["reason"] == "quote is not in the cited line" for x in r["rejected"]), "invented quote not reported")

    wrong_number = [{"text": "The HS code is 8524.19.", "cite": "invoice:8", "quote": "HS Code: 8524.11"}]
    r = draft(SHIPMENT, Q, use_llm=True, llm_call=fake(wrong_number))
    expect(r["mode"] == "offline", "wrong number should fall back")
    expect(any(x["reason"] == "a number is not in the quote" for x in r["rejected"]), "wrong number not reported")

    good = [{"text": "The HS code is 8524.11.", "cite": "invoice:8", "quote": "HS Code: 8524.11"}]
    r = draft(SHIPMENT, Q, use_llm=True, llm_call=fake(good))
    expect(r["mode"] == "llm" and len(r["sentences"]) == 1, "a verified proposal should be used")

    r = draft(SHIPMENT, Q, use_llm=True, llm_call=fake("not a list"))
    expect(r["mode"] == "offline" and r["sentences"], "non-list output should fall back to offline")

    r = draft(SHIPMENT, Q, use_llm=False, llm_call=fake(good))
    expect(r["mode"] == "offline", "llm must not run unless use_llm is set")

    if failures:
        print("FAILED")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("LLM gate tests passed.")


if __name__ == "__main__":
    main()
