import os
import random
import shutil
from sklearn.model_selection import train_test_split

# CONFIGURATION
USER_LABELS_DIR = "data/user_labels"
OUTPUT_DIR = "data/dataset_yolo"
TRAIN_SPLIT = 0.8  # 80% train, 20% val

# List of classes I'm going to use (must match the YOLO model)
CLASSES = ["bottle", "cup", "fork", "spoon", "knife", "book", "laptop", "cell phone", "remote", "plant"]

#  FUNCTIONS
def prepare_yolo_dataset():
    # Paths of corrected images
    all_images = [f for f in os.listdir(USER_LABELS_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    
    if not all_images:
        print("[ERROR] No images found in data/user_labels/")
        return

    # Create destination folders
    for subdir in ["images/train", "images/val", "labels/train", "labels/val"]:
        os.makedirs(os.path.join(OUTPUT_DIR, subdir), exist_ok=True)

    # Split train/val
    train_imgs, val_imgs = train_test_split(all_images, train_size=TRAIN_SPLIT, random_state=42)

    # Auxiliary function to copy images and generate empty YOLO labels (placeholder)
    def copy_and_label(image_list, subset):
        for img in image_list:
            src_path = os.path.join(USER_LABELS_DIR, img)
            dst_img_path = os.path.join(OUTPUT_DIR, f"images/{subset}", img)
            shutil.copy(src_path, dst_img_path)

            # YOLO label → filename.txt
            label_txt = os.path.splitext(img)[0] + ".txt"
            dst_label_path = os.path.join(OUTPUT_DIR, f"labels/{subset}", label_txt)

            # Extract class from the corrected filename
            label_name = img.split("_")[0]
            if label_name in CLASSES:
                class_id = CLASSES.index(label_name)
                # Without bounding boxes, YOLO needs empty or approximate marker
                with open(dst_label_path, "w") as f:
                    f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")  # box that covers the entire image
            else:
                print(f"[WARN] Class {label_name} is not in CLASSES. Skipping...")

    # Copy train and val
    copy_and_label(train_imgs, "train")
    copy_and_label(val_imgs, "val")

    # Create dataset.yaml
    yaml_path = os.path.join(OUTPUT_DIR, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {os.path.abspath(OUTPUT_DIR)}\n")
        f.write(f"train: images/train\n")
        f.write(f"val: images/val\n")
        f.write(f"names: {CLASSES}\n")

    print(f"[OK] Dataset prepared in {OUTPUT_DIR}")

if __name__ == "__main__":
    prepare_yolo_dataset()
