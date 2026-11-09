from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lsia.application.academics import attendance_summary, calculate_grade
from lsia.application.auth import school_name
from lsia.application.errors import NotFound
from lsia.infrastructure.models import Attendance, SchoolClass, Score, Student, Subject, Teacher


def ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def generate_broadsheet(session: Session, class_id: str, term: str) -> dict[str, Any]:
    klass = session.get(SchoolClass, class_id)
    if klass is None:
        raise NotFound(f"Class '{class_id}' not found.")

    students = list(
        session.scalars(
            select(Student).where(Student.class_id == class_id).order_by(Student.id)
        ).all()
    )
    subjects = list(session.scalars(select(Subject).order_by(Subject.code)).all())

    student_ids = [s.id for s in students]
    scores = list(
        session.scalars(
            select(Score).where(
                Score.student_id.in_(student_ids),
                Score.term == term,
            )
        ).all()
    )

    # Map student_id -> { subject_id: Score }
    scores_by_student: dict[str, dict[str, Score]] = {s.id: {} for s in students}
    for sc in scores:
        if sc.student_id in scores_by_student:
            scores_by_student[sc.student_id][sc.subject_id] = sc

    # Subject statistics & positions
    subject_stats: dict[str, dict[str, Any]] = {}
    for subj in subjects:
        subj_scores = [
            scores_by_student[s.id][subj.id].total_score
            for s in students
            if subj.id in scores_by_student[s.id]
            and scores_by_student[s.id][subj.id].total_score is not None
        ]
        if subj_scores:
            subject_stats[subj.id] = {
                "count": len(subj_scores),
                "highest": max(subj_scores),
                "lowest": min(subj_scores),
                "average": round(sum(subj_scores) / len(subj_scores), 1),
            }
        else:
            subject_stats[subj.id] = {
                "count": 0,
                "highest": None,
                "lowest": None,
                "average": None,
            }

    # Subject ranking per subject
    subject_ranks: dict[str, dict[str, str]] = {subj.id: {} for subj in subjects}
    for subj in subjects:
        # Sort students descending by score in this subject
        valid_entries = [
            (s.id, scores_by_student[s.id][subj.id].total_score)
            for s in students
            if subj.id in scores_by_student[s.id]
            and scores_by_student[s.id][subj.id].total_score is not None
        ]
        valid_entries.sort(key=lambda x: x[1], reverse=True)
        # Assign ranks
        current_rank = 1
        for idx, (sid, score_val) in enumerate(valid_entries):
            if idx > 0 and score_val < valid_entries[idx - 1][1]:
                current_rank = idx + 1
            subject_ranks[subj.id][sid] = ordinal(current_rank)

    # Student row computations
    student_rows = []
    for s in students:
        s_scores = scores_by_student[s.id]
        total_marks = 0.0
        subject_count = 0
        subject_entries: dict[str, Any] = {}

        for subj in subjects:
            sc = s_scores.get(subj.id)
            if sc and sc.total_score is not None:
                total_marks += sc.total_score
                subject_count += 1
                g = calculate_grade(sc.total_score)
                subject_entries[subj.id] = {
                    "ca_score": sc.ca_score,
                    "exam_score": sc.exam_score,
                    "total_score": sc.total_score,
                    "grade": g["grade"],
                    "remark": g["remark"],
                    "position": subject_ranks[subj.id].get(s.id, "—"),
                }
            else:
                subject_entries[subj.id] = None

        avg = round(total_marks / subject_count, 1) if subject_count > 0 else 0.0

        student_rows.append(
            {
                "student_id": s.id,
                "name": f"{s.data_json.get('first_name', '')} {s.data_json.get('last_name', '')}".strip()
                or s.id,
                "admission_number": s.data_json.get("admission_number", ""),
                "subjects": subject_entries,
                "total_marks": round(total_marks, 1),
                "subjects_taken": subject_count,
                "average_score": avg,
            }
        )

    # Class ranking by average_score
    student_rows.sort(key=lambda r: (r["average_score"], r["total_marks"]), reverse=True)
    current_class_rank = 1
    for idx, row in enumerate(student_rows):
        if idx > 0 and (row["average_score"], row["total_marks"]) < (
            student_rows[idx - 1]["average_score"],
            student_rows[idx - 1]["total_marks"],
        ):
            current_class_rank = idx + 1
        row["position"] = ordinal(current_class_rank)

    # Class overall average
    all_avgs = [r["average_score"] for r in student_rows if r["subjects_taken"] > 0]
    class_avg = round(sum(all_avgs) / len(all_avgs), 1) if all_avgs else 0.0

    return {
        "school_name": school_name(session),
        "class_id": klass.id,
        "class_name": klass.name,
        "academic_year": klass.academic_year,
        "term": term,
        "total_students": len(students),
        "class_average": class_avg,
        "subjects": [{"id": subj.id, "name": subj.name, "code": subj.code, "stats": subject_stats[subj.id]} for subj in subjects],
        "rows": student_rows,
    }


def generate_student_report(session: Session, student_id: str, term: str) -> dict[str, Any]:
    student = session.get(Student, student_id)
    if student is None:
        raise NotFound(f"Student '{student_id}' not found.")

    if not student.class_id:
        raise NotFound(f"Student '{student_id}' is not assigned to a class.")

    broadsheet = generate_broadsheet(session, student.class_id, term)
    student_row = next((r for r in broadsheet["rows"] if r["student_id"] == student_id), None)
    if student_row is None:
        raise NotFound(f"Student data not found in broadsheet for class '{student.class_id}'.")

    # Attendance
    att_summary = attendance_summary(session, actor=Teacher(id="system", role_json={"role": "administrator"}), student_id=student_id)

    # Subject performance list
    subject_details = []
    for subj in broadsheet["subjects"]:
        entry = student_row["subjects"].get(subj["id"])
        if entry:
            subject_details.append(
                {
                    "subject_id": subj["id"],
                    "subject_name": subj["name"],
                    "subject_code": subj["code"],
                    "ca_score": entry["ca_score"],
                    "exam_score": entry["exam_score"],
                    "total_score": entry["total_score"],
                    "grade": entry["grade"],
                    "remark": entry["remark"],
                    "position": entry["position"],
                    "class_average": subj["stats"]["average"],
                }
            )

    avg = student_row["average_score"]
    # Teacher & Principal Comments based on performance
    if avg >= 75.0:
        teacher_comment = "An outstanding academic performance. Demonstrates exceptional discipline and mastery."
        principal_comment = "Excellent result. Keep maintaining this exemplary standard of excellence."
    elif avg >= 65.0:
        teacher_comment = "A very good performance. Consistently participates and shows strong aptitude."
        principal_comment = "Commendable performance. With a little more effort, the top position is within reach."
    elif avg >= 50.0:
        teacher_comment = "Satisfactory effort shown, but there is room for significant academic improvement."
        principal_comment = "Fair result. Advised to devote more study hours to key subjects next term."
    else:
        teacher_comment = "Weak academic performance this term. Needs intensive revision and close guidance."
        principal_comment = "Poor result. Urgent improvement required. Parent conference recommended."

    return {
        "school_name": broadsheet["school_name"],
        "student": {
            "id": student.id,
            "name": student_row["name"],
            "admission_number": student_row["admission_number"],
            "gender": student.data_json.get("gender", ""),
            "date_of_birth": student.data_json.get("date_of_birth", ""),
        },
        "class": {
            "id": broadsheet["class_id"],
            "name": broadsheet["class_name"],
            "academic_year": broadsheet["academic_year"],
            "term": term,
            "total_students": broadsheet["total_students"],
            "class_average": broadsheet["class_average"],
        },
        "performance": {
            "total_marks": student_row["total_marks"],
            "subjects_taken": student_row["subjects_taken"],
            "average_score": student_row["average_score"],
            "position": student_row["position"],
            "subjects": subject_details,
        },
        "attendance": att_summary,
        "comments": {
            "teacher_comment": teacher_comment,
            "principal_comment": principal_comment,
        },
    }
