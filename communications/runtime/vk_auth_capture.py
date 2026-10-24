#!/usr/bin/env python3
"""One-shot VK community OAuth capture. No publishing or token API calls."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

ORIGIN = 'https://greensun.energy'
BASE = '/pr-auth/vk/'
CALLBACK = ORIGIN + BASE + 'callback'
APP = '54851169'
GROUP = '242557319'

def parse_result(fragment, expected_state):
    if not isinstance(fragment, str) or len(fragment) > 16000:
        raise ValueError('INVALID_RESPONSE')
    q = parse_qs(fragment.lstrip('#'), keep_blank_values=True)
    if any(len(v) != 1 for v in q.values()):
        raise ValueError('DUPLICATE_PARAMETERS')
    if not hmac.compare_digest(q.get('state', [''])[0], expected_state):
        raise ValueError('STATE_MISMATCH')
    if 'error' in q:
        raise ValueError('VK_AUTH_DENIED')
    keys = [k for k in q if k.startswith('access_token')]
    if keys != ['access_token_' + GROUP]:
        raise ValueError('WRONG_COMMUNITY')
    token = q[keys[0]][0]
    if len(token) < 20 or any(c.isspace() for c in token):
        raise ValueError('INVALID_TOKEN')
    expires = int(q.get('expires_in', ['0'])[0])
    if expires < 0:
        raise ValueError('INVALID_EXPIRY')
    return {'app_id': int(APP), 'group_id': int(GROUP),
            'access_token': token, 'expires_in': expires,
            'received_at': int(time.time()), 'publish_enabled': False,
            'status': 'UNVERIFIED', 'requested_scope': 'photos'}

def save_new(path, data):
    # An existing credential is never overwritten, including on repeated callbacks.
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())

def serve():
    os.umask(0o077)
    destination = Path.home() / '.config/gsun-pr/vk-candidate.json'
    if destination.exists():
        raise SystemExit('STOP: vk-candidate.json already exists; do not overwrite')
    ticket, state, cookie = [secrets.token_urlsafe(32) for _ in range(3)]
    deadline = time.monotonic() + 900
    started = False
    done = False
    script = """const fragment=location.hash.slice(1);
history.replaceState(null,'',location.pathname);
document.getElementById('result').textContent='Сохраняем результат авторизации…';
fetch('/pr-auth/vk/receive',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json'},body:JSON.stringify({fragment})})
.then(async r=>{const x=await r.json();document.getElementById('result').textContent=x.status;})
.catch(()=>{document.getElementById('result').textContent='Ошибка связи. Проверьте терминал; не повторяйте авторизацию вслепую.';});"""
    script_hash = __import__('base64').b64encode(hashlib.sha256(script.encode()).digest()).decode()
    page = ('<!doctype html><html lang="ru"><meta charset="utf-8">'
            '<title>GSun — VK</title><h1>Подключение VK</h1><p id="result"></p>'
            '<script>' + script + '</script></html>').encode()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *args):
            pass  # Never log query strings, cookies, tokens or request bodies.

        def reply(self, status, body=b'', content_type='application/json', headers=()):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'sha256-" + script_hash + "'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            for k, v in headers:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def valid(self):
            return time.monotonic() < deadline and self.headers.get('Host') == 'greensun.energy'

        def has_cookie(self):
            try:
                c = SimpleCookie(self.headers.get('Cookie', ''))
                return hmac.compare_digest(c['gsun_vk_setup'].value, cookie)
            except (KeyError, ValueError):
                return False

        def do_GET(self):
            nonlocal started
            if not self.valid():
                return self.reply(403)
            u = urlsplit(self.path)
            if u.path == BASE + 'start':
                q = parse_qs(u.query)
                if started or q.get('ticket') != [ticket]:
                    return self.reply(403)
                started = True
                url = 'https://oauth.vk.ru/authorize?' + urlencode({
                    'client_id': APP, 'redirect_uri': CALLBACK, 'group_ids': GROUP,
                    'display': 'page', 'scope': 'photos', 'response_type': 'token',
                    'v': '5.199', 'state': state})
                return self.reply(302, headers=[('Location', url), ('Set-Cookie',
                    'gsun_vk_setup=' + cookie + '; Secure; HttpOnly; SameSite=Lax; Path=' + BASE + '; Max-Age=900')])
            if u.path == BASE + 'callback' and started and self.has_cookie():
                return self.reply(200, page, 'text/html; charset=utf-8')
            self.reply(404)

        def do_POST(self):
            nonlocal done
            if (not self.valid() or self.path != BASE + 'receive' or not started
                    or not self.has_cookie() or self.headers.get('Origin') != ORIGIN
                    or self.headers.get('Content-Type') != 'application/json'):
                return self.reply(403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20000:
                    raise ValueError('INVALID_LENGTH')
                body = json.loads(self.rfile.read(length))
                data = parse_result(body['fragment'], state)
                save_new(destination, data)
            except FileExistsError:
                return self.reply(409, b'{"status":"ALREADY_SAVED"}')
            except (ValueError, KeyError, TypeError):
                return self.reply(400, b'{"status":"AUTH_RESPONSE_REJECTED"}')
            except OSError:
                return self.reply(500, b'{"status":"SAVE_FAILED"}')
            done = True
            print('VK_CANDIDATE_SAVED — unverified; publishing disabled', flush=True)
            self.reply(200, b'{"status":"TOKEN_SAVED_UNVERIFIED. Publishing disabled. Close this tab."}',
                       headers=[('Set-Cookie', 'gsun_vk_setup=; Secure; HttpOnly; SameSite=Lax; Path=' + BASE + '; Max-Age=0')])

    with HTTPServer(('127.0.0.1', 8792), Handler) as server:
        server.timeout = 1
        print('OPEN_ONCE_IN_BROWSER — do not share this setup link:', flush=True)
        print(ORIGIN + BASE + 'start?ticket=' + ticket, flush=True)
        while not done and time.monotonic() < deadline:
            server.handle_request()
    print('CAPTURE_CLOSED; no posts sent', flush=True)

def self_test():
    import tempfile
    state = 'test-state'
    good = urlencode({'state': state, 'access_token_' + GROUP: 'x' * 64, 'expires_in': '86400'})
    assert parse_result(good, state)['publish_enabled'] is False
    for bad in [good.replace('test-state', 'wrong'), good + '&state=duplicate',
                good.replace(GROUP, '1'), 'state=test-state&error=access_denied']:
        try:
            parse_result(bad, state)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid OAuth response accepted')
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'candidate.json'
        save_new(p, parse_result(good, state))
        assert p.stat().st_mode & 0o777 == 0o600
        try:
            save_new(p, {})
        except FileExistsError:
            pass
        else:
            raise AssertionError('Credential overwritten')
    print('SELF_TEST_PASS: state, duplicate parameters, community binding, errors, permissions, no overwrite')

if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        self_test()
    elif sys.argv[1:] == ['--serve']:
        serve()
    else:
        raise SystemExit('Use --self-test or --serve. No action by default.')
