# Building and publishing documentation

[Documentation home](index.md)

The site uses Sphinx, MyST Markdown, the PyData theme, and Sphinx-multiversion. Python API pages come from source definitions and docstrings. Executable generator and plotting modules are excluded from imports. Use NumPy-style docstrings for new functions.

## Local build

Use Python 3.12.14 and the pinned documentation dependencies:

```sh
python -m pip install -r requirements-docs.lock
MPLBACKEND=Agg python -m sphinx -W --keep-going -b html Documentation Documentation/_build/html
lychee --offline --include-fragments --no-ignore --exclude-path '(^|/)_static/' -- 'Documentation/_build/html/**/*.html'
```

For a versioned build, fetch tags and set the default-branch name:

```sh
git fetch origin --tags
DOCS_DEFAULT_BRANCH=Hi-COLA_public MPLBACKEND=Agg sphinx-multiversion -W --keep-going Documentation Documentation/_build/html
```

Multiversion builds committed Git references, so uncommitted changes appear only in the ordinary Sphinx build. Generated API stubs and build output are ignored by Git. The version dropdown is populated by multiversion and preserves the current page when it exists in the selected version.

## GitHub Pages

`.github/workflows/documentation.yml` validates documentation on pull requests and builds the default branch and release tags on default-branch pushes. Both workflows read GitHub's default-branch setting, currently `Hi-COLA_public`, so renaming that branch needs no workflow edit.

The build uploads its HTML using `actions/upload-pages-artifact`. The publication job uses `actions/deploy-pages`, with `pages: write` and `id-token: write`. It creates no publishing branch and needs no repository write permission. Pull requests never deploy. Select **GitHub Actions** in repository **Settings → Pages** and allow the default branch in the `github-pages` deployment environment.

The site root redirects to the default-branch documentation. Each version has its own directory and a dropdown provided through Sphinx-multiversion's template context; no custom publication script or JSON manifest is needed.

## Release versions and environment

Version-number tags such as `v1.0.0` are included alongside the default branch. Tags without Sphinx sources and `conf.py` are skipped. Release tags should be immutable. A tag created after a deployment appears on the next default-branch push.

Tagged pages are rebuilt from the tagged source rather than preserving old HTML bytes. Builds use the shared documentation configuration and pinned environment from the deployment checkout. `requirements-docs.lock` pins direct and transitive dependencies, and the workflows pin the Python patch version. Each release should retain its lock file for historical rebuilds. Pinning package versions does not guarantee identical bytes across operating systems or toolchains. If release-specific dependency environments later diverge, build those releases separately with their own locks rather than assuming a single multiversion environment reproduces all historical environments.

## Independent link workflow

`.github/workflows/links.yml`, named **Links**, uses Lychee for both local and external checks. Local checks run offline and validate files and anchors in rendered HTML. Theme template files are excluded from scan inputs; assets referenced by pages are still checked. Make **Links / local-links** a required branch-protection check to prevent merging broken local links.

External checks scan documentation, rendered HTML, and Python, C++, Lua, and INI source files directly, including URLs in comments, docstrings, strings, and code blocks. Failures are advisory because external sites may be unavailable or reject automated requests. Lychee adds a job summary and saves `documentation-link-report`; local results are saved as `local-link-report`. No custom extraction script or Python link tests are used.
