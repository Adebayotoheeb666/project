import base64
import json
import time
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from lsia.application.sync import canonical_operation_json


def bootstrap(client):
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"name": "Ada Admin", "password": "password1", "school_name": "Greenfield College"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_school_data(client, admin_token):
    headers = auth(admin_token)
    client.post("/api/v1/classes", headers=headers, json={"id": "SS1A", "name": "SS1 A", "academic_year": "2025/2026"})
    client.post("/api/v1/subjects", headers=headers, json={"id": "MTH", "name": "Mathematics", "code": "MTH"})
    client.post("/api/v1/subjects", headers=headers, json={"id": "ENG", "name": "English", "code": "ENG"})

    # Create students
    client.post(
        "/api/v1/students",
        headers=headers,
        json={"id": "STU/001", "class_id": "SS1A", "data": {"first_name": "Chidi", "last_name": "Eze", "admission_number": "001"}},
    )
    client.post(
        "/api/v1/students",
        headers=headers,
        json={"id": "STU/002", "class_id": "SS1A", "data": {"first_name": "Amina", "last_name": "Bello", "admission_number": "002"}},
    )


def test_attendance_and_scores(client):
    admin_token = bootstrap(client)
    headers = auth(admin_token)
    setup_school_data(client, admin_token)

    # 1. Record Attendance
    att_res = client.post(
        "/api/v1/attendance",
        headers=headers,
        json={
            "class_id": "SS1A",
            "date": "2026-11-08",
            "records": [
                {"student_id": "STU/001", "status": "present"},
                {"student_id": "STU/002", "status": "absent"},
            ],
        },
    )
    assert att_res.status_code == 200, att_res.text
    data = att_res.json()
    assert len(data) == 2
    assert data[0]["status"] == "present"

    # Query attendance
    att_list = client.get("/api/v1/attendance", headers=headers, params={"class_id": "SS1A"})
    assert att_list.status_code == 200
    assert len(att_list.json()) == 2

    # Attendance summary
    summary = client.get("/api/v1/attendance/summary", headers=headers, params={"class_id": "SS1A"})
    assert summary.status_code == 200
    assert summary.json()["total_days"] == 2
    assert summary.json()["present"] == 1
    assert summary.json()["absent"] == 1

    # 2. Record Scores
    score_res = client.post(
        "/api/v1/scores",
        headers=headers,
        json={
            "scores": [
                {"student_id": "STU/001", "subject_id": "MTH", "term": "2025/2026-Term1", "ca_score": 35.0, "exam_score": 50.0},
                {"student_id": "STU/002", "subject_id": "MTH", "term": "2025/2026-Term1", "ca_score": 25.0, "exam_score": 35.0},
                {"student_id": "STU/001", "subject_id": "ENG", "term": "2025/2026-Term1", "ca_score": 30.0, "exam_score": 45.0},
                {"student_id": "STU/002", "subject_id": "ENG", "term": "2025/2026-Term1", "ca_score": 38.0, "exam_score": 55.0},
            ]
        },
    )
    assert score_res.status_code == 200, score_res.text
    scores_out = score_res.json()
    assert len(scores_out) == 4
    # STU/001 in MTH: 35 + 50 = 85 -> Grade A1 (Excellent)
    assert scores_out[0]["total_score"] == 85.0
    assert scores_out[0]["grade"] == "A1"
    assert scores_out[0]["remark"] == "Excellent"


def test_broadsheet_and_report_cards(client):
    admin_token = bootstrap(client)
    headers = auth(admin_token)
    setup_school_data(client, admin_token)

    # Insert scores
    client.post(
        "/api/v1/scores",
        headers=headers,
        json={
            "scores": [
                {"student_id": "STU/001", "subject_id": "MTH", "term": "2025/2026-Term1", "ca_score": 35.0, "exam_score": 50.0},
                {"student_id": "STU/002", "subject_id": "MTH", "term": "2025/2026-Term1", "ca_score": 25.0, "exam_score": 35.0},
            ]
        },
    )

    # Broadsheet
    bs_res = client.get(
        "/api/v1/reports/broadsheet",
        headers=headers,
        params={"class_id": "SS1A", "term": "2025/2026-Term1"},
    )
    assert bs_res.status_code == 200, bs_res.text
    bs = bs_res.json()
    assert bs["class_id"] == "SS1A"
    assert bs["total_students"] == 2
    assert len(bs["rows"]) == 2
    # STU/001 has 85, STU/002 has 60 -> STU/001 is 1st, STU/002 is 2nd
    assert bs["rows"][0]["student_id"] == "STU/001"
    assert bs["rows"][0]["position"] == "1st"
    assert bs["rows"][1]["student_id"] == "STU/002"
    assert bs["rows"][1]["position"] == "2nd"

    # Individual Student Report Card
    rep_res = client.get(
        "/api/v1/reports/student",
        headers=headers,
        params={"student_id": "STU/001", "term": "2025/2026-Term1"},
    )
    assert rep_res.status_code == 200, rep_res.text
    rep = rep_res.json()
    assert rep["student"]["id"] == "STU/001"
    assert rep["performance"]["position"] == "1st"
    assert rep["comments"]["principal_comment"] != ""


def test_device_sync_protocol(client):
    admin_token = bootstrap(client)
    headers = auth(admin_token)
    setup_school_data(client, admin_token)

    # Create teacher
    client.post(
        "/api/v1/teachers",
        headers=headers,
        json={
            "id": "teacher_kemi",
            "name": "Kemi Teacher",
            "password": "teacherpass1",
            "role": {"role": "teacher", "classes": ["SS1A"], "subjects": ["MTH"]},
        },
    )

    # Issue enrollment ticket
    ticket_res = client.post("/api/v1/devices/enrollment-tickets", headers=headers, json={})
    assert ticket_res.status_code == 201
    ticket = ticket_res.json()["ticket"]

    # Generate device Ed25519 keypair
    device_key = Ed25519PrivateKey.generate()
    pub_bytes = device_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    device_pub_b64 = base64.b64encode(pub_bytes).decode("ascii")
    device_id = "phone_kemi_01"

    # Enroll device
    enroll_res = client.post(
        "/api/v1/devices/enroll",
        json={
            "ticket": ticket,
            "teacher_id": "teacher_kemi",
            "password": "teacherpass1",
            "device_id": device_id,
            "device_name": "Kemi Samsung Galaxy",
            "public_key": device_pub_b64,
        },
    )
    assert enroll_res.status_code == 200, enroll_res.text

    # 1. Test Handshake
    now_ms = int(time.time() * 1000)
    challenge = f"HANDSHAKE:{device_id}:{now_ms}".encode("utf-8")
    challenge_sig = base64.b64encode(device_key.sign(challenge)).decode("ascii")

    handshake_res = client.post(
        "/api/v1/sync/handshake",
        json={"device_id": device_id, "timestamp": now_ms, "challenge_response": challenge_sig},
    )
    assert handshake_res.status_code == 200, handshake_res.text
    hs = handshake_res.json()
    assert hs["status"] == "ready"
    assert hs["teacher_id"] == "teacher_kemi"

    # 2. Test Push Operations (Signed SCORE_UPDATE)
    op_id = str(uuid.uuid4())
    op_data = {
        "id": op_id,
        "student_id": "STU/001",
        "type": "SCORE_UPDATE",
        "payload": {
            "subject_id": "MTH",
            "term": "2025/2026-Term1",
            "ca_score": 38.0,
            "exam_score": 58.0,
        },
        "teacher_id": "teacher_kemi",
        "device_id": device_id,
        "timestamp": now_ms,
        "lamport_clock": 5,
    }
    canonical = canonical_operation_json(op_data)
    op_sig = base64.b64encode(device_key.sign(canonical)).decode("ascii")
    op_data["signature"] = op_sig

    push_res = client.post(
        "/api/v1/sync/push",
        json={"device_id": device_id, "operations": [op_data]},
    )
    assert push_res.status_code == 200, push_res.text
    receipts = push_res.json()["receipts"]
    assert len(receipts) == 1
    assert receipts[0]["id"] == op_id
    assert receipts[0]["status"] == "APPLIED"

    # Verify score in database was updated
    scores = client.get("/api/v1/scores", headers=headers, params={"student_id": "STU/001", "subject_id": "MTH"}).json()
    assert len(scores) == 1
    assert scores[0]["ca_score"] == 38.0
    assert scores[0]["exam_score"] == 58.0
    assert scores[0]["total_score"] == 96.0

    # Test Replay Protection
    push_replay = client.post(
        "/api/v1/sync/push",
        json={"device_id": device_id, "operations": [op_data]},
    )
    assert push_replay.status_code == 200
    assert push_replay.json()["receipts"][0]["status"] == "APPLIED"

    # 3. Test Pull Operations
    pull_res = client.post(
        "/api/v1/sync/pull",
        json={"device_id": device_id, "since_clock": 0, "limit": 10},
    )
    assert pull_res.status_code == 200, pull_res.text
    pull_data = pull_res.json()
    assert len(pull_data["events"]) >= 1
    pulled_ids = [e["id"] for e in pull_data["events"]]
    assert op_id in pulled_ids


def test_conflict_and_approval_workflow(client):
    admin_token = bootstrap(client)
    headers = auth(admin_token)
    setup_school_data(client, admin_token)

    # 1. Create a simulated conflict event
    ev_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"id": "STU/003", "class_id": "SS1A", "data": {"first_name": "Test", "last_name": "Student"}},
    )
    assert ev_res.status_code == 201

    # Insert a conflict event directly for resolution test
    from lsia.infrastructure.models import Event
    from lsia.infrastructure.db import SessionLocal

    with SessionLocal() as s:
        conflict_event = Event(
            id=str(uuid.uuid4()),
            student_id="STU/003",
            operation="STUDENT_UPSERT",
            payload={"data": {"first_name": "Modified", "last_name": "Student"}},
            teacher_id="admin",
            device_id="school-computer",
            signature="test",
            timestamp=1000,
            lamport_clock=10,
            status="CONFLICT",
        )
        s.add(conflict_event)
        s.commit()
        c_id = conflict_event.id

    # List conflicts
    conflicts_res = client.get("/api/v1/conflicts", headers=headers)
    assert conflicts_res.status_code == 200
    conflicts = conflicts_res.json()
    assert any(c["id"] == c_id for c in conflicts)

    # Resolve conflict with use_incoming
    resolve_res = client.post(
        f"/api/v1/conflicts/{c_id}/resolve",
        headers=headers,
        json={"choice": "use_incoming"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"

    # Verify student was updated
    stu = client.get("/api/v1/students/STU%2F003", headers=headers).json()
    assert stu["data"]["first_name"] == "Modified"
