from fastapi.testclient import TestClient
from src.app import app
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

client = TestClient(app)

def test_detect_endpoint_no_file():
    response = client.post("/detect")
    assert response.status_code == 422  
