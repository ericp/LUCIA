from ultralytics import YOLO
import os
import cv2
import numpy as np

# -----------------------
# Configuración
# -----------------------
OBJECTS_OF_INTEREST = [
    "bottle", "cup", "fork", "spoon", "knife",
    "book", "laptop", "cell phone", "remote", "plant"
]

# Umbral por clase (puedes ajustar con tus datos)
CLASS_THRESH = {
    "fork": 0.55, "spoon": 0.55, "knife": 0.55,
    "cup": 0.55, "bottle": 0.55,
    "book": 0.50, "laptop": 0.50, "cell phone": 0.50, "remote": 0.50, "plant": 0.50
}

# Tamaño mínimo de caja para evitar falsos positivos diminutos
MIN_BOX_AREA = 28 * 28

# Parámetros de inferencia (puedes rebajar imgsz si tu Mac va justo)
INFER_IMGSZ = 768
INFER_CONF = 0.45
INFER_IOU = 0.50

# -----------------------
# Cargar modelo (ajustado si existe)
# -----------------------
MODEL_PATH = "models/yolov8n_finetuned.pt" if os.path.exists("models/yolov8n_finetuned.pt") else "yolov8n.pt"
model = YOLO(MODEL_PATH)


def _compute_hints(img, best_box, img_w, img_h):
    """
    Devuelve hints (distance, center, light) + valores numéricos de apoyo.
    best_box: (x1, y1, x2, y2) o None si no hay detecciones válidas.
    """
    # Luz promedio (0-255 aprox)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())

    # Por defecto si no hay caja válida
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

    # Heurística de distancia por tamaño relativo
    if area_ratio < 0.03:
        dist_hint = "too_far"
    elif area_ratio > 0.45:
        dist_hint = "too_close"
    else:
        dist_hint = "ok"

    # Desviación de centro (0 perfecto, 1 en el borde)
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


def detect_objects_in_frame(frame):
    """
    Entrada: frame (BGR, np.ndarray)
    Salida:
      - label (str | None)
      - confidence (float | None)
      - hints (dict)  -> distance, center, light, etc.
    """
    if frame is None or not isinstance(frame, np.ndarray):
        return None, None, {"distance": "unknown", "center": "unknown", "light": "check"}

    img_h, img_w = frame.shape[:2]

    # Inferencia
    results = model.predict(
        frame, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU, verbose=False
    )
    names = model.names
    boxes = results[0].boxes

    best = None  # (label, conf, box_xyxy)
    best_box_for_hints = None

    if boxes is not None and len(boxes) > 0:
        for b in boxes:
            cls_id = int(b.cls[0])
            label = names[cls_id]
            conf = float(b.conf[0])
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
            area = max(0.0, (x2 - x1)) * max(0.0, (y2 - y1))

            if label not in OBJECTS_OF_INTEREST:
                continue

            thr = CLASS_THRESH.get(label, 0.55)
            if conf < thr or area < MIN_BOX_AREA:
                continue

            if (best is None) or (conf > best[1]):
                best = (label, conf, (x1, y1, x2, y2))

        if best is not None:
            best_box_for_hints = best[2]

    # Construir hints siempre (aunque no haya label)
    hints = _compute_hints(frame, best_box_for_hints, img_w, img_h)

    if best is not None:
        label, confidence, _ = best
        print(f"[detect] Detected: {label} ({confidence:.2f}) | hints={hints}")
        return label, confidence, hints

    print(f"[detect] No relevant object | hints={hints}")
    return None, None, hints
