#!/usr/bin/env python3
"""Attach the fixed RU card set to V5; never approve or enable publishing."""
import argparse
import base64
import copy
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
from datetime import datetime, timezone
import factory as f

SOURCE = 'gsun-november-2026-editorial-v5'
REVISION = 'gsun-november-2026-cards-ru-v1'

def load_reviewer():
    path = Path(__file__).with_name('revise-v2.py')
    if not path.exists():
        path = Path(__file__).with_name('revise.py')
    spec = importlib.util.spec_from_file_location('card_reviewer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

r = load_reviewer()

def fetch_asset(commit, item):
    f.require(bool(re.fullmatch('[0-9a-f]{40}', commit)), 'INVALID_COMMIT')
    name = item['file']
    f.require(bool(re.fullmatch(r'gsun-2026-11-\d{2}-ru\.png', name)), 'INVALID_ASSET_NAME')
    url = f'https://raw.githubusercontent.com/Sanyara1/greensun.energy/{commit}/communications/editorial/cards-2026-11/{name}'
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(1_000_001)
    f.require(len(data) <= 1_000_000 and data.startswith(b'\x89PNG\r\n\x1a\n'), 'INVALID_PNG')
    f.require(hashlib.sha256(data).hexdigest() == item['sha256'], 'CARD_HASH_MISMATCH')
    return data

def preview(home, plan, media, destination):
    cards = []
    for post in plan['posts']:
        path = f.media_path(home, media[post['media_id']])
        img = base64.b64encode(path.read_bytes()).decode()
        cards.append('<article><h2>'+html.escape(post['scheduled_at'])+'</h2><img alt="Карточка RU" src="data:image/png;base64,'+img+'"><p>'+html.escape(post['text_ru'])+'</p><details><summary>Перевод EN · изображение остаётся RU</summary><p>'+html.escape(post['text_en'])+'</p></details></article>')
    destination.write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GSun · полный предпросмотр</title><style>body{background:#f6f3ea;color:#153e35;font:18px system-ui;max-width:760px;margin:auto;padding:24px}article{margin:36px 0;padding:24px;background:white;border-radius:20px}img{width:100%}p{white-space:pre-wrap;line-height:1.6;overflow-wrap:anywhere}h2{font-size:20px}</style><h1>Ноябрь · карточки и подписи</h1><p>Черновик. Требуется визуальное согласование владельца. Отправка этим скриптом не включается.</p>'+''.join(cards)+'</html>')

def attach(home, manifest, fetcher, reviewer, check=lambda:None):
    path = home/'plans/2026-11.json'
    staging = home/'revisions'/REVISION
    with r.locked(home):
        check()
        original = f.read(path)
        media = f.read(home/'media.json'); facts = f.read(home/'facts.json')
        if original.get('media_revision') == REVISION:
            f.validate(original, home, facts, media)
            preview(home, original, media, staging/'preview.html')
            print('CARDS_ALREADY_ATTACHED: 13; no publishing started', flush=True)
            return original
        f.require(original.get('editorial_revision') == SOURCE, 'V5_REQUIRED')
        f.require(original.get('approval') is None, 'STOP_ALREADY_APPROVED')
        f.require(f.instant(original['posts'][0]['scheduled_at']) > datetime.now(timezone.utc), 'STOP_MONTH_STARTED')
        r.no_deliveries(home, original)
        f.validate(original, home, facts, media)
        f.require([p['id'] for p in original['posts']] == [m['post_id'] for m in manifest], 'CARD_IDS_MISMATCH')
        f.require(len(manifest) == 13 and len({m['file'] for m in manifest}) == 13, 'CARD_COUNT_INVALID')
        before = f.digest(original); source_hash = f.digest({'facts':facts,'media':media})
        plan = copy.deepcopy(original); updated_media = copy.deepcopy(media)
        plan['approval'] = None; plan['media_revision'] = REVISION
        plan['review'] = {'pass':False, 'issues':['REVIEW_PENDING']}
    # Slow downloads and reviews run outside the shared queue lock.
    for post, item in zip(plan['posts'], manifest):
        f.require(not post.get('media_id'), 'EXISTING_MEDIA_REQUIRES_RECONCILIATION')
        data = fetcher(item)
        f.require(hashlib.sha256(data).hexdigest() == item['sha256'], 'CARD_HASH_MISMATCH')
        mid = 'card-ru-' + post['id'] + '-' + item['sha256'][:12]
        asset = home/'assets'/REVISION/item['file']; asset.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        if asset.exists():
            f.require(asset.read_bytes() == data, 'EXISTING_ASSET_CHANGED')
        else:
            with asset.open('xb') as out:out.write(data)
        entry = {'path':str(asset.relative_to(home/'assets')), 'sha256':item['sha256'],
                 'rights_confirmed':True, 'kind':'illustration',
                 'provenance':'Original GSun programmatic typography; DejaVu font; no client photograph',
                 'language':'ru', 'card_copy':item['card_copy']}
        f.require(mid not in updated_media or updated_media[mid] == entry, 'MEDIA_ID_CONFLICT')
        updated_media[mid] = entry; post['media_id'] = mid
        post['text_ru'] += '\n\nИллюстрация: редакционная карточка GSun.'
        post['text_en'] += '\n\nIllustration: GSun editorial card (Russian).'
        plan['media_hashes'][mid] = f.digest(entry)
        for key in ('text_ru','text_en'):
            f.require(len(post[key].encode('utf-16-le'))//2 <= 1024, 'CAPTION_TOO_LONG')
        f.media_path(home, entry)
    f.write(staging/'candidate.json', plan)
    f.write(staging/'media-candidate.json', updated_media)
    preview(home, plan, updated_media, staging/'preview.html')
    verdict = reviewer(plan, facts, manifest, staging)
    f.require(isinstance(verdict,dict) and type(verdict.get('pass')) is bool and isinstance(verdict.get('issues'),list), 'REVIEW_FORMAT_INVALID')
    plan['review'] = {'pass':verdict['pass'] and not verdict['issues'], 'issues':verdict['issues'],
                     'posts_hash':f.digest(plan['posts']), 'scope':'captions_and_card_copy; owner_visual_review_required',
                     'checked_at':datetime.now(timezone.utc).isoformat()}
    f.write(staging/'candidate.json',plan)
    f.require(plan['review']['pass'], 'CARDS_REVIEW_REQUIRED_CURRENT_PLAN_UNCHANGED')
    with r.locked(home):
        check()
        f.require(f.digest(f.read(path)) == before, 'STOP_PLAN_CHANGED')
        f.require(f.digest({'facts':f.read(home/'facts.json'),'media':f.read(home/'media.json')}) == source_hash, 'STOP_SOURCES_CHANGED')
        r.no_deliveries(home, plan)
        f.require(f.instant(plan['posts'][0]['scheduled_at']) > datetime.now(timezone.utc), 'STOP_MONTH_STARTED')
        f.validate(plan,home,facts,updated_media)
        f.write(staging/'original-plan.json', original); f.write(staging/'original-media.json', media)
        # Additive catalog first: interruption here leaves the original plan valid.
        f.write(home/'media.json',updated_media)
        f.write(path,plan)
        f.require(f.digest(f.read(path))==f.digest(plan),'READBACK_FAILED')
        f.validate(f.read(path),home,f.read(home/'facts.json'),f.read(home/'media.json'))
    print('CARDS_READY: 13 RU images; captions verified; owner approval required; no publishing started',flush=True)
    return plan

def model_review(plan, facts, manifest, staging, config):
    verdict = r.review_with_cloudflare(plan,facts,config,staging/'captions')
    # Review card text as data; this is not a model inspection of pixels.
    for start in range(0,len(manifest),2):
        batch = []
        for post,item in zip(plan['posts'][start:start+2],manifest[start:start+2]):
            batch.append({'id':post['id'],'caption':post['text_ru'],'card_copy':item['card_copy'],
                          'facts':[x for x in facts if x['id'] in post['fact_ids']]})
        prompt = r.REVIEW_POLICY + 'Check card_copy agrees with the caption and facts. Card copy is a short headline/checklist, not a complete caption. Contact ceo@gsun.io and GSun branding are owner-provided design constants. Educational questions and blank worksheets are not measured results or feature claims. Do not demand additional detail solely because this is a short card.'
        key = f.digest({'prompt':prompt,'batch':batch,'model':config.get('LLM_MODEL'),'endpoint':config.get('LLM_URL')})
        cached = staging/('card-review-'+key+'.json')
        print('REVIEW_CARD_COPY: '+str(start//2+1)+'/7',flush=True)
        result = f.read(cached) if cached.exists() else r.review_call(prompt,{'posts':batch},config)
        r.check_verdict(result,{p['id'] for p in batch}); f.write(cached,result)
        verdict['pass'] = verdict['pass'] and result['pass']
        verdict['issues'].extend(result['issues'])
    return verdict

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
    os.umask(0o077)
    try:
        config_path=Path.home()/'.config/gsun-pr/runtime.env'
        config=r.load_env(config_path);config_hash=f.digest(config)
        def check():f.require(f.digest(r.load_env(config_path))==config_hash,'STOP_CONFIG_CHANGED')
        manifest=f.read(Path(__file__).with_name('cards-ru-manifest.json'))
        attach(Path.home()/'.local/share/gsun-pr',manifest,lambda item:fetch_asset(args.commit,item),
               lambda p,facts,m,s:model_review(p,facts,m,s,config),check)
    except f.Stop as e:
        print(str(e),file=sys.stderr);return 2
    except Exception:
        print('CARDS_FAILED_NO_SECRET_DETAILS',file=sys.stderr);return 2
    return 0

if __name__=='__main__':sys.exit(main())
