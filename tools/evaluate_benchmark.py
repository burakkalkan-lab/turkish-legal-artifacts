#!/usr/bin/env python3
"""Score Cite Check TR model reports against provisional benchmark labels.

This tool checks report structure and label agreement; it cannot authenticate
a quoted law, a legal interpretation, or the truth of any user-supplied source.
No network calls or LLM calls are made.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cite-check-tr" / "scripts"))
from validate_report import validate

CLASSES = ("dogrulandi", "uyumsuzluk", "dogrulanamadi", "uzman_incelemesi")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score(cases, gold, submissions):
    if cases.get("benchmark_version") != gold.get("benchmark_version"):
        raise ValueError("Benchmark/gold sürümleri eşleşmiyor.")
    if gold.get("review_status") != "provisional_requires_independent_qualified_lawyer_review":
        raise ValueError("Bu puanlayıcı yalnızca açıkça geçici etiketli ön benchmark içindir.")
    source_cases = cases.get("cases")
    labels = gold.get("labels")
    predictions = submissions.get("predictions")
    if not isinstance(source_cases, list) or not isinstance(labels, list) or not isinstance(predictions, list):
        raise ValueError("cases, labels ve predictions liste olmalıdır.")

    def keyed(rows, label):
        result = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                raise ValueError(label + ": geçersiz vaka/kimlik.")
            if row["id"] in result:
                raise ValueError(label + ": yinelenen id " + row["id"])
            result[row["id"]] = row
        return result

    case_map = keyed(source_cases, "cases")
    gold_map = keyed(labels, "gold")
    pred_map = keyed(predictions, "predictions")
    if set(case_map) != set(gold_map):
        raise ValueError("cases ile gold vaka kimlikleri eşleşmiyor.")
    if set(case_map) != set(pred_map):
        missing = sorted(set(case_map) - set(pred_map))
        extra = sorted(set(pred_map) - set(case_map))
        raise ValueError(f"Eksik tahmin: {missing}; beklenmeyen tahmin: {extra}")

    confusion = {true: {pred: 0 for pred in CLASSES} for true in CLASSES}
    rows = []
    for cid in sorted(case_map):
        expected = gold_map[cid].get("expected_status")
        if expected not in CLASSES:
            raise ValueError(f"{cid}: beklenen etiket geçersiz.")
        report = pred_map[cid].get("report")
        if not isinstance(report, dict):
            raise ValueError(f"{cid}: tam v0.2.7 JSON raporu gerekli.")
        errors = validate(report)
        if errors:
            raise ValueError(f"{cid}: rapor doğrulaması başarısız: {'; '.join(errors[:4])}")
        findings = report["bulgular"]
        if len(findings) != 1:
            raise ValueError(f"{cid}: bir ve yalnız bir bulgu gerekli.")
        got = findings[0]["durum"]
        confusion[expected][got] += 1
        rows.append({"id": cid, "expected": expected, "predicted": got, "correct": expected == got,
                     "case_type": case_map[cid]["case_type"]})

    total = len(rows)
    correct = sum(row["correct"] for row in rows)
    class_scores = {}
    for label in CLASSES:
        tp = confusion[label][label]
        actual = sum(confusion[label].values())
        predicted = sum(confusion[other][label] for other in CLASSES)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        class_scores[label] = {"support": actual, "precision": round(precision, 4),
                               "recall": round(recall, 4), "f1": round(f1, 4)}
    # A false positive is a "verified" classification where ground truth is not verified.
    verified_fps = sum(confusion[gold_class]["dogrulandi"] for gold_class in CLASSES if gold_class != "dogrulandi")
    verified_predictions = sum(confusion[gold_class]["dogrulandi"] for gold_class in CLASSES)
    unsupported_verification_rate = verified_fps / verified_predictions if verified_predictions else None
    # This is not a true citation-validity rate: JSON schemas cannot check source authenticity.
    return {
        "benchmark_version": cases["benchmark_version"],
        "label_status": gold["review_status"],
        "notice": "ÖN ÖLÇÜM: Bağımsız hukukçu onayı yok; kaynak sahihliği otomatik kanıtlanmaz.",
        "sample_size": total,
        "accuracy": round(correct / total, 4) if total else None,
        "macro_f1": round(sum(x["f1"] for x in class_scores.values()) / len(CLASSES), 4),
        "unsupported_verified_count": verified_fps,
        "verified_prediction_count": verified_predictions,
        "unsupported_verified_fraction": round(unsupported_verification_rate, 4) if unsupported_verification_rate is not None else None,
        "confusion_matrix": confusion,
        "per_class": class_scores,
        "per_case": rows,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", default=str(ROOT / "benchmarks/cite-check-tr/cases.json"))
    p.add_argument("--gold", default=str(ROOT / "benchmarks/cite-check-tr/gold.json"))
    p.add_argument("--predictions", required=True, help="Kullanıcı tarafından oluşturulmuş predictions JSON dosyası")
    p.add_argument("--output", help="İsteğe bağlı JSON sonuç dosyası (özel/kişisel veri içermemeli)")
    args = p.parse_args(argv)
    try:
        result = score(load_json(args.cases), load_json(args.gold), load_json(args.predictions))
        content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
        print(content, end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
