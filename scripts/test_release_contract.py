import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('alias', Path(__file__).with_name('promote-runtime-alias.py'))
alias = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alias)


class AliasTests(unittest.TestCase):
    def test_publication_requires_explicit_flag_and_evidence(self):
        for publish in (False, True):
            with tempfile.TemporaryDirectory() as d:
                manifest = Path(d)/'manifest.json'; evidence = Path(d)/'evidence.json'
                sha='sha256:'+'a'*64
                manifest.write_text(json.dumps({'runtimeVersion':'v1.13.8-rpi5-rc2','artifacts':[{'image':'ghcr.io/example/installer:v1.13.8-rpi5-rc2-arm64-extensions','runtimeAlias':'ghcr.io/example/installer:v1.13.8-rpi5-rc2','digest':sha}]}))
                evidence.write_text(json.dumps({'runtimeVersion':'v1.13.8-rpi5-rc2','installerDigest':sha,'extensionsVerified':True,'reviewedBy':'test'}))
                argv=['test','--manifest',str(manifest),'--observed-runtime','v1.13.8-rpi5-rc2','--validation-evidence',str(evidence)]+(['--publish'] if publish else [])
                missing=SimpleNamespace(returncode=1,stdout='',stderr='MANIFEST_UNKNOWN')
                with patch('sys.argv',argv), patch.object(alias.subprocess,'check_output',return_value=sha), patch.object(alias.subprocess,'run',return_value=missing) as run:
                    alias.main()
                    self.assertEqual(sum(c.args[0][1]=='copy' for c in run.call_args_list), 1 if publish else 0)

    def test_wrong_runtime_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            m=Path(d)/'m'; e=Path(d)/'e'; m.write_text('{"runtimeVersion":"v1.13.8-rpi5-rc2"}'); e.write_text('{}')
            with patch('sys.argv',['test','--manifest',str(m),'--observed-runtime','v1.13.8','--validation-evidence',str(e)]):
                with self.assertRaises(SystemExit): alias.main()


if __name__=='__main__': unittest.main()
