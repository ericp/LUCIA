"""
from src.detect import detect_first_object
from src.tts import speak

if __name__ == "__main__":
    label = detect_first_object()
    if label:
        speak(f"Object detected: {label}")
    else:
        print("No Object detected")
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
