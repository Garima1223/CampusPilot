from app.ai.attendance_ocr import extract_text

results = extract_text("test_attendance.jpg")

for r in results:
    print(f"Text: {r['text']}   Confidence: {r['confidence']:.2f}")