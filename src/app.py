# LUCIA src.app:app --reload
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
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
    """Recibe imagen, detecta objeto, guarda en BD y responde al frontend."""
    contents = await file.read()

    # Guardar imagen original
    image_save_path = os.path.join(IMAGES_DIR, file.filename)
    with open(image_save_path, "wb") as f:
        f.write(contents)

    # Procesar con OpenCV
    npimg = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    label, confidence = detect_objects_in_frame(frame)

    if label:
        # Guardar en BD
        session = SessionLocal()
        detection = Detection(filename=file.filename, label=label, confidence=confidence)
        session.add(detection)
        session.commit()
        detection_id = detection.id
        session.close()

        # TTS
        speak(f"{label} detected")

        return JSONResponse(content={
            "id": detection_id,
            "object_detected": label,
            "confidence": confidence,
            "message": f"Object detected: {label} ({confidence:.2f})"
        })
    else:
        speak("No relevant object detected")
        return JSONResponse(content={
            "id": None,
            "object_detected": None,
            "confidence": None,
            "message": "No relevant object detected."
        })

# -----------------------
# POST /correct
# -----------------------
@app.post("/correct")
async def correct_label(id: int = Form(...), new_label: str = Form(...)):
    """Recibe corrección de etiqueta, guarda en BD y lanza reentrenamiento en segundo plano."""
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

        # Estado: empezando entrenamiento
        set_status("training_started")

        # Ejecutar entrenamiento en segundo plano
        try:
            subprocess.Popen(
                ["python", "scripts/update_model.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"[ERROR] No se pudo lanzar update_model.py: {e}")

        return {"status": "updated_and_training_in_background", "id": id, "new_label": new_label}

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
