#!/usr/bin/env python3
"""Standalone owner-requested test; no schedule or November plan writes.
Product direction: consider paid GSun.AI editorial factory for other businesses;
no launched tariff, multi-tenant readiness or fully autonomous review claimed.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import sqlite3
import urllib.request

TG = -1004428833073
MAX = -71907934625976
EVENT = 'gsun-factory-introduction-20261024-v1'
TEXT = '''Как GSun рассказывает о своей работе?

Мы развиваем собственную фабрику постов GSun.AI: она помогает готовить тексты, проверять их по заданным фактам и собирать план публикаций. Для материалов создаём иллюстрации и проверяем предпросмотр.

Сейчас проверяем доставку одного материала в Telegram и MAX. Планы разработки отделяем от реализованных возможностей, а новые материалы проходят согласование.

Дальше рассматриваем фабрику как отдельный платный сервис для других компаний. Это направление развития, а не объявление готового тарифа.

О проекте: https://gsun.ai/start'''

class Stop(Exception): pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None

def require(ok, reason):
    if not ok: raise Stop(reason)

def env(path):
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        key, sep, value = line.partition('=')
        require(bool(sep) and key.strip() not in result, 'ENV_FORMAT')
        values = shlex.split(value, comments=True)
        require(len(values) <= 1, 'ENV_FORMAT')
        result[key.strip()] = values[0] if values else ''
    return result

class API:
    def __init__(self, tg, mx):
        self.tg, self.mx = tg, mx
        self.opener = urllib.request.build_opener(NoRedirect())
    def call(self, platform, route, body=None):
        headers = {'Content-Type': 'application/json'}
        if platform == 'telegram':
            url = 'https://api.telegram.org/bot' + self.tg + '/' + route
        else:
            url = 'https://platform-api2.max.ru' + route
            headers['Authorization'] = self.mx
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, headers=headers)
        with self.opener.open(request, timeout=40) as response: result = json.load(response)
        if platform == 'telegram':
            require(result.get('ok') is True, 'TELEGRAM_REJECTED')
            return result['result']
        return result
    def verify(self):
        me = self.call('telegram', 'getMe', {})
        require(me.get('username', '').lower() == 'greensun_energy_bot', 'WRONG_TG_BOT')
        c = self.call('telegram', 'getChat', {'chat_id': TG})
        require(c.get('id') == TG and c.get('type') == 'channel', 'WRONG_TG_CHANNEL')
        m = self.call('telegram', 'getChatMember', {'chat_id': TG, 'user_id': me['id']})
        require(m.get('status') == 'administrator' and m.get('can_post_messages') is True, 'TG_RIGHTS')
        me = self.call('max', '/me')
        require(me.get('user_id') == 493074255 and me.get('is_bot') is True, 'WRONG_MAX_BOT')
        c = self.call('max', f'/chats/{MAX}')
        require(c.get('chat_id') == MAX and c.get('type') == 'channel', 'WRONG_MAX_CHANNEL')
        m = self.call('max', f'/chats/{MAX}/members/me')
        require(m.get('is_admin') is True and 'write' in (m.get('permissions') or []), 'MAX_RIGHTS')
    def send(self, platform):
        if platform == 'telegram':
            r = self.call(platform, 'sendMessage', {'chat_id': TG, 'text': TEXT, 'disable_web_page_preview': True})
            require(r.get('chat', {}).get('id') == TG and r.get('message_id'), 'TG_RESULT_UNKNOWN')
            return str(r['message_id'])
        r = self.call(platform, f'/messages?chat_id={MAX}', {'text': TEXT, 'notify': True})
        m = r.get('message') or {}
        require(m.get('recipient', {}).get('chat_id') == MAX and m.get('body', {}).get('mid'), 'MAX_RESULT_UNKNOWN')
        return str(m['body']['mid'])

def deliver(db, api):
    db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS sends (event TEXT, platform TEXT, status TEXT, text_hash TEXT, message_id TEXT, PRIMARY KEY(event,platform))')
    digest = hashlib.sha256(TEXT.encode()).hexdigest()
    for platform in ('telegram', 'max'):
        old = db.execute('SELECT status FROM sends WHERE event=? AND platform=?', (EVENT, platform)).fetchone()
        if old:
            print(platform.upper(), 'SKIP_' + old[0].upper(), flush=True)
            continue
        db.execute('INSERT INTO sends VALUES (?, ?, ?, ?, ?)', (EVENT, platform, 'unknown', digest, ''))
        db.commit()
        try:
            mid = api.send(platform)
            db.execute('UPDATE sends SET status=?,message_id=? WHERE event=? AND platform=?', ('sent', mid, EVENT, platform))
            db.commit()
            print(platform.upper(), 'SENT', mid, flush=True)
            if platform == 'telegram': print('https://t.me/Gsun_ai/' + mid, flush=True)
        except Exception:
            print(platform.upper(), 'RESULT_UNKNOWN — do not resend; reconcile channel', flush=True)
    return db.execute('SELECT COUNT(*) FROM sends WHERE event=? AND status=?', (EVENT, 'sent')).fetchone()[0] == 2

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--send-both', action='store_true')
    a = p.parse_args()
    print(TEXT)
    print('\nTARGETS: Telegram @Gsun_ai; MAX Солнечные панели / GreenSun')
    if not a.send_both:
        print('PREVIEW_ONLY — no network, writes or publishing')
        return
    os.umask(0o077)
    home = Path.home()
    cfg = env(home / '.config/gsun-pr/runtime.env')
    mx = json.loads((home / '.config/gsun-pr/max.json').read_text())
    require(mx.get('chat_id') == MAX and mx.get('bot_id') == 493074255, 'MAX_CONFIG_MISMATCH')
    api = API(cfg['TELEGRAM_BOT_TOKEN'], mx['bot_token'])
    state = home / '.local/share/gsun-pr'
    with (state / '.crosspost-test.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        api.verify()
        with sqlite3.connect(state / 'crosspost-test.sqlite') as db:
            success = deliver(db, api)
    print('NOVEMBER_PLAN_AND_TIMERS_UNCHANGED')
    if not success: raise SystemExit(2)

if __name__ == '__main__':
    try: main()
    except Stop as e:
        print('STOP:', str(e)); raise SystemExit(1)
    except Exception:
        print('CHECK_FAILED — secrets hidden; inspect receipts before retry'); raise SystemExit(1)
