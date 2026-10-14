"""The launcher must be able to tell an old running Tally from the files on disk."""

from tally import build


def test_build_id_changes_when_files_change(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1")
    monkeypatch.setattr(build, "ROOT", tmp_path)
    first = build.build_id()
    assert first == build.build_id()
    (tmp_path / "a.py").write_text("x = 2")
    assert build.build_id() != first
