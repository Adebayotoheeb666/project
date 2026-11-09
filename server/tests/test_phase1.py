def bootstrap(client):
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"name": "Ada Admin", "password": "password1", "school_name": "Greenfield College"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_bootstrap_and_login(client):
    assert client.get("/api/v1/auth/bootstrap-status").json()["needs_bootstrap"] is True
    token = bootstrap(client)
    assert client.get("/api/v1/auth/bootstrap-status").json()["needs_bootstrap"] is False
    me = client.get(" /api/v1/auth/me".strip(), headers=auth(token))
    assert me.status_code == 200
    assert me.json()["id"] == "admin"
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "password1"})
    assert login.status_code == 200
    bad = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert bad.status_code == 401


def test_directory_flow_and_events(client):
    token = bootstrap(client)
    headers = auth(token)

    created_class = client.post(
        "/api/v1/classes",
        headers=headers,
        json={"id": "SS2A", "name": "SS2 A", "academic_year": "2025/2026"},
    )
    assert created_class.status_code == 201

    subject = client.post(
        "/api/v1/subjects",
        headers=headers,
        json={"id": "MATH", "name": "Mathematics", "code": "MATH"},
    )
    assert subject.status_code == 201

    teacher = client.post(
        "/api/v1/teachers",
        headers=headers,
        json={
            "id": "teacher_ade",
            "name": "Ade Teacher",
            "password": "password1",
            "role": {"role": "teacher", "classes": ["SS2A"], "subjects": ["MATHEMATICS"]},
        },
    )
    assert teacher.status_code == 201

    student = client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "id": "FUTA/SS2A/042",
            "class_id": "SS2A",
            "data": {"first_name": "Kemi", "last_name": "Ojo", "admission_number": "042"},
        },
    )
    assert student.status_code == 201
    found = client.get("/api/v1/students", headers=headers, params={"q": "Kemi"})
    assert found.status_code == 200
    assert found.json()[0]["id"] == "FUTA/SS2A/042"

    overview = client.get("/api/v1/overview", headers=headers)
    assert overview.json()["students"] == 1
    assert overview.json()["events"] >= 4

    teacher_headers = auth(
        client.post("/api/v1/auth/login", json={"username": "teacher_ade", "password": "password1"}).json()["token"]
    )
    forbidden = client.get("/api/v1/teachers", headers=teacher_headers)
    assert forbidden.status_code == 403

    revoke = client.post("/api/v1/teachers/teacher_ade/revoke", headers=headers)
    assert revoke.status_code == 200
    blocked = client.post("/api/v1/auth/login", json={"username": "teacher_ade", "password": "password1"})
    assert blocked.status_code == 422


def test_unauthenticated(client):
    bootstrap(client)
    response = client.get("/api/v1/students")
    assert response.status_code == 401
