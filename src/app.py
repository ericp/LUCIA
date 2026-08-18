# LUCIA src.app:app --reload
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import cv2
import numpy as np
import os
import shutil

# Import detection logic, text-to-speech, and database models
from src.detect import detect_objects_in_frame
from src.tts import speak
from src.database import PROJECT_ROOT, SessionLocal, Detection, UserLabel

app = FastAPI()


class DetectionTextUpdate(BaseModel):
    recognized_text: str
    confidence: Optional[float] = None

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

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
CORRECTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


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
        # Create row in DB to get the id
        session = SessionLocal()
        detection = Detection(filename="", label=label, confidence=confidence)
        session.add(detection)
        session.commit()
        detection_id = detection.id

        # Final name with leading zeros: 003.jpg, 010.jpg, ...
        final_name = f"{detection_id:03d}.jpg"
        image_save_path = IMAGES_DIR / final_name

        # Save the image with the final name
        with image_save_path.open("wb") as f:
            f.write(contents)

        # Update filename in the DB
        detection.filename = final_name
        session.commit()
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
):
    """Save a captured image when Apple Vision found text but YOLO found no object."""
    recognized_text = recognized_text.strip()
    _validate_recognized_text(recognized_text, confidence)
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
        )
        session.add(detection)
        session.commit()

        final_name = f"{detection.id:03d}.jpg"
        with (IMAGES_DIR / final_name).open("wb") as image_file:
            image_file.write(contents)
        detection.filename = final_name
        session.commit()

        return {
            "id": detection.id,
            "recognized_text": detection.recognized_text,
            "text_confidence": detection.text_confidence,
        }
    finally:
        session.close()


# GET /detections

@app.get("/detections")
def list_detections():
    """Return saved scans newest-first for the iOS scanned-objects screen."""
    session = SessionLocal()
    try:
        detections = (
            session.query(Detection)
            .order_by(Detection.scanned_at.desc(), Detection.id.desc())
            .all()
        )
        corrected_labels = {}
        for correction in session.query(UserLabel).order_by(UserLabel.id.asc()).all():
            corrected_labels[correction.detection_id] = correction.label

        response = []
        for detection in detections:
            corrected_label = corrected_labels.get(detection.id)
            scanned_at = detection.scanned_at or datetime.now(timezone.utc)
            if scanned_at.tzinfo is None:
                scanned_at = scanned_at.replace(tzinfo=timezone.utc)

            image_path = _image_path_for(detection)
            if image_path is None:
                continue
            response.append(
                {
                    "id": detection.id,
                    "label": corrected_label or detection.label,
                    "original_label": detection.label,
                    "corrected_label": corrected_label,
                    "confidence": detection.confidence,
                    "scanned_at": scanned_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "image_url": f"/detections/{detection.id}/image",
                    "details": detection.recognized_text,
                    "recognized_text": detection.recognized_text,
                    "text_confidence": detection.text_confidence,
                }
            )
        return response
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


@app.patch("/detections/{detection_id}/text")
def update_detection_text(detection_id: int, update: DetectionTextUpdate):
    """Store Apple Vision OCR output alongside a captured detection."""
    recognized_text = update.recognized_text.strip()
    _validate_recognized_text(recognized_text, update.confidence)

    session = SessionLocal()
    try:
        detection = (
            session.query(Detection).filter(Detection.id == detection_id).first()
        )
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        detection.recognized_text = recognized_text or None
        detection.text_confidence = update.confidence if recognized_text else None
        session.commit()
        return {
            "status": "updated",
            "id": detection_id,
            "recognized_text": detection.recognized_text,
            "text_confidence": detection.text_confidence,
        }
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
