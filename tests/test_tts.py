from src.tts import speak
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_speak_runs_without_error():
    try:
        speak("Testing speech synthesis")
        success = True
    except Exception:
        success = False

    assert success
