"""Check built documentation paths and anchors independently of scientific tests."""
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import re
import unittest
from urllib.parse import unquote, urlsplit

from documentation_links import comment_links, documentation_sources


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

    def test_documentation_source_local_paths(self):
        root = Path(__file__).resolve().parents[2]
        failures = []
        markdown_link = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        for path in documentation_sources(root):
            text = path.read_text(errors="replace")
            targets = [match[1].split()[0].strip("<>") for match in markdown_link.finditer(text)]
            targets.extend(re.findall(r'(?:src|srcset)="([^"]+)"', text))
            for href in targets:
                url = urlsplit(href)
                if url.scheme == "repo":
                    target = root / unquote(url.path)
                elif url.scheme or url.netloc or not url.path:
                    continue
                else:
                    target = path.parent / unquote(url.path)
                if not target.exists():
                    failures.append(f"{path.relative_to(root)}: missing {href}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_comment_scanner_includes_docstrings_and_ignores_code_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            python = root / "example.py"
            python.write_text('"""See https://example.invalid/doc."""\n'
                              '# See https://example.invalid/comment\n'
                              'url = "https://example.invalid/runtime"\n')
            self.assertEqual({url for url, _ in comment_links(python)},
                             {"https://example.invalid/doc", "https://example.invalid/comment"})
            cpp = root / "example.cpp"
            cpp.write_text('// https://example.invalid/cpp\n'
                           '/* https://example.invalid/block */\n'
                           'const char *url = "https://example.invalid/runtime";\n')
            self.assertEqual({url for url, _ in comment_links(cpp)},
                             {"https://example.invalid/cpp", "https://example.invalid/block"})


if __name__ == "__main__":
    unittest.main()
