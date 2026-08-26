import re

def detect_intent(question: str):
    q = question.lower()
    if any(w in q for w in ["attendance", "present", "absent"]):
        return "attendance"
    if any(w in q for w in ["risk", "at risk", "performance"]):
        return "risk"
    if any(w in q for w in ["job", "eligible", "placement", "company", "hire"]):
        return "placement"
    if any(w in q for w in ["grievance", "complaint"]):
        return "grievance"
    return "unknown"

def extract_subject(question: str):
    match = re.search(r"in ([A-Za-z]+)", question)
    return match.group(1).upper() if match else None