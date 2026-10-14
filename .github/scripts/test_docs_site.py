"""Verify snapshot preservation and the publication manifest without remote writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import os
import shutil
import textwrap
import unittest

spec = importlib.util.spec_from_file_location("docs_site", Path(__file__).with_name("docs_site.py"))
docs_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs_site)


class PublicationTests(unittest.TestCase):
    def test_release_snapshot_survives_updates_and_tag_moves_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.run(["git", "-C", str(repo), *args], check=True,
                                      capture_output=True, text=True)
            git("init")
            git("config", "user.name", "Documentation test")
            git("config", "user.email", "test@example.invalid")
            (repo / "source").write_text("release one")
            git("add", "source")
            git("commit", "-m", "release one")
            git("tag", "v1.0")
            latest = root / "latest"
            latest.mkdir()
            (latest / "README.html").write_text("development one")
            builds = []
            def builder(repo, tag, sha, destination, site_url):
                builds.append(tag)
                destination.mkdir()
                (destination / "README.html").write_text("frozen " + sha)
                return True
            releases = [{"tag_name": "v1.0", "draft": False, "prerelease": False}]
            first = root / "first"
            docs_site.assemble(repo, latest, root / "absent", first, releases,
                               "https://example.invalid/docs", builder)
            def snapshot(directory):
                return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in directory.rglob("*") if p.is_file()}
            frozen = snapshot(first / "v1.0")
            (latest / "README.html").write_text("development two")
            (repo / "source").write_text("release two")
            git("commit", "-am", "release two")
            git("tag", "v2.0")
            second = root / "second"
            docs_site.assemble(repo, latest, first, second,
                               releases + [{"tag_name": "v2.0"}, {"tag_name": "draft", "draft": True},
                                           {"tag_name": "preview", "prerelease": True}],
                               "https://example.invalid/docs", builder)
            self.assertEqual(frozen, snapshot(second / "v1.0"))
            self.assertEqual(builds, ["v1.0", "v2.0"])
            self.assertEqual((second / "latest/README.html").read_text(), "development two")
            versions = json.loads((second / "versions.json").read_text())
            self.assertEqual([v["version"] for v in versions], ["latest", "v2.0", "v1.0"])
            self.assertTrue((second / ".nojekyll").is_file())
            git("tag", "-f", "v1.0")
            with self.assertRaisesRegex(ValueError, "moved"):
                docs_site.assemble(repo, latest, second, root / "third", releases,
                                   "https://example.invalid/docs", builder)

    def test_workflow_creates_branch_updates_history_and_handles_noop(self):
        workflow = (Path(__file__).resolve().parents[1] / "workflows/documentation.yml").read_text()
        command = workflow.split("      - name: Update gh-pages branch\n        run: |\n", 1)[1]
        command = textwrap.dedent(command.split("      - uses:", 1)[0])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, remote, site = root / "workspace", root / "remote.git", root / "documentation-site"
            def git(*args):
                return subprocess.run(["git", *map(str, args)], check=True,
                                      capture_output=True, text=True)
            git("init", "--bare", remote)
            git("init", workspace)
            git("-C", workspace, "remote", "add", "origin", remote)
            env = dict(os.environ, RUNNER_TEMP=temp, GITHUB_WORKSPACE=str(workspace),
                       DOCS_COMMIT="test-source")
            for revision in ["first", "second", "second"]:
                if site.exists():
                    shutil.rmtree(site)
                site.mkdir()
                (site / "index.html").write_text(revision)
                result = subprocess.run(["bash", "-e", "-c", command], env=env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                git("-C", workspace, "fetch", "origin", "gh-pages:refs/remotes/origin/gh-pages")
            self.assertEqual(git("--git-dir", remote, "rev-list", "--count", "gh-pages").stdout.strip(), "2")
            self.assertEqual(git("--git-dir", remote, "show", "gh-pages:index.html").stdout, "second")

    def test_latest_switcher_uses_canonical_url_on_nested_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "api/generated"
            nested.mkdir(parents=True)
            fixture = "DOCUMENTATION_OPTIONS.theme_switcher_json_url = '../versions.json';"
            for page in [root / "index.html", nested / "function.html"]:
                page.write_text(fixture)
            docs_site.rewrite_latest(root, "https://example.invalid/docs/")
            for page in root.rglob("*.html"):
                self.assertIn('"https://example.invalid/docs/versions.json"', page.read_text())
            with tempfile.TemporaryDirectory() as empty:
                with self.assertRaisesRegex(ValueError, "No PyData"):
                    docs_site.rewrite_latest(Path(empty), "https://example.invalid/docs")

    def test_invalid_and_reserved_tags(self):
        for tag in ["../escape", "a/b", "latest", ".git", "versions.json", "index.html", "CNAME", "--option", ""]:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                docs_site.release_version(tag)


if __name__ == "__main__":
    unittest.main()
