from flask import Flask, render_template, redirect, url_for, request, jsonify
import pandas as pd
import os
import json
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "virtual_mentor_secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "student_performance.csv")
CAREER_PATHS_PATH = os.path.join(BASE_DIR, "career_paths.json")

# Load career paths once
if os.path.exists(CAREER_PATHS_PATH):
    with open(CAREER_PATHS_PATH, "r") as f:
        CAREER_PATHS = json.load(f)
else:
    CAREER_PATHS = {}


# ======================================================
# 🔹 Utility Functions
# ======================================================

def calculate_attendance(student):
    total_classes = student.get("total_classes", 0)
    attended = student.get("classes_attended", 0)

    if total_classes > 0:
        return round((attended / total_classes) * 100, 2)
    return 0


def calculate_placement_score(student, attendance):
    """
    Balanced formula (keeps score ~ 0–100)
    """
    return round(
        (student.get("current_gpa", 0) * 8) +      # max 80
        (attendance * 0.2) -                      # max 20
        (student.get("backlogs_count", 0) * 5),
        2
    )


def calculate_risk(score):
    if score >= 75:
        return "Low"
    elif score >= 55:
        return "Medium"
    return "High"


def external_marks_needed(internal_score, grade_threshold):
    """
    Calculate required external marks for grade.
    Returns None if impossible.
    """
    needed = (2 * grade_threshold) - internal_score

    if needed < 0:
        return 0
    elif needed > 100:
        return None

    return round(needed, 2)


# ======================================================
# 🔹 Routes
# ======================================================

@app.route("/")
def home():
    return redirect(url_for("mentor_dashboard"))


@app.route("/mentor/dashboard")
def mentor_dashboard():
    df = pd.read_csv(DATA_PATH)

    df["attendance"] = df.apply(calculate_attendance, axis=1)
    df["placement_score"] = df.apply(
        lambda row: calculate_placement_score(row, row["attendance"]), axis=1
    )
    df["risk"] = df["placement_score"].apply(calculate_risk)

    return render_template(
        "mentor_dashboard.html",
        students=df.to_dict(orient="records"),
        total_students=len(df),
        low_count=len(df[df["risk"] == "Low"]),
        mid_count=len(df[df["risk"] == "Medium"]),
        high_count=len(df[df["risk"] == "High"]),
    )


@app.route("/student/<int:student_id>")
def student_dashboard(student_id):
    df = pd.read_csv(DATA_PATH)
    student_df = df[df["student_id"] == student_id]

    if student_df.empty:
        return "Student not found", 404

    student = student_df.iloc[0].to_dict()

    # ======================================================
    # 🔹 Attendance Logic
    # ======================================================

    total_classes = student.get("total_classes", 0)
    attended = student.get("classes_attended", 0)

    attended = min(attended, total_classes)  # safety cap

    attendance_percentage = calculate_attendance(student)
    min_required = int(0.75 * total_classes)

    if attended >= min_required:
        can_miss = attended - min_required
        need_more = 0
    else:
        can_miss = 0
        need_more = min_required - attended

    # Add to student dict
    student["total_classes"] = total_classes
    student["attended_hours"] = attended
    student["overall_attendance_percentage"] = attendance_percentage
    student["min_required"] = min_required
    student["can_miss"] = can_miss
    student["need_more"] = need_more

    # ======================================================
    # 🔹 Placement & Risk
    # ======================================================

    placement_score = calculate_placement_score(student, attendance_percentage)
    risk = calculate_risk(placement_score)
    goal_divergence = "At Risk" if risk == "High" else "On Track"

    # ======================================================
    # 🔹 Alerts
    # ======================================================

    alerts = []

    if attendance_percentage < 75:
        alerts.append(f"Attendance is {attendance_percentage}%, below required 75%.")

    if student.get("backlogs_count", 0) > 0:
        alerts.append("You have pending backlogs.")

    if student.get("study_hours_per_day", 0) < 3:
        alerts.append("Increase study hours to at least 3 hours daily.")

    if not alerts:
        alerts.append("No critical alerts. Keep up the good work!")

    # ======================================================
    # 🔹 Subject Builder (FIXED with external_recommendations)
    # ======================================================

    def create_subject(name, prefix):
        cia1 = student.get(f"{prefix}_cia1", 0)
        cia2 = student.get(f"{prefix}_cia2", 0)
        sa1 = student.get(f"{prefix}_sa1", 0)
        sa2 = student.get(f"{prefix}_sa2", 0)

        total_internal = cia1 + cia2 + sa1 + sa2
        internal_normalized = round((total_internal / 300) * 100, 2)

        return {
            "name": name,
            "cia1": cia1,
            "cia2": cia2,
            "sa1": sa1,
            "sa2": sa2,
            "total_internal": total_internal,
            "internal_normalized": internal_normalized,
            "external_recommendations": {
                "A": external_marks_needed(internal_normalized, 85),
                "B": external_marks_needed(internal_normalized, 75),
                "C": external_marks_needed(internal_normalized, 65),
                "D": external_marks_needed(internal_normalized, 50),
            }
        }

    subject_definitions = [
        ("Machine Learning", "ml"),
        ("Cloud Computing", "cc"),
        ("Compiler Design", "cd"),
        ("Software Engineering", "se"),
        ("Data Structures", "ds"),
    ]

    subjects = [create_subject(name, prefix) for name, prefix in subject_definitions]

    # ======================================================
    # 🔹 Calendar Events
    # ======================================================

    calendar_events = [
        {"title": "Midterm Exam", "start": "2026-06-15"},
        {"title": "Final Exam", "start": "2026-09-10"},
    ]

    # ======================================================
    # 🔹 Render
    # ======================================================

    return render_template(
        "student_dashboard.html",
        student=student,
        placement_score=placement_score,
        risk=risk,
        alerts=alerts,
        subjects=subjects,
        calendar_events=calendar_events,
        goal_divergence=goal_divergence,
    )


# ======================================================
# 🔹 Run App
# ======================================================

if __name__ == "__main__":
    app.run(debug=True)
