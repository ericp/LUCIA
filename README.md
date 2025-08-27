#EN
# L.U.C.I.A. — Learning and Understanding Camera-based Intelligent Assistant

**LUCIA** is a lightweight assistant for blind/low-vision users that:
- Detects everyday objects with YOLOv8
- Guides the user **before** taking a photo with live **voice hints** (“get closer”, “center”, “need more light”, “take the picture now”)
- Speaks the **final detection result** (“bottle detected”)
- Lets users **correct labels** and stores them for future improvement
- Generates a **PDF validation report** (metrics + charts) from an Excel log

> Tech: FastAPI, Ultralytics/YOLOv8, OpenCV, WebSpeech (browser TTS), SQLite, ReportLab.

---

## Demo (Quick Start)

```bash
# 1) Create venv and install deps
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2) Run backend (serves the frontend at /web)
python main.py
# -> Uvicorn running at http://0.0.0.0:8000


## 3)Demo in API for iPhone on the same Wi-Fi:
#    Open http://<your-mac-ip>:8000/web
#    Tap "Start guidance" (or "Enable audio (test)" once to unlock TTS)

# Install ngrok (macOS)
brew install ngrok/ngrok/ngrok

# Add your token
ngrok config add-authtoken <YOUR_TOKEN>

# Expose backend
ngrok http 8000

------------------------------------------------------------------------------------

#ES
# L.U.C.I.A. — Asistente Inteligente de Aprendizaje y Comprensión Basado en Cámara

**LUCIA** es un asistente ligero para usuarios ciegos o con baja visión que:
- Detecta objetos cotidianos con YOLOv8
- Guía al usuario **antes** de tomar una foto con **instrucciones de voz en directo** (“acércate”, “centra”, “falta luz”, “haz la foto ahora”)
- Dice en voz alta el **resultado final de la detección** (“botella detectada”)
- Permite a los usuarios **corregir etiquetas** y las almacena para futuras mejoras
- Genera un **informe PDF de validación** (métricas + gráficos) a partir de un registro en Excel

> Tecnologías: FastAPI, Ultralytics/YOLOv8, OpenCV, WebSpeech (TTS en navegador), SQLite, ReportLab.

---

## Demo (Inicio Rápido)

```bash
# 1) Crear entorno virtual e instalar dependencias
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2) Ejecutar backend (sirve el frontend en /web)
python main.py
# -> Uvicorn ejecutándose en http://0.0.0.0:8000

## 3) Demo en la API para iPhone en la misma Wi-Fi:
#    Abrir http://<ip-de-tu-mac>:8000/web
#    Pulsa "Start guidance" (o "Enable audio (test)" una vez para desbloquear TTS)

# Instalar ngrok (macOS)
brew install ngrok/ngrok/ngrok

# Añadir tu token
ngrok config add-authtoken <TU_TOKEN>

# Exponer backend
ngrok http 8000

