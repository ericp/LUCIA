from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import app as app_module
from src.database import Base, Detection, RecognizedTextLineRecord


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


def test_text_capture_persists_type_and_structured_ocr_lines(tmp_path, monkeypatch):
    images_path = tmp_path / "images"
    images_path.mkdir()
    monkeypatch.setattr(app_module, "IMAGES_DIR", images_path)

    test_engine = create_engine(f"sqlite:///{tmp_path / 'test.sqlite3'}")
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine)()
    line = app_module.RecognizedTextLinePayload(
        text="Best before 2027",
        confidence=0.91,
        bounding_box=app_module.OCRBoundingBoxPayload(
            x=0.1,
            y=0.2,
            width=0.6,
            height=0.1,
        ),
    )
    detection = Detection(
        filename="",
        label="Visible text",
        capture_type="text",
        recognized_text=line.text,
        text_confidence=line.confidence,
    )

    app_module._persist_detection_with_image(
        test_session,
        detection,
        b"image bytes",
        recognized_lines=[line],
    )
    detection_id = detection.id
    test_session.close()

    verification_session = sessionmaker(bind=test_engine)()
    saved_detection = verification_session.query(Detection).filter_by(id=detection_id).one()
    saved_line = (
        verification_session.query(RecognizedTextLineRecord)
        .filter_by(detection_id=detection_id)
        .one()
    )

    assert saved_detection.capture_type == "text"
    assert saved_line.position == 0
    assert saved_line.text == "Best before 2027"
    assert saved_line.confidence == pytest.approx(0.91)
    assert saved_line.bounding_box_x == pytest.approx(0.1)
    assert saved_line.bounding_box_y == pytest.approx(0.2)
    assert saved_line.bounding_box_width == pytest.approx(0.6)
    assert saved_line.bounding_box_height == pytest.approx(0.1)
    verification_session.close()


def test_structured_ocr_is_canonical_source_for_text_and_confidence():
    lines = [
        app_module.RecognizedTextLinePayload(
            text=" First line ",
            confidence=0.8,
            bounding_box=app_module.OCRBoundingBoxPayload(
                x=0.1,
                y=0.7,
                width=0.4,
                height=0.1,
            ),
        ),
        app_module.RecognizedTextLinePayload(
            text="Second line",
            confidence=0.6,
            bounding_box=app_module.OCRBoundingBoxPayload(
                x=0.1,
                y=0.5,
                width=0.5,
                height=0.1,
            ),
        ),
    ]

    text, confidence, normalized_lines = app_module._canonical_ocr_values(
        "outdated combined text",
        0.1,
        lines,
    )

    assert text == "First line\nSecond line"
    assert confidence == pytest.approx(0.7)
    assert [line.text for line in normalized_lines] == ["First line", "Second line"]


def test_structured_ocr_rejects_out_of_bounds_boxes():
    line = app_module.RecognizedTextLinePayload(
        text="Outside image",
        confidence=0.9,
        bounding_box=app_module.OCRBoundingBoxPayload(
            x=0.8,
            y=0.2,
            width=0.3,
            height=0.1,
        ),
    )

    with pytest.raises(app_module.HTTPException) as error:
        app_module._canonical_ocr_values(line.text, line.confidence, [line])

    assert error.value.status_code == 422
