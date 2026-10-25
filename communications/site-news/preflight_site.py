#!/usr/bin/env python3
"""Read-only VPS audit. Saves a private snapshot; never deploys or reloads services."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tree(root):
    result = {}
    for path in [root, *sorted(root.rglob('*'))]:
        info = path.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError('Review symlinks/special files before installation: ' + str(path))
        result[str(path.relative_to(root))] = 'directory' if path.is_dir() else digest(path.read_bytes())
    return result


def fetch(route):
    data = subprocess.check_output(['curl','--silent','--show-error','--fail',
        '--noproxy','*','--proto','=https','--connect-timeout','5','--max-time','15',
        '--resolve','greensun.energy:443:127.0.0.1','https://greensun.energy'+route])
    return data


def inspect(root, output):
    if not root.is_absolute() or root.resolve() != root or not root.is_dir():
        raise ValueError('Use the verified absolute document root, without symlinks')
    if output.resolve() == root or root in output.resolve().parents:
        raise ValueError('Audit output must be private and outside the live document root')
    config = subprocess.check_output(['nginx','-T'], stderr=subprocess.PIPE)
    inventory = tree(root)
    served = fetch('/')
    if inventory.get('index.html') != digest(served):
        raise ValueError('Origin homepage does not match the selected document root')
    # GET only. No form submissions, social sends or application/config writes.
    sitemap, robots = fetch('/sitemap.xml'), fetch('/robots.txt')
    previous_umask = os.umask(0o077)
    try:
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
        (output/'nginx-T.txt').write_bytes(config)
        (output/'home.html').write_bytes(served)
        (output/'sitemap.xml').write_bytes(sitemap)
        (output/'robots.txt').write_bytes(robots)
        record = {'status':'AUDIT_ONLY_NOT_APPROVED', 'checked_at':datetime.now(timezone.utc).isoformat(),
            'site_root':str(root), 'root_identity':[root.stat().st_dev,root.stat().st_ino],
            'nginx_sha256':digest(config), 'home_sha256':digest(served), 'files':inventory,
            'news_exists':(root/'news').exists(), 'configuration_reviewed':False,
            'backup_created':False, 'publication_authorized':False}
        (output/'preflight.json').write_text(json.dumps(record,indent=2)+'\n')
    finally:
        os.umask(previous_umask)
    print('AUDIT_SAVED:',output)
    print('Review nginx-T.txt locally. This audit is neither backup nor deployment approval.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        inspect(args.site_root,args.output)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        parser.exit(1,'STOP: '+str(error)+'\n')
