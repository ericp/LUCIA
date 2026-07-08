#EN
# L.U.C.I.A. — Learning and Understanding Camera-based Intelligent Assistant

**LUCIA** is a lightweight assistant for blind and low-vision users that:
- Detects everyday objects with YOLOv8
- Guides the user **before** taking a photo with live **voice hints** (“get closer”, “center”, “need more light”, “take the picture now”)
- Speaks the **final detection result** (“bottle detected”)
- Lets users **correct labels** and stores them for future improvement
- Generates a **PDF validation report** (metrics + charts) from an Excel log

> Tech: FastAPI, Ultralytics/YOLOv8, OpenCV, WebSpeech (browser TTS), SQLite, ReportLab.

---

## Demo (Quick Start)

```bash
# 1) Create a virtual environment and install dependencies
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2) Run the backend (serves the frontend at /web)
python main.py
# -> Uvicorn running at http://0.0.0.0:8000


## 3) Demo in the API for iPhone on the same Wi-Fi:
#    Open http://<your-mac-ip>:8000/web
#    Tap "Start guidance" (or "Enable audio (test)" once to unlock TTS)

# Install ngrok (macOS)
brew install ngrok/ngrok/ngrok

# Add your token
ngrok config add-authtoken <YOUR_TOKEN>

# Expose the backend
ngrok http 8000
```

------------------------------------------------------------------------------------

#EN
# L.U.C.I.A. — Learning and Understanding Camera-Based Intelligent Assistant

**LUCIA** is a lightweight assistant for blind and low-vision users that:
- Detects everyday objects with YOLOv8
- Guides the user **before** taking a photo with live **voice instructions** (“get closer”, “center”, “need more light”, “take the picture now”)
- Speaks the **final detection result** aloud (“bottle detected”)
- Lets users **correct labels** and stores them for future improvements
- Generates a **PDF validation report** (metrics + charts) from an Excel log

> Technologies: FastAPI, Ultralytics/YOLOv8, OpenCV, WebSpeech (browser TTS), SQLite, ReportLab.

---

## Demo (Quick Start)

```bash
# 1) Create a virtual environment and install dependencies
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2) Run the backend (serves the frontend at /web)
python main.py
# -> Uvicorn running at http://0.0.0.0:8000

## 3) Demo in the API for iPhone on the same Wi-Fi:
#    Open http://<your-mac-ip>:8000/web
#    Tap "Start guidance" (or "Enable audio (test)" once to unlock TTS)

# Install ngrok (macOS)
brew install ngrok/ngrok/ngrok

# Add your token
ngrok config add-authtoken <YOUR_TOKEN>

# Expose the backend
ngrok http 8000
```
