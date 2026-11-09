def bootstrap(client):
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"name": "Ada Admin", "password": "password1", "school_name": "Greenfield College"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_backup_and_restore(client):
    admin_token = bootstrap(client)
    headers = auth(admin_token)

    # Create some data
    client.post("/api/v1/classes", headers=headers, json={"id": "JSS1A", "name": "JSS1 A", "academic_year": "2025/2026"})

    # 1. Trigger Backup
    backup_res = client.post("/api/v1/system/backup", headers=headers)
    assert backup_res.status_code == 200, backup_res.text
    backup_data = backup_res.json()
    assert backup_data["filename"].startswith("lsia_backup_")
    assert backup_data["size_bytes"] > 0
    assert "signature" in backup_data

    filename = backup_data["filename"]

    # 2. List Backups
    list_res = client.get("/api/v1/system/backups", headers=headers)
    assert list_res.status_code == 200
    backups = list_res.json()
    assert len(backups) >= 1
    assert any(b["filename"] == filename for b in backups)

    # 3. Download Backup
    dl_res = client.get(f"/api/v1/system/backups/{filename}/download", headers=headers)
    assert dl_res.status_code == 200
    assert len(dl_res.content) == backup_data["size_bytes"]

    # 4. Trigger Restore
    restore_res = client.post("/api/v1/system/restore", headers=headers, json={"filename": filename})
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "ok"
