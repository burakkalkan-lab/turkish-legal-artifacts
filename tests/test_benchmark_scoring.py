"""Synthetic scorer tests; not a legal accuracy assessment."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from evaluate_benchmark import score

CASES = json.loads((ROOT / "benchmarks/cite-check-tr/cases.json").read_text(encoding="utf-8"))
GOLD = json.loads((ROOT / "benchmarks/cite-check-tr/gold.json").read_text(encoding="utf-8"))
OFFLINE = json.loads((ROOT / "cite-check-tr/examples/expected-offline-report.json").read_text(encoding="utf-8"))


def predictions():
    reports = []
    for case in CASES["cases"]:
        report = deepcopy(OFFLINE)
        report["bulgular"] = [report["bulgular"][0]]
        reports.append({"id": case["id"], "report": report})
    return {"predictions": reports}


class BenchmarkScoringTests(unittest.TestCase):
    def test_expected_sample_count(self):
        result = score(CASES, GOLD, predictions())
        self.assertEqual(result["sample_size"], 9)
        self.assertEqual(result["verified_prediction_count"], 0)
        self.assertIsNone(result["unsupported_verified_fraction"])
        self.assertIn("ÖN ÖLÇÜM", result["notice"])

    def test_missing_case_fails(self):
        submission = predictions()
        submission["predictions"].pop()
        with self.assertRaisesRegex(ValueError, "Eksik tahmin"):
            score(CASES, GOLD, submission)

    def test_extra_case_fails(self):
        submission = predictions()
        submission["predictions"].append({"id": "EXTRA", "report": deepcopy(OFFLINE)})
        with self.assertRaisesRegex(ValueError, "beklenmeyen tahmin"):
            score(CASES, GOLD, submission)

    def test_duplicate_case_fails(self):
        submission = predictions()
        submission["predictions"].append(deepcopy(submission["predictions"][0]))
        with self.assertRaisesRegex(ValueError, "yinelenen id"):
            score(CASES, GOLD, submission)

    def test_invalid_report_fails(self):
        submission = predictions()
        submission["predictions"][0]["report"]["uzman_onayi_gerekli"] = False
        with self.assertRaisesRegex(ValueError, "rapor doğrulaması"):
            score(CASES, GOLD, submission)

    def test_multiple_findings_fail(self):
        submission = predictions()
        report = submission["predictions"][0]["report"]
        other = deepcopy(report["bulgular"][0])
        other["id"] = "A2"
        report["bulgular"].append(other)
        with self.assertRaisesRegex(ValueError, "yalnız bir bulgu"):
            score(CASES, GOLD, submission)

    def test_invalid_gold_set_fails(self):
        gold = deepcopy(GOLD)
        gold["labels"].pop()
        with self.assertRaisesRegex(ValueError, "eşleşmiyor"):
            score(CASES, gold, predictions())

    def test_gold_stays_provisional(self):
        gold = deepcopy(GOLD)
        gold["review_status"] = "verified"
        with self.assertRaisesRegex(ValueError, "geçici"):
            score(CASES, gold, predictions())


if __name__ == "__main__":
    unittest.main()
