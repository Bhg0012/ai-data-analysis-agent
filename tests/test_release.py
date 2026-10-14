"""The home screen shows which version is installed and when it was published."""

from tally import release


def test_release_info_from_git():
    info = release.release_info()
    assert info["version"]
    assert info["published"], "should know when this version was published"


def test_release_info_from_download_marker(tmp_path, monkeypatch):
    (tmp_path / ".tally-version").write_text("abcdef1234567890\n2026-10-14T20:17:16Z\n")
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    info = release.release_info()
    assert info == {"version": info["version"], "commit": "abcdef1", "published": "2026-10-14T20:17:16Z",
                    "source": "download"}
