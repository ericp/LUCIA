import os
import urllib.request
import zipfile
import tarfile

# Database base directory
RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

def download_file(url: str, target_path: str):
    """Downloads a file from a URL if it doesn't exist yet."""
    if os.path.exists(target_path):
        print(f"[SKIP] Already exists {target_path}")
        return
    print(f"[DOWN]  Downloading {url} → {target_path}")
    urllib.request.urlretrieve(url, target_path)
    print(f"[OK]    {target_path} downloaded")

def extract_zip(zip_path: str, extract_to: str):
    """Extracts a .zip in the specified folder."""
    if os.path.exists(extract_to) and os.listdir(extract_to):
        print(f"[SKIP] Content already extracted in {extract_to}")
        return
    print(f"[EXTR] Extracting {zip_path} → {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)
    print(f"[OK]    Extracted in {extract_to}")

def extract_tar(tar_path: str, extract_to: str):
    """Extracts a .tar.gz or .tar in the specified folder."""
    if os.path.exists(extract_to) and os.listdir(extract_to):
        print(f"[SKIP] Content already extracted in {extract_to}")
        return
    print(f"[EXTR] Extracting {tar_path} → {extract_to}")
    with tarfile.open(tar_path, 'r:*') as tf:
        tf.extractall(extract_to)
    print(f"[OK]    Extracted in {extract_to}")

def download_coco():
    # COCO 2017 Images
    url_imgs = "http://images.cocodataset.org/zips/train2017.zip"
    zip_imgs = os.path.join(RAW_DIR, "coco_train2017.zip")
    out_imgs = os.path.join(RAW_DIR, "COCO", "train2017")
    download_file(url_imgs, zip_imgs)
    extract_zip(zip_imgs, out_imgs)

    # COCO 2017 Annotations
    url_ann = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
    zip_ann = os.path.join(RAW_DIR, "coco_annotations2017.zip")
    out_ann = os.path.join(RAW_DIR, "COCO", "annotations")
    download_file(url_ann, zip_ann)
    extract_zip(zip_ann, out_ann)

def download_openimages_subset():
    # Example of first file from Open Images v6
    url = "https://storage.googleapis.com/openimages/v6/zip/train_0.zip"
    zip_path = os.path.join(RAW_DIR, "openimages_train_0.zip")
    out_dir = os.path.join(RAW_DIR, "OpenImages", "train_0")
    download_file(url, zip_path)
    extract_zip(zip_path, out_dir)

def download_food101():
    url = "https://data.vision.ee.ethz.ch/cvl/food-101.tar.gz"
    tar_path = os.path.join(RAW_DIR, "food101.tar.gz")
    out_dir = os.path.join(RAW_DIR, "Food101")
    download_file(url, tar_path)
    extract_tar(tar_path, out_dir)

if __name__ == "__main__":
    download_coco()
    download_openimages_subset()
    download_food101()
