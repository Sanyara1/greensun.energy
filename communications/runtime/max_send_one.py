#!/usr/bin/env python3
"""Pinned MAX smoke test. Default: local preview only. Never enables timers.
API reference: https://dev.max.ru/docs-api/use-cases/sending-messages/media
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import secrets
import sqlite3
import time
import urllib.request
from urllib.parse import urlsplit

CHANNEL = -71907934625976
BOT = 493074255
POST = '2026-11-02'
POST_HASH = 'a07c33402ff9a0d7494459c95253162702aef2f4ddbc8ef7bc57264c4f17a2be'
IMAGE_HASH = 'c8aa1e86ede77882b2f49ad4da3f145e466991cdd3ade2d49726624cde20fe52'
BASE = 'https://platform-api2.max.ru'

class Stop(Exception):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def require(ok, reason):
    if not ok:
        raise Stop(reason)

def prepare(home):
    state = home / '.local/share/gsun-pr'
    config = json.loads((home / '.config/gsun-pr/max.json').read_text())
    require(config.get('chat_id') == CHANNEL and config.get('bot_id') == BOT,
            'CONFIG_TARGET_MISMATCH')
    require(config.get('publish_enabled') is False, 'EXPECTED_MAX_DISABLED')
    plan = json.loads((state / 'plans/2026-11.json').read_text())
    posts = [p for p in plan['posts'] if p['id'] == POST]
    require(len(posts) == 1, 'POST_NOT_UNIQUE')
    post = posts[0]
    digest = hashlib.sha256(json.dumps(post, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    require(digest == POST_HASH, 'POST_CHANGED')
    media = json.loads((state / 'media.json').read_text())[post['media_id']]
    root = (state / 'assets').resolve()
    image = (root / media['path']).resolve()
    require(image.is_relative_to(root), 'MEDIA_PATH_ESCAPE')
    content = image.read_bytes()
    require(media.get('rights_confirmed') is True, 'MEDIA_RIGHTS_MISSING')
    require(hashlib.sha256(content).hexdigest() == IMAGE_HASH == media['sha256'], 'IMAGE_CHANGED')
    require(content.startswith(b'\x89PNG\r\n\x1a\n') and len(content) < 50_000_000, 'INVALID_PNG')
    require(0 < len(post['text_ru']) <= 4000, 'TEXT_LENGTH')
    return state, config, post, content

class Client:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, url, method='GET', data=None, content_type=None, auth=True):
        headers = {'Accept': 'application/json'}
        if auth:
            headers['Authorization'] = self.token
        if content_type:
            headers['Content-Type'] = content_type
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with self.opener.open(req, timeout=45) as response:
            return json.load(response)

    def api(self, route, method='GET', body=None):
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        return self.request(BASE + route, method, data, 'application/json' if data else None)

    def upload(self, content):
        url = self.api('/uploads?type=image', 'POST')['url']
        parsed = urlsplit(url)
        require(parsed.scheme == 'https' and parsed.hostname == 'iu.oneme.ru'
                and parsed.port in (None, 443) and not parsed.username and not parsed.password,
                'UPLOAD_HOST_REQUIRES_REVIEW')
        boundary = 'gsun' + secrets.token_hex(16)
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="data"; filename="card.png"\r\n'
                'Content-Type: image/png\r\n\r\n').encode() + content + f'\r\n--{boundary}--\r\n'.encode()
        result = self.request(url, 'POST', body, 'multipart/form-data; boundary=' + boundary, auth=False)
        photos = result.get('photos', {})
        tokens = [p.get('token') for p in photos.values() if isinstance(p, dict) and p.get('token')]
        require(len(tokens) == 1, 'UPLOAD_RESPONSE_REQUIRES_REVIEW')
        return tokens[0]

def deliver(state, config, post, content, client):
    # Isolated MAX ledger: never touches Telegram receipts or the approved plan.
    with sqlite3.connect(state / 'max-deliveries.sqlite', timeout=10) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS deliveries (key TEXT PRIMARY KEY, status TEXT NOT NULL, receipt TEXT NOT NULL)')
        key = f'max:{CHANNEL}:{POST}'
        old = db.execute('SELECT status FROM deliveries WHERE key=?', (key,)).fetchone()
        require(old is None, 'ALREADY_RECORDED_' + (old[0] if old else ''))
        me = client.api('/me')
        require(me.get('user_id') == BOT and me.get('is_bot') is True, 'BOT_MISMATCH')
        chat = client.api(f'/chats/{CHANNEL}')
        require(chat.get('chat_id') == CHANNEL and chat.get('type') == 'channel', 'CHANNEL_MISMATCH')
        member = client.api(f'/chats/{CHANNEL}/members/me')
        require(member.get('is_admin') is True and 'write' in (member.get('permissions') or []), 'WRITE_PERMISSION_MISSING')
        token = client.upload(content)
        time.sleep(3)
        receipt = {'post_sha256': POST_HASH, 'image_sha256': IMAGE_HASH, 'chat_id': CHANNEL,
                   'post_id': POST, 'at': int(time.time()), 'authorization': 'explicit CLI send-one'}
        # Durable reservation BEFORE the only send request. Any ambiguity blocks retry.
        db.execute('INSERT INTO deliveries VALUES (?, ?, ?)', (key, 'unknown', json.dumps(receipt)))
        db.commit()
        response = client.api(f'/messages?chat_id={CHANNEL}', 'POST', {
            'text': post['text_ru'], 'notify': True,
            'attachments': [{'type': 'image', 'payload': {'token': token}}]})
        message = response.get('message') or {}
        mid = (message.get('body') or {}).get('mid')
        require(mid and (message.get('recipient') or {}).get('chat_id') == CHANNEL, 'SEND_RESULT_REQUIRES_RECONCILIATION')
        receipt['message_id'] = mid
        receipt['url'] = message.get('url')
        db.execute('UPDATE deliveries SET status=?, receipt=? WHERE key=?', ('sent', json.dumps(receipt), key))
        db.commit()
        print('MAX_POST_SENT')
        print('MESSAGE_ID:', mid)
        if receipt['url']:
            print('POST_URL:', receipt['url'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send-one', action='store_true', help='Publish exactly the pinned post NOW; subscribers may receive notifications')
    args = parser.parse_args()
    os.umask(0o077)
    state, config, post, content = prepare(Path.home())
    print('CHANNEL_ID:', CHANNEL)
    print('POST_ID:', POST)
    print('POST_SHA256:', POST_HASH)
    print('IMAGE_SHA256:', IMAGE_HASH)
    print(post['text_ru'])
    if not args.send_one:
        print('MAX_PREVIEW_READY — no network, no writes, no publishing')
        return
    with (state / '.max-send.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        deliver(state, config, post, content, Client(config['bot_token']))
    print('MAX_SCHEDULE_DISABLED — Telegram unchanged')

if __name__ == '__main__':
    try:
        main()
    except Stop as error:
        print('STOP:', str(error))
        raise SystemExit(1)
    except Exception:
        print('MAX_OPERATION_FAILED — secrets hidden; inspect receipt before any retry')
        raise SystemExit(1)
