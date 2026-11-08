"""Offline regression checks for the optional official court-source adapter.

These tests use synthetic responses and DO NOT establish live site compatibility.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cite-check-tr" / "scripts"))
import official_sources as source


class OfficialSourceTests(unittest.TestCase):
    def test_four_official_sources(self):
        self.assertEqual(set(source.SOURCES), {"yargitay", "danistay", "aym_bireysel", "aym_norm"})
        for info in source.SOURCES.values():
            self.assertEqual(info["search_page"].split("/")[2], info["host"])

    def test_unlisted_provider_rejected(self):
        with self.assertRaises(source.SourceAccessError):
            source.search("private_service", "test")

    def test_search_rejects_bad_query(self):
        for value in ("", "  ", "a" * 161, "x\nother"):
            with self.subTest(value=value), self.assertRaises(source.SourceAccessError):
                source.search("yargitay", value)

    def test_search_limits_result_count(self):
        with self.assertRaises(source.SourceAccessError):
            source.search("danistay", "kira", page_size=100)

    def test_aym_search_does_not_claim_live_access(self):
        with patch.object(source, "_request", side_effect=AssertionError("Network should not be used")):
            result = source.search("aym_bireysel", "hak ihlali")
        self.assertEqual(result["status"], "manual_search_required")
        self.assertEqual(result["legal_verification"], "not_performed")

    def test_document_rejects_bad_ids(self):
        for bad in ("../../etc/passwd", "ab?c=d", "https://example.com/", ""):
            with self.subTest(bad=bad), self.assertRaises(source.SourceAccessError):
                source.document_url("yargitay", bad)

    def test_aym_rejects_cross_host_document(self):
        for bad in ("https://evil.example/kbb/pages/decision",
                    "//evil.example/kbb/pages/decision",
                    "https://normkararlarbilgibankasi.anayasa.gov.tr/kbb/pages/decision",
                    "https://kararlarbilgibankasi.anayasa.gov.tr:444/kbb/pages/decision",
                    "/foo", "/kbb/pages/../admin"):
            with self.subTest(bad=bad), self.assertRaises(source.SourceAccessError):
                source.document_url("aym_bireysel", bad)

    def test_yargitay_parses_index_as_unverified(self):
        data = {"data": {"data": [{"id": "abc-123", "daire": "1. Hukuk Dairesi",
                                      "esasNo": "2020/1", "kararNo": "2021/2"}],
                         "recordsTotal": 1}}
        with patch.object(source, "_request", return_value=(json.dumps(data).encode(),
                         "https://karararama.yargitay.gov.tr/aramadetaylist", "application/json")):
            result = source.search("yargitay", "iş akdi")
        self.assertEqual(result["status"], "index_results_only")
        self.assertEqual(result["results"][0]["id"], "abc-123")
        self.assertEqual(result["legal_verification"], "not_performed")

    def test_danistay_search_payload_is_restricted(self):
        data = {"data": {"data": [{"id": "12", "daireKurul": "Danıştay"}], "recordsTotal": 1}}
        with patch.object(source, "_request", return_value=(json.dumps(data).encode(),
                         "https://karararama.danistay.gov.tr/aramalist", "application/json")) as call:
            result = source.search("danistay", "idare", page_size=3)
        self.assertEqual(call.call_args.kwargs["method"], "POST")
        self.assertEqual(call.call_args.kwargs["payload"]["data"]["pageSize"], 3)
        self.assertEqual(result["results"][0]["daire"], "Danıştay")

    def test_unknown_search_response_fails_not_false_no_results(self):
        with patch.object(source, "_request", return_value=(b"<html>captcha</html>",
                         "https://karararama.yargitay.gov.tr/aramadetaylist", "text/html")):
            with self.assertRaises(source.SourceAccessError):
                source.search("yargitay", "kira")

    def test_document_does_not_verifiy_legal_claim(self):
        payload = {"data": "<html><title>Karar</title><body><h1>Resmî karar</h1><p>Örnek metin</p></body></html>"}
        with patch.object(source, "_request", return_value=(json.dumps(payload).encode(),
                         "https://karararama.yargitay.gov.tr/getDokuman?id=7", "application/json")):
            result = source.document("yargitay", "7")
        self.assertEqual(result["access_status"], "retrieved_unverified")
        self.assertIn("Örnek metin", result["text"])
        self.assertEqual(result["legal_verification"], "not_performed")

    def test_empty_document_rejected(self):
        with patch.object(source, "_request", return_value=(b'{"data": ""}',
                         "https://karararama.yargitay.gov.tr/getDokuman?id=7", "application/json")):
            with self.assertRaises(source.SourceAccessError):
                source.document("yargitay", "7")

    def test_aym_document_same_host_allowed(self):
        result = source.document_url("aym_norm", "/kbb/pages/decision/123")
        self.assertEqual(result, "https://normkararlarbilgibankasi.anayasa.gov.tr/kbb/pages/decision/123")

    def test_post_only_on_fixed_index_endpoints(self):
        with self.assertRaises(source.SourceAccessError):
            source._request("aym_norm", "/kbb/pages/decision/abc", method="POST", payload={})
        with self.assertRaises(source.SourceAccessError):
            source._request("yargitay", "/getDokuman", method="POST", payload={})

    def test_redirect_cross_host_rejected(self):
        r = source.SameHostRedirect("karararama.yargitay.gov.tr")
        with self.assertRaises(ValueError):
            r.redirect_request(None, None, 302, "redirect", {},
                               "https://evil.example/getDokuman")

    def test_no_httpx_and_no_disable_tls(self):
        src = Path(source.__file__).read_text(encoding="utf-8")
        self.assertNotIn("verify=False", src)
        self.assertNotIn("git push", src)
        self.assertNotIn("subprocess", src)


if __name__ == "__main__":
    unittest.main()
