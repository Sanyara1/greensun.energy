#!/usr/bin/env python3
"""Build an isolated editorial preview. No network, credentials or live writes."""
import argparse
import hashlib
import html
import json
from pathlib import Path

ARTICLE = {
    "id": "GSUN-NEWS-001",
    "slug": "digital-engineer",
    "title": "Зачем солнечной станции цифровой инженер",
    "description": "Развиваем помощника, который связывает вопросы владельца станции с документами и данными объекта.",
    "status": "Направление разработки",
    "draft_date": "2026-10-24",
    "published_at": None,
    "approval": None,
    "sections": [
        ["От графика к понятному вопросу", "Владельцу солнечной станции важно понимать, что показывают данные, откуда взялся вывод и что стоит проверить дальше. Одного графика для ответа на все эти вопросы недостаточно."],
        ["Что мы развиваем", "GSun.AI — направление цифрового инженера: помощника, который связывает вопрос с документами и данными конкретного объекта. Начальный режим — чтение и объяснение. Если сведений недостаточно, это должно быть видно в ответе."],
        ["Как будем показывать готовность", "Готовность будем подтверждать конкретными проверками. В публикациях будем отдельно обозначать задачу, условия проверки, результат, ограничения и следующий шаг. План разработки не означает, что функция уже доступна всем пользователям."],
        ["Для кого это направление", "Для владельцев станций, обслуживающих инженеров и партнёров, которым нужен понятный разговор об оборудовании и данных. Обсудить задачу своего объекта можно с командой GSun."],
    ],
    "source_ids": ["GSUN_DIGITAL_ENGINEER_DIRECTION", "GSUN_PUBLIC_PROGRESS_POLICY"],
    "editorial_source": "communications/editorial/v6/proposed-facts.json",
    "editorial_source_commit": "140dd8855727d33e8c110ba3e3d620c360db813e",
    "disclosure": "New article requires owner approval; source records are not public-release approvals.",
}

CSS = '''*{box-sizing:border-box}body{margin:0;background:#0a1110;color:#e7ece8;font:18px/1.65 system-ui,sans-serif}a{color:#8fe6bb;text-underline-offset:5px}a:focus-visible{outline:3px solid #efd082;outline-offset:5px}.wrap{width:min(1120px,90%);margin:auto}header{display:flex;justify-content:space-between;gap:20px;align-items:center;padding:28px 0;border-bottom:1px solid #31433b}.brand{font-size:29px;font-weight:750;text-decoration:none;color:#fff}.brand span{color:#80d6ae}nav{display:flex;gap:22px;flex-wrap:wrap}nav a{font-size:15px}.draft{background:#ede2c8;color:#302c20;padding:10px 5%;font-size:14px}.eyebrow{letter-spacing:.17em;text-transform:uppercase;color:#91d5b3;font-size:13px}h1{font-size:clamp(36px,6vw,72px);line-height:1.08;letter-spacing:-.04em;max-width:900px;margin:24px 0}h2{font-size:28px;line-height:1.25}main{padding:64px 0}.lead{font-size:22px;color:#b8c9c0;max-width:760px}.meta{display:flex;gap:15px;flex-wrap:wrap;font-size:14px;color:#b8c9c0;margin:28px 0}.badge{border:1px solid #547461;border-radius:30px;padding:3px 14px}.card{display:grid;grid-template-columns:1fr 1fr;border:1px solid #314c3d;border-radius:20px;overflow:hidden;margin:45px 0;background:#101e19}.card img{width:100%;height:100%;object-fit:cover}.card-body{padding:32px}.button{display:inline-block;border:1px solid #80d6ae;border-radius:9px;padding:10px 18px;text-decoration:none;margin-top:16px}.article{max-width:760px;margin:40px auto}.article section{margin:42px 0}.hero{display:block;width:100%;border-radius:18px}.note{border-left:3px solid #80d6ae;padding:15px 22px;background:#14261e;color:#c2d9cb}figcaption{color:#9aafa2;font-size:13px}footer{padding:30px 0;border-top:1px solid #31433b;color:#a7bbb0;font-size:14px}@media(max-width:650px){header{align-items:flex-start}.card{grid-template-columns:1fr}.card-body{padding:23px}main{padding:38px 0}.lead{font-size:19px}nav{gap:8px;flex-direction:column}.article{margin:25px 0}}'''

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="680" viewBox="0 0 1200 680"><defs><radialGradient id="g"><stop stop-color="#205c43"/><stop offset="1" stop-color="#0b1712"/></radialGradient></defs><rect width="1200" height="680" fill="url(#g)"/><g fill="none" stroke="#5dcd99" stroke-width="2" opacity=".65"><path d="M90 465H330L430 365H690L790 265H1110M90 525H360L460 425H720L820 325H1110M90 585H390L490 485H750L850 385H1110"/><circle cx="430" cy="365" r="9"/><circle cx="790" cy="265" r="9"/><circle cx="720" cy="425" r="9"/></g><text x="90" y="110" fill="#9ee5bf" font-family="sans-serif" font-size="28" letter-spacing="8">GSun.AI</text><text x="90" y="235" fill="#eff8f2" font-family="sans-serif" font-size="62" font-weight="bold">Данные. Контекст.</text><text x="90" y="310" fill="#eff8f2" font-family="sans-serif" font-size="62" font-weight="bold">Понятный следующий шаг.</text></svg>'''

def page(title, content, depth=0):
    prefix = '../' if depth else ''
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{html.escape(title)} — GSun</title><meta name="description" content="{html.escape(ARTICLE['description'], quote=True)}"><link rel="stylesheet" href="{prefix}news.css"></head><body><div class="draft">Предпросмотр · черновик от 24 октября 2026 · не опубликовано</div><div class="wrap"><header><a class="brand" href="{prefix}index.html">GSun<span> Energy</span></a><nav aria-label="Навигация"><a href="https://greensun.energy/">Основной сайт ↗</a><a href="https://gsun.ai/start">Связаться ↗</a></nav></header><main>{content}</main><footer>GSun · Солнечные станции и цифровой инженер. <a href="mailto:ceo@gsun.io">ceo@gsun.io</a></footer></div></body></html>'''

def build(destination):
    # mkdir without exist_ok: fail closed, never overwrite existing previews/live files.
    destination.mkdir(parents=True, exist_ok=False)
    article_dir = destination / ARTICLE['slug']
    article_dir.mkdir()
    title = html.escape(ARTICLE['title'])
    lead = html.escape(ARTICLE['description'])
    badge = '<div class="meta"><span class="badge">Направление разработки</span><span>Редакционный черновик</span></div>'
    listing = f'''<p class="eyebrow">Журнал GSun</p><h1>Энергия.<br>Инженерия. Развитие.</h1><p class="lead">Задачи реальных объектов и развитие цифрового инженера. Отдельно показываем проверенные результаты, пилоты и планы.</p><div class="card"><img src="cover.svg" alt="Абстрактная иллюстрация связей между данными и инженерным вопросом"><div class="card-body">{badge}<h2>{title}</h2><p>{lead}</p><a class="button" href="digital-engineer/index.html">Читать материал →</a></div></div>'''
    sections = ''.join(f'<section><h2>{html.escape(h)}</h2><p>{html.escape(t)}</p></section>' for h,t in ARTICLE['sections'])
    detail = f'''<a href="../index.html">← Все материалы</a>{badge}<h1>{title}</h1><p class="lead">{lead}</p><figure style="margin:35px 0"><img class="hero" src="../cover.svg" alt="Данные. Контекст. Понятный следующий шаг."><figcaption>Редакционная иллюстрация GSun, не фотография объекта и не экран продукта.</figcaption></figure><article class="article">{sections}<aside class="note">Статус материала: направление разработки. Это не объявление о готовности всех функций GSun.AI.</aside><a class="button" href="https://gsun.ai/start">Обсудить задачу объекта ↗</a></article>'''
    files = {'index.html':page('Новости и развитие',listing), 'digital-engineer/index.html':page(ARTICLE['title'],detail,1),'news.css':CSS,'cover.svg':SVG}
    for name,content in files.items():
        (destination/name).write_text(content,encoding='utf-8')
    manifest = {'status':'PREVIEW_ONLY','article':ARTICLE,'files':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()},'publishing_enabled':False,'social_sends':0}
    (destination/'review.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NEWS_PREVIEW_READY:', destination)
    print('No live files, timers, plans or social channels modified.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New empty preview directory; never use a public web root')
    args = parser.parse_args()
    build(args.output)
