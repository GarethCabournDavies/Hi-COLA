"""Check built documentation paths and anchors independently of scientific tests."""
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import unquote, urlsplit


class PageLinks(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.anchors = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.anchors.add(attrs["id"])
        if tag == "a":
            if "name" in attrs:
                self.anchors.add(attrs["name"])
            if "href" in attrs:
                self.links.append(attrs["href"])
        elif tag in {"img", "script"} and "src" in attrs:
            self.links.append(attrs["src"])
        elif tag == "link" and "href" in attrs:
            self.links.append(attrs["href"])


class DocumentationLinkTests(unittest.TestCase):
    def test_all_built_local_links_and_html_anchors(self):
        root = Path(__file__).resolve().parents[2] / "Documentation/_build/html"
        self.assertTrue((root / "index.html").is_file(), "Build Sphinx HTML before running link tests")
        pages = {path.resolve(): PageLinks(path.read_text()) for path in root.rglob("*.html")
                 if not {"_static", "_sources"}.intersection(path.relative_to(root).parts)}
        failures = []
        for source, page in pages.items():
            for href in page.links:
                url = urlsplit(href)
                if url.scheme or url.netloc:
                    self.assertNotIn("{path}", unquote(href), f"Unexpanded repository link in {source}")
                    continue
                target = (source.parent / unquote(url.path)).resolve() if url.path else source
                if target.is_dir():
                    target /= "index.html"
                if not target.exists():
                    failures.append(f"{source.relative_to(root)}: missing {href}")
                elif url.fragment and target.suffix == ".html":
                    fragment = unquote(url.fragment)
                    if fragment not in pages[target].anchors:
                        failures.append(f"{source.relative_to(root)}: missing anchor {href}")
        self.assertEqual(failures, [], "\n".join(failures))



if __name__ == "__main__":
    unittest.main()
