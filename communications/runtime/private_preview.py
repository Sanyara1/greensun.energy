#!/usr/bin/env python3
"""Verify the channel owner, bind a private chat, and send one preview once."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid
import factory as f


def load_reviewer():
    path = Path(__file__).with_name('revise-v2.py')
    if not path.exists():
        path = Path(__file__).with_name('revise.py')
    spec = importlib.util.spec_from_file_location('preview_reviewer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

r = load_reviewer()


def send_preview(home, config_path, owner_id, username, client=None, month='2026-11', post_id='2026-11-02'):
    f.require(type(owner_id) is int and owner_id > 0, 'PRIVATE_OWNER_REQUIRED')
    f.require(bool(re.fullmatch(r'[A-Za-z0-9_]{5,32}', username)), 'OWNER_USERNAME_INVALID')
    original_config = config_path.read_bytes()
    config = r.load_env(config_path)  # Refuses enabled publication.
    f.require(config.get('OWNER_CHAT_ID', '') in ('', str(owner_id)), 'EXISTING_OWNER_DIFFERS')
    bot = client or f.Telegram(config.get('TELEGRAM_BOT_TOKEN'))
    me = bot.call('getMe', {})
    f.require(me.get('username', '').lower() == f.BOT, 'WRONG_BOT')
    admins = bot.call('getChatAdministrators', {'chat_id': f.CHANNEL})
    f.require(any(a.get('status') == 'creator' and a.get('user', {}).get('id') == owner_id
                  and not a['user'].get('is_bot', False) for a in admins), 'CHANNEL_OWNER_CHANGED')
    chat = bot.call('getChat', {'chat_id': owner_id})
    f.require(chat.get('type') == 'private' and chat.get('id') == owner_id
              and chat.get('username', '').lower() == username.lower(), 'PRIVATE_RECIPIENT_MISMATCH')
    print('RECIPIENT_VERIFIED: @' + username, flush=True)
    with r.locked(home):
        f.require(config_path.read_bytes() == original_config, 'CONFIG_CHANGED')
        plan = f.read(home/'plans'/(month+'.json'))
        media = f.read(home/'media.json')
        f.validate(plan, home, f.read(home/'facts.json'), media)
        matches = [p for p in plan['posts'] if p['id'] == post_id]
        f.require(len(matches) == 1, 'POST_NOT_FOUND')
        post = matches[0]
        f.require(bool(post.get('media_id')), 'PREVIEW_IMAGE_REQUIRED')
        image_path = f.media_path(home, media[post['media_id']])
        f.require(plan.get('media_revision') == 'gsun-november-2026-cards-ru-v1', 'EXPECTED_CARD_REVISION_REQUIRED')
        # Only bind the verified private recipient; preserve every other setting.
        if not config.get('OWNER_CHAT_ID'):
            lines = [line for line in original_config.decode().splitlines()
                     if line.partition('=')[0].strip() != 'OWNER_CHAT_ID']
            lines.append('OWNER_CHAT_ID=' + str(owner_id))
            temporary = config_path.with_name('runtime.env.' + uuid.uuid4().hex)
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as out:
                out.write('\n'.join(lines) + '\n'); out.flush(); os.fsync(out.fileno())
            os.replace(temporary, config_path)
        print('OWNER_CHAT_SAVED', flush=True)
        # Separate receipt store: never marks a scheduled channel post as delivered.
        journal = home/'private-previews.sqlite'
        with sqlite3.connect(journal) as db:
            journal.chmod(0o600)
            db.execute('CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY,status TEXT,result TEXT)')
            key = f'private-preview-v1:{owner_id}:{post_id}'
            def deliver():
                result = bot.send(owner_id, post['text_ru'], image_path)
                f.require(result.get('chat', {}).get('id') == owner_id and result.get('message_id'),
                          'TELEGRAM_RECEIPT_MISMATCH')
                return {'message_id':result['message_id'], 'post_hash':f.digest(post),
                        'image_sha256':hashlib.sha256(image_path.read_bytes()).hexdigest()}
            status = f.once(db, key, deliver)
            row = db.execute('SELECT status FROM deliveries WHERE id=?', (key,)).fetchone()
        if row and row[0] == 'sent':
            print('PRIVATE_PREVIEW_SENT' if status == 'sent' else 'PRIVATE_PREVIEW_ALREADY_SENT', flush=True)
            print('One private card; channel plan and publication flags unchanged', flush=True)
            return 'sent'
        raise f.Stop('PREVIEW_RESULT_UNKNOWN_CHECK_TELEGRAM_NO_AUTO_RETRY')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--owner-id',required=True,type=int)
    parser.add_argument('--owner-username',required=True)
    args=parser.parse_args();os.umask(0o077)
    try:
        send_preview(Path.home()/'.local/share/gsun-pr',Path.home()/'.config/gsun-pr/runtime.env',
                     args.owner_id,args.owner_username)
    except f.Stop as error:
        print(str(error),file=sys.stderr);return 2
    except Exception:
        print('PRIVATE_PREVIEW_FAILED_NO_SECRET_DETAILS',file=sys.stderr);return 2
    return 0

if __name__=='__main__':sys.exit(main())
