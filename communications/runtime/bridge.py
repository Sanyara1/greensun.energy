#!/usr/bin/env python3
"""Loopback-only bridge. Put a TLS reverse proxy in front; never expose port directly."""
import fcntl
import hmac
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import factory as f


def month_path(home, month):
    f.require(bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month or '')), 'INVALID_MONTH')
    return home / 'plans' / (month + '.json')


def snapshot(home, month):
    plan = f.read(month_path(home, month))
    facts, media = f.read(home / 'facts.json'), f.read(home / 'media.json')
    error = None
    try:
        f.validate(plan, home, facts, media)
    except f.Stop as e:
        error = str(e)
    sealed = f.sealed_hash(plan)
    approved = plan.get('approval', {}) is not None and plan.get('approval', {}).get('hash') == sealed
    deliveries = {}
    dbpath = home / 'deliveries.sqlite'
    if dbpath.exists():
        with sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True) as db:
            deliveries = dict(db.execute('SELECT id,status FROM deliveries'))
    posts = []
    by_id = {v['id']: v for v in facts}
    for p in plan['posts']:
        posts.append({k: p.get(k) for k in ('id', 'scheduled_at', 'text_ru', 'text_en', 'media_id')})
        posts[-1].update({
            'delivery': deliveries.get('post:' + p['id'] + ':' + str(f.CHANNEL)),
            'reminders': [(f.instant(p['scheduled_at']) - timedelta(hours=n)).isoformat() for n in (24, 1)],
            'facts': [{k: by_id[fid].get(k) for k in ('text', 'status', 'source_url')} for fid in p['fact_ids'] if fid in by_id]})
    return {'month': month, 'hash': sealed, 'posts': posts, 'approved': approved,
            'can_approve': not error and f.instant(plan['posts'][0]['scheduled_at']) > datetime.now(timezone.utc),
            'validation_error': error, 'paused': (home / 'PAUSE').exists(),
            'publish_enabled': os.getenv('GSUN_PUBLISH_ENABLED') == 'yes'}


def action(home, month, data):
    path = month_path(home, month)
    f.require(set(data) <= {'action', 'hash'}, 'INVALID_ACTION')
    name = data.get('action')
    if name == 'approve':
        f.approve(path, home, data.get('hash'))
    elif name == 'pause':
        (home / 'PAUSE').touch(mode=0o600)
    elif name == 'resume':
        (home / 'PAUSE').unlink(missing_ok=True)
    else:
        raise f.Stop('INVALID_ACTION')
    # No secrets or draft content in this operator log.
    with (home / 'operator-actions.jsonl').open('a') as log:
        log.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'action': name, 'month': month}) + '\n')
    return {'status': 'OK'}


def handler(home, token):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass

        def reply(self, status, body, content_type='application/json'):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'private, no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self.handle_api(False)

        def do_POST(self):
            self.handle_api(True)

        def handle_api(self, posting):
            supplied = self.headers.get('Authorization', '')
            if not hmac.compare_digest(supplied.encode(), ('Bearer ' + token).encode()):
                return self.reply(401, {'status': 'UNAUTHORIZED'})
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            month = params.get('month', [''])[0]
            try:
                month_path(home, month)
                with (home / '.lock').open('a') as lock:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        return self.reply(409, {'status': 'BUSY'})
                    if posting and url.path == '/action':
                        size = int(self.headers.get('Content-Length', '0'))
                        f.require(0 < size <= 1024, 'INVALID_SIZE')
                        data = json.loads(self.rfile.read(size))
                        f.require(isinstance(data, dict), 'INVALID_ACTION')
                        return self.reply(200, action(home, month, data))
                    if not posting and url.path == '/plan':
                        return self.reply(200, snapshot(home, month))
                    if not posting and url.path == '/media':
                        mid = params.get('id', [''])[0]
                        plan = f.read(month_path(home, month))
                        f.require(any(p.get('media_id') == mid for p in plan['posts']), 'MEDIA_NOT_IN_PLAN')
                        item = f.read(home / 'media.json')[mid]
                        f.require(plan['media_hashes'].get(mid) == f.digest(item), 'MEDIA_CHANGED')
                        p = f.media_path(home, item)
                        return self.reply(200, p.read_bytes(), 'image/png' if p.suffix.lower() == '.png' else 'image/jpeg')
                    return self.reply(404, {'status': 'NOT_FOUND'})
            except FileNotFoundError:
                return self.reply(404, {'status': 'NOT_FOUND'})
            except f.Stop as e:
                return self.reply(409, {'status': str(e)})
            except Exception:
                return self.reply(400, {'status': 'INVALID_INPUT'})
    return Handler


if __name__ == '__main__':
    os.umask(0o077)
    home = Path.home() / '.local/share/gsun-pr'
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = os.getenv('GSUN_PR_BRIDGE_TOKEN', '')
    if len(token) < 32:
        raise SystemExit('BRIDGE_TOKEN_REQUIRED_MIN_32_CHARS')
    server = HTTPServer(('127.0.0.1', 8791), handler(home, token))
    server.timeout = 10
    server.serve_forever()
