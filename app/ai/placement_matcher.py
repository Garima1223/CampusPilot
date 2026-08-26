def calculate_match(student_skills: str, student_cgpa: float,
                     required_skills: str, minimum_cgpa: float):
    student_skill_set = set(s.strip().lower() for s in student_skills.split(",") if s.strip())
    required_skill_set = set(s.strip().lower() for s in required_skills.split(",") if s.strip())

    matched_skills = student_skill_set & required_skill_set
    missing_skills = required_skill_set - student_skill_set

    skill_score = (len(matched_skills) / len(required_skill_set) * 100) if required_skill_set else 100
    cgpa_eligible = student_cgpa >= minimum_cgpa

    final_score = skill_score * 0.7 + (100 if cgpa_eligible else 0) * 0.3

    return {
        "match_score": round(final_score, 1),
        "eligible": cgpa_eligible and skill_score >= 50,
        "matched_skills": list(matched_skills),
        "missing_skills": list(missing_skills),
        "cgpa_eligible": cgpa_eligible
    }