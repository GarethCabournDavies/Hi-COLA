"""Extract web references from comments and docstrings without executing code."""
import ast
import io
from pathlib import Path
import re
import tokenize

URL = re.compile(r"https?://[^\s<>\"'`]+")
C_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')


def comment_links(path):
    """Return URL and source-line pairs in Python, C++, Lua, or INI comments."""
    text = path.read_text(errors="replace")
    comments = []
    if path.suffix == ".py":
        comments.extend((token.string, token.start[0]) for token in
                        tokenize.generate_tokens(io.StringIO(text).readline)
                        if token.type == tokenize.COMMENT)
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node, clean=False)
                if docstring is not None:
                    comments.append((docstring, node.body[0].lineno))
    elif path.suffix in {".c", ".cpp", ".h", ".hpp"}:
        comments.extend((match[0], text.count("\n", 0, match.start()) + 1)
                        for match in C_TOKEN.finditer(text)
                        if match[0].startswith(("//", "/*")))
    else:
        marker = "--" if path.suffix == ".lua" else "#"
        comments.extend((line.split(marker, 1)[1], number)
                        for number, line in enumerate(text.splitlines(), 1) if marker in line)
    for comment, line in comments:
        for match in URL.finditer(comment):
            url = match[0].rstrip(".,;:)]}")
            yield url, line + comment.count("\n", 0, match.start())


def collect_comment_links(root):
    """Include Hi-COLA and bundled FML code, plus build and packaging scripts."""
    sources = list((root / "HiCOLA").rglob("*"))
    sources += list((root / ".github/scripts").glob("*.py"))
    sources += [root / "setup.py", root / "Documentation/conf.py"]
    links = {}
    for path in sources:
        if path.is_file() and path.suffix in {".py", ".c", ".cpp", ".h", ".hpp", ".lua", ".ini"}:
            for url, line in comment_links(path):
                links.setdefault(url, []).append(f"{path.relative_to(root)}:{line}")
    return links


def documentation_sources(root):
    """List source documentation, excluding generated pages and the local audit."""
    paths = [root / "README.md"]
    paths += [p for p in (root / "Documentation").rglob("*")
              if p.suffix in {".md", ".rst"}
              and not {"_build", "api"}.intersection(p.relative_to(root / "Documentation").parts)
              and p.name != "FML-dependency-audit.md"]
    paths += [p for p in (root / "HiCOLA").rglob("*") if p.suffix in {".md", ".rst"} or p.name == "README"]
    return paths


def collect_documentation_links(root):
    """Include web references from the repository README and bundled guides."""
    links = {}
    for path in documentation_sources(root):
        text = path.read_text(errors="replace")
        for match in URL.finditer(text):
            url = match[0].rstrip(".,;:)]}")
            line = text.count("\n", 0, match.start()) + 1
            links.setdefault(url, []).append(f"{path.relative_to(root)}:{line}")
    return links
