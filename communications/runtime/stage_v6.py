"""Prepare and review V6 in isolated state. Never installs, approves or sends."""
from pathlib import Path
import base64
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
import factory as f
import revise as r

EXPECTED = '01d37563a58fcb38d876f57084e80f86f65bc42d862292ca0318ae3761d87266'
PRESERVE = ['2026-11-02']
RID = 'gsun-november-2026-v6-final'

def snapshot(home):
    return {name: hashlib.sha256((home/name).read_bytes()).hexdigest()
            for name in ('plans/2026-11.json', 'facts.json', 'media.json')}

def prepare(home, work, payload):
    original = f.read(home/'plans/2026-11.json')
    f.require(f.sealed_hash(original) == EXPECTED, 'STOP_ORIGINAL_CHANGED')
    f.require(original.get('approval') is None, 'STOP_ALREADY_APPROVED')
    receipts = r.frozen_deliveries(home, original, PRESERVE)
    r.future_unsent(original, PRESERVE)
    facts, media = f.read(home/'facts.json'), f.read(home/'media.json')
    f.validate(original, home, facts, media)
    before = snapshot(home)
    facts, media = copy.deepcopy(facts), copy.deepcopy(media)
    ids = {x['id'] for x in facts}
    for fact in payload['facts']:
        f.require(fact['id'] not in ids, 'STOP_FACT_ID_COLLISION')
        facts.append(fact); ids.add(fact['id'])
    plan = copy.deepcopy(original)
    f.require(len(payload['posts']) == len(plan['posts']), 'STOP_POST_COUNT')
    for i, post in enumerate(payload['posts']):
        old = original['posts'][i]
        f.require(post['id'] == old['id'] and post['scheduled_at'] == old['scheduled_at'], 'STOP_SCHEDULE_CHANGED')
        if post['id'] in PRESERVE:
            f.require(post == old, 'STOP_SENT_POST_CHANGED')
        plan['posts'][i] = copy.deepcopy(post)
    # Copy validated existing assets into staging. The live directory is read-only here.
    for key in original['media_hashes']:
        item = media[key]
        asset = f.media_path(home, item)
        dest = work/'assets'/item['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(asset.read_bytes())
    for key, item in payload['media'].items():
        f.require(key not in media, 'STOP_MEDIA_ID_COLLISION')
        path = Path(item['path'])
        f.require(not path.is_absolute() and '..' not in path.parts, 'STOP_ASSET_PATH')
        raw = base64.b64decode(payload['assets'][key], validate=True)
        f.require(hashlib.sha256(raw).hexdigest() == item['sha256'], 'STOP_ASSET_HASH')
        dest = work/'assets'/path
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
        media[key] = item
    plan.update(editorial_revision=RID, revision_of=EXPECTED, approval=None,
                publication_holds={'2026-11-13': 'RESERVE_NOT_AUTHORIZED'},
                minimum_publisher_features=['publication_holds', 'sent_before_reminders'])
    plan['fact_hashes'] = {x['id']: f.digest(x) for x in facts}
    plan['media_hashes'] = {k: f.digest(v) for k,v in media.items()}
    # Structural preflight only: this verdict is never saved or used for release.
    plan['review'] = {'pass':True, 'posts_hash':f.digest(plan['posts'])}
    f.validate(plan, work, facts, media)
    plan['review'] = {'pass':False, 'issues':['MODEL_REVIEW_PENDING']}
    f.write(work/'candidate.json',plan)
    f.write(work/'facts.json', facts); f.write(work/'media.json',media)
    f.write(work/'source-snapshot.json', {'files':before, 'receipts':receipts})
    return plan, facts, media, before, receipts

def stage(home, work, payload, config, text_reviewer=None, card_reviewer=None):
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    (work/'READY.json').unlink(missing_ok=True)
    with r.locked(home):
        plan,facts,media,before,receipts = prepare(home,work,payload)
    print('V6_STAGED: 13 cards; sent post frozen; November 30 held',flush=True)
    # Only editorial evidence and public copy are sent to the configured model.
    # Secrets, infrastructure addresses and internal source URLs are never included.
    evidence = [{k:x[k] for k in ('id','text','status')} for x in facts]
    review_plan=copy.deepcopy(plan)
    review_plan['posts']=[p for p in plan['posts'] if p['id'] not in PRESERVE]
    verdict = (text_reviewer or (lambda p,fs:r.review_with_cloudflare(p,fs,config,work)))(review_plan,evidence)
    issues = list(verdict['issues'])
    accepted = verdict.get('pass') is True and not issues
    cache_key=f.digest({'posts':plan['posts'],'media':media,'model':config.get('LLM_MODEL'),
                        'endpoint':config.get('LLM_URL'),'policy':'card-review-v6-1'})
    cache_path=work/('card-review-'+cache_key+'.json')
    cache=f.read(cache_path) if cache_path.exists() else {}
    for i in range(0,len(review_plan['posts']),2):
        batch=review_plan['posts'][i:i+2]; name='CARDS_'+str(i//2+1)
        doc={'posts':[{'id':p['id'],'text_ru':p['text_ru'],
                      'card_copy':media[p['media_id']]['card_copy']} for p in batch]}
        if name not in cache:
            print('REVIEWING: '+name,flush=True)
            prompt=r.REVIEW_POLICY+'Check card copy against caption: unsupported claims, plan versus pilot status, contradictions and private implementation details. These are typographic illustrations, not telemetry screenshots. Do not demand photographs or certification. Shared branding is allowed.'
            cache[name]=(card_reviewer or (lambda a,b:r.review_call(a,b,config)))(prompt,doc)
            r.check_verdict(cache[name],{p['id'] for p in batch})
            f.write(cache_path,cache)
        v=r.check_verdict(cache[name],{p['id'] for p in batch})
        accepted=accepted and v['pass'] is True and not v['issues']; issues.extend(v['issues'])
    plan['review']={'pass':bool(accepted),'issues':issues,'posts_hash':f.digest(plan['posts']),
                    'scope':'unsent_ru_en_and_card_copy; sent_content_receipt_frozen',
                    'reviewed_ids':[p['id'] for p in review_plan['posts']],
                    'frozen_sent_ids':PRESERVE,
                    'historical_findings':[
                        {'post_id':'2026-11-02','reason':'Published wording operation is broader than maintenance in evidence.'},
                        {'post_id':'2026-11-02','reason':'Published EN electrical connection is more specific than RU connection.'}],
                    'checked_at':datetime.now(timezone.utc).isoformat()}
    with r.locked(home):
        f.require(snapshot(home)==before,'STOP_LIVE_STATE_CHANGED')
        f.require(r.frozen_deliveries(home,f.read(home/'plans/2026-11.json'),PRESERVE)==receipts,
                  'STOP_DELIVERIES_CHANGED')
        r.future_unsent(plan,PRESERVE)
        f.write(work/'candidate.json',plan)
        if not accepted:
            print('V6_REVIEW_REQUIRED — live plan unchanged',flush=True)
            print(json.dumps(issues,ensure_ascii=False,indent=2))
            return False
        f.validate(plan,work,facts,media)
        f.write(work/'READY.json',{'plan_hash':f.sealed_hash(plan),'source_hash':EXPECTED,
                                  'hold_ids':['2026-11-13'],'installed':False,'publishing_enabled':False})
    print('V6_REVIEW_PASS — ready for installation; no publishing started',flush=True)
    print('V6_HASH='+f.sealed_hash(plan),flush=True)
    return True
