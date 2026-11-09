import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tests.test_phase1 import auth, bootstrap


def teacher_key() -> str:
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(public).decode("ascii")


def setup_teacher(client):
    token = bootstrap(client)
    headers = auth(token)
    client.post(
        "/api/v1/classes",
        headers=headers,
        json={"id": "SS2A", "name": "SS2 A", "academic_year": "2025/2026"},
    )
    client.post(
        "/api/v1/classes",
        headers=headers,
        json={"id": "SS1B", "name": "SS1 B", "academic_year": "2025/2026"},
    )
    client.post(
        "/api/v1/teachers",
        headers=headers,
        json={
            "id": "teacher_ade",
            "name": "Ade Teacher",
            "password": "password1",
            "role": {"role": "teacher", "classes": ["SS2A"], "subjects": ["MATH"]},
        },
    )
    client.post(
        "/api/v1/students",
        headers=headers,
        json={"id": "FUTA/SS2A/042", "class_id": "SS2A", "data": {"first_name": "Kemi", "last_name": "Ojo"}},
    )
    client.post(
        "/api/v1/students",
        headers=headers,
        json={"id": "FUTA/SS1B/007", "class_id": "SS1B", "data": {"first_name": "Tunde", "last_name": "Bello"}},
    )
    return headers


def test_teacher_only_sees_assigned_class(client):
    setup_teacher(client)
    teacher_headers = auth(
        client.post("/api/v1/auth/login", json={"username": "teacher_ade", "password": "password1"}).json()["token"]
    )
    classes = client.get("/api/v1/classes", headers=teacher_headers).json()
    assert [row["id"] for row in classes] == ["SS2A"]
    students = client.get("/api/v1/students", headers=teacher_headers).json()
    assert [row["id"] for row in students] == ["FUTA/SS2A/042"]
    hidden = client.get("/api/v1/students/FUTA/SS1B/007", headers=teacher_headers)
    assert hidden.status_code == 403


def test_device_enrollment_and_revoke(client):
    admin_headers = setup_teacher(client)
    ticket = client.post(
        "/api/v1/devices/enrollment-tickets",
        headers=admin_headers,
        json={"base_url": "http://192.168.0.10:8080"},
    )
    assert ticket.status_code == 201, ticket.text
    payload = ticket.json()
    assert payload["school_id"]
    assert payload["school_public_key"]
    assert payload["base_url"] == "http://192.168.0.10:8080"

    inspect = client.get(f"/api/v1/devices/enrollment-tickets/{payload['ticket']}")
    assert inspect.status_code == 200
    qr = client.get(f"/api/v1/devices/enrollment-tickets/{payload['ticket']}/qr.png")
    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/png"

    enroll = client.post(
        "/api/v1/devices/enroll",
        json={
            "ticket": payload["ticket"],
            "teacher_id": "teacher_ade",
            "password": "password1",
            "device_id": "device_001",
            "device_name": "Ade Pixel",
            "public_key": teacher_key(),
        },
    )
    assert enroll.status_code == 200, enroll.text
    body = enroll.json()
    assert body["device"]["id"] == "device_001"
    assert body["teacher"]["id"] == "teacher_ade"
    assert [row["id"] for row in body["directory"]["students"]] == ["FUTA/SS2A/042"]

    reuse = client.post(
        "/api/v1/devices/enroll",
        json={
            "ticket": payload["ticket"],
            "teacher_id": "teacher_ade",
            "password": "password1",
            "device_id": "device_002",
            "device_name": "Other",
            "public_key": teacher_key(),
        },
    )
    assert reuse.status_code == 422

    devices = client.get("/api/v1/devices", headers=admin_headers).json()
    assert devices[0]["id"] == "device_001"

    revoked = client.post("/api/v1/devices/device_001/revoke", headers=admin_headers)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"


def test_canonical_event_matches_android_fixture():
    import json

    encoded = json.dumps(
        {
            "type": "STUDENT_CREATE",
            "payload": {"first_name": "Kemi", "ca": 20},
            "id": "evt-1",
            "lamport_clock": 42,
            "student_id": "FUTA/SS2A/042",
            "timestamp": 1726850000000,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    assert encoded == (
        '{"id":"evt-1","lamport_clock":42,"payload":{"ca":20,"first_name":"Kemi"},'
        '"student_id":"FUTA/SS2A/042","timestamp":1726850000000,"type":"STUDENT_CREATE"}'
    )
