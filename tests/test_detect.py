from src.detect import detect_objects_in_frame
import numpy as np
import cv2
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_detect_returns_tuple():
    # Create a black image (no objects)
    frame = np.zeros((640, 480, 3), dtype=np.uint8)
    result = detect_objects_in_frame(frame)

    # Detection returns the label, confidence, and live-guidance hints.
    assert isinstance(result, tuple)
    assert len(result) == 3
    label, confidence, hints = result
    assert isinstance(label, (str, type(None)))
    assert isinstance(confidence, (float, type(None)))
    assert isinstance(hints, dict)
