import os
import random
import shutil
from sklearn.model_selection import train_test_split

# CONFIGURACIÓN
USER_LABELS_DIR = "data/user_labels"
OUTPUT_DIR = "data/dataset_yolo"
TRAIN_SPLIT = 0.8  # 80% train, 20% val

# Lista de clases que voy a usar (deben coincidir con el modelo YOLO)
CLASSES = ["bottle", "cup", "fork", "spoon", "knife", "book", "laptop", "cell phone", "remote", "plant"]

#  FUNCIONES
def prepare_yolo_dataset():
    # Rutas de imágenes corregidas
    all_images = [f for f in os.listdir(USER_LABELS_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    
    if not all_images:
        print("[ERROR] No se encontraron imágenes en data/user_labels/")
        return

    # Crear carpetas destino
    for subdir in ["images/train", "images/val", "labels/train", "labels/val"]:
        os.makedirs(os.path.join(OUTPUT_DIR, subdir), exist_ok=True)

    # Dividir train/val
    train_imgs, val_imgs = train_test_split(all_images, train_size=TRAIN_SPLIT, random_state=42)

    # Función auxiliar para copiar imágenes y generar etiquetas YOLO vacías (placeholder)
    def copy_and_label(image_list, subset):
        for img in image_list:
            src_path = os.path.join(USER_LABELS_DIR, img)
            dst_img_path = os.path.join(OUTPUT_DIR, f"images/{subset}", img)
            shutil.copy(src_path, dst_img_path)

            # Etiqueta YOLO → filename.txt
            label_txt = os.path.splitext(img)[0] + ".txt"
            dst_label_path = os.path.join(OUTPUT_DIR, f"labels/{subset}", label_txt)

            # Extraer clase desde el nombre del archivo corregido
            label_name = img.split("_")[0]
            if label_name in CLASSES:
                class_id = CLASSES.index(label_name)
                # Al no tener bounding boxes, YOLO necesita marcador vacío o aproximado
                with open(dst_label_path, "w") as f:
                    f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")  # caja que cubre toda la imagen
            else:
                print(f"[WARN] Clase {label_name} no está en CLASSES. Saltando...")

    # Copiar train y val
    copy_and_label(train_imgs, "train")
    copy_and_label(val_imgs, "val")

    # Crear dataset.yaml
    yaml_path = os.path.join(OUTPUT_DIR, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {os.path.abspath(OUTPUT_DIR)}\n")
        f.write(f"train: images/train\n")
        f.write(f"val: images/val\n")
        f.write(f"names: {CLASSES}\n")

    print(f"[OK] Dataset preparado en {OUTPUT_DIR}")

if __name__ == "__main__":
    prepare_yolo_dataset()
