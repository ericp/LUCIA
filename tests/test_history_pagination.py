from datetime import datetime, timedelta

import cv2
from fastapi.testclient import TestClient
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import app as app_module
from src.database import Base, Detection


def test_history_pages_are_ordered_and_cursor_does_not_repeat_items(
    tmp_path,
    monkeypatch,
):
    images_path = tmp_path / "images"
    images_path.mkdir()
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'history.sqlite3'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    test_session_factory = sessionmaker(bind=test_engine)
    monkeypatch.setattr(app_module, "SessionLocal", test_session_factory)
    monkeypatch.setattr(app_module, "IMAGES_DIR", images_path)
    thumbnails_path = tmp_path / "thumbnails"
    thumbnails_path.mkdir()
    monkeypatch.setattr(app_module, "THUMBNAILS_DIR", thumbnails_path)

    encoded, jpeg = cv2.imencode(
        ".jpg",
        np.zeros((800, 600, 3), dtype=np.uint8),
    )
    assert encoded

    session = test_session_factory()
    start = datetime(2026, 8, 1, 12, 0, 0)
    for offset in range(5):
        detection = Detection(
            filename="pending.jpg",
            label=f"Object {offset + 1}",
            confidence=0.8,
            scanned_at=start + timedelta(minutes=offset),
            capture_type="object",
        )
        session.add(detection)
        session.flush()
        detection.filename = f"{detection.id:03d}.jpg"
        (images_path / detection.filename).write_bytes(jpeg.tobytes())
    session.commit()
    session.close()

    client = TestClient(app_module.app)
    first = client.get("/detections/page", params={"limit": 2})
    assert first.status_code == 200
    first_payload = first.json()
    assert [item["id"] for item in first_payload["items"]] == [5, 4]
    assert first_payload["next_cursor"]
    assert first_payload["items"][0]["thumbnail_url"] == "/detections/5/thumbnail"

    thumbnail = client.get(first_payload["items"][0]["thumbnail_url"])
    assert thumbnail.status_code == 200
    thumbnail_image = cv2.imdecode(np.frombuffer(thumbnail.content, np.uint8), cv2.IMREAD_COLOR)
    assert max(thumbnail_image.shape[:2]) == 256
    assert (thumbnails_path / "005.jpg").is_file()

    second = client.get(
        "/detections/page",
        params={"limit": 2, "cursor": first_payload["next_cursor"]},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert [item["id"] for item in second_payload["items"]] == [3, 2]
    assert second_payload["next_cursor"]

    third = client.get(
        "/detections/page",
        params={"limit": 2, "cursor": second_payload["next_cursor"]},
    )
    assert third.status_code == 200
    assert [item["id"] for item in third.json()["items"]] == [1]
    assert third.json()["next_cursor"] is None


def test_history_page_rejects_invalid_cursor():
    client = TestClient(app_module.app)
    response = client.get(
        "/detections/page",
        params={"limit": 20, "cursor": "not-a-valid-cursor"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "History cursor is invalid"
