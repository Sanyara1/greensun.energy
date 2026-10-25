"""Boundary tests: approval, preview isolation, URLs, payload hashes and dates."""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import build_news_preview as news


class HTML(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def fixture_approval():
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {'article_id': news.ARTICLE['id'], 'candidate_sha256': news.candidate_hash(),
            'publication_approved': True, 'disclosure_approved': True,
            'approved_by': 'TEST FIXTURE — NOT AN OWNER DECISION',
            'decision_ref': 'test://synthetic-not-valid-for-deployment',
            'approved_at': now, 'published_at': now}


class NewsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.receipt = self.root / 'test-approval.json'

    def tearDown(self):
        self.temp.cleanup()

    def public(self, changes=None):
        approval = fixture_approval()
        approval.update(changes or {})
        self.receipt.write_text(json.dumps(approval))
        return news.build(self.root / 'out', 'public', self.receipt)

    def test_preview_is_not_public(self):
        report = news.build(self.root / 'out')
        self.assertIsNone(report['approval'])
        self.assertIsNone(report['published_at'])
        self.assertFalse(report['publishing_enabled'])
        self.assertFalse((self.root / 'out/news/sitemap.xml').exists())
        self.assertFalse((self.root / 'out/news/review.json').exists())
        for page in (self.root / 'out/news').rglob('*.html'):
            text = page.read_text()
            self.assertIn('noindex,nofollow', text)
            self.assertIn('не опубликовано', text)
            self.assertNotIn('rel="canonical"', text)
            self.assertNotIn('property="og:', text)
            self.assertNotIn('<time', text)

    def test_no_implicit_approval_or_output(self):
        with self.assertRaises(ValueError):
            news.build(self.root / 'out', 'public')
        self.assertFalse((self.root / 'out').exists())
        with self.assertRaises(ValueError):
            news.build(self.root / 'preview', 'preview', self.receipt)

    def test_refuse_stale_or_incomplete_approval(self):
        for change in ({'candidate_sha256': '0'*64}, {'publication_approved': False},
                       {'disclosure_approved': False}, {'decision_ref': ''},
                       {'approved_by': ''}, {'article_id': 'wrong'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.public(change)
            self.assertFalse((self.root / 'out').exists())

    def test_refuse_ambiguous_or_future_date(self):
        for value in ('2026-10-24T12:00:00', (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.public({'published_at': value})

    def test_public_metadata_and_sitemap(self):
        report = self.public()
        self.assertEqual(report['status'], 'PUBLIC_BUILD_NOT_DEPLOYED')
        self.assertIsNone(report['published_at'])
        expected = [news.NEWS, news.NEWS + 'digital-engineer/']
        for relative, url in zip(('index.html', 'digital-engineer/index.html'), expected):
            text = (self.root / 'out/news' / relative).read_text()
            parsed = HTML(text)
            self.assertNotIn('noindex', text)
            self.assertNotIn('Локальный предпросмотр', text)
            self.assertIn(('link', {'rel': 'canonical', 'href': url}), parsed.tags)
            self.assertIn(('meta', {'property': 'og:url', 'content': url}), parsed.tags)
            self.assertIn(('time', {'datetime': report['release_timestamp']}), parsed.tags)
            if relative.startswith('digital'):
                self.assertIn(('meta', {'property': 'article:published_time', 'content': report['release_timestamp']}), parsed.tags)
            image = next(a['content'] for t, a in parsed.tags if a.get('property') == 'og:image')
            self.assertTrue(image.startswith(news.NEWS + 'assets/cover-og.png?v='))
        xml = ET.parse(self.root / 'out/news/sitemap.xml')
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        self.assertEqual([x.text for x in xml.findall('.//s:loc', ns)], expected)
        self.assertEqual([x.text for x in xml.findall('.//s:lastmod', ns)], [report['release_timestamp']]*2)

    def test_links_assets_manifest_and_overwrite(self):
        report = news.build(self.root / 'out')
        root = self.root / 'out/news'
        self.assertEqual(set(report['files']), {'index.html','digital-engineer/index.html','assets/news.css',
                         'assets/cover.svg','assets/cover-mobile.svg','assets/cover-og.png','assets/favicon.svg'})
        for name, digest in report['files'].items():
            self.assertEqual(news.sha((root / name).read_bytes()), digest)
        for page in root.rglob('*.html'):
            for tag, attrs in HTML(page.read_text()).tags:
                for attr in ('href','src','srcset'):
                    path = urlsplit(attrs.get(attr, ''))
                    if not path.scheme and path.path:
                        target = (page.parent / path.path).resolve()
                        self.assertTrue(target.is_relative_to(root.resolve()))
                        self.assertTrue(target.exists(), str(target))
        with self.assertRaises(FileExistsError):
            news.build(self.root / 'out')
        for name, digest in report['files'].items():
            self.assertEqual(news.sha((root / name).read_bytes()), digest)
        (self.root / 'link').symlink_to(root, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            news.build(self.root / 'link')


if __name__ == '__main__':
    unittest.main()
