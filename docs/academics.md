# Academic Management Specification

LSIA manages attendance and scores locally without internet dependencies.

## Continuous Assessment (CA) and Examination Scores

- **Maximum CA Score**: 40.0
- **Maximum Exam Score**: 60.0
- **Maximum Total Score**: 100.0 (Sum of CA and Exam)

### Grading Scale

| Score Range | Grade | Classification |
|-------------|-------|----------------|
| 75.0 – 100.0 | A1 | Excellent |
| 70.0 – 74.9 | B2 | Very Good |
| 65.0 – 69.9 | B3 | Good |
| 60.0 – 64.9 | C4 | Credit |
| 55.0 – 59.9 | C5 | Credit |
| 50.0 – 54.9 | C6 | Credit |
| 45.0 – 49.9 | D7 | Pass |
| 40.0 – 44.9 | E8 | Pass |
| 0.0 – 39.9 | F9 | Fail |

## Attendance Tracking

- Recorded per student, class, and date.
- Allowed statuses: `present`, `absent`, `late`, `excused`.
- Attendance percentage formula: `(present + late) / total_days * 100`.

## Permissions

- Teachers can only enter scores and attendance for classes and subjects assigned to their profile.
- Modifications emit signed events (`SCORE_UPDATE` and `ATTENDANCE_RECORD`).
