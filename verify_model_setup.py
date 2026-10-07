"""Non-secret readiness check and Windows OCR smoke test; no paid LLM calls."""
import json
import os
from pathlib import Path
import urllib.request
import cv2
import numpy as np
from model_profiles import Profiles
from scoreboard_reader import ocr_image

registry = Profiles()
for name in registry.data["profiles"]:
    print(f"{name}: {registry.readiness(name)}")
try:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
        print("Local models:", [model["name"] for model in json.load(response).get("models", [])])
except OSError:
    print("No local Ollama server responding.")
root = Path(__file__).parent / "artifacts/scoreboard-verification"
root.mkdir(parents=True, exist_ok=True)
image = np.full((300, 1200, 3), 255, dtype=np.uint8)
cv2.putText(image, "Ashe 7 / 2 / 4  123 CS", (40, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
path = root / "ocr-fixture.png"
cv2.imwrite(str(path), image)
result = ocr_image(path)
if "Ashe" not in result["text"] or "123" not in result["text"]:
    raise SystemExit("Windows OCR smoke test did not recognize the known text")
print("Windows OCR smoke test passed; language:", result.get("language"))
