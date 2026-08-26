import os
import cv2
import pytesseract

# Was hardcoded to a Windows-only path (C:\Program Files\Tesseract-OCR\...),
# which meant this silently threw on any non-Windows host (Linux/macOS
# servers, containers, etc.) — pytesseract already finds a `tesseract` on
# PATH by default, so only override it if TESSERACT_CMD is explicitly set.
_tesseract_cmd = os.environ.get("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd

def preprocess_image(image_path: str):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return thresh

def extract_text(image_path: str):
    processed = preprocess_image(image_path)
    data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
    extracted_lines = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = data['conf'][i]
        if text and conf != '-1':
            extracted_lines.append({"text": text, "confidence": float(conf) / 100})
    return extracted_lines
import re

def parse_attendance(ocr_results):
    """
    Takes raw OCR results and tries to extract (roll_number, status) pairs.
    Assumes a pattern where a roll number is followed shortly by a status mark.
    """
    parsed = []
    pending_roll = None

    for item in ocr_results:
        text = item["text"].strip()
        confidence = item["confidence"]

        # Looks like a roll number: 1-4 digit number
        if re.fullmatch(r"\d{1,4}", text):
            pending_roll = {"roll_number": text, "confidence": confidence}
            continue

        # Looks like a status mark: P, A, Pp, p, etc.
        normalized = text.upper().replace("PP", "P")
        if normalized in ("P", "A") and pending_roll:
            status = "PRESENT" if normalized == "P" else "ABSENT"
            avg_conf = (pending_roll["confidence"] + confidence) / 2
            parsed.append({
                "roll_number": pending_roll["roll_number"],
                "status": status,
                "confidence": round(avg_conf, 2)
            })
            pending_roll = None

    return parsed