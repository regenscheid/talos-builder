#!/usr/bin/env python3
"""Publish provenance only. Builds never approve artifacts or change runtime aliases."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def hashfile(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--installer', required=True)
    parser.add_argument('--extensions', nargs='+', required=True)
    parser.add_argument('--output', default='release-manifest.json')
    args = parser.parse_args()
    if not re.fullmatch(r'v\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?', args.tag):
        raise SystemExit('Expected exact Talos runtime build tag')
    installer_digest = command('crane', 'digest', args.installer)
    extensions = []
    for image in args.extensions:
        if not re.search(r'@sha256:[a-f0-9]{64}$', image):
            raise SystemExit('Every extension must already be pinned by digest')
        repository = image.split('@')[0].rsplit(':', 1)[0]
        extensions.append({'name': repository.rsplit('/', 1)[-1], 'image': image, 'digest': image.rsplit('@', 1)[1]})
    pkgfile = Path('checkouts/pkgs/Pkgfile').read_text()
    kernel_commit = re.search(r'^\s*linux_version:\s*([a-f0-9]{40})', pkgfile, re.M)
    if not kernel_commit:
        raise SystemExit('Cannot establish vendor kernel commit')
    manifest = {'schemaVersion': 1, 'id': args.tag.lower().replace('.', '-'), 'kind': 'TalosUpgrade',
                'hardwareFamily': 'rpi5-cm5', 'architecture': 'arm64', 'upstreamVersion': args.upstream,
                'runtimeVersion': args.tag, 'runtimeVersionEvidence': 'build-tag; hardware measurement required',
                'sourceCommit': command('git', 'rev-parse', 'HEAD'), 'promotion': 'built-unvalidated', 'validationEvidence': [],
                'artifacts': [{'image': args.installer, 'runtimeAlias': args.installer.rsplit(':', 1)[0]+':'+args.tag,
                  'digest': installer_digest, 'architecture': 'arm64', 'extensions': extensions,
                  'kernelCommit': kernel_commit[1], 'overlayCommit': command('git', '-C', 'checkouts/sbc-raspberrypi', 'rev-parse', 'HEAD'),
                  'kernelConfigSHA256': hashfile('checkouts/pkgs/kernel/build/config-arm64'),
                  'moduleListSHA256': hashfile('checkouts/pkgs/kernel/prepare/pkg.yaml')} ]}
    Path(args.output).write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__': main()
