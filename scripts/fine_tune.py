from ultralytics import YOLO
import os

# Ruta al dataset preparado por prepare_dataset.py
DATASET_PATH = "data/dataset_yolo/dataset.yaml"

# Verificar que existe
if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(f"No se encontró {DATASET_PATH}. Ejecuta primero prepare_dataset.py")

# Cargar modelo base YOLOv8 (puedes cambiar 'yolov8n.pt' por 'yolov8m.pt' si quieres más precisión)
model = YOLO("yolov8n.pt")

# Fine-tuning
model.train(
    data=DATASET_PATH,  # dataset.yaml
    epochs=5,           # entrenar pocas épocas para ajuste rápido
    imgsz=640,          # tamaño de imagen
    batch=8,            # puedes ajustar según tu RAM/GPU
    workers=0           # 0 en Mac para evitar problemas de multiproceso
)

# Guardar modelo ajustado
os.makedirs("models", exist_ok=True)
model.save("models/yolov8n_finetuned.pt")

print("[OK] Fine-tuning completado. Modelo guardado en models/yolov8n_finetuned.pt")
