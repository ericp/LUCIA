from types import SimpleNamespace

import pytest

from src import app as app_module


class FakeSession:
    def __init__(self, *, fail_commit=False):
        self.fail_commit = fail_commit
        self.rollback_called = False

    def add(self, detection):
        self.detection = detection

    def flush(self):
        self.detection.id = 7

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("database commit failed")

    def rollback(self):
        self.rollback_called = True


def test_capture_persistence_saves_database_reference_and_image(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "IMAGES_DIR", tmp_path)
    session = FakeSession()
    detection = SimpleNamespace(id=None, filename="")

    app_module._persist_detection_with_image(session, detection, b"image bytes")

    assert detection.filename == "007.jpg"
    assert (tmp_path / detection.filename).read_bytes() == b"image bytes"
    assert list(tmp_path.iterdir()) == [tmp_path / detection.filename]
    assert session.rollback_called is False


def test_capture_persistence_removes_image_when_database_commit_fails(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(app_module, "IMAGES_DIR", tmp_path)
    session = FakeSession(fail_commit=True)
    detection = SimpleNamespace(id=None, filename="")

    with pytest.raises(RuntimeError, match="database commit failed"):
        app_module._persist_detection_with_image(session, detection, b"image bytes")

    assert list(tmp_path.iterdir()) == []
    assert session.rollback_called is True
