# LUCIA src.app:app --reload
from datetime import datetime, timezone
import base64
import binascii
import json
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
import cv2
import numpy as np
import os
import shutil
import uuid
from sqlalchemy import and_, or_

# Import detection logic, text-to-speech, and database models
from src.detect import detect_objects_in_frame
from src.tts import speak
from src.database import (
    PROJECT_ROOT,
    SessionLocal,
    Detection,
    RecognizedTextLineRecord,
    UserLabel,
)

app = FastAPI()


class OCRBoundingBoxPayload(BaseModel):
    x: float
    y: float
    width: float
    height: float


class RecognizedTextLinePayload(BaseModel):
    text: str
    confidence: float
    bounding_box: OCRBoundingBoxPayload


class DetectionTextUpdate(BaseModel):
    recognized_text: str
    confidence: Optional[float] = None
    recognized_lines: List[RecognizedTextLinePayload] = Field(default_factory=list)

# Serve static frontend at /web (NOT at "/")
FRONTEND_DIR = PROJECT_ROOT / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/web", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

@app.get("/")
def root():
    return RedirectResponse(url="/web/")


# CORS (to allow calls from iPhone/other host)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Paths

IMAGES_DIR = Path(
    os.environ.get("LUCIA_IMAGES_DIR", PROJECT_ROOT / "data" / "images")
).expanduser().resolve()
CORRECTED_IMAGES_DIR = Path(
    os.environ.get("LUCIA_CORRECTED_IMAGES_DIR", PROJECT_ROOT / "data" / "user_labels")
).expanduser().resolve()
THUMBNAILS_DIR = Path(
    os.environ.get("LUCIA_THUMBNAILS_DIR", PROJECT_ROOT / "data" / "thumbnails")
).expanduser().resolve()

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
CORRECTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)


# POST /detect

@app.post("/detect")
async def detect_object(file: UploadFile = File(...)):
    """
    Receives image, detects object, saves to DB (if there's detection) and responds to frontend with guidance hints.
    The image is always named as <id_padded>.jpg (example: 003.jpg)
    """
    contents = await file.read()

    # Process with OpenCV (not saving to disk yet until we have the id)
    npimg = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # Detection -> (label, confidence, hints)
    label, confidence, hints = detect_objects_in_frame(frame)

    if label:
        session = SessionLocal()
        try:
            detection = Detection(
                filename="",
                label=label,
                confidence=confidence,
                capture_type="object",
            )
            _persist_detection_with_image(session, detection, contents)
            detection_id = detection.id
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail="The captured image could not be saved",
            ) from error
        finally:
            session.close()

        # Local TTS on Mac
        try:
            speak(f"{label} detected")
        except Exception:
            pass

        return JSONResponse(
            content={
                "id": detection_id,
                "object_detected": label,
                "confidence": confidence,
                "message": f"Object detected: {label} ({confidence:.2f})",
                "hints": hints,
                "capture_type": "object",
            }
        )
    else:
        # No detection: image nor row is saved in DB
        try:
            speak("No relevant object detected")
        except Exception:
            pass

        return JSONResponse(
            content={
                "id": None,
                "object_detected": None,
                "confidence": None,
                "message": "No relevant object detected.",
                "hints": hints,
            }
        )


# POST /text-captures

@app.post("/text-captures")
async def save_text_capture(
    file: UploadFile = File(...),
    recognized_text: str = Form(...),
    confidence: Optional[float] = Form(None),
    recognized_lines: Optional[str] = Form(None),
):
    """Save a captured image when Apple Vision found text but YOLO found no object."""
    line_payloads = _parse_recognized_lines(recognized_lines)
    recognized_text, confidence, line_payloads = _canonical_ocr_values(
        recognized_text,
        confidence,
        line_payloads,
    )
    if not recognized_text:
        raise HTTPException(status_code=422, detail="Recognized text is required")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="Captured image is required")

    session = SessionLocal()
    try:
        detection = Detection(
            filename="",
            label="Visible text",
            confidence=None,
            recognized_text=recognized_text,
            text_confidence=confidence,
            capture_type="text",
        )
        _persist_detection_with_image(
            session,
            detection,
            contents,
            recognized_lines=line_payloads,
        )

        return {
            "id": detection.id,
            "recognized_text": detection.recognized_text,
            "text_confidence": detection.text_confidence,
            "capture_type": detection.capture_type,
            "recognized_text_lines": [
                _serialize_recognized_line(line) for line in line_payloads
            ],
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="The text capture could not be saved",
        ) from error
    finally:
        session.close()


# GET /detections

@app.get("/detections")
def list_detections():
    """Return all saved scans for older clients that do not support pagination."""
    session = SessionLocal()
    try:
        detections = (
            session.query(Detection)
            .order_by(Detection.scanned_at.desc(), Detection.id.desc())
            .all()
        )
        return _history_payloads(session, detections)
    finally:
        session.close()


@app.get("/detections/page")
def paginated_detections(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
):
    """Return one newest-first history page using an opaque keyset cursor."""
    cursor_values = _decode_history_cursor(cursor) if cursor else None
    session = SessionLocal()
    try:
        query = session.query(Detection).filter(
            Detection.filename.isnot(None),
            Detection.filename != "",
        )
        if cursor_values is not None:
            cursor_date, cursor_id = cursor_values
            query = query.filter(
                or_(
                    Detection.scanned_at < cursor_date,
                    and_(
                        Detection.scanned_at == cursor_date,
                        Detection.id < cursor_id,
                    ),
                )
            )

        rows = (
            query.order_by(Detection.scanned_at.desc(), Detection.id.desc())
            .limit(limit + 1)
            .all()
        )
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = (
            _encode_history_cursor(page_rows[-1])
            if has_more and page_rows
            else None
        )
        return {
            "items": _history_payloads(
                session,
                page_rows,
                include_missing_images=True,
            ),
            "next_cursor": next_cursor,
        }
    finally:
        session.close()


@app.get("/detections/{detection_id}/image")
def detection_image(detection_id: int):
    """Return the original captured image for a saved detection."""
    session = SessionLocal()
    try:
        detection = (
            session.query(Detection).filter(Detection.id == detection_id).first()
        )
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        image_path = _image_path_for(detection)
        if image_path is None:
            raise HTTPException(status_code=404, detail="Detection image not found")

        return FileResponse(image_path, media_type="image/jpeg", filename=image_path.name)
    finally:
        session.close()


@app.get("/detections/{detection_id}/thumbnail")
def detection_thumbnail(detection_id: int):
    """Create and cache a bandwidth-efficient history thumbnail on first use."""
    session = SessionLocal()
    try:
        detection = (
            session.query(Detection).filter(Detection.id == detection_id).first()
        )
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        image_path = _image_path_for(detection)
        if image_path is None:
            raise HTTPException(status_code=404, detail="Detection image not found")

        thumbnail_path = THUMBNAILS_DIR / f"{detection.id:03d}.jpg"
        if not thumbnail_path.is_file():
            _create_thumbnail(image_path, thumbnail_path)
        return FileResponse(
            thumbnail_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    finally:
        session.close()


@app.patch("/detections/{detection_id}/text")
def update_detection_text(detection_id: int, update: DetectionTextUpdate):
    """Store Apple Vision OCR output alongside a captured detection."""
    recognized_text, confidence, line_payloads = _canonical_ocr_values(
        update.recognized_text,
        update.confidence,
        update.recognized_lines,
    )

    session = SessionLocal()
    try:
        detection = (
            session.query(Detection).filter(Detection.id == detection_id).first()
        )
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        detection.recognized_text = recognized_text or None
        detection.text_confidence = confidence if recognized_text else None
        _replace_recognized_lines(session, detection_id, line_payloads)
        session.commit()
        return {
            "status": "updated",
            "id": detection_id,
            "recognized_text": detection.recognized_text,
            "text_confidence": detection.text_confidence,
            "capture_type": detection.capture_type,
            "recognized_text_lines": [
                _serialize_recognized_line(line) for line in line_payloads
            ],
        }
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _validate_recognized_text(
    recognized_text: str,
    confidence: Optional[float],
) -> None:
    if len(recognized_text) > 20_000:
        raise HTTPException(status_code=422, detail="Recognized text is too long")
    if confidence is not None and not 0 <= confidence <= 1:
        raise HTTPException(status_code=422, detail="Confidence must be between 0 and 1")


def _parse_recognized_lines(
    serialized_lines: Optional[str],
) -> List[RecognizedTextLinePayload]:
    if not serialized_lines:
        return []

    try:
        raw_lines = json.loads(serialized_lines)
        if not isinstance(raw_lines, list):
            raise ValueError("recognized_lines must be a list")
        lines = [RecognizedTextLinePayload(**line) for line in raw_lines]
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as error:
        raise HTTPException(
            status_code=422,
            detail="Recognized text lines are invalid",
        ) from error
    return lines


def _canonical_ocr_values(
    recognized_text: str,
    confidence: Optional[float],
    lines: List[RecognizedTextLinePayload],
):
    normalized_lines = _normalize_recognized_lines(lines)
    if normalized_lines:
        recognized_text = "\n".join(line.text for line in normalized_lines)
        confidence = sum(line.confidence for line in normalized_lines) / len(normalized_lines)
    else:
        recognized_text = recognized_text.strip()

    _validate_recognized_text(recognized_text, confidence)
    return recognized_text, confidence, normalized_lines


def _normalize_recognized_lines(
    lines: List[RecognizedTextLinePayload],
) -> List[RecognizedTextLinePayload]:
    if len(lines) > 500:
        raise HTTPException(status_code=422, detail="Too many recognized text lines")

    normalized = []
    total_text_length = 0
    for line in lines:
        line_text = line.text.strip()
        if not line_text or len(line_text) > 2_000:
            raise HTTPException(status_code=422, detail="Recognized text line is invalid")
        if not 0 <= line.confidence <= 1:
            raise HTTPException(status_code=422, detail="Line confidence must be between 0 and 1")

        box = line.bounding_box
        coordinates = (box.x, box.y, box.width, box.height)
        if any(value < 0 or value > 1 for value in coordinates):
            raise HTTPException(status_code=422, detail="Text bounding box is invalid")
        if box.x + box.width > 1.001 or box.y + box.height > 1.001:
            raise HTTPException(status_code=422, detail="Text bounding box is out of bounds")

        total_text_length += len(line_text)
        normalized.append(
            RecognizedTextLinePayload(
                text=line_text,
                confidence=line.confidence,
                bounding_box=box,
            )
        )

    if total_text_length > 20_000:
        raise HTTPException(status_code=422, detail="Recognized text is too long")
    return normalized


def _serialize_recognized_line(line) -> dict:
    bounding_box = getattr(line, "bounding_box", None)
    return {
        "text": line.text,
        "confidence": line.confidence,
        "bounding_box": {
            "x": bounding_box.x if bounding_box is not None else line.bounding_box_x,
            "y": bounding_box.y if bounding_box is not None else line.bounding_box_y,
            "width": (
                bounding_box.width if bounding_box is not None else line.bounding_box_width
            ),
            "height": (
                bounding_box.height if bounding_box is not None else line.bounding_box_height
            ),
        },
    }


def _history_payloads(
    session,
    detections: List[Detection],
    include_missing_images: bool = False,
) -> List[dict]:
    if not detections:
        return []

    detection_ids = [detection.id for detection in detections]
    corrected_labels = {}
    for correction in (
        session.query(UserLabel)
        .filter(UserLabel.detection_id.in_(detection_ids))
        .order_by(UserLabel.id.asc())
        .all()
    ):
        corrected_labels[correction.detection_id] = correction.label

    recognized_lines_by_detection: Dict[int, List[RecognizedTextLineRecord]] = {}
    for line in (
        session.query(RecognizedTextLineRecord)
        .filter(RecognizedTextLineRecord.detection_id.in_(detection_ids))
        .order_by(
            RecognizedTextLineRecord.detection_id.asc(),
            RecognizedTextLineRecord.position.asc(),
        )
        .all()
    ):
        recognized_lines_by_detection.setdefault(line.detection_id, []).append(line)

    payloads = []
    for detection in detections:
        if not include_missing_images and _image_path_for(detection) is None:
            continue

        corrected_label = corrected_labels.get(detection.id)
        scanned_at = detection.scanned_at or datetime.now(timezone.utc)
        if scanned_at.tzinfo is None:
            scanned_at = scanned_at.replace(tzinfo=timezone.utc)
        else:
            scanned_at = scanned_at.astimezone(timezone.utc)

        payloads.append(
            {
                "id": detection.id,
                "label": corrected_label or detection.label,
                "original_label": detection.label,
                "corrected_label": corrected_label,
                "confidence": detection.confidence,
                "scanned_at": scanned_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "image_url": f"/detections/{detection.id}/image",
                "thumbnail_url": f"/detections/{detection.id}/thumbnail",
                "details": detection.recognized_text,
                "recognized_text": detection.recognized_text,
                "text_confidence": detection.text_confidence,
                "capture_type": detection.capture_type,
                "recognized_text_lines": [
                    _serialize_recognized_line(line)
                    for line in recognized_lines_by_detection.get(detection.id, [])
                ],
            }
        )
    return payloads


def _encode_history_cursor(detection: Detection) -> str:
    scanned_at = detection.scanned_at or datetime.min
    if scanned_at.tzinfo is not None:
        scanned_at = scanned_at.astimezone(timezone.utc).replace(tzinfo=None)
    payload = json.dumps(
        {"scanned_at": scanned_at.isoformat(timespec="microseconds"), "id": detection.id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_history_cursor(cursor: str):
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        scanned_at = datetime.fromisoformat(payload["scanned_at"])
        detection_id = int(payload["id"])
        if detection_id < 1:
            raise ValueError("invalid detection id")
        if scanned_at.tzinfo is not None:
            scanned_at = scanned_at.astimezone(timezone.utc).replace(tzinfo=None)
        return scanned_at, detection_id
    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise HTTPException(status_code=422, detail="History cursor is invalid") from error


def _create_thumbnail(source_path: Path, destination_path: Path) -> None:
    image = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=500, detail="Detection thumbnail could not be created")

    height, width = image.shape[:2]
    largest_dimension = max(height, width)
    if largest_dimension > 256:
        scale = 256 / largest_dimension
        image = cv2.resize(
            image,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    encoded, thumbnail_data = cv2.imencode(
        ".jpg",
        image,
        [cv2.IMWRITE_JPEG_QUALITY, 80],
    )
    if not encoded:
        raise HTTPException(status_code=500, detail="Detection thumbnail could not be created")

    temporary_path = destination_path.with_name(
        f".{destination_path.name}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with temporary_path.open("xb") as thumbnail_file:
            thumbnail_file.write(thumbnail_data.tobytes())
            thumbnail_file.flush()
            os.fsync(thumbnail_file.fileno())
        os.replace(temporary_path, destination_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _add_recognized_lines(
    session,
    detection_id: int,
    lines: List[RecognizedTextLinePayload],
) -> None:
    for position, line in enumerate(lines):
        box = line.bounding_box
        session.add(
            RecognizedTextLineRecord(
                detection_id=detection_id,
                position=position,
                text=line.text,
                confidence=line.confidence,
                bounding_box_x=box.x,
                bounding_box_y=box.y,
                bounding_box_width=box.width,
                bounding_box_height=box.height,
            )
        )


def _replace_recognized_lines(
    session,
    detection_id: int,
    lines: List[RecognizedTextLinePayload],
) -> None:
    session.query(RecognizedTextLineRecord).filter(
        RecognizedTextLineRecord.detection_id == detection_id
    ).delete(synchronize_session=False)
    _add_recognized_lines(session, detection_id, lines)


def _persist_detection_with_image(
    session,
    detection: Detection,
    contents: bytes,
    recognized_lines: Optional[List[RecognizedTextLinePayload]] = None,
) -> None:
    """Commit a detection and its image together, cleaning up either on failure."""
    temporary_path = None
    final_path = None
    final_file_created = False

    try:
        session.add(detection)
        session.flush()

        final_name = f"{detection.id:03d}.jpg"
        final_path = IMAGES_DIR / final_name
        temporary_path = IMAGES_DIR / f".{final_name}.{uuid.uuid4().hex}.tmp"

        with temporary_path.open("xb") as image_file:
            image_file.write(contents)
            image_file.flush()
            os.fsync(image_file.fileno())

        # A hard link publishes the complete file atomically and refuses to
        # overwrite an existing capture with the same database identifier.
        os.link(temporary_path, final_path)
        final_file_created = True
        temporary_path.unlink()
        temporary_path = None

        detection.filename = final_name
        if recognized_lines:
            _add_recognized_lines(session, detection.id, recognized_lines)
        session.commit()
    except Exception:
        session.rollback()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if final_file_created and final_path is not None:
            final_path.unlink(missing_ok=True)
        raise


def _image_path_for(detection: Detection) -> Optional[Path]:
    if not detection.filename:
        return None

    images_root = IMAGES_DIR.resolve()
    candidate = (images_root / detection.filename).resolve()
    try:
        candidate.relative_to(images_root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


# POST /guide

@app.post("/guide")
async def guide_object(file: UploadFile = File(...)):
    """
    Receives a frame (lightweight photo) and returns hints to guide the user in real time.
    Does not save to DB nor do TTS on the server.
    """
    contents = await file.read()
    npimg = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    label, confidence, hints = detect_objects_in_frame(frame)

    ready = bool(
        hints
        and hints.get("distance") == "ok"
        and hints.get("center") == "centered"
        and hints.get("light") == "ok_light"
    )

    return JSONResponse(
        content={
            "object_detected": label,
            "confidence": confidence,
            "hints": hints,
            "ready": ready,
        }
    )


# POST /correct

@app.post("/correct")
async def correct_label(id: int = Form(...), new_label: str = Form(...)):
    """
    Receives label correction and saves it to DB (user_labels table).
    Maintains the original schema: copies the image as <new_label>_<filename> in data/user_labels/.
    """
    session = SessionLocal()
    detection = session.query(Detection).filter(Detection.id == id).first()

    if detection:
        # Save corrected label in user_labels table 
        user_label = UserLabel(detection_id=id, label=new_label)
        session.add(user_label)
        session.commit()

        # Copy original image to corrections folder with label prefix
        original_path = IMAGES_DIR / detection.filename
        if original_path.exists():
            corrected_filename = f"{new_label}_{detection.filename}"
            corrected_path = CORRECTED_IMAGES_DIR / corrected_filename
            shutil.copy(original_path, corrected_path)

        session.close()
        return {"status": "updated", "id": id, "new_label": new_label}

    session.close()
    return {"status": "not found", "id": id}

# GET /yolo-selftest

@app.get("/yolo-selftest")
def yolo_selftest():
    """
    Self-check of YOLOv8 installation using the example image bus.jpg included in Ultralytics.
    """
    try:
        from ultralytics.utils import ASSETS
        test_img = os.path.join(ASSETS, "bus.jpg")
        from src.detect import model
        r = model.predict(test_img, imgsz=640, conf=0.01, iou=0.3, device="cpu", verbose=False)
        n = 0 if r[0].boxes is None else len(r[0].boxes)
        return {"ok": True, "boxes_on_bus_jpg": int(n)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
