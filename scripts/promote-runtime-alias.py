#!/usr/bin/env python3
"""Explicit runtime-alias publication; cannot overwrite an existing different digest."""
import argparse
import json
import re
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True)
    p.add_argument('--observed-runtime', required=True)
    p.add_argument('--validation-evidence', required=True)
    p.add_argument('--publish', action='store_true')
    args = p.parse_args()
    m = json.loads(Path(args.manifest).read_text())
    evidence = json.loads(Path(args.validation_evidence).read_text())
    if args.observed_runtime != m['runtimeVersion']:
        raise SystemExit('Observed runtime differs from the proposed alias')
    for artifact in m['artifacts']:
        expected = artifact['digest']
        if evidence.get('installerDigest') != expected or evidence.get('runtimeVersion') != args.observed_runtime or evidence.get('extensionsVerified') is not True or not evidence.get('reviewedBy'):
            raise SystemExit('Evidence must bind measured runtime and verified extensions to this exact digest')
        source = artifact['image']
        actual = subprocess.check_output(['crane','digest',source],text=True).strip()
        if actual != expected:
            raise SystemExit('Source artifact changed')
        alias = artifact['runtimeAlias']
        result = subprocess.run(['crane','digest',alias],text=True,capture_output=True)
        if result.returncode == 0 and result.stdout.strip() != expected:
            raise SystemExit('Refusing to overwrite an immutable runtime alias')
        if result.returncode != 0 and 'MANIFEST_UNKNOWN' not in result.stderr:
            raise SystemExit('Could not establish whether alias exists; check registry access')
        print(json.dumps({'source':source,'alias':alias,'digest':expected,'publish':args.publish,'rolloutApproved':False}))
        if args.publish and result.returncode != 0:
            # Resolve source by digest to avoid copying a moved tag.
            subprocess.run(['crane','copy',source.rsplit(':',1)[0]+'@'+expected,alias],check=True)
            if subprocess.check_output(['crane','digest',alias],text=True).strip()!=expected:
                raise SystemExit('Post-publication alias verification failed')


if __name__ == '__main__': main()
