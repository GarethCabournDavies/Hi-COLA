"""Build guides and API reference from the checked-out Hi-COLA source."""
import ast
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
project = "Hi-COLA"
author = "Hi-COLA team"
release = os.environ.get("DOCS_VERSION", "latest")
version = release
extensions = [
    "myst_parser", "sphinx.ext.autodoc", "sphinx.ext.autosummary",
    "sphinx.ext.napoleon", "sphinx.ext.mathjax", "sphinx.ext.githubpages",
]
root_doc = "index"
exclude_patterns = ["_build", "README.md", "FML-dependency-audit.md"]
autosummary_generate = True
autodoc_typehints = "description"
napoleon_numpy_docstring = True
myst_enable_extensions = ["dollarmath", "colon_fence"]
html_theme = "pydata_sphinx_theme"
site_url = os.environ.get("DOCS_SITE_URL", "").rstrip("/")
html_theme_options = {
    "navbar_start": ["navbar-logo", "version-switcher"],
    "switcher": {
        "json_url": f"{site_url}/versions.json" if site_url else "../versions.json",
        "version_match": release,
    },
    # The shared manifest is created during publication, after this build.
    "check_switcher": False,
}
html_static_path = []
repository = os.environ.get("GITHUB_REPOSITORY", "GarethCabournDavies/Hi-COLA")
source_ref = os.environ.get("DOCS_SOURCE_REF", "Hi-COLA_public")
myst_url_schemes = {
    "http": None, "https": None, "mailto": None,
    "repo": {"url": f"https://github.com/{repository}/blob/{source_ref}/{{{{path}}}}"},
}

# Enumerate definitions without importing executable CLI modules.
modules = {
    "Expression builder": "HiCOLA.Frontend.expression_builder",
    "Numerical solver": "HiCOLA.Frontend.numerical_solver",
    "Parameter reader": "HiCOLA.Frontend.read_parameters",
    "Utilities": "HiCOLA.Utilities.Other.support",
}
lines = ["Python API", "==========", "",
         "Signatures and docstrings are generated from the checked-out source.",
         "Functions without docstrings show their signatures only.", ""]
for title, module in modules.items():
    tree = ast.parse((ROOT / (module.replace(".", "/") + ".py")).read_text())
    names = [node.name for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and not node.name.startswith("_")]
    lines.extend([title, "-" * len(title), "", ".. autosummary::",
                  "   :toctree: generated", "   :nosignatures:", ""])
    lines.extend(f"   {module}.{name}" for name in names)
    lines.append("")
(ROOT / "Documentation/api/index.rst").write_text("\n".join(lines))

# Include raw comment references so Sphinx linkcheck covers code as well as guides.
sys.path.insert(0, str(ROOT / ".github/scripts"))
from documentation_links import collect_comment_links, collect_documentation_links
comment_lines = ["Code references", "===============", "",
                 "Web links found in documentation, source comments, and docstrings, including bundled FML.", ""]
reference_links = collect_comment_links(ROOT)
for url, locations in collect_documentation_links(ROOT).items():
    reference_links.setdefault(url, []).extend(locations)
for url, locations in sorted(reference_links.items()):
    comment_lines.extend([f"* `{url} <{url}>`_", "",
                          "  Found in: " + ", ".join(f"``{location}``" for location in locations), ""])
(ROOT / "Documentation/api/code-links.rst").write_text("\n".join(comment_lines))
linkcheck_timeout = 20
linkcheck_retries = 2
linkcheck_workers = 5
linkcheck_anchors = False
linkcheck_rate_limit_timeout = 30
