CATEGORY_RULES = {
    "Infrastructure": {
        "keywords": ["fan", "light", "wifi", "internet", "chair", "desk", "classroom",
                     "washroom", "toilet", "water", "electricity", "projector", "ac", "building"],
        "department": "Maintenance",
        "priority": "MEDIUM"
    },
    "Academic": {
        "keywords": ["exam", "marks", "grade", "professor", "faculty", "syllabus",
                     "lecture", "assignment", "attendance", "result"],
        "department": "Academic Office",
        "priority": "MEDIUM"
    },
    "Harassment": {
        "keywords": ["harassment", "bully", "abuse", "threat", "discrimination", "unsafe"],
        "department": "Student Welfare",
        "priority": "HIGH"
    },
    "Hostel": {
        "keywords": ["hostel", "room", "mess", "food", "warden", "roommate"],
        "department": "Hostel Administration",
        "priority": "MEDIUM"
    },
    "Fees": {
        "keywords": ["fee", "payment", "refund", "scholarship", "invoice"],
        "department": "Accounts Office",
        "priority": "LOW"
    }
}

def classify_grievance(description: str):
    text = description.lower()
    scores = {}

    for category, rule in CATEGORY_RULES.items():
        match_count = sum(1 for kw in rule["keywords"] if kw in text)
        if match_count > 0:
            scores[category] = match_count

    if not scores:
        return {
            "category": "General",
            "department": "Admin Office",
            "priority": "LOW"
        }

    best_category = max(scores, key=scores.get)
    rule = CATEGORY_RULES[best_category]

    # Escalate priority if urgency words are present, regardless of category
    urgent_words = ["urgent", "immediately", "days", "not working", "since"]
    if any(word in text for word in urgent_words) and rule["priority"] != "HIGH":
        priority = "HIGH"
    else:
        priority = rule["priority"]

    return {
        "category": best_category,
        "department": rule["department"],
        "priority": priority
    }