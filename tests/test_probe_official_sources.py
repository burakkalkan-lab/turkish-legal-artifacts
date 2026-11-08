"""Offline fake response tests for source probes; never contact real government sites."""
from pathlib import Path
import sys
import tempfile
from contextlib import redirect_stderr
from io import StringIO
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'cite-check-tr/scripts'))
import probe_official_sources as p


class ProbeTests(unittest.TestCase):
    def test_official_roots_only_and_not_legal_verification(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(p, 'fetch', return_value={'status':'retrieved', 'legal_verification':'not_performed'}) as fn:
                result=p.probe(['mevzuat','yargitay','danistay'], Path(d))
        self.assertEqual(len(result),3)
        self.assertTrue(all(r['legal_verification']=='not_performed' for r in result))
        self.assertEqual({a.args[0] for a in fn.call_args_list},set(p.SOURCES.values()))
        self.assertTrue(all(a.kwargs.get('engine')=='http' for a in fn.call_args_list))

    def test_no_live_without_explicit_confirmation(self):
        with self.assertRaises(SystemExit) as cm, patch.object(p, 'fetch', side_effect=AssertionError('no network')), redirect_stderr(StringIO()):
            p.main([])
        self.assertEqual(cm.exception.code, 2)


if __name__=='__main__':
    unittest.main()
