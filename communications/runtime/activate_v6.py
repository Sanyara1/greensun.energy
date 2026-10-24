"""Install an exact reviewed V6 and enable only its publisher timer."""
import copy, hashlib, os, shutil, sqlite3, subprocess, uuid
from pathlib import Path
from datetime import datetime,timezone,timedelta
import factory as f
import revise as r

EXPECTED='851bb5e09e13ad6018cc1fc463a19f31c13ce30290afcf997d87bd5c2611dd7b'
OLD='01d37563a58fcb38d876f57084e80f86f65bc42d862292ca0318ae3761d87266'
SENT=['2026-11-02']
def atomic(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    os.replace(tmp,path)
def env_flag(raw,value):
    lines=raw.decode().splitlines();key='GSUN_PUBLISH_ENABLED='
    matches=[i for i,s in enumerate(lines) if s.startswith(key)]
    f.require(len(matches)<=1,'STOP_ENV_DUPLICATE')
    if matches:lines[matches[0]]=key+value
    else:lines.append(key+value)
    return ('\n'.join(lines)+'\n').encode()
def system(*args):
    p=subprocess.run(['systemctl','--user',*args],capture_output=True,text=True,timeout=20)
    f.require(p.returncode==0,'STOP_SYSTEMCTL_'+args[0])
    return p.stdout.strip()
def inactive():
    for u in ('gsun-pr.timer','gsun-pr.service','gsun-pr-prepare.timer','gsun-pr-prepare.service'):
        f.require(system('show',u,'-p','ActiveState','--value') in ('inactive','failed'),'STOP_ACTIVE_UNIT')
def install(home,work,code,configpath,configraw):
    plan=f.read(work/'candidate.json');ready=f.read(work/'READY.json')
    f.require(f.sealed_hash(plan)==EXPECTED and ready['plan_hash']==EXPECTED,'STOP_REVIEWED_HASH_CHANGED')
    f.require(plan.get('approval') is None,'STOP_STAGE_APPROVED')
    f.require(plan.get('publication_holds')=={'2026-11-13':'RESERVE_NOT_AUTHORIZED'},'STOP_RESERVE_CHANGED')
    f.require(plan['review'].get('issues')==[] and plan['review'].get('pass') is True,'STOP_REVIEW_FAILED')
    f.require(set(plan['review'].get('reviewed_ids',[]))=={p['id'] for p in plan['posts']} - set(SENT),'STOP_REVIEW_SCOPE')
    original=f.read(home/'plans/2026-11.json')
    f.require(original.get('approval') is None and f.sealed_hash(original)==OLD,'STOP_LIVE_PLAN_CHANGED')
    saved=f.read(work/'source-snapshot.json')
    for name,sha in saved['files'].items():
        f.require(name in ('plans/2026-11.json','facts.json','media.json'),'STOP_SNAPSHOT_PATH')
        f.require(hashlib.sha256((home/name).read_bytes()).hexdigest()==sha,'STOP_LIVE_SOURCE_CHANGED')
    receipts=r.frozen_deliveries(home,original,SENT)
    f.require([list(x) for x in receipts]==saved['receipts'],'STOP_RECEIPT_CHANGED')
    f.require(plan['posts'][1]==original['posts'][1],'STOP_SENT_POST_CHANGED')
    for a,b in zip(original['posts'],plan['posts']):
        f.require(a['id']==b['id'] and a['scheduled_at']==b['scheduled_at'],'STOP_SCHEDULE_CHANGED')
    f.require(len(original['posts'])==len(plan['posts'])==13,'STOP_POST_COUNT')
    for p in (home/'plans').glob('*.json'):
        if p.name!='2026-11.json':f.require(not f.read(p).get('approval'),'STOP_OTHER_APPROVED_MONTH')
    f.require(f.instant(plan['posts'][0]['scheduled_at'])>datetime.now(timezone.utc)+timedelta(hours=25),'STOP_TOO_CLOSE_TO_FIRST_POST')
    facts,media=f.read(work/'facts.json'),f.read(work/'media.json')
    oldfacts,oldmedia=f.read(home/'facts.json'),f.read(home/'media.json')
    factmap={x['id']:x for x in facts}
    f.require(len(factmap)==len(facts),'STOP_DUPLICATE_FACTS')
    f.require(all(factmap.get(x['id'])==x for x in oldfacts),'STOP_EXISTING_FACT_CHANGED')
    f.require(all(media.get(k)==v for k,v in oldmedia.items()),'STOP_EXISTING_MEDIA_CHANGED')
    f.validate(plan,work,facts,media)
    f.require(configpath.read_bytes()==configraw,'STOP_CONFIG_CHANGED')
    f.require(not (home/'PAUSE').exists(),'STOP_ALREADY_PAUSED')
    backup=home/'backups'/('v6-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6])
    backup.mkdir(parents=True,mode=0o700)
    for name in ('facts.json','media.json','plans/2026-11.json'):
        target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);atomic(target,(home/name).read_bytes())
    atomic(backup/'factory.py',(code/'factory.py').read_bytes())
    atomic(backup/'runtime.env',configraw)
    with sqlite3.connect((home/'deliveries.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as src:
        with sqlite3.connect(backup/'deliveries.sqlite') as dst:src.backup(dst)
    atomic(home/'PAUSE',b'V6 installation in progress\n')
    # On any failure after this point PAUSE remains, and publication is still disabled.
    for item in media.values():
        raw=f.media_path(work,item).read_bytes();target=home/'assets'/item['path']
        f.require(target.resolve().is_relative_to((home/'assets').resolve()),'STOP_ASSET_PATH')
        if target.exists():f.require(target.read_bytes()==raw,'STOP_ASSET_COLLISION')
        else:atomic(target,raw)
    atomic(code/'factory.py',Path(f.__file__).read_bytes())
    f.write(home/'facts.json',facts);f.write(home/'media.json',media)
    f.write(home/'plans/2026-11.json',plan)
    f.approve(home/'plans/2026-11.json',home,EXPECTED)
    live=f.read(home/'plans/2026-11.json')
    f.require(live['approval']['hash']==EXPECTED and f.sealed_hash(live)==EXPECTED,'STOP_APPROVAL_READBACK')
    f.require(r.frozen_deliveries(home,live,SENT)==receipts,'STOP_LEDGER_CHANGED')
    (home/'PAUSE').unlink()
    try:
        f.require(f.tick(home,False)==[],'STOP_UNEXPECTED_DUE_EVENTS')
        atomic(configpath,env_flag(configraw,'yes'))
    except Exception:
        atomic(home/'PAUSE',b'V6 requires reconciliation\n');raise
    f.write(backup/'installation.json',{'plan_hash':EXPECTED,'frozen_sent_ids':SENT,'held_ids':['2026-11-13'],'owner_authorization':'Explicit launch instruction in conversation 2026-10-24','runtime_sha256':hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest()})
    return backup
def main():
    os.umask(0o077);home=Path.home()/'.local/share/gsun-pr';code=Path.home()/'gsun-pr'
    work=home/'revisions/gsun-november-2026-v6-final';cp=Path.home()/'.config/gsun-pr/runtime.env'
    mutated=False
    try:
        inactive()
        # Ensure the enabled unit is the known publisher, not an unrelated overridden command.
        expected_service=Path(__file__).with_name('gsun-pr.service').read_text().strip()
        expected_timer=Path(__file__).with_name('gsun-pr.timer').read_text().strip()
        for unit,expected in (('gsun-pr.service',expected_service),('gsun-pr.timer',expected_timer)):
            actual='\n'.join(x for x in system('cat',unit).splitlines() if not x.startswith('#')).strip()
            f.require(actual==expected,'STOP_UNIT_CONFIGURATION_CHANGED')
        cfg=r.load_env(cp);raw=cp.read_bytes()
        f.require(cfg.get('GSUN_GENERATE_ENABLED')!='yes','STOP_GENERATION_ENABLED')
        f.require(cfg.get('OWNER_CHAT_ID','').isdigit() and int(cfg['OWNER_CHAT_ID'])>0,'STOP_OWNER_ID')
        bot=f.Telegram(cfg.get('TELEGRAM_BOT_TOKEN'));bot.verify()
        owner=bot.call('getChat',{'chat_id':cfg['OWNER_CHAT_ID']})
        channel=bot.call('getChat',{'chat_id':f.CHANNEL})
        f.require(owner.get('type')=='private','STOP_OWNER_NOT_PRIVATE')
        f.require(channel.get('id')==f.CHANNEL and channel.get('username','').lower()=='gsun_ai','STOP_CHANNEL_CHANGED')
        with r.locked(home):
            inactive()
            # Flag is set before mutations so any installation failure remains paused.
            mutated=True
            backup=install(home,work,code,cp,raw)
        system('enable','--now','gsun-pr.timer')
        f.require(system('is-active','gsun-pr.timer')=='active','STOP_TIMER_NOT_ACTIVE')
        print('V6_INSTALLED_AND_TIMER_ACTIVE')
        print('PLAN_HASH='+EXPECTED)
        print('NEXT_POST: 2026-11-02 11:00 Europe/Moscow')
        print('11 future posts enabled; 1 already sent; November 30 held')
        print('BACKUP='+str(backup))
        print(system('show','gsun-pr.timer','-p','ActiveState','-p','NextElapseUSecRealtime'))
    except Exception as error:
        if mutated:
            atomic(home/'PAUSE',b'V6 activation stopped; inspect before resuming\n')
            try:atomic(cp,env_flag(cp.read_bytes(),'no'))
            except Exception:pass
            subprocess.run(['systemctl','--user','stop','gsun-pr.timer'],capture_output=True,timeout=20)
        print(str(error) if isinstance(error,f.Stop) else 'ACTIVATION_FAILED — secrets hidden')
        return 2
    return 0
