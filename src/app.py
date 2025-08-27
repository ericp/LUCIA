# LUCIA src.app:app --reload
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import os
from datetime import datetime
import shutil
import subprocess

# Import detection logic, text-to-speech, and database models
from src.detect import detect_objects_in_frame
from src.tts import speak
from src.database import SessionLocal, Detection, UserLabel

app = FastAPI()

# --- Servir frontend estático en /web (NO en "/") ---
if os.path.isdir("frontend"):
    app.mount("/web", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/")
def root():
    return RedirectResponse(url="/web/")


# -----------------------
# CORS (para permitir llamadas desde el iPhone/otro host)
# -----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # si quieres restringir, pon la IP del iPhone o un dominio concreto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------
# Paths
# -----------------------
IMAGES_DIR = "data/images"
CORRECTED_IMAGES_DIR = "data/user_labels"
STATUS_FILE = "training_status.txt"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(CORRECTED_IMAGES_DIR, exist_ok=True)


# -----------------------
# Helpers
# -----------------------
def set_status(status: str):
    """Guarda el estado del entrenamiento en un archivo de texto."""
    with open(STATUS_FILE, "w") as f:
        f.write(status)


# -----------------------
# POST /detect
# -----------------------
@app.post("/detect")
async def detect_object(file: UploadFile = File(...)):
    """Recibe imagen, detecta objeto, guarda en BD y responde al frontend con hints de guía."""
    contents = await file.read()

    # Guardar imagen original
    image_save_path = os.path.join(IMAGES_DIR, file.filename)
    with open(image_save_path, "wb") as f:
        f.write(contents)

    # Procesar con OpenCV
    npimg = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # NUEVO: detect devuelve (label, confidence, hints)
    label, confidence, hints = detect_objects_in_frame(frame)

    if label:
        # Guardar en BD
        session = SessionLocal()
        detection = Detection(filename=file.filename, label=label, confidence=confidence)
        session.add(detection)
        session.commit()
        detection_id = detection.id
        session.close()

        # TTS local en Mac (opcional)
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


# -----------------------
# POST /guide
# -----------------------
@app.post("/guide")
async def guide_object(file: UploadFile = File(...)):
    """
    Recibe un frame (foto ligera) y devuelve solo hints para guiar al usuario
    antes de tomar la foto buena. No guarda en BD ni hace TTS.
    """
    contents = await file.read()
    npimg = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    label, confidence, hints = detect_objects_in_frame(frame)

    # Señal de “listo para capturar” cuando todo está OK
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


# -----------------------
# POST /correct
# -----------------------
@app.post("/correct")
async def correct_label(id: int = Form(...), new_label: str = Form(...)):
    """Recibe corrección de etiqueta, guarda en BD y (opcional) lanza reentrenamiento en segundo plano."""
    session = SessionLocal()
    detection = session.query(Detection).filter(Detection.id == id).first()

    if detection:
        # Guardar etiqueta corregida
        user_label = UserLabel(detection_id=id, label=new_label)
        session.add(user_label)
        session.commit()

        # Guardar imagen en carpeta de user_labels
        original_path = os.path.join(IMAGES_DIR, detection.filename)
        if os.path.exists(original_path):
            corrected_filename = f"{new_label}_{detection.filename}"
            corrected_path = os.path.join(CORRECTED_IMAGES_DIR, corrected_filename)
            shutil.copy(original_path, corrected_path)

        session.close()

        # (Opcional) Si no vas a entrenar ahora, comenta estas 4 líneas:
        set_status("training_started")
        try:
            subprocess.Popen(
                ["python", "scripts/update_model.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[ERROR] No se pudo lanzar update_model.py: {e}")

        return {"status": "updated", "id": id, "new_label": new_label}

    session.close()
    return {"status": "not found", "id": id}


# -----------------------
# GET /training-status
# -----------------------
@app.get("/training-status")
async def get_training_status():
    """Devuelve el estado actual del entrenamiento."""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            status = f.read().strip()
        return {"status": status}
    return {"status": "unknown"}


@app.get("/yolo-selftest")
def yolo_selftest():
    try:
        from ultralytics.utils import ASSETS
        test_img = os.path.join(ASSETS, 'bus.jpg')
        from src.detect import model
        r = model.predict(test_img, imgsz=640, conf=0.01, iou=0.3, device='cpu', verbose=False)
        n = 0 if r[0].boxes is None else len(r[0].boxes)
        return {"ok": True, "boxes_on_bus_jpg": int(n)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

