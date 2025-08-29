from ultralytics import YOLO
import os
import cv2
import numpy as np


# Configuración

# Lista de objetos relevantes (COCO names estándar del yolov8n.pt)
OBJECTS_OF_INTEREST = [
    "bottle", "cup", "fork", "spoon", "knife",
    "book", "laptop", "cell phone", "remote", "plant"
]

# Umbral por clase (afinable)
CLASS_THRESH = {
    "fork": 0.40, "spoon": 0.40, "knife": 0.40,
    "cup": 0.40, "bottle": 0.40,
    "book": 0.35, "laptop": 0.35, "cell phone": 0.35, "remote": 0.35, "plant": 0.35
}

# Evitar cajas diminutas
MIN_BOX_AREA = 24 * 24

# Parámetros por defecto de inferencia
INFER_IMGSZ = 640
INFER_CONF = 0.25
INFER_IOU = 0.50


# Cargar SIEMPRE pesos base (para descartar pesos corruptos)

MODEL_PATH = "yolov8n.pt"   # <- forzado a base
print(f"[boot] Loading YOLO weights: {MODEL_PATH}")
model = YOLO(MODEL_PATH)
try:
    n_classes = len(model.names)
    print(f"[boot] Model loaded. classes={n_classes} | sample names={list(model.names.items())[:5]}")
except Exception as e:
    print(f"[boot] Could not read model.names: {e}")



# Utilidades

def _enhance_for_detection(img: np.ndarray) -> np.ndarray:
    """
    Mejora ligera de contraste para condiciones de poca luz.
    - escala a 640px máx lado
    - CLAHE en canal L del espacio LAB
    """
    if img is None or not isinstance(img, np.ndarray):
        return img

    h, w = img.shape[:2]
    max_side = max(h, w)
    if max_side > 800:
        scale = 800.0 / max_side
        img = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    L, A, B = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    L2 = clahe.apply(L)
    lab2 = cv2.merge([L2, A, B])
    out = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)
    return out


def _compute_hints(img, best_box, img_w, img_h):
    """ Devuelve hints (distance, center, light) + métricas de apoyo. """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())

    if best_box is None:
        light_hint = "too_dark" if brightness < 85 else "ok_light"
        return {
            "distance": "unknown",
            "center": "unknown",
            "light": light_hint,
            "area_ratio": None,
            "center_offset": None,
            "brightness": brightness
        }

    x1, y1, x2, y2 = best_box
    w = max(0.0, x2 - x1)
    h = max(0.0, y2 - y1)
    area = w * h
    img_area = float(img_w * img_h)
    area_ratio = area / img_area if img_area > 0 else 0.0

    # Distancia ~ tamaño relativo
    if area_ratio < 0.03:
        dist_hint = "too_far"
    elif area_ratio > 0.45:
        dist_hint = "too_close"
    else:
        dist_hint = "ok"

    # Centrado (0 perfecto, 1 borde)
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    center_offset = max(abs(cx - img_w/2) / (img_w/2), abs(cy - img_h/2) / (img_h/2))
    if center_offset < 0.20:
        center_hint = "centered"
    elif center_offset < 0.40:
        center_hint = "slightly_off"
    else:
        center_hint = "off_center"

    light_hint = "too_dark" if brightness < 85 else "ok_light"

    return {
        "distance": dist_hint,
        "center": center_hint,
        "light": light_hint,
        "area_ratio": float(area_ratio),
        "center_offset": float(center_offset),
        "brightness": float(brightness),
    }


def _predict_once(img_bgr: np.ndarray, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU):
    """ Una pasada de YOLO y devuelve (label, conf, box_xyxy) para el mejor candidato (whitelist). """
    res = model.predict(img_bgr, imgsz=imgsz, conf=conf, iou=iou, verbose=False, device='cpu')
    boxes = res[0].boxes
    names = model.names
    best = None

    if boxes is not None and len(boxes) > 0:
        for b in boxes:
            cls_id = int(b.cls[0])
            label = names[cls_id]
            confv = float(b.conf[0])
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
            area = max(0.0, (x2-x1)) * max(0.0, (y2-y1))

            if label not in OBJECTS_OF_INTEREST:
                continue

            thr = CLASS_THRESH.get(label, 0.40)
            if confv < thr or area < MIN_BOX_AREA:
                continue

            if (best is None) or (confv > best[1]):
                best = (label, confv, (x1, y1, x2, y2))
    return best



# API principal

def detect_objects_in_frame(frame: np.ndarray):
    """
    Entrada: frame (BGR, np.ndarray)
    Salida:
      - label (str | None)
      - confidence (float | None)
      - hints (dict): distance, center, light, etc.
    """
    if frame is None or not isinstance(frame, np.ndarray):
        return None, None, {"distance": "unknown", "center": "unknown", "light": "check"}

    img_h, img_w = frame.shape[:2]

    # 1) Mejora de imagen
    enhanced = _enhance_for_detection(frame)

    # 2) Pasada normal
    best = _predict_once(enhanced, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU)

    # 3) Si nada, intenta con conf más bajo (recuperación)
    if best is None:
        best = _predict_once(enhanced, imgsz=INFER_IMGSZ, conf=0.10, iou=0.50)

    # 4) Construir hints SIEMPRE, con la mejor caja si existe
    best_box_for_hints = None if best is None else best[2]
    hints = _compute_hints(enhanced, best_box_for_hints, enhanced.shape[1], enhanced.shape[0])

    if best is not None:
        label, confidence, _ = best
        print(f"[detect] {label=} {confidence:.2f} | hints={hints}")
        return label, confidence, hints

    print(f"[detect] no-object | hints={hints}")
    return None, None, hints



# Self-test (usado por /yolo-selftest)

def yolo_selftest():
    """
    Devuelve cuántas cajas detecta en la imagen demo 'bus.jpg' de Ultralytics.
    Si devuelve 0, la instalación/pesos estarian mal.
    """
    try:
        r = model.predict(source="https://ultralytics.com/images/bus.jpg",
                          imgsz=640, conf=0.01, iou=0.30, verbose=False, device='cpu')
        b = r[0].boxes
        n = 0 if b is None else len(b)
        return {"boxes_on_bus_jpg": int(n)}
    except Exception as e:
        return {"error": str(e)}
