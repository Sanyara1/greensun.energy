#!/usr/bin/env python3
"""Build isolated /news/ files. Python standard library; no deploy or network calls."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ORIGIN = 'https://greensun.energy'
NEWS = ORIGIN + '/news/'
CONTACT = ORIGIN + '/contacts/#station-form'
ARTICLE = json.loads((HERE / 'article.json').read_text(encoding='utf-8'))
DESCRIPTION = 'Задачи солнечных станций и развитие цифрового инженера GSun: проверенные результаты, пилоты и планы.'
MONTHS = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def candidate_hash():
    paths = [HERE / 'article.json', Path(__file__).resolve(), *sorted((HERE / 'assets').glob('*'))]
    values = {p.name: sha(p.read_bytes()) for p in paths if p.is_file()}
    return sha(json.dumps(values, sort_keys=True).encode())


def stamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Publication and approval timestamps require a timezone')
    return dt


def validate_approval(path):
    if path is None:
        raise ValueError('Public build requires an explicit owner approval record')
    approval = json.loads(Path(path).read_text(encoding='utf-8'))
    if (approval.get('article_id') != ARTICLE['id']
            or approval.get('candidate_sha256') != candidate_hash()
            or approval.get('publication_approved') is not True
            or approval.get('disclosure_approved') is not True
            or not str(approval.get('approved_by') or '').strip()
            or not str(approval.get('decision_ref') or '').strip()):
        raise ValueError('Approval must identify this exact candidate, owner decision and disclosure')
    approved, published = stamp(approval['approved_at']), stamp(approval['published_at'])
    if approved > published or published > datetime.now(timezone.utc):
        raise ValueError('Use the actual release time, not a future or pre-approval date')
    return approval


def date_label(iso):
    dt = stamp(iso)
    return f'{dt.day} {MONTHS[dt.month - 1]} {dt.year}'


def page(title, content, *, detail=False, approval=None):
    prefix = '../' if detail else ''
    description = ARTICLE['description'] if detail else DESCRIPTION
    public = approval is not None
    url = NEWS + (ARTICLE['slug'] + '/' if detail else '')
    metadata = '<meta name="robots" content="noindex,nofollow">'
    if public:
        image_version = sha((HERE / 'assets/cover-og.png').read_bytes())[:12]
        metadata = f'''<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{'article' if detail else 'website'}">
<meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="GSun Energy">
<meta property="og:title" content="{html.escape(title, quote=True)} — GSun">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{NEWS}assets/cover-og.png?v={image_version}">
<meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="GSun.AI. Данные. Контекст. Следующий шаг.">
<meta name="twitter:card" content="summary_large_image">'''
        if detail:
            metadata += f'\n<meta property="article:published_time" content="{html.escape(approval["published_at"], quote=True)}">'
    banner = '' if public else '<div class="draft">Локальный предпросмотр · не опубликовано · требуется решение владельца</div>'
    css_version = sha((HERE / 'assets/news.css').read_bytes())[:12]
    listing = ('../' if public else '../index.html') if detail else ('./' if public else 'index.html')
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — GSun</title><meta name="description" content="{html.escape(description, quote=True)}">
<meta name="theme-color" content="#0a1110">{metadata}
<link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{prefix}assets/news.css?v={css_version}"></head>
<body><a class="skip" href="#main">К содержанию</a>{banner}<div class="wrap">
<header><a class="brand" href="{ORIGIN}/" aria-label="GSun Energy — главная">GSun<span> Energy</span></a>
<nav aria-label="Основная навигация"><a href="{listing}"{' aria-current="page"' if not detail else ''}>Новости</a><a href="{CONTACT}">Связаться ↗</a></nav></header>
<main id="main">{content}</main><footer>GSun · Солнечные станции и цифровой инженер.<br><a href="mailto:ceo@gsun.io">ceo@gsun.io</a></footer>
</div></body></html>'''


def picture(prefix='', card=False):
    return f'''<picture><source media="(max-width: 650px)" srcset="{prefix}assets/cover-mobile.svg">
<img class="{'card-image' if card else 'hero'}" src="{prefix}assets/cover.svg" width="1200" height="630" alt="GSun.AI. Данные. Контекст. Следующий шаг."></picture>'''


def build(destination, mode='preview', approval_path=None):
    if mode not in ('preview', 'public'):
        raise ValueError('Unknown build mode')
    if mode == 'preview' and approval_path is not None:
        raise ValueError('Preview does not accept or imply approval')
    approval = validate_approval(approval_path) if mode == 'public' else None
    destination = Path(destination)
    # Fail closed: never overwrite an existing directory or symlink.
    destination.mkdir(parents=True, exist_ok=False)
    news = destination / 'news'
    (news / ARTICLE['slug']).mkdir(parents=True)
    shutil.copytree(HERE / 'assets', news / 'assets')
    title, lead = html.escape(ARTICLE['title']), html.escape(ARTICLE['description'])
    date = (f'<time datetime="{html.escape(approval["published_at"], quote=True)}">{date_label(approval["published_at"])}</time>'
            if approval else '<span>Черновик от 24 октября 2026 · дата публикации не назначена</span>')
    badge = f'<div class="meta"><span class="badge">Направление разработки</span>{date}</div>'
    article_link = ARTICLE['slug'] + ('/' if approval else '/index.html')
    listing = f'''<p class="eyebrow">Журнал GSun</p><h1>Энергия.<br>Инженерия. Развитие.</h1>
<p class="lead">{DESCRIPTION}</p><div class="card">{picture(card=True)}<div class="card-body">{badge}
<h2><a class="title-link" href="{article_link}">{title}</a></h2><p>{lead}</p><a class="button" href="{article_link}">Читать материал →</a></div></div>'''
    sections = ''.join(f'<section><h2>{html.escape(h)}</h2><p>{html.escape(t)}</p></section>' for h, t in ARTICLE['sections'])
    detail = f'''<a class="back" href="{'../' if approval else '../index.html'}">← Все материалы</a><article>
{badge}<h1>{title}</h1><p class="lead">{lead}</p><figure>{picture('../')}
<figcaption>Редакционная иллюстрация GSun, не фотография объекта и не экран продукта.</figcaption></figure>
<div class="article-body">{sections}<aside class="note">Статус направления: разработка. Материал описывает наши цели и требования, а не готовность всех функций GSun.AI.</aside>
<a class="button" href="{CONTACT}">Обсудить задачу объекта ↗</a></div></article>'''
    (news / 'index.html').write_text(page('Новости и развитие', listing, approval=approval), encoding='utf-8')
    (news / ARTICLE['slug'] / 'index.html').write_text(page(ARTICLE['title'], detail, detail=True, approval=approval), encoding='utf-8')
    if approval:
        entries = ''.join(f'<url><loc>{escape(url)}</loc><lastmod>{escape(approval["published_at"])}</lastmod></url>' for url in (NEWS, NEWS + ARTICLE['slug'] + '/'))
        (news / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + entries + '</urlset>\n', encoding='utf-8')
    manifest = {
        'status': 'PUBLIC_BUILD_NOT_DEPLOYED' if approval else 'PREVIEW_ONLY',
        'article_id': ARTICLE['id'], 'candidate_sha256': candidate_hash(),
        'article': ARTICLE, 'approval': approval, 'published_at': None,
        'release_timestamp': approval['published_at'] if approval else None,
        'publishing_enabled': False, 'social_sends': 0,
        'files': {str(p.relative_to(news)): sha(p.read_bytes()) for p in sorted(news.rglob('*')) if p.is_file()},
    }
    # This private record is a sibling of news/, outside the install payload.
    (destination / 'review.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{manifest["status"]}: {destination}')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New private build directory, never the live web root')
    parser.add_argument('--mode', choices=('preview', 'public'), default='preview')
    parser.add_argument('--approval', type=Path, help='Explicit owner decision bound to candidate_sha256; public mode only')
    args = parser.parse_args()
    try:
        build(args.output, args.mode, args.approval)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'STOP: {error}\n')
