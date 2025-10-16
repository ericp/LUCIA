# LUCIA src.app:app --reload
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import os
import shutil

# Importar detection logic, text-to-speech, y database models
from src.detect import detect_objects_in_frame
from src.tts import speak
from src.database import SessionLocal, Detection, UserLabel

app = FastAPI()

#  Servir frontend estático en /web (NO en "/") 
if os.path.isdir("frontend"):
    app.mount("/web", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/")
def root():
    return RedirectResponse(url="/web/")


# CORS (para permitir llamadas desde el iPhone/otro host)

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
    Recibe imagen, detecta objeto, guarda en BD (si hay detección) y responde al frontend con hints de guía.
    La imagen se nombra siempre como <id_padded>.jpg (ejemplo: 003.jpg)
    """
    contents = await file.read()

    # Procesar con OpenCV (todavía no guardamos a disco hasta tener el id)
    npimg = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # Detección -> (label, confidence, hints)
    label, confidence, hints = detect_objects_in_frame(frame)

    if label:
        # Crear fila en BD para obtener el id
        session = SessionLocal()
        detection = Detection(filename="", label=label, confidence=confidence)
        session.add(detection)
        session.commit()
        detection_id = detection.id

        # Nombre final con ceros a la izquierda: 003.jpg, 010.jpg, ...
        final_name = f"{detection_id:03d}.jpg"
        image_save_path = os.path.join(IMAGES_DIR, final_name)

        # Guardar la imagen con el nombre final
        with open(image_save_path, "wb") as f:
            f.write(contents)

        # Actualizar filename en la BD
        detection.filename = final_name
        session.commit()
        session.close()

        # TTS local en Mac
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
        # Sin detección: no se guarda imagen ni fila en BD
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
    Recibe un frame (foto ligera) y devuelve hints para guiar al usuario en directo.
    No guarda en BD ni hace TTS en el servidor.
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
    Recibe corrección de etiqueta y la guarda en BD (tabla user_labels).
    Mantiene el esquema original: copia la imagen como <new_label>_<filename> en data/user_labels/.
    """
    session = SessionLocal()
    detection = session.query(Detection).filter(Detection.id == id).first()

    if detection:
        # Guardar etiqueta corregida en tabla user_labels 
        user_label = UserLabel(detection_id=id, label=new_label)
        session.add(user_label)
        session.commit()

        # Copiar imagen original a carpeta de correcciones con prefijo de etiqueta
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
    Autocomprobación de la instalación de YOLOv8 usando la imagen de ejemplo bus.jpg incluida en Ultralytics.
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
