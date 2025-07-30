#Here we will have functions that download and unzip the data authomatically

import os
import urllib.request
import zipfile
import tarfile

# Directorio base de datos
RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

def download_file(url: str, target_path: str):
    """Descarga un archivo desde una URL si no existe aún."""
    if os.path.exists(target_path):
        print(f"[SKIP] Ya existe {target_path}")
        return
    print(f"[DOWN]  Descargando {url} → {target_path}")
    urllib.request.urlretrieve(url, target_path)
    print(f"[OK]    {target_path} descargado")

def extract_zip(zip_path: str, extract_to: str):
    """Descomprime un .zip en la carpeta indicada."""
    if os.path.exists(extract_to) and os.listdir(extract_to):
        print(f"[SKIP] Contenido ya extraído en {extract_to}")
        return
    print(f"[EXTR] Descomprimiendo {zip_path} → {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)
    print(f"[OK]    Descomprimido en {extract_to}")

def extract_tar(tar_path: str, extract_to: str):
    """Descomprime un .tar.gz o .tar en la carpeta indicada."""
    if os.path.exists(extract_to) and os.listdir(extract_to):
        print(f"[SKIP] Contenido ya extraído en {extract_to}")
        return
    print(f"[EXTR] Descomprimiendo {tar_path} → {extract_to}")
    with tarfile.open(tar_path, 'r:*') as tf:
        tf.extractall(extract_to)
    print(f"[OK]    Descomprimido en {extract_to}")

def download_coco():
    # Imágenes COCO 2017
    url_imgs = "http://images.cocodataset.org/zips/train2017.zip"
    zip_imgs = os.path.join(RAW_DIR, "coco_train2017.zip")
    out_imgs = os.path.join(RAW_DIR, "COCO", "train2017")
    download_file(url_imgs, zip_imgs)
    extract_zip(zip_imgs, out_imgs)

    # Anotaciones COCO 2017
    url_ann = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
    zip_ann = os.path.join(RAW_DIR, "coco_annotations2017.zip")
    out_ann = os.path.join(RAW_DIR, "COCO", "annotations")
    download_file(url_ann, zip_ann)
    extract_zip(zip_ann, out_ann)

def download_openimages_subset():
    # Ejemplo de primer archivo de Open Images v6 (puedes repetir para más partes)
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

def download_roboflow_dataset(api_key: str, workspace: str, project: str, version: str):
    """
    Si luego decides usar Roboflow, aquí podrías invocar su API:
    pip install roboflow
    """
    from roboflow import Roboflow
    rf = Roboflow(api_key=api_key)
    ds = rf.workspace(workspace).project(project).version(version).download("coco")
    print(f"[OK]    Roboflow {project} v{version} descargado en {ds.location}")

if __name__ == "__main__":
    download_coco()
    download_openimages_subset()
    download_food101()
    # download_roboflow_dataset(api_key="TU_APIKEY", workspace="mi_workspace", project="objetos-peligrosos", version="1")

