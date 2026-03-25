# LUCIA src.app:app --reload
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import os
import shutil

# Import detection logic, text-to-speech, and database models
from src.detect import detect_objects_in_frame
from src.tts import speak
from src.database import SessionLocal, Detection, UserLabel

app = FastAPI()

#  Serve static frontend at /web (NOT at "/") 
if os.path.isdir("frontend"):
    app.mount("/web", StaticFiles(directory="frontend", html=True), name="frontend")

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

IMAGES_DIR = "data/images"
CORRECTED_IMAGES_DIR = "data/user_labels"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(CORRECTED_IMAGES_DIR, exist_ok=True)


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
        image_save_path = os.path.join(IMAGES_DIR, final_name)

        # Save the image with the final name
        with open(image_save_path, "wb") as f:
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
        original_path = os.path.join(IMAGES_DIR, detection.filename) 
        if os.path.exists(original_path):
            corrected_filename = f"{new_label}_{detection.filename}"
            corrected_path = os.path.join(CORRECTED_IMAGES_DIR, corrected_filename)
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
