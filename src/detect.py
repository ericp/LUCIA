from ultralytics import YOLO
import os

# Lista de objetos relevantes (Whitelist)
OBJECTS_OF_INTEREST = ["bottle", "cup", "fork", "spoon", "knife", "book", "laptop", "cell phone", "remote", "plant"]

# Usar modelo ajustado si existe
MODEL_PATH = "models/yolov8n_finetuned.pt" if os.path.exists("models/yolov8n_finetuned.pt") else "yolov8n.pt"
model = YOLO(MODEL_PATH)

def detect_objects_in_frame(frame):
    results = model.predict(frame, verbose=False)
    boxes = results[0].boxes
    names = model.names

    if boxes is not None and len(boxes) > 0:
        for box in boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            label = names[cls_id]

            if confidence >= 0.6 and label in OBJECTS_OF_INTEREST:
                print(f"Detected: {label} ({confidence:.2f})")
                return label, confidence

    return None, None
