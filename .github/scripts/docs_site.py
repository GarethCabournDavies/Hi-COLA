"""Assemble a Pages site while preserving already-published release trees."""
import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

LOG = logging.getLogger(__name__)


def run(*args, **kwargs):
    logging.debug("Running %s", args)
    return subprocess.run(args, check=True, **kwargs)


def release_version(tag):
    """Accept a single safe directory component for each release tag."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", tag):
        raise ValueError(f"Unsupported release tag: {tag!r}")
    if tag in {"latest", ".git", "versions.json", "index.html", "CNAME"}:
        raise ValueError(f"Reserved release tag: {tag!r}")
    return tag


def build_release(repo, tag, sha, destination, site_url):
    """Build against the tagged code, guides, configuration, and dependencies."""
    with tempfile.TemporaryDirectory(prefix="hicola-release-") as temporary:
        source = Path(temporary) / "source"
        run("git", "-C", str(repo), "worktree", "add", "--detach", str(source), sha)
        try:
            if not (source / "Documentation/conf.py").is_file():
                LOG.warning("Skipping %s: tag predates the Sphinx documentation setup", tag)
                return False
            environment = Path(temporary) / "environment"
            run(sys.executable, "-m", "venv", str(environment))
            python = environment / "bin/python"
            run(str(python), "-m", "pip", "install", "-r", str(source / "requirements-docs.txt"))
            env = dict(os.environ, DOCS_VERSION=tag, DOCS_SOURCE_REF=tag,
                       DOCS_SITE_URL=site_url, MPLBACKEND="Agg")
            run(str(python), "-m", "sphinx", "-W", "--keep-going", "-b", "html",
                str(source / "Documentation"), str(destination), cwd=source, env=env)
        finally:
            run("git", "-C", str(repo), "worktree", "remove", "--force", str(source))
    return True


def assemble(repo, latest, existing, destination, releases, site_url, builder=build_release):
    """Replace latest only; create release directories once and retain old entries."""
    if destination.exists():
        raise ValueError("Destination must be a fresh directory")
    if existing.exists():
        shutil.copytree(existing, destination, ignore=shutil.ignore_patterns(".git"))
    else:
        destination.mkdir(parents=True)
    latest_target = destination / "latest"
    if latest_target.exists():
        shutil.rmtree(latest_target)
    shutil.copytree(latest, latest_target)
    manifest = destination / "versions.json"
    entries = json.loads(manifest.read_text()) if manifest.exists() else []
    by_version = {item["version"]: item for item in entries if item["version"] != "latest"}
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release_version(release["tag_name"])
        sha = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", f"refs/tags/{tag}^{{commit}}"], text=True
        ).strip()
        target = destination / tag
        if target.exists():
            provenance = json.loads((target / "build-info.json").read_text())
            if provenance["commit"] != sha:
                raise ValueError(f"Published tag {tag} moved; refusing to replace its snapshot")
        else:
            if not builder(repo, tag, sha, target, site_url):
                continue
            (target / "build-info.json").write_text(json.dumps({
                "tag": tag, "commit": sha,
                "built_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2) + "\n")
        by_version[tag] = {
            "name": tag, "version": tag,
            "url": f"{site_url.rstrip('/')}/{quote(tag)}/",
        }
    versions = [{"name": "Development (default branch)", "version": "latest",
                 "url": f"{site_url.rstrip('/')}/latest/", "preferred": True}]
    versions.extend(sorted(by_version.values(), key=lambda item: item["version"], reverse=True))
    manifest.write_text(json.dumps(versions, indent=2) + "\n")
    (destination / ".nojekyll").touch()
    (destination / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>Hi-COLA documentation</title><meta http-equiv="refresh" content="0;url=latest/">'
        '<a href="latest/">Hi-COLA documentation</a></html>\n'
    )


def rewrite_latest(directory, site_url):
    """Give all development pages the canonical shared switcher endpoint."""
    endpoint = json.dumps(site_url.rstrip("/") + "/versions.json")
    replacements = 0
    for html in directory.rglob("*.html"):
        content, count = re.subn(
            r"(DOCUMENTATION_OPTIONS\.theme_switcher_json_url\s*=\s*)[^;]+;",
            lambda match: match[1] + endpoint + ";", html.read_text(),
        )
        if count:
            html.write_text(content)
            replacements += count
    if not replacements:
        raise ValueError("No PyData version-switcher configuration found in latest HTML")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--rewrite-latest", type=Path)
    parser.add_argument("--latest", type=Path)
    parser.add_argument("--existing", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--releases", type=Path)
    parser.add_argument("--site-url", required=True)
    args = parser.parse_args()
    if args.rewrite_latest:
        rewrite_latest(args.rewrite_latest, args.site_url)
        sys.exit(0)
    if not all([args.latest, args.existing, args.destination, args.releases]):
        parser.error("assembly requires --latest, --existing, --destination, and --releases")
    assemble(args.repo.resolve(), args.latest.resolve(), args.existing.resolve(),
             args.destination.resolve(), json.loads(args.releases.read_text()), args.site_url)
