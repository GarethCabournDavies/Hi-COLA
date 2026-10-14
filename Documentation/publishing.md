# Building and publishing documentation

[Documentation home](index.md)

The site uses Sphinx, MyST Markdown, and the PyData theme. API pages are generated from function definitions and docstrings in the expression builder, numerical solver, parameter reader, and support utilities. Executable CLI and plotting modules are excluded because importing them runs their workflows. Write new function docstrings in NumPy style, including parameter meanings, normalisation, return values, and relevant failure conditions.

## Local build

Use Python 3.11 or newer in an isolated environment:

```sh
python -m pip install -r requirements-docs.txt
MPLBACKEND=Agg python -m sphinx -W --keep-going -b html Documentation Documentation/_build/html
python -m unittest discover -s .github/scripts -p 'test_*.py' -v
lychee --scheme http --scheme https --timeout 20 --max-retries 2 --max-concurrency 5 'Documentation/_build/html/**/*.html'
```

Open `Documentation/_build/html/index.html` to inspect the site. The online version dropdown reads the shared `versions.json` manifest created by the publishing job; it is not populated in a standalone local build. Generated API stubs and build outputs are ignored by Git.

## GitHub workflow

`.github/workflows/documentation.yml` builds on every pull request, with read-only repository permissions. Documentation warnings fail the build. Generated HTML is retained as the `documentation-html` workflow artifact for review. Pull requests never update the published site or documentation branch.

Publication runs after a successful **Documentation** build initiated by a push to the default branch. Pull-request runs never publish. The **Links** workflow runs independently. The publishing job replaces `latest/`, adds previously unpublished release snapshots, updates `versions.json`, commits the assembled site to `gh-pages`, and explicitly deploys it through GitHub Pages Actions. Publication jobs run serially to preserve branch updates. The generated branch contains HTML; edit documentation sources on the source branch instead.

In repository **Settings → Pages**, select **GitHub Actions** as the publishing source. Ensure the `github-pages` environment permits deployment from the default branch. No personal access token is required: the publishing job requests `contents: write`, `pages: write`, and `id-token: write`. Both workflows read `github.event.repository.default_branch`, currently `Hi-COLA_public`, rather than hard-coding its name. Pushes to other branches do not build or publish; pull requests targeting any branch still build.

## Link checks

`test_documentation_links.py` checks all built local links, page anchors, and referenced assets after the HTML build. It also verifies extraction of URLs from comments and docstrings without importing executable code. A generated code-reference page includes links from Python docstrings and comments, C/C++ comments, and Lua/INI comments, including bundled FML sources.

The independent `.github/workflows/links.yml` workflow builds on pull requests and default-branch pushes. Its `local-links` job runs the unit tests and retains the checked HTML artifact. Its advisory `external-links` job uses [lycheeverse/lychee-action](https://github.com/lycheeverse/lychee-action), with Lychee pinned to `v0.24.2`, to check HTTP and HTTPS links in the built HTML artifact. This includes guides, API docstrings, and generated code references. The check reuses the tested HTML instead of rebuilding it. Install the Lychee CLI separately to run the local network command above. It adds a GitHub job summary and saves `lychee/report.md` as the `documentation-link-report` artifact even when links fail. External failures are **advisory** and do not block publication: older references can be dead, and some sites reject automated requests. External fragment anchors are not checked; local HTML anchors are. Reports retain the failed URL and source location for investigation. Local structural failures fail the independent link workflow. To prevent merging a pull request with broken local links, make **Links / local-links** a required check in the default branch protection rules.

## Frozen release versions

On each push to the default branch, the workflow reads published, non-prerelease GitHub releases. For each new supported release tag, it checks out that tag and builds using its own code, documentation, Sphinx configuration, and declared dependencies in a fresh environment. The result is stored under `<tag>/`; `build-info.json` records the source commit and build time.

Existing release directories are copied without rebuilding or modifying their content. The shared dropdown manifest changes as versions are added, so older snapshots can still link to newer releases. Moving an already published tag causes publication to fail rather than silently replacing the snapshot. Deleting a GitHub release does not remove its archived docs.

Release tags must contain this documentation setup and use letters, digits, dots, underscores, or hyphens in a single path component. Tags predating the Sphinx setup are logged and skipped. Drafts and prereleases are excluded. A release published after the last push to the default branch appears after the **next push to the default branch**, keeping all documentation-branch writes tied to default-branch changes. Historical dependency declarations are preserved, but reproducible rebuilds also require pinning runtime dependencies in release sources; archived HTML itself is retained unchanged.

The site root links to `latest/`, labelled **Development (default branch)** in the dropdown. Released versions are listed separately by tag. Changing the GitHub Pages base URL later can invalidate links embedded in old snapshots; keep that URL stable when preserving published versions.
